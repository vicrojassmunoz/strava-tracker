import os
from datetime import date
import json
import tomllib
from loguru import logger
from dotenv import load_dotenv
from data_processing import StravaDataProcessor
from llm_provider import LlmProvider, AnthropicProvider, GroqProvider

load_dotenv()

# Model aliases that are served via Groq
_GROQ_ALIASES = {"qwen", "llama", "scout"}


class LlmClient:
    def __init__(self, provider: LlmProvider | None = None):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.toml")
        with open(config_path, "rb") as f:
            self.config = tomllib.load(f)
        logger.debug("Config loaded from config.toml")

        self.provider = provider or self._build_provider()

    def _build_provider(self) -> LlmProvider:
        active_key = self.config["models"]["active"]
        model = self.config["models"][active_key]

        if active_key in _GROQ_ALIASES:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("Missing GROQ_API_KEY in .env — required for the selected model")
            return GroqProvider(api_key=api_key, model=model)

        # Default: Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Missing ANTHROPIC_API_KEY in .env")
        return AnthropicProvider(api_key=api_key, model=model)

    def _build_system_prompt(self) -> str:
        raw = self.config["prompts"]["system_prompt"]
        today = date.today()
        race_date = date.fromisoformat(self.config["race"]["date"])
        weeks_to_race = (race_date - today).days // 7

        prompt = raw.format(
            today=today.strftime("%d %B %Y"),
            weeks_to_race=weeks_to_race,
        )
        logger.debug(f"Race in {weeks_to_race} weeks ({race_date})")
        return prompt

    USEFUL_KEYS = [
        "name", "type", "start_date_local", "distance", "moving_time",
        "elapsed_time", "total_elevation_gain", "average_speed", "max_speed",
        "average_heartrate", "max_heartrate", "average_cadence",
        "splits_metric", "laps", "best_efforts", "perceived_exertion",
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
        if "avg_heartrate" in p:
            lines.append(f"- Avg HR: {p['avg_heartrate']} bpm")
        if "max_heartrate" in p:
            lines.append(f"- Max HR: {p['max_heartrate']} bpm")
        logger.debug(f"Pre-calculated — distance: {p['distance_km']} km | pace: {p['pace']} | duration: {p['duration']}")
        return "\n".join(lines)

    def filter_activity_data(self, raw_data: dict) -> str:
        """Return a JSON string containing only the keys relevant to the LLM."""
        filtered = {k: raw_data[k] for k in self.USEFUL_KEYS if k in raw_data}
        return json.dumps(filtered, ensure_ascii=False, indent=2)

    def analyze_raw_workout(self, raw_data: dict, user_message: str = "") -> str:
        summary = self._build_summary(raw_data)
        data_string = self.filter_activity_data(raw_data)

        token_estimate = len(data_string) // 4
        logger.debug(f"Payload size: {len(data_string)} chars (~{token_estimate} tokens)")

        system_prompt = self._build_system_prompt()
        user_prompt = self.config["prompts"]["user_prompt"].format(
            user_message=user_message or "Sin comentarios adicionales.",
            summary=summary,
            data_string=data_string,
        )

        try:
            feedback = self.provider.complete(system_prompt, user_prompt, max_tokens=1024)
            logger.success("LLM response received")
            return feedback
        except Exception as e:
            logger.error(f"LLM provider error: {e}")
            return "Analysis failed."
