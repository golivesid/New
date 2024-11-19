import os
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


# Bot details from environment variables
BOT_TOKEN = "6910046562:AAE4z0SZBa0bEeyzcGbxX8chwC-7jFCeUcI"
CHANNEL_1_USERNAME = "Rishuteam" # First channel username
CHANNEL_2_USERNAME = "RishuNetwork" # Second channel username
API_HASH = "42a60d9c657b106370c79bb0a8ac560c"
API_ID = "14050586"
TERABOX_API = "https://terabox-api.mrspyboy.workers.dev/"
DUMP_CHANNEL = "-1002436700388"
ADMIN_ID = int(os.getenv("ADMIN_ID", "5738579437"))  # Admin ID for new user notifications

# Flask app for monitoring
flask_app = Flask(__name__)
start_time = time.time()

# MongoDB setup
mongo_client = pymongo.MongoClient(os.getenv("MONGO_URI","mongodb+srv://Teraboxdownloader:Rajubhai@cluster0.tbocw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"))
db = mongo_client[os.getenv("MONGO_DB_NAME", "Rishu-free-db")]
users_collection = db[os.getenv("MONGO_COLLECTION_NAME", "users")]

# Pyrogram bot client
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


@flask_app.route('/')
def home():
    uptime_minutes = (time.time() - start_time) / 60
    user_count = users_collection.count_documents({})
    return f"Bot uptime: {uptime_minutes:.2f} minutes\nUnique users: {user_count}"


async def is_user_in_channel(client, user_id, channel_username):
    """Check if the user is a member of the specified channel."""
    try:
        await client.get_chat_member(channel_username, user_id)
        return True
    except UserNotParticipant:
        return False


async def send_join_prompt(client, chat_id):
    """Send a message asking the user to join both channels."""
    join_button_1 = InlineKeyboardButton("♡ Join ♡", url=f"https://t.me/{CHANNEL_1_USERNAME}")
    join_button_2 = InlineKeyboardButton("♡ Join ♡", url=f"https://t.me/{CHANNEL_2_USERNAME}")
    markup = InlineKeyboardMarkup([[join_button_1], [join_button_2]])
    await client.send_message(
        chat_id,
        "♡ You need to join both channels to use this bot. ♡",
        reply_markup=markup,
    )


@app.on_message(filters.command("start"))
async def start_message(client, message):
    user_id = message.from_user.id
    if users_collection.count_documents({'user_id': user_id}) == 0:
        # Insert new user into database
        users_collection.insert_one({'user_id': user_id})

        # Notify admin about the new user
        await client.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"💡 **New User Alert**:\n"
                f"👤 **User:** {message.from_user.mention}\n"
                f"🆔 **User ID:** `{user_id}`\n"
                f"📊 **Total Users:** {users_collection.count_documents({})}"
            )
        )

    await message.reply_text("♡ Hello! Send me a TeraBox URL to Get Started. ♡")


@app.on_message(filters.command("status"))
async def status_message(client, message):
    user_count = users_collection.count_documents({})
    uptime_minutes = (time.time() - start_time) / 60
    await message.reply_text(f"💫 Bot uptime: {uptime_minutes:.2f} minutes\n👥 Total unique users: {user_count}")


@app.on_message(filters.text & ~filters.command(["start", "status"]))
async def get_video_links(client, message):
    user_id = message.from_user.id

    # Check if the user is a member of both channels
    if not await is_user_in_channel(client, user_id, CHANNEL_1_USERNAME):
        await send_join_prompt(client, message.chat.id)
        return
    if not await is_user_in_channel(client, user_id, CHANNEL_2_USERNAME):
        await send_join_prompt(client, message.chat.id)
        return

    # Process the video request
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
            thumbnail = "https://envs.sh/L75.jpg"  # Default image if thumbnail is missing

        # Player URL using WebAppInfo
        player_url = f"{TERABOX_API}{video_url}"
        web_app = WebAppInfo(url=player_url)

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("♡ PLAY VIDEO ♡", web_app=web_app)],
            [InlineKeyboardButton('♡ SUPPORT ♡', url='https://t.me/Ur_rishu_143')],
            [InlineKeyboardButton('♡All bots  ♡', url='https://t.me/vip_robotz')]
        ])

        bot_message_text = f"**User:🤩 {message.from_user.mention}\nHere's your video:**"

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