from dotenv import load_dotenv
import os
import telebot
from telebot.async_telebot import AsyncTeleBot
import asyncio
from telebot import types
from telebot.util import quick_markup
import logging
import sys
sys.path.append(os.getcwd()) #needed to import services
from global_utils import load_env

logging.getLogger().setLevel(logging.INFO)
logger = telebot.logger

load_env("/home/pablo/motionapps/AI_writer/.env", "/home/pablo/motionapps/AI_writer/ai_writer_prod.env")

from utils import compare_str_wo_emojis
from services import get_notes, get_transcription  # import after load_dotenv()

telebot.logger.setLevel(logging.DEBUG) # Outputs debug messages to console.

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
logger.info(f"Bot token: {BOT_TOKEN}")

bot = AsyncTeleBot(BOT_TOKEN, parse_mode="Markdown")
APP_NAME = "AI_writer"
remove_btns_markup = types.ReplyKeyboardRemove(selective=False)
START_MESSAGE = """Hi! To get started send audio notes or text messages, I will summarize them for you!
Feel free to forward from other Telegram or Whatsapp chats.
You can use me for:\n
• Brainstorming while walking the dog 🐶 and keeping a record of the most important items.
• Forwarding long audios and texts that you don't have the time to process entirely.
• Taking any notes you want quickly just with your voice: TODO lists, travel plans ✈️, etc.
"""

CRON_INTERVAL = int(os.environ.get('CRON_INTERVAL'))

async def process_message(message):
    chat_id = message.chat.id
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
    else:
        text = message.text
    # process when last msg arrives, else queue them so we later process them altogether
    # usecase: when we forward N msgs. in future improvement could also be the case if user starts recording new audio before receiving summary of previous one.
    try:
        title, notes = await get_notes([text])
        full_notes = f"*{title}*"
        if notes:
            full_notes += f"\n\n{notes}"
        msg = await bot.reply_to(message, full_notes, reply_markup=remove_btns_markup)
    except ValueError as e:
        await bot.send_message(message.chat.id, "*Could note take notes.* I'm sorry but the underlying LLM is refusing to take notes on this content. This may happen when content it about non politically correct topics. I'm sorry for the inconvenience.", reply_markup=remove_btns_markup)

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    await bot.reply_to(message, START_MESSAGE, reply_markup=remove_btns_markup)


@bot.message_handler(commands=['faq'])
async def send_faq(message):
    faq = """
    *Q: How do you handle my data?*
    A: All storage is ephemeral, I don't store any of your notes long term, I process them and drop all your audios, messages and summaries after sendimg them to you.\n\n*Q: How can I reach out to you?*
    A: Visit https://pablomarino.com for more information about the developer.
    """
    logging.info(f"User sent a message: {message}")
    await bot.reply_to(message, faq, reply_markup=remove_btns_markup)

@bot.message_handler(content_types=['voice', 'text', 'audio'])
async def handle_all(message):
    await process_message(message)

logging.info("Telegram bot is running...")

asyncio.run(bot.polling(request_timeout=30))


