"""Dispatcher multi-fournisseur IA — Groq par défaut, Mistral en option, repli Groq.

Tout le contenu (guides, destinations, newsletter, traduction FR→EN, suggestions de
sujets) passe désormais par ce module plutôt que d'appeler Groq directement. Le
fournisseur actif est choisi dans l'admin (réglage `ai_provider`) ou, à défaut, via la
variable d'environnement AI_PROVIDER. Si l'appel au fournisseur actif échoue (limite
atteinte, clé absente, erreur), on bascule automatiquement sur Groq en repli quand sa
clé est configurée — d'où « Mistral en parallèle, Groq en fallback ».

Les appelants n'ont plus à connaître le fournisseur : ils passent `fast=True` pour le
modèle rapide (traduction, suggestions, enrichissement) ou rien pour le modèle
principal, et ce module résout le bon nom de modèle selon le fournisseur retenu.
"""

from __future__ import annotations

import json
import os
import re

from admin import groq_client
from admin import mistral_client
from admin.store import get_settings

PROVIDERS = {"groq": groq_client, "mistral": mistral_client}
PROVIDER_LABELS = {"groq": "Groq", "mistral": "Mistral AI"}
DEFAULT_PROVIDER = "groq"
FALLBACK_PROVIDER = "groq"


def parse_json(raw: str) -> dict:
    """Parse la réponse IA en JSON, avec réparation si elle est tronquée.

    Les modèles renvoient parfois un JSON coupé (chaîne non terminée) quand la sortie
    bute sur le plafond de tokens — d'où l'erreur « Unterminated string starting at
    line 12 ». Plutôt que de planter la génération, on referme proprement la chaîne et
    les accolades/crochets ouverts pour récupérer un article exploitable (quitte à ce
    qu'il soit un peu court, l'utilisateur peut ensuite « Améliorer »).
    """
    text = (raw or "").strip()
    # Retire d'éventuelles clôtures markdown ```json ... ```
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_repair_truncated_json(text))


def _repair_truncated_json(text: str) -> str:
    start = text.find("{")
    if start > 0:
        text = text[start:]

    stack: list[str] = []
    in_str = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if in_str:
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]" and stack:
            stack.pop()

    if in_str:  # chaîne coupée en plein milieu → on la referme
        text += '"'
    text = text.rstrip()
    if text.endswith(","):  # virgule pendante avant une accolade fermante
        text = text[:-1]
    for opener in reversed(stack):
        text += "}" if opener == "{" else "]"
    return text


def provider() -> str:
    """Fournisseur actif : réglage admin prioritaire, sinon AI_PROVIDER, sinon défaut."""
    name = get_settings().get("ai_provider")
    if not name:
        name = os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER)
    name = str(name).strip().lower()
    return name if name in PROVIDERS else DEFAULT_PROVIDER


def provider_label(name: str | None = None) -> str:
    return PROVIDER_LABELS.get(name or provider(), "IA")


def _impl(name: str):
    return PROVIDERS.get(name, groq_client)


def _has_key(name: str) -> bool:
    if name == "groq":
        return bool(os.environ.get("GROQ_API_KEY", "").strip())
    if name == "mistral":
        return mistral_client.has_api_key()
    return False


def is_configured() -> bool:
    """Au moins un fournisseur exploitable (clé présente)."""
    return any(_has_key(name) for name in PROVIDERS)


def provider_status() -> dict:
    """État par fournisseur pour l'UI admin."""
    return {name: _has_key(name) for name in PROVIDERS}


def require_api_key() -> None:
    if not is_configured():
        raise ValueError(
            "Aucune clé IA configurée — ajoutez GROQ_API_KEY ou MISTRAL_API_KEY dans .env"
        )


def main_model() -> str:
    return _impl(provider()).main_model()


def fast_model() -> str:
    return _impl(provider()).fast_model()


def friendly_error(error: Exception) -> str:
    return _impl(provider()).friendly_error(error)


def _provider_order() -> list[str]:
    """Fournisseur actif d'abord, puis repli Groq s'il est distinct et configuré."""
    active = provider()
    order = [active]
    if FALLBACK_PROVIDER != active and _has_key(FALLBACK_PROVIDER):
        order.append(FALLBACK_PROVIDER)
    return order


def chat_completion(
    *,
    client=None,  # ignoré : chaque fournisseur gère son propre client
    model: str | None = None,  # override explicite optionnel (rarement utile)
    messages: list,
    max_tokens: int,
    temperature: float = 0.65,
    json_mode: bool = True,
    fast: bool = False,
    max_retries: int = 5,
    pause_before: float = 0,
):
    """Route l'appel vers le fournisseur actif, avec repli Groq automatique.

    `fast=True` sélectionne le modèle rapide du fournisseur (quota séparé, plus véloce) —
    utilisé pour la traduction, l'enrichissement et les suggestions.
    """
    last_error: Exception | None = None
    attempted = False

    for idx, name in enumerate(_provider_order()):
        if not _has_key(name):
            continue
        impl = _impl(name)
        chosen_model = model or (impl.fast_model() if fast else impl.main_model())
        attempted = True
        try:
            return impl.chat_completion(
                model=chosen_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=json_mode,
                max_retries=max_retries,
                # On ne paie la pause anti rate-limit que sur la 1re tentative.
                pause_before=pause_before if idx == 0 else 0,
            )
        except Exception as exc:  # noqa: BLE001 — on tente le fournisseur de repli
            last_error = exc
            continue

    if last_error:
        raise last_error
    if not attempted:
        raise ValueError(
            "Aucune clé IA configurée — ajoutez GROQ_API_KEY ou MISTRAL_API_KEY dans .env"
        )
    raise RuntimeError("Appel IA échoué")
