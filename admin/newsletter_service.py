"""Newsletter — abonnés, template email et envoi SMTP."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

import config
from admin.database import get_connection, is_postgres
from admin.newsletter_tokens import unsubscribe_url

NEWSLETTER_FILE = Path(__file__).parent.parent / "data" / "newsletter_subscribers.txt"
SITE_NAME = "Inside Vietnam Travel"
SITE_URL = config.SITE_URL
SITE_CANONICAL_URL = config.SITE_CANONICAL_URL
SITE_PUBLIC_DOMAIN = config.SITE_PUBLIC_DOMAIN
PRIVACY_URL = f"{SITE_CANONICAL_URL}/politique-confidentialite"


from admin.mail_service import MailProfile, is_newsletter_smtp_configured, is_contact_smtp_configured, send_email


def is_smtp_configured() -> bool:
    return is_newsletter_smtp_configured()


def _read_from_file() -> list[dict]:
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
        rows.append({"email": email, "subscribed_at": subscribed_at.strip()})
    rows.sort(key=lambda r: r.get("subscribed_at", ""), reverse=True)
    return rows


def get_newsletter_subscribers() -> list[dict]:
    if is_postgres():
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT email, subscribed_at FROM newsletter_subscribers ORDER BY subscribed_at DESC"
            )
            rows = cur.fetchall()
        return [
            {
                "email": r["email"] if isinstance(r, dict) else r[0],
                "subscribed_at": str(r["subscribed_at"] if isinstance(r, dict) else r[1]),
            }
            for r in rows
        ]
    return _read_from_file()


def add_newsletter_subscriber(email: str) -> bool:
    email = email.strip().lower()
    if not email or "@" not in email:
        return False
    if is_postgres():
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO newsletter_subscribers (email, subscribed_at)
                VALUES (%s, NOW()) ON CONFLICT (email) DO NOTHING
                """,
                (email,),
            )
            return cur.rowcount > 0
    if NEWSLETTER_FILE.exists():
        suffix = f",{email}"
        for line in NEWSLETTER_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip().endswith(suffix):
                return False
    NEWSLETTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NEWSLETTER_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()},{email}\n")
    return True


def remove_newsletter_subscriber(email: str) -> bool:
    email = email.strip().lower()
    if is_postgres():
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM newsletter_subscribers WHERE email = %s", (email,))
            return cur.rowcount > 0
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


def normalize_email_domains(text: str) -> str:
    """Force insidevietnamtravel.fr — jamais .com dans les emails."""
    if not text:
        return text
    canonical = SITE_CANONICAL_URL
    domain = SITE_PUBLIC_DOMAIN
    replacements = (
        ("https://www.insidevietnamtravel.com", canonical),
        ("http://www.insidevietnamtravel.com", canonical),
        ("https://insidevietnamtravel.com", canonical),
        ("http://insidevietnamtravel.com", canonical),
        ("www.insidevietnamtravel.com", f"www.{domain}"),
        ("insidevietnamtravel.com", domain),
    )
    for wrong, right in replacements:
        text = text.replace(wrong, right)
    return text


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


def wrap_email_html(
    body_html: str,
    preheader: str = "",
    *,
    recipient_email: str | None = None,
    email_type: str = "newsletter",
) -> str:
    """Template email responsive — charte Inside Vietnam Travel."""
    preheader_html = ""
    if preheader:
        preheader_html = (
            '<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;font-size:1px;line-height:1px;">'
            f"{preheader}</div>"
        )

    is_partnership = email_type == "partenariat"
    body_html = normalize_email_domains(body_html)
    unsub_block = ""
    if recipient_email and not is_partnership:
        unsub_link = unsubscribe_url(recipient_email)
        unsub_block = f"""
              <p style="margin:12px 0 0;">
                <a href="{unsub_link}" style="color:#7a7772;text-decoration:underline;">Se désinscrire de la newsletter</a>
              </p>"""

    if is_partnership:
        footer_intro = (
            "<p style=\"margin:0 0 8px;\">"
            "Inside Vietnam Travel — guide francophone indépendant du voyage au Vietnam."
            "</p>"
        )
        cta_html = ""
    else:
        footer_intro = (
            "<p style=\"margin:0 0 8px;\">"
            "Vous recevez cet email car vous êtes inscrit(e) à la newsletter "
            "<strong style=\"color:#1b4d4a;\">Inside Vietnam Travel</strong>."
            "</p>"
        )
        cta_html = """
          <!-- CTA -->
          <tr>
            <td style="padding:0 32px 28px;text-align:center;">
              <a href="{site_url}" style="display:inline-block;background:#1b4d4a;color:#ffffff;font-family:'Segoe UI',Arial,sans-serif;font-size:15px;font-weight:600;text-decoration:none;padding:14px 28px;border-radius:8px;">Explorer le site</a>
            </td>
          </tr>""".format(site_url=SITE_CANONICAL_URL)

    return f"""<!DOCTYPE html>
<html lang="fr" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>{SITE_NAME}</title>
  <!--[if mso]><style>table,td{{font-family:Arial,sans-serif!important}}</style><![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#faf7f2;-webkit-text-size-adjust:100%;">
  {preheader_html}
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#faf7f2;padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e8e4dc;">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1b4d4a 0%,#0f3330 100%);padding:28px 32px;text-align:left;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <p style="margin:0 0 4px;font-family:'Segoe UI',Arial,sans-serif;font-size:11px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:#d4b86a;">Inside Vietnam Travel</p>
                    <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:26px;font-weight:600;color:#ffffff;line-height:1.2;">Votre guide voyage<br><span style="color:#d4b86a;font-style:italic;">au Vietnam</span></p>
                  </td>
                  <td width="48" align="right" valign="top">
                    <div style="width:40px;height:40px;border:1.5px solid rgba(255,255,255,0.5);border-radius:50%;text-align:center;line-height:40px;color:#ffffff;font-size:18px;">&#9679;</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px 32px 28px;font-family:Georgia,'Times New Roman',serif;font-size:17px;line-height:1.65;color:#1a1a18;">
              {body_html}
            </td>
          </tr>
          {cta_html}
          <!-- Footer -->
          <tr>
            <td style="padding:24px 32px;background:#f0ebe3;border-top:1px solid #e8e4dc;font-family:'Segoe UI',Arial,sans-serif;font-size:12px;line-height:1.6;color:#7a7772;">
              {footer_intro}
              <p style="margin:0;">
                <a href="{SITE_CANONICAL_URL}" style="color:#1b4d4a;text-decoration:none;font-weight:600;">{SITE_PUBLIC_DOMAIN}</a>
                &nbsp;&middot;&nbsp;
                <a href="{PRIVACY_URL}" style="color:#1b4d4a;text-decoration:none;">Confidentialité</a>
              </p>
              {unsub_block}
            </td>
          </tr>
        </table>
        <p style="margin:20px 0 0;font-family:'Segoe UI',Arial,sans-serif;font-size:11px;color:#7a7772;">
          &copy; {datetime.now().year} Inside Vietnam Travel &mdash; Guide indépendant, pas une agence.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""


def render_newsletter_preview(draft: dict, *, sample_email: str = "lecteur@exemple.fr") -> str:
    return wrap_email_html(
        draft.get("body_html", ""),
        draft.get("preheader", ""),
        recipient_email=sample_email,
        email_type=draft.get("email_type") or "newsletter",
    )


def send_newsletter_email(
    recipients: list[str],
    subject: str,
    body_html: str,
    *,
    preheader: str = "",
    partner_id: str = "",
    recipient_name: str = "",
    email_type: str = "newsletter",
    track: bool = True,
) -> dict:
    from admin.email_tracking_service import (
        create_email_send,
        delete_email_send,
        inject_email_utm,
        inject_tracking,
    )

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

    sent = 0
    failed: list[str] = []
    send_ids: list[int] = []
    all_errors: dict[str, str] = {}
    last_from = ""
    mail_profile: MailProfile = "contact" if email_type == "partenariat" else "newsletter"
    reply_to = ""
    if email_type == "partenariat":
        if not is_contact_smtp_configured():
            mail_profile = "newsletter"
        reply_to = (
            os.environ.get("CONTACT_SMTP_FROM")
            or os.environ.get("LEGAL_CONTACT_EMAIL", "contact@insidevietnamtravel.fr")
        )

    for addr in recipients:
        send_rec = None
        if track:
            send_rec = create_email_send(
                recipient_email=addr,
                recipient_name=recipient_name,
                partner_id=partner_id,
                subject=subject,
                email_type=email_type,
            )
        full_html = wrap_email_html(
            normalize_email_domains(body_html), preheader, recipient_email=addr, email_type=email_type,
        )
        if send_rec:
            full_html = inject_tracking(
                full_html,
                send_rec["send_token"],
                email_type=email_type,
                subject=subject,
                partner_id=partner_id,
            )
        else:
            full_html = inject_email_utm(
                full_html,
                email_type=email_type,
                subject=subject,
                partner_id=partner_id,
            )
        plain = _strip_html(body_html)
        if email_type != "partenariat":
            plain += f"\n\nSe désinscrire : {unsubscribe_url(addr)}"
            extra = {"List-Unsubscribe": f"<{unsubscribe_url(addr)}>"}
        else:
            extra = {}
        result = send_email(
            profile=mail_profile,
            to_addrs=[addr],
            subject=subject,
            html_body=full_html,
            plain_body=plain,
            extra_headers=extra,
            reply_to=reply_to or None,
        )
        if result["sent"]:
            sent += 1
            last_from = result.get("from_addr") or last_from
            if send_rec:
                send_ids.append(send_rec["id"])
            if email_type == "partenariat":
                from admin.partners_service import mark_partner_emailed

                mark_partner_emailed(partner_id=partner_id, email=addr)
        else:
            failed.append(addr)
            all_errors.update(result.get("errors") or {})
            if send_rec:
                delete_email_send(send_rec["id"])

    return {
        "sent": sent,
        "failed": failed,
        "total": len(recipients),
        "send_ids": send_ids,
        "errors": all_errors,
        "from_addr": last_from,
    }
