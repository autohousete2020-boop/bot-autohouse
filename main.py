import os
import time
import logging
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # необов'язково
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # необов'язково (@your_channel)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# --- команди ---
@bot.message_handler(commands=['start'])
def cmd_start(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🚗 Зробити замовлення"))
    kb.add(types.KeyboardButton("📞 Контакти"), types.KeyboardButton("ℹ️ Допомога"))
    bot.reply_to(m,
        "Привіт! Це бот <b>AutoHouse</b>.\nПідберу авто з США/Європи під ключ.\n\n"
        "Натисни «🚗 Зробити замовлення» або /order.",
        reply_markup=kb
    )

@bot.message_handler(commands=['help'])
def cmd_help(m):
    bot.reply_to(m, "Команди:\n/start – меню\n/order – оформити запит\n/post – інструкція для публікації в канал")

@bot.message_handler(commands=['order'])
def cmd_order(m):
    ask_brand(m)

def ask_brand(m):
    msg = bot.send_message(m.chat.id, "Яка марка/модель цікавить?")
    bot.register_next_step_handler(msg, ask_budget)

def ask_budget(m):
    brand = m.text.strip()
    msg = bot.send_message(m.chat.id, "Який бюджет (у $)?")
    bot.register_next_step_handler(msg, lambda mm: ask_year(mm, brand))

def ask_year(m, brand):
    budget = m.text.strip()
    msg = bot.send_message(m.chat.id, "Бажаний рік випуску?")
    bot.register_next_step_handler(msg, lambda mm: finalize_order(mm, brand, budget))

def finalize_order(m, brand, budget):
    year = m.text.strip()
    phone = "+38 096 067 01 90"
    text = (f"✅ Запит прийнято!\n\n"
            f"• Марка/модель: <b>{brand}</b>\n"
            f"• Бюджет: <b>{budget}$</b>\n"
            f"• Рік: <b>{year}</b>\n\n"
            f"Ми зв’яжемось із вами. Телефон: <b>{phone}</b>")
    bot.send_message(m.chat.id, text)

    # опціонально — перекинути в адмін-чат
    if ADMIN_CHAT_ID:
        bot.send_message(int(ADMIN_CHAT_ID),
                         f"🆕 Лід від @{m.from_user.username or m.from_user.id}\n" + text)

@bot.message_handler(func=lambda m: m.text == "🚗 Зробити замовлення")
def btn_order(m): cmd_order(m)

@bot.message_handler(func=lambda m: m.text == "📞 Контакти")
def btn_contacts(m):
    bot.reply_to(m, "Телефон: <b>+38 096 067 01 90</b>\nInstagram: autohouse.te", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "ℹ️ Допомога")
def btn_help(m): cmd_help(m)

# --- надійний polling з авто-повтором при 409/мережевих ---
if __name__ == "__main__":
    while True:
        try:
            logging.info("Starting polling…")
            bot.infinity_polling(timeout=60, long_polling_timeout=20, allowed_updates=[])
        except ApiTelegramException as e:
            # 409 = “Conflict: terminated by other getUpdates request”
            if getattr(e, "error_code", None) == 409:
                logging.warning("Got 409 Conflict. Seems another instance is running. Retrying in 15s…")
                time.sleep(15)
            else:
                logging.exception("Telegram API error, retrying in 10s…")
                time.sleep(10)
        except Exception:
            logging.exception("Unexpected error, retrying in 10s…")
            time.sleep(10)
