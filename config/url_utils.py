from urllib.parse import urljoin

from django.conf import settings


def build_public_url(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    if not path_or_url.startswith("/"):
        path_or_url = f"/{path_or_url}"

    public_base_url = getattr(settings, "PUBLIC_BASE_URL", "").strip()
    if not public_base_url:
        return path_or_url

    return urljoin(f"{public_base_url.rstrip('/')}/", path_or_url.lstrip("/"))
