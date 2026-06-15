"""Maillage interne automatique des articles IA + traçage UTM (invisible).

L'IA insère des liens internes contextuels DIRECTEMENT dans le texte (jamais en
note de bas de page, en liste séparée ni en commentaire HTML). Ce module :

1. construit le CATALOGUE des cibles internes réelles (articles publiés + piliers),
   fourni à l'IA dans le prompt pour qu'elle ne lie QUE des URLs existantes ;
2. POST-TRAITE le HTML généré : retire les liens hallucinés / externes (on garde le
   texte de l'ancre), supprime les autoliens, puis ajoute des paramètres UTM à chaque
   lien interne conservé pour le suivi analytics.

Les UTM sont ensuite retirés de la barre d'adresse côté client (static/js/main.js)
→ INVISIBLES pour l'utilisateur, mais bien comptabilisés (log serveur au GET +
GA4). Le trafic « interne » est exclu du tableau « réseaux sociaux » (admin/db.py)
pour ne pas le fausser.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Nomenclature UTM FIXE des liens internes (cohérence analytics, distincte du social).
UTM_SOURCE = "interne"
UTM_MEDIUM = "maillage-interne"

# Nombre maximal de cibles proposées à l'IA dans le prompt.
MAX_PROMPT_LINKS = 25

_A_TAG = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_HREF = re.compile(r"""href\s*=\s*["']([^"']*)["']""", re.IGNORECASE)


def _slugify_campaign(value: str) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "article"


def build_catalog(exclude_slug: str | None = None) -> list[dict]:
    """Cibles internes RÉELLES : articles publiés (FR) + piliers (pages-hub).

    Imports tardifs pour éviter tout cycle et rester robuste hors contexte app.
    """
    catalog: list[dict] = []

    try:
        from admin.store import get_articles
        for a in get_articles("fr"):
            slug = a.get("slug")
            title = (a.get("title") or "").strip()
            if not slug or not title or slug == exclude_slug:
                continue
            catalog.append({"url": f"/blog/{slug}", "title": title})
    except Exception:
        pass

    try:
        from data import pillars
        for _key, p in pillars.PILLARS.items():
            if p.get("kind") != "hub":
                continue
            slug = p.get("slug")
            title = ((p.get("title") or {}).get("fr") or "").strip()
            if not slug or not title:
                continue
            catalog.append({"url": f"/guide/{slug}", "title": title})
    except Exception:
        pass

    try:
        from admin.store import get_destinations_dict
        for slug, d in get_destinations_dict("fr").items():
            title = (d.get("name") or "").strip()
            if slug and title:
                catalog.append({"url": f"/{slug}", "title": title})
    except Exception:
        pass

    try:
        from data.itineraries import ITINERARIES
        for slug, itin in ITINERARIES.items():
            title = (itin.get("title") or "").strip()
            if slug and title:
                catalog.append({"url": f"/itineraries/{slug}", "title": title})
    except Exception:
        pass

    try:
        from admin.partner_portal_service import list_public_partners
        from admin.partner_seo import profile_type_label

        for page in list_public_partners():
            slug = page.get("slug")
            title = (page.get("title") or "").strip()
            partner = page.get("partner") or {}
            if not slug or not title:
                continue
            ptype = profile_type_label(partner, "fr")
            catalog.append({
                "url": f"/partenaire/{slug}",
                "title": f"{title} ({ptype})",
            })
        catalog.append({
            "url": "/partenaires-vietnam",
            "title": "Partenaires voyage Vietnam — Inside Vietnam Travel",
        })
    except Exception:
        pass

    try:
        from admin.seo_pages_service import get_published_seo_pages
        for page in get_published_seo_pages("fr"):
            slug = page.get("slug")
            title = (page.get("title") or "").strip()
            if slug and title:
                catalog.append({"url": f"/seo/{slug}", "title": title})
    except Exception:
        pass

    # Dédoublonnage par URL.
    seen: set[str] = set()
    out: list[dict] = []
    for item in catalog:
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        out.append(item)
    return out


def prompt_block(catalog: list[dict], limit: int = MAX_PROMPT_LINKS) -> str:
    """Liste « titre → URL » à coller dans le prompt utilisateur."""
    if not catalog:
        return ""
    return "\n".join(f'- {c["title"]} → {c["url"]}' for c in catalog[:limit])


def _known_paths(catalog: list[dict]) -> set[str]:
    return {c["url"].rstrip("/") for c in catalog}


def add_utm(path: str, campaign: str) -> str:
    """Ajoute utm_source/medium/campaign à une URL interne, en préservant sa query."""
    parts = urlparse(path)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["utm_source"] = UTM_SOURCE
    query["utm_medium"] = UTM_MEDIUM
    query["utm_campaign"] = _slugify_campaign(campaign)
    return urlunparse(parts._replace(query=urlencode(query)))


def process_content(html: str, source_slug: str, catalog: list[dict]) -> tuple[str, int]:
    """Valide les <a> générés et ajoute les UTM.

    - lien sans href ou cible inconnue (hallucinée / externe) → on retire la balise
      mais on CONSERVE le texte de l'ancre ;
    - autolien (vers l'article courant) → retiré de la même façon ;
    - lien interne connu → réécrit proprement avec UTM.

    Retourne (html_traité, nombre_de_liens_internes_conservés).
    """
    if not html:
        return html, 0

    known = _known_paths(catalog)
    self_path = (f"/blog/{source_slug}".rstrip("/")) if source_slug else None
    count = 0

    def _repl(m: re.Match) -> str:
        nonlocal count
        attrs, inner = m.group(1), m.group(2)
        href_m = _HREF.search(attrs)
        if not href_m:
            return inner
        path = urlparse(href_m.group(1).strip()).path.rstrip("/")
        if not path or path == self_path or path not in known:
            return inner
        count += 1
        return f'<a href="{add_utm(path, source_slug or "article")}">{inner}</a>'

    return _A_TAG.sub(_repl, html), count
