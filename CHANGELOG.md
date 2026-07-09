# Changelog

## v0.2 — 2026-7-9
- Password gate on every page (fixed password via `.streamlit/secrets.toml`;
  single `verify_password` seam left open for the future one-time-code system).
- Agent Lab is live: enter a ticker → runs the local **TradingAgents** pipeline
  in-process → live "k / N — <agent>" progress synced to real pipeline stages →
  the generated report renders on the page (with decision badge + download).
- Demo mode replays a saved report so the flow works with no API key / no spend.
- Added `agent_runner.py` (UI↔TradingAgents bridge + `StageTracker`), `auth.py`,
  `run_app.command` launcher, `.gitignore`, secrets template.

## v0.1 — 2026-7-2
- Platform skeleton live at: (https://ai-trading-agents-lab-4gzaeejfyqmtqspjxurwbm.streamlit.app/)
- Fixed pages/ structure, rebooted app, sidebar live
- 5 pages up; Tool Explorer seeded with 12 tools (links unverified)
