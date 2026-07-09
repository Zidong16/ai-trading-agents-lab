"""Bridge between the Streamlit UI and the local TradingAgents framework.

Responsibilities
----------------
1. Locate and import the user's local TradingAgents install (path is
   configurable; defaults to ~/TradingAgents).
2. Run a full multi-agent analysis for a ticker via ``graph.stream`` so we can
   report **live per-agent progress** ("k / N — Fundamentals Analyst"), then
   persist the same on-disk report tree the CLI produces.
3. Expose a pure-Python ``StageTracker`` (no heavy imports) that turns the
   streamed graph state into a progress snapshot. It is deliberately importable
   and unit-testable on its own.

The expensive imports (``tradingagents`` and its deps) are done lazily inside
``run_analysis`` so this module — and ``StageTracker`` in particular — imports
instantly anywhere.
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

# --------------------------------------------------------------------------- #
# Stage model (pure Python — safe to import without TradingAgents installed)
# --------------------------------------------------------------------------- #

# Selectable analysts, in graph execution order.
ANALYST_ORDER = ["market", "social", "news", "fundamentals"]
ANALYST_AGENT_NAMES = {
    "market": "Market Analyst",
    "social": "Sentiment Analyst",
    "news": "News Analyst",
    "fundamentals": "Fundamentals Analyst",
}
ANALYST_REPORT_KEY = {
    "market": "market_report",
    "social": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
}

# Fixed teams that always run, in graph execution order
# (Trader -> Aggressive -> Conservative -> Neutral -> Portfolio Manager).
FIXED_STAGES_AFTER_ANALYSTS = [
    "Bull Researcher",
    "Bear Researcher",
    "Research Manager",
    "Trader",
    "Aggressive Analyst",
    "Conservative Analyst",
    "Neutral Analyst",
    "Portfolio Manager",
]

PENDING, IN_PROGRESS, COMPLETED = "pending", "in_progress", "completed"


def stage_names(selected_analysts) -> list[str]:
    """Ordered list of agent stage names for the given analyst selection."""
    analysts = [
        ANALYST_AGENT_NAMES[k] for k in ANALYST_ORDER if k in set(selected_analysts)
    ]
    return analysts + list(FIXED_STAGES_AFTER_ANALYSTS)


@dataclass
class ProgressSnapshot:
    completed: int
    total: int
    current: str
    statuses: list[tuple[str, str]]  # ordered [(agent_name, status), ...]

    @property
    def fraction(self) -> float:
        return (self.completed / self.total) if self.total else 0.0

    @property
    def label(self) -> str:
        return f"{self.completed} / {self.total} — {self.current}"


class StageTracker:
    """Derive per-agent progress from the streamed graph state.

    ``update(state)`` is called with the full graph state (the framework streams
    in ``values`` mode, so every chunk is the complete, cumulative state). Status
    is recomputed from scratch each call, which is safe and monotonic because the
    underlying state only ever accumulates content.

    The rules mirror the reference logic in the TradingAgents CLI so the counter
    matches what a CLI run would show.
    """

    def __init__(self, selected_analysts):
        self.selected = [k for k in ANALYST_ORDER if k in set(selected_analysts)]
        self.order = stage_names(self.selected)

    def update(self, state: dict) -> ProgressSnapshot:
        status = {name: PENDING for name in self.order}

        def sets(name: str, value: str) -> None:
            if name in status:
                status[name] = value

        state = state or {}

        # --- 1. Analyst team -------------------------------------------------
        found_active = False
        for key in self.selected:
            name = ANALYST_AGENT_NAMES[key]
            if (state.get(ANALYST_REPORT_KEY[key]) or "").strip():
                sets(name, COMPLETED)
            elif not found_active:
                sets(name, IN_PROGRESS)
                found_active = True
            # else stays pending

        analysts_done = all(status[ANALYST_AGENT_NAMES[k]] == COMPLETED for k in self.selected) if self.selected else True

        # --- 2. Research team (Bull -> Bear -> Manager) ----------------------
        # Rule of thumb throughout: an agent's output appearing in the state
        # means that agent has *finished its turn* (mark completed) and the next
        # one becomes active. This keeps the k/N counter advancing responsively,
        # since the framework streams a chunk only once a node completes.
        debate = state.get("investment_debate_state") or {}
        bull = (debate.get("bull_history") or "").strip()
        bear = (debate.get("bear_history") or "").strip()
        r_judge = (debate.get("judge_decision") or "").strip()

        if analysts_done:
            if bull:
                sets("Bull Researcher", COMPLETED)
            if bear:
                sets("Bear Researcher", COMPLETED)
            if r_judge:
                sets("Research Manager", COMPLETED)
            # first unfinished research stage is the active one
            if not r_judge:
                if not bull:
                    sets("Bull Researcher", IN_PROGRESS)
                elif not bear:
                    sets("Bear Researcher", IN_PROGRESS)
                else:
                    sets("Research Manager", IN_PROGRESS)

        research_done = status["Research Manager"] == COMPLETED

        # --- 3. Trader -------------------------------------------------------
        trader_plan = (state.get("trader_investment_plan") or "").strip()
        if trader_plan:
            sets("Trader", COMPLETED)
        elif research_done:
            sets("Trader", IN_PROGRESS)

        trader_done = status["Trader"] == COMPLETED

        # --- 4. Risk team (Aggressive -> Conservative -> Neutral) + PM -------
        risk = state.get("risk_debate_state") or {}
        agg = (risk.get("aggressive_history") or "").strip()
        con = (risk.get("conservative_history") or "").strip()
        neu = (risk.get("neutral_history") or "").strip()
        risk_judge = (risk.get("judge_decision") or "").strip()
        final_decision = (state.get("final_trade_decision") or "").strip()

        if risk_judge or final_decision:
            # portfolio manager delivered the verdict -> everything upstream done
            for name in ("Aggressive Analyst", "Conservative Analyst",
                         "Neutral Analyst", "Portfolio Manager"):
                sets(name, COMPLETED)
        elif trader_done:
            if agg:
                sets("Aggressive Analyst", COMPLETED)
            if con:
                sets("Conservative Analyst", COMPLETED)
            if neu:
                sets("Neutral Analyst", COMPLETED)
            # first unfinished risk stage is active; once all three are in,
            # the portfolio manager is the active stage
            if not agg:
                sets("Aggressive Analyst", IN_PROGRESS)
            elif not con:
                sets("Conservative Analyst", IN_PROGRESS)
            elif not neu:
                sets("Neutral Analyst", IN_PROGRESS)
            else:
                sets("Portfolio Manager", IN_PROGRESS)

        # --- snapshot --------------------------------------------------------
        ordered = [(name, status[name]) for name in self.order]
        completed = sum(1 for _, s in ordered if s == COMPLETED)
        current = next((n for n, s in ordered if s == IN_PROGRESS), None)
        if current is None:
            current = "Complete" if completed == len(ordered) else (
                next((n for n, s in ordered if s == PENDING), self.order[-1])
            )
        return ProgressSnapshot(completed, len(ordered), current, ordered)


# --------------------------------------------------------------------------- #
# Environment / preflight
# --------------------------------------------------------------------------- #

DEFAULT_HOME_CANDIDATES = [
    os.environ.get("TRADINGAGENTS_HOME"),
    os.path.expanduser("~/TradingAgents"),
    str(Path(__file__).resolve().parent.parent / "TradingAgents"),
]

# Minimal provider -> API-key env var map for the preflight check.
_PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
}


def resolve_home(explicit: Optional[str] = None) -> Optional[str]:
    """Return the first existing TradingAgents home directory, or None."""
    candidates = [explicit] + DEFAULT_HOME_CANDIDATES
    for c in candidates:
        if c and Path(c).expanduser().is_dir():
            return str(Path(c).expanduser())
    return None


def find_saved_report(
    home: Optional[str], symbol: str, sample_dir: Optional[str] = None
) -> tuple[Optional[Path], list[str]]:
    """Find the newest saved ``complete_report.md`` for *symbol*.

    Report directories are named ``<SYMBOL>_<suffix>`` (e.g. ``MRVL_demo``,
    ``NVDA_2026-07-09``); a report matches only if the token before the first
    underscore equals *symbol* (case-insensitive). Searches ``<home>/reports``
    first (newest mtime wins), then *sample_dir* (bundled samples).

    Returns ``(path_or_None, symbols_that_do_have_saved_reports)`` so the UI
    can tell the user what is replayable instead of silently substituting a
    report for a different ticker.
    """
    sym = (symbol or "").strip().upper()
    candidates: list[Path] = []
    if home:
        reports = Path(home).expanduser() / "reports"
        if reports.is_dir():
            candidates += sorted(
                reports.glob("*/complete_report.md"),
                key=lambda p: p.stat().st_mtime, reverse=True,
            )
    if sample_dir and Path(sample_dir).is_dir():
        candidates += sorted(Path(sample_dir).glob("*/complete_report.md"))

    match: Optional[Path] = None
    available: list[str] = []
    for p in candidates:
        s = p.parent.name.split("_")[0].strip().upper()
        if s and s not in available:
            available.append(s)
        if match is None and s == sym:
            match = p
    return match, available


def _load_env_file(home: str) -> None:
    """Load TradingAgents/.env so API keys/provider settings are available.

    Uses python-dotenv if present (a TradingAgents dependency); otherwise falls
    back to a tiny manual parser so this never hard-fails.
    """
    env_path = Path(home) / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
        return
    except Exception:
        pass
    # Manual fallback parser (KEY=VALUE, ignores comments/blank lines).
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass


def preflight(home: Optional[str] = None) -> dict:
    """Check that a real run is possible: package importable + API key present.

    Returns a dict the UI can use to warn the user before spending money.
    """
    result = {
        "home": None,
        "importable": False,
        "provider": "openai",
        "api_key_present": False,
        "error": None,
    }
    resolved = resolve_home(home)
    result["home"] = resolved
    if not resolved:
        result["error"] = "TradingAgents folder not found."
        return result

    _load_env_file(resolved)

    if resolved not in sys.path:
        sys.path.insert(0, resolved)
    try:
        from tradingagents.default_config import DEFAULT_CONFIG  # noqa: F401

        provider = str(DEFAULT_CONFIG.get("llm_provider", "openai")).lower()
        result["provider"] = provider
        result["importable"] = True
        key_env = _PROVIDER_KEY_ENV.get(provider, "OPENAI_API_KEY")
        result["api_key_present"] = bool(os.environ.get(key_env))
        result["key_env"] = key_env
    except Exception as exc:  # pragma: no cover - depends on user env
        result["error"] = f"Could not import tradingagents: {exc}"
    return result


# --------------------------------------------------------------------------- #
# The run itself
# --------------------------------------------------------------------------- #

ProgressCallback = Callable[[ProgressSnapshot], None]


@dataclass
class RunResult:
    ok: bool
    symbol: str
    trade_date: str
    report_path: Optional[str] = None          # complete_report.md
    report_dir: Optional[str] = None
    report_markdown: Optional[str] = None
    decision: Optional[str] = None             # BUY / SELL / HOLD (processed signal)
    final_state: dict = field(default_factory=dict)
    elapsed_sec: float = 0.0
    error: Optional[str] = None
    traceback: Optional[str] = None


def run_analysis(
    symbol: str,
    trade_date: str,
    selected_analysts=("market", "social", "news", "fundamentals"),
    progress_cb: Optional[ProgressCallback] = None,
    config_overrides: Optional[dict] = None,
    tradingagents_home: Optional[str] = None,
    asset_type: str = "stock",
) -> RunResult:
    """Run one full TradingAgents analysis, reporting live progress.

    ``progress_cb`` (if given) receives a ``ProgressSnapshot`` after every graph
    step. This function is synchronous and CPU/network/LLM bound — callers that
    want a responsive UI should run it in a background thread and read progress
    via the callback.
    """
    started = time.monotonic()
    selected_analysts = tuple(k for k in ANALYST_ORDER if k in set(selected_analysts))
    tracker = StageTracker(selected_analysts)

    def emit(state: dict) -> None:
        if progress_cb:
            try:
                progress_cb(tracker.update(state))
            except Exception:
                pass  # never let UI progress errors kill the run

    # initial snapshot (all pending / first analyst active)
    emit({})

    home = resolve_home(tradingagents_home)
    if not home:
        return RunResult(
            ok=False, symbol=symbol, trade_date=trade_date,
            error="Could not find your TradingAgents folder. Set TRADINGAGENTS_HOME "
                  "or `tradingagents_home` in secrets.",
            elapsed_sec=time.monotonic() - started,
        )

    _load_env_file(home)
    if home not in sys.path:
        sys.path.insert(0, home)

    try:
        from tradingagents.default_config import DEFAULT_CONFIG
        from tradingagents.graph.trading_graph import TradingAgentsGraph
    except Exception as exc:
        return RunResult(
            ok=False, symbol=symbol, trade_date=trade_date,
            error=f"Failed to import tradingagents from {home}: {exc}",
            traceback=traceback.format_exc(),
            elapsed_sec=time.monotonic() - started,
        )

    # Build config (copy so we never mutate the framework's module-level dict).
    config = dict(DEFAULT_CONFIG)
    if config_overrides:
        config.update(config_overrides)

    try:
        ta = TradingAgentsGraph(
            selected_analysts=selected_analysts, debug=False, config=config
        )

        # Learning loop: resolve any pending reflections for this ticker.
        try:
            ta._resolve_pending_entries(symbol)
        except Exception:
            pass

        past_context = ""
        try:
            past_context = ta.memory_log.get_past_context(symbol)
        except Exception:
            pass
        instrument_context = ""
        try:
            instrument_context = ta.resolve_instrument_context(symbol, asset_type)
        except Exception:
            pass

        init_state = ta.propagator.create_initial_state(
            symbol, trade_date, asset_type=asset_type,
            past_context=past_context, instrument_context=instrument_context,
        )
        args = ta.propagator.get_graph_args()

        final_state: dict = {}
        for chunk in ta.graph.stream(init_state, **args):
            if isinstance(chunk, dict):
                final_state.update(chunk)
                emit(final_state)

        # Persist logs + memory (best-effort; don't fail the run on these).
        try:
            ta._log_state(trade_date, final_state)
        except Exception:
            pass
        try:
            ta.memory_log.store_decision(
                ticker=symbol, trade_date=trade_date,
                final_trade_decision=final_state.get("final_trade_decision", ""),
            )
        except Exception:
            pass

        report_path = ta.save_reports(final_state, symbol)
        decision = None
        try:
            decision = ta.process_signal(final_state.get("final_trade_decision", ""))
        except Exception:
            pass

        report_md = None
        try:
            report_md = Path(report_path).read_text(encoding="utf-8")
        except Exception:
            pass

        emit(final_state)  # final 100%
        return RunResult(
            ok=True, symbol=symbol, trade_date=trade_date,
            report_path=str(report_path), report_dir=str(Path(report_path).parent),
            report_markdown=report_md, decision=decision, final_state=final_state,
            elapsed_sec=time.monotonic() - started,
        )
    except Exception as exc:
        return RunResult(
            ok=False, symbol=symbol, trade_date=trade_date,
            error=str(exc), traceback=traceback.format_exc(),
            elapsed_sec=time.monotonic() - started,
        )
