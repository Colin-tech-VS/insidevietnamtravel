"""Matrice de mots-clés SEO — construction manuelle, IA et filtrage anti-doublon."""

from __future__ import annotations

import itertools
import re
import uuid

from admin import ai_client
from admin.partner_seo_keywords import gsc_top_queries, seed_keywords
from admin.seo_page_suggestions import _existing_titles, _is_duplicate
from data.vietnam_cities import ALL_CITY_VALUES

MAX_MATRIX_ROWS = 24
MAX_BATCH_GENERATE = 12


def parse_axis_lines(text: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for part in (text or "").replace(";", "\n").split("\n"):
        for chunk in part.split(","):
            line = chunk.strip()
            if not line:
                continue
            key = line.lower()
            if key not in seen:
                seen.add(key)
                items.append(line)
    return items[:16]


def _unique_keywords(parts: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        p = (p or "").strip()
        if not p:
            continue
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _topic_from_axes(a: str, b: str, city: str) -> str:
    a, b = a.strip(), b.strip()
    if city and city != "Tout le Vietnam":
        return f"{a.capitalize()} à {city} — {b} (guide Vietnam)"
    return f"{a.capitalize()} au Vietnam — {b}"


def _row_id() -> str:
    return uuid.uuid4().hex[:10]


def build_manual_matrix(
    axis_a: str,
    axis_b: str,
    *,
    city: str = "",
    page_type: str = "landing",
    max_rows: int = MAX_MATRIX_ROWS,
) -> list[dict]:
    """Produit cartésien A×B — chaque ligne = une page SEO avec mix de mots-clés."""
    a_items = parse_axis_lines(axis_a)
    b_items = parse_axis_lines(axis_b)
    if not a_items or not b_items:
        raise ValueError("Renseignez au moins un mot-clé sur chaque axe de la matrice.")

    rows: list[dict] = []
    for a, b in itertools.product(a_items, b_items):
        if len(rows) >= max_rows:
            break
        base_kws = [a, b, f"{a} vietnam", f"{b} vietnam", f"voyage {a}", f"{a} {b}"]
        if city and city != "Tout le Vietnam":
            base_kws.extend([f"{a} {city}", f"{city} {b}", f"guide {city}"])
        rows.append({
            "id": _row_id(),
            "topic": _topic_from_axes(a, b, city),
            "keywords": _unique_keywords(base_kws)[:8],
            "city": city,
            "page_type": page_type,
            "priority": "haute",
            "reason": f"Matrice manuelle : « {a} » × « {b} »",
            "selected": True,
        })
    return filter_matrix_rows(rows)


def filter_matrix_rows(rows: list[dict]) -> list[dict]:
    existing = _existing_titles()
    out: list[dict] = []
    seen_topics: set[str] = set()
    for row in rows:
        topic = (row.get("topic") or "").strip()
        if not topic:
            continue
        key = topic.lower()[:40]
        if key in seen_topics or _is_duplicate(topic, existing):
            row = {**row, "duplicate": True, "selected": False}
        else:
            seen_topics.add(key)
        out.append(row)
    return out


MATRIX_AI_PROMPT = """Tu es stratège SEO pour Inside Vietnam Travel (voyage Vietnam, Français).

Brief éditorial : {brief}
Nombre de lignes : {count}
Ville focus (optionnel) : {city}
Requêtes GSC récentes : {gsc}
Mots-clés seed : {seeds}

Pages SEO déjà en ligne (ne pas dupliquer) :
{existing}

Construis une MATRICE de pages SEO : chaque ligne combine PLUSIEURS mots-clés
complémentaires (cluster sémantique) pour une landing /seo/slug distincte.
Varie les intentions (info, comparatif, FAQ, guide ville, budget, visa…).

JSON uniquement :
{{
  "rows": [
    {{
      "topic": "Titre H1 landing",
      "keywords": ["kw1", "kw2", "kw3", "kw4"],
      "city": "Ville ou Tout le Vietnam",
      "page_type": "landing|guide|comparison|faq",
      "priority": "haute|moyenne",
      "reason": "Pourquoi ce cluster"
    }}
  ]
}}

Villes autorisées : {cities}
"""


def generate_matrix_ai(
    *,
    brief: str = "",
    count: int = 12,
    city: str = "",
    progress=None,
) -> list[dict]:
    """Génère une matrice de pages SEO par IA."""
    ai_client.require_api_key()
    report = progress or (lambda *_: None)
    count = max(4, min(count, MAX_MATRIX_ROWS))

    existing = "\n".join(
        f"- {(r.get('topic') or '')[:80]}"
        for r in []  # placeholder replaced below
    )
    from admin.seo_pages_service import get_published_seo_pages
    existing = "\n".join(
        f"- {p.get('title', '')}"
        for p in get_published_seo_pages()[:25]
    ) or "(aucune)"

    report("Construction de la matrice SEO par IA…")
    prompt = MATRIX_AI_PROMPT.format(
        brief=brief or "Couvrir des clusters SEO voyage Vietnam non encore traités",
        count=count,
        city=city or "variable",
        gsc=", ".join(gsc_top_queries(limit=10)) or "(non connecté)",
        seeds=", ".join(seed_keywords("fr")[:14]),
        existing=existing,
        cities=", ".join(ALL_CITY_VALUES[:16]) + ", …",
    )
    response = ai_client.chat_completion(
        fast=True,
        messages=[
            {"role": "system", "content": "Tu réponds uniquement en JSON valide."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.75,
        max_tokens=2500,
    )
    data = ai_client.parse_json(response.choices[0].message.content)
    rows: list[dict] = []
    for raw in data.get("rows", [])[:count]:
        topic = (raw.get("topic") or "").strip()
        if not topic:
            continue
        kws = raw.get("keywords") or []
        if isinstance(kws, str):
            kws = [k.strip() for k in re.split(r"[,;]", kws) if k.strip()]
        row_city = (raw.get("city") or city or "").strip()
        if row_city and row_city not in ALL_CITY_VALUES:
            row_city = next(
                (c for c in ALL_CITY_VALUES if row_city.lower() in c.lower()),
                city or "Tout le Vietnam",
            )
        rows.append({
            "id": _row_id(),
            "topic": topic,
            "keywords": _unique_keywords([str(k) for k in kws])[:8],
            "city": row_city or city,
            "page_type": raw.get("page_type", "landing"),
            "priority": raw.get("priority", "moyenne"),
            "reason": raw.get("reason", "Cluster IA"),
            "selected": True,
        })
    if len(rows) < 3:
        raise ValueError("Matrice IA incomplète — réessayez avec un brief plus précis.")
    return filter_matrix_rows(rows)


def rows_from_suggestions(suggestions: list[dict]) -> list[dict]:
    """Convertit des propositions en lignes de matrice."""
    rows = []
    for s in suggestions:
        rows.append({
            "id": _row_id(),
            "topic": s.get("topic", ""),
            "keywords": s.get("keywords") or [],
            "city": s.get("city", ""),
            "page_type": s.get("page_type", "landing"),
            "priority": s.get("priority", "moyenne"),
            "reason": s.get("reason", ""),
            "selected": True,
        })
    return filter_matrix_rows(rows)


def clamp_batch_rows(rows: list[dict]) -> list[dict]:
    selected = [r for r in rows if r.get("selected") and not r.get("duplicate")]
    if not selected:
        raise ValueError("Aucune ligne sélectionnée dans la matrice.")
    if len(selected) > MAX_BATCH_GENERATE:
        raise ValueError(f"Maximum {MAX_BATCH_GENERATE} pages par lot — désélectionnez-en.")
    return selected
