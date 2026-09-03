"""SEO, schéma JSON-LD et maillage — pages SEO landing publiques."""

from __future__ import annotations

import re

import config
from admin.seo_pages_service import get_published_seo_pages
from admin.store import find_destination_slug, get_articles, get_destinations_dict
from i18n_utils import lang_url

_DEFAULT_HERO = "/static/images/destinations/hanoi-960.webp"


def meta_keywords(page: dict, lang: str) -> str:
    kws = list(page.get("target_keywords") or [])
    focus = (page.get("focus_keyword") or "").strip()
    if focus and focus not in kws:
        kws.insert(0, focus)
    city = (page.get("city") or "").strip()
    if city and city != "Tout le Vietnam":
        kws.append(city)
    kws.append("Vietnam")
    if lang == "en":
        kws.extend(["Vietnam travel", "trip to Vietnam"])
    else:
        kws.extend(["voyage Vietnam", "voyage au Vietnam"])
    seen: set[str] = set()
    out: list[str] = []
    for kw in kws:
        key = kw.lower()
        if key and key not in seen:
            seen.add(key)
            out.append(kw)
    return ", ".join(out[:18])


def _keyword_overlap(a: dict, b: dict) -> int:
    ka = {k.lower() for k in (a.get("target_keywords") or [])}
    ka.add((a.get("focus_keyword") or "").lower())
    kb = {k.lower() for k in (b.get("target_keywords") or [])}
    kb.add((b.get("focus_keyword") or "").lower())
    return len(ka & kb)


def related_seo_pages(page: dict, lang: str, *, limit: int = 4) -> list[dict]:
    slug = page.get("slug")
    city = (page.get("city") or "").lower()
    scored: list[tuple[int, dict]] = []
    for other in get_published_seo_pages(lang):
        if other.get("slug") == slug:
            continue
        score = _keyword_overlap(page, other) * 3
        if city and city in (other.get("city") or "").lower():
            score += 2
        if score > 0:
            scored.append((score, other))
    scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    return [
        {
            "title": p.get("title", ""),
            "url": lang_url("seo_page", lang, slug=p["slug"]),
            "excerpt": (p.get("excerpt") or "")[:120],
        }
        for _, p in scored[:limit]
    ]


def maillage_links(page: dict, lang: str, *, limit: int = 8) -> list[dict]:
    """Liens contextuels vers le reste du site (sidebar + bloc bas de page)."""
    links: list[dict] = []
    seen: set[str] = set()

    def add(url: str, title: str) -> None:
        if not url or url in seen:
            return
        seen.add(url)
        links.append({"url": url, "title": title})

    city = (page.get("city") or "").strip()
    if city and city != "Tout le Vietnam":
        dest_slug = find_destination_slug(city)
        if dest_slug:
            dest = get_destinations_dict(lang).get(dest_slug, {})
            add(lang_url("destination_page", lang, slug=dest_slug), dest.get("name") or city)

    kws = [k.lower() for k in (page.get("target_keywords") or [])]
    for article in get_articles(lang)[:40]:
        slug = article.get("slug")
        title = (article.get("title") or "").strip()
        if not slug or not title:
            continue
        hay = f"{title} {' '.join(article.get('tags') or [])}".lower()
        if any(k in hay for k in kws[:5]):
            add(lang_url("article", lang, slug=slug), title)
        if len(links) >= limit:
            break

    add(lang_url("prepare_trip", lang), "Préparer mon voyage" if lang == "fr" else "Plan my trip")
    add(lang_url("blog_index", lang), "Actualités voyage Vietnam" if lang == "fr" else "Vietnam travel news")
    add(lang_url("destinations_index", lang), "Destinations Vietnam" if lang == "fr" else "Vietnam destinations")
    add(lang_url("partners_index", lang), "Partenaires voyage Vietnam" if lang == "fr" else "Vietnam travel partners")

    for rel in related_seo_pages(page, lang, limit=3):
        add(rel["url"], rel["title"])

    return links[:limit]


def page_context(page: dict, lang: str) -> dict:
    return {
        "meta_keywords": meta_keywords(page, lang),
        "maillage_links": maillage_links(page, lang),
        "related_seo_pages": related_seo_pages(page, lang),
        "hero_fallback": _DEFAULT_HERO,
        "canonical_path": lang_url("seo_page", lang, slug=page.get("slug", "")),
    }


def json_ld_schemas(page: dict, lang: str, *, canonical_url: str, faq_items: list) -> list[dict]:
    from seo_utils import breadcrumb_schema, faq_schema, webpage_schema

    home = config.SITE_URL + lang_url("index", lang)
    schemas = [
        webpage_schema(
            name=page.get("meta_title") or page.get("title", ""),
            description=page.get("meta_description") or page.get("excerpt", ""),
            url=canonical_url,
            lang=lang,
        ),
        breadcrumb_schema([
            ("Accueil" if lang == "fr" else "Home", home),
            ("Pages SEO" if lang == "fr" else "SEO guides", config.SITE_URL + lang_url("blog_index", lang)),
            (page.get("title", ""), None),
        ]),
    ]
    faq = faq_schema(faq_items)
    if faq:
        schemas.append(faq)
    return schemas
