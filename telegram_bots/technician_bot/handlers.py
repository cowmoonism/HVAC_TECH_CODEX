from urllib.parse import urlencode, urljoin

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.filters.command import Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from telegram_bots.technician_bot.client import claim_registration, complete_registration
from telegram_bots.technician_bot.config import get_settings


router = Router()


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Submit Report"), KeyboardButton(text="Submit Expense")],
            [KeyboardButton(text="Receipt / Contract"), KeyboardButton(text="My ID")],
            [KeyboardButton(text="Complete Registration")],
        ],
        is_persistent=True,
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


def technician_panel_keyboard(user_id: int, chat_id: int) -> InlineKeyboardMarkup:
    return form_links_keyboard(user_id=user_id, chat_id=chat_id)


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
async def start(message: Message, command: CommandObject | None = None) -> None:
    token = (command.args or "").strip() if command else ""
    if token and message.chat.type == "private":
        try:
            claim_registration(
                {
                    "token": token,
                    "telegram_user_id": message.from_user.id,
                    "telegram_username": message.from_user.username or "",
                }
            )
        except Exception:
            await message.answer(
                "I couldn't link your registration token. Ask your manager to generate a fresh Telegram registration link.",
                reply_markup=main_menu_keyboard(),
            )
            return
        await message.answer(
            "Registration token linked. Now open your work group chat and press Complete Registration there.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        "HVAC technician tools are ready. Choose a form below.",
        reply_markup=technician_panel_keyboard(message.from_user.id, message.chat.id),
    )


@router.message(Command("menu"))
async def menu(message: Message) -> None:
    sent_message = await message.answer(
        "Technician panel",
        reply_markup=technician_panel_keyboard(message.from_user.id, message.chat.id),
    )
    if message.chat.type in {"group", "supergroup"}:
        try:
            await sent_message.pin(disable_notification=True)
        except Exception:
            await message.answer("Panel is ready. Pin it in this chat if you want it to stay at the top.")


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
@router.message(Command("report"))
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
@router.message(Command("expense"))
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
@router.message(Command("contract"))
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


@router.message(F.text == "Complete Registration")
@router.message(Command("register"))
async def complete_registration_handler(message: Message) -> None:
    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("Please use Complete Registration inside your work group chat.")
        return

    try:
        complete_registration(
            {
                "telegram_user_id": message.from_user.id,
                "telegram_username": message.from_user.username or "",
                "telegram_group_chat_id": message.chat.id,
                "telegram_group_title": message.chat.title or "",
                "telegram_chat_type": message.chat.type,
            }
        )
    except Exception:
        await message.answer(
            "I couldn't complete registration yet. First open your manager's registration link in a private chat with me, then try again here."
        )
        return

    await message.answer(
        "Registration complete. This work chat is now linked to your technician profile."
    )
    sent_message = await message.answer(
        "Technician panel",
        reply_markup=technician_panel_keyboard(message.from_user.id, message.chat.id),
    )
    try:
        await sent_message.pin(disable_notification=True)
    except Exception:
        await message.answer("Panel is ready. Pin it in this chat if you want it to stay at the top.")
