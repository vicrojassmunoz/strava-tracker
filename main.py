import sys
from loguru import logger
from logger import setup_logger
from strava_client import StravaClient
from llm_client import LlmClient

setup_logger()


def main():
    logger.info("Initializing performance tracker...")

    # 1. Init clients
    try:
        strava = StravaClient()
        logger.success("Strava client initialized")
        ai_coach = LlmClient()
        logger.success("Groq client initialized")
    except ValueError as e:
        logger.critical(f"Configuration error: {e}")
        sys.exit(1)

    # 2. Fetch latest activity
    logger.info("Fetching latest activity from Strava...")
    activities = strava.get_activities(limit=1)

    if not activities:
        logger.warning("No activities found.")
        sys.exit(0)

    activity = activities[0]
    activity_id = activity.get('id')
    activity_name = activity.get('name', 'Unknown')
    activity_date = activity.get('start_date_local', 'Unknown date')[:10]
    distance_km = round(activity.get('distance', 0) / 1000, 2)
    moving_time = activity.get('moving_time', 0)
    avg_speed = activity.get('average_speed', 0)
    pace_min_km = (1000 / (avg_speed * 60)) if avg_speed > 0 else 0
    pace_fmt = f"{int(pace_min_km)}:{int((pace_min_km % 1) * 60):02d} min/km"

    logger.info(f"Activity found: '{activity_name}' — {activity_date}")
    logger.debug(f"  ID       : {activity_id}")
    logger.debug(f"  Distance : {distance_km} km")
    logger.debug(f"  Time     : {moving_time // 60}min {moving_time % 60}s")
    logger.debug(f"  Avg pace : {pace_fmt}")

    # 3. Fetch full details
    logger.info(f"Fetching full details for activity {activity_id}...")
    detailed_data = strava.get_activity_details(activity_id)
    logger.debug(f"  JSON keys: {list(detailed_data.keys())}")
    logger.success(f"Detail data fetched — {len(detailed_data)} fields")

    # 4. Analyze with Groq
    logger.info("Sending data to AI coach (Groq / LLaMA 3.3 70B)...")
    feedback = ai_coach.analyze_raw_workout(detailed_data)
    logger.success("Feedback received from AI coach")

    # 5. Print feedback
    logger.info(f"Feedback: \n{feedback}")


if __name__ == '__main__':
    main()