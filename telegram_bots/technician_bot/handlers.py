from urllib.parse import urlencode, urljoin

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from telegram_bots.technician_bot.config import get_settings


router = Router()


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Submit Report"), KeyboardButton(text="Submit Expense")],
            [KeyboardButton(text="Receipt / Contract"), KeyboardButton(text="My ID")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose an action",
    )


def form_links_keyboard(user_id: int, chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Submit Report", web_app=WebAppInfo(url=_form_url("report", user_id, chat_id))),
                InlineKeyboardButton(text="Submit Expense", web_app=WebAppInfo(url=_form_url("expense", user_id, chat_id))),
            ],
            [
                InlineKeyboardButton(text="Receipt / Contract", web_app=WebAppInfo(url=_form_url("contract", user_id, chat_id))),
                InlineKeyboardButton(text="My ID", callback_data="my_id"),
            ],
        ]
    )


def _form_url(form_name: str, user_id: int, chat_id: int) -> str:
    settings = get_settings()
    path = f"/technician/forms/{form_name}/"
    query = urlencode(
        {
            "telegram_user_id": user_id,
            "telegram_group_chat_id": chat_id,
        }
    )
    return f"{urljoin(settings.backend_public_base_url.rstrip('/') + '/', path.lstrip('/'))}?{query}"


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "HVAC technician tools are ready. Choose a form below.",
        reply_markup=form_links_keyboard(message.from_user.id, message.chat.id),
    )


@router.message(F.text == "My ID")
async def my_id(message: Message) -> None:
    user = message.from_user
    username = f"@{user.username}" if user and user.username else "N/A"
    await message.answer(
        "\n".join(
            [
                "Telegram identity",
                f"User ID: {user.id if user else 'N/A'}",
                f"Chat ID: {message.chat.id}",
                f"Username: {username}",
            ]
        )
    )


@router.callback_query(F.data == "my_id")
async def my_id_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    username = f"@{user.username}" if user and user.username else "N/A"
    await callback.message.answer(
        "\n".join(
            [
                "Telegram identity",
                f"User ID: {user.id if user else 'N/A'}",
                f"Chat ID: {callback.message.chat.id}",
                f"Username: {username}",
            ]
        )
    )
    await callback.answer()


@router.message(F.text == "Submit Report")
async def submit_report_link(message: Message) -> None:
    await message.answer(
        "Open the report form:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Submit Report",
                        web_app=WebAppInfo(url=_form_url("report", message.from_user.id, message.chat.id)),
                    )
                ]
            ]
        ),
    )


@router.message(F.text == "Submit Expense")
async def submit_expense_link(message: Message) -> None:
    await message.answer(
        "Open the expense form:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Submit Expense",
                        web_app=WebAppInfo(url=_form_url("expense", message.from_user.id, message.chat.id)),
                    )
                ]
            ]
        ),
    )


@router.message(F.text == "Receipt / Contract")
async def receipt_contract_link(message: Message) -> None:
    await message.answer(
        "Open the receipt / contract form:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Receipt / Contract",
                        web_app=WebAppInfo(url=_form_url("contract", message.from_user.id, message.chat.id)),
                    )
                ]
            ]
        ),
    )
