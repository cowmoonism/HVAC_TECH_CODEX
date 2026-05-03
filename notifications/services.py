import logging

import requests
from django.conf import settings

from technicians.models import Technician


logger = logging.getLogger(__name__)


class MissingTechnicianTelegramChatError(ValueError):
    pass


def get_technician_group_chat(technician: Technician) -> int:
    if not technician.telegram_group_chat_id:
        raise MissingTechnicianTelegramChatError(
            f"Technician {technician.id} does not have a Telegram group chat id configured."
        )
    return int(technician.telegram_group_chat_id)


class NotificationService:
    telegram_api_base_url = "https://api.telegram.org"

    def send_text_to_telegram(self, chat_id: int, text: str) -> bool:
        token = self._get_telegram_token()
        if not token:
            logger.warning("Telegram bot token is missing; text message to chat %s was not sent.", chat_id)
            return False

        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        return self._post_telegram("sendMessage", token, payload)

    def send_document_to_telegram(self, chat_id: int, file_url: str, caption: str = None) -> bool:
        token = self._get_telegram_token()
        if not token:
            logger.warning("Telegram bot token is missing; document to chat %s was not sent.", chat_id)
            return False

        payload = {
            "chat_id": chat_id,
            "document": file_url,
        }
        if caption:
            payload["caption"] = caption
        return self._post_telegram("sendDocument", token, payload)

    def _get_telegram_token(self) -> str:
        return getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""

    def _post_telegram(self, method: str, token: str, payload: dict) -> bool:
        url = f"{self.telegram_api_base_url}/bot{token}/{method}"
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error(
                "Telegram %s request failed for chat %s with %s.",
                method,
                payload.get("chat_id"),
                exc.__class__.__name__,
                exc_info=True,
            )
            return False

        data = response.json()
        if not data.get("ok"):
            logger.error(
                "Telegram %s request returned not-ok response for chat %s with description=%s.",
                method,
                payload.get("chat_id"),
                data.get("description", ""),
            )
            return False

        logger.info("Telegram %s request succeeded for chat %s.", method, payload.get("chat_id"))
        return True
