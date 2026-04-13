# Strava Tracker

  Personal Telegram bot that fetches your latest Strava activity and delivers AI-powered coaching feedback via Claude.

  ## How it works

  Send any message to the bot → it fetches your latest Strava activity → analyzes it with an AI coach → replies with a structured training report in Spanish.

  The report always covers three points:
  1. Performance breakdown (pace, splits, HR zones, consistency)
  2. Half-marathon projection (how the session maps to race goal)
  3. Coach's directive (one specific action for the next session)

  ## Stack

  - **python-telegram-bot** — async bot framework
  - **Strava API v3** — activity data
  - **Anthropic Claude** — AI coaching analysis
  - **loguru** — structured logging with daily rotation

  ## Setup

  **1. Clone and install dependencies**
  ```bash
  uv sync
  ````
  2. Create a .env file
  ANTHROPIC_API_KEY=
  TELEGRAM_BOT_TOKEN=
  TELEGRAM_ALLOWED_USER_ID=
  STRAVA_CLIENT_ID=
  STRAVA_CLIENT_SECRET=
  STRAVA_REFRESH_TOKEN=

  3. Get your Strava refresh token

  Go to https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all, authorize, copy the code from the redirect URL,
  paste it into src/auth_strava.py and run it once:

  python src/auth_strava.py

  Copy the printed refresh token into your .env.

  Running

  # Start the bot
  python src/telegram_bot.py

  # Test the pipeline locally without Telegram
  python src/test_pipeline.py

  # Run unit tests
  uv run pytest tests/ -v

  Configuration

  config.toml controls prompts, model selection, and race target:

  [race]
  date = "2027-03-01"   # target race date

  [models]
  active = "claude"     # switch to "llama" or "qwen" to change model
