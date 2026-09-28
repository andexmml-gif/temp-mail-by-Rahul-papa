import httpx
import random
import string
import html
import re
import asyncio
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

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

# Database
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
        user_id INTEGER PRIMARY KEY
    )
''')
conn.commit()

user_sessions = {}
active_watchers = {}

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_fake_profile():
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Ryan", "David", "Ethan", "Lucas"]
    last_names = ["Vance", "Mercer", "Blackwood", "Sterling", "Kowalski", "Stone", "Hayes", "Drake", "Sinclair"]
    streets = ["Sunset Blvd", "Broadway Ave", "Maple Street", "Silicon Park", "Kings Road", "Wall Street"]
    cities = [("New York", "NY", "10001"), ("Los Angeles", "CA", "90001"), ("Austin", "TX", "73301"), ("Miami", "FL", "33101")]
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

def get_force_join_keyboard():
    keyboard = []
    for ch in CHANNELS:
        keyboard.append([InlineKeyboardButton(f"👉 Join {ch['name']}", url=ch["link"])])
    keyboard.append([InlineKeyboardButton("✅ Verify / Unlock Bot", callback_data="verify_join")])
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("⚡ Instant Fresh Email", callback_data="gen_mail"),
            InlineKeyboardButton("🌐 Custom Domain", callback_data="list_domains")
        ],
        [
            InlineKeyboardButton("💾 Save to Vault", callback_data="save_vault"),
            InlineKeyboardButton("📁 My Vault (Saved)", callback_data="view_vault")
        ],
        [
            InlineKeyboardButton("🎭 Fake Profile Generator", callback_data="fake_id"),
            InlineKeyboardButton("📬 Manual Refresh", callback_data="check_mail")
        ],
        [
            InlineKeyboardButton("🗑 Delete Session", callback_data="del_mail"),
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
                        await bot.send_message(chat_id=user_id, text=alert_card, parse_mode="HTML", reply_markup=get_main_keyboard())
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
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    joined = await check_user_membership(context.bot, user_id)
    if not joined:
        lock_text = (
            "╔════════════════════════╗\n"
            "   🔒 <b>ACCESS RESTRICTED!</b> 🔒\n"
            "╚════════════════════════╝\n\n"
            "⚠️ <b>Syntax Empire Temp-Mail Bot</b> ko access karne ke liye official platforms join karna zaroori hai.\n\n"
            "👇 <i>Neeche diye gaye sabhi links join karein, fir 'Verify' par tap karein:</i>"
        )
        if update.message:
            await update.message.reply_text(lock_text, reply_markup=get_force_join_keyboard(), parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.message.edit_text(lock_text, reply_markup=get_force_join_keyboard(), parse_mode="HTML")
        return

    welcome_text = (
        "╔════════════════════════╗\n"
        "   👑  <b>SYNTAX EMPIRE BOT</b>  👑\n"
        "╚════════════════════════╝\n\n"
        "⚡ <b>Next-Gen High-Speed Temp Mail Hub!</b>\n\n"
        "✨ <b>Pro Features:</b>\n"
        "├ 🌐 <b>Custom Domain Picker:</b> Apni marzi ka domain chuno\n"
        "├ 🔔 <b>Auto Live OTP Alerts:</b> Direct notification aayega\n"
        "├ 💾 <b>Email Vault:</b> Reserve your favorite emails\n"
        "└ 🎭 <b>Fake Profiles:</b> US IDs for signups\n\n"
        "💡 <i>Tip: Apna custom naam rakhne ke liye type karein:</i> <code>/custom apnanaam</code>\n\n"
        "👇 <i>Neeche diye gaye buttons se operate karein:</i>"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

async def custom_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    joined = await check_user_membership(context.bot, user_id)
    if not joined:
        await update.message.reply_text("❌ Pehle mandatory channels join karein!", reply_markup=get_force_join_keyboard())
        return

    text = update.message.text.replace("/custom", "").strip().lower()
    clean_prefix = re.sub(r'[^a-z0-9]', '', text)
    
    if not clean_prefix or len(clean_prefix) < 3:
        await update.message.reply_text("⚠️ <b>Sahi format:</b> <code>/custom rahulbhai</code>\n(Kam se kam 3 characters hone chahiye)", parse_mode="HTML")
        return

    await update.message.reply_text("⏳ <i>Custom name ke sath email register ho raha hai...</i>", parse_mode="HTML")
    async with httpx.AsyncClient(timeout=10.0) as client:
        dom_resp = await client.get("https://api.mail.tm/domains")
        domains = dom_resp.json().get("hydra:member", [])
        if not domains:
            await update.message.reply_text("❌ Domain server unavailable", reply_markup=get_main_keyboard())
            return
        
        domain = domains[0]["domain"]
        email_addr, pwd, tok = await create_email_account(domain, prefix=clean_prefix)
        if not email_addr:
            await update.message.reply_text("⚠️ Yeh custom username already taken hai! Dusra naam try karein.", reply_markup=get_main_keyboard())
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
        await update.message.reply_text(mail_card, reply_markup=get_main_keyboard(), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    joined = await check_user_membership(context.bot, user_id)
    if not joined:
        await query.answer("❌ Pehle sabhi channels join karein!", show_alert=True)
        return

    await query.answer()

    if data == "verify_join":
        await start(update, context)
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        # LIST DOMAINS FOR SELECTION
        if data == "list_domains":
            try:
                dom_resp = await client.get("https://api.mail.tm/domains")
                domains = dom_resp.json().get("hydra:member", [])
                if not domains:
                    await query.edit_message_text("❌ Abhi domains load nahi hue. Dobara try karein.", reply_markup=get_main_keyboard())
                    return

                buttons = []
                for d in domains[:6]:
                    dom_name = d["domain"]
                    buttons.append([InlineKeyboardButton(f"🌐 @{dom_name}", callback_data=f"seldom_{dom_name}")])
                buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])

                domain_text = (
                    "╔════════════════════════╗\n"
                    "   🌐 <b>CHOOSE DOMAIN</b>\n"
                    "╚════════════════════════╝\n\n"
                    "Neeche diye gaye available domains me se apna pasandeeda domain select karein:"
                )
                await query.edit_message_text(domain_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
            except Exception:
                await query.edit_message_text("❌ Domain list fetch error", reply_markup=get_main_keyboard())

        # GENERATE EMAIL WITH SELECTED DOMAIN
        elif data.startswith("seldom_"):
            chosen_domain = data.replace("seldom_", "")
            await query.edit_message_text(f"⏳ <i>@{chosen_domain} par email allocate ho raha hai...</i>", parse_mode="HTML")
            email_addr, pwd, tok = await create_email_account(chosen_domain)
            if not email_addr:
                await query.edit_message_text("⚠️ Domain rate limit, dusra domain chuno!", reply_markup=get_main_keyboard())
                return

            user_sessions[user_id] = {"address": email_addr, "password": pwd, "token": tok}
            if user_id in active_watchers:
                active_watchers[user_id].cancel()
            active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))

            mail_card = (
                "╔════════════════════════╗\n"
                "    📧  <b>FRESH EMAIL READY</b>\n"
                "╚════════════════════════╝\n\n"
                f"⚡ <b>Domain:</b> <code>@{chosen_domain}</code>\n"
                f"📫 <b>Email:</b> <code>{email_addr}</code>\n\n"
                "🎯 <b>Status:</b> 🟢 <b>Auto-Listening Active!</b>"
            )
            await query.edit_message_text(mail_card, reply_markup=get_main_keyboard(), parse_mode="HTML")

        elif data == "gen_mail":
            await query.edit_message_text("⚡ <i>Allocating fresh random email...</i>", parse_mode="HTML")
            try:
                dom_resp = await client.get("https://api.mail.tm/domains")
                domains = dom_resp.json().get("hydra:member", [])
                domain = domains[0]["domain"]
                email_addr, pwd, tok = await create_email_account(domain)

                user_sessions[user_id] = {"address": email_addr, "password": pwd, "token": tok}
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))

                mail_card = (
                    "╔════════════════════════╗\n"
                    "    📧  <b>FRESH EMAIL READY</b>\n"
                    "╚════════════════════════╝\n\n"
                    f"⚡ <b>Email:</b> <code>{email_addr}</code>\n\n"
                    "🎯 <b>Status:</b> 🟢 <b>Auto-Listening Active!</b>"
                )
                await query.edit_message_text(mail_card, reply_markup=get_main_keyboard(), parse_mode="HTML")
            except Exception:
                await query.edit_message_text("❌ Connection timeout", reply_markup=get_main_keyboard())

        elif data == "save_vault":
            if user_id not in user_sessions:
                await query.answer("⚠️ Pehle email banayein!", show_alert=True)
                return
            sess = user_sessions[user_id]
            cursor.execute("INSERT OR REPLACE INTO vault (user_id, email, password, token) VALUES (?, ?, ?, ?)",
                           (user_id, sess["address"], sess["password"], sess["token"]))
            conn.commit()
            await query.answer("💾 Email Saved into Vault!", show_alert=True)

        elif data == "view_vault":
            cursor.execute("SELECT email, password FROM vault WHERE user_id = ?", (user_id,))
            saved = cursor.fetchall()
            if not saved:
                await query.answer("📁 Vault khali hai!", show_alert=True)
                return
            buttons = []
            for item in saved[:5]:
                mail_btn_text = item[0][:20] + "..." if len(item[0]) > 20 else item[0]
                buttons.append([InlineKeyboardButton(f"📬 {mail_btn_text}", callback_data=f"restore_{item[0]}")])
            buttons.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main")])
            await query.edit_message_text("📁 <b>MY SAVED VAULT:</b>\n\nRestore karne ke liye tap karein:", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

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
                await query.edit_message_text(f"🔄 <b>RESTORED:</b> <code>{email_addr}</code>\n\n🟢 <b>Listening for OTPs...</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")

        elif data == "fake_id":
            name, address, dob = generate_fake_profile()
            profile_card = (
                "╔════════════════════════╗\n"
                "    🎭  <b>FAKE PROFILE GENERATED</b>\n"
                "╚════════════════════════╝\n\n"
                f"👤 <b>Full Name:</b> <code>{name}</code>\n"
                f"🎂 <b>Date of Birth:</b> <code>{dob}</code>\n"
                f"🏠 <b>US Address:</b> <code>{address}</code>\n"
            )
            await query.message.reply_text(profile_card, reply_markup=get_main_keyboard(), parse_mode="HTML")

        elif data == "check_mail":
            if user_id not in user_sessions:
                await query.answer("⚠️ Pehle email banayein!", show_alert=True)
                return
            token = user_sessions[user_id]["token"]
            headers = {"Authorization": f"Bearer {token}"}
            try:
                msg_resp = await client.get("https://api.mail.tm/messages", headers=headers)
                messages = msg_resp.json().get("hydra:member", [])
                if not messages:
                    await query.answer("📭 Abhi koi email nahi aaya!", show_alert=True)
                    return
                latest_id = messages[0]["id"]
                detail_resp = await client.get(f"https://api.mail.tm/messages/{latest_id}", headers=headers)
                mail_data = detail_resp.json()
                sender = html.escape(mail_data.get("from", {}).get("address", "Unknown"))
                subject = html.escape(mail_data.get("subject", "No Subject"))
                body_text = mail_data.get("text", "") or "No text content"
                otp_match = re.search(r'\b\d{4,8}\b', body_text)
                detected_otp = f"\n\n🔑 <b>Extracted OTP/Code:</b> <code>{otp_match.group(0)}</code>" if otp_match else ""
                inbox_card = (
                    "╔════════════════════════╗\n"
                    "    📬  <b>LATEST EMAIL</b>\n"
                    "╚════════════════════════╝\n\n"
                    f"👤 <b>From:</b> <code>{sender}</code>\n"
                    f"📌 <b>Subject:</b> <b>{subject}</b>"
                    f"{detected_otp}\n\n"
                    f"<blockquote>{html.escape(body_text[:1200])}</blockquote>"
                )
                await query.message.reply_text(inbox_card, reply_markup=get_main_keyboard(), parse_mode="HTML")
            except Exception:
                await query.answer("❌ Error fetching", show_alert=True)

        elif data == "del_mail":
            if user_id in user_sessions:
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                del user_sessions[user_id]
                await query.answer("🗑 Deleted!", show_alert=True)
                await query.edit_message_text("🗑 <b>Session closed.</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")

        elif data == "back_main":
            await start(update, context)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("custom", custom_name_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Syntax Empire Custom-Domain Core is Live...")
    app.run_polling()
