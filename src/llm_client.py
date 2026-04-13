import os
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

    def analyze_raw_workout(self, raw_data: dict) -> str:
        data_string = json.dumps(raw_data, ensure_ascii=False, indent=2)
        token_estimate = len(data_string) // 4
        logger.debug(f"Payload size: {len(data_string)} chars (~{token_estimate} tokens)")

        system_prompt = self.config["prompts"]["system_prompt"]
        user_prompt = self.config["prompts"]["user_prompt"].format(data_string=data_string)

        try:
            logger.debug("Calling Groq API...")
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1024,
            )
            usage = response.usage
            logger.debug(f"  Tokens used — prompt: {usage.prompt_tokens} | completion: {usage.completion_tokens} | total: {usage.total_tokens}")
            logger.success("Groq response received")
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return "Analysis failed."