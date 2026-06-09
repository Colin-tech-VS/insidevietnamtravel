"""Client Mistral AI (API REST) — alternative gratuite à Groq.

Pourquoi Mistral : le palier gratuit Mistral (« La Plateforme ») offre des limites
par minute bien plus larges que Groq (≈ 500 k tokens/min vs 6 000 sur le 70B de Groq),
donc un guide long de 1 500–1 800 mots passe en un seul appel, sans la gymnastique de
clamp/bascule de modèle qu'impose le TPM riquiqui de Groq.

On utilise l'API REST directement via `requests` (déjà une dépendance) : endpoint
OpenAI-compatible, stable, et zéro nouvelle dépendance à maintenir. On expose un objet
de réponse au même format que le SDK Groq (`resp.choices[0].message.content`) pour que
les modules appelants soient agnostiques du fournisseur.
"""

from __future__ import annotations

import os
import time

import requests

from admin.store import get_settings

API_URL = "https://api.mistral.ai/v1/chat/completions"

# Modèles par défaut du palier gratuit Mistral.
# - mistral-small-latest : bon rapport qualité/limites, rédaction longue FR solide.
# - open-mistral-nemo    : léger et rapide, idéal traduction/suggestions (quota séparé).
DEFAULT_MODEL = "mistral-small-latest"
FAST_MODEL = "open-mistral-nemo"

# Plafond de sortie (mistral-small a un grand contexte). Contrairement à Groq, Mistral
# n'a pas de TPM riquiqui : on peut laisser de la marge pour que le JSON se termine.
MAX_OUTPUT_TOKENS = 16000
# Marge ajoutée au max_tokens demandé : les cibles SEO ont été dimensionnées au plus
# juste pour le TPM de Groq ; sans marge, Mistral coupe parfois le JSON en plein milieu
# (« Unterminated string »). On lui laisse de quoi refermer proprement la réponse.
OUTPUT_HEADROOM = 4096
REQUEST_TIMEOUT = 120  # secondes


class _Message:
    def __init__(self, content: str):
        self.content = content


class _Choice:
    def __init__(self, content: str):
        self.message = _Message(content)


class _Response:
    """Réponse minimaliste au format SDK : resp.choices[0].message.content."""

    def __init__(self, content: str):
        self.choices = [_Choice(content)]


def require_api_key() -> str:
    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not api_key:
        raise ValueError("MISTRAL_API_KEY manquante dans le fichier .env")
    return api_key


def has_api_key() -> bool:
    return bool(os.environ.get("MISTRAL_API_KEY", "").strip())


def main_model() -> str:
    return get_settings().get("mistral_model", DEFAULT_MODEL)


def fast_model() -> str:
    return get_settings().get("mistral_fast_model", FAST_MODEL)


def is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return (
        "429" in text
        or "rate limit" in text
        or "too many requests" in text
        or "capacity exceeded" in text
    )


def friendly_error(error: Exception) -> str:
    if is_rate_limit_error(error):
        return (
            "Limite Mistral atteinte (requêtes par minute). Le palier gratuit Mistral "
            "est large mais plafonné (≈ 1 requête/seconde) : patientez quelques secondes "
            "puis réessayez. Voir console.mistral.ai."
        )
    return str(error)


def _retry_wait_seconds(resp: requests.Response | None, attempt: int) -> float:
    if resp is not None:
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after) + 0.5
            except ValueError:
                pass
    return min(30.0, (2 ** attempt) + 1.0)


def chat_completion(
    *,
    client=None,  # accepté pour la parité de signature avec groq_client (non utilisé)
    model: str | None = None,
    messages: list,
    max_tokens: int,
    temperature: float = 0.65,
    json_mode: bool = True,
    max_retries: int = 5,
    pause_before: float = 0,
) -> _Response:
    if pause_before > 0:
        time.sleep(pause_before)

    api_key = require_api_key()
    payload: dict = {
        "model": model or main_model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": min(int(max_tokens) + OUTPUT_HEADROOM, MAX_OUTPUT_TOKENS),
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(min(30.0, (2 ** attempt) + 1.0))
                continue
            raise

        if resp.status_code == 429:
            last_error = RuntimeError(f"429 rate limit Mistral: {resp.text[:200]}")
            if attempt < max_retries - 1:
                time.sleep(_retry_wait_seconds(resp, attempt))
                continue
            raise last_error

        if resp.status_code >= 400:
            raise RuntimeError(f"Erreur Mistral {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return _Response(content)

    if last_error:
        raise last_error
    raise RuntimeError("Appel Mistral échoué")
