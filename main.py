import os, telebot, logging, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("ERROR: BOT_TOKEN is empty", file=sys.stderr)
    raise SystemExit(1)

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

@bot.message_handler(commands=['start','help'])
def start(msg):
    bot.reply_to(msg, "Привіт! Це бот АвтоХаус 🚗 Готовий приймати запити.")

@bot.message_handler(commands=['lead'])
def lead(msg):
    bot.reply_to(msg, "Напиши марку/модель і бюджет — передам Назару.")

@bot.message_handler(func=lambda m: True)
def echo(msg):
    bot.reply_to(msg, f"Прийняв: <b>{msg.text}</b>")

if __name__ == "__main__":
    print("BOT STARTED (polling)…")
    try:
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
    except Exception as e:
        logging.exception("BOT CRASHED: %s", e)
        raise
