"""Résolution pays depuis l'IP — cache mémoire, sans stocker l'IP en clair."""

from __future__ import annotations

import ipaddress
import threading
from typing import Optional

import requests

_cache: dict[str, tuple[str, str]] = {}
_cache_lock = threading.Lock()
_MAX_CACHE = 4000


def _is_public_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def _trim_cache() -> None:
    if len(_cache) <= _MAX_CACHE:
        return
    for key in list(_cache.keys())[: len(_cache) - _MAX_CACHE]:
        _cache.pop(key, None)


def resolve_country(ip: str = "") -> tuple[str, str]:
    """Retourne (country_code, country_name) — chaînes vides si inconnu."""
    ip = (ip or "").strip()
    if not ip or not _is_public_ip(ip):
        return "", ""

    with _cache_lock:
        cached = _cache.get(ip)
        if cached is not None:
            return cached

    code, name = "", ""
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,country,countryCode"},
            timeout=2.5,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            code = (data.get("countryCode") or "").upper()[:2]
            name = (data.get("country") or "").strip()[:80]
    except Exception:
        pass

    result = (code, name)
    with _cache_lock:
        _cache[ip] = result
        _trim_cache()
    return result


def country_label(code: str = "", name: str = "") -> str:
    code = (code or "").upper()
    name = (name or "").strip()
    if code and name:
        return f"{code} · {name}"
    if code:
        return code
    if name:
        return name
    return "Inconnu"
