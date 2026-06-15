"""Génération IA de pages SEO landing — multi-passes anti-troncature."""

from __future__ import annotations

import re
import time
from datetime import date

from admin import ai_client, internal_links
from admin.partner_seo_keywords import gsc_top_queries, seed_keywords
from admin.seo_pages_service import _parse_keywords
from admin.store import slugify

MIN_WORDS = 1200
TARGET_WORDS = 1500
EXPAND_TOLERANCE = 0.85
MAX_CONTINUE_PASSES = 4

# ≈ mots × 2,2 + marge JSON — calibré comme groq_ai (évite la troncature Groq TPM).
META_MAX_TOKENS = 2048
CONTENT_MAX_TOKENS = 5120
CONTINUE_MAX_TOKENS = 4608

META_SYSTEM = """Tu es expert SEO voyage Vietnam (Inside Vietnam Travel). Public : Français.
Réponds en JSON valide UNIQUEMENT :
{
  "title": "H1 50-65 car.",
  "meta_title": "50-60 car.",
  "meta_description": "140-160 car.",
  "excerpt": "140-160 car.",
  "focus_keyword": "mot-clé principal",
  "image_prompt": "English photorealistic Vietnam scene, 16:9, no text",
  "outline": ["Section H2 1", "Section H2 2", "... 6 à 8 titres dont FAQ"]
}
Pas de champ content ici."""

CONTENT_SYSTEM = """Tu es rédacteur SEO senior — voyage Vietnam, audience française.
HTML autorisé : <h2>, <h3>, <p>, <ul>, <li>, <blockquote>, <table>, <a> — jamais <h1>.
Réponds en JSON : {"content": "<p>…</p>"} — le champ content contient TOUT le corps de la page.
Pas d'autres champs."""

CONTINUE_SYSTEM = """Tu complètes une page SEO Vietnam coupée avant la fin.
Réponds en JSON : {"append": "<html à AJOUTER à la suite, sans répéter le début>"}
HTML : <h2>, <h3>, <p>, <ul>, <li>, <blockquote>, <table>, <a>."""


def _count_words(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(text.split()) if text.strip() else 0


def _read_time(words: int) -> int:
    return max(5, round(words / 200))


def _links_section(link_block: str) -> str:
    if not link_block:
        return ""
    return (
        "\n\nLIENS INTERNES (4 à 6 liens <a href> dans le corps, liste fournie) :\n"
        + link_block
    )


def _keyword_block(keywords: list[str], city: str) -> str:
    lines = [f"- {k}" for k in keywords]
    if city and city != "Tout le Vietnam":
        lines.append(f"- Contexte : {city}, Vietnam")
    for q in gsc_top_queries(limit=6):
        lines.append(f"- (GSC) {q}")
    return "\n".join(lines)


def _call_ai(
    messages: list,
    max_tokens: int,
    *,
    fast: bool = True,
    pause_before: float = 0,
) -> tuple[dict, bool]:
    if pause_before > 0:
        time.sleep(pause_before)
    response = ai_client.chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        fast=fast,
        temperature=0.55,
    )
    choice = response.choices[0]
    raw = choice.message.content
    truncated = getattr(choice, "finish_reason", None) == "length"
    data = ai_client.parse_json(raw)
    return data, truncated


def _html_looks_incomplete(html: str) -> bool:
    if not (html or "").strip():
        return True
    html = html.strip()
    open_p, close_p = html.count("<p>"), html.count("</p>")
    open_h2, close_h2 = html.count("<h2"), html.count("</h2>")
    if open_p > close_p or open_h2 > close_h2:
        return True
    if _count_words(html) < 400:
        return True
    tail = html[-120:].lower()
    if tail.endswith(("<", "</", '"', "&")):
        return True
    return False


def _generate_meta(
    *,
    topic: str,
    keywords: list[str],
    city: str,
    page_type: str,
) -> dict:
    user = f"""Page SEO landing — métadonnées + plan.

Sujet : {topic}
Type : {page_type}
Ville : {city or "Vietnam"}
Mots-clés : {_keyword_block(keywords, city)}

outline : 6 à 8 titres H2 (dont section FAQ avec 5+ questions prévues)."""
    data, _ = _call_ai(
        [
            {"role": "system", "content": META_SYSTEM},
            {"role": "user", "content": user},
        ],
        META_MAX_TOKENS,
        fast=True,
    )
    required = ("title", "meta_title", "meta_description", "excerpt", "focus_keyword")
    if not all(data.get(k) for k in required):
        raise ValueError("Métadonnées SEO incomplètes.")
    return data


def _generate_content(
    *,
    meta: dict,
    keywords: list[str],
    city: str,
    link_block: str,
) -> tuple[str, bool]:
    outline = meta.get("outline") or []
    if isinstance(outline, str):
        outline = [outline]
    outline_txt = "\n".join(f"- {t}" for t in outline) if outline else "(structure libre : intro, 6 H2, FAQ, conclusion)"

    user = f"""Rédige le CORPS HTML complet de la page SEO.

Titre H1 : {meta.get("title", "")}
Mot-clé principal : {meta.get("focus_keyword", keywords[0] if keywords else "")}
Mots-clés secondaires : {", ".join(keywords[:10])}
Ville : {city or "Vietnam"}

Plan H2 à suivre :
{outline_txt}

LONGUEUR OBLIGATOIRE : minimum {MIN_WORDS} mots (texte hors balises), cible {TARGET_WORDS}.
Intro percutante + featured snippet (réponse directe en 40 mots) + sections + FAQ (h3+p) + conclusion.
{_links_section(link_block)}"""

    data, truncated = _call_ai(
        [
            {"role": "system", "content": CONTENT_SYSTEM},
            {"role": "user", "content": user},
        ],
        CONTENT_MAX_TOKENS,
        fast=True,
        pause_before=0.4,
    )
    content = (data.get("content") or "").strip()
    if not content:
        raise ValueError("Contenu SEO vide.")
    return content, truncated


def _continue_content(
    existing: str,
    *,
    meta: dict,
    keywords: list[str],
    city: str,
    link_block: str,
    words_needed: int,
) -> str:
    tail = existing[-6000:] if len(existing) > 6000 else existing
    user = f"""La page a été COUPÉE. Complète-la.

Titre : {meta.get("title", "")}
Mot-clé : {meta.get("focus_keyword", "")}
Il manque environ {words_needed} mots (FAQ complète, conclusion, sections inachevées).

FIN du HTML déjà publié (continue APRÈS, sans répéter) :
…{tail}

Ajoute UNIQUEMENT la suite dans "append". Minimum {max(300, words_needed)} mots dans append.
{_links_section(link_block)}"""

    data, _ = _call_ai(
        [
            {"role": "system", "content": CONTINUE_SYSTEM},
            {"role": "user", "content": user},
        ],
        CONTINUE_MAX_TOKENS,
        fast=True,
        pause_before=0.5,
    )
    append = (data.get("append") or data.get("content") or "").strip()
    if not append:
        return existing
    if append.startswith(existing[:200]):
        return append
    return existing + append


def _ensure_full_content(
    content: str,
    *,
    meta: dict,
    keywords: list[str],
    city: str,
    link_block: str,
    truncated: bool,
    progress=None,
) -> str:
    report = progress or (lambda *_: None)

    for attempt in range(MAX_CONTINUE_PASSES):
        wc = _count_words(content)
        incomplete = _html_looks_incomplete(content) or truncated
        if wc >= MIN_WORDS * EXPAND_TOLERANCE and not incomplete:
            return content

        need = max(MIN_WORDS - wc, 400)
        report(f"Suite de la rédaction ({wc} mots → objectif {MIN_WORDS})…")
        content = _continue_content(
            content,
            meta=meta,
            keywords=keywords,
            city=city,
            link_block=link_block,
            words_needed=need,
        )
        truncated = False
        wc = _count_words(content)
        if wc >= MIN_WORDS * EXPAND_TOLERANCE and not _html_looks_incomplete(content):
            return content

    return content


def generate_seo_page(
    *,
    topic: str,
    keywords: list[str] | str,
    city: str = "",
    page_type: str = "landing",
    progress=None,
) -> dict:
    """Génère une page SEO FR complète (meta → corps → continuations si tronqué)."""
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

    report("Préparation SEO et maillage interne…")
    catalog = internal_links.build_catalog()
    link_block = internal_links.prompt_block(catalog)

    report("Titres, meta et plan de la page…")
    meta = _generate_meta(topic=topic, keywords=keywords, city=city, page_type=page_type)

    report("Rédaction du contenu (peut prendre 1–2 min)…")
    content, truncated = _generate_content(
        meta=meta,
        keywords=keywords,
        city=city,
        link_block=link_block,
    )

    content = _ensure_full_content(
        content,
        meta=meta,
        keywords=keywords,
        city=city,
        link_block=link_block,
        truncated=truncated,
        progress=report,
    )

    slug = slugify(meta.get("title") or topic)
    word_count = _count_words(content)
    page = {
        "slug": slug,
        "title": meta["title"].strip(),
        "meta_title": (meta.get("meta_title") or meta["title"])[:70].strip(),
        "meta_description": (meta.get("meta_description") or meta.get("excerpt", ""))[:160].strip(),
        "excerpt": (meta.get("excerpt") or meta.get("meta_description", ""))[:160].strip(),
        "focus_keyword": (meta.get("focus_keyword") or keywords[0])[:80],
        "target_keywords": keywords,
        "city": city,
        "page_type": page_type,
        "date": date.today().isoformat(),
        "read_time": _read_time(word_count),
        "word_count": word_count,
        "image_prompt": meta.get("image_prompt", ""),
        "content": content,
        "ai_generated": True,
        "status": "draft",
    }

    report("Maillage interne…")
    page["content"], _ = internal_links.process_content(page["content"], slug, catalog)
    page["word_count"] = _count_words(page["content"])
    page["read_time"] = _read_time(page["word_count"])
    return page


def generate_seo_batch(
    rows: list[dict],
    progress=None,
) -> dict:
    """Génère plusieurs pages SEO (pause anti rate-limit entre chaque)."""
    report = progress or (lambda *_: None)
    pages: list[dict] = []
    errors: list[dict] = []
    total = len(rows)

    for i, row in enumerate(rows, 1):
        topic = (row.get("topic") or "").strip()
        report(f"Page {i}/{total} — {topic[:50]}…")
        try:
            page = generate_seo_page(
                topic=topic,
                keywords=row.get("keywords") or [],
                city=row.get("city") or "",
                page_type=row.get("page_type") or "landing",
                progress=report,
            )
            from admin.image_service import attach_image_to_article

            report(f"Page {i}/{total} — image…")
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
