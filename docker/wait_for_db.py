import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
from django.db import OperationalError, connections


def main() -> int:
    django.setup()
    max_attempts = int(os.environ.get("DB_WAIT_ATTEMPTS", "30"))
    delay_seconds = float(os.environ.get("DB_WAIT_DELAY", "1"))

    for attempt in range(1, max_attempts + 1):
        try:
            connections["default"].ensure_connection()
        except OperationalError as exc:
            print(f"Waiting for database ({attempt}/{max_attempts}): {exc}")
            time.sleep(delay_seconds)
        else:
            connections["default"].close()
            print("Database is ready.")
            return 0

    print("Database did not become ready in time.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
