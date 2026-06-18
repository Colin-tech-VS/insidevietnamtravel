"""Génération IA d'une page ACTIVITÉ d'un partenaire recommandé (voyage Vietnam).

Chaque page met en avant UNE activité proposée par un partenaire recommandé, avec son
prix. Le contenu est optimisé SEO (recherche francophone « activité + Vietnam ») et CRO
(persuasion, réassurance, appel à l'action vers la réservation).
"""

from __future__ import annotations

import json
import re
from datetime import date

from admin import ai_client
from admin.recommended_partners import PARTNERSHIP_TYPE_LABELS
from admin.store import slugify

MIN_WORDS = 550
GEN_MAX_TOKENS = 4096
EXPAND_TOLERANCE = 0.70

SYSTEM_PROMPT = """Tu es rédacteur SEO + CRO spécialisé voyage Vietnam pour "Inside Vietnam Travel".

PUBLIC : voyageurs FRANCOPHONES qui préparent un séjour au Vietnam et comparent des
activités à réserver (excursions, circuits, ateliers, croisières, transferts…).

OBJECTIF : rédiger la page d'UNE activité précise proposée par un partenaire recommandé.
La page doit être à la fois :
- SEO : naturelle pour la recherche francophone (« [activité] Vietnam », « que faire à … »,
  prix, durée, avis) — titres structurés, champ lexical riche, intentions de recherche.
- CRO : pousser à la réservation — bénéfices concrets, réassurance (sécurité, francophone,
  annulation si pertinent), preuve de valeur, et une INCITATION CLAIRE à réserver. Le prix
  fourni doit être mis en avant naturellement. N'invente JAMAIS de prix, garanties, avis ou
  chiffres non fournis ; reste honnête et concret.

Réponds en JSON valide UNIQUEMENT :
{
  "title": "Titre de l'activité, orienté voyageur (40-70 car.)",
  "meta_title": "Titre SEO 50-65 car. avec le mot-clé activité + Vietnam",
  "meta_description": "140-160 caractères, accrocheur, avec bénéfice + incitation",
  "content_html": "<p class=\\"tour-lead\\">Accroche 2–3 phrases.</p> HTML structuré façon fiche activité / excursion (comme une page tour operator) : <h2>Description</h2> (développement), <div class=\\"tour-includes-grid\\"><div class=\\"tour-includes-col\\"><h3>Inclus</h3><ul>…</ul></div><div class=\\"tour-includes-col tour-includes-col--excluded\\"><h3>Non inclus</h3><ul>…</ul></div></div>, <h2>Déroulé de l'activité</h2> (<ol> étapes horaires si pertinent), <h2>Infos pratiques</h2>, <h2>Questions fréquentes</h2>. PAS de <h1>. PAS de balise <a> ni de bouton (le CTA est ajouté automatiquement).",
  "image_prompt": "Prompt photo anglais de la scène/activité au Vietnam, photorealistic, 16:9, no text"
}

Règles :
- content_html : minimum """ + str(MIN_WORDS) + """ mots, en français, structuré (sections tour : description, inclus/non inclus côte à côte, déroulé, FAQ).
- Mentionne le partenaire et l'activité par leur nom. Centre tout sur cette activité au Vietnam.
- Ton honnête et engageant, sans superlatifs creux ni fausses promesses.
"""


def _count_words(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(re.sub(r"\s+", " ", text).strip().split())


def _build_page(data: dict, partner: dict, activity: dict) -> dict:
    fallback = activity.get("title") or f"Activité — {partner.get('name', '')}"
    title = (data.get("title") or "").strip() or fallback
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


def _context(partner: dict, activity: dict, prompt: str) -> str:
    ptype = PARTNERSHIP_TYPE_LABELS.get(partner.get("partnership_type", ""), "partenaire")
    lines = [
        f"PARTENAIRE : {partner.get('name', '')} ({ptype})",
    ]
    if partner.get("website"):
        lines.append(f"Site du partenaire : {partner['website']}")
    if partner.get("tagline"):
        lines.append(f"Accroche partenaire : {partner['tagline']}")
    lines.append(f"ACTIVITÉ : {activity.get('title', '')}")
    price = activity.get("price")
    if price:
        lines.append(f"Prix : {price} {activity.get('currency', '€')} par personne (à mettre en avant)")
    if activity.get("duration"):
        lines.append(f"Durée : {activity['duration']}")
    lines.append(
        "CONSIGNE DE L'ADMIN (à suivre fidèlement) :\n"
        + (prompt or "Présente cette activité et donne envie de la réserver, pour des voyageurs francophones au Vietnam.")
    )
    return "\n".join(lines)


def generate_activity_page(partner: dict, activity: dict, prompt: str = "", progress=None) -> dict:
    """Génère la page IA d'une activité (SEO + CRO) selon la consigne admin."""
    ai_client.require_api_key()
    report = progress or (lambda *_: None)
    year = date.today().year
    report("Rédaction de la page activité (SEO + CRO)…")

    user_prompt = (
        f"Rédige la page de cette activité à réserver, pour des voyageurs francophones.\n\n"
        f"{_context(partner, activity, prompt)}\n\n"
        f"Année : {year}\nMinimum {MIN_WORDS} mots, structuré, orienté réservation."
    )

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
    page = _build_page(data, partner, activity)

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
                        f"Enrichis pour atteindre {MIN_WORDS}+ mots, même angle SEO + CRO.\n\n"
                        f"{_context(partner, activity, prompt)}\n\n"
                        f"{json.dumps({k: page.get(k) for k in ('title', 'content_html')}, ensure_ascii=False)}"
                    ),
                },
            ],
            temperature=0.5,
            max_tokens=GEN_MAX_TOKENS,
            pause_before=0.5,
        )
        data = ai_client.parse_json(expand.choices[0].message.content)
        page = _build_page(data, partner, activity)

    report("Finalisation de la page…")
    return page


# Alias rétro-compatible (ancien nom).
def generate_partner_page(partner: dict, prompt: str, progress=None) -> dict:
    return generate_activity_page(partner, {"title": partner.get("name", "")}, prompt, progress=progress)


_TRANSLATE_SYSTEM = (
    "You are a professional FR→EN translator for a Vietnam travel website. "
    "Translate every provided French field to natural, fluent English. "
    "Keep HTML tags intact. Reply with a JSON object using the SAME keys."
)


def translate_to_en(fields: dict, *, deadline: float | None = 60) -> dict:
    """Traduit en anglais un dict de champs FR (titre, contenu HTML, meta…).

    Best-effort : renvoie {} si l'IA n'est pas configurée ou échoue (l'appelant
    retombe alors sur le FR).
    """
    fields = {k: v for k, v in (fields or {}).items() if v}
    if not fields or not ai_client.is_configured():
        return {}
    try:
        resp = ai_client.chat_completion(
            fast=True,
            messages=[
                {"role": "system", "content": _TRANSLATE_SYSTEM},
                {"role": "user", "content": "Translate these French fields to English:\n" + json.dumps(fields, ensure_ascii=False)},
            ],
            temperature=0.3,
            max_tokens=5120,
            deadline=deadline,
        )
        return ai_client.parse_json(resp.choices[0].message.content) or {}
    except Exception:  # noqa: BLE001
        return {}
