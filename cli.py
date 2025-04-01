import sqlite3
import config
from threading import Lock
from database import check_balance_CLI, decrement_visits, reset_review_cooldown, add_visit
import telebot  # Добавляем импорт telebot
import sys
import logging
from logger_config import transactions_logger, errors_logger

# Глобальное подключение к базе данных
connection = sqlite3.connect(config.DATABASE_NAME, check_same_thread=False)
connection.execute("PRAGMA journal_mode=WAL;")  # Включаем WAL режим

# Глобальная блокировка для синхронизации операций записи
db_lock = Lock()

# Создаем экземпляр бота
bot = telebot.TeleBot(config.BOT_TOKEN)

def add_balance_command(user_id, amount, description):
    with db_lock:
        try:
            amount = float(amount)
            user_id = int(user_id)
        except ValueError:
            print("Ошибка: Неправильный формат user_id или amount.")
            return

        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            cursor.execute("""
                INSERT INTO transactions (user_id, type, amount, description)
                VALUES (?, ?, ?, ?)
            """, (user_id, 'deposit', amount, description))
            connection.commit()

            # Логируем пополнение баланса
            transactions_logger.info(f"User ID: {user_id}, Type: deposit, Amount: {amount}, Description: {description}")

            print(f"Успешно добавлено {amount} пользователю {user_id}. Описание: {description}")

            # Получаем chat_id пользователя
            cursor.execute("SELECT chat_id FROM users WHERE user_id = ?", (user_id,))
            chat_id = cursor.fetchone()[0]

            # Отправляем сообщение в чат
            bot.send_message(chat_id, f"На ваш баланс зачислено {amount} рублей. Описание: {description}")

        except sqlite3.Error as e:
            print(f"Ошибка при добавлении баланса: {e}")
            errors_logger.error(f"Ошибка при добавлении баланса: {e}", exc_info=True)

def check_balance_command(user_id):
    try:
        user_id = int(user_id)
    except ValueError:
        print("Ошибка: Неправильный формат user_id.")
        return
    print(check_balance_CLI(user_id))

def add_visit_command(user_id, description):
    try:
        user_id = int(user_id)
    except ValueError:
        print("Ошибка: Неправильный формат user_id.")
        return
    success = add_visit(user_id, description)
    if success:
        print(f"Успешно отмечено посещение пользователем {user_id}. Описание: {description}")
    else:
        print(f"Ошибка при отметке посещения пользователем {user_id}.")

def list_users_command():
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT user_id, chat_id, name, balance FROM users")
        users = cursor.fetchall()
        for user in users:
            print(f"ID: {user[0]}, Chat ID: {user[1]}, Name: {user[2]}, Balance: {user[3]}")
    except sqlite3.Error as e:
        print(f"Ошибка при чтении данных: {e}")

def show_transactions_command(user_id):
    try:
        user_id = int(user_id)
    except ValueError:
        print("Ошибка: Неправильный формат user_id.")
        return
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT timestamp, type, amount, description FROM transactions WHERE user_id = ?", (user_id,))
        transactions = cursor.fetchall()
        if transactions:
            print(f"История транзакций для пользователя {user_id}:")
            for transaction in transactions:
                print(f"  Timestamp: {transaction[0]}, Type: {transaction[1]}, Amount: {transaction[2]}, Description: {transaction[3]}")
        else:
            print(f"У пользователя {user_id} нет транзакций.")
    except sqlite3.Error as e:
        print(f"Ошибка при чтении транзакций: {e}")

def change_name_command(user_id, new_name):
    try:
        user_id = int(user_id)
    except ValueError:
        print("Ошибка: Неправильный формат user_id.")
        return
    with db_lock:  # Блокируем доступ к базе для операций записи
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
            connection.commit()
            print(f"Имя пользователя {user_id} успешно изменено на {new_name}")
        except sqlite3.Error as e:
            print(f"Ошибка при изменении имени: {e}")

def mark_used_command(user_id, abonement_id):
    try:
        user_id = int(user_id)
    except ValueError:
        print("Ошибка: Неправильный формат user_id.")
        return
    cursor = connection.cursor()

    # Проверяем, существует ли такой абонемент и какой он
    cursor.execute("""
        SELECT is_training, subscription_name
        FROM user_subscriptions
        WHERE user_id = ? AND subscription_id = ? AND end_date > datetime('now')
    """, (user_id, abonement_id))
    result = cursor.fetchone()

    if not result:
        print(f"У пользователя {user_id} нет активного абонемента с ID {abonement_id}.")
        return

    is_training, subscription_name = result

    success, abonement_name = decrement_visits(user_id, abonement_id)

    if not success:
        print(f"Не удалось отметить использование абонемента {abonement_id} для пользователя {user_id}.")
        return

    # Получаем chat_id пользователя
    cursor.execute("SELECT chat_id FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        chat_id = result[0]
        if abonement_name:  # Если имя абонемента получено
            if is_training:
                bot.send_message(chat_id, f"Использована тренировка {abonement_name}.")
                add_visit_description = f"Использовано разовое посещение {abonement_name}"
            else:
                bot.send_message(chat_id, f"Использовано посещение по абонементу {abonement_name}.")
                add_visit_description = f"Использован абонемент {abonement_name}"
        else:  # Если имя абонемента не получено
            bot.send_message(chat_id, f"Посещение отмечено.")
            add_visit_description = f"Использовано посещение по абонементу {abonement_id}"

        # Добавляем запись о посещении в таблицу transactions
        add_visit(user_id, add_visit_description)

        print(f"Использование абонемента {abonement_id} для пользователя {user_id} отмечено.")
    else:
        print(f"Пользователь с ID {user_id} не найден.")

def show_table_command(table_name):
    try:
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        if rows:
            print(f"Содержимое таблицы {table_name}:")
            for row in rows:
                print(row)
        else:
            print(f"Таблица {table_name} пуста или не существует.")
    except sqlite3.Error as e:
        print(f"Ошибка при чтении таблицы {table_name}: {e}")

def reset_cooldown_command(user_id):
    success = reset_review_cooldown(user_id)
    if success:
        print(f"Успешно сброшен кулдаун отзывов для пользователя {user_id}.")
    else:
        print(f"Ошибка при сбросе кулдауна для пользователя {user_id}.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Пожалуйста, укажите команду. Используйте python cli.py <command> <arguments>.")
        sys.exit(1)

    command = sys.argv[1]

    if command == "add-balance":
        if len(sys.argv) != 5:
            print("Использование: python cli.py add-balance <user_id> <amount> <description>")
        else:
            add_balance_command(sys.argv[2], sys.argv[3], sys.argv[4])

    elif command == "check-balance":
        if len(sys.argv) != 3:
            print("Использование: python cli.py check-balance <user_id>")
        else:
            check_balance_command(sys.argv[2])

    elif command == "add-visit":
        if len(sys.argv) != 4:
            print("Использование: python cli.py add-visit <user_id> <description>")
        else:
            add_visit_command(sys.argv[2], sys.argv[3])

    elif command == "list-users":
        list_users_command()

    elif command == "show-transactions":
        if len(sys.argv) != 3:
            print("Использование: python cli.py show-transactions <user_id>")
        else:
            show_transactions_command(sys.argv[2])

    elif command == "change-name":
        if len(sys.argv) != 4:
            print("Использование: python cli.py change-name <user_id> <new_name>")
        else:
            change_name_command(sys.argv[2], sys.argv[3])

    elif command == "mark-used":
        if len(sys.argv) != 4:
            print("Использование: python cli.py mark-used <user_id> <abonement_id>")
        else:
            mark_used_command(sys.argv[2], sys.argv[3])

    elif command == "show-table":
        if len(sys.argv) != 3:
            print("Использование: python cli.py show-table <table_name>")
        else:
            show_table_command(sys.argv[2])

    elif command == "reset-cooldown":
        if len(sys.argv) != 3:
            print("Использование: python cli.py reset-cooldown <user_id>")
        else:
            reset_cooldown_command(sys.argv[2])

    else:
        print("Неизвестная команда")