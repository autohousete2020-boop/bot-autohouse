import os
import telebot
from telebot import types

# === Конфіг із ENV ===========================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "771906613"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@autohouse_te").strip()   # публічний @юзернейм каналу
BOT_USERNAME = os.getenv("BOT_USERNAME", "AutoTernopil_bot").strip()         # юзернейм бота без @

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env is missing")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# === Прості "стани" користувача для заявки ==================================
user_state = {}  # user_id -> {"step": ..., "data": {...}}

def reset_state(uid):
    user_state[uid] = {"step": None, "data": {}}

# === Клавіатури ==============================================================
def main_menu_kbd():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton("🚗 Зробити замовлення"))
    kb.row(types.KeyboardButton("📞 Контакти"), types.KeyboardButton("ℹ️ Допомога"))
    return kb

def share_phone_kbd():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row(types.KeyboardButton("📲 Поділитися телефоном", request_contact=True))
    kb.row(types.KeyboardButton("⬅️ Назад у меню"))
    return kb

def order_button_inline():
    url = f"https://t.me/{BOT_USERNAME}?start=order"
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("📝 Залишити заявку", url=url))
    return ikb

# === Повідомлення ============================================================
START_TEXT = """Привіт! Це бот <b>AutoHouse</b>.
Підберу авто з США/Європи під ключ.

Натисни «🚗 Зробити замовлення» або команду /order щоб залишити заявку.
Також можеш скористатися кнопками нижче."""
HELP_TEXT = """Як працює бот:
• «🚗 Зробити замовлення» — відповідай на кілька запитань і залиш свій номер.
• «📞 Контакти» — наш телефон і посилання.
• /post — (тільки для адміна) опублікувати пост у канал з кнопкою «Залишити заявку».
"""
CONTACTS_TEXT = """Наш телефон: <b>+38 096 067 01 90</b>
Сайт/Instagram/інші посилання — надішлю за запитом."""

# === /start ==================================================================
@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    text = START_TEXT
    bot.send_message(message.chat.id, text, reply_markup=main_menu_kbd())
    reset_state(message.from_user.id)
    # Якщо прийшли з deep-link ?start=order — одразу запускаємо заявку
    if message.text and "start order" in message.text.lower():
        start_order(message)

# === Меню-кнопки =============================================================
@bot.message_handler(func=lambda m: m.text in ["🚗 Зробити замовлення", "📞 Контакти", "ℹ️ Допомога"])
def menu_buttons(message: types.Message):
    if message.text == "🚗 Зробити замовлення":
        start_order(message)
    elif message.text == "📞 Контакти":
        bot.send_message(message.chat.id, CONTACTS_TEXT, reply_markup=main_menu_kbd())
    else:
        bot.send_message(message.chat.id, HELP_TEXT, reply_markup=main_menu_kbd())

# === Заявка: крок 1 — марка/модель ==========================================
def start_order(message: types.Message):
    uid = message.from_user.id
    user_state[uid] = {"step": "model", "data": {}}
    bot.send_message(message.chat.id, "Яка марка/модель цікавить?", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("step") == "model")
def order_step_model(message: types.Message):
    uid = message.from_user.id
    user_state[uid]["data"]["model"] = message.text.strip()
    user_state[uid]["step"] = "budget"
    bot.send_message(message.chat.id, "Який бюджет (у $)?")

# === Крок 2 — бюджет =========================================================
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("step") == "budget")
def order_step_budget(message: types.Message):
    uid = message.from_user.id
    user_state[uid]["data"]["budget"] = message.text.strip()
    user_state[uid]["step"] = "year"
    bot.send_message(message.chat.id, "Бажаний рік випуску?")

# === Крок 3 — рік ============================================================
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("step") == "year")
def order_step_year(message: types.Message):
    uid = message.from_user.id
    user_state[uid]["data"]["year"] = message.text.strip()
    user_state[uid]["step"] = "phone"
    bot.send_message(
        message.chat.id,
        "Залиш номер телефону (введи текстом) або натисни кнопку нижче, щоб поділитися контактом.",
        reply_markup=share_phone_kbd()
    )

# === Крок 4 — телефон ========================================================
@bot.message_handler(content_types=["contact"])
def order_step_phone_contact(message: types.Message):
    # якщо поділилися контактом
    uid = message.from_user.id
    if user_state.get(uid, {}).get("step") != "phone":
        return
    phone = message.contact.phone_number
    finish_order(message, phone)

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id, {}).get("step") == "phone")
def order_step_phone_text(message: types.Message):
    uid = message.from_user.id
    phone = message.text.strip()
    finish_order(message, phone)

def finish_order(message: types.Message, phone: str):
    uid = message.from_user.id
    data = user_state.get(uid, {}).get("data", {})
    data["phone"] = phone

    # Підтвердження клієнту
    confirm = f"""✅ Запит прийнято!

• Марка/модель: <b>{data.get('model','-')}</b>
• Бюджет: <b>{data.get('budget','-')}$</b>
• Рік: <b>{data.get('year','-')}</b>
• Телефон: <b>{data.get('phone','-')}</b>

Ми скоро зателефонуємо!
"""
    bot.send_message(message.chat.id, confirm, reply_markup=main_menu_kbd())

    # Надіслати в адмін-чат
    admin_msg = f"""📩 Нова заявка
Користувач: @{message.from_user.username or '—'} (id {message.from_user.id})
Марка/модель: {data.get('model','-')}
Бюджет: {data.get('budget','-')}$
Рік: {data.get('year','-')}
Телефон: {data.get('phone','-')}
"""
    try:
        bot.send_message(ADMIN_CHAT_ID, admin_msg)
    except Exception:
        pass

    reset_state(uid)

# === Команда /order прямо текстом ============================================
@bot.message_handler(commands=["order"])
def cmd_order(message: types.Message):
    start_order(message)

# === Пости в канал (тільки для адміна) =======================================
@bot.message_handler(commands=["post"])
def cmd_post(message: types.Message):
    if message.from_user.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "Ця команда лише для адміністратора.")
        return
    bot.reply_to(message, """Надішли <b>фото з підписом</b> — опублікую в канал з кнопкою «Залишити заявку».
(Підпис — це текст під фото).""")

@bot.message_handler(content_types=["photo"])
def handle_admin_photo(message:
