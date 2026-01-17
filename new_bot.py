# new_bot.py
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, html, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, g
from yookassa import Configuration, Payment
import uuid
import threading
from waitress import serve
import csv
import os
from aiogram.filters import Command
from aiogram.types import FSInputFile
import json
# ... остальные импорты ...

# --- НАШИ МОДУЛИ ---
from key import my_key
from json_storage import add_user_if_not_exists, add_tickets_for_payment

# --- КОНФИГУРАЦИЯ ---
Configuration.account_id = "1085561"
Configuration.secret_key = "live_L2jrGwfcPBjEmTk_tJlzN7PaD36dPljqctXPrw0TVbU"
TOKEN = my_key
TICKET_PRICE = 1

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
app = Flask(__name__)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

user_start_times = {}
BOT_START_TIME = datetime.now()

# --- FSM СТЕЙТЫ ---
class Form(StatesGroup):
    name = State()
    phone = State()
    ticket_count = State()

# --- ХЕНДЛЕРЫ AIOGRAM ---

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    args = message.text.split(maxsplit=1)
    arg = args[1] if len(args) > 1 else None
    print(f"/start received with arg: {arg}")

    # --- ИЗМЕНЕННЫЙ БЛОК ---
    if arg == "payment_done":
        # Отправляем максимально короткое и полезное сообщение
        await message.answer(
            "✅ Спасибо за участие! ✅ "
        )
        return

    # Добавляем пользователя в нашу JSON-базу
    add_user_if_not_exists(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username or ""
    )

    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔍 Узнать правила участия', callback_data='show_rules')]
    ])

    photo_file_id = "AgACAgIAAxkBAAIogWlrxT1LdVodHaGeZWTBH96faVr0AALTDWsb5kVgS0isW8FIVrKOAQADAgADeQADOAQ"

    caption_text = (
        f"<b><i>Привет! {html.bold(message.from_user.first_name)}, это бот-помощник команды NPAuto</i></b> 👋 \n\n"
        "Мы запускаем новогодний <b><i>промо-\nрозыгрыш,</i></b> присоединяйся!!!🚗 🎁 \n\n"
        "Главный приз <b><i>PORSCHE Cayenne S</i></b> 🤩\n\n"
        "<b><i>Будут и другие призы</i></b>👇🏻\n\n"
        "💫 <b><i>1 из покупателей наших наклеек получит</i></b>\n"
        "- Умные часы Apple Watch SE\n"
        "💫 <b><i>2 покупателя - </i></b>Безпроводные наушники\n"
        "Beats Studio Pro\n"
        "💫 <b><i>10 покупателей - </i></b>наклейку с правом\n"
        "участия в следующем промо-розыгрыше\n\n"
        "👇🏻<b><i>Но ЭТО еще НЕ ВСЁ!!!</i></b>\n\n"
        "Среди тех, кто примет участие в нашей\n"
        "движухе <b><i>в первый час,</i></b>мы выберем одного\n"
        "обладателя <b><i>Игровой приставки Sony</i></b>\n"
        "<b><i>PlayStation 5</i></b>🤩🍀\n\n"
        "ЖМИ👇🏻\n\n"

    )
    await message.answer_photo(
        photo=photo_file_id,
        caption=caption_text,
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("export"))
async def export_csv(message: types.Message):
    # ❗️ ЗАМЕНИ НА СВОЙ ID (иначе бот тебе не ответит)
    ADMIN_ID = 494097833
    
    if message.from_user.id != ADMIN_ID:
        return

    json_file = "database.json"
    csv_file = "raffle_data.csv"

    # Проверяем, существует ли база
    if not os.path.exists(json_file):
        await message.answer("❌ База данных не найдена.")
        return

    try:
        # 1. Читаем JSON
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        tickets = data.get("tickets", {})
        
        # 2. Создаем CSV (encoding='utf-8-sig' нужен, чтобы Excel правильно читал русский язык)
        with open(csv_file, "w", newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';') # Используем точку с запятой для Excel
            
            # Заголовки столбцов
            headers = ["Номер билета", "Тип билета", "Имя (Анкета)", "Телефон", "ID Telegram", "Дата покупки"]
            writer.writerow(headers)

            # Записываем данные построчно
            # Сортируем билеты по номеру (превращаем ключи в int для правильной сортировки)
            sorted_ids = sorted(tickets.keys(), key=lambda x: int(x))
            
            for t_id in sorted_ids:
                ticket_info = tickets[t_id]
                
                # Собираем строку
                row = [
                    t_id,                                      # Номер
                    ticket_info.get("type", "unknown"),        # Тип (main/bonus)
                    ticket_info.get("owner_name", "-"),        # Имя
                    ticket_info.get("owner_phone", "-"),       # Телефон
                    str(ticket_info.get("user_id", "-")),      # ID
                    ticket_info.get("purchase_date", "-")      # Дата
                ]
                writer.writerow(row)

        # 3. Отправляем файл
        await message.answer_document(
            FSInputFile(csv_file),
            caption=f"📊 Выгрузка билетов на {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                    f"Всего билетов: {len(tickets)}"
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка при экспорте: {e}")
        logging.error("Export error:", exc_info=True)

# ... (остальные хендлеры до process_ticket_count остаются без изменений) ...

@dp.callback_query(F.data == "show_rules")
async def send_rules(callback: types.CallbackQuery):
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/+r2nV1ThTyZVlNzli")],
        [InlineKeyboardButton(text="✅ Участвовать", callback_data="participate")]
    ])
    await callback.answer()

    # --- ИСПРАВЛЕННЫЙ ТЕКСТ ---
    caption_text = (
        "<b><i>Разыгрывать автомобиль Мы будем\n"
        "среди покупателей наших наклеек 😁\n"
        "Каждому из которых будет присвоен</i></b>\n"
        "персональный код1️⃣2️⃣3️⃣\n\n"
        "<b><i>Условия участия просты:📋</i></b>\n\n"
        "1. Быть подписанным на наш канал\n"
        "<b><i>NPAuto</i></b>, чтобы быть в курсе событий.\n\n"
        f"2. Купить наклейку стоимостью <b>{TICKET_PRICE} руб</b>\n"
        "и получить свой персональный код. 🔢\n\n"
        # Закрываем тег <i> в конце строки
        f"<i>Всего в продаже 555 наклеек, купив которые, "
        "Вы сможете участвовать в акции.</i> 😎\n\n"
        "<b>Обращаем ваше внимание:</b> промо-розыгрыш\n"
        "проводится без фиксированной даты\n"
        "окончания и может завершится в любой\n"
        "момент🤚🏻⛔️\n\n"
        "Как получить свой приз, Мы расскажем\n"
        "в нашем ТГ канале!🎁"
    )

    await callback.message.answer(
        #video="BAACAgIAAxkBAAMFaF_JunR6fKD6Dq6lHtOJflr8hsAAAptwAAI3qwABS5CXnF6ECpdsNgQ",
        caption_text,
        reply_markup=inline_kb,
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data == "participate")
async def handle_participation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    channel_id = "@npauto1"

    try:
        member = await callback.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Заполнить анкету", callback_data="fill_form")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="show_rules")]
            ])
            await callback.message.answer(
                "✅ <b>Подписка подтверждена!</b>\n"
                "Переодически я буду ее проверять, так что\n"
                "оставайся на канале😉\n\n"
                "Осталось заполнить анкету,\n"
                "приобрести наклейку и ты в деле⬇️",
                reply_markup=inline_kb
            )
        else:
            raise Exception("Not subscribed")
    except Exception as e:
        print(f"🔴 Ошибка проверки подписки: {e}")
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/+r2nV1ThTyZVlNzli")],
            [InlineKeyboardButton(text="🔁 Проверить подписку", callback_data="check_subscription")]
        ])
        await callback.message.answer_photo(
            photo="AgACAgIAAxkBAAMDaF_JVWA10_CyZiTuXWzThJzp2xoAAnnzMRtu2fhKSg8xW2NZvC0BAAMCAAN4AAM2BA",
            caption="<b>❌ К сожалению, не вижу тебя в списке</b>\n"
                    "<b>подписчиков</b>🥺/n/n"
                    "Чтобы принять участие в промо-розыгрыше,\n"
                    "подпишись на канал NPAuto и нажми⬇️\n"
                    "'Проверить подписку'",
            reply_markup=inline_kb,
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "check_subscription")
async def check_subscription(callback: types.CallbackQuery):
    await handle_participation(callback)

@dp.callback_query(F.data == "fill_form")
async def start_form(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Для участия <b>напиши свое ИМЯ</b>\n👇")
    await state.set_state(Form.name)

@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("❗ Ты не ввел имя😢")
        return
    await state.update_data(name=name)
    await message.answer("📞 <b>И номер телефона</b>\n\nв формате: +79991234567\n\n"
                         "Не переживай, беспокоить спамом не будем😉")
    await state.set_state(Form.phone)

@dp.message(Form.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not (phone.startswith("+7") and len(phone) == 12 and phone[2:].isdigit()):
        await message.answer("❌ Неверный формат номера. Попробуй ещё раз😉")
        return

    await state.update_data(phone=phone)
    user_start_times[message.from_user.id] = datetime.now()

    await message.answer(f"<b>Напиши сколько наклеек ТЫ хочешь приобрести?😊</b>\n\n"
                         f"Стоимость 1-ой наклейки - <b>{TICKET_PRICE} руб</b>💸\n\n"
                         f"Чем больше у тебя наклеек, тем больше\n"
                         f"шансов выиграть Porsche Cayenne S!\n"
                        # f"В связи с этим Мы подготовили\n"
                        # f"спец. предложение: <b><i>купив 3 наклейки,\n"
                        # f"ты получаешь в подарок\n"
                        # f"1 дополнительный персональный код</i></b>🤩\n\n"
                        # f"<i>*спец. предложение действует 17.07.2025</i>\n"
                        #f"<i>с 7:00 до 21:00</i>\n"
                        )
    await state.set_state(Form.ticket_count)


@dp.message(Form.ticket_count)
async def process_ticket_count(message: types.Message, state: FSMContext):
    try:
        # 1. Проверяем, что ввели число
        count = int(message.text.strip())
        if count <= 0:
            raise ValueError("Количество должно быть положительным")
    except (ValueError, TypeError):
        await message.answer("❗️ Введите корректное число наклеек (цифрами).")
        return

    # 2. Рассчитываем бонусы и цену
    # Акция: 1 бонусный код за каждые 3 купленные наклейки
    bonus_codes = 0 #count // 3  
    total_codes = count #+ bonus_codes
    
    # Цена считается только за КУПЛЕННЫЕ
    price = TICKET_PRICE * count

    # Сохраняем в состояние (хотя для платежа данные берем сразу)
    await state.update_data(
        ticket_count=count,
        price=price
    )

    user_data = await state.get_data()
    name = user_data.get("name")
    phone = user_data.get("phone")

    if not name or not phone:
        await message.answer("❗️ Не удалось получить данные анкеты. Нажмите /start для перезапуска.")
        await state.clear()
        return

    # 3. Формируем текст сообщения для пользователя
    summary = (
        f"✅ Количество наклеек к покупке: <b>{count}</b>\n"
        f"💰 Стоимость: <b>{price} руб</b>\n"
    )

    if bonus_codes > 0:
        summary += f"🎁 <b>Бонус по акции: +{bonus_codes} доп. кодов!</b>\n"

    summary += (
        f"🔢 Итого вы получите персональных кодов: <b>{total_codes}</b>\n\n"
        f"<i>(Из них {count} основных участвуют в розыгрыше Porsche Cayenne S,\n"
        f"а бонусные коды увеличивают шансы на другие призы!)</i>\n\n" # Текст можно поправить под ваши правила
        f"Количество наклеек забронировано для тебя на 5 минут👌\n\n"
        f"‼️<b><i>ВНИМАНИЕ</i></b>‼️ Убедительная просьба "
        f"<b><i>оплачивать только по СБП и сделать</i></b> "
        f"<b><i>скриншот чека!!!</i></b>\n\n"
        f"После оплаты придет сообщение с твоими "
        f"персональными кодами участника🥳\n\n"
        f"Если возникли сложности, напиши нам "
        f"в телеграмме по номеру +79995295511\n\n"
        f"<b><i>Если все понятно, жми 'перейти к оплате'</i></b>\n"
        f"⬇️"
    )

    # 4. Создаем платеж в ЮКассе
    try:
        payment_price_str = f"{price:.2f}"
        bot_info = await bot.get_me()

        payment_data = {
            "amount": {"value": payment_price_str, "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{bot_info.username}?start=payment_done"
            },
            "capture": True,
            "description": f"Покупка {count} накл. (+{bonus_codes} бонус). User: {message.from_user.id}",
            "receipt": {
                "customer": {"phone": phone},
                "items": [{
                    "description": f"Фирменная наклейка NPAuto ({count} шт.)",
                    "quantity": str(count), # В чеке только платные
                    "amount": {"value": f"{TICKET_PRICE:.2f}", "currency": "RUB"},
                    "vat_code": 1,
                    "payment_mode": "full_prepayment",
                    "payment_subject": "commodity"
                }]
            },
            "metadata": {
                "tg_id": str(message.from_user.id),
                "name": name,
                "phone": phone,
                # ВАЖНО: Передаем раздельно, чтобы база данных знала, как генерировать номера
                "paid_count": str(count),      # Эти пойдут в случайные 1-555
                "bonus_count": str(bonus_codes) # Эти пойдут последовательно 556+
            }
        }

        payment = Payment.create(payment_data, uuid.uuid4())
        confirmation_url = payment.confirmation.confirmation_url

    except Exception as e:
        await message.answer("❌ Ошибка при создании платежа. Пожалуйста, попробуйте позже.")
        logging.error("Ошибка создания платежа YooKassa:", exc_info=True)
        await state.clear()
        return

    # 5. Отправляем кнопку оплаты
    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=confirmation_url)]
    ])
    await message.answer(summary, reply_markup=pay_kb, parse_mode=ParseMode.HTML)
    await state.clear()


async def send_success_message(user_id: int, ticket_numbers: list[str]):
    """Асинхронно отправляет сообщение об успехе вместе с видео."""    
    # ВАЖНО: количество купленных наклеек может не совпадать с количеством кодов.
    # Чтобы правильно уменьшить остаток, нужно получить его из базы.
    # Но для простоты пока оставим вычитание по количеству кодов.
    # Если у вас акция "2+1", то вычитаться будет 3, а не 2. Это нужно иметь в виду.    
    # Вставьте сюда file_id вашего видео
    #video_file_id = "BAACAgIAAxkBAAICe2hqf4KRNqxJ4rdSJcZpk0wZaA_SAAIofwAChJZZSxqaBQeuOPLfNgQ" # ЗАМЕНИТЕ НА СВОЙ FILE_ID

    # Формируем текст сообщения (caption для видео)
    caption_text = (
        f"🎉 <b>Оплата подтверждена! Поздравляем,</b>\n"
        f"<b>ты участвуешь в промо-розыгрыше,</b>\n"
        f"<b>удачи!🍀</b>\n\n"
        f"Ты получил(а) <b>{len(ticket_numbers)}</b> персональных кода(ов)\n"
        f"Твой код(ы): <b>{', '.join(ticket_numbers)}</b>\n\n"
        f"Сохрани свой(и) код(ы)!\n"
        f"Именно <b>по коду мы определим</b>\n"
        f"<b>обладателя Porsche Cayenne S</b>\n"
        f"<b>и других призов 💫</b>\n\n"
        f"Как и где можно получить свою\n"
        f"наклейку, мы расскажем\n"
        f"в нашем ТГ канале 😎\n\n"
        f"Будь на связи 📲"
    )

    try:
        # Используем bot.send_video вместо bot.send_message
        await bot.send_video(
            chat_id=user_id,
            video=video_file_id,
            caption=caption_text,
            parse_mode=ParseMode.HTML # Убедимся, что HTML-теги обработаются
        )
        print(f"Сообщение об успехе с видео отправлено пользователю {user_id}. Номера: {ticket_numbers}")
    except Exception as e:
        # Если отправка видео не удалась (например, неверный file_id),
        # отправим хотя бы текстовое сообщение.
        logging.error(f"Не удалось отправить видео пользователю {user_id}: {e}. Отправляю текст.")
        await bot.send_message(
            chat_id=user_id,
            text=caption_text,
            parse_mode=ParseMode.HTML
        )

# ... (остальной код вебхука без изменений)

@app.route('/yookassa/webhook', methods=['POST'])
def yookassa_webhook():
    print("🔔 Вебхук получен")
    try:
        data = request.json
        if data.get('event') == 'payment.succeeded':
            metadata = data['object']['metadata']
            
            user_id = int(metadata['tg_id'])
            name = metadata['name']
            phone = metadata['phone']
            
            # Читаем новые поля
            paid_count = int(metadata.get('paid_count', 0))
            bonus_count = int(metadata.get('bonus_count', 0))

            print(f"💰 Оплата: {name}, куплено: {paid_count}, бонус: {bonus_count}")

            # Вызываем НОВУЮ функцию добавления билетов
            ticket_numbers = add_tickets_for_payment(
                user_id, name, phone, 
                paid_count=paid_count, 
                bonus_count=bonus_count
            )
            
            # Сортируем билеты для красоты (чтобы сначала шли мелкие номера)
            ticket_numbers.sort()
            ticket_numbers_str = [str(num) for num in ticket_numbers]

            main_loop = g.get('main_loop')
            if main_loop and main_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    send_success_message(user_id, ticket_numbers_str),
                    main_loop
                )

    except Exception as e:
        logging.error(f"Webhook error: {e}", exc_info=True)

    return '', 200


# --- ЗАПУСК ---

def start_flask(loop):
    @app.before_request
    def before_request():
        g.main_loop = loop
    serve(app, host="0.0.0.0", port=5000)

async def main():
    loop = asyncio.get_running_loop()
    flask_thread = threading.Thread(target=start_flask, args=(loop,))
    flask_thread.daemon = True
    flask_thread.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")


