from Mytoken import TOKEN
import telebot
from telebot import types
import sqlite3
import requests
import json

# Создание БД
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users
               (username TEXT, token TEXT)''')
conn.commit()
conn.close()

# Токен бота
bot = telebot.TeleBot(TOKEN)


def get_token(username):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT token FROM users WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.commit()
    conn.close()

    # По апи передать список задач по токену
    return 'Token ' + result[0]


def get_keyboard(task):
    keyboard = types.InlineKeyboardMarkup()
    not_done_button = types.InlineKeyboardButton(text='Не выполнено', callback_data=f'not_done {task["id"]}')
    done_button = types.InlineKeyboardButton(text='Выполнено', callback_data=f'done {task["id"]}')
    in_process_button = types.InlineKeyboardButton(text='В процессе', callback_data=f'in_process {task["id"]}')
    delete_button = types.InlineKeyboardButton(text='Удалить', callback_data=f'delete {task["id"]}')
    if not task['status'] == 'Выполнено':
        keyboard.add(done_button)
    if not task['status'] == 'Не выполнено':
        keyboard.add(not_done_button)
    if not task['status'] == 'В процессе':
        keyboard.add(in_process_button)
    keyboard.add(delete_button)
    return keyboard


def post_task(message):
    # Выгрузка из БД
    headers1 = {'Content-Type': 'application/json', 'Authorization': get_token(message.from_user.username), }

    user_text = message.text
    user_text = user_text.split("; ")

    name = user_text[0]
    target = user_text[1]
    deadline = user_text[2]
    print(name)
    print(target)
    print(deadline)
    body = {
        "name": name,
        "target": target,
        "deadline": deadline,
        "status": "Не выполнено"
    }

    response = requests.post('http://127.0.0.1:8000/api/tasks/', headers=headers1, data=json.dumps(body))

    if response.status_code == 201:
        bot.send_message(message.chat.id, 'Задача добавлена!')
    else:
        bot.send_message(message.chat.id, 'Введены некорректные данные!')


# Команда старт
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Привет!")

    # Проверка, что пользователь зарегался
    username = message.from_user.username
    response = requests.get('http://127.0.0.1:8000/api/auth/users/').json()
    for x in response:
        if x['username'] == username:
            break
    else:
        body = {
            "username": username,
            "password": "testpassword1"
        }
        headers = {'Content-Type': 'application/json', }
        requests.post('http://127.0.0.1:8000/api/auth/users/',
                      headers=headers, data=json.dumps(body))
        response_to_get_token = requests.post('http://127.0.0.1:8000/api/auth/token/login/',
                                              headers=headers, data=json.dumps(body))
        user_token = response_to_get_token.json()['auth_token']

        # Добавление айди и токен в бд
        conn = sqlite3.connect('database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, token) VALUES (?, ?)", (username, user_token))
        conn.commit()
        conn.close()
        print("Love kate")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Мои Задачи")
    markup.add(item1)
    item2 = types.KeyboardButton("Добавить Задачу")
    markup.add(item2)
    bot.send_message(message.chat.id, "Можешь работать над своими задачами!",
                     reply_markup=markup)


# Ответы на команду меню
@bot.message_handler(content_types=['text'])
def message_reply(message):
    if message.text == "Мои Задачи":
        bot.send_message(message.chat.id, 'Вот список ваших задач:')

        headers1 = {'Content-Type': 'application/json', 'Authorization': get_token(message.from_user.username), }
        response = requests.get('http://127.0.0.1:8000/api/tasks/', headers=headers1)

        for task in response.json():
            task_msg = (f'Название: {task["name"]}\n'
                        f'target: {task["target"]}\n'
                        f'deadline: {task["deadline"]}\n'
                        f'status: {task["status"]}\n')
            bot.send_message(message.chat.id, task_msg, reply_markup=get_keyboard(task))

    elif message.text == "Добавить Задачу":
        bot.send_message(message.chat.id,
                         'Напиши название вашей задачи; вашу цель; дедлайн(в формате YYYY-MM-DD). Например:')
        bot.send_message(message.chat.id, 'Домашка по математике; сделать упражнение 1, 2, 3; 2023-12-30')
        bot.register_next_step_handler(message, post_task)


@bot.callback_query_handler(func=lambda call: call.data.startswith('not_done'))
def approve_image(callback_query):
    id = callback_query.json['data'].split()[1]
    username = callback_query.json['from']['username']
    body = {
        "status": "Не выполнено"
    }
    headers1 = {'Content-Type': 'application/json', 'Authorization': get_token(username), }
    requests.patch(f'http://127.0.0.1:8000/api/tasks/{id}/',
                   headers=headers1, data=json.dumps(body))
    bot.edit_message_text('Время собраться с мыслями!', chat_id=callback_query.message.chat.id,
                          message_id=callback_query.message.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('done'))
def approve_image(callback_query):
    id = callback_query.json['data'].split()[1]
    username = callback_query.json['from']['username']
    body = {
        "status": "Выполнено"
    }
    headers1 = {'Content-Type': 'application/json', 'Authorization': get_token(username), }
    requests.patch(f'http://127.0.0.1:8000/api/tasks/{id}/',
                   headers=headers1, data=json.dumps(body))
    bot.edit_message_text('Отличная работа!', chat_id=callback_query.message.chat.id,
                          message_id=callback_query.message.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('in_process'))
def approve_image(callback_query):
    id = callback_query.json['data'].split()[1]
    username = callback_query.json['from']['username']
    body = {
        "status": "В процессе"
    }
    headers1 = {'Content-Type': 'application/json', 'Authorization': get_token(username), }
    requests.patch(f'http://127.0.0.1:8000/api/tasks/{id}/',
                   headers=headers1, data=json.dumps(body))
    bot.edit_message_text('Все получится!', chat_id=callback_query.message.chat.id,
                          message_id=callback_query.message.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete'))
def approve_image(callback_query):
    id = callback_query.json['data'].split()[1]
    username = callback_query.json['from']['username']

    headers1 = {'Content-Type': 'application/json', 'Authorization': get_token(username), }
    requests.delete(f'http://127.0.0.1:8000/api/tasks/{id}/',
                    headers=headers1)
    bot.edit_message_text('Задача удалена!', chat_id=callback_query.message.chat.id,
                          message_id=callback_query.message.id)


bot.polling(none_stop=True)
