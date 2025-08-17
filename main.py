import os
import telebot

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Set BOT_TOKEN in Render → Settings → Environment")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

@bot.message_handler(commands=['start', 'help'])
def start(msg):
    bot.reply_to(msg, "Привіт! Це бот АвтоХаус 🚗 Готовий приймати запити.")

@bot.message_handler(commands=['lead'])
def lead(msg):
    bot.reply_to(msg, "Напиши марку, модель і бюджет — передам Назару.")

@bot.message_handler(func=lambda m: True)
def echo(msg):
    bot.reply_to(msg, f"Прийняв: <b>{msg.text}</b>\nНазар зв'яжеться найближчим часом.")

if __name__ == "__main__":
    # нескінченний long-polling без вебхуків
    bot.infinity_polling(skip_pending=True)
