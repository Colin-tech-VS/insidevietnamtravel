"""Vérification dynamique des IDs et liens affiliés (admin)."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse

from data.affiliate_urls import LOCATION_META

# id_key → paramètre de tracking attendu dans l'URL générée
_TRACKING = {
    "booking_aid": ("aid", r"^\d{4,10}$"),
    "agoda_cid": ("cid", r"^\d{3,12}$"),
    "gyg_partner_id": ("partner_id", r"^[A-Za-z0-9]{4,20}$"),
    "viator_pid": ("pid", r"^[A-Za-z0-9]{4,20}$"),
    "airalo_ref": ("ref", None),
    "holafly_ref": ("ref", None),
    "worldnomads_affiliate": ("affiliate", None),
}

_EXTRACT = {
    "booking_aid": [r"[?&]aid=(\d+)", r"aid[=:](\d+)"],
    "agoda_cid": [r"[?&]cid=(\d+)", r"cid[=:](\d+)"],
    "gyg_partner_id": [r"[?&]partner_id=([^&\s]+)", r"partner_id[=:]([A-Za-z0-9]+)"],
    "viator_pid": [r"[?&]pid=([^&\s]+)", r"[?&]mcid=([^&\s]+)"],
    "airalo_ref": [r"[?&]ref=([^&\s]+)"],
    "holafly_ref": [r"[?&]ref=([^&\s]+)"],
    "worldnomads_affiliate": [r"[?&]affiliate=([^&\s]+)"],
}


def normalize_affiliate_input(id_key: str, raw: str) -> str:
    """Extrait l'ID depuis une URL collée ou renvoie la valeur nettoyée."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if id_key == "pdf_checkout_url":
        return raw

    lowered = raw.lower()
    if lowered.startswith("http") or "?" in raw or "gyg.me/" in lowered:
        for pattern in _EXTRACT.get(id_key, []):
            match = re.search(pattern, raw, re.I)
            if match:
                return match.group(1).strip()
        if id_key == "gyg_partner_id" and "gyg.me/" in lowered:
            return raw  # lien court — pas d'extraction possible
    return raw


def _sample_url(id_key: str, value: str) -> str:
    loc = LOCATION_META["hanoi"]
    if id_key == "booking_aid":
        q = urlencode({"ss": loc["booking_city"], "aid": value, "lang": "fr"})
        return f"https://www.booking.com/searchresults.html?{q}"
    if id_key == "agoda_cid":
        q = urlencode({"city": loc["agoda_city_id"], "cid": value, "locale": "fr-fr"})
        return f"https://www.agoda.com/search?{q}"
    if id_key == "gyg_partner_id":
        q = urlencode({"q": "Hanoi street food tour Vietnam", "partner_id": value})
        return f"https://www.getyourguide.com/{loc['gyg_location']}/?{q}"
    if id_key == "viator_pid":
        q = urlencode({"text": "Hanoi food tour Vietnam", "pid": value, "mcid": value, "destId": loc["viator_dest"]})
        return f"https://www.viator.com/searchResults/all?{q}"
    if id_key == "airalo_ref":
        return f"https://www.airalo.com/vietnam-esim?ref={value}"
    if id_key == "holafly_ref":
        return f"https://esim.holafly.com/data-plans/vietnam/?ref={value}"
    if id_key == "worldnomads_affiliate":
        q = urlencode({"affiliate": value, "destination": "Vietnam"})
        return f"https://www.worldnomads.com/travel-insurance/?{q}"
    if id_key == "pdf_checkout_url":
        return value if value.startswith("http") else "#pdf-guide"
    return ""


def _param_in_url(url: str, param: str, expected: str) -> bool:
    if not url or not expected:
        return False
    if url.startswith("#"):
        return True
    parsed = urlparse(url)
    values = parse_qs(parsed.query).get(param, [])
    return expected in values


def verify_affiliate_id(id_key: str, raw_value: str) -> dict:
    """
    Vérifie un ID affilié : extraction, format, présence dans un lien exemple.
    status: ok | warn | error
    """
    normalized = normalize_affiliate_input(id_key, raw_value)
    name = id_key.replace("_", " ")

    if not normalized:
        return {
            "status": "error",
            "message": "ID vide — les liens du site ne seront pas affiliés.",
            "normalized": "",
            "sample_url": "",
            "param": "",
            "param_found": False,
        }

    if id_key == "pdf_checkout_url":
        if normalized.startswith("#"):
            return {
                "status": "ok",
                "message": "Paiement Stripe interne (#pdf-guide).",
                "normalized": normalized,
                "sample_url": normalized,
                "param": "",
                "param_found": True,
            }
        if normalized.startswith("http"):
            return {
                "status": "ok",
                "message": "URL de paiement externe détectée.",
                "normalized": normalized,
                "sample_url": normalized,
                "param": "url",
                "param_found": True,
            }
        return {
            "status": "error",
            "message": "URL invalide — commencez par https:// ou utilisez #pdf-guide.",
            "normalized": normalized,
            "sample_url": "",
            "param": "",
            "param_found": False,
        }

    if "PLACEHOLDER" in normalized.upper():
        return {
            "status": "error",
            "message": "ID placeholder — remplacez par votre vrai identifiant partenaire.",
            "normalized": normalized,
            "sample_url": "",
            "param": _TRACKING.get(id_key, ("", None))[0],
            "param_found": False,
        }

    if id_key == "gyg_partner_id" and normalized.lower().startswith("http"):
        return {
            "status": "warn",
            "message": "Lien gyg.me ou URL sans partner_id — collez l'ID seul (ex. NHP1RKO) ou une URL avec ?partner_id=.",
            "normalized": normalized,
            "sample_url": "",
            "param": "partner_id",
            "param_found": False,
        }

    param, pattern = _TRACKING.get(id_key, ("", None))
    sample = _sample_url(id_key, normalized)
    found = _param_in_url(sample, param, normalized)

    if pattern and not re.match(pattern, normalized):
        return {
            "status": "warn",
            "message": f"Format inhabituel pour {param} — vérifiez que l'ID est correct.",
            "normalized": normalized,
            "sample_url": sample,
            "param": param,
            "param_found": found,
        }

    if not found:
        return {
            "status": "error",
            "message": f"Le paramètre {param}=… est absent du lien généré.",
            "normalized": normalized,
            "sample_url": sample,
            "param": param,
            "param_found": False,
        }

    extracted_note = ""
    if raw_value.strip() != normalized:
        extracted_note = f" ID extrait : {normalized}."

    return {
        "status": "ok",
        "message": f"Tracking {param}={normalized} présent dans le lien exemple.{extracted_note}",
        "normalized": normalized,
        "sample_url": sample,
        "param": param,
        "param_found": True,
    }


def verify_all_partners(ids: dict) -> dict[str, dict]:
    """Vérifie tous les partenaires intégrés à partir des IDs enregistrés."""
    from data.affiliate_partners import BUILTIN_PARTNERS

    out = {}
    for p in BUILTIN_PARTNERS:
        key = p["id_key"]
        out[p["id"]] = verify_affiliate_id(key, ids.get(key, ""))
    return out
