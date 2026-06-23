"""Leads agences — captation des demandes qualifiées (trip planner) à revendre
à un DMC / agence locale au lead.

Stockage PostgreSQL (table `agency_leads`) en prod, fallback JSON local
(`data/store/agency_leads.json`) en dev sans DATABASE_URL.

Modèle économique : chaque demande qualifiée (email + profil de voyage) vaut
~15-50 € auprès d'une agence francophone au Vietnam. On est payé à la livraison
du lead, pas à la réservation.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from admin.database import get_connection, is_postgres

LEADS_FILE = Path(__file__).parent.parent / "data" / "store" / "agency_leads.json"

# Valeur indicative d'un lead qualifié (pour l'estimation de potentiel dans l'admin).
ESTIMATED_LEAD_VALUE = 25.0

STATUSES = [
    ("nouveau", "Nouveau"),
    ("contacte", "Contacté"),
    ("vendu", "Vendu"),
    ("perdu", "Perdu"),
]
STATUS_KEYS = {k for k, _ in STATUSES}
STATUS_LABELS = dict(STATUSES)

GROUP_LABELS = {
    "solo": "Solo",
    "couple": "Couple",
    "family": "Famille",
    "friends": "Entre amis",
}
STYLE_LABELS = {
    "culture": "Culture & patrimoine",
    "nature": "Nature & aventure",
    "adventure": "Nature & aventure",
    "beach": "Plages & farniente",
    "relax": "Détente",
    "food": "Gastronomie",
    "luxury": "Luxe & confort",
    "budget": "Petit budget",
    "roadtrip": "Roadtrip",
    "romantic": "Romantique",
}
DURATION_LABELS = {
    "short": "≈ 7 jours",
    "medium": "≈ 10 jours",
    "long": "14 jours et +",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Fallback JSON local ───────────────────────────────────────────────


def _read_file() -> list[dict]:
    if not LEADS_FILE.exists():
        return []
    try:
        data = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_file(rows: list[dict]) -> None:
    LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEADS_FILE.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _next_local_id(rows: list[dict]) -> int:
    return (max((int(r.get("id", 0)) for r in rows), default=0) + 1) if rows else 1


def _clean(value, limit: int = 200) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


# ── Écriture ──────────────────────────────────────────────────────────


def add_lead(
    *,
    email: str,
    group_type: str | None = None,
    persons=None,
    style: str | None = None,
    duration: str | None = None,
    cities=None,
    lang: str | None = None,
    source_path: str | None = None,
    ip_hash: str | None = None,
) -> dict | None:
    """Enregistre un lead qualifié. Renvoie la ligne créée (ou None si email invalide)."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return None

    if isinstance(cities, (list, tuple)):
        cities = ", ".join(str(c).strip() for c in cities if str(c).strip())
    try:
        persons_val = int(persons) if persons not in (None, "") else None
    except (TypeError, ValueError):
        persons_val = None

    group_type = _clean(group_type, 40)
    style = _clean(style, 40)
    duration = _clean(duration, 40)
    cities = _clean(cities, 400)
    lang = _clean(lang, 8)
    source_path = _clean(source_path, 300)
    ip_hash = _clean(ip_hash, 80)
    now = _now_iso()

    if is_postgres():
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO agency_leads
                    (email, group_type, persons, style, duration, cities, lang,
                     source_path, status, sold_price, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'nouveau',0,NOW(),NOW())
                RETURNING id
                """,
                (email, group_type, persons_val, style, duration, cities, lang,
                 source_path),
            )
            row = cur.fetchone()
            new_id = (row["id"] if isinstance(row, dict) else row[0]) if row else None
        return {"id": new_id, "email": email}

    rows = _read_file()
    new = {
        "id": _next_local_id(rows),
        "email": email,
        "group_type": group_type,
        "persons": persons_val,
        "style": style,
        "duration": duration,
        "cities": cities,
        "lang": lang,
        "source_path": source_path,
        "status": "nouveau",
        "sold_price": 0,
        "agency": None,
        "note": None,
        "ip_hash": ip_hash,
        "created_at": now,
        "updated_at": now,
    }
    rows.append(new)
    _write_file(rows)
    return new


def update_lead(lead_id: int, *, status=None, sold_price=None, agency=None, note=None) -> bool:
    try:
        lead_id = int(lead_id)
    except (TypeError, ValueError):
        return False

    fields: dict = {}
    if status is not None and status in STATUS_KEYS:
        fields["status"] = status
    if sold_price is not None:
        try:
            fields["sold_price"] = round(float(str(sold_price).replace(",", ".")), 2)
        except (TypeError, ValueError):
            pass
    if agency is not None:
        fields["agency"] = _clean(agency, 120) or ""
    if note is not None:
        fields["note"] = _clean(note, 1000) or ""
    if not fields:
        return False

    if is_postgres():
        sets = ", ".join(f"{k} = %s" for k in fields)
        params = list(fields.values()) + [lead_id]
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE agency_leads SET {sets}, updated_at = NOW() WHERE id = %s",
                params,
            )
            return cur.rowcount > 0

    rows = _read_file()
    found = False
    for r in rows:
        if int(r.get("id", 0)) == lead_id:
            r.update(fields)
            r["updated_at"] = _now_iso()
            found = True
            break
    if found:
        _write_file(rows)
    return found


def delete_lead(lead_id: int) -> bool:
    try:
        lead_id = int(lead_id)
    except (TypeError, ValueError):
        return False
    if is_postgres():
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM agency_leads WHERE id = %s", (lead_id,))
            return cur.rowcount > 0
    rows = _read_file()
    kept = [r for r in rows if int(r.get("id", 0)) != lead_id]
    if len(kept) == len(rows):
        return False
    _write_file(kept)
    return True


# ── Lecture ───────────────────────────────────────────────────────────

_FIELDS = (
    "id", "email", "group_type", "persons", "style", "duration", "cities",
    "lang", "source_path", "status", "sold_price", "agency", "note",
    "created_at", "updated_at",
)


def get_leads(status: str | None = None) -> list[dict]:
    if is_postgres():
        with get_connection() as conn:
            cur = conn.cursor()
            cols = ", ".join(_FIELDS)
            if status and status in STATUS_KEYS:
                cur.execute(
                    f"SELECT {cols} FROM agency_leads WHERE status = %s ORDER BY created_at DESC",
                    (status,),
                )
            else:
                cur.execute(
                    f"SELECT {cols} FROM agency_leads ORDER BY created_at DESC"
                )
            raw = cur.fetchall()
        rows = []
        for r in raw:
            if isinstance(r, dict):
                rows.append(dict(r))
            else:
                rows.append(dict(zip(_FIELDS, r)))
    else:
        rows = _read_file()
        rows.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
        if status and status in STATUS_KEYS:
            rows = [r for r in rows if r.get("status") == status]

    for r in rows:
        r["status"] = r.get("status") or "nouveau"
        r["status_label"] = STATUS_LABELS.get(r["status"], r["status"])
        r["group_label"] = GROUP_LABELS.get(r.get("group_type"), r.get("group_type") or "—")
        r["style_label"] = STYLE_LABELS.get(r.get("style"), r.get("style") or "—")
        r["duration_label"] = DURATION_LABELS.get(r.get("duration"), r.get("duration") or "—")
        r["created_at"] = str(r.get("created_at") or "")[:16].replace("T", " ")
    return rows


def get_stats() -> dict:
    rows = get_leads()
    by_status = {k: 0 for k, _ in STATUSES}
    revenue = 0.0
    for r in rows:
        by_status[r.get("status", "nouveau")] = by_status.get(r.get("status", "nouveau"), 0) + 1
        try:
            revenue += float(r.get("sold_price") or 0)
        except (TypeError, ValueError):
            pass
    total = len(rows)
    open_leads = by_status.get("nouveau", 0) + by_status.get("contacte", 0)
    return {
        "total": total,
        "by_status": by_status,
        "revenue": round(revenue, 2),
        "open": open_leads,
        # Potentiel : leads non encore vendus × valeur indicative d'un lead.
        "potential": round(open_leads * ESTIMATED_LEAD_VALUE, 2),
        "lead_value": ESTIMATED_LEAD_VALUE,
    }


def count_leads(status: str | None = None) -> int:
    if is_postgres():
        with get_connection() as conn:
            cur = conn.cursor()
            if status and status in STATUS_KEYS:
                cur.execute("SELECT COUNT(*) FROM agency_leads WHERE status = %s", (status,))
            else:
                cur.execute("SELECT COUNT(*) FROM agency_leads")
            row = cur.fetchone()
        return int((row[0] if not isinstance(row, dict) else list(row.values())[0]) or 0)
    rows = _read_file()
    if status and status in STATUS_KEYS:
        return sum(1 for r in rows if r.get("status") == status)
    return len(rows)


def export_csv() -> str:
    rows = get_leads()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "date", "email", "groupe", "personnes", "style", "duree",
        "villes", "langue", "source", "statut", "prix_vendu", "agence", "note",
    ])
    for r in rows:
        writer.writerow([
            r.get("id"), r.get("created_at"), r.get("email"),
            r.get("group_label"), r.get("persons") or "", r.get("style_label"),
            r.get("duration_label"), r.get("cities") or "", r.get("lang") or "",
            r.get("source_path") or "", r.get("status_label"),
            r.get("sold_price") or 0, r.get("agency") or "", r.get("note") or "",
        ])
    return buf.getvalue()
