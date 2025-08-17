import os
import logging
from telebot import TeleBot, types

# ============ CONFIG ============
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables")

# Адмін для отримання заявок (твій ID)
try:
    ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "771906613"))
except ValueError:
    ADMIN_CHAT_ID = 771906613

# Канал для публікацій (/post). Може бути '@username' або -100XXXXXXXXXX
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()  # optional

# Логування
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("autohouse")

# ===============================

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")
user_state = {}  # chat_id -> dict

# ---------- helpers ----------
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🚗 Зробити замовлення"))
    kb.row(types.KeyboardButton("📞 Контакти"), types.KeyboardButton("ℹ️ Допомога"))
    return kb

def clear_state(chat_id):
    user_state.pop(chat_id, None)

def ask_car(chat_id):
    bot.send_message(chat_id, "Яка марка/модель цікавить?", reply_markup=types.ReplyKeyboardRemove())
    # наступний крок: бюджет буде зареєстровано у handler тексту

def deep_link_button():
    # Кнопка «Залишити заявку» під постом у каналі
    try:
        username = bot.get_me().username
    except Exception:
        username = ""
    url = f"https://t.me/{username}?start=order" if username else "https://t.me/"
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("📝 Залишити заявку", url=url))
    return ikb

# ---------- start / menu ----------
@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    # deep-link ?start=order -> одразу анкета
    arg = message.text.split(maxsplit=1)
    if len(arg) > 0 and " " in message.text:
        # старі клієнти Telegram можуть передавати через пробіл
        pass
    # через /start startparam у нових клієнтів:
    # message.text виглядає як "/start order"
    parts = message.text.split(maxsplit=1)
    if len(parts) == 2 and parts[1].strip().lower() == "order":
        start_order(message)
        return

    text = (
        "Привіт! Це бот <b>AutoHouse</b>.\n"
        "Підберу авто з США/Європи під ключ.\n\n"
        "Натисни «🚗 Зробити замовлення»."
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "ℹ️ Допомога")
def on_help(message: types.Message):
    text = (
        "Можу допомогти з підбором авто під ключ: США 🇺🇸 / Європа 🇪🇺 → Україна 🇺🇦\n"
        "Почни з кнопки «🚗 Зробити замовлення», відповідай на кілька запитань, і я зв’яжусь."
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📞 Контакти")
def on_contacts(message: types.Message):
    text = (
        "📞 <b>Авто з США та Європи під ключ</b>\n"
        "• Доставка + митниця + ремонт\n"
        "• Економія від 20%\n\n"
        "Зв'язок: +38 096 067 01 90\n"
        "Instagram: https://instagram.com/autohouse.te"
    )
    bot.send_message(message.chat.id, text, disable_web_page_preview=True)

# ---------- order flow ----------
@bot.message_handler(commands=["order"])
def start_order(message: types.Message):
    chat_id = message.chat.id
    clear_state(chat_id)
    user_state[chat_id] = {}
    ask_car(chat_id)

@bot.message_handler(func=lambda m: m.text == "🚗 Зробити замовлення")
def order_btn(message: types.Message):
    start_order(message)

@bot.message_handler(func=lambda m: m.chat.id in user_state and "car" not in user_state[m.chat.id])
def step_car(message: types.Message):
    chat_id = message.chat.id
    user_state[chat_id]["car"] = message.text.strip()
    bot.send_message(chat_id, "Який бюджет (у $)?")
    # Далі чекаємо бюджет

@bot.message_handler(func=lambda m: m.chat.id in user_state and "budget" not in user_state[m.chat.id] and "car" in user_state[m.chat.id])
def step_budget(message: types.Message):
    chat_id = message.chat.id
    user_state[chat_id]["budget"] = message.text.strip()
    bot.send_message(chat_id, "Бажаний рік випуску?")
    # Далі чекаємо рік

@bot.message_handler(func=lambda m: m.chat.id in user_state and "year" not in user_state[m.chat.id] and "budget" in user_state[m.chat.id])
def step_year(message: types.Message):
    chat_id = message.chat.id
    user_state[chat_id]["year"] = message.text.strip()

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📱 Надати мій номер", request_contact=True))
    bot.send_message(chat_id, "Введіть ваш номер телефону або натисніть кнопку нижче ⬇️", reply_markup=kb)
    # Далі чекаємо телефон

@bot.message_handler(content_types=["contact"])
def got_contact(message: types.Message):
    # Якщо юзер натиснув кнопку «Надати мій номер»
    chat_id = message.chat.id
    if chat_id not in user_state:
        return
    phone = message.contact.phone_number
    finish_order_with_phone(chat_id, phone)

@bot.message_handler(func=lambda m: m.chat.id in user_state and "phone" not in user_state[m.chat.id] and m.content_type == "text")
def step_phone_text(message: types.Message):
    # Якщо юзер ввів телефон текстом
    chat_id = message.chat.id
    phone = message.text.strip()
    finish_order_with_phone(chat_id, phone)

def finish_order_with_phone(chat_id: int, phone: str):
    user_state[chat_id]["phone"] = phone
    data = user_state[chat_id]

    summary = (
        "✅ <b>Запит прийнято!</b>\n\n"
        f"• <b>Марка/модель:</b> {data.get('car','—')}\n"
        f"• <b>Бюджет:</b> {data.get('budget','—')}$\n"
        f"• <b>Рік:</b> {data.get('year','—')}\n"
        f"• <b>Телефон:</b> {data.get('phone','—')}\n\n"
        "Ми з вами скоро зв’яжемось!"
    )
    bot.send_message(chat_id, summary, reply_markup=main_menu())

    admin_text = (
        "🔔 <b>НОВЕ ЗАМОВЛЕННЯ</b>\n\n"
        f"Марка/модель: {data.get('car','—')}\n"
        f"Бюджет: {data.get('budget','—')}$\n"
        f"Рік: {data.get('year','—')}\n"
        f"Телефон клієнта: {data.get('phone','—')}"
    )
    try:
        bot.send_message(ADMIN_CHAT_ID, admin_text)
    except Exception as e:
        log.error(f"Can't send to admin: {e}")

    clear_state(chat_id)

# ---------- posting to channel (optional) ----------
@bot.message_handler(commands=["post"])
def cmd_post(message: types.Message):
    """
    Простий режим публікації в канал:
    - доступно тільки адміну (ADMIN_CHAT_ID)
    - попросимо надіслати фото з підписом або просто текст
    - опублікуємо в CHANNEL_USERNAME (якщо задано), додамо кнопку «Залишити заявку»
    """
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "Ця команда доступна тільки адміну.")
        return

    if not CHANNEL_USERNAME:
        bot.reply_to(message, "Не задано CHANNEL_USERNAME в змінних середовища.")
        return

    bot.reply_to(message, "Надішли <b>фото з підписом</b> або пр
