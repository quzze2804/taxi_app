import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from handlers import client, driver

load_dotenv()

async def main():
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    dp = Dispatcher()

    # Удаляем webhook, чтобы можно было использовать polling
    await bot.delete_webhook(drop_pending_updates=True)

    dp.include_router(client.router)
    dp.include_router(driver.router)

    print("🚕 Бот такси Арциз запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())