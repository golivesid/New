import os
import urllib.parse
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatAction
from pyrogram.errors import UserNotParticipant, FloodWait
import requests
import time
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
import pymongo
import random

# Bot details from environment variables
BOT_TOKEN = "7838756294:AAHl13XUVw-8wgVJmla-Dz5qUl-8C9ijB_I"
CHANNEL_1_USERNAME = "VillageTv_Serials"  # First channel username
CHANNEL_2_USERNAME = "VijayTv_Serial_25"  # Second channel username
API_HASH = "561ae93345a2a4e435cff3c75a088b72"
API_ID = "20026290"
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


async def process_video_request(client, message):
    video_url = message.text.strip()
    await message.reply_chat_action(ChatAction.TYPING)

    # Check if the user sent a valid link
    if video_url.startswith(("http://", "https://")):
        # User sent a link
        parsed_link = urllib.parse.quote(video_url, safe='')
        modified_link = f"https://terabox-player-one.vercel.app/?url=https://www.terabox.tech/play.html?url={parsed_link}"
        modified_url = f"https://terabox-player-one.vercel.app/?url=https://www.terabox.tech/play.html?url={parsed_link}"
        link_parts = video_url.split('/')
        link_id = link_parts[-1]
        sharelink = f"https://t.me/share/url?url=https://t.me/TeraBox_OnlineBot?start=terabox-{link_id}"

        # Create buttons
        buttons = [
            [InlineKeyboardButton("🌐Stream Server 1🌐", url=modified_link)],
            [InlineKeyboardButton("🌐Stream Server 2🌐", url=modified_url)],
            [InlineKeyboardButton("◀Share▶", url=sharelink)]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        # Send the user's details and message to the dump channel
        user_message = (
            f"User message:\n"
            f"Name: {message.from_user.first_name}\n"
            f"Username: @{message.from_user.username}\n"
            f"User ID: {message.from_user.id}\n"
            f"Message: {video_url}"
        )
        await client.send_message(chat_id=DUMP_CHANNEL, text=user_message)

        # Send the message with the link and buttons
        await message.reply_text(
            "👇👇 YOUR VIDEO LINK IS READY, USE THESE SERVERS 👇👇\n\n"
            f"Original Link\n`{video_url}`\n\n"
            "♥ 👇Your Stream Link👇 ♥\n",
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'  # Use 'MarkdownV2' or 'HTML'
        )
    else:
        await message.reply_text("Please send me only a valid TeraBox link.")

# Flask thread for monitoring
def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)


flask_thread = Thread(target=run_flask)
flask_thread.start()

# Run Pyrogram bot
app.run()
