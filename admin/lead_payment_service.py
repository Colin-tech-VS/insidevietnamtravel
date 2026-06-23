"""Vente d'un lead agence : paiement Stripe (pay-to-unlock) + livraison email brandée.

Flux « payer pour débloquer » :
1. Depuis /admin/leads, l'admin envoie un lien de paiement à un partenaire (agence
   choisie dans la liste, ou email saisi à la main) — prix par défaut 15 €, modifiable.
2. Le partenaire reçoit un email brandé Inside Vietnam Travel avec un aperçu du profil
   (SANS les coordonnées) et un bouton « Débloquer ce lead — N € ».
3. Il paie via Stripe Checkout. À son retour sur la page de succès, le lead COMPLET
   (email du voyageur + profil) lui est envoyé par email, le lead passe « vendu » et
   le montant est enregistré en Revenus.

Réutilise le même pattern Stripe que le guide PDF (validation au retour, pas de
webhook) et le wrapper email brandé `wrap_email_html` (type « partenariat », donc
sans pied de page newsletter).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from admin.kv_store import get_json, set_json
from admin.mail_service import is_newsletter_smtp_configured, send_email
from admin.newsletter_service import wrap_email_html

logger = logging.getLogger(__name__)

KV_DELIVERIES = "lead_deliveries"
LEAD_PRICE_CENTS = int(os.environ.get("LEAD_PRICE_CENTS", "1500"))


def _stripe_enabled() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY", "").strip())


def _get_stripe():
    import stripe

    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    return stripe


def is_payment_configured() -> bool:
    return _stripe_enabled()


def _deliveries() -> list[dict]:
    return get_json(KV_DELIVERIES, [], file_name="lead_deliveries.json") or []


def _save_deliveries(items: list[dict]) -> None:
    set_json(KV_DELIVERIES, items, file_name="lead_deliveries.json")


# ── Création du paiement ──────────────────────────────────────────────


def create_lead_checkout(
    *,
    lead: dict,
    recipient_email: str,
    price_cents: int | None,
    base_url: str,
    success_path: str,
    cancel_path: str,
) -> dict:
    """Crée une session Stripe Checkout pour débloquer un lead. Renvoie {ok, url, ...}."""
    if not _stripe_enabled():
        return {"ok": False, "error": "stripe_not_configured"}

    recipient_email = (recipient_email or "").strip().lower()
    if "@" not in recipient_email:
        return {"ok": False, "error": "invalid_email"}

    try:
        price_cents = int(price_cents) if price_cents else LEAD_PRICE_CENTS
    except (TypeError, ValueError):
        price_cents = LEAD_PRICE_CENTS
    if price_cents < 100:
        price_cents = LEAD_PRICE_CENTS

    lead_id = lead.get("id")
    success_url = base_url + success_path + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = base_url + cancel_path

    stripe = _get_stripe()
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            customer_email=recipient_email,
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "unit_amount": price_cents,
                    "product_data": {
                        "name": f"Lead voyage qualifié #{lead_id} — Inside Vietnam Travel",
                        "description": (
                            "Coordonnées + profil complet d'un voyageur ayant demandé "
                            "un itinéraire Vietnam personnalisé."
                        ),
                    },
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "product": "agency_lead",
                "lead_id": str(lead_id),
                "recipient_email": recipient_email,
            },
            locale="fr",
        )
    except Exception as exc:
        logger.exception("Stripe lead checkout create failed")
        return {"ok": False, "error": str(exc)}

    return {"ok": True, "url": session.url, "session_id": session.id, "price_cents": price_cents}


# ── Livraison après paiement ──────────────────────────────────────────


def fulfill_lead_checkout(session_id: str) -> dict:
    """Vérifie le paiement, livre le lead par email (une seule fois), marque vendu."""
    if not _stripe_enabled():
        return {"ok": False, "error": "stripe_not_configured"}

    stripe = _get_stripe()
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        logger.exception("Stripe lead session retrieve failed")
        return {"ok": False, "error": str(exc)}

    if session.payment_status != "paid":
        return {"ok": False, "error": "not_paid"}
    meta = session.metadata or {}
    if meta.get("product") != "agency_lead":
        return {"ok": False, "error": "wrong_product"}

    # Idempotence : ne pas re-livrer ni re-créditer si déjà traité.
    existing = next((d for d in _deliveries() if d.get("session_id") == session_id), None)
    if existing:
        return {
            "ok": True,
            "already": True,
            "recipient": existing.get("recipient_email", ""),
            "lead_id": existing.get("lead_id"),
        }

    from admin import leads_service

    lead_id = meta.get("lead_id")
    recipient_email = (meta.get("recipient_email") or "").strip().lower()
    if not recipient_email and session.customer_details:
        recipient_email = (session.customer_details.email or "").strip().lower()
    amount = int(session.amount_total or LEAD_PRICE_CENTS)

    lead = leads_service.get_lead(lead_id)
    if not lead:
        return {"ok": False, "error": "lead_not_found"}

    delivered = _send_lead_delivery(lead, recipient_email)

    price_eur = round(amount / 100, 2)
    leads_service.update_lead(
        lead_id, status="vendu", sold_price=price_eur, agency=recipient_email
    )
    try:
        from admin import db

        db.add_revenue("lead_agence", price_eur, note=f"Lead #{lead_id} → {recipient_email}")
    except Exception:
        logger.exception("add_revenue (lead) failed")

    items = _deliveries()
    items.insert(0, {
        "session_id": session_id,
        "lead_id": lead.get("id"),
        "recipient_email": recipient_email,
        "amount_cents": amount,
        "email_sent": delivered,
        "delivered_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_deliveries(items[:1000])

    return {
        "ok": True,
        "already": False,
        "recipient": recipient_email,
        "lead_id": lead.get("id"),
        "email_sent": delivered,
    }


# ── Emails brandés ────────────────────────────────────────────────────


def _profile_table(lead: dict, *, include_contact: bool) -> str:
    rows: list[tuple[str, str]] = []
    if include_contact:
        email = lead.get("email", "")
        rows.append(("Email du voyageur", f'<a href="mailto:{email}" style="color:#1b4d4a;">{email}</a>'))
    rows.append(("Type de groupe", lead.get("group_label") or "—"))
    if lead.get("persons"):
        rows.append(("Nombre de voyageurs", str(lead["persons"])))
    rows.append(("Style de voyage", lead.get("style_label") or "—"))
    rows.append(("Durée souhaitée", lead.get("duration_label") or "—"))
    if lead.get("cities"):
        rows.append(("Villes / régions", lead["cities"]))
    if lead.get("lang"):
        rows.append(("Langue du voyageur", str(lead["lang"]).upper()))
    rows.append(("Demande reçue le", lead.get("created_at") or "—"))

    cells = "".join(
        f'<tr>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #e8e4dc;color:#7a7772;'
        f'font-size:13px;white-space:nowrap;vertical-align:top;">{label}</td>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #e8e4dc;color:#1a1a18;'
        f'font-size:15px;font-weight:600;">{value}</td>'
        f'</tr>'
        for label, value in rows
    )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="margin:16px 0;border:1px solid #e8e4dc;border-radius:8px;'
        f'border-collapse:separate;overflow:hidden;">{cells}</table>'
    )


def send_payment_link(lead: dict, recipient_email: str, checkout_url: str, price_eur: float) -> bool:
    """Email brandé : aperçu du profil (sans coordonnées) + bouton de paiement."""
    if not recipient_email or "@" not in recipient_email or not is_newsletter_smtp_configured():
        return False

    price_label = str(int(price_eur)) if price_eur == int(price_eur) else f"{price_eur:.2f}"
    body = f"""
      <p style="margin:0 0 16px;">Bonjour,</p>
      <p style="margin:0 0 16px;">
        Un voyageur vient de demander un itinéraire <strong>Vietnam</strong> personnalisé
        via notre planificateur. Son profil correspond à votre activité — voici un aperçu :
      </p>
      {_profile_table(lead, include_contact=False)}
      <p style="margin:16px 0;">
        Débloquez ses <strong>coordonnées complètes</strong> pour le recontacter directement.
        Après paiement, le lead vous est envoyé immédiatement par email.
      </p>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0;">
        <tr><td style="border-radius:8px;background:#1b4d4a;">
          <a href="{checkout_url}" style="display:inline-block;padding:14px 30px;font-family:'Segoe UI',Arial,sans-serif;font-size:16px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;">
            Débloquer ce lead — {price_label} €
          </a>
        </td></tr>
      </table>
      <p style="margin:16px 0 0;font-size:14px;color:#7a7772;">
        Paiement sécurisé par Stripe. Lien personnel, à usage unique.
      </p>
    """
    html = wrap_email_html(
        body,
        preheader=f"Un lead voyage Vietnam qualifié à débloquer ({price_label} €).",
        email_type="partenariat",
    )
    try:
        send_email(
            profile="newsletter",
            to_addrs=[recipient_email],
            subject="Un lead voyage Vietnam qualifié pour vous",
            html_body=html,
        )
        return True
    except Exception:
        logger.exception("lead payment-link email failed for %s", recipient_email)
        return False


def _send_lead_delivery(lead: dict, recipient_email: str) -> bool:
    """Email brandé envoyé après paiement : le lead complet avec coordonnées."""
    if not recipient_email or "@" not in recipient_email or not is_newsletter_smtp_configured():
        return False

    body = f"""
      <p style="margin:0 0 16px;">Merci pour votre paiement — voici votre lead qualifié.</p>
      <p style="margin:0 0 16px;">
        Vous pouvez désormais recontacter ce voyageur directement par email pour lui
        proposer votre devis ou votre itinéraire.
      </p>
      {_profile_table(lead, include_contact=True)}
      <p style="margin:16px 0 0;font-size:14px;color:#7a7772;">
        Ce voyageur a consenti au partage de ses données avec un partenaire voyage.
        Merci de respecter le RGPD et de lui offrir une option de désinscription.
      </p>
    """
    html = wrap_email_html(
        body,
        preheader="Votre lead voyage Vietnam qualifié (coordonnées incluses).",
        email_type="partenariat",
    )
    try:
        send_email(
            profile="newsletter",
            to_addrs=[recipient_email],
            subject=f"Votre lead voyage Vietnam #{lead.get('id')} — coordonnées",
            html_body=html,
        )
        return True
    except Exception:
        logger.exception("lead delivery email failed for %s", recipient_email)
        return False
