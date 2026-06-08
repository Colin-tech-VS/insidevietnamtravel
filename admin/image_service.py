"""Images d'articles — une photo Vietnam unique par article, export WebP optimisé."""

from __future__ import annotations

import io
import time
import urllib.parse
from pathlib import Path

import requests
from PIL import Image, ImageDraw

BLOG_IMAGES_DIR = Path(__file__).parent.parent / "static" / "images" / "blog"
DEST_IMAGES_DIR = Path(__file__).parent.parent / "static" / "images" / "destinations"

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

# Photos Vietnam par page destination publique
DESTINATION_PHOTO_MAP: dict[str, str] = {
    "hanoi": "1555921015-5532091f6026",
    "ho-chi-minh-city": "1583417319070-4a69db38a482",
    "hoi-an": "1528127269322-539801943592",
    "da-nang": "1555979864-7a8f9b4fddf8",
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


def _photo_url(photo_id: str) -> str:
    return (
        f"https://images.unsplash.com/photo-{photo_id}"
        f"?w=1200&h=675&fit=crop&q=80&auto=format"
    )


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


def _pick_unique_photo_id(slug: str, nonce: int = 0) -> str:
    if slug in SLUG_PHOTO_MAP:
        return SLUG_PHOTO_MAP[slug]

    used = _used_photo_ids(exclude_slug=slug)
    pool_ids = [p[0] for p in VIETNAM_PHOTO_POOL]

    start = (abs(hash(f"{slug}-{nonce}")) % len(pool_ids))
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
    resp = requests.get(url, timeout=120, headers={"User-Agent": "InsideVietnamTravel/1.0"})
    resp.raise_for_status()
    if len(resp.content) < 8000:
        raise ValueError("Image IA invalide")
    return resp.content


def _fetch_vietnam_photo(photo_id: str) -> bytes:
    resp = requests.get(
        _photo_url(photo_id),
        timeout=60,
        headers={"User-Agent": "InsideVietnamTravel/1.0"},
    )
    resp.raise_for_status()
    if len(resp.content) < 30000:
        raise ValueError("Photo Vietnam trop petite")
    return resp.content


def _to_webp(raw: bytes, out_path: Path) -> None:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img = img.resize((1200, 675), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=82, method=6)
    _create_responsive_variants(img, out_path)


def _create_responsive_variants(img: Image.Image, full_path: Path) -> None:
    """Génère -640 et -960 pour les cartes et grilles (chargement plus rapide)."""
    w, h = img.size
    for target_w, suffix, quality in ((640, "-640", 76), (960, "-960", 78)):
        out = full_path.parent / f"{full_path.stem}{suffix}.webp"
        if out.exists():
            continue
        nh = max(1, int(h * target_w / w))
        resized = img.resize((target_w, nh), Image.Resampling.LANCZOS)
        resized.save(out, "WEBP", quality=quality, method=6)


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


def attach_image_to_article(
    article: dict,
    ai_prompt: str | None = None,
    *,
    force_regenerate: bool = False,
    image_nonce: int | None = None,
) -> dict:
    """Une image Vietnam unique par article — WebP 1200×675."""
    slug = article["slug"]
    out_path = BLOG_IMAGES_DIR / f"{slug}.webp"
    nonce = image_nonce if image_nonce is not None else int(time.time())
    photo_id = _pick_unique_photo_id(slug, nonce)
    prompt = build_image_prompt(article, ai_prompt)
    seed = abs(hash(f"{slug}-{prompt}-{nonce}")) % 999_999

    raw: bytes | None = None

    # 1) Génération IA (prompt unique → image unique)
    if ai_prompt or article.get("ai_generated"):
        try:
            raw = _fetch_remote_image(prompt, seed)
        except Exception:
            raw = None

    # 2) Photo Vietnam réelle unique du pool
    if raw is None:
        try:
            raw = _fetch_vietnam_photo(photo_id)
        except Exception:
            for alt_id in [p[0] for p in VIETNAM_PHOTO_POOL]:
                if alt_id == photo_id:
                    continue
                try:
                    raw = _fetch_vietnam_photo(alt_id)
                    photo_id = alt_id
                    break
                except Exception:
                    continue

    if raw is None:
        raw = _fallback_gradient_webp(slug)

    if force_regenerate and out_path.exists():
        out_path.unlink()
    _to_webp(raw, out_path)

    city = article.get("city", "")
    title = article.get("title", "Guide voyage Vietnam")
    alt = f"{title} — voyage Vietnam"
    if city and city != "Tout le Vietnam":
        alt = f"{title} — {city}, Vietnam"

    return {
        "image": f"/static/images/blog/{slug}.webp",
        "image_alt": alt[:140],
        "image_photo_id": photo_id,
    }


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
    if slug in DESTINATION_PHOTO_MAP:
        return DESTINATION_PHOTO_MAP[slug]
    used = set()
    from admin.store import get_destinations_dict
    for d in get_destinations_dict().values():
        if pid := d.get("image_photo_id"):
            used.add(pid)
    pool_ids = [p[0] for p in VIETNAM_PHOTO_POOL]
    start = abs(hash(f"dest-{slug}-{nonce}")) % len(pool_ids)
    for offset in range(len(pool_ids)):
        pid = pool_ids[(start + offset) % len(pool_ids)]
        if pid not in used:
            return pid
    return pool_ids[start % len(pool_ids)]


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

    raw: bytes | None = None
    if ai_prompt or dest.get("ai_generated") or dest.get("image_prompt"):
        try:
            raw = _fetch_remote_image(prompt, seed)
        except Exception:
            raw = None

    if raw is None:
        try:
            raw = _fetch_vietnam_photo(photo_id)
        except Exception:
            for alt_id in [p[0] for p in VIETNAM_PHOTO_POOL if p[0] != photo_id]:
                try:
                    raw = _fetch_vietnam_photo(alt_id)
                    photo_id = alt_id
                    break
                except Exception:
                    continue

    if raw is None:
        raw = _fallback_gradient_webp(slug)

    if force_regenerate and out_path.exists():
        out_path.unlink()
    _to_webp(raw, out_path)

    name = dest.get("name", "Vietnam")
    return {
        "image": f"/static/images/destinations/{slug}.webp",
        "image_alt": f"Guide voyage {name}, Vietnam"[:140],
        "image_photo_id": photo_id,
    }


def ensure_all_destination_images() -> int:
    """Génère les images manquantes pour toutes les destinations."""
    from admin.store import get_destinations_dict, save_destinations

    dests = get_destinations_dict()
    updated = 0
    for slug, dest in dests.items():
        path = DEST_IMAGES_DIR / f"{slug}.webp"
        if dest.get("image") and path.exists():
            continue
        meta = attach_image_to_destination(dest, dest.get("image_prompt"), image_nonce=abs(hash(slug)) % 9999)
        dests[slug] = {**dest, **meta}
        updated += 1
    if updated:
        save_destinations(dests)
    return updated
