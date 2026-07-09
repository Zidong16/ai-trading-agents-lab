import streamlit as st

st.set_page_config(page_title="Backtest Lab", layout="wide")
import auth
import ui
ui.sidebar_brand()
auth.require_auth()
auth.logout_button()
st.title("Backtest Lab")
st.info("Feeds from Week 3 — code-based backtests on historical data. Paper only.")
st.markdown("""
Coming here as Week 3 progresses:
- FinRL / backtesting.py runs: return, drawdown, Sharpe/Sortino, win rate
- Signal → order pipeline trace (Alpaca paper endpoint)
- StockBench reality-check notes
""")
