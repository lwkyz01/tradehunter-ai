import os
import requests
import pandas as pd
import streamlit as st
from engine import DEFAULT_SYMBOLS, indicators, backtest, db_connect, paper_trade, sample_data

st.set_page_config(page_title='TRADEHUNTER AI',page_icon='📈',layout='wide')
st.title('📈 TRADEHUNTER AI')
st.caption('Research, backtesting and simulated trades only. No real orders are placed. Signals are rules-based, not predictive AI.')

@st.cache_data(ttl=900)
def prices(symbol,period,interval):
    import yfinance as yf
    d=yf.download(symbol,period=period,interval=interval,auto_adjust=True,progress=False,threads=False)
    if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
    return d.dropna(subset=['Open','High','Low','Close'])

def telegram(message):
    token=os.getenv('TELEGRAM_BOT_TOKEN'); chat=os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat: return 'Telegram not configured; see README.'
    try:
        r=requests.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':message},timeout=10);r.raise_for_status();return 'Telegram alert sent.'
    except requests.RequestException as e: return f'Alert failed: {e}'

with st.sidebar:
    st.header('Settings')
    symbols=st.text_area('Symbols, comma-separated',','.join(DEFAULT_SYMBOLS))
    period=st.selectbox('History', ['1y','2y','5y'],index=1)
    fee=st.number_input('Estimated fees (basis points per trade)',0,500,10)
    slip=st.number_input('Estimated slippage (basis points per trade)',0,500,5)
    st.caption('Symbols: BHP.AX = ASX; BTC-USD = crypto. Data from Yahoo Finance via yfinance; often delayed and not guaranteed.')
    demo=st.checkbox('Offline demo data (synthetic, not market prices)',value=False)

watch=[s.strip().upper() for s in symbols.split(',') if s.strip()][:30]
tabs=st.tabs(['Scanner','Backtest','Paper trading','Alerts'])
with tabs[0]:
    st.subheader('Market scanner')
    st.caption('Signal = SMA20 above SMA50, closing price above SMA20, RSI between 50 and 70. Evaluated on latest completed daily candle.')
    if st.button('Scan watchlist',type='primary'):
        rows=[]
        for symbol in watch:
            try:
                d=sample_data() if demo else prices(symbol,period,'1d')
                if len(d)<65: continue
                x=indicators(d).dropna(subset=['SMA50','RSI']); last=x.iloc[-1]
                rows.append({'Symbol':symbol,'As of':str(x.index[-1].date()),'Price':round(float(last['Close']),4),'RSI':round(float(last['RSI']),1),'SMA20':round(float(last['SMA20']),3),'SMA50':round(float(last['SMA50']),3),'Watch signal':bool(last['Signal'])})
            except Exception as e: st.warning(f'{symbol}: {e}')
        if rows:
            result=pd.DataFrame(rows).sort_values('Watch signal',ascending=False)
            st.session_state['scan']=result
    if 'scan' in st.session_state: st.dataframe(st.session_state['scan'],use_container_width=True,hide_index=True)
with tabs[1]:
    st.subheader('Historical backtest')
    symbol=st.selectbox('Backtest symbol',watch or ['SPY'])
    initial=st.number_input('Starting simulated balance',min_value=100.,value=10000.,step=100.)
    if st.button('Run backtest'):
        try:
            d=sample_data() if demo else prices(symbol,period,'1d')
            if len(d)<80: st.error('Not enough historical data.')
            else:
                r=backtest(d,initial,fee,slip)
                a,b,c,e=st.columns(4)
                a.metric('Total return',f"{r['return_pct']:.2f}%")
                b.metric('Max drawdown',f"{r['max_drawdown_pct']:.2f}%")
                c.metric('Closed trades',r['closed_trades'])
                e.metric('Win rate',f"{r['win_rate_pct']:.1f}%" if r['win_rate_pct'] is not None else 'N/A')
                st.line_chart(r['equity'].set_index('Date')['Equity'])
                st.dataframe(r['trades'],hide_index=True,use_container_width=True)
                st.caption('Simplified long-only, all-in strategy; next-session open fills with estimated friction. No shorting, financing, taxes, liquidity limits or intraday stop orders. Backtest performance is not predictive; no out-of-sample validation in V1.')
        except Exception as exc: st.error(str(exc))
with tabs[2]:
    st.subheader('Paper trading journal')
    conn=db_connect()
    st.caption('Records simulated transactions. Does not connect to a brokerage or enforce a cash balance.')
    sym=st.selectbox('Symbol',watch or ['SPY'],key='paper_sym')
    side=st.radio('Action',['BUY','SELL'],horizontal=True)
    quantity=st.number_input('Units',min_value=.000001,value=1.,format='%.6f')
    price=st.number_input('Simulated fill price (in symbol quote currency)',min_value=.000001,value=100.,format='%.4f')
    if st.button('Record paper trade'):
        try: paper_trade(conn,sym,side,quantity,price,fee);st.success('Simulated trade recorded.')
        except Exception as exc: st.error(str(exc))
    journal=pd.read_sql_query('SELECT timestamp,symbol,side,quantity,price,fee FROM paper_trades ORDER BY id DESC',conn)
    st.dataframe(journal,hide_index=True,use_container_width=True)
    st.caption('Currencies are not converted. Do not aggregate AUD and USD holdings as one account balance.')
with tabs[3]:
    st.subheader('Alerts')
    st.write('The scanner can notify you of qualifying watch signals via Telegram when configured.')
    if st.button('Check and send new signals'):
        conn=db_connect(); count=0
        for sym in watch:
            try:
                d=sample_data() if demo else prices(sym,period,'1d')
                if len(d)<65: continue
                x=indicators(d).dropna(subset=['SMA50','RSI']);last=x.iloc[-1]
                date=str(x.index[-1].date())
                seen=conn.execute('SELECT last_signal_date FROM alerts WHERE symbol=?',(sym,)).fetchone()
                if bool(last['Signal']) and (not seen or seen[0]!=date):
                    msg=f'TRADEHUNTER WATCH: {sym} | {date} | close {last["Close"]:.4f} | RSI {last["RSI"]:.1f}. Research only; not a buy recommendation.'
                    status='Demo mode: alert suppressed.' if demo else telegram(msg)
                    st.write(f'{sym}: {status}')
                    if status=='Telegram alert sent.':
                        conn.execute('INSERT OR REPLACE INTO alerts(symbol,last_signal_date) VALUES(?,?)',(sym,date));conn.commit()
                    count+=1
            except Exception as exc: st.warning(f'{sym}: {exc}')
        if count==0: st.info('No new qualifying signals.')
    st.caption('Alerts run when you click the button. To automate them, deploy a scheduled runner; the Streamlit interface itself does not run in the background.')
