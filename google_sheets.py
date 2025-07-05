import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os


def append_to_sheet(name: str, phone: str, ticket_count: int) -> list[str]:
    print(f"📥 append_to_sheet вызван: {name}, {phone}, {ticket_count}")

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        os.path.join(os.path.dirname(__file__), "credentials.json"),
        scope
    )
    client = gspread.authorize(creds)

    sheet = client.open("оплата билетов").sheet1

    try:
        meta_sheet = client.open("оплата билетов").worksheet("meta")
    except:
        meta_sheet = client.open("оплата билетов").add_worksheet(title="meta", rows="1", cols="1")
        meta_sheet.update("A1", "0")

    # Чтение последнего номера
    last_number_cell = meta_sheet.acell("A1").value
    last_number = int(last_number_cell) if last_number_cell.isdigit() else 0

    # Генерация новых номеров
    new_numbers = [str(last_number + i + 1) for i in range(ticket_count)]

    # Обновление meta
    meta_sheet.update("A1", str(last_number + ticket_count))

    # Запись данных
    sheet.append_row([
        name,
        phone,
        ticket_count,
        ", ".join(new_numbers)
    ])

    print(f"✅ Добавлено: {name}, {phone}, билеты: {new_numbers}")
    return new_numbers

# def append_to_sheet(name: str, phone: str, ticket_count: int) -> list[str]:
#     print(f"📥 append_to_sheet вызван: {name}, {phone}, {ticket_count}")
#     scope = [
#         "https://spreadsheets.google.com/feeds",
#         "https://www.googleapis.com/auth/drive"
#     ]
#     creds = ServiceAccountCredentials.from_json_keyfile_name(
#         os.path.join(os.path.dirname(__file__), "credentials.json"),
#         scope
#     )
#     client = gspread.authorize(creds)
#
#     sheet = client.open("оплата билетов").sheet1
#
#     existing_data = sheet.get_all_records()
#     last_number = 0
#
#     for row in existing_data:
#         numbers_str = row.get("Номера", "")
#         if numbers_str:
#             numbers = [int(n.strip()) for n in numbers_str.split(",") if n.strip().isdigit()]
#             if numbers:
#                 last_number = max(last_number, max(numbers))
#
#     new_numbers = [str(last_number + i + 1) for i in range(ticket_count)]
#
#     print(f"📋 Запись в таблицу: {name}, {phone}, {ticket_count}, номера: {new_numbers}")
#
#     sheet.append_row([
#         name,
#         phone,
#         ticket_count,
#         ", ".join(new_numbers)
#     ])
#
#     print(f"✅ Добавлено в таблицу: {name}, {phone}, билеты: {new_numbers}")
#     return new_numbers
#
# if __name__ == "__main__":
#     tickets = append_to_sheet("Тестовый", "+79991234567", 3)
#     print("🎟️ Получены номера билетов:", tickets)
