"""Helpers SEO — meta, canonical, FAQ et JSON-LD pour voyage Vietnam (FR)."""

from __future__ import annotations

import re
from html import unescape

import config

_LEGACY_DEST_LINK = re.compile(r'href="/destinations/([^"/]+)"', re.IGNORECASE)


def fix_legacy_article_links(html: str) -> str:
    """Réécrit les anciens liens /destinations/<slug> vers /<slug> (routes réelles)."""
    if not html:
        return html
    return _LEGACY_DEST_LINK.sub(r'href="/\1"', html)


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
    base = config.SITE_URL.rstrip("/")
    # sameAs : profils sociaux officiels (configurables) + ressources canoniques.
    same_as = [base] + list(getattr(config, "SITE_SOCIAL_URLS", []) or []) + [f"{base}/llms.txt"]
    return {
        "@type": "Organization",
        "@id": f"{base}/#organization",
        "name": config.SITE_NAME,
        "url": base,
        "description": desc,
        # Logo raster (Google ignore les SVG pour le logo d'organisation).
        "logo": {
            "@type": "ImageObject",
            "url": f"{base}/static/images/favicon-180.png",
            "width": 180,
            "height": 180,
        },
        "image": f"{base}/static/images/og-default.jpg",
        "email": config.LEGAL_CONTACT_EMAIL,
        "areaServed": {"@type": "Country", "name": "Vietnam"},
        "knowsAbout": [
            "Vietnam travel", "Vietnam visa", "Vietnam visa price",
            "Vietnam itinerary", "Vietnam itinerary 10 days", "15 days in Vietnam",
            "Hanoi travel", "where to stay in Hanoi", "where to eat in Hanoi",
            "Hội An travel", "Ho Chi Minh City travel",
            "Nha Trang", "Ninh Binh travel guide", "Cat Ba island",
            "Ha Giang", "Tam Dao Vietnam", "Vung Tau", "Cu Chi",
            "Halong Bay", "Mekong Delta", "Vietnam budget travel",
            "transport in Vietnam", "Vietnam eSIM", "Vietnam street food",
            "best time to visit Vietnam", "Vietnam festivals",
        ],
        "audience": {
            "@type": "Audience",
            "audienceType": "International travellers planning a trip to Vietnam",
        },
        "sameAs": same_as,
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer support",
            "email": config.LEGAL_CONTACT_EMAIL,
            "availableLanguage": ["French", "English"],
        },
    }


def website_schema(lang: str = "fr") -> dict:
    from i18n_utils import schema_language, lang_url
    desc = config.SITE_DESCRIPTION_I18N.get(lang, config.SITE_DESCRIPTION)
    base = config.SITE_URL.rstrip("/")
    return {
        "@type": "WebSite",
        "@id": f"{base}/#website",
        "name": config.SITE_NAME,
        "url": base,
        "description": desc,
        "inLanguage": [schema_language("fr"), schema_language("en")],
        "publisher": {"@id": f"{base}/#organization"},
        "about": {"@type": "Place", "name": "Vietnam"},
        "isAccessibleForFree": True,
        "copyrightHolder": {"@id": f"{base}/#organization"},
        "hasPart": {
            "@type": "WebPage",
            "url": base + lang_url("index", lang),
            "name": config.SITE_NAME,
        },
    }


def webpage_schema(
    name: str,
    description: str,
    url: str,
    image: str | None = None,
    lang: str = "fr",
) -> dict:
    """Noeud WebPage de la page courante — rattache à l'Organization et au WebSite.

    Emis sur CHAQUE page (y compris futures) depuis base.html : ancre l'entité de la
    page dans le graphe (utile aux rich results et au knowledge graph de Google).
    """
    from i18n_utils import schema_language

    base = config.SITE_URL.rstrip("/")
    data: dict = {
        "@type": "WebPage",
        "@id": f"{url}#webpage",
        "url": url,
        "name": name or config.SITE_NAME,
        "description": truncate_text(
            description or config.SITE_DESCRIPTION_I18N.get(lang, config.SITE_DESCRIPTION), 200
        ),
        "inLanguage": schema_language(lang),
        "isPartOf": {"@id": f"{base}/#website"},
        "about": {"@id": f"{base}/#organization"},
    }
    if image:
        data["primaryImageOfPage"] = {
            "@type": "ImageObject",
            "url": image,
            "width": 1200,
            "height": 630,
        }
    return data


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
    entities = []
    for item in faq_items:
        q = item.get("question") or item.get("q") or item.get("name") or ""
        a = item.get("answer") or item.get("a") or ""
        if isinstance(a, dict):
            a = a.get("text") or a.get("fr") or a.get("en") or ""
        q, a = str(q).strip(), str(a).strip()
        if q and a:
            entities.append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            })
    if not entities:
        return None
    return {"@type": "FAQPage", "mainEntity": entities}


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
