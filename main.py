# -*- coding: utf-8 -*-
import os
import re
import logging
from typing import Dict, Any

import telebot
from telebot import types

# --------------------------
# Логування
# --------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger(__name__)

# --------------------------
# Конфіг з Environment
# --------------------------
def env(name: str, default: str = "") -> str:
    v = os.getenv(name, default if default is not None else "")
    return v.strip() if isinstance(v, str) else v

BOT_TOKEN = env("BOT_TOKEN")
ADMIN_CHAT_ID_STR = env("ADMIN_CHAT_ID")
BOT_USERNAME = env("BOT_USERNAME")  # без @
CHANNEL_USERNAME = env("CHANNEL_USERNAME")  # з @
INSTAGRAM_URL = env("INSTAGRAM_URL", "https://instagram.com/")
CONTACT_CITY = env("CONTACT_CITY", "")
PHONE_E164 = env("PHONE_E164", "")
PHONE_READABLE = env("PHONE_READABLE", "")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN is not set")
    raise SystemExit(1)

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_STR)
except Exception:
    logger.error("ADMIN_CHAT_ID must be integer; got: %r", ADMIN_CHAT_ID_STR)
    raise SystemExit(1)

if not BOT_USERNAME:
    logger.error("BOT_USERNAME is not set (e.g. AutoTernopil_bot)")
    raise SystemExit(1)

if not CHANNEL_USERNAME.startswith("@"):
    logger.error("CHANNEL_USERNAME must start with @ (e.g. @autohouse_te)")
    raise SystemExit(1)

# --------------------------
# Створюємо бота
# --------------------------
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", use_class_middlewares=False)

# На всякий випадок — прибираємо webhook, щоб не було 409
try:
    bot.remove_webhook()
except Exception as e:
    logger.warning("remove_webhook warning: %s", e)

# --------------------------
# Прості тексти (щоб не ламалися лапки)
# --------------------------
WELCOME_TEXT = (
    "Привіт! Це бот <b>AutoHouse</b>.\n"
    "Підберу авто з США/Європи під ключ.\n\n"
    "Натисни «🚗 Зробити замовлення» або /order."
)

HELP_TEXT = (
    "Як це працює:\n"
    "1) Тисни «🚗 Зробити замовлення».\n"
    "2) Вкажи марку/модель, бюджет і бажаний рік.\n"
    "3) Надішли свій номер (кнопкою або текстом).\n"
    "Ми зв’яжемося з тобою найближчим часом."
)

CONTACTS_TEXT = (
    "Зв’язок:\n"
    f"• Телефон: <b>{PHONE_READABLE}</b>\n"
    f"• Instagram: {INSTAGRAM_URL}\n"
    f"• Місто: {CONTACT_CITY}"
)

# --------------------------
# Стан користувачів (простий FSM у пам'яті)
# --------------------------
user_state: Dict[int, Dict[str, Any]] = {}

def reset_state(uid: int):
    user_state[uid] = {"step": None, "brand": None, "budget": None, "year": None, "phone": None}

reset_kb = types.ReplyKeyboardRemove()

def main_menu_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(types.KeyboardButton("🚗 Зробити замовлення"))
    kb.add(types.KeyboardButton("📞 Контакти"), types.KeyboardButton("ℹ️ Допомога"))
    return kb

def share_phone_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📲 Поділитися номером", request_contact=True))
    kb.add(types.KeyboardButton("⬅️ Назад"))
    return kb

def order_button_inline() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    deep_link = f"https://t.me/{BOT_USERNAME}?start=order"
    kb.add(types.InlineKeyboardButton("Оставить заявку", url=deep_link))
    return kb

# --------------------------
# Валідація телефону (якщо текстом)
# --------------------------
PHONE_RE = re.compile(r"^\+?\d[\d\-\s]{7,}$")

def normalize_phone(text: str) -> str:
    t = text.strip()
    # допускаємо початок з + та пробіли/дефіси
    if PHONE_RE.match(t):
        return t
    return ""

# --------------------------
# Хендлери команд/кнопок
# --------------------------
@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    uid = message.from_user.id
    reset_state(uid)

    # deep-link параметр
    arg = ""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2:
            arg = parts[1].strip()
    except Exception:
        pass

    if arg.lower().startswith("order"):
        # одразу у форму
        user_state[uid]["step"] = "brand"
        bot.send_message(uid, "Яка марка/модель цікавить?", reply_markup=reset_kb)
        return

    bot.send_message(uid, WELCOME_TEXT, reply_markup=main_menu_kb())

@bot.message_handler(commands=["help"])
def cmd_help(message: types.Message):
    bot.send_message(message.chat.id, HELP_TEXT, reply_markup=main_menu_kb())

@bot.message_handler(commands=["order"])
def cmd_order(message: types.Message):
    uid = message.from_user.id
    reset_state(uid)
    user_state[uid]["step"] = "brand"
    bot.send_message(uid, "Яка марка/модель цікавить?", reply_markup=reset_kb)

@bot.message_handler(func=lambda m: m.text == "ℹ️ Допомога")
def btn_help(message: types.Message):
    bot.send_message(message.chat.id, HELP_TEXT, reply_markup=main_menu_kb())

@bot.message_handler(func=lambda m: m.text == "📞 Контакти")
def btn_contacts(message: types.Message):
    bot.send_message(message.chat.id, CONTACTS_TEXT, reply_markup=main_menu_kb())

@bot.message_handler(func=lambda m: m.text == "🚗 Зробити замовлення")
def btn_order(message: types.Message):
    uid = message.from_user.id
    reset_state(uid)
    user_state[uid]["step"] = "brand"
    bot.send_message(uid, "Яка марка/модель цікавить?", reply_markup=reset_kb)

# --------------------------
# Діалог оформлення замовлення
# --------------------------
@bot.message_handler(content_types=["contact"])
def on_contact(message: types.Message):
    uid = message.from_user.id
    if uid not in user_state or user_state[uid].get("step") != "phone":
        return
    phone = message.contact.phone_number
    user_state[uid]["phone"] = phone
    finish_order(uid, message)

@bot.message_handler(func=lambda m: True, content_types=["text"])
def on_text(message: types.Message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    # Назад з клавіатури телефону
    if text == "⬅️ Назад":
        bot.send_message(uid, "Скасовано. Повернув головне меню.", reply_markup=main_menu_kb())
        reset_state(uid)
        return

    st = user_state.get(uid)
    if not st or not st.get("step"):
        # поза діалогом
        return

    step = st["step"]

    if step == "brand":
        st["brand"] = text
        st["step"] = "budget"
        bot.send_message(uid, "Який бюджет (у $)?")
        return

    if step == "budget":
        st["budget"] = text
        st["step"] = "year"
        bot.send_message(uid, "Бажаний рік випуску?")
        return

    if step == "year":
        st["year"] = text
        st["step"] = "phone"
        bot.send_message(
            uid,
            "Надішли свій номер телефону.\n"
