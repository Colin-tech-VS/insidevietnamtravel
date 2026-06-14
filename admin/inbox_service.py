"""Boîte de réception unifiée — formulaire contact + IMAP + badges d'origine."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from admin.contact_service import (
    delete_message as delete_form_message,
    get_contact_messages,
    mark_message_read,
)
from admin.imap_service import (
    CONTACT_SUBJECT_PREFIX,
    delete_imap_message,
    fetch_inbox_messages,
    is_imap_configured,
    mark_imap_read,
)

SOURCE_LABELS = {
    "contact_form": "Formulaire contact",
    "reply": "Réponse email",
    "external": "Email externe",
}

_REPLY_SUBJECT_RE = re.compile(r"^(re|fw|fwd|aw|tr|ré|ref)\s*:", re.I)
_OUR_DOMAIN = "insidevietnamtravel.fr"
_SNIPPET_LEN = 140
# Intervalle conseillé pour recharger la page Contact (sync IMAP à chaque chargement).
IMAP_SYNC_INTERVAL_SEC = max(60, int(os.environ.get("CONTACT_IMAP_SYNC_SECONDS", "180")))


def _snippet(text: str, *, max_len: int = _SNIPPET_LEN) -> str:
    one_line = re.sub(r"\s+", " ", (text or "").strip())
    if len(one_line) <= max_len:
        return one_line
    return one_line[: max_len - 1].rstrip() + "…"


def _enrich_message(msg: dict) -> dict:
    import base64

    out = dict(msg)
    plain = (out.get("message") or "").strip()
    html = (out.get("message_html") or "").strip()
    if not plain and html:
        from admin.mail_service import _strip_tags

        plain = _strip_tags(html)
        out["message"] = plain
    out["has_html"] = bool(html)
    out["snippet"] = _snippet(plain)
    if html:
        out["message_html_b64"] = base64.b64encode(html.encode("utf-8")).decode("ascii")
    else:
        out["message_html_b64"] = ""
    return out


def get_unified_inbox(*, limit: int = 80) -> dict:
    """Fusionne IMAP + messages formulaire, avec classification et dédoublonnage."""
    form_messages = get_contact_messages()
    imap_messages: list[dict] = []
    imap_error = ""

    if is_imap_configured():
        try:
            imap_messages = fetch_inbox_messages(limit=limit)
        except Exception as exc:  # noqa: BLE001
            imap_error = str(exc)[:300]

    known_recipients = _sent_recipient_emails()
    merged = _merge_inbox(form_messages, imap_messages, known_recipients)
    merged.sort(key=lambda m: m.get("created_at") or "", reverse=True)
    merged = [_enrich_message(m) for m in merged]

    by_source = {key: 0 for key in SOURCE_LABELS}
    for m in merged:
        src = m.get("source", "external")
        by_source[src] = by_source.get(src, 0) + 1

    unread = sum(1 for m in merged if not m.get("read"))

    return {
        "messages": merged[:limit],
        "imap_ok": is_imap_configured() and not imap_error,
        "imap_error": imap_error,
        "unread": unread,
        "by_source": by_source,
        "source_labels": SOURCE_LABELS,
        "synced_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "sync_interval_sec": IMAP_SYNC_INTERVAL_SEC,
    }


def count_unread_inbox() -> int:
    try:
        return get_unified_inbox(limit=200)["unread"]
    except Exception:  # noqa: BLE001
        return sum(1 for m in get_contact_messages() if not m.get("read"))


def mark_inbox_read(msg_id: str, *, form_id: str = "") -> bool:
    ok = False
    if msg_id.startswith("imap:"):
        ok = mark_imap_read(msg_id.split(":", 1)[1])
    else:
        raw_id = msg_id.replace("form:", "", 1) if msg_id.startswith("form:") else msg_id
        ok = mark_message_read(raw_id)
    if form_id and not form_id.startswith("imap:"):
        mark_message_read(form_id)
    return ok


def delete_inbox_message(msg_id: str) -> bool:
    if msg_id.startswith("imap:"):
        return delete_imap_message(msg_id.split(":", 1)[1])
    raw_id = msg_id.replace("form:", "", 1) if msg_id.startswith("form:") else msg_id
    return delete_form_message(raw_id)


def classify_message(msg: dict, known_recipients: set[str]) -> str:
    if msg.get("source"):
        return msg["source"]

    raw_subject = msg.get("raw_subject") or msg.get("subject") or ""
    subject = msg.get("subject") or ""
    email = (msg.get("email") or "").strip().lower()
    channel = msg.get("channel", "")
    in_reply_to = (msg.get("in_reply_to") or "").lower()
    references = (msg.get("references") or "").lower()

    if channel == "form" or raw_subject.startswith(CONTACT_SUBJECT_PREFIX):
        return "contact_form"

    is_reply_subject = bool(_REPLY_SUBJECT_RE.match(subject.strip()) or _REPLY_SUBJECT_RE.match(raw_subject.strip()))
    has_thread = _OUR_DOMAIN in in_reply_to or _OUR_DOMAIN in references
    if email in known_recipients and (is_reply_subject or has_thread or in_reply_to):
        return "reply"

    if is_reply_subject and email in known_recipients:
        return "reply"

    return "external"


def _sent_recipient_emails() -> set[str]:
    try:
        from admin.database import get_connection
        from admin.email_tracking_service import ensure_email_tracking_schema

        ensure_email_tracking_schema()
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT LOWER(recipient_email) AS e FROM email_sends WHERE recipient_email != ''")
            rows = cur.fetchall()
        out: set[str] = set()
        for row in rows:
            if isinstance(row, dict):
                e = (row.get("e") or "").strip().lower()
            else:
                e = (row[0] if row else "").strip().lower()
            if e:
                out.add(e)
        return out
    except Exception:  # noqa: BLE001
        return set()


def _merge_inbox(
    form_messages: list[dict],
    imap_messages: list[dict],
    known_recipients: set[str],
) -> list[dict]:
    merged: list[dict] = []
    matched_form_ids: set[str] = set()

    for im in imap_messages:
        item = dict(im)
        item["source"] = classify_message(item, known_recipients)

        for fm in form_messages:
            if _form_matches_imap(fm, im):
                matched_form_ids.add(fm["id"])
                item["form_id"] = fm["id"]
                if fm.get("name"):
                    item["name"] = fm["name"]
                if fm.get("message") and len(fm["message"]) >= len(item.get("message") or ""):
                    item["message"] = fm["message"]
                if fm.get("lang"):
                    item["lang"] = fm["lang"]
                item["source"] = "contact_form"
                item["read"] = item.get("read") and fm.get("read", False)
                break

        item["source_label"] = SOURCE_LABELS.get(item["source"], item["source"])
        merged.append(item)

    for fm in form_messages:
        if fm["id"] in matched_form_ids:
            continue
        item = {
            "id": f"form:{fm['id']}",
            "channel": "form",
            "form_id": fm["id"],
            "name": fm.get("name") or "",
            "email": fm.get("email") or "",
            "subject": fm.get("subject") or "",
            "message": fm.get("message") or "",
            "message_html": "",
            "lang": fm.get("lang") or "fr",
            "created_at": fm.get("created_at") or "",
            "read": bool(fm.get("read")),
            "source": "contact_form",
            "source_label": SOURCE_LABELS["contact_form"],
        }
        merged.append(item)

    return merged


def _form_matches_imap(form: dict, imap: dict) -> bool:
    form_email = (form.get("email") or "").strip().lower()
    imap_email = (imap.get("email") or "").strip().lower()
    if not form_email or form_email != imap_email:
        return False

    form_subject = (form.get("subject") or "").strip().lower()
    imap_subject = (imap.get("subject") or "").strip().lower()
    raw = (imap.get("raw_subject") or "").strip().lower()
    if form_subject not in imap_subject and form_subject not in raw:
        if not raw.startswith("[contact]") or form_subject not in raw.replace("[contact]", "").strip():
            return False

    return _dates_close(form.get("created_at"), imap.get("created_at"), hours=48)


def _dates_close(a: str | None, b: str | None, *, hours: int = 48) -> bool:
    try:
        da = datetime.fromisoformat((a or "")[:19])
        db = datetime.fromisoformat((b or "")[:19])
        return abs((da - db).total_seconds()) <= hours * 3600
    except Exception:  # noqa: BLE001
        return True
