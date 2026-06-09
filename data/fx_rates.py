"""Taux de change EUR/USD → VND pour le calculateur budget (cache serveur)."""

from __future__ import annotations

import time
from typing import Any

import requests

_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}
_CACHE_TTL = 3600  # 1 h

# Repli si l'API est indisponible (taux indicatifs).
FALLBACK = {
    "base": "EUR",
    "EUR": 1.0,
    "USD": 1.08,
    "VND": 27_500.0,
    "USD_VND": 25_400.0,
    "source": "fallback",
    "updated_at": None,
}


def get_fx_rates() -> dict:
    """Retourne EUR→USD, EUR→VND et USD→VND avec cache."""
    now = time.time()
    if _CACHE["data"] and now - _CACHE["ts"] < _CACHE_TTL:
        return _CACHE["data"]

    data = _fetch_live_rates() or dict(FALLBACK)
    data.setdefault("base", "EUR")
    data.setdefault("EUR", 1.0)
    if not data.get("VND"):
        data["VND"] = FALLBACK["VND"]
    if not data.get("USD"):
        data["USD"] = FALLBACK["USD"]
    if not data.get("USD_VND"):
        data["USD_VND"] = round(data["VND"] / data["USD"], 2) if data["USD"] else FALLBACK["USD_VND"]

    _CACHE["ts"] = now
    _CACHE["data"] = data
    return data


def _fetch_live_rates() -> dict | None:
    try:
        r = requests.get(
            "https://open.er-api.com/v6/latest/EUR",
            timeout=8,
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        payload = r.json()
        if payload.get("result") != "success":
            return None
        rates = payload.get("rates") or {}
        vnd = float(rates.get("VND") or 0)
        usd = float(rates.get("USD") or 0)
        if vnd <= 0 or usd <= 0:
            return None
        return {
            "base": "EUR",
            "EUR": 1.0,
            "USD": round(usd, 4),
            "VND": round(vnd, 2),
            "USD_VND": round(vnd / usd, 2),
            "source": "open.er-api.com",
            "updated_at": payload.get("time_last_update_utc"),
        }
    except Exception:
        return None
