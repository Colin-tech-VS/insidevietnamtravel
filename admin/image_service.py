"""Images d'articles — une photo Vietnam unique par article, export WebP optimisé."""

from __future__ import annotations

import io
import os
import re
import threading
import time
import urllib.parse
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageOps

from admin.genlog import log

# Gunicorn (--preload + --threads 4) : les plugins Pillow (BmpImagePlugin, etc.)
# se chargent paresseusement au premier Image.open(). Deux threads concurrents
# provoquent « partially initialized module PIL.BmpImagePlugin ». On pré-charge
# tout au import du module principal, puis on sérialise les opérations PIL.
_pil_lock = threading.RLock()


def _init_pil_plugins() -> None:
    with _pil_lock:
        Image.preinit()
        Image.init()


_init_pil_plugins()

BLOG_IMAGES_DIR = Path(__file__).parent.parent / "static" / "images" / "blog"
DEST_IMAGES_DIR = Path(__file__).parent.parent / "static" / "images" / "destinations"
PARTNER_IMAGES_DIR = Path(__file__).parent.parent / "static" / "images" / "partners"
# Pool de vraies photos Vietnam EMBARQUÉES dans le repo (static/images/pool/<id>.webp).
# C'est la source par défaut : aucun appel réseau au moment de générer → l'étape image
# est INSTANTANÉE et ne peut plus « bloquer » (le réseau sortant de l'hébergeur, lent ou
# filtré vers Unsplash, était la cause des blocages à 15 s puis du logo de secours).
POOL_IMAGES_DIR = Path(__file__).parent.parent / "static" / "images" / "pool"

# Génération d'image IA (Pollinations Flux) : l'endpoint ne renvoie l'image qu'une
# fois calculée, donc le timeout de lecture = temps de génération. Flux est lent et
# souvent en file d'attente : un timeout long (120 s) faisait monopoliser toute la
# génération à cette seule étape (« ça charge sans fin »). On échoue donc VITE pour
# basculer sur la photo Vietnam de secours (Unsplash, quasi instantanée) : une image
# IA absente vaut mieux qu'un brouillon bloqué plusieurs minutes.
REMOTE_IMAGE_CONNECT_TIMEOUT = 6   # secondes pour établir la connexion
REMOTE_IMAGE_READ_TIMEOUT = 12     # secondes max d'inactivité socket

# Repli réseau quand le pool local manque : Pixabay (au lieu d'Unsplash, dont le réseau
# sortant de l'hébergeur était lent/filtré et faisait pendre l'étape image). Pixabay
# nécessite une clé gratuite (PIXABAY_API_KEY) ; sans clé, on saute direct au logo.
PIXABAY_API_URL = "https://pixabay.com/api/"
PIXABAY_CONNECT_TIMEOUT = 5
PIXABAY_READ_TIMEOUT = 10

# Échéance MURALE absolue de TOUTE l'étape image (IA + photo Vietnam + reprises). Les
# timeouts socket de requests ne se déclenchent qu'en l'absence totale d'octets, et
# l'ancien chemin Unsplash enchaînait jusqu'à 4 essais (≈130 s) sans plafond global :
# si le réseau sortant est lent/bloqué, l'étape image pendait des minutes et le
# brouillon (pourtant déjà rédigé FR + EN) n'était jamais déposé — d'où le « ça bloque
# et ne génère rien ». Ce plafond, imposé par un thread démon, garantit qu'au-delà de
# 15 s on abandonne l'image, on dépose le logo de marque (image_placeholder) et la
# génération du contenu se termine TOUJOURS. Le thread orphelin meurt seul ensuite.
IMAGE_STEP_HARD_DEADLINE = 15      # secondes max, tout compris, pour l'étape image

# Échéance dure de l'ENCODAGE WebP (décodage + redimension + 3 écritures method=4).
# L'encodage était jusqu'ici HORS de tout plafond : sur un conteneur bridé en CPU,
# `method=6` ×3 pouvait pendre longtemps SANS aucun log entre « IMAGE start » et
# « IMAGE done » — d'où le « ça bloque et rien n'indique pourquoi ». On le borne donc
# comme le reste ; au-delà, on dépose une version rapide (method=0) et on continue.
IMAGE_ENCODE_DEADLINE = 10         # secondes max pour l'encodage WebP + variantes (articles)
PARTNER_ENCODE_DEADLINE = 60       # partenaires : CPU Scalingo + verrou PIL partagé

# Effort de compression WebP (0 rapide … 6 exhaustif). `method=6` est très lent pour un
# gain de taille marginal vs `method=4` (défaut libwebp) ; sur l'hébergeur bridé il était
# une cause directe de lenteur de l'étape image. On reste à 4 : bon compromis vitesse/poids.
WEBP_METHOD = 4

# Photos Unsplash vérifiées — scènes Vietnam uniquement (id, description)
VIETNAM_PHOTO_POOL: list[tuple[str, str]] = [
    ("1528127269322-539801943592", "Baie d'Halong / Hoi An, bateaux"),
    ("1772867342647-6e6d87a0b014", "Baie d'Halong, karsts"),
    ("1559592413-7cec4d0cae2b", "Pont et vie locale Vietnam"),
    ("1557750255-c76072a7aad1", "Pagode Ninh Binh, montagnes"),
    ("1583417319070-4a69db38a482", "Skyline Ho Chi Minh-Ville"),
    ("1531737212413-667205e1cda7", "Montagnes rizières Sapa"),
    ("1545172538-171a802bd867", "Baie d'Halong, kayak"),
    ("1609412058473-c199497c3c5d", "Paysage verdoyant Vietnam"),
    ("1555921015-5532091f6026", "Train street Hanoï"),
    ("1526139334526-f591a54b477c", "Marché nocturne, lanternes"),
    ("1555979864-7a8f9b4fddf8", "Plage Vietnam vue aérienne"),
    ("1480996408299-fc0e830b5db1", "Montagnes tropicales Vietnam"),
    ("1521993117367-b7f70ccd029d", "Scooter, rue vietnamienne"),
    ("1602646993875-70bc0ba52c87", "Formations rocheuses Vietnam"),
    ("1504457047772-27faf1c00561", "Maison falaises Vietnam"),
    ("1603852452378-a4e8d84324a2", "Vue aérienne ville Vietnam"),
    ("1578662996442-48f60103fc96", "Temple / architecture Vietnam"),
    ("1605649487212-47bdab064df7", "Paysage campagne Vietnam"),
    ("1432405972618-c60b0225b8f9", "Nature tropicale Vietnam"),
]

# Thèmes par photo : tokens d'un vocabulaire partagé avec _article_keywords().
# Sert à choisir une image EN RAPPORT avec le sujet de l'article (ville, gastronomie,
# nature, plage, ville, temple…) plutôt qu'une photo tirée au hasard.
PHOTO_THEMES: dict[str, set[str]] = {
    "1528127269322-539801943592": {"halong", "hoian", "beach", "cruise", "nature"},
    "1772867342647-6e6d87a0b014": {"halong", "nature", "cruise"},
    "1559592413-7cec4d0cae2b": {"city", "local"},
    "1557750255-c76072a7aad1": {"ninhbinh", "nature", "temple", "mountain"},
    "1583417319070-4a69db38a482": {"hochiminh", "city", "skyline"},
    "1531737212413-667205e1cda7": {"sapa", "nature", "mountain", "trekking"},
    "1545172538-171a802bd867": {"halong", "nature", "cruise"},
    "1609412058473-c199497c3c5d": {"nature", "countryside"},
    "1555921015-5532091f6026": {"hanoi", "city", "transport"},
    "1526139334526-f591a54b477c": {"food", "market", "hoian", "night"},
    "1555979864-7a8f9b4fddf8": {"danang", "beach", "nature"},
    "1480996408299-fc0e830b5db1": {"nature", "mountain"},
    "1521993117367-b7f70ccd029d": {"city", "transport"},
    "1602646993875-70bc0ba52c87": {"halong", "nature"},
    "1504457047772-27faf1c00561": {"nature", "countryside"},
    "1603852452378-a4e8d84324a2": {"city"},
    "1578662996442-48f60103fc96": {"hue", "temple", "culture"},
    "1605649487212-47bdab064df7": {"nature", "countryside"},
    "1432405972618-c60b0225b8f9": {"nature"},
}

# Indices ville → token thématique (normalisés sans accents/espaces).
_CITY_TOKENS: dict[str, str] = {
    "hanoi": "hanoi",
    "hochiminh": "hochiminh", "saigon": "hochiminh", "hcmville": "hochiminh",
    "hoian": "hoian",
    "danang": "danang",
    "sapa": "sapa",
    "ninhbinh": "ninhbinh",
    "halong": "halong", "halongbay": "halong",
    "hue": "hue",
    "phuquoc": "beach", "nhatrang": "beach", "mui ne": "beach", "muine": "beach",
    "mekong": "nature", "deltadumekong": "nature",
}

# Mots-clés (FR/EN) → token thématique, cherchés dans titre/tags/focus.
_KEYWORD_TOKENS: list[tuple[tuple[str, ...], str]] = [
    (("gastronom", "cuisine", "restaurant", "manger", "street food", "food", "pho", "plat"), "food"),
    (("march", "market", "night market", "lanterne"), "market"),
    (("plage", "beach", "ile", "island", "mer", "balnea"), "beach"),
    (("trek", "randonn", "rizi", "montagne", "mountain", "sapa"), "trekking"),
    (("nature", "campagne", "paysage", "parc", "baie", "karst"), "nature"),
    (("temple", "pagode", "pagoda", "culture", "histoire", "patrimoine"), "temple"),
    (("transport", "train", "bus", "scooter", "moto", "vol", "avion", "taxi", "deplac"), "transport"),
    (("ville", "city", "urbain", "skyline"), "city"),
    (("croisi", "cruise", "bateau", "kayak", "jonque"), "cruise"),
]

_CATEGORY_TOKENS: dict[str, str] = {
    "food": "food",
    "itinerary": "city",
    "budget": "city",
    "practical": "city",
}

# Correspondance thématique slug → photo (prioritaire, toujours unique)
SLUG_PHOTO_MAP: dict[str, str] = {
    "visa-vietnam-guide-complet-francais": "1557750255-c76072a7aad1",
    "budget-voyage-vietnam-2026": "1526139334526-f591a54b477c",
    "carte-sim-esim-vietnam": "1583417319070-4a69db38a482",
    "securite-voyage-vietnam-conseils": "1528127269322-539801943592",
    "transport-vietnam-train-bus-vol": "1555921015-5532091f6026",
    "train-reunification-hanoi-saigon": "1555921015-5532091f6026",
    "vols-interieurs-vietnam": "1603852452378-a4e8d84324a2",
    "location-scooter-vietnam": "1521993117367-b7f70ccd029d",
    "plats-incontournables-vietnam": "1526139334526-f591a54b477c",
    "cafe-vietnamien-guide": "1559592413-7cec4d0cae2b",
    "meilleurs-restaurants-hanoi": "1521993117367-b7f70ccd029d",
    "decouvrez-hanoi-en-7-jours-itineraire-ideal-pour-les-debutants-au-vietnam": "1772867342647-6e6d87a0b014",
}

# Photos Vietnam par page destination publique (photo_id → ville)
DESTINATION_PHOTO_MAP: dict[str, str] = {
    "hanoi": "1555921015-5532091f6026",
    "ho-chi-minh-city": "1583417319070-4a69db38a482",
    "hoi-an": "1528127269322-539801943592",
    "da-nang": "1555979864-7a8f9b4fddf8",
    "halong": "1772867342647-6e6d87a0b014",
    "sapa": "1531737212413-667205e1cda7",
    "hue": "1578662996442-48f60103fc96",
    "delta-du-mekong": "1605649487212-47bdab064df7",
    "phu-quoc": "1480996408299-fc0e830b5db1",
}

DESTINATION_PHOTO_ALTERNATES: dict[str, list[str]] = {
    "hanoi": ["1521993117367-b7f70ccd029d"],
    "halong": ["1545172538-171a802bd867"],
    "sapa": ["1609412058473-c199497c3c5d"],
    "hoi-an": ["1526139334526-f591a54b477c"],
    "ho-chi-minh-city": ["1603852452378-a4e8d84324a2"],
    "delta-du-mekong": ["1432405972618-c60b0225b8f9", "1559592413-7cec4d0cae2b"],
    "phu-quoc": ["1602646993875-70bc0ba52c87"],
    "hue": ["1557750255-c76072a7aad1"],
    "da-nang": ["1504457047772-27faf1c00561"],
}

# Requêtes Pixabay par défaut (Linh / admin) — toujours ancrées sur la ville
DESTINATION_PIXABAY_QUERIES: dict[str, str] = {
    "hanoi": "Hanoi Vietnam old quarter street food",
    "ho-chi-minh-city": "Ho Chi Minh City Vietnam skyline",
    "hoi-an": "Hoi An Vietnam ancient town river lanterns",
    "da-nang": "Da Nang Vietnam beach coastline",
    "halong": "Halong Bay Vietnam limestone karst boats",
    "sapa": "Sapa Vietnam rice terrace mountains",
    "hue": "Hue Vietnam imperial citadel pagoda",
    "delta-du-mekong": "Mekong Delta Vietnam floating market boat",
    "phu-quoc": "Phu Quoc Vietnam tropical beach turquoise",
}

# Article → destination (image ville commitée dans static/images/destinations/)
ARTICLE_DESTINATION_SLUG_MAP: dict[str, str] = {
    "decouvrez-hanoi-en-7-jours-itineraire-ideal-pour-les-debutants-au-vietnam": "hanoi",
    "meilleurs-restaurants-hanoi": "hanoi",
    "visa-vietnam-guide-complet-francais": "hanoi",
    "budget-voyage-vietnam-2026": "hanoi",
    "securite-voyage-vietnam-conseils": "hanoi",
    "transport-vietnam-train-bus-vol": "hanoi",
    "plats-incontournables-vietnam": "hanoi",
    "train-reunification-hanoi-saigon": "hanoi",
    "carte-sim-esim-vietnam": "ho-chi-minh-city",
    "vols-interieurs-vietnam": "ho-chi-minh-city",
    "cafe-vietnamien-guide": "hoi-an",
    "location-scooter-vietnam": "hoi-an",
    "da-nang-plages-vietnam": "da-nang",
    "phu-quoc-plages-ile-tropicale": "phu-quoc",
    "hue-citadelle-imperiale-vietnam": "hue",
    "hoi-an-lanternes-vieille-ville": "hoi-an",
    "excursion-delta-mekong-marches-flottants": "delta-du-mekong",
    "trek-sapa-rizieres-vietnam": "sapa",
    "croisiere-baie-halong-vietnam": "halong",
}

_SLUG_DESTINATION_HINTS: list[tuple[str, str]] = [
    ("ho-chi-minh", "ho-chi-minh-city"),
    ("hochiminh", "ho-chi-minh-city"),
    ("saigon", "ho-chi-minh-city"),
    ("hoi-an", "hoi-an"),
    ("hoian", "hoi-an"),
    ("da-nang", "da-nang"),
    ("danang", "da-nang"),
    ("phu-quoc", "phu-quoc"),
    ("phuquoc", "phu-quoc"),
    ("delta-du-mekong", "delta-du-mekong"),
    ("mekong", "delta-du-mekong"),
    ("halong", "halong"),
    ("sapa", "sapa"),
    ("hanoi", "hanoi"),
    ("hue", "hue"),
]


def _resolve_article_destination_slug(article: dict) -> str | None:
    """Destination dont l'image ville commitée convient le mieux à l'article."""
    slug = article.get("slug", "")
    if slug in ARTICLE_DESTINATION_SLUG_MAP:
        return ARTICLE_DESTINATION_SLUG_MAP[slug]
    norm = _normalize_token(slug)
    for hint, dest in _SLUG_DESTINATION_HINTS:
        if _normalize_token(hint) in norm:
            return dest
    city_norm = _normalize_token(article.get("city", ""))
    city_to_dest = {
        "hanoi": "hanoi",
        "hochiminh": "ho-chi-minh-city",
        "hoian": "hoi-an",
        "danang": "da-nang",
        "halong": "halong",
        "sapa": "sapa",
        "hue": "hue",
        "phuquoc": "phu-quoc",
        "mekong": "delta-du-mekong",
        "deltadumekong": "delta-du-mekong",
    }
    for key, dest in city_to_dest.items():
        if key in city_norm:
            return dest
    return None


def _committed_destination_image_url(dest_slug: str) -> str | None:
    path = DEST_IMAGES_DIR / f"{dest_slug}.webp"
    if path.is_file():
        return f"/static/images/destinations/{dest_slug}.webp"
    return None


def _article_image_needs_repair(article: dict) -> bool:
    if article.get("image_placeholder"):
        return True
    image = article.get("image") or ""
    if not image:
        return True
    if image.startswith("/static/images/blog/") and not _static_image_exists(image):
        return True
    return False


def sync_article_destination_images() -> int:
    """Aligne les articles sur les images ville commitées (ou pool de secours)."""
    from admin.store import get_articles, save_articles

    articles = get_articles()
    updated = 0

    for i, article in enumerate(articles):
        slug = article["slug"]
        dest_slug = _resolve_article_destination_slug(article)
        dest_url = _committed_destination_image_url(dest_slug) if dest_slug else None
        current = article.get("image") or ""

        if dest_url and (current != dest_url or _article_image_needs_repair(article)):
            photo_ids = _photo_ids_for_destination(dest_slug) if dest_slug else []
            photo_id = photo_ids[0] if photo_ids else (article.get("image_photo_id") or "")
            meta = _article_image_meta(
                article, slug, photo_id, placeholder=False, image_url=dest_url,
            )
            articles[i] = {**article, **meta}
            updated += 1
            continue

        if not _article_image_needs_repair(article):
            continue

        photo_id = article.get("image_photo_id") or _pick_unique_photo_id(slug, 0, article)
        pool_url = f"/static/images/pool/{photo_id}.webp"
        if _local_pool_path(photo_id).exists():
            meta = _article_image_meta(
                article, slug, photo_id, placeholder=False, image_url=pool_url,
            )
            articles[i] = {**article, **meta}
            updated += 1

    if updated:
        save_articles(articles)
    return updated


def destination_pixabay_query(slug: str, dest: dict | None = None) -> str:
    """Mots-clés Pixabay garantissant une photo de la bonne ville."""
    if slug in DESTINATION_PIXABAY_QUERIES:
        return DESTINATION_PIXABAY_QUERIES[slug]
    name = (dest or {}).get("name") or slug.replace("-", " ")
    return f"{name} Vietnam travel landmark"


def _slug_theme_tokens(slug: str) -> set[str]:
    key = slug.replace("-", "")
    if key in _CITY_TOKENS:
        return {_CITY_TOKENS[key]}
    for city_key, token in _CITY_TOKENS.items():
        if city_key in key or key.startswith(city_key):
            return {token}
    return set()


def _photo_ids_for_destination(slug: str) -> list[str]:
    """Photo_ids du pool compatibles avec le slug (ordre de préférence)."""
    ordered: list[str] = []
    primary = DESTINATION_PHOTO_MAP.get(slug)
    if primary:
        ordered.append(primary)
    for pid in DESTINATION_PHOTO_ALTERNATES.get(slug, []):
        if pid not in ordered:
            ordered.append(pid)
    tokens = _slug_theme_tokens(slug)
    if tokens:
        for pid, themes in PHOTO_THEMES.items():
            if tokens & themes and pid not in ordered:
                ordered.append(pid)
    return ordered


def _photo_id_from_pool_url(image_url: str | None) -> str:
    if not image_url or "/static/images/pool/" not in image_url:
        return ""
    return image_url.rsplit("/", 1)[-1].removesuffix(".webp")


def photo_id_matches_destination(slug: str, photo_id: str) -> bool:
    if not photo_id:
        return True
    return photo_id in _photo_ids_for_destination(slug)


def _align_destination_pool_image(dest: dict) -> dict | None:
    """Corrige une image pool qui ne correspond pas à la ville de la page."""
    slug = dest.get("slug", "")
    image = (dest.get("image") or "").strip()
    if image.startswith("/static/images/destinations/") or _is_remote_image_url(image):
        return None

    photo_id = (dest.get("image_photo_id") or "").strip() or _photo_id_from_pool_url(image)
    if photo_id and photo_id_matches_destination(slug, photo_id):
        if _local_pool_path(photo_id).exists():
            return {**dest, **_commit_pool_photo_to_destination(slug, photo_id)}
        pool_url = pool_image_url(photo_id)
        if image != pool_url:
            return {**dest, "image": pool_url, "image_photo_id": photo_id, "image_placeholder": False}
        return None

    pid = _pick_destination_photo_id(slug, abs(hash(slug)) % 9999)
    if _local_pool_path(pid).exists():
        return {**dest, **_commit_pool_photo_to_destination(slug, pid)}
    return {
        **dest,
        "image": pool_image_url(pid),
        "image_photo_id": pid,
        "image_placeholder": False,
    }

# Texte alternatif des photos de ville committées dans static/images/destinations/.
DESTINATION_IMAGE_ALTS: dict[str, str] = {
    "hanoi": "Pont rouge Thê Húc sur le lac Hoàn Kiếm, Hanoï, Vietnam",
    "ho-chi-minh-city": "Skyline de Ho Chi Minh-Ville illuminée la nuit, Vietnam",
    "hoi-an": "Lanternes colorées de la vieille ville de Hội An la nuit, Vietnam",
    "da-nang": "Pont d'Or (Golden Bridge) soutenu par des mains géantes, Bà Nà Hills, Đà Nẵng",
    "halong": "Karsts calcaires émergeant des eaux émeraude de la baie d'Halong, Vietnam",
    "sapa": "Rizières en terrasses dorées de la vallée de Sapa, Vietnam",
    "delta-du-mekong": "Marché flottant de Cái Răng, barques chargées de fruits, delta du Mékong",
    "hue": "Tour du drapeau et douves de la citadelle impériale de Huế, Vietnam",
    "phu-quoc": "Plage de sable blanc, palmiers et eaux turquoise de Phú Quốc, Vietnam",
}


def _upgrade_to_committed_city_image(dest: dict) -> dict | None:
    """Adopte la photo de VILLE committée (destinations/<slug>.webp) à la place
    d'une photo pool générique.

    Le pool est un stock de photos Vietnam génériques : plusieurs villes y
    partagent la même ambiance (« paysage », « plage »…). Quand une vraie photo
    de la ville est committée dans le repo (persistante au redéploiement), elle
    est toujours plus représentative. On ne touche PAS aux images destinations/
    ni aux URLs distantes déjà en place : ce sont des choix explicites de
    l'admin (manuel ou via Linh)."""
    slug = dest.get("slug", "")
    image = (dest.get("image") or "").strip()
    if image.startswith("/static/images/destinations/") or _is_remote_image_url(image):
        return None
    committed = DEST_IMAGES_DIR / f"{slug}.webp"
    if not committed.is_file():
        return None
    return {
        **dest,
        "image": f"/static/images/destinations/{slug}.webp",
        "image_alt": DESTINATION_IMAGE_ALTS.get(slug)
        or f"Guide voyage {dest.get('name', slug)}, Vietnam",
        "image_photo_id": "",
        "image_placeholder": False,
    }


LEGACY_PROMPTS: dict[str, str] = {
    "visa-vietnam-guide-complet-francais": (
        "Ninh Binh pagoda surrounded by water and mountains Vietnam, travel photography, no text"
    ),
    "budget-voyage-vietnam-2026": (
        "Vietnamese street food market with lanterns at night Hanoi, travel budget, no text"
    ),
    "carte-sim-esim-vietnam": (
        "Ho Chi Minh City skyline at night Vietnam, smartphone connectivity, no text"
    ),
    "securite-voyage-vietnam-conseils": (
        "Hoi An ancient town boats Vietnam peaceful travel scene, no text"
    ),
    "transport-vietnam-train-bus-vol": (
        "Hanoi train street famous railway alley Vietnam, photorealistic, no text"
    ),
    "meilleurs-restaurants-hanoi": (
        "Vietnamese pho and street food Hanoi old quarter steam vibrant, no text"
    ),
}


def _ai_images_enabled() -> bool:
    """L'image IA (Pollinations Flux) est OPT-IN.

    Par défaut on utilise le pool de vraies photos Vietnam (immédiat et fiable) : Flux
    est lent/instable et faisait pendre la génération. Pour réactiver l'image IA,
    mettre `ai_image_enabled: true` dans les réglages.
    """
    try:
        from admin.store import get_settings
        return bool(get_settings().get("ai_image_enabled", False))
    except Exception:
        return False


def _pixabay_api_key() -> str:
    return os.environ.get("PIXABAY_API_KEY", "").strip()


def _used_photo_ids(exclude_slug: str | None = None) -> set[str]:
    from admin.store import get_articles

    used = set()
    for a in get_articles():
        if exclude_slug and a.get("slug") == exclude_slug:
            continue
        pid = a.get("image_photo_id")
        if pid:
            used.add(pid)
    return used


def _normalize_token(text: str) -> str:
    """Minuscule sans accents ni séparateurs — pour matcher 'Hội An' → 'hoian'."""
    text = (text or "").lower()
    for a, b in (("àâä", "a"), ("éèêë", "e"), ("îï", "i"), ("ôö", "o"), ("ùûü", "u"), ("ç", "c")):
        for ch in a:
            text = text.replace(ch, b)
    return re.sub(r"[^a-z0-9]+", "", text)


def _article_keywords(article: dict) -> set[str]:
    """Tokens thématiques (ville + concepts) déduits de l'article pour choisir l'image."""
    tokens: set[str] = set()

    city_tok = _normalize_token(article.get("city", ""))
    if city_tok in _CITY_TOKENS:
        tokens.add(_CITY_TOKENS[city_tok])

    cat = (article.get("category") or "").lower()
    if cat in _CATEGORY_TOKENS:
        tokens.add(_CATEGORY_TOKENS[cat])

    haystack = " ".join(str(article.get(k, "")) for k in ("title", "focus_keyword", "guide_type")).lower()
    haystack += " " + " ".join(str(t) for t in article.get("tags", [])).lower()
    for needles, token in _KEYWORD_TOKENS:
        if any(n in haystack for n in needles):
            tokens.add(token)
    # Villes citées dans le titre/tags même si le champ city est générique.
    for city_key, token in _CITY_TOKENS.items():
        if city_key in _normalize_token(haystack):
            tokens.add(token)
    return tokens


def _pick_unique_photo_id(slug: str, nonce: int = 0, article: dict | None = None) -> str:
    if slug in SLUG_PHOTO_MAP:
        return SLUG_PHOTO_MAP[slug]

    used = _used_photo_ids(exclude_slug=slug)
    pool_ids = [p[0] for p in VIETNAM_PHOTO_POOL]
    keywords = _article_keywords(article) if article else set()

    # 1) Photo la plus EN RAPPORT avec le sujet : meilleur recouvrement de thèmes,
    #    en privilégiant celles pas encore utilisées (image unique par article).
    if keywords:
        def score(pid: str) -> tuple[int, int]:
            overlap = len(PHOTO_THEMES.get(pid, set()) & keywords)
            return (overlap, 0 if pid in used else 1)

        # Départ pseudo-aléatoire stable pour ne pas toujours renvoyer le même id à
        # score égal (variété entre articles d'un même thème).
        start = abs(hash(f"{slug}-{nonce}")) % len(pool_ids)
        ordered = [pool_ids[(start + i) % len(pool_ids)] for i in range(len(pool_ids))]
        best = max(ordered, key=score)
        if len(PHOTO_THEMES.get(best, set()) & keywords) > 0:
            return best

    # 2) Aucun thème exploitable : 1re photo libre à partir d'un départ stable.
    start = abs(hash(f"{slug}-{nonce}")) % len(pool_ids)
    for offset in range(len(pool_ids)):
        pid = pool_ids[(start + offset) % len(pool_ids)]
        if pid not in used:
            return pid

    return pool_ids[start % len(pool_ids)]


def build_image_prompt(article: dict, ai_prompt: str | None = None) -> str:
    if ai_prompt and ai_prompt.strip():
        base = ai_prompt.strip()
        if "vietnam" not in base.lower():
            base += ", Vietnam travel scene"
        return base + ", photorealistic, 16:9, no text, no watermark"
    slug = article.get("slug", "")
    if slug in LEGACY_PROMPTS:
        return LEGACY_PROMPTS[slug]
    city = article.get("city", "Vietnam")
    title = article.get("title", "Vietnam travel")
    tags = ", ".join(article.get("tags", [])[:5])
    return (
        f"Authentic Vietnam travel photography, {city}, {title}, {tags}, "
        f"local landmark or daily life, golden hour, cinematic 16:9, no text, no watermark"
    )


def _fallback_gradient_webp(slug: str) -> bytes:
    w, h = 1200, 675
    img = Image.new("RGB", (w, h))
    seed = abs(hash(slug)) % 255
    for y in range(h):
        t = y / h
        r = int(27 + (seed % 40 - 20) * t)
        g = int(77 + (seed % 30 - 15) * t)
        b = int(74 + (seed % 25 - 12) * t)
        ImageDraw.Draw(img).line([(0, y), (w, y)], fill=(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))))
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=80, method=6)
    return buf.getvalue()


def _fetch_remote_image(prompt: str, seed: int, *, width: int = 1200, height: int = 675) -> bytes:
    encoded = urllib.parse.quote(prompt, safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&nologo=true&seed={seed}&model=flux"
    )
    resp = requests.get(
        url,
        timeout=(REMOTE_IMAGE_CONNECT_TIMEOUT, REMOTE_IMAGE_READ_TIMEOUT),
        headers={"User-Agent": "InsideVietnamTravel/1.0"},
    )
    resp.raise_for_status()
    if len(resp.content) < 8000:
        raise ValueError("Image IA invalide")
    return resp.content


def _run_with_deadline(fn, deadline: float, *args, **kwargs):
    """Exécute `fn` dans un thread démon avec une échéance murale stricte.

    Si `fn` n'a pas rendu son résultat dans `deadline` secondes, on lève TimeoutError ;
    le thread orphelin (réseau lent/bloqué) finira par mourir seul via son timeout
    socket, sans jamais bloquer l'appelant. Garantit qu'une étape réseau ne pend pas.
    """
    result: dict = {}

    def _worker():
        try:
            result["data"] = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — relayé via result
            result["error"] = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(deadline)
    if thread.is_alive():
        raise TimeoutError("Étape image trop lente (échéance dépassée)")
    if "data" in result:
        return result["data"]
    raise result.get("error", RuntimeError("Image indisponible"))


def _logo_placeholder_webp(slug: str) -> bytes:
    """Visuel de secours de marque : motif du logo (anneau + arc + voyageur) sur teal.

    Affiché quand l'étape image dépasse l'échéance de 15 s — le contenu n'est jamais
    bloqué. Le front (aperçu brouillon) anime ce même motif en SVG « en attendant ».
    """
    w, h = 1200, 675
    teal = (27, 77, 74)
    gold = (196, 160, 83)
    rice = (250, 247, 242)
    img = Image.new("RGB", (w, h), teal)
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2 - 24
    r = 120

    # Anneau
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=gold, width=6)

    # Arc « voyage » (courbe de Bézier quadratique → polyligne)
    p0 = (cx - r * 0.62, cy + r * 0.42)
    p1 = (cx, cy - r * 0.72)
    p2 = (cx + r * 0.62, cy + r * 0.42)
    pts = []
    for i in range(41):
        t = i / 40
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    draw.line(pts, fill=gold, width=6, joint="curve")

    # Point « voyageur » au sommet de l'arc
    tx, ty = pts[20]
    draw.ellipse([tx - 16, ty - 16, tx + 16, ty + 16], fill=gold)

    # Nom de marque
    label = "Inside Vietnam Travel"
    try:
        from PIL import ImageFont
        font = ImageFont.load_default()
        tw = draw.textlength(label, font=font) if hasattr(draw, "textlength") else len(label) * 6
        draw.text((cx - tw / 2, cy + r + 48), label, fill=rice, font=font)
    except Exception:
        pass

    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=82, method=6)
    return buf.getvalue()


def _local_pool_path(photo_id: str) -> Path:
    return POOL_IMAGES_DIR / f"{photo_id}.webp"


_STATIC_ROOT = Path(__file__).parent.parent / "static"


def destination_image_for_display(dest: dict) -> str | None:
    """URL servie au visiteur — même logique que l'admin doit afficher."""
    return persistent_image_url(
        dest.get("image"),
        dest.get("image_photo_id"),
        dest.get("image_source_url"),
    )


def enrich_destination_for_display(dest: dict) -> dict:
    """Copie destination avec `image` résolue (fichier local, source ou pool)."""
    out = dict(dest)
    out["image"] = destination_image_for_display(dest)
    return out


def _canonical_destination_image_url(slug: str) -> str:
    return f"/static/images/destinations/{slug}.webp"


def _commit_pool_photo_to_destination(slug: str, photo_id: str) -> dict:
    """Copie une photo pool vers destinations/<slug>.webp — URL unique admin + public."""
    raw = _fetch_vietnam_photo(photo_id)
    out_path = DEST_IMAGES_DIR / f"{slug}.webp"
    try:
        _to_webp(raw, out_path)
    except Exception:
        _write_webp_fast(raw, out_path)
    return {
        "image": _canonical_destination_image_url(slug),
        "image_alt": DESTINATION_IMAGE_ALTS.get(slug, f"Guide voyage {slug.replace('-', ' ')}, Vietnam"),
        "image_photo_id": "",
        "image_placeholder": False,
    }


def _normalize_destination_store_record(slug: str, dest: dict, *, allow_network: bool) -> dict | None:
    """Force l'URL canonique destinations/<slug>.webp quand le fichier existe ou peut être recréé."""
    canonical = _canonical_destination_image_url(slug)
    committed = DEST_IMAGES_DIR / f"{slug}.webp"
    source = (dest.get("image_source_url") or "").strip()

    if not committed.is_file() and allow_network and _is_remote_image_url(source):
        try:
            _write_remote_webp(source, committed)
        except Exception:
            pass

    if committed.is_file():
        changed = dest.get("image") != canonical or dest.get("image_photo_id")
        alt = dest.get("image_alt") or DESTINATION_IMAGE_ALTS.get(slug)
        if not changed and not alt:
            return None
        patch = {**dest, "image": canonical, "image_photo_id": "", "image_placeholder": False}
        if alt:
            patch["image_alt"] = alt
        return patch

    image = (dest.get("image") or "").strip()
    if image.startswith("/static/images/pool/"):
        photo_id = _photo_id_from_pool_url(image) or (dest.get("image_photo_id") or "").strip()
        if photo_id and _local_pool_path(photo_id).exists():
            return {**dest, **_commit_pool_photo_to_destination(slug, photo_id)}
    return None


def persistent_image_url(
    image_url: str | None,
    photo_id: str | None,
    source_url: str | None = None,
) -> str | None:
    """Garantit une URL d'image présente au rendu.

    Les images écrites au runtime (static/images/blog|destinations/) vivent sur le FS
    éphémère de Scalingo : après un redéploiement elles disparaissent, alors que l'article
    (en base Supabase) garde son URL → image cassée. Plan de repli, dans l'ordre :
    1) le fichier /static pointé existe → on le sert (cas normal, optimisé) ;
    2) `source_url` (image internet d'origine choisie via Linh) → on la sert directement,
       toujours disponible même après un redéploiement ;
    3) la photo du POOL (commitée dans git) via `image_photo_id` ;
    4) à défaut, l'URL telle quelle (ex. image déjà externe en http).
    """
    def _is_remote(u: str | None) -> bool:
        return bool(u) and u.startswith(("http://", "https://"))

    if image_url and image_url.startswith("/static/"):
        rel = image_url.removeprefix("/static/")
        if (_STATIC_ROOT / rel).is_file():
            return image_url
        if _is_remote(source_url):
            return source_url
    if _is_remote(image_url):
        return image_url
    if photo_id and _local_pool_path(photo_id).exists():
        return f"/static/images/pool/{photo_id}.webp"
    if _is_remote(source_url):
        return source_url
    return image_url


def _is_remote_image_url(url: str | None) -> bool:
    return bool(url) and url.startswith(("http://", "https://"))


def _static_image_exists(image_url: str | None) -> bool:
    if not image_url or not image_url.startswith("/static/"):
        return False
    rel = image_url.removeprefix("/static/")
    return (_STATIC_ROOT / rel).is_file()


def destination_image_resolves(dest: dict) -> bool:
    """True si le champ `image` enregistré en admin pointe vers un fichier ou une URL valide."""
    return _is_remote_image_url(dest.get("image")) or _static_image_exists(dest.get("image"))


def pool_image_url(photo_id: str) -> str:
    return f"/static/images/pool/{photo_id}.webp"


def sync_destination_images(*, allow_network: bool = True) -> int:
    """Aligne le store sur des URLs d'image réellement servables (même rendu admin + public).

    - Image pool générique + photo de VILLE committée dans destinations/ → on adopte
      la photo de ville (plus représentative ; cf. _upgrade_to_committed_city_image).
    - Image déjà valide → conservée telle quelle (choix admin).
    - Fichier destinations/ manquant + `image_source_url` → re-télécharge (si allow_network).
    - `image_photo_id` + pool local → met à jour `image` vers /static/images/pool/….
    - Sinon → génère via attach_image_to_destination (référence pool par défaut).
    """
    from admin.store import get_destinations_dict, save_destinations

    dests = get_destinations_dict()
    updated = 0
    for slug, dest in list(dests.items()):
        dest = {**dest, "slug": slug}
        normalized = _normalize_destination_store_record(slug, dest, allow_network=allow_network)
        if normalized:
            dests[slug] = normalized
            updated += 1
            dest = normalized

        upgraded = _upgrade_to_committed_city_image(dest)
        if upgraded:
            dests[slug] = upgraded
            updated += 1
            continue
        aligned = _align_destination_pool_image(dest)
        if aligned:
            dests[slug] = aligned
            updated += 1
            dest = aligned

        if destination_image_resolves(dest):
            continue

        image = (dest.get("image") or "").strip()
        source = (dest.get("image_source_url") or "").strip()
        photo_id = (dest.get("image_photo_id") or "").strip()

        if (
            allow_network
            and source
            and _is_remote_image_url(source)
            and image.startswith("/static/images/destinations/")
        ):
            try:
                _write_remote_webp(source, DEST_IMAGES_DIR / f"{slug}.webp")
                continue
            except Exception:
                pass

        if photo_id and _local_pool_path(photo_id).exists():
            pool_url = pool_image_url(photo_id)
            if image != pool_url:
                dests[slug] = {**dest, "image": pool_url}
                updated += 1
            continue

        meta = attach_image_to_destination(
            dest,
            dest.get("image_prompt"),
            image_nonce=abs(hash(slug)) % 9999,
        )
        dests[slug] = {**dest, **meta}
        updated += 1

    if updated:
        save_destinations(dests)
    return updated


def ensure_all_destination_images() -> int:
    """Alias historique — synchronise les images destination (admin = public)."""
    return sync_destination_images(allow_network=True)


def refresh_all_destination_images_from_sources() -> int:
    """Re-télécharge chaque bannière depuis image_source_url (photos uniques par ville)."""
    from admin.store import get_destinations_dict, save_destinations

    dests = get_destinations_dict()
    updated = 0
    for slug, dest in dests.items():
        source = (dest.get("image_source_url") or "").strip()
        if not _is_remote_image_url(source):
            continue
        try:
            _write_remote_webp(source, DEST_IMAGES_DIR / f"{slug}.webp")
            alt = DESTINATION_IMAGE_ALTS.get(slug) or dest.get("image_alt")
            dests[slug] = {
                **dest,
                "image": _canonical_destination_image_url(slug),
                "image_photo_id": "",
                "image_placeholder": False,
                "image_alt": alt,
            }
            updated += 1
        except Exception as exc:
            log(f"refresh destination image {slug} failed: {exc}")
    if updated:
        save_destinations(dests)
    return updated


def _article_image_meta(article: dict, slug: str, photo_id: str, placeholder: bool,
                        image_url: str | None = None) -> dict:
    city = article.get("city", "")
    title = article.get("title", "Guide voyage Vietnam")
    alt = f"{title} — voyage Vietnam"
    if city and city != "Tout le Vietnam":
        alt = f"{title} — {city}, Vietnam"
    return {
        "image": image_url or f"/static/images/blog/{slug}.webp",
        "image_alt": alt[:140],
        "image_photo_id": photo_id,
        "image_placeholder": placeholder,
    }


def _fetch_vietnam_photo(photo_id: str) -> bytes:
    """Octets d'une vraie photo Vietnam depuis le pool LOCAL embarqué (instantané).

    Plus aucun appel réseau ici : le réseau sortant vers Unsplash, lent/filtré chez
    l'hébergeur, était la cause des blocages. Si le fichier local manque, on lève une
    erreur et l'appelant tente le repli Pixabay puis le logo de marque.
    """
    local = _local_pool_path(photo_id)
    if local.exists():
        data = local.read_bytes()
        if len(data) > 5000:  # WebP local : seuil bas (certaines tiennent en ~25 Ko)
            return data
    raise FileNotFoundError(f"Photo locale absente du pool : {photo_id}")


def _pixabay_query(article: dict) -> str:
    """Construit une requête Pixabay pertinente : Vietnam + ville + thème de l'article."""
    parts = ["Vietnam"]
    city = (article.get("city") or "").strip()
    if city and city != "Tout le Vietnam":
        parts.append(city)
    theme_words = {
        "food": "street food", "market": "market", "beach": "beach",
        "trekking": "mountains", "nature": "landscape", "mountain": "mountains",
        "temple": "temple", "transport": "city", "city": "city", "cruise": "bay",
    }
    for tok in _article_keywords(article):
        if tok in theme_words:
            parts.append(theme_words[tok])
            break
    return " ".join(parts)


def pixabay_photo_url(query: str, seed: int = 0, *, prefer_small: bool = False) -> str:
    """URL d'une photo Pixabay pour `query` (sans téléchargement).

    Nécessite PIXABAY_API_KEY (clé gratuite). Lève une erreur si pas de clé ou pas de résultat.
    """
    key = _pixabay_api_key()
    if not key:
        raise ValueError("PIXABAY_API_KEY absente")

    resp = requests.get(
        PIXABAY_API_URL,
        params={
            "key": key,
            "q": query,
            "image_type": "photo",
            "orientation": "horizontal",
            "safesearch": "true",
            "per_page": 16,
            "lang": "en",
        },
        timeout=(PIXABAY_CONNECT_TIMEOUT, PIXABAY_READ_TIMEOUT),
        headers={"User-Agent": "InsideVietnamTravel/1.0"},
    )
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    if not hits:
        raise ValueError("Aucune image Pixabay pour cette requête")

    hit = hits[seed % len(hits)]
    if prefer_small:
        img_url = hit.get("webformatURL") or hit.get("largeImageURL")
    else:
        img_url = hit.get("largeImageURL") or hit.get("webformatURL")
    if not img_url:
        raise ValueError("URL d'image Pixabay manquante")
    return img_url


def _fetch_pixabay_photo(query: str, seed: int) -> bytes:
    """Repli réseau : photo Vietnam sur Pixabay → octets."""
    raw, _url = _fetch_pixabay_photo_and_url(query, seed)
    return raw


def _fetch_pixabay_photo_and_url(query: str, seed: int) -> tuple[bytes, str]:
    """Pixabay : octets + URL source (repli si encodage local trop lent / FS éphémère)."""
    img_url = pixabay_photo_url(query, seed)
    img = requests.get(
        img_url,
        timeout=(PIXABAY_CONNECT_TIMEOUT, PIXABAY_READ_TIMEOUT),
        headers={"User-Agent": "InsideVietnamTravel/1.0"},
    )
    img.raise_for_status()
    if len(img.content) < 8000:
        raise ValueError("Image Pixabay trop petite")
    return img.content, img_url


def _cover_1200x675(img: Image.Image) -> Image.Image:
    """Recadre au format 16:9 (1200×675) SANS déformer.

    L'ancien resize((1200, 675)) étirait l'image : une photo 4:3 arrivait
    écrasée de ~25 % (visages et monuments déformés). On recadre au centre,
    légèrement vers le haut (0.42) : sur les photos de voyage, le sujet
    (monument, horizon) est plus souvent dans la moitié haute que plein centre.
    """
    return ImageOps.fit(img, (1200, 675), Image.Resampling.LANCZOS, centering=(0.5, 0.42))


# Partenaires recommandés / vitrine : master 1920×1080 (net sur grands écrans Retina).
PARTNER_COVER_SIZE = (1920, 1080)
PARTNER_WEBP_QUALITY = 88
PARTNER_VARIANTS = (
    (640, "-640", 84),
    (960, "-960", 86),
    (1280, "-1280", 88),
)
# method=0 : encodage WebP le plus rapide (Scalingo CPU limité). Les variantes
# -960/-1280 sont générées en tâche de fond ; -640 est écrite en premier pour
# l'aperçu admin et le srcset mobile.
PARTNER_FAST_WEBP_METHOD = 0


def _cover_partner(img: Image.Image) -> Image.Image:
    """Recadre 16:9 haute définition pour couvertures partenaires."""
    return ImageOps.fit(img, PARTNER_COVER_SIZE, Image.Resampling.LANCZOS, centering=(0.5, 0.42))


def _create_partner_responsive_variants(
    img: Image.Image, full_path: Path, *, force: bool = False, webp_method: int | None = None,
) -> None:
    """Variantes srcset partenaires (-640 / -960 / -1280)."""
    method = PARTNER_FAST_WEBP_METHOD if webp_method is None else webp_method
    w, h = img.size
    for target_w, suffix, quality in PARTNER_VARIANTS:
        out = full_path.parent / f"{full_path.stem}{suffix}.webp"
        if out.exists() and not force:
            continue
        nh = max(1, int(h * target_w / w))
        resized = img.resize((target_w, nh), Image.Resampling.LANCZOS)
        resized.save(out, "WEBP", quality=quality, method=method)


def _write_partner_cover_master(
    raw: bytes,
    out_path: Path,
    *,
    prevalidated: bool = False,
    on_thumb_ready: Callable[[], None] | None = None,
) -> None:
    """Master 1920×1080 + variante -640 — un seul décodage PIL."""
    if not prevalidated:
        raw = validate_image_bytes(raw, max_bytes=MAX_PARTNER_COVER_BYTES)
    with _pil_lock:
        img = _cover_partner(_decode_upload_image_unlocked(raw))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        w, h = img.size
        thumb_path = out_path.parent / f"{out_path.stem}-640.webp"
        nh = max(1, int(h * 640 / w))
        img.resize((640, nh), Image.Resampling.LANCZOS).save(
            thumb_path, "WEBP", quality=84, method=PARTNER_FAST_WEBP_METHOD,
        )
        img.save(out_path, "WEBP", quality=PARTNER_WEBP_QUALITY, method=PARTNER_FAST_WEBP_METHOD)
    if on_thumb_ready:
        on_thumb_ready()


def _write_partner_cover_ultrafast(raw: bytes, out_path: Path, *, prevalidated: bool = False) -> None:
    """Repli encodage partenaire — 1280×720, method=0 (Scalingo CPU limité)."""
    if not prevalidated:
        raw = validate_image_bytes(raw, max_bytes=MAX_PARTNER_COVER_BYTES)
    with _pil_lock:
        img = ImageOps.fit(
            _decode_upload_image_unlocked(raw),
            (1280, 720),
            Image.Resampling.BILINEAR,
            centering=(0.5, 0.42),
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "WEBP", quality=80, method=0)
        w, h = img.size
        nh = max(1, int(h * 640 / w))
        img.resize((640, nh), Image.Resampling.BILINEAR).save(
            out_path.parent / f"{out_path.stem}-640.webp", "WEBP", quality=78, method=0,
        )


def _encode_partner_cover(raw: bytes, out_path: Path, *, prevalidated: bool = False) -> None:
    """Encode couverture partenaire — qualité normale puis repli ultra-rapide."""
    try:
        _write_partner_cover_master(raw, out_path, prevalidated=prevalidated)
    except Exception as exc:
        log(f"reco cover master KO {out_path.name} -- {type(exc).__name__}: {exc}")
        _write_partner_cover_ultrafast(raw, out_path, prevalidated=prevalidated)


def _partner_variants_worker(out_path: Path) -> None:
    """Génère les variantes -960/-1280 hors requête HTTP (thread daemon)."""
    try:
        with _pil_lock:
            if not out_path.is_file():
                return
            img = Image.open(out_path).convert("RGB")
            w, h = img.size
            method = PARTNER_FAST_WEBP_METHOD
            for target_w, suffix, quality in PARTNER_VARIANTS:
                if suffix == "-640":
                    continue
                variant = out_path.parent / f"{out_path.stem}{suffix}.webp"
                if variant.is_file():
                    continue
                nh = max(1, int(h * target_w / w))
                img.resize((target_w, nh), Image.Resampling.LANCZOS).save(
                    variant, "WEBP", quality=quality, method=method,
                )
    except Exception:  # noqa: BLE001
        pass


def _schedule_partner_variants(out_path: Path) -> None:
    threading.Thread(target=_partner_variants_worker, args=(out_path,), daemon=True).start()


def _write_partner_gallery_master(raw: bytes, out_path: Path) -> None:
    """Galerie activité — 1200×675, une seule taille (affichée en petit)."""
    with _pil_lock:
        img = _cover_1200x675(_decode_upload_image_unlocked(raw))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "WEBP", quality=82, method=PARTNER_FAST_WEBP_METHOD)


def _to_partner_webp(raw: bytes, out_path: Path) -> None:
    with _pil_lock:
        img = _cover_partner(_decode_upload_image(raw))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "WEBP", quality=PARTNER_WEBP_QUALITY, method=WEBP_METHOD)
        _create_partner_responsive_variants(img, out_path, force=True)


def _write_partner_webp_fast(raw: bytes, out_path: Path) -> None:
    """Repli encodage partenaire — garde les variantes srcset (qualité préservée)."""
    with _pil_lock:
        img = _cover_partner(_decode_upload_image(raw))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "WEBP", quality=86, method=2)
        _create_partner_responsive_variants(img, out_path, force=True)


def _decode_upload_image_unlocked(raw: bytes) -> Image.Image:
    """Décode une image importée (appelant doit tenir _pil_lock si besoin)."""
    with Image.open(io.BytesIO(raw)) as src:
        img = ImageOps.exif_transpose(src)
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            return bg
        if img.mode == "P":
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            return bg
        return img.convert("RGB")


def _decode_upload_image(raw: bytes) -> Image.Image:
    """Décode une image importée : EXIF (rotation iPhone), transparence → fond blanc."""
    with _pil_lock:
        return _decode_upload_image_unlocked(raw)


def _to_webp(raw: bytes, out_path: Path) -> None:
    with _pil_lock:
        img = _cover_1200x675(_decode_upload_image(raw))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "WEBP", quality=82, method=WEBP_METHOD)
        _create_responsive_variants(img, out_path, force=True)


def _write_webp_fast(raw: bytes, out_path: Path) -> None:
    """Écriture WebP minimale (method=0, sans variantes) — repli si l'encodage soigné
    dépasse son échéance. Garantit qu'un fichier image valide existe toujours."""
    with _pil_lock:
        img = _cover_1200x675(_decode_upload_image(raw))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "WEBP", quality=80, method=0)
        for suffix in ("-640", "-960"):
            (out_path.parent / f"{out_path.stem}{suffix}.webp").unlink(missing_ok=True)


def _create_responsive_variants(img: Image.Image, full_path: Path, *, force: bool = False) -> None:
    """Génère -640 et -960 pour les cartes et grilles (chargement plus rapide)."""
    w, h = img.size
    for target_w, suffix, quality in ((640, "-640", 76), (960, "-960", 78)):
        out = full_path.parent / f"{full_path.stem}{suffix}.webp"
        if out.exists() and not force:
            continue
        nh = max(1, int(h * target_w / w))
        resized = img.resize((target_w, nh), Image.Resampling.LANCZOS)
        resized.save(out, "WEBP", quality=quality, method=WEBP_METHOD)


def ensure_responsive_variants() -> int:
    """Crée les variantes manquantes à partir des WebP existants."""
    created = 0
    for directory in (BLOG_IMAGES_DIR, DEST_IMAGES_DIR, PARTNER_IMAGES_DIR):
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.webp")):
            if path.stem.endswith(("-640", "-960", "-1280")):
                continue
            try:
                with _pil_lock:
                    img = Image.open(path).convert("RGB")
                    before = {p.name for p in directory.glob(f"{path.stem}*.webp")}
                    if directory == PARTNER_IMAGES_DIR:
                        _create_partner_responsive_variants(img, path)
                    else:
                        _create_responsive_variants(img, path)
                after = {p.name for p in directory.glob(f"{path.stem}*.webp")}
                if after - before:
                    created += 1
            except Exception:
                continue
    return created


def _gather_article_photo(
    article: dict, ai_prompt: str | None, prompt: str, seed: int, photo_id: str
) -> tuple[bytes, str]:
    """Récupère les octets de l'image (IA opt-in puis photo Vietnam + reprises).

    Tourne sous `_run_with_deadline` : l'échéance murale de 15 s borne l'ensemble, donc
    on garde ici les essais utiles sans plafond interne — le thread est abandonné net
    si la 15ᵉ seconde arrive en plein appel réseau.
    """
    # 1) Génération IA (prompt unique → image unique) — uniquement si activée.
    if (ai_prompt or article.get("ai_generated")) and _ai_images_enabled():
        try:
            return _fetch_remote_image(prompt, seed), photo_id
        except Exception:
            pass

    # 2) Photo Vietnam réelle unique du pool LOCAL (instantané, jamais de blocage).
    try:
        return _fetch_vietnam_photo(photo_id), photo_id
    except Exception:
        for alt_id in [p[0] for p in VIETNAM_PHOTO_POOL if p[0] != photo_id][:2]:
            try:
                return _fetch_vietnam_photo(alt_id), alt_id
            except Exception:
                continue

    # 3) Pool local absent : repli réseau Pixabay (au lieu d'Unsplash).
    try:
        return _fetch_pixabay_photo(_pixabay_query(article), seed), photo_id
    except Exception:
        pass

    raise RuntimeError("Aucune image disponible")


def attach_image_to_article(
    article: dict,
    ai_prompt: str | None = None,
    *,
    force_regenerate: bool = False,
    image_nonce: int | None = None,
    draft_preview: bool = False,
) -> dict:
    """Une image Vietnam unique par article — WebP 1200×675.

    L'étape réseau est bornée à IMAGE_STEP_HARD_DEADLINE (15 s) : au-delà, on bascule
    sur le logo de marque et on signale `image_placeholder` au front (logo animé en
    attendant) — la génération du contenu FR + EN n'est jamais bloquée par l'image.
    """
    slug = article["slug"]
    out_path = BLOG_IMAGES_DIR / f"{slug}.webp"
    nonce = image_nonce if image_nonce is not None else int(time.time())
    photo_id = _pick_unique_photo_id(slug, nonce, article)
    prompt = build_image_prompt(article, ai_prompt)
    seed = abs(hash(f"{slug}-{prompt}-{nonce}")) % 999_999

    t0 = time.time()
    want_ai = bool(ai_prompt or article.get("ai_generated")) and _ai_images_enabled()
    log(f"IMAGE start slug={slug} ai_enabled={_ai_images_enabled()} want_ai={want_ai}")

    if force_regenerate and out_path.exists():
        out_path.unlink()

    # ── Chemin RAPIDE (cas par défaut, image IA désactivée) ───────────────────
    # On RÉFÉRENCE directement la photo du pool (déjà WebP 1200×675, COMMITÉE dans le
    # repo) au lieu d'écrire une copie. Double bénéfice :
    #  • zéro ré-encodage (le conteneur bridé mettait >10 s) ET zéro écriture disque ;
    #  • surtout, l'image est PERSISTANTE : le FS de Scalingo est éphémère, donc une
    #    copie écrite au runtime disparaissait au déploiement suivant (« l'image de
    #    l'article généré disparaît après un push »). Le pool, lui, est dans git.
    if not want_ai:
        dest_slug = _resolve_article_destination_slug(article)
        if dest_slug:
            dest_url = _committed_destination_image_url(dest_slug)
            if dest_url:
                candidates = _photo_ids_for_destination(dest_slug)
                pid = candidates[0] if candidates else photo_id
                log(f"IMAGE done  slug={slug} en {time.time() - t0:.1f}s dest_ref {dest_slug}")
                return _article_image_meta(
                    article, slug, pid, placeholder=False, image_url=dest_url,
                )
        for pid in [photo_id] + [p[0] for p in VIETNAM_PHOTO_POOL if p[0] != photo_id]:
            if _local_pool_path(pid).exists():
                log(f"IMAGE done  slug={slug} en {time.time() - t0:.1f}s pool_ref photo_id={pid}")
                return _article_image_meta(article, slug, pid, placeholder=False,
                                           image_url=f"/static/images/pool/{pid}.webp")
        if draft_preview:
            log(f"IMAGE preview slug={slug} placeholder (pool absent)")
            return _article_image_meta(article, slug, photo_id, placeholder=True)

    if draft_preview:
        log(f"IMAGE preview slug={slug} placeholder (pas de pool local)")
        return _article_image_meta(article, slug, photo_id, placeholder=True)

    # ── Chemin IA / Pixabay (opt-in) ou pool absent : gather + encodage bornés ──
    raw: bytes | None = None
    placeholder = False
    try:
        raw, photo_id = _run_with_deadline(
            _gather_article_photo, IMAGE_STEP_HARD_DEADLINE,
            article, ai_prompt, prompt, seed, photo_id,
        )
    except Exception as exc:  # noqa: BLE001
        log(f"IMAGE gather KO apres {time.time() - t0:.1f}s -- {type(exc).__name__}: {str(exc)[:120]}")
        raw = None

    if raw is None:
        # Échéance dépassée ou réseau indisponible : logo de marque, contenu jamais bloqué.
        raw = _logo_placeholder_webp(slug)
        placeholder = True

    # Encodage borné + tracé : seul maillon nécessitant un vrai encodage (format étranger).
    log(f"IMAGE encode start slug={slug} bytes={len(raw)}")
    try:
        _run_with_deadline(_to_webp, IMAGE_ENCODE_DEADLINE, raw, out_path)
    except Exception as exc:  # noqa: BLE001
        log(f"IMAGE encode KO apres {time.time() - t0:.1f}s -- {type(exc).__name__}: {str(exc)[:120]}")
        _write_webp_fast(raw, out_path)
    log(f"IMAGE done  slug={slug} en {time.time() - t0:.1f}s placeholder={placeholder} photo_id={photo_id}")

    return _article_image_meta(article, slug, photo_id, placeholder)


def regenerate_all_article_images() -> int:
    """Regénère une image unique Vietnam pour chaque article."""
    from admin.store import get_articles, save_articles

    articles = get_articles()
    used_ids: set[str] = set()
    updated = 0

    for i, article in enumerate(articles):
        slug = article["slug"]
        photo_id = SLUG_PHOTO_MAP.get(slug)
        if not photo_id or photo_id in used_ids:
            for pid, _ in VIETNAM_PHOTO_POOL:
                if pid not in used_ids:
                    photo_id = pid
                    break
        used_ids.add(photo_id)

        meta = attach_image_to_article(
            article,
            article.get("image_prompt"),
            force_regenerate=True,
            image_nonce=i + 1,
        )
        meta["image_photo_id"] = photo_id
        articles[i] = {**article, **meta}
        updated += 1

    save_articles(articles)
    return updated


def _pick_destination_photo_id(slug: str, nonce: int = 0) -> str:
    candidates = _photo_ids_for_destination(slug)
    if not candidates:
        candidates = [p[0] for p in VIETNAM_PHOTO_POOL]
    used = set()
    from admin.store import get_destinations_dict
    for d in get_destinations_dict().values():
        if pid := d.get("image_photo_id"):
            used.add(pid)
    start = abs(hash(f"dest-{slug}-{nonce}")) % len(candidates)
    for offset in range(len(candidates)):
        pid = candidates[(start + offset) % len(candidates)]
        if pid not in used:
            return pid
    return candidates[start % len(candidates)]


def build_destination_image_prompt(dest: dict, ai_prompt: str | None = None) -> str:
    if ai_prompt and ai_prompt.strip():
        base = ai_prompt.strip()
        if "vietnam" not in base.lower():
            base += ", Vietnam"
        return base + ", photorealistic travel photography, 16:9, no text, no watermark"
    name = dest.get("name", dest.get("city", "Vietnam"))
    return (
        f"Iconic {name} Vietnam travel destination, landmark or authentic street scene, "
        f"cinematic golden hour, wide 16:9, no text, no watermark"
    )


def attach_image_to_destination(
    dest: dict,
    ai_prompt: str | None = None,
    *,
    force_regenerate: bool = False,
    image_nonce: int | None = None,
    draft_preview: bool = False,
) -> dict:
    slug = dest["slug"]
    out_path = DEST_IMAGES_DIR / f"{slug}.webp"
    nonce = image_nonce if image_nonce is not None else int(time.time())
    photo_id = _pick_destination_photo_id(slug, nonce)
    prompt = build_destination_image_prompt(dest, ai_prompt or dest.get("image_prompt"))
    seed = abs(hash(f"dest-{slug}-{prompt}-{nonce}")) % 999_999
    name = dest.get("name", "Vietnam")

    def _meta(pid: str, placeholder: bool, image_url: str | None = None) -> dict:
        return {
            "image": image_url or f"/static/images/destinations/{slug}.webp",
            "image_alt": f"Guide voyage {name}, Vietnam"[:140],
            "image_photo_id": pid,
            "image_placeholder": placeholder,
        }

    t0 = time.time()
    want_ai = bool(ai_prompt or dest.get("ai_generated") or dest.get("image_prompt")) and _ai_images_enabled()

    if force_regenerate and out_path.exists():
        out_path.unlink()

    # Chemin rapide : RÉFÉRENCE directe d'une photo du pool (commitée → persistante au
    # redéploiement, contrairement à une copie sur le FS éphémère de Scalingo).
    if not want_ai:
        pool_candidates = _photo_ids_for_destination(slug) or [photo_id]
        for pid in pool_candidates:
            if _local_pool_path(pid).exists():
                if draft_preview:
                    log(f"IMAGE dest preview slug={slug} en {time.time() - t0:.1f}s pool_ref photo_id={pid}")
                    return _meta(pid, placeholder=False, image_url=pool_image_url(pid))
                _commit_pool_photo_to_destination(slug, pid)
                log(f"IMAGE dest done slug={slug} en {time.time() - t0:.1f}s pool_commit photo_id={pid}")
                return _meta(pid, placeholder=False, image_url=_canonical_destination_image_url(slug))
        if draft_preview:
            for pid in [photo_id] + [p[0] for p in VIETNAM_PHOTO_POOL]:
                if _local_pool_path(pid).exists():
                    return _meta(pid, placeholder=False, image_url=pool_image_url(pid))
            if out_path.exists():
                return _meta(photo_id, placeholder=False)
            return _meta(photo_id, placeholder=True)

    def _gather() -> tuple[bytes, str]:
        if want_ai:
            try:
                return _fetch_remote_image(prompt, seed), photo_id
            except Exception:
                pass
        try:
            return _fetch_vietnam_photo(photo_id), photo_id
        except Exception:
            for alt_id in _photo_ids_for_destination(slug)[1:3]:
                try:
                    return _fetch_vietnam_photo(alt_id), alt_id
                except Exception:
                    continue
        # Pool local absent : repli réseau Pixabay (au lieu d'Unsplash).
        try:
            query = destination_pixabay_query(slug, dest)
            return _fetch_pixabay_photo(query, seed), photo_id
        except Exception:
            pass
        raise RuntimeError("Aucune image disponible")

    raw: bytes | None = None
    placeholder = False
    try:
        raw, photo_id = _run_with_deadline(_gather, IMAGE_STEP_HARD_DEADLINE)
    except Exception:
        raw = None

    if raw is None:
        raw = _logo_placeholder_webp(slug)
        placeholder = True

    try:
        _run_with_deadline(_to_webp, IMAGE_ENCODE_DEADLINE, raw, out_path)
    except Exception:
        _write_webp_fast(raw, out_path)

    return _meta(photo_id, placeholder)


# ── Image fournie / trouvée sur internet (Linh) ─────────────────────────────

# Taille max d'une image téléchargée depuis le web (octets) — garde-fou mémoire/abus.
MAX_DOWNLOAD_BYTES = 12 * 1024 * 1024
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
_DIRECT_IMAGE_HOST_MARKERS = (
    "upload.wikimedia.org",
    "images.unsplash.com",
    "cdn.pixabay.com",
    "pixabay.com/get/",
    "live.staticflickr.com",
    "i.imgur.com",
)


def _looks_like_direct_image_url(url: str) -> bool:
    path = urllib.parse.urlparse(url).path.lower()
    if "/wiki/file:" in path:
        return False
    if path.endswith(_IMAGE_EXTS):
        return True
    lower = url.lower()
    return any(marker in lower for marker in _DIRECT_IMAGE_HOST_MARKERS)


def _wikimedia_commons_direct_url(page_url: str) -> str | None:
    """Convertit une page Commons /wiki/File:… en URL directe (API Wikimedia)."""
    try:
        path = urllib.parse.urlparse(page_url).path
        if "/wiki/File:" not in path:
            return None
        filename = urllib.parse.unquote(path.split("/wiki/File:", 1)[1].split("#")[0])
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "titles": f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 1200,
                "format": "json",
            },
            timeout=(REMOTE_IMAGE_CONNECT_TIMEOUT, REMOTE_IMAGE_READ_TIMEOUT),
            headers={"User-Agent": "InsideVietnamTravel/1.0"},
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            if page.get("missing"):
                continue
            infos = page.get("imageinfo") or []
            if infos:
                return infos[0].get("thumburl") or infos[0].get("url")
    except Exception:
        return None
    return None


def _extract_og_image_url(page_url: str) -> str | None:
    """Extrait og:image / twitter:image d'une page HTML (galerie, article…).

    Si l'URL sert en réalité une image (Content-Type image/*) sans extension
    visible — fréquent sur Openverse, Flickr, CDN — on la renvoie telle quelle.
    """
    try:
        resp = requests.get(
            page_url,
            timeout=(REMOTE_IMAGE_CONNECT_TIMEOUT, REMOTE_IMAGE_READ_TIMEOUT),
            headers={"User-Agent": "Mozilla/5.0 (compatible; InsideVietnamTravel/1.0)"},
            stream=True,
        )
        resp.raise_for_status()
        if (resp.headers.get("Content-Type") or "").lower().startswith("image/"):
            resp.close()
            return page_url
        buf = bytearray()
        for chunk in resp.iter_content(4096):
            if not chunk:
                continue
            buf.extend(chunk)
            if len(buf) >= 80_000:
                break
        html = bytes(buf).decode("utf-8", errors="ignore")
        patterns = (
            r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::url)?["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        )
        for pattern in patterns:
            match = re.search(pattern, html, re.I)
            if match:
                candidate = urllib.parse.urljoin(page_url, match.group(1).strip())
                if candidate.startswith(("http://", "https://")):
                    return candidate
    except Exception:
        return None
    return None


def resolve_direct_image_url(url: str, *, depth: int = 0) -> str | None:
    """Résout une URL (directe, Commons, page HTML) vers une image téléchargeable."""
    url = (url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        return None
    if _looks_like_direct_image_url(url):
        return url
    if "wikimedia.org/wiki/File:" in url:
        direct = _wikimedia_commons_direct_url(url)
        if direct:
            return direct
    if depth < 1:
        og = _extract_og_image_url(url)
        if og and og != url:
            return resolve_direct_image_url(og, depth=depth + 1)
    return None


def _download_image_bytes(url: str) -> bytes:
    """Télécharge une image depuis une URL http(s) publique (validations + plafond).

    Refuse tout ce qui n'est pas http/https et ce qui ne ressemble pas à une image
    (Content-Type ou extension), borne la taille, et lit en flux pour ne pas charger
    un fichier géant en mémoire. PIL validera ensuite que les octets sont décodables.
    """
    if not url or not url.lower().startswith(("http://", "https://")):
        raise ValueError("URL d'image invalide — fournis une adresse http(s) directe vers une image.")

    resolved = resolve_direct_image_url(url) or url

    # 429/5xx transitoires (rate-limit Wikimedia/Flickr…) : 2 reprises courtes plutôt
    # qu'un échec sec — un lot Linh de 9 images perdait une image sur un simple 429.
    # Les pauses restent courtes pour tenir dans IMAGE_STEP_HARD_DEADLINE (15 s).
    resp = None
    for attempt in range(3):
        resp = requests.get(
            resolved,
            timeout=(REMOTE_IMAGE_CONNECT_TIMEOUT, REMOTE_IMAGE_READ_TIMEOUT),
            headers={"User-Agent": "InsideVietnamTravel/1.0"},
            stream=True,
        )
        if resp.status_code == 429 or resp.status_code >= 500:
            resp.close()
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
        break
    resp.raise_for_status()

    ctype = (resp.headers.get("Content-Type") or "").lower()
    path_lower = urllib.parse.urlparse(resolved).path.lower()
    looks_image = ctype.startswith("image/") or path_lower.endswith(_IMAGE_EXTS)
    if not looks_image:
        raise ValueError(
            f"L'URL ne renvoie pas une image (type : {ctype or 'inconnu'}). "
            "Utilise une URL directe (.jpg/.webp), une page Wikimedia Commons, "
            "ou le paramètre query (ex. « Hue imperial citadel Vietnam ») pour Pixabay."
        )

    data = bytearray()
    for chunk in resp.iter_content(8192):
        if not chunk:
            continue
        data.extend(chunk)
        if len(data) > MAX_DOWNLOAD_BYTES:
            raise ValueError("Image trop volumineuse (> 12 Mo).")
    if len(data) < 1000:
        raise ValueError("Image trop petite ou vide.")
    return bytes(data)


def pixabay_image_url(query: str, seed: int = 0) -> str:
    """Renvoie l'URL d'une photo Pixabay pour `query` (clé gratuite requise)."""
    key = _pixabay_api_key()
    if not key:
        raise ValueError(
            "Recherche d'image par mot-clé indisponible (PIXABAY_API_KEY absente) — "
            "fournis plutôt une URL d'image directe."
        )
    resp = requests.get(
        PIXABAY_API_URL,
        params={
            "key": key, "q": query, "image_type": "photo",
            "orientation": "horizontal", "safesearch": "true", "per_page": 16, "lang": "en",
        },
        timeout=(PIXABAY_CONNECT_TIMEOUT, PIXABAY_READ_TIMEOUT),
        headers={"User-Agent": "InsideVietnamTravel/1.0"},
    )
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    if not hits:
        raise ValueError(f"Aucune image trouvée pour « {query} ».")
    hit = hits[seed % len(hits)]
    img_url = hit.get("largeImageURL") or hit.get("webformatURL")
    if not img_url:
        raise ValueError("URL d'image Pixabay manquante.")
    return img_url


def _write_remote_webp(image_url: str, out_path: Path) -> None:
    """Télécharge `image_url` puis l'encode en WebP 1200×675 (chemins bornés)."""
    raw = _run_with_deadline(_download_image_bytes, IMAGE_STEP_HARD_DEADLINE, image_url)
    try:
        _run_with_deadline(_to_webp, IMAGE_ENCODE_DEADLINE, raw, out_path)
    except Exception:  # noqa: BLE001 — encodage soigné trop lent : version rapide garantie
        _write_webp_fast(raw, out_path)


def _write_remote_partner_webp(image_url: str, out_path: Path) -> None:
    """Télécharge une URL puis encode en WebP partenaire (+ variantes async)."""
    raw = _run_with_deadline(_download_image_bytes, IMAGE_STEP_HARD_DEADLINE, image_url)
    _encode_partner_cover(raw, out_path, prevalidated=True)
    _schedule_partner_variants(out_path)


def set_remote_image_for_article(article: dict, image_url: str, alt: str | None = None) -> dict:
    """Remplace l'image d'un article par une image internet (téléchargée + WebP).

    On conserve l'URL source (`image_source_url`) : si le fichier local disparaît au
    redéploiement (FS éphémère), le rendu retombe dessus (cf. persistent_image_url).
    """
    slug = article["slug"]
    _write_remote_webp(image_url, BLOG_IMAGES_DIR / f"{slug}.webp")
    meta = _article_image_meta(article, slug, "", placeholder=False)
    meta["image_photo_id"] = ""  # plus une photo du pool → repli sur la source internet
    meta["image_source_url"] = image_url
    if alt and alt.strip():
        meta["image_alt"] = alt.strip()[:140]
    return meta


def set_remote_image_for_destination(dest: dict, image_url: str, alt: str | None = None) -> dict:
    """Remplace l'image d'une destination par une image internet (téléchargée + WebP)."""
    slug = dest["slug"]
    _write_remote_webp(image_url, DEST_IMAGES_DIR / f"{slug}.webp")
    name = dest.get("name", dest.get("city", "Vietnam"))
    return {
        "image": f"/static/images/destinations/{slug}.webp",
        "image_alt": (alt.strip() if alt and alt.strip() else f"Guide voyage {name}, Vietnam")[:140],
        "image_photo_id": "",
        "image_placeholder": False,
        "image_source_url": image_url,
    }


MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_PARTNER_COVER_BYTES = 5 * 1024 * 1024


def normalize_image_url(url: str) -> str:
    """Ajoute https:// si l'URL est saisie sans schéma (champ partenaire)."""
    url = (url or "").strip()
    if not url:
        return ""
    if not url.lower().startswith(("http://", "https://")):
        return f"https://{url.lstrip('/')}"
    return url


def validate_image_bytes(raw: bytes, *, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    """Valide les octets d'une image importée avant conversion WebP."""
    if not raw or len(raw) < 200:
        raise ValueError("Fichier image vide ou invalide.")
    if len(raw) > max_bytes:
        max_mb = max(1, max_bytes // (1024 * 1024))
        raise ValueError(f"Photo trop volumineuse (max {max_mb} Mo).")
    try:
        with _pil_lock:
            with Image.open(io.BytesIO(raw)) as img:
                if img.format not in ("JPEG", "PNG", "WEBP", "GIF", "MPO"):
                    raise ValueError("Format non supporté — utilisez JPG, PNG ou WebP.")
                img.load()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Format d'image non supporté (JPG, PNG ou WebP).") from exc
    return raw


def read_uploaded_image_bytes(file_storage) -> bytes:
    """Lit et valide un fichier image importé depuis l'admin (max 12 Mo)."""
    if not file_storage or not getattr(file_storage, "filename", None):
        raise ValueError("Fichier image manquant.")
    raw = file_storage.read()
    return validate_image_bytes(raw, max_bytes=MAX_UPLOAD_BYTES)


def _partner_cover_slug(slug: str) -> str:
    from admin.store import slugify

    safe = re.sub(r"[^a-z0-9\-]+", "-", slugify(slug or "partenaire")).strip("-")[:60]
    return safe or "partenaire"


def partner_cover_paths(slug: str) -> tuple[str, Path, Path]:
    """Chemin public, fichier WebP cible, fichier .upload en attente."""
    safe = _partner_cover_slug(slug)
    out_path = PARTNER_IMAGES_DIR / f"{safe}.webp"
    return f"/static/images/partners/{safe}.webp", out_path, out_path.with_suffix(".upload")


def quick_check_upload_bytes(raw: bytes, *, max_bytes: int = MAX_PARTNER_COVER_BYTES) -> bytes:
    """Contrôle taille sans PIL — réponse HTTP immédiate."""
    if not raw or len(raw) < 200:
        raise ValueError("Fichier image vide ou invalide.")
    if len(raw) > max_bytes:
        max_mb = max(1, max_bytes // (1024 * 1024))
        raise ValueError(f"Photo trop volumineuse (max {max_mb} Mo).")
    return raw


def _encode_partner_cover_file(slug: str, raw: bytes) -> str:
    """Encode octets → WebP partenaire (appelé hors requête HTTP)."""
    local_path, out_path, pending_path = partner_cover_paths(slug)
    PARTNER_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    raw = validate_image_bytes(raw, max_bytes=MAX_PARTNER_COVER_BYTES)
    try:
        _encode_partner_cover(raw, out_path, prevalidated=True)
        _schedule_partner_variants(out_path)
    except Exception as exc:
        log(f"reco cover bg encode KO {slug} -- {type(exc).__name__}: {exc}")
        _write_partner_cover_ultrafast(raw, out_path, prevalidated=True)
    pending_path.unlink(missing_ok=True)
    if not out_path.is_file() or out_path.stat().st_size < 100:
        raise ValueError("La conversion WebP a échoué.")
    return local_path


def _encode_partner_cover_url(slug: str, image_url: str) -> str:
    """Télécharge + encode une URL (hors requête HTTP)."""
    local_path, out_path, _ = partner_cover_paths(slug)
    url = normalize_image_url(image_url)
    raw = _run_with_deadline(_download_image_bytes, IMAGE_STEP_HARD_DEADLINE, url)
    _encode_partner_cover(raw, out_path, prevalidated=True)
    _schedule_partner_variants(out_path)
    return local_path


def store_partner_gallery_webp_fast(partner_slug: str, item_id: str, raw: bytes) -> str:
    """Galerie — encodage rapide 960px (hors requête HTTP)."""
    safe = _partner_cover_slug(partner_slug)
    item_safe = re.sub(r"[^a-z0-9\-]+", "-", (item_id or "img").lower()).strip("-")[:24] or "img"
    gal_dir = PARTNER_IMAGES_DIR / safe
    gal_dir.mkdir(parents=True, exist_ok=True)
    out_path = gal_dir / f"gallery-{item_safe}.webp"
    raw = validate_image_bytes(raw, max_bytes=MAX_PARTNER_COVER_BYTES)
    with _pil_lock:
        img = ImageOps.fit(
            _decode_upload_image_unlocked(raw),
            (960, 540),
            Image.Resampling.BILINEAR,
            centering=(0.5, 0.42),
        )
        img.save(out_path, "WEBP", quality=78, method=0)
    return f"/static/images/partners/{safe}/gallery-{item_safe}.webp"


def store_partner_cover_webp(
    slug: str,
    *,
    file_bytes: bytes | None = None,
    image_url: str = "",
    prevalidated: bool = False,
    on_thumb_ready: Callable[[], None] | None = None,
) -> str:
    """Enregistre la photo de couverture partenaire en WebP 1920×1080 (+ variantes)."""
    safe = _partner_cover_slug(slug)
    try:
        PARTNER_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError("Impossible d'enregistrer la photo sur le serveur — réessayez.") from exc
    out_path = PARTNER_IMAGES_DIR / f"{safe}.webp"
    if file_bytes:
        _encode_partner_cover(file_bytes, out_path, prevalidated=prevalidated)
        if on_thumb_ready:
            on_thumb_ready()
        _schedule_partner_variants(out_path)
    elif (image_url or "").strip():
        url = normalize_image_url(image_url)
        try:
            raw = _run_with_deadline(_download_image_bytes, IMAGE_STEP_HARD_DEADLINE, url)
            _encode_partner_cover(raw, out_path, prevalidated=True)
            _schedule_partner_variants(out_path)
        except (ValueError, TimeoutError) as exc:
            raise ValueError(str(exc)) from exc
        except Exception as exc:
            raise ValueError(
                "Impossible de télécharger ou convertir l'image depuis l'URL."
            ) from exc
    else:
        raise ValueError("Photo manquante — uploadez un fichier ou indiquez une URL.")
    if not out_path.is_file() or out_path.stat().st_size < 100:
        raise ValueError("La conversion WebP a échoué — réessayez avec une autre image.")
    return f"/static/images/partners/{safe}.webp"


def store_partner_gallery_webp(
    partner_slug: str, item_id: str, file_bytes: bytes, *, prevalidated: bool = False,
) -> str:
    """Image galerie partenaire — sous-dossier par slug."""
    safe = _partner_cover_slug(partner_slug)
    item_safe = re.sub(r"[^a-z0-9\-]+", "-", (item_id or "img").lower()).strip("-")[:24] or "img"
    gal_dir = PARTNER_IMAGES_DIR / safe
    try:
        gal_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError("Impossible d'enregistrer la photo sur le serveur — réessayez.") from exc
    out_path = gal_dir / f"gallery-{item_safe}.webp"
    raw = file_bytes if prevalidated else validate_image_bytes(file_bytes, max_bytes=MAX_PARTNER_COVER_BYTES)
    _write_partner_gallery_master(raw, out_path)
    if not out_path.is_file() or out_path.stat().st_size < 100:
        raise ValueError("La conversion WebP a échoué — réessayez avec une autre image.")
    return f"/static/images/partners/{safe}/gallery-{item_safe}.webp"


def _gather_partner_activity_raw(
    *,
    slug: str,
    title: str,
    image_prompt: str | None,
    ai_generated: bool,
) -> tuple[bytes, bool, str]:
    """Télécharge une couverture activité (IA → Pixabay → logo). Retourne (octets, placeholder, source_url)."""
    prompt = (image_prompt or "").strip()
    if prompt and "vietnam" not in prompt.lower():
        prompt += ", Vietnam travel scene"
    if prompt:
        prompt += ", photorealistic, 16:9, no text, no watermark"
    seed = abs(hash(f"{slug}-{prompt}-{title}")) % 999_999
    source_url = ""

    raw: bytes | None = None
    if ai_generated and prompt and _ai_images_enabled():
        try:
            raw = _fetch_remote_image(
                prompt,
                seed,
                width=PARTNER_COVER_SIZE[0],
                height=PARTNER_COVER_SIZE[1],
            )
        except Exception:
            raw = None

    if raw is None:
        try:
            raw, source_url = _fetch_pixabay_photo_and_url(_pixabay_query({"title": title}), seed)
            return raw, False, source_url
        except Exception:
            return _logo_placeholder_webp(slug), True, ""
    return raw, False, source_url


def partner_activity_cover_preview_meta(
    *,
    slug: str,
    title: str,
) -> dict:
    """Couverture brouillon IA — URL Pixabay seulement, sans téléchargement ni PIL (OOM-safe)."""
    safe = _partner_cover_slug(slug)
    local_path = f"/static/images/partners/{safe}.webp"
    alt = (title or "Activité Vietnam")[:140]
    try:
        seed = abs(hash(f"{slug}-{title}")) % 999_999
        source_url = pixabay_photo_url(_pixabay_query({"title": title}), seed)
        return {
            "image": local_path,
            "image_source_url": source_url,
            "image_alt": alt,
            "image_placeholder": False,
        }
    except Exception as exc:
        log(f"reco cover preview KO slug={slug} -- {type(exc).__name__}: {exc}")
        return {
            "image": "",
            "image_alt": alt,
            "image_placeholder": True,
            "image_source_url": "",
        }


def attach_partner_activity_cover(
    *,
    slug: str,
    title: str,
    image_prompt: str | None = None,
    ai_generated: bool = False,
) -> dict:
    """Image de couverture activité partenaire recommandé — WebP local + repli URL source."""
    safe = _partner_cover_slug(slug)
    out_path = PARTNER_IMAGES_DIR / f"{safe}.webp"
    local_path = f"/static/images/partners/{safe}.webp"
    alt = (title or "Activité Vietnam")[:140]
    placeholder = False
    source_url = ""
    try:
        raw, placeholder, source_url = _run_with_deadline(
            _gather_partner_activity_raw,
            IMAGE_STEP_HARD_DEADLINE,
            slug=slug,
            title=title,
            image_prompt=image_prompt,
            ai_generated=ai_generated,
        )
    except Exception as exc:
        log(f"reco cover gather KO slug={slug} -- {type(exc).__name__}: {exc}")
        raw = _logo_placeholder_webp(slug)
        placeholder = True
        source_url = ""

    encoded = False
    try:
        _run_with_deadline(
            lambda: _encode_partner_cover(raw, out_path, prevalidated=True),
            PARTNER_ENCODE_DEADLINE,
        )
        encoded = out_path.is_file() and out_path.stat().st_size >= 100
        if encoded:
            _schedule_partner_variants(out_path)
    except Exception as exc:
        log(f"reco cover encode KO slug={slug} -- {type(exc).__name__}: {exc}")

    meta: dict = {
        "image_alt": alt,
        "image_placeholder": placeholder,
        "image_source_url": source_url,
    }
    if encoded or source_url:
        meta["image"] = local_path
    else:
        meta["image"] = ""
    return meta


def _write_uploaded_webp(raw: bytes, out_path: Path) -> None:
    """Encode un fichier importé en WebP 1200×675 (+ variantes si possible)."""
    try:
        _run_with_deadline(_to_webp, IMAGE_ENCODE_DEADLINE, raw, out_path)
    except Exception:
        _write_webp_fast(raw, out_path)


def set_uploaded_image_for_article(article: dict, raw: bytes, alt: str | None = None) -> dict:
    """Remplace l'image d'un article par un fichier importé (WebP optimisé)."""
    slug = article["slug"]
    _write_uploaded_webp(raw, BLOG_IMAGES_DIR / f"{slug}.webp")
    meta = _article_image_meta(article, slug, "", placeholder=False)
    meta["image_photo_id"] = ""
    meta["image_source_url"] = ""
    if alt and alt.strip():
        meta["image_alt"] = alt.strip()[:140]
    return meta


def set_uploaded_image_for_destination(dest: dict, raw: bytes, alt: str | None = None) -> dict:
    """Remplace l'image d'une destination par un fichier importé (WebP optimisé)."""
    slug = dest["slug"]
    _write_uploaded_webp(raw, DEST_IMAGES_DIR / f"{slug}.webp")
    name = dest.get("name", dest.get("city", "Vietnam"))
    return {
        "image": f"/static/images/destinations/{slug}.webp",
        "image_alt": (alt.strip() if alt and alt.strip() else f"Guide voyage {name}, Vietnam")[:140],
        "image_photo_id": "",
        "image_placeholder": False,
        "image_source_url": "",
    }


