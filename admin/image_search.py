"""Recherche d'images pour Linh 🧭 — banques d'images libres, URLs directes.

Pourquoi : pour trouver une image, Linh perdait beaucoup de temps en recherches
web TEXTUELLES (web_search) qui renvoient des pages HTML sans URL d'image
exploitable, et la recherche par mots-clés dépendait entièrement de Pixabay
(clé API obligatoire — sans clé, échec direct). Ici on interroge de BONS sites
où l'image est directement TÉLÉCHARGEABLE, en cascade :

  1) Pixabay (si PIXABAY_API_KEY) — photos libres, URLs CDN directes ;
  2) Openverse (sans clé)        — images sous licence Creative Commons ;
  3) Wikimedia Commons (sans clé) — lieux/monuments très bien couverts ;
  4) DuckDuckGo Images via ddgs (sans clé) — dernier recours, large couverture.

La PREMIÈRE source qui répond avec des résultats suffit (une seule requête HTTP
dans le cas nominal) ; chaque source est bornée par une échéance murale courte
pour ne jamais cumuler les lenteurs. Les URLs renvoyées sont directes : le
téléchargement + l'optimisation WebP + le remplacement se font ensuite via
image_service (set_remote_image_for_article/destination).
"""

from __future__ import annotations

import re

import requests

CONNECT_TIMEOUT = 5
READ_TIMEOUT = 10
# Échéance murale par source (réseau lent/filtré : on passe à la source suivante).
PROVIDER_DEADLINE = 8
MAX_QUERY_LEN = 200
USER_AGENT = "InsideVietnamTravel/1.0 (https://insidevietnamtravel.com)"

OPENVERSE_API_URL = "https://api.openverse.org/v1/images/"
WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"

# Largeur minimale souhaitée pour une bannière 1200×675 ; en dessous, l'image
# upscalée est floue. On garde quand même les petites si rien d'autre.
MIN_BANNER_WIDTH = 1000


def _pixabay_provider(query: str, max_results: int) -> list[dict]:
    """Photos libres Pixabay (clé gratuite requise — sinon liste vide, repli suivant)."""
    from admin.image_service import (
        PIXABAY_API_URL,
        PIXABAY_CONNECT_TIMEOUT,
        PIXABAY_READ_TIMEOUT,
        _pixabay_api_key,
    )

    key = _pixabay_api_key()
    if not key:
        return []
    resp = requests.get(
        PIXABAY_API_URL,
        params={
            "key": key, "q": query, "image_type": "photo",
            "orientation": "horizontal", "safesearch": "true",
            "per_page": max(3, min(max_results, 20)), "lang": "en",
        },
        timeout=(PIXABAY_CONNECT_TIMEOUT, PIXABAY_READ_TIMEOUT),
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    results = []
    for hit in resp.json().get("hits", []):
        image_url = hit.get("largeImageURL") or hit.get("webformatURL")
        if not image_url:
            continue
        results.append({
            "title": (hit.get("tags") or "Photo Pixabay").strip()[:120],
            "image_url": image_url,
            "thumb_url": hit.get("webformatURL") or image_url,
            "page_url": hit.get("pageURL") or image_url,
            "source": "pixabay",
            "width": int(hit.get("imageWidth") or 0),
            "height": int(hit.get("imageHeight") or 0),
        })
    return results


def _openverse_provider(query: str, max_results: int) -> list[dict]:
    """Openverse (openverse.org) — images Creative Commons, API publique sans clé."""
    resp = requests.get(
        OPENVERSE_API_URL,
        params={
            "q": query,
            "page_size": max(3, min(max_results, 20)),
            "mature": "false",
        },
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    results = []
    for row in resp.json().get("results", []):
        image_url = (row.get("url") or "").strip()
        if not image_url.startswith(("http://", "https://")):
            continue
        results.append({
            "title": (row.get("title") or "Image Openverse").strip()[:120],
            "image_url": image_url,
            "thumb_url": (row.get("thumbnail") or image_url).strip(),
            "page_url": (row.get("foreign_landing_url") or image_url).strip(),
            "source": "openverse",
            "width": int(row.get("width") or 0),
            "height": int(row.get("height") or 0),
        })
    return results


def _wikimedia_provider(query: str, max_results: int) -> list[dict]:
    """Wikimedia Commons — photos de lieux/monuments, API publique sans clé.

    `iiurlwidth=1600` : on récupère l'URL d'une MINIATURE grand format plutôt que
    l'original (souvent > 10 Mo, refusé par le plafond de téléchargement).
    """
    resp = requests.get(
        WIKIMEDIA_API_URL,
        params={
            "action": "query", "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": 6,
            "gsrlimit": max(3, min(max_results, 20)),
            "prop": "imageinfo",
            "iiprop": "url|size",
            "iiurlwidth": 1600,
        },
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        image_url = info.get("thumburl") or info.get("url")
        if not image_url:
            continue
        title = (page.get("title") or "").removeprefix("File:").rsplit(".", 1)[0]
        results.append({
            "title": (title or "Photo Wikimedia Commons").strip()[:120],
            "image_url": image_url,
            "thumb_url": image_url,
            "page_url": info.get("descriptionurl") or image_url,
            "source": "wikimedia",
            "width": int(info.get("thumbwidth") or info.get("width") or 0),
            "height": int(info.get("thumbheight") or info.get("height") or 0),
        })
    return results


def _ddgs_images_provider(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo Images via ddgs (déjà utilisé pour web_search) — dernier recours :
    URLs directes mais hébergées sur des sites quelconques (parfois protégées)."""
    from ddgs import DDGS

    rows = DDGS(timeout=READ_TIMEOUT).images(
        query, region="fr-fr", safesearch="moderate", max_results=max_results
    )
    results = []
    for row in rows or []:
        image_url = (row.get("image") or "").strip()
        if not image_url.startswith(("http://", "https://")):
            continue
        results.append({
            "title": (row.get("title") or "Image").strip()[:120],
            "image_url": image_url,
            "thumb_url": (row.get("thumbnail") or image_url).strip(),
            "page_url": (row.get("url") or image_url).strip(),
            "source": "duckduckgo",
            "width": int(row.get("width") or 0),
            "height": int(row.get("height") or 0),
        })
    return results


# Ordre = fiabilité du téléchargement (CDN dédiés d'abord, scraping ensuite).
_PROVIDERS: tuple[tuple[str, object], ...] = (
    ("pixabay", _pixabay_provider),
    ("openverse", _openverse_provider),
    ("wikimedia", _wikimedia_provider),
    ("duckduckgo", _ddgs_images_provider),
)


def search_images(query: str, max_results: int = 8) -> list[dict]:
    """Cherche des images aux URLs directement téléchargeables.

    Renvoie [{title, image_url, thumb_url, page_url, source, width, height}] —
    sources interrogées en cascade jusqu'à obtenir `max_results` candidates.
    Lève ValueError si aucune source ne répond.
    """
    from admin.image_service import _run_with_deadline

    query = re.sub(r"\s+", " ", (query or "")).strip()[:MAX_QUERY_LEN]
    if len(query) < 2:
        raise ValueError("Mots-clés de recherche d'image vides.")

    results: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []
    for name, provider in _PROVIDERS:
        if len(results) >= max_results:
            break
        try:
            rows = _run_with_deadline(provider, PROVIDER_DEADLINE, query, max_results)
        except Exception as exc:  # noqa: BLE001 — source en panne : on passe à la suivante
            errors.append(f"{name} {type(exc).__name__}: {str(exc)[:80]}")
            continue
        for row in rows:
            url = row.get("image_url")
            if not url or url in seen:
                continue
            seen.add(url)
            results.append(row)
            if len(results) >= max_results:
                break

    if not results:
        raise ValueError(
            "Aucune image trouvée pour « " + query + " »"
            + (" — " + " ; ".join(errors) if errors else "")
        )
    return results


def find_image_url(query: str, seed: int = 0, prefer_small: bool = False) -> str:
    """URL directe d'UNE image pour `query` (remplace l'ancienne recherche Pixabay seule).

    `seed` varie le choix (lots d'images sans doublon) ; `prefer_small` renvoie la
    variante légère (vignettes des points de carte).
    """
    results = search_images(query, max_results=10)
    big = [r for r in results if (r.get("width") or 0) >= MIN_BANNER_WIDTH] or results
    pick = big[seed % len(big)]
    if prefer_small:
        return pick.get("thumb_url") or pick["image_url"]
    return pick["image_url"]


def format_image_results(query: str, results: list[dict]) -> str:
    """Bloc texte injecté dans le prompt de Linh après une recherche d'images."""
    lines = [
        f"Recherche d'images « {query} » — {len(results)} résultat(s), "
        "URLs DIRECTES téléchargeables (champ image_url) :"
    ]
    for i, r in enumerate(results, 1):
        dims = f"{r.get('width') or '?'}×{r.get('height') or '?'}"
        lines.append(f"{i}. {r['title']} — {dims} — source {r['source']}")
        lines.append(f"   image_url: {r['image_url']}")
        if r.get("page_url") and r["page_url"] != r["image_url"]:
            lines.append(f"   page: {r['page_url']}")
    return "\n".join(lines)
