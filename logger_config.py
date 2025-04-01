# logger_config.py
import logging

# Настройка логирования транзакций
transactions_logger = logging.getLogger('transactions')
transactions_logger.setLevel(logging.INFO)
transactions_handler = logging.FileHandler('transactions.log', encoding='utf-8')
transactions_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
transactions_handler.setFormatter(transactions_formatter)
transactions_logger.addHandler(transactions_handler)

# Настройка логирования ошибок
errors_logger = logging.getLogger('errors')
errors_logger.setLevel(logging.ERROR)
errors_handler = logging.FileHandler('error_logs.txt', encoding='utf-8')
errors_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
errors_handler.setFormatter(errors_formatter)
errors_logger.addHandler(errors_handler)