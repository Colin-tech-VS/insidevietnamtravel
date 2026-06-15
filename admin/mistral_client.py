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

import json
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

# On appelle Mistral en STREAMING (SSE). En non-streamé, le serveur calcule tout
# l'article (jusqu'à ~10 000 tokens) avant d'envoyer le moindre octet : le `read
# timeout` de requests = durée TOTALE de génération, qui dépasse vite 120 s sur le
# palier gratuit → la requête était coupée (« ça prend trop de temps »), puis
# réessayée 5×, d'où des attentes de plusieurs minutes et le « anormalement long ».
# En streaming, les tokens arrivent en continu : le timeout ci-dessous ne mesure plus
# que l'écart ENTRE deux chunks (quelques centaines de ms), pas la durée totale —
# une génération longue peut donc durer plusieurs minutes sans jamais être coupée.
CONNECT_TIMEOUT = 15   # secondes pour établir la connexion
READ_TIMEOUT = 120     # secondes d'inactivité MAX entre deux chunks streamés


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


def _consume_stream(resp: requests.Response) -> str:
    """Agrège le contenu d'une réponse SSE Mistral (`stream: true`).

    Chaque ligne `data: {...}` porte un delta ; `data: [DONE]` clôt le flux. Tant que
    des chunks arrivent, la connexion reste active : on ne peut donc pas être coupé par
    un timeout « durée totale », seulement par une vraie inactivité prolongée du serveur.
    """
    parts: list[str] = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if not line.startswith("data:"):
            continue
        data = line[len("data:"):].strip()
        if data == "[DONE]":
            break
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        choices = obj.get("choices") or []
        if not choices:
            continue
        piece = (choices[0].get("delta") or {}).get("content")
        if piece:
            parts.append(piece)
    return "".join(parts)


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
    chosen = model or main_model()
    headroom = 768 if chosen == fast_model() else OUTPUT_HEADROOM
    payload: dict = {
        "model": chosen,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": min(int(max_tokens) + headroom, MAX_OUTPUT_TOKENS),
        "stream": True,
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
            resp = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                stream=True,
            )
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(min(30.0, (2 ** attempt) + 1.0))
                continue
            raise

        if resp.status_code == 429:
            body = resp.text[:200]
            resp.close()
            last_error = RuntimeError(f"429 rate limit Mistral: {body}")
            if attempt < max_retries - 1:
                time.sleep(_retry_wait_seconds(resp, attempt))
                continue
            raise last_error

        if resp.status_code >= 400:
            body = resp.text[:300]
            resp.close()
            raise RuntimeError(f"Erreur Mistral {resp.status_code}: {body}")

        try:
            content = _consume_stream(resp)
        except requests.RequestException as exc:
            # Flux interrompu en cours de route (coupure réseau / serveur muet) : on
            # retente une fois de plus si le budget de tentatives le permet.
            last_error = exc
            resp.close()
            if attempt < max_retries - 1:
                time.sleep(min(30.0, (2 ** attempt) + 1.0))
                continue
            raise
        finally:
            resp.close()

        if content:
            return _Response(content)

        # Flux vide (rare) : on retente, sinon on remonte une erreur claire.
        last_error = RuntimeError("Réponse Mistral vide (flux sans contenu)")
        if attempt < max_retries - 1:
            time.sleep(min(30.0, (2 ** attempt) + 1.0))
            continue
        raise last_error

    if last_error:
        raise last_error
    raise RuntimeError("Appel Mistral échoué")
