import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from pyrogram.enums import ChatAction
from pyrogram.errors import UserNotParticipant, FloodWait
import requests
import time
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
import pymongo
import re
from typing import Optional
import random

# Bot details from environment variables
BOT_TOKEN = "7838756294:AAHl13XUVw-8wgVJmla-Dz5qUl-8C9ijB_I"
CHANNEL_1_USERNAME = "VillageTv_Serials"  # First channel username
CHANNEL_2_USERNAME = "VijayTv_Serial_25"  # Second channel username
API_HASH = "561ae93345a2a4e435cff3c75a088b72"
API_ID = "20026290"
TERABOX_API = "https://terabox-api.mrspyboy.workers.dev/"  # Ensure this URL is correct
DUMP_CHANNEL = "-1002688354661"
ADMIN_ID = int(os.getenv("ADMIN_ID", "5084389526"))  # Admin ID for new user notifications

# Flask app for monitoring
flask_app = Flask(__name__)
start_time = time.time()

# MongoDB setup
mongo_client = pymongo.MongoClient(
    os.getenv(
        "MONGO_URI",
        "mongodb+srv://sankar:sankar@sankar.lldcdsx.mongodb.net/?retryWrites=true&w=majority"
    )
)
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
    except Exception:
        return False


async def send_join_prompt(client, chat_id):
    """Send a message asking the user to join both channels."""
    join_button_1 = InlineKeyboardButton("♡ Join ♡", url=f"https://t.me/{CHANNEL_1_USERNAME}")
    join_button_2 = InlineKeyboardButton("♡ Join ♡", url=f"https://t.me/{CHANNEL_2_USERNAME}")
    markup = InlineKeyboardMarkup([[join_button_1], [join_button_2]])
    await client.send_message(
        chat_id,
        "♡ You need to join both channels to use this bot.. ♡",
        reply_markup=markup,
    )


@app.on_message(filters.command("start"))
async def start_message(client, message):
    user_id = message.from_user.id
    # Check if the user is new
    if users_collection.count_documents({'user_id': user_id}) == 0:
        # Insert new user into the database
        users_collection.insert_one({'user_id': user_id})

        # Notify the admin about the new user
        await client.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"💡 **New User Alert**:\n\n"
                f"👤 **User:** {message.from_user.mention}\n"
                f"🆔 **User ID:** `{user_id}`\n"
                f"📊 **Total Users:** {users_collection.count_documents({})}"
            )
        )

    # Random image selection
    image_urls = [
        "https://envs.sh/53z.jpg",
        "https://envs.sh/53K.jpg",
        "https://envs.sh/5zY.jpg",
        "https://envs.sh/5z3.jpg",
        "https://envs.sh/5zz.jpg"
    ]
    random_image = random.choice(image_urls)

    # Inline buttons for channel join
    join_button_1 = InlineKeyboardButton("♡ Support ♡", url=f"https://t.me/Ur_rishu_143")
    join_button_2 = InlineKeyboardButton("♡ All Bots ♡", url=f"https://t.me/vip_robotz")
    support_button = InlineKeyboardButton('♡ FAQ ♡', callback_data='faq')

    markup = InlineKeyboardMarkup([[join_button_1], [join_button_2], [support_button]])

    # Send the welcome message with the random image
    await client.send_photo(
        chat_id=message.chat.id,
        photo=random_image,
        caption=f"**♡ Welcome: {message.from_user.mention} **\n\n**♡Send me a TeraBox URL to Get Started. ♡**\n\n╔═════════════════╗\n║ ➻**ʟᴏᴠᴇ ᴡɪᴛʜ** ➪ [꯭꯭↬꯭ᬃ꯭ ⃪꯭ ꯭⁢⁣⁤⁣⁣⁢⁣⁤⁢⁤⁣⁢⁤⁣⁤᪳᪳🇷꯭𝚰𝛅꯭꯭ʜ꯭֟፝፝֟ᴜ ꯭꯭༗꯭»꯭݅݅݅݅𓆪](https://t.me/ur_rishu_143)\n║\n╚═════════════════╝",
        reply_markup=markup
    )


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

    # Validate the video URL
    if not video_url.startswith(("http://", "https://")):
        await message.reply_text("❌ Invalid URL. Please provide a valid TeraBox URL.")
        return

    try:
        # Construct the API request URL
        api_url = f"{TERABOX_API}?url={video_url}"
        print(f"API URL: {api_url}")  # Debugging

        # Fetch the video download link from the API
        response = requests.get(api_url)
        if response.status_code != 200:
            await message.reply_text("❌ Failed to fetch video details from the API.")
            return

        # Parse the API response
        data = response.json()
        if not data.get("success"):
            await message.reply_text("❌ Failed to fetch video details from the API.")
            return

        # Get the video download link
        download_url = data.get("download_url")
        if not download_url:
            await message.reply_text("❌ No download URL found in the API response.")
            return

        # Download the video
        video_response = requests.get(download_url, stream=True)
        if video_response.status_code != 200:
            await message.reply_text("❌ Failed to download the video.")
            return

        # Save the video temporarily
        with open("video.mp4", "wb") as f:
            for chunk in video_response.iter_content(chunk_size=1024):
                f.write(chunk)

        # Send the video to the user
        await client.send_video(
            chat_id=message.chat.id,
            video="video.mp4",
            caption=f"**Dear: 🤩  {message.from_user.mention}\n\nHere's your video:**"
        )

        # Clean up the temporary file
        os.remove("video.mp4")

    except requests.exceptions.RequestException as e:
        await message.reply_text(f"Error connecting to the API: {str(e)}")


# Flask thread for monitoring
def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)


flask_thread = Thread(target=run_flask)
flask_thread.start()

# Run Pyrogram bot
app.run()
