"""Opt-in ChatGPT Business Workspace Agent trigger.

Returns a conversation pointer only; the API does not return agent output text.
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .safety import find_sensitive


def trigger_review(input_text: str, *, trigger_id: str | None = None,
                   token: str | None = None, allow_external: bool = False,
                   approved_for_workspace: bool = False, idempotency_key: str | None = None,
                   opener=urlopen) -> dict:
    if not allow_external or not approved_for_workspace:
        raise PermissionError("A Workspace Agent trigger requires explicit external and data-sharing approval")
    if not input_text.strip() or len(input_text) > 10000:
        raise ValueError("Review brief must be nonempty and bounded")
    if find_sensitive(input_text):
        raise ValueError("Sensitive data detected in review brief")
    identifier = trigger_id or os.getenv("JARVIS_WORKSPACE_AGENT_TRIGGER_ID")
    secret = token or os.getenv("JARVIS_WORKSPACE_AGENT_TOKEN")
    if not identifier or not re.fullmatch(r"agtch_[A-Za-z0-9_-]+", identifier):
        raise ValueError("Published Workspace Agent trigger ID is not configured")
    if not secret:
        raise ValueError("Workspace Agent access token is not configured")
    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json",
               "OpenAI-Beta": "workspace_agent_runs=v1"}
    if idempotency_key:
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", idempotency_key):
            raise ValueError("Invalid idempotency key")
        headers["Idempotency-Key"] = idempotency_key
    request = Request(f"https://api.chatgpt.com/v1/workspace_agents/{identifier}/trigger",
                      data=json.dumps({"input": input_text}).encode(), headers=headers, method="POST")
    try:
        with opener(request, timeout=20) as response:
            if response.status != 202:
                raise ValueError("Workspace Agent trigger was not accepted")
            payload = json.load(response)
    except Exception as exc:
        raise RuntimeError(f"Workspace Agent trigger failed ({type(exc).__name__})") from None
    url = payload.get("conversation_url", "")
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != "chatgpt.com" or not parts.path.startswith("/c/"):
        raise ValueError("Unexpected Workspace Agent conversation URL")
    return {"status": "accepted", "conversation_url": url,
            "run_id": payload.get("agent_trigger_run_id"),
            "response_text_available": False}
