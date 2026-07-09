# AI Trading Agents Lab

A living platform for a technical study of AI trading agents — architectures,
algorithms, and engineering mechanisms. It grows one page per research deliverable.

**Paper-only by design.** No live brokerage connections. Analysis, historical
backtests, and paper endpoints only.

## Running

The **Agent Lab** page runs the local
[TradingAgents](https://github.com/TauricResearch/TradingAgents) pipeline
in-process, so the app needs the `tradingagents` package importable. The
simplest way is to launch with TradingAgents' own virtualenv, which already has
both `streamlit` and `tradingagents`:

    ./run_app.command            # macOS: or double-click it in Finder

That resolves to `~/TradingAgents/.venv/bin/streamlit`. Override the location
with `TRADINGAGENTS_HOME` or `tradingagents_home` in `.streamlit/secrets.toml`.

Standalone (only the first three pages need this; Agent Lab needs the step
above):

    pip install -r requirements.txt
    streamlit run streamlit_app.py

## Setup

1. **Password.** Copy `.streamlit/secrets.toml.example` →
   `.streamlit/secrets.toml` and set `app_password`. This file is gitignored.
   The current default password is `niuniu-lab-2026` — change it.
2. **API key (for real runs).** Put your provider key in `~/TradingAgents/.env`
   (e.g. `OPENAI_API_KEY=...`). Until then, Agent Lab stays in **Demo mode**,
   which replays a previously generated report with no API calls.

## How Agent Lab works

`agent_runner.py` bridges the UI and the framework: it imports
`TradingAgentsGraph`, streams the graph (`stream_mode="values"`), and a
`StageTracker` turns each streamed state into a live `k / N — <agent>` progress
reading synced to the real pipeline stages (Market → Sentiment → News →
Fundamentals → Bull/Bear → Research Manager → Trader → Risk → Portfolio Manager).
The same report tree the CLI writes is saved and rendered on the page.

Auth lives in `auth.py`; `verify_password()` is the single seam where the
planned auto-generated **one-time-code** system will slot in without touching
any page code.
