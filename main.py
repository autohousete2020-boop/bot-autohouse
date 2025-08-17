import os
import logging
from telebot import TeleBot, types

# -------------------- ЛОГІНГ --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("bot")

# -------------------- ENV --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()  # формат: @your_channel
CONTACT_PHONE = os.getenv("CONTACT_PHONE", "+380000000000")
CONTACT_CITY = os.getenv("CONTACT_CITY", "Ternopil")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not ADMIN_CHAT_ID:
    raise RuntimeError("ADMIN_CHAT_ID is not set")
if not CHANNEL_USERNAME:
    log.warning("CHANNEL_USERNAME is empty. /post у канал працювати не буде, доки не задасте @username каналу.")

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# -------------------- СТАНИ КОРИСТУВАЧІВ --------------------
# Простий FSM на словниках
user_state = {}        # user_id -> {"step": ..., "data": {...}}
STATE_NONE = "NONE"
STATE_ORDER_MAKE = "ORDER_MAKE"
STATE_POST = "POST"

def reset_state(uid: int):
    user_state[uid] = {"step": None, "data": {}, "mode": STATE_NONE}

# -------------------- КНОПКИ --------------------
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton("🚗 Зробити замовлення"))
    kb.row(types.KeyboardButton("📞 Контакти"), types.KeyboardButton("ℹ️ Допомога"))
    return kb

def post_cta_inline(bot_username: str):
    # Кнопка "Залишити заявку" під постом у каналі → відкриває бота з параметром start=order
    url = f"https://t.me/{bot_username}?start=order"
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("📝 Залишити заявку", url=url))
    return ikb

# -------------------- ХЕНДЛЕРИ --------------------
@bot.message_handler(commands=["start"])
def cmd_start(m: types.Message):
    uid = m.from_user.id
    text = ( "Привіт! Це бот <b>AutoHouse</b>.\n"
             "Підберу авто з США/Європи під ключ.\n\n"
             "Натисни «🚗 Зробити замовлення» або команду /order.\n"
             "Щоб опублікувати оголошення в канал — /post." )
    reset_state(uid)

    # якщо прийшов deep-link ?start=order → одразу запускаємо форму замовлення
    if m.text and ("start order" in m.text or m.text.strip() == "/start order"):
        return start_order_flow(m)
    bot.send_message(m.chat.id, text, reply_markup=main_menu())

@bot.message_handler(commands=["help"])
def cmd_help(m: types.Message):
    bot.send_message(
        m.chat.id,
        "Основні команди:\n"
        "/start — головне меню\n"
        "/order — оформити заявку\n"
        "/post — зробити пост у канал (бот має бути адміном каналу)\n"
        "/contacts — контакти",
        reply_markup=main_menu()
    )

@bot.message_handler(commands=["contacts"])
def cmd_contacts(m: types.Message):
    bot.send_message(
        m.chat.id,
        f"📞 Телефон: <b>{CONTACT_PHONE}</b>\n📍 Місто: {CONTACT_CITY}",
        reply_markup=main_menu()
    )

# ----------- ЗАМОВЛЕННЯ -----------
@bot.message_handler(commands=["order"])
def start_order_flow(m: types.Message):
    uid = m.from_user.id
    user_state[uid] = {"mode": STATE_ORDER_MAKE, "step": "car", "data": {}}
    bot.send_message(m.chat.id, "Яка марка/модель цікавить?", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda msg: user_state.get(msg.from_user.id, {}).get("mode") == STATE_ORDER_MAKE)
def order_flow(m: types.Message):
    uid = m.from_user.id
    st = user_state.get(uid, {})
    step = st.get("step")
    data = st.get("data", {})

    if step == "car":
        data["car"] = m.text.strip()
        st["step"] = "budget"
        bot.send_message(m.chat.id, "Який бюджет (у $)?")
    elif step == "budget":
        data["budget"] = m.text.strip()
        st["step"] = "year"
        bot.send_message(m.chat.id, "Бажаний рік випуску?")
    elif step == "year":
        data["year"] = m.text.strip()
        # Підсумок
        summary = (
            "✅ Запит прийнято!\n\n"
            f"• Марка/модель: <b>{data.get('car')}</b>\n"
            f"• Бюджет: <b>{data.get('budget')}$</b>\n"
            f"• Рік: <b>{data.get('year')}</b>\n\n"
            f"Ми зв'яжемось із вами. Телефон: <b>{CONTACT_PHONE}</b>"
        )
        bot.send_message(m.chat.id, summary, reply_markup=main_menu())

        # Відправляємо заявку адміну в особисті
        try:
            bot.send_message(
                ADMIN_CHAT_ID,
                f"🆕 <b>Нова заявка</b>\n"
                f"Від: {m.from_user.first_name} (@{m.from_user.username or '—'}) [id {uid}]\n"
                f"Марка/модель: {data.get('car')}\n"
                f"Бюджет: {data.get('budget')}$\n"
                f"Рік: {data.get('year')}"
            )
        except Exception as e:
            log.error(f"Не вдалось надіслати адміну: {e}")

        reset_state(uid)
    else:
        reset_state(uid)
        bot.send_message(m.chat.id, "Почнемо спочатку. Натисни «🚗 Зробити замовлення» або /order.", reply_markup=main_menu())

# Кнопка меню
@bot.message_handler(func=lambda m: m.text == "🚗 Зробити замовлення")
def menu_make_order(m: types.Message):
    start_order_flow(m)

@bot.message_handler(func=lambda m: m.text == "📞 Контакти")
def menu_contacts(m: types.Message):
    cmd_contacts(m)

@bot.message_handler(func=lambda m: m.text == "ℹ️ Допомога")
def menu_help(m: types.Message):
    cmd_help(m)

# ----------- /post: створення поста у канал -----------
@bot.message_handler(commands=["post"])
def start_post_flow(m: types.Message):
    if not CHANNEL_USERNAME:
        bot.send_message(m.chat.id, "❗️Не задано CHANNEL_USERNAME у Environment. Додайте @юзернейм каналу та зробіть бота адміністратором.")
        return
    uid = m.from_user.id
    user_state[uid] = {"mode": STATE_POST, "step": "title", "data": {}}
    bot.send_message(m.chat.id, "Надішли <b>заголовок</b> для поста (рядком).", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda msg: user_state.get(msg.from_user.id, {}).get("mode") == STATE_POST)
def post_flow(m: types.Message):
    uid = m.from_user.id
    st = user_state.get(uid, {})
    step = st.get("step")
    data = st.get("data", {})

    if step == "title":
        data["title"] = m.text.strip()
        st["step"] = "desc"
        bot.send_message(m.chat.id, "Добре. Тепер надішли <b>опис</b> (можна кілька рядків).")
    elif step == "desc":
        data["desc"] = m.text
        st["step"] = "photo_q"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row(types.KeyboardButton("Додати фото"), types.KeyboardButton("Без фото"))
        bot.send_message(m.chat.id, "Додати фото до поста?", reply_markup=kb)
    elif step == "photo_q":
        if m.text == "Додати фото":
            st["step"] = "photo"
            bot.send_message(m.chat.id, "Надішли <b>фото</b> одним знімком.", reply_markup=ty
