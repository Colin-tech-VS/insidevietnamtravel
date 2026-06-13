"""Flux RSS 2.0 du blog (FR + EN) — découverte, syndication et signaux GEO/IA."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape, unescape

import config
from admin.store import get_articles
from i18n_utils import lang_url

# Nombre d'articles publiés dans le flux (les plus récents).
FEED_LIMIT = 30


def _site_base() -> str:
    return config.SITE_URL.rstrip("/")


def _strip_html(text: str, max_len: int = 320) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rsplit(" ", 1)[0] + "…"


def _parse_date(value: str | None) -> datetime:
    """Best-effort parsing d'une date d'article → datetime aware (UTC)."""
    if value:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value[: len(fmt) + 2], fmt).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
    return datetime.now(timezone.utc)


def _abs_image(path: str | None) -> str | None:
    if not path:
        return None
    path = path.strip()
    if not path:
        return None
    if "://" in path:
        return path
    return _site_base() + "/" + path.lstrip("/")


def render_blog_feed(lang: str = "fr") -> str:
    base = _site_base()
    lang = lang if lang in ("fr", "en") else "fr"
    self_url = base + ("/en/feed.xml" if lang == "en" else "/feed.xml")
    blog_url = base + lang_url("blog_index", lang)

    if lang == "en":
        title = f"{config.SITE_NAME} — Vietnam travel blog"
        description = config.SITE_DESCRIPTION_I18N.get("en", config.SITE_DESCRIPTION)
        language = "en"
    else:
        title = f"{config.SITE_NAME} — Blog voyage Vietnam"
        description = config.SITE_DESCRIPTION_I18N.get("fr", config.SITE_DESCRIPTION)
        language = "fr"

    articles = get_articles(lang)[:FEED_LIMIT]
    build_date = format_datetime(datetime.now(timezone.utc))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        'xmlns:content="http://purl.org/rss/1.0/modules/content/">',
        "  <channel>",
        f"    <title>{escape(title)}</title>",
        f"    <link>{escape(blog_url)}</link>",
        f"    <description>{escape(description)}</description>",
        f"    <language>{language}</language>",
        f"    <lastBuildDate>{build_date}</lastBuildDate>",
        f"    <generator>{escape(config.SITE_NAME)}</generator>",
        f'    <atom:link href="{escape(self_url)}" rel="self" type="application/rss+xml" />',
    ]

    for article in articles:
        slug = article.get("slug")
        if not slug:
            continue
        url = base + lang_url("article", lang, slug=slug)
        item_title = _strip_html(article.get("title", slug), 180)
        summary = _strip_html(
            article.get("excerpt") or article.get("meta_description") or "", 320
        )
        pub_date = format_datetime(_parse_date(article.get("date") or article.get("updated_at")))
        category = article.get("category") or article.get("city")

        lines.append("    <item>")
        lines.append(f"      <title>{escape(item_title)}</title>")
        lines.append(f"      <link>{escape(url)}</link>")
        lines.append(f'      <guid isPermaLink="true">{escape(url)}</guid>')
        lines.append(f"      <pubDate>{pub_date}</pubDate>")
        if category:
            lines.append(f"      <category>{escape(str(category))}</category>")
        lines.append(f"      <description>{escape(summary)}</description>")
        image = _abs_image(article.get("image"))
        if image:
            mime = (
                "image/webp" if image.endswith(".webp")
                else "image/png" if image.endswith(".png")
                else "image/jpeg"
            )
            lines.append(
                f'      <enclosure url="{escape(image)}" type="{mime}" length="0" />'
            )
        lines.append("    </item>")

    lines.append("  </channel>")
    lines.append("</rss>")
    return "\n".join(lines) + "\n"
