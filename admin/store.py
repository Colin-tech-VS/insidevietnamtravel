"""Store contenu & réglages — Supabase (JSONB) ou fichiers JSON locaux."""

import re
from copy import deepcopy
from datetime import date

from data.affiliates import AFFILIATE_IDS as DEFAULT_AFFILIATE_IDS
from data.articles import ARTICLES as DEFAULT_ARTICLES
from data.articles import CATEGORIES as DEFAULT_CATEGORIES
from data.destinations import DESTINATIONS as DEFAULT_DESTINATIONS

from admin.kv_store import get_json, set_json
from i18n_utils import (
    DEFAULT_LANG,
    localize_article,
    localize_category,
    localize_destination,
    wrap_article_i18n,
    wrap_destination_i18n,
)


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
    stored = get_json("settings", {}, file_name="settings.json")
    if stored is None:
        stored = {}
    return {**defaults, **stored}


def save_settings(data: dict):
    current = get_settings()
    current.update(data)
    set_json("settings", current, file_name="settings.json")


def get_affiliate_ids() -> dict:
    stored = get_json("affiliate_ids", {}, file_name="affiliate_ids.json")
    if stored is None:
        stored = {}
    return {**DEFAULT_AFFILIATE_IDS, **stored}


def save_affiliate_ids(data: dict):
    set_json("affiliate_ids", data, file_name="affiliate_ids.json")


def get_custom_partners() -> list:
    stored = get_json("custom_partners", [], file_name="custom_partners.json")
    return stored if stored is not None else []


def save_custom_partners(partners: list):
    set_json("custom_partners", partners, file_name="custom_partners.json")


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
        return value.startswith("http")
    return "PLACEHOLDER" not in value.upper()


def _raw_articles() -> list:
    stored = get_json("articles", None, file_name="articles.json")
    if stored is None:
        set_json("articles", DEFAULT_ARTICLES, file_name="articles.json")
        return deepcopy(DEFAULT_ARTICLES)
    return stored


def get_articles(lang: str | None = None) -> list:
    articles = [wrap_article_i18n(a) for a in _raw_articles()]
    if lang:
        return [localize_article(a, lang) for a in articles]
    return articles


def get_categories(lang: str | None = None) -> dict:
    if not lang:
        return DEFAULT_CATEGORIES
    return {
        key: localize_category(cat, lang)
        for key, cat in DEFAULT_CATEGORIES.items()
    }


def _auto_translate_article(article: dict) -> dict:
    article = wrap_article_i18n(article)
    en = article.get("i18n", {}).get("en", {})
    if en.get("content"):
        return article
    try:
        from admin.groq_translate import translate_article_block
        fr = article["i18n"]["fr"]
        translated = translate_article_block({**article, **fr})
        article["i18n"]["en"] = {k: translated.get(k, fr.get(k, "")) for k in fr}
    except Exception:
        pass
    return article


def _auto_translate_destination(dest: dict) -> dict:
    dest = wrap_destination_i18n(dest)
    en = dest.get("i18n", {}).get("en", {})
    if en.get("overview"):
        return dest
    try:
        from admin.groq_translate import translate_destination_block
        fr = dest["i18n"]["fr"]
        translated = translate_destination_block({**dest, **fr})
        dest["i18n"]["en"] = {k: translated.get(k, fr.get(k, "")) for k in fr}
    except Exception:
        pass
    return dest


def save_articles(articles: list):
    normalized = [_auto_translate_article(wrap_article_i18n(a)) for a in articles]
    set_json("articles", normalized, file_name="articles.json")


def get_article_by_slug(slug: str, lang: str | None = None) -> dict | None:
    article = next((a for a in _raw_articles() if a["slug"] == slug), None)
    if not article:
        return None
    article = wrap_article_i18n(article)
    return localize_article(article, lang) if lang else article


def add_article(article: dict):
    articles = _raw_articles()
    article = wrap_article_i18n(article)
    articles = [wrap_article_i18n(a) for a in articles if a["slug"] != article["slug"]]
    articles.insert(0, article)
    save_articles(articles)


def _raw_destinations() -> dict:
    stored = get_json("destinations", None, file_name="destinations.json")
    if stored is None:
        set_json("destinations", DEFAULT_DESTINATIONS, file_name="destinations.json")
        return deepcopy(DEFAULT_DESTINATIONS)
    return stored


def get_destinations_dict(lang: str | None = None) -> dict:
    raw = _raw_destinations()
    wrapped = {slug: wrap_destination_i18n(d) for slug, d in raw.items()}
    if not lang:
        return wrapped
    return {
        slug: localize_destination(d, lang)
        for slug, d in wrapped.items()
    }


def save_destinations(destinations: dict):
    normalized = {
        slug: _auto_translate_destination(wrap_destination_i18n(d))
        for slug, d in destinations.items()
    }
    set_json("destinations", normalized, file_name="destinations.json")


def get_destination_by_slug(slug: str, lang: str | None = None) -> dict | None:
    dest = _raw_destinations().get(slug)
    if not dest:
        return None
    dest = wrap_destination_i18n(dest)
    return localize_destination(dest, lang) if lang else dest


def add_or_update_destination(dest: dict):
    data = _raw_destinations()
    data[dest["slug"]] = wrap_destination_i18n(dest)
    save_destinations(data)


def delete_destination(slug: str):
    data = _raw_destinations()
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


# ── Avis voyageurs ────────────────────────────────────────────────────
def get_reviews() -> list:
    from data.reviews import DEFAULT_REVIEWS

    stored = get_json("reviews", None, file_name="reviews.json")
    if stored is None:
        return deepcopy(DEFAULT_REVIEWS)
    return stored


def save_reviews(reviews: list):
    set_json("reviews", reviews, file_name="reviews.json")


def localized_reviews(lang: str) -> list:
    out = []
    for r in get_reviews():
        text = r.get("text", {})
        if isinstance(text, dict):
            body = text.get(lang) or text.get(DEFAULT_LANG) or ""
        else:
            body = text
        out.append({**r, "body": body})
    return out
