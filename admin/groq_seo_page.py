"""Génération IA de pages SEO landing (multi mots-clés) — objectif SEO maximal."""

from __future__ import annotations

import re
import time
from datetime import date

from admin import ai_client, internal_links
from admin.partner_seo_keywords import gsc_top_queries, seed_keywords
from admin.seo_pages_service import _parse_keywords
from admin.store import slugify

MIN_WORDS = 1500
TARGET_WORDS = 1800
EXPAND_TOLERANCE = 0.88

SYSTEM_PROMPT = """Tu es un expert SEO senior (10+ ans) spécialisé voyage au Vietnam pour "Inside Vietnam Travel".

MISSION : produire la MEILLEURE page landing possible pour ranker sur Google.fr sur PLUSIEURS
requêtes complémentaires — sans bourrage, sans contenu générique.

PUBLIC : voyageurs FRANÇAIS en phase de découverte ou préparation de voyage au Vietnam.

OBJECTIFS SEO MAXIMUM (non négociables) :
1. Mot-clé principal dans les 60 premiers caractères du H1 et dans les 100 premiers mots du corps.
2. Chaque mot-clé secondaire apparaît au moins une fois (H2, paragraphe ou FAQ) de façon naturelle.
3. Variantes sémantiques (LSI) : voyage au Vietnam, séjour, partir, itinéraire, conseils, guide…
4. Featured snippet : la première phrase après l'intro répond directement à l'intention principale (40–50 mots).
5. H1 (title) : 50–65 car., mot-clé principal en tête, "Vietnam" si pertinent.
6. meta_title : 50–60 car., optimisé CTR (chiffre, année ou bénéfice si pertinent), distinct du H1.
7. meta_description : 140–160 car., CTA implicite, 2 mots-clés, pas de points de suspension.
8. excerpt : 140–160 car., résumé vendeur sous le H1.
9. LONGUEUR : minimum {min_words} mots dans content (hors balises). Cible {target_words} mots.
10. HTML : <h2>, <h3>, <p>, <ul>, <li>, <blockquote>, <table>, <a> — JAMAIS de <h1>.
11. Structure : intro percutante → 6–8 sections <h2> (dont 1 tableau comparatif ou budget si pertinent)
    → FAQ 5–7 questions style « People Also Ask » → conclusion avec prochaine étape concrète.
12. Maillage interne : 4 à 6 liens <a href="…"> dans le corps, UNIQUEMENT depuis la liste fournie.
13. E-E-A-T : conseils pratiques vérifiés, ton expert, pas de stats inventées, fourchettes de prix en €.
14. Chaque paragraphe apporte une info utile — zéro remplissage.

JSON uniquement :
{{
  "title": "...",
  "meta_title": "...",
  "meta_description": "...",
  "excerpt": "...",
  "focus_keyword": "mot-clé principal exact",
  "read_time": 10,
  "image_prompt": "Unique English prompt: specific Vietnam scene for THIS topic, photorealistic, 16:9, no text",
  "content": "<p>...</p>"
}}
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
        "\n\nLIENS INTERNES DISPONIBLES (intègre 4 à 6 des plus pertinents DANS les phrases) :\n"
        + link_block
    )


def _keyword_block(keywords: list[str], city: str) -> str:
    lines = [f"- {k}" for k in keywords]
    if city and city != "Tout le Vietnam":
        lines.append(f"- Contexte géographique obligatoire : {city}, Vietnam")
    gsc = gsc_top_queries(limit=10)
    if gsc:
        lines.append("\nRequêtes Search Console (variations sémantiques à intégrer si pertinent) :")
        lines.extend(f"- {q}" for q in gsc[:10])
    return "\n".join(lines)


def _call_ai(messages: list, max_tokens: int = 16000, *, fast: bool = False) -> dict:
    response = ai_client.chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        fast=fast,
        temperature=0.55,
    )
    data = ai_client.parse_json(response.choices[0].message.content)
    if "content" not in data or "title" not in data:
        raise ValueError("Réponse IA incomplète pour la page SEO.")
    return data


def _expand_if_short(page: dict, keywords: list[str], city: str, link_block: str, progress=None) -> dict:
    current = _count_words(page.get("content", ""))
    if current >= MIN_WORDS * EXPAND_TOLERANCE:
        page["word_count"] = current
        page["read_time"] = _read_time(current)
        return page

    report = progress or (lambda *_: None)
    report(f"Enrichissement SEO ({current} → {MIN_WORDS}+ mots)…")

    expand_prompt = f"""L'article ci-dessous fait seulement {current} mots. Il DOIT atteindir {MIN_WORDS} mots minimum (cible {TARGET_WORDS}).

Mot-clé principal : {page.get('focus_keyword', keywords[0] if keywords else '')}
Mots-clés secondaires : {', '.join(keywords[:8])}
Ville : {city or 'Vietnam'}

Enrichis SANS changer le sujet :
- Ajoute sections H2, FAQ, tableau budget, erreurs à éviter
- Renforce le SEO (mots-clés, LSI, featured snippet)
- Garde le HTML existant et complète

Réponds en JSON complet (title, meta_title, meta_description, excerpt, focus_keyword, content, image_prompt).

Contenu actuel :
{page.get('content', '')[:14000]}""" + _links_section(link_block)

    sys = SYSTEM_PROMPT.format(min_words=MIN_WORDS, target_words=TARGET_WORDS)
    data = _call_ai(
        [
            {"role": "system", "content": sys},
            {"role": "user", "content": expand_prompt},
        ],
        max_tokens=16000,
        fast=False,
    )
    for key in ("title", "meta_title", "meta_description", "excerpt", "content", "focus_keyword", "image_prompt"):
        if data.get(key):
            page[key] = data[key]
    wc = _count_words(page["content"])
    page["word_count"] = wc
    page["read_time"] = _read_time(wc)
    return page


def generate_seo_page(
    *,
    topic: str,
    keywords: list[str] | str,
    city: str = "",
    page_type: str = "landing",
    progress=None,
) -> dict:
    """Génère une page SEO FR optimisée au maximum (traduction EN à la publication)."""
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
    sys = SYSTEM_PROMPT.format(min_words=MIN_WORDS, target_words=TARGET_WORDS)

    user_prompt = f"""Rédige une page SEO landing ULTRA-OPTIMISÉE (objectif : top 3 Google.fr).

Sujet / angle principal : {topic}
Type de page : {page_type}
Ville / région : {city or "Vietnam (général)"}

CLUSTER DE MOTS-CLÉS (tous à intégrer naturellement) :
{_keyword_block(keywords, city)}

LONGUEUR OBLIGATOIRE : minimum {MIN_WORDS} mots dans content, cible {TARGET_WORDS} mots.""" + _links_section(link_block)

    report("Rédaction SEO maximale (titres, sections, FAQ, tableau)…")
    data = _call_ai(
        [
            {"role": "system", "content": sys},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=16000,
        fast=False,
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

    page = _expand_if_short(page, keywords, city, link_block, progress=report)

    report("Maillage interne et validation des liens…")
    page["content"], _ = internal_links.process_content(page["content"], slug, catalog)
    return page


def generate_seo_batch(
    rows: list[dict],
    progress=None,
) -> dict:
    """Génère plusieurs pages SEO à partir d'une matrice (avec pause anti rate-limit)."""
    report = progress or (lambda *_: None)
    pages: list[dict] = []
    errors: list[dict] = []
    total = len(rows)

    for i, row in enumerate(rows, 1):
        topic = (row.get("topic") or "").strip()
        report(f"Page {i}/{total} — rédaction SEO : {topic[:55]}…")
        try:
            page = generate_seo_page(
                topic=topic,
                keywords=row.get("keywords") or [],
                city=row.get("city") or "",
                page_type=row.get("page_type") or "landing",
                progress=report,
            )
            from admin.image_service import attach_image_to_article

            report(f"Page {i}/{total} — image WebP…")
            page.update(attach_image_to_article(page, page.get("image_prompt")))
            pages.append(page)
        except Exception as exc:  # noqa: BLE001
            errors.append({"topic": topic, "error": str(exc)})
        if i < total:
            time.sleep(2.5)

    return {
        "batch": True,
        "pages": pages,
        "errors": errors,
        "total": total,
        "completed": len(pages),
    }
