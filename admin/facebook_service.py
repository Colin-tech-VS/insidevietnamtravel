"""Publication Facebook depuis l'admin (Graph API) + traçage UTM.

Deux types de publication :
- LIEN  : `POST /{page-id}/feed` avec message + link → Facebook récupère l'aperçu OG
          de la page (titre, description, image og:image). Utilisé pour publier une
          page existante du site.
- PHOTO : `POST /{page-id}/photos` avec une image (url) + caption → grande image dans
          le fil. Utilisé pour du contenu nouveau (image obligatoire).

Identifiants (Page ID + Page Access Token longue durée) : lus d'abord dans les réglages
admin (table app_kv / Supabase), sinon dans les variables d'env FACEBOOK_PAGE_ID /
FACEBOOK_PAGE_ACCESS_TOKEN. Le token n'est JAMAIS renvoyé en clair au front (masqué).
"""

from __future__ import annotations

import os
import re
import unicodedata
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import requests

GRAPH_VERSION = "v21.0"
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
TIMEOUT = (8, 25)  # (connexion, lecture)

# Nomenclature UTM FIXE pour TOUT lien publié sur Facebook (cohérence analytics).
UTM_SOURCE = "facebook"
UTM_MEDIUM = "social"


# ── Configuration (réglages admin > variables d'env) ──────────────────────

def _settings() -> dict:
    try:
        from admin.store import get_settings
        return get_settings()
    except Exception:
        return {}


def get_page_id() -> str:
    return (_settings().get("facebook_page_id") or os.environ.get("FACEBOOK_PAGE_ID", "")).strip()


def get_token() -> str:
    return (_settings().get("facebook_page_token") or
            os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "")).strip()


def is_configured() -> bool:
    return bool(get_page_id() and get_token())


def save_config(page_id: str, token: str) -> None:
    """Enregistre Page ID et token. Token vide => on conserve l'existant (champ masqué)."""
    from admin.store import save_settings
    data = {"facebook_page_id": (page_id or "").strip()}
    token = (token or "").strip()
    if token and not _is_masked(token):
        data["facebook_page_token"] = token
    save_settings(data)


def _is_masked(token: str) -> bool:
    return bool(re.fullmatch(r"[•*]{3,}\d{0,4}", token.strip()))


def masked_token() -> str:
    """Aperçu masqué du token pour l'UI (jamais le token complet)."""
    tok = get_token()
    if not tok:
        return ""
    return "••••••••" + tok[-4:]


# ── UTM ───────────────────────────────────────────────────────────────────

def sanitize_campaign(value: str) -> str:
    """Normalise un nom de campagne : minuscules, tirets, sans accents/diacritiques."""
    value = (value or "").lower().strip()
    value = value.replace("đ", "d")  # lettre vietnamienne (non décomposée par NFKD)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "fb-post"


def add_utm(url: str, campaign: str, content: str | None = None) -> str:
    """Ajoute utm_source/medium/campaign (+ content) à une URL, en préservant sa query."""
    if not url:
        return url
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["utm_source"] = UTM_SOURCE
    query["utm_medium"] = UTM_MEDIUM
    query["utm_campaign"] = sanitize_campaign(campaign)
    if content:
        query["utm_content"] = sanitize_campaign(content)
    return urlunparse(parts._replace(query=urlencode(query)))


# ── Graph API ─────────────────────────────────────────────────────────────

class FacebookError(RuntimeError):
    pass


def _post(path: str, data: dict) -> dict:
    token = get_token()
    page_id = get_page_id()
    if not (token and page_id):
        raise FacebookError("Facebook non configuré : renseignez l'ID de page et le token.")
    data = {**data, "access_token": token}
    try:
        resp = requests.post(f"{GRAPH}/{page_id}/{path}", data=data, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise FacebookError(f"Connexion à Facebook impossible : {exc}") from exc
    return _handle(resp)


def _handle(resp: requests.Response) -> dict:
    try:
        payload = resp.json()
    except ValueError:
        payload = {}
    if resp.status_code >= 400 or "error" in payload:
        err = payload.get("error", {})
        msg = err.get("message") or f"Erreur Facebook (HTTP {resp.status_code})"
        raise FacebookError(msg)
    return payload


def test_connection() -> dict:
    """Vérifie le token/page : renvoie le nom de la page et le nb d'abonnés."""
    token, page_id = get_token(), get_page_id()
    if not (token and page_id):
        raise FacebookError("Renseignez l'ID de page et le token d'accès.")
    try:
        resp = requests.get(
            f"{GRAPH}/{page_id}",
            params={"fields": "name,fan_count,link", "access_token": token},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise FacebookError(f"Connexion à Facebook impossible : {exc}") from exc
    return _handle(resp)


def publish_link(message: str, link: str) -> dict:
    """Publie un post avec lien (Facebook génère l'aperçu OG de la page)."""
    return _post("feed", {"message": message, "link": link})


def publish_photo(caption: str, image_url: str) -> dict:
    """Publie une photo (grande image) avec légende. image_url doit être public."""
    return _post("photos", {"caption": caption, "url": image_url, "published": "true"})


def post_permalink(result: dict) -> str:
    """URL du post publié, à partir de la réponse Graph (id = '<page>_<post>')."""
    post_id = result.get("post_id") or result.get("id", "")
    if "_" in post_id:
        page, pid = post_id.split("_", 1)
        return f"https://www.facebook.com/{page}/posts/{pid}"
    return f"https://www.facebook.com/{post_id}" if post_id else ""
