"""Création manuelle d'articles et destinations (sans IA)."""

from __future__ import annotations

import re
from datetime import date

from admin.store import slugify

CATEGORY_LABELS = {
    "practical": "Pratique",
    "food": "Gastronomie",
    "itinerary": "Itinéraire",
    "budget": "Budget",
}


def _ensure_html(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if "<" in text and ">" in text:
        return text
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{p.replace(chr(10), ' ')}</p>" for p in parts)


def _parse_lines(text: str) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text or "", flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_list_items(html: str) -> list[str]:
    items = re.findall(r"<li[^>]*>(.*?)</li>", html or "", flags=re.DOTALL | re.IGNORECASE)
    if items:
        return [_strip_html(i) for i in items if _strip_html(i)]
    plain = _strip_html(html)
    return _parse_lines(plain) if plain else []


def _parse_things_from_html(html: str) -> list[dict]:
    items = []
    for block in re.findall(r"<li[^>]*>(.*?)</li>", html or "", flags=re.DOTALL | re.IGNORECASE):
        strong = re.search(r"<strong[^>]*>(.*?)</strong>", block, flags=re.DOTALL | re.IGNORECASE)
        if strong:
            title = _strip_html(strong.group(1))
            desc = _strip_html(re.sub(r"<strong[^>]*>.*?</strong>", "", block, flags=re.DOTALL | re.IGNORECASE))
            desc = desc.lstrip("—-–:| ").strip()
            items.append({"title": title, "desc": desc})
            continue
        text = _strip_html(block)
        if "|" in text:
            title, desc = text.split("|", 1)
        elif " — " in text:
            title, desc = text.split(" — ", 1)
        elif " - " in text:
            title, desc = text.split(" - ", 1)
        else:
            title, desc = text, ""
        items.append({"title": title.strip(), "desc": desc.strip()})

    if items:
        return items

    headings = re.findall(
        r"<h[23][^>]*>(.*?)</h[23]>\s*(?:<p[^>]*>(.*?)</p>)?",
        html or "",
        flags=re.DOTALL | re.IGNORECASE,
    )
    for title_raw, desc_raw in headings:
        title = _strip_html(title_raw)
        desc = _strip_html(desc_raw or "")
        if title:
            items.append({"title": title, "desc": desc})

    if items:
        return items

    return _parse_pipe_items(_strip_html(html))


def _parse_pipe_items(text: str) -> list[dict]:
    items = []
    for line in _parse_lines(text):
        if "|" in line:
            title, desc = line.split("|", 1)
        elif " — " in line:
            title, desc = line.split(" — ", 1)
        elif " - " in line:
            title, desc = line.split(" - ", 1)
        else:
            title, desc = line, ""
        items.append({"title": title.strip(), "desc": desc.strip()})
    return items


def _word_count(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(re.sub(r"\s+", " ", text).strip().split())


def build_manual_article(form) -> dict:
    title = (form.get("title") or "").strip()
    if not title:
        raise ValueError("Le titre est obligatoire.")

    city = (form.get("city") or "").strip()
    if not city:
        raise ValueError("La ville est obligatoire.")

    content = _ensure_html(form.get("content") or "")
    if not content or not _strip_html(content):
        raise ValueError("Le contenu est obligatoire.")

    excerpt = _strip_html(form.get("excerpt") or "")
    if not excerpt:
        raise ValueError("L'extrait SEO est obligatoire.")

    category = form.get("category") or "practical"
    slug = slugify((form.get("slug") or "").strip() or title)
    tags_raw = form.get("tags") or ""
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    if city not in tags:
        tags.insert(0, city)

    wc = _word_count(content)
    return {
        "slug": slug,
        "title": title,
        "excerpt": excerpt[:160],
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, "Pratique"),
        "date": date.today().isoformat(),
        "read_time": max(5, round(wc / 200)),
        "word_count": wc,
        "featured": False,
        "tags": tags[:12],
        "content": content,
        "city": city,
        "ai_generated": False,
        "manual": True,
    }


def build_manual_destination(form) -> dict:
    name = (form.get("name") or "").strip()
    if not name:
        raise ValueError("Le nom de la destination est obligatoire.")

    city = (form.get("city") or name).strip()
    slug = slugify((form.get("slug") or "").strip() or name)
    from data.affiliate_urls import get_location_meta

    loc = get_location_meta(slug, name=name)
    if city and "Vietnam" not in city:
        loc["booking_city"] = f"{city}, Vietnam"
    tagline = (form.get("tagline") or "").strip()
    meta_title = (form.get("meta_title") or "").strip()
    meta_description = _strip_html(form.get("meta_description") or "")
    overview = _ensure_html(form.get("overview") or "")

    if not tagline:
        raise ValueError("L'accroche est obligatoire.")
    if not meta_title:
        raise ValueError("Le meta title est obligatoire.")
    if not meta_description:
        raise ValueError("La meta description est obligatoire.")
    if not overview or not _strip_html(overview):
        raise ValueError("La vue d'ensemble est obligatoire.")

    things = _parse_things_from_html(form.get("things_to_do") or "")
    tips = _parse_list_items(form.get("tips") or "")

    return {
        "slug": slug,
        "name": name,
        "meta_title": meta_title,
        "meta_description": meta_description[:160],
        "tagline": tagline,
        "overview": overview,
        "things_to_do": things or [
            {"title": f"Découvrir {name}", "desc": "À compléter depuis l'admin."},
        ],
        "hotels": [],
        "activities": [],
        "tips": tips or [f"Prévoyez 2–4 jours pour explorer {name}."],
        "location_meta": loc,
        "city": city,
        "ai_generated": False,
        "manual": True,
        "updated_at": date.today().isoformat(),
    }
