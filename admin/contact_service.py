"""Formulaire de contact public — stockage + notification email."""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime

import config
from admin.kv_store import get_json, set_json
from admin.mail_service import is_contact_smtp_configured, send_email

KV_KEY = "contact_messages"


def get_contact_messages() -> list[dict]:
    return get_json(KV_KEY, [], file_name="contact_messages.json") or []


def _save_messages(messages: list[dict]):
    set_json(KV_KEY, messages, file_name="contact_messages.json")


def count_unread_messages() -> int:
    try:
        from admin.inbox_service import count_unread_inbox

        return count_unread_inbox()
    except Exception:  # noqa: BLE001
        return sum(1 for m in get_contact_messages() if not m.get("read"))


def mark_message_read(msg_id: str) -> bool:
    messages = get_contact_messages()
    found = False
    for m in messages:
        if m.get("id") == msg_id:
            m["read"] = True
            found = True
            break
    if found:
        _save_messages(messages)
    return found


def delete_message(msg_id: str) -> bool:
    messages = get_contact_messages()
    new_list = [m for m in messages if m.get("id") != msg_id]
    if len(new_list) == len(messages):
        return False
    _save_messages(new_list)
    return True


def submit_contact_form(
    *,
    name: str,
    email: str,
    subject: str,
    message: str,
    lang: str = "fr",
) -> dict:
    name = (name or "").strip()
    email = (email or "").strip().lower()
    subject = (subject or "").strip()
    message = (message or "").strip()

    if not name or len(name) < 2:
        raise ValueError("Nom invalide.")
    if not email or "@" not in email:
        raise ValueError("Email invalide.")
    if not subject or len(subject) < 3:
        raise ValueError("Sujet invalide.")
    if not message or len(message) < 10:
        raise ValueError("Message trop court.")

    entry = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "email": email,
        "subject": subject[:200],
        "message": message[:5000],
        "lang": lang,
        "created_at": datetime.utcnow().isoformat(),
        "read": False,
    }

    messages = get_contact_messages()
    messages.insert(0, entry)
    _save_messages(messages)

    email_sent = False
    if is_contact_smtp_configured():
        to = os.environ.get("CONTACT_NOTIFY_TO") or config.LEGAL_CONTACT_EMAIL
        site = config.SITE_NAME
        if lang == "en":
            mail_subject = f"[Contact] {subject}"
            html = f"""
<p><strong>New message from {site}</strong></p>
<ul>
  <li><strong>Name:</strong> {name}</li>
  <li><strong>Email:</strong> <a href="mailto:{email}">{email}</a></li>
  <li><strong>Subject:</strong> {subject}</li>
</ul>
<p>{message.replace(chr(10), '<br>')}</p>
"""
        else:
            mail_subject = f"[Contact] {subject}"
            html = f"""
<p><strong>Nouveau message depuis {site}</strong></p>
<ul>
  <li><strong>Nom :</strong> {name}</li>
  <li><strong>Email :</strong> <a href="mailto:{email}">{email}</a></li>
  <li><strong>Sujet :</strong> {subject}</li>
</ul>
<p>{message.replace(chr(10), '<br>')}</p>
"""
        result = send_email(
            profile="contact",
            to_addrs=[to],
            subject=mail_subject,
            html_body=html,
            plain_body=f"{name} <{email}>\n{subject}\n\n{message}",
            reply_to=email,
        )
        email_sent = result["sent"] > 0

    return {"saved": True, "email_sent": email_sent, "id": entry["id"]}


_REPLY_PREFIX_RE = re.compile(r"^(re|fw|fwd|aw|tr|ré|ref)\s*:", re.I)


def _reply_subject(subject: str) -> str:
    subject = (subject or "").strip()
    if _REPLY_PREFIX_RE.match(subject):
        return subject[:200]
    return f"Re: {subject}"[:200]


def send_inbox_reply(
    *,
    to_email: str,
    subject: str,
    body: str,
    message_id: str = "",
    in_reply_to: str = "",
    references: str = "",
) -> dict:
    """Envoie une réponse depuis la boîte contact@ vers le destinataire."""
    if not is_contact_smtp_configured():
        raise ValueError("SMTP contact non configuré.")

    to_email = (to_email or "").strip().lower()
    body = (body or "").strip()
    if not to_email or "@" not in to_email:
        raise ValueError("Destinataire invalide.")
    if len(body) < 2:
        raise ValueError("Message trop court.")

    mail_subject = _reply_subject(subject)
    site = config.SITE_NAME
    plain_body = body
    html_body = (
        f"<p>{body.replace(chr(10), '<br>')}</p>"
        f'<p style="margin-top:1.5em;font-size:0.85em;color:#666;">'
        f"— {site}</p>"
    )

    extra_headers: dict[str, str] = {}
    thread_id = (message_id or in_reply_to or "").strip()
    if thread_id:
        extra_headers["In-Reply-To"] = thread_id
        refs = (references or "").strip()
        extra_headers["References"] = f"{refs} {thread_id}".strip() if refs else thread_id

    result = send_email(
        profile="contact",
        to_addrs=[to_email],
        subject=mail_subject,
        html_body=html_body,
        plain_body=plain_body,
        extra_headers=extra_headers or None,
    )
    if result["sent"] < 1:
        err = ""
        if result.get("errors"):
            err = next(iter(result["errors"].values()), "")
        raise ValueError(err or "Échec de l'envoi SMTP.")

    return {
        "sent": True,
        "to": to_email,
        "subject": mail_subject,
        "from_addr": result.get("from_addr") or "",
    }
