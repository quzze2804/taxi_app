from aiogram import Router, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

router = Router()

location_btn = KeyboardButton(
    text="📍 Отправить геолокацию",
    request_location=True
)

menu = ReplyKeyboardMarkup(
    keyboard=[[location_btn]],
    resize_keyboard=True
)

@router.message(F.text == "/start")
async def start(message: Message):
    await message.answer(
        "🚕 Добро пожаловать в Taxi Bot",
        reply_markup=menu
    )

@router.message(F.location)
async def get_location(message: Message):

    lat = message.location.latitude
    lon = message.location.longitude

    await message.answer(
        f"📍 Геолокация получена\n"
        f"Широта: {lat}\n"
        f"Долгота: {lon}\n\n"
        f"Ищем водителя..."
    )

    # Тут потом поиск ближайшего водителя
