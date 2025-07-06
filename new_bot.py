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

available_tickets = 888
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

    photo_file_id = "AgACAgIAAxkBAAICx2hqkPpqYTYgLjcb4x6Nniyc7nuTAALb9TEbhJZZSzy800ilJfUOAQADAgADeQADNgQ"

    caption_text = (
        f"<b><i>Привет! {html.bold(message.from_user.first_name)}, это бот-помощник команды NPAuto</i></b> 👋 \n\n"
        "Совсем скоро <b><i>МЫ проведем</i></b> свой первый масштабный <b>промо-розыгрыш!</b> 🚗 🎁 \n\n"
        "Победитель станет обладателем легендарной <b><i>Audi A4</i></b>\n\n"
        "<b><i>Но это еще не все!!!</i></b> Мы подготовили для\n"
        " вас еще несколько приятных призов:\n\n"
        "💫 <b><i>3 покупателя наших фирменных\n"
        "наклеек получат - </i></b>Наушники\n"
        "Apple AirPods 4\n"
        "💫 <b><i>2 покупателя получат - </i></b>Часы\n"
        "Apple Watch SE 2\n"
        "💫 <b><i>2 покупателя получат - </i></b>Умную колонку\n"
        "Алиса мини\n"
        "💫 <b><i>1 покупатель получит - </i></b>Прогулку на\n"
        "катере по центру Питера\n"
        "💫 <b><i>10 покупателей получит - </i></b>наклейку,\n"
        "которая дает право участвовать в нашем\n"
        "следующем мероприятие\n\n"
        "Присоединяйся 🍀"
    )
    await message.answer_photo(
        photo=photo_file_id,
        caption=caption_text,
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.HTML
    )

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
        "<b><i>Разыгрывать автомобиль мы будем\n"
        "среди покупателей наших наклеек 😁\n"
        "Каждому из которых будет присвоен</i></b>\n"
        "персональный код1️⃣2️⃣3️⃣\n\n"
        "<b><i>Условия участия просты:📋</i></b>\n\n"
        "1. Быть подписанным на наш канал\n"
        "<b><i>NPAuto</i></b>, чтоб быть в курсе событий.\n\n"
        f"2. Купить наклейку стоимостью <b>{TICKET_PRICE} руб</b>\n"
        "и получить свой персональный код. 🔢\n\n"
        # Закрываем тег <i> в конце строки
        f"<i>Всего в продаже {available_tickets} наклеек, купив которые, "
        "вы сможете участвовать в акции.</i> 😎\n\n"
        "<b>*Промо-розыгрыш проводится до 31.07.2025.</b>\n\n"
        "Как получить свой приз, мы расскажем в нашем ТГ канале!"
    )

    await callback.message.answer_video(
        video="BAACAgIAAxkBAAMFaF_JunR6fKD6Dq6lHtOJflr8hsAAAptwAAI3qwABS5CXnF6ECpdsNgQ",
        caption=caption_text, # Используем исправленный текст
        reply_markup=inline_kb,
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data == "participate")
async def handle_participation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    channel_id = "@npcoolauto"

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
                    "подпишись на канал NPAuto и нажми\n"
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
                         f"Стоимость 1-й наклейки - <b>{TICKET_PRICE} руб</b>💸\n\n"
                         f"Чем больше у тебя наклеек, тем больше шансов выиграть Audi A4!\n"
                         f"В связи с этим мы подготовили\n"
                         f"спец. предложение: <b><i>купив 2 наклейки,\n"
                         f"ты получаешь в подарок\n"
                         f"1 дополнительный персональный код</i></b>🤩\n\n"
                         f"<i>*спец. предложение будет действовать первые 6 часов с запуска продаж</i>")
    await state.set_state(Form.ticket_count)


@dp.message(Form.ticket_count)
async def process_ticket_count(message: types.Message, state: FSMContext):
    global available_tickets
    try:
        # Получаем количество наклеек, которое пользователь хочет КУПИТЬ
        count = int(message.text.strip())
        if count <= 0:
            raise ValueError("Количество должно быть положительным")
    except (ValueError, TypeError):
        await message.answer("❗ Введите корректное число наклеек.")
        return

    if count > available_tickets:
        await message.answer(f"⚠️ К сожалению, осталось только {available_tickets} наклеек. Пожалуйста, введите меньшее количество.")
        return

    # --- Новая логика расчета кодов и применения акции ---
    # По умолчанию количество кодов равно количеству купленных наклеек
    codes_to_generate = count
    discount_applied = False
    now = datetime.now()

    # Проверяем, активна ли акция (6 часов с момента старта бота)
    if (now - BOT_START_TIME) <= timedelta(hours=6):
        # Если акция активна и пользователь покупает РОВНО 2 наклейки
        if count == 2:
            codes_to_generate = 3  # Даем 3 кода (2 купленных + 1 бонусный)
            discount_applied = True  # Ставим флаг, чтобы показать сообщение об акции

    # Цена ВСЕГДА рассчитывается по количеству КУПЛЕННЫХ наклеек
    price = TICKET_PRICE * count

    # Сохраняем в FSM и цену, и ИТОГОВОЕ количество кодов
    await state.update_data(
        ticket_count=count,          # Сколько наклеек купил
        price=price,
        final_code_count=codes_to_generate  # Сколько кодов в итоге получит
    )
    user_data = await state.get_data()
    name = user_data.get("name")
    phone = user_data.get("phone")

    if not name or not phone:
        await message.answer("❗ Не удалось получить данные анкеты. Попробуйте заполнить заново, нажав /start.")
        await state.clear()
        return

    # --- Формируем понятное сообщение для пользователя ---
    summary = f"✅ Количество наклеек к покупке: {count}\n💰 Cтоимость: {price} руб\n"

    if discount_applied:
        summary += f"🎉 <b>Применено спец. предложение!</b> Вы получите <b>{codes_to_generate} персональных кодов!</b>\n"
    else:
        summary += f"🎁 Количество персональных кодов: {codes_to_generate}\n"


    summary += (
        f"\nКоличество наклеек забронировано для вас на 5 минут👌\n\n"
        f"‼️<b><i>ВНИМАНИЕ</i></b>‼️ Убедительная просьба "
        f"<b><i>оплачивать только по СБП и сделать</i></b> "
        f"<b><i>скриншот чека!!!</i></b>\n\n"
        f"После оплаты вам придет сообщение с вашим "
        f"персональным кодом участника🥳\n\n"
        f"Если возникли сложности, напиши нам "
        f"в телеграмме по номеру +79995295511\n\n"
        f"<b><i>Если все понятно, жми 'перейти к оплате'</i></b>\n"
        f"⬇️"
    )

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
            "description": f"Покупка {count} наклеек от NPAuto. Пользователь: {message.from_user.id}",
            "receipt": {
                "customer": {"phone": phone},
                "items": [{
                    "description": f"Фирменная наклейка NPAuto ({count} шт.)", # В чеке указываем реальное количество купленных наклеек
                    "quantity": str(count),
                    "amount": {"value": f"{TICKET_PRICE:.2f}", "currency": "RUB"}, # Цена за 1 шт.
                    "vat_code": 1,
                    "payment_mode": "full_prepayment",
                    "payment_subject": "commodity" # Наклейка - это товар (commodity)
                }]
            },
            "metadata": {
                "tg_id": str(message.from_user.id),
                "name": name,
                "phone": phone,
                "count": str(codes_to_generate) # ВАЖНО: передаем итоговое количество кодов для их генерации
            }
        }
        
        payment = Payment.create(payment_data, uuid.uuid4())
        confirmation_url = payment.confirmation.confirmation_url
        
    except Exception as e:
        await message.answer("❌ Ошибка при создании платежа. Пожалуйста, попробуйте позже.")
        logging.error("Ошибка создания платежа YooKassa:", exc_info=True)
        await state.clear()
        return

    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=confirmation_url)]
    ])
    # Убираем старый summary и отправляем новый, более структурированный
    await message.answer(summary, reply_markup=pay_kb, parse_mode=ParseMode.HTML)
    await state.clear()


# --- FLASK ВЕБХУК ---

# --- FLASK ВЕБХУК ---

async def send_success_message(user_id: int, ticket_numbers: list[str]):
    """Асинхронно отправляет сообщение об успехе вместе с видео."""
    global available_tickets
    
    # ВАЖНО: количество купленных наклеек может не совпадать с количеством кодов.
    # Чтобы правильно уменьшить остаток, нужно получить его из базы.
    # Но для простоты пока оставим вычитание по количеству кодов.
    # Если у вас акция "2+1", то вычитаться будет 3, а не 2. Это нужно иметь в виду.
    available_tickets -= len(ticket_numbers)
    
    # Вставьте сюда file_id вашего видео
    video_file_id = "BAACAgIAAxkBAAICe2hqf4KRNqxJ4rdSJcZpk0wZaA_SAAIofwAChJZZSxqaBQeuOPLfNgQ" # ЗАМЕНИТЕ НА СВОЙ FILE_ID

    # Формируем текст сообщения (caption для видео)
    caption_text = (
        f"🎉 <b>Оплата подтверждена! Поздравляем,</b>\n"
        f"<b>ты участвуешь в промо-розыгрыше,</b>\n"
        f"<b>удачи!🍀</b>\n\n"
        f"Ты получил(а) <b>{len(ticket_numbers)}</b> персональных кода(ов)\n"
        f"Твой код(ы): <b>{', '.join(ticket_numbers)}</b>\n\n"
        f"Сохрани свой(и) код(ы)!\n"
        f"Именно <b>по коду мы определим</b>\n"
        f"<b>обладателя Audi A4</b>\n"
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
    print("🔔 Вебхук получен от YooKassa")
    try:
        data = request.json
        print("Тело вебхука:", data)

        if data.get('event') == 'payment.succeeded':
            metadata = data['object']['metadata']
            user_id = int(metadata['tg_id'])
            name = metadata['name']
            phone = metadata['phone']
            count = int(metadata['count'])

            print(f"Успешная оплата от {name} (ID: {user_id}) на {count} наклеек.")

            # Добавляем билеты в нашу JSON-базу
            ticket_numbers = add_tickets_for_payment(user_id, name, phone, count)
            ticket_numbers_str = [str(num) for num in ticket_numbers]

            main_loop = g.get('main_loop')
            if main_loop and main_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    send_success_message(user_id, ticket_numbers_str),
                    main_loop
                )
            else:
                logging.error("Event loop не найден или не запущен!")

    except Exception as e:
        logging.error(f"Ошибка в обработчике вебхука: {e}", exc_info=True)

    return '', 200


@dp.message(F.photo)
async def get_photo_file_id(message: types.Message):
    # Берем фото самого лучшего качества (последнее в списке)
    file_id = message.photo[-1].file_id
    await message.answer(f"📸 Photo file_id: <code>{file_id}</code>")
    print(f"🖼️ Получен photo file_id: {file_id}")


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


