import httpx
import random
import string
import html
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8604538821:AAEXkRMTPA5jnuyI0YzNaiyeCelBuWhWJe4"

# 3 MANDATORY PLATFORMS
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

user_sessions = {}

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

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
            InlineKeyboardButton("⚡ Generate Fresh Email", callback_data="gen_mail"),
            InlineKeyboardButton("📬 Check Inbox / OTP", callback_data="check_mail")
        ],
        [
            InlineKeyboardButton("🔄 Refresh Inbox", callback_data="check_mail"),
            InlineKeyboardButton("🗑 Delete Session", callback_data="del_mail")
        ],
        [
            InlineKeyboardButton("👑 Syntax Empire Community", url="https://t.me/syntaxredirect")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
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
        "⚡ <b>Welcome to the High-Speed Temp Mail Engine!</b>\n\n"
        "💎 <b>Domain Status:</b> 100% Fresh & Clean\n"
        "🚀 <b>Engine:</b> Ultra-Fast Asynchronous Core\n"
        "🛡 <b>Access:</b> Verified VIP Member\n\n"
        "👇 <i>Neeche diye gaye buttons se operate karein:</i>"
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

                user_sessions[user_id] = {"address": email_address, "token": token}

                mail_card = (
                    "╔════════════════════════╗\n"
                    "    📧  <b>FRESH EMAIL READY</b>\n"
                    "╚════════════════════════╝\n\n"
                    "⚡ <b>Aapka Private Email:</b>\n"
                    f"<code>{email_address}</code>\n\n"
                    "👆 <i>(Email par tap karo, turant copy ho jayega)</i>\n\n"
                    "🎯 <b>Status:</b> Active & Listening for OTP\n"
                    "🛡 <b>Network:</b> <b>Syntax Empire Fast-Track</b>\n\n"
                    "<i>Kisi bhi website par dalein aur neeche <b>Check Inbox</b> dabayein!</i>"
                )
                await query.edit_message_text(mail_card, reply_markup=get_main_keyboard(), parse_mode="HTML")
            except Exception:
                await query.edit_message_text("❌ Connection timeout. Dobara try karein.", reply_markup=get_main_keyboard())

        elif data == "check_mail":
            if user_id not in user_sessions:
                await query.answer("⚠️ Pehle 'Generate Fresh Email' se email banayein!", show_alert=True)
                return

            token = user_sessions[user_id]["token"]
            headers = {"Authorization": f"Bearer {token}"}

            try:
                msg_resp = await client.get("https://api.mail.tm/messages", headers=headers)
                messages = msg_resp.json().get("hydra:member", [])

                if not messages:
                    await query.answer("📭 Inbox khali hai! OTP aane me 5-10s lag sakte hain.", show_alert=True)
                    return

                latest_id = messages[0]["id"]
                detail_resp = await client.get(f"https://api.mail.tm/messages/{latest_id}", headers=headers)
                mail_data = detail_resp.json()

                sender = html.escape(mail_data.get("from", {}).get("address", "Unknown"))
                subject = html.escape(mail_data.get("subject", "No Subject"))
                body_text = mail_data.get("text", "") or "No text content"

                otp_match = re.search(r'\b\d{4,8}\b', body_text)
                detected_otp = f"\n\n🔑 <b>Extracted OTP/Code:</b> <code>{otp_match.group(0)}</code>" if otp_match else ""

                clean_preview = html.escape(body_text[:1500])

                inbox_card = (
                    "╔════════════════════════╗\n"
                    "    📬  <b>NEW OTP / MAIL ARRIVED!</b>\n"
                    "╚════════════════════════╝\n\n"
                    f"👤 <b>From:</b> <code>{sender}</code>\n"
                    f"📌 <b>Subject:</b> <b>{subject}</b>"
                    f"{detected_otp}\n\n"
                    "📝 <b>Message Body:</b>\n"
                    f"<blockquote>{clean_preview}</blockquote>\n\n"
                    "👑 <b>Syntax Empire Instant Core</b>"
                )
                await query.message.reply_text(inbox_card, reply_markup=get_main_keyboard(), parse_mode="HTML")
            except Exception:
                await query.answer("❌ Network lag. Dobara check dabayein!", show_alert=True)

        elif data == "del_mail":
            if user_id in user_sessions:
                del user_sessions[user_id]
                await query.answer("🗑 Email successfully deleted!", show_alert=True)
                await query.edit_message_text(
                    "🗑 <b>Session closed!</b>\n\nNaya email lene ke liye neeche button dabayein.",
                    reply_markup=get_main_keyboard(),
                    parse_mode="HTML"
                )
            else:
                await query.answer("Koi active session nahi mila!", show_alert=True)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Syntax Empire Clean Bot is Live...")
    app.run_polling()
