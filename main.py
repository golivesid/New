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
from pyrogram.errors import FloodWait
import pymongo
import re
from typing import Optional
import random

# Bot details from environment variables
BOT_TOKEN = "6956731651:AAHdXJxSS6qliZAkCCCPAzPwU4i-oha0PY0"
CHANNEL_1_USERNAME = "Rishuteam"  # First channel username
CHANNEL_2_USERNAME = "RishuNetwork"  # Second channel username
API_HASH = "42a60d9c657b106370c79bb0a8ac560c"
API_ID = "14050586"
TERABOX_API = "https://terabox-api.mrspyboy.workers.dev/"
DUMP_CHANNEL = "-1002436700388"
ADMIN_ID = int(os.getenv("ADMIN_ID", "5738579437"))  # Admin ID for new user notifications

# Flask app for monitoring
flask_app = Flask(__name__)
start_time = time.time()

# MongoDB setup
mongo_client = pymongo.MongoClient(
    os.getenv(
        "MONGO_URI",
        "mongodb+srv://Krishna:pss968048@cluster0.4rfuzro.mongodb.net/?retryWrites=true&w=majority"
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


def setup_faq_handlers(bot, problems_collection):
    # Set owner ID directly
    owner_id = 5738579437  # Replace with the actual owner ID if needed

    # Handle FAQ button callback
    @bot.callback_query_handler(func=lambda call: call.data == "faq")
    def handle_faq_button(call):
        chat_id = call.message.chat.id
        bot.send_message(chat_id, "Please describe your problem:")
        bot.register_next_step_handler_by_chat_id(chat_id, save_problem)

    # Save the user problem
    def save_problem(message):
        chat_id = message.chat.id
        problem_text = message.text

        # Save the problem in MongoDB
        problems_collection.insert_one({"chat_id": chat_id, "problem": problem_text})

        # Notify the owner/admin
        bot.send_message(
            owner_id,
            f"🤔 New issue from User {chat_id}:\n\n{problem_text}"
        )
        # Notify the user
        bot.send_message(chat_id, "Thank you! Your problem has been forwarded to the admin.")

    # Admin replies to user problem
    @bot.message_handler(commands=['reply'])
    def handle_reply(message):
        if message.chat.id != owner_id:
            bot.send_message(message.chat.id, "❌ You are not authorized to use this command.")
            return

        try:
            # Command format: /reply <user_id> <reply_message>
            parts = message.text.split(' ', 2)
            user_id = int(parts[1])
            reply_text = parts[2]

            # Ensure the user exists in the problem collection
            problem = problems_collection.find_one({"chat_id": user_id})
            if problem:
                # Send the reply to the user
                bot.send_message(user_id, f"Reply from Admin: {reply_text}")
                # Notify the admin
                bot.send_message(owner_id, f"Your reply has been sent to user {user_id}.")
                # Optionally, delete the problem after reply
                problems_collection.delete_one({"chat_id": user_id})
            else:
                bot.send_message(owner_id, f"User {user_id} has not submitted any problems.")
        except (IndexError, ValueError):
            bot.send_message(owner_id, "❌ Invalid command format. Use: /reply <user_id> <reply_message>.")

    # List all problems submitted by users
    @bot.message_handler(commands=['problems'])
    def list_problems(message):
        if message.chat.id != owner_id:
            bot.send_message(message.chat.id, "❌ You are not authorized to use this command.")
            return

        problems = problems_collection.find()
        if problems.count() == 0:
            bot.send_message(owner_id, "No problems have been submitted yet.")
        else:
            response = "📋 **List of Submitted Problems:**\n\n"
            for problem in problems:
                chat_id = problem['chat_id']
                problem_text = problem['problem']
                response += f"👤 **User ID:** {chat_id}\n📝 **Problem:** {problem_text}\n\n"

            bot.send_message(owner_id, response, parse_mode='Markdown')

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

# Add this function to the provided script
@app.on_message(filters.command("broadcast") & filters.user(5738579437))
async def broadcast_message(client, message):
    """Broadcast a message (text, photo, video, etc.) to all users."""
    if not (message.reply_to_message or len(message.command) > 1):
        await message.reply_text(
            "Please reply to a message or provide text to broadcast.\n\nUsage:\n"
            "/broadcast Your message here\nOR\nReply to any media with /broadcast"
        )
        return

    broadcast_content = message.reply_to_message if message.reply_to_message else message
    users = users_collection.find()
    sent_count = 0
    failed_count = 0

    await message.reply_text("Starting the broadcast...")

    for user in users:
        try:
            user_id = user["user_id"]

            if broadcast_content.photo:
                await client.send_photo(
                    chat_id=user_id,
                    photo=broadcast_content.photo.file_id,
                    caption=broadcast_content.caption or ""
                )
            elif broadcast_content.video:
                await client.send_video(
                    chat_id=user_id,
                    video=broadcast_content.video.file_id,
                    caption=broadcast_content.caption or ""
                )
            elif broadcast_content.document:
                await client.send_document(
                    chat_id=user_id,
                    document=broadcast_content.document.file_id,
                    caption=broadcast_content.caption or ""
                )
            elif broadcast_content.audio:
                await client.send_audio(
                    chat_id=user_id,
                    audio=broadcast_content.audio.file_id,
                    caption=broadcast_content.caption or ""
                )
            elif broadcast_content.voice:
                await client.send_voice(
                    chat_id=user_id,
                    voice=broadcast_content.voice.file_id,
                    caption=broadcast_content.caption or ""
                )
            else:
                await client.send_message(
                    chat_id=user_id,
                    text=broadcast_content.text or "",
                    parse_mode="html"
                )
            sent_count += 1
        except FloodWait as e:
            await sleep(e.value)
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")
            failed_count += 1

    # Notify admin
    await client.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"📢 **Broadcast Completed**:\n\n"
            f"✅ Sent: {sent_count} users\n"
            f"❌ Failed: {failed_count} users\n"
            f"👥 Total: {users_collection.count_documents({})} users"
        )
    )

@app.on_message(filters.command("Rishu"))
async def status_message(client, message):
    user_count = users_collection.count_documents({})
    uptime_minutes = (time.time() - start_time) / 60
    await message.reply_text(f"💫 Bot uptime: {uptime_minutes:.2f} minutes\n\n👥 Total unique users: {user_count}")


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
            thumbnail = "https://envs.sh/L75.jpg"  # Default image if thumbnail is missing

        # Player URL using WebAppInfo
        player_url = f"{TERABOX_API}{video_url}"
        web_app = WebAppInfo(url=player_url)

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("♡ PLAY VIDEO ♡", web_app=web_app)],
            [InlineKeyboardButton('♡ SUPPORT ♡', url='https://t.me/Ur_rishu_143')],
            [InlineKeyboardButton('♡All bots  ♡', url='https://t.me/vip_robotz')]
        ])

        bot_message_text = f"**Dear: 🤩  {message.from_user.mention}\n\nHere's your video:**"

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