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
import time
import unicodedata
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import requests

GRAPH_VERSION = "v21.0"
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
TIMEOUT = (8, 25)  # (connexion, lecture)

# Délai minimum entre deux publications (anti double-clic / anti-spam Facebook).
PUBLISH_COOLDOWN_S = 60
_last_publish_ts = 0.0

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
    """Erreur Graph API, avec code/sous-code Facebook pour un diagnostic actionnable."""

    def __init__(self, message: str, code: int | None = None, subcode: int | None = None):
        super().__init__(message)
        self.code = code
        self.subcode = subcode


# Codes d'erreur Graph connus → explication + marche à suivre (en français).
# Réf. https://developers.facebook.com/docs/graph-api/guide/error-handling
_ERROR_HELP: dict[int, str] = {
    368: (
        "Facebook a déclenché son blocage anti-spam TEMPORAIRE sur la page ou le compte "
        "(erreur 368). Ce n'est pas lié au nombre de posts envoyés depuis le site : ce blocage "
        "touche souvent la toute première publication via API quand l'app Meta, la page ou le "
        "token sont récents. Que faire : 1) attendez quelques heures (jusqu'à 24 h) avant de "
        "réessayer ; 2) vérifiez « Statut du compte » dans Meta Business Suite "
        "(business.facebook.com) pour lever une éventuelle restriction ; 3) publiez d'abord un "
        "post manuellement depuis Facebook pour « réchauffer » la page ; 4) si votre app Meta "
        "est en mode Développement, vérifiez qu'elle est bien la vôtre et que le token vient "
        "d'un admin de la page."
    ),
    4: "Limite d'appels API de l'application atteinte (erreur 4). Réessayez dans une heure.",
    17: "Limite d'appels API de l'utilisateur atteinte (erreur 17). Réessayez dans une heure.",
    32: "Limite d'appels API de la page atteinte (erreur 32). Réessayez dans une heure.",
    613: "Limite de débit API atteinte (erreur 613). Réessayez dans une heure.",
    190: (
        "Token d'accès invalide ou expiré (erreur 190). Regénérez un Page Access Token "
        "longue durée et enregistrez-le dans la configuration ci-dessus."
    ),
    200: (
        "Permission manquante (erreur 200) : le token doit avoir la permission "
        "pages_manage_posts et provenir d'un admin de la page."
    ),
    100: "Paramètre invalide (erreur 100) : vérifiez l'ID de page et le lien/l'image du post.",
    506: "Publication en double détectée par Facebook (erreur 506) : modifiez le texte avant de republier.",
}


def friendly_error(exc: Exception) -> str:
    """Message clair pour l'UI : explication connue si code identifié, sinon message brut."""
    if isinstance(exc, FacebookError) and exc.code in _ERROR_HELP:
        return _ERROR_HELP[exc.code]
    return str(exc)


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
        raise FacebookError(msg, code=err.get("code"), subcode=err.get("error_subcode"))
    return payload


def _check_cooldown() -> None:
    """Empêche deux publications rapprochées (double-clic, rafale) qui nourrissent
    le détecteur de spam de Facebook. Garde-fou local au processus, best-effort."""
    global _last_publish_ts
    elapsed = time.monotonic() - _last_publish_ts
    if _last_publish_ts and elapsed < PUBLISH_COOLDOWN_S:
        wait = int(PUBLISH_COOLDOWN_S - elapsed) + 1
        raise FacebookError(
            f"Publication trop rapprochée de la précédente : patientez {wait} s "
            "(protection contre les doublons et le blocage anti-spam Facebook)."
        )


def test_connection() -> dict:
    """Vérifie le token/page : renvoie le nom de la page (+ abonnés si permission).

    On tente d'abord avec `fan_count` (nécessite pages_read_engagement) ; si Facebook
    refuse faute de cette permission, on retombe sur `name,link` seuls — la connexion
    et la PUBLICATION (pages_manage_posts) restent valides sans pages_read_engagement.
    """
    token, page_id = get_token(), get_page_id()
    if not (token and page_id):
        raise FacebookError("Renseignez l'ID de page et le token d'accès.")

    def _fetch(fields: str) -> requests.Response:
        try:
            return requests.get(
                f"{GRAPH}/{page_id}",
                params={"fields": fields, "access_token": token},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            raise FacebookError(f"Connexion à Facebook impossible : {exc}") from exc

    resp = _fetch("name,fan_count,link")
    payload = resp.json() if resp.content else {}
    if resp.status_code >= 400 or "error" in payload:
        # Probable manque de pages_read_engagement → on réessaie sans fan_count.
        resp = _fetch("name,link")
    return _handle(resp)


def publish_link(message: str, link: str) -> dict:
    """Publie un post avec lien (Facebook génère l'aperçu OG de la page)."""
    global _last_publish_ts
    _check_cooldown()
    result = _post("feed", {"message": message, "link": link})
    _last_publish_ts = time.monotonic()
    return result


def publish_photo(caption: str, image_url: str) -> dict:
    """Publie une photo (grande image) avec légende. image_url doit être public."""
    global _last_publish_ts
    _check_cooldown()
    result = _post("photos", {"caption": caption, "url": image_url, "published": "true"})
    _last_publish_ts = time.monotonic()
    return result


def post_permalink(result: dict) -> str:
    """URL du post publié, à partir de la réponse Graph (id = '<page>_<post>')."""
    post_id = result.get("post_id") or result.get("id", "")
    if "_" in post_id:
        page, pid = post_id.split("_", 1)
        return f"https://www.facebook.com/{page}/posts/{pid}"
    return f"https://www.facebook.com/{post_id}" if post_id else ""
