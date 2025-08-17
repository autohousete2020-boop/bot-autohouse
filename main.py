import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1) Токен беремо з Environment Variables (BOT_TOKEN)
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# 2) Текст вітання
WELCOME_TEXT = (
    "🚗 Авто з США та Європи під ключ\n"
    "🇺🇸 США | 🇪🇺 Європа ➡️ 🇺🇦 Україна\n"
    "📱 +38 096 067 01 90\n"
    "📦 Доставка + митниця + ремонт\n"
    "💵 Економія від 20%\n"
    "✉️ Пиши в Direct\n"
    "📍Ternopil"
)

# 3) Посилання для кнопок (за потреби підміниш)
CALL_URL = "tel:+380960670190"
TG_URL   = "https://t.me/AutoTernopil_bot"       # або лінк на твій профіль/чат
IG_URL   = "https://instagram.com/autohouse.te"  # підстав свій інстаграм
SITE_URL = "https://autohouse.te"                # якщо немає сайту — можеш забрати кнопку

def main_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📞 Подзвонити", url=CALL_URL))
    kb.add(InlineKeyboardButton("💬 Написати в Telegram", url=TG_URL))
    kb.add(InlineKeyboardButton("📷 Instagram", url=IG_URL))
    kb.add(InlineKeyboardButton("🌐 Сайт", url=SITE_URL))
    return kb

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    # 4) Шлях до лого (файл уже в корені репозиторію як logo.png)
    logo_path = "logo.png"
    try:
        with open(logo_path, "rb") as photo:
            bot.send_photo(
                message.chat.id,
                photo,
                caption=WELCOME_TEXT,
                reply_markup=main_keyboard()
            )
    except FileNotFoundError:
        # Якщо раптом немає файлу — відправимо тільки текст
        bot.send_message(message.chat.id, WELCOME_TEXT, reply_markup=main_keyboard())

# 5) Запускаємо довге опитування
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
