from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class GitHubInventoryError(RuntimeError):
    pass


def list_repositories(owner: str | None = None, timeout: int = 30) -> list[dict[str, Any]]:
    """List public repos, or all accessible repos when GITHUB_TOKEN is configured."""
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "jarvis-control-tower"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        url = "https://api.github.com/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator,organization_member"
    else:
        selected_owner = owner or os.getenv("GITHUB_OWNER", "lippytm")
        url = f"https://api.github.com/users/{quote(selected_owner)}/repos?per_page=100&sort=updated"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            repos = json.loads(response.read().decode())
    except HTTPError as exc:
        raise GitHubInventoryError(f"GitHub returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GitHubInventoryError(f"GitHub inventory failed: {type(exc).__name__}") from exc
    return [{"full_name": repo["full_name"], "private": repo["private"],
             "default_branch": repo.get("default_branch"), "updated_at": repo.get("updated_at"),
             "url": repo.get("html_url")} for repo in repos]
