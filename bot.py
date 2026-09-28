import httpx
import random
import string
import html
import re
import asyncio
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8604538821:AAEXkRMTPA5jnuyI0YzNaiyeCelBuWhWJe4"
ADMIN_ID = 8604538821

CHANNELS = [
    {
        "name": "📢 Syntax Main Channel",
        "chat_id": "@syntaxredirect",
        "link": "https://t.me/syntaxredirect"
    },
    {
        "name": "💬 Syntax Group Chat",
        "chat_id": "@syntaxkagc",
        "link": "https://t.me/syntaxkagc"
    },
    {
        "name": "⚡ TDLE Updates",
        "chat_id": "@TDLE_robot",
        "link": "https://t.me/TDLE_robot"
    }
]

# Database Setup (Auto-Safe Schema)
conn = sqlite3.connect("bot_vault.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS vault (
        user_id INTEGER,
        email TEXT,
        password TEXT,
        token TEXT,
        PRIMARY KEY (user_id, email)
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'hinglish'
    )
''')
try:
    cursor.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'hinglish'")
except Exception:
    pass
conn.commit()

user_sessions = {}
active_watchers = {}
waiting_for_custom_name = {}

# Premium Owner Information Card
OWNER_CARD = (
    "╭──────────────────────────────────╮\n"
    "│   👑 <b>BOT OWNER & DEVELOPER</b>         │\n"
    "├──────────────────────────────────┤\n"
    "│ 👤 <b>Developer :</b> Rahul                 │\n"
    "│ ⚡ <b>Brand     :</b> Syntax Empire         │\n"
    "│ 🚀 <b>Engine    :</b> Fast Asynchronous Core │\n"
    "│ 💬 <b>Support   :</b> @syntaxkagc           │\n"
    "╰──────────────────────────────────╯"
)

LANGUAGES = {
    "en": {"flag": "🇬🇧 English", "verify_btn": "✅ Verify Membership", "lock": "⚠️ <b>ACCESS RESTRICTED!</b>\nYou must join all official channels:"},
    "hi": {"flag": "🇮🇳 हिन्दी", "verify_btn": "✅ सत्यापित करें", "lock": "⚠️ <b>पहुंच प्रतिबंधित है!</b>\nसभी आधिकारिक चैनलों से जुड़ें:"},
    "hinglish": {"flag": "🇮🇳 Hinglish", "verify_btn": "✅ Verify / Unlock Bot", "lock": "⚠️ <b>ACCESS RESTRICTED!</b>\nBot access karne ke liye official platforms join karna zaroori hai:"}
}

def get_user_lang(user_id):
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if res and res[0] in LANGUAGES:
        return res[0]
    return "hinglish"

def set_user_lang(user_id, lang_code):
    cursor.execute("INSERT INTO users (user_id, lang) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET lang = ?", (user_id, lang_code, lang_code))
    conn.commit()

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_fake_profile():
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Ryan", "David", "Lucas"]
    last_names = ["Vance", "Mercer", "Blackwood", "Sterling", "Kowalski", "Stone", "Sinclair"]
    streets = ["Sunset Blvd", "Broadway Ave", "Kings Road", "Wall Street", "Silicon Ave"]
    cities = [("New York", "NY", "10001"), ("Los Angeles", "CA", "90001"), ("Austin", "TX", "73301")]
    city, state, zip_code = random.choice(cities)
    full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
    address = f"{random.randint(100, 9999)} {random.choice(streets)}, {city}, {state} {zip_code}"
    dob = f"{random.randint(1995, 2004)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
    return full_name, address, dob

async def check_user_membership(bot, user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            pass
    return True

def get_force_join_keyboard(lang_code):
    keyboard = []
    for ch in CHANNELS:
        keyboard.append([InlineKeyboardButton(f"👉 Join {ch['name']}", url=ch["link"])])
    keyboard.append([InlineKeyboardButton(LANGUAGES[lang_code]["verify_btn"], callback_data="verify_join")])
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard():
    keyboard = []
    keys = list(LANGUAGES.keys())
    for i in range(0, len(keys), 2):
        row = [InlineKeyboardButton(LANGUAGES[keys[i]]["flag"], callback_data=f"setlang_{keys[i]}")]
        if i + 1 < len(keys):
            row.append(InlineKeyboardButton(LANGUAGES[keys[i+1]]["flag"], callback_data=f"setlang_{keys[i+1]}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Dashboard", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

# ----------------- UI / KEYBOARD LAYOUTS ----------------- #

def build_status_card(user_id):
    sess = user_sessions.get(user_id)
    if sess:
        email = sess.get("address", "None")
        created = sess.get("created_at", "Just now")
        card = (
            "╭──────────────────────────────────╮\n"
            "│   ⚡ <b>SYNTAX EMPIRE DASHBOARD</b>   │\n"
            "╰──────────────────────────────────╯\n\n"
            f"📧 <b>Current Email:</b>\n<code>{email}</code>\n\n"
            f"🟢 <b>Status:</b> Active & Auto-Listening\n"
            f"⏱️ <b>Allocated:</b> {created}\n"
            "🛡️ <b>Engine:</b> Fast-Track Interceptor"
        )
    else:
        card = (
            "╭──────────────────────────────────╮\n"
            "│   ⚡ <b>SYNTAX EMPIRE DASHBOARD</b>   │\n"
            "╰──────────────────────────────────╯\n\n"
            "📧 <b>Current Email:</b> <i>No active session</i>\n"
            "⚪ <b>Status:</b> Standby / Idle\n"
            "💡 <i>Neeche diye gaye buttons se naya email create karein:</i>"
        )
    return card

def get_main_keyboard(has_session=False):
    if has_session:
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh Inbox", callback_data="check_mail"),
                InlineKeyboardButton("💾 Save to Vault", callback_data="save_vault")
            ],
            [
                InlineKeyboardButton("⚡ Instant Fresh Email", callback_data="gen_mail"),
                InlineKeyboardButton("✏️ Custom Name Email", callback_data="btn_custom_name")
            ],
            [
                InlineKeyboardButton("🌐 Custom Domain", callback_data="list_domains"),
                InlineKeyboardButton("📂 My Vault (Saved)", callback_data="view_vault")
            ],
            [
                InlineKeyboardButton("🛠️ Tools & Settings", callback_data="menu_tools"),
                InlineKeyboardButton("🗑️ Delete Session", callback_data="del_mail")
            ],
            [
                InlineKeyboardButton("👑 Bot Owner Info", callback_data="view_owner"),
                InlineKeyboardButton("👑 Syntax Community", url="https://t.me/syntaxredirect")
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("⚡ Instant Fresh Email", callback_data="gen_mail"),
                InlineKeyboardButton("✏️ Custom Name Email", callback_data="btn_custom_name")
            ],
            [
                InlineKeyboardButton("🌐 Custom Domain", callback_data="list_domains"),
                InlineKeyboardButton("📂 My Vault (Saved)", callback_data="view_vault")
            ],
            [
                InlineKeyboardButton("🛠️ Tools & Settings", callback_data="menu_tools"),
                InlineKeyboardButton("👑 Bot Owner Info", callback_data="view_owner")
            ],
            [
                InlineKeyboardButton("👑 Syntax Community", url="https://t.me/syntaxredirect")
            ]
        ]
    return InlineKeyboardMarkup(keyboard)

def get_tools_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🎭 Fake Profile Generator", callback_data="fake_id"),
            InlineKeyboardButton("🌍 Change Language", callback_data="open_lang_menu")
        ],
        [
            InlineKeyboardButton("🔙 Back to Main Dashboard", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ----------------- BACKGROUND OTP LISTENER ----------------- #

async def watch_inbox(bot, user_id, token, address):
    headers = {"Authorization": f"Bearer {token}"}
    seen_ids = set()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get("https://api.mail.tm/messages", headers=headers)
            for m in res.json().get("hydra:member", []):
                seen_ids.add(m["id"])
    except Exception:
        pass

    while user_sessions.get(user_id, {}).get("address") == address:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get("https://api.mail.tm/messages", headers=headers)
                messages = res.json().get("hydra:member", [])
                
                for msg in messages:
                    msg_id = msg["id"]
                    if msg_id not in seen_ids:
                        seen_ids.add(msg_id)
                        det = await client.get(f"https://api.mail.tm/messages/{msg_id}", headers=headers)
                        mail_data = det.json()
                        sender = html.escape(mail_data.get("from", {}).get("address", "Unknown"))
                        subject = html.escape(mail_data.get("subject", "No Subject"))
                        body = mail_data.get("text", "") or "No text content"
                        
                        otp_match = re.search(r'\b\d{4,8}\b', body)
                        detected_otp = f"\n\n🔑 <b>EXTRACTED OTP / CODE:</b> <code>{otp_match.group(0)}</code>" if otp_match else ""
                        
                        alert_card = (
                            "╭──────────────────────────────────╮\n"
                            "│   🔔 <b>NEW OTP / EMAIL RECEIVED</b>     │\n"
                            "╰──────────────────────────────────╯\n\n"
                            f"👤 <b>From:</b> <code>{sender}</code>\n"
                            f"📌 <b>Subject:</b> <b>{subject}</b>"
                            f"{detected_otp}\n\n"
                            "📝 <b>Message Content:</b>\n"
                            f"<blockquote>{html.escape(body[:1200])}</blockquote>\n\n"
                            "⚡ <i>Auto-intercepted by Syntax Empire Core</i>"
                        )
                        inbox_actions = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Refresh Inbox", callback_data="check_mail")],
                            [InlineKeyboardButton("🔙 Back to Main Dashboard", callback_data="back_main")]
                        ])
                        await bot.send_message(chat_id=user_id, text=alert_card, parse_mode="HTML", reply_markup=inbox_actions)
        except Exception:
            pass
        await asyncio.sleep(4)

async def create_email_account(domain, prefix=None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        if not prefix:
            prefix = f"{random_string()}{random.randint(100,999)}"
        email_address = f"{prefix}@{domain}"
        password = random_string(12)
        reg_resp = await client.post("https://api.mail.tm/accounts", json={"address": email_address, "password": password})
        if reg_resp.status_code != 201:
            return None, None, None
        tok_resp = await client.post("https://api.mail.tm/token", json={"address": email_address, "password": password})
        token = tok_resp.json().get("token")
        return email_address, password, token

# ----------------- TELEGRAM HANDLERS ----------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = get_user_lang(user_id)

    joined = await check_user_membership(context.bot, user_id)
    if not joined:
        lock_text = (
            "╭──────────────────────────────────╮\n"
            "│   🔒 <b>ACCESS RESTRICTED</b>            │\n"
            "╰──────────────────────────────────╯\n\n"
            f"{LANGUAGES[lang_code]['lock']}"
        )
        if update.message:
            await update.message.reply_text(lock_text, reply_markup=get_force_join_keyboard(lang_code), parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.message.edit_text(lock_text, reply_markup=get_force_join_keyboard(lang_code), parse_mode="HTML")
        return

    has_session = user_id in user_sessions
    welcome_text = build_status_card(user_id)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(has_session), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=get_main_keyboard(has_session), parse_mode="HTML")

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if user_id in waiting_for_custom_name and waiting_for_custom_name[user_id]:
        waiting_for_custom_name[user_id] = False
        clean_prefix = re.sub(r'[^a-z0-9]', '', text)

        if len(clean_prefix) < 3:
            await update.message.reply_text("⚠️ <i>Minimum 3 alphanumeric characters required!</i>", reply_markup=get_main_keyboard(user_id in user_sessions), parse_mode="HTML")
            return

        await update.message.reply_text(f"⏳ <i>Allocating `{clean_prefix}` domain...</i>", parse_mode="HTML")
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                dom_resp = await client.get("https://api.mail.tm/domains")
                domains = dom_resp.json().get("hydra:member", [])
                domain = domains[0]["domain"]
                email_addr, pwd, tok = await create_email_account(domain, prefix=clean_prefix)
                if not email_addr:
                    await update.message.reply_text("⚠️ <i>Username already taken! Please choose another.</i>", reply_markup=get_main_keyboard(user_id in user_sessions), parse_mode="HTML")
                    return

                user_sessions[user_id] = {
                    "address": email_addr,
                    "password": pwd,
                    "token": tok,
                    "created_at": datetime.now().strftime("%I:%M %p")
                }
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))

                card = build_status_card(user_id)
                await update.message.reply_text(card, reply_markup=get_main_keyboard(has_session=True), parse_mode="HTML")
            except Exception:
                await update.message.reply_text("❌ <i>Network error. Please try again!</i>", reply_markup=get_main_keyboard(user_id in user_sessions), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    joined = await check_user_membership(context.bot, user_id)
    if not joined and data != "verify_join":
        await query.answer("❌ Join all official channels to unlock!", show_alert=True)
        return

    await query.answer()

    if data == "verify_join":
        await start(update, context)
        return

    if data == "back_main":
        waiting_for_custom_name[user_id] = False
        await start(update, context)
        return

    if data == "menu_tools":
        tools_card = (
            "╭──────────────────────────────────╮\n"
            "│   🛠️ <b>UTILITIES & SETTINGS</b>       │\n"
            "╰──────────────────────────────────╯\n\n"
            "Select an action from the options below:"
        )
        await query.edit_message_text(tools_card, reply_markup=get_tools_keyboard(), parse_mode="HTML")
        return

    if data == "view_owner":
        owner_msg = (
            f"{OWNER_CARD}\n\n"
            "Official project engineered under <b>Syntax Empire</b>.\n"
            "For collaborations, support, or promotions, contact our support community."
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Dashboard", callback_data="back_main")]])
        await query.edit_message_text(owner_msg, reply_markup=back_kb, parse_mode="HTML")
        return

    if data == "open_lang_menu":
        await query.edit_message_text(
            "🌐 <b>SELECT LANGUAGE / भाषा चुनें:</b>",
            reply_markup=get_language_keyboard(),
            parse_mode="HTML"
        )
        return

    elif data.startswith("setlang_"):
        chosen_lang = data.replace("setlang_", "")
        set_user_lang(user_id, chosen_lang)
        await query.answer(f"Language set to {LANGUAGES[chosen_lang]['flag']}!")
        await start(update, context)
        return

    elif data == "btn_custom_name":
        waiting_for_custom_name[user_id] = True
        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="back_main")]])
        await query.edit_message_text(
            "╭──────────────────────────────────╮\n"
            "│   ✏️ <b>CUSTOM NAME EMAIL</b>           │\n"
            "╰──────────────────────────────────╯\n\n"
            "Apna manpasand username chat me type karke bhejein:\n"
            "<i>(Example: <code>syntaxpro</code>, <code>rahul99</code>)</i>",
            reply_markup=cancel_kb,
            parse_mode="HTML"
        )
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        if data == "list_domains":
            try:
                dom_resp = await client.get("https://api.mail.tm/domains")
                domains = dom_resp.json().get("hydra:member", [])
                buttons = []
                for d in domains[:6]:
                    dom_name = d["domain"]
                    buttons.append([InlineKeyboardButton(f"🌐 @{dom_name}", callback_data=f"seldom_{dom_name}")])
                buttons.append([InlineKeyboardButton("🔙 Back to Main Dashboard", callback_data="back_main")])
                await query.edit_message_text(
                    "╭──────────────────────────────────╮\n"
                    "│   🌐 <b>CHOOSE PREFERRED DOMAIN</b>    │\n"
                    "╰──────────────────────────────────╯\n\n"
                    "Select an active domain from the list:",
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="HTML"
                )
            except Exception:
                await query.edit_message_text("❌ <i>Error fetching domain list.</i>", reply_markup=get_main_keyboard(user_id in user_sessions), parse_mode="HTML")

        elif data.startswith("seldom_"):
            chosen_domain = data.replace("seldom_", "")
            email_addr, pwd, tok = await create_email_account(chosen_domain)
            if not email_addr:
                await query.edit_message_text("⚠️ <i>Domain busy. Please select another!</i>", reply_markup=get_main_keyboard(user_id in user_sessions), parse_mode="HTML")
                return

            user_sessions[user_id] = {
                "address": email_addr,
                "password": pwd,
                "token": tok,
                "created_at": datetime.now().strftime("%I:%M %p")
            }
            if user_id in active_watchers:
                active_watchers[user_id].cancel()
            active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))

            card = build_status_card(user_id)
            await query.edit_message_text(card, reply_markup=get_main_keyboard(has_session=True), parse_mode="HTML")

        elif data == "gen_mail":
            try:
                dom_resp = await client.get("https://api.mail.tm/domains")
                domains = dom_resp.json().get("hydra:member", [])
                domain = domains[0]["domain"]
                email_addr, pwd, tok = await create_email_account(domain)

                user_sessions[user_id] = {
                    "address": email_addr,
                    "password": pwd,
                    "token": tok,
                    "created_at": datetime.now().strftime("%I:%M %p")
                }
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))

                card = build_status_card(user_id)
                await query.edit_message_text(card, reply_markup=get_main_keyboard(has_session=True), parse_mode="HTML")
            except Exception:
                await query.edit_message_text("❌ <i>Connection timeout. Please retry!</i>", reply_markup=get_main_keyboard(user_id in user_sessions), parse_mode="HTML")

        elif data == "save_vault":
            if user_id not in user_sessions:
                await query.answer("⚠️ Generate an email first!", show_alert=True)
                return
            sess = user_sessions[user_id]
            cursor.execute("INSERT OR REPLACE INTO vault (user_id, email, password, token) VALUES (?, ?, ?, ?)",
                           (user_id, sess["address"], sess["password"], sess["token"]))
            conn.commit()
            await query.answer("💾 Email safely stored in your Vault!", show_alert=True)

        elif data == "view_vault":
            cursor.execute("SELECT email FROM vault WHERE user_id = ?", (user_id,))
            saved = cursor.fetchall()
            if not saved:
                await query.answer("📂 Vault is empty! Save an email first.", show_alert=True)
                return
            buttons = []
            for item in saved[:5]:
                buttons.append([InlineKeyboardButton(f"📬 {item[0][:22]}", callback_data=f"restore_{item[0]}")])
            buttons.append([InlineKeyboardButton("🔙 Back to Main Dashboard", callback_data="back_main")])
            await query.edit_message_text(
                "╭──────────────────────────────────╮\n"
                "│   📂 <b>SAVED EMAIL VAULT</b>           │\n"
                "╰──────────────────────────────────╯\n\n"
                "Select a saved email to restore & activate inbox listening:",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML"
            )

        elif data.startswith("restore_"):
            target_email = data.replace("restore_", "")
            cursor.execute("SELECT email, password, token FROM vault WHERE user_id = ? AND email = ?", (user_id, target_email))
            res = cursor.fetchone()
            if res:
                email_addr, pwd, tok = res
                user_sessions[user_id] = {
                    "address": email_addr,
                    "password": pwd,
                    "token": tok,
                    "created_at": datetime.now().strftime("%I:%M %p")
                }
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))

                card = build_status_card(user_id)
                await query.edit_message_text(card, reply_markup=get_main_keyboard(has_session=True), parse_mode="HTML")

        elif data == "fake_id":
            name, address, dob = generate_fake_profile()
            profile_card = (
                "╭──────────────────────────────────╮\n"
                "│   🎭 <b>MOCK IDENTITY PROFILE</b>       │\n"
                "╰──────────────────────────────────╯\n\n"
                f"👤 <b>Full Name :</b> <code>{name}</code>\n"
                f"🎂 <b>Birthdate :</b> <code>{dob}</code>\n"
                f"🏠 <b>US Address:</b> <code>{address}</code>\n\n"
                "💡 <i>Tap any detail to copy directly.</i>"
            )
            back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Tools", callback_data="menu_tools")]])
            await query.edit_message_text(profile_card, reply_markup=back_kb, parse_mode="HTML")

        elif data == "check_mail":
            if user_id not in user_sessions:
                await query.answer("⚠️ Pehle email create karein!", show_alert=True)
                return
            token = user_sessions[user_id]["token"]
            headers = {"Authorization": f"Bearer {token}"}
            try:
                msg_resp = await client.get("https://api.mail.tm/messages", headers=headers)
                messages = msg_resp.json().get("hydra:member", [])
                if not messages:
                    await query.answer("📭 Inbox empty! No incoming messages yet.", show_alert=True)
                    return
                latest_id = messages[0]["id"]
                detail_resp = await client.get(f"https://api.mail.tm/messages/{latest_id}", headers=headers)
                mail_data = detail_resp.json()
                sender = html.escape(mail_data.get("from", {}).get("address", "Unknown"))
                subject = html.escape(mail_data.get("subject", "No Subject"))
                body_text = mail_data.get("text", "") or "No text content"
                otp_match = re.search(r'\b\d{4,8}\b', body_text)
                detected_otp = f"\n\n🔑 <b>EXTRACTED OTP / CODE:</b> <code>{otp_match.group(0)}</code>" if otp_match else ""
                
                inbox_view = (
                    "╭──────────────────────────────────╮\n"
                    "│   📨 <b>LATEST INBOX MESSAGE</b>         │\n"
                    "╰──────────────────────────────────╯\n\n"
                    f"👤 <b>From:</b> <code>{sender}</code>\n"
                    f"📌 <b>Subject:</b> <b>{subject}</b>"
                    f"{detected_otp}\n\n"
                    "📝 <b>Message Content:</b>\n"
                    f"<blockquote>{html.escape(body_text[:1200])}</blockquote>"
                )
                await query.message.reply_text(inbox_view, reply_markup=get_main_keyboard(has_session=True), parse_mode="HTML")
            except Exception:
                await query.answer("❌ Error reading inbox.", show_alert=True)

        elif data == "del_mail":
            if user_id in user_sessions:
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                del user_sessions[user_id]
                await query.answer("🗑️ Session closed!", show_alert=True)
                card = build_status_card(user_id)
                await query.edit_message_text(card, reply_markup=get_main_keyboard(has_session=False), parse_mode="HTML")

# ----------------- SERVER INITIALIZATION ----------------- #

if __name__ == '__main__':
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .read_timeout(35)
        .write_timeout(35)
        .connect_timeout(35)
        .pool_timeout(35)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    print("Syntax Empire Commercial-Grade Core is Live...")
    app.run_polling()
