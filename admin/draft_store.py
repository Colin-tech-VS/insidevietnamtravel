"""Stockage serveur des brouillons admin + génération IA en tâche de fond.

Pourquoi :
- Le cookie de session Flask (signé) est limité à ~4 Ko par le navigateur ; un guide
  bilingue complet (1000-1800 mots × 2 langues) le dépasse largement → le brouillon
  ne survivait pas au rechargement de page.
- Le routeur de la plateforme (Scalingo) coupe les requêtes HTTP trop longues
  (~60 s). Or une génération = plusieurs appels Groq (rédaction + enrichissement +
  traduction EN) + image. En synchrone, le navigateur recevait « Failed to fetch ».

Solution : la génération tourne dans un thread démon hors du cycle requête/réponse.
Le navigateur lance le job, reçoit aussitôt un accusé, puis interroge un endpoint de
statut. Une fois asynchrone, les pauses anti rate-limit de Groq n'échouent plus :
elles attendent simplement sans bloquer de requête HTTP.

Note : store en mémoire process. Le Procfile tourne avec `--workers 1 --preload`
(un seul process), donc les threads partagent ce dict. Un brouillon est rattaché à
la session via un petit token (seul le token transite dans le cookie).
"""

from __future__ import annotations

import secrets
import threading
import time
from typing import Callable

from admin.genlog import log

_LOCK = threading.Lock()
_STORE: dict[str, dict] = {}
_TTL_SECONDS = 3600  # un brouillon expire au bout d'1 h


def _prune_locked() -> None:
    now = time.time()
    stale = [k for k, v in _STORE.items() if now - v.get("ts", now) > _TTL_SECONDS]
    for k in stale:
        _STORE.pop(k, None)


def new_token() -> str:
    return secrets.token_urlsafe(16)


def set_draft(token: str, draft: dict) -> None:
    """Stocke un brouillon prêt (création manuelle ou résultat synchrone)."""
    with _LOCK:
        _prune_locked()
        _STORE[token] = {"status": "done", "draft": draft, "error": "", "phase": "", "ts": time.time()}


def set_phase(token: str | None, phase: str) -> None:
    """Met à jour l'étape EN COURS d'un job (affichée en direct dans le modal IA).

    Permet au front d'afficher ce que l'IA fait réellement (rédaction → enrichissement
    → traduction → image) au lieu de phrases qui défilent au hasard sur un minuteur.
    """
    if not token:
        return
    log(f"PHASE [{token[:6]}] {phase}")
    with _LOCK:
        entry = _STORE.get(token)
        if entry and entry.get("status") == "running":
            entry["phase"] = phase


def get_draft(token: str | None) -> dict | None:
    if not token:
        return None
    with _LOCK:
        entry = _STORE.get(token)
        if entry and entry.get("status") == "done":
            return entry.get("draft")
    return None


def patch_draft(token: str | None, patch: dict) -> None:
    """Fusionne des champs dans un brouillon terminé (ex. image IA en arrière-plan)."""
    if not token or not patch:
        return
    with _LOCK:
        entry = _STORE.get(token)
        if entry and entry.get("status") == "done" and isinstance(entry.get("draft"), dict):
            entry["draft"].update(patch)
            entry["ts"] = time.time()


def clear(token: str | None) -> None:
    if not token:
        return
    with _LOCK:
        _STORE.pop(token, None)


def status(token: str | None) -> dict:
    """Renvoie {status, error, phase}. status ∈ running|done|error|missing."""
    if not token:
        return {"status": "missing", "error": "", "phase": ""}
    with _LOCK:
        entry = _STORE.get(token)
        if not entry:
            return {"status": "missing", "error": "", "phase": ""}
        out = {
            "status": entry.get("status", "missing"),
            "error": entry.get("error", ""),
            "phase": entry.get("phase", ""),
        }
        draft = entry.get("draft")
        if entry.get("status") == "done" and isinstance(draft, dict) and draft.get("message"):
            out["result"] = draft
        return out


def start_job(
    token: str,
    fn: Callable[..., dict],
    friendly_error: Callable[[Exception], str] | None = None,
    initial_phase: str = "",
) -> None:
    """Exécute fn(report) dans un thread démon ; stocke le brouillon ou l'erreur.

    `fn` reçoit un callback `report(phase: str)` pour signaler son étape en cours,
    relayée telle quelle au front via status().
    """
    with _LOCK:
        _prune_locked()
        _STORE[token] = {
            "status": "running",
            "draft": None,
            "error": "",
            "phase": initial_phase,
            "ts": time.time(),
        }

    def report(phase: str) -> None:
        set_phase(token, phase)

    def _run() -> None:
        t0 = time.time()
        log(f"JOB  [{token[:6]}] START")
        try:
            draft = fn(report)
            with _LOCK:
                _STORE[token] = {
                    "status": "done",
                    "draft": draft,
                    "error": "",
                    "ts": time.time(),
                }
            log(f"JOB  [{token[:6]}] DONE en {time.time() - t0:.1f}s")
        except Exception as exc:  # noqa: BLE001 — on remonte le message à l'UI
            message = friendly_error(exc) if friendly_error else str(exc)
            log(
                f"JOB  [{token[:6]}] ERROR apres {time.time() - t0:.1f}s -- "
                f"{type(exc).__name__}: {str(exc)[:200]}"
            )
            with _LOCK:
                _STORE[token] = {
                    "status": "error",
                    "draft": None,
                    "error": message or "Échec de la génération.",
                    "ts": time.time(),
                }

    threading.Thread(target=_run, daemon=True).start()
