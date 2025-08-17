import os
import logging
from telebot import TeleBot, types

# ==== Налаштування через змінні оточення ====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))             # твій telegram id (для заявок і доступу до /post)
CHANNEL_ID = os.getenv("CHANNEL_ID")                   # -100xxxxxxxxxx або @username
PHONE_E164 = os.getenv("PHONE_E164", "+380960670190")  # для кнопки "Подзвонити"
PHONE_READABLE = os.getenv("PHONE_READABLE", "+38 096 067 01 90")

assert BOT_TOKEN and CHANNEL_ID, "BOT_TOKEN і CHANNEL_ID обов'язкові!"

logging.basicConfig(level=logging.INFO)
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# Пам’ять діалогів заявки (дуже проста)
orders = {}  # user_id -> {"step": str, "data": {...}}

# ===== Допоміжні =====
def is_admin(user_id: int) -> bool:
    return ADMIN_ID and user_id == ADMIN_ID

def channel_button_row():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("📞 Подзвонити", url=f"tel:{PHONE_E164}"),
        types.InlineKeyboardButton("📝 Залишити заявку", callback_data="order_start"),
    )
    return kb

def order_summary(data: dict) -> str:
    return (
        "<b>Нова заявка</b>\n"
        f"🚗 Марка/Модель: <b>{data.get('car','-')}</b>\n"
        f"💸 Бюджет: <b>{data.get('budget','-')}</b>\n"
        f"📅 Рік: <b>{data.get('year','-')}</b>\n"
        f"👤 Ім'я: <b>{data.get('name','-')}</b>\n"
        f"📞 Контакт: <b>{data.get('contact','-')}</b>\n"
        f"🆔 Користувач: <code>{data.get('username','-')}</code>"
    )

# ===== Команди в приваті =====
@bot.message_handler(commands=["start", "help"])
def start_cmd(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📝 Залишити заявку"))
    kb.add(types.KeyboardButton("📞 Контакти"))
    text = (
        "Привіт! Це бот <b>AutoHouse.te</b>.\n"
        "Я можу прийняти вашу заявку на авто та\n"
        "дати контакти.\n\n"
        "Натисніть <b>“Залишити заявку”</b> щоб почати."
    )
    bot.send_message(m.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "📞 Контакти")
def contacts_msg(m):
    bot.send_message(
        m.chat.id,
        f"📞 Телефон: <b>{PHONE_READABLE}</b>\n"
        "📍 Тернопіль\n"
        "Пишіть сюди або натисніть кнопку Подзвонити під постами в каналі.",
    )

@bot.message_handler(func=lambda m: m.text == "📝 Залишити заявку")
def order_from_menu(m):
    start_order(m)

# ===== Хендлери заявок =====
def start_order(m):
    uid = m.from_user.id
    orders[uid] = {"step": "car", "data": {"username": m.from_user.username or m.from_user.id}}
    bot.send_message(uid, "🚗 Вкажіть <b>марку та модель</b> авто (напр. BMW 3 Series).")

@bot.callback_query_handler(func=lambda c: c.data == "order_start")
def cb_order(c):
    bot.answer_callback_query(c.id)
    start_order(c.message)

@bot.message_handler(func=lambda m: orders.get(m.from_user.id, {}).get("step") == "car")
def order_car(m):
    uid = m.from_user.id
    orders[uid]["data"]["car"] = m.text.strip()
    orders[uid]["step"] = "budget"
    bot.send_message(uid, "💸 Який <b>бюджет</b>? (грн/€/$)")

@bot.message_handler(func=lambda m: orders.get(m.from_user.id, {}).get("step") == "budget")
def order_budget(m):
    uid = m.from_user.id
    orders[uid]["data"]["budget"] = m.text.strip()
    orders[uid]["step"] = "year"
    bot.send_message(uid, "📅 Який бажаний <b>рік</b>? (можна діапазон)")

@bot.message_handler(func=lambda m: orders.get(m.from_user.id, {}).get("step") == "year")
def order_year(m):
    uid = m.from_user.id
    orders[uid]["data"]["year"] = m.text.strip()
    orders[uid]["step"] = "name"
    bot.send_message(uid, "👤 Як до вас звертатись? <b>Ім'я</b>")

@bot.message_handler(func=lambda m: orders.get(m.from_user.id, {}).get("step") == "name")
def order_name(m):
    uid = m.from_user.id
    orders[uid]["data"]["name"] = m.text.strip()
    orders[uid]["step"] = "contact"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Поділитись телефоном", request_contact=True))
    bot.send_message(uid, "📞 Дайте контакт: телефон або @username", reply_markup=kb)

@bot.message_handler(content_types=["contact"])
def order_contact_share(m):
    uid = m.from_user.id
    if uid in orders and orders[uid].get("step") == "contact":
        phone = m.contact.phone_number
        orders[uid]["data"]["contact"] = phone
        finish_order(uid, m)

@bot.message_handler(func=lambda m: orders.get(m.from_user.id, {}).get("step") == "contact")
def order_contact_text(m):
    uid = m.from_user.id
    orders[uid]["data"]["contact"] = m.text.strip()
    finish_order(uid, m)

def finish_order(uid: int, m):
    data = orders[uid]["data"]
    text = order_summary(data)
    # надсилаємо адміну
    if ADMIN_ID:
        bot.send_message(ADMIN_ID, text)
    # підтвердження клієнту
    bot.send_message(uid, "✅ Дякую! Ми зв'яжемося найближчим часом.\n"
                          f"Якщо терміново — телефонуйте: <b>{PHONE_READABLE}</b>")
    orders.pop(uid, None)

# ===== Пости в канал (тільки адмін) =====
@bot.message_handler(commands=["post"])
def post_cmd(m):
    if not is_admin(m.from_user.id):
        return bot.reply_to(m, "Команда лише для адміністратора.")

    # текст після /post
    parts = m.text.split(" ", 1)
    caption = parts[1].strip() if len(parts) > 1 else "(без тексту)"

    # якщо відповідь на фото/док — шлемо медіа, інакше звичайний пост
    if m.reply_to_message and m.reply_to_message.photo:
        # беремо найбільше фото
        file_id = m.reply_to_message.photo[-1].file_id
        bot.send_photo(CHANNEL_ID, file_id, caption=caption, reply_markup=channel_button_row())
    elif m.reply_to_message and (m.reply_to_message.document or m.reply_to_message.video):
        if m.reply_to_message.document:
            bot.send_document(CHANNEL_ID, m.reply_to_message.document.file_id,
                              caption=caption, reply_markup=channel_button_row())
        else:
            bot.send_video(CHANNEL_ID, m.reply_to_message.video.file_id,
                           caption=caption, reply_markup=channel_button_row())
    else:
        bot.send_message(CHANNEL_ID, caption, reply_markup=channel_button_row())

    bot.reply_to(m, "✅ Опубліковано.")

# ===== Старт поллінгу =====
if __name__ == "__main__":
    # важливо: logger_level має бути саме числом
    logging.getLogger("telebot").setLevel(logging.INFO)
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
