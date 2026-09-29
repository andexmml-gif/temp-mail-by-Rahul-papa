import os
import sqlite3
import random
import string
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIGURATION & LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8604538821:AAEXkRMTPA5jnuyI0YzNaiyeCelBuWhWJe4")
BASE_API_URL = "https://api.mail.tm"

# States for custom username
WAITING_CUSTOM_NAME = 1

# ---------------- RENDER 24/7 DUMMY PORT LISTENER ----------------
class RenderHealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - Syntax Empire Temp Mail Core Running 24/7")

    def log_message(self, format, *args):
        return

def start_background_port():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), RenderHealthServer)
    logger.info(f"Render Port Listener successfully started on port {port}")
    server.serve_forever()

# ---------------- PERSISTENT SQLITE DATABASE ----------------
DB_FILE = "syntax_vault.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            user_id INTEGER PRIMARY KEY,
            email TEXT,
            token TEXT,
            password TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            email TEXT,
            password TEXT,
            token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'en'
        )
    """)
    conn.commit()
    conn.close()

def get_user_lang(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT lang FROM user_settings WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "en"

def set_user_lang(user_id, lang):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_settings (user_id, lang)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang
    """, (user_id, lang))
    conn.commit()
    conn.close()

def save_session(user_id, email, token, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO sessions (user_id, email, token, password)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            email=excluded.email,
            token=excluded.token,
            password=excluded.password
    """, (user_id, email, token, password))
    conn.commit()
    conn.close()

def get_session(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT email, token, password FROM sessions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def delete_session(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_to_vault(user_id, email, password, token):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO vault (user_id, email, password, token) VALUES (?, ?, ?, ?)",
              (user_id, email, password, token))
    conn.commit()
    conn.close()

def get_user_vault(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, email, password FROM vault WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# ---------------- MAIL ENGINE CLIENT (MAIL.TM) ----------------
async def fetch_available_domains():
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(f"{BASE_API_URL}/domains")
        if res.status_code == 200:
            domains = res.json().get("hydra:member", [])
            return [d["domain"] for d in domains if d.get("isActive", True)]
    return ["uberip.com"]

async def create_mail_account(custom_user=None, domain=None):
    if not domain:
        domains = await fetch_available_domains()
        domain = domains[0] if domains else "uberip.com"
        
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    username = custom_user.strip().lower() if custom_user else random_str
    email = f"{username}@{domain}"
    password = "".join(random.choices(string.ascii_letters + string.digits, k=12))

    payload = {"address": email, "password": password}
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(f"{BASE_API_URL}/accounts", json=payload)
        if res.status_code in [200, 201]:
            token_res = await client.post(f"{BASE_API_URL}/token", json=payload)
            if token_res.status_code == 200:
                token = token_res.json().get("token")
                return email, token, password
    return None, None, None

async def fetch_inbox_messages(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(f"{BASE_API_URL}/messages", headers=headers)
        if res.status_code == 200:
            return res.json().get("hydra:member", [])
    return []

# ---------------- MULTILINGUAL STRING DICTIONARY ----------------
STRINGS = {
    "en": {
        "title": "SYNTAX EMPIRE DASHBOARD",
        "curr_email": "Current Email",
        "status": "Active & Auto-Listening",
        "allocated": "Allocated Cloud Session",
        "engine": "Fast-Track Interceptor",
        "btn_refresh": "🔄 Refresh Inbox",
        "btn_save": "💾 Save to Vault",
        "btn_instant": "⚡ Instant Fresh Email",
        "btn_custom": "✏️ Custom Name Email",
        "btn_domain": "🌐 Custom Domain",
        "btn_vault": "📁 My Vault (Saved)",
        "btn_tools": "🛠️ Tools & Settings",
        "btn_delete": "🗑️ Delete Session",
        "btn_owner": "👑 Bot Owner Info",
        "btn_comm": "👑 Syntax Community",
        "btn_back": "🔙 Back to Dashboard",
        "btn_lang": "🌐 Switch Language (भाषा)",
        "empty_inbox": "📭 Inbox is empty! No new OTP or email received.",
        "vault_saved": "✅ Current email saved to your private Vault!",
        "vault_empty": "📁 Vault is empty! Save emails using the Save button.",
        "session_cleared": "Session Cleared",
        "ask_custom_name": "✏️ <b>Enter your desired email username:</b>\n<i>(e.g., rahul, king, boss99)</i>",
        "select_domain": "🌐 <b>Select an available domain:</b>"
    },
    "hi": {
        "title": "सिंटेक्स एम्पायर डैशबोर्ड",
        "curr_email": "वर्तमान ईमेल",
        "status": "सक्रिय और ऑटो-सुनना चालू",
        "allocated": "क्लाउड सेशन आवंटित",
        "engine": "फास्ट-ट्रैक इंटरसेप्टर",
        "btn_refresh": "🔄 इनबॉक्स रिफ्रेश",
        "btn_save": "💾 वॉल्ट में सेव करें",
        "btn_instant": "⚡ नया इंस्टेंट ईमेल",
        "btn_custom": "✏️ कस्टम नाम ईमेल",
        "btn_domain": "🌐 कस्टम डोमेन",
        "btn_vault": "📁 मेरा वॉल्ट (सेव्ड)",
        "btn_tools": "🛠️ टूल्स और सेटिंग्स",
        "btn_delete": "🗑️ सेशन डिलीट करें",
        "btn_owner": "👑 बॉट ओनर जानकारी",
        "btn_comm": "👑 सिंटेक्स कम्युनिटी",
        "btn_back": "🔙 डैशबोर्ड पर वापस",
        "btn_lang": "🌐 भाषा बदलें (Language)",
        "empty_inbox": "📭 इनबॉक्स खाली है! कोई नया OTP या ईमेल नहीं आया।",
        "vault_saved": "✅ ईमेल सफलतापूर्वक आपके प्राइवेट वॉल्ट में सेव हो गया!",
        "vault_empty": "📁 वॉल्ट खाली है! सेव बटन दबाकर ईमेल सुरक्षित रखें।",
        "session_cleared": "सेशन डिलीट हो गया",
        "ask_custom_name": "✏️ <b>अपना मनपसंद यूजरनेम टाइप करके भेजें:</b>\n<i>(जैसे: rahul, king, boss99)</i>",
        "select_domain": "🌐 <b>उपलब्ध डोमेन में से एक चुनें:</b>"
    }
}

# ---------------- UI DASHBOARDS & LAYOUTS ----------------
def get_main_dashboard_markup(lang="en"):
    t = STRINGS.get(lang, STRINGS["en"])
    keyboard = [
        [
            InlineKeyboardButton(t["btn_refresh"], callback_data="refresh_inbox"),
            InlineKeyboardButton(t["btn_save"], callback_data="save_to_vault"),
        ],
        [
            InlineKeyboardButton(t["btn_instant"], callback_data="new_instant"),
            InlineKeyboardButton(t["btn_custom"], callback_data="custom_name"),
        ],
        [
            InlineKeyboardButton(t["btn_domain"], callback_data="custom_domain"),
            InlineKeyboardButton(t["btn_vault"], callback_data="view_vault"),
        ],
        [
            InlineKeyboardButton(t["btn_tools"], callback_data="tools_settings"),
            InlineKeyboardButton(t["btn_delete"], callback_data="delete_session"),
        ],
        [
            InlineKeyboardButton(t["btn_owner"], callback_data="owner_info"),
            InlineKeyboardButton(t["btn_comm"], url="https://t.me/syntaxkagc"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def render_dashboard_text(email="Not Generated", lang="en"):
    t = STRINGS.get(lang, STRINGS["en"])
    return (
        f"┌───────────────────────────────┐\n"
        f"│  ⚡ <b>{t['title']}</b>  │\n"
        f"└───────────────────────────────┘\n\n"
        f"📧 <b>{t['curr_email']}:</b>\n<code>{email}</code>\n\n"
        f"🟢 <b>Status:</b> {t['status']}\n"
        f"⏱️ <b>Allocated:</b> {t['allocated']}\n"
        f"🛡️ <b>Engine:</b> {t['engine']}\n"
        f"⚙️ <b>Architecture:</b> Cloud 24/7 Distributed"
    )

def get_tools_markup(lang="en"):
    t = STRINGS.get(lang, STRINGS["en"])
    keyboard = [
        [InlineKeyboardButton(t["btn_lang"], callback_data="open_lang_menu")],
        [InlineKeyboardButton("🗑️ Clear Local Vault", callback_data="clear_vault_confirm")],
        [InlineKeyboardButton(t["btn_back"], callback_data="back_dashboard")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_markup():
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
            InlineKeyboardButton("🇮🇳 हिन्दी (Hindi)", callback_data="set_lang_hi"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="tools_settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------------- HANDLERS ----------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    session = get_session(user_id)

    if not session:
        email, token, password = await create_mail_account()
        if email:
            save_session(user_id, email, token, password)
            current_email = email
        else:
            current_email = "Server Error - Click Refresh"
    else:
        current_email = session[0]

    text = render_dashboard_text(current_email, lang)
    reply_markup = get_main_dashboard_markup(lang)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def prompt_custom_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = STRINGS.get(lang, STRINGS["en"])

    cancel_btn = InlineKeyboardMarkup([[InlineKeyboardButton(t["btn_back"], callback_data="cancel_custom")]])
    await query.edit_message_text(text=t["ask_custom_name"], reply_markup=cancel_btn, parse_mode=ParseMode.HTML)
    return WAITING_CUSTOM_NAME

async def receive_custom_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    raw_name = update.message.text.strip().replace(" ", "")

    email, token, password = await create_mail_account(custom_user=raw_name)
    if email:
        save_session(user_id, email, token, password)
        await update.message.reply_text(
            text=render_dashboard_text(email, lang),
            reply_markup=get_main_dashboard_markup(lang),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            text="⚠️ Name unavailable or format invalid! Please try another name or send /start."
        )
    return ConversationHandler.END

async def cancel_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    session = get_session(user_id)
    email = session[0] if session else "Session Inactive"

    await query.edit_message_text(
        text=render_dashboard_text(email, lang),
        reply_markup=get_main_dashboard_markup(lang),
        parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    t = STRINGS.get(lang, STRINGS["en"])

    if data == "refresh_inbox":
        session = get_session(user_id)
        if not session:
            await query.answer("No active email!", show_alert=True)
            return

        token = session[1]
        emails = await fetch_inbox_messages(token)
        if not emails:
            await query.answer(t["empty_inbox"], show_alert=True)
            return

        inbox_text = "📬 <b>Recent Intercepted Messages:</b>\n\n"
        for idx, mail in enumerate(emails[:5], 1):
            sender = mail.get("from", {}).get("address", "Unknown")
            subject = mail.get("subject", "No Subject")
            intro = mail.get("intro", "")
            inbox_text += f"<b>{idx}. From:</b> <code>{sender}</code>\n"
            inbox_text += f"<b>Subject:</b> {subject}\n"
            inbox_text += f"<b>Snippet:</b> <i>{intro[:90]}...</i>\n\n"

        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton(t["btn_back"], callback_data="back_dashboard")]])
        await query.edit_message_text(text=inbox_text, reply_markup=back_markup, parse_mode=ParseMode.HTML)

    elif data == "new_instant":
        await query.answer("Generating fresh address...", show_alert=False)
        email, token, password = await create_mail_account()
        if email:
            save_session(user_id, email, token, password)
            await query.edit_message_text(
                text=render_dashboard_text(email, lang),
                reply_markup=get_main_dashboard_markup(lang),
                parse_mode=ParseMode.HTML
            )
        else:
            await query.answer("API Busy! Please retry.", show_alert=True)

    elif data == "custom_domain":
        domains = await fetch_available_domains()
        kb = [[InlineKeyboardButton(f"🌐 @{d}", callback_data=f"set_domain_{d}")] for d in domains]
        kb.append([InlineKeyboardButton(t["btn_back"], callback_data="back_dashboard")])
        await query.edit_message_text(text=t["select_domain"], reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("set_domain_"):
        chosen_domain = data.replace("set_domain_", "")
        email, token, password = await create_mail_account(domain=chosen_domain)
        if email:
            save_session(user_id, email, token, password)
            await query.edit_message_text(
                text=render_dashboard_text(email, lang),
                reply_markup=get_main_dashboard_markup(lang),
                parse_mode=ParseMode.HTML
            )
        else:
            await query.answer("Error allocating domain!", show_alert=True)

    elif data == "save_to_vault":
        session = get_session(user_id)
        if session:
            add_to_vault(user_id, session[0], session[2], session[1])
            await query.answer(t["vault_saved"], show_alert=True)
        else:
            await query.answer("No email active!", show_alert=True)

    elif data == "view_vault":
        vault_items = get_user_vault(user_id)
        if not vault_items:
            await query.answer(t["vault_empty"], show_alert=True)
            return

        vault_text = "📁 <b>Saved Vault Credentials:</b>\n\n"
        for v in vault_items:
            vault_text += f"📧 <code>{v[1]}</code>\n🔑 Pass: <code>{v[2]}</code>\n\n"

        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton(t["btn_back"], callback_data="back_dashboard")]])
        await query.edit_message_text(text=vault_text, reply_markup=back_markup, parse_mode=ParseMode.HTML)

    elif data == "tools_settings":
        tools_text = (
            "🛠️ <b>TOOLS & ADVANCED SETTINGS</b>\n"
            "─────────────────────────────\n"
            "• Customize preferences & interface language\n"
            "• Manage saved credentials & engine rules"
        )
        await query.edit_message_text(text=tools_text, reply_markup=get_tools_markup(lang), parse_mode=ParseMode.HTML)

    elif data == "open_lang_menu":
        menu_text = "🌐 <b>Choose Preferred Language / भाषा चुनें:</b>"
        await query.edit_message_text(text=menu_text, reply_markup=get_language_markup(), parse_mode=ParseMode.HTML)

    elif data.startswith("set_lang_"):
        new_lang = data.split("_")[-1]
        set_user_lang(user_id, new_lang)
        alert_msg = "Language updated to English!" if new_lang == "en" else "भाषा सफलतापूर्वक हिन्दी में सेट हो गई!"
        await query.answer(alert_msg, show_alert=True)

        session = get_session(user_id)
        email = session[0] if session else "Session Inactive"
        await query.edit_message_text(
            text=render_dashboard_text(email, new_lang),
            reply_markup=get_main_dashboard_markup(new_lang),
            parse_mode=ParseMode.HTML
        )

    elif data == "clear_vault_confirm":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM vault WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await query.answer("Vault cleared successfully!", show_alert=True)
        await query.edit_message_text(
            text=render_dashboard_text(get_session(user_id)[0] if get_session(user_id) else "Session Inactive", lang),
            reply_markup=get_main_dashboard_markup(lang),
            parse_mode=ParseMode.HTML
        )

    elif data == "owner_info":
        info_text = (
            "👑 <b>SYNTAX EMPIRE ARCHITECTURE</b>\n"
            "─────────────────────────────\n"
            "• <b>Founder & Lead:</b> Rahul\n"
            "• <b>Support Community:</b> @syntaxkagc\n"
            "• <b>Core Engine:</b> 24/7 Cloud Architecture\n"
            "• <b>Framework:</b> Python 3.12 (Long-Polling + Keep-Alive)"
        )
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton(t["btn_back"], callback_data="back_dashboard")]])
        await query.edit_message_text(text=info_text, reply_markup=back_markup, parse_mode=ParseMode.HTML)

    elif data == "delete_session":
        delete_session(user_id)
        await query.answer(t["session_cleared"], show_alert=True)
        await query.edit_message_text(
            text=render_dashboard_text(t["session_cleared"], lang),
            reply_markup=get_main_dashboard_markup(lang),
            parse_mode=ParseMode.HTML
        )

    elif data == "back_dashboard":
        session = get_session(user_id)
        email = session[0] if session else "Session Inactive"
        await query.edit_message_text(
            text=render_dashboard_text(email, lang),
            reply_markup=get_main_dashboard_markup(lang),
            parse_mode=ParseMode.HTML
        )

# ---------------- APPLICATION INITIALIZATION ----------------
def main():
    init_db()

    server_thread = threading.Thread(target=start_background_port, daemon=True)
    server_thread.start()

    logger.info("Initializing Syntax Empire Telegram Core Engine...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Custom Name Conversation Handler
    custom_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(prompt_custom_name, pattern="^custom_name$")],
        states={
            WAITING_CUSTOM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_name)]
        },
        fallbacks=[CallbackQueryHandler(cancel_custom, pattern="^cancel_custom$")]
    )

    application.add_handler(custom_conv)
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    logger.info("Bot is active and running polling on Render Cloud...")
    application.run_polling()

if __name__ == "__main__":
    main()
