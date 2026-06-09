"""Client Groq partagé — retry rate limit + modèles principal / rapide."""

from __future__ import annotations

import os
import re
import time

from groq import Groq

from admin.store import get_settings

DEFAULT_MODEL = "llama-3.3-70b-versatile"
FAST_MODEL = "llama-3.1-8b-instant"

# TPM (tokens/minute) du palier gratuit Groq, par modèle. POINT CLÉ : Groq
# décompte de ce budget « tokens d'entrée + max_tokens RÉSERVÉS » (pas seulement
# la sortie réelle). Un seul appel qui réserve plus que ce budget renvoie donc un
# 429 immédiat — même si le dashboard, qui n'affiche que l'usage JOURNALIER
# (RPD/TPD), paraît très loin du plafond. On borne max_tokens sous ce budget pour
# qu'un appel ne puisse jamais dépasser la limite par minute à lui seul.
MODEL_TPM = {
    "llama-3.3-70b-versatile": 6_000,
    "llama-3.1-8b-instant": 30_000,
}
DEFAULT_TPM = 6_000
TPM_SAFETY = 0.92  # marge pour l'imprécision de l'estimation de tokens
MIN_MAX_TOKENS = 512  # plancher : on garde de quoi produire un JSON exploitable


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


def _estimate_prompt_tokens(messages: list) -> int:
    """Estimation grossière des tokens d'entrée (~4 caractères/token)."""
    chars = sum(len(str(m.get("content", ""))) for m in messages)
    return chars // 4 + 8 * len(messages)


def _budget(model: str) -> int:
    """Budget tokens/minute exploitable pour un appel (TPM du modèle × marge)."""
    return int(MODEL_TPM.get(model, DEFAULT_TPM) * TPM_SAFETY)


def _clamp_max_tokens(model: str, messages: list, max_tokens: int) -> int:
    """Borne max_tokens pour que (entrée + réservation) tienne sous le TPM du modèle.

    Évite le 429 instantané du palier gratuit : sans ce garde-fou, un guide long
    réserve plus que les 6 000 tokens/minute du modèle 70B et échoue dès le 1er appel.
    """
    allowed = _budget(model) - _estimate_prompt_tokens(messages)
    return max(MIN_MAX_TOKENS, min(max_tokens, allowed))


def _select_model(requested: str, messages: list, tried: set[str]) -> str:
    """Choisit un modèle dont le TPM peut accueillir l'entrée + un minimum de sortie.

    Le clamp sur max_tokens ne suffit pas quand l'ENTRÉE seule (gros guide à
    traduire/enrichir) dépasse déjà le budget tokens/minute : Groq renvoie alors un
    413 « Request too large ». On bascule donc vers le modèle au TPM le plus élevé
    capable de faire tenir la requête (le 8B à 30 000 TPM accueille de bien plus gros
    contenus que le 70B à 6 000). `tried` exclut les modèles déjà tentés sur 413.
    """
    candidates = dict(MODEL_TPM)
    candidates.setdefault(requested, MODEL_TPM.get(requested, DEFAULT_TPM))
    available = {m: tpm for m, tpm in candidates.items() if m not in tried}
    if not available:
        return requested

    needed = _estimate_prompt_tokens(messages) + MIN_MAX_TOKENS

    def fits(model: str) -> bool:
        return needed <= int(available[model] * TPM_SAFETY)

    # 1) le modèle demandé s'il fait tenir la requête (cas nominal : aucun changement)
    if requested in available and fits(requested):
        return requested
    # 2) sinon le TPM le plus élevé qui accueille l'entrée
    fitting = sorted((m for m in available if fits(m)), key=lambda m: available[m], reverse=True)
    if fitting:
        return fitting[0]
    # 3) aucun ne fait tenir l'entrée → le plus gros TPM disponible (meilleure chance)
    return max(available, key=lambda m: available[m])


def _retry_wait_seconds(error: Exception, attempt: int) -> float:
    text = str(error)
    match = re.search(r"try again in ([\d.]+)\s*s", text, re.I)
    if match:
        return float(match.group(1)) + 0.75
    return min(30.0, (2 ** attempt) + 1.0)


def is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "429" in text or "rate limit" in text or "too many requests" in text


def is_request_too_large_error(error: Exception) -> bool:
    """413 Groq : la requête (entrée + sortie réservée) dépasse le TPM du modèle.

    Groq renvoie un HTTP 413 de code `rate_limit_exceeded` — distinct du 429 cumulatif :
    ici c'est un SEUL appel qui est trop gros, pas le quota glissant qui est atteint.
    """
    text = str(error).lower()
    return (
        "413" in text
        or "request too large" in text
        or "request entity too large" in text
        or "too large for model" in text
    )


def friendly_error(error: Exception) -> str:
    if is_request_too_large_error(error):
        return (
            "Contenu trop volumineux pour la limite par minute (TPM) du modèle Groq : "
            "la requête (texte d'entrée + réponse réservée) dépasse à elle seule le budget "
            "tokens/minute, même après bascule automatique vers le modèle au TPM le plus élevé. "
            "Découpez le contenu (générez ou traduisez par sections plus courtes) ou augmentez "
            "votre palier sur console.groq.com/settings/limits."
        )
    if is_rate_limit_error(error):
        return (
            "Limite Groq par minute atteinte (TPM — tokens/minute). "
            "C'est une limite glissante par minute, indépendante de l'usage JOURNALIER "
            "affiché sur le dashboard (vous pouvez donc être « loin du plafond » et la "
            "déclencher quand même). Le palier gratuit du modèle 70B est à 6 000 tokens/min. "
            "Attendez 30–60 s puis réessayez ; voir console.groq.com/settings/limits."
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
    requested_model = model or main_model()

    def _build_kwargs(active_model: str) -> dict:
        kwargs: dict = {
            "model": active_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": _clamp_max_tokens(active_model, messages, max_tokens),
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return kwargs

    # Choix proactif : si l'entrée seule dépasse le TPM du modèle demandé, on part
    # directement sur un modèle au TPM plus élevé plutôt que d'essuyer un 413 certain.
    tried: set[str] = set()
    active_model = _select_model(requested_model, messages, tried)
    tried.add(active_model)

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**_build_kwargs(active_model))
        except Exception as exc:
            last_error = exc
            # 413 : ce modèle ne peut pas accueillir la requête. On tente le prochain
            # modèle à TPM plus élevé non encore essayé ; sinon on remonte l'erreur.
            if is_request_too_large_error(exc):
                fallback = _select_model(requested_model, messages, tried)
                current_tpm = MODEL_TPM.get(active_model, DEFAULT_TPM)
                if fallback not in tried and MODEL_TPM.get(fallback, DEFAULT_TPM) > current_tpm:
                    active_model = fallback
                    tried.add(active_model)
                    continue
                raise
            if is_rate_limit_error(exc) and attempt < max_retries - 1:
                time.sleep(_retry_wait_seconds(exc, attempt))
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("Appel Groq échoué")
