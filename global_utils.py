#from telegram import sync_send_telegram_msg
from dotenv import load_dotenv
import os
import logging
from datetime import datetime

def custom_error_handler(record):
    print(f"Custom handling for error: {record.levelname} - {record.getMessage()}")
    tg_msg = f"{record.levelname} - {record.getMessage()}"
    BOT_TOKEN = os.environ.get("MONITORING_TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("MONITORING_TELEGRAM_USER_ID")
    #sync_send_telegram_msg(CHAT_ID, BOT_TOKEN, tg_msg, parse_mode="HTML")


def get_logger(name):
    class CustomFormatter(logging.Formatter):
        def format(self, record):
            record.date = datetime.now().strftime("%Y-%m-%d")
            return super().format(record)

    class CustomHandler(logging.StreamHandler):
        def emit(self, record):
            if record.levelno >= logging.WARNING and custom_error_handler:
                custom_error_handler(record)
            super().emit(record)

    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Create a custom formatter
    formatter = CustomFormatter('%(asctime)s - %(date)s - %(name)s - %(levelname)s - %(message)s')

    # Create a custom handler and set the formatter
    handler = CustomHandler()
    handler.setFormatter(formatter)

    # Remove any existing handlers and add the new one
    logger.handlers.clear()
    logger.addHandler(handler)

    return logger

def load_env(dev_env_path, prod_env_path):
    logger = get_logger(__name__)
    load_dotenv(dev_env_path)
    if os.path.exists(prod_env_path):
        # overwrites with production env variables # if prod file exists
        load_dotenv(prod_env_path, override=True)
        logger.info("Production env file loaded")
    else:
        logger.info("No production env file found")


def extract_title_and_notes(text):
    # Extract the title
    if("<title>" not in text):
        raise ValueError("Title not found in the output")
    start_title = text.find("<title>") + len("<title>")
    end_title = text.find("</title>")
    title = text[start_title:end_title].strip()
    
    # Extract the notes
    if "<notes>" in text:
        start_notes = text.find("<notes>") + len("<notes>")
        end_notes = text.find("</notes>")
        notes_text = text[start_notes:end_notes].strip()
    else:
        notes_text = ""
    
    return title, notes_text