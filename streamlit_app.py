import streamlit as st

st.set_page_config(page_title="AI Trading Agents Lab", page_icon="🤖", layout="wide")
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
| Agent Lab | Week 4 — hands-on eval | ⚪ not started |
""")
st.info("v0.1 — the skeleton is live. That was the point.")
