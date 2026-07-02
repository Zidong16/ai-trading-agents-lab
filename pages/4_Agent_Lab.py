import streamlit as st

st.set_page_config(page_title="Agent Lab", layout="wide")
st.title("Agent Lab")
st.info("Feeds from Week 4 — one open-source agent, run and evaluated like an engineer.")
st.markdown("""
Coming here as Week 4 progresses:
- End-to-end agent run output for one ticker
- Consistency & grounding eval (same input twice → diff the rationales)
- What gets ported into my own multi-agent codebase, and why
""")
