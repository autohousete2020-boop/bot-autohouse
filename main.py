import os
import logging
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ---------- Налаштування логів ----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger("bot")

# ---------- Змінні середовища ----------
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # число у вигляді рядка — конвертуємо нижче
CHANNEL_ID = os.getenv("CHANNEL_ID")  # @public_name або -100xxxxxxxxxx
PHONE_E164 = os.getenv("PHONE_E164", "+380960670190")
PHONE_READABLE = os.getenv("PHONE_READABLE", "+38 096 067 01 90")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# ---------- Бот ----------
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Вимикаємо вебхук на всяк випадок (щоб polling не ловив 409)
try:
    bot.delete_webhook(drop_pending_updates=True)
except Exception as e:
    log.warning(f"delete_webhook failed: {e}")

def is_admin(chat_id) -> bool:
    try:
        return ADMIN_ID is not None and int(chat_id) == int(ADMIN_ID)
    except Exception:
        return False

# ---------- Клавіатура ----------
def main_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🚗 Зробити замовлення"))
    kb.add(KeyboardButton("📞 Контакти"), KeyboardButton("ℹ️ Допомога"))
    return kb

# ---------- Старт/Хелп ----------
@bot.message_handler(commands=["start"])
def cmd_start(m):
    bot.reply_to(
        m,
        "<b>Привіт!</b> Це бот <b>AutoHouse</b>.\n"
        "Підберу авто з США/Європи під ключ.\n\n"
        "Натисни «🚗 Зробити замовлення» або /order.",
        reply_markup=main_kb(),
    )

@bot.message_handler(commands=["help"])
def cmd_help(m):
    bot.reply_to(
        m,
        "Команди:\n"
        "/order – залишити заявку\n"
        "/contact – контакти\n"
        "/post <текст> – публікація в канал (лише адмін)",
        reply_markup=main_kb(),
    )

@bot.message_handler(commands=["contact"])
def cmd_contact(m):
    bot.reply_to(m, f"📞 Телефон: <b>{PHONE_READABLE}</b>", reply_markup=main_kb())

# ---------- Проста форма заявки ----------
STATE = {}         # user_id -> назва кроку
LEAD = {}          # user_id -> тимчасові відповіді

def ask(m, text):
    return bot.send_message(m.chat.id, text)

@bot.message_handler(commands=["order"])
def cmd_order(m):
    STATE[m.from_user.id] = "brand"
    LEAD[m.from_user.id] = {}
    ask(m, "Яка марка/модель цікавить?")

@bot.message_handler(func=lambda m: m.text == "🚗 Зробити замовлення")
def btn_order(m):
    cmd_order(m)

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id) == "brand")
def step_brand(m):
    LEAD[m.from_user.id]["brand"] = m.text.strip()
    STATE[m.from_user.id] = "budget"
    ask(m, "Який бюджет (у $)?")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id) == "budget")
def step_budget(m):
    LEAD[m.from_user.id]["budget"] = m.text.strip()
    STATE[m.from_user.id] = "year"
    ask(m, "Бажаний рік випуску?")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id) == "year")
def step_year(m):
    LEAD[m.from_user.id]["year"] = m.text.strip()
    data = LEAD.pop(m.from_user.id, {})
    STATE.pop(m.from_user.id, None)

    summary = (
        "🆕 <b>Нова заявка</b>\n"
        f"👤 {m.from_user.first_name or ''} @{m.from_user.username or ''}\n"
        f"🚗 Модель: {data.get('brand','-')}\n"
        f"💵 Бюджет: {data.get('budget','-')}\n"
        f"📅 Рік: {data.get('year','-')}\n"
        f"📞 {PHONE_READABLE}"
    )

    # Відправляємо адміну
    try:
        if ADMIN_ID:
            bot.send_message(int(ADMIN_ID), summary)
    except Exception as e:
        log.error(f"send to admin failed: {e}")

    # Підтвердження користувачу
    bot.reply_to(m, "Дякую! Ми вже обробляємо вашу заявку. Очікуйте на контакт ☎️", reply_markup=main_kb())

# ---------- Публікація в канал (для адміна) ----------
@bot.message_handler(commands=["post"])
def cmd_post(m):
    if not is_admin(m.from_user.id):
        return bot.reply_to(m, "Команда доступна лише адміну.")

    text = m.text.partition(" ")[2].strip()
    if not CHANNEL_ID:
        return bot.reply_to(m, "CHANNEL_ID не налаштований у Render → Environment.")
    if not text:
        return bot.reply_to(m, "Приклад: /post Продамо Audi A6 2018…")

    try:
        bot.send_message(CHANNEL_ID, text, disable_web_page_preview=False)
        bot.reply_to(m, "Опубліковано ✅")
    except Exception as e:
        log.error(f"post failed: {e}")
        bot.reply_to(m, f"Помилка публікації: {e}")

# ---------- Запуск ----------
if __name__ == "__main__":
    log.info("Bot started. Polling…")
    # allowed_updates обмежує типи подій та робить polling стабільнішим
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20, allowed_updates=["message"])
