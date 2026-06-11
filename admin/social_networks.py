"""Réseaux sociaux voyageurs (hors Facebook) — registre, connexion et publication API.

Chaque réseau du registre `NETWORKS` décrit :
- où y trouver des voyageurs (texte affiché dans l'admin) ;
- les champs de connexion à enregistrer (réglages app_kv, secrets masqués) ;
- les étapes pour obtenir les identifiants (« comment connecter & publier ») ;
- une fonction de test et une fonction de publication via l'API officielle.

Réseaux publiables depuis le composer : Telegram, Pinterest, Reddit, X (Twitter),
Threads, Instagram. TikTok est listé à titre informatif (API soumise à audit).
Le suivi UTM suit la même nomenclature que Facebook avec utm_source = clé du réseau.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets as _secrets
import time
from urllib.parse import quote, urlencode, urlparse, urlunparse, parse_qsl

import requests

from admin.facebook_service import sanitize_campaign

TIMEOUT = (8, 25)
USER_AGENT = "InsideVietnamTravel/1.0 (admin publisher)"

# Délai minimum entre deux publications sur un même réseau (anti double-clic).
PUBLISH_COOLDOWN_S = 30
_last_publish: dict[str, float] = {}


class SocialPublishError(RuntimeError):
    """Erreur de connexion/publication avec message actionnable pour l'UI."""


# ── Registre des réseaux ──────────────────────────────────────────────────
# specialized : audience voyage particulièrement qualifiée.
# needs_image : une image est obligatoire pour publier.
# publishable : publication via le composer possible (sinon fiche info seule).

NETWORKS: list[dict] = [
    {
        "key": "facebook",
        "name": "Facebook",
        "icon": "📘",
        "color": "#1877F2",
        "publishable": True,
        "needs_image": False,
        "specialized": False,
        "managed_elsewhere": True,  # carte de connexion dédiée existante
        "fields": [],
        "audience": "Groupes voyage Vietnam très actifs ; votre page existante.",
        "connect_steps": [],
        "docs_url": "https://developers.facebook.com/docs/pages-api/",
    },
    {
        "key": "pinterest",
        "name": "Pinterest",
        "icon": "📌",
        "color": "#E60023",
        "publishable": True,
        "needs_image": True,
        "specialized": True,
        "fields": [
            {"key": "pinterest_access_token", "label": "Access token", "secret": True,
             "hint": "OAuth, scopes pins:write + boards:read"},
            {"key": "pinterest_board_id", "label": "ID du tableau (board)", "secret": False,
             "hint": "tableau où épingler, ex. 1234567890"},
        ],
        "audience": (
            "Le réseau n°1 de la PLANIFICATION de voyage : on y prépare activement son "
            "itinéraire (« Vietnam 3 semaines », « que faire à Hanoï »…). Une épingle "
            "continue d'amener du trafic pendant des mois — idéal pour vos guides, "
            "itinéraires et articles avec une belle image verticale."
        ),
        "connect_steps": [
            "Créez un compte Pinterest Business (gratuit) et un tableau « Vietnam ».",
            "Sur developers.pinterest.com, créez une app puis demandez l'accès Standard "
            "(une démo vidéo du flux OAuth + création d'épingle est exigée ; l'accès Trial "
            "ne permet pas d'écrire).",
            "Générez un access token OAuth avec les scopes pins:write et boards:read.",
            "Récupérez l'ID du tableau (dans l'URL du board ou via GET /v5/boards).",
            "Collez token + ID de tableau ci-dessous, puis « Tester ». Image obligatoire "
            "pour chaque épingle (le format vertical 1000×1500 fonctionne le mieux).",
        ],
        "docs_url": "https://developers.pinterest.com/docs/api/v5/",
    },
    {
        "key": "reddit",
        "name": "Reddit",
        "icon": "🤖",
        "color": "#FF4500",
        "publishable": True,
        "needs_image": False,
        "specialized": True,
        "fields": [
            {"key": "reddit_client_id", "label": "Client ID", "secret": False,
             "hint": "app « script » sur reddit.com/prefs/apps"},
            {"key": "reddit_client_secret", "label": "Client secret", "secret": True, "hint": ""},
            {"key": "reddit_username", "label": "Nom d'utilisateur", "secret": False, "hint": ""},
            {"key": "reddit_password", "label": "Mot de passe", "secret": True,
             "hint": "compte SANS 2FA pour l'API script"},
            {"key": "reddit_default_sub", "label": "Subreddit par défaut", "secret": False,
             "hint": "ex. VietnamTravel (sans r/)"},
        ],
        "audience": (
            "LE réseau spécialisé : r/VietnamTravel (100 % conseils Vietnam), r/travel, "
            "r/solotravel, r/backpacking… Des voyageurs qui préparent CONCRÈTEMENT leur "
            "voyage et cherchent des réponses détaillées. ⚠ L'autopromo y est très "
            "encadrée : répondez d'abord aux questions, gardez ~1 lien promo pour 10 "
            "contributions, et lisez les règles de chaque subreddit."
        ),
        "connect_steps": [
            "Créez un compte Reddit et participez d'abord (karma) : un compte neuf qui "
            "poste des liens est filtré automatiquement.",
            "Sur reddit.com/prefs/apps, créez une app de type « script » → notez le "
            "client ID (sous le nom) et le client secret.",
            "Renseignez aussi le nom d'utilisateur et le mot de passe du compte "
            "(authentification « password grant » des apps script).",
            "Choisissez un subreddit par défaut (ex. VietnamTravel) — modifiable à "
            "chaque publication dans le composer.",
            "Respectez les règles : certains subreddits exigent un flair ou interdisent "
            "les liens — le message d'erreur de Reddit est alors renvoyé tel quel.",
        ],
        "docs_url": "https://www.reddit.com/dev/api/",
    },
    {
        "key": "telegram",
        "name": "Telegram",
        "icon": "✈️",
        "color": "#26A5E4",
        "publishable": True,
        "needs_image": False,
        "specialized": True,
        "fields": [
            {"key": "telegram_bot_token", "label": "Token du bot", "secret": True,
             "hint": "créé via @BotFather"},
            {"key": "telegram_chat_id", "label": "Canal (chat ID)", "secret": False,
             "hint": "ex. @insidevietnamtravel"},
        ],
        "audience": (
            "Très utilisé par les voyageurs en Asie du Sud-Est et les expats : canaux et "
            "groupes « Vietnam Travel », « Backpacking Vietnam », « Expats in Hanoi »… "
            "Créez votre canal, publiez-y vos guides automatiquement, puis partagez les "
            "posts dans les groupes spécialisés. API 100 % gratuite et sans validation."
        ),
        "connect_steps": [
            "Dans Telegram, parlez à @BotFather → /newbot → récupérez le token du bot.",
            "Créez un canal public (ex. @insidevietnamtravel) et ajoutez le bot comme "
            "administrateur avec le droit « Publier des messages ».",
            "Renseignez le token et le @nom_du_canal ci-dessous, puis « Tester ».",
            "Astuce : rejoignez les groupes voyage Vietnam existants et partagez-y vos "
            "posts du canal (manuel — les groupes n'acceptent pas les bots inconnus).",
        ],
        "docs_url": "https://core.telegram.org/bots/api",
    },
    {
        "key": "x",
        "name": "X (Twitter)",
        "icon": "🐦",
        "color": "#0F1419",
        "publishable": True,
        "needs_image": False,
        "specialized": False,
        "fields": [
            {"key": "x_api_key", "label": "API Key (consumer)", "secret": False, "hint": ""},
            {"key": "x_api_secret", "label": "API Secret", "secret": True, "hint": ""},
            {"key": "x_access_token", "label": "Access Token", "secret": False,
             "hint": "du compte, avec Read & Write"},
            {"key": "x_access_secret", "label": "Access Token Secret", "secret": True, "hint": ""},
        ],
        "audience": (
            "Questions voyage en temps réel et communautés #travel actives ; bon canal "
            "pour les conseils rapides (visa, météo, actualité Vietnam) et pour répondre "
            "aux voyageurs qui demandent des recommandations. Offre API gratuite : "
            "~500 posts/mois (suffisant pour 1-2 posts/jour)."
        ),
        "connect_steps": [
            "Sur developer.x.com, créez un compte développeur (offre Free) puis un "
            "projet + une app.",
            "Dans l'app : User authentication settings → activez Read and Write.",
            "Dans « Keys and tokens », générez API Key/Secret (consumer) ET Access "
            "Token/Secret du compte — 4 valeurs au total.",
            "Collez les 4 clés ci-dessous puis « Tester ». Les posts sont limités à "
            "280 caractères (le lien compte pour 23).",
        ],
        "docs_url": "https://docs.x.com/x-api/posts/create-post",
    },
    {
        "key": "threads",
        "name": "Threads",
        "icon": "🧵",
        "color": "#000000",
        "publishable": True,
        "needs_image": False,
        "specialized": False,
        "fields": [
            {"key": "threads_user_id", "label": "ID utilisateur Threads", "secret": False, "hint": ""},
            {"key": "threads_access_token", "label": "Access token", "secret": True,
             "hint": "scopes threads_basic + threads_content_publish"},
        ],
        "audience": (
            "Le « Twitter » de Meta : conversations voyage en plein essor et bonne portée "
            "organique pour les nouveaux comptes. Connexion rapide si vous avez déjà un "
            "compte Instagram — même app Meta que Facebook/Instagram."
        ),
        "connect_steps": [
            "Créez un compte Threads (lié à votre compte Instagram).",
            "Dans votre app Meta (developers.facebook.com), ajoutez le produit "
            "« Threads API » et le cas d'usage de publication.",
            "Générez un access token utilisateur avec les scopes threads_basic et "
            "threads_content_publish (token longue durée conseillé : 60 jours, "
            "renouvelable).",
            "Récupérez votre ID utilisateur Threads (GET /me via l'API) et collez les "
            "deux valeurs ci-dessous.",
        ],
        "docs_url": "https://developers.facebook.com/docs/threads/",
    },
    {
        "key": "instagram",
        "name": "Instagram",
        "icon": "📸",
        "color": "#E1306C",
        "publishable": True,
        "needs_image": True,
        "specialized": False,
        "fields": [
            {"key": "instagram_user_id", "label": "ID du compte IG", "secret": False,
             "hint": "compte professionnel lié à la page FB"},
            {"key": "instagram_access_token", "label": "Access token", "secret": True,
             "hint": "scope instagram_content_publish"},
        ],
        "audience": (
            "Inspiration voyage par l'image : les hashtags #vietnamtravel et "
            "#voyagevietnam touchent des voyageurs en phase de rêve et de décision. "
            "⚠ Les liens ne sont PAS cliquables dans les légendes — l'appel à l'action "
            "renvoie vers le « lien en bio ». Image obligatoire (format 4:5 ou carré)."
        ),
        "connect_steps": [
            "Passez votre compte Instagram en compte PROFESSIONNEL et liez-le à votre "
            "page Facebook (Meta Business Suite).",
            "Dans votre app Meta, ajoutez les permissions instagram_basic et "
            "instagram_content_publish.",
            "Générez un token longue durée (le même flux que pour la page Facebook) et "
            "récupérez l'ID du compte IG : GET /{page-id}?fields=instagram_business_account.",
            "Collez l'ID et le token ci-dessous. Limite Meta : 50 publications API / 24 h.",
        ],
        "docs_url": "https://developers.facebook.com/docs/instagram-platform/content-publishing",
    },
    {
        "key": "tiktok",
        "name": "TikTok",
        "icon": "🎵",
        "color": "#161823",
        "publishable": False,
        "needs_image": False,
        "specialized": False,
        "fields": [],
        "audience": (
            "Moteur de découverte voyage des 18-34 ans : « vietnam itinerary », "
            "« vietnam food »… y sont des recherches massives. L'API de publication "
            "(Content Posting API) existe mais exige un AUDIT TikTok de 2 à 4 semaines ; "
            "sans audit, les posts API restent privés (SELF_ONLY). En attendant : "
            "publiez manuellement vos vidéos courtes (les guides s'y prêtent très bien)."
        ),
        "connect_steps": [
            "Créez une app sur developers.tiktok.com et ajoutez la Content Posting API.",
            "Soumettez l'app à l'audit TikTok (démo vidéo OAuth + politique de "
            "confidentialité requises ; comptez 2-4 semaines et plusieurs allers-retours).",
            "Une fois l'audit validé, revenez ici : la connexion pourra être ajoutée "
            "comme pour les autres réseaux.",
        ],
        "docs_url": "https://developers.tiktok.com/doc/content-posting-api-get-started",
    },
]

NETWORK_KEYS = {n["key"]: n for n in NETWORKS}


# ── Réglages (app_kv, mêmes conventions que facebook_service) ─────────────

def _settings() -> dict:
    try:
        from admin.store import get_settings
        return get_settings()
    except Exception:
        return {}


def _is_masked(value: str) -> bool:
    return bool(value) and set(value.strip()) <= set("•*0123456789") and value.strip().startswith(("•", "*"))


def _masked(value: str) -> str:
    return "••••••••" + value[-4:] if value else ""


def get_field(field_key: str) -> str:
    return str(_settings().get(field_key) or "").strip()


def is_network_configured(net_key: str) -> bool:
    net = NETWORK_KEYS.get(net_key)
    if not net:
        return False
    if net_key == "facebook":
        from admin import facebook_service as fb
        return fb.is_configured()
    fields = net.get("fields") or []
    return bool(fields) and all(get_field(f["key"]) for f in fields if f["key"] != "reddit_default_sub")


def save_network_config(net_key: str, form) -> None:
    """Enregistre les champs du réseau ; un secret vide ou masqué conserve l'existant."""
    from admin.store import save_settings
    net = NETWORK_KEYS.get(net_key)
    if not net:
        raise SocialPublishError(f"Réseau inconnu : {net_key}")
    data: dict = {}
    for f in net.get("fields") or []:
        value = (form.get(f["key"]) or "").strip()
        if f.get("secret") and (not value or _is_masked(value)):
            continue  # champ masqué laissé vide → on garde le secret enregistré
        data[f["key"]] = value
    if data:
        save_settings(data)


def network_status() -> list[dict]:
    """Vue du registre pour l'admin : configuré ?, champs avec valeur/masque."""
    out = []
    for net in NETWORKS:
        fields = []
        for f in net.get("fields") or []:
            value = get_field(f["key"])
            fields.append({
                **f,
                "value": "" if f.get("secret") else value,
                "masked": _masked(value) if f.get("secret") else "",
            })
        out.append({
            **{k: net[k] for k in ("key", "name", "icon", "color", "publishable",
                                   "needs_image", "specialized", "audience",
                                   "connect_steps", "docs_url")},
            "managed_elsewhere": net.get("managed_elsewhere", False),
            "configured": is_network_configured(net["key"]),
            "fields": fields,
        })
    return out


# ── UTM (utm_source = clé du réseau, même nomenclature que Facebook) ──────

def add_utm(url: str, campaign: str, source: str) -> str:
    if not url:
        return url
    if source == "facebook":
        from admin import facebook_service as fb
        return fb.add_utm(url, campaign)
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["utm_source"] = source
    query["utm_medium"] = "social"
    query["utm_campaign"] = sanitize_campaign(campaign)
    return urlunparse(parts._replace(query=urlencode(query)))


# ── Helpers HTTP ──────────────────────────────────────────────────────────

def _request(method: str, url: str, *, label: str, **kwargs) -> dict:
    kwargs.setdefault("timeout", TIMEOUT)
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", USER_AGENT)
    try:
        resp = requests.request(method, url, headers=headers, **kwargs)
    except requests.RequestException as exc:
        raise SocialPublishError(f"Connexion à {label} impossible : {exc}") from exc
    try:
        payload = resp.json()
    except ValueError:
        payload = {}
    if resp.status_code >= 400:
        detail = (
            (payload.get("error") or {}).get("message") if isinstance(payload.get("error"), dict)
            else payload.get("error")
        ) or payload.get("message") or payload.get("detail") or resp.text[:300]
        raise SocialPublishError(f"Erreur {label} (HTTP {resp.status_code}) : {detail}")
    return payload


def _check_cooldown(net_key: str) -> None:
    elapsed = time.monotonic() - _last_publish.get(net_key, 0.0)
    if _last_publish.get(net_key) and elapsed < PUBLISH_COOLDOWN_S:
        wait = int(PUBLISH_COOLDOWN_S - elapsed) + 1
        raise SocialPublishError(
            f"Publication trop rapprochée de la précédente sur ce réseau : patientez {wait} s."
        )


def _mark_published(net_key: str) -> None:
    _last_publish[net_key] = time.monotonic()


def _first_line(message: str, limit: int) -> str:
    line = (message or "").strip().splitlines()[0] if (message or "").strip() else ""
    return line[:limit].strip() or "Inside Vietnam Travel"


# ── Telegram ──────────────────────────────────────────────────────────────

def _telegram_api(method: str, data: dict) -> dict:
    token = get_field("telegram_bot_token")
    payload = _request("POST", f"https://api.telegram.org/bot{token}/{method}",
                       label="Telegram", data=data)
    if not payload.get("ok"):
        raise SocialPublishError(f"Erreur Telegram : {payload.get('description', 'réponse inattendue')}")
    return payload.get("result") or {}


def _telegram_test() -> str:
    chat = _telegram_api("getChat", {"chat_id": get_field("telegram_chat_id")})
    return f"canal « {chat.get('title') or chat.get('username', '?')} »"


def _telegram_publish(message: str, link: str, image_url: str) -> str:
    chat_id = get_field("telegram_chat_id")
    text = f"{message}\n\n👉 {link}" if link else message
    if image_url:
        result = _telegram_api("sendPhoto", {"chat_id": chat_id, "photo": image_url,
                                             "caption": text[:1024]})
    else:
        result = _telegram_api("sendMessage", {"chat_id": chat_id, "text": text[:4096]})
    message_id = result.get("message_id")
    username = (result.get("chat") or {}).get("username")
    return f"https://t.me/{username}/{message_id}" if username and message_id else ""


# ── Pinterest ─────────────────────────────────────────────────────────────

def _pinterest_headers() -> dict:
    return {"Authorization": f"Bearer {get_field('pinterest_access_token')}"}


def _pinterest_test() -> str:
    payload = _request("GET", "https://api.pinterest.com/v5/user_account",
                       label="Pinterest", headers=_pinterest_headers())
    return f"compte @{payload.get('username', '?')}"


def _pinterest_publish(message: str, link: str, image_url: str) -> str:
    if not image_url:
        raise SocialPublishError("Pinterest exige une image pour chaque épingle.")
    body = {
        "board_id": get_field("pinterest_board_id"),
        "title": _first_line(message, 100),
        "description": (message or "")[:800],
        "media_source": {"source_type": "image_url", "url": image_url},
    }
    if link:
        body["link"] = link
    payload = _request("POST", "https://api.pinterest.com/v5/pins", label="Pinterest",
                       headers={**_pinterest_headers(), "Content-Type": "application/json"},
                       json=body)
    pin_id = payload.get("id", "")
    return f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else ""


# ── Reddit ────────────────────────────────────────────────────────────────

def _reddit_token() -> str:
    payload = _request(
        "POST", "https://www.reddit.com/api/v1/access_token", label="Reddit",
        auth=(get_field("reddit_client_id"), get_field("reddit_client_secret")),
        data={"grant_type": "password", "username": get_field("reddit_username"),
              "password": get_field("reddit_password")},
    )
    token = payload.get("access_token")
    if not token:
        raise SocialPublishError(
            "Authentification Reddit refusée : vérifiez client ID/secret, identifiants "
            "du compte, et que l'app est bien de type « script » (compte sans 2FA)."
        )
    return token


def _reddit_test() -> str:
    token = _reddit_token()
    payload = _request("GET", "https://oauth.reddit.com/api/v1/me", label="Reddit",
                       headers={"Authorization": f"Bearer {token}"})
    return f"compte u/{payload.get('name', '?')} ({payload.get('link_karma', 0)} karma)"


def _reddit_publish(message: str, link: str, image_url: str, subreddit: str) -> str:
    sr = (subreddit or get_field("reddit_default_sub")).strip().lstrip("r/").strip("/")
    if not sr:
        raise SocialPublishError("Indiquez le subreddit où publier (ex. VietnamTravel).")
    token = _reddit_token()
    title = _first_line(message, 290)
    body = "\n".join((message or "").strip().splitlines()[1:]).strip()
    data = {"sr": sr, "title": title, "api_type": "json", "resubmit": "true"}
    if link:
        data.update({"kind": "link", "url": link})
        if body:
            data["text"] = body  # subreddits autorisant le commentaire de lien
    else:
        data.update({"kind": "self", "text": body or message})
    payload = _request("POST", "https://oauth.reddit.com/api/submit", label="Reddit",
                       headers={"Authorization": f"Bearer {token}"}, data=data)
    inner = (payload.get("json") or {})
    errors = inner.get("errors") or []
    if errors:
        raise SocialPublishError(
            "Reddit a refusé la publication : "
            + " ; ".join(str(e[1] if len(e) > 1 else e[0]) for e in errors)
            + f" — vérifiez les règles de r/{sr} (flair obligatoire, liens interdits, karma minimum…)."
        )
    return (inner.get("data") or {}).get("url", "")


# ── X (Twitter) — OAuth 1.0a signé à la main (aucune dépendance) ──────────

def _oauth1_header(method: str, url: str, query: dict) -> str:
    ck, cs = get_field("x_api_key"), get_field("x_api_secret")
    tk, ts = get_field("x_access_token"), get_field("x_access_secret")
    oauth = {
        "oauth_consumer_key": ck,
        "oauth_nonce": _secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": tk,
        "oauth_version": "1.0",
    }
    q = lambda s: quote(str(s), safe="~")  # noqa: E731
    items = sorted({**query, **oauth}.items())
    base = "&".join([method.upper(), q(url), q("&".join(f"{q(k)}={q(v)}" for k, v in items))])
    key = f"{q(cs)}&{q(ts)}".encode()
    oauth["oauth_signature"] = base64.b64encode(
        hmac.new(key, base.encode(), hashlib.sha1).digest()
    ).decode()
    return "OAuth " + ", ".join(f'{q(k)}="{q(v)}"' for k, v in sorted(oauth.items()))


def _x_test() -> str:
    url = "https://api.x.com/2/users/me"
    payload = _request("GET", url, label="X",
                       headers={"Authorization": _oauth1_header("GET", url, {})})
    data = payload.get("data") or {}
    return f"compte @{data.get('username', '?')}"


def _x_publish(message: str, link: str, image_url: str) -> str:
    # 280 caractères max ; tout lien compte pour 23 (t.co).
    budget = 280 - (25 if link else 0)
    text = (message or "").strip()
    if len(text) > budget:
        text = text[: budget - 1].rstrip() + "…"
    if link:
        text = f"{text}\n{link}"
    url = "https://api.x.com/2/tweets"
    payload = _request("POST", url, label="X",
                       headers={"Authorization": _oauth1_header("POST", url, {}),
                                "Content-Type": "application/json"},
                       json={"text": text})
    tweet_id = (payload.get("data") or {}).get("id", "")
    return f"https://x.com/i/web/status/{tweet_id}" if tweet_id else ""


# ── Threads (Meta) ────────────────────────────────────────────────────────

THREADS_GRAPH = "https://graph.threads.net/v1.0"


def _threads_test() -> str:
    payload = _request(
        "GET", f"{THREADS_GRAPH}/{get_field('threads_user_id')}", label="Threads",
        params={"fields": "username", "access_token": get_field("threads_access_token")},
    )
    return f"compte @{payload.get('username', '?')}"


def _threads_publish(message: str, link: str, image_url: str) -> str:
    uid = get_field("threads_user_id")
    token = get_field("threads_access_token")
    text = f"{message}\n\n{link}" if link else message
    data = {"text": text[:500], "access_token": token}
    if image_url:
        data.update({"media_type": "IMAGE", "image_url": image_url})
    else:
        data["media_type"] = "TEXT"
    container = _request("POST", f"{THREADS_GRAPH}/{uid}/threads", label="Threads", data=data)
    creation_id = container.get("id")
    if not creation_id:
        raise SocialPublishError("Threads n'a pas renvoyé d'identifiant de brouillon.")
    if image_url:
        time.sleep(2)  # Meta recommande de laisser le média se préparer
    published = _request("POST", f"{THREADS_GRAPH}/{uid}/threads_publish", label="Threads",
                         data={"creation_id": creation_id, "access_token": token})
    media_id = published.get("id")
    if not media_id:
        return ""
    info = _request("GET", f"{THREADS_GRAPH}/{media_id}", label="Threads",
                    params={"fields": "permalink", "access_token": token})
    return info.get("permalink", "")


# ── Instagram (Graph API) ─────────────────────────────────────────────────

IG_GRAPH = "https://graph.facebook.com/v21.0"


def _instagram_test() -> str:
    payload = _request(
        "GET", f"{IG_GRAPH}/{get_field('instagram_user_id')}", label="Instagram",
        params={"fields": "username", "access_token": get_field("instagram_access_token")},
    )
    return f"compte @{payload.get('username', '?')}"


def _instagram_publish(message: str, link: str, image_url: str) -> str:
    if not image_url:
        raise SocialPublishError("Instagram exige une image pour publier via l'API.")
    uid = get_field("instagram_user_id")
    token = get_field("instagram_access_token")
    caption = f"{message}\n\n🔗 {link}" if link else message  # lien non cliquable sur IG
    container = _request("POST", f"{IG_GRAPH}/{uid}/media", label="Instagram",
                         data={"image_url": image_url, "caption": caption[:2200],
                               "access_token": token})
    creation_id = container.get("id")
    if not creation_id:
        raise SocialPublishError("Instagram n'a pas renvoyé d'identifiant de média.")
    published = _request("POST", f"{IG_GRAPH}/{uid}/media_publish", label="Instagram",
                         data={"creation_id": creation_id, "access_token": token})
    media_id = published.get("id")
    if not media_id:
        return ""
    info = _request("GET", f"{IG_GRAPH}/{media_id}", label="Instagram",
                    params={"fields": "permalink", "access_token": token})
    return info.get("permalink", "")


# ── Dispatch ──────────────────────────────────────────────────────────────

_TESTERS = {
    "telegram": _telegram_test,
    "pinterest": _pinterest_test,
    "reddit": _reddit_test,
    "x": _x_test,
    "threads": _threads_test,
    "instagram": _instagram_test,
}


def test_connection(net_key: str) -> str:
    """Vérifie les identifiants du réseau ; renvoie un libellé lisible (compte/canal)."""
    tester = _TESTERS.get(net_key)
    if not tester:
        raise SocialPublishError(f"Test indisponible pour ce réseau : {net_key}")
    if not is_network_configured(net_key):
        raise SocialPublishError("Renseignez d'abord tous les champs de connexion.")
    return tester()


def publish(net_key: str, *, message: str, link: str = "", image_url: str = "",
            subreddit: str = "") -> str:
    """Publie sur le réseau demandé ; renvoie le permalien du post (ou '')."""
    net = NETWORK_KEYS.get(net_key)
    if not net or not net.get("publishable"):
        raise SocialPublishError(f"Publication non disponible pour ce réseau : {net_key}")
    if not is_network_configured(net_key):
        raise SocialPublishError(f"{net['name']} n'est pas configuré : renseignez la connexion.")
    if net.get("needs_image") and not image_url:
        raise SocialPublishError(f"{net['name']} exige une image pour publier.")
    _check_cooldown(net_key)

    if net_key == "telegram":
        permalink = _telegram_publish(message, link, image_url)
    elif net_key == "pinterest":
        permalink = _pinterest_publish(message, link, image_url)
    elif net_key == "reddit":
        permalink = _reddit_publish(message, link, image_url, subreddit)
    elif net_key == "x":
        permalink = _x_publish(message, link, image_url)
    elif net_key == "threads":
        permalink = _threads_publish(message, link, image_url)
    elif net_key == "instagram":
        permalink = _instagram_publish(message, link, image_url)
    else:
        raise SocialPublishError(f"Publication non implémentée : {net_key}")

    _mark_published(net_key)
    return permalink
