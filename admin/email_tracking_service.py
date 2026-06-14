"""Suivi ouvertures / clics des emails admin (pixel + redirections signées)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import datetime, timezone
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import config
from admin.database import get_connection, is_postgres
from admin.facebook_service import sanitize_campaign

logger = logging.getLogger(__name__)

SITE_URL = config.SITE_URL.rstrip("/")
PIXEL_GIF = base64.b64decode(
    "R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="
)
_HREF_RE = re.compile(r'(<a\b[^>]*\shref=")([^"]+)(")', re.I)
_SCHEMA_READY = False

EMAIL_UTM_MEDIUM = "email"
EMAIL_UTM_SOURCES = frozenset({
    "newsletter", "partenariat", "test", "email-test",
    "actualite", "nouveau_guide", "conseils", "promo_pdf", "saison",
})


def _secret() -> bytes:
    return os.environ.get("SECRET_KEY", "dev-change-in-production").encode()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_email_tracking_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    try:
        with get_connection() as conn:
            if is_postgres():
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS email_sends (
                        id SERIAL PRIMARY KEY,
                        send_token TEXT NOT NULL UNIQUE,
                        recipient_email TEXT NOT NULL,
                        recipient_name TEXT,
                        partner_id TEXT,
                        subject TEXT,
                        email_type TEXT NOT NULL DEFAULT 'newsletter',
                        tracking_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        open_count INTEGER NOT NULL DEFAULT 0,
                        first_opened_at TIMESTAMPTZ,
                        last_opened_at TIMESTAMPTZ,
                        click_count INTEGER NOT NULL DEFAULT 0,
                        first_clicked_at TIMESTAMPTZ,
                        last_clicked_at TIMESTAMPTZ
                    )""")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS email_click_events (
                        id SERIAL PRIMARY KEY,
                        send_id INTEGER NOT NULL REFERENCES email_sends(id) ON DELETE CASCADE,
                        url TEXT NOT NULL,
                        clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )""")
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_email_sends_partner ON email_sends(partner_id)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_email_sends_recipient ON email_sends(recipient_email)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_email_clicks_send ON email_click_events(send_id)"
                )
            else:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS email_sends (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        send_token TEXT NOT NULL UNIQUE,
                        recipient_email TEXT NOT NULL,
                        recipient_name TEXT,
                        partner_id TEXT,
                        subject TEXT,
                        email_type TEXT NOT NULL DEFAULT 'newsletter',
                        tracking_enabled INTEGER NOT NULL DEFAULT 1,
                        sent_at TEXT NOT NULL,
                        open_count INTEGER NOT NULL DEFAULT 0,
                        first_opened_at TEXT,
                        last_opened_at TEXT,
                        click_count INTEGER NOT NULL DEFAULT 0,
                        first_clicked_at TEXT,
                        last_clicked_at TEXT
                    )""")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS email_click_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        send_id INTEGER NOT NULL,
                        url TEXT NOT NULL,
                        clicked_at TEXT NOT NULL,
                        FOREIGN KEY (send_id) REFERENCES email_sends(id) ON DELETE CASCADE
                    )""")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_email_sends_partner ON email_sends(partner_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_email_sends_recipient ON email_sends(recipient_email)"
                )
        _SCHEMA_READY = True
    except Exception:
        logger.exception("Impossible d'initialiser le schéma email_sends")


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    cols = (
        "id", "send_token", "recipient_email", "recipient_name", "partner_id",
        "subject", "email_type", "tracking_enabled", "sent_at",
        "open_count", "first_opened_at", "last_opened_at",
        "click_count", "first_clicked_at", "last_clicked_at",
    )
    return {k: row[i] for i, k in enumerate(cols) if i < len(row)}


def _normalize_send(row: dict) -> dict:
    out = dict(row)
    out["tracking_enabled"] = bool(out.get("tracking_enabled", True))
    for key in ("sent_at", "first_opened_at", "last_opened_at", "first_clicked_at", "last_clicked_at"):
        if out.get(key) is not None:
            out[key] = str(out[key])
    return out


def open_tracking_url(token: str) -> str:
    return f"{SITE_URL}/e/o/{quote(token, safe='')}.gif"


def _sign_click_target(send_token: str, url: str) -> str:
    digest = hmac.new(_secret(), f"{send_token}:{url}".encode(), hashlib.sha256).hexdigest()[:20]
    payload = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    return f"{payload}.{digest}"


def verify_click_target(send_token: str, signed: str) -> str | None:
    if not send_token or not signed or "." not in signed:
        return None
    payload, digest = signed.rsplit(".", 1)
    pad = "=" * (-len(payload) % 4)
    try:
        url = base64.urlsafe_b64decode(payload + pad).decode()
    except Exception:
        return None
    expected = hmac.new(_secret(), f"{send_token}:{url}".encode(), hashlib.sha256).hexdigest()[:20]
    if not hmac.compare_digest(expected, digest):
        return None
    return url


def click_tracking_url(token: str, target_url: str) -> str:
    absolute = _absolute_url(target_url)
    signed = _sign_click_target(token, absolute)
    return f"{SITE_URL}/e/c/{quote(token, safe='')}?u={quote(signed, safe='')}"


def _absolute_url(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("/"):
        return f"{SITE_URL}{url}"
    return url


def _is_our_site_url(url: str) -> bool:
    absolute = _absolute_url(url)
    try:
        host = (urlparse(absolute).netloc or "").lower()
    except Exception:  # noqa: BLE001
        return False
    if not host:
        return absolute.startswith(SITE_URL)
    site_host = (urlparse(SITE_URL).netloc or "").lower()
    allowed = {
        site_host,
        "www.insidevietnamtravel.fr",
        "insidevietnamtravel.fr",
        "www.insidevietnamtravel.com",
        "insidevietnamtravel.com",
    }
    return host in allowed or host.endswith(".insidevietnamtravel.fr")


def email_utm_params(
    *,
    email_type: str = "newsletter",
    subject: str = "",
    send_token: str = "",
    partner_id: str = "",
) -> dict[str, str]:
    """Nomenclature UTM email — même logique que les réseaux sociaux (invisible côté visiteur)."""
    source = sanitize_campaign(email_type or "newsletter")[:40]
    campaign = sanitize_campaign(subject or email_type or "newsletter")[:80]
    params = {
        "utm_source": source,
        "utm_medium": EMAIL_UTM_MEDIUM,
        "utm_campaign": campaign,
    }
    if send_token:
        params["utm_content"] = sanitize_campaign(send_token)[:24]
    elif partner_id:
        params["utm_content"] = sanitize_campaign(partner_id)[:40]
    return params


def add_email_utm(
    url: str,
    *,
    email_type: str = "newsletter",
    subject: str = "",
    send_token: str = "",
    partner_id: str = "",
) -> str:
    """Ajoute UTM aux liens du site (préservant la query existante)."""
    if not url or not _is_our_site_url(url):
        return url
    low = url.lower()
    if "desinscription" in low or "unsubscribe" in low:
        return url
    absolute = _absolute_url(url)
    parts = urlparse(absolute)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key, val in email_utm_params(
        email_type=email_type,
        subject=subject,
        send_token=send_token,
        partner_id=partner_id,
    ).items():
        query[key] = val
    rebuilt = urlunparse(parts._replace(query=urlencode(query)))
    if url.startswith("/"):
        parsed = urlparse(rebuilt)
        return parsed.path + (f"?{parsed.query}" if parsed.query else "") + (parsed.fragment or "")
    return rebuilt


def inject_email_utm(
    html: str,
    *,
    email_type: str = "newsletter",
    subject: str = "",
    send_token: str = "",
    partner_id: str = "",
) -> str:
    """UTM invisibles sur tous les liens internes (retirés ensuite par main.js)."""
    if not html:
        return html

    def repl(match: re.Match) -> str:
        prefix, href, suffix = match.group(1), match.group(2), match.group(3)
        if not _should_track_link(href) or not _is_our_site_url(href):
            return match.group(0)
        tagged = add_email_utm(
            href,
            email_type=email_type,
            subject=subject,
            send_token=send_token,
            partner_id=partner_id,
        )
        return f"{prefix}{tagged}{suffix}"

    return _HREF_RE.sub(repl, html)


def _should_track_link(url: str) -> bool:
    u = (url or "").strip().lower()
    if not u or u.startswith("#") or u.startswith("mailto:"):
        return False
    if "/e/c/" in u or "/e/o/" in u:
        return False
    if "desinscription" in u or "unsubscribe" in u:
        return False
    return u.startswith("http://") or u.startswith("https://") or u.startswith("/")


def inject_tracking(
    html: str,
    token: str,
    *,
    email_type: str = "newsletter",
    subject: str = "",
    partner_id: str = "",
) -> str:
    """UTM internes + pixel d'ouverture + réécriture des liens cliquables."""
    if not html or not token:
        return html

    html = inject_email_utm(
        html,
        email_type=email_type,
        subject=subject,
        send_token=token,
        partner_id=partner_id,
    )

    def repl(match: re.Match) -> str:
        prefix, href, suffix = match.group(1), match.group(2), match.group(3)
        if not _should_track_link(href):
            return match.group(0)
        return f"{prefix}{click_tracking_url(token, href)}{suffix}"

    html = _HREF_RE.sub(repl, html)
    pixel = (
        f'<img src="{open_tracking_url(token)}" width="1" height="1" alt="" '
        'style="display:block;width:1px;height:1px;border:0;margin:0;padding:0;" />'
    )
    if re.search(r"</body>", html, re.I):
        html = re.sub(r"</body>", pixel + "</body>", html, count=1, flags=re.I)
    else:
        html += pixel
    return html


def create_email_send(
    *,
    recipient_email: str,
    subject: str,
    email_type: str = "newsletter",
    recipient_name: str = "",
    partner_id: str = "",
    tracking_enabled: bool = True,
    sent_at: str | None = None,
) -> dict:
    ensure_email_tracking_schema()
    token = secrets.token_urlsafe(24)
    email = recipient_email.strip().lower()
    ts = sent_at or _now_iso()
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """
                INSERT INTO email_sends (
                    send_token, recipient_email, recipient_name, partner_id,
                    subject, email_type, tracking_enabled, sent_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, send_token, recipient_email, recipient_name, partner_id,
                          subject, email_type, tracking_enabled, sent_at,
                          open_count, first_opened_at, last_opened_at,
                          click_count, first_clicked_at, last_clicked_at
                """,
                (
                    token, email, (recipient_name or "")[:120], (partner_id or "")[:40],
                    (subject or "")[:200], (email_type or "newsletter")[:40],
                    tracking_enabled, ts,
                ),
            )
            row = cur.fetchone()
        else:
            cur.execute(
                """
                INSERT INTO email_sends (
                    send_token, recipient_email, recipient_name, partner_id,
                    subject, email_type, tracking_enabled, sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    token, email, (recipient_name or "")[:120], (partner_id or "")[:40],
                    (subject or "")[:200], (email_type or "newsletter")[:40],
                    1 if tracking_enabled else 0, ts,
                ),
            )
            cur.execute(
                """
                SELECT id, send_token, recipient_email, recipient_name, partner_id,
                       subject, email_type, tracking_enabled, sent_at,
                       open_count, first_opened_at, last_opened_at,
                       click_count, first_clicked_at, last_clicked_at
                FROM email_sends WHERE send_token = ?
                """,
                (token,),
            )
            row = cur.fetchone()
    return _normalize_send(_row_to_dict(row))


def delete_email_send(send_id: int) -> None:
    ensure_email_tracking_schema()
    with get_connection() as conn:
        cur = conn.cursor()
        ph = "%s" if is_postgres() else "?"
        cur.execute(f"DELETE FROM email_sends WHERE id = {ph}", (send_id,))


def _get_send_by_token(token: str) -> dict | None:
    ensure_email_tracking_schema()
    with get_connection() as conn:
        cur = conn.cursor()
        ph = "%s" if is_postgres() else "?"
        cur.execute(
            f"""
            SELECT id, send_token, recipient_email, recipient_name, partner_id,
                   subject, email_type, tracking_enabled, sent_at,
                   open_count, first_opened_at, last_opened_at,
                   click_count, first_clicked_at, last_clicked_at
            FROM email_sends WHERE send_token = {ph}
            """,
            (token,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return _normalize_send(_row_to_dict(row))


def record_open(token: str) -> bool:
    send = _get_send_by_token(token)
    if not send or not send.get("tracking_enabled"):
        return False
    now = _now_iso()
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """
                UPDATE email_sends SET
                    open_count = open_count + 1,
                    first_opened_at = COALESCE(first_opened_at, %s),
                    last_opened_at = %s
                WHERE send_token = %s AND tracking_enabled = TRUE
                """,
                (now, now, token),
            )
        else:
            cur.execute(
                """
                UPDATE email_sends SET
                    open_count = open_count + 1,
                    first_opened_at = COALESCE(first_opened_at, ?),
                    last_opened_at = ?
                WHERE send_token = ? AND tracking_enabled = 1
                """,
                (now, now, token),
            )
    return True


def record_click(token: str, target_url: str) -> bool:
    send = _get_send_by_token(token)
    if not send or not send.get("tracking_enabled"):
        return False
    now = _now_iso()
    send_id = send["id"]
    url = (target_url or "")[:2000]
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                "INSERT INTO email_click_events (send_id, url, clicked_at) VALUES (%s, %s, %s)",
                (send_id, url, now),
            )
            cur.execute(
                """
                UPDATE email_sends SET
                    click_count = click_count + 1,
                    first_clicked_at = COALESCE(first_clicked_at, %s),
                    last_clicked_at = %s
                WHERE id = %s
                """,
                (now, now, send_id),
            )
        else:
            cur.execute(
                "INSERT INTO email_click_events (send_id, url, clicked_at) VALUES (?, ?, ?)",
                (send_id, url, now),
            )
            cur.execute(
                """
                UPDATE email_sends SET
                    click_count = click_count + 1,
                    first_clicked_at = COALESCE(first_clicked_at, ?),
                    last_clicked_at = ?
                WHERE id = ?
                """,
                (now, now, send_id),
            )
    return True


def _count_sends_for_partner(partner_id: str) -> int:
    ensure_email_tracking_schema()
    with get_connection() as conn:
        cur = conn.cursor()
        ph = "%s" if is_postgres() else "?"
        cur.execute(
            f"SELECT COUNT(*) AS n FROM email_sends WHERE partner_id = {ph}",
            (partner_id,),
        )
        row = cur.fetchone()
    if isinstance(row, dict):
        return int(row.get("n") or 0)
    return int(row[0] if row else 0)


def ensure_legacy_partner_sends() -> None:
    """Crée une entrée « sans suivi » pour les partenaires contactés avant le tracking."""
    from admin.partners_service import get_partnerships

    for p in get_partnerships():
        pid = (p.get("id") or "").strip()
        contacted = (p.get("last_contacted_at") or "").strip()
        email = (p.get("email") or "").strip().lower()
        if not pid or not contacted or not email:
            continue
        if _count_sends_for_partner(pid) > 0:
            continue
        try:
            create_email_send(
                recipient_email=email,
                recipient_name=p.get("name") or "",
                partner_id=pid,
                subject="(email partenariat — envoyé avant suivi)",
                email_type="partenariat",
                tracking_enabled=False,
                sent_at=f"{contacted}T12:00:00+00:00",
            )
        except Exception:
            logger.exception("Backfill email send for partner %s", pid)


def get_latest_sends_by_partner(partner_ids: list[str]) -> dict[str, dict]:
    """Dernier envoi connu par partenaire (stats ouverture / clic)."""
    ensure_email_tracking_schema()
    ensure_legacy_partner_sends()
    ids = [i for i in partner_ids if i]
    if not ids:
        return {}
    out: dict[str, dict] = {}
    with get_connection() as conn:
        cur = conn.cursor()
        for pid in ids:
            ph = "%s" if is_postgres() else "?"
            cur.execute(
                f"""
                SELECT id, send_token, recipient_email, recipient_name, partner_id,
                       subject, email_type, tracking_enabled, sent_at,
                       open_count, first_opened_at, last_opened_at,
                       click_count, first_clicked_at, last_clicked_at
                FROM email_sends
                WHERE partner_id = {ph}
                ORDER BY sent_at DESC
                LIMIT 1
                """,
                (pid,),
            )
            row = cur.fetchone()
            if row:
                out[pid] = _normalize_send(_row_to_dict(row))
    return out


def get_latest_send_for_email(email: str) -> dict | None:
    ensure_email_tracking_schema()
    email = (email or "").strip().lower()
    if not email:
        return None
    with get_connection() as conn:
        cur = conn.cursor()
        ph = "%s" if is_postgres() else "?"
        cur.execute(
            f"""
            SELECT id, send_token, recipient_email, recipient_name, partner_id,
                   subject, email_type, tracking_enabled, sent_at,
                   open_count, first_opened_at, last_opened_at,
                   click_count, first_clicked_at, last_clicked_at
            FROM email_sends
            WHERE recipient_email = {ph}
            ORDER BY sent_at DESC
            LIMIT 1
            """,
            (email,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return _normalize_send(_row_to_dict(row))


def get_emails_with_partnership_sends() -> set[str]:
    """Emails ayant déjà reçu un email partenariat (historique suivi)."""
    ensure_email_tracking_schema()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT LOWER(recipient_email) AS recipient_email
            FROM email_sends
            WHERE email_type = 'partenariat'
            """
        )
        rows = cur.fetchall()
    out: set[str] = set()
    for row in rows:
        d = _row_to_dict(row)
        email = (d.get("recipient_email") or "").strip().lower()
        if email:
            out.add(email)
    return out


def get_recent_sends(limit: int = 30) -> list[dict]:
    ensure_email_tracking_schema()
    limit = max(1, min(limit, 100))
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """
                SELECT id, send_token, recipient_email, recipient_name, partner_id,
                       subject, email_type, tracking_enabled, sent_at,
                       open_count, first_opened_at, last_opened_at,
                       click_count, first_clicked_at, last_clicked_at
                FROM email_sends
                ORDER BY sent_at DESC
                LIMIT %s
                """,
                (limit,),
            )
        else:
            cur.execute(
                """
                SELECT id, send_token, recipient_email, recipient_name, partner_id,
                       subject, email_type, tracking_enabled, sent_at,
                       open_count, first_opened_at, last_opened_at,
                       click_count, first_clicked_at, last_clicked_at
                FROM email_sends
                ORDER BY sent_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cur.fetchall()
    return [_normalize_send(_row_to_dict(r)) for r in rows]


def get_click_urls_for_send(send_id: int, limit: int = 8) -> list[str]:
    ensure_email_tracking_schema()
    with get_connection() as conn:
        cur = conn.cursor()
        if is_postgres():
            cur.execute(
                """
                SELECT url FROM email_click_events
                WHERE send_id = %s
                ORDER BY clicked_at DESC
                LIMIT %s
                """,
                (send_id, limit),
            )
        else:
            cur.execute(
                """
                SELECT url FROM email_click_events
                WHERE send_id = ?
                ORDER BY clicked_at DESC
                LIMIT ?
                """,
                (send_id, limit),
            )
        rows = cur.fetchall()
    urls = []
    for row in rows:
        url = row["url"] if isinstance(row, dict) else row[0]
        if url and url not in urls:
            urls.append(url)
    return urls


def format_tracking_label(send: dict | None) -> str:
    if not send:
        return ""
    sent = (send.get("sent_at") or "")[:10]
    if not send.get("tracking_enabled"):
        return f"Envoyé {sent} (sans suivi)"
    opens = int(send.get("open_count") or 0)
    clicks = int(send.get("click_count") or 0)
    parts = [f"Envoyé {sent}"]
    if opens:
        parts.append(f"{opens} ouverture{'s' if opens > 1 else ''}")
    else:
        parts.append("non ouvert")
    if clicks:
        parts.append(f"{clicks} clic{'s' if clicks > 1 else ''}")
    return " · ".join(parts)


EMAIL_TYPE_LABELS = {
    "partenariat": "Partenariat",
    "newsletter": "Newsletter",
    "test": "Test",
}


def get_analytics_summary() -> dict:
    """Totaux ouvertures / clics pour le dashboard admin."""
    ensure_email_tracking_schema()
    empty = {
        "total_sends": 0,
        "tracked_sends": 0,
        "legacy_sends": 0,
        "total_opens": 0,
        "total_clicks": 0,
        "opened_sends": 0,
        "clicked_sends": 0,
    }
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if is_postgres():
                cur.execute("""
                    SELECT
                        COUNT(*)::int AS total,
                        COUNT(*) FILTER (WHERE tracking_enabled)::int AS tracked,
                        COALESCE(SUM(open_count), 0)::int AS opens,
                        COALESCE(SUM(click_count), 0)::int AS clicks,
                        COUNT(*) FILTER (WHERE tracking_enabled AND open_count > 0)::int AS opened,
                        COUNT(*) FILTER (WHERE tracking_enabled AND click_count > 0)::int AS clicked
                    FROM email_sends
                """)
            else:
                cur.execute("""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN tracking_enabled = 1 THEN 1 ELSE 0 END) AS tracked,
                        COALESCE(SUM(open_count), 0) AS opens,
                        COALESCE(SUM(click_count), 0) AS clicks,
                        SUM(CASE WHEN tracking_enabled = 1 AND open_count > 0 THEN 1 ELSE 0 END) AS opened,
                        SUM(CASE WHEN tracking_enabled = 1 AND click_count > 0 THEN 1 ELSE 0 END) AS clicked
                    FROM email_sends
                """)
            row = cur.fetchone()
        if not row:
            return empty
        if isinstance(row, dict):
            total = int(row.get("total") or 0)
            tracked = int(row.get("tracked") or 0)
            return {
                "total_sends": total,
                "tracked_sends": tracked,
                "legacy_sends": total - tracked,
                "total_opens": int(row.get("opens") or 0),
                "total_clicks": int(row.get("clicks") or 0),
                "opened_sends": int(row.get("opened") or 0),
                "clicked_sends": int(row.get("clicked") or 0),
            }
        return {
            "total_sends": int(row[0] or 0),
            "tracked_sends": int(row[1] or 0),
            "legacy_sends": int(row[0] or 0) - int(row[1] or 0),
            "total_opens": int(row[2] or 0),
            "total_clicks": int(row[3] or 0),
            "opened_sends": int(row[4] or 0),
            "clicked_sends": int(row[5] or 0),
        }
    except Exception:
        logger.exception("Résumé analytics email indisponible")
        return empty


def get_sends_for_admin_table(limit: int = 100) -> list[dict]:
    """Envois récents enrichis (URLs cliquées) pour la page admin."""
    sends = get_recent_sends(limit)
    for send in sends:
        if send.get("click_count", 0) > 0:
            send["click_urls"] = get_click_urls_for_send(send["id"], limit=5)
        else:
            send["click_urls"] = []
    return sends
