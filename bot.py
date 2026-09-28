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
ADMIN_ID = 8604538821  # Aapka Telegram ID (Admin commands ke liye)

# 3 MANDATORY PLATFORMS CONFIGURATION
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

# Database Setup (Persistent Vault)
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

# Active In-Memory Sessions & Watchers
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
            InlineKeyboardButton("📬 Manual Refresh", callback_data="check_mail")
        ],
        [
            InlineKeyboardButton("💾 Save to Vault", callback_data="save_vault"),
            InlineKeyboardButton("📁 My Vault (Saved)", callback_data="view_vault")
        ],
        [
            InlineKeyboardButton("🎭 Fake Profile Generator", callback_data="fake_id"),
            InlineKeyboardButton("🗑 Delete Session", callback_data="del_mail")
        ],
        [
            InlineKeyboardButton("👑 Syntax Empire Community", url="https://t.me/syntaxredirect")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Background Task for Auto OTP Alerts
async def watch_inbox(bot, user_id, token, address):
    headers = {"Authorization": f"Bearer {token}"}
    seen_ids = set()
    
    # Pre-populate already seen messages
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
                        
                        # Fetch full email
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
                            "📝 <b>Body Snippet:</b>\n"
                            f"<blockquote>{html.escape(body[:1200])}</blockquote>\n\n"
                            "⚡ <i>Auto-intercepted by Syntax Empire Core</i>"
                        )
                        await bot.send_message(chat_id=user_id, text=alert_card, parse_mode="HTML", reply_markup=get_main_keyboard())
        except Exception:
            pass
        await asyncio.sleep(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Save user to DB for stats
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    joined = await check_user_membership(context.bot, user_id)
    if not joined:
        lock_text = (
            "╔════════════════════════╗\n"
            "   🔒 <b>ACCESS RESTRICTED!</b> 🔒\n"
            "╚════════════════════════╝\n\n"
            "⚠️ <b>Syntax Empire Temp-Mail Bot</b> ko access karne ke liye aapko hamare official platforms join karna zaroori hai.\n\n"
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
        "├ 💎 100% Fresh Clean Domains\n"
        "├ 🔔 <b>Auto Live OTP Alerts</b> (No clicking needed!)\n"
        "├ 💾 <b>Email Vault:</b> Reserve your favorite emails\n"
        "└ 🎭 <b>Fake Profiles:</b> Instant US IDs for trials\n\n"
        "👇 <i>Select an option below:</i>"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    joined = await check_user_membership(context.bot, user_id)
    if not joined:
        await query.answer("❌ Pehle sabhi channels join karein!", show_alert=True)
        lock_text = (
            "╔════════════════════════╗\n"
            "   🔒 <b>ACCESS RESTRICTED!</b> 🔒\n"
            "╚════════════════════════╝\n\n"
            "⚠️ Bot ko access karne ke liye official platforms join karein:"
        )
        await query.message.edit_text(lock_text, reply_markup=get_force_join_keyboard(), parse_mode="HTML")
        return

    await query.answer()

    if data == "verify_join":
        await start(update, context)
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        if data == "gen_mail":
            await query.edit_message_text("⚡ <i>Syntax Empire server se fresh domain allocate ho raha hai...</i>", parse_mode="HTML")
            try:
                dom_resp = await client.get("https://api.mail.tm/domains")
                domains = dom_resp.json().get("hydra:member", [])
                if not domains:
                    await query.edit_message_text("❌ Domain server busy. 5s baad try karein.", reply_markup=get_main_keyboard())
                    return

                domain = domains[0]["domain"]
                email_address = f"{random_string()}{random.randint(100,999)}@{domain}"
                password = random_string(12)

                reg_resp = await client.post("https://api.mail.tm/accounts", json={"address": email_address, "password": password})
                if reg_resp.status_code != 201:
                    await query.edit_message_text("⚠️ Rate limit, dobara try karein.", reply_markup=get_main_keyboard())
                    return

                tok_resp = await client.post("https://api.mail.tm/token", json={"address": email_address, "password": password})
                token = tok_resp.json().get("token")

                user_sessions[user_id] = {"address": email_address, "password": password, "token": token}

                # Start Background Live OTP Watcher
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, token, email_address))

                mail_card = (
                    "╔════════════════════════╗\n"
                    "    📧  <b>FRESH EMAIL READY</b>\n"
                    "╚════════════════════════╝\n\n"
                    "⚡ <b>Aapka Private Email:</b>\n"
                    f"<code>{email_address}</code>\n\n"
                    "👆 <i>(Email par tap karo, turant copy ho jayega)</i>\n\n"
                    "🎯 <b>Status:</b> 🟢 <b>Auto-Listening Active!</b>\n"
                    "💡 <i>Aapko 'Check Inbox' dabane ki zaroorat nahi hai. OTP aate hi bot khud notification bhejega!</i>"
                )
                await query.edit_message_text(mail_card, reply_markup=get_main_keyboard(), parse_mode="HTML")
            except Exception:
                await query.edit_message_text("❌ Connection timeout. Dobara try karein.", reply_markup=get_main_keyboard())

        elif data == "save_vault":
            if user_id not in user_sessions:
                await query.answer("⚠️ Pehle email banayein, tabhi save hoga!", show_alert=True)
                return
            
            sess = user_sessions[user_id]
            cursor.execute("INSERT OR REPLACE INTO vault (user_id, email, password, token) VALUES (?, ?, ?, ?)",
                           (user_id, sess["address"], sess["password"], sess["token"]))
            conn.commit()
            await query.answer("💾 Email Saved! Ab aap ise kabhi bhi restore kar sakte hain.", show_alert=True)

        elif data == "view_vault":
            cursor.execute("SELECT email, password FROM vault WHERE user_id = ?", (user_id,))
            saved = cursor.fetchall()
            if not saved:
                await query.answer("📁 Aapke vault me abhi koi email save nahi hai!", show_alert=True)
                return

            buttons = []
            for item in saved[:5]:
                mail_btn_text = item[0][:20] + "..." if len(item[0]) > 20 else item[0]
                buttons.append([InlineKeyboardButton(f"📬 {mail_btn_text}", callback_data=f"restore_{item[0]}")])
            buttons.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main")])

            vault_text = (
                "╔════════════════════════╗\n"
                "    📁  <b>MY SAVED VAULT</b>\n"
                "╚════════════════════════╝\n\n"
                "Jis email ko activate karna hai, us par tap karein:"
            )
            await query.edit_message_text(vault_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

        elif data.startswith("restore_"):
            target_email = data.replace("restore_", "")
            cursor.execute("SELECT email, password, token FROM vault WHERE user_id = ? AND email = ?", (user_id, target_email))
            res = cursor.fetchone()
            if res:
                email_addr, pwd, tok = res
                user_sessions[user_id] = {"address": email_addr, "password": pwd, "token": tok}
                
                # Start watcher for restored mail
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                active_watchers[user_id] = asyncio.create_task(watch_inbox(context.bot, user_id, tok, email_addr))

                await query.answer("✅ Email restored & Auto-Alerts activated!")
                restored_text = (
                    "╔════════════════════════╗\n"
                    "    🔄  <b>RESTORED & ACTIVE</b>\n"
                    "╚════════════════════════╝\n\n"
                    f"📧 <b>Current Email:</b> <code>{email_addr}</code>\n\n"
                    "🎯 <b>Status:</b> 🟢 <b>Listening for incoming OTPs...</b>"
                )
                await query.edit_message_text(restored_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

        elif data == "fake_id":
            name, address, dob = generate_fake_profile()
            profile_card = (
                "╔════════════════════════╗\n"
                "    🎭  <b>FAKE PROFILE GENERATED</b>\n"
                "╚════════════════════════╝\n\n"
                f"👤 <b>Full Name:</b> <code>{name}</code>\n"
                f"🎂 <b>Date of Birth:</b> <code>{dob}</code>\n"
                f"🏠 <b>US Address:</b> <code>{address}</code>\n\n"
                "💡 <i>Free trials, signups aur gaming sites par fill karne ke liye tap karke copy karein!</i>"
            )
            await query.message.reply_text(profile_card, reply_markup=get_main_keyboard(), parse_mode="HTML")

        elif data == "check_mail":
            if user_id not in user_sessions:
                await query.answer("⚠️ Pehle email generate karein!", show_alert=True)
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
                await query.answer("❌ Error fetching inbox", show_alert=True)

        elif data == "del_mail":
            if user_id in user_sessions:
                if user_id in active_watchers:
                    active_watchers[user_id].cancel()
                del user_sessions[user_id]
                await query.answer("🗑 Current session removed!", show_alert=True)
                await query.edit_message_text("🗑 <b>Session closed.</b> (Saved vault emails safe hain).", reply_markup=get_main_keyboard(), parse_mode="HTML")

        elif data == "back_main":
            await start(update, context)

# Admin Commands: /stats and /broadcast
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM vault")
    v_count = cursor.fetchone()[0]
    await update.message.reply_text(f"📊 <b>Bot Statistics:</b>\n\n👥 Total Users: {u_count}\n💾 Saved Vault Mails: {v_count}", parse_mode="HTML")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.message.text.replace("/broadcast", "").strip()
    if not msg:
        await update.message.reply_text("Usage: `/broadcast Aapka message yahan`", parse_mode="Markdown")
        return
    cursor.execute("SELECT user_id FROM users")
    all_users = cursor.fetchall()
    sent = 0
    for u in all_users:
        try:
            await context.bot.send_message(chat_id=u[0], text=msg, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users!")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Syntax Empire Pro Multi-Feature Bot is Live...")
    app.run_polling()
