import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonWebApp, WebAppInfo

from telegram_bots.technician_bot.config import get_settings
from telegram_bots.technician_bot.handlers import router


logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("TECHNICIAN_BOT_TOKEN is required to run the technician bot.")

    bot = Bot(token=settings.bot_token)
    app_url = settings.backend_public_base_url.rstrip("/") + "/technician/forms/app/"
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Open App",
                web_app=WebAppInfo(url=app_url),
            )
        )
        logger.info("Technician bot menu button configured.")
    except Exception:
        logger.exception("Failed to configure technician bot menu button.")

    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    logger.info("Starting technician Telegram bot polling.")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
