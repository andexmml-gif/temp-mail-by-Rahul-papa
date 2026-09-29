import os
import random
import string
from threading import Thread
from flask import Flask
import requests
import telebot
from telebot import types

# ================= CONFIGURATION =================
BOT_TOKEN = "8604538821:AAExD6oBo_ueJT98Ti_hCqVmx_dyGVQUDbY"
BOT_USERNAME = "@TDLE_robot"

CHANNEL_USERNAME = "@syntaxredirect"
CHANNEL_LINK = "https://t.me/syntaxredirect"

GROUP_USERNAME = "@syntaxkagc"
GROUP_LINK = "https://t.me/syntaxkagc"

bot = telebot.TeleBot(BOT_TOKEN)

# User session storage
user_emails = {}
user_vaults = {}  # user_id -> list of saved emails
user_state = {}

# ================= KEEP-ALIVE SERVER (RENDER) =================
server = Flask("")


@server.route("/")
def home():
  return "SYNTAX EMPIRE BOT IS 100% ONLINE!"


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


# ================= DASHBOARD UI BUILDER =================
def get_dashboard_text(user_id):
  current_email = user_emails.get(user_id, "No active session")
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


def generate_random_email():
  domains = get_domains()
  user = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
  return f"{user}@{random.choice(domains)}"


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
            " करना अनिवार्य है।\n\n"
            "Join करने के बाद **'Check / Verified'** पर click करें।"
        ),
        parse_mode="Markdown",
        reply_markup=get_force_join_markup(),
    )
    return

  if user_id not in user_emails:
    user_emails[user_id] = generate_random_email()

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
      domains = get_domains()
      custom_mail = f"{name}@{random.choice(domains)}"
      user_emails[user_id] = custom_mail
      user_state.pop(user_id, None)
      bot.send_message(
          message.chat.id,
          f"✅ **Custom Email Allocated:**\n`{custom_mail}`\n\nReturning to"
          " Dashboard...",
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
          "❌ Invalid name! केवल letters और numbers का इस्तेमाल करें (बिना"
          " space).",
      )


# ================= CALLBACK HANDLER =================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
  user_id = call.from_user.id
  chat_id = call.message.chat.id

  # Force Join Verify
  if call.data == "check_join":
    if is_user_joined_all(user_id):
      bot.delete_message(chat_id, call.message.message_id)
      if user_id not in user_emails:
        user_emails[user_id] = generate_random_email()
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
    email = user_emails.get(user_id)
    if not email:
      bot.answer_callback_query(call.id, "No active email!", show_alert=True)
      return

    bot.answer_callback_query(call.id, "🔄 Fetching messages...")
    login, domain = email.split("@")
    messages = fetch_inbox(login, domain)

    if not messages:
      bot.answer_callback_query(
          call.id, "📭 Inbox is empty! No new mails.", show_alert=True
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
            f"📩 **New Incoming Message!**\n\n"
            f"👤 **From:** `{sender}`\n"
            f"📌 **Subject:** {subject}\n"
            f"🕒 **Time:** {date}\n\n"
            f"📝 **Body / OTP:**\n{body[:3500]}"
        )
        bot.send_message(chat_id, full_msg, parse_mode="Markdown")

  # 2. Save to Vault
  elif call.data == "save_vault":
    email = user_emails.get(user_id)
    if not email:
      bot.answer_callback_query(call.id, "No email to save!", show_alert=True)
      return
    if user_id not in user_vaults:
      user_vaults[user_id] = []
    if email not in user_vaults[user_id]:
      user_vaults[user_id].append(email)
      bot.answer_callback_query(
          call.id, "💾 Email saved in Vault!", show_alert=True
      )
    else:
      bot.answer_callback_query(
          call.id, "Already present in Vault!", show_alert=True
      )

  # 3. Instant Fresh Email
  elif call.data == "instant_email":
    user_emails[user_id] = generate_random_email()
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
    domains = get_domains()
    dom_markup = types.InlineKeyboardMarkup(row_width=1)
    for dom in domains:
      dom_markup.add(
          types.InlineKeyboardButton(
              f"🌐 @{dom}", callback_data=f"setdom_{dom[:25]}"
          )
      )
    bot.send_message(
        chat_id,
        "🌐 **उपलब्ध डोमेन में से एक चुनें:**",
        reply_markup=dom_markup,
    )

  elif call.data.startswith("setdom_"):
    domain = call.data.replace("setdom_", "")
    user = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    user_emails[user_id] = f"{user}@{domain}"
    bot.answer_callback_query(call.id, f"Allocated @{domain}")
    bot.send_message(
        chat_id,
        get_dashboard_text(user_id),
        parse_mode="Markdown",
        reply_markup=get_dashboard_markup(),
    )

  # 6. My Vault (Saved)
  elif call.data == "my_vault":
    saved = user_vaults.get(user_id, [])
    if not saved:
      bot.answer_callback_query(
          call.id, "📁 Vault is empty! No emails saved.", show_alert=True
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
        "🛠 Engine: 1secmail High-Speed Interceptor v2.5\nStatus: Operational",
        show_alert=True,
    )

  # 8. Delete Session
  elif call.data == "delete_session":
    user_emails.pop(user_id, None)
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
  print(f"{BOT_USERNAME} SYNTAX EMPIRE UI running...")
  bot.infinity_polling(skip_pending=True)
