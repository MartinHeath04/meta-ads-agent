# Meta Ads Agent

An AI-powered agent that automatically analyzes and improves Meta (Facebook/Instagram) ad campaigns.

## What It Does

- Connects to the Meta Marketing API to pull campaign, ad set, and ad-level performance data
- Uses AI to analyze performance metrics, ad copy effectiveness, creative performance, and geographic trends
- Generates daily reports with prioritized, actionable recommendations
- Emails you the report on a schedule so you always know what's working and what's not
- Learns from past decisions and outcomes to improve recommendations over time

## Architecture

```
┌─────────────────────────────────────┐
│           AGENT CORE                │
│     AI-Powered Analysis Engine      │
└──────────┬──────────┬───────────────┘
           │          │
     ┌─────▼──┐  ┌────▼────┐  ┌────────────┐
     │  Data  │  │ Action  │  │   Memory   │
     │ Layer  │  │  Layer  │  │   Layer    │
     │Meta API│  │Safe Ops │  │ Learnings  │
     └────────┘  └─────────┘  └────────────┘
```

## Features

- **Smart Analysis** - Goes beyond simple metrics to identify patterns, trends, and opportunities
- **Copy & Creative Insights** - Evaluates which messaging and images drive conversions
- **Geographic Intelligence** - Identifies top-performing locations and underserved areas
- **Safety First** - Operates in dry-run mode by default; no changes without your approval
- **Daily Email Reports** - Automated reports delivered to your inbox
- **Memory & Learning** - Stores past decisions and outcomes to avoid repeating mistakes

## Setup

1. Clone the repo
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
4. Test your connections:
   ```bash
   python scripts/run_agent.py --test-meta
   python scripts/run_agent.py --test-brain
   ```
5. Run the agent:
   ```bash
   python scripts/run_agent.py
   ```

## Usage

```bash
# Full daily analysis
python scripts/run_agent.py

# Quick health check
python scripts/run_agent.py --quick

# Analyze last 14 days and email the report
python scripts/run_agent.py --date-range last_14d --email

# Test connections
python scripts/run_agent.py --test-brain
python scripts/run_agent.py --test-meta
```

## Project Structure

```
agent/           # Core AI agent (brain, memory, actions)
data_layer/      # Meta Marketing API client and data models
config/          # Settings and configuration
scripts/         # Entry points and scheduling
data/            # Database, exports, and logs
```

## Requirements

- Python 3.10+
- Meta Marketing API access (access token + ad account ID)
- Anthropic API key

## License

Private - All rights reserved.
