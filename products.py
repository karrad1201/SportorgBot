# products.py
ABONEMENTS = {
    "abonement_unlimited_30": {
        "name": "♾️ Безлимитный (30 дней)",
        "price": 2200,
        "duration": 30,
        "abonement_id": "abonement_unlimited_30"
    },
    "abonement_unlimited_90": {
        "name": "♾️ Безлимитный на 90 дней",
        "price": 5600,
        "duration": 90,
        "abonement_id": "abonement_unlimited_90"
    },
    "abonement_student": {
        "name": "🏫 Для школьников и студентов (до 17:00)",
        "price": 1800,
        "duration": 30, # Длительность в днях
        "restriction": "Посещение до 17:00",
        "abonement_id": "abonement_student"
    },
    "abonement_12_visits": {
        "name": "💨 На 12 дней (действует 30 дней)",
        "price": 2000,
        "visits": 12, # Количество посещений
        "duration": 30,
        "abonement_id": "abonement_12_visits"
    },
    "abonement_trainer_10": {
        "name": "🏋️‍♂️ С тренером на 10 занятий (действует 30 дней)",
        "price": 4500,
        "visits": 10, # Количество занятий
        "duration": 30, # Длительность в днях
        "trainer": "Обычный",
        "abonement_id": "abonement_trainer_10"
    },
    "abonement_trainer_10_senior": {
        "name": "🏋️‍♂️ На 10 занятий со старшим тренером (действует 30 дней)",
        "price": 5000,
        "visits": 10, # Количество занятий
        "duration": 30, # Длительность в днях
        "trainer": "Старший",
        "abonement_id": "abonement_trainer_10_senior"
    },
    "abonement_trainer_20": {
        "name": "🏋️‍♂️ С тренером на 20 занятий (действует 45 дней)",
        "price": 8500,
        "visits": 20, # Количество занятий
        "duration": 45, # Длительность в днях
        "trainer": "Обычный",
        "abonement_id": "abonement_trainer_20"
    },
     "abonement_trainer_paired_10": {
        "name": "🏋️‍♂️ Парные занятия с тренером на 10 занятий (действует 30 дней)",
        "price": 8500,
        "visits": 10, # Количество занятий
        "duration": 30, # Длительность в днях
        "trainer": "Обычный",
        "paired": True,
        "abonement_id": "abonement_trainer_paired_10"
    },
}


TRAININGS = {
    "training_single": {
        "name": "💪 Разовое посещение",
        "price": 250,
        "visits": 1,
        "training_id": "training_single"
    },
    "abonement_trainer_single": {
        "name": "🏋️‍♀️ Разовое занятие с тренером",
        "price": 550,
        "visits": 1,
        "training_id": "training_trainer_single"
    },
}
TRAINERS = {
    "trainer1": {
        "fio": "Иванов Иван Иванович",
        "name": "Тренер 1",
        "description": "Мастер спорта по бодибилдингу. Опыт работы 5 лет.",
        "photo": "photo/trainer1.jpg",
        "vk_link": "https://vk.com/trainer1",
        "telegram_link": "https://t.me/trainer1"
    },
    "trainer2": {
        "fio": "Петров Петр Петрович",
        "name": "Тренер 2",
        "description": "Кандидат в мастера спорта по пауэрлифтингу. Опыт работы 3 года.",
        "photo": "photo/trainer2.jpg",
        "vk_link": "https://vk.com/trainer2",
        "telegram_link": "https://t.me/trainer2"
    },
    "trainer3": {
        "fio": "Сидоров Сидор Сидорович",
        "name": "Тренер 3",
        "description": "Инструктор групповых программ. Опыт работы 7 лет.",
        "photo": "photo/trainer3.jpg",
        "vk_link": "https://vk.com/trainer3",
        "telegram_link": "https://t.me/trainer3"
    },
    "trainer4": {
        "fio": "Смирнов Алексей Дмитриевич",
        "name": "Тренер 4",
        "description": "Персональный тренер по фитнесу. Опыт работы 2 года.",
        "photo": "photo/trainer4.jpg",
        "vk_link": "https://vk.com/trainer4",
        "telegram_link": "https://t.me/trainer4"
    },
    "trainer5": {
        "fio": "Кузнецова Анна Сергеевна",
        "name": "Тренер 5",
        "description": "Тренер по йоге и пилатесу. Опыт работы 4 года.",
        "photo": "photo/trainer5.jpg",
        "vk_link": "https://vk.com/trainer5",
        "telegram_link": "https://t.me/trainer5"
    }
}