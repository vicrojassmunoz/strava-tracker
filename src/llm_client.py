import os
from datetime import date
import json
import tomllib
from groq import Groq
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class GroqClient:
    def __init__(self):
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY in .env file")

        self.client = Groq(api_key=api_key)
        logger.debug("Groq API client created")

        with open("config.toml", "rb") as f:
            self.config = tomllib.load(f)
        logger.debug("Prompts loaded from config.toml")

    def _build_system_prompt(self) -> str:
        raw = self.config["prompts"]["system_prompt"]
        today = date.today()
        race_date = date(2027, 3, 1)  # ajusta cuando confirmes la fecha exacta
        weeks_to_race = (race_date - today).days // 7

        prompt = raw.format(
            today=today.strftime("%d %B %Y"),
            weeks_to_race=weeks_to_race
        )
        logger.debug(f"Race in {weeks_to_race} weeks ({race_date})")
        return prompt

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

        data_string = json.dumps(raw_data, ensure_ascii=False, indent=2)
        token_estimate = len(data_string) // 4
        logger.debug(f"Payload size: {len(data_string)} chars (~{token_estimate} tokens)")
        logger.debug(f"Pre-calculated — distance: {distance_km} km | pace: {pace_fmt} | duration: {duration_fmt}")

        system_prompt = self._build_system_prompt()
        user_prompt = self.config["prompts"]["user_prompt"].format(
            user_message=user_message or "Sin comentarios adicionales.",
            summary=summary,
            data_string=data_string
        )

        active = self.config["models"]["active"]
        model = self.config["models"][active]

        try:
            logger.debug("Calling Groq API...")
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1024,
            )
            usage = response.usage
            logger.debug(
                f"Model used: {model} | Tokens — prompt: {usage.prompt_tokens} | "
                f"completion: {usage.completion_tokens} | total: {usage.total_tokens}")
            logger.success("Groq response received")
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return "Analysis failed."
