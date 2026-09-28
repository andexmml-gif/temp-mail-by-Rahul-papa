import httpx
import random
import string
import html
import re
import asyncio
import sqlite3
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

# Database Setup (Auto-Safe)
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

# Developer & Owner ASCII Badge Box
OWNER_CARD = (
    "╔════════════════════════╗\n"
    "   👑 <b>BOT OWNER DETAILS</b> 👑\n"
    "╠════════════════════════╣\n"
    "  👤 <b>Developer :</b> Rahul\n"
    "  ⚡ <b>Brand     :</b> Syntax Empire\n"
    "  🚀 <b>Engine    :</b> Fast Asynchronous Core\n"
    "  💬 <b>Support   :</b> @syntaxkagc\n"
    "╚════════════════════════╝"
)

LANGUAGES = {
    "en": {
        "flag": "🇬🇧 English",
        "gen_btn": "⚡ Instant Fresh Email",
        "custom_btn": "✏️ Custom Name Email",
        "domain_btn": "🌐 Custom Domain",
        "save_btn": "💾 Save to Vault",
        "vault_btn": "📁 My Vault (Saved)",
        "fake_btn": "🎭 Fake Profile Gen",
        "refresh_btn": "📬 Manual Refresh",
        "del_btn": "🗑 Delete Session",
        "owner_btn": "👑 Bot Owner Info",
        "lang_btn": "🌐 Change Language",
        "lock": "⚠️ <b>ACCESS RESTRICTED!</b>\nYou must join all official channels:",
        "verify_btn": "✅ Verify Membership"
    },
    "hi": {
        "flag": "🇮🇳 हिन्दी",
        "gen_btn": "⚡ नया ईमेल बनाएं",
        "custom_btn": "✏️ मनपसंद नाम का ईमेल",
        "domain_btn": "🌐 डोमेन बदलें",
        "save_btn": "💾 ईमेल वॉल्ट में सेव करें",
        "vault_btn": "📁 सेव किए गए ईमेल",
        "fake_btn": "🎭 फेक प्रोफ़ाइल बनाएं",
        "refresh_btn": "📬 इनबॉक्स चेक करें",
        "del_btn": "🗑 सेशन डिलीट करें",
        "owner_btn": "👑 ओनर की जानकारी",
        "lang_btn": "🌐 भाषा बदलें",
        "lock": "⚠️ <b>पहुंच प्रतिबंधित है!</b>\nसभी चैनल्स से जुड़ें:",
        "verify_btn": "✅ सत्यापित करें"
    },
    "hinglish": {
        "flag": "🇮🇳 Hinglish",
        "gen_btn": "⚡ Instant Fresh Email",
        "custom_btn": "✏️ Custom Name Email",
        "domain_btn": "🌐 Custom Domain",
        "save_btn": "💾 Save to Vault",
        "vault_btn": "📁 My Vault (Saved)",
        "fake_btn": "🎭 Fake Profile Generator",
        "refresh_btn": "📬 Manual Refresh",
        "del_btn": "🗑 Delete Session",
        "owner_btn": "👑 Bot Owner Info",
        "lang_btn": "🌐 Change Language",
        "lock": "⚠️ <b>ACCESS RESTRICTED!</b>\nOfficial channels join karna zaroori hai:",
        "verify_btn": "✅ Verify / Unlock Bot"
    }
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
    return InlineKeyboardMarkup(keyboard)

# MAIN DASHBOARD KEYBOARD WITH PROMINENT OWNER BUTTON
def get_main_keyboard(lang_code):
    l = LANGUAGES[lang_code]
    keyboard = [
        [
            InlineKeyboardButton(l["gen_btn"], callback_data="gen_mail"),
            InlineKeyboardButton(l["custom_btn"], callback_data="btn_custom_name")
        ],
        [
            InlineKeyboardButton(l["domain_btn"], callback_data="list_domains"),
            InlineKeyboardButton(l["save_btn"], callback_data="save_vault")
        ],
        [
            InlineKeyboardButton(l["vault_btn"], callback_data="view_vault"),
            InlineKeyboardButton(l["fake_btn"], callback_data="fake_id")
        ],
        [
            InlineKeyboardButton(l["refresh_btn"], callback_data="check_mail"),
            InlineKeyboardButton(l["del_btn"], callback_data="del_mail")
        ],
        [
            InlineKeyboardButton(l["owner_btn"], callback_data="view_owner")
        ],
        [
            InlineKeyboardButton(l["lang_btn"], callback_data="open_lang_menu"),
            InlineKeyboardButton("👑 Syntax Community", url="https://t.me/syntaxredirect")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

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
                        detected_otp = f"\n\n🔑 <b>EXTRACTED OTP/CODE:</b> <code>{otp_match.group(0)}</code>" if otp_match else ""
                        
                        alert_card = (
                            "╔════════════════════════╗\n"
                            "   🔔 <b>LIVE INCOMING OTP ALERT!</b> 🔔\n"
                            "╚════════════════════════╝\n\n"
                            f"👤 <b>From:</b> <code>{sender}</code>\n"
                            f"📌 <b>Subject:</b> <b>{subject}</b>"
                            f"{detected_otp}\n\n"
                            "📝 <b>Body:</b>\n"
                            f"<blockquote>{html.escape(body[:1200])}</blockquote>\n\n"
                            "⚡ <i>Auto-intercepted by Syntax Empire Core</i>"
                        )
                        lang_code = get_user_lang(user_id)
                        await bot.send_message(chat_id=user_id, text=alert_card, parse_mode="HTML", reply_markup=get_main_keyboard(lang_code))
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = get_user_lang(user_id)

    joined = await check_user_membership(context.bot, user_id)
    if not joined:
        lock_text = (
            "╔════════════════════════╗\n"
            "   🔒 <b>ACCESS RESTRICTED!</b> 🔒\n"
            "╚════════════════════════╝\n\n"
            f"{LANGUAGES[lang_code]['lock']}"
        )
        if update.message:
            await update.message.reply_text(lock_text, reply_markup=get_force_join_keyboard(lang_code), parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.message.edit_text(lock_text, reply_markup=get_force_join_keyboard(lang_code), parse_mode="HTML")
        return

    welcome_text = (
        f"{OWNER_CARD}\n\n"
        "⚡ <b>Next-Gen High-Speed Disposable Temp-Mail Engine</b>\n\n"
        "👇 <i>Neeche diye gaye buttons se operate karein:</i>"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(lang_code), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=get_main_keyboard(lang_code), parse_mode="HTML")

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = get_user_lang(user_id)
    text = update.message.text.strip().lower()

    if user_id in waiting_for_custom_name and waiting_for_custom_name[user_id]:
        waiting_for_custom_name[user_id] = False
        clean_prefix = re.sub(r'[^a-z0-9]', '', text)

        if len(clean_prefix) < 3:
            await update.message.reply_text("⚠️ Minimum 3 characters required!", reply_markup=get_main_keyboard(lang_code))
            return

        await update.message.reply_text(f"⏳ <i>Allocating `{clean_prefix}` email...</i>", parse_mode="HTML")
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                dom_resp = await client.get("https://api.mail.tm/domains")
                domains = dom_resp.json().get("hydra:member", [])
                domain = domains[0]["domain"]
                email_addr, pwd, tok = await create_email_account(domain, prefix=clean_prefix)
                if not email_addr:
                    await update.message.reply_text("⚠️ Name already taken! Try another.", reply_markup=get_main_keyboard(lang_code))
                    return

                user_sessions[user_id] = {"address": email_addr, "password": pwd, "token": tok}
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))

                mail_card = (
                    "╔════════════════════════╗\n"
                    "   👑 <b>CUSTOM EMAIL READY!</b>\n"
                    "╚════════════════════════╝\n\n"
                    f"📧 <b>Your Custom Email:</b>\n<code>{email_addr}</code>\n\n"
                    "🎯 <b>Status:</b> 🟢 <b>Auto-Listening Active!</b>"
                )
                await update.message.reply_text(mail_card, reply_markup=get_main_keyboard(lang_code), parse_mode="HTML")
            except Exception:
                await update.message.reply_text("❌ Network timeout!", reply_markup=get_main_keyboard(lang_code))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    lang_code = get_user_lang(user_id)

    joined = await check_user_membership(context.bot, user_id)
    if not joined and data != "verify_join":
        await query.answer("❌ Please join required channels!", show_alert=True)
        return

    await query.answer()

    if data == "verify_join":
        await start(update, context)
        return

    # Direct Click on Owner Info Button
    if data == "view_owner":
        owner_details_msg = (
            f"{OWNER_CARD}\n\n"
            "Official Telegram project engineered by <b>Syntax Empire</b>.\n"
            "For inquiries, custom bot development, or promotions, reach out to our community!"
        )
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Dashboard", callback_data="back_main")]])
        await query.edit_message_text(owner_details_msg, reply_markup=back_kb, parse_mode="HTML")
        return

    if data == "open_lang_menu":
        await query.edit_message_text(
            "🌐 <b>SELECT YOUR LANGUAGE / अपनी भाषा चुनें:</b>",
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
            "✏️ <b>CUSTOM NAME:</b>\n\nSend your desired name in chat (e.g. <code>syntaxvip99</code>):",
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
                buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
                await query.edit_message_text("🌐 <b>AVAILABLE DOMAINS:</b>", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
            except Exception:
                await query.edit_message_text("❌ Domain fetch error", reply_markup=get_main_keyboard(lang_code))

        elif data.startswith("seldom_"):
            chosen_domain = data.replace("seldom_", "")
            email_addr, pwd, tok = await create_email_account(chosen_domain)
            if not email_addr:
                await query.edit_message_text("⚠️ Rate limit, try another domain!", reply_markup=get_main_keyboard(lang_code))
                return

            user_sessions[user_id] = {"address": email_addr, "password": pwd, "token": tok}
            if user_id in active_watchers:
                active_watchers[user_id].cancel()
            active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))

            await query.edit_message_text(f"📧 <b>Email:</b> <code>{email_addr}</code>\n🟢 <b>Auto-Listening Active!</b>", reply_markup=get_main_keyboard(lang_code), parse_mode="HTML")

        elif data == "gen_mail":
            try:
                dom_resp = await client.get("https://api.mail.tm/domains")
                domains = dom_resp.json().get("hydra:member", [])
                domain = domains[0]["domain"]
                email_addr, pwd, tok = await create_email_account(domain)

                user_sessions[user_id] = {"address": email_addr, "password": pwd, "token": tok}
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))

                await query.edit_message_text(f"⚡ <b>Fresh Email:</b>\n<code>{email_addr}</code>\n\n🟢 <b>Listening for OTPs...</b>", reply_markup=get_main_keyboard(lang_code), parse_mode="HTML")
            except Exception:
                await query.edit_message_text("❌ Timeout!", reply_markup=get_main_keyboard(lang_code))

        elif data == "save_vault":
            if user_id not in user_sessions:
                await query.answer("⚠️ Generate an email first!", show_alert=True)
                return
            sess = user_sessions[user_id]
            cursor.execute("INSERT OR REPLACE INTO vault (user_id, email, password, token) VALUES (?, ?, ?, ?)",
                           (user_id, sess["address"], sess["password"], sess["token"]))
            conn.commit()
            await query.answer("💾 Email Saved into Vault!", show_alert=True)

        elif data == "view_vault":
            cursor.execute("SELECT email FROM vault WHERE user_id = ?", (user_id,))
            saved = cursor.fetchall()
            if not saved:
                await query.answer("📁 Vault is empty!", show_alert=True)
                return
            buttons = []
            for item in saved[:5]:
                buttons.append([InlineKeyboardButton(f"📬 {item[0][:22]}", callback_data=f"restore_{item[0]}")])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
            await query.edit_message_text("📁 <b>SAVED VAULT:</b>\nTap to restore:", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

        elif data.startswith("restore_"):
            target_email = data.replace("restore_", "")
            cursor.execute("SELECT email, password, token FROM vault WHERE user_id = ? AND email = ?", (user_id, target_email))
            res = cursor.fetchone()
            if res:
                email_addr, pwd, tok = res
                user_sessions[user_id] = {"address": email_addr, "password": pwd, "token": tok}
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))
                await query.edit_message_text(f"🔄 <b>RESTORED:</b> <code>{email_addr}</code>\n🟢 <b>Listening for OTPs...</b>", reply_markup=get_main_keyboard(lang_code), parse_mode="HTML")

        elif data == "fake_id":
            name, address, dob = generate_fake_profile()
            profile_card = (
                "╔════════════════════════╗\n"
                "    🎭  <b>FAKE PROFILE DATA</b>\n"
                "╚════════════════════════╝\n\n"
                f"👤 <b>Full Name:</b> <code>{name}</code>\n"
                f"🎂 <b>Date of Birth:</b> <code>{dob}</code>\n"
                f"🏠 <b>US Address:</b> <code>{address}</code>\n"
            )
            await query.message.reply_text(profile_card, reply_markup=get_main_keyboard(lang_code), parse_mode="HTML")

        elif data == "check_mail":
            if user_id not in user_sessions:
                await query.answer("⚠️ Generate an email first!", show_alert=True)
                return
            token = user_sessions[user_id]["token"]
            headers = {"Authorization": f"Bearer {token}"}
            try:
                msg_resp = await client.get("https://api.mail.tm/messages", headers=headers)
                messages = msg_resp.json().get("hydra:member", [])
                if not messages:
                    await query.answer("📭 Inbox empty!", show_alert=True)
                    return
                latest_id = messages[0]["id"]
                detail_resp = await client.get(f"https://api.mail.tm/messages/{latest_id}", headers=headers)
                mail_data = detail_resp.json()
                sender = html.escape(mail_data.get("from", {}).get("address", "Unknown"))
                subject = html.escape(mail_data.get("subject", "No Subject"))
                body_text = mail_data.get("text", "") or "No text content"
                otp_match = re.search(r'\b\d{4,8}\b', body_text)
                detected_otp = f"\n\n🔑 <b>Extracted OTP/Code:</b> <code>{otp_match.group(0)}</code>" if otp_match else ""
                await query.message.reply_text(f"📬 <b>From:</b> {sender}\n📌 <b>Subject:</b> {subject}{detected_otp}\n\n<blockquote>{html.escape(body_text[:1200])}</blockquote>", reply_markup=get_main_keyboard(lang_code), parse_mode="HTML")
            except Exception:
                await query.answer("❌ Error fetching", show_alert=True)

        elif data == "del_mail":
            if user_id in user_sessions:
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                del user_sessions[user_id]
                await query.answer("🗑 Session Closed!", show_alert=True)
                await query.edit_message_text("🗑 <b>Session closed.</b>", reply_markup=get_main_keyboard(lang_code), parse_mode="HTML")

        elif data == "back_main":
            waiting_for_custom_name[user_id] = False
            await start(update, context)

if __name__ == '__main__':
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    print("Syntax Empire Global Multi-Language Core is Live...")
    app.run_polling()
