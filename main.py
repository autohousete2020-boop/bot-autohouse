import os
import time
import logging
import telebot
from telebot import types

# ====== ENV ======
BOT_TOKEN = os.getenv("BOT_TOKEN")  # токен бота
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # твій Telegram ID (хто може постити в канал)
# Один із двох: публічний username каналу або числовий ID (-100...)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")  # напр. @autohouse_te
CHANNEL_ID = os.getenv("CHANNEL_ID", "")              # напр. -1001234567890
PHONE_E164 = os.getenv("PHONE_E164", "+380960670190")         # для кнопки tel:
PHONE_READABLE = os.getenv("PHONE_READABLE", "+38 096 067 01 90")  # у текстах
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "")  # опційно, якщо хочеш кнопку Instagram

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

TARGET_CHANNEL = CHANNEL_ID if CHANNEL_ID else CHANNEL_USERNAME  # одне з двох обов'язково

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bot")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# На всякий випадок, щоб polling не бився з webhook
try:
    bot.delete_webhook(drop_pending_updates=True)
except Exception as e:
    log.warning(f"delete_webhook warn: {e}")

# Буде заповнено після get_me()
BOT_DEEPLINK = None  # типу https://t.me/YourBot?start=order

# ====== КНОПКИ під постом каналу ======
def channel_buttons() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    # кнопка в бота з автозапуском анкети
    order_btn = types.InlineKeyboardButton("📝 Залишити заявку", url=BOT_DEEPLINK or "https://t.me/")
    kb.add(order_btn)
    # кнопка подзвонити
    kb.add(types.InlineKeyboardButton("📞 Подзвонити", url=f"tel:{PHONE_E164}"))
    # опційно інстаграм
    if INSTAGRAM_URL:
        kb.add(types.InlineKeyboardButton("📷 Instagram", url=INSTAGRAM_URL))
    return kb

# ====== МЕНЮ у приваті ======
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton("📝 Залишити заявку"))
    kb.row(types.KeyboardButton("📞 Контакти"), types.KeyboardButton("ℹ️ Допомога"))
    return kb

def cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("❌ Скасувати"))
    return kb

# ====== ПРОСТА FSM для анкети ======
STATE = {}   # user_id -> step
DATA = {}    # user_id -> dict

def reset_user(uid: int):
    STATE.pop(uid, None)
    DATA.pop(uid, None)

def start_order(chat_id: int, from_user):
    STATE[chat_id] = "car"
    DATA[chat_id] = {"by": f"@{from_user.username}" if from_user.username else str(from_user.id)}
    bot.send_message(chat_id, "🚗 Вкажи марку/модель (напр. BMW 320i):", reply_markup=cancel_kb())

@bot.message_handler(commands=["start"])
def cmd_start(m: types.Message):
    # deep link /start order -> одразу запускаємо анкету
    payload = m.text.split(maxsplit=1)[1].strip() if len(m.text.split(maxsplit=1)) == 2 else ""
    if payload.startswith("order"):
        start_order(m.chat.id, m.from_user)
        return
    bot.send_message(
        m.chat.id,
        "Привіт! Це бот <b>AutoHouse</b>.\n"
        "Підберу авто з США/Європи під ключ.\n\n"
        "Натисни «📝 Залишити заявку» або /order.",
        reply_markup=main_kb()
    )

@bot.message_handler(commands=["help"])
def cmd_help(m: types.Message):
    bot.send_message(
        m.chat.id,
        "Команди:\n"
        "• /order — оформити заявку\n"
        "• /contacts — контакти\n"
        "• /post <текст> — пост у канал (лише адмін)\n"
        "• (як адмін) надішли ФОТО з підписом — я опублікую в канал з кнопками",
        reply_markup=main_kb()
    )

@bot.message_handler(commands=["contacts"])
def cmd_contacts(m: types.Message):
    bot.send_message(
        m.chat.id,
        f"📞 <b>{PHONE_READABLE}</b>\n"
        "📍 Тернопіль\n"
        + (f"Instagram: {INSTAGRAM_URL}" if INSTAGRAM_URL else ""),
        reply_markup=main_kb(),
        disable_web_page_preview=True
    )

@bot.message_handler(commands=["order"])
def cmd_order(m: types.Message):
    start_order(m.chat.id, m.from_user)

@bot.message_handler(func=lambda msg: msg.text == "📝 Залишити заявку")
def btn_order(m: types.Message):
    start_order(m.chat.id, m.from_user)

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id) == "car")
def st_car(m: types.Message):
    if m.text == "❌ Скасувати":
        reset_user(m.from_user.id); bot.reply_to(m, "Скасовано.", reply_markup=main_kb()); return
    DATA[m.from_user.id]["car"] = m.text.strip()
    STATE[m.from_user.id] = "budget"
    bot.send_message(m.chat.id, "💸 Який бюджет (у $, грн або €)?", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id) == "budget")
def st_budget(m: types.Message):
    if m.text == "❌ Скасувати":
        reset_user(m.from_user.id); bot.reply_to(m, "Скасовано.", reply_markup=main_kb()); return
    DATA[m.from_user.id]["budget"] = m.text.strip()
    STATE[m.from_user.id] = "year"
    bot.send_message(m.chat.id, "📅 Бажаний рік випуску? (можна діапазон)", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id) == "year")
def st_year(m: types.Message):
    if m.text == "❌ Скасувати":
        reset_user(m.from_user.id); bot.reply_to(m, "Скасовано.", reply_markup=main_kb()); return
    DATA[m.from_user.id]["year"] = m.text.strip()
    STATE[m.from_user.id] = "name"
    bot.send_message(m.chat.id, "👤 Як до тебе звертатись? (ім'я)", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id) == "name")
def st_name(m: types.Message):
    if m.text == "❌ Скасувати":
        reset_user(m.from_user.id); bot.reply_to(m, "Скасовано.", reply_markup=main_kb()); return
    DATA[m.from_user.id]["name"] = m.text.strip()
    STATE[m.from_user.id] = "contact"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Поділитись телефоном", request_contact=True))
    kb.add(types.KeyboardButton("❌ Скасувати"))
    bot.send_message(m.chat.id, "📞 Дай номер телефону або @нік:", reply_markup=kb)

@bot.message_handler(content_types=["contact"])
def st_contact_share(m: types.Message):
    if STATE.get(m.from_user.id) != "contact":
        return
    DATA[m.from_user.id]["contact"] = m.contact.phone_number
    finish_order(m)

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id) == "contact")
def st_contact_text(m: types.Message):
    if m.text == "❌ Скасувати":
        reset_user(m.from_user.id); bot.reply_to(m, "Скасовано.", reply_markup=main_kb()); return
    DATA[m.from_user.id]["contact"] = m.text.strip()
    finish_order(m)

def finish_order(m: types.Message):
    uid = m.from_user.id
    d = DATA.get(uid, {})
    text = (
        "🆕 <b>Нова заявка</b>\n"
        f"👤 {d.get('name','-')} ({d.get('by','-')})\n"
        f"🚗 {d.get('car','-')}\n"
        f"💸 {d.get('budget','-')}\n"
        f"📅 {d.get('year','-')}\n"
        f"📞 {d.get('contact','-')}"
    )
