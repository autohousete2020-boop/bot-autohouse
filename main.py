import os
import time
import requests
import telebot  # pyTelegramBotAPI

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# На всяк випадок знімаємо вебхук перед long polling
try:
    requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=10)
except Exception as e:
    print(f"deleteWebhook warning: {e}")

@bot.message_handler(commands=['start', 'help'])
def start_handler(msg: telebot.types.Message):
    bot.reply_to(msg, "Привіт! Це бот АвтоХаус 🚗 Готовий приймати запити.")

# Головний цикл з авто-відновленням (щоб короткі 409 не валили процес)
while True:
    try:
        # skip_pending=True — ігноримо «старі» апдейти після рестарту
        bot.infinity_polling(timeout=30, long_polling_timeout=25, skip_pending=True, allowed_updates=['message'])
    except Exception as e:
        print(f"Polling error: {e}")
        time.sleep(5)  # невелика пауза і пробуємо знову
