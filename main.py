# Don't Remove Credit Tg - @Whosekirito
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @Whosekirito

import os
import asyncio
import threading
import datetime
import time
import traceback
import motor.motor_asyncio
from flask import Flask
from pyrogram import Client, filters, enums
from pyrogram.errors import (
    FloodWait, UserIsBlocked, InputUserDeactivated, UserAlreadyParticipant, 
    InviteHashExpired, UsernameNotOccupied, ApiIdInvalid, PhoneNumberInvalid,
    PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid,
    PeerIdInvalid
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from asyncio.exceptions import TimeoutError

# Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7807552195:AAGzBSvBoN8HNSLUy5QRX5yT6bJWUyKDAiM")
API_ID = int(os.environ.get("API_ID", "23572045"))
API_HASH = os.environ.get("API_HASH", "6bf81dff6563e3f1fb3c7d23a6872291")
ADMINS = int(os.environ.get("ADMINS", "7577853954"))
DB_URI = os.environ.get("DB_URI", "mongodb+srv://sumitsajwan135:gameno01@cluster0.ja0i0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = os.environ.get("DB_NAME", "vjsavecontentbot")
ERROR_MESSAGE = bool(os.environ.get('ERROR_MESSAGE', True))

# Flask App for Render
app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <html>
        <head><title>Bot Server</title></head>
        <body>
            <h1>🤖 Telegram Bot Server</h1>
            <p>✅ Server is running</p>
            <p>🚀 Bot is active</p>
        </body>
    </html>
    '''

@app.route('/health')
def health():
    return {'status': 'healthy'}

# Database Class
class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.sess_col = self.db.session
        self.sub_col = self.db.subscriptions

    async def add_user(self, user_id, name):
        user = {"user_id": user_id, "name": name}
        await self.col.insert_one(user)

    async def total_users_count(self):
        return await self.col.count_documents({})

    async def is_user_exist(self, user_id):
        user = await self.col.find_one({"user_id": user_id})
        return bool(user)

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({"user_id": user_id})

    async def get_session(self, user_id):
        data = await self.sess_col.find_one({"user_id": user_id})
        return data.get("session") if data else None

    async def set_session(self, user_id, session):
        await self.sess_col.update_one(
            {"user_id": user_id},
            {"$set": {"session": session}},
            upsert=True
        )

    async def get_user_subscription(self, user_id):
        data = await self.sub_col.find_one({"user_id": user_id})
        return data.get("subscription") if data else None

    async def set_user_subscription(self, user_id, subscription_data):
        await self.sub_col.update_one(
            {"user_id": user_id},
            {"$set": {"subscription": subscription_data}},
            upsert=True
        )

# Initialize Database
db = Database(DB_URI, DB_NAME)

# Constants
SESSION_STRING_SIZE = 351
HELP_TXT = """<b>🤖 SAVE CONTENT BOT - HELP

🔐 PRIVATE CHANNELS:
Send: https://t.me/c/1234567890/100

📦 BATCH DOWNLOADS:
Send: https://t.me/channelname/1001-1010

🎮 COMMANDS:
🔑 /login - Login with Telegram
🚪 /logout - Logout 
❌ /cancel - Cancel downloads
📊 /mysub - Check subscription

⚠️ NOTES:
✅ Login required for restricted content
✅ Premium users get unlimited downloads

💬 Support: @Whosekirito</b>"""

# Plans Configuration
PLANS = {
    "basic": {"name": "🌟 Basic Plan", "price": "$2.99", "duration": 30},
    "premium": {"name": "💎 Premium Plan", "price": "$5.99", "duration": 30},
    "pro": {"name": "⚡ Pro Plan", "price": "$8.99", "duration": 30},
    "lifetime": {"name": "🚀 Lifetime Plan", "price": "$15.99", "duration": 36500}
}

# Bot Class
class Bot(Client):
    def __init__(self):
        super().__init__(
            "techvj_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=200,
            sleep_threshold=5
        )

    async def start(self):
        await super().start()
        print('Bot Started Powered By @Whosekirito')

    async def stop(self, *args):
        await super().stop()
        print('Bot Stopped')

# Global Variables
class batch_temp:
    IS_BATCH = {}

# Helper Functions
async def downstatus(client, statusfile, message, chat):
    while True:
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(3)
    
    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Downloaded:** **{txt}**")
            await asyncio.sleep(2)
        except:
            await asyncio.sleep(1)

async def upstatus(client, statusfile, message, chat):
    while True:
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(3)
    
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Uploaded:** **{txt}**")
            await asyncio.sleep(2)
        except:
            await asyncio.sleep(1)

def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")

def get_message_type(msg):
    try: msg.document.file_id; return "Document"
    except: pass
    try: msg.video.file_id; return "Video"
    except: pass
    try: msg.animation.file_id; return "Animation"
    except: pass
    try: msg.sticker.file_id; return "Sticker"
    except: pass
    try: msg.voice.file_id; return "Voice"
    except: pass
    try: msg.audio.file_id; return "Audio"
    except: pass
    try: msg.photo.file_id; return "Photo"
    except: pass
    try: msg.text; return "Text"
    except: pass

# Initialize Bot
bot = Bot()

# Start Command
@bot.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)

    user_data = await db.get_user_subscription(message.from_user.id)
    subscription_status = "🔓 Premium User" if user_data and user_data.get('is_premium') else "🔒 Free User"

    buttons = [[
        InlineKeyboardButton("💎 View Plans", callback_data="show_plans"),
        InlineKeyboardButton("📊 My Status", callback_data="my_status")
    ],[
        InlineKeyboardButton("❣️ Developer", url = "https://t.me/whosekirito")
    ],[
        InlineKeyboardButton('🔍 Support', url='https://t.me/AACBotSupport'),
        InlineKeyboardButton('🤖 Updates', url='https://t.me/kirito_bots')
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)

    start_text = f"""<b>🌟 Welcome {message.from_user.mention}! 

🤖 Save Restricted Content Bot
✨ Download restricted content easily!

📊 Status: {subscription_status}

🚀 Features:
• Download from Private Channels
• Batch Download Support
• High Speed Downloads

💡 Start: /login to authenticate
📚 Help: /help command</b>"""

    await client.send_photo(
        chat_id=message.chat.id,
        photo="https://graph.org/file/2812e2626acfdc47f21c9-95414f2c2838c627ee.jpg",
        caption=start_text,
        reply_markup=reply_markup,
        reply_to_message_id=message.id
    )

# Help Command
@bot.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    await client.send_message(chat_id=message.chat.id, text=HELP_TXT)

# Login Command
@bot.on_message(filters.private & ~filters.forwarded & filters.command(["login"]))
async def login_command(bot_client: Client, message: Message):
    user_data = await db.get_session(message.from_user.id)
    if user_data is not None:
        await message.reply("**Already logged in. First /logout then login.**")
        return 
    
    user_id = int(message.from_user.id)
    phone_number_msg = await bot_client.ask(chat_id=user_id, text="<b>Send your phone number with country code</b>\n<b>Example:</b> <code>+1234567890</code>")
    if phone_number_msg.text=='/cancel':
        return await phone_number_msg.reply('<b>Process cancelled!</b>')
    
    phone_number = phone_number_msg.text
    client = Client(":memory:", API_ID, API_HASH)
    await client.connect()
    await phone_number_msg.reply("Sending OTP...")
    
    try:
        code = await client.send_code(phone_number)
        phone_code_msg = await bot_client.ask(user_id, "Check for OTP in Telegram. Send OTP as: `1 2 3 4 5`\n\n**Enter /cancel to cancel**", filters=filters.text, timeout=600)
    except PhoneNumberInvalid:
        await phone_number_msg.reply('Invalid phone number.')
        return
    
    if phone_code_msg.text=='/cancel':
        return await phone_code_msg.reply('<b>Process cancelled!</b>')
    
    try:
        phone_code = phone_code_msg.text.replace(" ", "")
        await client.sign_in(phone_number, code.phone_code_hash, phone_code)
    except PhoneCodeInvalid:
        await phone_code_msg.reply('Invalid OTP.')
        return
    except SessionPasswordNeeded:
        two_step_msg = await bot_client.ask(user_id, '**Two-step verification enabled. Enter password:**', filters=filters.text, timeout=300)
        if two_step_msg.text=='/cancel':
            return await two_step_msg.reply('<b>Process cancelled!</b>')
        try:
            await client.check_password(password=two_step_msg.text)
        except PasswordHashInvalid:
            await two_step_msg.reply('Invalid password.')
            return
    
    string_session = await client.export_session_string()
    await client.disconnect()
    
    if len(string_session) < SESSION_STRING_SIZE:
        return await message.reply('<b>Invalid session string</b>')
    
    try:
        await db.set_session(message.from_user.id, session=string_session)
        await bot_client.send_message(message.from_user.id, "<b>Login successful!</b>")
    except Exception as e:
        return await message.reply_text(f"<b>Login error:</b> `{e}`")

# Logout Command
@bot.on_message(filters.private & ~filters.forwarded & filters.command(["logout"]))
async def logout_command(client, message):
    user_data = await db.get_session(message.from_user.id)  
    if user_data is None:
        return 
    await db.set_session(message.from_user.id, session=None)  
    await message.reply("**Logout successful**")

# Cancel Command
@bot.on_message(filters.command(["cancel"]))
async def cancel_command(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in batch_temp.IS_BATCH and not batch_temp.IS_BATCH[user_id]:
        batch_temp.IS_BATCH[user_id] = True
        await client.send_message(chat_id=message.chat.id, text="**✅ Batch cancelled!**")
    else:
        await client.send_message(chat_id=message.chat.id, text="**No active process found.**")

# Check Subscription Command
@bot.on_message(filters.command(["mysub"]))
async def check_subscription(client: Client, message: Message):
    user_data = await db.get_user_subscription(message.from_user.id)
    if user_data and user_data.get('is_premium'):
        await message.reply(f"""<b>🎉 Subscription Active
💎 Plan: {user_data.get('plan_name', 'Premium')}
📅 Expires: {user_data.get('expiry_date', 'Never')}</b>""")
    else:
        await message.reply("""<b>🔒 Free User
💎 Upgrade to Premium for unlimited downloads!
Use /start to view plans</b>""")

# Broadcast Command (Admin only)
@bot.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_command(bot_client, message):
    users = await db.get_all_users()
    b_msg = message.reply_to_message
    if not b_msg:
        return await message.reply_text("**Reply to a message to broadcast**")
    
    sts = await message.reply_text('Broadcasting...')
    total_users = await db.total_users_count()
    success = failed = 0
    
    async for user in users:
        if 'user_id' in user:
            try:
                await b_msg.copy(chat_id=user['user_id'])
                success += 1
            except:
                failed += 1
                await db.delete_user(int(user['user_id']))
    
    await sts.edit(f"Broadcast complete!\nSuccess: {success}\nFailed: {failed}")

# Give Subscription Command (Admin only)
@bot.on_message(filters.command(["givsub"]) & filters.user(ADMINS))
async def give_subscription(client: Client, message: Message):
    try:
        if len(message.command) < 4:
            await message.reply("**Usage:** /givsub [user_id] [plan] [days]\n**Plans:** basic, premium, pro, lifetime")
            return
        
        user_id = int(message.command[1])
        plan_name = message.command[2].lower()
        days = int(message.command[3])
        
        if plan_name not in PLANS:
            await message.reply("Invalid plan!")
            return
        
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=days)
        expiry_str = expiry_date.strftime("%d-%m-%Y") if days < 36500 else "Never"
        
        await db.set_user_subscription(user_id, {
            'is_premium': True,
            'plan_name': PLANS[plan_name]['name'],
            'expiry_date': expiry_str
        })
        
        await message.reply(f"**✅ Subscription granted!**\nUser: {user_id}\nPlan: {PLANS[plan_name]['name']}")
        
        try:
            await client.send_message(user_id, f"**🎉 You got {PLANS[plan_name]['name']}!\nExpires: {expiry_str}**")
        except:
            pass
            
    except Exception as e:
        await message.reply(f"Error: {str(e)}")

# Main Content Handler
@bot.on_message(filters.text & filters.private)
async def save_content(client: Client, message: Message):
    if "https://t.me/" not in message.text:
        return
        
    if batch_temp.IS_BATCH.get(message.from_user.id) == False:
        return await message.reply_text("**Task in progress. Use /cancel to stop.**")
    
    datas = message.text.split("/")
    temp = datas[-1].replace("?single","").split("-")
    fromID = int(temp[0].strip())
    try:
        toID = int(temp[1].strip())
    except:
        toID = fromID
    
    batch_temp.IS_BATCH[message.from_user.id] = False
    
    for msgid in range(fromID, toID+1):
        if batch_temp.IS_BATCH.get(message.from_user.id): 
            break
            
        user_data = await db.get_session(message.from_user.id)
        if user_data is None:
            await message.reply("**Login required. Use /login first.**")
            batch_temp.IS_BATCH[message.from_user.id] = True
            return
        
        try:
            acc = Client("saverestricted", session_string=user_data, api_hash=API_HASH, api_id=API_ID)
            await acc.connect()
        except:
            batch_temp.IS_BATCH[message.from_user.id] = True
            return await message.reply("**Session expired. /logout then /login again.**")

        if "https://t.me/c/" in message.text:
            chatid = int("-100" + datas[4])
            try:
                await handle_private(client, acc, message, chatid, msgid)
            except Exception as e:
                if ERROR_MESSAGE:
                    await client.send_message(message.chat.id, f"Error: {e}")
        else:
            username = datas[3]
            try:
                msg = await client.get_messages(username, msgid)
                await client.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
            except:
                try:    
                    await handle_private(client, acc, message, username, msgid)               
                except Exception as e:
                    if ERROR_MESSAGE:
                        await client.send_message(message.chat.id, f"Error: {e}")
        
        await asyncio.sleep(3)
    
    batch_temp.IS_BATCH[message.from_user.id] = True

# Handle Private Content
async def handle_private(client: Client, acc, message: Message, chatid, msgid: int):
    msg: Message = await acc.get_messages(chatid, msgid)
    if msg.empty: 
        return 
    
    msg_type = get_message_type(msg)
    if not msg_type: 
        return 
    
    chat = message.chat.id
    if batch_temp.IS_BATCH.get(message.from_user.id): 
        return 
    
    if "Text" == msg_type:
        try:
            await client.send_message(chat, msg.text, entities=msg.entities, reply_to_message_id=message.id)
            return 
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}")
            return 

    smsg = await client.send_message(message.chat.id, '**Downloading**', reply_to_message_id=message.id)
    asyncio.create_task(downstatus(client, f'{message.id}downstatus.txt', smsg, chat))
    
    try:
        file = await acc.download_media(msg, progress=progress, progress_args=[message,"down"])
        os.remove(f'{message.id}downstatus.txt')
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error: {e}")
        return await smsg.delete()
    
    if batch_temp.IS_BATCH.get(message.from_user.id): 
        return 
    
    asyncio.create_task(upstatus(client, f'{message.id}upstatus.txt', smsg, chat))
    caption = msg.caption if msg.caption else None
    
    try:
        if "Document" == msg_type:
            await client.send_document(chat, file, caption=caption, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])
        elif "Video" == msg_type:
            await client.send_video(chat, file, caption=caption, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])
        elif "Photo" == msg_type:
            await client.send_photo(chat, file, caption=caption, reply_to_message_id=message.id)
        elif "Audio" == msg_type:
            await client.send_audio(chat, file, caption=caption, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])
        elif "Voice" == msg_type:
            await client.send_voice(chat, file, caption=caption, reply_to_message_id=message.id, progress=progress, progress_args=[message,"up"])
        elif "Animation" == msg_type:
            await client.send_animation(chat, file, reply_to_message_id=message.id)
        elif "Sticker" == msg_type:
            await client.send_sticker(chat, file, reply_to_message_id=message.id)
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error: {e}")

    if os.path.exists(f'{message.id}upstatus.txt'): 
        os.remove(f'{message.id}upstatus.txt')
        os.remove(file)
    await client.delete_messages(message.chat.id,[smsg.id])

# Callback Query Handlers
@bot.on_callback_query(filters.regex("show_plans"))
async def show_plans(client: Client, callback_query: CallbackQuery):
    buttons = []
    for plan_id, plan in PLANS.items():
        buttons.append([InlineKeyboardButton(f"{plan['name']} - {plan['price']}", callback_data=f"plan_{plan_id}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    
    plans_text = """<b>💎 Choose Your Plan

🌟 Basic - $2.99/month
💎 Premium - $5.99/month  
⚡ Pro - $8.99/month
🚀 Lifetime - $15.99 (One-time)

Contact @Whosekirito to purchase</b>"""
    
    await callback_query.edit_message_caption(caption=plans_text, reply_markup=InlineKeyboardMarkup(buttons))

@bot.on_callback_query(filters.regex("my_status"))
async def my_status(client: Client, callback_query: CallbackQuery):
    user_data = await db.get_user_subscription(callback_query.from_user.id)
    
    if user_data and user_data.get('is_premium'):
        status_text = f"""<b>🎉 Premium User
Plan: {user_data.get('plan_name', 'Premium')}
Expires: {user_data.get('expiry_date', 'Never')}</b>"""
    else:
        status_text = """<b>🔒 Free User
Upgrade to Premium for unlimited downloads!</b>"""
    
    buttons = [
        [InlineKeyboardButton("💎 Upgrade", callback_data="show_plans")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    await callback_query.edit_message_caption(caption=status_text, reply_markup=InlineKeyboardMarkup(buttons))

@bot.on_callback_query(filters.regex("back_to_main"))
async def back_to_main(client: Client, callback_query: CallbackQuery):
    user_data = await db.get_user_subscription(callback_query.from_user.id)
    subscription_status = "🔓 Premium User" if user_data and user_data.get('is_premium') else "🔒 Free User"
    
    buttons = [[
        InlineKeyboardButton("💎 View Plans", callback_data="show_plans"),
        InlineKeyboardButton("📊 My Status", callback_data="my_status")
    ],[
        InlineKeyboardButton("❣️ Developer", url = "https://t.me/whosekirito")
    ]]
    
    start_text = f"""<b>🌟 Welcome {callback_query.from_user.mention}! 

🤖 Save Restricted Content Bot
Status: {subscription_status}

🚀 Features:
• Download from Private Channels
• Batch Download Support
• High Speed Downloads</b>"""
    
    await callback_query.edit_message_caption(caption=start_text, reply_markup=InlineKeyboardMarkup(buttons))

# Flask server function
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

# Main function
def main():
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start the bot
    bot.run()

if __name__ == "__main__":
    main()
