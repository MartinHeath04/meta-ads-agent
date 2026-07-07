# Meta Ads AI Agent — Detailing Vertical

A **multi-tenant AI agent** that analyzes Meta (Facebook/Instagram) advertising
performance for detailing businesses and recommends optimizations to drive more
inbound leads. Built around Claude: the model reasons over real campaign data
rather than applying hardcoded rules.

> **Status:** report-only, evolving into an autonomous, multi-tenant agent with a
> FastAPI service and a human-in-the-loop action layer. See the [Roadmap](#roadmap).

## What it does

- Connects to the Meta Marketing API and pulls campaign, ad set, and ad-level data
  (spend, impressions, CTR, cost per message, creatives, geo).
- Uses Claude to analyze performance, ad copy, creative, and geographic trends —
  grounded with industry benchmarks and aware of campaign type (boosted post vs
  structured campaign).
- Generates prioritized, actionable recommendations and emails a daily report.
- Remembers past decisions and outcomes (SQLite) to improve over time.
- Optimizes for the metric that matters to a service business: **messages received
  (leads)** and **cost per message** — not vanity metrics.

## Architecture

```
                ┌──────────────────────────────┐
                │          AGENT CORE          │
                │   Claude-powered reasoning   │
                └───────┬───────────┬──────────┘
                        │           │
        ┌───────────────▼──┐   ┌────▼─────┐   ┌──────────────┐
        │   Data Layer     │   │  Action  │   │    Memory    │
        │  Meta API +      │   │  Layer   │   │   Layer      │
        │  context builder │   │ (HITL)   │   │  (SQLite)    │
        └──────────────────┘   └──────────┘   └──────────────┘
```

- **`data_layer/`** — Meta Marketing API client, typed models, campaign
  classification, and the context builder that formats data for the model.
- **`agent/`** — the reasoning loop, prompts/guardrails, memory, and action stubs.
- **`config/`** — Pydantic-validated settings and tunable thresholds.

## Tech stack

Python · `facebook-business` SDK · Anthropic Claude · Pydantic · SQLite · pytest

## Key engineering details

- **Reasoning, not rules** — Claude evaluates the data with industry benchmarks as
  soft context and assigns confidence levels, instead of fixed if/else thresholds.
- **Campaign-type awareness** — boosted posts are classified and judged differently
  from structured Ads Manager campaigns (they optimize for engagement, not messages).
- **Resilient data layer** — Meta's API filtering is unreliable, so data is fetched
  in bulk and filtered client-side; reporting lag is accounted for so brand-new
  campaigns aren't penalized as failures.
- **Safety first** — no changes are made to live ad accounts without explicit human
  approval.

## Setup

```bash
# 1. Clone, create a virtual environment, install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure credentials (placeholders shown in .env.example)
cp .env.example .env   # then fill in your values

# 3. Verify connections
python scripts/run_agent.py --test-meta
python scripts/run_agent.py --test-brain
```

All credentials live in `.env` (gitignored). See `.env.example` for the required
keys (Meta API token + ad account, Anthropic API key, SMTP for email).

## Usage

```bash
python scripts/run_agent.py                       # full analysis
python scripts/run_agent.py --quick               # quick health check
python scripts/run_agent.py --date-range last_14d --email   # analyze 14d + email
```

## Tests

```bash
python -m pytest tests/ -v
```

## Project structure

```
agent/           # Reasoning loop, prompts, memory, actions
data_layer/      # Meta API client, models, campaign classification, context builder
config/          # Pydantic settings and thresholds
scripts/         # CLI entry point and scheduling
tests/           # pytest suite
```

## Roadmap

The project is being built out as a portfolio-grade, multi-tenant AI agent:

- [x] Meta API integration, Claude-powered analysis, daily email reports
- [x] Industry benchmarks + boosted-post vs structured-campaign classification
- [x] **Multi-tenant foundation** — config-driven business profiles, isolated data
  and credentials per tenant, plus a demo mode that runs without live credentials
- [x] **FastAPI service** — REST endpoints, tenant onboarding, OpenAPI docs
- [x] **Agentic tool-use loop** — Claude tool calling with structured, human-approved
  optimization actions
- [x] **Evaluation harness + observability** — eval suite for the agent's judgments,
  token cost and latency tracking
- [x] **CI/CD, Docker, and a live demo deployment**
- [x] **Lightweight dashboard** — KPIs and an action-approval queue

## Requirements

- Python 3.10+
- Meta Marketing API access (access token + ad account ID)
- Anthropic API key

## License

Private — all rights reserved.
