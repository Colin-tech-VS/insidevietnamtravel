"""Génération IA de pages SEO landing (multi mots-clés)."""

from __future__ import annotations

import re
from datetime import date

from admin import ai_client, internal_links
from admin.partner_seo_keywords import gsc_top_queries, seed_keywords
from admin.seo_pages_service import _parse_keywords
from admin.store import slugify

SYSTEM_PROMPT = """Tu es un expert SEO senior spécialisé voyage au Vietnam pour "Inside Vietnam Travel".

OBJECTIF : rédiger une PAGE SEO LANDING (pas un article de blog) qui cible PLUSIEURS requêtes
Google complémentaires de façon naturelle, sans bourrage de mots-clés.

PUBLIC : voyageurs FRANÇAIS qui préparent un voyage au Vietnam.

RÈGLES SEO STRICTES :
1. H1 (title) : 50–65 car., mot-clé principal en début, "Vietnam" si pertinent.
2. meta_title : 50–60 car., optimisé SERP, peut différer du H1.
3. meta_description : 140–160 car., incitative, intègre 1–2 mots-clés secondaires.
4. excerpt : 140–160 car., résumé visible sous le H1.
5. Longueur : minimum 1200 mots dans content (texte hors balises HTML).
6. HTML : <h2>, <h3>, <p>, <ul>, <li>, <blockquote>, <table>, <a> uniquement — pas de <h1>.
7. Structure : intro accrocheuse, 5–7 sections <h2>, FAQ (4–6 Q/R en <h3>+<p>), conclusion avec CTA doux.
8. Intègre TOUS les mots-clés cibles de façon naturelle (titres, paragraphes, FAQ) — pas de liste de mots-clés.
9. Maillage interne : 3 à 5 liens <a href="…"> dans le corps, UNIQUEMENT depuis la liste fournie.
10. Fourchettes de prix en euros. Ton expert bienveillant. Pas de statistiques inventées.

JSON uniquement :
{
  "title": "...",
  "meta_title": "...",
  "meta_description": "...",
  "excerpt": "...",
  "focus_keyword": "mot-clé principal",
  "read_time": 8,
  "image_prompt": "Unique English prompt: specific Vietnam scene for THIS topic, photorealistic, 16:9, no text",
  "content": "<p>...</p>"
}
"""


def _count_words(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(text.split()) if text.strip() else 0


def _read_time(words: int) -> int:
    return max(5, round(words / 200))


def _links_section(link_block: str) -> str:
    if not link_block:
        return ""
    return (
        "\n\nLIENS INTERNES DISPONIBLES (intègre 3 à 5 des plus pertinents DANS les phrases) :\n"
        + link_block
    )


def _keyword_block(keywords: list[str], city: str) -> str:
    lines = [f"- {k}" for k in keywords]
    if city and city != "Tout le Vietnam":
        lines.append(f"- Contexte géographique : {city}, Vietnam")
    gsc = gsc_top_queries(limit=8)
    if gsc:
        lines.append("\nRequêtes Search Console (inspiration, pas copier-coller) :")
        lines.extend(f"- {q}" for q in gsc[:8])
    return "\n".join(lines)


def _call_ai(messages: list, max_tokens: int = 12000) -> dict:
    response = ai_client.chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        fast=True,
    )
    data = ai_client.parse_json(response.choices[0].message.content)
    if "content" not in data or "title" not in data:
        raise ValueError("Réponse IA incomplète pour la page SEO.")
    return data


def generate_seo_page(
    *,
    topic: str,
    keywords: list[str] | str,
    city: str = "",
    page_type: str = "landing",
    progress=None,
) -> dict:
    """Génère une page SEO FR (traduction EN à la publication)."""
    ai_client.require_api_key()
    report = progress or (lambda *_: None)
    keywords = _parse_keywords(keywords)
    if not keywords:
        keywords = [k for k in seed_keywords("fr")[:6]]
    if topic:
        if topic not in keywords:
            keywords.insert(0, topic)
    else:
        topic = keywords[0]

    report("Analyse des mots-clés et du maillage interne…")
    catalog = internal_links.build_catalog()
    link_block = internal_links.prompt_block(catalog)

    user_prompt = f"""Rédige une page SEO landing ultra-optimisée.

Sujet / angle principal : {topic}
Type de page : {page_type}
Ville / région (si pertinent) : {city or "Vietnam (général)"}

MOTS-CLÉS CIBLES (à intégrer naturellement dans titres, corps et FAQ) :
{_keyword_block(keywords, city)}

LONGUEUR : minimum 1200 mots dans content.""" + _links_section(link_block)

    report("Rédaction de la page SEO (titres, sections, FAQ)…")
    data = _call_ai(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=14000,
    )

    slug = slugify(data.get("title") or topic)
    word_count = _count_words(data["content"])
    page = {
        "slug": slug,
        "title": data["title"].strip(),
        "meta_title": (data.get("meta_title") or data["title"])[:70].strip(),
        "meta_description": (data.get("meta_description") or data.get("excerpt", ""))[:160].strip(),
        "excerpt": (data.get("excerpt") or data.get("meta_description", ""))[:160].strip(),
        "focus_keyword": (data.get("focus_keyword") or keywords[0])[:80],
        "target_keywords": keywords,
        "city": city,
        "page_type": page_type,
        "date": date.today().isoformat(),
        "read_time": _read_time(word_count),
        "word_count": word_count,
        "image_prompt": data.get("image_prompt", ""),
        "content": data["content"],
        "ai_generated": True,
        "status": "draft",
    }

    report("Maillage interne et validation des liens…")
    page["content"], _ = internal_links.process_content(page["content"], slug, catalog)
    return page
