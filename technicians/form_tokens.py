import base64
import hashlib
import hmac
import json
import time


class TechnicianFormTokenError(ValueError):
    pass


def create_technician_form_token(payload: dict, secret: str, ttl_seconds: int = 600) -> str:
    if not secret:
        raise TechnicianFormTokenError("Technician form token secret is not configured.")
    token_payload = dict(payload)
    token_payload["exp"] = int(time.time()) + ttl_seconds
    payload_bytes = json.dumps(token_payload, separators=(",", ":"), sort_keys=True).encode()
    payload_part = _base64url_encode(payload_bytes)
    signature = _sign(payload_part, secret)
    return f"{payload_part}.{signature}"


def validate_technician_form_token(token: str, secret: str) -> dict:
    if not token:
        raise TechnicianFormTokenError("Technician form token is required.")
    if not secret:
        raise TechnicianFormTokenError("Technician form token secret is not configured.")

    try:
        payload_part, signature = token.split(".", 1)
    except ValueError as exc:
        raise TechnicianFormTokenError("Technician form token format is invalid.") from exc

    expected_signature = _sign(payload_part, secret)
    if not hmac.compare_digest(signature, expected_signature):
        raise TechnicianFormTokenError("Technician form token signature is invalid.")

    try:
        payload = json.loads(_base64url_decode(payload_part))
    except (ValueError, json.JSONDecodeError) as exc:
        raise TechnicianFormTokenError("Technician form token payload is invalid.") from exc

    expires_at = int(payload.get("exp", 0))
    if expires_at < int(time.time()):
        raise TechnicianFormTokenError("Technician form token has expired.")
    return payload


def _sign(payload_part: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), payload_part.encode(), hashlib.sha256).digest()
    return _base64url_encode(digest)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _base64url_decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding).decode()
