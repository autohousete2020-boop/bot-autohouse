# main.py
import os
import re
import logging
import telebot
from telebot import types

# ---------- ENV ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0") or "0")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()  # e.g. @autohouse_te
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()  # numeric id for private channels (optional)

if not BOT_TOKEN:
    raise RuntimeError("Env BOT_TOKEN is empty. Set BOT_TOKEN in Render → Environment.")
if not ADMIN_CHAT_ID:
    raise RuntimeError("Env ADMIN_CHAT_ID is empty.")

# ---------- BOT ----------
logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_USERNAME = None  # заповнимо після get_me()

# Пам'ять діалогів
user_state = {}   # chat_id -> step name
order_data = {}   # chat_id -> dict

def channel_target():
    """Куди постити: публічний @username або числовий id."""
    return CHANNEL_ID if CHANNEL_ID else CHANNEL_USERNAME

# --------- УТИЛІТИ ----------
PHONE_RE = re.compile(r"^\+?\d[\d\s\-\(\)]{7,}$")

def ask_make(chat_id):
    user_state[chat_id] = "make"
    bot.send_message(chat_id, "Яка марка/модель цікавить?")

def ask_budget(chat_id):
    user_state[chat_id] = "budget"
    bot.send_message(chat_id, "Який бюджет (у $)?")

def ask_year(chat_id):
    user_state[chat_id] = "year"
    bot.send_message(chat_id, "Бажаний рік випуску?")

def ask_phone(chat_id):
    user_state[chat_id] = "phone"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📞 Поділитися телефоном", request_contact=True))
    kb.add(types.KeyboardButton("Пропустити й ввести вручну"))
    bot.send_message(
        chat_id,
        "Залиште номер телефону для зв'язку.\n"
        "Натисніть кнопку нижче або надішліть номер повідомленням.",
        reply_markup=kb
    )

def clear_state(chat_id):
    user_state.pop(chat_id, None)
    order_data.pop(chat_id, None)
    bot.send_chat_action(chat_id, "typing")

def lead_card(data: dict) -> str:
    return (
        "✅ <b>Запит прийнято!</b>\n\n"
        f"• <b>Марка/модель:</b> {telebot.util.escape(data.get('make',''))}\n"
        f"• <b>Бюджет:</b> {telebot.util.escape(str(data.get('budget','')))}$\n"
        f"• <b>Рік:</b> {telebot.util.escape(str(data.get('year','')))}\n"
        f"• <b>Телефон клієнта:</b> {telebot.util.escape(data.get('phone','—'))}"
    )

def admin_lead_card(user, data: dict) -> str:
    name = telebot.util.escape(f"{user.first_name or ''} {user.last_name or ''}".strip())
    uname = f"@{user.username}" if getattr(user, 'username', None) else "—"
    uid = user.id
    return (
        "📥 <b>Нова заявка</b>\n\n"
        f"👤 <b>Клієнт:</b> {name or '—'} ({uname}), id: <code>{uid}</code>\n"
        f"📞 <b>Телефон:</b> {telebot.util.escape(data.get('phone','—'))}\n"
        f"🚗 <b>Марка/модель:</b> {telebot.util.escape(data.get('make',''))}\n"
        f"💵 <b>Бюджет:</b> {telebot.util.escape(str(data.get('budget','')))}$\n"
        f"📅 <b>Рік:</b> {telebot.util.escape(str(data.get('year','')))}"
    )

# ---------- МЕНЮ ----------
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🚗 Зробити замовлення"))
    kb.add(types.KeyboardButton("📞 Контакти"), types.KeyboardButton("ℹ️ Допомога"))
    return kb

@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    global BOT_USERNAME
    if BOT_USERNAME is None:
        me = bot.get_me()
        BOT_USERNAME = me.username

    text = (
        "<b>Привіт!</b> Це бот AutoHouse.\n"
        "Підберу авто з США/Європи під ключ.\n\n"
        "Натисни «🚗 Зробити замовлення» або /order."
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu())
    # Якщо прийшли з параметром start=lead — одразу форма
    if message.text and " " in message.text:
        _, param = message.text.split(" ", 1)
        if param.strip().lower().startswith("lead"):
            ask_make(message.chat.id)

@bot.message_handler(commands=["order"])
def cmd_order(message: types.Message):
    order_data[message.chat.id] = {}
    ask_make(message.chat.id)

@bot.message_handler(commands=["help"])
def cmd_help(message: types.Message):
    bot.send_message(
        message.chat.id,
        "Напишіть у меню «🚗 Зробити замовлення», а я задам кілька питань і передам заявку менеджеру.\n"
        "Команди: /start, /order, /post (для адміна)."
    )

@bot.message_handler(commands=["contacts", "contact"])
def cmd_contacts(message: types.Message):
    bot.send_message(
        message.chat.id,
        "📞 Телефон: <b>+38 096 067 01 90</b>\n"
        "Instagram: <a href='https://instagram.com/autohouse.te'>@autohouse.te</a>\n"
        "Адреса: Тернопіль",
        disable_web_page_preview=True
    )

@bot.message_handler(func=lambda m: m.text == "📞 Контакти")
def btn_contacts(message: types.Message):
    cmd_contacts(message)

@bot.message_handler(func=lambda m: m.text == "ℹ️ Допомога")
def btn_help(message: types.Message):
    cmd_help(message)

@bot.message_handler(func=lambda m: m.text == "🚗 Зробити замовлення")
def btn_order(message: types.Message):
    cmd_order(message)

# ---------- ФОРМА ЗАЯВКИ ----------
@bot.message_handler(content_types=["contact"])
def on_contact(message: types.Message):
    if user_state.get(message.chat.id) != "phone":
        return
    phone = message.contact.phone_number
    order_data.setdefault(message.chat.id, {})["phone"] = phone
    finish_lead(message)

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) in {"make", "budget", "year", "phone"}, content_types=["text"])
def order_steps(message: types.Message):
    chat_id = message.chat.id
    state = user_state.get(chat_id)

    if state == "make":
        order_data.setdefault(chat_id, {})["make"] = message.text.strip()
        ask_budget(chat_id)
        return

    if state == "budget":
        # просто збережемо як є; можна додати перевірку на число
        order_data.setdefault(chat_id, {})["budget"] = re.sub(r"[^\d]", "", message.text) or message.text.strip()
        ask_year(chat_id)
        return

    if state == "year":
        order_data.setdefault(chat_id, {})["year"] = re.sub(r"[^\d]", "", message.text) or message.text.strip()
        ask_phone(chat_id)
        return

    if state == "phone":
        txt = message.text.strip()
        if txt.lower().startswith("пропустити"):
            bot.send_message(chat_id, "Надішліть номер повідомленням або натисніть кнопку 'Поділитися телефоном'.")
            return
        if not PHONE_RE.match(txt):
            bot.send_message(chat_id, "Будь ласка, надішліть номер у форматі +380XXXXXXXXX.")
            return
        order_data.setdefault(chat_id, {})["phone"] = txt
        finish_lead(message)

def finish_lead(message: types.Message):
    chat_id = message.chat.id
    data = order_data.get(chat_id, {})
    # Картка клієнту
    bot.send_message(chat_id, lead_c
