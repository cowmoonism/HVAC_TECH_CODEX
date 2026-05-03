import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import parse_qsl

from django.utils import timezone


MAX_INIT_DATA_AGE_SECONDS = 600


class TelegramWebAppAuthError(ValueError):
    pass


def validate_telegram_webapp_init_data(init_data: str, bot_token: str) -> dict:
    if not init_data:
        raise TelegramWebAppAuthError("Telegram WebApp initData is required.")
    if not bot_token:
        raise TelegramWebAppAuthError("Telegram bot token is not configured.")

    parsed_pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    parsed_data = dict(parsed_pairs)
    received_hash = parsed_data.pop("hash", None)
    if not received_hash:
        raise TelegramWebAppAuthError("Telegram WebApp initData is missing hash.")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed_data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramWebAppAuthError("Telegram WebApp initData hash is invalid.")

    auth_date = parsed_data.get("auth_date")
    if not auth_date:
        raise TelegramWebAppAuthError("Telegram WebApp initData is missing auth_date.")
    try:
        auth_timestamp = int(auth_date)
    except (TypeError, ValueError) as exc:
        raise TelegramWebAppAuthError("Telegram WebApp initData auth_date is invalid.") from exc

    auth_time = datetime.fromtimestamp(auth_timestamp, tz=dt_timezone.utc)
    if timezone.now() - auth_time > timedelta(seconds=MAX_INIT_DATA_AGE_SECONDS):
        raise TelegramWebAppAuthError("Telegram WebApp initData is too old.")

    if "user" in parsed_data:
        try:
            parsed_data["user"] = json.loads(parsed_data["user"])
        except json.JSONDecodeError as exc:
            raise TelegramWebAppAuthError("Telegram WebApp initData user payload is invalid.") from exc

    return parsed_data
