import json
import threading
from datetime import datetime
import os
import random

DB_FILE = "database.json"
lock = threading.Lock()

# Константы лотереи
MAX_MAIN_TICKETS = 555  # Всего основных билетов
START_BONUS_ID = 555    # Бонусные начинаются с 556 (START_BONUS_ID + 1)

def init_db():
    """Инициализирует JSON-файл с новой структурой."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            initial_data = {
                "users": {},
                # Список занятых номеров из диапазона 1-555
                "taken_main_ids": [],
                # Счетчик для бонусных билетов (начинаем с 555)
                "last_bonus_id": START_BONUS_ID,
                "tickets": {}
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
    """(Без изменений)"""
    user_id_str = str(user_id)
    db = read_db()
    
    if user_id_str not in db["users"]:
        db["users"][user_id_str] = {
            "first_name": first_name,
            "username": username,
            "phone": None,
            "registration_date": datetime.now().isoformat()
        }
        write_db(db)

def get_available_main_count():
    """Возвращает количество оставшихся основных билетов."""
    db = read_db()
    taken = len(db.get("taken_main_ids", []))
    return max(0, MAX_MAIN_TICKETS - taken)

def add_tickets_for_payment(user_id: int, name: str, phone: str, paid_count: int, bonus_count: int) -> list[int]:
    """
    Генерирует билеты:
    paid_count -> выбираются случайно из свободных номеров 1-555
    bonus_count -> выдаются по порядку начиная с 556
    """
    user_id_str = str(user_id)
    db = read_db()

    # Обновляем данные юзера
    if user_id_str in db["users"]:
        db["users"][user_id_str]["phone"] = phone
        db["users"][user_id_str]["name_on_payment"] = name

    # 1. Генерация ОСНОВНЫХ билетов (Случайные 1-555)
    new_ticket_numbers = []
    
    # Определяем, какие номера заняты, а какие свободны
    taken_ids = set(db.get("taken_main_ids", []))
    all_ids = set(range(1, MAX_MAIN_TICKETS + 1))
    available_ids = list(all_ids - taken_ids)

    # Проверяем, хватит ли основных билетов
    if paid_count > len(available_ids):
        # Если билетов не хватает, берем все что есть (или можно выдать ошибку)
        # В данном случае возьмем сколько есть, остальные придется делать бонусными или не выдавать
        print(f"⚠️ ВНИМАНИЕ: Основные билеты заканчиваются! Запрошено {paid_count}, есть {len(available_ids)}")
        tickets_to_take = available_ids # Берем все остатки
        # Остаток перекидываем в бонусные (опционально)
        bonus_count += (paid_count - len(available_ids))
    else:
        # Выбираем случайные уникальные номера
        tickets_to_take = random.sample(available_ids, paid_count)

    # Записываем основные билеты
    for t_id in tickets_to_take:
        new_ticket_numbers.append(t_id)
        db["taken_main_ids"].append(t_id)
        db["tickets"][str(t_id)] = {
            "user_id": user_id,
            "type": "main",
            "purchase_date": datetime.now().isoformat()
        }

    # 2. Генерация БОНУСНЫХ билетов (По порядку 556+)
    last_bonus = db.get("last_bonus_id", START_BONUS_ID)
    
    for i in range(bonus_count):
        current_bonus_id = last_bonus + 1
        new_ticket_numbers.append(current_bonus_id)
        last_bonus = current_bonus_id
        
        db["tickets"][str(current_bonus_id)] = {
            "user_id": user_id,
            "type": "bonus",
            "purchase_date": datetime.now().isoformat()
        }
            # Сохраняем новый счетчик бонусных
    db["last_bonus_id"] = last_bonus
    
    write_db(db)
    print(f"✅ Пользователь {user_id} получил билеты: {new_ticket_numbers}")
    return new_ticket_numbers

init_db()
