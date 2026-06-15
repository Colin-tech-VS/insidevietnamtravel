"""Espace partenaires — inscriptions, comptes, pages publiques."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from admin.database import get_connection, is_postgres
from admin.store import slugify

PROFILE_TYPES = [
    ("guide", "Guide local"),
    ("influenceur", "Influenceur / créateur"),
    ("blogueur", "Blogueur voyage"),
    ("agence", "Agence locale"),
    ("hotel", "Hébergement"),
    ("autre", "Autre"),
]
PROFILE_TYPE_KEYS = {k for k, _ in PROFILE_TYPES}
PROFILE_TYPE_LABELS = dict(PROFILE_TYPES)

PAGE_STATUSES = [
    ("draft", "Brouillon"),
    ("ai_review", "Vérification en cours"),
    ("approved", "Validé"),
    ("published", "Publié"),
    ("rejected", "Refusé"),
]
PAGE_STATUS_LABELS = dict(PAGE_STATUSES)

ACCOUNT_STATUSES = [
    ("active", "Actif"),
    ("suspended", "Suspendu"),
]
ACCOUNT_STATUS_LABELS = dict(ACCOUNT_STATUSES)

# Compte partenaire interne — invisible (pas de page publique, absent admin/SEO).
HIDDEN_TEST_PARTNER_EMAIL = "contact@insidevietnamtravel.fr"

_SLUG_RE = re.compile(r"[^a-z0-9\-]+")


def is_hidden_test_partner(account_or_email) -> bool:
    if isinstance(account_or_email, dict):
        email = account_or_email.get("email") or ""
    else:
        email = account_or_email or ""
    return email.strip().lower() == HIDDEN_TEST_PARTNER_EMAIL


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _row_dict(row) -> dict:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "keys"):
        return {k: row[k] for k in row.keys()}
    cols = (
        "id", "email", "password_hash", "first_name", "last_name", "profile_type",
        "business_name", "phone", "city", "website", "languages", "bio", "services",
        "social_links", "status", "created_at", "updated_at",
    )
    return {k: row[i] for i, k in enumerate(cols) if i < len(row)}


def _page_row_dict(row) -> dict:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "keys"):
        return {k: row[k] for k in row.keys()}
    return row


def _parse_json_field(raw: str | None) -> list | dict:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return []


def _parse_extra_json(raw) -> dict:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if not isinstance(raw, str):
        return {}
    try:
        data = json.loads(raw)
        return dict(data) if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _highlights_from_html(html: str | None, *, max_len: int = 500) -> list[str]:
    if not html:
        return []
    from html import unescape

    items: list[str] = []
    for match in re.finditer(r"<li[^>]*>(.*?)</li>", html, re.I | re.S):
        text = unescape(re.sub(r"<[^>]+>", " ", match.group(1)))
        text = " ".join(text.split()).strip()
        if text and len(text) <= max_len:
            items.append(text)
    return items


def _coerce_profile_highlights(raw) -> list[str]:
    """Normalise profile_highlights (list, JSON string, texte multiligne)."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(h).strip() for h in raw if str(h).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(h).strip() for h in parsed if str(h).strip()]
            except Exception:  # noqa: BLE001
                pass
        return _parse_profile_highlights_lines(text)
    return [str(raw).strip()] if str(raw).strip() else []


def _highlights_from_extra(extra: dict | None) -> list[str]:
    """Points forts affichables — profile_highlights (IA/vitrine) ou brouillon highlights."""
    extra = extra or {}
    items = _coerce_profile_highlights(extra.get("profile_highlights"))
    if not items:
        raw = extra.get("highlights") or ""
        for line in re.split(r"[\n\r,;]+", str(raw)):
            line = line.strip()
            if line:
                items.append(line)
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out[:8]


def page_public_highlights(page: dict | None) -> list[str]:
    if not page:
        return []
    return _resolve_public_highlights(page)


def _resolve_public_highlights(page: dict, *, extra: dict | None = None) -> list[str]:
    """Points « Pourquoi choisir » — extra, puis HTML services / à propos."""
    extra = extra if extra is not None else (page.get("extra") if isinstance(page.get("extra"), dict) else {})
    items = _highlights_from_extra(extra)
    if len(items) >= 3:
        return items[:8]
    for html in (page.get("services_html"), page.get("overview_html")):
        items = _highlights_from_pourquoi_section(html)
        if len(items) >= 3:
            return items[:8]
        items = _highlights_from_html(html)
        if len(items) >= 3:
            return items[:8]
    return items[:8]


_POURQUOI_SECTION = re.compile(
    r"<h2[^>]*>\s*(?:Pourquoi\s+choisir|Why\s+(?:travellers?\s+)?choose).*?</h2>\s*(.*?)(?=<h2\b|$)",
    re.I | re.S,
)


def _highlights_from_pourquoi_section(html: str | None) -> list[str]:
    if not html:
        return []
    match = _POURQUOI_SECTION.search(html)
    if not match:
        return []
    return _highlights_from_html(match.group(1))


def _persist_extra_profile_highlights(partner_id: str, highlights: list[str]) -> None:
    """Écrit profile_highlights dans extra_json si absent ou incomplet."""
    if not partner_id or len(highlights) < 3:
        return
    page = get_page_by_partner(partner_id)
    if not page:
        return
    extra = dict(page.get("extra") or {})
    stored = _coerce_profile_highlights(extra.get("profile_highlights"))
    if stored == highlights[:8]:
        return
    extra["profile_highlights"] = highlights[:8]
    now = _now_iso()
    extra_json = json.dumps(extra, ensure_ascii=False)
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


def ensure_page_profile_highlights(page: dict | None, *, persist: bool = False) -> list[str]:
    """Résout les points forts et optionnellement les persiste en BDD."""
    if not page:
        return []
    highlights = _resolve_public_highlights(page)
    if persist and len(highlights) >= 3:
        pid = page.get("partner_id") or ""
        stored = _coerce_profile_highlights((page.get("extra") or {}).get("profile_highlights"))
        if len(stored) < 3:
            _persist_extra_profile_highlights(pid, highlights)
    return highlights


def _parse_profile_highlights_lines(text: str) -> list[str]:
    items: list[str] = []
    for line in re.split(r"[\n\r]+", text or ""):
        line = " ".join(line.split()).strip()
        if line:
            items.append(line[:220])
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out[:8]


def page_vitrine_checklist(page: dict | None) -> dict:
    """État vitrine publique pour le dashboard partenaire."""
    if not page:
        return {
            "has_custom_photo": False,
            "highlights_count": 0,
            "highlights_ok": False,
            "highlights_text": "",
            "highlights_items": ["", "", ""],
            "can_edit": False,
            "checklist": [],
            "image_url": "",
        }
    extra = page.get("extra") if isinstance(page.get("extra"), dict) else {}
    highlights = page_public_highlights(page)
    stored = _coerce_profile_highlights(extra.get("profile_highlights"))
    if stored:
        highlights_text = "\n".join(stored)
    elif highlights:
        highlights_text = "\n".join(highlights)
    elif extra.get("highlights"):
        highlights_text = str(extra.get("highlights") or "").replace(",", "\n")
    else:
        highlights_text = ""
    base_items = stored if stored else (highlights[:8] if highlights else [])
    if not base_items and extra.get("highlights"):
        base_items = _highlights_from_extra({"highlights": extra.get("highlights")})
    highlights_items = list(base_items[:8])
    slot_count = max(3, min(8, len(highlights_items) if highlights_items else 3))
    while len(highlights_items) < slot_count:
        highlights_items.append("")
    has_photo = bool((page.get("image_url") or "").strip())
    can_edit = page.get("status") != "ai_review"
    checklist = [
        {
            "id": "photo",
            "label": "Photo de couverture",
            "ok": has_photo,
            "hint": "Ajoutée" if has_photo else "Par défaut (ville) — ajoutez la vôtre",
        },
        {
            "id": "highlights",
            "label": "Pourquoi choisir ce partenaire",
            "ok": len(highlights) >= 3,
            "hint": f"{len(highlights)} point(s) — min. 3 recommandés",
        },
        {
            "id": "content",
            "label": "Texte & offre (wizard)",
            "ok": bool((extra.get("pitch") or "").strip() and (extra.get("offer_details") or "").strip()),
            "hint": "Accroche et offre détaillée",
        },
    ]
    return {
        "has_custom_photo": has_photo,
        "highlights_count": len(highlights),
        "highlights_ok": len(highlights) >= 3,
        "highlights_text": highlights_text,
        "highlights_items": highlights_items,
        "can_edit": can_edit,
        "checklist": checklist,
        "image_url": (page.get("image_url") or "").strip(),
    }


def _store_partner_image(slug: str, *, file_bytes: bytes | None = None, image_url: str = "") -> str:
    from admin.image_service import store_partner_cover_webp

    return store_partner_cover_webp(slug, file_bytes=file_bytes, image_url=image_url)


def profile_highlights_text_from_form(raw_list: list[str] | None, *, fallback: str = "") -> str:
    """Combine les champs profile_highlights[] du formulaire vitrine."""
    lines = [str(v).strip() for v in (raw_list or []) if str(v).strip()]
    if lines:
        return "\n".join(lines)
    return (fallback or "").strip()


def save_page_vitrine(
    partner_id: str,
    *,
    profile_highlights_text: str = "",
    image_url: str = "",
    image_file: bytes | None = None,
    clear_image: bool = False,
) -> dict:
    """Photo + points « Pourquoi choisir » — conserve le statut (publié/validé)."""
    page = get_page_by_partner(partner_id)
    if not page:
        raise ValueError("Créez d'abord votre page (wizard étapes 1–3).")
    if page.get("status") == "ai_review":
        raise ValueError("Vérification en cours — patientez.")

    slug = (page.get("slug") or "partenaire").strip()
    now = _now_iso()
    extra = dict(page.get("extra") or {})
    new_image = (page.get("image_url") or "").strip()

    text = (profile_highlights_text or "").strip()
    if text:
        highlights = _parse_profile_highlights_lines(text)
        if len(highlights) >= 3:
            extra["profile_highlights"] = highlights
        elif len(highlights) > 0:
            pass
        else:
            resolved = _resolve_public_highlights(page, extra=extra)
            if len(resolved) >= 3:
                extra["profile_highlights"] = resolved[:8]
    else:
        resolved = _resolve_public_highlights(page, extra=extra)
        if len(resolved) >= 3:
            extra["profile_highlights"] = resolved[:8]
        elif not _coerce_profile_highlights(extra.get("profile_highlights")):
            wizard_hl = _highlights_from_extra({"highlights": extra.get("highlights") or ""})
            if len(wizard_hl) >= 3:
                extra["profile_highlights"] = wizard_hl

    if image_file:
        new_image = _store_partner_image(slug, file_bytes=image_file)
    elif clear_image:
        new_image = ""
    elif (image_url or "").strip():
        new_image = _store_partner_image(slug, image_url=image_url.strip())

    extra_json = json.dumps(extra, ensure_ascii=False)
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """UPDATE partner_pages SET extra_json = %s, image_url = %s, updated_at = %s
                   WHERE partner_id = %s""",
                (extra_json, new_image, now, partner_id),
            )
        else:
            cur.execute(
                """UPDATE partner_pages SET extra_json = ?, image_url = ?, updated_at = ?
                   WHERE partner_id = ?""",
                (extra_json, new_image, now, partner_id),
            )
    return get_page_by_partner(partner_id) or {}


def _iso_date(raw) -> str | None:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw.date().isoformat()
    text = str(raw).strip()
    return text[:10] if text else None


def partner_page_publication(page: dict | None, *, is_hidden: bool = False) -> dict:
    """Résumé lisible pour le dashboard partenaire."""
    if not page:
        return {
            "is_validated": False,
            "is_published_public": False,
            "headline": "Aucune page",
            "detail": "Créez votre fiche pour commencer.",
            "badge": "none",
        }
    status = page.get("status") or "draft"
    review_approved = bool((page.get("ai_review") or {}).get("approved"))

    if status == "published":
        if is_hidden:
            return {
                "is_validated": True,
                "is_published_public": False,
                "headline": "Validée — aperçu privé uniquement",
                "detail": "Compte test : la page n’apparaît pas sur le site public ni dans l’annuaire.",
                "badge": "private",
            }
        return {
            "is_validated": True,
            "is_published_public": True,
            "headline": "Page publiée en ligne",
            "detail": "Votre fiche est visible sur insidevietnamtravel.fr et dans l’annuaire partenaires.",
            "badge": "live",
        }
    if status == "approved" or (review_approved and status not in ("rejected", "ai_review", "draft")):
        return {
            "is_validated": True,
            "is_published_public": False,
            "headline": "Validée par l’IA — pas encore en ligne",
            "detail": "Aperçu privé disponible. Publiez en ligne pour rendre la page publique.",
            "badge": "approved",
        }
    if status == "ai_review":
        return {
            "is_validated": False,
            "is_published_public": False,
            "headline": "Vérification en cours",
            "detail": "L’IA analyse votre page — patientez quelques instants.",
            "badge": "pending",
        }
    if status == "rejected":
        return {
            "is_validated": False,
            "is_published_public": False,
            "headline": "Non validée",
            "detail": "Corrigez les points signalés puis relancez la vérification IA.",
            "badge": "rejected",
        }
    return {
        "is_validated": False,
        "is_published_public": False,
        "headline": "Non publiée",
        "detail": "Brouillon — lancez « Vérifier ma page » (validation IA obligatoire).",
        "badge": "draft",
    }


def partner_page_workflow(page: dict | None, *, publication: dict | None = None, is_hidden: bool = False) -> dict:
    """Étapes du parcours partenaire (rédaction → IA → aperçu → publication)."""
    pub = publication or partner_page_publication(page, is_hidden=is_hidden)
    publish_label = "Confirmer l’aperçu" if is_hidden else "Publier en ligne"
    steps = [
        {"id": "draft", "label": "Rédiger", "state": "upcoming"},
        {"id": "verify", "label": "Vérification IA", "state": "upcoming"},
        {"id": "preview", "label": "Aperçu privé", "state": "upcoming"},
        {"id": "publish", "label": publish_label, "state": "upcoming"},
    ]
    if not page:
        steps[0]["state"] = "current"
        return {"steps": steps, "current_id": "draft"}

    status = page.get("status") or "draft"
    extra = page.get("extra") if isinstance(page.get("extra"), dict) else {}
    has_draft = bool((extra.get("pitch") or "").strip())

    if has_draft or status not in ("draft",):
        steps[0]["state"] = "done"

    if status in ("approved", "published"):
        steps[1]["state"] = "done"
        if status == "approved":
            steps[2]["state"] = "current"
            steps[3]["state"] = "upcoming"
        else:
            steps[2]["state"] = "done"
            steps[3]["state"] = "done"
    elif status == "ai_review":
        steps[1]["state"] = "current"
    elif status == "rejected":
        steps[1]["state"] = "current"
    elif has_draft:
        steps[1]["state"] = "current"
    elif steps[0]["state"] != "done":
        steps[0]["state"] = "current"

    current_id = next((s["id"] for s in steps if s["state"] == "current"), steps[-1]["id"])
    if pub.get("is_published_public") or (status == "published" and is_hidden):
        current_id = "publish"
    return {"steps": steps, "current_id": current_id}


def _normalize_page_record(page: dict) -> dict:
    page["extra"] = _parse_extra_json(page.get("extra_json"))
    raw_review = page.get("ai_review_json")
    if raw_review:
        try:
            page["ai_review"] = json.loads(raw_review) if isinstance(raw_review, str) else raw_review
        except Exception:  # noqa: BLE001
            page["ai_review"] = {}
    else:
        page["ai_review"] = {}
    if page.get("published_at"):
        page["published_at"] = _iso_date(page.get("published_at"))
    if page.get("updated_at"):
        page["updated_at"] = _iso_date(page.get("updated_at"))
    return page


def _public_account(row: dict) -> dict:
    out = dict(row)
    out.pop("password_hash", None)
    out["services"] = _parse_json_field(out.get("services"))
    out["social_links"] = _parse_json_field(out.get("social_links"))
    if isinstance(out.get("created_at"), datetime):
        out["created_at"] = out["created_at"].isoformat()
    if isinstance(out.get("updated_at"), datetime):
        out["updated_at"] = out["updated_at"].isoformat()
    return out


def _unique_slug(base: str, *, exclude_id: str = "") -> str:
    slug = _SLUG_RE.sub("-", slugify(base or "partenaire")).strip("-")[:60] or "partenaire"
    with get_connection() as conn:
        cur = conn.cursor()
        candidate = slug
        n = 1
        while True:
            if is_postgres():
                cur.execute(
                    "SELECT id FROM partner_pages WHERE slug = %s AND id <> %s LIMIT 1",
                    (candidate, exclude_id or ""),
                )
            else:
                cur.execute(
                    "SELECT id FROM partner_pages WHERE slug = ? AND id <> ? LIMIT 1",
                    (candidate, exclude_id or ""),
                )
            if not cur.fetchone():
                return candidate
            n += 1
            candidate = f"{slug}-{n}"


def register_partner(
    *,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    password_confirm: str,
    profile_type: str,
    business_name: str = "",
    phone: str = "",
    city: str = "",
    website: str = "",
    languages: str = "",
    bio: str = "",
    services: list | None = None,
    social_links: list | None = None,
) -> dict:
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()
    email = (email or "").strip().lower()
    business_name = (business_name or "").strip()
    profile_type = (profile_type or "").strip().lower()

    if len(first_name) < 2 or len(last_name) < 2:
        raise ValueError("Prénom et nom obligatoires (2 caractères minimum).")
    if not email or "@" not in email:
        raise ValueError("Email invalide.")
    if len(password or "") < 8:
        raise ValueError("Mot de passe : 8 caractères minimum.")
    if password != password_confirm:
        raise ValueError("Les mots de passe ne correspondent pas.")
    if profile_type not in PROFILE_TYPE_KEYS:
        raise ValueError("Type de profil invalide.")
    if not business_name and profile_type != "influenceur":
        raise ValueError("Nom de votre activité / marque obligatoire.")
    if not (bio or "").strip() or len((bio or "").strip()) < 40:
        raise ValueError("Présentez votre activité (40 caractères minimum).")

    from admin.partner_discovery import location_from_destination
    loc = location_from_destination(city, required=True)
    city = loc["name"]

    if find_account_by_email(email):
        raise ValueError("Un compte existe déjà avec cet email.")

    pid = uuid.uuid4().hex[:16]
    now = _now_iso()
    services_json = json.dumps(services or [], ensure_ascii=False)
    social_json = json.dumps(social_links or [], ensure_ascii=False)
    pw_hash = generate_password_hash(password)

    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """INSERT INTO partner_accounts
                   (id, email, password_hash, first_name, last_name, profile_type,
                    business_name, phone, city, website, languages, bio, services,
                    social_links, status, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s,%s)""",
                (
                    pid, email, pw_hash, first_name, last_name, profile_type,
                    business_name, (phone or "").strip(), (city or "").strip(),
                    (website or "").strip(), (languages or "").strip(), bio.strip(),
                    services_json, social_json, now, now,
                ),
            )
        else:
            cur.execute(
                """INSERT INTO partner_accounts
                   (id, email, password_hash, first_name, last_name, profile_type,
                    business_name, phone, city, website, languages, bio, services,
                    social_links, status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?)""",
                (
                    pid, email, pw_hash, first_name, last_name, profile_type,
                    business_name, (phone or "").strip(), (city or "").strip(),
                    (website or "").strip(), (languages or "").strip(), bio.strip(),
                    services_json, social_json, now, now,
                ),
            )
    return get_account_by_id(pid) or {}


def create_partner_by_admin(
    *,
    first_name: str,
    last_name: str,
    email: str,
    password: str = "",
    profile_type: str,
    business_name: str = "",
    phone: str = "",
    city: str = "",
    website: str = "",
    languages: str = "",
    bio: str = "",
    admin_note: str = "",
    create_page: bool = True,
) -> dict:
    """Crée un compte espace partenaire depuis l'admin (contact bouche-à-oreille, etc.)."""
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()
    email = (email or "").strip().lower()
    business_name = (business_name or "").strip()
    profile_type = (profile_type or "").strip().lower()
    bio = (bio or "").strip()
    temp_password = (password or "").strip() or secrets.token_urlsafe(10)

    if len(first_name) < 2 or len(last_name) < 2:
        raise ValueError("Prénom et nom obligatoires (2 caractères minimum).")
    if not email or "@" not in email:
        raise ValueError("Email invalide.")
    if len(temp_password) < 8:
        raise ValueError("Mot de passe : 8 caractères minimum (ou laissez vide pour génération auto).")
    if profile_type not in PROFILE_TYPE_KEYS:
        raise ValueError("Type de profil invalide.")
    if not business_name and profile_type != "influenceur":
        raise ValueError("Nom de l'activité / marque obligatoire pour ce type de profil.")
    if find_account_by_email(email):
        raise ValueError("Un compte espace partenaire existe déjà avec cet email.")

    from admin.partner_discovery import location_from_destination
    if (city or "").strip():
        city = location_from_destination(city, required=True)["name"]

    pid = uuid.uuid4().hex[:16]
    now = _now_iso()
    pw_hash = generate_password_hash(temp_password)
    services_json = json.dumps([], ensure_ascii=False)
    social_json = json.dumps([], ensure_ascii=False)

    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """INSERT INTO partner_accounts
                   (id, email, password_hash, first_name, last_name, profile_type,
                    business_name, phone, city, website, languages, bio, services,
                    social_links, status, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s,%s)""",
                (
                    pid, email, pw_hash, first_name, last_name, profile_type,
                    business_name, (phone or "").strip(), (city or "").strip(),
                    (website or "").strip(), (languages or "").strip(), bio,
                    services_json, social_json, now, now,
                ),
            )
        else:
            cur.execute(
                """INSERT INTO partner_accounts
                   (id, email, password_hash, first_name, last_name, profile_type,
                    business_name, phone, city, website, languages, bio, services,
                    social_links, status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?)""",
                (
                    pid, email, pw_hash, first_name, last_name, profile_type,
                    business_name, (phone or "").strip(), (city or "").strip(),
                    (website or "").strip(), (languages or "").strip(), bio,
                    services_json, social_json, now, now,
                ),
            )

    account = get_account_by_id(pid) or {}
    if create_page:
        _ensure_partner_draft_page(
            pid,
            account,
            extra_fields={
                "created_by_admin": True,
                "admin_onboarding_note": (admin_note or "").strip()[:500],
            },
        )
    return {"account": account, "temp_password": temp_password}


def _ensure_partner_draft_page(
    partner_id: str,
    account: dict,
    *,
    extra_fields: dict | None = None,
) -> dict:
    """Crée une page brouillon si le partenaire n'en a pas encore."""
    existing = get_page_by_partner(partner_id)
    if existing:
        return existing
    now = _now_iso()
    page_id = uuid.uuid4().hex[:16]
    slug = _unique_slug(
        account.get("business_name") or f"{account.get('first_name')}-{account.get('last_name')}"
    )
    extra = {"city": (account.get("city") or "").strip()}
    if extra_fields:
        extra.update({k: v for k, v in extra_fields.items() if v is not None})
    extra_json = json.dumps(extra, ensure_ascii=False)
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """INSERT INTO partner_pages
                   (id, partner_id, slug, status, extra_json, created_at, updated_at)
                   VALUES (%s,%s,%s,'draft',%s,%s,%s)""",
                (page_id, partner_id, slug, extra_json, now, now),
            )
        else:
            cur.execute(
                """INSERT INTO partner_pages
                   (id, partner_id, slug, status, extra_json, created_at, updated_at)
                   VALUES (?,?,?,'draft',?,?,?)""",
                (page_id, partner_id, slug, extra_json, now, now),
            )
    return get_page_by_partner(partner_id) or {}


def authenticate_partner(email: str, password: str) -> dict | None:
    email = (email or "").strip().lower()
    account = find_account_by_email(email)
    if not account:
        return None
    if account.get("status") == "suspended":
        return None
    if not check_password_hash(account.get("password_hash") or "", password or ""):
        return None
    return _public_account(account)


def find_account_by_email(email: str) -> dict | None:
    email = (email or "").strip().lower()
    if not email:
        return None
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute("SELECT * FROM partner_accounts WHERE email = %s LIMIT 1", (email,))
        else:
            cur.execute("SELECT * FROM partner_accounts WHERE email = ? LIMIT 1", (email,))
        row = cur.fetchone()
    return _row_dict(row) if row else None


def get_account_by_id(partner_id: str) -> dict | None:
    if not partner_id:
        return None
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute("SELECT * FROM partner_accounts WHERE id = %s LIMIT 1", (partner_id,))
        else:
            cur.execute("SELECT * FROM partner_accounts WHERE id = ? LIMIT 1", (partner_id,))
        row = cur.fetchone()
    return _public_account(_row_dict(row)) if row else None


def list_accounts(*, status: str = "") -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor()
        if status:
            if is_postgres():
                cur.execute(
                    "SELECT * FROM partner_accounts WHERE status = %s ORDER BY created_at DESC",
                    (status,),
                )
            else:
                cur.execute(
                    "SELECT * FROM partner_accounts WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                )
        else:
            cur.execute("SELECT * FROM partner_accounts ORDER BY created_at DESC")
        rows = cur.fetchall()
    return [
        _public_account(_row_dict(r))
        for r in rows
        if not is_hidden_test_partner(_row_dict(r))
    ]


def set_account_status(partner_id: str, status: str) -> bool:
    if status not in {s for s, _ in ACCOUNT_STATUSES}:
        return False
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                "UPDATE partner_accounts SET status = %s, updated_at = %s WHERE id = %s",
                (status, now, partner_id),
            )
        else:
            cur.execute(
                "UPDATE partner_accounts SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, partner_id),
            )
        return cur.rowcount > 0


def get_page_by_partner(partner_id: str) -> dict | None:
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute("SELECT * FROM partner_pages WHERE partner_id = %s LIMIT 1", (partner_id,))
        else:
            cur.execute("SELECT * FROM partner_pages WHERE partner_id = ? LIMIT 1", (partner_id,))
        row = cur.fetchone()
    if not row:
        return None
    return _normalize_page_record(_page_row_dict(row))


def get_page_by_slug(slug: str) -> dict | None:
    slug = (slug or "").strip().lower()
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                "SELECT * FROM partner_pages WHERE slug = %s AND status = 'published' LIMIT 1",
                (slug,),
            )
        else:
            cur.execute(
                "SELECT * FROM partner_pages WHERE slug = ? AND status = 'published' LIMIT 1",
                (slug,),
            )
        row = cur.fetchone()
    if not row:
        return None
    page = _normalize_page_record(_page_row_dict(row))
    account = get_account_by_id(page.get("partner_id"))
    if account and is_hidden_test_partner(account):
        return None
    return page


def list_pages(*, status: str = "") -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor()
        if status:
            if is_postgres():
                cur.execute(
                    "SELECT * FROM partner_pages WHERE status = %s ORDER BY updated_at DESC",
                    (status,),
                )
            else:
                cur.execute(
                    "SELECT * FROM partner_pages WHERE status = ? ORDER BY updated_at DESC",
                    (status,),
                )
        else:
            cur.execute("SELECT * FROM partner_pages ORDER BY updated_at DESC")
        rows = cur.fetchall()
    out = []
    for r in rows:
        p = _normalize_page_record(_page_row_dict(r))
        account = get_account_by_id(p.get("partner_id"))
        if account and is_hidden_test_partner(account):
            continue
        out.append(p)
    return out


def list_public_partners() -> list[dict]:
    """Pages publiées indexables (hors compte test interne)."""
    out: list[dict] = []
    for page in list_pages(status="published"):
        account = get_account_by_id(page.get("partner_id"))
        if not account or account.get("status") != "active" or is_hidden_test_partner(account):
            continue
        entry = dict(page)
        entry["partner"] = account
        out.append(entry)
    return out


def save_page_draft(
    partner_id: str,
    *,
    pitch: str,
    highlights: str,
    offer_details: str,
    city: str = "",
    contact_note: str = "",
) -> dict:
    pitch = (pitch or "").strip()
    highlights = (highlights or "").strip()
    offer_details = (offer_details or "").strip()
    if len(pitch) < 30:
        raise ValueError("Accroche trop courte (30 caractères minimum).")
    if len(offer_details) < 40:
        raise ValueError("Décrivez votre offre (40 caractères minimum).")

    account = get_account_by_id(partner_id)
    if not account:
        raise ValueError("Compte introuvable.")

    from admin.partner_discovery import location_from_destination
    loc = location_from_destination(city or account.get("city"), required=True)

    existing = get_page_by_partner(partner_id)
    now = _now_iso()
    prev_extra = (existing or {}).get("extra") if isinstance((existing or {}).get("extra"), dict) else {}
    extra = {
        **prev_extra,
        "pitch": pitch,
        "highlights": highlights,
        "offer_details": offer_details,
        "city": loc["name"],
        "destination_slug": loc["slug"],
        "contact_note": (contact_note or "").strip(),
    }
    if "profile_highlights" not in extra or not _coerce_profile_highlights(extra.get("profile_highlights")):
        if prev_extra.get("profile_highlights") is not None:
            extra["profile_highlights"] = prev_extra["profile_highlights"]
        elif highlights:
            extra["profile_highlights"] = _highlights_from_extra({"highlights": highlights})
    extra_json = json.dumps(extra, ensure_ascii=False)

    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                "UPDATE partner_accounts SET city = %s, updated_at = %s WHERE id = %s",
                (loc["name"], now, partner_id),
            )
        else:
            cur.execute(
                "UPDATE partner_accounts SET city = ?, updated_at = ? WHERE id = ?",
                (loc["name"], now, partner_id),
            )

    if existing:
        if existing.get("status") == "ai_review":
            raise ValueError("Page en cours de validation — patientez.")
        page_id = existing["id"]
        slug = existing.get("slug") or _unique_slug(account.get("business_name") or account.get("last_name"))
        with get_connection() as conn:
            cur = conn.cursor()
            if is_postgres():
                cur.execute(
                    """UPDATE partner_pages SET extra_json = %s, status = 'draft',
                       updated_at = %s WHERE partner_id = %s""",
                    (extra_json, now, partner_id),
                )
            else:
                cur.execute(
                    """UPDATE partner_pages SET extra_json = ?, status = 'draft',
                       updated_at = ? WHERE partner_id = ?""",
                    (extra_json, now, partner_id),
                )
    else:
        page_id = uuid.uuid4().hex[:16]
        slug = _unique_slug(account.get("business_name") or f"{account.get('first_name')}-{account.get('last_name')}")
        with get_connection() as conn:
            cur = conn.cursor()
            if is_postgres():
                cur.execute(
                    """INSERT INTO partner_pages
                       (id, partner_id, slug, status, extra_json, created_at, updated_at)
                       VALUES (%s,%s,%s,'draft',%s,%s,%s)""",
                    (page_id, partner_id, slug, extra_json, now, now),
                )
            else:
                cur.execute(
                    """INSERT INTO partner_pages
                       (id, partner_id, slug, status, extra_json, created_at, updated_at)
                       VALUES (?,?,?,'draft',?,?,?)""",
                    (page_id, partner_id, slug, extra_json, now, now),
                )
    return get_page_by_partner(partner_id) or {}


def get_page_fixes(page: dict | None) -> list[dict]:
    """Corrections IA proposées pour le brouillon partenaire."""
    if not page:
        return []
    review = page.get("ai_review") or {}
    fixes = review.get("fixes") or []
    if fixes:
        return fixes
    return (page.get("extra") or {}).get("pending_fixes") or []


def save_page_review_hints(partner_id: str, review: dict, *, error_reason: str = "") -> None:
    """Enregistre issues/fixes sans publier (après échec technique de vérification)."""
    page = get_page_by_partner(partner_id)
    if not page:
        return
    review = dict(review or {})
    review.setdefault("approved", False)
    if error_reason:
        review["error_reason"] = str(error_reason).strip()[:800]
    if not review.get("summary"):
        review["summary"] = review.get("error_reason") or "Vérification incomplète — corrections proposées."
    now = _now_iso()
    extra = dict(page.get("extra") or {})
    if error_reason:
        extra["last_verification_error"] = str(error_reason).strip()[:800]
    if review.get("fixes"):
        extra["pending_fixes"] = review["fixes"]
    extra.pop("ai_job_token", None)
    extra.pop("ai_job_started_at", None)
    ai_review_json = json.dumps(review, ensure_ascii=False)
    extra_json = json.dumps(extra, ensure_ascii=False)
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """UPDATE partner_pages SET status = 'draft', extra_json = %s,
                   ai_review_json = %s, updated_at = %s WHERE partner_id = %s""",
                (extra_json, ai_review_json, now, partner_id),
            )
        else:
            cur.execute(
                """UPDATE partner_pages SET status = 'draft', extra_json = ?,
                   ai_review_json = ?, updated_at = ? WHERE partner_id = ?""",
                (extra_json, ai_review_json, now, partner_id),
            )


def _set_review_fixes(partner_id: str, fixes: list[dict]) -> None:
    page = get_page_by_partner(partner_id)
    if not page:
        return
    review = dict(page.get("ai_review") or {})
    review["fixes"] = fixes
    extra = dict(page.get("extra") or {})
    if fixes:
        extra["pending_fixes"] = fixes
    else:
        extra.pop("pending_fixes", None)
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """UPDATE partner_pages SET ai_review_json = %s, extra_json = %s,
                   updated_at = %s WHERE partner_id = %s""",
                (json.dumps(review, ensure_ascii=False), json.dumps(extra, ensure_ascii=False), now, partner_id),
            )
        else:
            cur.execute(
                """UPDATE partner_pages SET ai_review_json = ?, extra_json = ?,
                   updated_at = ? WHERE partner_id = ?""",
                (json.dumps(review, ensure_ascii=False), json.dumps(extra, ensure_ascii=False), now, partner_id),
            )


def _patch_page_extra(partner_id: str, patch: dict) -> None:
    page = get_page_by_partner(partner_id)
    if not page:
        return
    extra = dict(page.get("extra") or {})
    extra.update({k: v for k, v in patch.items() if v is not None})
    now = _now_iso()
    extra_json = json.dumps(extra, ensure_ascii=False)
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


def apply_partner_fixes(
    partner_id: str,
    *,
    fix_ids: list[str] | None = None,
    apply_all: bool = False,
) -> int:
    """Applique une ou plusieurs corrections IA au brouillon."""
    page = get_page_by_partner(partner_id)
    if not page:
        raise ValueError("Page introuvable.")
    fixes = get_page_fixes(page)
    if not fixes:
        raise ValueError("Aucune correction disponible.")

    if apply_all:
        selected = fixes
    else:
        ids = {i.strip() for i in (fix_ids or []) if i and i.strip()}
        if not ids:
            raise ValueError("Correction introuvable.")
        selected = [f for f in fixes if f.get("id") in ids]
        if not selected:
            raise ValueError("Correction introuvable.")

    extra = dict(page.get("extra") or {})
    fields = {
        "pitch": extra.get("pitch") or "",
        "highlights": extra.get("highlights") or "",
        "offer_details": extra.get("offer_details") or "",
        "city": extra.get("city") or "",
        "contact_note": extra.get("contact_note") or "",
    }
    applied_ids: set[str] = set()
    for fix in selected:
        field = fix.get("field")
        suggested = (fix.get("suggested") or "").strip()
        if field not in fields or not suggested:
            continue
        fields[field] = suggested
        applied_ids.add(fix.get("id", ""))

    if not applied_ids:
        raise ValueError("Aucune correction applicable.")

    save_page_draft(partner_id, **fields)
    remaining = [f for f in fixes if f.get("id") not in applied_ids]
    _set_review_fixes(partner_id, remaining)
    patch: dict = {"ai_fixes_applied": True, "ai_fixes_applied_at": _now_iso()}
    if not remaining:
        patch["ai_fixes_ready_for_recheck"] = True
    _patch_page_extra(partner_id, patch)
    applied_labels = [
        str(f.get("label") or f.get("field") or "")
        for f in selected
        if f.get("id") in applied_ids
    ]
    return {
        "applied_count": len(applied_ids),
        "applied_ids": [i for i in applied_ids if i],
        "applied_labels": applied_labels,
        "remaining_fixes": remaining,
        "draft": fields,
        "should_relaunch": not remaining,
    }


def apply_ai_page_result(partner_id: str, result: dict) -> dict:
    """Persiste le résultat IA (contenu + décision)."""
    page = get_page_by_partner(partner_id)
    if not page:
        raise ValueError("Page introuvable.")

    review = result.get("review") or {}
    approved = bool(review.get("approved"))
    try:
        score = int(review.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    if approved and score < 65:
        approved = False
        review = dict(review)
        review["approved"] = False
        if not review.get("issues"):
            review["issues"] = [f"Score insuffisant ({score}/100) — minimum 65 requis pour publier."]
    page_data = result.get("page") or {}
    now = _now_iso()

    account = get_account_by_id(partner_id)
    title = (page_data.get("title") or "").strip()
    overview_html = (page_data.get("overview_html") or "").strip()
    has_content = bool(title and overview_html)

    if is_hidden_test_partner(account) and has_content and approved:
        review = dict(review)
        review["approved"] = True
        if not review.get("summary"):
            review["summary"] = "Page validée par l’IA — publiez en ligne quand vous êtes prêt."
    if approved and has_content:
        status = "approved"
        published_at = None
    else:
        status = "rejected"
        published_at = None

    tagline = (page_data.get("tagline") or "").strip()
    services_html = (page_data.get("services_html") or "").strip()
    seo_title = (page_data.get("seo_title") or title)[:120]
    seo_description = (page_data.get("seo_description") or "")[:320]
    image_url = (page_data.get("image_url") or "").strip()
    if not image_url:
        image_url = (page.get("image_url") or "").strip()
    ai_review_json = json.dumps(review, ensure_ascii=False)
    extra = dict(page.get("extra") or {})
    saved_vitrine_hl = _coerce_profile_highlights(extra.get("profile_highlights"))
    profile_highlights = _coerce_profile_highlights(page_data.get("profile_highlights"))
    if len(profile_highlights) < 3:
        profile_highlights = _highlights_from_extra(extra)
    if len(profile_highlights) < 3:
        profile_highlights = _highlights_from_html(page_data.get("services_html"))
    if len(profile_highlights) < 3:
        profile_highlights = _highlights_from_html(page.get("services_html"))
    if len(profile_highlights) < 3 and len(saved_vitrine_hl) >= 3:
        profile_highlights = saved_vitrine_hl
    if len(profile_highlights) >= 3:
        extra["profile_highlights"] = profile_highlights[:8]
    elif saved_vitrine_hl:
        extra["profile_highlights"] = saved_vitrine_hl[:8]
    if review.get("fixes"):
        extra["pending_fixes"] = review["fixes"]
    else:
        extra.pop("pending_fixes", None)
    extra.pop("last_verification_error", None)
    extra.pop("ai_job_token", None)
    extra.pop("ai_job_started_at", None)
    if status == "approved":
        extra.pop("ai_fixes_ready_for_recheck", None)

    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """UPDATE partner_pages SET
                   status = %s, title = %s, tagline = %s, overview_html = %s,
                   services_html = %s, seo_title = %s, seo_description = %s,
                   image_url = %s, extra_json = %s, ai_review_json = %s,
                   updated_at = %s, published_at = %s
                   WHERE partner_id = %s""",
                (
                    status, title, tagline, overview_html, services_html,
                    seo_title, seo_description, image_url,
                    json.dumps(extra, ensure_ascii=False), ai_review_json,
                    now, published_at, partner_id,
                ),
            )
        else:
            cur.execute(
                """UPDATE partner_pages SET
                   status = ?, title = ?, tagline = ?, overview_html = ?,
                   services_html = ?, seo_title = ?, seo_description = ?,
                   image_url = ?, extra_json = ?, ai_review_json = ?,
                   updated_at = ?, published_at = ?
                   WHERE partner_id = ?""",
                (
                    status, title, tagline, overview_html, services_html,
                    seo_title, seo_description, image_url,
                    json.dumps(extra, ensure_ascii=False), ai_review_json,
                    now, published_at, partner_id,
                ),
            )
    if approved or status == "published":
        try:
            from admin import chat_service
            chat_service.invalidate_cache()
        except Exception:
            pass
    return get_page_by_partner(partner_id) or {}


def partner_page_has_publishable_content(page: dict | None) -> bool:
    if not page:
        return False
    return bool((page.get("title") or "").strip() and (page.get("overview_html") or "").strip())


def publish_partner_page(partner_id: str) -> dict:
    """Publication publique — uniquement après validation IA (statut approved)."""
    page = get_page_by_partner(partner_id)
    if not page:
        raise ValueError("Page introuvable.")
    if page.get("status") == "published":
        return page
    if page.get("status") == "ai_review":
        raise ValueError("Vérification en cours — patientez.")
    review = page.get("ai_review") or {}
    if not review.get("approved"):
        raise ValueError("Publication impossible — la page doit d’abord être validée par l’IA.")
    if page.get("status") != "approved":
        raise ValueError("Publication impossible — relancez la vérification IA si besoin.")
    if not partner_page_has_publishable_content(page):
        raise ValueError("Contenu incomplet — relancez la vérification IA.")
    extra = dict(page.get("extra") or {})
    highlights = _resolve_public_highlights(page, extra=extra)
    if len(highlights) >= 3 and not _coerce_profile_highlights(extra.get("profile_highlights")):
        extra["profile_highlights"] = highlights[:8]
        now = _now_iso()
        extra_json = json.dumps(extra, ensure_ascii=False)
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
    if not set_page_status(partner_id, "published"):
        raise ValueError("Échec de la publication.")
    return get_page_by_partner(partner_id) or {}


def partner_page_can_preview(page: dict | None) -> bool:
    if not page:
        return False
    if not partner_page_has_publishable_content(page):
        return False
    return page.get("status") in ("approved", "published") or bool((page.get("ai_review") or {}).get("approved"))


def set_page_status(partner_id: str, status: str, *, admin_notes: str = "") -> bool:
    if status not in {s for s, _ in PAGE_STATUSES}:
        return False
    now = _now_iso()
    published_at = now if status == "published" else None
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """UPDATE partner_pages SET status = %s, admin_notes = %s,
                   updated_at = %s, published_at = COALESCE(%s, published_at)
                   WHERE partner_id = %s""",
                (status, (admin_notes or "").strip(), now, published_at, partner_id),
            )
        else:
            cur.execute(
                """UPDATE partner_pages SET status = ?, admin_notes = ?,
                   updated_at = ?, published_at = COALESCE(?, published_at)
                   WHERE partner_id = ?""",
                (status, (admin_notes or "").strip(), now, published_at, partner_id),
            )
        ok = cur.rowcount > 0
    if ok and status == "published":
        try:
            from admin import chat_service
            chat_service.invalidate_cache()
        except Exception:
            pass
    return ok


def mark_page_ai_review(partner_id: str, *, job_token: str = "") -> bool:
    now = _now_iso()
    page = get_page_by_partner(partner_id)
    extra = dict((page or {}).get("extra") or {})
    if job_token:
        extra["ai_job_token"] = job_token
        extra["ai_job_started_at"] = now
    extra_json = json.dumps(extra, ensure_ascii=False)
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """UPDATE partner_pages SET status = 'ai_review', extra_json = %s,
                   updated_at = %s WHERE partner_id = %s""",
                (extra_json, now, partner_id),
            )
        else:
            cur.execute(
                """UPDATE partner_pages SET status = 'ai_review', extra_json = ?,
                   updated_at = ? WHERE partner_id = ?""",
                (extra_json, now, partner_id),
            )
        return cur.rowcount > 0


def clear_page_review_job(partner_id: str) -> None:
    page = get_page_by_partner(partner_id)
    if not page:
        return
    extra = dict(page.get("extra") or {})
    if not extra.pop("ai_job_token", None) and not extra.pop("ai_job_started_at", None):
        return
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                "UPDATE partner_pages SET extra_json = %s, updated_at = %s WHERE partner_id = %s",
                (json.dumps(extra, ensure_ascii=False), now, partner_id),
            )
        else:
            cur.execute(
                "UPDATE partner_pages SET extra_json = ?, updated_at = ? WHERE partner_id = ?",
                (json.dumps(extra, ensure_ascii=False), now, partner_id),
            )


def review_job_token(page: dict | None, session_token: str | None = None) -> str | None:
    extra = (page or {}).get("extra") or {}
    return (session_token or extra.get("ai_job_token") or "").strip() or None


def page_review_job_running(token: str | None) -> bool:
    if not token:
        return False
    from admin import draft_store

    return draft_store.status(token).get("status") == "running"


def page_ai_review_orphaned(page: dict | None, token: str | None) -> bool:
    """Page bloquée en ai_review sans job actif (session perdue, redémarrage serveur…)."""
    if not page or page.get("status") != "ai_review":
        return False
    if page_review_job_running(token):
        return False
    if not token:
        return True
    from admin import draft_store

    st = draft_store.status(token).get("status")
    return st not in ("running", "done")


def release_page_from_ai_review(partner_id: str) -> bool:
    """Remet la page en brouillon après une analyse IA interrompue ou en échec."""
    clear_page_review_job(partner_id)
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """UPDATE partner_pages SET status = 'draft', updated_at = %s
                   WHERE partner_id = %s AND status = 'ai_review'""",
                (now, partner_id),
            )
        else:
            cur.execute(
                """UPDATE partner_pages SET status = 'draft', updated_at = ?
                   WHERE partner_id = ? AND status = 'ai_review'""",
                (now, partner_id),
            )
        return cur.rowcount > 0


def page_ai_review_stale(page: dict | None, *, minutes: int = 12) -> bool:
    """True si la page est bloquée en ai_review depuis trop longtemps."""
    if not page or page.get("status") != "ai_review":
        return False
    extra = page.get("extra") or {}
    raw = extra.get("ai_job_started_at") or page.get("updated_at")
    if not raw:
        return True
    try:
        if isinstance(raw, datetime):
            dt = raw
        else:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - dt > timedelta(minutes=minutes)
    except (TypeError, ValueError):
        return True


def portal_stats() -> dict:
    accounts = list_accounts()
    pages = list_pages()
    return {
        "accounts": len(accounts),
        "pages_published": sum(1 for p in pages if p.get("status") == "published"),
        "pages_pending": sum(1 for p in pages if p.get("status") in ("ai_review", "approved")),
        "pages_rejected": sum(1 for p in pages if p.get("status") == "rejected"),
    }


_PARTNER_RESET_TTL = timedelta(hours=1)


def _hash_partner_reset_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _parse_reset_expires(raw) -> datetime | None:
    if not raw:
        return None
    try:
        if isinstance(raw, datetime):
            dt = raw
        else:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def _clear_partner_password_resets(partner_id: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                "DELETE FROM partner_password_resets WHERE partner_id = %s",
                (partner_id,),
            )
        else:
            cur.execute(
                "DELETE FROM partner_password_resets WHERE partner_id = ?",
                (partner_id,),
            )


def _send_partner_password_reset_email(account: dict, reset_url: str) -> None:
    import config as site_config
    from admin.mail_service import send_email
    from admin.newsletter_service import wrap_email_html

    first_name = (account.get("first_name") or "").strip() or "Partenaire"
    body_html = f"""
      <p style="margin:0 0 16px;">Bonjour {first_name},</p>
      <p style="margin:0 0 16px;">Vous avez demandé la réinitialisation du mot de passe de votre espace partenaire Inside Vietnam Travel.</p>
      <p style="margin:0 0 24px;text-align:center;">
        <a href="{reset_url}" style="display:inline-block;background:#1b4d4a;color:#ffffff;font-family:'Segoe UI',Arial,sans-serif;font-size:15px;font-weight:600;text-decoration:none;padding:14px 28px;border-radius:8px;">Choisir un nouveau mot de passe</a>
      </p>
      <p style="margin:0 0 12px;font-family:'Segoe UI',Arial,sans-serif;font-size:14px;color:#7a7772;">Ce lien expire dans 1&nbsp;heure. Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.</p>
      <p style="margin:0;font-family:'Segoe UI',Arial,sans-serif;font-size:13px;color:#7a7772;word-break:break-all;">Lien direct : {reset_url}</p>
    """
    html = wrap_email_html(
        body_html,
        preheader="Réinitialisez votre mot de passe partenaire.",
        recipient_email=account.get("email"),
        email_type="partenariat",
    )
    plain = (
        f"Bonjour {first_name},\n\n"
        "Réinitialisez votre mot de passe partenaire :\n"
        f"{reset_url}\n\n"
        "Ce lien expire dans 1 heure."
    )
    send_email(
        profile="newsletter",
        to_addrs=[account["email"]],
        subject="Réinitialisation mot de passe — Espace partenaire Inside Vietnam Travel",
        html_body=html,
        plain_body=plain,
        reply_to=site_config.LEGAL_CONTACT_EMAIL,
    )


def request_partner_password_reset(email: str) -> dict:
    """Demande de reset — retourne toujours ok (ne divulgue pas si l'email existe)."""
    import config as site_config

    email = (email or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("Email invalide.")

    account = find_account_by_email(email)
    if not account or account.get("status") == "suspended":
        return {"ok": True}

    token = secrets.token_urlsafe(32)
    token_hash = _hash_partner_reset_token(token)
    reset_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc)
    expires = now + _PARTNER_RESET_TTL
    expires_iso = expires.replace(tzinfo=None).isoformat()
    created_iso = _now_iso()

    _clear_partner_password_resets(account["id"])
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """INSERT INTO partner_password_resets
                   (id, partner_id, token_hash, expires_at, created_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (reset_id, account["id"], token_hash, expires, created_iso),
            )
        else:
            cur.execute(
                """INSERT INTO partner_password_resets
                   (id, partner_id, token_hash, expires_at, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (reset_id, account["id"], token_hash, expires_iso, created_iso),
            )

    reset_url = f"{site_config.SITE_CANONICAL_URL.rstrip('/')}/partners/reset-password/{token}"
    try:
        _send_partner_password_reset_email(account, reset_url)
    except Exception:  # noqa: BLE001
        _clear_partner_password_resets(account["id"])
        raise ValueError(
            "Impossible d'envoyer l'email pour le moment. Réessayez dans quelques minutes."
        )
    return {"ok": True}


def reset_partner_password_with_token(
    token: str,
    *,
    password: str,
    password_confirm: str,
) -> dict:
    token = (token or "").strip()
    if not token:
        raise ValueError("Lien de réinitialisation invalide.")
    if len(password or "") < 8:
        raise ValueError("Mot de passe : 8 caractères minimum.")
    if password != password_confirm:
        raise ValueError("Les mots de passe ne correspondent pas.")

    token_hash = _hash_partner_reset_token(token)
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """SELECT id, partner_id, expires_at FROM partner_password_resets
                   WHERE token_hash = %s ORDER BY created_at DESC LIMIT 1""",
                (token_hash,),
            )
        else:
            cur.execute(
                """SELECT id, partner_id, expires_at FROM partner_password_resets
                   WHERE token_hash = ? ORDER BY created_at DESC LIMIT 1""",
                (token_hash,),
            )
        row = cur.fetchone()
        if not row:
            raise ValueError("Lien invalide ou déjà utilisé.")
        if isinstance(row, dict):
            rec = dict(row)
        elif hasattr(row, "keys"):
            rec = {k: row[k] for k in row.keys()}
        else:
            rec = {"id": row[0], "partner_id": row[1], "expires_at": row[2]}
        expires = _parse_reset_expires(rec.get("expires_at"))
        if not expires or expires < now:
            _clear_partner_password_resets(rec["partner_id"])
            raise ValueError("Ce lien a expiré. Demandez un nouvel email.")

        partner_id = rec["partner_id"]
        pw_hash = generate_password_hash(password)
        updated_iso = _now_iso()
        if is_postgres():
            cur.execute(
                "UPDATE partner_accounts SET password_hash = %s, updated_at = %s WHERE id = %s",
                (pw_hash, updated_iso, partner_id),
            )
            cur.execute("DELETE FROM partner_password_resets WHERE partner_id = %s", (partner_id,))
        else:
            cur.execute(
                "UPDATE partner_accounts SET password_hash = ?, updated_at = ? WHERE id = ?",
                (pw_hash, updated_iso, partner_id),
            )
            cur.execute("DELETE FROM partner_password_resets WHERE partner_id = ?", (partner_id,))

    return {"ok": True, "partner_id": partner_id}
