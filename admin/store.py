"""JSON stores — settings, affiliates, articles."""

import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from data.affiliates import AFFILIATE_IDS as DEFAULT_AFFILIATE_IDS
from data.affiliates import PDF_GUIDE as DEFAULT_PDF_GUIDE
from data.articles import ARTICLES as DEFAULT_ARTICLES
from data.articles import CATEGORIES as DEFAULT_CATEGORIES
from data.destinations import DESTINATIONS as DEFAULT_DESTINATIONS

STORE_DIR = Path(__file__).parent.parent / "data" / "store"
SETTINGS_FILE = STORE_DIR / "settings.json"
AFFILIATES_FILE = STORE_DIR / "affiliate_ids.json"
CUSTOM_PARTNERS_FILE = STORE_DIR / "custom_partners.json"
ARTICLES_FILE = STORE_DIR / "articles.json"
DESTINATIONS_FILE = STORE_DIR / "destinations.json"

_json_cache: dict[str, tuple[float, Any]] = {}


def _read_json(path: Path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return deepcopy(default)


def _read_json_cached(path: Path, default, cache_key: str):
    mtime = path.stat().st_mtime if path.exists() else -1.0
    cached = _json_cache.get(cache_key)
    if cached and cached[0] == mtime:
        return deepcopy(cached[1])
    data = _read_json(path, default)
    if path.exists():
        _json_cache[cache_key] = (mtime, data)
    return deepcopy(data)


def _invalidate_cache(*keys: str):
    for key in keys:
        _json_cache.pop(key, None)


def _write_json(path: Path, data, *cache_keys: str):
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _invalidate_cache(*cache_keys)


def get_settings() -> dict:
    defaults = {
        "ga4_measurement_id": "",
        "groq_model": "llama-3.3-70b-versatile",
        "commission_estimates": {
            "booking": 8.0,
            "agoda": 6.0,
            "getyourguide": 4.0,
            "viator": 4.0,
            "esim_airalo": 2.0,
            "esim_holafly": 2.0,
            "travel_insurance": 5.0,
            "pdf": 9.0,
        },
    }
    return {**defaults, **_read_json_cached(SETTINGS_FILE, {}, "settings")}


def save_settings(data: dict):
    current = get_settings()
    current.update(data)
    _write_json(SETTINGS_FILE, current, "settings")


def get_affiliate_ids() -> dict:
    return {**DEFAULT_AFFILIATE_IDS, **_read_json_cached(AFFILIATES_FILE, {}, "affiliates")}


def save_affiliate_ids(data: dict):
    _write_json(AFFILIATES_FILE, data, "affiliates")


def get_custom_partners() -> list:
    return _read_json_cached(CUSTOM_PARTNERS_FILE, [], "custom_partners")


def save_custom_partners(partners: list):
    _write_json(CUSTOM_PARTNERS_FILE, partners, "custom_partners")


def add_custom_partner(partner: dict):
    partners = get_custom_partners()
    partners = [p for p in partners if p["id"] != partner["id"]]
    partners.append(partner)
    save_custom_partners(partners)


def delete_custom_partner(partner_id: str):
    partners = [p for p in get_custom_partners() if p["id"] != partner_id]
    save_custom_partners(partners)


def is_configured(value: str) -> bool:
    if not value or value.startswith("#"):
        return value.startswith("http")  # PDF URL
    return "PLACEHOLDER" not in value.upper()


def get_articles() -> list:
    stored = _read_json_cached(ARTICLES_FILE, None, "articles")
    if stored is None:
        _write_json(ARTICLES_FILE, DEFAULT_ARTICLES, "articles")
        return deepcopy(DEFAULT_ARTICLES)
    return stored


def get_categories() -> dict:
    return DEFAULT_CATEGORIES


def save_articles(articles: list):
    _write_json(ARTICLES_FILE, articles, "articles")


def get_article_by_slug(slug: str) -> dict | None:
    return next((a for a in get_articles() if a["slug"] == slug), None)


def add_article(article: dict):
    articles = get_articles()
    articles = [a for a in articles if a["slug"] != article["slug"]]
    articles.insert(0, article)
    save_articles(articles)


def get_destinations_dict() -> dict:
    stored = _read_json_cached(DESTINATIONS_FILE, None, "destinations")
    if stored is None:
        _write_json(DESTINATIONS_FILE, DEFAULT_DESTINATIONS, "destinations")
        return deepcopy(DEFAULT_DESTINATIONS)
    return stored


def save_destinations(destinations: dict):
    _write_json(DESTINATIONS_FILE, destinations, "destinations")


def get_destination_by_slug(slug: str) -> dict | None:
    return get_destinations_dict().get(slug)


def add_or_update_destination(dest: dict):
    data = get_destinations_dict()
    data[dest["slug"]] = dest
    save_destinations(data)


def delete_destination(slug: str):
    data = get_destinations_dict()
    data.pop(slug, None)
    save_destinations(data)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[àâä]", "a", text)
    text = re.sub(r"[éèêë]", "e", text)
    text = re.sub(r"[îï]", "i", text)
    text = re.sub(r"[ôö]", "o", text)
    text = re.sub(r"[ùûü]", "u", text)
    text = re.sub(r"ç", "c", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]


def count_newsletter_subscribers() -> int:
    from admin.newsletter_service import get_newsletter_subscribers
    return len(get_newsletter_subscribers())
