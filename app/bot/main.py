
import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler
from .handlers import get_auth_handler, get_ocr_handler, stats

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables.")
        return

    application = ApplicationBuilder().token(token).build()

    # Auth & Registration Conversation
    application.add_handler(get_auth_handler())
    
    # OCR & Record Logic (New ConversationHandler)
    application.add_handler(get_ocr_handler())
    
    # Simple Commands
    application.add_handler(CommandHandler("stats", stats))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
