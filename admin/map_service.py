"""Carte interactive (Leaflet/OSM) — points géolocalisés + liens affiliés."""

from __future__ import annotations

import re
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Callable

import config
import requests

# Villes admin → slug destination publiée (si page existe).
CITY_VALUE_TO_SLUG: dict[str, str] = {
    "Hanoï": "hanoi",
    "Ho Chi Minh-Ville": "ho-chi-minh-city",
    "Hội An": "hoi-an",
    "Đà Nẵng": "da-nang",
    "Ha Long / Quảng Ninh": "halong",
    "Sapa / Lào Cai": "sapa",
    "Huế": "hue",
    "Phú Quốc": "phu-quoc",
    "Mỹ Tho / Delta Mekong": "delta-du-mekong",
}

KIND_LABELS = {
    "hotel": {"fr": "Hôtel", "en": "Hotel"},
    "activity": {"fr": "Activité", "en": "Activity"},
    "food": {"fr": "Resto / bar", "en": "Food & drink"},
    "poi": {"fr": "À voir", "en": "Sights"},
}

PROVIDER_LABELS = {
    "booking": "Booking",
    "agoda": "Agoda",
    "getyourguide": "GetYourGuide",
    "viator": "Viator",
    "custom": "Lien perso",
}

_last_geocode_ts = 0.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text.lower().strip())


def _default_store() -> dict:
    return {"points": [], "pending": []}


def get_map_store() -> dict:
    from admin.kv_store import get_json, set_json

    stored = get_json("map_points", None, file_name="map_points.json")
    if stored is None:
        set_json("map_points", _default_store(), file_name="map_points.json")
        return _default_store()
    if "points" not in stored:
        stored = {**_default_store(), **stored}
    if "pending" not in stored:
        stored["pending"] = []
    return stored


def save_map_store(data: dict) -> None:
    from admin.kv_store import set_json

    set_json("map_points", data, file_name="map_points.json")


def published_destination_slugs() -> list[str]:
    from admin.store import get_destinations_dict

    return list(get_destinations_dict().keys())


def destination_options() -> list[dict]:
    from admin.store import get_destinations_dict

    dests = get_destinations_dict()
    return [
        {"slug": slug, "name": d.get("name", slug)}
        for slug, d in sorted(dests.items(), key=lambda x: x[1].get("name", ""))
    ]


def resolve_destination_slug(city_or_slug: str) -> str | None:
    """Associe une ville (admin) ou un slug à une page destination publiée."""
    raw = (city_or_slug or "").strip()
    if not raw:
        return None

    dests = get_destinations_dict_safe()
    if raw in dests:
        return raw

    norm = _normalize(raw)
    for slug, d in dests.items():
        if _normalize(slug) == norm or _normalize(d.get("name", "")) == norm:
            return slug

    if raw in CITY_VALUE_TO_SLUG:
        slug = CITY_VALUE_TO_SLUG[raw]
        return slug if slug in dests else None

    for city_label, slug in CITY_VALUE_TO_SLUG.items():
        if _normalize(city_label) == norm and slug in dests:
            return slug

    return None


def get_destinations_dict_safe() -> dict:
    from admin.store import get_destinations_dict

    return get_destinations_dict()


def geocode_address(address: str, *, context: str = "Vietnam") -> dict:
    """Géocode une adresse via Nominatim (gratuit)."""
    global _last_geocode_ts

    address = (address or "").strip()
    if len(address) < 4:
        raise ValueError("Adresse trop courte.")

    query = address if "vietnam" in address.lower() else f"{address}, Vietnam"
    wait = max(0.0, 1.1 - (time.time() - _last_geocode_ts))
    if wait > 0:
        time.sleep(wait)

    headers = {
        "User-Agent": f"{config.SITE_NAME}/1.0 ({config.LEGAL_CONTACT_EMAIL})",
        "Accept-Language": "fr,en",
    }
    resp = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 1, "countrycodes": "vn"},
        headers=headers,
        timeout=20,
    )
    _last_geocode_ts = time.time()
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        raise ValueError(f"Adresse introuvable : {address}")

    row = rows[0]
    return {
        "lat": float(row["lat"]),
        "lng": float(row["lon"]),
        "display_name": row.get("display_name", address),
    }


def build_point_affiliate_url(point: dict, track_url_fn: Callable[[str, str], str]) -> str:
    from data.affiliate_urls import build_activity_link, build_hotel_link, get_location_meta

    provider = (point.get("affiliate_provider") or "").strip()
    custom = (point.get("affiliate_url") or "").strip()
    if provider == "custom" and custom.startswith("http"):
        return track_url_fn("custom", custom)

    slug = point.get("destination_slug") or ""
    loc = get_location_meta(slug, name=point.get("destination_name"))

    if provider in ("booking", "agoda"):
        hotel = {
            "name": point.get("affiliate_search") or point.get("title", ""),
            "search": point.get("affiliate_search") or point.get("title", ""),
        }
        target = build_hotel_link(provider, hotel, loc)
        return track_url_fn(provider, target)

    if provider in ("getyourguide", "viator"):
        activity = {
            "name": point.get("affiliate_search") or point.get("title", ""),
            "search": point.get("affiliate_search") or point.get("title", ""),
        }
        target = build_activity_link(provider, activity, loc)
        return track_url_fn(provider, target)

    return ""


def serialize_point_for_public(point: dict, lang: str, track_url_fn: Callable[[str, str], str]) -> dict:
    kind = point.get("kind") or "poi"
    provider = point.get("affiliate_provider") or ""
    affiliate_url = build_point_affiliate_url(point, track_url_fn)
    return {
        "id": point.get("id"),
        "title": point.get("title", ""),
        "desc": point.get("desc", ""),
        "address": point.get("address", ""),
        "lat": point.get("lat"),
        "lng": point.get("lng"),
        "kind": kind,
        "kind_label": KIND_LABELS.get(kind, {}).get(lang, kind),
        "price_hint": point.get("price_hint", ""),
        "provider": provider,
        "provider_label": PROVIDER_LABELS.get(provider, provider),
        "affiliate_url": affiliate_url,
        "affiliate_cta": _affiliate_cta(provider, lang),
    }


def _affiliate_cta(provider: str, lang: str) -> str:
    if lang == "en":
        mapping = {
            "booking": "View on Booking",
            "agoda": "View on Agoda",
            "getyourguide": "Book on GetYourGuide",
            "viator": "Book on Viator",
            "custom": "Book / visit",
        }
        return mapping.get(provider, "Learn more")
    mapping = {
        "booking": "Voir sur Booking",
        "agoda": "Voir sur Agoda",
        "getyourguide": "Réserver sur GetYourGuide",
        "viator": "Réserver sur Viator",
        "custom": "Réserver / visiter",
    }
    return mapping.get(provider, "En savoir plus")


def get_public_map_points(destination_slug: str, lang: str, track_url_fn) -> list[dict]:
    store = get_map_store()
    out = []
    for p in store.get("points", []):
        if p.get("destination_slug") != destination_slug:
            continue
        if p.get("lat") is None or p.get("lng") is None:
            continue
        out.append(serialize_point_for_public(p, lang, track_url_fn))
    return out


def add_map_point(form: dict) -> dict:
    """Ajoute un point publié ou en attente selon la destination."""
    title = (form.get("title") or "").strip()
    address = (form.get("address") or "").strip()
    city = (form.get("city") or form.get("destination_slug") or "").strip()
    kind = (form.get("kind") or "poi").strip()
    provider = (form.get("affiliate_provider") or "custom").strip()
    affiliate_search = (form.get("affiliate_search") or title).strip()
    affiliate_url = (form.get("affiliate_url") or "").strip()
    desc = (form.get("desc") or "").strip()
    price_hint = (form.get("price_hint") or "").strip()

    if not title:
        raise ValueError("Titre obligatoire.")
    if not address:
        raise ValueError("Adresse obligatoire.")
    if kind not in KIND_LABELS:
        raise ValueError("Type de point invalide.")

    geo = geocode_address(address)
    slug = resolve_destination_slug(city)

    point = {
        "id": str(uuid.uuid4()),
        "title": title,
        "address": address,
        "display_name": geo.get("display_name", address),
        "lat": geo["lat"],
        "lng": geo["lng"],
        "kind": kind,
        "desc": desc,
        "price_hint": price_hint,
        "affiliate_provider": provider,
        "affiliate_search": affiliate_search,
        "affiliate_url": affiliate_url,
        "source": "manual",
        "created_at": _now_iso(),
    }

    store = get_map_store()
    if slug:
        dests = get_destinations_dict_safe()
        point["destination_slug"] = slug
        point["destination_name"] = dests[slug].get("name", slug)
        store.setdefault("points", []).append(point)
        save_map_store(store)
        return {"status": "published", "point": point, "slug": slug}

    point["requested_city"] = city or "(non précisée)"
    point["pending_reason"] = "destination_not_published"
    store.setdefault("pending", []).append(point)
    save_map_store(store)
    return {
        "status": "pending",
        "point": point,
        "message": (
            f"« {city or 'Ville inconnue'} » n'a pas encore de page destination — "
            "le point est en attente."
        ),
    }


def delete_map_point(point_id: str, *, pending: bool = False) -> bool:
    store = get_map_store()
    key = "pending" if pending else "points"
    items = store.get(key, [])
    new_items = [p for p in items if p.get("id") != point_id]
    if len(new_items) == len(items):
        return False
    store[key] = new_items
    save_map_store(store)
    return True


def publish_pending_point(point_id: str, destination_slug: str) -> bool:
    store = get_map_store()
    pending = store.get("pending", [])
    point = next((p for p in pending if p.get("id") == point_id), None)
    if not point:
        return False

    slug = resolve_destination_slug(destination_slug)
    if not slug:
        raise ValueError("Destination invalide — choisissez une ville publiée.")

    dests = get_destinations_dict_safe()
    point = {k: v for k, v in point.items() if not k.startswith("pending") and k != "requested_city"}
    point["destination_slug"] = slug
    point["destination_name"] = dests[slug].get("name", slug)
    store["pending"] = [p for p in pending if p.get("id") != point_id]
    store.setdefault("points", []).append(point)
    save_map_store(store)
    return True


def sync_from_destinations(*, replace: bool = False) -> dict:
    """Importe hôtels & activités des pages destination (géocodage Nominatim)."""
    from admin.store import get_destinations_dict

    dests = get_destinations_dict()
    store = get_map_store()
    if replace:
        store["points"] = [p for p in store.get("points", []) if p.get("source") != "destination_sync"]
    else:
        existing = {
            (p.get("destination_slug"), p.get("title"), p.get("kind"))
            for p in store.get("points", [])
        }

    added = 0
    errors: list[str] = []

    for slug, dest in dests.items():
        city_label = dest.get("name", slug)
        items: list[tuple[str, dict]] = []
        for h in dest.get("hotels") or []:
            items.append(("hotel", h))
        for a in dest.get("activities") or []:
            items.append(("activity", a))

        for kind, item in items:
            title = item.get("name", "").strip()
            if not title:
                continue
            key = (slug, title, kind)
            if not replace and key in existing:
                continue
            address_query = f"{title}, {city_label}, Vietnam"
            try:
                geo = geocode_address(address_query, context=city_label)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{city_label} — {title}: {exc}")
                continue

            point = {
                "id": str(uuid.uuid4()),
                "destination_slug": slug,
                "destination_name": city_label,
                "title": title,
                "address": address_query,
                "display_name": geo.get("display_name", address_query),
                "lat": geo["lat"],
                "lng": geo["lng"],
                "kind": kind,
                "desc": item.get("desc", ""),
                "price_hint": item.get("price_hint", ""),
                "affiliate_provider": item.get("provider", "booking"),
                "affiliate_search": item.get("search", title),
                "affiliate_url": "",
                "source": "destination_sync",
                "created_at": _now_iso(),
            }
            store.setdefault("points", []).append(point)
            existing.add(key)
            added += 1

    save_map_store(store)
    return {"added": added, "errors": errors[:12], "error_count": len(errors)}
