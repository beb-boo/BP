
import logging
from logging.handlers import RotatingFileHandler
import os
import sys

# Configure specific logger for transactions
txn_logger = logging.getLogger("bot_transactions")
txn_logger.setLevel(logging.INFO)
txn_logger.propagate = False  # Prevent propagation to root logger (avoid double printing if root has console)

# Check if handlers already exist to avoid adding duplicates on reload
if not txn_logger.handlers:
    # 1. Console Handler (stdout)
    c_handler = logging.StreamHandler(sys.stdout)
    c_formatter = logging.Formatter('🔵 [BOT-TXN] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    c_handler.setFormatter(c_formatter)
    txn_logger.addHandler(c_handler)

    # 2. File Handler (Rotating)
    # Create logs directory if not exists
    log_dir = "logs"
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "bot_transactions.log")
        
        # Rotate: 10MB limit, keep 5 backups
        f_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        f_formatter = logging.Formatter('%(asctime)s - %(message)s')
        f_handler.setFormatter(f_formatter)
        txn_logger.addHandler(f_handler)
    except Exception as e:
        print(f"Failed to setup file logging: {e}")

class BotLogService:
    @staticmethod
    def log(telegram_id: int, direction: str, message_type: str, content: str, user_id: int = None, meta_data: dict = None):
        """
        Log a bot transaction to Console and File.
        direction: 'IN' or 'OUT'
        """
        try:
            user_label = f"UID:{user_id}" if user_id else f"TID:{telegram_id}"
            
            # Truncate content for log readability if too long
            clean_content = str(content).replace('\n', ' ')
            if len(clean_content) > 100:
                clean_content = clean_content[:97] + "..."
                
            log_msg = f"[{direction}] [{user_label}] [{message_type}] {clean_content}"
            
            txn_logger.info(log_msg)
            
        except Exception as e:
            # Fallback to print if logger fails
            print(f"Logging Error: {e}")
