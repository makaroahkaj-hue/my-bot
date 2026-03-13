import os
import random
import logging
import telebot
from telebot import types

# ================= ЛОГИРОВАНИЕ =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("TOKEN")  # перед запуском задай переменную окружения TOKEN

if not TOKEN:
    raise ValueError("Токен не найден. Задай переменную окружения TOKEN.")

bot = telebot.TeleBot(TOKEN)

# ================= "БАЗА ДАННЫХ" В ПАМЯТИ =================
USERS = {}
INTERACTIONS = {}
TEMP_REG = {}

# ================= КЛАВИАТУРЫ =================
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🚀 Смотреть анкеты"),
        types.KeyboardButton("👤 Моя анкета"),
        types.KeyboardButton("❌ Удалить анкету")
    )
    return markup


def get_gender_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Парень", "Девушка")
    return markup


def get_search_gender_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Парней", "Девушек", "Всё равно")
    return markup


def get_reaction_keyboard(target_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn_like = types.InlineKeyboardButton("❤️", callback_data=f"like_{target_id}")
    btn_dislike = types.InlineKeyboardButton("👎", callback_data=f"dislike_{target_id}")
    btn_stop = types.InlineKeyboardButton("💤", callback_data="stop")
    markup.add(btn_like, btn_dislike, btn_stop)
    return markup


# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def build_profile_caption(user_data, show_likes=False):
    caption = (
        f"{user_data['name']}, {user_data['age']}, {user_data['city']}\n"
        f"Пол: {user_data['gender']} | Ищет: {user_data['looking_for']}\n\n"
        f"{user_data['desc']}"
    )
    if show_likes:
        caption += f"\n\nСобрано лайков: ❤️ {user_data['likes']}"
    return caption


def ensure_user_interactions(user_id):
    if user_id not in INTERACTIONS:
        INTERACTIONS[user_id] = {}


def get_random_unseen_profile(user_id):
    ensure_user_interactions(user_id)

    if user_id not in USERS:
        return None

    seen_users = INTERACTIONS[user_id].keys()
    my_profile = USERS[user_id]
    available_users = []

    for uid, u_data in USERS.items():
        if uid == user_id or uid in seen_users:
            continue

        # Подходит ли этот пользователь нам?
        if my_profile['looking_for'] != "Всё равно":
            if (
                my_profile['looking_for'] == "Парней" and u_data['gender'] != "Парень"
            ) or (
                my_profile['looking_for'] == "Девушек" and u_data['gender'] != "Девушка"
            ):
                continue

        # Подходим ли мы этому пользователю?
        if u_data['looking_for'] != "Всё равно":
            if (
                u_data['looking_for'] == "Парней" and my_profile['gender'] != "Парень"
            ) or (
                u_data['looking_for'] == "Девушек" and my_profile['gender'] != "Девушка"
            ):
                continue

        available_users.append(uid)

    if not available_users:
        return None

    return random.choice(available_users)


def show_next_profile(user_id):
    if user_id not in USERS:
        bot.send_message(user_id, "Сначала нужно создать анкету! Нажми /start")
        return

    target_id = get_random_unseen_profile(user_id)

    if target_id is None:
        bot.send_message(
            user_id,
            "Анкеты закончились! Возвращайся позже ⏳",
            reply_markup=get_main_menu()
        )
        return

    u = USERS[target_id]
    caption = f"{u['name']}, {u['age']}, {u['city']}\n\n{u['desc']}"
    bot.send_photo(
        user_id,
        u['photo'],
        caption=caption,
        reply_markup=get_reaction_keyboard(target_id)
    )


# ================= РЕГИСТРАЦИЯ =================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    logging.info(f"Пользователь {user_id} нажал /start")

    if user_id in USERS:
        bot.send_message(
            user_id,
            "С возвращением! Твоя анкета уже в базе.",
            reply_markup=get_main_menu()
        )
    else:
        TEMP_REG[user_id] = {}
        msg = bot.send_message(
            user_id,
            "Привет! Добро пожаловать в бота знакомств 💘\nКак тебя зовут?",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, ask_age)


def ask_age(message):
    user_id = message.chat.id
    name = (message.text or "").strip()

    if not name:
        msg = bot.send_message(user_id, "Имя не может быть пустым. Напиши своё имя:")
        bot.register_next_step_handler(msg, ask_age)
        return

    TEMP_REG[user_id]['name'] = name
    msg = bot.send_message(user_id, f"Приятно познакомиться, {name}! Сколько тебе лет?")
    bot.register_next_step_handler(msg, ask_gender)


def ask_gender(message):
    user_id = message.chat.id
    text = (message.text or "").strip()

    if not text.isdigit():
        msg = bot.send_message(user_id, "Возраст должен быть числом! Сколько тебе лет?")
        bot.register_next_step_handler(msg, ask_gender)
        return

    age = int(text)
    if age < 10 or age > 100:
        msg = bot.send_message(user_id, "Введи реальный возраст от 10 до 100:")
        bot.register_next_step_handler(msg, ask_gender)
        return

    TEMP_REG[user_id]['age'] = age
    msg = bot.send_message(user_id, "Кто ты?", reply_markup=get_gender_keyboard())
    bot.register_next_step_handler(msg, ask_search_gender)


def ask_search_gender(message):
    user_id = message.chat.id
    text = (message.text or "").strip()

    if text not in ["Парень", "Девушка"]:
        msg = bot.send_message(
            user_id,
            "Пожалуйста, используй кнопки внизу!",
            reply_markup=get_gender_keyboard()
        )
        bot.register_next_step_handler(msg, ask_search_gender)
        return

    TEMP_REG[user_id]['gender'] = text
    msg = bot.send_message(
        user_id,
        "Кого ты ищешь?",
        reply_markup=get_search_gender_keyboard()
    )
    bot.register_next_step_handler(msg, ask_city)


def ask_city(message):
    user_id = message.chat.id
    text = (message.text or "").strip()

    if text not in ["Парней", "Девушек", "Всё равно"]:
        msg = bot.send_message(
            user_id,
            "Пожалуйста, используй кнопки!",
            reply_markup=get_search_gender_keyboard()
        )
        bot.register_next_step_handler(msg, ask_city)
        return

    TEMP_REG[user_id]['looking_for'] = text
    msg = bot.send_message(
        user_id,
        "Из какого ты города?",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, ask_desc)


def ask_desc(message):
    user_id = message.chat.id
    city = (message.text or "").strip()

    if not city:
        msg = bot.send_message(user_id, "Город не может быть пустым. Напиши свой город:")
        bot.register_next_step_handler(msg, ask_desc)
        return

    TEMP_REG[user_id]['city'] = city
    msg = bot.send_message(user_id, "Расскажи немного о себе:")
    bot.register_next_step_handler(msg, ask_photo)


def ask_photo(message):
    user_id = message.chat.id
    desc = (message.text or "").strip()

    if not desc:
        msg = bot.send_message(user_id, "Описание не может быть пустым. Напиши пару слов о себе:")
        bot.register_next_step_handler(msg, ask_photo)
        return

    TEMP_REG[user_id]['desc'] = desc
    msg = bot.send_message(user_id, "И последний шаг! Отправь своё лучшее фото 📸")
    bot.register_next_step_handler(msg, finish_registration)


def finish_registration(message):
    user_id = message.chat.id

    if not message.photo:
        msg = bot.send_message(user_id, "Нужно отправить именно фото! Жду картинку:")
        bot.register_next_step_handler(msg, finish_registration)
        return

    if user_id not in TEMP_REG:
        bot.send_message(user_id, "Ошибка регистрации. Нажми /start и попробуй заново.")
        return

    photo_id = message.photo[-1].file_id
    username = message.from_user.username
    username = f"@{username}" if username else f"tg://user?id={user_id}"

    USERS[user_id] = {
        'name': TEMP_REG[user_id]['name'],
        'age': TEMP_REG[user_id]['age'],
        'gender': TEMP_REG[user_id]['gender'],
        'looking_for': TEMP_REG[user_id]['looking_for'],
        'city': TEMP_REG[user_id]['city'],
        'desc': TEMP_REG[user_id]['desc'],
        'photo': photo_id,
        'likes': 0,
        'username': username
    }

    ensure_user_interactions(user_id)
    del TEMP_REG[user_id]

    logging.info(f"Пользователь {user_id} успешно зарегистрировался.")
    bot.send_message(user_id, "Анкета успешно создана! 🎉", reply_markup=get_main_menu())


# ================= ГЛАВНОЕ МЕНЮ =================
@bot.message_handler(content_types=['text'])
def handle_menu(message):
    user_id = message.chat.id
    text = (message.text or "").strip()

    if user_id not in USERS and text in ["🚀 Смотреть анкеты", "👤 Моя анкета", "❌ Удалить анкету"]:
        bot.send_message(user_id, "Сначала нужно создать анкету! Нажми /start")
        return

    if text == "👤 Моя анкета":
        u = USERS[user_id]
        caption = build_profile_caption(u, show_likes=True)
        bot.send_photo(user_id, u['photo'], caption=caption)

    elif text == "❌ Удалить анкету":
        if user_id in USERS:
            del USERS[user_id]
        if user_id in INTERACTIONS:
            del INTERACTIONS[user_id]
        if user_id in TEMP_REG:
            del TEMP_REG[user_id]

        logging.info(f"Пользователь {user_id} удалил анкету.")
        bot.send_message(
            user_id,
            "Твоя анкета удалена!",
            reply_markup=types.ReplyKeyboardRemove()
        )

    elif text == "🚀 Смотреть анкеты":
        show_next_profile(user_id)

    else:
        if user_id in USERS:
            bot.send_message(user_id, "Выбери действие из меню 👇", reply_markup=get_main_menu())
        else:
            bot.send_message(user_id, "Нажми /start, чтобы создать анкету.")


# ================= ОБРАБОТКА КНОПОК =================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id

    # обязательно отвечаем на callback, чтобы кнопка не "висела"
    try:
        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.error(f"Ошибка answer_callback_query: {e}")

    if user_id not in USERS:
        bot.send_message(user_id, "Сначала нужно создать анкету! Нажми /start")
        return

    if call.data == "stop":
        try:
            bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        except Exception as e:
            logging.error(f"Ошибка удаления сообщения: {e}")

        bot.send_message(user_id, "Поиск остановлен.", reply_markup=get_main_menu())
        return

    try:
        action, target_id_str = call.data.split('_', 1)
        target_id = int(target_id_str)
    except ValueError:
        logging.error(f"Некорректный callback_data: {call.data}")
        bot.send_message(user_id, "Ошибка обработки кнопки.")
        return

    if target_id not in USERS:
        bot.send_message(user_id, "Эта анкета уже недоступна.")
        show_next_profile(user_id)
        return

    ensure_user_interactions(user_id)

    # защита от повторного нажатия по той же анкете
    if target_id in INTERACTIONS[user_id]:
        bot.send_message(user_id, "Ты уже оценил(а) эту анкету.")
        return

    INTERACTIONS[user_id][target_id] = action
    logging.info(f"Пользователь {user_id} поставил {action} пользователю {target_id}")

    if action == "like":
        USERS[target_id]['likes'] += 1

        # Проверяем взаимный лайк
        if (
            target_id in INTERACTIONS
            and user_id in INTERACTIONS[target_id]
            and INTERACTIONS[target_id][user_id] == "like"
        ):
            user1 = USERS[user_id]
            user2 = USERS[target_id]
            logging.info(f"МЕТЧ! Между {user_id} и {target_id}")

            try:
                bot.send_message(
                    user_id,
                    f"🎉 ВЗАИМНАЯ СИМПАТИЯ!\nНачинай общаться: {user2['username']}"
                )
                bot.send_message(
                    target_id,
                    f"🎉 ВЗАИМНАЯ СИМПАТИЯ!\nНачинай общаться: {user1['username']}"
                )
            except Exception as e:
                logging.error(f"Ошибка отправки метча: {e}")

    elif action == "dislike":
        logging.info(f"Пользователь {user_id} дизлайкнул пользователя {target_id}")

    # Убираем inline-кнопки у текущей анкеты
    try:
        bot.edit_message_reply_markup(
            chat_id=user_id,
            message_id=call.message.message_id,
            reply_markup=None
        )
    except Exception as e:
        logging.error(f"Ошибка удаления кнопок: {e}")

    show_next_profile(user_id)


# ================= ЗАПУСК БОТА =================
if __name__ == "__main__":
    logging.info("Бот запущен!")
    bot.infinity_polling(skip_pending=True)


