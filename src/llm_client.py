import os
from datetime import date
import json
import tomllib
import anthropic
from loguru import logger
from dotenv import load_dotenv
from data_processing import StravaDataProcessor

load_dotenv()


class LlmClient:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("Missing ANTHROPIC_API_KEY in .env file")

        self.client = anthropic.Anthropic(api_key=api_key)
        logger.debug("Anthropic API client created")

        config_path = os.path.join(os.path.dirname(__file__), "..", "config.toml")
        with open(config_path, "rb") as f:
            self.config = tomllib.load(f)
        logger.debug("Prompts loaded from config.toml")

    def _build_system_prompt(self) -> str:
        raw = self.config["prompts"]["system_prompt"]
        today = date.today()
        race_date = date.fromisoformat(self.config["race"]["date"])
        weeks_to_race = (race_date - today).days // 7

        prompt = raw.format(
            today=today.strftime("%d %B %Y"),
            weeks_to_race=weeks_to_race
        )
        logger.debug(f"Race in {weeks_to_race} weeks ({race_date})")
        return prompt

    USEFUL_KEYS = [
        'name', 'type', 'start_date_local', 'distance', 'moving_time',
        'elapsed_time', 'total_elevation_gain', 'average_speed', 'max_speed',
        'average_heartrate', 'max_heartrate', 'average_cadence',
        'splits_metric', 'laps', 'best_efforts', 'perceived_exertion'
    ]

    def _build_summary(self, raw_data: dict) -> str:
        p = StravaDataProcessor.process_activity(raw_data)
        lines = [
            "## Pre-calculated session summary (use these values, do not recalculate)",
            f"- Date: {p['date']}",
            f"- Distance: {p['distance_km']} km",
            f"- Duration: {p['duration']}",
            f"- Average pace: {p['pace']}",
            f"- Elevation gain: {p['elevation_m']} m",
        ]
        if 'avg_heartrate' in p:
            lines.append(f"- Avg HR: {p['avg_heartrate']} bpm")
        if 'max_heartrate' in p:
            lines.append(f"- Max HR: {p['max_heartrate']} bpm")
        logger.debug(f"Pre-calculated — distance: {p['distance_km']} km | pace: {p['pace']} | duration: {p['duration']}")
        return "\n".join(lines)

    def _filter_activity_data(self, raw_data: dict) -> str:
        filtered = {k: raw_data[k] for k in self.USEFUL_KEYS if k in raw_data}
        return json.dumps(filtered, ensure_ascii=False, indent=2)

    def analyze_raw_workout(self, raw_data: dict, user_message: str = "") -> str:
        summary = self._build_summary(raw_data)
        data_string = self._filter_activity_data(raw_data)

        token_estimate = len(data_string) // 4
        logger.debug(f"Payload size: {len(data_string)} chars (~{token_estimate} tokens)")

        system_prompt = self._build_system_prompt()
        user_prompt = self.config["prompts"]["user_prompt"].format(
            user_message=user_message or "Sin comentarios adicionales.",
            summary=summary,
            data_string=data_string
        )

        active_key = self.config["models"]["active"]
        model = self.config["models"][active_key]

        try:
            logger.debug("Calling Anthropic API...")
            response = self.client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            usage = response.usage
            logger.debug(
                f"Model used: {model} | Tokens — input: {usage.input_tokens} | "
                f"output: {usage.output_tokens} | total: {usage.input_tokens + usage.output_tokens}"
            )
            logger.success("Anthropic response received")
            return response.content[0].text

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return "Analysis failed."