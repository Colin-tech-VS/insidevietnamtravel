"""Partenaires recommandés — module admin-piloté (curation éditoriale).

À NE PAS confondre avec :
- `admin/partners_service.py` : CRM de prospection (qui contacter par email).
- `admin/partner_portal_service.py` : portail self-service SQL (comptes + 1 page vitrine).

Ici l'admin crée lui-même des partenaires qu'il recommande et, pour chacun, PLUSIEURS
pages dédiées (générées par IA ou saisies). Stockage KV (`recommended_partners.json` en
local, table `app_kv` en prod) — pas de migration de schéma.

Structure stockée (liste) :
[{
  id, slug, name, website,
  partnership_type,            # clé dans PARTNERSHIP_TYPES
  commission, objective, notes,# INTERNES — jamais exposés au public
  enabled: bool,               # switch publication (cascade fiche + pages)
  tagline, intro_html,         # public
  image, image_alt, image_prompt,
  created_at, updated_at,
  pages: [{
    id, slug, title, content_html, meta_title, meta_description,
    image, image_alt, image_prompt, prompt,
    enabled: bool, created_at, updated_at,
  }],
}]
"""

from __future__ import annotations

import secrets
import threading
from datetime import date

from admin.kv_store import get_json, set_json
from admin.store import slugify

# Types de partenariat (clé interne, libellé admin).
PARTNERSHIP_TYPES = [
    ("affiliation", "💶 Affiliation (commission)"),
    ("sponsorise", "📢 Sponsorisé (montant fixe)"),
    ("echange", "🔁 Échange de visibilité"),
    ("apporteur", "🤝 Apporteur d'affaires"),
    ("autre", "✨ Autre"),
]
PARTNERSHIP_TYPE_KEYS = {k for k, _ in PARTNERSHIP_TYPES}
PARTNERSHIP_TYPE_LABELS = dict(PARTNERSHIP_TYPES)

# Champs internes (pilotage) à ne JAMAIS sérialiser vers le public.
_INTERNAL_FIELDS = ("commission", "commission_rate", "objective", "notes", "partnership_type")

_save_lock = threading.Lock()


# ── Store ───────────────────────────────────────────────────────────────────

def _pages_list(partner: dict) -> list[dict]:
    pages = partner.get("pages")
    return pages if isinstance(pages, list) else []


def _sanitize_partner(raw: dict) -> dict:
    """Normalize legacy/corrupt KV records (e.g. pages=null → [])."""
    partner = dict(raw)
    partner["pages"] = [
        {**pg, "images": _clean_url_list(pg.get("images"))}
        for pg in _pages_list(partner)
        if isinstance(pg, dict)
    ]
    return partner


def get_partners() -> list[dict]:
    stored = get_json("recommended_partners", [], file_name="recommended_partners.json")
    if not stored:
        return []
    if not isinstance(stored, list):
        return []
    return [_sanitize_partner(p) for p in stored if isinstance(p, dict)]


def save_partners(items: list[dict]) -> None:
    with _save_lock:
        set_json("recommended_partners", items, file_name="recommended_partners.json")


def find_partner(pid: str) -> dict | None:
    pid = (pid or "").strip()
    return next((p for p in get_partners() if p.get("id") == pid), None)


def find_partner_by_slug(slug: str) -> dict | None:
    slug = (slug or "").strip().lower()
    if not slug:
        return None
    return next((p for p in get_partners() if p.get("slug") == slug), None)


def find_page_by_slug(partner_slug: str, page_slug: str) -> tuple[dict, dict] | tuple[None, None]:
    """Retourne (partner, page) ou (None, None) — sans filtrage publication."""
    partner = find_partner_by_slug(partner_slug)
    if not partner:
        return None, None
    page_slug = (page_slug or "").strip().lower()
    page = next((pg for pg in _pages_list(partner) if pg.get("slug") == page_slug), None)
    if not page:
        return None, None
    return partner, page


# ── Normalisation ────────────────────────────────────────────────────────────

def _unique_partner_slug(base: str, *, exclude_id: str = "") -> str:
    base = slugify(base) or f"partenaire-{secrets.token_hex(3)}"
    existing = {
        p.get("slug")
        for p in get_partners()
        if p.get("id") != exclude_id
    }
    slug = base
    i = 2
    while slug in existing:
        slug = f"{base}-{i}"
        i += 1
    return slug


def _unique_page_slug(partner: dict, base: str, *, exclude_id: str = "") -> str:
    base = slugify(base) or f"page-{secrets.token_hex(3)}"
    existing = {
        pg.get("slug")
        for pg in _pages_list(partner)
        if pg.get("id") != exclude_id
    }
    slug = base
    i = 2
    while slug in existing:
        slug = f"{base}-{i}"
        i += 1
    return slug


def _coerce_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "on", "yes", "oui")


def _normalize_url(value: str) -> str:
    url = str(value or "").strip()[:300]
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _clean_url_list(value) -> list[str]:
    """Liste d'URLs d'images (chemins /static ou http), dédupliquée, max 12."""
    if isinstance(value, str):
        import re as _re
        value = _re.split(r"[\n,]+", value)
    out: list[str] = []
    for raw in value or []:
        u = str(raw).strip()
        if u and u not in out:
            out.append(u[:300])
    return out[:12]


def _coerce_rating(value, default: int = 5) -> int:
    try:
        return max(1, min(5, int(value)))
    except (TypeError, ValueError):
        return default


def _clean_reviews_list(value) -> list[dict]:
    """Avis curés admin (max 20) — {id, author, location, rating, date, text{fr,en}, enabled}."""
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        text = raw.get("text") or {}
        if not isinstance(text, dict):
            text = {"fr": str(text or ""), "en": ""}
        author = str(raw.get("author") or "").strip()[:80]
        body_fr = str(text.get("fr") or "").strip()
        if not author or not body_fr:
            continue
        out.append({
            "id": str(raw.get("id") or secrets.token_urlsafe(8)),
            "author": author,
            "location": str(raw.get("location") or "").strip()[:80],
            "rating": _coerce_rating(raw.get("rating")),
            "date": str(raw.get("date") or date.today().isoformat())[:10],
            "text": {
                "fr": body_fr[:2000],
                "en": str(text.get("en") or "").strip()[:2000] or body_fr[:2000],
            },
            "enabled": _coerce_bool(raw.get("enabled"), default=True),
        })
    return out[:20]


def _localize_reviews_list(reviews: list | None, lang: str | None) -> list[dict]:
    out: list[dict] = []
    for r in _clean_reviews_list(reviews or []):
        if not r.get("enabled", True):
            continue
        text = r.get("text") or {}
        body = (text.get("en") if lang == "en" else None) or text.get("fr") or ""
        if not body:
            continue
        out.append({
            "id": r.get("id", ""),
            "author": r.get("author", ""),
            "location": r.get("location", ""),
            "rating": r.get("rating", 5),
            "date": r.get("date", ""),
            "body": body,
        })
    return out


def _coerce_float(value, default: float = 0.0) -> float:
    """Parse un nombre tolérant : « 45 €  », « 45,90 », « 1 200 » → float."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = (
        str(value)
        .replace(" ", "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    cleaned = "".join(c for c in cleaned if c.isdigit() or c == ".")
    try:
        return float(cleaned) if cleaned else default
    except ValueError:
        return default


def _normalize_partner(data: dict, *, existing: dict | None = None) -> dict:
    existing = existing or {}
    name = str(data.get("name") or "").strip()[:120]
    if not name:
        raise ValueError("Le nom du partenaire est obligatoire.")
    ptype = str(data.get("partnership_type") or "affiliation").strip().lower()
    if ptype not in PARTNERSHIP_TYPE_KEYS:
        ptype = "autre"
    website = _normalize_url(data.get("website") or "")
    pid = data.get("id") or existing.get("id") or secrets.token_urlsafe(8)
    slug_source = data.get("slug") or existing.get("slug") or name
    slug = _unique_partner_slug(slug_source, exclude_id=pid)
    today = date.today().isoformat()
    return {
        "id": pid,
        "slug": slug,
        "name": name,
        "website": website,
        "partnership_type": ptype,
        "commission": str(data.get("commission") or "").strip()[:200],
        # Taux de commission (%) appliqué au prix de chaque activité (interne).
        "commission_rate": _coerce_float(data.get("commission_rate"), default=existing.get("commission_rate", 0.0)),
        "objective": str(data.get("objective") or "").strip()[:500],
        "notes": str(data.get("notes") or "").strip()[:2000],
        "enabled": _coerce_bool(data.get("enabled"), default=existing.get("enabled", False)),
        "tagline": str(data.get("tagline") or "").strip()[:200],
        "intro_html": str(data.get("intro_html") or "").strip(),
        "image": str(data.get("image") or existing.get("image") or "").strip(),
        "image_alt": str(data.get("image_alt") or existing.get("image_alt") or "").strip()[:200],
        "image_source_url": str(data.get("image_source_url") or existing.get("image_source_url") or "").strip()[:500],
        "image_prompt": str(data.get("image_prompt") or existing.get("image_prompt") or "").strip()[:300],
        "reviews": _clean_reviews_list(
            data.get("reviews") if data.get("reviews") is not None else existing.get("reviews", [])
        ),
        # Traductions EN (best-effort) : {tagline, intro_html}.
        "i18n": data.get("i18n") if data.get("i18n") is not None else existing.get("i18n", {}),
        "pages": _pages_list(existing),
        "created_at": existing.get("created_at") or today,
        "updated_at": today,
    }


def _normalize_page(partner: dict, data: dict, *, existing: dict | None = None) -> dict:
    existing = existing or {}
    title = str(data.get("title") or "").strip()[:160]
    if not title:
        raise ValueError("Le titre de la page est obligatoire.")
    page_id = data.get("id") or existing.get("id") or secrets.token_urlsafe(8)
    slug_source = data.get("slug") or existing.get("slug") or title
    slug = _unique_page_slug(partner, slug_source, exclude_id=page_id)
    today = date.today().isoformat()
    # Une page = une ACTIVITÉ proposée par le partenaire (avec son prix). La
    # commission de l'admin s'applique sur ce prix (cf. activity_commission()).
    return {
        "id": page_id,
        "slug": slug,
        "title": title,
        "price": _coerce_float(data.get("price"), default=existing.get("price", 0.0)),
        "currency": str(data.get("currency") or existing.get("currency") or "€").strip()[:6],
        "duration": str(data.get("duration") or existing.get("duration") or "").strip()[:80],
        "booking_url": _normalize_url(data.get("booking_url") or existing.get("booking_url") or ""),
        "content_html": str(data.get("content_html") or existing.get("content_html") or "").strip(),
        "meta_title": str(data.get("meta_title") or "").strip()[:70],
        "meta_description": str(data.get("meta_description") or "").strip()[:200],
        "image": str(data.get("image") or existing.get("image") or "").strip(),
        "image_alt": str(data.get("image_alt") or existing.get("image_alt") or "").strip()[:200],
        "image_source_url": str(data.get("image_source_url") or existing.get("image_source_url") or "").strip()[:500],
        "image_prompt": str(data.get("image_prompt") or existing.get("image_prompt") or "").strip()[:300],
        # Galerie d'images supplémentaires (URLs /static ou http), optionnelle.
        "images": _clean_url_list(data.get("images") if data.get("images") is not None else existing.get("images", [])),
        "reviews": _clean_reviews_list(
            data.get("reviews") if data.get("reviews") is not None else existing.get("reviews", [])
        ),
        "prompt": str(data.get("prompt") or existing.get("prompt") or "").strip()[:2000],
        "enabled": _coerce_bool(data.get("enabled"), default=existing.get("enabled", False)),
        # Traductions EN (best-effort) : {title, meta_title, meta_description, content_html}.
        "i18n": data.get("i18n") if data.get("i18n") is not None else existing.get("i18n", {}),
        "created_at": existing.get("created_at") or today,
        "updated_at": today,
    }


# ── i18n FR/EN (traduction best-effort + localisation au rendu) ──────────────

PARTNER_I18N_FIELDS = ("tagline", "intro_html")
PAGE_I18N_FIELDS = ("title", "meta_title", "meta_description", "content_html")


def _record_fr(record: dict, fields: tuple[str, ...]) -> dict:
    return {k: (record.get(k) or "") for k in fields}


def _needs_translation(record: dict, fields: tuple[str, ...]) -> bool:
    fr = _record_fr(record, fields)
    if not any(fr.values()):
        return False
    i18n = record.get("i18n") or {}
    return not (i18n.get("en") and i18n.get("fr") == fr)


def _translate_and_store(partner_id: str, page_id: str | None, fields: tuple[str, ...]) -> None:
    """Traduit FR→EN puis écrit i18n DIRECTEMENT dans le store (sans re-déclencher).

    Exécuté en tâche de fond : le formulaire admin répond immédiatement (le FR est
    déjà enregistré), l'EN apparaît quelques secondes plus tard.
    """
    target = find_partner(partner_id)
    if not target:
        return
    record = target
    if page_id:
        record = next((pg for pg in _pages_list(target) if pg.get("id") == page_id), None)
        if not record:
            return
    if not _needs_translation(record, fields):
        return
    fr = _record_fr(record, fields)
    try:
        from admin.groq_recommended_partner import translate_to_en
        en = translate_to_en(fr)
    except Exception:  # noqa: BLE001
        en = {}
    if not en:
        return
    items = get_partners()
    for p in items:
        if p.get("id") != partner_id:
            continue
        if page_id:
            for pg in _pages_list(p):
                if pg.get("id") == page_id:
                    pg["i18n"] = {"fr": fr, "en": en}
        else:
            p["i18n"] = {"fr": fr, "en": en}
        save_partners(items)
        return


def _schedule_translation(record: dict, partner_id: str, page_id: str | None, fields: tuple[str, ...]) -> None:
    if not _needs_translation(record, fields):
        return
    import threading
    threading.Thread(
        target=_translate_and_store, args=(partner_id, page_id, fields), daemon=True
    ).start()


def localize_page(page: dict, lang: str | None = None) -> dict:
    out = dict(page)
    if lang == "en":
        en = (page.get("i18n") or {}).get("en") or {}
        if en:
            out.update({k: en[k] for k in PAGE_I18N_FIELDS if en.get(k)})
    out["reviews"] = _localize_reviews_list(page.get("reviews"), lang)
    return out


def localize_partner(partner: dict, lang: str | None = None) -> dict:
    out = dict(partner)
    if lang == "en":
        en = (partner.get("i18n") or {}).get("en") or {}
        if en:
            out.update({k: en[k] for k in PARTNER_I18N_FIELDS if en.get(k)})
    out["reviews"] = _localize_reviews_list(partner.get("reviews"), lang)
    return out


# ── CRUD partenaire ──────────────────────────────────────────────────────────

def add_partner(data: dict) -> dict:
    partner = _normalize_partner(data)
    items = get_partners()
    items.insert(0, partner)
    save_partners(items)
    _schedule_translation(partner, partner["id"], None, PARTNER_I18N_FIELDS)
    return partner


def update_partner(pid: str, fields: dict, *, schedule_i18n: bool = True) -> dict:
    items = get_partners()
    for i, p in enumerate(items):
        if p.get("id") != pid:
            continue
        merged = {**p, **{k: v for k, v in fields.items() if v is not None}, "id": pid}
        items[i] = _normalize_partner(merged, existing=p)
        save_partners(items)
        if schedule_i18n:
            _schedule_translation(items[i], pid, None, PARTNER_I18N_FIELDS)
        return items[i]
    raise ValueError(f"Partenaire introuvable : {pid}")


def delete_partner(pid: str) -> None:
    items = [p for p in get_partners() if p.get("id") != pid]
    save_partners(items)


def set_partner_enabled(pid: str, enabled: bool) -> dict:
    return update_partner(pid, {"enabled": bool(enabled)})


# ── CRUD page ────────────────────────────────────────────────────────────────

def add_page(partner_id: str, page: dict) -> dict:
    items = get_partners()
    for i, p in enumerate(items):
        if p.get("id") != partner_id:
            continue
        normalized = _normalize_page(p, page)
        pages = _pages_list(p)
        pages.insert(0, normalized)
        p["pages"] = pages
        p["updated_at"] = date.today().isoformat()
        items[i] = p
        save_partners(items)
        _schedule_translation(normalized, partner_id, normalized["id"], PAGE_I18N_FIELDS)
        return normalized
    raise ValueError(f"Partenaire introuvable : {partner_id}")


def update_page(partner_id: str, page_id: str, fields: dict, *, schedule_i18n: bool = True) -> dict:
    items = get_partners()
    for i, p in enumerate(items):
        if p.get("id") != partner_id:
            continue
        pages = _pages_list(p)
        for j, pg in enumerate(pages):
            if pg.get("id") != page_id:
                continue
            merged = {**pg, **{k: v for k, v in fields.items() if v is not None}, "id": page_id}
            pages[j] = _normalize_page(p, merged, existing=pg)
            p["pages"] = pages
            p["updated_at"] = date.today().isoformat()
            items[i] = p
            save_partners(items)
            if schedule_i18n:
                _schedule_translation(pages[j], partner_id, page_id, PAGE_I18N_FIELDS)
            return pages[j]
        raise ValueError(f"Page introuvable : {page_id}")
    raise ValueError(f"Partenaire introuvable : {partner_id}")


def delete_page(partner_id: str, page_id: str) -> None:
    items = get_partners()
    for i, p in enumerate(items):
        if p.get("id") != partner_id:
            continue
        p["pages"] = [pg for pg in _pages_list(p) if pg.get("id") != page_id]
        p["updated_at"] = date.today().isoformat()
        items[i] = p
        save_partners(items)
        return
    raise ValueError(f"Partenaire introuvable : {partner_id}")


def set_page_enabled(partner_id: str, page_id: str, enabled: bool) -> dict:
    return update_page(partner_id, page_id, {"enabled": bool(enabled)})


def _build_review_from_form(form) -> dict:
    """Construit un avis depuis les champs formulaire admin."""
    author = str(form.get("review_author") or "").strip()
    text_fr = str(form.get("review_text_fr") or "").strip()
    if not author or not text_fr:
        raise ValueError("Nom et témoignage (FR) obligatoires pour l'avis.")
    rid = (form.get("review_id") or "").strip() or secrets.token_urlsafe(8)
    return {
        "id": rid,
        "author": author[:80],
        "location": str(form.get("review_location") or "").strip()[:80],
        "rating": _coerce_rating(form.get("review_rating")),
        "date": str(form.get("review_date") or date.today().isoformat())[:10],
        "text": {
            "fr": text_fr[:2000],
            "en": str(form.get("review_text_en") or "").strip()[:2000] or text_fr[:2000],
        },
        "enabled": bool(form.get("review_enabled")),
    }


def save_partner_review(partner_id: str, review: dict) -> dict:
    items = get_partners()
    for i, p in enumerate(items):
        if p.get("id") != partner_id:
            continue
        reviews = [r for r in _clean_reviews_list(p.get("reviews") or []) if r.get("id") != review["id"]]
        reviews.insert(0, review)
        p["reviews"] = reviews[:20]
        p["updated_at"] = date.today().isoformat()
        items[i] = p
        save_partners(items)
        return review
    raise ValueError(f"Partenaire introuvable : {partner_id}")


def delete_partner_review(partner_id: str, review_id: str) -> None:
    items = get_partners()
    for i, p in enumerate(items):
        if p.get("id") != partner_id:
            continue
        p["reviews"] = [r for r in _clean_reviews_list(p.get("reviews") or []) if r.get("id") != review_id]
        p["updated_at"] = date.today().isoformat()
        items[i] = p
        save_partners(items)
        return
    raise ValueError(f"Partenaire introuvable : {partner_id}")


def save_page_review(partner_id: str, page_id: str, review: dict) -> dict:
    items = get_partners()
    for i, p in enumerate(items):
        if p.get("id") != partner_id:
            continue
        pages = _pages_list(p)
        for j, pg in enumerate(pages):
            if pg.get("id") != page_id:
                continue
            reviews = [r for r in _clean_reviews_list(pg.get("reviews") or []) if r.get("id") != review["id"]]
            reviews.insert(0, review)
            pg["reviews"] = reviews[:20]
            pg["updated_at"] = date.today().isoformat()
            pages[j] = pg
            p["pages"] = pages
            p["updated_at"] = date.today().isoformat()
            items[i] = p
            save_partners(items)
            return review
        raise ValueError(f"Page introuvable : {page_id}")
    raise ValueError(f"Partenaire introuvable : {partner_id}")


def delete_page_review(partner_id: str, page_id: str, review_id: str) -> None:
    items = get_partners()
    for i, p in enumerate(items):
        if p.get("id") != partner_id:
            continue
        pages = _pages_list(p)
        for j, pg in enumerate(pages):
            if pg.get("id") != page_id:
                continue
            pg["reviews"] = [r for r in _clean_reviews_list(pg.get("reviews") or []) if r.get("id") != review_id]
            pg["updated_at"] = date.today().isoformat()
            pages[j] = pg
            p["pages"] = pages
            p["updated_at"] = date.today().isoformat()
            items[i] = p
            save_partners(items)
            return
        raise ValueError(f"Page introuvable : {page_id}")
    raise ValueError(f"Partenaire introuvable : {partner_id}")


def resolve_public_images(entity: dict) -> dict:
    """Résout l'URL d'image (repli source_url si fichier local absent sur Scalingo)."""
    from admin.image_service import persistent_image_url

    out = dict(entity)
    if out.get("image"):
        resolved = persistent_image_url(out.get("image"), None, out.get("image_source_url"))
        if resolved:
            out["image"] = resolved
    out.pop("image_source_url", None)
    return out


# ── Vue publique (sans champs internes) ──────────────────────────────────────

_PUBLIC_STRIP = set(_INTERNAL_FIELDS) | {"i18n"}


def _public_pages(partner: dict, lang: str | None = None) -> list[dict]:
    return [
        resolve_public_images({k: v for k, v in localize_page(pg, lang).items() if k != "i18n"})
        for pg in _pages_list(partner)
        if pg.get("enabled")
    ]


def public_partner(partner: dict, lang: str | None = None) -> dict:
    """Copie localisée sans champs internes, avec uniquement les pages publiées."""
    loc = localize_partner(partner, lang)
    out = resolve_public_images({k: v for k, v in loc.items() if k not in _PUBLIC_STRIP})
    out["reviews"] = loc.get("reviews") or []
    out["pages"] = _public_pages(partner, lang)
    return out


def list_public_partners(lang: str | None = None) -> list[dict]:
    """Partenaires activés ayant au moins une page activée (pour l'index public)."""
    out = []
    for p in get_partners():
        if not p.get("enabled"):
            continue
        if not _public_pages(p):
            continue
        out.append(public_partner(p, lang))
    return out


# ── Commission interne (sur le prix de l'activité) ───────────────────────────

def activity_commission(partner: dict, page: dict) -> dict:
    """Estimation interne de la commission pour une activité = prix × taux partenaire.

    Retourne {price, currency, rate, amount, has_estimate} pour affichage admin.
    """
    price = _coerce_float(page.get("price"))
    rate = _coerce_float(partner.get("commission_rate"))
    currency = page.get("currency") or "€"
    amount = round(price * rate / 100.0, 2) if price and rate else 0.0
    return {
        "price": price,
        "currency": currency,
        "rate": rate,
        "amount": amount,
        "has_estimate": bool(price and rate),
    }
