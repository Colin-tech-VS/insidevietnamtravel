"""Internationalisation FR/EN — routes, contenu et UI."""

from __future__ import annotations

import copy
import os
from typing import Any

from flask import g, request

import config

SUPPORTED_LANGS = ("fr", "en")
DEFAULT_LANG = "fr"
LANG_COOKIE = "site_lang"

ARTICLE_I18N_FIELDS = (
    "title", "meta_title", "meta_description", "excerpt", "content",
    "category_label", "tags", "focus_keyword", "image_alt",
)
DESTINATION_I18N_FIELDS = (
    "name", "meta_title", "meta_description", "tagline", "overview",
    "image_alt",
)
ITINERARY_I18N_FIELDS = (
    "title", "meta_title", "meta_description", "summary", "budget_hint",
)

ANALYTICS_EXCLUDED_IPS: frozenset[str] = frozenset(
    ip.strip()
    for ip in os.environ.get("ANALYTICS_EXCLUDED_IPS", "").split(",")
    if ip.strip()
)


def client_ip() -> str:
    return (request.remote_addr or "").strip()


def is_analytics_excluded_ip() -> bool:
    from admin.analytics_filters import is_analytics_excluded_ip as _is_excluded

    return _is_excluded(client_ip())


def detect_lang_from_path(path: str | None = None) -> str:
    path = path if path is not None else request.path
    if path == "/en" or path.startswith("/en/"):
        return "en"
    return DEFAULT_LANG


def get_lang() -> str:
    return getattr(g, "lang", DEFAULT_LANG)


def set_lang(lang: str) -> None:
    g.lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def og_locale(lang: str | None = None) -> str:
    lang = lang or get_lang()
    return "en_GB" if lang == "en" else "fr_FR"


def html_lang(lang: str | None = None) -> str:
    lang = lang or get_lang()
    return "en" if lang == "en" else "fr"


def schema_language(lang: str | None = None) -> str:
    lang = lang or get_lang()
    return "en-GB" if lang == "en" else "fr-FR"


def site_tagline(lang: str | None = None) -> str:
    lang = lang or get_lang()
    return config.SITE_TAGLINE_I18N.get(lang, config.SITE_TAGLINE)


def site_description(lang: str | None = None) -> str:
    lang = lang or get_lang()
    return config.SITE_DESCRIPTION_I18N.get(lang, config.SITE_DESCRIPTION)


def site_keywords(lang: str | None = None) -> str:
    lang = lang or get_lang()
    return config.SITE_KEYWORDS_I18N.get(lang, config.SITE_KEYWORDS)


def _pick_i18n_block(item: dict, lang: str, fields: tuple[str, ...]) -> dict:
    i18n = item.get("i18n") or {}
    block = i18n.get(lang)
    if block:
        return {k: block[k] for k in fields if k in block}
    if lang == DEFAULT_LANG:
        return {k: item[k] for k in fields if k in item}
    fr_block = i18n.get(DEFAULT_LANG) or {
        k: item[k] for k in fields if k in item
    }
    return {k: fr_block.get(k, "") for k in fields}


def _localize_list_items(items: list, lang: str, keys: tuple[str, ...]) -> list:
    out = []
    for item in items:
        if not isinstance(item, dict):
            out.append(item)
            continue
        loc = copy.deepcopy(item)
        i18n = item.get("i18n", {})
        if lang in i18n:
            for key in keys:
                if key in i18n[lang]:
                    loc[key] = i18n[lang][key]
        out.append(loc)
    return out


def localize_article(article: dict, lang: str | None = None) -> dict:
    from seo_utils import fix_legacy_article_links

    lang = lang or get_lang()
    result = copy.deepcopy(article)
    result.update(_pick_i18n_block(article, lang, ARTICLE_I18N_FIELDS))
    if result.get("content"):
        result["content"] = fix_legacy_article_links(result["content"])
    return result


def localize_destination(dest: dict, lang: str | None = None) -> dict:
    lang = lang or get_lang()
    result = copy.deepcopy(dest)
    result.update(_pick_i18n_block(dest, lang, DESTINATION_I18N_FIELDS))

    i18n = dest.get("i18n", {})
    if lang in i18n:
        if "things_to_do" in i18n[lang]:
            result["things_to_do"] = i18n[lang]["things_to_do"]
        if "tips" in i18n[lang]:
            result["tips"] = i18n[lang]["tips"]
        if "hotels" in i18n[lang]:
            result["hotels"] = _localize_list_items(
                dest.get("hotels", []), lang, ("name", "desc", "price_hint")
            )
        if "activities" in i18n[lang]:
            result["activities"] = _localize_list_items(
                dest.get("activities", []), lang, ("name", "desc", "price_hint")
            )
    elif lang != DEFAULT_LANG:
        fr = i18n.get(DEFAULT_LANG, {})
        for key in ("things_to_do", "tips", "hotels", "activities"):
            if key in fr:
                result[key] = fr[key]

    return result


def localize_itinerary(itin: dict, lang: str | None = None) -> dict:
    lang = lang or get_lang()
    result = copy.deepcopy(itin)
    result.update(_pick_i18n_block(itin, lang, ITINERARY_I18N_FIELDS))

    i18n = itin.get("i18n", {})
    block = i18n.get(lang) or (i18n.get(DEFAULT_LANG) if lang != DEFAULT_LANG else {})
    if block:
        for key in (
            "sample_hotel", "sample_activity", "days", "overview",
            "highlights", "experiences", "faq", "affiliate_sections",
            "best_season", "includes", "practical",
        ):
            if key in block:
                if key in ("sample_hotel", "sample_activity") and isinstance(block[key], dict):
                    result[key] = {**result.get(key, {}), **block[key]}
                else:
                    result[key] = block[key]
    return result


def localize_category(cat: dict, lang: str | None = None) -> dict:
    lang = lang or get_lang()
    i18n = cat.get("i18n", {})
    if lang in i18n:
        return {**cat, **i18n[lang]}
    if lang == DEFAULT_LANG:
        return {k: cat.get(k, "") for k in ("label", "description")}
    fr = i18n.get(DEFAULT_LANG, cat)
    return {
        "label": fr.get("label", cat.get("label", "")),
        "description": fr.get("description", cat.get("description", "")),
    }


def wrap_article_i18n(article: dict) -> dict:
    """Convertit un article plat ou partiel en structure i18n."""
    if article.get("i18n") and "fr" in article["i18n"]:
        return article
    fr = {k: article[k] for k in ARTICLE_I18N_FIELDS if k in article}
    en = article.get("i18n", {}).get("en", {}) if isinstance(article.get("i18n"), dict) else {}
    base = {k: v for k, v in article.items() if k not in ("i18n",) + ARTICLE_I18N_FIELDS}
    base["i18n"] = {"fr": fr, "en": en}
    merged = {**base, **fr}
    return merged


def wrap_destination_i18n(dest: dict) -> dict:
    if dest.get("i18n") and "fr" in dest["i18n"]:
        return dest
    fr = {k: dest[k] for k in DESTINATION_I18N_FIELDS if k in dest}
    for key in ("things_to_do", "tips", "hotels", "activities"):
        if key in dest:
            fr[key] = dest[key]
    en = {}
    if isinstance(dest.get("i18n"), dict):
        en = dest["i18n"].get("en", {})
    base = {
        k: v for k, v in dest.items()
        if k not in ("i18n",) + DESTINATION_I18N_FIELDS
        and k not in ("things_to_do", "tips", "hotels", "activities")
    }
    base["i18n"] = {"fr": fr, "en": en}
    return {**base, **fr}


def merge_bilingual_article(fr_data: dict, en_data: dict, shared: dict) -> dict:
    article = {**shared}
    article["i18n"] = {
        "fr": {k: fr_data.get(k, "") for k in ARTICLE_I18N_FIELDS},
        "en": {k: en_data.get(k, "") for k in ARTICLE_I18N_FIELDS},
    }
    article.update(article["i18n"]["fr"])
    return article


def merge_bilingual_destination(fr_data: dict, en_data: dict, shared: dict) -> dict:
    dest = {**shared}
    fr_block = {k: fr_data.get(k, "") for k in DESTINATION_I18N_FIELDS}
    en_block = {k: en_data.get(k, "") for k in DESTINATION_I18N_FIELDS}
    for key in ("things_to_do", "tips", "hotels", "activities"):
        if key in fr_data:
            fr_block[key] = fr_data[key]
        if key in en_data:
            en_block[key] = en_data[key]
    dest["i18n"] = {"fr": fr_block, "en": en_block}
    dest.update(fr_block)
    return dest


# ── Routes localisées ─────────────────────────────────────────────────

ROUTE_PATHS: dict[str, dict[str, str]] = {
    "index": {"fr": "/", "en": "/en/"},
    "blog_index": {"fr": "/blog", "en": "/en/blog"},
    "prepare_trip": {"fr": "/preparer-mon-voyage", "en": "/en/plan-my-trip"},
    "best_season": {"fr": "/quand-partir-au-vietnam", "en": "/en/best-time-to-visit-vietnam"},
    "budget_tool": {"fr": "/calculateur-budget-vietnam", "en": "/en/vietnam-budget-calculator"},
    "visa_tool": {"fr": "/visa-vietnam", "en": "/en/vietnam-visa"},
    "essentials_tool": {"fr": "/esim-assurance-vietnam", "en": "/en/esim-insurance-vietnam"},
    "useful_apps": {"fr": "/applications-utiles-vietnam", "en": "/en/useful-apps-vietnam"},
    "safety_guide": {"fr": "/securite-voyage-vietnam", "en": "/en/vietnam-travel-safety"},
    "customs_guide": {"fr": "/coutumes-vietnam", "en": "/en/vietnam-customs-etiquette"},
    "phrases_guide": {"fr": "/phrases-utiles-vietnamien", "en": "/en/useful-vietnamese-phrases"},
    "events_calendar": {"fr": "/evenements-vietnam-2026", "en": "/en/vietnam-events-calendar"},
    "about": {"fr": "/a-propos", "en": "/en/about"},
    "contact": {"fr": "/contact", "en": "/en/contact"},
    "destinations_index": {"fr": "/destinations-vietnam", "en": "/en/vietnam-destinations"},
    "become_partner": {"fr": "/devenir-partenaire", "en": "/en/become-a-partner"},
    "become_partner_register": {
        "fr": "/devenir-partenaire/inscription",
        "en": "/en/become-a-partner/register",
    },
    "partner_public": {"fr": "/partenaire/{slug}", "en": "/en/partner/{slug}"},
    "partners_index": {"fr": "/partenaires-vietnam", "en": "/en/vietnam-travel-partners"},
    "recommended_partner_fiche": {
        "fr": "/partenaires-recommandes/{slug}",
        "en": "/en/recommended-partners/{slug}",
    },
    "recommended_partner_page": {
        "fr": "/partenaires-recommandes/{slug}/{page_slug}",
        "en": "/en/recommended-partners/{slug}/{page_slug}",
    },
    "privacy": {"fr": "/politique-confidentialite", "en": "/en/privacy"},
    "legal_notices": {"fr": "/mentions-legales", "en": "/en/legal"},
    "newsletter_unsubscribe": {
        "fr": "/newsletter/desinscription",
        "en": "/en/newsletter/unsubscribe",
    },
    "newsletter_subscribe": {"fr": "/newsletter", "en": "/en/newsletter"},
    "category": {"fr": "/categorie/{category}", "en": "/en/category/{category}"},
    "article": {"fr": "/blog/{slug}", "en": "/en/blog/{slug}"},
    "seo_page": {"fr": "/seo/{slug}", "en": "/en/seo/{slug}"},
    "seo_hub": {"fr": "/ressources-voyage-vietnam", "en": "/en/vietnam-travel-resources"},
    "itinerary": {"fr": "/itineraries/{slug}", "en": "/en/itineraries/{slug}"},
    "itinerary_guide_subscribe": {
        "fr": "/itineraries/{slug}/guide",
        "en": "/en/itineraries/{slug}/guide",
    },
    "prepare_trip_unlock": {
        "fr": "/preparer-mon-voyage/unlock",
        "en": "/en/plan-my-trip/unlock",
    },
    "itinerary_guide_download": {
        "fr": "/itineraries/{slug}/guide/{token}",
        "en": "/en/itineraries/{slug}/guide/{token}",
    },
    "pillar": {"fr": "/guide/{slug}", "en": "/en/guide/{slug}"},
    "pdf_checkout": {"fr": "/checkout", "en": "/en/guide-pdf/checkout"},
    "pdf_success": {"fr": "/guide-pdf/merci", "en": "/en/guide-pdf/success"},
    "pdf_download": {"fr": "/guide-pdf/telecharger/{token}", "en": "/en/guide-pdf/download/{token}"},
    "destination_page": {"fr": "/{slug}", "en": "/en/{slug}"},
}


def lang_url(endpoint: str, lang: str | None = None, **kwargs: Any) -> str:
    lang = lang or get_lang()
    template = ROUTE_PATHS.get(endpoint, {}).get(lang)
    if not template:
        from flask import url_for
        return url_for(endpoint, **kwargs)
    path = template.format(**kwargs)
    if path.endswith("/") and path not in ("/", "/en/"):
        path = path.rstrip("/")
    return path


def alternate_lang(lang: str | None = None) -> str:
    lang = lang or get_lang()
    return "en" if lang == "fr" else "fr"


def page_url_in_lang(target_lang: str) -> str:
    """URL de la page courante dans la langue demandée."""
    if target_lang not in SUPPORTED_LANGS:
        target_lang = DEFAULT_LANG
    if target_lang == get_lang():
        path = request.path
        return path if path != "/en" else "/en/"
    return switch_lang_url() if target_lang == alternate_lang() else lang_url("index", target_lang)


def switch_lang_url() -> str:
    """URL de la page courante dans l'autre langue."""
    alt = alternate_lang()
    endpoint = request.endpoint or ""
    view_args = dict(request.view_args or {})

    if endpoint.endswith("_en"):
        endpoint = endpoint[:-3]
    elif alt == "en" and not endpoint.endswith("_en"):
        pass

    base_endpoint = endpoint.replace("_en", "")

    if base_endpoint == "category":
        return lang_url("category", alt, category=view_args.get("category", ""))
    if base_endpoint == "article":
        return lang_url("article", alt, slug=view_args.get("slug", ""))
    if base_endpoint == "seo_page":
        return lang_url("seo_page", alt, slug=view_args.get("slug", ""))
    if base_endpoint == "itinerary":
        return lang_url("itinerary", alt, slug=view_args.get("slug", ""))
    if base_endpoint == "itinerary_guide_download":
        return lang_url(
            "itinerary_guide_download",
            alt,
            slug=view_args.get("slug", ""),
            token=view_args.get("token", ""),
        )
    if base_endpoint == "destination_page":
        return lang_url("destination_page", alt, slug=view_args.get("slug", ""))
    if base_endpoint == "pillar":
        return lang_url("pillar", alt, slug=view_args.get("slug", ""))
    if base_endpoint in ("partner_public", "partner_public_page"):
        return lang_url("partner_public", alt, slug=view_args.get("slug", ""))
    if base_endpoint == "partners_index":
        return lang_url("partners_index", alt)
    if base_endpoint == "recommended_partner_fiche":
        return lang_url("recommended_partner_fiche", alt, slug=view_args.get("slug", ""))
    if base_endpoint == "recommended_partner_page":
        return lang_url(
            "recommended_partner_page",
            alt,
            slug=view_args.get("slug", ""),
            page_slug=view_args.get("page_slug", ""),
        )

    if base_endpoint in ROUTE_PATHS:
        return lang_url(base_endpoint, alt)

    return lang_url("index", alt)


def _route_endpoint(endpoint: str) -> str:
    endpoint = (endpoint or "").replace("_en", "")
    aliases = {
        "partner_public_page": "partner_public",
        "partners_index": "partners_index",
    }
    return aliases.get(endpoint, endpoint)


def canonical_for_request(lang: str | None = None) -> str:
    lang = lang or get_lang()
    endpoint = _route_endpoint(request.endpoint or "")
    view_args = dict(request.view_args or {})
    base = config.SITE_URL.rstrip("/")

    if endpoint == "index":
        return base + ("/en/" if lang == "en" else "/")
    if endpoint in ROUTE_PATHS:
        path = lang_url(endpoint, lang, **view_args)
        return base + path
    return base + request.path


def hreflang_urls() -> list[dict[str, str]]:
    endpoint = _route_endpoint(request.endpoint or "")
    if endpoint in ("affiliate_redirect", "robots", "sitemap", "newsletter_subscribe"):
        return []
    view_args = dict(request.view_args or {})
    base = config.SITE_URL.rstrip("/")
    urls = []
    for lang in SUPPORTED_LANGS:
        if endpoint in ROUTE_PATHS:
            path = lang_url(endpoint, lang, **view_args)
            urls.append({"lang": lang, "href": base + path})
    return urls
