import os
import random
import string
from threading import Thread
from flask import Flask
import requests
import telebot
from telebot import types

# ================= CONFIGURATION =================
BOT_TOKEN = "8604538821:AAEXkRMTPA5jnuyI0YzNaiyeCelBuWhWJe4"
BOT_USERNAME = "@TDLE_robot"

CHANNEL_USERNAME = "@syntaxredirect"
CHANNEL_LINK = "https://t.me/syntaxredirect"

GROUP_USERNAME = "@syntaxkagc"
GROUP_LINK = "https://t.me/syntaxkagc"

bot = telebot.TeleBot(BOT_TOKEN)

user_emails = {}
user_lang = {}
user_state = {}  # Tracks user input state for custom username

# ================= MULTI-LANGUAGE STRINGS =================
STRINGS = {
    "en": {
        "welcome": (
            f"👋 Welcome to {BOT_USERNAME}!\n\nGenerate disposable temporary"
            " emails, choose custom names/domains, and receive OTPs instantly."
        ),
        "force_join": (
            "⚠️ **Access Denied!**\n\nYou must join our Channel and Group"
            " first.\n\nJoin below, then press **Verify**."
        ),
        "btn_channel": "📢 1. Join Channel",
        "btn_group": "👥 2. Join Group",
        "btn_verify": "🔄 Check / Verify",
        "btn_gen": "🎲 Random Email",
        "btn_custom": "✏️ Custom Name",
        "btn_domain": "🌐 Choose Domain",
        "btn_inbox": "📥 Check Inbox",
        "btn_del": "🗑 Delete Email",
        "btn_lang": "🌐 Change Language",
        "verified_success": "✅ Verification Successful! Choose an option:",
        "not_joined": (
            "❌ You have not joined both channels yet! Please join first."
        ),
        "mail_generated": (
            "✅ **Your Temporary Email:**\n`{email}`\n\n👉 Use this email,"
            " then click **Check Inbox** to view OTPs."
        ),
        "inbox_empty": (
            "📭 Inbox is empty! ({email})\nNo incoming messages yet."
        ),
        "no_email": "⚠️ No active email! Generate or create one first.",
        "mail_deleted": "🗑 Email deleted successfully!",
        "ask_custom_name": (
            "✏️ **Send me your custom name** (letters & numbers only):\nExample:"
            " `rahulboss99`"
        ),
        "invalid_custom_name": (
            "❌ Invalid format! Use only letters and numbers without spaces."
        ),
        "choose_domain_txt": (
            "🌐 Select a domain to generate an email with that domain:"
        ),
    },
    "hi": {
        "welcome": (
            f"👋 {BOT_USERNAME} में आपका स्वागत है!\n\nटेम्परेरी ईमेल जनरेट"
            " करें, अपनी पसंद का कस्टम नाम/डोमेन चुनें और तुरंत OTP पाएं।"
        ),
        "force_join": (
            "⚠️ **पहुंच प्रतिबंधित!**\n\nबॉट का उपयोग करने के लिए चैनल और ग्रुप"
            " जॉइन करना अनिवार्य है।\n\nनीचे दिए बटन से जॉइन करें और"
            " **सत्यापित करें**।"
        ),
        "btn_channel": "📢 1. चैनल जॉइन करें",
        "btn_group": "👥 2. ग्रुप जॉइन करें",
        "btn_verify": "🔄 जॉइन चेक करें",
        "btn_gen": "🎲 रैंडम ईमेल",
        "btn_custom": "✏️ कस्टम नाम ईमेल",
        "btn_domain": "🌐 डोमेन चुनें",
        "btn_inbox": "📥 इनबॉक्स देखें",
        "btn_del": "🗑 ईमेल हटाएं",
        "btn_lang": "🌐 भाषा बदलें",
        "verified_success": "✅ सत्यापन सफल हुआ! अब आप उपयोग कर सकते हैं:",
        "not_joined": "❌ आपने अभी तक दोनों जॉइन नहीं किए हैं!",
        "mail_generated": (
            "✅ **आपका टेम्प ईमेल:**\n`{email}`\n\n👉 इसे OTP के लिए इस्तेमाल"
            " करें, फिर **इनबॉक्स देखें** दबाएं।"
        ),
        "inbox_empty": (
            "📭 इनबॉक्स खाली है! ({email})\nअभी कोई नया मैसेज नहीं मिला।"
        ),
        "no_email": "⚠️ कोई सक्रिय ईमेल नहीं मिला! पहले नया ईमेल बनाएं।",
        "mail_deleted": "🗑 ईमेल सफलतापूर्वक हटा दिया गया!",
        "ask_custom_name": (
            "✏️ **अपना मनपसंद नाम लिखकर भेजें** (सिर्फ लेटर्स और"
            " नंबर):\nउदाहरण: `rahulboss99`"
        ),
        "invalid_custom_name": (
            "❌ गलत नाम! सिर्फ बिना स्पेस के लेटर्स और नंबर का इस्तेमाल करें।"
        ),
        "choose_domain_txt": (
            "🌐 नीचे दिए गए डोमेन में से अपनी पसंद का डोमेन चुनें:"
        ),
    },
    "es": {
        "welcome": (
            f"👋 ¡Bienvenido a {BOT_USERNAME}!\n\nGenera correos temporales,"
            " elige nombre/dominio personalizado y recibe OTPs."
        ),
        "force_join": (
            "⚠️ **¡Acceso denegado!**\n\nDebes unirte a nuestro Canal y"
            " Grupo.\n\nÚnete abajo y presiona **Verificar**."
        ),
        "btn_channel": "📢 1. Unirse al Canal",
        "btn_group": "👥 2. Unirse al Grupo",
        "btn_verify": "🔄 Verificar",
        "btn_gen": "🎲 Correo Aleatorio",
        "btn_custom": "✏️ Nombre Personalizado",
        "btn_domain": "🌐 Elegir Dominio",
        "btn_inbox": "📥 Ver Mensajes",
        "btn_del": "🗑 Eliminar Correo",
        "btn_lang": "🌐 Cambiar Idioma",
        "verified_success": "✅ ¡Verificación exitosa!",
        "not_joined": "❌ ¡Aún no te has unido a ambos!",
        "mail_generated": (
            "✅ **Tu Correo:**\n`{email}`\n\n👉 Úsalo y luego pulsa **Ver"
            " Mensajes**."
        ),
        "inbox_empty": "📭 ¡Bandeja vacía! ({email})",
        "no_email": "⚠️ ¡No tienes correo activo!",
        "mail_deleted": "🗑 ¡Correo eliminado con éxito!",
        "ask_custom_name": (
            "✏️ **Envía tu nombre personalizado** (solo letras y"
            " números):\nEjemplo: `rahulboss99`"
        ),
        "invalid_custom_name": "❌ Formato inválido. Solo letras y números.",
        "choose_domain_txt": "🌐 Selecciona un dominio:",
    },
}


def get_text(user_id, key):
  lang = user_lang.get(user_id, "en")
  return STRINGS.get(lang, STRINGS["en"]).get(key, "")


# ================= KEEP-ALIVE SERVER (RENDER) =================
server = Flask("")


@server.route("/")
def home():
  return f"{BOT_USERNAME} is Live and Running!"


def run_web():
  port = int(os.environ.get("PORT", 8080))
  server.run(host="0.0.0.0", port=port)


Thread(target=run_web, daemon=True).start()


# ================= FORCE JOIN CHECK =================
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


# ================= KEYBOARDS =================
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


def get_main_menu_markup(user_id):
  markup = types.InlineKeyboardMarkup(row_width=2)
  b_rand = types.InlineKeyboardButton(
      get_text(user_id, "btn_gen"), callback_data="gen_random"
  )
  b_custom = types.InlineKeyboardButton(
      get_text(user_id, "btn_custom"), callback_data="gen_custom"
  )
  b_domain = types.InlineKeyboardButton(
      get_text(user_id, "btn_domain"), callback_data="choose_domain"
  )
  b_inbox = types.InlineKeyboardButton(
      get_text(user_id, "btn_inbox"), callback_data="check_inbox"
  )
  b_del = types.InlineKeyboardButton(
      get_text(user_id, "btn_del"), callback_data="delete_mail"
  )
  b_lang = types.InlineKeyboardButton(
      get_text(user_id, "btn_lang"), callback_data="change_lang"
  )

  markup.add(b_rand, b_custom)
  markup.add(b_domain, b_inbox)
  markup.add(b_del, b_lang)
  return markup


def get_domain_markup(domains):
  markup = types.InlineKeyboardMarkup(row_width=1)
  for dom in domains:
    markup.add(
        types.InlineKeyboardButton(
            f"@{dom}", callback_data=f"seldom_{dom[:25]}"
        )
    )
  return markup


# ================= 1SECMAIL API =================
def get_domains():
  try:
    res = requests.get(
        "https://www.1secmail.com/api/v1/?action=getDomainList", timeout=10
    )
    if res.status_code == 200:
      return res.json()
  except Exception:
    pass
  return ["1secmail.com", "1secmail.org", "1secmail.net"]


def fetch_inbox(login, domain):
  try:
    res = requests.get(
        f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}",
        timeout=10,
    )
    return res.json() if res.status_code == 200 else []
  except Exception:
    return []


def fetch_message_content(login, domain, msg_id):
  try:
    res = requests.get(
        f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}",
        timeout=10,
    )
    return res.json() if res.status_code == 200 else None
  except Exception:
    return None


# ================= BOT COMMANDS =================
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
        message.chat.id,
        get_text(user_id, "force_join"),
        parse_mode="Markdown",
        reply_markup=get_force_join_markup(user_id),
    )
    return

  bot.send_message(
      message.chat.id,
      get_text(user_id, "welcome"),
      reply_markup=get_main_menu_markup(user_id),
  )


# Text Handler for Custom Name input
@bot.message_handler(func=lambda msg: True)
def handle_text(message):
  user_id = message.from_user.id
  if user_state.get(user_id) == "waiting_custom_name":
    name = message.text.strip().lower()
    # Check if alphanumeric
    if name.isalnum() and len(name) >= 3:
      domain = random.choice(get_domains())
      custom_mail = f"{name}@{domain}"
      user_emails[user_id] = custom_mail
      user_state.pop(user_id, None)
      bot.send_message(
          message.chat.id,
          get_text(user_id, "mail_generated").format(email=custom_mail),
          parse_mode="Markdown",
          reply_markup=get_main_menu_markup(user_id),
      )
    else:
      bot.send_message(message.chat.id, get_text(user_id, "invalid_custom_name"))


# ================= CALLBACK QUERIES =================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
  user_id = call.from_user.id
  chat_id = call.message.chat.id

  # Language Selection
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
      bot.send_message(
          chat_id,
          get_text(user_id, "welcome"),
          reply_markup=get_main_menu_markup(user_id),
      )
    return

  if call.data == "change_lang":
    bot.send_message(
        chat_id, "🌐 Select language:", reply_markup=get_lang_markup()
    )
    return

  # Force Join Verify
  if call.data == "check_join":
    if is_user_joined_all(user_id):
      bot.delete_message(chat_id, call.message.message_id)
      bot.send_message(
          chat_id,
          get_text(user_id, "verified_success"),
          reply_markup=get_main_menu_markup(user_id),
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

  # 1. Random Email
  if call.data == "gen_random":
    bot.answer_callback_query(call.id)
    domains = get_domains()
    user = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{user}@{random.choice(domains)}"
    user_emails[user_id] = email
    bot.send_message(
        chat_id,
        get_text(user_id, "mail_generated").format(email=email),
        parse_mode="Markdown",
        reply_markup=get_main_menu_markup(user_id),
    )

  # 2. Custom Name Email
  elif call.data == "gen_custom":
    user_state[user_id] = "waiting_custom_name"
    bot.answer_callback_query(call.id)
    bot.send_message(
        chat_id, get_text(user_id, "ask_custom_name"), parse_mode="Markdown"
    )

  # 3. Choose Custom Domain
  elif call.data == "choose_domain":
    bot.answer_callback_query(call.id)
    domains = get_domains()
    bot.send_message(
        chat_id,
        get_text(user_id, "choose_domain_txt"),
        reply_markup=get_domain_markup(domains),
    )

  # Domain Selected Callback
  elif call.data.startswith("seldom_"):
    domain = call.data.replace("seldom_", "")
    user = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{user}@{domain}"
    user_emails[user_id] = email
    bot.answer_callback_query(call.id, f"Domain @{domain} set!")
    bot.send_message(
        chat_id,
        get_text(user_id, "mail_generated").format(email=email),
        parse_mode="Markdown",
        reply_markup=get_main_menu_markup(user_id),
    )

  # 4. Check Inbox
  elif call.data == "check_inbox":
    email = user_emails.get(user_id)
    if not email:
      bot.answer_callback_query(
          call.id, get_text(user_id, "no_email"), show_alert=True
      )
      return

    bot.answer_callback_query(call.id, "Checking Inbox...")
    login, domain = email.split("@")
    messages = fetch_inbox(login, domain)

    if not messages:
      bot.send_message(
          chat_id,
          get_text(user_id, "inbox_empty").format(email=email),
          reply_markup=get_main_menu_markup(user_id),
      )
      return

    for msg in messages[:5]:
      content = fetch_message_content(login, domain, msg.get("id"))
      if content:
        sender = content.get("from", "Unknown")
        subject = content.get("subject", "No Subject")
        date = content.get("date", "")
        body = (
            content.get("textBody")
            or content.get("body")
            or "No content preview"
        )

        full_msg = (
            f"📩 **New Message!**\n\n👤 **From:** `{sender}`\n📌"
            f" **Subject:** {subject}\n🕒 **Date:** {date}\n\n📝"
            f" **Content/OTP:**\n{body[:3500]}"
        )
        bot.send_message(chat_id, full_msg, parse_mode="Markdown")

    bot.send_message(
        chat_id, "Inbox updated.", reply_markup=get_main_menu_markup(user_id)
    )

  # 5. Delete Email
  elif call.data == "delete_mail":
    if user_id in user_emails:
      del user_emails[user_id]
      bot.answer_callback_query(call.id, get_text(user_id, "mail_deleted"))
      bot.send_message(
          chat_id,
          get_text(user_id, "mail_deleted"),
          reply_markup=get_main_menu_markup(user_id),
      )
    else:
      bot.answer_callback_query(
          call.id, get_text(user_id, "no_email"), show_alert=True
      )


# ================= START POLLING =================
if __name__ == "__main__":
  print(f"{BOT_USERNAME} running with Custom Name & Domain support...")
  bot.infinity_polling(skip_pending=True)
