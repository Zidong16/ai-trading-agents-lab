from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Changelog", layout="wide")
import auth
auth.require_auth()
auth.logout_button()
st.title("Changelog")
st.markdown(Path("CHANGELOG.md").read_text(encoding="utf-8"))
