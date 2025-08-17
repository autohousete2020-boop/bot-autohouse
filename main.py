# -*- coding: utf-8 -*-
import os
import logging
import re
from typing import Dict, Any

import telebot
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    Contact,
)

# -------------------- CONFIG --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "771906613"))
# Публічний канал: тільки username БЕЗ @, наприклад "autohouse_te"
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()  # приклад: autohouse_te
# Якщо плануєш приватний канал, краще завести CHANNEL_ID = "-100xxxxxxxxxx"
# і далі використовувати саме його у bot.send_photo(CHANNEL_ID, ...)

if not BOT_TOKEN:
    raise RuntimeError("ENV BOT_TOKEN не заданий.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
me = bot.get_me()
BOT_LINK = f"https://t.me/{me.username}"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

# -------------------- ДЕРЖАВА ДЛЯ ЗАМОВЛЕНЬ --------------------
# Проста памʼять у RAM для кроків замовлення
user_state: Dict[int, Dict[str, Any]] = {}
# Флаг очікування посту після /post
awaiting_post_photo: Dict[int, bool] = {}

ASK_MODEL = "ask_model"
ASK_BUDGET = "ask_budget"
ASK_YEAR = "ask_year"
ASK_PHONE = "ask_phone"

# -------------------- ДОП. КНОПКИ --------------------
def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🚗 Зробити замовлення")
    kb.row("📞 Контакти", "ℹ️ Допомога")
    return kb

def contact_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("📱 Надіслати номер телефону", request_contact=True))
    kb.add(KeyboardButton("🔙 Скасувати"))
    return kb

def order_button_inline() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup()
    # deep-link повертає користувача в бота і стартує форму
    m.add(InlineKeyboardButton("📝 Залишити заявку", url=f"{BOT_LINK}?start=order"))
    return m

# -------------------- ДОПОМОЖНІ --------------------
def sanitize_text(s: str) -> str:
    """Очищення зайвих пробілів/переносів, безпечне для HTML."""
    return re.sub(r"\s+", " ", s).strip()

def valid_budget(text: str) -> bool:
    return bool(re.fullmatch(r"\d{1,9}", text.replace(" ", "")))

def valid_year(text: str) -> bool:
    return bool(re.fullmatch(r"(19[6-9]\d|20\d{2})", text.strip()))

def normalize_phone(raw: str) -> str:
    # Проста нормалізація: залишаємо + та цифри
    s = re.sub(r"[^\d+]", "", raw)
    return s

def lead_text(lead: Dict[str, Any]) -> str:
    brand = sanitize_text(lead.get("brand", "—"))
    budget = sanitize_text(lead.get("budget", "—"))
    year = sanitize_text(lead.get("year", "—"))
    phone = sanitize_text(lead.get("phone", "—"))

    return (
        "✅ <b>Запит прийнято!</b>\n"
        f"• <b>Марка/модель:</b> {brand}\n"
        f"• <b>Бюджет:</b> {budget}$\n"
        f"• <b>Рік:</b> {year}\n\n"
        f"Наш менеджер звʼяжеться з вами. "
        f"<b>Телефон:</b> {phone}"
    )

def admin_lead_text(user: telebot.types.User, lead: Dict[str, Any]) -> str:
    return (
        "🆕 <b>Нова заявка</b>\n"
        f"👤 Користувач: <b>{user.first_name or ''} {user.last_name or ''}</b> @{user.username or '—'} (id {user.id})\n\n"
        f"{lead_text(lead)}"
    )

# -------------------- ХЕНДЛЕРИ --------------------
@bot.message_handler(commands=["start"])
def cmd_start(message: Message):
    # Підтримка deep-link /start order
    if message.text and " " in message.text:
        arg = message.text.split(" ", 1)[1].strip()
        if arg.lower().startswith("order"):
            _start_order(message)
            return

    welcome = (
        "Привіт! Це бот <b>AutoHouse</b>.\n"
        "Підберу авто з США/Європи під ключ.\n\n"
        "Натисни «🚗 Зробити замовлення», щоб залишити заявку."
    )
    bot.reply_to(message, welcome, reply_markup=main_menu_kb())

@bot.message_handler(func=lambda m: m.text == "ℹ️ Допомога", content_types=["text"])
@bot.message_handler(commands=["help"])
def cmd_help(message: Message):
    bot.reply_to(
        message,
        "Щоб оформити заявку — натисни «🚗 Зробити замовлення» або команду /order.\n"
        "Для публікації в канал — у приваті з ботом введи /post і далі надішли <b>фото з підписом</b>.",
        reply_markup=main_menu_kb(),
    )

@bot.message_handler(func=lambda m: m.text == "📞 Контакти", content_types=["text"])
def contacts(message: Message):
    bot.reply_to(
        message,
        "📞 <b>Контакти</b>\n"
        "Телефон: +38 096 067 01 90\n"
        "Instagram: https://instagram.com/autohouse.te\n"
        "Місто: Тернопіль",
        reply_markup=main_menu_kb(),
    )

@bot.message_handler(commands=["order"])
@bot.message_handler(func=lambda m: m.text == "🚗 Зробити замовлення", content_types=["text"])
def start_order(message: Message):
    _start_order(message)

def _start_order(message: Message):
    user_state[message.from_user.id] = {"step": ASK_MODEL}
    bot.reply_to(message, "Яка марка/модель цікавить?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("🔙 Скасувати")))

@bot.message_handler(content_types=["text"])
def on_text(message: Message):
    uid = message.from_user.id
    if message.text == "🔙 Скасувати":
        user_state.pop(uid, None)
        awaiting_post_photo.pop(uid, None)
        bot.reply_to(message, "Скасовано. Оберіть дію з меню.", reply_markup=main_menu_kb())
        return

    # Обробка кроків заявки
    st = user_state.get(uid)
    if st:
        step = st.get("step")

        if step == ASK_MODEL:
            st["brand"] = sanitize_text(message.text)
            st["step"] = ASK_BUDGET
            bot.reply_to(message, "Який бюджет (у $)?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("🔙 Скасувати")))
            return

        if step == ASK_BUDGET:
            val = message.text.replace(" ", "")
            if not valid_budget(val):
                bot.reply_to(message, "Введіть бюджет цифрами, наприклад: 15000")
                return
            st["budget"] = val
            st["step"] = ASK_YEAR
            bot.reply_to(message, "Бажаний рік випуску?")
            return

        if step == ASK_YEAR:
            if not valid_year(message.text.strip()):
                bot.reply_to(message, "Введіть рік, наприклад: 2018")
                return
            st["year"] = message.text.strip()
            st["step"] = ASK_PHONE
            bot.reply_to(
                message,
                "Залиште номер телефону (можна у форматі +380...) "
                "або натисніть кнопку:",
                reply_markup=contact_kb(),
            )
            return

        if step == ASK_PHONE:
            phone = normalize_phone(message.text)
            if len(phone) < 10:
                bot.reply_to(message, "Будь ласка, вкажіть дійсний номер. Приклад: +380960000000")
                return
