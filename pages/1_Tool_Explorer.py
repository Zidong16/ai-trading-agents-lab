import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tool Explorer", layout="wide")
import auth
import ui
ui.sidebar_brand()
auth.require_auth()
auth.logout_button()
st.title("Tool Explorer")
st.caption("Week 1 deliverable: the AI-trading-agent landscape. "
           "Verify links, tag functions, expand — edit data/tools.csv in the repo.")

df = pd.read_csv("data/tools.csv")
buckets = st.multiselect("Bucket", sorted(df["bucket"].unique()),
                         default=sorted(df["bucket"].unique()))
only_verified = st.toggle("Verified links only", value=False)

view = df[df["bucket"].isin(buckets)]
if only_verified:
    view = view[view["verified"] == "yes"]

st.dataframe(view, use_container_width=True, hide_index=True,
             column_config={"link": st.column_config.LinkColumn("link")})
st.caption(f"{len(view)} of {len(df)} tools shown")
