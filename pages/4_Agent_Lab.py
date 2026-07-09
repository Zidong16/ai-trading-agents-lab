"""Agent Lab — run the local TradingAgents pipeline on a ticker and show the report.

Flow: password gate -> enter a symbol -> the local multi-agent pipeline runs ->
a live "k / N — <agent>" progress bar tracks each stage -> the generated report
is rendered on the page. A Demo mode replays a previously generated report so the
UI can be exercised without an API key or spend.
"""

from __future__ import annotations

import datetime as _dt
import threading
import time
from pathlib import Path

import streamlit as st

import auth
import agent_runner as runner
import ui

st.set_page_config(page_title="Agent Lab", page_icon="🤖", layout="wide")
ui.sidebar_brand()
auth.require_auth()
auth.logout_button()

st.title("Agent Lab")
st.caption(
    "Feeds from Week 4 — one open-source agent, run and evaluated like an engineer. "
    "Paper-only: this produces analysis, not orders."
)

# --------------------------------------------------------------------------- #
# Preflight: can we do a real run?
# --------------------------------------------------------------------------- #
home_override = None
try:
    home_override = st.secrets.get("tradingagents_home")
except Exception:
    pass

pf = runner.preflight(home_override)
can_run_real = pf["importable"] and pf["api_key_present"]

with st.sidebar:
    st.subheader("Engine status")
    st.write("📁 TradingAgents:", "✅ found" if pf["home"] else "❌ not found")
    if pf["home"]:
        st.caption(pf["home"])
    st.write("📦 Package import:", "✅ ok" if pf["importable"] else "❌ failed")
    st.write(
        f"🔑 API key ({pf.get('key_env', 'OPENAI_API_KEY')}):",
        "✅ set" if pf["api_key_present"] else "⚠️ missing",
    )
    if pf.get("error"):
        st.error(pf["error"])

# --------------------------------------------------------------------------- #
# Input form
# --------------------------------------------------------------------------- #
ANALYST_LABELS = {
    "market": "Market",
    "social": "Sentiment",
    "news": "News",
    "fundamentals": "Fundamentals",
}

with st.form("run_form"):
    c1, c2 = st.columns([1, 1])
    with c1:
        symbol = st.text_input("Ticker symbol", value="NVDA", max_chars=12,
                               help="US ticker, e.g. NVDA, AAPL, MRVL.").strip().upper()
    with c2:
        trade_date = st.date_input("Trade date", value=_dt.date.today(),
                                   max_value=_dt.date.today())

    selected = st.multiselect(
        "Analyst team",
        options=list(ANALYST_LABELS.keys()),
        default=list(ANALYST_LABELS.keys()),
        format_func=lambda k: ANALYST_LABELS[k],
        help="Fewer analysts = faster & cheaper. Research, Trader, Risk and "
             "Portfolio-Manager stages always run.",
    )

    demo_default = not can_run_real
    demo_mode = st.toggle(
        "Demo mode (replay a saved report — no API calls, no cost)",
        value=demo_default,
        help="On by default until a real run is possible. Steps the progress bar "
             "through the stages, then loads a previously generated report.",
    )

    submitted = st.form_submit_button("▶ Run analysis", type="primary")

# Guard rails before a real (paid) run.
if submitted and not demo_mode and not can_run_real:
    st.warning(
        "A real run isn't possible yet: "
        + ("the tradingagents package couldn't be imported. "
           if not pf["importable"] else "")
        + ("no API key is set in TradingAgents/.env. "
           if pf["importable"] and not pf["api_key_present"] else "")
        + "Falling back to Demo mode."
    )
    demo_mode = True

if submitted and not selected:
    st.error("Pick at least one analyst.")
    st.stop()

if submitted and not symbol:
    st.error("Enter a ticker symbol.")
    st.stop()


# --------------------------------------------------------------------------- #
# Progress rendering helpers
# --------------------------------------------------------------------------- #
_ICON = {"completed": "✅", "in_progress": "⏳", "pending": "⚪"}


def _render_progress(bar, headline, checklist, snap, elapsed, phase=""):
    if snap is None:
        headline.markdown(f"⏳ **Starting…**  ·  {elapsed:0.0f}s")
        bar.progress(0.0)
        return
    bar.progress(min(1.0, snap.fraction))
    pref = f"{phase} " if phase else ""
    headline.markdown(f"{pref}**{snap.label}**  ·  {elapsed:0.0f}s elapsed")
    lines = []
    for name, status in snap.statuses:
        lines.append(f"{_ICON.get(status, '⚪')} {name}")
    # two columns of checklist for compactness
    mid = (len(lines) + 1) // 2
    left = "  \n".join(lines[:mid])
    right = "  \n".join(lines[mid:])
    with checklist.container():
        a, b = st.columns(2)
        a.markdown(left)
        b.markdown(right)


def _render_result(symbol, decision, report_md, report_path, elapsed):
    st.success(f"Analysis complete for {symbol} in {elapsed:0.0f}s.")
    if decision:
        d = str(decision).upper()
        color = {"BUY": "green", "SELL": "red", "HOLD": "gray"}.get(d, "blue")
        st.markdown(f"### Decision: :{color}[{d}]")
    if report_path:
        st.caption(f"Saved to: `{report_path}`")
    if report_md:
        st.download_button(
            "⬇ Download report (.md)", report_md,
            file_name=f"{symbol}_report.md", mime="text/markdown",
        )
        with st.container(border=True):
            st.markdown(report_md)
    else:
        st.info("Report generated, but the markdown could not be read back.")


def _find_demo_report(home: str | None) -> Path | None:
    """Locate a report to replay in Demo mode.

    Prefers a real report generated locally under ``<home>/reports`` (most
    relevant on your Mac); falls back to the sample bundled in the repo under
    ``sample_reports/`` so Demo mode also works on Streamlit Cloud, where
    TradingAgents isn't installed and nothing has been generated on disk.
    """
    if home:
        reports = Path(home) / "reports"
        if reports.is_dir():
            local = sorted(
                reports.glob("*/complete_report.md"),
                key=lambda p: p.stat().st_mtime, reverse=True,
            )
            if local:
                return local[0]
    bundled = sorted(
        (Path(__file__).resolve().parent.parent / "sample_reports").glob(
            "*/complete_report.md"
        )
    )
    return bundled[0] if bundled else None


# --------------------------------------------------------------------------- #
# Execute
# --------------------------------------------------------------------------- #
if submitted:
    st.divider()
    st.subheader(f"{'🧪 Demo — ' if demo_mode else ''}Running {symbol} · {trade_date}")
    bar = st.progress(0.0)
    headline = st.empty()
    checklist = st.empty()
    start = time.time()

    if demo_mode:
        # Step the progress bar through the real stage list, then replay a report.
        tracker = runner.StageTracker(selected)
        names = runner.stage_names(selected)
        # Build a synthetic state that grows one stage at a time.
        fake: dict = {}
        report_keys = {
            "Market Analyst": ("market_report", "demo"),
            "Sentiment Analyst": ("sentiment_report", "demo"),
            "News Analyst": ("news_report", "demo"),
            "Fundamentals Analyst": ("fundamentals_report", "demo"),
        }
        for i, name in enumerate(names):
            # populate state so the tracker advances to this stage
            if name in report_keys:
                k, _ = report_keys[name]
                fake[k] = "demo"
            elif name == "Research Manager":
                fake["investment_debate_state"] = {
                    "bull_history": "demo", "bear_history": "demo",
                    "judge_decision": "demo",
                }
            elif name == "Bull Researcher":
                fake.setdefault("investment_debate_state", {})["bull_history"] = "demo"
            elif name == "Bear Researcher":
                fake["investment_debate_state"] = {
                    "bull_history": "demo", "bear_history": "demo",
                }
            elif name == "Trader":
                fake["trader_investment_plan"] = "demo"
            elif name == "Portfolio Manager":
                fake["risk_debate_state"] = {
                    "aggressive_history": "demo", "conservative_history": "demo",
                    "neutral_history": "demo", "judge_decision": "demo",
                }
                fake["final_trade_decision"] = "demo"
            else:  # risk analysts
                rk = {"Aggressive Analyst": "aggressive_history",
                      "Conservative Analyst": "conservative_history",
                      "Neutral Analyst": "neutral_history"}[name]
                fake.setdefault("risk_debate_state", {})[rk] = "demo"
            snap = tracker.update(fake)
            _render_progress(bar, headline, checklist, snap, time.time() - start,
                             phase="🧪")
            time.sleep(0.18)

        demo_path = _find_demo_report(pf["home"])
        report_md = None
        if demo_path:
            try:
                report_md = demo_path.read_text(encoding="utf-8")
            except Exception:
                report_md = None
        st.info(
            "Demo mode: progress above is simulated. Report below is a previously "
            "generated one" + (f" (`{demo_path.parent.name}`)." if demo_path else
                               " — none found on disk yet.")
        )
        _render_result(symbol, None, report_md,
                       str(demo_path) if demo_path else None, time.time() - start)

    else:
        # Real run in a background thread; poll shared state for live progress.
        shared = {"snap": None, "result": None}
        lock = threading.Lock()

        def _cb(snap):
            with lock:
                shared["snap"] = snap

        def _worker():
            res = runner.run_analysis(
                symbol=symbol, trade_date=str(trade_date),
                selected_analysts=selected, progress_cb=_cb,
                tradingagents_home=pf["home"],
            )
            with lock:
                shared["result"] = res

        st.caption("⏱ This can take several minutes and calls your LLM provider. "
                   "Keep this tab open.")
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        while t.is_alive():
            with lock:
                snap = shared["snap"]
            _render_progress(bar, headline, checklist, snap, time.time() - start)
            time.sleep(0.4)
        t.join(timeout=2)
        with lock:
            snap = shared["snap"]
            res = shared["result"]
        _render_progress(bar, headline, checklist, snap, time.time() - start)

        if res is None:
            st.error("The run ended without returning a result.")
        elif res.ok:
            _render_result(res.symbol, res.decision, res.report_markdown,
                           res.report_path, res.elapsed_sec)
        else:
            st.error(f"Run failed: {res.error}")
            if res.traceback:
                with st.expander("Traceback"):
                    st.code(res.traceback)

else:
    st.info(
        "Enter a ticker and press **Run analysis**. With no API key configured, "
        "leave **Demo mode** on to preview the full flow using a saved report."
    )
