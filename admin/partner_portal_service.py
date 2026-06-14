"""Espace partenaires — inscriptions, comptes, pages publiques."""

from __future__ import annotations

import json
import re
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
    page = _page_row_dict(row)
    page["extra"] = _parse_json_field(page.get("extra_json"))
    raw_review = page.get("ai_review_json")
    if raw_review:
        try:
            page["ai_review"] = json.loads(raw_review) if isinstance(raw_review, str) else raw_review
        except Exception:  # noqa: BLE001
            page["ai_review"] = {}
    else:
        page["ai_review"] = {}
    return page


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
    page = _page_row_dict(row)
    account = get_account_by_id(page.get("partner_id"))
    if account and is_hidden_test_partner(account):
        return None
    page["extra"] = _parse_json_field(page.get("extra_json"))
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
        p = _page_row_dict(r)
        account = get_account_by_id(p.get("partner_id"))
        if account and is_hidden_test_partner(account):
            continue
        p["extra"] = _parse_json_field(p.get("extra_json"))
        p["ai_review"] = _parse_json_field(p.get("ai_review_json"))
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

    existing = get_page_by_partner(partner_id)
    now = _now_iso()
    extra = {
        "pitch": pitch,
        "highlights": highlights,
        "offer_details": offer_details,
        "city": (city or account.get("city") or "").strip(),
        "contact_note": (contact_note or "").strip(),
    }
    extra_json = json.dumps(extra, ensure_ascii=False)

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
    }


def apply_ai_page_result(partner_id: str, result: dict) -> dict:
    """Persiste le résultat IA (contenu + décision)."""
    page = get_page_by_partner(partner_id)
    if not page:
        raise ValueError("Page introuvable.")

    review = result.get("review") or {}
    approved = bool(review.get("approved"))
    page_data = result.get("page") or {}
    now = _now_iso()

    status = "published" if approved else "rejected"
    published_at = now if approved else None

    title = (page_data.get("title") or "").strip()
    tagline = (page_data.get("tagline") or "").strip()
    overview_html = (page_data.get("overview_html") or "").strip()
    services_html = (page_data.get("services_html") or "").strip()
    seo_title = (page_data.get("seo_title") or title)[:120]
    seo_description = (page_data.get("seo_description") or "")[:320]
    image_url = (page_data.get("image_url") or "").strip()
    ai_review_json = json.dumps(review, ensure_ascii=False)
    extra = dict(page.get("extra") or {})
    extra["profile_highlights"] = page_data.get("profile_highlights") or []
    if review.get("fixes"):
        extra["pending_fixes"] = review["fixes"]
    else:
        extra.pop("pending_fixes", None)
    extra.pop("last_verification_error", None)

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
    if approved:
        try:
            from admin import chat_service
            chat_service.invalidate_cache()
        except Exception:
            pass
    return get_page_by_partner(partner_id) or {}


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


def mark_page_ai_review(partner_id: str) -> bool:
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                "UPDATE partner_pages SET status = 'ai_review', updated_at = %s WHERE partner_id = %s",
                (now, partner_id),
            )
        else:
            cur.execute(
                "UPDATE partner_pages SET status = 'ai_review', updated_at = ? WHERE partner_id = ?",
                (now, partner_id),
            )
        return cur.rowcount > 0


def release_page_from_ai_review(partner_id: str) -> bool:
    """Remet la page en brouillon après une analyse IA interrompue ou en échec."""
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


def page_ai_review_stale(page: dict | None, *, minutes: int = 3) -> bool:
    """True si la page est bloquée en ai_review depuis trop longtemps."""
    if not page or page.get("status") != "ai_review":
        return False
    raw = page.get("updated_at")
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
