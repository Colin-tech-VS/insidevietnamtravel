"""Helpers SEO — meta, canonical, FAQ et JSON-LD pour voyage Vietnam (FR)."""

from __future__ import annotations

import re
from html import unescape

import config


def truncate_text(text: str, max_len: int = 160) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1].rsplit(" ", 1)[0]
    return cut + "…"


def build_meta_title(title: str, *, brand: str | None = None, max_len: int = 60) -> str:
    """Title tag optimisé — mot-clé en tête, brand court en suffixe."""
    brand = brand or config.SITE_NAME
    title = (title or "").strip()
    suffix = f" | {brand}"
    if len(title) + len(suffix) <= max_len:
        return title + suffix
    room = max_len - len(suffix) - 1
    return title[:room].rsplit(" ", 1)[0] + suffix


def article_meta_title(article: dict) -> str:
    if article.get("meta_title"):
        return article["meta_title"][:70]
    return build_meta_title(article.get("title", ""))


def article_meta_description(article: dict, lang: str = "fr") -> str:
    if article.get("meta_description"):
        return truncate_text(article["meta_description"], 160)
    excerpt = article.get("excerpt", "")
    if len(excerpt) >= 100:
        return truncate_text(excerpt, 160)
    city = article.get("city", "")
    if lang == "en":
        extra = " Practical guide for travellers"
        if city and city not in ("Tout le Vietnam", "All Vietnam"):
            extra += f" — {city}, Vietnam."
        else:
            extra += " — plan your Vietnam trip."
    else:
        extra = " Guide pratique pour voyageurs français"
        if city and city != "Tout le Vietnam":
            extra += f" — {city}, Vietnam."
        else:
            extra += " — préparez votre voyage au Vietnam."
    return truncate_text(f"{excerpt}{extra}", 160)


def extract_faq_from_html(html: str) -> list[dict]:
    """Extrait paires H3 + paragraphe suivant pour FAQPage schema."""
    if not html:
        return []
    items = []
    pattern = re.compile(
        r"<h3[^>]*>(.*?)</h3>\s*(?:<p[^>]*>(.*?)</p>|<div[^>]*>(.*?)</div>)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(html):
        q = _strip_tags(m.group(1))
        a = _strip_tags(m.group(2) or m.group(3) or "")
        if q and a and len(q) > 8 and len(a) > 15:
            items.append({"question": q, "answer": a})
    return items[:8]


def _strip_tags(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def organization_schema(lang: str = "fr") -> dict:
    desc = config.SITE_DESCRIPTION_I18N.get(lang, config.SITE_DESCRIPTION)
    return {
        "@type": "Organization",
        "@id": f"{config.SITE_URL}/#organization",
        "name": config.SITE_NAME,
        "url": config.SITE_URL,
        "description": desc,
        "logo": {
            "@type": "ImageObject",
            "url": f"{config.SITE_URL}/static/images/favicon.svg",
        },
    }


def website_schema(lang: str = "fr") -> dict:
    from i18n_utils import schema_language
    desc = config.SITE_DESCRIPTION_I18N.get(lang, config.SITE_DESCRIPTION)
    return {
        "@type": "WebSite",
        "@id": f"{config.SITE_URL}/#website",
        "name": config.SITE_NAME,
        "url": config.SITE_URL,
        "description": desc,
        "inLanguage": schema_language(lang),
        "publisher": {"@id": f"{config.SITE_URL}/#organization"},
    }


def breadcrumb_schema(items: list[tuple[str, str | None]]) -> dict:
    """items = [(label, url_or_none), ...] — dernier sans URL."""
    elements = []
    for i, (name, url) in enumerate(items, start=1):
        el: dict = {"@type": "ListItem", "position": i, "name": name}
        if url:
            el["item"] = url
        elements.append(el)
    return {"@type": "BreadcrumbList", "itemListElement": elements}


def faq_schema(faq_items: list[dict]) -> dict | None:
    if not faq_items:
        return None
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
            }
            for item in faq_items
        ],
    }


def item_list_schema(name: str, items: list[dict]) -> dict:
    """items: [{name, url}, ...]"""
    return {
        "@type": "ItemList",
        "name": name,
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": it["name"],
                "url": it["url"],
            }
            for i, it in enumerate(items, start=1)
        ],
    }
