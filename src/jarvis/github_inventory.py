from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class GitHubInventoryError(RuntimeError):
    pass


_PAGE_SIZE = 100
_MAX_PAGES = 10
_OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")


def _normalize(batch: Any, public_owner: str | None) -> list[dict[str, Any]]:
    if not isinstance(batch, list) or len(batch) > _PAGE_SIZE:
        raise GitHubInventoryError("GitHub inventory returned an unexpected response shape")
    normalized = []
    for repo in batch:
        if not isinstance(repo, dict):
            raise GitHubInventoryError("GitHub inventory returned an invalid repository record")
        name, private = repo.get("full_name"), repo.get("private")
        if (not isinstance(name, str) or len(name.split("/")) != 2
                or not all(name.split("/")) or type(private) is not bool):
            raise GitHubInventoryError("GitHub inventory returned invalid repository identity fields")
        if public_owner is not None:
            if private:
                raise GitHubInventoryError("Public inventory unexpectedly included private data")
            if name.split("/", 1)[0].casefold() != public_owner.casefold():
                raise GitHubInventoryError("Public inventory returned a different owner")
        for field in ("default_branch", "updated_at", "html_url"):
            if repo.get(field) is not None and not isinstance(repo[field], str):
                raise GitHubInventoryError("GitHub inventory returned invalid repository metadata")
        normalized.append({"full_name": name, "private": private,
                           "default_branch": repo.get("default_branch"),
                           "updated_at": repo.get("updated_at"), "url": repo.get("html_url")})
    return normalized


def list_repositories(owner: str | None = None, timeout: int = 30) -> list[dict[str, Any]]:
    """Read a complete bounded inventory; an explicit owner always means public.

    GITHUB_OWNER also selects public scope. Only an owner-less call with a token
    selects authenticated accessible repositories. Public requests omit the token.
    """
    token = os.getenv("GITHUB_TOKEN")
    selected_owner = owner if owner is not None else os.getenv("GITHUB_OWNER") or None
    if selected_owner is None and not token:
        selected_owner = "lippytm"
    if selected_owner is not None and (
            not isinstance(selected_owner, str) or not _OWNER.fullmatch(selected_owner)):
        raise GitHubInventoryError("GitHub owner must be a valid account login")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "jarvis-control-tower"}
    if selected_owner is None:
        headers["Authorization"] = f"Bearer {token}"
        base_url = "https://api.github.com/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator,organization_member"
    else:
        base_url = f"https://api.github.com/users/{quote(selected_owner, safe='')}/repos?per_page=100&sort=updated"
    repos: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in range(1, _MAX_PAGES + 1):
        request = Request(f"{base_url}&page={page}", headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                batch = json.loads(response.read().decode())
                links = response.headers.get("Link", "")
        except HTTPError as exc:
            raise GitHubInventoryError(f"GitHub returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GitHubInventoryError(f"GitHub inventory failed: {type(exc).__name__}") from exc
        normalized = _normalize(batch, selected_owner)
        for repo in normalized:
            identity = repo["full_name"].casefold()
            if identity in seen:
                raise GitHubInventoryError("Inventory changed or repeated during pagination; retry the read")
            seen.add(identity)
        repos.extend(normalized)
        if not isinstance(links, str):
            raise GitHubInventoryError("GitHub returned an invalid pagination header")
        has_next = bool(re.search(r'\brel\s*=\s*[\"\']next[\"\']', links))
        if not has_next and (links or len(batch) < _PAGE_SIZE):
            return repos
        if not batch and has_next:
            raise GitHubInventoryError("GitHub returned an empty page with a next-page link")
    raise GitHubInventoryError("Inventory pagination limit reached; refusing an incomplete inventory")
