# research-ops-agent
Autonomous agent that researches a question, checks its own findings for contradictions, and adapts — built for Tech Zephyr 4.0.
Built for Tech Zephyr 4.0 — Agentic AI Hackathon, IIT Bhubaneswar.

## Why this is agentic

A static search-and-summarize pipeline can't decide that a claim is contested and launch a follow-up search, or recover when a source is unavailable by falling back to another one. This agent does both — see `docs/architecture.md` for the full breakdown and diagram.

## Project structure

```
research-ops-agent/
├── agent/           # Controller: plan → act → observe → replan loop
├── tools/           # Search, fetch, and claim-verification tools
├── memory/          # Running state: claims, sources, confidence scores
├── evaluation/       # Evidence/contradiction checks before finalizing
├── docs/            # Architecture documentation and diagram
├── tests/           # Test suite
├── .env.example      # Required environment variables (copy to .env)
└── requirements.txt
```

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/<your-org>/research-ops-agent.git
   cd research-ops-agent
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Copy the environment template and fill in your own keys:
   ```bash
   cp .env.example .env
   ```
   **Never commit `.env`.** It's already in `.gitignore`. You need:
   - `LLM_API_KEY` — an Anthropic API key
   - `TAVILY_API_KEY` — a free key from [tavily.com](https://tavily.com) for web search

4. Run the agent from the command line:
   ```bash
   python -m agent.controller --question "your research question here"
   ```

   Or launch the web UI:
   ```bash
   streamlit run app.py
   ```

## Running tests

Tests mock all external calls (LLM, search, fetch), so no API keys are needed to run them:

```bash
pytest tests/ -v
```

## Deployment

The Streamlit app (`app.py`) is ready to deploy on [Streamlit Community Cloud](https://streamlit.io/cloud) for free:
1. Push this repo to GitHub
2. Connect it in Streamlit Community Cloud, point it at `app.py`
3. Add `LLM_API_KEY` and `TAVILY_API_KEY` as secrets in the dashboard (never in the repo)

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full system diagram and component breakdown (controller, tools, memory, evaluation gate, human steering, failure handling).

## Team

[Team name] — [Member 1, Member 2, Member 3, Member 4]

## License

[Choose a license — MIT is a safe default for hackathon submissions]
