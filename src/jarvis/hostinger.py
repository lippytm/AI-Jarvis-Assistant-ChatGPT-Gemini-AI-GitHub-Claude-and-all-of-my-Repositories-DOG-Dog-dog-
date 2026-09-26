"""Read-only Hostinger inventory adapter; no deployment or site editing methods."""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


WEBSITES_URL = "https://developers.hostinger.com/api/hosting/v1/websites"


def list_websites(*, allow_external: bool = False, token: str | None = None, opener=urlopen) -> dict:
    if not allow_external:
        raise PermissionError("Hostinger network access requires explicit allow_external")
    secret = token or os.getenv("HOSTINGER_API_TOKEN")
    if not secret:
        raise ValueError("HOSTINGER_API_TOKEN is not configured")
    request = Request(WEBSITES_URL, headers={"Authorization": f"Bearer {secret}",
                                             "Content-Type": "application/json"}, method="GET")
    try:
        with opener(request, timeout=15) as response:
            payload = json.load(response)
    except Exception as exc:
        raise RuntimeError(f"Hostinger read-only inventory failed ({type(exc).__name__})") from None
    if not isinstance(payload, dict):
        raise ValueError("Unexpected Hostinger response")
    return payload
