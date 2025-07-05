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
from key import my_key
from table import append_user
from google_sheets import append_to_sheet
from flask import Flask, request
from yookassa import Configuration, Payment
import uuid
from decimal import Decimal, ROUND_HALF_UP


Configuration.account_id = "1085561"  # или os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = "live_L2jrGwfcPBjEmTk_tJlzN7PaD36dPljqctXPrw0TVbU"  # или os.getenv("YOOKASSA_SECRET_KEY")


TOKEN = my_key
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

available_tickets = 700
user_start_times = {}  # user_id -> datetime


class Form(StatesGroup):
    name = State()
    phone = State()
    ticket_count = State()


@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    args = message.text.split(maxsplit=1)
    arg = args[1] if len(args) > 1 else None
    print(f"/start received with arg: {arg}")

    if arg == "payment_done":
        await message.answer(
            "🎉 Спасибо за оплату! Мы получили подтверждение.\n\n"
            "Ты участвуешь в розыгрыше, удачи! 🍀"
        )
        return

    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔍 Узнать правила участия', callback_data='show_rules')]
    ])

    try:
        append_user(message.from_user.id, message.from_user.first_name, "")
    except Exception as e:
        print(f"Error in append_user: {e}")

    await message.answer(
        f"<b><i>Привет! {html.bold(message.from_user.first_name)}, это бот-помощник команды NPAuto</i></b> 👋 \n\n"
        "Совсем скоро <b><i>МЫ проведем</i></b> свой первый масштабный <b>розыгрыш автомобиля!</b> 🚗 🎁 \n\n"
        "Победитель станет обладателем легендарной <b><i>Audi A4</i></b>\n\n"
        "Присоединяйся 🍀",
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == "show_rules")
async def send_rules(callback: types.CallbackQuery):
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/+r2nV1ThTyZVlNzli")],
        [InlineKeyboardButton(text="✅ Участвовать", callback_data="participate")]
    ])
    await callback.answer()

    await callback.message.answer_video(
        video="BAACAgIAAxkBAAMFaF_JunR6fKD6Dq6lHtOJflr8hsAAAptwAAI3qwABS5CXnF6ECpdsNgQ",  # замените на реальный file_id
        caption=(
            "<b><i>Разыгрывать автомобиль мы будем по\n"
            "электронным билетам с присвоенным вам\n"
            "порядковым номером</i></b>1️⃣2️⃣3️⃣\n\n"
            "<b><i>Условия участия просты:📋</i></b>\n\n"
            "1. Быть подписанным на наш канал <b><i>NPAuto</i></b>\n"
            "🔥 чтоб быть в курсе событий\n\n"
            "2. Купить электронный билет, стоимостью\n"
            "1000руб и получить личный номер участника🔢\n\n"
            "<i>Всего в продаже 700 билетов, количество\n"
            "мест ограничено</i>😎\n\n"
            "Специально для тех, кто хочет увеличить\n"
            "свои шансы на удачу, мы подготовили <b>спец.</b>\n"
            "<b>предложение 3 билета по цене 2-х</b>👌\n\n"
            "<i>*спец. предложение будет действовать\n"
            "первые 5 часов с запуска продаж</i>"
        ),
        reply_markup=inline_kb,
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "participate")
async def handle_participation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    channel_id = "@npcoolauto"  # 👈 Убедись, что бот добавлен в этот канал как админ

    bot = callback.bot
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Заполнить анкету", callback_data="fill_form")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="show_rules")]
            ])
            await callback.message.answer(
                "✅ <b>Подписка подтверждена!</b>\n"
                "переодически я буду ее проверять, так что\n"
                "оставайся на канале😉\n\n"
                "Итак, осталось заполнить анкету,\n"
                "пробрести билет и ты в деле⬇️",
                reply_markup=inline_kb
            )
        else:
            raise Exception("Not subscribed")
    except Exception as e:
        print(f"🔴 Ошибка: {e}")
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/+r2nV1ThTyZVlNzli")],
            [InlineKeyboardButton(text="🔁 Проверить подписку", callback_data="check_subscription")]
        ])
        await callback.message.answer_photo(
            photo="AgACAgIAAxkBAAMDaF_JVWA10_CyZiTuXWzThJzp2xoAAnnzMRtu2fhKSg8xW2NZvC0BAAMCAAN4AAM2BA",  # заменишь на свой file_id
            caption="<b>К сожалению, подписка не подтверждена 😢</b>\n\n"
                    "Пожалуйста, подпишись и повтори попытку.",
            reply_markup=inline_kb,
            parse_mode="HTML"
        )


@dp.callback_query(F.data == "check_subscription")
async def check_subscription(callback: types.CallbackQuery):
    await handle_participation(callback)


@dp.callback_query(F.data == "fill_form")
async def start_form(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Для оформления билета <b>напиши свое ИМЯ</b>\n"
                                  "👇")
    await state.set_state(Form.name)


@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("❗ Ты не ввел имя😢")
        return
    await state.update_data(name=name)
    await message.answer("📞 <b>И номер телефона</b>\n\n"
                         "в формат: +79991234567\n\n"
                         "Не переживай, беспокоить спамом\n"
                         "не будем😉")
    await state.set_state(Form.phone)


@dp.message(Form.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not (phone.startswith("+7") and len(phone) == 12 and phone[2:].isdigit()):
        await message.answer("❌ Неверный формат номера. Попробуй ещё раз😉")
        return

    await state.update_data(phone=phone)
    user_start_times[message.from_user.id] = datetime.now()

    await message.answer(f"<b>Напиши сколько билетов ТЫ хочешь"
                         f"приобрести?☺️</b>\n\n"
                         f"⚠️ Осталось: {available_tickets} билетов\n\n"
                         f"Стоимость 1 билета - <b>1000руб</b>💸\n\n"
                         f"Чем больше у тебя билетов, тем больше\n"
                         f"шансов выйграть автомобиль. В связи с этим\n"
                         f"мы подготовили спец. предложение <b><i>3\n"
                         f"билета по цене 2-х</i></b>🤩\n\n"
                         f"<i>*спец. предложение будет действовать\n"
                         f"первые 5 часов с запуска продаж</i>")
    await state.set_state(Form.ticket_count)


@dp.message(Form.ticket_count)
async def process_ticket_count(message: types.Message, state: FSMContext):
    global available_tickets
    try:
        count = int(message.text.strip())
        if count <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введите корректное число билетов")
        return

    if count > available_tickets:
        await message.answer(f"⚠️ Осталось только {available_tickets} билетов")
        return

    user_id = message.from_user.id
    start_time = user_start_times.get(user_id)
    now = datetime.now()

    discounted = False
    price = 1 * count
    if count == 3 and start_time and (now - start_time <= timedelta(hours=5)):
        price = 2
        discounted = True

    available_tickets -= count

    await state.update_data(ticket_count=count, price=price)
    user_data = await state.get_data()

    name = user_data.get("name")
    phone = user_data.get("phone")

    if not name or not phone:
        await message.answer("❗ Не удалось получить данные анкеты. Попробуйте заполнить заново.")
        await state.clear()
        return

    summary = f"✅ Билетов: {count}\n💰 Цена: {price} руб"
    if discounted:
        summary += "\n🎉 Применено спец. предложение <b>3 билета по цене 2!</b>"

    try:
        unit_price = Decimal(price) / count
        unit_price = unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        print(unit_price)

        payment_data = {
            "amount": {
                "value": price,
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/npauto_gift_bot?start=payment_done"
            },
            "capture": True,
            "description": f"{message.from_user.first_name} покупает {count} билетов",
            "receipt": {
                "customer": {
                    "phone": phone
                },
                "items": [
                    {
                        "description": "Электронный билет",
                        "quantity": 1,
                        "amount": {
                            "value": price,
                            "currency": "RUB"
                        },
                        "vat_code": 1,
                        "payment_mode": "full_prepayment",
                        "payment_subject": "service"
                    }
                ]
            },
            "metadata": {
                "tg_id": str(message.from_user.id),
                "name": name,
                "phone": phone,
                "count": count
            }
        }

        print(payment_data)

        payment = Payment.create(payment_data, uuid.uuid4())
        confirmation_url = payment.confirmation.confirmation_url
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании платежа: {e}")
        logging.error("Ошибка платежа:", exc_info=True)
        await state.clear()
        return

    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=confirmation_url)]
    ])

    await message.answer(f"{summary}\n\nПерейдите к оплате:", reply_markup=pay_kb)
    await state.clear()


app = Flask(__name__)


@app.route('/yookassa/webhook', methods=['POST'])
def yookassa_webhook():
    print("🔔 Вебхук получен от YooKassa")
    print(request.json)
    data = request.json

    if data['event'] == 'payment.succeeded':
        metadata = data['object']['metadata']
        user_id = int(metadata['tg_id'])
        name = metadata['name']
        phone = metadata['phone']
        count = int(metadata['count'])

        try:
            ticket_numbers = append_to_sheet(name, phone, count)
            asyncio.run(send_success_message(user_id, ticket_numbers))
        except Exception as e:
            logging.error(f"Ошибка записи в таблицу или отправки сообщения: {e}")

    return '', 200


async def send_success_message(user_id: int, ticket_numbers: list[str]):
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.send_message(
        user_id,
        f"🎉 Оплата прошла успешно!\n\n"
        f"Ты получил <b>{len(ticket_numbers)}</b> билет(ов)\n"
        f"📌 Номера: <b>{', '.join(ticket_numbers)}</b>\n\n"
        f"Желаем удачи! 🍀"
    )


async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


@dp.message(F.photo)
async def get_file_id(message: types.Message):
    file_id = message.photo[-1].file_id
    await message.answer(f"📸 file_id: <code>{file_id}</code>", parse_mode="HTML")
    print("🔍 file_id:", file_id)


@dp.message(F.video)
async def get_video_file_id(message: types.Message):
    file_id = message.video.file_id
    await message.answer(f"🎥 file_id видео: <code>{file_id}</code>", parse_mode="HTML")
    print("🎬 video_file_id:", file_id)


if __name__ == "__main__":
    import threading

    def start_flask():
        app.run(host="0.0.0.0", port=5000)

    threading.Thread(target=start_flask).start()
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(send_success_message(user_id=123456789, ticket_numbers=["101", "102"]))
