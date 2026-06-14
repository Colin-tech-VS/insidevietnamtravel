"""Génération et validation IA des pages partenaires."""

from __future__ import annotations

import json
import re

from admin import ai_client
from admin.partner_portal_service import PROFILE_TYPE_LABELS

ALLOWED_FIX_FIELDS = frozenset({"pitch", "highlights", "offer_details", "city", "contact_note"})

FIELD_LABELS = {
    "pitch": "Accroche",
    "highlights": "Points forts",
    "offer_details": "Offre détaillée",
    "city": "Ville / région",
    "contact_note": "Contact",
}

SYSTEM_PROMPT = """Tu es éditeur SEO pour « Inside Vietnam Travel », guide voyage Vietnam en français.

Tu reçois le profil d'un partenaire (guide, influenceur, blogueur, agence, hôtel…) et son brouillon.
Tu dois :
1) Rédiger une page partenaire cohérente avec le site (ton chaleureux, expert, honnête).
2) Vérifier que le contenu respecte les règles éditoriales du site.
3) Si la page n'est PAS validée, proposer des corrections concrètes sur le BROUILLON (champs pitch, highlights, offer_details, city, contact_note).

RÈGLES DESIGN & CONTENU (obligatoires pour valider) :
- Contenu 100% lié au Vietnam (voyage, tourisme, expérience locale).
- Pas de promesses mensongères, pas de chiffres d'audience inventés.
- Pas de contenu spam, adulte, crypto, MLM ou hors-sujet.
- HTML corps : uniquement <p>, <h2>, <ul>, <li>, <strong>, <a href="…"> (pas de h1).
- Ton professionnel mais humain, en français.
- SEO : meta_title 50-65 car., meta_description 140-160 car.
- Adapte le SEO au type de partenaire (guide → tours privés, excursions ; influenceur → créateur contenu, Instagram ; blogueur → blog voyage, conseils ; agence → circuit sur mesure, DMC ; hôtel → hébergement, séjour).
- Intègre des mots-clés naturels liés au Vietnam et au profil (sans bourrage).
- La page doit compléter le site (pas dupliquer une destination existante mot pour mot).
- Accroche (pitch) : min. 30 caractères. Offre (offer_details) : min. 40 caractères.

JSON strict :
{
  "review": {
    "approved": true|false,
    "score": 0-100,
    "issues": ["problème 1", "…"],
    "summary": "1-2 phrases expliquant la décision",
    "fixes": [
      {
        "id": "fix_pitch",
        "field": "pitch|highlights|offer_details|city|contact_note",
        "label": "Libellé court",
        "reason": "Pourquoi corriger ce champ",
        "current": "extrait actuel",
        "suggested": "texte corrigé prêt à remplacer le champ"
      }
    ]
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

approved=true seulement si score >= 65 et aucun problème bloquant (hors-sujet, spam, mensonge).
Si approved=false : issues non vide ET fixes avec au moins 1 entrée (suggested respecte les minimums de caractères).
"""

FIXES_ONLY_PROMPT = """Tu es éditeur pour Inside Vietnam Travel (guide voyage Vietnam, FR).

Un partenaire a soumis un brouillon de fiche partenaire. La vérification automatique a échoué ou est incomplète.
Analyse le brouillon et la raison de l'échec, puis propose des corrections concrètes sur les champs éditables.

Champs autorisés : pitch (accroche, min 30 car.), highlights (points forts), offer_details (offre, min 40 car.), city, contact_note.

JSON strict :
{
  "review": {
    "approved": false,
    "score": 0-100,
    "issues": ["…"],
    "summary": "Explication claire de pourquoi la vérification a échoué",
    "fixes": [
      {
        "id": "fix_pitch",
        "field": "pitch",
        "label": "Accroche",
        "reason": "…",
        "current": "…",
        "suggested": "…"
      }
    ]
  }
}

Propose 1 à 5 corrections actionnables. suggested doit être du texte final utilisable tel quel (pas de placeholder).
"""


def _partner_context(account: dict, page: dict) -> str:
    extra = page.get("extra") or {}
    profile_label = PROFILE_TYPE_LABELS.get(account.get("profile_type"), account.get("profile_type"))
    services = account.get("services") or []
    social = account.get("social_links") or []
    return (
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
        f"- Accroche (pitch) : {extra.get('pitch') or '—'}\n"
        f"- Points forts (highlights) : {extra.get('highlights') or '—'}\n"
        f"- Offre détaillée (offer_details) : {extra.get('offer_details') or '—'}\n"
        f"- Ville (city) : {extra.get('city') or '—'}\n"
        f"- Contact (contact_note) : {extra.get('contact_note') or '—'}\n"
    )


def _parse_fixes(raw_fixes, extra: dict) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for idx, item in enumerate(raw_fixes or []):
        if not isinstance(item, dict):
            continue
        field = (item.get("field") or "").strip()
        if field not in ALLOWED_FIX_FIELDS:
            continue
        suggested = str(item.get("suggested") or "").strip()
        if not suggested:
            continue
        fix_id = (item.get("id") or f"fix_{field}_{idx}").strip()[:40]
        if fix_id in seen:
            fix_id = f"{fix_id}_{idx}"
        seen.add(fix_id)
        current = str(item.get("current") or extra.get(field) or "").strip()
        out.append({
            "id": fix_id,
            "field": field,
            "label": str(item.get("label") or FIELD_LABELS.get(field, field))[:80],
            "reason": str(item.get("reason") or "").strip()[:400],
            "current": current[:600],
            "suggested": suggested[:5000],
        })
    return out[:6]


def _normalize_review(review: dict, extra: dict) -> dict:
    review = dict(review or {})
    review["approved"] = bool(review.get("approved"))
    try:
        review["score"] = int(review.get("score", 0))
    except (TypeError, ValueError):
        review["score"] = 0
    review["issues"] = [str(i).strip() for i in (review.get("issues") or []) if str(i).strip()][:8]
    review["summary"] = str(review.get("summary") or "").strip()[:500]
    review["fixes"] = _parse_fixes(review.get("fixes"), extra)
    return review


def _ensure_html(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if "<p" in text.lower() or "<h2" in text.lower():
        return text
    parts = [f"<p>{p.strip()}</p>" for p in re.split(r"\n\s*\n", text) if p.strip()]
    return "".join(parts) if parts else f"<p>{text}</p>"


def _parse_response(raw: str, extra: dict | None = None) -> dict:
    data = ai_client.parse_json(raw)
    review = _normalize_review(data.get("review") or {}, extra or {})
    page = data.get("page") or {}
    if "approved" not in (data.get("review") or {}):
        raise ValueError("Réponse IA incomplète (review)")
    if not page.get("title") or not page.get("overview_html"):
        raise ValueError("Réponse IA incomplète (page)")
    page["overview_html"] = _ensure_html(str(page.get("overview_html", "")))
    page["services_html"] = _ensure_html(str(page.get("services_html", "")))
    if not review["approved"] and not review["fixes"] and review["issues"]:
        review["summary"] = review["summary"] or " ".join(review["issues"][:2])
    return {"review": review, "page": page}


def _parse_fixes_response(raw: str, extra: dict) -> dict:
    data = ai_client.parse_json(raw)
    review = _normalize_review(data.get("review") or {}, extra)
    if not review["summary"]:
        review["summary"] = "La vérification n'a pas pu aboutir — voici les corrections proposées."
    if not review["issues"] and not review["fixes"]:
        raise ValueError("Réponse IA incomplète (corrections)")
    return {"review": review, "page": {}}


def generate_and_review_partner_page(account: dict, page: dict, *, progress=None) -> dict:
    ai_client.require_api_key()
    report = progress or (lambda *_: None)
    report("Analyse du profil partenaire…")

    extra = page.get("extra") or {}
    user_msg = (
        _partner_context(account, page)
        + "\nRédige la page ET décide si elle peut être publiée sur insidevietnamtravel.fr/partenaire/… "
        "Si tu refuses (approved=false), liste les problèmes ET des fixes actionnables sur le brouillon. "
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
        vitrine=True,
    )
    raw = response.choices[0].message.content or ""
    report("Finalisation…")
    result = _parse_response(raw, extra)
    if not result["review"].get("approved") and not result["review"].get("fixes"):
        try:
            hints = suggest_partner_page_fixes(
                account,
                page,
                reason=result["review"].get("summary") or "Page non validée",
            )
            hint_review = hints.get("review") or {}
            if hint_review.get("fixes"):
                result["review"]["fixes"] = hint_review["fixes"]
            if hint_review.get("issues") and not result["review"].get("issues"):
                result["review"]["issues"] = hint_review["issues"]
            if hint_review.get("summary") and len(result["review"].get("summary", "")) < 20:
                result["review"]["summary"] = hint_review["summary"]
        except Exception:
            pass
    return result


def suggest_partner_page_fixes(account: dict, page: dict, *, reason: str = "") -> dict:
    """Propose issues + corrections sans régénérer toute la page (échec technique ou relance)."""
    ai_client.require_api_key()
    extra = page.get("extra") or {}
    err = (reason or "").strip()[:800]
    user_msg = (
        _partner_context(account, page)
        + (f"\nRAISON DE L'ÉCHEC : {err}\n" if err else "\n")
        + "Explique pourquoi la vérification a échoué et propose des corrections sur le brouillon. "
        "JSON strict."
    )
    response = ai_client.chat_completion(
        messages=[
            {"role": "system", "content": FIXES_ONLY_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.25,
        max_tokens=2048,
        json_mode=True,
        vitrine=True,
    )
    raw = response.choices[0].message.content or ""
    return _parse_fixes_response(raw, extra)
