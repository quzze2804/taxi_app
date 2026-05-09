from aiogram import Router, F
from aiogram.types import Message

router = Router()

@router.message(F.text == "/driver")
async def driver_panel(message: Message):
    await message.answer(
        "🚖 Режим водителя активирован"
    )
