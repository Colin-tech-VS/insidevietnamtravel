"""Génération IA d'une page de partenaire recommandé (voyage Vietnam).

Miroir léger de `admin/groq_destinations.py` : l'admin fournit une consigne (prompt) et
les infos du partenaire (nom, site, type), l'IA rédige une page SEO complète en JSON.
"""

from __future__ import annotations

import json
import re
from datetime import date

from admin import ai_client
from admin.recommended_partners import PARTNERSHIP_TYPE_LABELS
from admin.store import slugify

MIN_WORDS = 500
GEN_MAX_TOKENS = 4096
EXPAND_TOLERANCE = 0.85

SYSTEM_PROMPT = """Tu es un rédacteur SEO voyage Vietnam pour "Inside Vietnam Travel".

PUBLIC : voyageurs français qui préparent un séjour au Vietnam.

Tu rédiges une page qui MET EN AVANT UN PARTENAIRE RECOMMANDÉ par le site (un prestataire,
service, marque ou créateur utile au voyageur). La page doit être honnête, concrète et utile :
elle explique ce que propose le partenaire et pourquoi il est recommandé, SANS langue de bois
publicitaire ni superlatifs creux. N'invente pas de faits (prix, garanties, chiffres) non
fournis dans la consigne.

Réponds en JSON valide UNIQUEMENT :
{
  "title": "Titre de la page (clair, 40-70 car.)",
  "meta_title": "Titre SEO 50-65 car.",
  "meta_description": "140-160 caractères SEO",
  "content_html": "<p>HTML…</p> — minimum 450 mots ; <h2>/<h3>, <p>, <ul><li>. PAS de <h1>.",
  "image_prompt": "Prompt photo anglais, scène Vietnam pertinente, photorealistic, 16:9, no text"
}

Règles :
- content_html : minimum """ + str(MIN_WORDS) + """ mots, structuré (sous-titres, listes).
- Mentionne le partenaire par son nom. Reste centré sur l'utilité pour un voyage au Vietnam.
- Ton honnête, pas de fausses promesses. Pas de noms de personnes fictifs.
"""


def _count_words(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(re.sub(r"\s+", " ", text).strip().split())


def _build_page(data: dict, partner: dict) -> dict:
    title = (data.get("title") or "").strip() or f"Partenaire recommandé : {partner.get('name', '')}"
    return {
        "title": title[:160],
        "slug": slugify(data.get("slug") or title),
        "meta_title": (data.get("meta_title") or title)[:70],
        "meta_description": (data.get("meta_description") or "")[:200],
        "content_html": data.get("content_html") or "",
        "image_prompt": (data.get("image_prompt") or "")[:300],
        "ai_generated": True,
        "updated_at": date.today().isoformat(),
    }


def _partner_brief(partner: dict) -> str:
    ptype = PARTNERSHIP_TYPE_LABELS.get(partner.get("partnership_type", ""), "partenaire")
    lines = [
        f"Nom du partenaire : {partner.get('name', '')}",
        f"Type de partenariat : {ptype}",
    ]
    if partner.get("website"):
        lines.append(f"Site web : {partner['website']}")
    if partner.get("tagline"):
        lines.append(f"Accroche : {partner['tagline']}")
    return "\n".join(lines)


def generate_partner_page(partner: dict, prompt: str, progress=None) -> dict:
    """Génère une page IA pour un partenaire recommandé selon la consigne admin."""
    ai_client.require_api_key()
    report = progress or (lambda *_: None)
    year = date.today().year
    report("Rédaction de la page partenaire (présentation, points forts)…")

    user_prompt = f"""Rédige une page présentant ce partenaire recommandé.

{_partner_brief(partner)}

Année : {year}
CONSIGNE DE L'ADMIN (à suivre fidèlement) :
{prompt or "Présente ce partenaire et ce qu'il propose aux voyageurs français au Vietnam."}

Minimum {MIN_WORDS} mots, structuré et utile."""

    response = ai_client.chat_completion(
        fast=True,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
        max_tokens=GEN_MAX_TOKENS,
    )
    data = ai_client.parse_json(response.choices[0].message.content)
    page = _build_page(data, partner)

    if _count_words(page["content_html"]) < MIN_WORDS * EXPAND_TOLERANCE:
        report("Enrichissement du contenu…")
        expand = ai_client.chat_completion(
            fast=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Le contenu est trop court ({_count_words(page['content_html'])} mots). "
                        f"Enrichis pour atteindre {MIN_WORDS}+ mots en gardant le même angle.\n\n"
                        f"Partenaire : {partner.get('name', '')}\n"
                        f"Consigne : {prompt}\n\n"
                        f"{json.dumps({k: page.get(k) for k in ('title', 'content_html')}, ensure_ascii=False)}"
                    ),
                },
            ],
            temperature=0.5,
            max_tokens=GEN_MAX_TOKENS,
            pause_before=0.5,
        )
        data = ai_client.parse_json(expand.choices[0].message.content)
        page = _build_page(data, partner)

    report("Finalisation de la page…")
    return page
