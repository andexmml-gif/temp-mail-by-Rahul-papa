import os
import random
import string
from threading import Thread
from flask import Flask
import requests
import telebot
from telebot import types

# ================= CONFIGURATION =================
# Yahan BotFather se mila naya token paste karo:
RAW_TOKEN = "8604538821:AAE2xvDJ4_rjfc1dbohQS09_sbprbUontCY"
BOT_TOKEN = os.environ.get("BOT_TOKEN", RAW_TOKEN).strip()

BOT_USERNAME = "@Temp_mail_by_syntaxbot"

CHANNEL_USERNAME = "@syntaxredirect"
CHANNEL_LINK = "https://t.me/syntaxredirect"

GROUP_USERNAME = "@syntaxkagc"
GROUP_LINK = "https://t.me/syntaxkagc"

bot = telebot.TeleBot(BOT_TOKEN)

# In-memory storage
user_sessions = {}
user_vaults = {}
user_state = {}
user_lang = {}

MAIL_API_BASE = "https://api.mail.tm"

# ================= MULTI-LANGUAGE STRINGS =================
STRINGS = {
    "en": {
        "force_join": (
            "⚠️ **ACCESS DENIED!**\n\nYou must join our Official Channel and"
            " Group before using this bot.\n\nJoin below, then press"
            " **Verify**."
        ),
        "btn_channel": "📢 1. Join Official Channel",
        "btn_group": "👥 2. Join Official Group",
        "btn_verify": "🔄 Check / Verified",
        "not_joined": (
            "❌ You have not joined both channels yet! Please join first."
        ),
        "inbox_empty": "📭 Inbox empty! No messages received yet.",
        "vault_saved": "💾 Email saved to Vault!",
        "vault_empty": "📁 Vault is empty! No emails saved.",
        "ask_custom": (
            "✏️ **Send me your custom name** (letters & numbers only):\nExample:"
            " `syntaxboss99`"
        ),
        "invalid_custom": (
            "❌ Invalid name! Use only letters and numbers without spaces."
        ),
        "choose_domain": "🌐 **Select an available active domain:**",
        "session_deleted": "🗑 Session deleted successfully!",
    },
    "hi": {
        "force_join": (
            "⚠️ **पहुंच प्रतिबंधित!**\n\nबॉट का उपयोग करने के लिए हमारे चैनल"
            " और ग्रुप दोनों को जॉइन करना अनिवार्य है।\n\nनीचे दिए बटन से"
            " जॉइन करें और **सत्यापित करें**।"
        ),
        "btn_channel": "📢 1. चैनल जॉइन करें",
        "btn_group": "👥 2. ग्रुप जॉइन करें",
        "btn_verify": "🔄 जॉइन चेक करें",
        "not_joined": "❌ आपने अभी तक दोनों जॉइन नहीं किए हैं! कृपया जॉइन करें।",
        "inbox_empty": "📭 इनबॉक्स खाली है! अभी तक कोई मैसेज नहीं आया।",
        "vault_saved": "💾 ईमेल वॉल्ट में सेव हो गया!",
        "vault_empty": "📁 वॉल्ट खाली है! कोई ईमेल सेव नहीं है।",
        "ask_custom": (
            "✏️ **अपना मनपसंद नाम लिखकर चैट में भेजें:**\nउदाहरण:"
            " `syntaxboss99`"
        ),
        "invalid_custom": (
            "❌ गलत नाम! सिर्फ लेटर्स और नंबर्स (बिना स्पेस) का उपयोग करें।"
        ),
        "choose_domain": "🌐 **उपलब्ध एक्टिव डोमेन में से एक चुनें:**",
        "session_deleted": "🗑 सेशन सफलतापूर्वक हटा दिया गया!",
    },
    "es": {
        "force_join": (
            "⚠️ **¡ACCESO DENEGADO!**\n\nDebes unirte a nuestro Canal y Grupo"
            " para usar el bot.\n\nÚnete abajo y presiona **Verificar**."
        ),
        "btn_channel": "📢 1. Unirse al Canal",
        "btn_group": "👥 2. Unirse al Grupo",
        "btn_verify": "🔄 Verificar",
        "not_joined": "❌ ¡Aún no te has unido a ambos canales!",
        "inbox_empty": "📭 ¡Bandeja vacía! No hay mensajes nuevos.",
        "vault_saved": "💾 ¡Correo guardado en la bóveda!",
        "vault_empty": "📁 ¡La bóveda está vacía!",
        "ask_custom": (
            "✏️ **Envía tu nombre personalizado:**\nEjemplo: `syntaxboss99`"
        ),
        "invalid_custom": "❌ Formato inválido. Solo letras y números.",
        "choose_domain": "🌐 **Selecciona un dominio activo:**",
        "session_deleted": "🗑 ¡Sesión eliminada con éxito!",
    },
}


def get_text(user_id, key):
  lang = user_lang.get(user_id, "en")
  return STRINGS.get(lang, STRINGS["en"]).get(key, "")


# ================= KEEP-ALIVE SERVER (RENDER) =================
server = Flask("")


@server.route("/")
def home():
  return "SYNTAX EMPIRE BOT IS 100% OPERATIONAL!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  server.run(host="0.0.0.0", port=port)


Thread(target=run_web, daemon=True).start()


# ================= FORCE JOIN VERIFICATION =================
def check_membership(chat_id, user_id):
  try:
    member = bot.get_chat_member(chat_id, user_id)
    return member.status in ["member", "administrator", "creator"]
  except Exception as e:
    print(f"Join Check Error: {e}")
    return False


def is_user_joined_all(user_id):
  return check_membership(CHANNEL_USERNAME, user_id) and check_membership(
      GROUP_USERNAME, user_id
  )


def get_lang_markup():
  markup = types.InlineKeyboardMarkup(row_width=3)
  markup.add(
      types.InlineKeyboardButton("English 🇬🇧", callback_data="setlang_en"),
      types.InlineKeyboardButton("हिन्दी 🇮🇳", callback_data="setlang_hi"),
      types.InlineKeyboardButton("Español 🌐", callback_data="setlang_es"),
  )
  return markup


def get_force_join_markup(user_id):
  markup = types.InlineKeyboardMarkup(row_width=1)
  markup.add(
      types.InlineKeyboardButton(
          get_text(user_id, "btn_channel"), url=CHANNEL_LINK
      ),
      types.InlineKeyboardButton(
          get_text(user_id, "btn_group"), url=GROUP_LINK
      ),
      types.InlineKeyboardButton(
          get_text(user_id, "btn_verify"), callback_data="check_join"
      ),
  )
  return markup


# ================= MAIL.TM API =================
def get_mailtm_domains():
  try:
    res = requests.get(f"{MAIL_API_BASE}/domains", timeout=10)
    if res.status_code == 200:
      domains = [d["domain"] for d in res.json().get("hydra:member", [])]
      if domains:
        return domains
  except Exception as e:
    print(f"Domain fetch error: {e}")
  return ["bugfoo.com", "chitthi.in", "cevipsa.com"]


def create_mailtm_account(username=None, domain=None):
  try:
    if not domain:
      domains = get_mailtm_domains()
      domain = domains[0]
    if not username:
      username = "".join(
          random.choices(string.ascii_lowercase + string.digits, k=9)
      )

    address = f"{username}@{domain}"
    password = "".join(
        random.choices(
            string.ascii_letters + string.digits + "!@#$%", k=14
        )
    )

    res = requests.post(
        f"{MAIL_API_BASE}/accounts",
        json={"address": address, "password": password},
        timeout=10,
    )
    if res.status_code in [200, 201]:
      token_res = requests.post(
          f"{MAIL_API_BASE}/token",
          json={"address": address, "password": password},
          timeout=10,
      )
      if token_res.status_code == 200:
        return {"address": address, "token": token_res.json().get("token")}
  except Exception as e:
    print(f"Account creation error: {e}")
  return None


def fetch_mailtm_messages(token):
  try:
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(
        f"{MAIL_API_BASE}/messages", headers=headers, timeout=10
    )
    if res.status_code == 200:
      return res.json().get("hydra:member", [])
  except Exception as e:
    print(f"Messages fetch error: {e}")
  return []


def fetch_mailtm_message_content(token, msg_id):
  try:
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(
        f"{MAIL_API_BASE}/messages/{msg_id}", headers=headers, timeout=10
    )
    if res.status_code == 200:
      return res.json()
  except Exception as e:
    print(f"Message read error: {e}")
  return None


# ================= DASHBOARD UI =================
def get_dashboard_text(user_id):
  session = user_sessions.get(user_id)
  current_email = session["address"] if session else "No active session"
  return (
      "╭────────────────────────────╮\n"
      "│ ⚡ **SYNTAX EMPIRE DASHBOARD** │\n"
      "╰────────────────────────────╯\n\n"
      f"🪪 **Current Email:**\n`{current_email}`\n\n"
      "🟢 **Status:** Active & Auto-Listening\n"
      "⏱ **Allocated:** Allocated Cloud Session\n"
      "🛡 **Engine:** Fast-Track Interceptor\n"
      "⚙️ **Architecture:** Cloud 24/7 Distributed"
  )


def get_dashboard_markup():
  markup = types.InlineKeyboardMarkup(row_width=2)
  b1 = types.InlineKeyboardButton(
      "🔄 Refresh Inbox", callback_data="refresh_inbox"
  )
  b2 = types.InlineKeyboardButton(
      "💾 Save to Vault", callback_data="save_vault"
  )
  b3 = types.InlineKeyboardButton(
      "⚡ Instant Fresh Email", callback_data="instant_email"
  )
  b4 = types.InlineKeyboardButton(
      "✏️ Custom Name Email", callback_data="custom_name"
  )
  b5 = types.InlineKeyboardButton(
      "🌐 Custom Domain", callback_data="custom_domain"
  )
  b6 = types.InlineKeyboardButton(
      "📁 My Vault (Saved)", callback_data="my_vault"
  )
  b7 = types.InlineKeyboardButton(
      "🛠 Tools & Settings", callback_data="tools_settings"
  )
  b8 = types.InlineKeyboardButton(
      "🗑 Delete Session", callback_data="delete_session"
  )
  b9 = types.InlineKeyboardButton(
      "👑 Bot Owner Info", callback_data="owner_info"
  )
  b10 = types.InlineKeyboardButton(
      "👑 Syntax Community", url="https://t.me/syntaxredirect"
  )

  markup.add(b1, b2)
  markup.add(b3, b4)
  markup.add(b5, b6)
  markup.add(b7, b8)
  markup.add(b9, b10)
  return markup


# ================= COMMANDS =================
@bot.message_handler(commands=["start"])
def start_command(message):
  user_id = message.from_user.id
  user_state.pop(user_id, None)

  if user_id not in user_lang:
    bot.send_message(
        message.chat.id,
        "🌐 Choose Language / भाषा चुनें / Seleccione el idioma:",
        reply_markup=get_lang_markup(),
    )
    return

  if not is_user_joined_all(user_id):
    bot.send_message(
        chat_id=message.chat.id,
        text=get_text(user_id, "force_join"),
        parse_mode="Markdown",
        reply_markup=get_force_join_markup(user_id),
    )
    return

  if user_id not in user_sessions:
    acc = create_mailtm_account()
    if acc:
      user_sessions[user_id] = acc

  bot.send_message(
      message.chat.id,
      get_dashboard_text(user_id),
      parse_mode="Markdown",
      reply_markup=get_dashboard_markup(),
  )


# Custom Name Input Handler
@bot.message_handler(func=lambda msg: True)
def handle_text(message):
  user_id = message.from_user.id
  if user_state.get(user_id) == "waiting_custom":
    name = message.text.strip().lower()
    if name.isalnum() and len(name) >= 3:
      domains = get_mailtm_domains()
      acc = create_mailtm_account(username=name, domain=domains[0])
      if acc:
        user_sessions[user_id] = acc
        user_state.pop(user_id, None)
        bot.send_message(
            message.chat.id,
            f"✅ **Custom Email Allocated:**\n`{acc['address']}`",
            parse_mode="Markdown",
        )
        bot.send_message(
            message.chat.id,
            get_dashboard_text(user_id),
            parse_mode="Markdown",
            reply_markup=get_dashboard_markup(),
        )
      else:
        bot.send_message(
            message.chat.id,
            "❌ यह नाम पहले से इस्तेमाल में है। कोई दूसरा नाम ट्राई करें!",
        )
    else:
      bot.send_message(message.chat.id, get_text(user_id, "invalid_custom"))


# ================= CALLBACKS =================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
  user_id = call.from_user.id
  chat_id = call.message.chat.id

  # 0. Language Select
  if call.data.startswith("setlang_"):
    user_lang[user_id] = call.data.split("_")[1]
    bot.delete_message(chat_id, call.message.message_id)

    if not is_user_joined_all(user_id):
      bot.send_message(
          chat_id,
          get_text(user_id, "force_join"),
          parse_mode="Markdown",
          reply_markup=get_force_join_markup(user_id),
      )
    else:
      if user_id not in user_sessions:
        acc = create_mailtm_account()
        if acc:
          user_sessions[user_id] = acc
      bot.send_message(
          chat_id,
          get_dashboard_text(user_id),
          parse_mode="Markdown",
          reply_markup=get_dashboard_markup(),
      )
    return

  # 1. Force Join Verify
  if call.data == "check_join":
    if is_user_joined_all(user_id):
      bot.delete_message(chat_id, call.message.message_id)
      if user_id not in user_sessions:
        acc = create_mailtm_account()
        if acc:
          user_sessions[user_id] = acc
      bot.send_message(
          chat_id,
          get_dashboard_text(user_id),
          parse_mode="Markdown",
          reply_markup=get_dashboard_markup(),
      )
    else:
      bot.answer_callback_query(
          call.id, get_text(user_id, "not_joined"), show_alert=True
      )
    return

  if not is_user_joined_all(user_id):
    bot.answer_callback_query(
        call.id, get_text(user_id, "not_joined"), show_alert=True
    )
    return

  # 2. Refresh Inbox
  if call.data == "refresh_inbox":
    session = user_sessions.get(user_id)
    if not session or not session.get("token"):
      bot.answer_callback_query(call.id, "No active session!", show_alert=True)
      return

    bot.answer_callback_query(call.id, "🔄 Checking Inbox...")
    messages = fetch_mailtm_messages(session["token"])

    if not messages:
      bot.answer_callback_query(
          call.id, get_text(user_id, "inbox_empty"), show_alert=True
      )
      return

    for msg in messages[:5]:
      full_data = fetch_mailtm_message_content(session["token"], msg.get("id"))
      if full_data:
        sender = full_data.get("from", {}).get("address", "Unknown")
        subject = full_data.get("subject", "No Subject")
        intro = full_data.get("intro", "")
        text_body = full_data.get("text") or intro or "No content preview"
        date = full_data.get("createdAt", "")[:19].replace("T", " ")

        alert_msg = (
            f"📩 **New Incoming Message!**\n\n"
            f"👤 **From:** `{sender}`\n"
            f"📌 **Subject:** {subject}\n"
            f"🕒 **Time:** {date}\n\n"
            f"📝 **Body / OTP:**\n{text_body[:3500]}"
        )
        bot.send_message(chat_id, alert_msg, parse_mode="Markdown")

  # 3. Save to Vault
  elif call.data == "save_vault":
    session = user_sessions.get(user_id)
    if not session:
      bot.answer_callback_query(call.id, "No email to save!", show_alert=True)
      return
    email = session["address"]
    if user_id not in user_vaults:
      user_vaults[user_id] = []
    if email not in user_vaults[user_id]:
      user_vaults[user_id].append(email)
      bot.answer_callback_query(
          call.id, get_text(user_id, "vault_saved"), show_alert=True
      )
    else:
      bot.answer_callback_query(call.id, "Already in Vault!", show_alert=True)

  # 4. Instant Fresh Email
  elif call.data == "instant_email":
    acc = create_mailtm_account()
    if acc:
      user_sessions[user_id] = acc
      bot.answer_callback_query(call.id, "⚡ New Email Allocated!")
      try:
        bot.edit_message_text(
            get_dashboard_text(user_id),
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=get_dashboard_markup(),
        )
      except Exception:
        pass

  # 5. Custom Name Email
  elif call.data == "custom_name":
    user_state[user_id] = "waiting_custom"
    bot.answer_callback_query(call.id)
    bot.send_message(
        chat_id, get_text(user_id, "ask_custom"), parse_mode="Markdown"
    )

  # 6. Custom Domain
  elif call.data == "custom_domain":
    bot.answer_callback_query(call.id)
    domains = get_mailtm_domains()
    dom_markup = types.InlineKeyboardMarkup(row_width=1)
    for dom in domains:
      dom_markup.add(
          types.InlineKeyboardButton(
              f"🌐 @{dom}", callback_data=f"setdom_{dom}"
          )
      )
    bot.send_message(
        chat_id, get_text(user_id, "choose_domain"), reply_markup=dom_markup
    )

  elif call.data.startswith("setdom_"):
    domain = call.data.replace("setdom_", "")
    acc = create_mailtm_account(domain=domain)
    if acc:
      user_sessions[user_id] = acc
      bot.answer_callback_query(call.id, f"Allocated @{domain}")
      bot.send_message(
          chat_id,
          get_dashboard_text(user_id),
          parse_mode="Markdown",
          reply_markup=get_dashboard_markup(),
      )

  # 7. My Vault
  elif call.data == "my_vault":
    saved = user_vaults.get(user_id, [])
    if not saved:
      bot.answer_callback_query(
          call.id, get_text(user_id, "vault_empty"), show_alert=True
      )
    else:
      txt = "📁 **YOUR SAVED VAULT EMAILS:**\n\n"
      for i, mail in enumerate(saved, 1):
        txt += f"{i}. `{mail}`\n"
      bot.send_message(chat_id, txt, parse_mode="Markdown")

  # 8. Tools & Settings
  elif call.data == "tools_settings":
    bot.answer_callback_query(
        call.id,
        "🛠 Engine: Mail.tm REST Interceptor v3.0\nStatus: 100% Operational",
        show_alert=True,
    )

  # 9. Delete Session
  elif call.data == "delete_session":
    user_sessions.pop(user_id, None)
    bot.answer_callback_query(call.id, get_text(user_id, "session_deleted"))
    try:
      bot.edit_message_text(
          get_dashboard_text(user_id),
          chat_id=chat_id,
          message_id=call.message.message_id,
          parse_mode="Markdown",
          reply_markup=get_dashboard_markup(),
      )
    except Exception:
      pass

  # 10. Bot Owner Info
  elif call.data == "owner_info":
    bot.answer_callback_query(
        call.id,
        "👑 Developed by Syntax Empire\nSupport: @syntaxredirect",
        show_alert=True,
    )


# ================= START POLLING =================
if __name__ == "__main__":
  print(f"{BOT_USERNAME} 100% Final Engine running...")
  bot.infinity_polling(skip_pending=True)
