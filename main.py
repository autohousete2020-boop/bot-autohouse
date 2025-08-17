import os
import csv
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

if not TOKEN:
    raise RuntimeError("Set BOT_TOKEN in Render → Worker → Environment")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --------- Кнопки головного меню ----------
def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton("Підібрати авто 🚗"))
    kb.row(types.KeyboardButton("Контакти 📲"), types.KeyboardButton("Про нас ℹ️"))
    return kb

# --------- Проста FSM для ліда ----------
USER_STATE = {}  # user_id -> {"step": str, "data": {...}}

def reset_state(uid: int):
    USER_STATE.pop(uid, None)

def set_step(uid: int, step: str):
    USER_STATE.setdefault(uid, {"step": None, "data": {}})["step"] = step

def get_step(uid: int):
    return USER_STATE.get(uid, {}).get("step")

def set_data(uid: int, key: str, value: str):
    USER_STATE.setdefault(uid, {"step": None, "data": {}})["data"][key] = value

def get_data(uid: int):
    return USER_STATE.get(uid, {}).get("data", {})

# --------- Команди ----------
@bot.message_handler(commands=["start", "help"])
def cmd_start(m: types.Message):
    bot.send_message(
        m.chat.id,
        "Привіт! Це бот autohouse.te 🚗\n"
        "Натискай кнопки нижче або введи /lead щоб залишити заявку.",
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=["lead"])
def cmd_lead(m: types.Message):
    uid = m.from_user.id
    reset_state(uid)
    set_step(uid, "car_model")
    bot.send_message(m.chat.id, "Яка марка/модель цікавить? (наприклад: Audi Q5 2020)")

@bot.message_handler(commands=["cancel"])
def cmd_cancel(m: types.Message):
    reset_state(m.from_user.id)
    bot.send_message(m.chat.id, "Готово, скинув форму. Можеш почати спочатку /lead", reply_markup=main_keyboard())

# --------- Обробка кнопок меню ----------
@bot.message_handler(func=lambda msg: msg.text == "Підібрати авто 🚗")
def btn_pick(m: types.Message):
    cmd_lead(m)

@bot.message_handler(func=lambda msg: msg.text == "Контакти 📲")
def btn_contacts(m: types.Message):
    bot.send_message(
        m.chat.id,
        "Зв'язок:\n"
        "Instagram: @autohouse.te\n"
        "Телефон: +380XXXXXXXXX\n"
        "Або просто залиш заявку — передзвонимо."
    )

@bot.message_handler(func=lambda msg: msg.text == "Про нас ℹ️")
def btn_about(m: types.Message):
    bot.send_message(
        m.chat.id,
        "autohouse.te — підбір і пригнання авто з США під ключ.\n"
        "Економія до 20%, прозора калькуляція, супровід від аукціону до реєстрації."
    )

# --------- Логіка форми по кроках ----------
@bot.message_handler(func=lambda m: get_step(m.from_user.id) is not None)
def lead_flow(m: types.Message):
    uid = m.from_user.id
    step = get_step(uid)
    text = (m.text or "").strip()

    if step == "car_model":
        set_data(uid, "car_model", text)
        set_step(uid, "budget")
        bot.send_message(m.chat.id, "Який бюджет? (сума у $ або діапазон)")
        return

    if step == "budget":
        set_data(uid, "budget", text)
        set_step(uid, "name")
        bot.send_message(m.chat.id, "Як до вас звертатись? (ім'я)")
        return

    if step == "name":
        set_data(uid, "name", text)
        set_step(uid, "phone")
        bot.send_message(m.chat.id, "Телефон або Telegram @нік:")
        return

    if step == "phone":
        set_data(uid, "phone", text)
        data = get_data(uid)

        # Зберегти у CSV
        try:
            header = ["tg_user_id", "name", "phone", "car_model", "budget"]
            file_exists = os.path.exists("leads.csv")
            with open("leads.csv", "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    "tg_user_id": uid,
                    "name": data.get("name", ""),
                    "phone": data.get("phone", ""),
                    "car_model": data.get("car_model", ""),
                    "budget": data.get("budget", "")
                })
        except Exception as e:
            bot.send_message(m.chat.id, f"⚠️ Не вдалось записати у базу: {e}")

        # Повідомити адміну
        if ADMIN_ID:
            try:
                bot.send_message(
                    ADMIN_ID,
                    "🆕 <b>Новий лід</b>\n"
                    f"👤 {data.get('name','')}\n"
                    f"📞 {data.get('phone','')}\n"
                    f"🚗 {data.get('car_model','')}\n"
                    f"💵 {data.get('budget','')}\n"
                    f"TG ID: <code>{uid}</code>"
                )
            except Exception:
                pass

        # Підтвердження користувачу
        bot.send_message(
            m.chat.id,
            "Дякую! Прийняв заявку ✅\nНайближчим часом зв'яжемося з вами.",
            reply_markup=main_keyboard()
        )
        reset_state(uid)
        return

# --------- Фолбек: інші повідомлення ----------
@bot.message_handler(func=lambda m: True)
def fallback(m: types.Message):
    bot.send_message(
        m.chat.id,
        "Можу залишити заявку (/lead), показати контакти або розповісти про послуги.",
        reply_markup=main_keyboard()
    )

if __name__ == "__main__":
    # Long polling — під Render Worker
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
