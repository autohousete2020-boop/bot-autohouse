# main.py
import os
import telebot

# Токен беремо з Environment Variable на Render: BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Твої контактні дані
PHONE_DISPLAY = "+38 096 067 01 90"
PHONE_TEL = "+380960670190"  # для кнопки tel:
INSTAGRAM_URL = "https://instagram.com/autohouse.te"  # заміни, якщо інший @
CITY = "Ternopil"

ABOUT_TEXT = (
    "🚗 <b>Авто з США та Європи під ключ</b>\n"
    "🇺🇸 США | 🇪🇺 Європа ➡️ 🇺🇦 Україна\n"
    f"📱 <b>{PHONE_DISPLAY}</b>\n"
    "📦 Доставка + митниця + ремонт\n"
    "💵 Економія від 20%\n"
    "✉️ Пиши в Direct\n"
    f"<i>{CITY}</i>"
)

def start_keyboard():
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(
        telebot.types.InlineKeyboardButton("📞 Подзвонити", url=f"tel:{PHONE_TEL}"),
        telebot.types.InlineKeyboardButton("📸 Instagram", url=INSTAGRAM_URL),
    )
    return kb

@bot.message_handler(commands=["start", "help"])
def on_start(message: telebot.types.Message):
    # Пробуємо відправити логотип, якщо файл є в репозиторії
    try:
        with open("logo.png", "rb") as f:
            bot.send_photo(
                message.chat.id,
                f,
                caption=ABOUT_TEXT,
                reply_markup=start_keyboard(),
            )
    except FileNotFoundError:
        # Якщо logo.png немає — просто текст
        bot.send_message(
            message.chat.id,
            ABOUT_TEXT,
            reply_markup=start_keyboard(),
        )

@bot.message_handler(func=lambda m: True, content_types=["text"])
def fallback(message: telebot.types.Message):
    bot.reply_to(
        message,
        "Напишіть /start, щоб отримати контакти та посилання 😉",
        reply_markup=start_keyboard(),
    )

if __name__ == "__main__":
    # long polling для Render Background Worker
    bot.infinity_polling(timeout=60, skip_pending=True)
