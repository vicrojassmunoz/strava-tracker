import os
from datetime import date
import json
import tomllib
import anthropic
from loguru import logger
from dotenv import load_dotenv

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
        race_date = date(2027, 3, 1)
        weeks_to_race = (race_date - today).days // 7

        prompt = raw.format(
            today=today.strftime("%d %B %Y"),
            weeks_to_race=weeks_to_race
        )
        logger.debug(f"Race in {weeks_to_race} weeks ({race_date})")
        return prompt

    # TODO: Refactorizar y meter cada cosa en su sitio
    def analyze_raw_workout(self, raw_data: dict, user_message: str = "") -> str:
        # Pre-calcular datos clave para que el modelo no los infiera
        distance_km = round(raw_data.get('distance', 0) / 1000, 2)
        time_s = raw_data.get('moving_time', 0)
        avg_speed = raw_data.get('average_speed', 0)
        hours, remainder = divmod(time_s, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_fmt = f"{int(hours)}h {int(minutes)}min {int(seconds)}s" if hours > 0 else f"{int(minutes)}min {int(seconds)}s"

        if avg_speed > 0:
            pace_min_km = 1000 / (avg_speed * 60)
            pace_min, pace_sec = divmod(pace_min_km * 60, 60)
            pace_fmt = f"{int(pace_min)}:{int(pace_sec):02d} min/km"
        else:
            pace_fmt = "--:--"

        activity_date = raw_data.get('start_date_local', '')[:10]

        summary = f"""
        ## Pre-calculated session summary (use these values, do not recalculate)
        - Date: {activity_date}
        - Distance: {distance_km} km
        - Duration: {duration_fmt}
        - Average pace: {pace_fmt}
        - Elevation gain: {raw_data.get('total_elevation_gain', 0)} m
        - Avg HR: {raw_data.get('average_heartrate', 'N/A')} bpm
        - Max HR: {raw_data.get('max_heartrate', 'N/A')} bpm
        """

        USEFUL_KEYS = [
            'name', 'type', 'start_date_local', 'distance', 'moving_time',
            'elapsed_time', 'total_elevation_gain', 'average_speed', 'max_speed',
            'average_heartrate', 'max_heartrate', 'average_cadence',
            'splits_metric', 'laps', 'best_efforts', 'perceived_exertion'
        ]
        filtered_data = {k: raw_data[k] for k in USEFUL_KEYS if k in raw_data}
        data_string = json.dumps(filtered_data, ensure_ascii=False, indent=2)

        token_estimate = len(data_string) // 4
        logger.debug(f"Payload size: {len(data_string)} chars (~{token_estimate} tokens)")
        logger.debug(f"Pre-calculated — distance: {distance_km} km | pace: {pace_fmt} | duration: {duration_fmt}")

        system_prompt = self._build_system_prompt()
        user_prompt = self.config["prompts"]["user_prompt"].format(
            user_message=user_message or "Sin comentarios adicionales.",
            summary=summary,
            data_string=data_string
        )

        model = self.config["models"]["claude"]

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