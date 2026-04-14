"""
Local pipeline test — runs without Telegram.
Edit USER_MESSAGE below, then: python src/test_pipeline.py
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from logger import setup_logger
from strava_client import StravaClient
from llm_client import LlmClient
from llm_provider import LlmProvider, AnthropicProvider
from fitness_client import FitnessClient
from data_processing import StravaDataProcessor
from loguru import logger

USER_MESSAGE = "Hoy me notaba con las piernas cargadas pero terminé bien el fondo."


def check_interfaces():
    """Verify that the concrete classes properly implement their abstract interfaces."""
    assert issubclass(StravaClient, FitnessClient), "StravaClient must implement FitnessClient"
    assert issubclass(AnthropicProvider, LlmProvider), "AnthropicProvider must implement LlmProvider"
    logger.success("Interface checks passed — StravaClient and AnthropicProvider implement their ABCs")


def main():
    setup_logger()
    logger.info("=== LOCAL PIPELINE TEST ===")
    logger.info(f"User message: '{USER_MESSAGE}'")

    # 1. Interface sanity checks (no network calls)
    check_interfaces()

    strava = StravaClient()
    ai_coach = LlmClient()

    # 2. Fetch latest activity
    logger.info("Fetching latest activity from Strava...")
    activities = strava.get_activities(limit=1)

    if not activities:
        logger.error("No activities found in Strava.")
        sys.exit(1)

    activity = activities[0]
    activity_id = activity.get('id')
    processed = StravaDataProcessor.process_activity(activity)
    logger.info(f"Activity: '{processed['name']}' — {processed['date']} ({processed['distance_km']} km)")

    # 3. Fetch full detail
    detailed_data = strava.get_activity_details(activity_id)

    # 4. Verify filter_activity_data (used for the Telegram attachment)
    filtered_json = ai_coach.filter_activity_data(detailed_data)
    try:
        parsed = json.loads(filtered_json)
        logger.success(
            f"filter_activity_data — valid JSON, {len(parsed)} keys, "
            f"{len(filtered_json)} chars (~{len(filtered_json) // 4} tokens)"
        )
    except json.JSONDecodeError as e:
        logger.error(f"filter_activity_data returned invalid JSON: {e}")
        sys.exit(1)

    # 5. Analyze with AI coach
    logger.info("Sending to AI coach...")
    feedback = ai_coach.analyze_raw_workout(detailed_data, user_message=USER_MESSAGE)

    logger.success("=== FEEDBACK ===")
    print("\n" + feedback + "\n")

    logger.success("=== FILTERED JSON (attachment preview) ===")
    print(filtered_json + "\n")


if __name__ == "__main__":
    main()
