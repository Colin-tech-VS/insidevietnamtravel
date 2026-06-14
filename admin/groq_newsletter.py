"""Génération d'emails newsletter via Groq."""

from __future__ import annotations

import json
import re

from admin import ai_client
from admin.partners_service import partnership_greeting

EMAIL_TYPES = [
    {"value": "actualite", "label": "Actualité voyage", "icon": "📰"},
    {"value": "nouveau_guide", "label": "Nouvel article / guide", "icon": "✦"},
    {"value": "conseils", "label": "Conseils pratiques", "icon": "💡"},
    {"value": "promo_pdf", "label": "Guide PDF / offre", "icon": "📘"},
    {"value": "saison", "label": "Meilleure saison", "icon": "🌤"},
    {"value": "partenariat", "label": "Proposition de partenariat", "icon": "🤝"},
]

SYSTEM_PROMPT = """Tu es rédacteur email marketing pour "Inside Vietnam Travel", guide voyage Vietnam en français.

PUBLIC : français qui préparent un voyage au Vietnam ou y rêvent.

RÈGLES :
- Ton chaleureux, expert, utile — jamais agressif ni spam.
- Objet accrocheur 40–70 caractères, pas de MAJUSCULES abusives.
- Preheader 80–120 caractères (aperçu inbox).
- Corps HTML : <p>, <h2>, <ul>, <li>, <strong>, <a href="#"> uniquement (pas de h1).
- 250–450 mots. Paragraphes courts. 1 CTA clair vers le site.
- Contenu 100% Vietnam, conseils concrets.
- Pas de fausses promos ni statistiques inventées.

JSON uniquement :
{
  "subject": "...",
  "preheader": "...",
  "body_html": "<p>...</p>"
}
"""


def _parse_response(raw: str) -> dict:
    data = ai_client.parse_json(raw)
    for key in ("subject", "body_html"):
        if key not in data or not str(data[key]).strip():
            raise ValueError("Réponse IA incomplète")
    return data


def _ensure_html(text: str) -> str:
    text = text.strip()
    if "<" in text and ">" in text:
        return text
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in parts)


def _partner_name_from_topic(topic: str) -> str:
    m = re.match(r"(?i)partenariat\s+avec\s+(.+?)(?:\s*\(|$)", (topic or "").strip())
    return m.group(1).strip() if m else ""


_PLACEHOLDER_GREETING_RE = re.compile(
    r"Bonjour\s*(?:"
    r"\[[^\]]*pr[eé]nom[^\]]*\]"
    r"|\([^)]*pr[eé]nom[^)]*\)"
    r"|\{[^}]*pr[eé]nom[^}]*\}"
    r"|\[[^\]]+\]"
    r"|\([^)]+\)"
    r"|\{[^}]+\}"
    r"|Pr[eé]nom"
    r")",
    re.IGNORECASE,
)


def _apply_partnership_greeting(body_html: str, greeting: str) -> str:
    """Remplace salutations placeholder ou inventées par la formule calculée."""
    if not body_html or not greeting:
        return body_html
    fixed = _PLACEHOLDER_GREETING_RE.sub(greeting.rstrip(","), body_html, count=1)
    if fixed == body_html and greeting.lower() not in body_html.lower():
        fixed = re.sub(
            r"(<p>\s*)Bonjour[^,<]*,",
            rf"\1{greeting.rstrip(',')},",
            body_html,
            count=1,
            flags=re.IGNORECASE,
        )
    return fixed


def generate_newsletter_email(
    topic: str,
    email_type: str = "actualite",
    notes: str = "",
    progress=None,
    partner_name: str = "",
    recipient_email: str = "",
) -> dict:
    ai_client.require_api_key()
    report = progress or (lambda *_: None)
    report("Rédaction de l'email (objet, accroche, corps)…")

    type_label = next((t["label"] for t in EMAIL_TYPES if t["value"] == email_type), email_type)
    user_msg = (
        f"Rédige un email newsletter.\n"
        f"Type : {type_label}\n"
        f"Sujet / angle : {topic}\n"
    )
    greeting = ""
    if email_type == "partenariat":
        pname = (partner_name or "").strip() or _partner_name_from_topic(topic)
        remail = (recipient_email or "").strip()
        greeting = partnership_greeting(pname, remail)
        dest_line = pname or topic
        if remail:
            dest_line += f" ({remail})"
        user_msg = (
            "Rédige un email de PROSPECTION PARTENARIAT (B2B) — PAS une newsletter aux abonnés.\n"
            f"Destinataire : {dest_line}\n"
            f"SALUTATION OBLIGATOIRE (première phrase, copier-coller exact) : « {greeting} »\n"
            "INTERDIT : prénom inventé, [Prénom], (Prénom), {prénom}, ou tout placeholder.\n"
            "CONTEXTE : tu écris au nom de l'éditeur d'Inside Vietnam Travel "
            "(insidevietnamtravel.fr), guide francophone du voyage au Vietnam, à un "
            "partenaire potentiel (influenceur, blogueur, créateur, guide local ou agence).\n"
            "OBJECTIF : proposer une collaboration concrète et gagnant-gagnant — au choix "
            "selon le profil : article invité ou interview sur le site, mise en avant de son "
            "contenu auprès de notre audience, post sponsorisé / échange de visibilité sur "
            "nos réseaux (Facebook, Pinterest, Instagram…), lien d'affiliation.\n"
            "RÈGLES SPÉCIFIQUES : personnalise avec le nom de marque / chaîne / blog "
            "(pas un prénom de contact) et la niche (sujet/notes) ; reste court (120-200 mots), "
            "humain et direct ; montre qu'on connaît son travail ; UNE proposition claire + "
            "question simple en fin (« partant pour en discuter ? ») ; pas de jargon marketing "
            "ni de promesses chiffrées inventées ; signature « L'équipe Inside Vietnam Travel ».\n"
        )
    if notes:
        user_msg += f"Notes éditoriales : {notes}\n"
    user_msg += "Réponds en JSON strict."

    response = ai_client.chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=2048,
    )
    raw = response.choices[0].message.content or ""
    data = _parse_response(raw)
    body_html = _ensure_html(str(data["body_html"]))
    if email_type == "partenariat" and greeting:
        body_html = _apply_partnership_greeting(body_html, greeting)
    return {
        "subject": str(data["subject"]).strip()[:120],
        "preheader": str(data.get("preheader", "")).strip()[:160],
        "body_html": body_html,
        "ai_generated": True,
        "manual": False,
        "email_type": email_type,
        "topic": topic,
    }
