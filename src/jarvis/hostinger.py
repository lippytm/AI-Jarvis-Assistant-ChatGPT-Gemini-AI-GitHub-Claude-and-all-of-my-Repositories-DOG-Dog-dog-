"""Read-only Hostinger inventory adapter; no deployment or site editing methods."""

from __future__ import annotations

import hashlib
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from .hermes import MemPalace
from .models import utc_now


WEBSITES_URL = "https://developers.hostinger.com/api/hosting/v1/websites"
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_WEBSITES = 250
MAX_PAGES = 10
PER_PAGE = 100


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate response field")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-finite response value")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def _page(opener, token: str, page: int) -> dict:
    # Only locally constructed page numbers are used; no response URL is followed.
    url = WEBSITES_URL + "?" + urlencode({"page": page, "per_page": PER_PAGE})
    try:
        request = Request(url, headers={"Authorization": f"Bearer {token}",
                                       "Content-Type": "application/json"}, method="GET")
        with opener(request, timeout=15) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Invalid response size")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant)
    except HTTPError as exc:
        exc.close()
        raise RuntimeError("Hostinger inventory request failed") from None
    except Exception:
        # Request/header, decoder and transport errors may contain private data.
        raise RuntimeError("Hostinger inventory request failed") from None
    if not isinstance(value, dict):
        raise ValueError("Unexpected Hostinger inventory response")
    return value


def list_websites(*, allow_external: bool = False, token: str | None = None,
                  opener=None, ledger: MemPalace | None = None) -> dict:
    """Read a complete bounded account inventory; keep returned site data private.

    The official contract uses data and meta.current_page/per_page/total, not
    last_page or next URLs. A changing or incomplete pagination sequence fails.
    Injected openers support offline testing; their receipts cannot prove live access.
    """
    if allow_external is not True:
        raise PermissionError("Hostinger network access requires explicit allow_external")
    secret = token if token is not None else os.getenv("HOSTINGER_API_TOKEN")
    if (not isinstance(secret, str) or not secret
            or any(not 33 <= ord(character) <= 126 for character in secret)):
        raise ValueError("HOSTINGER_API_TOKEN must be a nonempty valid token")
    transport = "injected" if opener is not None else "default_https"
    request_opener = opener if opener is not None else build_opener(_RejectRedirects()).open
    websites = []
    total = per_page = None
    seen_records, seen_identities = set(), set()
    identity_unavailable_records = 0
    started_at = utc_now()
    for page in range(1, MAX_PAGES + 1):
        payload = _page(request_opener, secret, page)
        data, meta = payload.get("data"), payload.get("meta")
        if (not isinstance(data, list) or not all(isinstance(item, dict) for item in data)
                or not isinstance(meta, dict)
                or any(type(meta.get(key)) is not int for key in ("current_page", "per_page", "total"))
                or meta["current_page"] != page or not 1 <= meta["per_page"] <= PER_PAGE
                or not 0 <= meta["total"] <= MAX_WEBSITES):
            raise ValueError("Unexpected or over-limit Hostinger inventory pagination")
        if total is None:
            total, per_page = meta["total"], meta["per_page"]
        if meta["total"] != total or meta["per_page"] != per_page:
            raise ValueError("Hostinger inventory changed during pagination")
        expected = min(per_page, total - len(websites))
        if len(data) != expected:
            raise ValueError("Incomplete Hostinger inventory page")
        for website in data:
            record_hash = _digest(website)
            if record_hash in seen_records:
                raise ValueError("Duplicate Hostinger inventory record")
            seen_records.add(record_hash)
            has_identity = False
            # The official SDK documents these as optional; domain can be null
            # for a website with no attached domain. Do not invent a required ID.
            for key in ("domain", "horizons_uuid"):
                value = website.get(key)
                if value is None:
                    continue
                if not isinstance(value, str) or not value or value != value.strip():
                    raise ValueError("Unexpected Hostinger website identity")
                normalized = value.lower().rstrip(".") if key == "domain" else value.lower()
                if not normalized:
                    raise ValueError("Unexpected Hostinger website identity")
                identity = (key, normalized)
                if identity in seen_identities:
                    raise ValueError("Duplicate Hostinger website identity")
                seen_identities.add(identity)
                has_identity = True
            if not has_identity:
                identity_unavailable_records += 1
        websites.extend(data)
        if len(websites) == total:
            break
    else:
        raise ValueError("Hostinger inventory exceeds the page limit")

    report = {"data": websites, "meta": {"total": total, "per_page": per_page,
                                         "pages_fetched": page, "complete": True},
              "scope": "hostinger_account_website_inventory", "read_only": True,
              "started_at": started_at, "observed_at": utc_now(), "transport": transport,
              "completeness_basis": "pagination_totals_and_available_record_identity",
              "identity_unavailable_records": identity_unavailable_records,
              "transactional_snapshot": False}
    if ledger is not None:
        run_id = str(uuid4())
        anchor = ledger.append(run_id, "hostinger_inventory", {
            "action": "read", "status": "inventory_response_validated",
            "scope": report["scope"], "complete": True, "website_count": total,
            "pages_fetched": page, "observed_at": report["observed_at"],
            "transport": transport, "report_sha256": _digest(report),
            "completeness_basis": report["completeness_basis"],
            "identity_unavailable_records": identity_unavailable_records,
            "transactional_snapshot": False,
            "memory_scope": "local_run_metadata_only", "shared_sync_established": False})
        events = ledger.history(run_id, expected_head=anchor)
        report["receipt"] = {"run_id": run_id, "head_sha256": anchor,
                             "chain_valid": bool(events), "scope": "local_metadata_only"}
    return report
