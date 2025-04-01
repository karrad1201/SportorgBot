import telebot
import config
import os
import logging
from logger_config import errors_logger

def save_avatar(user_id, file):
    """Сохраняет аватарку пользователя в папку avatar."""
    try:
        # Создаем папку avatar, если её нет
        if not os.path.exists("avatar"):
            os.makedirs("avatar")

        # Получаем расширение файла
        file_extension = file.file_path.split('.')[-1]
        avatar_path = f"avatar/{user_id}.{file_extension}"

        # Сохраняем файл
        with open(avatar_path, 'wb') as new_file:
            new_file.write(file.download())

        return avatar_path
    except Exception as e:
        print(f"Ошибка при сохранении аватарки: {e}")
        return None

def delete_avatar(avatar_path):
    """Удаляет аватарку пользователя."""
    try:
        if avatar_path and os.path.exists(avatar_path):
            os.remove(avatar_path)
    except Exception as e:
        print(f"Ошибка при удалении аватарки: {e}")

bot = telebot.TeleBot(config.BOT_TOKEN)

def send_and_save_message(chat_id, text=None, photo=None, **kwargs):
    """Отправляет сообщение (текст или фото) и возвращает message_id."""
    try:
        if photo:
            sent_message = bot.send_photo(chat_id, photo, **kwargs)
        else:
            sent_message = bot.send_message(chat_id, text, **kwargs)

        return sent_message.message_id

    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")
        return None

def delete_message(chat_id, message_id):
    """Удаляет сообщение."""
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        None
