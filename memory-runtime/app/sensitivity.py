from __future__ import annotations

import re

from app.config import get_settings


WS_RE = re.compile(r"\s+")
NON_WORD_RE = re.compile(r"[^a-z0-9\s]+")

SENSITIVE_PATTERNS = {
    "privacy_sensitive_secret": (
        "wifi password",
        "wi fi password",
        "alarm code",
        "door code",
        "lockbox code",
        "verification code",
        "one time code",
        "otp code",
        "api key",
        "secret key",
        "credit card number",
        "card number is",
        "cvv is",
        "social security number",
        "ssn is",
        "passport number",
    ),
}


def normalize_sensitive_text(content: str) -> str:
    normalized = content.strip().lower()
    normalized = NON_WORD_RE.sub(" ", normalized)
    return WS_RE.sub(" ", normalized).strip()


def detect_sensitive_reason(content: str) -> str | None:
    normalized = normalize_sensitive_text(content)
    for reason, phrases in SENSITIVE_PATTERNS.items():
        if any(phrase in normalized for phrase in phrases):
            return reason
    return None


def sensitive_memory_policy() -> str:
    return get_settings().sensitive_memory_policy


def should_mask_sensitive_outputs() -> bool:
    return get_settings().mask_sensitive_memory_outputs


def format_sensitive_text(content: str, *, is_sensitive: bool, masked: bool) -> str:
    if not is_sensitive:
        return content
    if masked:
        return "[sensitive] hidden content"
    return f"[sensitive] {content}"
