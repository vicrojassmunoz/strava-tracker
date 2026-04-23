import io
import sys
from telegram import Update
from telegram.error import Conflict
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
        await update.message.reply_text("No estás autorizado para usar este bot.")
        return

    user_message = update.message.text
    logger.info(f"Message received: '{user_message}'")

    await update.message.reply_text(
        "¡Vamos allá! Estoy revisando tu última sesión de Strava... un momento."
    )

    try:
        # 1. Fetch latest activity
        logger.info("Fetching latest activity from Strava...")
        activities = strava.get_activities(limit=1)

        if not activities:
            await update.message.reply_text(
                "No encontré ninguna actividad reciente en Strava. ¿Has registrado algo últimamente?"
            )
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

        # 4. Send coach feedback
        await update.message.reply_text(feedback)

        # 5. Send filtered activity data as a JSON attachment
        filtered_json = ai_coach.filter_activity_data(detailed_data)
        file_buffer = io.BytesIO(filtered_json.encode("utf-8"))
        filename = f"activity_{activity_id}.json"
        await update.message.reply_document(
            document=file_buffer,
            filename=filename,
            caption=f"Datos de la sesión: {processed['name']} ({processed['date']})",
        )

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        await update.message.reply_text(
            "Algo salió mal al analizar la sesión. Inténtalo de nuevo en un momento."
        )


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        logger.warning("Conflict: another bot instance is already polling. This instance will back off.")
    else:
        logger.error(f"Unhandled update error: {context.error}")


def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.critical("Missing TELEGRAM_BOT_TOKEN in .env")
        sys.exit(1)

    logger.info("Starting Telegram bot...")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(handle_error)

    logger.success("Bot is running. Waiting for messages...")
    app.run_polling()


if __name__ == '__main__':
    main()
