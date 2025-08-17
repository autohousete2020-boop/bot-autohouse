import os
import logging
import telebot

# --- ЛОГІНГ ---
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

# --- ЗМІННІ ОТОЧЕННЯ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # приклад: @autoternopil_bot_news або -100xxxxxxxxxxxx
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # твій Telegram ID (771396613)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in env")
if not CHANNEL_USERNAME:
    raise RuntimeError("CHANNEL_USERNAME is not set in env")
if ADMIN_CHAT_ID == 0:
    log.warning("ADMIN_CHAT_ID is not set — обмеження постингу за адміном вимкнено")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# --- Налаштовуваний футер для кожного поста ---
PHONE = "+38 096 067 01 90"
CITY = "Ternopil"
FOOTER = (
    f"\n\n<b>Контакти:</b> {PHONE}\n"
    f"🇺🇸 США | 🇪🇺 Європа ➜ 🇺🇦 Україна\n"
    f"📦 Доставка • митниця • ремонт\n"
    f"💵 Економія від 20%\n"
    f"📍 {CITY}\n"
    f"#AutoHouse #autohouse_te"
)

# --- Команди ---
@bot.message_handler(commands=["start", "help"])
def cmd_start(message: telebot.types.Message):
    text = (
        "Привіт! Я бот 🤖 AutoHouse.te.\n\n"
        "Як користуватись для постингу в канал:\n"
        "1) Надішли МЕНІ фото авто з підписом (опис/ціна/рік і т.д.).\n"
        "2) Я опублікую це в канал і додам контакти автоматично.\n\n"
        "Команди:\n"
        "/postdemo — тестовий пост у канал\n"
        "/status — перевірка стану"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=["status"])
def cmd_status(message: telebot.types.Message):
    bot.reply_to(message, "✅ Я на зв'язку. Готовий постити в канал.")

@bot.message_handler(commands=["postdemo"])
def cmd_postdemo(message: telebot.types.Message):
    if ADMIN_CHAT_ID and message.from_user.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "⛔ Лише адміністратор може відправити демо-пост.")
        return

    caption = (
        "<b>BMW 320i</b> • 2018\n"
        "Пробіг: 85 000 км\n"
        "Ціна: $12 000\n"
        "Стан: відмінний\n"
        + FOOTER
    )
    try:
        # якщо логотип завантажений у репо як logo.png — можемо відправити його як демо
        if os.path.exists("logo.png"):
            with open("logo.png", "rb") as ph:
                bot.send_photo(CHANNEL_USERNAME, ph, caption=caption)
        else:
            # без фото — просто текст
            bot.send_message(CHANNEL_USERNAME, caption)
        bot.reply_to(message, "✅ Демо-пост відправлено в канал.")
    except Exception as e:
        log.exception("postdemo error")
        bot.reply_to(message, f"⚠️ Не вдалось відправити: {e}")

# --- Постинг справжніх оголошень ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message: telebot.types.Message):
    # Дозволити постити лише тобі (адміну) — щоб ніхто чужий не заспамив канал
    if ADMIN_CHAT_ID and message.from_user.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "⛔ Лише адміністратор може публікувати в канал.")
        return

    # Беремо найбільше фото (останній елемент)
    photo = message.photo[-1].file_id
    caption = (message.caption or "Оголошення") + FOOTER

    try:
        bot.send_photo(CHANNEL_USERNAME, photo, caption=caption)
        bot.reply_to(message, "✅ Опубліковано в канал.")
    except Exception as e:
        log.exception("send_photo error")
        bot.reply_to(message, f"⚠️ Не вдалось опублікувати: {e}")

# На випадок, якщо ти випадково надішлеш текст/документ і т.д.
@bot.message_handler(func=lambda m: True, content_types=['text', 'document', 'video', 'audio'])
def fallback(message: telebot.types.Message):
    if message.text and message.text.startswith("/"):
        return  # команди вже обробляються вище
    bot.reply_to(
        message,
        "Надішли МЕНІ 📸 фото авто з підписом — я опублікую це в канал і додам контакти."
    )

if __name__ == "__main__":
    log.info("Bot started. Polling…")
    bot.infinity_polling(skip_pending=True, timeout=30)

