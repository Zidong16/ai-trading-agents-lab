"""Regression tests for agent_runner.find_saved_report.

Bug: Demo mode replayed the newest report on disk regardless of the requested
symbol, so after generating one MRVL report every search returned it. The
lookup must be symbol-aware.

Run:  python -m pytest tests/test_find_saved_report.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_runner import find_saved_report  # noqa: E402


def _make_report(root, dirname, text="report", mtime=None):
    d = root / "reports" / dirname
    d.mkdir(parents=True)
    p = d / "complete_report.md"
    p.write_text(text, encoding="utf-8")
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


def test_only_matching_symbol_is_returned(tmp_path):
    """The MRVL bug: newest report must NOT win for a different symbol."""
    now = time.time()
    mrvl = _make_report(tmp_path, "MRVL_2026-07-02", mtime=now)  # newest
    nvda = _make_report(tmp_path, "NVDA_2026-07-01", mtime=now - 100)

    path, available = find_saved_report(str(tmp_path), "NVDA")
    assert path == nvda
    assert set(available) == {"MRVL", "NVDA"}

    path, _ = find_saved_report(str(tmp_path), "MRVL")
    assert path == mrvl


def test_no_match_returns_none_with_available_list(tmp_path):
    _make_report(tmp_path, "MRVL_demo")
    path, available = find_saved_report(str(tmp_path), "AAPL")
    assert path is None
    assert available == ["MRVL"]


def test_newest_wins_among_same_symbol(tmp_path):
    now = time.time()
    _make_report(tmp_path, "NVDA_old", mtime=now - 100)
    newer = _make_report(tmp_path, "NVDA_new", mtime=now)
    path, _ = find_saved_report(str(tmp_path), "NVDA")
    assert path == newer


def test_sample_dir_fallback_and_case_insensitive(tmp_path):
    sample = tmp_path / "sample_reports"
    d = sample / "MRVL_demo"
    d.mkdir(parents=True)
    bundled = d / "complete_report.md"
    bundled.write_text("sample", encoding="utf-8")

    # no home at all -> falls back to bundled sample, symbol lowercased
    path, available = find_saved_report(None, "mrvl", sample_dir=str(sample))
    assert path == bundled
    assert available == ["MRVL"]

    # local report for the same symbol beats the bundled sample
    local = _make_report(tmp_path, "MRVL_2026-07-02")
    path, _ = find_saved_report(str(tmp_path), "MRVL", sample_dir=str(sample))
    assert path == local


def test_symbol_prefix_does_not_false_match(tmp_path):
    """Searching 'A' must not match 'AAPL_...' directories."""
    _make_report(tmp_path, "AAPL_2026-07-01")
    path, available = find_saved_report(str(tmp_path), "A")
    assert path is None
    assert available == ["AAPL"]


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
