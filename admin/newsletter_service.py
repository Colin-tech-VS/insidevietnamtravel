"""Newsletter — abonnés et envoi d'emails."""

from __future__ import annotations

import os
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

NEWSLETTER_FILE = Path(__file__).parent.parent / "data" / "newsletter_subscribers.txt"
SITE_NAME = "Inside Vietnam Travel"
import config

SITE_URL = config.SITE_URL


def is_smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def get_newsletter_subscribers() -> list[dict]:
    if not NEWSLETTER_FILE.exists():
        return []
    rows = []
    seen: set[str] = set()
    for line in NEWSLETTER_FILE.read_text(encoding="utf-8").strip().splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        subscribed_at, email = line.split(",", 1)
        email = email.strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        rows.append({
            "email": email,
            "subscribed_at": subscribed_at.strip(),
        })
    rows.sort(key=lambda r: r.get("subscribed_at", ""), reverse=True)
    return rows


def add_newsletter_subscriber(email: str) -> bool:
    email = email.strip().lower()
    if not email or "@" not in email:
        return False
    existing = {s["email"] for s in get_newsletter_subscribers()}
    if email in existing:
        return False
    NEWSLETTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NEWSLETTER_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()},{email}\n")
    return True


def remove_newsletter_subscriber(email: str) -> bool:
    email = email.strip().lower()
    subs = get_newsletter_subscribers()
    kept = [s for s in subs if s["email"] != email]
    if len(kept) == len(subs):
        return False
    NEWSLETTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NEWSLETTER_FILE, "w", encoding="utf-8") as f:
        for s in kept:
            f.write(f"{s['subscribed_at']},{s['email']}\n")
    return True


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def build_manual_newsletter(form) -> dict:
    subject = (form.get("subject") or "").strip()
    body_html = (form.get("body_html") or "").strip()
    preheader = (form.get("preheader") or "").strip()

    if not subject:
        raise ValueError("L'objet de l'email est obligatoire.")
    if not body_html or not _strip_html(body_html):
        raise ValueError("Le contenu de l'email est obligatoire.")

    return {
        "subject": subject[:120],
        "preheader": preheader[:160],
        "body_html": body_html,
        "manual": True,
        "ai_generated": False,
    }


def wrap_email_html(body_html: str, preheader: str = "") -> str:
    preheader_html = ""
    if preheader:
        preheader_html = (
            f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">'
            f"{preheader}</div>"
        )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{SITE_NAME}</title>
</head>
<body style="margin:0;padding:0;background:#f5f3ef;font-family:Georgia,'Times New Roman',serif;color:#2a2825;">
  {preheader_html}
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f3ef;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border:1px solid #e8e4dc;border-radius:8px;overflow:hidden;">
          <tr>
            <td style="background:#1b4d4a;padding:20px 28px;">
              <p style="margin:0;font-family:Arial,sans-serif;font-size:13px;letter-spacing:0.08em;text-transform:uppercase;color:#d4a853;">Newsletter</p>
              <p style="margin:6px 0 0;font-family:Georgia,serif;font-size:22px;color:#ffffff;">{SITE_NAME}</p>
            </td>
          </tr>
          <tr>
            <td style="padding:28px;font-size:16px;line-height:1.6;color:#2a2825;">
              {body_html}
            </td>
          </tr>
          <tr>
            <td style="padding:18px 28px;background:#faf9f7;border-top:1px solid #e8e4dc;font-family:Arial,sans-serif;font-size:12px;line-height:1.5;color:#7a7772;">
              <p style="margin:0 0 8px;">Vous recevez cet email car vous êtes inscrit à la newsletter {SITE_NAME}.</p>
              <p style="margin:0;">
                <a href="{SITE_URL}" style="color:#1b4d4a;">Visiter le site</a>
                · Répondez à cet email pour vous désinscrire.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_newsletter_email(
    recipients: list[str],
    subject: str,
    body_html: str,
    *,
    preheader: str = "",
) -> dict:
    recipients = [e.strip().lower() for e in recipients if e and "@" in e]
    if not recipients:
        raise ValueError("Aucun destinataire valide.")
    if not subject.strip():
        raise ValueError("Objet email manquant.")
    if not is_smtp_configured():
        raise ValueError(
            "SMTP non configuré. Ajoutez SMTP_HOST, SMTP_PORT, SMTP_USER, "
            "SMTP_PASSWORD et SMTP_FROM dans .env"
        )

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    from_addr = os.environ["SMTP_FROM"]
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    full_html = wrap_email_html(body_html, preheader)
    plain = _strip_html(body_html)

    sent = 0
    failed: list[str] = []

    with smtplib.SMTP(host, port, timeout=30) as server:
        if use_tls:
            server.starttls()
        if user and password:
            server.login(user, password)

        for addr in recipients:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = addr
            msg.attach(MIMEText(plain, "plain", "utf-8"))
            msg.attach(MIMEText(full_html, "html", "utf-8"))
            try:
                server.sendmail(from_addr, [addr], msg.as_string())
                sent += 1
            except Exception:
                failed.append(addr)

    return {"sent": sent, "failed": failed, "total": len(recipients)}
