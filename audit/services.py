import logging
from typing import Any


logger = logging.getLogger("audit")

SENSITIVE_KEYS = {
    "password",
    "token",
    "access",
    "refresh",
    "secret",
    "authorization",
    "init_data",
    "x-technician-api-secret",
    "x-telegram-webapp-initdata",
}


def log_audit_event(event: str, *, actor: Any = None, target: str = "", metadata: dict | None = None) -> None:
    logger.info(
        "AUDIT event=%s actor=%s target=%s metadata=%s",
        event,
        _actor_label(actor),
        target,
        _sanitize_metadata(metadata or {}),
    )


def _actor_label(actor: Any) -> str:
    if actor is None:
        return "anonymous"

    user_id = getattr(actor, "id", None)
    username = getattr(actor, "username", None)
    role = getattr(getattr(actor, "profile", None), "role", "")
    if user_id is None and username is None:
        return str(actor)
    return f"id={user_id},username={username},role={role}"


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if key.lower() in SENSITIVE_KEYS:
            sanitized[key] = "[REDACTED]"
            continue
        if isinstance(value, dict):
            sanitized[key] = _sanitize_metadata(value)
            continue
        if isinstance(value, (list, tuple)):
            sanitized[key] = [_sanitize_scalar(item) for item in value]
            continue
        sanitized[key] = _sanitize_scalar(value)
    return sanitized


def _sanitize_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    if len(text) > 250:
        return f"{text[:247]}..."
    return text
