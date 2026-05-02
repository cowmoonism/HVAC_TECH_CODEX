from urllib.parse import urljoin

import requests

from telegram_bots.technician_bot.config import TechnicianBotSettings, get_settings


class TechnicianBackendClient:
    def __init__(self, settings: TechnicianBotSettings | None = None):
        self.settings = settings or get_settings()

    def submit_work_report(self, payload: dict) -> dict:
        return self._post("/api/technician/submit-work-report/", payload)

    def submit_expense(self, payload: dict) -> dict:
        return self._post("/api/technician/submit-expense/", payload)

    def submit_contract(self, payload: dict) -> dict:
        return self._post("/api/technician/submit-contract/", payload)

    def build_url(self, path: str) -> str:
        return urljoin(self.settings.backend_api_base_url.rstrip("/") + "/", path.lstrip("/"))

    def headers(self) -> dict:
        return {
            "X-Technician-Api-Secret": self.settings.technician_api_shared_secret,
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict) -> dict:
        response = requests.post(
            self.build_url(path),
            json=payload,
            headers=self.headers(),
            timeout=15,
        )
        response.raise_for_status()
        return response.json()


def submit_work_report(payload: dict) -> dict:
    return TechnicianBackendClient().submit_work_report(payload)


def submit_expense(payload: dict) -> dict:
    return TechnicianBackendClient().submit_expense(payload)


def submit_contract(payload: dict) -> dict:
    return TechnicianBackendClient().submit_contract(payload)
