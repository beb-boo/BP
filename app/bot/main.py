
import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes
from telegram.error import NetworkError, TimedOut, TelegramError
from telegram.request import HTTPXRequest
from .handlers import get_auth_handler, get_ocr_handler, stats, help_command, unknown

load_dotenv()

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Suppress verbose httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and handle connection issues gracefully."""
    # If it's a network error, we can just log a simple message
    if isinstance(context.error, NetworkError):
        logger.warning(f"⚠️ Network Error detected: {context.error}. Retrying...")
        # run_polling handles retries automatically, no need to restart manually.
        return

    if isinstance(context.error, TimedOut):
        logger.warning("⚠️ Request Timed Out. Retrying...")
        return
    
    # For other errors, you might want to notify yourself or log more details
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables.")
        return

    # Configure connection timeouts via HTTPXRequest
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0
    )

    application = ApplicationBuilder().token(token).request(request).build()

    # Add Error Handler
    application.add_error_handler(error_handler)

    # Auth & Registration Conversation
    application.add_handler(get_auth_handler())
    
    # OCR & Record Logic (New ConversationHandler)
    application.add_handler(get_ocr_handler())
    
    # Simple Commands
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("help", help_command))

    # Fallback for unknown messages (Must be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    
    print("Bot is running... (Press Ctrl+C to stop)")
    
    # Run polling with correct arguments
    # poll_interval: Time to wait between polling updates from Telegram
    # timeout: Timeout for long polling connection (server side wait time)
    application.run_polling(poll_interval=1.0, timeout=30)

if __name__ == '__main__':
    main()
