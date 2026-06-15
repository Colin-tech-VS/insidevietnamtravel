"""Création manuelle de pages SEO (sans IA)."""

from __future__ import annotations

import re
from datetime import date

from admin.seo_pages_service import _parse_keywords, validate_slug
from i18n_utils import merge_bilingual_article


def _ensure_html(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if "<" in text and ">" in text:
        return text
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{p.replace(chr(10), ' ')}</p>" for p in parts)


def _read_time(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    words = len(text.split())
    return max(5, round(words / 200))


def build_manual_seo_page(form) -> dict:
    title_fr = (form.get("title_fr") or form.get("title") or "").strip()
    if not title_fr:
        raise ValueError("Titre FR obligatoire.")
    slug_raw = (form.get("slug") or title_fr).strip()
    editing_slug = (form.get("editing_slug") or "").strip()
    slug = validate_slug(slug_raw, exclude=editing_slug or None)

    content_fr = _ensure_html(form.get("content_fr") or form.get("content") or "")
    if not content_fr:
        raise ValueError("Contenu FR obligatoire.")

    title_en = (form.get("title_en") or "").strip()
    content_en = _ensure_html(form.get("content_en") or "")
    meta_title_fr = (form.get("meta_title_fr") or form.get("meta_title") or title_fr)[:70].strip()
    meta_title_en = (form.get("meta_title_en") or title_en or meta_title_fr)[:70].strip()
    meta_desc_fr = (form.get("meta_description_fr") or form.get("meta_description") or "")[:160].strip()
    meta_desc_en = (form.get("meta_description_en") or "")[:160].strip()
    excerpt_fr = (form.get("excerpt_fr") or form.get("excerpt") or meta_desc_fr)[:160].strip()
    excerpt_en = (form.get("excerpt_en") or meta_desc_en or excerpt_fr)[:160].strip()
    focus = (form.get("focus_keyword") or "").strip()
    keywords = _parse_keywords(form.get("keywords") or form.get("target_keywords") or "")
    city = (form.get("city") or "").strip()

    fr_data = {
        "title": title_fr,
        "meta_title": meta_title_fr,
        "meta_description": meta_desc_fr or excerpt_fr,
        "excerpt": excerpt_fr,
        "content": content_fr,
        "focus_keyword": focus or (keywords[0] if keywords else title_fr),
        "image_alt": (form.get("image_alt_fr") or title_fr)[:120],
    }
    en_data = {
        "title": title_en or title_fr,
        "meta_title": meta_title_en,
        "meta_description": meta_desc_en or excerpt_en or meta_desc_fr,
        "excerpt": excerpt_en or excerpt_fr,
        "content": content_en or content_fr,
        "focus_keyword": focus or (keywords[0] if keywords else title_en or title_fr),
        "image_alt": (form.get("image_alt_en") or title_en or title_fr)[:120],
    }
    shared = {
        "slug": slug,
        "city": city,
        "target_keywords": keywords,
        "page_type": (form.get("page_type") or "landing").strip(),
        "date": date.today().isoformat(),
        "read_time": _read_time(content_fr),
        "manual": True,
        "status": "draft",
    }
    if editing_slug:
        shared["editing_slug"] = editing_slug
    page = merge_bilingual_article(fr_data, en_data, shared)
    if form.get("image"):
        page["image"] = form.get("image").strip()
    return page
