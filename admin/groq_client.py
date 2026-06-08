"""Client Groq partagé — retry rate limit + modèles principal / rapide."""

from __future__ import annotations

import os
import re
import time

from groq import Groq

from admin.store import get_settings

DEFAULT_MODEL = "llama-3.3-70b-versatile"
FAST_MODEL = "llama-3.1-8b-instant"


def require_api_key() -> str:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY manquante dans le fichier .env")
    return api_key


def get_client() -> Groq:
    return Groq(api_key=require_api_key())


def main_model() -> str:
    return get_settings().get("groq_model", DEFAULT_MODEL)


def fast_model() -> str:
    return get_settings().get("groq_fast_model", FAST_MODEL)


def _retry_wait_seconds(error: Exception, attempt: int) -> float:
    text = str(error)
    match = re.search(r"try again in ([\d.]+)\s*s", text, re.I)
    if match:
        return float(match.group(1)) + 0.75
    return min(30.0, (2 ** attempt) + 1.0)


def is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "429" in text or "rate limit" in text or "too many requests" in text


def friendly_error(error: Exception) -> str:
    if is_rate_limit_error(error):
        return (
            "Limite Groq atteinte (tokens/minute). "
            "Une génération = plusieurs appels (rédaction + enrichissement + traduction EN). "
            "Attendez 30–60 s puis réessayez, ou consultez console.groq.com/settings/limits."
        )
    return str(error)


def chat_completion(
    *,
    client: Groq | None = None,
    model: str | None = None,
    messages: list,
    max_tokens: int,
    temperature: float = 0.65,
    json_mode: bool = True,
    max_retries: int = 5,
    pause_before: float = 0,
):
    if pause_before > 0:
        time.sleep(pause_before)

    client = client or get_client()
    model = model or main_model()
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            last_error = exc
            if is_rate_limit_error(exc) and attempt < max_retries - 1:
                time.sleep(_retry_wait_seconds(exc, attempt))
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("Appel Groq échoué")
