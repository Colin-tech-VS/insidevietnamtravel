"""Images pool pour les pages itinéraires — une photo distincte par ville/étape."""

from __future__ import annotations

from collections import defaultdict


def pool_img(photo_id: str) -> str:
    return f"/static/images/pool/{photo_id}.webp"


# photo_id → légende FR
_PHOTO_CAPTIONS_FR: dict[str, str] = {
    "1555921015-5532091f6026": "Hanoï — Train Street",
    "1521993117367-b7f70ccd029d": "Hanoï — vie de rue",
    "1578662996442-48f60103fc96": "Temple et architecture vietnamienne",
    "1772867342647-6e6d87a0b014": "Baie d'Halong — îlots karstiques",
    "1545172538-171a802bd867": "Baie d'Halong — kayak",
    "1531737212413-667205e1cda7": "Sapa — rizières en terrasses",
    "1480996408299-fc0e830b5db1": "Sapa — montagnes tropicales",
    "1609412058473-c199497c3c5d": "Hauts plateaux — paysage verdoyant",
    "1557750255-c76072a7aad1": "Ninh Bình — pagode et pains de sucre",
    "1602646993875-70bc0ba52c87": "Ninh Bình — formations rocheuses",
    "1528127269322-539801943592": "Hội An — vieille ville et rivière",
    "1526139334526-f591a54b477c": "Hội An — marché nocturne et lanternes",
    "1555979864-7a8f9b4fddf8": "Đà Nẵng — plage et skyline",
    "1583417319070-4a69db38a482": "Ho Chi Minh-Ville — skyline",
    "1603852452378-a4e8d84324a2": "Ho Chi Minh-Ville — vue aérienne",
    "1605649487212-47bdab064df7": "Delta du Mékong — campagne et canaux",
    "1432405972618-c60b0225b8f9": "Delta du Mékong — nature tropicale",
    "1559592413-7cec4d0cae2b": "Village et pont du delta",
}

# Images dédiées (fichiers destinations admin)
_DEST_HUE = "/static/images/destinations/hue.webp"
_DEST_MEKONG = "/static/images/destinations/delta-du-mekong.webp"

# Par ville : liste ordonnée (rotation si plusieurs jours dans la même ville)
# Entrée = photo_id pool OU tuple ("dest", url, alt)
LOCATION_PHOTOS: dict[str, list] = {
    "hanoi": [
        "1555921015-5532091f6026",
        "1521993117367-b7f70ccd029d",
        "1578662996442-48f60103fc96",
    ],
    "halong": [
        "1772867342647-6e6d87a0b014",
        "1545172538-171a802bd867",
    ],
    "sapa": [
        "1531737212413-667205e1cda7",
        "1480996408299-fc0e830b5db1",
        "1609412058473-c199497c3c5d",
    ],
    "ninh-binh": [
        "1557750255-c76072a7aad1",
        "1602646993875-70bc0ba52c87",
    ],
    "hue": [
        ("dest", _DEST_HUE, "Citadelle impériale de Huế"),
        "1578662996442-48f60103fc96",
    ],
    "hoi-an": [
        "1528127269322-539801943592",
        "1526139334526-f591a54b477c",
        "1559592413-7cec4d0cae2b",
    ],
    "da-nang": [
        "1555979864-7a8f9b4fddf8",
    ],
    "ho-chi-minh-city": [
        "1583417319070-4a69db38a482",
        "1603852452378-a4e8d84324a2",
    ],
    "delta-du-mekong": [
        ("dest", _DEST_MEKONG, "Delta du Mékong — sampan et marché fluvial"),
        "1605649487212-47bdab064df7",
        "1432405972618-c60b0225b8f9",
        "1559592413-7cec4d0cae2b",
    ],
    # alias utilisé dans certains jours transit
    "mekong": [
        ("dest", _DEST_MEKONG, "Delta du Mékong — sampan et marché fluvial"),
        "1605649487212-47bdab064df7",
    ],
}

ITINERARY_HERO: dict[str, str] = {
    "3-days-vietnam": pool_img("1555921015-5532091f6026"),
    "7-days-vietnam": pool_img("1772867342647-b7f70ccd029d"),
    "10-days-vietnam": pool_img("1528127269322-539801943592"),
    "15-days-vietnam": pool_img("1531737212413-667205e1cda7"),
}

ITINERARY_HERO_ALT: dict[str, str] = {
    "3-days-vietnam": "visiter vietnam hanoï",
    "7-days-vietnam": "visiter vietnam baie d'halong",
    "10-days-vietnam": "visiter vietnam hội an",
    "15-days-vietnam": "visiter vietnam sapa",
}

# Galerie = une photo par ville du circuit (sans doublon)
ITINERARY_GALLERY: dict[str, list[dict]] = {
    "3-days-vietnam": [
        {"photo_id": "1555921015-5532091f6026"},
        {"photo_id": "1772867342647-b7f70ccd029d"},
        {"photo_id": "1526139334526-f591a54b477c"},
    ],
    "7-days-vietnam": [
        {"photo_id": "1555921015-5532091f6026"},
        {"photo_id": "1772867342647-b7f70ccd029d"},
        {"photo_id": "1528127269322-539801943592"},
        {"photo_id": "1555979864-7a8f9b4fddf8"},
    ],
    "10-days-vietnam": [
        {"photo_id": "1555921015-5532091f6026"},
        {"photo_id": "1772867342647-b7f70ccd029d"},
        {"photo_id": "1528127269322-539801943592"},
        {"photo_id": "1583417319070-4a69db38a482"},
        {"dest": _DEST_MEKONG, "caption": "Delta du Mékong — canaux et sampan", "alt": "Delta du Mékong, Vietnam"},
    ],
    "15-days-vietnam": [
        {"photo_id": "1555921015-5532091f6026"},
        {"photo_id": "1531737212413-667205e1cda7"},
        {"photo_id": "1557750255-c76072a7aad1"},
        {"photo_id": "1772867342647-b7f70ccd029d"},
        {"dest": _DEST_HUE, "caption": "Citadelle impériale de Huế", "alt": "Huế, Vietnam"},
        {"photo_id": "1528127269322-539801943592"},
        {"photo_id": "1583417319070-4a69db38a482"},
        {"dest": _DEST_MEKONG, "caption": "Delta du Mékong — marché fluvial", "alt": "Delta du Mékong, Vietnam"},
    ],
}


def _resolve_photo_entry(entry) -> tuple[str, str]:
    """Retourne (url, alt) pour une entrée pool ou dest."""
    if isinstance(entry, tuple) and entry[0] == "dest":
        return entry[1], entry[2] if len(entry) > 2 else "Vietnam"
    photo_id = entry
    return pool_img(photo_id), _PHOTO_CAPTIONS_FR.get(photo_id, "Vietnam")


def _resolve_gallery_item(item: dict) -> dict:
    if item.get("dest"):
        return {
            "image": item["dest"],
            "caption": item.get("caption", ""),
            "alt": item.get("alt", item.get("caption", "Vietnam")),
        }
    photo_id = item["photo_id"]
    return {
        "image": pool_img(photo_id),
        "caption": item.get("caption") or _PHOTO_CAPTIONS_FR.get(photo_id, ""),
        "alt": item.get("alt") or _PHOTO_CAPTIONS_FR.get(photo_id, "Vietnam"),
    }


def _day_image_for_location(location_slug: str, index: int) -> tuple[str, str]:
    photos = LOCATION_PHOTOS.get(location_slug, [])
    if not photos:
        return "", ""
    entry = photos[index % len(photos)]
    return _resolve_photo_entry(entry)


def attach_itinerary_media(itin: dict) -> dict:
    """Ajoute hero_image, galerie et images jour par jour (distinctes par ville)."""
    slug = itin.get("slug", "")
    itin = {**itin}
    if slug in ITINERARY_HERO:
        itin["hero_image"] = ITINERARY_HERO[slug]
        itin["image_alt"] = ITINERARY_HERO_ALT.get(slug, itin.get("title", "Vietnam"))

    itin["gallery"] = [
        _resolve_gallery_item(item)
        for item in ITINERARY_GALLERY.get(slug, [])
    ]

    location_counters: dict[str, int] = defaultdict(int)
    days = []
    for day in itin.get("days", []):
        d = dict(day)
        loc = d.get("location_slug")
        if not d.get("image") and loc:
            idx = location_counters[loc]
            url, alt = _day_image_for_location(loc, idx)
            if url:
                d["image"] = url
                d["image_alt"] = alt
                location_counters[loc] += 1
        days.append(d)
    itin["days"] = days
    return itin
