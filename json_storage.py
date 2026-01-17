import json
import threading
from datetime import datetime
import os
import random

DB_FILE = "database.json"
lock = threading.Lock()

# Константы лотереи
MAX_MAIN_TICKETS = 555  # Всего основных билетов (1-555)
START_BONUS_ID = 555    # Бонусные начинаются с 556

def init_db():
    """Инициализирует JSON-файл с новой структурой."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            initial_data = {
                "users": {},          # Здесь храним инфо о юзерах
                "taken_main_ids": [], # Список занятых номеров 1-555
                "last_bonus_id": START_BONUS_ID, # Последний выданный бонусный
                "tickets": {}         # Информация о каждом билете
            }
            json.dump(initial_data, f, indent=4)

def read_db():
    with lock:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def write_db(data):
    with lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

def add_user_if_not_exists(user_id: int, first_name: str, username: str):
    """Добавляет пользователя при нажатии /start"""
    user_id_str = str(user_id)
    db = read_db()
    
    if user_id_str not in db["users"]:
        db["users"][user_id_str] = {
            "tg_first_name": first_name, # Имя из Телеграма
            "tg_username": username,     # Юзернейм
            "form_name": None,           # Имя из анкеты (заполнится при оплате)
            "phone": None,               # Телефон (заполнится при оплате)
            "registration_date": datetime.now().isoformat(),
            "history": []                # История полученных билетов
        }
        write_db(db)
        print(f"👤 Новый пользователь: {first_name} (ID: {user_id})")

def get_available_main_count():
    """Возвращает количество оставшихся основных билетов."""
    db = read_db()
    taken = len(db.get("taken_main_ids", []))
    return max(0, MAX_MAIN_TICKETS - taken)

def add_tickets_for_payment(user_id: int, name: str, phone: str, paid_count: int, bonus_count: int) -> list[int]:
    """
    1. Сохраняет имя и телефон пользователя.
    2. Генерирует билеты (paid_count случайных, bonus_count последовательных).
    """
    user_id_str = str(user_id)
    db = read_db()

    # --- БЛОК СОХРАНЕНИЯ ДАННЫХ ПОЛЬЗОВАТЕЛЯ ---
    # Если пользователя вдруг нет (не жал start), создаем заготовку
    if user_id_str not in db["users"]:
        db["users"][user_id_str] = {
            "tg_first_name": "Unknown",
            "tg_username": "Unknown",
            "registration_date": datetime.now().isoformat(),
            "history": []
        }
    
    # Обновляем данные из анкеты (Имя и Телефон)
    db["users"][user_id_str]["form_name"] = name
    db["users"][user_id_str]["phone"] = phone
    # -------------------------------------------

    # 1. Генерация ОСНОВНЫХ билетов (Случайные 1-555)
    new_ticket_numbers = []
    
    taken_ids = set(db.get("taken_main_ids", []))
    all_ids = set(range(1, MAX_MAIN_TICKETS + 1))
    available_ids = list(all_ids - taken_ids)

    # Если просят больше, чем есть основных -> берем все остатки
    count_to_take = min(paid_count, len(available_ids))
    
    # Если основных не хватило, остаток переносим в бонусные (чтобы не терять билеты)
    overflow = paid_count - count_to_take
    if overflow > 0:
        bonus_count += overflow
        print(f"⚠️ Основные билеты кончились! {overflow} переведены в бонусные.")

    # Выбираем случайные
    tickets_to_take = random.sample(available_ids, count_to_take)

    for t_id in tickets_to_take:
        new_ticket_numbers.append(t_id)
        db["taken_main_ids"].append(t_id)
        
        # Запись билета
        db["tickets"][str(t_id)] = {
            "user_id": user_id,
            "type": "main",  # Тип: основной
            "owner_name": name,
            "owner_phone": phone,
            "purchase_date": datetime.now().isoformat()
        }

    # 2. Генерация БОНУСНЫХ билетов (По порядку 556+)
    last_bonus = db.get("last_bonus_id", START_BONUS_ID)
    
    for i in range(bonus_count):
        current_bonus_id = last_bonus + 1
        new_ticket_numbers.append(current_bonus_id)
        last_bonus = current_bonus_id
        
        # Запись билета
        db["tickets"][str(current_bonus_id)] = {
            "user_id": user_id,
            "type": "bonus", # Тип: бонусный
            "owner_name": name,
            "owner_phone": phone,
            "purchase_date": datetime.now().isoformat()
        }

    # Обновляем счетчик
    db["last_bonus_id"] = last_bonus
    
    # Сохраняем историю билетов в объект пользователя (для удобства)
    if "history" not in db["users"][user_id_str]:
        db["users"][user_id_str]["history"] = []
    db["users"][user_id_str]["history"].extend(new_ticket_numbers)
    
    write_db(db)
    print(f"✅ Данные сохранены: {name}, {phone}. Билеты: {new_ticket_numbers}")
    return new_ticket_numbers

# Инициализация при импорте
init_db()
