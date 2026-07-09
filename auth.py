"""Authentication gate for the AI Trading Agents Lab.

v0.2 — fixed shared password.

The password is read from ``.streamlit/secrets.toml`` (key ``app_password``)
with an env-var fallback (``TRADINGAGENTS_LAB_PASSWORD``) and finally a hard
default. Keeping the check behind ``verify_password`` gives us a single seam to
swap in the future *auto-generated one-time-code* system without touching any
page code: see ``verify_password`` below.

Usage — call once at the very top of every page (and the main app)::

    import auth
    auth.require_auth()
"""

from __future__ import annotations

import hmac
import os

import streamlit as st

# Fallback used only when neither secrets.toml nor the env var is set. Override
# it by putting `app_password = "..."` in .streamlit/secrets.toml.
_DEFAULT_PASSWORD = "changeme"

_SESSION_FLAG = "_authenticated"


def _configured_password() -> str:
    """Resolve the currently-valid fixed password.

    Order: Streamlit secrets -> environment variable -> built-in default.
    """
    # st.secrets raises if there is no secrets.toml at all, so guard it.
    try:
        secret = st.secrets.get("app_password")
        if secret:
            return str(secret)
    except Exception:
        pass
    return os.environ.get("TRADINGAGENTS_LAB_PASSWORD") or _DEFAULT_PASSWORD


def verify_password(entered: str) -> bool:
    """Return True if ``entered`` is an accepted credential.

    ---------------------------------------------------------------------------
    FUTURE EXTENSION POINT (auto-generated one-time codes)
    ---------------------------------------------------------------------------
    Today this compares against a single fixed password. When the one-time-code
    generator ships, add its check here, e.g.::

        if onetime_codes.consume(entered):   # validate + burn the code
            return True

    Keep the constant-time compare below for the static-password path so the two
    schemes can coexist during migration. No page code needs to change because
    every caller goes through this one function.
    ---------------------------------------------------------------------------
    """
    if not entered:
        return False
    # hmac.compare_digest avoids leaking length/among-chars timing info.
    return hmac.compare_digest(str(entered), _configured_password())


def _login_form() -> None:
    st.markdown("### 🔒 Restricted access")
    st.caption(
        "AI Trading Agents Lab is private. Enter the access password to continue."
    )
    with st.form("login", clear_on_submit=False):
        pw = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Enter", type="primary")
    if submitted:
        if verify_password(pw):
            st.session_state[_SESSION_FLAG] = True
            st.rerun()
        else:
            st.error("Incorrect password.")


def require_auth() -> None:
    """Block the page until the visitor authenticates.

    Safe to call at the top of every page: once authenticated the flag lives in
    ``st.session_state`` for the whole browser session, so other pages pass
    through immediately.
    """
    if st.session_state.get(_SESSION_FLAG):
        return
    _login_form()
    st.stop()


def logout_button(location=st.sidebar) -> None:
    """Render a small logout control (defaults to the sidebar)."""
    if st.session_state.get(_SESSION_FLAG):
        if location.button("Log out"):
            st.session_state[_SESSION_FLAG] = False
            st.rerun()
