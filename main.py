import telebot
from telebot import types
import random
import logging

# ================= ЛОГИРОВАНИЕ =================
# Настраиваем логирование: пишем время, уровень важности и само сообщение
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ================= НАСТРОЙКИ =================
TOKEN = '8503977875:AAEpoKf308aNhu5pF7q_-xYkUXh_B4EPiaw'  # Замени на свой токен
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

# ================= ЛОГИКА ПОИСКА =================
def get_random_unseen_profile(user_id):
    if user_id not in INTERACTIONS:
        INTERACTIONS[user_id] = {}
        
    seen_users = INTERACTIONS[user_id].keys()
    my_profile = USERS[user_id]
    
    available_users = []
    for uid, u_data in USERS.items():
        if uid == user_id or uid in seen_users:
            continue
            
        # ПРОВЕРКА ПОЛА
        # Подходит ли нам этот человек?
        if my_profile['looking_for'] != "Всё равно":
            if (my_profile['looking_for'] == "Парней" and u_data['gender'] != "Парень") or \
               (my_profile['looking_for'] == "Девушек" and u_data['gender'] != "Девушка"):
                continue
                
        # Подходим ли мы этому человеку? (взаимный фильтр)
        if u_data['looking_for'] != "Всё равно":
            if (u_data['looking_for'] == "Парней" and my_profile['gender'] != "Парень") or \
               (u_data['looking_for'] == "Девушек" and my_profile['gender'] != "Девушка"):
                continue

        available_users.append(uid)
            
    if not available_users:
        return None
        
    return random.choice(available_users)

# ================= РЕГИСТРАЦИЯ =================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    logging.info(f"Пользователь {user_id} нажал /start")
    
    if user_id in USERS:
        bot.send_message(user_id, "С возвращением! Твоя анкета уже в базе.", reply_markup=get_main_menu())
    else:
        bot.send_message(user_id, "Привет! Добро пожаловать в бота знакомств 💘\nКак тебя зовут?", reply_markup=types.ReplyKeyboardRemove())
        TEMP_REG[user_id] = {}
        bot.register_next_step_handler(message, ask_age)

def ask_age(message):
    user_id = message.chat.id
    TEMP_REG[user_id]['name'] = message.text
    msg = bot.send_message(user_id, f"Приятно познакомиться, {message.text}! Сколько тебе лет?")
    bot.register_next_step_handler(msg, ask_gender)

def ask_gender(message):
    user_id = message.chat.id
    if not message.text.isdigit():
        msg = bot.send_message(user_id, "Возраст должен быть числом! Сколько тебе лет?")
        bot.register_next_step_handler(msg, ask_gender)
        return
        
    TEMP_REG[user_id]['age'] = int(message.text)
    msg = bot.send_message(user_id, "Кто ты?", reply_markup=get_gender_keyboard())
    bot.register_next_step_handler(msg, ask_search_gender)


def ask_search_gender(message):
    user_id = message.chat.id
    if message.text not in ["Парень", "Девушка"]:
        msg = bot.send_message(user_id, "Пожалуйста, используй кнопки внизу!", reply_markup=get_gender_keyboard())
        bot.register_next_step_handler(msg, ask_search_gender)
        return

    TEMP_REG[user_id]['gender'] = message.text
    msg = bot.send_message(user_id, "Кого ты ищешь?", reply_markup=get_search_gender_keyboard())
    bot.register_next_step_handler(msg, ask_city)

def ask_city(message):
    user_id = message.chat.id
    if message.text not in ["Парней", "Девушек", "Всё равно"]:
        msg = bot.send_message(user_id, "Пожалуйста, используй кнопки!", reply_markup=get_search_gender_keyboard())
        bot.register_next_step_handler(msg, ask_city)
        return

    TEMP_REG[user_id]['looking_for'] = message.text
    msg = bot.send_message(user_id, "Из какого ты города?", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, ask_desc)

def ask_desc(message):
    user_id = message.chat.id
    TEMP_REG[user_id]['city'] = message.text
    msg = bot.send_message(user_id, "Расскажи немного о себе:")
    bot.register_next_step_handler(msg, ask_photo)

def ask_photo(message):
    user_id = message.chat.id
    TEMP_REG[user_id]['desc'] = message.text
    msg = bot.send_message(user_id, "И последний шаг! Отправь свое лучшее фото 📸")
    bot.register_next_step_handler(msg, finish_registration)

def finish_registration(message):
    user_id = message.chat.id
    if not message.photo:
        msg = bot.send_message(user_id, "Нужно отправить именно фото! Жду картинку:")
        bot.register_next_step_handler(msg, finish_registration)
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
    
    del TEMP_REG[user_id]
    logging.info(f"Пользователь {user_id} успешно зарегистрировался.")
    bot.send_message(user_id, "Анкета успешно создана! 🎉", reply_markup=get_main_menu())

# ================= ГЛАВНОЕ МЕНЮ =================
@bot.message_handler(content_types=['text'])
def handle_menu(message):
    user_id = message.chat.id
    text = message.text
    
    if user_id not in USERS and text in ["🚀 Смотреть анкеты", "👤 Моя анкета", "❌ Удалить анкету"]:
        bot.send_message(user_id, "Сначала нужно создать анкету! Нажми /start")
        return

    if text == "👤 Моя анкета":
        u = USERS[user_id]
        caption = f"{u['name']}, {u['age']}, {u['city']}\nПол: {u['gender']} | Ищет: {u['looking_for']}\n{u['desc']}\n\nСобрано лайков: ❤️ {u['likes']}"
        bot.send_photo(user_id, u['photo'], caption=caption)
        
    elif text == "❌ Удалить анкету":
        del USERS[user_id]
        if user_id in INTERACTIONS:
            del INTERACTIONS[user_id]
        logging.info(f"Пользователь {user_id} удалил анкету.")
        bot.send_message(user_id, "Твоя анкета удалена!", reply_markup=types.ReplyKeyboardRemove())
        
    elif text == "🚀 Смотреть анкеты":
        show_next_profile(user_id)

def show_next_profile(user_id):
    target_id = get_random_unseen_profile(user_id)
    if target_id is None:
        bot.send_message(user_id, "Анкеты закончились! Возвращайся позже ⏳", reply_markup=get_main_menu())
        return
        
    u = USERS[target_id]
    caption = f"{u['name']}, {u['age']}, {u['city']}\n\n{u['desc']}"
    bot.send_photo(user_id, u['photo'], caption=caption, reply_markup=get_reaction_keyboard(target_id))

# ================= ОБРАБОТКА ЛАЙКОВ/ДИЗЛАЙКОВ =================



@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    
    
    if call.data == "stop":
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        bot.send_message(user_id, "Поиск остановлен.", reply_markup=get_main_menu())
        return
        
    action, target_id_str = call.data.split('_')
    target_id = int(target_id_str)
    
    if user_id not in INTERACTIONS:
        INTERACTIONS[user_id] = {}
    INTERACTIONS[user_id][target_id] = action
    
    logging.info(f"Пользователь {user_id} поставил {action} пользователю {target_id}")
    
    if action == "like" and target_id in USERS:
        USERS[target_id]['likes'] += 1
        
        if target_id in INTERACTIONS and user_id in INTERACTIONS[target_id]:
            if INTERACTIONS[target_id][user_id] == "like":
                user1, user2 = USERS[user_id], USERS[target_id]
                logging.info(f"МЕТЧ! Между {user_id} и {target_id}")
                try:
                    bot.send_message(user_id, f"🎉 ВЗАИМНАЯ СИМПАТИЯ! Начинай общаться: {user2['username']}")
                    bot.send_message(target_id, f"🎉 ВЗАИМНАЯ СИМПАТИЯ! Начинай общаться: {user1['username']}")
                except Exception as e:
                    logging.error(f"Ошибка отправки метча: {e}")

    try:
        bot.edit_message_reply_markup(chat_id=user_id, message_id=call.message.message_id, reply_markup=None)
    except:
        pass
        
    show_next_profile(user_id)

# ================= ЗАПУСК БОТА =================
if __name__ == "__main__":
    logging.info("Бот запущен!")
    bot.infinity_polling(skip_pending=True)


