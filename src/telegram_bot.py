import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from loguru import logger
from logger import setup_logger
from strava_client import StravaClient
from llm_client import LlmClient
from data_processing import StravaDataProcessor
import os
from dotenv import load_dotenv

load_dotenv()
setup_logger()

ALLOWED_USER_ID = int(os.getenv('TELEGRAM_ALLOWED_USER_ID', 0))
strava = StravaClient()
ai_coach = LlmClient()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ALLOWED_USER_ID:
        logger.warning(f"Unauthorized access attempt from user_id: {user_id}")
        await update.message.reply_text("No autorizado.")
        return

    user_message = update.message.text
    logger.info(f"Message received: '{user_message}'")

    await update.message.reply_text("Analizando tu última sesión... dame un momento.")

    try:
        # 1. Fetch latest activity
        logger.info("Fetching latest activity from Strava...")
        activities = strava.get_activities(limit=1)

        if not activities:
            await update.message.reply_text("No encontré actividades en Strava.")
            return

        activity = activities[0]
        activity_id = activity.get('id')
        processed = StravaDataProcessor.process_activity(activity)

        logger.info(f"Activity: '{processed['name']}' — {processed['date']}")
        logger.debug(f"  Distance: {processed['distance_km']} km | Pace: {processed['pace']}")

        # 2. Fetch full details
        detailed_data = strava.get_activity_details(activity_id)
        logger.success(f"Detail data fetched — {len(detailed_data)} fields")

        # 3. Analyze with AI coach
        logger.info("Sending to AI coach...")
        feedback = ai_coach.analyze_raw_workout(detailed_data, user_message=user_message)
        logger.success("Feedback received")

        # 4. Reply on Telegram
        await update.message.reply_text(feedback)

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        await update.message.reply_text("Ha ocurrido un error analizando la sesión. Revisa los logs.")


def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.critical("Missing TELEGRAM_BOT_TOKEN in .env")
        sys.exit(1)

    logger.info("Starting Telegram bot...")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.success("Bot is running. Waiting for messages...")
    app.run_polling()


if __name__ == '__main__':
    main()