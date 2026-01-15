
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes, TypeHandler, CallbackQueryHandler
from telegram.error import NetworkError, TimedOut, TelegramError
from telegram.request import HTTPXRequest
from .handlers import get_auth_handler, get_ocr_handler, stats, help_command, unknown, language_command, language_callback, settings_command, settings_callback, timezone_callback
from .payment_handlers import get_payment_handler, subscription_command
import warnings
from telegram.warnings import PTBUserWarning

# Suppress PTBUserWarning about CallbackQueryHandler in ConversationHandler
warnings.filterwarnings("ignore", category=PTBUserWarning, message=".*CallbackQueryHandler.*")

from .log_service import BotLogService

async def log_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log all incoming updates."""
    try:
        user = update.effective_user
        if not user:
            return

        msg_type = "unknown"
        content = ""
        
        if update.message:
            if update.message.text:
                msg_type = "text"
                content = update.message.text
            elif update.message.photo:
                msg_type = "photo"
                content = "User sent a photo"
            elif update.message.contact:
                msg_type = "contact"
                content = f"Contact: {update.message.contact.phone_number}"
        elif update.callback_query:
            msg_type = "callback"
            content = f"Data: {update.callback_query.data}"
        
        if content:
            BotLogService.log(
                telegram_id=user.id,
                direction="IN",
                message_type=msg_type,
                content=content
            )
    except Exception as e:
        logger.error(f"Logging Error: {e}")

load_dotenv()

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Suppress verbose httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Track connection state
IS_CONNECTION_LOST = False

async def connection_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitor successfully received updates to log reconnection."""
    global IS_CONNECTION_LOST
    if IS_CONNECTION_LOST:
        logger.info("✅ Connection restored! Resuming update processing...")
        IS_CONNECTION_LOST = False

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and handle connection issues gracefully."""
    global IS_CONNECTION_LOST
    
    # If it's a network error, we can just log a simple message
    if isinstance(context.error, NetworkError):
        if not IS_CONNECTION_LOST:
            logger.warning(f"⚠️ Network Error detected: {context.error}. Retrying...")
            IS_CONNECTION_LOST = True
        return

    if isinstance(context.error, TimedOut):
        if not IS_CONNECTION_LOST:
            logger.warning("⚠️ Request Timed Out. Retrying...")
            IS_CONNECTION_LOST = True
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
    
    # Monitor connection state (Runs first)
    application.add_handler(TypeHandler(Update, connection_monitor), group=-1)
    
    # Log Middleware (Runs in separate group to ensure execution)
    application.add_handler(TypeHandler(Update, log_middleware), group=-5)

    # Add Error Handler
    application.add_error_handler(error_handler)

    # Auth & Registration Conversation
    application.add_handler(get_auth_handler())
    
    # Payment / Subscription (New)
    application.add_handler(get_payment_handler())
    application.add_handler(CommandHandler("subscription", subscription_command))
    
    # OCR & Record Logic (New ConversationHandler)
    
    # OCR & Record Logic (New ConversationHandler)
    application.add_handler(get_ocr_handler())
    
    # Simple Commands
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("help", help_command))
    
    # Language (New)
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CallbackQueryHandler(language_callback, pattern='^lang_'))

    # Settings with Timezone (New)
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern='^settings_'))
    application.add_handler(CallbackQueryHandler(timezone_callback, pattern='^tz_'))

    # Fallback for unknown messages (Must be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    
    print("Bot is running... (Press Ctrl+C to stop)")
    
    # Run polling with correct arguments
    # poll_interval: Time to wait between polling updates from Telegram
    # timeout: Timeout for long polling connection (server side wait time)
    application.run_polling(poll_interval=1.0, timeout=30)

if __name__ == '__main__':
    main()
