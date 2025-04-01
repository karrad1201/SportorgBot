import sqlite3
from threading import Lock
import config
import datetime
import logging
from logger_config import transactions_logger, errors_logger

# Глобальное подключение к базе данных
connection = sqlite3.connect(config.DATABASE_NAME, check_same_thread=False)
connection.execute("PRAGMA journal_mode=WAL;")  # Включаем WAL режим

# Глобальная блокировка для синхронизации операций записи
db_lock = Lock()



def init_db():
    """Инициализация базы данных, создание таблиц."""
    with db_lock:  # Блокируем доступ к базе для операций записи
        cursor = connection.cursor()

        # Создание таблицы users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER,
                name VARCHAR(50),
                balance INTEGER DEFAULT 0,
                phone VARCHAR(20),
                avatar_path TEXT
            )
        """)

        # Создание таблицы transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,  -- 'deposit', 'purchase', 'visit'
                amount INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_id TEXT,
                subscription_name TEXT,
                start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_date DATETIME,
                visits_left INTEGER,
                is_training BOOLEAN DEFAULT FALSE,
             FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        # Создание таблицы reviews
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        review_text TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,  -- Добавлен столбец timestamp
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
        # Создание индекса для быстрого поиска отзывов пользователя
        cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews (user_id)
                """)
        connection.commit()
def add_visit(user_id, description):
    """Добавляет запись о посещении зала пользователем."""
    with db_lock:  # Блокируем доступ к базе для операций записи
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO transactions (user_id, type, amount, description)
                VALUES (?, ?, ?, ?)
            """, (user_id, 'visit', 0, description))  # amount = 0 для посещения
            connection.commit()

            # Логируем посещение
            transactions_logger.info(f"User ID: {user_id}, Type: visit, Description: {description}")

            return True
        except sqlite3.Error as e:
            print(f"Ошибка при добавлении посещения: {e}")
            return False


def update_user_name(user_id, new_name):
    """Обновляет имя пользователя."""
    with db_lock:
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (new_name, user_id))
            connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении имени: {e}")
            return False

def update_user_phone(user_id, new_phone):
    """Обновляет номер телефона пользователя."""
    with db_lock:
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET phone = ? WHERE user_id = ?", (new_phone, user_id))
            connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении номера телефона: {e}")
            return False

def update_user_avatar(user_id, avatar_path):
    """Обновляет путь к аватарке пользователя."""
    with db_lock:
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET avatar_path = ? WHERE user_id = ?", (avatar_path, user_id))
            connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении аватарки: {e}")
            return False

def get_user(user_id):
    """Получает данные пользователя из базы данных."""
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    return user_data

def add_user(user_id, chat_id, name):
    """Добавляет информацию о пользователе в базу данных."""
    with db_lock:  # Блокируем доступ к базе для операций записи
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO users (user_id, chat_id, name) VALUES (?, ?, ?)", (user_id, chat_id, name))
            connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def get_balance(user_id):
    """Получает баланс пользователя из базы данных."""
    cursor = connection.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()
    if balance:
        return balance[0]
    return 0

def check_review_cooldown(user_id):
    """Проверяет, может ли пользователь написать отзыв (кулдаун 24 часа)."""
    with db_lock:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT timestamp FROM reviews
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id,))
            last_review_time = cursor.fetchone()

            if last_review_time:
                last_review_time = datetime.datetime.strptime(last_review_time[0], '%Y-%m-%d %H:%M:%S')
                time_difference = datetime.datetime.now() - last_review_time
                if time_difference < datetime.timedelta(days=1):
                    return False  # Кулдаун еще не прошел
            return True  # Можно писать отзыв
        except sqlite3.Error as e:
            print(f"Ошибка при проверке кулдауна отзыва: {e}")
            return False

def reset_review_cooldown(user_id):
    """Сбрасывает кулдаун на написание отзывов для пользователя."""
    with db_lock:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM reviews WHERE user_id = ?", (user_id,))
            connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при сбросе кулдауна отзыва: {e}")
            return False


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

            # Логируем транзакцию
            transactions_logger.info(f"User ID: {user_id}, Type: {transaction_type}, Amount: {amount}, Description: {description}")

            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении баланса: {e}")
            return False

def get_transactions(user_id):
    """Получает историю транзакций пользователя (только баланс)."""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT timestamp, type, amount, description
            FROM transactions
            WHERE user_id = ? AND (type = 'deposit' OR type = 'purchase')
            ORDER BY timestamp DESC
        """, (user_id,))
        transactions = cursor.fetchall()
        return transactions
    except sqlite3.Error as e:
        print(f"Ошибка при получении истории транзакций: {e}")
        return None

def get_all_users():
    """Получает все данные из таблицы users."""
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM users')
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"Ошибка при чтении базы данных: {e}")
        return None

def get_user_abonements(user_id):
    """Получает список абонементов и разовых посещений пользователя."""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT subscription_id, end_date, visits_left
            FROM user_subscriptions
            WHERE user_id = ? AND end_date > datetime('now')
        """, (user_id,))  # Убрано условие is_training = 0
        abonements = cursor.fetchall()
        return abonements
    except sqlite3.Error as e:
        print(f"Ошибка при получении абонементов: {e}")
        return None


def decrement_visits(user_id, abonement_id):
    """Уменьшает количество посещений для абонемента."""
    print(f"decrement_visits called with user_id: {user_id}, abonement_id: {abonement_id}")
    with db_lock:  # Блокируем доступ к базе для операций записи
        try:
            cursor = connection.cursor()

            # Получаем абонемент
            cursor.execute("""
                SELECT id, visits_left, subscription_name, is_training
                FROM user_subscriptions
                WHERE user_id = ? AND subscription_id = ? AND end_date > datetime('now')
                ORDER BY end_date ASC
            """, (user_id, abonement_id))
            abonements = cursor.fetchall()

            if not abonements:
                print(f"У пользователя {user_id} нет активных абонементов {abonement_id}.")
                return False, None  # Возвращаем False и None, если абонементов нет

            # Берем абонемент
            abonement = abonements[0]
            abonement_db_id = abonement[0]
            visits_left = abonement[1]
            subscription_name = abonement[2]
            is_training = abonement[3]

            # Если visits_left равно None, то абонемент безлимитный.
            if visits_left is None:
                print(f"Абонемент {abonement_id} не имеет ограничений по количеству посещений.")
                return True, subscription_name  # Возвращаем True и название абонемента

            # Если visits_left равно 1, то удаляем абонемент после использования
            if visits_left == 1:
                cursor.execute("""
                    DELETE FROM user_subscriptions
                    WHERE id = ?
                """, (abonement_db_id,))
                connection.commit()
                print(f"Абонемент {abonement_id} использован и удален.")
                return True, subscription_name  # Возвращаем True и название абонемента

            # Если visits_left больше 1, то уменьшаем его
            if visits_left > 1:
                cursor.execute("""
                    UPDATE user_subscriptions
                    SET visits_left = visits_left - 1
                    WHERE id = ?
                """, (abonement_db_id,))
                connection.commit()

                print(f"Использовано посещение по абонементу {abonement_id}. Осталось посещений: {visits_left - 1}")

                return True, subscription_name  # Возвращаем True и название абонемента

            # Если visits_left меньше 1, то это ошибка
            else:
                print(f"Ошибка: У абонемента {abonement_id} не осталось посещений.")
                return False, None  # Возвращаем False и None

        except sqlite3.Error as e:
            print(f"Ошибка при списании посещения: {e}")
            return False, None  # Возвращаем False и None
def get_visits(user_id):
    """Получает историю посещений пользователя."""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT timestamp, description
            FROM transactions
            WHERE user_id = ? AND type = 'visit'
            ORDER BY timestamp DESC
        """, (user_id,))
        visits = cursor.fetchall()
        return visits
    except sqlite3.Error as e:
        print(f"Ошибка при получении истории посещений: {e}")
        return None

def check_balance_CLI(user_id):
    with db_lock:  # Блокируем доступ к базе для операций записи
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))

            balance = cursor.fetchone()
            connection.commit()
            return(f'Баланс пользователя {user_id}: {balance[0]}')

        except sqlite3.Error as e:
            print(f"Ошибка при зачислении средств: {e}")
            return False

def add_review(user_id, review_text):
    """Добавляет отзыв в базу данных."""
    with db_lock:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO reviews (user_id, review_text)
                VALUES (?, ?)
            """, (user_id, review_text))
            connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при добавлении отзыва: {e}")
            return False

def get_random_review():
    """Получает случайный отзыв из базы данных."""
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM reviews ORDER BY RANDOM() LIMIT 1")
        review = cursor.fetchone()
        return review
    except sqlite3.Error as e:
        print(f"Ошибка при получении отзыва: {e}")
        return None

def get_review_by_id(review_id):
    """Получает отзыв по его ID."""
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
        review = cursor.fetchone()
        return review
    except sqlite3.Error as e:
        print(f"Ошибка при получении отзыва: {e}")
        return None

def get_all_reviews():
    """Получает все отзывы из базы данных."""
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM reviews")
        reviews = cursor.fetchall()
        return reviews
    except sqlite3.Error as e:
        print(f"Ошибка при получении отзывов: {e}")
        return None

def check_and_add_user(user_id, chat_id, name):
    """Проверяет, существует ли пользователь, и добавляет, если нет."""
    with db_lock:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO users (user_id, chat_id, name) VALUES (?, ?, ?)", (user_id, chat_id, name))
                connection.commit()
                print(f"Добавлен новый пользователь: ID={user_id}, Chat ID={chat_id}, Name={name}")
            else:
                print(f"Пользователь с ID={user_id} уже существует.")
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при проверке/добавлении пользователя: {e}")
            return False