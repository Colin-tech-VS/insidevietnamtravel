"""Lecture IMAP — boîte contact@ (même serveur que SMTP LWS)."""

from __future__ import annotations

import email
import imaplib
import logging
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime

from admin.mail_service import _strip_tags, is_contact_smtp_configured

logger = logging.getLogger(__name__)

IMAP_PORT_SSL = 993
CONTACT_SUBJECT_PREFIX = "[Contact]"
IMAP_TIMEOUT = max(2, int(os.environ.get("IMAP_TIMEOUT", "8")))


def _imap_config() -> dict:
    host = os.environ.get("IMAP_HOST") or os.environ.get("SMTP_HOST", "mail.insidevietnamtravel.fr")
    port = int(os.environ.get("IMAP_PORT", str(IMAP_PORT_SSL)))
    user = os.environ.get("CONTACT_IMAP_USER") or os.environ.get(
        "CONTACT_SMTP_USER", os.environ.get("LEGAL_CONTACT_EMAIL", "contact@insidevietnamtravel.fr")
    )
    password = os.environ.get("CONTACT_IMAP_PASSWORD") or os.environ.get("CONTACT_SMTP_PASSWORD", "")
    folder = os.environ.get("CONTACT_IMAP_FOLDER", "INBOX")
    use_ssl = os.environ.get("IMAP_USE_SSL", "true").lower() in ("1", "true", "yes")
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "folder": folder,
        "use_ssl": use_ssl,
    }


def is_imap_configured() -> bool:
    if not is_contact_smtp_configured():
        return False
    cfg = _imap_config()
    return bool(cfg["host"] and cfg["user"] and cfg["password"])


def imap_status() -> dict:
    cfg = _imap_config()
    return {
        "configured": is_imap_configured(),
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "folder": cfg["folder"],
    }


def verify_imap() -> dict:
    cfg = _imap_config()
    if not is_imap_configured():
        return {"ok": False, "error": "IMAP contact non configuré (identifiants manquants)."}
    try:
        with _open_imap(cfg) as mail:
            typ, _ = mail.select(cfg["folder"], readonly=True)
            if typ != "OK":
                return {"ok": False, "error": f"Impossible d'ouvrir le dossier {cfg['folder']}."}
        return {"ok": True, "host": cfg["host"], "user": cfg["user"], "folder": cfg["folder"]}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Échec verify_imap")
        return {"ok": False, "error": str(exc)[:300]}


def fetch_inbox_messages(*, limit: int = 80) -> list[dict]:
    """Derniers messages IMAP du dossier contact (ordre récent → ancien)."""
    cfg = _imap_config()
    if not is_imap_configured():
        return []

    limit = max(1, min(limit, 200))
    out: list[dict] = []

    with _open_imap(cfg) as mail:
        typ, _ = mail.select(cfg["folder"], readonly=True)
        if typ != "OK":
            raise RuntimeError(f"Dossier IMAP introuvable : {cfg['folder']}")

        typ, data = mail.uid("search", None, "ALL")
        if typ != "OK" or not data or not data[0]:
            return []

        uids = data[0].split()
        uids = uids[-limit:]
        uids.reverse()

        for uid in uids:
            uid_s = uid.decode() if isinstance(uid, bytes) else str(uid)
            typ, msg_data = mail.uid("fetch", uid, "(RFC822 FLAGS)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            flags = msg_data[0][0].decode() if isinstance(msg_data[0][0], bytes) else str(msg_data[0][0])
            seen = "\\Seen" in flags
            parsed = _parse_raw_message(raw, uid=uid_s, read=seen)
            if parsed:
                out.append(parsed)

    return out


def mark_imap_read(uid: str) -> bool:
    cfg = _imap_config()
    if not uid or not is_imap_configured():
        return False
    try:
        with _open_imap(cfg) as mail:
            mail.select(cfg["folder"])
            typ, _ = mail.uid("STORE", uid, "+FLAGS", "\\Seen")
            return typ == "OK"
    except Exception:  # noqa: BLE001
        logger.exception("mark_imap_read uid=%s", uid)
        return False


def delete_imap_message(uid: str) -> bool:
    cfg = _imap_config()
    if not uid or not is_imap_configured():
        return False
    try:
        with _open_imap(cfg) as mail:
            mail.select(cfg["folder"])
            typ, _ = mail.uid("STORE", uid, "+FLAGS", "\\Deleted")
            if typ != "OK":
                return False
            mail.expunge()
            return True
    except Exception:  # noqa: BLE001
        logger.exception("delete_imap_message uid=%s", uid)
        return False


@contextmanager
def _open_imap(cfg: dict):
    if cfg["use_ssl"]:
        mail = imaplib.IMAP4_SSL(cfg["host"], cfg["port"], timeout=IMAP_TIMEOUT)
    else:
        mail = imaplib.IMAP4(cfg["host"], cfg["port"], timeout=IMAP_TIMEOUT)
    try:
        mail.login(cfg["user"], cfg["password"])
        yield mail
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    chunks: list[str] = []
    for part, charset in parts:
        if isinstance(part, bytes):
            chunks.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            chunks.append(part)
    return " ".join(chunks).strip()


def _message_datetime(msg: Message) -> str:
    raw = msg.get("Date")
    if not raw:
        return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.isoformat()
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _extract_addresses(msg: Message) -> tuple[str, str, str]:
    """from_email, from_name, reply_to_email."""
    from_raw = _decode_header_value(msg.get("From"))
    reply_raw = _decode_header_value(msg.get("Reply-To")) or from_raw

    def _split(addr: str) -> tuple[str, str]:
        m = re.match(r"^(?:\"?([^\"<]+)\"?\s*)?<([^>]+@[^>]+)>$", addr.strip())
        if m:
            name = (m.group(1) or "").strip().strip('"')
            return name, m.group(2).strip().lower()
        if "@" in addr:
            return "", addr.strip().lower()
        return addr.strip(), ""

    from_name, from_email = _split(from_raw)
    _, reply_email = _split(reply_raw)
    return from_email, from_name, reply_email or from_email


def _extract_body_parts(msg: Message) -> tuple[str, str]:
    """Retourne (texte brut, html) du corps du message."""
    plain = ""
    html = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition", "").startswith("attachment"):
                continue
            ctype = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if ctype == "text/plain" and not plain:
                plain = text
            elif ctype == "text/html" and not html:
                html = text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                html = text
            else:
                plain = text

    plain = re.sub(r"\n{3,}", "\n\n", plain.strip())
    return plain[:8000], html[:120000]


def _extract_body(msg: Message) -> str:
    plain, html = _extract_body_parts(msg)
    return plain or _strip_tags(html)


def _parse_contact_notification(body: str, html_hint: str = "") -> tuple[str, str]:
    """Extrait nom + message depuis la notification formulaire contact."""
    src = body or _strip_tags(html_hint)
    name = ""
    m = re.search(r"(?:Nom|Name)\s*:\s*(.+)", src, re.I)
    if m:
        name = m.group(1).strip()
    message = src
    m_msg = re.search(
        r"(?:Sujet|Subject)\s*:.+?\n\n(.+)",
        src,
        re.I | re.S,
    )
    if m_msg:
        message = m_msg.group(1).strip()
    return name, message


def _parse_raw_message(raw: bytes, *, uid: str, read: bool) -> dict | None:
    try:
        msg = email.message_from_bytes(raw)
    except Exception:  # noqa: BLE001
        return None

    subject = _decode_header_value(msg.get("Subject")) or "(sans objet)"
    from_email, from_name, reply_email = _extract_addresses(msg)
    message_id = (msg.get("Message-ID") or "").strip()
    in_reply_to = (msg.get("In-Reply-To") or "").strip()
    references = (msg.get("References") or "").strip()
    plain_body, html_body = _extract_body_parts(msg)
    body = plain_body or _strip_tags(html_body)

    display_email = reply_email or from_email
    display_name = from_name
    message_html = html_body.strip()

    clean_subject = subject
    if subject.startswith(CONTACT_SUBJECT_PREFIX):
        clean_subject = subject[len(CONTACT_SUBJECT_PREFIX) :].strip()
        parsed_name, parsed_body = _parse_contact_notification(body, html_body)
        if parsed_name:
            display_name = parsed_name
        if parsed_body:
            body = parsed_body
            if html_body and not message_html:
                message_html = html_body
        display_email = reply_email or from_email

    if not display_email:
        return None

    return {
        "id": f"imap:{uid}",
        "uid": uid,
        "channel": "imap",
        "name": display_name or display_email.split("@")[0],
        "email": display_email,
        "subject": clean_subject[:200],
        "message": body or "(message vide)",
        "message_html": message_html,
        "created_at": _message_datetime(msg),
        "read": read,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "raw_subject": subject,
    }
