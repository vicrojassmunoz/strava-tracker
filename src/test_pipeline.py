"""
Local pipeline test — runs without Telegram.
Edit USER_MESSAGE below, then: python src/test_pipeline.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from logger import setup_logger
from strava_client import StravaClient
from llm_client import LlmClient
from data_processing import StravaDataProcessor
from loguru import logger

USER_MESSAGE = "Hoy me notaba con las piernas cargadas pero terminé bien el fondo."


def main():
    setup_logger()
    logger.info("=== LOCAL PIPELINE TEST ===")
    logger.info(f"User message: '{USER_MESSAGE}'")

    strava = StravaClient()
    ai_coach = LlmClient()

    logger.info("Fetching latest activity from Strava...")
    activities = strava.get_activities(limit=1)

    if not activities:
        logger.error("No activities found in Strava.")
        sys.exit(1)

    activity = activities[0]
    activity_id = activity.get('id')
    processed = StravaDataProcessor.process_activity(activity)
    logger.info(f"Activity: '{processed['name']}' — {processed['date']} ({processed['distance_km']} km)")

    detailed_data = strava.get_activity_details(activity_id)
    logger.info("Sending to AI coach...")

    feedback = ai_coach.analyze_raw_workout(detailed_data, user_message=USER_MESSAGE)

    logger.success("=== FEEDBACK ===")
    print("\n" + feedback + "\n")


if __name__ == "__main__":
    main()
