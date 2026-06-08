"""Génération d'emails newsletter via Groq."""

from __future__ import annotations

import json
import os
import re

from groq import Groq

from admin.store import get_settings

EMAIL_TYPES = [
    {"value": "actualite", "label": "Actualité voyage", "icon": "📰"},
    {"value": "nouveau_guide", "label": "Nouvel article / guide", "icon": "✦"},
    {"value": "conseils", "label": "Conseils pratiques", "icon": "💡"},
    {"value": "promo_pdf", "label": "Guide PDF / offre", "icon": "📘"},
    {"value": "saison", "label": "Meilleure saison", "icon": "🌤"},
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
    data = json.loads(raw)
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


def generate_newsletter_email(
    topic: str,
    email_type: str = "actualite",
    notes: str = "",
) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    settings = get_settings()
    model = settings.get("groq_model", "llama-3.3-70b-versatile")

    type_label = next((t["label"] for t in EMAIL_TYPES if t["value"] == email_type), email_type)
    user_msg = (
        f"Rédige un email newsletter.\n"
        f"Type : {type_label}\n"
        f"Sujet / angle : {topic}\n"
    )
    if notes:
        user_msg += f"Notes éditoriales : {notes}\n"
    user_msg += "Réponds en JSON strict."

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or ""
    data = _parse_response(raw)
    return {
        "subject": str(data["subject"]).strip()[:120],
        "preheader": str(data.get("preheader", "")).strip()[:160],
        "body_html": _ensure_html(str(data["body_html"])),
        "ai_generated": True,
        "manual": False,
        "email_type": email_type,
        "topic": topic,
    }
