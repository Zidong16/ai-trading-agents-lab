import streamlit as st

st.set_page_config(page_title="Architecture Gallery", layout="wide")
st.title("Architecture Gallery")
st.info("Feeds from Week 2 — how agents 'think'.")
st.markdown("""
Coming here as Week 2 progresses:
- TradingAgents multi-agent debate flow (analysts → bull/bear debate → trader → risk → PM)
- FinRobot's 4-layer architecture
- LLM-reasoning vs RL vs rule/factor signals — comparison
- Real prompts & signal rules, annotated
""")
