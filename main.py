import sqlite3
from telebot import TeleBot, types

# Telegram bot token
BOT_TOKEN = "replace_with_bot_token"
bot = TeleBot(BOT_TOKEN)

local_storage = {}

# Database setup
def init_db():
    conn = sqlite3.connect("event_bot.db")
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE,
            name TEXT,
            is_admin BOOLEAN DEFAULT 0,
            state TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            question TEXT,
            answer TEXT DEFAULT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

# Helper functions
def db_update_data(func):
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect("event_bot.db")
        cursor = conn.cursor()
        sql_query = func(*args, **kwargs)
        cursor.execute(sql_query)
        conn.commit()
        conn.close()
    return wrapper

def get_records(query, multiple):
    conn = sqlite3.connect("event_bot.db")
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall() if multiple else cursor.fetchone()
    conn.close()
    return rows

def get_all_records(query):
    return get_records(query, True)

def get_one_record(query):
    return get_records(query, False)

def get_users():
    return get_all_records("SELECT * FROM users")

def get_user(chat_id):
    user = get_one_record(f"SELECT name, is_admin, state FROM users WHERE chat_id = {chat_id}")
    return {
        'name': user[0],
        'is_admin': user[1],
        'state': user[2]
    } if user else None

def get_questions():
    return get_all_records("SELECT id, chat_id, question FROM questions WHERE answer IS NULL")

@db_update_data
def update_question(question_id, answer_text):
    return f"""
        UPDATE questions 
        SET answer = '{answer_text}'
        WHERE id = {question_id}
    """

def get_user_state(chat_id):
    user = get_user(chat_id)
    return user['state'] if user else None

@db_update_data
def set_user_state(chat_id, state):
    return f"""
        INSERT INTO users (chat_id, state) 
        VALUES ({chat_id}, '{state}') 
        ON CONFLICT(chat_id) DO UPDATE SET state = excluded.state
        """

@db_update_data
def set_user(chat_id, name):
    return f"""
        INSERT OR IGNORE INTO users (chat_id, name) 
        VALUES ({chat_id}, '{name}') 
        ON CONFLICT(chat_id) DO UPDATE SET name = '{name}'"""

def is_admin(chat_id):
    user = get_user(chat_id)
    return user['is_admin'] if user else False

@db_update_data
def set_question(chat_id, question_text):
    return f"""
        INSERT INTO questions (chat_id, question)
        VALUES ({chat_id}, '{question_text}')
    """

def get_user_chat(question_id):
    return get_one_record(f"SELECT chat_id FROM questions WHERE id = {question_id}")[0]

def set_local_storage(id, key, value):
    if id in local_storage:
        local_storage[id][key] = value
    else:
        local_storage[id] = {
            key: value
        }

def get_local_storage(id, key):
    if id in local_storage and key in local_storage[id]:
        return local_storage[id][key]
    else:
        return ''

# Command: Start
@bot.message_handler(commands=['start'])
def start_handler(message):
    chat_id = message.chat.id
    user = get_user(chat_id)

    if user and user['name'] and user['state']:
        set_user_state(chat_id, 'USERMAINMENU')
        main_menu_handler(message)
        return

    # Parse identifier from the message (e.g., from a referral link or QR code (preferable))
    identifier = message.text.split(" ")[1] if len(message.text.split(" ")) > 1 else None

    if identifier:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Підтвердити'))
        bot.send_message(message.chat.id, f"Вітаємо, {identifier}! Підтвердь реєстрацію, будь ласка.", reply_markup=markup)
        set_user_state(chat_id, "REGISTER")
        set_local_storage(chat_id, 'identifier', identifier)
    else:
        bot.send_message(chat_id, "Помилка: Ідентифікатор не знайдено. Або у вас немає доступу")

@bot.message_handler(func=lambda message: message.text.startswith("/answer_"))
def answer_question_handler(message):
    chat_id = message.chat.id
    if is_admin(chat_id):
        question_id = int(message.text.split("_")[1])
        bot.send_message(chat_id, "Напишіть вашу відповідь:")
        set_user_state(chat_id, f"ANSWER_QUESTION_{question_id}")
    else:
        bot.send_message(chat_id, "У вас немає прав адміністратора.")

# Command: Register
@bot.message_handler(func=lambda message: get_user_state(message.chat.id) == "REGISTER")
def register_handler(message):
    chat_id = message.chat.id
    name = get_local_storage(chat_id, 'identifier')

    set_user(chat_id, name)

    bot.send_message(chat_id, "Реєстрація успішна! Тепер ви зможете отримувати новини по івенту.")
    set_user_state(chat_id, 'USERMAINMENU')
    main_menu_handler(message)

# Show main menu for user
def main_menu_handler(message):
    chat_id = message.chat.id

    if is_admin(chat_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Перевірити питання'))
        markup.add(types.KeyboardButton('Додати новину'))
        bot.send_message(chat_id, f"Давай подивимось питання, чи запостимо новину", reply_markup=markup)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Задати питання'))
        bot.send_message(chat_id, f"Якщо у вас є якесь питання, або уточнення - не соромтесь, питайте, ми відповімо.", reply_markup=markup)

# Command: Ask a Question
@bot.message_handler(func=lambda message: get_user_state(message.chat.id) == "USERMAINMENU")
def main_menu_command_handler(message):
    if message.text == "Задати питання":
        ask_question_handler(message)
    if message.text == "Перевірити питання":
        view_questions_handler(message)
    if message.text == "Додати новину":
        broadcast_handler(message)
    else:
        bot.send_message(message.chat.id, "Оберіть одну з доступних опцій.")
        main_menu_handler(message)

def ask_question_handler(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Напишіть ваше питання:")
    set_user_state(chat_id, "ASK_QUESTION")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id) == "ASK_QUESTION")
def save_question(message):
    chat_id = message.chat.id
    question_text = message.text

    set_question(chat_id, question_text)

    bot.send_message(chat_id, "Ваше питання було надіслане.")
    set_user_state(chat_id, 'USERMAINMENU')

# Command: Admin Answer Questions
def view_questions_handler(message):
    chat_id = message.chat.id

    if is_admin(chat_id):
        questions = get_questions()
        if questions:
            for q_id, user_chat_id, question_text in questions:
                bot.send_message(chat_id, f"Питання від {user_chat_id}:\n{question_text}\n\nВідповісти: /answer_{q_id}")
        else:
            bot.send_message(chat_id, "Немає нових питань для відповіді.")
    else:
        bot.send_message(chat_id, "У вас немає прав адміністратора.")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id).startswith("ANSWER_QUESTION_"))
def save_answer(message):
    chat_id = message.chat.id
    state = get_user_state(chat_id)
    question_id = int(state.split("_")[-1])
    answer_text = message.text

    update_question(question_id, answer_text)

    bot.send_message(get_user_chat(question_id), f"Відповідь на ваше запитання:\n{answer_text}")
    bot.send_message(chat_id, "Відповідь успішно надіслана.")
    set_user_state(chat_id, 'USERMAINMENU')

# Command: Admin Send News
def broadcast_handler(message):
    chat_id = message.chat.id

    if is_admin(chat_id):
        bot.send_message(chat_id, "Напишіть повідомлення для всіх гостей:")
        set_user_state(chat_id, "BROADCAST")
    else:
        bot.send_message(chat_id, "У вас немає прав адміністратора.")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id) == "BROADCAST")
def send_broadcast(message):
    chat_id = message.chat.id
    text = message.text

    for user in get_users():
        bot.send_message(user[0], text)

    bot.send_message(chat_id, "Повідомлення успішно відправлене всім гостям.")
    set_user_state(chat_id, 'USERMAINMENU')

# Main loop
if __name__ == "__main__":
    init_db()
    bot.polling(none_stop=True)