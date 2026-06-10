"""Tokens HMAC pour téléchargement guide itinéraire (inscription newsletter)."""

from __future__ import annotations

import hashlib
import hmac
import os


def _secret() -> bytes:
    return os.environ.get("SECRET_KEY", "dev-change-in-production").encode()


def make_itinerary_download_token(email: str, slug: str) -> str:
    payload = f"{email.strip().lower()}|{slug.strip()}"
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


def verify_itinerary_download_token(email: str, slug: str, token: str) -> bool:
    if not email or not slug or not token:
        return False
    expected = make_itinerary_download_token(email, slug)
    return hmac.compare_digest(expected, token.strip())
