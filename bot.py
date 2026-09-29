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
BOT_USERNAME = "@Temp_mail_by_syntaxbot"

CHANNEL_USERNAME = "@syntaxredirect"
CHANNEL_LINK = "https://t.me/syntaxredirect"

GROUP_USERNAME = "@syntaxkagc"
GROUP_LINK = "https://t.me/syntaxkagc"

bot = telebot.TeleBot(BOT_TOKEN)

# In-memory storage: user_id -> {'address': str, 'token': str, 'id': str}
user_sessions = {}
user_vaults = {}
user_state = {}

MAIL_API_BASE = "https://api.mail.tm"

# ================= KEEP-ALIVE SERVER (RENDER) =================
server = Flask("")


@server.route("/")
def home():
  return "SYNTAX EMPIRE BOT IS LIVE & LISTENING!"


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


def get_force_join_markup():
  markup = types.InlineKeyboardMarkup(row_width=1)
  markup.add(
      types.InlineKeyboardButton(
          "📢 1. Join Official Channel", url=CHANNEL_LINK
      ),
      types.InlineKeyboardButton("👥 2. Join Official Group", url=GROUP_LINK),
      types.InlineKeyboardButton(
          "🔄 Check / Verified", callback_data="check_join"
      ),
  )
  return markup


# ================= MAIL.TM API INTEGRATION =================
def get_mailtm_domains():
  try:
    res = requests.get(f"{MAIL_API_BASE}/domains", timeout=10)
    if res.status_code == 200:
      data = res.json()
      domains = [d["domain"] for d in data.get("hydra:member", [])]
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

    # 1. Create Account
    res = requests.post(
        f"{MAIL_API_BASE}/accounts",
        json={"address": address, "password": password},
        timeout=10,
    )
    if res.status_code in [200, 201]:
      # 2. Get JWT Token
      token_res = requests.post(
          f"{MAIL_API_BASE}/token",
          json={"address": address, "password": password},
          timeout=10,
      )
      if token_res.status_code == 200:
        token = token_res.json().get("token")
        return {"address": address, "token": token}
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
    print(f"Message content error: {e}")
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

  if not is_user_joined_all(user_id):
    bot.send_message(
        chat_id=message.chat.id,
        text=(
            "⚠️ **ACCESS DENIED!**\n\n"
            "Bot को access करने के लिए Official Channel और Group दोनों join"
            " करें।\n\n"
            "Join करने के बाद **'Check / Verified'** पर click करें।"
        ),
        parse_mode="Markdown",
        reply_markup=get_force_join_markup(),
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


# Custom Name Input
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
      bot.send_message(
          message.chat.id,
          "❌ Invalid name! केवल लेटर्स और नंबर्स (बिना स्पेस) का उपयोग करें।",
      )


# ================= CALLBACKS =================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
  user_id = call.from_user.id
  chat_id = call.message.chat.id

  # Verify Join
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
          call.id,
          "❌ Channel और Group दोनों join करें पहले!",
          show_alert=True,
      )
    return

  if not is_user_joined_all(user_id):
    bot.answer_callback_query(
        call.id, "⚠️ पहले Channel & Group join करें!", show_alert=True
    )
    return

  # 1. Refresh Inbox
  if call.data == "refresh_inbox":
    session = user_sessions.get(user_id)
    if not session or not session.get("token"):
      bot.answer_callback_query(call.id, "No active session!", show_alert=True)
      return

    bot.answer_callback_query(call.id, "🔄 Checking Inbox...")
    messages = fetch_mailtm_messages(session["token"])

    if not messages:
      bot.answer_callback_query(
          call.id, "📭 Inbox empty! No messages yet.", show_alert=True
      )
      return

    for msg in messages[:5]:
      msg_id = msg.get("id")
      full_data = fetch_mailtm_message_content(session["token"], msg_id)
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

  # 2. Save to Vault
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
          call.id, "💾 Email saved to Vault!", show_alert=True
      )
    else:
      bot.answer_callback_query(call.id, "Already in Vault!", show_alert=True)

  # 3. Instant Fresh Email
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
    else:
      bot.answer_callback_query(
          call.id, "Error generating email. Try again!", show_alert=True
      )

  # 4. Custom Name Email
  elif call.data == "custom_name":
    user_state[user_id] = "waiting_custom"
    bot.answer_callback_query(call.id)
    bot.send_message(
        chat_id,
        "✏️ **अपना मनपसंद नाम लिखकर चैट में भेजें:**\n(उदाहरण: `syntaxking99`)",
        parse_mode="Markdown",
    )

  # 5. Custom Domain
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
        chat_id,
        "🌐 **उपलब्ध एक्टिव डोमेन चुनें:**",
        reply_markup=dom_markup,
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

  # 6. My Vault
  elif call.data == "my_vault":
    saved = user_vaults.get(user_id, [])
    if not saved:
      bot.answer_callback_query(
          call.id, "📁 Vault is empty!", show_alert=True
      )
    else:
      txt = "📁 **YOUR SAVED VAULT EMAILS:**\n\n"
      for i, mail in enumerate(saved, 1):
        txt += f"{i}. `{mail}`\n"
      bot.send_message(chat_id, txt, parse_mode="Markdown")

  # 7. Tools & Settings
  elif call.data == "tools_settings":
    bot.answer_callback_query(
        call.id,
        "🛠 Engine: Mail.tm REST Interceptor v3.0\nStatus: 100% Operational",
        show_alert=True,
    )

  # 8. Delete Session
  elif call.data == "delete_session":
    user_sessions.pop(user_id, None)
    bot.answer_callback_query(call.id, "🗑 Session deleted!")
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

  # 9. Bot Owner Info
  elif call.data == "owner_info":
    bot.answer_callback_query(
        call.id,
        "👑 Developed by Syntax Empire\nSupport: @syntaxredirect",
        show_alert=True,
    )


# ================= START POLLING =================
if __name__ == "__main__":
  print(f"{BOT_USERNAME} Mail.tm engine running...")
  bot.infinity_polling(skip_pending=True)
