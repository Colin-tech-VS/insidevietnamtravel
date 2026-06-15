"""Pages SEO landing — stockage KV, CRUD et publication."""

from __future__ import annotations

import copy
from datetime import date

from admin.kv_store import get_json, set_json
from admin.store import get_article_by_slug, get_destinations_dict, slugify
from i18n_utils import ARTICLE_I18N_FIELDS, wrap_article_i18n

KV_KEY = "seo_pages"
FILE_NAME = "seo_pages.json"

RESERVED_SEO_SLUGS = frozenset({
    "seo", "blog", "admin", "guide", "partenaire", "partners", "itineraries",
    "contact", "newsletter", "destinations-vietnam", "partenaires-vietnam",
})


def _raw_pages() -> list:
    stored = get_json(KV_KEY, None, file_name=FILE_NAME)
    if stored is None:
        set_json(KV_KEY, [], file_name=FILE_NAME)
        return []
    return stored if isinstance(stored, list) else []


def wrap_seo_page(page: dict) -> dict:
    """Structure i18n identique aux articles (title, meta, content…)."""
    return wrap_article_i18n(page)


def localize_seo_page(page: dict, lang: str | None = None) -> dict:
    from i18n_utils import localize_article

    return localize_article(page, lang)


def _auto_translate_page(page: dict) -> dict:
    page = wrap_seo_page(page)
    en = page.get("i18n", {}).get("en", {})
    if en.get("content"):
        return page
    try:
        from admin.groq_translate import translate_article_block

        fr = page["i18n"]["fr"]
        translated = translate_article_block({**page, **fr})
        page["i18n"]["en"] = {k: translated.get(k, fr.get(k, "")) for k in fr}
    except Exception:
        pass
    return page


def save_pages(pages: list) -> None:
    normalized = [_auto_translate_page(wrap_seo_page(p)) for p in pages]
    set_json(KV_KEY, normalized, file_name=FILE_NAME)


def get_seo_pages(lang: str | None = None, *, published_only: bool = False) -> list:
    pages = [wrap_seo_page(p) for p in _raw_pages()]
    if published_only:
        pages = [p for p in pages if (p.get("status") or "published") == "published"]
    pages.sort(key=lambda p: p.get("published_at") or p.get("updated_at") or "", reverse=True)
    if lang:
        return [localize_seo_page(p, lang) for p in pages]
    return pages


def get_published_seo_pages(lang: str | None = None) -> list:
    return get_seo_pages(lang, published_only=True)


def get_seo_page_by_slug(slug: str, lang: str | None = None) -> dict | None:
    slug = (slug or "").strip()
    page = next((p for p in _raw_pages() if p.get("slug") == slug), None)
    if not page:
        return None
    page = wrap_seo_page(page)
    if (page.get("status") or "published") != "published":
        return None
    return localize_seo_page(page, lang) if lang else page


def get_seo_page_raw(slug: str) -> dict | None:
    page = next((p for p in _raw_pages() if p.get("slug") == slug), None)
    return wrap_seo_page(page) if page else None


def validate_slug(slug: str, *, exclude: str | None = None) -> str:
    slug = slugify(slug)
    if not slug:
        raise ValueError("Slug invalide.")
    if slug in RESERVED_SEO_SLUGS:
        raise ValueError(f"Slug réservé : « {slug} ».")
    if get_destinations_dict().get(slug):
        raise ValueError(f"Conflit avec une destination existante : /{slug}")
    if get_article_by_slug(slug):
        raise ValueError(f"Conflit avec un article existant : /blog/{slug}")
    existing = get_seo_page_raw(slug)
    if existing and slug != (exclude or ""):
        raise ValueError(f"Page SEO déjà publiée : /seo/{slug}")
    return slug


def _parse_keywords(raw) -> list[str]:
    if isinstance(raw, list):
        items = [str(k).strip() for k in raw if str(k).strip()]
    else:
        text = str(raw or "")
        items = []
        for part in text.replace(";", ",").split(","):
            for line in part.splitlines():
                kw = line.strip()
                if kw:
                    items.append(kw)
    seen: set[str] = set()
    out: list[str] = []
    for kw in items:
        key = kw.lower()
        if key not in seen:
            seen.add(key)
            out.append(kw)
    return out[:20]


def add_seo_page(page: dict) -> dict:
    page = wrap_seo_page(page)
    slug = validate_slug(page.get("slug") or page.get("title") or "")
    page["slug"] = slug
    page["status"] = "published"
    page["target_keywords"] = _parse_keywords(page.get("target_keywords") or [])
    today = date.today().isoformat()
    page.setdefault("published_at", today)
    page["updated_at"] = today
    pages = [p for p in _raw_pages() if p.get("slug") != slug]
    pages.insert(0, page)
    save_pages(pages)
    return page


def replace_seo_page(old_slug: str, page: dict) -> dict:
    old_slug = (old_slug or "").strip()
    page = wrap_seo_page(page)
    new_slug = slugify(page.get("slug") or old_slug)
    validate_slug(new_slug, exclude=old_slug)
    page["slug"] = new_slug
    page["status"] = "published"
    page["target_keywords"] = _parse_keywords(page.get("target_keywords") or [])
    page["updated_at"] = date.today().isoformat()
    pages = _raw_pages()
    found = False
    for i, raw in enumerate(pages):
        if raw.get("slug") != old_slug:
            continue
        page.setdefault("published_at", raw.get("published_at") or date.today().isoformat())
        pages.pop(i)
        found = True
        break
    if not found:
        raise ValueError(f"Page SEO introuvable : {old_slug}")
    pages = [p for p in pages if p.get("slug") != new_slug]
    pages.insert(0, page)
    save_pages(pages)
    return page


def delete_seo_page(slug: str) -> None:
    slug = (slug or "").strip()
    pages = [p for p in _raw_pages() if p.get("slug") != slug]
    if len(pages) == len(_raw_pages()):
        raise ValueError(f"Page SEO introuvable : {slug}")
    save_pages(pages)


def build_manual_seo_page(form) -> dict:
    """Construit un brouillon/page depuis le formulaire admin."""
    from admin.seo_manual import build_manual_seo_page as _build

    return _build(form)
