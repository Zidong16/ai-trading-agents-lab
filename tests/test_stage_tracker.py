"""Unit tests for the progress logic in agent_runner.StageTracker.

These run without the tradingagents package (StageTracker is pure Python), so
they exercise the k/N progress mapping deterministically by feeding synthetic
graph states — the same shape the framework streams in `values` mode.

Run:  python -m pytest tests/test_stage_tracker.py   (or just: python tests/test_stage_tracker.py)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_runner import StageTracker, stage_names  # noqa: E402


def _grow_states(selected):
    """Yield (label, state) pairs that populate one stage at a time, in order."""
    names = stage_names(selected)
    state = {}
    analyst_key = {
        "Market Analyst": "market_report",
        "Sentiment Analyst": "sentiment_report",
        "News Analyst": "news_report",
        "Fundamentals Analyst": "fundamentals_report",
    }
    for name in names:
        if name in analyst_key:
            state[analyst_key[name]] = "x"
        elif name == "Bull Researcher":
            state.setdefault("investment_debate_state", {})["bull_history"] = "x"
        elif name == "Bear Researcher":
            state["investment_debate_state"] = {"bull_history": "x", "bear_history": "x"}
        elif name == "Research Manager":
            state["investment_debate_state"] = {
                "bull_history": "x", "bear_history": "x", "judge_decision": "x"}
        elif name == "Trader":
            state["trader_investment_plan"] = "x"
        elif name in ("Aggressive Analyst", "Conservative Analyst", "Neutral Analyst"):
            key = {"Aggressive Analyst": "aggressive_history",
                   "Conservative Analyst": "conservative_history",
                   "Neutral Analyst": "neutral_history"}[name]
            state.setdefault("risk_debate_state", {})[key] = "x"
        elif name == "Portfolio Manager":
            state["risk_debate_state"] = {
                "aggressive_history": "x", "conservative_history": "x",
                "neutral_history": "x", "judge_decision": "x"}
            state["final_trade_decision"] = "x"
        yield name, dict(state)


def test_total_matches_selection():
    assert StageTracker(["market", "social", "news", "fundamentals"]).update({}).total == 12
    assert StageTracker(["market", "news"]).update({}).total == 10  # 2 + 8 fixed
    assert StageTracker(["market"]).update({}).total == 9


def test_initial_state_first_analyst_active():
    snap = StageTracker(["market", "social", "news", "fundamentals"]).update({})
    assert snap.completed == 0
    assert snap.current == "Market Analyst"
    assert dict(snap.statuses)["Market Analyst"] == "in_progress"


def test_monotonic_and_current_follows_stage():
    selected = ["market", "social", "news", "fundamentals"]
    tracker = StageTracker(selected)
    last = -1
    for i, (name, state) in enumerate(_grow_states(selected)):
        snap = tracker.update(state)
        # completed count never goes backwards
        assert snap.completed >= last, f"regressed at {name}"
        last = snap.completed
        # the stage we just populated is completed
        assert dict(snap.statuses)[name] == "completed", f"{name} not completed"


def test_end_state_fully_complete():
    selected = ["market", "social", "news", "fundamentals"]
    tracker = StageTracker(selected)
    snap = None
    for _, state in _grow_states(selected):
        snap = tracker.update(state)
    assert snap.completed == snap.total == 12
    assert snap.current == "Complete"
    assert abs(snap.fraction - 1.0) < 1e-9


def test_partial_selection_runs_clean():
    selected = ["market", "fundamentals"]
    tracker = StageTracker(selected)
    snap = None
    for _, state in _grow_states(selected):
        snap = tracker.update(state)
    assert snap.completed == snap.total == 10
    assert snap.current == "Complete"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")
