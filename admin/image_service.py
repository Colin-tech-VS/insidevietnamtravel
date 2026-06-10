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
from PIL import Image, ImageDraw

from admin.genlog import log

BLOG_IMAGES_DIR = Path(__file__).parent.parent / "static" / "images" / "blog"
DEST_IMAGES_DIR = Path(__file__).parent.parent / "static" / "images" / "destinations"
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
IMAGE_ENCODE_DEADLINE = 10         # secondes max pour l'encodage WebP + variantes

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
    "sapa": ["1480996408299-fc0e830b5db1", "1609412058473-c199497c3c5d"],
    "hoi-an": ["1526139334526-f591a54b477c"],
    "ho-chi-minh-city": ["1603852452378-a4e8d84324a2"],
    "delta-du-mekong": ["1432405972618-c60b0225b8f9", "1559592413-7cec4d0cae2b"],
    "phu-quoc": ["1555979864-7a8f9b4fddf8"],
    "hue": ["1557750255-c76072a7aad1"],
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
        pool_url = pool_image_url(photo_id)
        if image != pool_url:
            return {**dest, "image": pool_url, "image_photo_id": photo_id, "image_placeholder": False}
        return None

    pid = _pick_destination_photo_id(slug, abs(hash(slug)) % 9999)
    return {
        **dest,
        "image": pool_image_url(pid),
        "image_photo_id": pid,
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


def _fetch_remote_image(prompt: str, seed: int) -> bytes:
    encoded = urllib.parse.quote(prompt, safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1200&height=675&nologo=true&seed={seed}&model=flux"
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

    - Image déjà valide → conservée telle quelle (choix admin).
    - Fichier destinations/ manquant + `image_source_url` → re-télécharge (si allow_network).
    - `image_photo_id` + pool local → met à jour `image` vers /static/images/pool/….
    - Sinon → génère via attach_image_to_destination (référence pool par défaut).
    """
    from admin.store import get_destinations_dict, save_destinations

    dests = get_destinations_dict()
    updated = 0
    for slug, dest in dests.items():
        dest = {**dest, "slug": slug}
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


def _fetch_pixabay_photo(query: str, seed: int) -> bytes:
    """Repli réseau : cherche une photo Vietnam sur Pixabay et renvoie ses octets.

    Nécessite PIXABAY_API_KEY (clé gratuite). Sans clé, lève une erreur → logo de marque.
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
    img_url = hit.get("largeImageURL") or hit.get("webformatURL")
    if not img_url:
        raise ValueError("URL d'image Pixabay manquante")

    img = requests.get(
        img_url,
        timeout=(PIXABAY_CONNECT_TIMEOUT, PIXABAY_READ_TIMEOUT),
        headers={"User-Agent": "InsideVietnamTravel/1.0"},
    )
    img.raise_for_status()
    if len(img.content) < 8000:
        raise ValueError("Image Pixabay trop petite")
    return img.content


def _to_webp(raw: bytes, out_path: Path) -> None:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img = img.resize((1200, 675), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=82, method=WEBP_METHOD)
    _create_responsive_variants(img, out_path)


def _write_webp_fast(raw: bytes, out_path: Path) -> None:
    """Écriture WebP minimale (method=0, sans variantes) — repli si l'encodage soigné
    dépasse son échéance. Garantit qu'un fichier image valide existe toujours."""
    img = Image.open(io.BytesIO(raw)).convert("RGB").resize((1200, 675), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=80, method=0)


def _create_responsive_variants(img: Image.Image, full_path: Path) -> None:
    """Génère -640 et -960 pour les cartes et grilles (chargement plus rapide)."""
    w, h = img.size
    for target_w, suffix, quality in ((640, "-640", 76), (960, "-960", 78)):
        out = full_path.parent / f"{full_path.stem}{suffix}.webp"
        if out.exists():
            continue
        nh = max(1, int(h * target_w / w))
        resized = img.resize((target_w, nh), Image.Resampling.LANCZOS)
        resized.save(out, "WEBP", quality=quality, method=WEBP_METHOD)


def ensure_responsive_variants() -> int:
    """Crée les variantes manquantes à partir des WebP existants."""
    created = 0
    for directory in (BLOG_IMAGES_DIR, DEST_IMAGES_DIR):
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.webp")):
            if path.stem.endswith(("-640", "-960")):
                continue
            try:
                img = Image.open(path).convert("RGB")
                before = {p.name for p in directory.glob(f"{path.stem}*.webp")}
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
        for pid in [photo_id] + [p[0] for p in VIETNAM_PHOTO_POOL if p[0] != photo_id]:
            if _local_pool_path(pid).exists():
                log(f"IMAGE done  slug={slug} en {time.time() - t0:.1f}s pool_ref photo_id={pid}")
                return _article_image_meta(article, slug, pid, placeholder=False,
                                           image_url=f"/static/images/pool/{pid}.webp")
        # Aucun fichier pool disponible (anormal) → on bascule sur le chemin réseau/encodage.

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
                log(f"IMAGE dest done slug={slug} en {time.time() - t0:.1f}s pool_ref photo_id={pid}")
                return _meta(pid, placeholder=False, image_url=f"/static/images/pool/{pid}.webp")

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
    """Extrait og:image / twitter:image d'une page HTML (galerie, article…)."""
    try:
        resp = requests.get(
            page_url,
            timeout=(REMOTE_IMAGE_CONNECT_TIMEOUT, REMOTE_IMAGE_READ_TIMEOUT),
            headers={"User-Agent": "Mozilla/5.0 (compatible; InsideVietnamTravel/1.0)"},
            stream=True,
        )
        resp.raise_for_status()
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
    resp = requests.get(
        resolved,
        timeout=(REMOTE_IMAGE_CONNECT_TIMEOUT, REMOTE_IMAGE_READ_TIMEOUT),
        headers={"User-Agent": "InsideVietnamTravel/1.0"},
        stream=True,
    )
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


def read_uploaded_image_bytes(file_storage) -> bytes:
    """Lit et valide un fichier image importé depuis l'admin (max 12 Mo)."""
    if not file_storage or not getattr(file_storage, "filename", None):
        raise ValueError("Fichier image manquant.")
    raw = file_storage.read()
    if not raw or len(raw) < 200:
        raise ValueError("Fichier image vide ou invalide.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Image trop lourde (maximum 12 Mo).")
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.verify()
        with Image.open(io.BytesIO(raw)) as img:
            if img.format not in ("JPEG", "PNG", "WEBP", "GIF"):
                raise ValueError("Format non supporté.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Format d'image non supporté (JPEG, PNG, WebP, GIF).") from exc
    return raw


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


