import asyncio
import logging

from aiogram import Bot, Dispatcher

from telegram_bots.technician_bot.config import get_settings
from telegram_bots.technician_bot.handlers import router


logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("TECHNICIAN_BOT_TOKEN is required to run the technician bot.")

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    logger.info("Starting technician Telegram bot polling.")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
