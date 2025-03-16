from dotenv import load_dotenv
import os
import telebot
from telebot.async_telebot import AsyncTeleBot
import asyncio
import json
from telebot import types
from telebot.util import quick_markup
import logging
import sys
sys.path.append(os.getcwd()) #needed to import services
from utils import load_env

logging.getLogger().setLevel(logging.INFO)
logger = telebot.logger

# Get the current directory and load .env from there
current_dir = os.path.dirname(os.path.abspath(__file__))
load_env(os.path.join(current_dir, ".env"))
from services import get_transcription, process_text  # import after load_dotenv()

telebot.logger.setLevel(logging.DEBUG) # Outputs debug messages to console.

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_USER_ID = os.environ.get('TELEGRAM_USER_ID')
logger.info(f"Bot token: {BOT_TOKEN}")

bot = AsyncTeleBot(BOT_TOKEN)
remove_btns_markup = types.ReplyKeyboardRemove(selective=False)
START_MESSAGE = """Hi! To get started send audio notes or text messages.
"""

async def process_message(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    if user_id != TELEGRAM_USER_ID:
        # Only authorized user can use this bot, to prevent hackers from accessing your server and LLM calls.
        user_details = f"User ID: {message.from_user.id}, Username: {message.from_user.username}, First Name: {message.from_user.first_name}, Last Name: {message.from_user.last_name}"
        logger.error(f"User is not authorized to use this bot, user details: {user_details}")
        await bot.send_message(TELEGRAM_USER_ID, f"SOMEONE NOT AUTHORIZED IS TRYING TO USE THE BOT, USER INFORMATION: {user_details}", reply_markup=remove_btns_markup)
        return
    await bot.send_chat_action(chat_id, "typing")
    if message.content_type in ['voice', 'audio']:
        if message.content_type == 'voice':
            file_info = await bot.get_file(message.voice.file_id)
        else:
            file_info = await bot.get_file(message.audio.file_id)
        MAX_FILE_SIZE = 2* 1024 * 1024 # 2 mb of audio is a lot!
        if file_info.file_size > MAX_FILE_SIZE:
            logger.error(f"File size is too big, please upload a file smaller than 2MB")
            await bot.reply_to(message, "File size is too big, please upload a file smaller than 2MB", reply_markup=remove_btns_markup)
            return 
        downloaded_file = await bot.download_file(file_info.file_path)
        file_name = file_info.file_path.split("/")[-1]
        text = await get_transcription(downloaded_file, file_name)
        await bot.reply_to(message, "I just transcribed your audio to: \n\n"+text, reply_markup=remove_btns_markup)
    else:
        text = message.text
    # process when last msg arrives, else queue them so we later process them altogether
    # usecase: when we forward N msgs. in future improvement could also be the case if user starts recording new audio before receiving summary of previous one.
    try:
        outputs = await process_text(text)
        for output in outputs:
            msg = await bot.reply_to(message, output, reply_markup=remove_btns_markup)
    except ValueError as e:
        await bot.send_message(message.chat.id, "*Could process request.* I'm sorry but the underlying LLM is refusing to take notes on this content. This may happen when content it about non politically correct topics. I'm sorry for the inconvenience.", reply_markup=remove_btns_markup)

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    await bot.reply_to(message, START_MESSAGE, reply_markup=remove_btns_markup)

@bot.message_handler(content_types=['voice', 'text', 'audio'])
async def handle_all(message):
    await process_message(message)

logging.info("Telegram bot is running...")

asyncio.run(bot.polling(request_timeout=30))


