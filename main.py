from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from pyrogram.enums import ChatAction
from pyrogram.errors import UserNotParticipant
import requests
import time
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
import pymongo
from typing import Optional

# Bot details
BOT_TOKEN = '6910046562:AAE4z0SZBa0bEeyzcGbxX8chwC-7jFCeUcI'
CHANNEL_USERNAME = 'RishuTeam'  # Ensure no '@' symbol here
API_HASH = '42a60d9c657b106370c79bb0a8ac560c'
API_ID = '14050586'
TERABOX_API = 'https://terabox-api.mrspyboy.workers.dev'
DUMP_CHANNEL = -1002436700388

# Flask app for monitoring
flask_app = Flask(__name__)
start_time = time.time()

# MongoDB setup
mongo_client = pymongo.MongoClient('mongo:lOMs3uDmCxgNFYNP@cluster0.376zvxq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = mongo_client['Rishu-free-db']
users_collection = db['users']

# Pyrogram bot client
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@flask_app.route('/')
def home():
    uptime_minutes = (time.time() - start_time) / 60
    user_count = users_collection.count_documents({})
    return f"Bot uptime: {uptime_minutes:.2f} minutes\nUnique users: {user_count}"

async def is_user_in_channel(client, user_id):
    try:
        await client.get_chat_member(CHANNEL_USERNAME, user_id)
        return True
    except UserNotParticipant:
        return False

async def send_join_prompt(client, chat_id):
    join_button = InlineKeyboardButton("♡ Join ♡", url=f"https://t.me/{CHANNEL_USERNAME}")
    blume_button = InlineKeyboardButton('♡ Join ♡', url='https://t.me/vip_robotz')
    markup = InlineKeyboardMarkup([[join_button, blume_button]])
    await client.send_message(chat_id, "You need to join our channel to use this bot. ♡♡♡", reply_markup=markup)

@app.on_message(filters.command("start"))
async def start_message(client, message):
    user_id = message.from_user.id
    if users_collection.count_documents({'user_id': user_id}) == 0:
        users_collection.insert_one({'user_id': user_id})
    await message.reply_text("♡ Hello! Send me a TeraBox URL to Get Started. ♡")

@app.on_message(filters.command("status"))
async def status_message(client, message):
    user_count = users_collection.count_documents({})
    uptime_minutes = (time.time() - start_time) / 60
    await message.reply_text(f"💫 Bot uptime: {uptime_minutes:.2f} minutes\n👥 Total unique users: {user_count}")

@app.on_message(filters.text & ~filters.command(["start", "status"]))
async def get_video_links(client, message):
    user_id = message.from_user.id
    if not await is_user_in_channel(client, user_id):
        await send_join_prompt(client, message.chat.id)
        return
    await process_video_request(client, message)

def fetch_video_details(video_url: str) -> Optional[str]:
    """Fetch video thumbnail from a direct TeraBox URL."""
    try:
        response = requests.get(video_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.find("meta", property="og:image")["content"] if soup.find("meta", property="og:image") else None
    except requests.exceptions.RequestException:
        return None

async def process_video_request(client, message):
    video_url = message.text.strip()
    await message.reply_chat_action(ChatAction.TYPING)
    
    try:
        # Retrieve video details
        thumbnail = fetch_video_details(video_url)
        if not thumbnail:
            thumbnail = "https://envs.sh/L75.jpg"  # Use a default image if thumbnail is missing
        
        # Player URL using WebAppInfo
        player_url = f"{TERABOX_API}{video_url}"
        web_app = WebAppInfo(url=player_url)
        
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("♡ Play Video ♡", web_app=web_app)],
            [InlineKeyboardButton('♡ Support ♡', url='https://t.me/ur_rishu_143')],
            [InlineKeyboardButton('♡ All Bots ♡', url='https://t.me/vip_robotz')]
        ])
        
        # Prepare the bot message
        bot_message_text = f"**User:💀 {message.from_user.mention}\nHere's your video:**"
        
        # Send video details to the user
        await client.send_photo(
            chat_id=message.chat.id,
            photo=thumbnail,
            caption=bot_message_text,
            reply_markup=markup,
        )
        
        # Forward the link and thumbnail to the dump channel
        dump_message_text = f"From {message.from_user.mention}:\n Link: [Watch Video]({player_url})"
        await client.send_photo(
            chat_id=DUMP_CHANNEL,
            photo=thumbnail,
            caption=dump_message_text
        )
        
    except requests.exceptions.RequestException as e:
        await message.reply_text(f"Error connecting to the API: {str(e)}")

# Flask thread for monitoring
def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

flask_thread = Thread(target=run_flask)
flask_thread.start()

# Run Pyrogram bot
app.run()
