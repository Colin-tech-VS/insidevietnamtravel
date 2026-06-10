"""Recherche web pour Linh 🧭 — bibliothèque ddgs, sans clé API.

Pourquoi ddgs : DuckDuckGo bloque désormais le scraping direct de ses endpoints
HTML/lite (HTTP 202 + page anti-bot), ce qui rendait la recherche de Linh
inutilisable. La bibliothèque ddgs est maintenue précisément pour contourner
cela (anti-bot géré, bascule automatique entre plusieurs moteurs). L'ancien
scraping requests des endpoints html/lite reste en DERNIER repli au cas où
ddgs serait indisponible (import impossible, incident…).

Utilisé par l'outil `web_search` de Linh : la recherche est exécutée côté
serveur, puis les résultats sont réinjectés dans un second appel IA qui rédige
la réponse finale en citant ses sources.
"""

from __future__ import annotations

import html as html_lib
import re
import urllib.parse

import requests

SEARCH_URL = "https://html.duckduckgo.com/html/"
LITE_URL = "https://lite.duckduckgo.com/lite/"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 20
MAX_QUERY_LEN = 200
MAX_SNIPPET_LEN = 300


def _strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment or "")
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


def _clean_url(href: str) -> str:
    """Décode les liens de redirection DuckDuckGo (//duckduckgo.com/l/?uddg=…)."""
    href = html_lib.unescape(href or "")
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = urllib.parse.parse_qs(parsed.query).get("uddg", [""])[0]
        if target:
            return target
    return href


def _search_ddgs(query: str, max_results: int) -> list[dict]:
    """Moteur principal : ddgs (anti-bot géré, plusieurs moteurs en interne)."""
    from ddgs import DDGS

    rows = DDGS(timeout=READ_TIMEOUT).text(
        query, region="fr-fr", safesearch="moderate", max_results=max_results
    )
    results: list[dict] = []
    for row in rows or []:
        url = (row.get("href") or row.get("url") or "").strip()
        title = _strip_tags(row.get("title") or "")
        if not url.startswith("http") or not title:
            continue
        snippet = _strip_tags(row.get("body") or row.get("snippet") or "")
        results.append({"title": title, "url": url, "snippet": snippet[:MAX_SNIPPET_LEN]})
    return results[:max_results]


def _parse_html_results(page: str, max_results: int) -> list[dict]:
    titles = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S
    )
    snippets = re.findall(
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', page, re.S
    )
    results: list[dict] = []
    for idx, (href, title_html) in enumerate(titles[:max_results]):
        url = _clean_url(href)
        title = _strip_tags(title_html)
        if not url.startswith("http") or not title:
            continue
        snippet = _strip_tags(snippets[idx]) if idx < len(snippets) else ""
        results.append({"title": title, "url": url, "snippet": snippet[:MAX_SNIPPET_LEN]})
    return results


def _parse_lite_results(page: str, max_results: int) -> list[dict]:
    links = re.findall(
        r'<a[^>]+rel="nofollow"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S
    )
    snippets = re.findall(r'<td[^>]+class="result-snippet"[^>]*>(.*?)</td>', page, re.S)
    results: list[dict] = []
    for idx, (href, title_html) in enumerate(links[:max_results]):
        url = _clean_url(href)
        title = _strip_tags(title_html)
        if not url.startswith("http") or not title:
            continue
        snippet = _strip_tags(snippets[idx]) if idx < len(snippets) else ""
        results.append({"title": title, "url": url, "snippet": snippet[:MAX_SNIPPET_LEN]})
    return results


def search_web(query: str, max_results: int = 6) -> list[dict]:
    """Recherche web → [{title, url, snippet}]. Lève ValueError si tout échoue."""
    query = re.sub(r"\s+", " ", (query or "")).strip()[:MAX_QUERY_LEN]
    if len(query) < 2:
        raise ValueError("Requête de recherche vide.")

    errors: list[str] = []

    try:
        results = _search_ddgs(query, max_results)
        if results:
            return results
        errors.append("aucun résultat (ddgs)")
    except Exception as exc:  # noqa: BLE001 — on tente le scraping direct en repli
        errors.append(f"ddgs {type(exc).__name__}: {str(exc)[:120]}")

    headers = {"User-Agent": USER_AGENT, "Accept-Language": "fr,en;q=0.8"}

    try:
        resp = requests.post(
            SEARCH_URL, data={"q": query}, headers=headers,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        resp.raise_for_status()
        results = _parse_html_results(resp.text, max_results)
        if results:
            return results
        errors.append("aucun résultat (endpoint html)")
    except Exception as exc:  # noqa: BLE001 — on tente l'endpoint lite en repli
        errors.append(f"{type(exc).__name__}: {str(exc)[:120]}")

    try:
        resp = requests.get(
            LITE_URL, params={"q": query}, headers=headers,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        resp.raise_for_status()
        results = _parse_lite_results(resp.text, max_results)
        if results:
            return results
        errors.append("aucun résultat (endpoint lite)")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{type(exc).__name__}: {str(exc)[:120]}")

    raise ValueError(
        "Recherche web indisponible pour « " + query + " » — " + " ; ".join(errors)
    )


def format_results(query: str, results: list[dict]) -> str:
    """Bloc texte injecté dans le prompt de Linh après une recherche."""
    lines = [f"Recherche web « {query} » — {len(results)} résultat(s) :"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']} — {r['url']}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet']}")
    return "\n".join(lines)
