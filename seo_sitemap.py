"""Sitemap XML — génération automatique depuis routes + contenu (admin/store)."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Callable

import config
from admin.store import get_articles, get_categories, get_destinations_dict
from data.itineraries import ITINERARIES
from data.pillars import hub_slugs
from i18n_utils import ROUTE_PATHS, SUPPORTED_LANGS, lang_url

# Pages statiques indexables (clés = ROUTE_PATHS)
SITEMAP_STATIC: dict[str, dict[str, str]] = {
    "index": {"priority": "1.0", "changefreq": "weekly"},
    "destinations_index": {"priority": "0.92", "changefreq": "weekly"},
    "blog_index": {"priority": "0.9", "changefreq": "daily"},
    "prepare_trip": {"priority": "0.95", "changefreq": "weekly"},
    "best_season": {"priority": "0.85", "changefreq": "monthly"},
    "budget_tool": {"priority": "0.85", "changefreq": "monthly"},
    "visa_tool": {"priority": "0.85", "changefreq": "monthly"},
    "essentials_tool": {"priority": "0.7", "changefreq": "monthly"},
    "useful_apps": {"priority": "0.8", "changefreq": "monthly"},
    "safety_guide": {"priority": "0.82", "changefreq": "monthly"},
    "customs_guide": {"priority": "0.82", "changefreq": "monthly"},
    "phrases_guide": {"priority": "0.82", "changefreq": "monthly"},
    "events_calendar": {"priority": "0.88", "changefreq": "weekly"},
    "about": {"priority": "0.5", "changefreq": "monthly"},
    "become_partner": {"priority": "0.65", "changefreq": "monthly"},
    "partners_index": {"priority": "0.75", "changefreq": "weekly"},
    "privacy": {"priority": "0.4", "changefreq": "yearly"},
    "legal_notices": {"priority": "0.4", "changefreq": "yearly"},
}

# Routes dynamiques : endpoint → (priority, changefreq, resolver)
DynamicResolver = Callable[[], list[tuple[str, str | None]]]


def _abs_image(path: str | None) -> str | None:
    """Normalise un chemin image (store ou /static) en URL absolue pour le sitemap."""
    if not path:
        return None
    path = path.strip()
    if not path:
        return None
    if "://" in path:
        return path
    base = _site_base()
    return base + ("/" + path.lstrip("/"))


def _article_entries() -> list[tuple[str, str | None, str | None]]:
    seen: set[str] = set()
    entries: list[tuple[str, str | None, str | None]] = []
    for article in get_articles():
        slug = article.get("slug")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        lastmod = article.get("date") or article.get("updated_at")
        entries.append((slug, lastmod, _abs_image(article.get("image"))))
    return entries


def _destination_entries() -> list[tuple[str, str | None, str | None]]:
    raw = get_destinations_dict()
    entries: list[tuple[str, str | None, str | None]] = []
    for slug, dest in raw.items():
        lastmod = dest.get("updated_at")
        entries.append((slug, lastmod, _abs_image(dest.get("image"))))
    return entries


def _category_entries() -> list[tuple[str, str | None]]:
    return [(key, None) for key in get_categories().keys()]


def _itinerary_entries() -> list[tuple[str, str | None]]:
    return [(slug, None) for slug in ITINERARIES.keys()]


def _pillar_entries() -> list[tuple[str, str | None]]:
    return [(slug, None) for slug in hub_slugs()]


def _partner_page_entries() -> list[tuple[str, str | None, str | None]]:
    from admin.partner_portal_service import list_public_partners

    entries: list[tuple[str, str | None, str | None]] = []
    for page in list_public_partners():
        slug = (page.get("slug") or "").strip()
        if not slug:
            continue
        lastmod = page.get("published_at") or page.get("updated_at")
        entries.append((slug, lastmod, _abs_image(page.get("image_url"))))
    return entries


SITEMAP_DYNAMIC: dict[str, dict] = {
    "article": {
        "priority": "0.8",
        "changefreq": "weekly",
        "param": "slug",
        "items": _article_entries,
    },
    "destination_page": {
        "priority": "0.9",
        "changefreq": "monthly",
        "param": "slug",
        "items": _destination_entries,
    },
    "category": {
        "priority": "0.7",
        "changefreq": "weekly",
        "param": "category",
        "items": _category_entries,
    },
    "itinerary": {
        "priority": "0.9",
        "changefreq": "monthly",
        "param": "slug",
        "items": _itinerary_entries,
    },
    "pillar": {
        "priority": "0.9",
        "changefreq": "weekly",
        "param": "slug",
        "items": _pillar_entries,
    },
    "partner_public": {
        "priority": "0.72",
        "changefreq": "monthly",
        "param": "slug",
        "items": _partner_page_entries,
    },
}


def _validate_sitemap_config() -> None:
    for endpoint in SITEMAP_STATIC:
        if endpoint not in ROUTE_PATHS:
            raise ValueError(f"SITEMAP_STATIC endpoint « {endpoint} » missing from ROUTE_PATHS")
    for endpoint in SITEMAP_DYNAMIC:
        if endpoint not in ROUTE_PATHS:
            raise ValueError(f"SITEMAP_DYNAMIC endpoint « {endpoint} » missing from ROUTE_PATHS")


_validate_sitemap_config()


@dataclass
class SitemapUrl:
    loc: str
    priority: str
    changefreq: str | None = None
    lastmod: str | None = None
    alternates: list[tuple[str, str]] = field(default_factory=list)
    images: list[str] = field(default_factory=list)


def _site_base() -> str:
    return config.SITE_URL.rstrip("/")


def _alternate_links(endpoint: str, **kwargs) -> list[tuple[str, str]]:
    base = _site_base()
    links = [(lang, base + lang_url(endpoint, lang, **kwargs)) for lang in SUPPORTED_LANGS]
    links.append(("x-default", base + lang_url(endpoint, "fr", **kwargs)))
    return links


def _add_url(
    urls: list[SitemapUrl],
    *,
    endpoint: str,
    priority: str,
    changefreq: str | None,
    lastmod: str | None,
    images: list[str] | None = None,
    **path_kwargs,
) -> None:
    base = _site_base()
    alternates = _alternate_links(endpoint, **path_kwargs)
    for lang in SUPPORTED_LANGS:
        urls.append(SitemapUrl(
            loc=base + lang_url(endpoint, lang, **path_kwargs),
            priority=priority,
            changefreq=changefreq,
            lastmod=lastmod,
            alternates=alternates,
            images=list(images or []),
        ))


def build_sitemap_urls() -> list[SitemapUrl]:
    """Construit toutes les URLs publiques indexables (FR + EN)."""
    urls: list[SitemapUrl] = []

    for endpoint, meta in SITEMAP_STATIC.items():
        _add_url(
            urls,
            endpoint=endpoint,
            priority=meta["priority"],
            changefreq=meta.get("changefreq"),
            lastmod=None,
        )

    for endpoint, meta in SITEMAP_DYNAMIC.items():
        param = meta["param"]
        resolver: DynamicResolver = meta["items"]
        for entry in resolver():
            slug, lastmod = entry[0], entry[1]
            image = entry[2] if len(entry) > 2 else None
            _add_url(
                urls,
                endpoint=endpoint,
                priority=meta["priority"],
                changefreq=meta.get("changefreq"),
                lastmod=lastmod,
                images=[image] if image else None,
                **{param: slug},
            )

    return urls


def render_sitemap_xml(urls: list[SitemapUrl] | None = None) -> str:
    urls = urls if urls is not None else build_sitemap_urls()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml"',
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    ]
    for entry in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(entry.loc)}</loc>")
        if entry.lastmod:
            lines.append(f"    <lastmod>{escape(entry.lastmod)}</lastmod>")
        if entry.changefreq:
            lines.append(f"    <changefreq>{entry.changefreq}</changefreq>")
        lines.append(f"    <priority>{entry.priority}</priority>")
        for hreflang, href in entry.alternates:
            lines.append(
                f'    <xhtml:link rel="alternate" hreflang="{escape(hreflang)}" '
                f'href="{escape(href)}" />'
            )
        for image_loc in entry.images:
            lines.append("    <image:image>")
            lines.append(f"      <image:loc>{escape(image_loc)}</image:loc>")
            lines.append("    </image:image>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"
