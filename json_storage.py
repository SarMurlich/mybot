# json_storage.py
import json
import threading
from datetime import datetime
import os

DB_FILE = "database.json"
lock = threading.Lock()

def init_db():
    """Инициализирует JSON-файл, если он не существует."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            # Создаем базовую структуру
            initial_data = {
                "users": {},
                "last_ticket_id": 0,
                "tickets": {}
            }
            json.dump(initial_data, f, indent=4)

def read_db():
    """Читает данные из JSON-файла."""
    with lock:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def write_db(data):
    """Записывает данные в JSON-файл."""
    with lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

def add_user_if_not_exists(user_id: int, first_name: str, username: str):
    """Добавляет пользователя, если его еще нет в базе."""
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
        print(f"Пользователь {first_name} (ID: {user_id}) добавлен в базу.")
    else:
        print(f"Пользователь {first_name} (ID: {user_id}) уже существует.")

def add_tickets_for_payment(user_id: int, name: str, phone: str, count: int) -> list[int]:
    """
    Добавляет билеты после успешной оплаты.
    Обновляет телефон пользователя.
    Возвращает список номеров новых билетов.
    """
    user_id_str = str(user_id)
    db = read_db()

    # Обновляем телефон пользователя
    if user_id_str in db["users"]:
        db["users"][user_id_str]["phone"] = phone
        db["users"][user_id_str]["name_on_payment"] = name # Сохраняем имя из анкеты

    last_ticket_id = db.get("last_ticket_id", 0)
    new_ticket_numbers = []

    for i in range(count):
        current_ticket_id = last_ticket_id + i + 1
        new_ticket_numbers.append(current_ticket_id)
        
        db["tickets"][str(current_ticket_id)] = {
            "user_id": user_id,
            "purchase_date": datetime.now().isoformat()
        }
    
    db["last_ticket_id"] = last_ticket_id + count
    
    write_db(db)
    print(f"✅ Добавлены билеты {new_ticket_numbers} для пользователя {name} (ID: {user_id})")
    return new_ticket_numbers

# Инициализируем базу данных при запуске модуля
init_db()
