import os
import logging
from typing import Dict, Any, Optional

from telebot import TeleBot, types

# --------- Конфіг із ENV ---------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0").strip() or 0)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()  # можна з @ або без
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip()          # наприклад AutoTernopil_bot
CONTACT_CITY = os.getenv("CONTACT_CITY", "Ternopil").strip()
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "https://instagram.com/autohouse.te").strip()
PHONE_E164 = os.getenv("PHONE_E164", "+380960670190").strip()
PHONE_READABLE = os.getenv("PHONE_READABLE", "+38 096 067 01 90").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is empty. Set env BOT_TOKEN.")

# Нормалізуємо ім'я каналу (@ додаємо за потреби)
if CHANNEL_USERNAME and not CHANNEL_USERNAME.startswith("@"):
    CHANNEL_USERNAME = "@" + CHANNEL_USERNAME

# Логування (без рядків рівнів — раніше це давало TypeError)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

bot = TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=True)

# --------- Прості "стани" користувачів ---------
USER_STATE: Dict[int, Dict[str, Any]] = {}

# --------- Клавіатури ---------
def main_menu_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("🚗 Зробити замовлення"),
        types.KeyboardButton("📞 Контакти"),
        types.KeyboardButton("ℹ️ Допомога"),
    )
    return kb

def share_phone_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📱 Поділитись номером", request_contact=True))
    kb.add(types.KeyboardButton("Пропустити"))
    return kb

def inline_order_button() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    # Deep-link для старту бота з параметром "order"
    if BOT_USERNAME:
        url = f"https://t.me/{BOT_USERNAME}?start=order"
    else:
        # Фолбек: просто відкрити бот
        url = "https://t.me/"
    kb.add(types.InlineKeyboardButton("Залишити заявку", url=url))
    return kb

# --------- Тексти (залишив по суті як були, лише акуратно оформив) ---------
WELCOME_TEXT = (
    "Привіт! Це бот <b>AutoHouse</b>.\n"
    "Підберу авто з США/Європи під ключ.\n\n"
    "Натисни «🚗 Зробити замовлення» або /order."
)

HELP_TEXT = (
    "Я можу:\n"
    "• Прийняти заявку на підбір авто — натисни «🚗 Зробити замовлення» або /order\n"
    "• Опублікувати твій пост у каналі (для адміністратора) — команда /post\n\n"
    "Постав запитання у відповідь на це повідомлення — допоможу 🙂"
)

CONTACTS_TEXT = (
    f"Телефон: <b>{PHONE_READABLE}</b>\n"
    f"Місто: <b>{CONTACT_CITY}</b>\n"
    f"Instagram: <a href=\"{INSTAGRAM_URL}\">{INSTAGRAM_URL}</a>"
)

ADMIN_POST_HINT = (
    "Надішли <b>фото з підписом</b> — опублікую в каналі та додам кнопку «Залишити заявку».\n"
    "Або надішли просто текст — опублікую як текстовий пост.\n\n"
    "Канал: <b>{channel}</b>"
)

ASK_BRAND = "Яка марка/модель цікавить?"
ASK_BUDGET = "Який бюджет (у $)?"
ASK_YEAR = "Бажаний рік випуску?"
ASK_PHONE = (
    "Залиш свій номер телефону (написом) або натисни кнопку нижче, щоб поділитись контактом."
)

LEAD_OK_TMPL = (
    "✅ Запит прийнято!\n"
    "• Марка/модель: <b>{brand}</b>\n"
    "• Бюджет: <b>{budget}$</b>\n"
    "• Рік: <b>{year}</b>\n"
    "• Телефон: <b>{phone}</b>\n\n"
    "Ми зв'яжемось із вами найближчим часом."
)

ADMIN_LEAD_TMPL = (
    "🔔 <b>Новий лід</b>\n"
    "Користувач: {name} (@{username}, id={uid})\n"
    "Марка/модель: {brand}\n"
    "Бюджет: {budget}$\n"
    "Рік: {year}\n"
    "Телефон: {phone}"
)

# --------- Хелпери станів ---------
def reset_state(user_id: int) -> None:
    USER_STATE[user_id] = {"step": None, "data": {}}

def set_step(user_id: int, step: str) -> None:
    state = USER_STATE.setdefault(user_id, {"step": None, "data": {}})
    state["step"] = step

def get_step(user_id: int) -> Optional[str]:
    return USER_STATE.get(user_id, {}).get("step")

def save_answer(user_id: int, key: str, value: Any) -> None:
    state = USER_STATE.setdefault(user_id, {"step": None, "data": {}})
    state["data"][key] = value

def get_data(user_id: int) -> Dict[str, Any]:
    return USER_STATE.get(user_id, {}).get("data", {})

# --------- Команди ---------
@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    # deep-link ?start=order
    if message.text and message.text.strip().startswith("/start") and "order" in message.text:
        reset_state(message.from_user.id)
        set_step(message.from_user.id, "brand")
        bot.send_message(message.chat.id, ASK_BRAND, reply_markup=types.ReplyKeyboardRemove())
        return

    bot.send_message(message.chat.id, WELCOME_TEXT, reply_markup=main_menu_kb())

@bot.message_handler(commands=["help"])
def cmd_help(message: types.Message):
    bot.send_message(message.chat.id, HELP_TEXT, reply_markup=main_menu_kb())

@bot.message_handler(commands=["order"])
def cmd_order(message: types.Message):
    reset_state(message.from_user.id)
    set_step(message.from_user.id, "brand")
    bot.send_message(message.chat.id, ASK_BRAND, reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=["post"])
def cmd_post(message: types.Message):
    if message.from_user.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "Ця команда тільки для адміністратора.")
        return
    text = ADMIN_POST_HINT.format(channel=CHANNEL_USERNAME or "(не задано)")
    bot.reply_to(message, text)

# --------- Кнопки головного меню ---------
@bot.message_handler(func=lambda m: m.text == "🚗 Зробити замовлення")
def menu_order(message: types.Message):
    cmd_order(message)

@bot.message_handler(func=lambda m: m.text == "📞 Контакти")
def menu_contacts(message: types.Message):
    bot.send_message(message.chat.id, CONTACTS_TEXT, disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text == "ℹ️ Допомога")
def menu_help(message: types.Message):
    cmd_help(message)

# --------- Прийом ліда ---------
@bot.message_handler(content_types=["contact"])
def on_contact(message: types.Message):
    # контакт користувача
    phone = message.contact.phone_number if message.contact else ""
    save_answer(message.from_user.id, "phone", phone or "не вказано")
    finish_lead_if_ready(message)

@bot.message_handler(func=lambda m: get_step(m.from_user.id) in {"brand", "budget", "year", "phone"} and m.content_type == "text")
def lead_flow(message: types.Message):
    uid = message.from_user.id
    step = get_step(uid)

    if step == "brand":
        save_answer(uid, "brand", message.text.strip())
        set_step(uid, "budget")
        bot.send_message(message.chat.id, ASK_BUDGET)
        return

    if step == "budget":
        budget = "".join(ch for ch in message.text if ch.isdigit())
        if not budget:
