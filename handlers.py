# bot/handlers.py
import utils, database, config, products
from config import BAD_WORDS
from database import connection
from telebot import types
from telebot.apihelper import ApiTelegramException
from threading import Lock
import sqlite3
import random
import os
import logging
from logger_config import transactions_logger, errors_logger


bot = utils.bot

db_lock = Lock()
TRAINERS_PER_PAGE = 1

current_review_index = 0
reviews_list = []



@bot.message_handler(commands=['start'])
def start_handler(message):
    """Приветствие пользователя и добавление в БД при команде /start."""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        name = message.from_user.first_name

        # Пытаемся добавить пользователя в базу данных
        added = database.add_user(user_id, chat_id, name)
        if added:
            print(f"Добавлен новый пользователь: ID={user_id}, Chat ID={chat_id}, Name={name}")
        else:
            # Пользователь уже существует в базе данных, просто выводим сообщение
            print(f"Пользователь с ID={user_id} уже существует.")

        # Создаем клавиатуру
        markup = types.InlineKeyboardMarkup()
        btn_info = types.InlineKeyboardButton('Информация', callback_data='info')
        markup.add(btn_info)

        # Отправляем приветственное сообщение
        text = f"Добро пожаловать, ***{name}***! Я Millenium - твой личный бот-помощник для: \n\n  🛒 Покупки абонемента в спортзал \n\n  💲 Мониторинга цен \n\n  🆘***Если есть вопросы:*** @KarrradM "
        message_id = utils.send_and_save_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
        utils.delete_message(chat_id, message.message_id)

    except Exception as e:
        errors_logger.error(f"Ошибка в start_handler: {e}", exc_info=True)

@bot.callback_query_handler(func=lambda call: call.data == 'info')
def info_handler(call):
    """Вывод информации о боте."""
    try:
        markup = types.InlineKeyboardMarkup()
        btntren = types.InlineKeyboardButton(f'💪 Список тренеров', callback_data='trainers')
        ###btnfrz = types.InlineKeyboardButton(f'❄️Заморозка', callback_data='freeze')
        btninfacc = types.InlineKeyboardButton(f'👤 Профиль', callback_data='account')
        btnbuy = types.InlineKeyboardButton(f'📋 Ассортимент', callback_data='buy')
        ###btncall = types.InlineKeyboardButton(f'☎️ Связь с тренером', callback_data='call')
        btnball = types.InlineKeyboardButton(f'💰 Баланс', callback_data='balance')
        btnrecall = types.InlineKeyboardButton(f'🖋 Отзывы людей', callback_data='recall')
        btnmyclasses = types.InlineKeyboardButton(f'📅 Мои занятия', callback_data='my_classes')  # Новая кнопка
        markup.row(btninfacc, btnball)
        markup.row(btntren, btnmyclasses)
        markup.row(btnbuy, btnrecall)  # Добавляем кнопку в меню

        text = f' 🤖***Ниже представлен весь функционал бота*** \n🆘***Если есть вопросы:*** @KarrradM'
        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        errors_logger.error(f"Ошибка в info_handler: {e}", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data == 'account')
def account_handler(call):
    """Обработчик для кнопки 'Профиль'."""
    try:
        user_id = call.from_user.id
        user_data = database.get_user(user_id)

        if user_data:
            name = user_data[2]  # Имя пользователя
            balance = user_data[3]  # Баланс
            phone = user_data[4] if user_data[4] else "Не указан"  # Номер телефона
            avatar_path = user_data[5]  # Путь к аватарке

            # Формируем текст профиля
            text = f"👤 *Имя:* {name}\n"
            text += f"💰 *Баланс:* {balance}\n"
            text += f"📞 *Номер:* {phone}"

            # Создаем клавиатуру
            markup = types.InlineKeyboardMarkup()
            btn_edit = types.InlineKeyboardButton('Изменить', callback_data='edit_profile')
            btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
            markup.row(btn_edit, btn_back)

            # Отправляем фото профиля и текст, если фото есть
            if avatar_path and os.path.exists(avatar_path):
                with open(avatar_path, 'rb') as photo:
                    utils.delete_message(call.message.chat.id, call.message.message_id)
                    bot.send_photo(call.message.chat.id, photo, caption=text, reply_markup=markup, parse_mode="Markdown")
            else:
                # Если фото нет, предлагаем добавить фото
                markup_add_photo = types.InlineKeyboardMarkup()
                btn_add_photo = types.InlineKeyboardButton('Добавить фото', callback_data='edit_avatar')
                btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
                markup_add_photo.row(btn_add_photo, btn_back)

                utils.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, text + "\n\n❌ Фото профиля не найдено.", reply_markup=markup_add_photo, parse_mode="Markdown")
        else:
            utils.send_and_save_message(call.message.chat.id, "❌ Профиль не найден.", parse_mode="Markdown")

    except Exception as e:
        errors_logger.error(f"Ошибка в account_handler: {e}", exc_info=True)



@bot.callback_query_handler(func=lambda call: call.data == 'trainings')
def trainings_handler(call):
    """Обработчик для кнопки 'Разовое занятие'."""
    try:
        markup = types.InlineKeyboardMarkup()
        for training_id, training in products.TRAININGS.items():
            btn = types.InlineKeyboardButton(training['name'], callback_data=f"selecttraining_{training_id}")
            markup.add(btn)
        btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back3")  # Возврат к buying_handler
        markup.add(btn_back)

        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, "🗂 Выберите разовое занятие:", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        errors_logger.error(f"Ошибка в trainings_handler: {e}", exc_info=True)

@bot.callback_query_handler(func=lambda call: call.data == 'edit_profile')
def edit_profile_handler2(call):
    """Обработчик для кнопки 'Изменить'."""
    try:
        markup = types.InlineKeyboardMarkup()
        btn_edit_name = types.InlineKeyboardButton('Изменить имя', callback_data='edit_name')
        btn_edit_phone = types.InlineKeyboardButton('Изменить номер', callback_data='edit_phone')
        btn_edit_avatar = types.InlineKeyboardButton('Изменить фото', callback_data='edit_avatar')
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back7')
        markup.add(btn_edit_name, btn_edit_phone)
        markup.add(btn_edit_avatar, btn_back)

        # Удаляем предыдущие сообщения
        print(f"Попытка удалить сообщение в чате {call.message.chat.id}")
        utils.delete_message(call.message.chat.id, call.message.message_id)

        # Отправляем новое сообщение
        utils.send_and_save_message(call.message.chat.id, "Что вы хотите изменить?", reply_markup=markup)
    except Exception as e:
        errors_logger.error(f"Ошибка в edit_profile_handler2: {e}", exc_info=True)

@bot.callback_query_handler(func=lambda call: call.data == 'edit_name')
def edit_name_handler(call):
    """Обработчик для кнопки 'Изменить имя'."""
    try:
        utils.delete_message(call.message.chat.id, call.message.message_id)  # Исправлено: передаем message_id
        bot.send_message(call.message.chat.id, "📝 Введите новое имя:")
        bot.register_next_step_handler(call.message, process_new_name)
    except Exception as e:
        errors_logger.error(f"Ошибка в edit_name_handler: {e}", exc_info=True)
def process_new_name(message):
    """Обрабатывает ввод нового имени."""
    user_id = message.from_user.id
    new_name = message.text

    if database.update_user_name(user_id, new_name):
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back7')
        markup.add(btn_back)
        utils.send_and_save_message(message.chat.id, "✅ Имя успешно изменено!", reply_markup=markup)
    else:
        utils.send_and_save_message(message.chat.id, "❌ Ошибка при изменении имени.")

@bot.callback_query_handler(func=lambda call: call.data == 'edit_phone')
def edit_phone_handler(call):
    """Обработчик для кнопки 'Изменить номер'."""
    try:
        utils.delete_message(call.message.chat.id, call.message.message_id)  # Исправлено: передаем message_id
        bot.send_message(call.message.chat.id, "📞 Введите новый номер телефона:")
        bot.register_next_step_handler(call.message, process_new_phone)
    except Exception as e:
        errors_logger.error(f"Ошибка в edit_phone_handler: {e}", exc_info=True)

def process_new_phone(message):
    """Обрабатывает ввод нового номера телефона."""
    user_id = message.from_user.id
    new_phone = message.text

    if database.update_user_phone(user_id, new_phone):
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back7')
        markup.add(btn_back)
        utils.send_and_save_message(message.chat.id, "✅ Номер телефона успешно изменен!", reply_markup=markup)
    else:
        utils.send_and_save_message(message.chat.id, "❌ Ошибка при изменении номера телефона.")


@bot.callback_query_handler(func=lambda call: call.data == 'edit_avatar')
def edit_avatar_handler(call):
    """Обработчик для кнопки 'Изменить фото'."""
    try:
        markup = types.InlineKeyboardMarkup()
        # Удаляем предыдущее сообщение
        utils.delete_message(call.message.chat.id, call.message.message_id)

        # Отправляем сообщение с просьбой отправить новое фото
        bot.send_message(call.message.chat.id, "📸 Отправьте новое фото профиля:")
        bot.register_next_step_handler(call.message, process_new_avatar)

        # Добавляем кнопку "Назад"
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back7')
        markup.add(btn_back)

    except Exception as e:
        errors_logger.error(f"Ошибка в edit_avatar_handler: {e}", exc_info=True)

def process_new_avatar(message):
    """Обрабатывает ввод нового фото профиля."""
    user_id = message.from_user.id
    if message.photo:
        # Получаем самое большое фото
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Удаляем старое фото, если оно есть
        user_data = database.get_user(user_id)
        if user_data and user_data[5]:  # Проверяем, есть ли старое фото
            utils.delete_avatar(user_data[5])

        # Сохраняем новое фото
        file_extension = file_info.file_path.split('.')[-1]  # Получаем расширение файла
        avatar_path = f"avatar/{user_id}.{file_extension}"

        # Сохраняем файл
        with open(avatar_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        # Обновляем путь к аватарке в базе данных
        if database.update_user_avatar(user_id, avatar_path):
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back7')
            markup.add(btn_back)
            utils.send_and_save_message(message.chat.id, "✅ Фото профиля успешно изменено!", reply_markup=markup)
        else:
            utils.send_and_save_message(message.chat.id, "❌ Ошибка при изменении фото профиля.")
    else:
        utils.send_and_save_message(message.chat.id, "❌ Пожалуйста, отправьте фото.")

@bot.callback_query_handler(func=lambda call: call.data == '')
def edit_profile_handler1(call):
    """Обработчик для кнопки 'Изменить'."""
    try:
        markup = types.InlineKeyboardMarkup()
        btn_edit_name = types.InlineKeyboardButton('Изменить имя', callback_data='edit_name')
        btn_edit_phone = types.InlineKeyboardButton('Изменить номер', callback_data='edit_phone')
        btn_edit_avatar = types.InlineKeyboardButton('Изменить фото', callback_data='edit_avatar')
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
        markup.add(btn_edit_name, btn_edit_phone, btn_edit_avatar, btn_back)

        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, "Что вы хотите изменить?", reply_markup=markup)
    except Exception as e:
        errors_logger.error(f"Ошибка в edit_profile_handler1: {e}", exc_info=True)

def get_trainers_page(page_num):
    """Возвращает список тренеров для указанной страницы."""
    trainers = list(products.TRAINERS.values())
    start_index = (page_num - 1) * TRAINERS_PER_PAGE
    end_index = start_index + TRAINERS_PER_PAGE
    return trainers[start_index:end_index]

def format_trainer(trainer):
    """Форматирует информацию о тренере для отображения."""
    fio = trainer['fio']
    name = trainer['name']
    description = trainer['description']
    vk_link = trainer['vk_link']
    telegram_link = trainer['telegram_link']
    photo = trainer['photo']  # Путь к фотографии

    # Формируем сообщение с использованием HTML-разметки и эмодзи
    message_text = f"<b>💪 {fio}</b>\n"  # ФИО выделено жирным и добавлен эмодзи
    message_text += f"<i>{name}</i>\n\n"  # Имя выделено курсивом и добавлен отступ

    message_text += f"⭐ <i>Опыт и достижения:</i>\n"  # Заголовок для описания
    message_text += f"{description}\n\n"  # Описание с отступом

    message_text += f"🔗 <b>Связаться:</b>\n"  # Заголовок для ссылок
    message_text += f"🔵ВКонтакте: <a href=\"{vk_link}\">Перейти</a> ↗️\n"  # Ссылка на VK с эмодзи
    message_text += f"🔵Telegram: <a href=\"{telegram_link}\">Написать</a> ✉️\n"  # Ссылка на Telegram с эмодзи
    return message_text, photo


@bot.callback_query_handler(func=lambda call: call.data == 'recall')
def recall_handler(call):
    """Обработчик для кнопки 'Отзывы'."""
    global current_review_index, reviews_list

    # Удаляем предыдущее сообщение
    utils.delete_message(call.message.chat.id, call.message.message_id)

    # Получаем все отзывы из базы данных
    reviews_list = database.get_all_reviews()

    if not reviews_list:
        # Если отзывов нет, показываем сообщение и кнопки
        markup = types.InlineKeyboardMarkup()
        btn_write_review = types.InlineKeyboardButton('Написать отзыв', callback_data='write_review')
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
        markup.add(btn_write_review, btn_back)
        utils.send_and_save_message(call.message.chat.id, "❌ Отзывов пока нет.", reply_markup=markup)
    else:
        # Если отзывы есть, показываем случайный отзыв
        current_review_index = random.randint(0, len(reviews_list) - 1)
        show_review(call.message.chat.id, current_review_index, call.message.message_id)  # Передаем message_id

def show_review(chat_id, review_index, message_id):
    """Показывает отзыв по индексу."""
    global reviews_list

    review = reviews_list[review_index]
    user_id = review[1]  # ID пользователя, оставившего отзыв
    user_data = database.get_user(user_id)
    user_name = user_data[2] if user_data else "Неизвестный пользователь"  # Имя пользователя

    review_text = f"📝 Отзыв от пользователя {user_name}:\n\n{review[2]}"

    markup = types.InlineKeyboardMarkup()
    btn_prev = types.InlineKeyboardButton('⬅️ Предыдущий', callback_data='prev_review')
    btn_next = types.InlineKeyboardButton('Следующий ➡️', callback_data='next_review')
    btn_write_review = types.InlineKeyboardButton('Написать отзыв', callback_data='write_review')
    btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
    markup.add(btn_prev, btn_next)
    markup.add(btn_write_review, btn_back)

    utils.delete_message(chat_id, message_id)  # Используем переданный message_id
    utils.send_and_save_message(chat_id, review_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'next_review')
def next_review_handler(call):
    """Обработчик для кнопки 'Следующий'."""
    global current_review_index, reviews_list

    # Получаем случайный отзыв
    current_review_index = random.randint(0, len(reviews_list) - 1)
    show_review(call.message.chat.id, current_review_index, call.message.message_id)  # ПЕРЕДАЕМ message_id

@bot.callback_query_handler(func=lambda call: call.data == 'prev_review')
def prev_review_handler(call):
    """Обработчик для кнопки 'Предыдущий'."""
    global current_review_index, reviews_list

    # Показываем предыдущий отзыв
    current_review_index = (current_review_index - 1) % len(reviews_list)
    show_review(call.message.chat.id, current_review_index, call.message.message_id)  # ПЕРЕДАЕМ message_id

@bot.callback_query_handler(func=lambda call: call.data == 'write_review')
def write_review_handler(call):
    """Обработчик для кнопки 'Написать отзыв'."""
    utils.delete_message(call.message.chat.id, call.message.message_id) # Удаляем предыдущее сообщение
    bot.send_message(call.message.chat.id, "📝 Напишите ваш отзыв:")
    bot.register_next_step_handler(call.message, process_review)



def contains_bad_word(text):
    """Проверяет, содержит ли текст запрещенные слова."""
    text = text.lower()  # Приводим к нижнему регистру для регистронезависимости
    for word in BAD_WORDS:
        if word in text:
            return True
    return False

def process_review(message):
    """Обрабатывает ввод отзыва."""
    user_id = message.from_user.id
    review_text = message.text

    if not database.check_review_cooldown(user_id):
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
        markup.add(btn_back)
        utils.send_and_save_message(message.chat.id, "❌ Вы можете написать только один отзыв в сутки. Попробуйте завтра.", reply_markup=markup)
        return

    if contains_bad_word(review_text):
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
        markup.add(btn_back)

        utils.send_and_save_message(message.chat.id, "❌ Ваш отзыв содержит недопустимые выражения и не будет добавлен.", reply_markup=markup)
        return

    if database.add_review(user_id, review_text):
        # Удаляем предыдущее сообщение
        utils.delete_message(message.chat.id, message.message_id)  # Передаем message_id

        # Добавляем кнопку "Назад"
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
        markup.add(btn_back)

        # Отправляем сообщение об успешном добавлении отзыва
        utils.send_and_save_message(message.chat.id, "✅ Ваш отзыв успешно добавлен!", reply_markup=markup)
    else:
        utils.send_and_save_message(message.chat.id, "❌ Произошла ошибка при добавлении отзыва.")


@bot.callback_query_handler(func=lambda call: call.data == 'my_classes')
def my_classes_handler(call):
    """Обработчик для кнопки 'Мои Занятия'."""
    try:
        user_id = call.from_user.id

        # Получаем активные абонементы
        abonements = database.get_user_abonements(user_id)

        # Формируем сообщение
        text = "⏳ Ваши активные абонементы:\n\n"
        if abonements:
            for abonement in abonements:
                abonement_id = abonement[0]
                end_date = abonement[1]
                visits_left = abonement[2]
                abonement_info = products.ABONEMENTS.get(abonement_id)
                train_info = products.TRAININGS.get(abonement_id)
                if abonement_info:
                    text += f"- {abonement_info['name']} (до {end_date}"
                    if 'visits' in abonement_info:
                        text += f", осталось {visits_left} посещений)\n"
                    else:
                        text += ")\n"  # Безлимитный абонемент
                elif train_info:
                    text += f"- {train_info['name']} (до {end_date})\n"
                else:
                    text += f"- Неизвестный абонемент (до {end_date})\n"
        else:
            text += "❌ У вас нет активных абонементов.\n"

        markup = types.InlineKeyboardMarkup()
        btn_history = types.InlineKeyboardButton("📋 История Посещений", callback_data="visits_history")  # Новая кнопка
        btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back2")
        markup.add(btn_history)
        markup.add(btn_back)

        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        errors_logger.error(f"Ошибка в my_classes_handler: {e}", exc_info=True)

@bot.callback_query_handler(func=lambda call: call.data == 'visits_history')
def visits_history_handler(call):
    """Обработчик для кнопки 'История Посещений'."""
    try:
        user_id = call.from_user.id
        visits = database.get_visits(user_id)

        if visits:
            message_text = "📋 История ваших посещений:\n"
            for timestamp, description in visits:
                # Экранируем символы Markdown в описании
                description = description.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
                message_text += f"- {timestamp}: {description}\n"
        else:
            message_text = "❌ У вас пока нет записей о посещениях."

        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
        markup.add(btn_back)

        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, message_text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        errors_logger.error(f"Ошибка в visits_history_handler: {e}", exc_info=True)



@bot.callback_query_handler(func=lambda call: call.data == 'trainers')
def trainers_handler(call):
    """Обработчик для кнопки 'Список тренеров'."""
    try:
        chat_id = call.message.chat.id
        page_num = 1  # Начинаем с первой страницы
        trainers = get_trainers_page(page_num)
        total_trainers = len(products.TRAINERS)
        total_pages = (total_trainers + TRAINERS_PER_PAGE - 1) // TRAINERS_PER_PAGE  # Количество страниц

        markup = types.InlineKeyboardMarkup()

        # Добавляем кнопки "Вперед" и "Назад", если необходимо
        if total_pages > 1:
            if page_num > 1:
                btn_prev = types.InlineKeyboardButton('⬅️ Назад', callback_data=f'trainers_page_{page_num - 1}_{call.message.message_id}')
                markup.add(btn_prev)
            if page_num < total_pages:
                btn_next = types.InlineKeyboardButton('Вперед ➡️', callback_data=f'trainers_page_{page_num + 1}_{call.message.message_id}')
                markup.add(btn_next)

        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
        markup.add(btn_back)

        # Удаляем предыдущее сообщение
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except ApiTelegramException as e:
            print(f"Ошибка при удалении сообщения в trainers_handler: {e}")

        if trainers:
            # Если есть тренеры на странице, отправляем информацию о первом тренере
            trainer = trainers[0]
            if trainer:  # Проверяем, что trainer не None
                trainer_text, trainer_photo = format_trainer(trainer)
                if trainer_text and trainer_photo:
                    try:
                        with open(trainer_photo, 'rb') as photo:
                            bot.send_photo(chat_id, photo=photo, caption=trainer_text, parse_mode="HTML", reply_markup=markup)
                    except FileNotFoundError:
                        print(f"Ошибка: Файл {trainer_photo} не найден.")
                        utils.send_and_save_message(chat_id, "❌ Ошибка: Фото тренера не найдено.", reply_markup=markup, parse_mode="HTML")
                else:
                    utils.send_and_save_message(chat_id, "❌ Ошибка при форматировании данных тренера.", reply_markup=markup, parse_mode="HTML")
            else:
                utils.send_and_save_message(chat_id, "❌ Ошибка: Нет информации о тренере.", reply_markup=markup, parse_mode="HTML")
        else:
            utils.send_and_save_message(chat_id, "❌ Нет тренеров для отображения.", reply_markup=markup, parse_mode="HTML")

    except Exception as e:
        errors_logger.error(f"Ошибка в trainers_handler: {e}", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('trainers_page_'))
def trainers_page_handler(call):
    """Обработчик для кнопок 'Вперед' и 'Назад'."""
    try:
        chat_id = call.message.chat.id
        data = call.data.split('_')

        # Проверяем, что callback_data содержит достаточно элементов
        if len(data) < 4:
            print(f"Некорректный формат callback_{call.data}")
            return

        page_num = int(data[2])  # Получаем номер страницы из callback_data
        try:
            old_message_id = int(data[3])  # Получаем message_id из callback_data
        except (IndexError, ValueError):
            print(f"Некорректный формат message_id: {call.data}")
            old_message_id = None

        # Удаляем предыдущее сообщение
        if old_message_id:
            try:
                print(f"Попытка удалить сообщение trainers_page_handler с ID: {call.message.message_id}")
                bot.delete_message(chat_id, call.message.message_id)  # Используем call.message.message_id
            except ApiTelegramException as e:
                print(f"Ошибка при удалении сообщения: {e}")

        # Получаем список тренеров для текущей страницы
        trainers = get_trainers_page(page_num)
        total_trainers = len(products.TRAINERS)
        total_pages = (total_trainers + TRAINERS_PER_PAGE - 1) // TRAINERS_PER_PAGE

        markup = types.InlineKeyboardMarkup()
        buttons = []

        # Добавляем кнопку "Назад", если это не первая страница
        if page_num > 1:
            btn_prev = types.InlineKeyboardButton('⬅️ Назад', callback_data=f'trainers_page_{page_num - 1}_{call.message.message_id}')
            buttons.append(btn_prev)

        # Добавляем кнопку "Вперед", если это не последняя страница
        if page_num < total_pages:
            btn_next = types.InlineKeyboardButton('Вперед ➡️', callback_data=f'trainers_page_{page_num + 1}_{call.message.message_id}')
            buttons.append(btn_next)
        if buttons:
            markup.row(*buttons)

        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
        markup.add(btn_back)

        if trainers:
            # Если есть тренеры на странице, отправляем информацию о первом тренере
            trainer_text, trainer_photo = format_trainer(trainers[0])
            with open(trainer_photo, 'rb') as photo:
                sent_message = bot.send_photo(chat_id, photo=photo, caption=trainer_text, parse_mode="HTML",
                                              reply_markup=markup)
                # utils.send_and_save_message(chat_id, text=trainer_text, photo=photo, reply_markup=markup, parse_mode="HTML")
        else:
            sent_message = utils.send_and_save_message(chat_id, "❌ Нет тренеров для отображения.", reply_markup=markup,
                                                       parse_mode="HTML")
    except Exception as e:
        errors_logger.error(f"Ошибка в trainers_page_handler: {e}", exc_info=True)

@bot.callback_query_handler(func=lambda call: call.data == 'noop')
def noop_handler(call):
    """Обработчик для кнопок, которые ничего не делают."""
    bot.answer_callback_query(call.id)  # Отвечает на callback, чтобы убрать "часики"
@bot.callback_query_handler(func=lambda call: call.data == 'buy')
def buying_handler(call):
    """Обработчик для кнопки 'Ассортимент'."""
    try:
        # Здесь должен быть код, который выводит ассортимент
        markup = types.InlineKeyboardMarkup()
        btn_abonements = types.InlineKeyboardButton("Абонементы", callback_data="abonements")
        btn_trainings = types.InlineKeyboardButton("Разовое занятие", callback_data="trainings")
        btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back2")
        markup.add(btn_abonements)
        markup.add(btn_trainings)
        markup.add(btn_back)

        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, "🗂 Выберите категорию:", reply_markup=markup,
                                    parse_mode="Markdown")

    except Exception as e:
        errors_logger.error(f"Ошибка в buying_handler: {e}", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data == 'abonements')
def abonements_handler(call):
    """Обработчик для кнопки 'Абонементы'."""
    try:
        markup = types.InlineKeyboardMarkup()
        for abonement_id, abonement in products.ABONEMENTS.items():
            print(f"abonement_id: {abonement_id}, type: {type(abonement_id)}")
            btn = types.InlineKeyboardButton(abonement['name'], callback_data=f"selectabonement_{abonement_id}")
            markup.add(btn)
        btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back3")  # Возврат к buying_handler
        markup.add(btn_back)

        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, "🗂 Выберите абонемент:", reply_markup=markup,
                                    parse_mode="Markdown")
    except Exception as e:
        errors_logger.error(f"Ошибка в abonements_handler: {e}", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('selectabonement_'))
def select_abonement_handler(call):
    """Обработчик для выбора конкретного абонемента."""
    try:
        # Извлекаем abonement_id из callback_data
        abonement_id = call.data.replace('selectabonement_', '')
        print(f"select_abonement_handler: abonement_id = {abonement_id}, type: {type(abonement_id)}")

        # Получаем абонемент из словаря
        abonement = products.ABONEMENTS.get(abonement_id)

        if abonement is None:
            utils.send_and_save_message(call.message.chat.id, "❌ Абонемент не найден.", parse_mode="Markdown")
            return

        user_id = call.from_user.id

        # Выводим информацию о выбранном абонементе
        text = f"Вы выбрали абонемент: *{abonement['name']}*\nЦена: {abonement['price']} рублей"
        markup = types.InlineKeyboardMarkup()
        btn_buy = types.InlineKeyboardButton("Купить", callback_data=f"buyabonement_{abonement_id}")
        btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back6")
        markup.add(btn_buy, btn_back)

        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        errors_logger.error(f"Ошибка в select_abonement_handler: {e}", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('buyabonement_'))
def buy_abonement_handler(call):
    """Обработчик для покупки абонемента."""
    print("buy_abonement_handler called")  # Добавлено для отладки
    try:
        abonement_id = call.data.replace('buyabonement_', '')
        user_id = call.from_user.id
        abonement = products.ABONEMENTS.get(abonement_id)

        if not abonement:
            utils.send_and_save_message(call.message.chat.id, "Ошибка:❌ Абонемент не найден.")
            return

        # Проверяем баланс пользователя
        balance = database.get_balance(user_id)
        if balance < abonement['price']:
            utils.send_and_save_message(call.message.chat.id, "❌ Недостаточно средств на балансе.")
            return

        # Списываем деньги с баланса
        success = database.update_balance(user_id, -abonement['price'], f"Покупка абонемента {abonement_id}")
        if not success:
            utils.send_and_save_message(call.message.chat.id, "❌ Ошибка при списании средств.")
            return

        # Добавляем абонемент в таблицу user_subscriptions
        with db_lock:
            cursor = connection.cursor()
            end_date = f"datetime('now', '+{abonement.get('duration', 30)} days')"  # Длительность в днях
            visits = abonement.get('visits')
            abonement_name = abonement['name']  # Получаем название абонемента
            is_training = False  # Добавляем флаг is_training

            # Учитываем количество посещений
            if visits:
                cursor.execute("""
                    INSERT INTO user_subscriptions (user_id, subscription_id, subscription_name, end_date, visits_left, is_training)
                    VALUES (?, ?, ?, """ + end_date + """, ?, ?)
                """, (user_id, abonement_id, abonement_name, visits, is_training))
            else:
                cursor.execute("""
                    INSERT INTO user_subscriptions (user_id, subscription_id, subscription_name, end_date, visits_left, is_training)
                    VALUES (?, ?, ?, """ + end_date + """, NULL, ?)
                """, (user_id, abonement_id, abonement_name, is_training))  # NULL для безлимитных

            connection.commit()

            # Выводим сообщение об успешной покупке
            markup = types.InlineKeyboardMarkup()
            utils.delete_message(call.message.chat.id, call.message.message_id)
            btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back2")
            markup.add(btn_back)
            utils.send_and_save_message(call.message.chat.id,
                                        f"✅ Вы успешно купили абонемент *{abonement['name']}*!\nНа вашем счету осталось: {balance - abonement['price']}",
                                        reply_markup=markup, parse_mode="Markdown")

            # Выводим сообщение в консоль
            print(f"Пользователь {user_id} купил абонемент {abonement_id}")

    except Exception as e:
        errors_logger.error(f"Ошибка в buy_abonement_handler: {e}", exc_info=True)



@bot.callback_query_handler(func=lambda call: call.data == 'history')
def show_history_handler(call):
    """Показывает историю транзакций пользователя."""
    try:
        user_id = call.from_user.id
        transactions = database.get_transactions(user_id)

        if transactions:
            message_text = "📋 История ваших транзакций:\n"
            for timestamp, type, amount, description in transactions:
                # Экранируем символы Markdown в описании
                description = description.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
                message_text += f"- {timestamp}: {type} {amount} руб. ({description})\n"
        else:
            message_text = "❌ У вас пока нет транзакций."

        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
        markup.add(btn_back)

        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, message_text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        errors_logger.error(f"Ошибка в show_history_handler: {e}", exc_info=True)
# Шаг 3.1: Редактируем функцию add_balance в database.py для вывода сообщения:

def update_balance(user_id, amount, description):
    """Обновляет баланс пользователя и добавляет запись в transactions."""
    with db_lock:  # Блокируем доступ к базе для операций записи
        try:
            cursor = connection.cursor()

            # Обновляем баланс пользователя
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))

            # Добавляем запись в transactions
            transaction_type = 'deposit' if amount > 0 else 'purchase'
            cursor.execute("""
                INSERT INTO transactions (user_id, type, amount, description)
                VALUES (?, ?, ?, ?)
            """, (user_id, transaction_type, amount, description))

            connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"❌ Ошибка при обновлении баланса: {e}")
            return False


def check_balance(message, user_id):
    with db_lock:  # Блокируем доступ к базе для операций записи
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))

            balance = cursor.fetchone()
            connection.commit()
            bot.reply_to(message, f'💰 Ваш текущий баланс: {balance[0]}')

        except sqlite3.Error as e:
            print(f"❌ Ошибка при зачислении средств: {e}")
            return False


def check_balance_CLI(user_id):
    with db_lock:  # Блокируем доступ к базе для операций записи
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))

            balance = cursor.fetchone()
            connection.commit()
            return (f'Баланс пользователя {user_id}: {balance[0]}')

        except sqlite3.Error as e:
            print(f"❌ Ошибка при зачислении средств: {e}")
            return False


@bot.callback_query_handler(func=lambda call: call.data == 'balance')
def check_balance_call_handler(call):
    """Выводит текущий баланс пользователю."""
    try:
        user_id = call.from_user.id
        cursor = connection.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()

        if balance:
            markup = types.InlineKeyboardMarkup()
            btn_transactions = types.InlineKeyboardButton("История транзакций", callback_data="transactions") #История транзакций
            btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="info")  # Кнопка "Назад"
            markup.add(btn_transactions)
            markup.add(btn_back)
            utils.delete_message(call.message.chat.id, call.message.message_id)
            utils.send_and_save_message(call.message.chat.id, f"💰 Ваш текущий баланс: `{balance[0]}`",
                                        reply_markup=markup, parse_mode="Markdown")
        else:
            utils.send_and_save_message(call.message.chat.id, "❌ Не удалось получить информацию о балансе.",
                                        parse_mode="Markdown")
    except Exception as e:
        errors_logger.error(f"Ошибка в check_balance_call_handler: {e}", exc_info=True)


@bot.message_handler(commands=['check_user_abonement'])
def check_user_abonements_handler(message):
    """Команда для просмотра списка абонементов пользователя (для отладки)."""
    try:
        user_id = message.from_user.id
        abonements = database.get_user_abonements(user_id)

        if abonements:
            message_text = "⏳ Ваши текущие абонементы:\n"
            for abonement_id, end_date, visits_left in abonements:
                message_text += f"- {abonement_id} (действует до {end_date}"
                if visits_left:
                    message_text += f", осталось посещений: {visits_left}"
                message_text += ")\n"

            bot.send_message(message.chat.id, message_text)
        else:
            bot.send_message(message.chat.id, "❌ У вас нет активных абонементов.")

    except Exception as e:
        errors_logger.error(f"Ошибка в check_user_abonements_handler: {e}", exc_info=True)

@bot.callback_query_handler(func=lambda call: call.data == 'transactions')
def transactions_handler(call):
    """Показывает историю транзакций пользователя."""
    try:
        user_id = call.from_user.id
        transactions = database.get_transactions(user_id)

        if transactions:
            message_text = "💰 *История Ваших транзакций:*\n"
            current_message = ""
            for timestamp, type, amount, description in transactions:
                # Экранируем специальные символы Markdown в описании
                description = description.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`").replace("[", "\\[").replace("]", "\\]").replace("(", "\\(").replace(")", "\\)")
                transaction_text = f"• _Дата:_ {timestamp}\n   _Тип:_ {type}\n   _Сумма:_ {amount} руб.\n   _Описание:_ {description}\n\n"

                # Если добавление новой транзакции превысит лимит, отправляем текущее сообщение и начинаем новое
                if len(current_message) + len(transaction_text) > 4096:
                    markup = types.InlineKeyboardMarkup()
                    btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='info')
                    markup.add(btn_back)
                    utils.delete_message(call.message.chat.id, call.message.message_id)
                    utils.send_and_save_message(call.message.chat.id, current_message, reply_markup=markup, parse_mode="Markdown")
                    current_message = ""  # Начинаем новое сообщение

                current_message += transaction_text

            # Отправляем последнее сообщение, если оно не пустое
            if current_message:
                markup = types.InlineKeyboardMarkup()
                btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='info')
                markup.add(btn_back)
                utils.delete_message(call.message.chat.id, call.message.message_id)
                utils.send_and_save_message(call.message.chat.id, current_message, reply_markup=markup, parse_mode="Markdown")
        else:
            message_text = "❌ У вас пока нет транзакций."
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='info')
            markup.add(btn_back)
            utils.delete_message(call.message.chat.id, call.message.message_id)
            utils.send_and_save_message(call.message.chat.id, message_text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        errors_logger.error(f"Ошибка в show_history_handler: {e}", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data == 'trainers')
def trainers_handler(call):
    """Обработчик для кнопки 'Список тренеров'."""
    try:
        chat_id = call.message.chat.id
        page_num = 1  # Начинаем с первой страницы
        trainers = get_trainers_page(page_num)
        total_trainers = len(products.TRAINERS)
        total_pages = (total_trainers + TRAINERS_PER_PAGE - 1) // TRAINERS_PER_PAGE  # Количество страниц

        markup = types.InlineKeyboardMarkup()

        # Добавляем кнопки "Вперед" и "Назад", если необходимо
        if total_pages > 1:
            if page_num > 1:
                btn_prev = types.InlineKeyboardButton('⬅️ Назад', callback_data=f'trainers_page_{page_num - 1}_{call.message.message_id}')
                markup.add(btn_prev)
            if page_num < total_pages:
                btn_next = types.InlineKeyboardButton('Вперед ➡️', callback_data=f'trainers_page_{page_num + 1}_{call.message.message_id}')
                markup.add(btn_next)

        btn_back = types.InlineKeyboardButton('⬅️ Назад', callback_data='back2')
        markup.add(btn_back)

        # Удаляем предыдущее сообщение
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except ApiTelegramException as e:
            print(f"Ошибка при удалении сообщения в trainers_handler: {e}")

        if trainers:
            # Если есть тренеры на странице, отправляем информацию о первом тренере
            trainer = trainers[0]
            trainer_text, trainer_photo = format_trainer(trainer) if trainer else (None, None) # Добавлена проверка

            if trainer_text and trainer_photo: #Проверка форматирования тренера
                with open(trainer_photo, 'rb') as photo:
                    bot.send_photo(chat_id, photo=photo, caption=trainer_text, parse_mode="HTML", reply_markup=markup)
            else:
                utils.send_and_save_message(chat_id, "❌ Ошибка при форматировании данных тренера.", reply_markup=markup, parse_mode="HTML")
        else:
            utils.send_and_save_message(chat_id, "❌ Нет тренеров для отображения.", reply_markup=markup, parse_mode="HTML")

    except Exception as e:
        errors_logger.error(f"Ошибка в trainers_handler: {e}", exc_info=True)

@bot.callback_query_handler(func=lambda call: call.data == 'abonements')
def abonements_handler(call):
    """Обработчик для кнопки 'Абонементы'."""
    try:
        markup = types.InlineKeyboardMarkup()
        for abonement_id, abonement in products.ABONEMENTS.items():
            print(f"abonement_id: {abonement_id}, type: {type(abonement_id)}")
            btn = types.InlineKeyboardButton(abonement['name'], callback_data=f"selectabonement_{abonement_id}")
            markup.add(btn)
        btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back3")  # Возврат к buying_handler
        markup.add(btn_back)

        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, "🗂 Выберите абонемент:", reply_markup=markup,
                                    parse_mode="Markdown")
    except Exception as e:
        errors_logger.error(f"Ошибка в abonements_handler: {e}", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('selecttraining_'))
def select_training_handler(call):
    """Обработчик для выбора конкретного абонемента."""
    try:
        # Извлекаем abonement_id из callback_data
        training_id = call.data.replace('selecttraining_', '')
        print(f"select_training_handler: training_id = {training_id}, type: {type(training_id)}")

        # Получаем абонемент из словаря
        training = products.TRAININGS.get(training_id)

        if training is None:
            utils.send_and_save_message(call.message.chat.id, "❌ Разовое занятие не найдено.", parse_mode="Markdown")
            return

        user_id = call.from_user.id

        # Выводим информацию о выбранном абонементе
        text = f"Вы выбрали абонемент: *{training['name']}*\nЦена: {training['price']} рублей"
        markup = types.InlineKeyboardMarkup()
        btn_buy = types.InlineKeyboardButton("Купить", callback_data=f"buytraining_{training_id}")
        btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back6")
        markup.add(btn_buy, btn_back)

        utils.delete_message(call.message.chat.id, call.message.message_id)
        utils.send_and_save_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        errors_logger.error(f"Ошибка в select_training_handler: {e}", exc_info=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buytraining_'))
def buy_training_handler(call):
    """Обработчик для покупки разового занятия."""
    print("buy_training_handler called")  # Добавлено для отладки
    try:
        training_id = call.data.replace('buytraining_', '')
        user_id = call.from_user.id
        training = products.TRAININGS.get(training_id)

        if not training:
            utils.send_and_save_message(call.message.chat.id, "❌ Разовое занятие не найдено.")
            return

        # Проверяем баланс пользователя
        balance = database.get_balance(user_id)
        if balance < training['price']:
            utils.send_and_save_message(call.message.chat.id, "❌ Недостаточно средств на балансе.")
            return

        # Списываем деньги с баланса
        success = database.update_balance(user_id, -training['price'], f"Покупка занятия {training['name']}")
        if not success:
            utils.send_and_save_message(call.message.chat.id, "❌ Ошибка при списании средств.")
            return

        # Добавляем тренировку в таблицу user_subscriptions
        with db_lock:
            cursor = connection.cursor()
            end_date = f"datetime('now', '+{training.get('duration', 30)} days')"  # Длительность в днях, можно настроить
            visits = training.get('visits', 1) # Разовое занятие, обычно 1 посещение
            training_name = training['name']

            cursor.execute("""
                INSERT INTO user_subscriptions (user_id, subscription_id, subscription_name, end_date, visits_left, is_training)
                VALUES (?, ?, ?, """ + end_date + """, ?, 1)  -- is_training = 1 для разовых занятий
            """, (user_id, training_id, training_name, visits))

            connection.commit()

            # Выводим сообщение об успешной покупке
            markup = types.InlineKeyboardMarkup()
            utils.delete_message(call.message.chat.id, call.message.message_id)
            btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back2")
            markup.add(btn_back)
            utils.send_and_save_message(call.message.chat.id,
                                        f"✅ Вы успешно купили разовое занятие *{training['name']}*!\n", #убрал {balance - training['price']}
                                        reply_markup=markup, parse_mode="Markdown")

            # Выводим сообщение в консоль
            print(f"Пользователь {user_id} купил разовое занятие {training_id}")

    except Exception as e:
        errors_logger.error(f"Ошибка в buy_training_handler: {e}", exc_info=True)
    print("buy_training_handler finished")



@bot.callback_query_handler(func=lambda call: call.data.startswith('back'))
def back_navigation_handler(call):
    """Обработчик всех кнопок 'Назад'."""
    try:
        data = call.data
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        # Удаляем сообщение
        try:
            bot.delete_message(chat_id, message_id)
        except ApiTelegramException as e:
            print(f"Ошибка при удалении сообщения в back_navigation_handler: {e}")

        if data == 'back1':
            start_handler(call.message)
        elif data == 'back2':
            info_handler(call)
        elif data == 'back3':
            buying_handler(call)
        elif data == 'back6':
            # Возврат к выбору абонемента или тренировки
            buying_handler(call)
        elif data == 'back7':
            account_handler(call)

    except Exception as e:
        errors_logger.error(f"Ошибка в back_navigation_handler: {e}", exc_info=True)


@bot.message_handler(commands=[config.SECRET_COMMAND])
def show_users(message):
    """Обработчик секретной команды для просмотра списка пользователей (только для администраторов)."""
    try:
        if message.from_user.id in config.ADMIN_USER_ID:
            users = database.get_all_users()
            if users:
                output = "📋 Список пользователей:\n"
                for user in users:
                    output += f"ID: {user[0]}, Chat ID: {user[1]}, Имя: {user[2]}, Баланс: {user[3]}\n"
            bot.send_message(message.chat.id, "✅ Данные выведены в консоль.")
            print(output)
        else:
            bot.send_message(message.chat.id, "❌ У вас нет прав для выполнения этой команды.")
    except Exception as e:
        errors_logger.error(f"Ошибка в show_users: {e}", exc_info=True)


@bot.message_handler(commands=['products'])
def show_products(message):
    """Выводит содержимое products.py."""
    try:
        text = "Содержимое products.py:\n\n"
        text += "ABONEMENTS:\n"
        for key, value in products.ABONEMENTS.items():
            text += f"  {key}: {value}\n"

        text += "\nTRAININGS:\n"

        text += "\nTRAINERS:\n"
        for key, value in products.TRAINERS.items():
            text += f"  {key}: {value}\n"

        bot.send_message(message.chat.id, text)

    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {e}")
