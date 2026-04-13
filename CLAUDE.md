# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Strava Tracker is a personal Telegram bot that fetches the user's latest Strava activity, pre-processes the raw JSON, and sends it to an AI coach (Claude) for training feedback. The bot is single-user (gated by `TELEGRAM_ALLOWED_USER_ID`) and designed to run as a long-lived worker process.

## Running the bot

```bash
# Install dependencies (uses uv)
uv sync

# Run the bot directly
python src/telegram_bot.py

# Or via Procfile (as deployed)
# worker: python src/telegram_bot.py
```

## Required environment variables (`.env`)

```
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_ID=
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REFRESH_TOKEN=
```

## One-time Strava auth setup

`src/auth_strava.py` is a standalone script used to exchange a Strava authorization code for a refresh token. Run it once, copy the printed refresh token to `.env`, then discard it. The `AUTHORIZATION_CODE` constant inside must be updated each time the token needs to be re-generated.

## Architecture

The message flow is: **Telegram** → `telegram_bot.py` → **StravaClient** → **LlmClient** → **reply**

- `src/telegram_bot.py` — entry point; owns the full pipeline per message: fetch latest activity, get detail, call AI, reply.
- `src/strava_client.py` — wraps Strava API v3. Always refreshes the access token on init using the stored refresh token (tokens are ephemeral).
- `src/llm_client.py` — calls Anthropic's API. Loads prompts and model config from `config.toml`. Pre-calculates pace/duration/distance before sending to the model so the model doesn't have to infer from raw m/s values.
- `src/data_processing.py` — `StravaDataProcessor.process_activity()` converts raw Strava JSON to human-readable fields. Currently not used in the main pipeline (the LLM client does its own inline pre-processing), but available for future use.
- `src/logger.py` — `setup_logger()` configures loguru to write to stdout and to daily rotating files under `logs/`.
- `config.toml` — holds the system prompt, user prompt template, and model aliases. The `[models] active` key selects which model alias to use — but `llm_client.py` currently hardcodes `self.config["models"]["claude"]` regardless of `active`.

## Prompt config

`config.toml` `[prompts]` contains two templates:
- `system_prompt`: injected with `{today}` and `{weeks_to_race}` (calculated dynamically relative to a hardcoded March 2027 race date).
- `user_prompt`: injected with `{user_message}`, `{summary}` (pre-calculated stats), and `{data_string}` (filtered Strava JSON).

The filtered keys sent to the model are defined in `USEFUL_KEYS` inside `LlmClient.analyze_raw_workout`.

## Key dependencies

- `anthropic` — LLM calls (Claude)
- `python-telegram-bot` — async Telegram bot framework
- `requests` — Strava API HTTP calls
- `loguru` — structured logging
- `python-dotenv` — env var loading
- `google-genai`, `groq` — present in dependencies and `config.toml` model aliases, but not actively used in the main pipeline
