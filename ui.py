"""Shared sidebar chrome shown on every page.

`sidebar_brand()` pins a single, non-clickable text line to the very top of the
sidebar — above Streamlit's automatic page-navigation list. In a multipage app
you can't put normal `st.sidebar.*` content above that auto nav, so we add the
label as a CSS ``::before`` on the nav container: it renders as plain,
unclickable text and always sits at the top.

Call once near the top of every page. CSS is global, so call order relative to
other sidebar content doesn't matter.
"""

from __future__ import annotations

import streamlit as st

# The non-clickable label. Change this one string to rename it.
BRAND = "自由自在的牛牛牛牛"


def sidebar_brand(name: str = BRAND) -> None:
    """Render a non-clickable label at the very top of the sidebar."""
    safe = str(name).replace("\\", "\\\\").replace('"', '\\"')
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebarNav"]::before {{
            content: "{safe}";
            display: block;
            padding: 0.75rem 1rem 0.40rem 1rem;
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1.3;
            /* inherits the sidebar text color, so it works in light & dark */
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
