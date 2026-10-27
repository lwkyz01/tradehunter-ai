import sqlite3
from datetime import datetime, timezone
import numpy as np
import pandas as pd

DEFAULT_SYMBOLS = ['AAPL','MSFT','NVDA','SPY','BHP.AX','CBA.AX','BTC-USD','ETH-USD','SOL-USD']

def indicators(df):
    d=df.copy().sort_index()
    d['SMA20']=d['Close'].rolling(20).mean()
    d['SMA50']=d['Close'].rolling(50).mean()
    delta=d['Close'].diff()
    gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rs=gain/loss.replace(0,np.nan)
    d['RSI']=100-100/(1+rs)
    d['ATR']=(pd.concat([(d['High']-d['Low']).abs(),(d['High']-d['Close'].shift()).abs(),(d['Low']-d['Close'].shift()).abs()],axis=1).max(axis=1)).rolling(14).mean()
    # Signal on close; execution at following session's open.
    d['Signal']=(d['SMA20']>d['SMA50']) & (d['Close']>d['SMA20']) & d['RSI'].between(50,70)
    d['Exit']=(d['Close']<d['SMA20']) | (d['RSI']>75)
    return d

def backtest(df, initial=10000., fee_bps=10, slippage_bps=5):
    d=indicators(df).dropna(subset=['SMA50','RSI']).copy()
    cash=float(initial); qty=0.; entry=0.; trades=[]; equity=[]
    rate=(fee_bps+slippage_bps)/10000
    for i in range(1,len(d)):
        prev=d.iloc[i-1]; now=d.iloc[i]; price=float(now['Open'])
        if price<=0: continue
        if qty and bool(prev['Exit']):
            proceeds=qty*price*(1-rate)
            trades.append({'Date':str(d.index[i].date()),'Action':'SELL','Price':round(price,4),'Units':round(qty,6),'PnL':round(proceeds-entry,2)})
            cash+=proceeds; qty=0.; entry=0.
        elif not qty and bool(prev['Signal']):
            # All-in simple baseline; includes estimated execution friction.
            qty=cash/(price*(1+rate)); entry=cash; cash=0.
            trades.append({'Date':str(d.index[i].date()),'Action':'BUY','Price':round(price,4),'Units':round(qty,6),'PnL':None})
        equity.append({'Date':d.index[i],'Equity':cash+qty*float(now['Close'])})
    final=cash+qty*float(d.iloc[-1]['Close']) if len(d) else initial
    curve=pd.DataFrame(equity)
    if len(curve):
        peak=curve['Equity'].cummax(); drawdown=float((curve['Equity']/peak-1).min())*100
    else: drawdown=0.
    sells=[t['PnL'] for t in trades if t['Action']=='SELL']
    return {'return_pct':(final/initial-1)*100,'final':final,'max_drawdown_pct':drawdown,'closed_trades':len(sells),'win_rate_pct':(sum(x>0 for x in sells)/len(sells)*100 if sells else None),'trades':pd.DataFrame(trades),'equity':curve}

def db_connect(path='tradehunter.db'):
    c=sqlite3.connect(path)
    c.execute('CREATE TABLE IF NOT EXISTS paper_trades (id INTEGER PRIMARY KEY, timestamp TEXT, symbol TEXT, side TEXT, quantity REAL, price REAL, fee REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS alerts (symbol TEXT PRIMARY KEY, last_signal_date TEXT)')
    c.commit(); return c

def paper_trade(c,symbol,side,quantity,price,fee_bps=10):
    side=side.upper(); quantity=float(quantity); price=float(price)
    if side not in ('BUY','SELL') or quantity<=0 or price<=0: raise ValueError('Invalid trade')
    if side=='SELL':
        held=c.execute("SELECT COALESCE(SUM(CASE WHEN side='BUY' THEN quantity ELSE -quantity END),0) FROM paper_trades WHERE symbol=?",(symbol,)).fetchone()[0]
        if quantity>held+1e-9: raise ValueError('Not enough simulated units to sell')
    fee=quantity*price*fee_bps/10000
    c.execute('INSERT INTO paper_trades(timestamp,symbol,side,quantity,price,fee) VALUES(?,?,?,?,?,?)',(datetime.now(timezone.utc).isoformat(),symbol,side,quantity,price,fee));c.commit()

def sample_data(n=260,seed=42):
    rng=np.random.default_rng(seed); dates=pd.bdate_range(end=pd.Timestamp.today().normalize(),periods=n)
    returns=rng.normal(.00025,.018,n); close=100*np.exp(np.cumsum(returns)); op=np.r_[close[0],close[:-1]]*(1+rng.normal(0,.003,n))
    high=np.maximum(op,close)*(1+rng.uniform(0,.012,n)); low=np.minimum(op,close)*(1-rng.uniform(0,.012,n))
    return pd.DataFrame({'Open':op,'High':high,'Low':low,'Close':close,'Volume':rng.integers(100000,1000000,n)},index=dates)
