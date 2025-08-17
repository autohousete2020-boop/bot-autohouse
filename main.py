# -*- coding: utf-8 -*-
import os
import logging
from datetime import datetime
from telebot import TeleBot, types

# -------------------- Налаштування --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()
CONTACT_CITY = os.getenv("CONTACT_CITY", "Ternopil")
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "https://instagram.com/autohouse.te")
PHONE_E164 = os.getenv("PHONE_E164", "+380960670190")
PHONE_READABLE = os.getenv("PHONE_READABLE", "+38 096 067 01 90")

if not BOT_TOKEN:
    raise RuntimeError("ENV BOT_TOKEN is empty")

# Якщо канал ввели без @ — додамо
if CHANNEL_USERNAME and not CHANNEL_USERNAME.startswith("@"):
    CHANNEL_USERNAME = "@" + CHANNEL_USERNAME

# Логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("bot")

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# -------------------- Пам'ять (просте FSM у RAM) --------------------
# У продакшені краще Redis/DB, але для Render Starter підійде RAM
STATE = {}          # user_id -> "brand" | "budget" | "year" | "phone" | None
LEADS = {}          # user_id -> dict(brand, budget, year, phone)

def get_state(uid): return STATE.get(uid)
def set_state(uid, val): STATE[uid] = val
def clear_state(uid): STATE.pop(uid, None)

def lead_get(uid): return LEADS.setdefault(uid, {})
def lead_set(uid, key, val): LEADS.setdefault(uid, {})[key] = val
def lead_clear(uid): LEADS.pop(uid, None)

# -------------------- Тексти --------------------
WELCOME = (
    "Привіт! Це бот <b>AutoHouse</b>.\n"
    "Підберу авто з США/Європи під ключ.\n\n"
    "Натисни «🚗 Зробити замовлення» або /order."
)

HELP_TEXT = (
    "<b>Команди</b>:\n"
    "• /start — головне меню\n"
    "• /order — створити заявку\n"
    "• /help — довідка\n"
    "• /post — (адмін) опублікувати фото/опис у канал"
)

ASK_BRAND = "Яка марка/модель цікавить?"
ASK_BUDGET = "Який бюджет (у $)?"
ASK_YEAR = "Бажаний рік випуску?"
ASK_PHONE = (
    "Залиште номер телефону (введіть цифрами) або натисніть кнопку нижче, "
    "щоб поділитися контактом."
)
ASK_PHONE_BUTTON = "📱 Поділитися телефоном"

LEAD_SAVED_FOR_USER = (
    "✅ Запит прийнято!\n"
    "• Марка/модель: <b>{brand}</b>\n"
    "• Бюджет: <b>{budget}$</b>\n"
    "• Рік: <b>{year}</b>\n"
    "• Телефон: <b>{phone}</b>\n\n"
    "Ми зв'яжемося з вами. Дякуємо!"
)

LEAD_FOR_ADMIN = (
    "🆕 <b>Нова заявка</b>\n"
    "Час: <code>{ts}</code>\n"
    "Користувач: <a href='tg://user?id={uid}'>{name}</a> (id: <code>{uid}</code>)\n\n"
    "• Марка/модель: <b>{brand}</b>\n"
    "• Бюджет: <b>{budget}$</b>\n"
    "• Рік: <b>{year}</b>\n"
    "• Телефон: <b>{phone}</b>"
)

CONTACTS_TEXT = (
    "📍 <b>{city}</b>\n"
    "📞 <b>{phone_pretty}</b>\n"
    "🔗 Instagram: {insta}"
).format(city=CONTACT_CITY, phone_pretty=PHONE_READABLE, insta=INSTAGRAM_URL)

# -------------------- Клавіатури --------------------
def main_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🚗 Зробити замовлення")
    kb.row("📞 Контакти", "ℹ️ Допомога")
    return kb

def phone_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton(text=ASK_PHONE_BUTTON, request_contact=True)
    kb.add(btn_phone)
    return kb

def post_inline_kb() -> types.InlineKeyboardMarkup:
    # Кнопка під постом у каналі, веде до бота
    url = f"https://t.me/{BOT_USERNAME}?start=from_post"
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("📝 Залишити заявку", url=url))
    return ikb

# -------------------- Команди --------------------
@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    clear_state(message.from_user.id)
    lead_clear(message.from_user.id)
    bot.send_message(message.chat.id, WELCOME, reply_markup=main_kb())

@bot.message_handler(commands=["help"])
def cmd_help(message: types.Message):
    bot.send_message(message.chat.id, HELP_TEXT, reply_markup=main_kb())

@bot.message_handler(commands=["order"])
def cmd_order(message: types.Message):
    uid = message.from_user.id
    lead_clear(uid)
    set_state(uid, "brand")
    bot.send_message(message.chat.id, ASK_BRAND, reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: m.text == "ℹ️ Допомога")
def btn_help(message: types.Message):
    cmd_help(message)

@bot.message_handler(func=lambda m: m.text == "📞 Контакти")
def btn_contacts(message: types.Message):
    bot.send_message(message.chat.id, CONTACTS_TEXT, disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == "🚗 Зробити замовлення")
def btn_order(message: types.Message):
    cmd_order(message)

# -------------------- Прийом контактів --------------------
@bot.message_handler(content_types=["contact"])
def on_contact(message: types.Message):
    uid = message.from_user.id
    phone = ""
    if message.contact and message.contact.phone_number:
        phone = message.contact.phone_number
    if phone:
        lead_set(uid, "phone", phone)
        finish_lead_if_ready(message)
    else:
        bot.send_message(message.chat.id, "❌ Не вдалось отримати номер. Введіть його текстом, будь ласка.")

# -------------------- Основний діалог замовлення --------------------
@bot.message_handler(func=lambda m: get_state(m.from_user.id) in ("brand", "budget", "year", "phone"))
def lead_flow(message: types.Message):
    uid = message.from_user.id
    step = get_state(uid)

    if step == "brand":
        lead_set(uid, "brand", message.text.strip())
        set_state(uid, "budget")
        bot.send_message(message.chat.id, ASK_BUDGET)
        return

    if step == "budget":
        budget_text = message.text.strip()
        budget = "".join(ch for ch in budget_text if ch.isdigit())
        if not budget:
            bot.send_message(message.chat.id, "❌ Ви не ввели бюджет. Спробуйте ще раз.")
            return
        lead_set(uid, "budget", budget)
        set_state(uid, "year")
        bot.send_message(message.chat.id, ASK_YEAR)
        return

    if step == "year":
        year_text = message.text.strip()
        year = "".join(ch for ch in year_text if ch.isdigit())[:4]
        if not year or len(year) < 4:
            bot.send_message(message.chat.id, "❌ Вкажіть рік числом, напр. 2018.")
            return
        lead_set(uid, "year", year)
        set_state(uid, "phone")
        bot.send_message(message.chat.id, ASK_PHONE, reply_markup=phone_kb())
        return

    if step == "phone":
        phone = message.text.strip()
        # Дозволимо + та цифри
        cleaned = "+" + "".join(ch for ch in phone if ch.isdigit())
        if len(cleaned) < 8:  # дуже короткий — попросимо ще раз
            bot.send_message(message.chat.id, "❌ Вкажіть коректний
