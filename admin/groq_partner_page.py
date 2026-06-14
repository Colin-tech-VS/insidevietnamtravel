"""Génération et validation IA des pages partenaires."""

from __future__ import annotations

import json
import re

from admin import ai_client
from admin.partner_portal_service import PROFILE_TYPE_LABELS

SYSTEM_PROMPT = """Tu es éditeur SEO pour « Inside Vietnam Travel », guide voyage Vietnam en français.

Tu reçois le profil d'un partenaire (guide, influenceur, blogueur, agence, hôtel…) et son brouillon.
Tu dois :
1) Rédiger une page partenaire cohérente avec le site (ton chaleureux, expert, honnête).
2) Vérifier que le contenu respecte les règles éditoriales du site.

RÈGLES DESIGN & CONTENU (obligatoires pour valider) :
- Contenu 100% lié au Vietnam (voyage, tourisme, expérience locale).
- Pas de promesses mensongères, pas de chiffres d'audience inventés.
- Pas de contenu spam, adulte, crypto, MLM ou hors-sujet.
- HTML corps : uniquement <p>, <h2>, <ul>, <li>, <strong>, <a href="…"> (pas de h1).
- Ton professionnel mais humain, en français.
- SEO : meta_title 50-65 car., meta_description 140-160 car.
- La page doit compléter le site (pas dupliquer une destination existante mot pour mot).

JSON strict :
{
  "review": {
    "approved": true|false,
    "score": 0-100,
    "issues": ["…"],
    "summary": "1-2 phrases"
  },
  "page": {
    "title": "Nom affiché",
    "tagline": "Accroche courte",
    "overview_html": "<p>…</p>",
    "services_html": "<h2>…</h2><ul>…</ul>",
    "seo_title": "…",
    "seo_description": "…",
    "profile_highlights": ["point fort 1", "…"]
  }
}

approved=true seulement si score >= 72 et aucun problème bloquant (hors-sujet, spam, mensonge).
"""


def _ensure_html(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if "<p" in text.lower() or "<h2" in text.lower():
        return text
    parts = [f"<p>{p.strip()}</p>" for p in re.split(r"\n\s*\n", text) if p.strip()]
    return "".join(parts) if parts else f"<p>{text}</p>"


def _parse_response(raw: str) -> dict:
    data = ai_client.parse_json(raw)
    review = data.get("review") or {}
    page = data.get("page") or {}
    if "approved" not in review:
        raise ValueError("Réponse IA incomplète (review)")
    if not page.get("title") or not page.get("overview_html"):
        raise ValueError("Réponse IA incomplète (page)")
    page["overview_html"] = _ensure_html(str(page.get("overview_html", "")))
    page["services_html"] = _ensure_html(str(page.get("services_html", "")))
    review["approved"] = bool(review.get("approved"))
    try:
        review["score"] = int(review.get("score", 0))
    except (TypeError, ValueError):
        review["score"] = 0
    review["issues"] = [str(i) for i in (review.get("issues") or [])][:8]
    review["summary"] = str(review.get("summary") or "").strip()[:500]
    return {"review": review, "page": page}


def generate_and_review_partner_page(account: dict, page: dict, *, progress=None) -> dict:
    ai_client.require_api_key()
    report = progress or (lambda *_: None)
    report("Analyse du profil partenaire…")

    extra = page.get("extra") or {}
    profile_label = PROFILE_TYPE_LABELS.get(account.get("profile_type"), account.get("profile_type"))
    services = account.get("services") or []
    social = account.get("social_links") or []

    user_msg = (
        f"Type de partenaire : {profile_label}\n"
        f"Nom / marque : {account.get('business_name') or account.get('first_name')} "
        f"{account.get('last_name', '')}\n"
        f"Ville : {extra.get('city') or account.get('city') or '—'}\n"
        f"Site : {account.get('website') or '—'}\n"
        f"Langues : {account.get('languages') or '—'}\n"
        f"Bio inscription : {account.get('bio') or '—'}\n"
        f"Services déclarés : {', '.join(services) if services else '—'}\n"
        f"Réseaux : {', '.join(social) if social else '—'}\n\n"
        f"BROUILLON PAGE :\n"
        f"- Accroche : {extra.get('pitch') or '—'}\n"
        f"- Points forts : {extra.get('highlights') or '—'}\n"
        f"- Offre détaillée : {extra.get('offer_details') or '—'}\n"
        f"- Note contact : {extra.get('contact_note') or '—'}\n\n"
        "Rédige la page ET décide si elle peut être publiée sur insidevietnamtravel.fr/partenaire/… "
        "Réponds en JSON strict."
    )

    report("Rédaction et contrôle qualité SEO…")
    response = ai_client.chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.35,
        max_tokens=4096,
        json_mode=True,
    )
    raw = response.choices[0].message.content or ""
    report("Finalisation…")
    return _parse_response(raw)
