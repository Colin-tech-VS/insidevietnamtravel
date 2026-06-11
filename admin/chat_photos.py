"""Photos pour le chat Mai — priorité au site, complément Pixabay si demandé."""

from __future__ import annotations

import re

import config

_PHOTO_INTENT_WORDS = (
    "photo", "photos", "image", "images", "picture", "pictures", "pic", "pics",
    "montre", "montrer", "montrez", "voir", "illustre", "illustrer", "aperçu",
    "aperçu", "visuel", "envoie", "envoyer", "show me", "look at", "gallery",
    "photograph", "photographie",
)

_PHOTO_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 600.0


def wants_photos(text: str) -> bool:
    hay = (text or "").lower()
    return any(w in hay for w in _PHOTO_INTENT_WORDS)


def _abs_url(path: str) -> str:
    path = (path or "").strip()
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return config.SITE_URL.rstrip("/") + (path if path.startswith("/") else "/" + path)


def _site_photos(slug: str | None, lang: str, *, max_n: int = 2) -> list[dict]:
    from admin.image_service import (
        _photo_ids_for_destination,
        persistent_image_url,
        pool_image_url,
    )
    from admin.store import get_articles, get_destinations_dict

    lang = "en" if lang == "en" else "fr"
    out: list[dict] = []
    seen: set[str] = set()

    def add(url: str | None, alt: str, *, caption: str = "", page_url: str = "") -> None:
        if not url or len(out) >= max_n:
            return
        resolved = persistent_image_url(url, None, url if url.startswith("http") else None)
        if not resolved:
            resolved = url
        key = resolved.split("?")[0]
        if key in seen:
            return
        seen.add(key)
        item: dict = {
            "url": _abs_url(resolved) if resolved.startswith("/") else resolved,
            "alt": (alt or "Vietnam")[:140],
            "source": "site",
            "credit": "Inside Vietnam Travel",
        }
        if caption:
            item["caption"] = caption[:120]
        if page_url:
            item["page_url"] = _abs_url(page_url)
        out.append(item)

    if slug:
        dest = get_destinations_dict(lang).get(slug, {})
        name = dest.get("name") or slug.replace("-", " ")
        img = persistent_image_url(
            dest.get("image"),
            dest.get("image_photo_id"),
            dest.get("image_source_url"),
        )
        from i18n_utils import lang_url
        page = _abs_url(lang_url("destination_page", lang, slug=slug))
        add(img, name, caption=dest.get("tagline", "") or name, page_url=page)

        for pid in _photo_ids_for_destination(slug):
            if len(out) >= max_n:
                break
            add(pool_image_url(pid), name, page_url=page)

    name_fold = ""
    if slug:
        from admin.store import get_destinations_dict
        name_fold = (get_destinations_dict(lang).get(slug, {}).get("name") or "").lower()

    for art in get_articles(lang):
        if len(out) >= max_n:
            break
        hay = f"{art.get('title', '')} {art.get('excerpt', '')} {art.get('city', '')}".lower()
        if slug and name_fold and name_fold not in hay and slug.replace("-", " ") not in hay:
            continue
        img = persistent_image_url(
            art.get("image"),
            art.get("image_photo_id"),
            art.get("image_source_url"),
        )
        if not img:
            continue
        from i18n_utils import lang_url
        add(
            img,
            art.get("image_alt") or art.get("title", ""),
            caption=art.get("title", "")[:120],
            page_url=_abs_url(lang_url("article", lang, slug=art["slug"])),
        )

    return out


def _pixabay_photos(query: str, *, max_n: int = 2, seed_base: int = 0) -> list[dict]:
    from admin.image_service import pixabay_photo_url

    out: list[dict] = []
    seen: set[str] = set()
    for i in range(max_n):
        try:
            url = pixabay_photo_url(query, seed_base + i)
        except Exception:
            break
        key = url.split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "url": url,
            "alt": query[:140],
            "source": "web",
            "credit": "Pixabay",
        })
    return out


def _web_photos(query: str, slug: str | None, lang: str, *, max_n: int) -> list[dict]:
    if max_n <= 0:
        return []
    cache_key = f"{lang}:{slug or ''}:{query[:80]}"
    import time
    now = time.monotonic()
    cached = _PHOTO_CACHE.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1][:max_n]

    from admin.image_service import destination_pixabay_query
    from admin.store import get_destinations_dict

    q = query.strip()
    if slug:
        dest = get_destinations_dict(lang).get(slug, {})
        q = destination_pixabay_query(slug, dest)
    elif len(q) < 8:
        q = f"{q} Vietnam travel"

    photos = _pixabay_photos(q, max_n=max_n, seed_base=abs(hash(query)) % 7)
    _PHOTO_CACHE[cache_key] = (now, photos)
    return photos[:max_n]


def build_chat_photos(
    user_question: str,
    context_text: str,
    lang: str,
    slug: str | None,
    *,
    detect_slug_fn=None,
) -> list[dict]:
    """Jusqu'à 3 photos : d'abord le site, puis Pixabay si besoin."""
    hay = f"{user_question} {context_text}"
    if not wants_photos(hay):
        return []

    if not slug and detect_slug_fn:
        slug = detect_slug_fn(user_question, lang) or detect_slug_fn(context_text, lang)

    site = _site_photos(slug, lang, max_n=2)
    need_web = max(0, 3 - len(site))
    web: list[dict] = []
    if need_web:
        q = user_question
        if slug:
            from admin.store import get_destinations_dict
            name = get_destinations_dict(lang).get(slug, {}).get("name", "")
            if name and name.lower() not in q.lower():
                q = f"{name} {q}"
        web = _web_photos(q, slug, lang, max_n=need_web)

    combined = site + web
    seen: set[str] = set()
    unique: list[dict] = []
    for p in combined:
        key = p.get("url", "").split("?")[0]
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique[:3]
