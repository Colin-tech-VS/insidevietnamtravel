"""Résolution pays depuis l'IP — cache mémoire, sans stocker l'IP en clair."""

from __future__ import annotations

import ipaddress
import threading
from typing import Optional

import requests

# Enregistrement par IP : (country_code, country_name, city, hosting, proxy).
_cache: dict[str, tuple[str, str, str, bool, bool]] = {}
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


def _lookup(ip: str = "") -> tuple[str, str, str, bool, bool]:
    """Résout (code, name, city, hosting, proxy) avec cache mémoire."""
    ip = (ip or "").strip()
    if not ip or not _is_public_ip(ip):
        return "", "", "", False, False

    with _cache_lock:
        cached = _cache.get(ip)
        if cached is not None:
            return cached

    code, name, city, hosting, proxy = "", "", "", False, False
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}",
            # hosting/proxy : champs gratuits qui révèlent datacenters & anonymiseurs
            # (le trafic « bot » qui passe le filtre user-agent vient de là).
            params={"fields": "status,country,countryCode,city,hosting,proxy"},
            timeout=2.5,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            code = (data.get("countryCode") or "").upper()[:2]
            name = (data.get("country") or "").strip()[:80]
            city = (data.get("city") or "").strip()[:80]
            hosting = bool(data.get("hosting"))
            proxy = bool(data.get("proxy"))
    except Exception:
        pass

    result = (code, name, city, hosting, proxy)
    with _cache_lock:
        _cache[ip] = result
        _trim_cache()
    return result


def resolve_location(ip: str = "") -> tuple[str, str, str]:
    """Retourne (country_code, country_name, city) — chaînes vides si inconnu."""
    code, name, city, _hosting, _proxy = _lookup(ip)
    return code, name, city


def resolve_country(ip: str = "") -> tuple[str, str]:
    """Retourne (country_code, country_name) — chaînes vides si inconnu."""
    code, name, _city, _hosting, _proxy = _lookup(ip)
    return code, name


def is_bot_network(ip: str = "") -> bool:
    """True si l'IP appartient à un datacenter (hosting) ou un proxy/VPN/Tor.

    Un blog voyage grand public ne reçoit pas de vrais lecteurs depuis ces réseaux :
    c'est du trafic automatisé (scanners, scrapers) qui usurpe un user-agent de
    navigateur et échappe donc au filtre user-agent. On l'exclut des analytics.
    En cas d'IP privée/inconnue ou d'échec réseau, renvoie False (ne bloque jamais
    un visiteur par défaut).
    """
    _code, _name, _city, hosting, proxy = _lookup(ip)
    return hosting or proxy


def city_label(city: str = "", code: str = "", name: str = "") -> str:
    """Libellé affichable : « Paris · FR » ou « Paris, France »."""
    city = (city or "").strip()
    code = (code or "").upper()
    name = (name or "").strip()
    if city and code:
        return f"{city} · {code}"
    if city and name:
        return f"{city}, {name}"
    if city:
        return city
    return country_label(code, name)


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
