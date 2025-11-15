from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, TypedDict

from app.config import settings


class PromptOverrideInvalidError(Exception):
    """Raised when a prompt override token cannot be decoded or signature fails."""


class PromptOverrideExpiredError(Exception):
    """Raised when a prompt override token is older than the allowed TTL."""


class PromptOverridePayload(TypedDict):
    work_id: int
    chapter_id: int
    model: str
    template: str
    parameters: dict[str, Any] | None
    exp: int


@dataclass(frozen=True, slots=True)
class PromptOverrideToken:
    token: str
    expires_at: int


def create_prompt_override_token(
    *,
    work_id: int,
    chapter_id: int,
    model: str,
    template: str,
    parameters: dict[str, Any] | None = None,
) -> PromptOverrideToken:
    ttl_seconds = max(60, settings.prompt_override_token_ttl_seconds or 0)
    expires_at = int(time.time()) + ttl_seconds
    payload: PromptOverridePayload = {
        "work_id": work_id,
        "chapter_id": chapter_id,
        "model": model,
        "template": template,
        "parameters": parameters or None,
        "exp": expires_at,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signature = _sign(payload_bytes)
    token = f"{_b64encode(signature)}.{_b64encode(payload_bytes)}"
    return PromptOverrideToken(token=token, expires_at=expires_at)


def decode_prompt_override_token(token: str) -> PromptOverridePayload:
    try:
        sig_b64, payload_b64 = token.split(".", 1)
    except ValueError:
        raise PromptOverrideInvalidError("Malformed prompt override token") from None

    payload_bytes = _b64decode(payload_b64)
    provided_sig = _b64decode(sig_b64)
    expected_sig = _sign(payload_bytes)
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise PromptOverrideInvalidError("Prompt override signature mismatch")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError as exc:
        raise PromptOverrideInvalidError("Prompt override payload invalid") from exc

    if not isinstance(payload, dict):
        raise PromptOverrideInvalidError("Prompt override payload malformed")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise PromptOverrideInvalidError("Prompt override expiration missing")

    now = int(time.time())
    if now > exp:
        raise PromptOverrideExpiredError("Prompt override expired")

    return payload  # type: ignore[return-value]


def _sign(payload: bytes) -> bytes:
    secret = settings.prompt_override_secret.encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).digest()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(encoded + padding)
