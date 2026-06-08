"""Paiement Stripe et tokens de téléchargement du guide PDF."""

from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import config
from admin.kv_store import get_json, set_json
from admin.mail_service import is_newsletter_smtp_configured, send_email

logger = logging.getLogger(__name__)

KV_PURCHASES = "pdf_purchases"
TOKEN_TTL_DAYS = 30
PDF_PRICE_CENTS = int(os.environ.get("PDF_GUIDE_PRICE_CENTS", "990"))


def _stripe_enabled() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY", "").strip())


def _get_stripe():
    import stripe

    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    return stripe


def _purchases() -> list[dict]:
    return get_json(KV_PURCHASES, [], file_name="pdf_purchases.json") or []


def _save_purchases(items: list[dict]):
    set_json(KV_PURCHASES, items, file_name="pdf_purchases.json")


def is_payment_configured() -> bool:
    return _stripe_enabled()


def create_checkout_session(*, lang: str, success_url: str, cancel_url: str) -> dict:
    if not _stripe_enabled():
        return {"ok": False, "error": "stripe_not_configured"}

    lang = "en" if lang == "en" else "fr"
    product_name = (
        "Vietnam PDF Guide — 2026 Edition"
        if lang == "en"
        else "Guide Vietnam PDF — Édition 2026"
    )
    product_desc = (
        "3 day-by-day itineraries (7, 10 & 14 days), checklists, budgets and city addresses."
        if lang == "en"
        else "3 itinéraires jour par jour (7, 10 & 14 j), checklists, budgets et adresses par ville."
    )

    stripe = _get_stripe()
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "eur",
                "unit_amount": PDF_PRICE_CENTS,
                "product_data": {
                    "name": product_name,
                    "description": product_desc,
                },
            },
            "quantity": 1,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"lang": lang, "product": "pdf_guide"},
        locale="en" if lang == "en" else "fr",
    )
    return {"ok": True, "session_id": session.id, "url": session.url}


def _issue_token(*, session_id: str, email: str, lang: str, amount_cents: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS)
    record = {
        "id": str(uuid.uuid4()),
        "token": token,
        "session_id": session_id,
        "email": email,
        "lang": lang,
        "amount_cents": amount_cents,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires.isoformat(),
        "downloads": 0,
    }
    items = _purchases()
    items = [p for p in items if p.get("session_id") != session_id]
    items.insert(0, record)
    _save_purchases(items[:500])
    return token


def _send_download_email(*, email: str, lang: str, download_url: str):
    if not email or not is_newsletter_smtp_configured():
        return
    if lang == "en":
        subject = "Your Inside Vietnam Travel PDF guide"
        body = (
            f"Thank you for your purchase!\n\n"
            f"Download your guide (valid 30 days):\n{download_url}\n\n"
            f"Inside Vietnam Travel — insidevietnamtravel.fr"
        )
    else:
        subject = "Votre guide PDF Inside Vietnam Travel"
        body = (
            f"Merci pour votre achat !\n\n"
            f"Téléchargez votre guide (lien valable 30 jours) :\n{download_url}\n\n"
            f"Inside Vietnam Travel — insidevietnamtravel.fr"
        )
    try:
        send_email(
            profile="newsletter",
            to_addrs=[email],
            subject=subject,
            html_body=f"<pre>{body}</pre>",
            plain_body=body,
        )
    except Exception:
        logger.exception("PDF download email failed for %s", email)


def fulfill_checkout_session(session_id: str) -> dict:
    if not _stripe_enabled():
        return {"ok": False, "error": "stripe_not_configured"}

    stripe = _get_stripe()
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        logger.exception("Stripe session retrieve failed")
        return {"ok": False, "error": str(exc)}

    if session.payment_status != "paid":
        return {"ok": False, "error": "not_paid"}

    existing = next((p for p in _purchases() if p.get("session_id") == session_id), None)
    if existing:
        return {
            "ok": True,
            "token": existing["token"],
            "email": existing.get("email", ""),
            "lang": existing.get("lang", "fr"),
            "already": True,
        }

    email = (session.customer_details.email if session.customer_details else "") or ""
    lang = (session.metadata or {}).get("lang", "fr")
    amount = int(session.amount_total or PDF_PRICE_CENTS)
    token = _issue_token(session_id=session_id, email=email, lang=lang, amount_cents=amount)
    return {"ok": True, "token": token, "email": email, "lang": lang, "already": False}


def get_valid_token(token: str) -> dict | None:
    if not token:
        return None
    now = datetime.now(timezone.utc)
    for record in _purchases():
        if record.get("token") != token:
            continue
        expires_raw = record.get("expires_at", "")
        try:
            expires = datetime.fromisoformat(expires_raw)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
        if now > expires:
            return None
        return record
    return None


def record_download(token: str):
    items = _purchases()
    for record in items:
        if record.get("token") == token:
            record["downloads"] = int(record.get("downloads", 0)) + 1
            record["last_download_at"] = datetime.now(timezone.utc).isoformat()
            break
    _save_purchases(items)


def build_download_url(token: str, lang: str) -> str:
    from i18n_utils import lang_url

    base = config.pdf_flow_base_url()
    path = lang_url("pdf_download", lang, token=token)
    return base + path


def notify_purchase_fulfilled(*, token: str, email: str, lang: str):
    url = build_download_url(token, lang)
    _send_download_email(email=email, lang=lang, download_url=url)
