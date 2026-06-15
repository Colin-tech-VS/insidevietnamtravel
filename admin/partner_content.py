"""Contenu personnalisé par type de profil partenaire (activités, galerie, vidéos…)."""

from __future__ import annotations

import re
import uuid
from typing import Any

PROFILE_CONTENT_BLOCKS: dict[str, list[dict[str, Any]]] = {
    "guide": [
        {
            "id": "activities",
            "label": "Circuits & activités",
            "label_en": "Tours & activities",
            "type": "items",
            "max": 10,
            "placeholder_title": "Ex. : Street food tour à Hô Chi Minh-Ville",
            "placeholder_detail": "Durée, langues, nombre de personnes…",
        },
        {
            "id": "gallery",
            "label": "Galerie photos",
            "label_en": "Photo gallery",
            "type": "gallery",
            "max": 8,
        },
    ],
    "agence": [
        {
            "id": "activities",
            "label": "Activités proposées",
            "label_en": "Activities offered",
            "type": "items",
            "max": 12,
            "placeholder_title": "Ex. : Croisière baie d'Halong 2 jours",
            "placeholder_detail": "Inclus, prix indicatif, zone…",
        },
        {
            "id": "packages",
            "label": "Forfaits & séjours",
            "label_en": "Packages & trips",
            "type": "items",
            "max": 8,
            "placeholder_title": "Ex. : Vietnam 10 jours sur mesure",
            "placeholder_detail": "Public cible, budget indicatif…",
        },
        {
            "id": "gallery",
            "label": "Galerie",
            "label_en": "Gallery",
            "type": "gallery",
            "max": 10,
        },
    ],
    "influenceur": [
        {
            "id": "videos",
            "label": "Vidéos",
            "label_en": "Videos",
            "type": "videos",
            "max": 6,
            "placeholder_title": "Titre de la vidéo",
            "placeholder_url": "YouTube, TikTok ou Instagram…",
        },
        {
            "id": "gallery",
            "label": "Photos & visuels",
            "label_en": "Photos & visuals",
            "type": "gallery",
            "max": 12,
        },
        {
            "id": "platforms",
            "label": "Réseaux & liens",
            "label_en": "Social & links",
            "type": "links",
            "max": 6,
            "placeholder_title": "Instagram, TikTok, blog…",
            "placeholder_url": "https://…",
        },
    ],
    "blogueur": [
        {
            "id": "articles",
            "label": "Articles & contenus",
            "label_en": "Articles & content",
            "type": "links",
            "max": 8,
            "placeholder_title": "Titre de l'article",
            "placeholder_url": "https://…",
        },
        {
            "id": "gallery",
            "label": "Galerie",
            "label_en": "Gallery",
            "type": "gallery",
            "max": 8,
        },
    ],
    "hotel": [
        {
            "id": "amenities",
            "label": "Équipements & services",
            "label_en": "Amenities & services",
            "type": "items",
            "max": 12,
            "placeholder_title": "Ex. : Piscine, petit-déjeuner inclus",
            "placeholder_detail": "",
        },
        {
            "id": "rooms",
            "label": "Chambres & hébergements",
            "label_en": "Rooms & stays",
            "type": "items",
            "max": 8,
            "placeholder_title": "Ex. : Suite vue jardin",
            "placeholder_detail": "Capacité, tarif indicatif…",
        },
        {
            "id": "gallery",
            "label": "Photos de l'hébergement",
            "label_en": "Property photos",
            "type": "gallery",
            "max": 12,
        },
    ],
    "autre": [
        {
            "id": "offerings",
            "label": "Prestations",
            "label_en": "Services",
            "type": "items",
            "max": 10,
            "placeholder_title": "Ex. : Atelier cuisine vietnamienne",
            "placeholder_detail": "Détails, durée, public…",
        },
        {
            "id": "gallery",
            "label": "Galerie",
            "label_en": "Gallery",
            "type": "gallery",
            "max": 6,
        },
    ],
}

_URL_RE = re.compile(r"^https?://", re.I)


def content_blocks_for_profile(profile_type: str) -> list[dict[str, Any]]:
    key = (profile_type or "autre").strip().lower()
    return list(PROFILE_CONTENT_BLOCKS.get(key, PROFILE_CONTENT_BLOCKS["autre"]))


def get_profile_content(page: dict | None) -> dict[str, list[dict]]:
    if not page:
        return {}
    extra = page.get("extra") if isinstance(page.get("extra"), dict) else {}
    raw = extra.get("profile_content")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[dict]] = {}
    for block_id, items in raw.items():
        if isinstance(items, list):
            out[block_id] = [dict(i) for i in items if isinstance(i, dict)]
    return out


def _clean_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not _URL_RE.match(url):
        url = f"https://{url.lstrip('/')}"
    return url[:500]


def _parse_items_block(form, block_id: str, *, max_items: int) -> list[dict]:
    titles = form.getlist(f"pc_{block_id}_title[]") or form.getlist(f"pc_{block_id}_title")
    details = form.getlist(f"pc_{block_id}_detail[]") or form.getlist(f"pc_{block_id}_detail")
    items: list[dict] = []
    for i, title in enumerate(titles):
        title = (title or "").strip()[:200]
        detail = (details[i] if i < len(details) else "").strip()[:400]
        if not title and not detail:
            continue
        if not title:
            continue
        items.append({"type": "item", "title": title, "detail": detail})
        if len(items) >= max_items:
            break
    return items


def _parse_links_block(form, block_id: str, *, max_items: int) -> list[dict]:
    labels = form.getlist(f"pc_{block_id}_label[]") or form.getlist(f"pc_{block_id}_label")
    urls = form.getlist(f"pc_{block_id}_url[]") or form.getlist(f"pc_{block_id}_url")
    items: list[dict] = []
    for i, label in enumerate(labels):
        label = (label or "").strip()[:120]
        url = _clean_url(urls[i] if i < len(urls) else "")
        if not label or not url:
            continue
        items.append({"type": "link", "label": label, "url": url})
        if len(items) >= max_items:
            break
    return items


def _parse_videos_block(form, block_id: str, *, max_items: int) -> list[dict]:
    titles = form.getlist(f"pc_{block_id}_title[]") or form.getlist(f"pc_{block_id}_title")
    urls = form.getlist(f"pc_{block_id}_url[]") or form.getlist(f"pc_{block_id}_url")
    items: list[dict] = []
    for i, title in enumerate(titles):
        title = (title or "").strip()[:160]
        url = _clean_url(urls[i] if i < len(urls) else "")
        if not url:
            continue
        items.append({"type": "video", "title": title or "Vidéo", "url": url})
        if len(items) >= max_items:
            break
    return items


def _parse_gallery_block(form, files, block_id: str, partner_slug: str, *, max_items: int) -> list[dict]:
    from admin.image_service import MAX_PARTNER_COVER_BYTES, store_partner_gallery_webp, validate_image_bytes

    captions = form.getlist(f"pc_{block_id}_caption[]") or form.getlist(f"pc_{block_id}_caption")
    existing_urls = form.getlist(f"pc_{block_id}_existing[]") or form.getlist(f"pc_{block_id}_existing")
    items: list[dict] = []

    row_count = max(len(captions), len(existing_urls))
    for i in range(row_count):
        if len(items) >= max_items:
            break
        caption = (captions[i] if i < len(captions) else "").strip()[:160]
        existing = (existing_urls[i] if i < len(existing_urls) else "").strip()
        file_key = f"pc_{block_id}_file_{i}"
        upload = files.get(file_key) if files else None
        url = existing
        if upload and getattr(upload, "filename", None):
            raw = upload.read()
            if raw:
                validated = validate_image_bytes(raw, max_bytes=MAX_PARTNER_COVER_BYTES)
                item_id = uuid.uuid4().hex[:10]
                url = store_partner_gallery_webp(partner_slug, item_id, validated)
        elif not url:
            continue
        items.append({"type": "image", "url": url, "caption": caption})

    return items


def save_profile_content_from_form(
    partner_id: str,
    profile_type: str,
    form,
    files,
) -> dict:
    """Parse le formulaire vitrine et enregistre extra.profile_content."""
    from admin.partner_portal_service import get_page_by_partner

    page = get_page_by_partner(partner_id)
    if not page:
        raise ValueError("Créez d'abord votre page (wizard étapes 1–3).")
    if page.get("status") == "ai_review":
        raise ValueError("Vérification en cours — patientez.")

    slug = (page.get("slug") or "partenaire").strip()
    extra = dict(page.get("extra") or {})
    profile_content: dict[str, list[dict]] = dict(get_profile_content(page))

    for block in content_blocks_for_profile(profile_type):
        block_id = block["id"]
        block_type = block["type"]
        max_items = int(block.get("max") or 8)
        if block_type == "items":
            profile_content[block_id] = _parse_items_block(form, block_id, max_items=max_items)
        elif block_type == "links":
            profile_content[block_id] = _parse_links_block(form, block_id, max_items=max_items)
        elif block_type == "videos":
            profile_content[block_id] = _parse_videos_block(form, block_id, max_items=max_items)
        elif block_type == "gallery":
            profile_content[block_id] = _parse_gallery_block(
                form, files, block_id, slug, max_items=max_items
            )

    extra["profile_content"] = profile_content
    _persist_extra(partner_id, extra)
    return get_page_by_partner(partner_id) or {}


def _persist_extra(partner_id: str, extra: dict) -> None:
    import json

    from admin.database import get_connection, is_postgres
    from admin.partner_portal_service import _now_iso

    extra_json = json.dumps(extra, ensure_ascii=False)
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                "UPDATE partner_pages SET extra_json = %s, updated_at = %s WHERE partner_id = %s",
                (extra_json, now, partner_id),
            )
        else:
            cur.execute(
                "UPDATE partner_pages SET extra_json = ?, updated_at = ? WHERE partner_id = ?",
                (extra_json, now, partner_id),
            )


def public_content_sections(page: dict, partner: dict, *, lang: str = "fr") -> list[dict]:
    """Sections à afficher sur la fiche publique."""
    profile_type = (partner.get("profile_type") or "autre").strip().lower()
    stored = get_profile_content(page)
    blocks = content_blocks_for_profile(profile_type)
    is_en = lang == "en"
    sections: list[dict] = []
    for block in blocks:
        items = stored.get(block["id"]) or []
        if not items:
            continue
        sections.append({
            "id": block["id"],
            "label": block.get("label_en") if is_en and block.get("label_en") else block["label"],
            "type": block["type"],
            "items": items,
        })
    return sections
