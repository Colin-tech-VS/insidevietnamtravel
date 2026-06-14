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

MIN_FIELD_LEN = {
    "pitch": 30,
    "offer_details": 40,
}

MIN_PUBLISH_SCORE = 65

FIX_GROUNDING_RULES = """
RÈGLES CORRECTIONS (fixes) — OBLIGATOIRES :
- Chaque « suggested » doit être une AMÉLIORATION du texte « current » / brouillon : conserve les faits, villes, langues, activités et spécificités déjà saisis par le partenaire.
- Ne remplace pas par un texte générique ou un autre métier : reformule, structure, corrige orthographe/SEO et complète ce qui manque.
- Utilise le nom de marque exact du profil (business_name) — ne dupliques pas « Travel », ne mélange pas avec « Inside Vietnam Travel » (c’est le site éditeur, pas le partenaire).
- Si bio inscription ou services déclarés existent, intègre-les dans pitch/offre/highlights quand le brouillon est vide ou faible.
- contact_note : inclure email et site web du profil s’ils existent.
- highlights : 3 à 6 points courts, distincts, sans redondance (une puce = un atout).
- L’objectif des corrections : après application, une nouvelle vérification doit pouvoir atteindre score ≥ 70 et approved=true si le Vietnam et le profil sont cohérents.
- suggested = texte final prêt à coller (pas de placeholder, pas de « … », pas de consigne entre crochets).
"""

SYSTEM_PROMPT = f"""Tu es éditeur SEO pour « Inside Vietnam Travel », guide voyage Vietnam en français.

Tu reçois le profil d'un partenaire (guide, influenceur, blogueur, agence, hôtel…) et son brouillon.
Tu dois :
1) Rédiger une page partenaire cohérente avec le site (ton chaleureux, expert, honnête) EN T'APPUYANT SUR LE BROUILLON ET LE PROFIL.
2) Vérifier que le contenu respecte les règles éditoriales du site.
3) Si la page n'est PAS validée, proposer des corrections concrètes sur le BROUILLON (champs pitch, highlights, offer_details, city, contact_note).

RÈGLES DESIGN & CONTENU (obligatoires pour valider) :
- Contenu 100% lié au Vietnam (voyage, tourisme, expérience locale).
- Pas de promesses mensongères, pas de chiffres d'audience inventés.
- Pas de contenu spam, adulte, crypto, MLM ou hors-sujet.
- HTML corps : uniquement <p>, <h2>, <ul>, <li>, <strong>, <a href="…"> (pas de h1).
- Ton professionnel mais humain, en français.
- SEO : meta_title 50-65 car., meta_description 140-160 car.
- profile_highlights : reprends et reformule les points forts du brouillon (highlights) — minimum 3 entrées courtes et concrètes, jamais vide si le brouillon en contient.
- Adapte le SEO au type de partenaire (guide → tours privés, excursions ; influenceur → créateur contenu, Instagram ; blogueur → blog voyage, conseils ; agence → circuit sur mesure, DMC ; hôtel → hébergement, séjour).
- Intègre des mots-clés naturels liés au Vietnam et au profil (sans bourrage).
- La page doit compléter le site (pas dupliquer une destination existante mot pour mot).
- Accroche (pitch) : min. 30 caractères. Offre (offer_details) : min. 40 caractères.
- page.title = nom affiché du partenaire (business_name ou prénom + nom), jamais le nom du site éditeur.
- overview_html : 2 à 3 paragraphes <p> (présentation, approche, zone géographique) — min. 120 mots au total.
- services_html : un <h2> titre des prestations + <ul> de 4 à 6 <li> détaillés. Chaque <li> : <strong>intitulé court</strong> puis 1–2 phrases concrètes (expériences, durées, publics). Ne pas répéter profile_highlights mot pour mot — ici le détail des offres.
- profile_highlights : 3 à 5 puces courtes (résumé), distinctes du détail services_html.

{FIX_GROUNDING_RULES}

JSON strict :
{{
  "review": {{
    "approved": true|false,
    "score": 0-100,
    "issues": ["problème 1", "…"],
    "summary": "1-2 phrases expliquant la décision",
    "fixes": [
      {{
        "id": "fix_pitch",
        "field": "pitch|highlights|offer_details|city|contact_note",
        "label": "Libellé court",
        "reason": "Pourquoi corriger ce champ",
        "current": "extrait actuel",
        "suggested": "texte corrigé prêt à remplacer le champ"
      }}
    ]
  }},
  "page": {{
    "title": "Nom affiché",
    "tagline": "Accroche courte",
    "overview_html": "<p>…</p>",
    "services_html": "<h2>…</h2><ul>…</ul>",
    "seo_title": "…",
    "seo_description": "…",
    "profile_highlights": ["point fort 1", "…"]
  }}
}}

approved=true seulement si score >= {MIN_PUBLISH_SCORE} et aucun problème bloquant (hors-sujet, spam, mensonge).
Si le brouillon est Vietnam + cohérent avec le profil après corrections, privilégie approved=true plutôt qu'un refus perfectionniste.
Si approved=false : issues non vide ET fixes avec au moins 1 entrée (suggested respecte les minimums de caractères).
"""

FIXES_ONLY_PROMPT = f"""Tu es éditeur pour Inside Vietnam Travel (guide voyage Vietnam, FR).

Un partenaire a soumis un brouillon de fiche partenaire. La vérification automatique a échoué ou est incomplète.
Analyse le brouillon et la raison de l'échec, puis propose des corrections concrètes sur les champs éditables.

Champs autorisés : pitch (accroche, min 30 car.), highlights (points forts), offer_details (offre, min 40 car.), city, contact_note.

{FIX_GROUNDING_RULES}

Propose 1 à 5 corrections actionnables couvrant tous les problèmes bloquants.
Chaque suggested doit permettre d'atteindre score ≥ 70 à la prochaine vérification.

JSON strict :
{{
  "review": {{
    "approved": false,
    "score": 0-100,
    "issues": ["…"],
    "summary": "Explication claire de pourquoi la vérification a échoué",
    "fixes": [
      {{
        "id": "fix_pitch",
        "field": "pitch",
        "label": "Accroche",
        "reason": "…",
        "current": "…",
        "suggested": "…"
      }}
    ]
  }}
}}
"""


def _display_name(account: dict) -> str:
    business = (account.get("business_name") or "").strip()
    if business:
        return business
    parts = [account.get("first_name") or "", account.get("last_name") or ""]
    return " ".join(p.strip() for p in parts if p and str(p).strip()).strip() or "Partenaire"


def _partner_context(account: dict, page: dict) -> str:
    extra = page.get("extra") or {}
    profile_label = PROFILE_TYPE_LABELS.get(account.get("profile_type"), account.get("profile_type"))
    services = account.get("services") or []
    social = account.get("social_links") or []
    display_name = _display_name(account)
    lines = [
        f"Type de partenaire : {profile_label}",
        f"Nom affiché (à utiliser pour title/page) : {display_name}",
        f"Prénom / nom : {account.get('first_name') or '—'} {account.get('last_name') or ''}".strip(),
        f"Ville profil : {account.get('city') or '—'}",
        f"Email contact : {account.get('email') or '—'}",
        f"Site web : {account.get('website') or '—'}",
        f"Langues : {account.get('languages') or '—'}",
        f"Bio inscription : {account.get('bio') or '—'}",
        f"Services déclarés : {', '.join(services) if services else '—'}",
        f"Réseaux : {', '.join(social) if social else '—'}",
        "",
        "BROUILLON PAGE (source de vérité — enrichir, ne pas jeter) :",
        f"- Accroche (pitch) : {extra.get('pitch') or '—'}",
        f"- Points forts (highlights) : {extra.get('highlights') or '—'}",
        f"- Offre détaillée (offer_details) : {extra.get('offer_details') or '—'}",
        f"- Ville (city) : {extra.get('city') or '—'}",
        f"- Contact (contact_note) : {extra.get('contact_note') or '—'}",
    ]
    if extra.get("ai_fixes_applied"):
        lines.append("")
        lines.append(
            "NOTE : le partenaire a déjà appliqué des corrections IA. "
            "Évalue le brouillon ACTUEL ci-dessus : si Vietnam + profil cohérents "
            f"(pitch ≥30 car., offer ≥40 car.), valide (approved=true, score ≥ 70)."
        )
    return "\n".join(lines) + "\n"


def _enrich_fix_suggested(field: str, suggested: str, current: str, account: dict, extra: dict) -> str:
    suggested = (suggested or "").strip()
    current = (current or "").strip()
    if not suggested:
        return current
    if field == "contact_note":
        bits = [suggested]
        email = (account.get("email") or "").strip()
        website = (account.get("website") or "").strip()
        low = suggested.lower()
        if email and email.lower() not in low:
            bits.append(f"Email : {email}")
        if website and website.lower() not in low:
            bits.append(f"Site : {website}")
        return "\n".join(bits)
    if field == "city" and not suggested and (extra.get("city") or account.get("city")):
        return (extra.get("city") or account.get("city") or "").strip()
    return suggested


def _fix_meets_minimum(field: str, suggested: str) -> bool:
    min_len = MIN_FIELD_LEN.get(field)
    if min_len and len((suggested or "").strip()) < min_len:
        return False
    if not (suggested or "").strip():
        return False
    placeholder_markers = ("...", "[", "]", "à compléter", "placeholder", "exemple :", "ex :")
    low = suggested.lower()
    if any(m in low for m in placeholder_markers):
        return False
    return True


def _parse_fixes(raw_fixes, extra: dict, account: dict | None = None) -> list[dict]:
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
        current = str(item.get("current") or extra.get(field) or "").strip()
        if account:
            suggested = _enrich_fix_suggested(field, suggested, current, account, extra)
        if not _fix_meets_minimum(field, suggested):
            continue
        fix_id = (item.get("id") or f"fix_{field}_{idx}").strip()[:40]
        if fix_id in seen:
            fix_id = f"{fix_id}_{idx}"
        seen.add(fix_id)
        out.append({
            "id": fix_id,
            "field": field,
            "label": str(item.get("label") or FIELD_LABELS.get(field, field))[:80],
            "reason": str(item.get("reason") or "").strip()[:400],
            "current": current[:600],
            "suggested": suggested[:5000],
        })
    return out[:6]


def _normalize_review(review: dict, extra: dict, account: dict | None = None) -> dict:
    review = dict(review or {})
    review["approved"] = bool(review.get("approved"))
    try:
        review["score"] = int(review.get("score", 0))
    except (TypeError, ValueError):
        review["score"] = 0
    if review["approved"] and review["score"] < MIN_PUBLISH_SCORE:
        review["approved"] = False
    review["issues"] = [str(i).strip() for i in (review.get("issues") or []) if str(i).strip()][:8]
    review["summary"] = str(review.get("summary") or "").strip()[:500]
    review["fixes"] = _parse_fixes(review.get("fixes"), extra, account)
    return review


def _ensure_html(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if "<p" in text.lower() or "<h2" in text.lower():
        return text
    parts = [f"<p>{p.strip()}</p>" for p in re.split(r"\n\s*\n", text) if p.strip()]
    return "".join(parts) if parts else f"<p>{text}</p>"


def _parse_response(raw: str, extra: dict | None = None, account: dict | None = None) -> dict:
    data = ai_client.parse_json(raw)
    review = _normalize_review(data.get("review") or {}, extra or {}, account)
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


def _parse_fixes_response(raw: str, extra: dict, account: dict | None = None) -> dict:
    data = ai_client.parse_json(raw)
    review = _normalize_review(data.get("review") or {}, extra, account)
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
        + "\nRédige la page EN T'INSPIRANT DU BROUILLON (reformule, structure, complète — ne remplace pas par un profil générique). "
        f"title = « {_display_name(account)} ». "
        "Décide si elle peut être publiée sur insidevietnamtravel.fr/partenaire/… "
        "Si tu refuses (approved=false), liste les problèmes ET des fixes actionnables ancrés dans le brouillon actuel. "
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
    result = _parse_response(raw, extra, account)
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
        + "Propose des corrections ANCRÉES dans le brouillon actuel (reformulation, pas remplacement générique). "
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
    return _parse_fixes_response(raw, extra, account)
