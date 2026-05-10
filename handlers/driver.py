import os
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, Message
from aiogram.enums import ParseMode

router = Router()
TAXI_PHONE = "+380 75 443 67 57"

# Временное хранилище: driver_id -> client_id
driver_context = {}

def get_driver_location_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить мою геопозицию", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_quick_responses():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏳ Уже выхожу")],
            [KeyboardButton(text="⏳ Буду через 5 минут")],
            [KeyboardButton(text="🚕 Я уже у машины")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

@router.callback_query(F.data.startswith("accept_"))
async def accept_order(callback: CallbackQuery, bot: Bot):
    client_id = int(callback.data.split("_")[1])
    driver_name = callback.from_user.first_name
    driver_id = callback.from_user.id

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📍 Запросить ГЕО у клиента", callback_data=f"req_geo_{client_id}"),
            InlineKeyboardButton(text="📞 Запросить номер клиента", callback_data=f"req_phone_{client_id}")
        ],
        [InlineKeyboardButton(text="🚗 Отправить моё ГЕО клиенту", callback_data=f"send_driver_geo_{client_id}")],
        [InlineKeyboardButton(text="📍 Я на месте", callback_data=f"on_spot_{client_id}")],
        [InlineKeyboardButton(text="🏁 Завершить поездку", callback_data=f"finish_{client_id}")]
    ])

    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"✅ <b>Заказ принят!</b>\n"
        f"🚕 <b>Водитель:</b> {driver_name}\n"
        f"🆔 <b>ID клиента:</b> {client_id}\n\n"
        f"⬇️ <i>Используйте кнопки ниже для управления поездкой</i>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Отправляем клиенту уведомление и кнопку для отправки геолокации
    await bot.send_message(
        chat_id=client_id,
        text=f"🚕 <b>Водитель найден!</b>\n\n"
             f"✓ <b>Водитель:</b> {driver_name}\n"
             f"✓ Ваш заказ принят\n"
             f"✓ Автомобиль уже направляется к вам\n\n"
             f"📍 <b>Чтобы водитель быстрее вас нашел, поделитесь своей геолокацией:</b>\n\n"
             f"Нажмите на кнопку ниже и отправьте ваше местоположение. 👇\n\n"
             f"📞 <i>При необходимости свяжитесь с нами:</i> <a href='tel:{TAXI_PHONE}'>{TAXI_PHONE}</a>\n\n"
             f"✨ <i>Благодарим за выбор нашего сервиса!</i>",
        reply_markup=get_share_location_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

def get_share_location_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить мою геолокацию водителю", request_location=True)],
            [KeyboardButton(text="🚕 Основное меню")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

@router.callback_query(F.data.startswith("send_driver_geo_"))
async def send_driver_geo_request(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    client_id = int(parts[3])
    driver_id = callback.from_user.id
    
    driver_context[driver_id] = client_id
    
    await bot.send_message(
        chat_id=driver_id,
        text="📍 <b>Отправка геолокации клиенту</b>\n\n"
             "Нажмите на кнопку ниже и отправьте ваше текущее местоположение.\n"
             "<i>Клиент увидит, где находится ваш автомобиль.</i>",
        reply_markup=get_driver_location_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.message(F.location)
async def handle_location(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    # Если это водитель отправляет геолокацию клиенту
    if user_id in driver_context:
        client_id = driver_context.pop(user_id)
        lat = message.location.latitude
        lon = message.location.longitude
        maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        
        await bot.send_message(
            chat_id=client_id,
            text=f"📍 <b>Ваш водитель уже в пути!</b>\n\n"
                 f"Вы можете отслеживать местоположение автомобиля:\n"
                 f"<a href='{maps_link}'>🗺 Открыть карту</a>",
            parse_mode=ParseMode.HTML
        )
        await bot.send_location(client_id, latitude=lat, longitude=lon)
        
        await message.answer(
            "✅ <b>Геолокация успешно отправлена клиенту!</b>\n\n"
            "Клиент теперь видит, где находится ваш автомобиль. 🚕",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Если это клиент отправляет геолокацию водителю (в чат заказов)
    orders_chat_id = os.getenv('ORDERS_CHAT_ID')
    lat = message.location.latitude
    lon = message.location.longitude
    maps_link = f"https://www.google.com/maps?q={lat},{lon}"
    
    await bot.send_message(
        chat_id=orders_chat_id,
        text=f"📍 <b>Клиент поделился геолокацией!</b>\n"
             f"👤 <b>Клиент:</b> @{message.from_user.username or message.from_user.id}\n\n"
             f"<a href='{maps_link}'>🗺 Открыть в Google Maps</a>",
        parse_mode=ParseMode.HTML
    )
    await bot.send_location(orders_chat_id, latitude=lat, longitude=lon)
    
    await message.answer(
        "✅ <b>Ваша геолокация отправлена водителю!</b>\n\n"
        "📍 Теперь водитель точно знает, где вас найти.\n\n"
        "✨ <i>Спасибо!</i>",
        reply_markup=get_main_menu(),  # нужно импортировать или определить
        parse_mode=ParseMode.HTML
    )

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚕 Заказать такси")],
            [KeyboardButton(text="💬 Поддержка")]
        ],
        resize_keyboard=True
    )

@router.callback_query(F.data.startswith("req_geo_"))
async def request_geo(callback: CallbackQuery, bot: Bot):
    client_id = int(callback.data.split("_")[2])
    location_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить моё местоположение", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await bot.send_message(
        chat_id=client_id,
        text="🚕 <b>Водитель просит уточнить ваше местоположение</b>\n\n"
             "Пожалуйста, поделитесь вашей геолокацией, нажав на кнопку ниже: 👇",
        reply_markup=location_keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer("✓ Запрос отправлен!")

@router.callback_query(F.data.startswith("req_phone_"))
async def request_phone(callback: CallbackQuery, bot: Bot):
    client_id = int(callback.data.split("_")[2])
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await bot.send_message(
        chat_id=client_id,
        text="📞 <b>Водитель просит ваш номер телефона для связи</b>\n\n"
             "Пожалуйста, поделитесь вашим контактом: 👇",
        reply_markup=contact_keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer("✓ Запрос отправлен!")

@router.callback_query(F.data.startswith("on_spot_"))
async def driver_on_spot(callback: CallbackQuery, bot: Bot):
    client_id = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🏁 Завершить поездку", callback_data=f"finish_{client_id}")
        ]]
    )
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await bot.send_message(
        chat_id=client_id,
        text="🚕 <b>Водитель на месте!</b>\n\n"
             "Ваш автомобиль уже ожидает вас. Выходите, пожалуйста. ✨\n\n"
             "<i>Хорошей поездки!</i>",
        reply_markup=get_quick_responses(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer("✓ Клиент уведомлен о прибытии")

@router.callback_query(F.data.startswith("finish_"))
async def finish_trip(callback: CallbackQuery, bot: Bot):
    client_id = int(callback.data.split("_")[1])
    msg_id = callback.message.message_id 
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"🏁 <b>Поездка успешно завершена!</b>\n"
        f"<i>Благодарим за сотрудничество ✨</i>",
        parse_mode=ParseMode.HTML
    )
    
    rating_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 ⭐", callback_data=f"rate_1_{msg_id}"),
             InlineKeyboardButton(text="2 ⭐", callback_data=f"rate_2_{msg_id}"),
             InlineKeyboardButton(text="3 ⭐", callback_data=f"rate_3_{msg_id}")],
            [InlineKeyboardButton(text="4 ⭐", callback_data=f"rate_4_{msg_id}"),
             InlineKeyboardButton(text="5 ⭐", callback_data=f"rate_5_{msg_id}")]
        ]
    )
    
    await bot.send_message(
        chat_id=client_id,
        text="🏁 <b>Поездка завершена!</b>\n\n"
             "Пожалуйста, оцените качество обслуживания водителя, "
             "чтобы мы могли стать еще лучше:\n\n"
             "<i>Ваша оценка очень важна для нас! ✨</i>",
        reply_markup=rating_keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()