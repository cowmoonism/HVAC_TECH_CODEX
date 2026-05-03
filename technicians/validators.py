from decimal import Decimal

from rest_framework import serializers


MAX_TEXT_LENGTH = 2000


def validate_non_negative_amount(value: Decimal, field_name: str = "amount") -> Decimal:
    if value < 0:
        raise serializers.ValidationError("Negative amounts are not allowed.")
    return value


def validate_telegram_numeric(value: str, field_name: str) -> str:
    if value in (None, ""):
        return value
    try:
        int(str(value))
    except (TypeError, ValueError):
        raise serializers.ValidationError("Use a numeric Telegram identifier.")
    return str(value)


def validate_http_url(value: str, field_name: str) -> str:
    if value in (None, ""):
        return value
    if not str(value).startswith(("http://", "https://")):
        raise serializers.ValidationError("Use an http or https URL.")
    return value
