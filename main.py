import os
import re
import time
import logging
import telebot
from telebot import types

# -------- Logging --------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# -------- Env --------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0") or "0")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()  # @public_channel
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()              # numeric for private

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is empty")
if not ADMIN_CHAT_ID:
    raise RuntimeError("ADMIN_CHAT_ID is empty")

def channel_target():
    return CHANNEL_ID if CHANNEL_ID else CHANNEL_USERNAME

# -------- Bot --------
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_USERNAME = None

# -------- State --------
user_state = {}   # chat_id -> step
order_data = {}   # chat_id -> dict
PHONE_RE = re.compile(r"^\+?\d[\d\s\-\(\)]{7,}$")

# -------- Helpers --------
def mm():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🚗 Зробити замовлення"))
    kb.add(types.KeyboardButton("📞 Контакти"), types.KeyboardButton("ℹ️ Допомога"))
    return kb

def ask_make(cid):
    user_state[cid] = "make"
    bot.send_message(cid, "Яка марка/модель цікавить?")

def ask_budget(cid):
    user_state[cid] = "budget"
    bot.send_message(cid, "Який бюджет (у $)?")

def ask_year(cid):
    user_state[cid] = "year"
    bot.send_message(cid, "Бажаний рік випуску?")

def ask_phone(cid):
    user_state[cid] = "phone"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📞 Поділитися телефоном", request_contact=True))
    bot.send_message(cid, "Надішліть номер або поділіться контактом кнопкою нижче.", reply_markup=kb)

def clear(cid):
    user_state.pop(cid, None)
    order_data.pop(cid, None)

def lead_card(d):
    return (
        "✅ <b>Запит прийнято!</b>\n\n"
        f"• <b>Марка/модель:</b> {telebot.util.escape(d.get('make',''))}\n"
        f"• <b>Бюджет:</b> {telebot.util.escape(str(d.get('budget','')))}$\n"
        f"• <b>Рік:</b> {telebot.util.escape(str(d.get('year','')))}\n"
        f"• <b>Телефон клієнта:</b> {telebot.util.escape(d.get('phone','—'))}"
    )

def admin_lead(user, d):
    name = telebot.util.escape(f"{user.first_name or ''} {user.last_name or ''}".strip()) or "—"
    uname = f"@{user.username}" if getattr(user, "username", None) else "—"
    return (
        "📥 <b>Нова заявка</b>\n\n"
        f"👤 <b>Клієнт:</b> {name} ({uname}), id: <code>{user.id}</code>\n"
        f"📞 <b>Телефон:</b> {telebot.util.escape(d.get('phone','—'))}\n"
        f"🚗 <b>Марка/модель:</b> {telebot.util.escape(d.get('make',''))}\n"
        f"💵 <b>Бюджет:</b> {telebot.util.escape(str(d.get('budget','')))}$\n"
        f"📅 <b>Рік:</b> {telebot.util.escape(str(d.get('year','')))}"
    )

def post_kb():
    target = f"https://t.me/{BOT_USERNAME}?start=lead" if BOT_USERNAME else "https://t.me/"
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("📝 Залишити заявку", url=target))
    return ikb

# -------- Handlers (з try/except, щоб нічого не валило сервіс) --------
@bot.message_handler(commands=["start"])
def h_start(m):
    try:
        global BOT_USERNAME
        if BOT_USERNAME is None:
            BOT_USERNAME = bot.get_me().username
        text = (
            "<b>Привіт!</b> Це бот AutoHouse.\n"
            "Підберу авто з США/Європи під ключ.\n\n"
            "Натисни «🚗 Зробити замовлення» або /order."
        )
        bot.send_message(m.chat.id, text, reply_markup=mm())
        if m.text and " " in m.text:
            _, p = m.text.split(" ", 1)
            if p.strip().lower().startswith("lead"):
                ask_make(m.chat.id)
    except Exception as e:
        logging.exception("start: %s", e)

@bot.message_handler(commands=["order"])
def h_order(m):
    try:
        order_data[m.chat.id] = {}
        ask_make(m.chat.id)
    except Exception as e:
        logging.exception("order: %s", e)

@bot.message_handler(func=lambda x: x.text == "🚗 Зробити замовлення")
def h_btn_order(m):
    h_order(m)

@bot.message_handler(commands=["help"])
def h_help(m):
    try:
        bot.send_message(m.chat.id, "Команди: /start, /order, /post (для адміна).", reply_markup=mm())
    except Exception as e:
        logging.exception("help: %s", e)

@bot.message_handler(func=lambda x: x.text == "ℹ️ Допомога")
def h_btn_help(m):
    h_help(m)

@bot.message_handler(commands=["contacts","contact"])
def h_contacts(m):
    try:
        bot.send_message(
            m.chat.id,
            "📞 Телефон: <b>+38 096 067 01 90</b>\n"
            "Instagram: <a href='https://instagram.com/autohouse.te'>@autohouse.te</a>\n"
            "Адреса: Тернопіль",
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.exception("contacts: %s", e)

@bot.message_handler(func=lambda x: x.text == "📞 Контакти")
def h_btn_contacts(m):
    h_contacts(m)

@bot.message_handler(content_types=["contact"])
def h_contact(m):
    try:
        if user_state.get(m.chat.id) != "phone":
            return
        order_data.setdefault(m.chat.id, {})["phone"] = m.contact.phone_number
        finalize(m)
    except Exception as e:
        logging.exception("contact: %s", e)

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) in {"make","budget","year","phone"}, content_types=["text"])
def h_form(m):
    try:
        cid = m.chat.id
        st = user_state.get(cid)
        if st == "make":
            order_data.setdefault(cid, {})["make"] = m.text.strip()
            ask_budget(cid)
        elif st == "budget":
            order_data.setdefault(cid, {})["budget"] = re.sub(r"[^\d]", "", m.text) or m.text.strip()
            ask_year(cid)
        elif st == "year":
            order_data.setdefault(cid, {})["year"] = re.sub(r"[^\d]", "", m.text) or m.text.strip()
            ask_phone(cid)
        elif st == "phone":
            if not PHONE_RE.match(m.text.strip()):
                bot.send_message(cid, "Будь ласка, номер у форматі +380XXXXXXXXX.")
                return
            order_data.setdefault(cid, {})["phone"] = m.text.strip()
            finalize(m)
    except Exception as e:
        logging.exception("form: %s", e)

def finalize(m):
    try:
        cid = m.chat.id
        d = order_data.get(cid, {})
        bot.send_message(cid, lead_card(d), reply_markup=mm())
        try:
            bot.send_message(ADMIN_CHAT_ID, admin_lead(m.from_user, d))
        except Exception as ex:
            logging.exception("send to admin: %s", ex)
        clear(cid)
    except Exception as e:
        logging.exception("finalize: %s", e)

@bot.message_handler(commands=["post"])
def h_post_hint(m):
    try:
        if m.from_user.id != ADMIN_CHAT_ID:
            return
        bot.reply_to(m, "Надішліть <b>фото з підписом</b> — опублікую в каналі з кнопк
