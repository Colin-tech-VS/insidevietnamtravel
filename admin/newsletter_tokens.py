"""Tokens sécurisés pour désinscription newsletter (HMAC)."""

from __future__ import annotations

import hashlib
import hmac
import os
from urllib.parse import quote

import config


def _secret() -> bytes:
    return os.environ.get("SECRET_KEY", "dev-change-in-production").encode()


def make_unsubscribe_token(email: str) -> str:
    email = email.strip().lower()
    return hmac.new(_secret(), email.encode(), hashlib.sha256).hexdigest()


def verify_unsubscribe_token(email: str, token: str) -> bool:
    if not email or not token:
        return False
    expected = make_unsubscribe_token(email)
    return hmac.compare_digest(expected, token.strip())


def unsubscribe_url(email: str) -> str:
    email = email.strip().lower()
    token = make_unsubscribe_token(email)
    return (
        f"{config.SITE_URL}/newsletter/desinscription"
        f"?email={quote(email)}&token={token}"
    )
