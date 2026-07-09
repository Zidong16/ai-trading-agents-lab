#!/bin/bash
# Double-click launcher (macOS) for the AI Trading Agents Lab.
# Runs Streamlit using your TradingAgents virtualenv so the Agent Lab page can
# import `tradingagents`.
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TA_HOME="${TRADINGAGENTS_HOME:-$HOME/TradingAgents}"
STREAMLIT="$TA_HOME/.venv/bin/streamlit"

if [ ! -x "$STREAMLIT" ]; then
  echo "⚠  Couldn't find $STREAMLIT"
  echo "   Falling back to whatever 'streamlit' is on PATH."
  STREAMLIT="streamlit"
fi

cd "$HERE"
echo "▶ Launching AI Trading Agents Lab from $HERE"
echo "  using: $STREAMLIT"
exec "$STREAMLIT" run streamlit_app.py
