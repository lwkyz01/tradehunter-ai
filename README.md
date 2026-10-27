# TRADEHUNTER AI V1

A beginner-friendly **stock + crypto market research prototype**. It includes a daily market scanner, a simple historical backtest, an SQLite paper-trading journal, and optional Telegram watch-signal alerts.

**Not financial advice. No real trades. No trained machine-learning predictor in V1.** The indicators are deterministic rules, not forecasts. Prices from Yahoo Finance via `yfinance` may be delayed, incomplete or unavailable, and Yahoo's terms/data rights should be checked before any commercial deployment. This app is intended for personal experimentation.

## Install (Windows / Mac)

1. Install Python 3.11 or 3.12 from https://python.org (on Windows, tick **Add Python to PATH**).
2. Unzip this folder, open Terminal (Mac) or PowerShell (Windows), and change into the folder containing `app.py`.
3. Run:

```bash
python -m venv .venv
```

Activate on Windows:

```powershell
.venv\Scripts\activate
```

Activate on Mac/Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local address shown, usually http://localhost:8501 . The browser can also be opened on your phone if hosted securely; localhost on a computer is not automatically accessible from a phone.

## First test

Tick **Offline demo data** in the sidebar, then click **Scan watchlist** and **Run backtest**. This is reproducible synthetic data and must not be confused with live market prices. Untick demo mode to request Yahoo Finance daily historical data.

## Symbol examples

- US stocks: `AAPL`, `MSFT`, `SPY`
- ASX: `BHP.AX`, `CBA.AX`
- Crypto quoted in USD: `BTC-USD`, `ETH-USD`, `SOL-USD`

## Trading logic

- 20-day SMA above 50-day SMA
- Price above 20-day SMA
- RSI (14, exponentially smoothed) between 50 and 70
- Exit when price closes below 20-day SMA or RSI above 75
- Backtest uses the **previous day's close signal** to trade at the **next day's open**, reducing lookahead bias. Execution includes configurable fees and slippage, but excludes many real-world effects.
- Backtests are in the instrument's quote currency and are not comparable across different currency denominations without FX conversion.
- Scanner is based on daily data, **not** real-time intraday day-trading signals.

## Telegram alerts

1. Create a bot through Telegram's `@BotFather`, obtain its token.
2. Send a message to your bot and find your chat ID via the Telegram Bot API (keep credentials private).
3. Set environment variables before launching:

Mac/Linux:
```bash
export TELEGRAM_BOT_TOKEN='your_token'
export TELEGRAM_CHAT_ID='your_chat_id'
```

Windows PowerShell:
```powershell
$env:TELEGRAM_BOT_TOKEN='your_token'
$env:TELEGRAM_CHAT_ID='your_chat_id'
```

4. Use the **Alerts** tab, click **Check and send new signals**. Alerts are deduplicated by symbol and signal date **only after successful delivery**. The demo mode suppresses Telegram sends.

**Important:** V1 alerts run only when you click the check button. It does not automatically poll markets in the background. A scheduler, deployment, logging and alert runner are needed for unattended alerts.

## Limitations and next steps

- No real-money trading or broker connectivity.
- Paper journal records trades but does not enforce starting cash, mark-to-market P&L, FX or margin.
- The backtest is a simplified all-in, long-only simulation. It has no train/test separation, stop-loss execution, spread modeling, market impact, survivorship-bias adjustment or tax calculations.
- A single historical backtest is not proof of a profitable strategy. Test out of sample and paper trade for an extended period.
- Add a licensed intraday feed and exchange calendars for true day-trading analysis.
- Add an independent scheduled alert worker, secure hosting, secrets management and proper monitoring before relying on unattended operation.
- If distributing trading signals commercially in Australia, get appropriate advice on Australian financial-services regulation.
