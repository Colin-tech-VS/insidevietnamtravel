"""Carte interactive (Leaflet/OSM) — points géolocalisés + liens affiliés."""

from __future__ import annotations

import hashlib
import math
import re
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Callable, Iterator

import config
import requests

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
    "service": {"fr": "Service voyage", "en": "Travel service"},
}

PROVIDER_LABELS = {
    "booking": "Booking",
    "agoda": "Agoda",
    "getyourguide": "GetYourGuide",
    "viator": "Viator",
    "esim_airalo": "Airalo",
    "esim_holafly": "Holafly",
    "travel_insurance": "World Nomads",
    "custom": "Partenaire",
}

AUTO_SOURCES = frozenset({"destination_sync", "affiliate_auto"})
_last_geocode_ts = 0.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text.lower().strip())


def _default_store() -> dict:
    return {"points": [], "pending": [], "meta": {"city_coords": {}}}


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
    if "meta" not in stored:
        stored["meta"] = {"city_coords": {}}
    return stored


def save_map_store(data: dict) -> None:
    from admin.kv_store import set_json

    set_json("map_points", data, file_name="map_points.json")
    try:
        from admin import chat_service
        chat_service.invalidate_cache()
    except Exception:
        pass


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


def _city_center(store: dict, slug: str, city_label: str) -> dict:
    cached = store.get("meta", {}).get("city_coords", {}).get(slug)
    if cached:
        return cached
    from data.affiliate_urls import LOCATION_META

    meta = LOCATION_META.get(slug, {})
    query = meta.get("booking_city") or f"{city_label}, Vietnam"
    geo = geocode_address(query)
    store.setdefault("meta", {}).setdefault("city_coords", {})[slug] = {
        "lat": geo["lat"],
        "lng": geo["lng"],
    }
    return store["meta"]["city_coords"][slug]


def _spread_coords(center: dict, ref: str) -> tuple[float, float]:
    """Décale légèrement les pins autour du centre-ville pour éviter la superposition."""
    digest = hashlib.md5(ref.encode("utf-8")).hexdigest()
    h1 = int(digest[:8], 16) / 0xFFFFFFFF
    h2 = int(digest[8:16], 16) / 0xFFFFFFFF
    angle = h1 * 2 * math.pi
    radius = 0.004 + h2 * 0.012
    lat = center["lat"] + radius * math.cos(angle) * 0.9
    lng = center["lng"] + radius * math.sin(angle) * 1.0
    return lat, lng


def _point_fingerprint(slug: str, ref: str) -> str:
    return f"{slug}:{ref}"


def _existing_fingerprints(store: dict) -> set[str]:
    fps: set[str] = set()
    for p in store.get("points", []):
        fp = p.get("fingerprint")
        if fp:
            fps.add(fp)
    return fps


def iter_destination_affiliate_items(slug: str, dest: dict, lang: str = "fr") -> Iterator[dict]:
    city = dest.get("name", slug)
    is_en = lang == "en"

    for hotel in dest.get("hotels") or []:
        provider = (hotel.get("provider") or "").strip()
        name = (hotel.get("name") or "").strip()
        if not provider or not name:
            continue
        yield {
            "ref": f"hotel:{name}",
            "title": name,
            "kind": "hotel",
            "desc": hotel.get("desc", ""),
            "price_hint": hotel.get("price_hint", ""),
            "affiliate_provider": provider,
            "affiliate_search": hotel.get("search", name),
            "affiliate_link_type": "hotel",
        }

    for act in dest.get("activities") or []:
        provider = (act.get("provider") or "").strip()
        name = (act.get("name") or "").strip()
        if not provider or not name:
            continue
        yield {
            "ref": f"activity:{name}",
            "title": name,
            "kind": "activity",
            "desc": act.get("desc", ""),
            "price_hint": act.get("price_hint", ""),
            "affiliate_provider": provider,
            "affiliate_search": act.get("search", name),
            "affiliate_link_type": "activity",
        }

    city_hotel_title = f"Hotels in {city} (Booking)" if is_en else f"Hôtels à {city} (Booking)"
    city_act_title = f"Activities in {city} (GetYourGuide)" if is_en else f"Activités à {city} (GetYourGuide)"
    city_viator_title = f"Tours in {city} (Viator)" if is_en else f"Tours à {city} (Viator)"
    city_agoda_title = f"Hotels in {city} (Agoda)" if is_en else f"Hôtels à {city} (Agoda)"

    yield {
        "ref": "city:booking",
        "title": city_hotel_title,
        "kind": "hotel",
        "desc": city_hotel_title,
        "price_hint": "",
        "affiliate_provider": "booking",
        "affiliate_search": "",
        "affiliate_link_type": "city_booking",
    }
    yield {
        "ref": "city:agoda",
        "title": city_agoda_title,
        "kind": "hotel",
        "desc": city_agoda_title,
        "price_hint": "",
        "affiliate_provider": "agoda",
        "affiliate_search": "",
        "affiliate_link_type": "city_agoda",
    }
    yield {
        "ref": "city:gyg",
        "title": city_act_title,
        "kind": "activity",
        "desc": city_act_title,
        "price_hint": "",
        "affiliate_provider": "getyourguide",
        "affiliate_search": f"{city} things to do",
        "affiliate_link_type": "city_gyg",
    }
    yield {
        "ref": "city:viator",
        "title": city_viator_title,
        "kind": "activity",
        "desc": city_viator_title,
        "price_hint": "",
        "affiliate_provider": "viator",
        "affiliate_search": f"{city} tours",
        "affiliate_link_type": "city_viator",
    }


def iter_global_affiliate_items() -> Iterator[dict]:
    from data.affiliate_urls import esim_airalo, esim_holafly, travel_insurance

    globals_list = [
        ("global:esim_airalo", "eSIM Airalo Vietnam", "esim_airalo", esim_airalo()),
        ("global:esim_holafly", "eSIM Holafly Vietnam", "esim_holafly", esim_holafly()),
        ("global:insurance", "Assurance voyage Vietnam", "travel_insurance", travel_insurance()),
    ]
    for ref, title, provider, url in globals_list:
        if not url or url.startswith("#"):
            continue
        yield {
            "ref": ref,
            "title": title,
            "kind": "service",
            "desc": title,
            "price_hint": "",
            "affiliate_provider": provider,
            "affiliate_url": url,
            "affiliate_link_type": "global",
            "destination_slug": "hanoi",
            "destination_name": "Vietnam",
        }


def iter_custom_partner_items() -> Iterator[dict]:
    from admin.store import get_custom_partners

    for partner in get_custom_partners():
        url = (partner.get("affiliate_url") or "").strip()
        name = (partner.get("name") or partner.get("id") or "").strip()
        if not url.startswith("http") or not name:
            continue
        slug = resolve_destination_slug(partner.get("city", "") or partner.get("destination_slug", ""))
        yield {
            "ref": f"partner:{partner.get('id', name)}",
            "title": name,
            "kind": "activity",
            "desc": name,
            "price_hint": "",
            "affiliate_provider": partner.get("id", "custom"),
            "affiliate_url": url,
            "affiliate_link_type": "global",
            "destination_slug": slug or "",
            "destination_name": partner.get("city", "") or "",
            "pending_if_no_slug": not bool(slug),
        }


def _make_auto_point(
    store: dict,
    *,
    slug: str,
    city_label: str,
    item: dict,
    source: str = "affiliate_auto",
) -> dict | None:
    ref = item["ref"]
    fp = _point_fingerprint(slug, ref)
    center = _city_center(store, slug, city_label)
    lat, lng = _spread_coords(center, fp)
    return {
        "id": str(uuid.uuid4()),
        "fingerprint": fp,
        "destination_slug": slug,
        "destination_name": city_label,
        "title": item["title"],
        "address": f"{city_label}, Vietnam",
        "display_name": city_label,
        "lat": lat,
        "lng": lng,
        "kind": item.get("kind", "poi"),
        "desc": item.get("desc", ""),
        "price_hint": item.get("price_hint", ""),
        "affiliate_provider": item.get("affiliate_provider", "custom"),
        "affiliate_search": item.get("affiliate_search", item["title"]),
        "affiliate_url": item.get("affiliate_url", ""),
        "affiliate_link_type": item.get("affiliate_link_type", "hotel"),
        "source": source,
        "created_at": _now_iso(),
    }


def sync_destination_affiliates(slug: str) -> dict:
    """Synchronise tous les liens affiliés d'une destination sur la carte."""
    dests = get_destinations_dict_safe()
    dest = dests.get(slug)
    if not dest:
        return {"added": 0, "slug": slug}

    store = get_map_store()
    existing = _existing_fingerprints(store)
    city_label = dest.get("name", slug)
    added = 0

    store["points"] = [
        p for p in store.get("points", [])
        if not (p.get("destination_slug") == slug and p.get("source") in AUTO_SOURCES)
    ]
    existing = _existing_fingerprints(store)

    for item in iter_destination_affiliate_items(slug, dest):
        fp = _point_fingerprint(slug, item["ref"])
        point = _make_auto_point(store, slug=slug, city_label=city_label, item=item)
        if point:
            store.setdefault("points", []).append(point)
            existing.add(fp)
            added += 1

    save_map_store(store)
    return {"added": added, "slug": slug}


def sync_all_affiliate_points(*, replace_auto: bool = True) -> dict:
    """Importe automatiquement tous les liens affiliés du site sur la carte."""
    dests = get_destinations_dict_safe()
    store = get_map_store()

    if replace_auto:
        store["points"] = [p for p in store.get("points", []) if p.get("source") not in AUTO_SOURCES]

    existing = _existing_fingerprints(store)
    added = 0
    errors: list[str] = []

    for slug, dest in dests.items():
        city_label = dest.get("name", slug)
        try:
            _city_center(store, slug, city_label)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{city_label}: {exc}")
            continue

        for item in iter_destination_affiliate_items(slug, dest):
            fp = _point_fingerprint(slug, item["ref"])
            if fp in existing:
                continue
            point = _make_auto_point(store, slug=slug, city_label=city_label, item=item)
            store.setdefault("points", []).append(point)
            existing.add(fp)
            added += 1

    for item in iter_global_affiliate_items():
        slug = item.get("destination_slug") or "hanoi"
        fp = _point_fingerprint(slug, item["ref"])
        if fp in existing:
            continue
        city_label = dests.get(slug, {}).get("name", "Vietnam")
        try:
            center = _city_center(store, slug, city_label)
            lat, lng = _spread_coords(center, fp)
        except Exception:
            lat, lng = 16.0, 108.0
        store.setdefault("points", []).append({
            "id": str(uuid.uuid4()),
            "fingerprint": fp,
            "destination_slug": slug,
            "destination_name": city_label,
            "title": item["title"],
            "address": "Vietnam",
            "display_name": item["title"],
            "lat": lat,
            "lng": lng,
            "kind": item.get("kind", "service"),
            "desc": item.get("desc", ""),
            "price_hint": "",
            "affiliate_provider": item.get("affiliate_provider", "custom"),
            "affiliate_url": item.get("affiliate_url", ""),
            "affiliate_link_type": "global",
            "source": "affiliate_auto",
            "created_at": _now_iso(),
        })
        existing.add(fp)
        added += 1

    for item in iter_custom_partner_items():
        slug = item.get("destination_slug") or ""
        if item.get("pending_if_no_slug") or not slug:
            store.setdefault("pending", []).append({
                "id": str(uuid.uuid4()),
                "title": item["title"],
                "address": f"{item.get('destination_name') or item['title']}, Vietnam",
                "kind": item.get("kind", "activity"),
                "affiliate_provider": item.get("affiliate_provider", "custom"),
                "affiliate_url": item.get("affiliate_url", ""),
                "affiliate_link_type": "global",
                "requested_city": item.get("destination_name") or "(partenaire)",
                "pending_reason": "destination_not_published",
                "source": "affiliate_auto",
                "created_at": _now_iso(),
            })
            continue
        fp = _point_fingerprint(slug, item["ref"])
        if fp in existing:
            continue
        city_label = dests.get(slug, {}).get("name", slug)
        point = _make_auto_point(store, slug=slug, city_label=city_label, item=item)
        point["affiliate_url"] = item.get("affiliate_url", "")
        point["affiliate_link_type"] = "global"
        store.setdefault("points", []).append(point)
        existing.add(fp)
        added += 1

    save_map_store(store)
    return {"added": added, "errors": errors[:8], "error_count": len(errors)}


def sync_from_destinations(*, replace: bool = False) -> dict:
    """Alias admin — synchronise tous les affiliés."""
    return sync_all_affiliate_points(replace_auto=replace)


def ensure_map_for_destination(slug: str) -> None:
    """Garantit des points carte pour une ville (sync auto si vide)."""
    store = get_map_store()
    count = sum(1 for p in store.get("points", []) if p.get("destination_slug") == slug)
    if count == 0:
        sync_destination_affiliates(slug)


def defer_sync_destination(slug: str) -> None:
    import threading

    def _run():
        try:
            sync_destination_affiliates(slug)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def defer_sync_all() -> None:
    import threading

    def _run():
        try:
            sync_all_affiliate_points()
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def build_point_affiliate_url(point: dict, track_url_fn: Callable[[str, str], str]) -> str:
    from data.affiliate_urls import (
        agoda_city,
        booking_city,
        build_activity_link,
        build_city_link,
        build_hotel_link,
        get_location_meta,
    )

    link_type = point.get("affiliate_link_type") or "hotel"
    provider = (point.get("affiliate_provider") or "").strip()
    custom = (point.get("affiliate_url") or "").strip()

    if link_type == "global" and custom.startswith("http"):
        return track_url_fn(provider, custom)

    slug = point.get("destination_slug") or ""
    loc = get_location_meta(slug, name=point.get("destination_name"))

    if link_type == "city_booking":
        return track_url_fn("booking", booking_city(loc))
    if link_type == "city_agoda":
        return track_url_fn("agoda", agoda_city(loc))
    if link_type == "city_gyg":
        return track_url_fn("getyourguide", build_city_link("getyourguide", loc))
    if link_type == "city_viator":
        return track_url_fn("viator", build_city_link("viator", loc))

    if provider in ("booking", "agoda"):
        hotel = {
            "name": point.get("affiliate_search") or point.get("title", ""),
            "search": point.get("affiliate_search") or point.get("title", ""),
        }
        return track_url_fn(provider, build_hotel_link(provider, hotel, loc))

    if provider in ("getyourguide", "viator"):
        activity = {
            "name": point.get("affiliate_search") or point.get("title", ""),
            "search": point.get("affiliate_search") or point.get("title", ""),
        }
        return track_url_fn(provider, build_activity_link(provider, activity, loc))

    if provider == "custom" and custom.startswith("http"):
        return track_url_fn("custom", custom)

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
            "esim_airalo": "Get Airalo eSIM",
            "esim_holafly": "Get Holafly eSIM",
            "travel_insurance": "Get insurance",
            "custom": "Book / visit",
        }
        return mapping.get(provider, "Learn more")
    mapping = {
        "booking": "Voir sur Booking",
        "agoda": "Voir sur Agoda",
        "getyourguide": "Réserver sur GetYourGuide",
        "viator": "Réserver sur Viator",
        "esim_airalo": "eSIM Airalo",
        "esim_holafly": "eSIM Holafly",
        "travel_insurance": "Assurance voyage",
        "custom": "Réserver / visiter",
    }
    return mapping.get(provider, "En savoir plus")


def get_public_map_points(destination_slug: str, lang: str, track_url_fn) -> list[dict]:
    ensure_map_for_destination(destination_slug)
    store = get_map_store()
    out = []
    for p in store.get("points", []):
        if p.get("destination_slug") != destination_slug:
            continue
        if p.get("lat") is None or p.get("lng") is None:
            continue
        out.append(serialize_point_for_public(p, lang, track_url_fn))
    return out


def map_page_url(slug: str, lang: str) -> str:
    from i18n_utils import lang_url

    base = config.SITE_URL.rstrip("/") + lang_url("destination_page", lang, slug=slug)
    return f"{base}#dest-map"


def build_chat_map_card(
    destination_slug: str,
    lang: str,
    track_url_fn: Callable[[str, str], str],
    *,
    highlight_urls: set[str] | None = None,
    max_points: int = 6,
) -> dict | None:
    """Carte compacte pour le widget Mai — points + URLs pour mini-carte Leaflet."""
    ensure_map_for_destination(destination_slug)
    points = get_public_map_points(destination_slug, lang, track_url_fn)
    if not points:
        return None

    dests = get_destinations_dict_safe()
    name = dests.get(destination_slug, {}).get("name", destination_slug)
    highlights = highlight_urls or set()
    serialized = []
    for p in points[:max_points]:
        row = dict(p)
        row["highlight"] = bool(p.get("affiliate_url") and p["affiliate_url"] in highlights)
        serialized.append(row)

    return {
        "slug": destination_slug,
        "name": name,
        "map_url": map_page_url(destination_slug, lang),
        "points": serialized,
    }


def build_chat_map_chunks(lang: str, track_url_fn: Callable[[str, str], str]) -> list[dict]:
    """Chunks carte pour Mai — pages carte + pins affiliés."""
    from i18n_utils import lang_url

    lang = "en" if lang == "en" else "fr"
    dests = get_destinations_dict_safe()
    store = get_map_store()
    chunks: list[dict] = []

    by_slug: dict[str, list] = {}
    for p in store.get("points", []):
        slug = p.get("destination_slug")
        if slug:
            by_slug.setdefault(slug, []).append(p)

    map_titles = {
        "fr": "Carte interactive — {name} (hôtels, activités, liens affiliés)",
        "en": "Interactive map — {name} (hotels, activities, affiliate links)",
    }
    map_text = {
        "fr": "Carte gratuite sur la page {name} : pins cliquables avec liens Booking, Agoda, GetYourGuide, Viator.",
        "en": "Free map on the {name} page: clickable pins with Booking, Agoda, GetYourGuide, Viator links.",
    }

    for slug, dest in dests.items():
        pts = by_slug.get(slug, [])
        if not pts:
            continue
        name = dest.get("name", slug)
        url = map_page_url(slug, lang)
        chunks.append({
            "id": f"map:page:{slug}",
            "title": map_titles[lang].format(name=name),
            "url": url,
            "group": "Carte",
            "text": map_text[lang].format(name=name),
            "affiliate": False,
        })

        for p in pts[:6]:
            aff_url = build_point_affiliate_url(p, track_url_fn)
            if not aff_url:
                continue
            chunks.append({
                "id": f"map:pin:{p.get('id', slug)}",
                "title": f"{p.get('title', '')} — {name}",
                "url": aff_url,
                "group": "Carte affiliée",
                "text": p.get("desc") or p.get("title", ""),
                "affiliate": True,
            })

    return chunks


def add_map_point(form: dict) -> dict:
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
        "affiliate_link_type": "hotel" if kind == "hotel" else "activity" if kind == "activity" else "global",
        "source": "manual",
        "created_at": _now_iso(),
    }

    store = get_map_store()
    if slug:
        dests = get_destinations_dict_safe()
        point["destination_slug"] = slug
        point["destination_name"] = dests[slug].get("name", slug)
        point["fingerprint"] = _point_fingerprint(slug, f"manual:{point['id']}")
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
    point = {k: v for k, v in point.items() if k not in ("requested_city", "pending_reason")}
    point["destination_slug"] = slug
    point["destination_name"] = dests[slug].get("name", slug)
    if point.get("lat") is None and point.get("address"):
        geo = geocode_address(point["address"])
        point["lat"] = geo["lat"]
        point["lng"] = geo["lng"]
    store["pending"] = [p for p in pending if p.get("id") != point_id]
    store.setdefault("points", []).append(point)
    save_map_store(store)
    return True
