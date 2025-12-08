import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from pyvnytsya_bot.config import config
from pyvnytsya_bot.handlers import common, menu, game
from pyvnytsya_bot.database.engine import init_db, async_session
from pyvnytsya_bot.middlewares.db import DbSessionMiddleware

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    # Initialize DB
    await init_db()

    bot = Bot(token=config.BOT_TOKEN.get_secret_value())
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares
    dp.update.middleware(DbSessionMiddleware(session_pool=async_session))

    # Routers
    dp.include_router(common.router)
    dp.include_router(menu.router)
    dp.include_router(game.router)

    logging.info("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
