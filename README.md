# Strava Tracker

Personal Telegram bot that fetches your latest Strava activity and delivers AI-powered coaching feedback.

## How it works

Send any message to the bot → it fetches your latest Strava activity → analyzes it with an AI coach → replies with a structured training report in Spanish, followed by a JSON attachment with the raw session data.

The report always covers three points:
1. Performance breakdown (pace, splits, HR zones, consistency)
2. Half-marathon projection (how the session maps to race goal)
3. Coach's directive (one specific action for the next session)

## Architecture

The project uses abstract interfaces so LLM and fitness providers can be swapped without touching the pipeline:

```
FitnessClient (ABC)
└── StravaClient          — Strava API v3, handles token refresh + Railway rotation

LlmProvider (ABC)
├── AnthropicProvider     — Claude models (Anthropic API)
└── GroqProvider          — llama / qwen / scout models (Groq API)

LlmClient                 — orchestrates prompts, data filtering, and provider selection
telegram_bot.py           — entry point; wires everything together
```

## Stack

- **python-telegram-bot** — async bot framework
- **Strava API v3** — activity data with automatic refresh token rotation
- **Anthropic Claude** — default AI coaching analysis
- **Groq** — alternative LLM backend (llama-3.3-70b, qwen3-32b, llama-4-scout)
- **loguru** — structured logging with daily rotation
- **Railway** — deployment target (Procfile included); token rotation via Railway GraphQL API

## Setup

**1. Clone and install dependencies**
```bash
uv sync
```

**2. Create a `.env` file**
```env
# Required
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_ID=
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REFRESH_TOKEN=

# Required only when using Groq models
GROQ_API_KEY=

# Optional — enables automatic refresh token rotation on Railway
RAILWAY_API_TOKEN=
RAILWAY_PROJECT_ID=
RAILWAY_SERVICE_ID=
RAILWAY_ENVIRONMENT_ID=
```

**3. Get your Strava refresh token**

Go to the Strava OAuth authorization URL (replace `YOUR_CLIENT_ID`):
```
https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all
```
Authorize, copy the `code` from the redirect URL, paste it into `src/auth_strava.py`, then run it once:
```bash
python src/auth_strava.py
```
Copy the printed refresh token into your `.env`.

## Running

```bash
# Start the Telegram bot
python src/telegram_bot.py

# Test the full pipeline locally without Telegram
python src/test_pipeline.py

# Run unit tests
uv run pytest tests/ -v
```

## Configuration

`config.toml` controls prompts, model selection, and race target:

```toml
[race]
date = "2027-03-01"   # target race date

[models]
active = "claude"     # switch to "llama", "qwen", or "scout" to use Groq
```

Available model aliases:

| Alias   | Model                                        | Provider  |
|---------|----------------------------------------------|-----------|
| `claude`| claude-sonnet-4-20250514                     | Anthropic |
| `llama` | llama-3.3-70b-versatile                      | Groq      |
| `qwen`  | qwen/qwen3-32b                               | Groq      |
| `scout` | meta-llama/llama-4-scout-17b-16e-instruct    | Groq      |

## Deployment (Railway)

The `Procfile` is configured for Railway:
```
worker: python src/telegram_bot.py
```

When Strava issues a new refresh token, the bot persists it to `.tokens.json` in the working directory so it survives process restarts. On Railway, `.tokens.json` is written to `/app` which persists between deploys. Additionally, if the `RAILWAY_*` env vars are configured, the new token is also upserted into the Railway environment variables as a backup.
