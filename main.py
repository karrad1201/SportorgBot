import config, handlers, database, utils
import telebot
import time
from sqlite3 import OperationalError
import signal
import sys

# Флаг для контроля работы бота
running = True

def signal_handler(sig, frame):
    """Обработчик сигналов для корректного завершения работы."""
    global running
    print("\nБот останавливается...")
    running = False
    sys.exit(0)  # Завершаем программу

def start_bot():
    """Запуск бота с возможностью перезапуска при ошибке."""
    global running
    restarts = 0
    MAX_RESTARTS = 5  # Максимальное количество перезапусков

    while running and restarts < MAX_RESTARTS:
        try:
            print("Запуск бота...")
            utils.bot.infinity_polling()  # Запуск бесконечного опроса
        except OperationalError as e:
            if "database is locked" in str(e):
                restarts += 1
                print(f"Ошибка: database is locked. Перезапуск бота ({restarts}/{MAX_RESTARTS})...")
                time.sleep(5)  # Пауза перед перезапуском
            else:
                print(f"Критическая ошибка: {e}")
                break  # Выход из цикла при других ошибках
        except KeyboardInterrupt:
            print("\nБот остановлен пользователем.")
            break  # Выход из цикла при ручной остановке
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")
            break  # Выход из цикла при других ошибках
    else:
        if restarts >= MAX_RESTARTS:
            print("Достигнуто максимальное количество перезапусков. Бот завершает работу.")

def main():
    """Инициализация и запуск бота."""
    # Регистрируем обработчик сигналов (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    database.init_db()  # Инициализация базы данных
    start_bot()  # Запуск бота с возможностью перезапуска

if __name__ == "__main__":
    main()