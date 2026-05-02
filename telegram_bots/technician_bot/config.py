import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TechnicianBotSettings:
    bot_token: str
    backend_api_base_url: str
    backend_public_base_url: str
    technician_api_shared_secret: str


def get_settings() -> TechnicianBotSettings:
    return TechnicianBotSettings(
        bot_token=os.environ.get("TECHNICIAN_BOT_TOKEN", ""),
        backend_api_base_url=os.environ.get("BACKEND_API_BASE_URL", "http://127.0.0.1:8000"),
        backend_public_base_url=os.environ.get("BACKEND_PUBLIC_BASE_URL", "http://127.0.0.1:8000"),
        technician_api_shared_secret=os.environ.get("TECHNICIAN_API_SHARED_SECRET", ""),
    )
