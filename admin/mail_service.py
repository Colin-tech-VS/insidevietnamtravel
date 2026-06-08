"""Envoi SMTP partagé — newsletter (noreply) et contact."""

from __future__ import annotations

import os
import smtplib
from contextlib import contextmanager
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterator, Literal

MailProfile = Literal["newsletter", "contact"]

SMTP_HOST = "mail.insidevietnamtravel.fr"
SMTP_PORT_SSL = 465
SMTP_PORT_TLS = 587


def _profile_config(profile: MailProfile) -> dict:
    if profile == "contact":
        user = os.environ.get("CONTACT_SMTP_USER") or os.environ.get(
            "LEGAL_CONTACT_EMAIL", "contact@insidevietnamtravel.fr"
        )
        password = os.environ.get("CONTACT_SMTP_PASSWORD") or os.environ.get("SMTP_PASSWORD", "")
        from_addr = os.environ.get("CONTACT_SMTP_FROM") or user
        from_name = os.environ.get("CONTACT_SMTP_FROM_NAME", "Inside Vietnam Travel Contact")
    else:
        user = os.environ.get("SMTP_USER", "")
        password = os.environ.get("SMTP_PASSWORD", "")
        from_addr = os.environ.get("SMTP_FROM", user)
        from_name = os.environ.get("SMTP_FROM_NAME", "Inside Vietnam Travel")
    return {
        "host": os.environ.get("SMTP_HOST", SMTP_HOST),
        "port": int(os.environ.get("SMTP_PORT", str(SMTP_PORT_SSL))),
        "user": user,
        "password": password,
        "from_addr": from_addr,
        "from_name": from_name,
        "use_ssl": os.environ.get("SMTP_USE_SSL", "true").lower() in ("1", "true", "yes"),
        "use_tls": os.environ.get("SMTP_USE_TLS", "false").lower() in ("1", "true", "yes"),
    }


def is_newsletter_smtp_configured() -> bool:
    cfg = _profile_config("newsletter")
    return bool(cfg["host"] and cfg["from_addr"] and cfg["user"] and cfg["password"])


def is_contact_smtp_configured() -> bool:
    cfg = _profile_config("contact")
    return bool(cfg["host"] and cfg["from_addr"] and cfg["user"] and cfg["password"])


def send_email(
    *,
    profile: MailProfile,
    to_addrs: list[str],
    subject: str,
    html_body: str,
    plain_body: str | None = None,
    reply_to: str | None = None,
    extra_headers: dict | None = None,
) -> dict:
    cfg = _profile_config(profile)
    if not cfg["host"] or not cfg["from_addr"]:
        raise ValueError("SMTP non configuré (SMTP_HOST / SMTP_FROM).")
    if not cfg["user"] or not cfg["password"]:
        raise ValueError(f"Identifiants SMTP manquants pour le profil « {profile} ».")

    recipients = [a.strip() for a in to_addrs if a and "@" in a]
    if not recipients:
        raise ValueError("Aucun destinataire valide.")

    plain = plain_body or _strip_tags(html_body)
    sent = 0
    failed: list[str] = []

    with _open_smtp(cfg) as server:
        for addr in recipients:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{cfg['from_name']} <{cfg['from_addr']}>"
            msg["To"] = addr
            if reply_to:
                msg["Reply-To"] = reply_to
            if extra_headers:
                for key, val in extra_headers.items():
                    msg[key] = val
            msg.attach(MIMEText(plain, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            try:
                server.sendmail(cfg["from_addr"], [addr], msg.as_string())
                sent += 1
            except Exception:
                failed.append(addr)

    return {"sent": sent, "failed": failed, "total": len(recipients)}


@contextmanager
def _open_smtp(cfg: dict) -> Iterator[smtplib.SMTP]:
    host, port = cfg["host"], cfg["port"]
    if cfg["use_ssl"] or port == SMTP_PORT_SSL:
        server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        if cfg["use_tls"]:
            server.starttls()
    try:
        if cfg["user"] and cfg["password"]:
            server.login(cfg["user"], cfg["password"])
        yield server
    finally:
        try:
            server.quit()
        except Exception:
            pass


def _strip_tags(html: str) -> str:
    import re
    text = re.sub(r"<br\s*/?>", "\n", html or "", flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
