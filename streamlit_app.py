import streamlit as st

import auth

st.set_page_config(page_title="AI Trading Agents Lab", page_icon="🤖", layout="wide")
auth.require_auth()
auth.logout_button()
st.title("AI Trading Agents Lab 天真快乐的牛牛号交易员")
st.caption("A technical study of AI trading agents — architectures, algorithms, and "
           "engineering mechanisms. Paper-only by design: no live trading.")

st.markdown("""
**What this is.** A living platform that grows as the 4-week research track progresses.
Every deliverable ships here as a page instead of dying in a document.

| Page | Feeds from | Status |
|---|---|---|
| Tool Explorer | Week 1 — landscape survey | 🟡 seeded, verifying |
| Architecture Gallery | Week 2 — how agents "think" | ⚪ not started |
| Backtest Lab | Week 3 — code-based backtests | ⚪ not started |
| Agent Lab | Week 4 — hands-on eval | 🟢 live — run a ticker end-to-end |
""")
st.info("v0.2 — password-gated, and the Agent Lab now runs the local TradingAgents "
        "pipeline on a ticker with live progress. Open **Agent Lab** in the sidebar.")
