import os
import telebot
from telebot import types

# --- Конфіг з оточення ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@autohouse_te")   # для публічного каналу можна @username
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()

# Перетворюємо ADMIN_CHAT_ID у int, якщо заданий
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID) if ADMIN_CHAT_ID.isdigit() else None

if not BOT_TOKEN:
    raise RuntimeError("Env BOT_TOKEN is required")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# ---- Допоміжне: перевірка адміна ----
def is_admin(user_id: int) -> bool:
    # Якщо ADMIN_CHAT_ID не заданий — дозволяємо всім (зручно на етапі тестів)
    if ADMIN_CHAT_ID is None:
        return True
    return user_id == ADMIN_CHAT_ID


# ---- Команди ----
@bot.message_handler(commands=['start'])
def cmd_start(message: types.Message):
    text = (
        "Привіт! Це бот <b>AutoHouse.te</b> 🚗\n\n"
        "Я можу публікувати пости у ваш канал.\n"
        "Спробуй:\n"
        "• <b>/post</b> Текст повідомлення — опублікує текст у канал\n"
        "• Просто надішли <b>фото з підписом</b> — опублікую фото у канал\n"
        "• <b>/postlogo</b> — опублікувати логотип + опис + телефон\n"
        "• <b>/id</b> — покажу твій Telegram ID (щоб додати як ADMIN_CHAT_ID)\n"
        "• <b>/help</b> — список команд\n"
        f"\nПублічний канал зараз: <code>{CHANNEL_ID}</code>"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=['help'])
def cmd_help(message: types.Message):
    text = (
        "<b>Команди:</b>\n"
        "• /post ТЕКСТ — пост у канал\n"
        "• (Фото + підпис) — фото у канал\n"
        "• /postlogo — логотип + опис\n"
        "• /id — твій Telegram ID\n"
        "• /help — це меню\n"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=['id'])
def cmd_id(message: types.Message):
    bot.reply_to(message, f"Твій Telegram ID: <code>{message.from_user.id}</code>")


@bot.message_handler(commands=['post'])
def cmd_post(message: types.Message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "⛔ Лише адміністратор може публікувати пости.")

    # беремо текст після команди
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return bot.reply_to(message, "Напиши так: <code>/post ТЕКСТ</code>")

    text_to_post = parts[1].strip()
    try:
        bot.send_message(CHANNEL_ID, text_to_post, disable_web_page_preview=False)
        bot.reply_to(message, "✅ Опубліковано в канал.")
    except Exception as e:
        bot.reply_to(message, f"❗️Помилка публікації: <code>{e}</code>")


@bot.message_handler(commands=['postlogo'])
def cmd_postlogo(message: types.Message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "⛔ Лише адміністратор може публікувати пости.")

    caption = (
        "🚗 <b>Авто з США та Європи під ключ</b>\n"
        "🇺🇸 США | 🇪🇺 Європа ➡️ 🇺🇦 Україна\n"
        "📲 <b>+38 096 067 01 90</b>\n"
        "📦 Доставка + митниця + ремонт\n"
        "💸 Економія від 20%\n"
        "✉️ Пиши в Direct\n"
        "📍 Ternopil"
    )

    # лого очікуємо як logo.png у корені репо
    logo_path = os.path.join(os.getcwd(), "logo.png")
    if not os.path.exists(logo_path):
        return bot.reply_to(message, "Не знайдено файл <code>logo.png</code> у корені репозиторію.")

    try:
        with open(logo_path, "rb") as ph:
            bot.send_photo(CHANNEL_ID, ph, caption=caption)
        bot.reply_to(message, "✅ Логотип + опис опубліковано.")
    except Exception as e:
        bot.reply_to(message, f"❗️Помилка публікації: <code>{e}</code>")


# ---- Фото від адміна -> в канал ----
@bot.message_handler(content_types=['photo'])
def on_photo(message: types.Message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "⛔ Лише адміністратор може публікувати фото.")

    try:
        # беремо найбільшу версію фото
        file_id = message.photo[-1].file_id
        caption = message.caption or ""
        bot.send_photo(CHANNEL_ID, file_id, caption=caption)
        bot.reply_to(message, "✅ Фото опубліковано в канал.")
    except Exception as e:
        bot.reply_to(message, f"❗️Помилка публікації: <code>{e}</code>")


# ---- Запуск ----
if __name__ == "__main__":
    # нескінченний полінг (Render Background Worker)
    bot.infinity_polling(skip_pending=True, logger_level="INFO")
