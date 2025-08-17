# main.py
import os
import logging
from typing import Dict, Any

import telebot
from telebot import types

# ---------- Налаштування логів ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# ---------- Змінні оточення ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("ENV BOT_TOKEN is empty!")

# Можна задавати з ENV. Якщо не задано – беремо значення за замовчуванням нижче.
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "771906613"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@autohouse_te").strip()  # ваш публічний канал @xxxxx

# Телефон компанії (для кнопки «Контакти» та текстів)
BUSINESS_PHONE = "+38 096 067 01 90"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Збереження простих станів користувача (без БД)
user_states: Dict[int, Dict[str, Any]] = {}

# Імена кроків анкети
STEP_BRAND = "brand"
STEP_BUDGET = "budget"
STEP_YEAR = "year"
STEP_CONTACT = "contact"
STEP_DONE = "done"

# Отримаємо @username бота для deep-link
_me = bot.get_me()
BOT_USERNAME = _me.username  # без @


# ---------- Корисні клавіатури ----------
def main_menu_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton("🚗 Зробити замовлення"))
    kb.row(types.KeyboardButton("📞 Контакти"), types.KeyboardButton("ℹ️ Допомога"))
    return kb


def contact_request_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📱 Поділитися номером", request_contact=True))
    kb.add(types.KeyboardButton("Пропустити та ввести вручну"))
    return kb


def channel_cta_inline_kb() -> types.InlineKeyboardMarkup:
    # Кнопка веде у бот із deep-link параметром start=order (відкриє анкету)
    url = f"https://t.me/{BOT_USERNAME}?start=order"
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("📝 Залишити заявку", url=url))
    return ikb


# ---------- Допоміжне ----------
def start_order(chat_id: int):
    user_states[chat_id] = {"step": STEP_BRAND}
    bot.send_message(chat_id, "Яка марка/модель цікавить?", reply_markup=types.ReplyKeyboardRemove())


def send_order_to_admin(order: Dict[str, Any], user: types.User):
    text = (
        "🆕 <b>Нова заявка</b>\n"
        f"👤 Від: <a href=\"tg://user?id={user.id}\">{user.first_name or ''} {user.last_name or ''}</a> @{user.username or ''}\n\n"
        f"• Марка/модель: <b>{order.get('brand','-')}</b>\n"
        f"• Бюджет: <b>{order.get('budget','-')}</b>\n"
        f"• Рік: <b>{order.get('year','-')}</b>\n"
        f"• Телефон клієнта: <b>{order.get('contact','не надано')}</b>"
    )
    bot.send_message(ADMIN_CHAT_ID, text)


# ---------- Команди ----------
@bot.message_handler(commands=["start"])
def cmd_start(m: types.Message):
    # Deep-link: /start order -> одразу анкета
    if m.text and len(m.text.split()) > 1 and m.text.split()[1].lower() == "order":
        bot.send_message(
            m.chat.id,
            "Привіт! 👋 Давайте оформимо запит на підбір авто.\nВідповідайте, будь ласка, на кілька питань.",
            reply_markup=main_menu_kb(),
        )
        start_order(m.chat.id)
        return

    bot.send_message(
        m.chat.id,
        (
            "Привіт! Це бот <b>AutoHouse</b>.\n"
            "Підберу авто з США/Європи під ключ.\n\n"
            "Натисни «🚗 Зробити замовлення» або /order."
        ),
        reply_markup=main_menu_kb(),
    )


@bot.message_handler(commands=["help"])
def cmd_help(m: types.Message):
    bot.send_message(
        m.chat.id,
        "Команди:\n"
        "• /start – головне меню\n"
        "• /order – оформити запит на підбір авто\n"
        "• /post – (тільки адмін) опублікувати пост у каналі з кнопкою «Залишити заявку»",
        reply_markup=main_menu_kb(),
    )


@bot.message_handler(commands=["order"])
def cmd_order(m: types.Message):
    bot.send_message(m.chat.id, "Розпочинаємо оформлення запиту. Це займе 1–2 хвилини.")
    start_order(m.chat.id)


# ---------- Меню кнопок ----------
@bot.message_handler(func=lambda msg: msg.text == "🚗 Зробити замовлення")
def menu_order(m: types.Message):
    start_order(m.chat.id)


@bot.message_handler(func=lambda msg: msg.text == "📞 Контакти")
def menu_contacts(m: types.Message):
    bot.send_message(
        m.chat.id,
        f"Ми на зв'язку:\n• Телефон: <b>{BUSINESS_PHONE}</b>\n• Канал: {CHANNEL_USERNAME}",
        reply_markup=main_menu_kb(),
    )


@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Допомога")
def menu_help(m: types.Message):
    cmd_help(m)


# ---------- Анкета (проста FSM без БД) ----------
@bot.message_handler(content_types=["text", "contact"])
def questionnaire(m: types.Message):
    st = user_states.get(m.chat.id)

    # якщо не в анкеті — ігноруємо
    if not st or st.get("step") is None:
        return

    step = st["step"]

    # 1) Марка/модель
    if step == STEP_BRAND:
        st["brand"] = m.text.strip()
        st["step"] = STEP_BUDGET
        bot.send_message(m.chat.id, "Який бюджет (у $)?")
        return

    # 2) Бюджет
    if step == STEP_BUDGET:
        st["budget"] = m.text.strip()
        st["step"] = STEP_YEAR
        bot.send_message(m.chat.id, "Бажаний рік випуску?")
        return

    # 3) Рік
    if step == STEP_YEAR:
        st["year"] = m.text.strip()
        st["step"] = STEP_CONTACT
        bot.send_message(
            m.chat.id,
            "Залиште ваш номер телефону, будь ласка.",
            reply_markup=contact_request_kb(),
        )
        return

    # 4) Контакт (через share contact або текстом)
    if step == STEP_CONTACT:
        phone = None
        if m.content_type == "contact" and m.contact and m.contact.phone_number:
            phone = m.contact.phone_number
        else:
            # якщо користувач натисне «Пропустити та ввести вручну» – наступне повідомлення беремо як телефон
            phone = (m.text or "").strip()

        st["contact"] = phone if phone else "не надано"
        st["step"] = STEP_DONE

        # Підтвердження клієнту
        bot.send_message(
            m.chat.id,
            (
                "✅ <b>Запит прийнято!</b>\n"
                f"• Марка/модель: <b>{st.get('brand')}</b>\n"
                f"• Бюджет: <b>{st.get('budget')}</b>\n"
                f"• Рік: <b>{st.get('year')}</b>\n"
                f"• Телефон: <b>{st.get('contact')}</b>\n\n"
                "Ми зв'яжемося з вами найближчим часом. Дякуємо! 🙌"
            ),
            reply_markup=main_menu_kb(),
        )

        # Повідомлення адмінам
        send_order_to_admin(st, m.from_user)

        # Очистимо стан
        user_states.pop(m.chat.id, None)
        return


# ---------- Публікація постів у канал (для адміна) ----------
@bot.message_handler(commands=["post"])
def cmd_post(m: types.Message):
    if m.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(m, "Команда доступна тільки адміністратору.")
