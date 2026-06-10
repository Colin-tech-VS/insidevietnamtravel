"""Images pool pour les pages itinéraires (fichiers commités dans static/images/pool/)."""

from __future__ import annotations


def pool_img(photo_id: str) -> str:
    return f"/static/images/pool/{photo_id}.webp"


# hero + galerie par slug d'itinéraire
ITINERARY_HERO: dict[str, str] = {
    "3-days-vietnam": pool_img("1555921015-5532091f6026"),
    "7-days-vietnam": pool_img("1521993117367-b7f70ccd029d"),
    "10-days-vietnam": pool_img("1528127269322-539801943592"),
    "15-days-vietnam": pool_img("1521993117367-b7f70ccd029d"),
}

ITINERARY_HERO_ALT: dict[str, str] = {
    "3-days-vietnam": "Street food et Vieux Quartier de Hanoï, Vietnam",
    "7-days-vietnam": "Baie d'Halong au lever du soleil, Vietnam",
    "10-days-vietnam": "Vieille ville de Hội An illuminée, Vietnam",
    "15-days-vietnam": "Jonques traditionnelles dans la baie d'Halong, Vietnam",
}

# photo_id → légende FR (EN via i18n overlay si besoin)
_PHOTO_CAPTIONS_FR: dict[str, str] = {
    "1555921015-5532091f6026": "Hanoï — Vieux Quartier",
    "1521993117367-b7f70ccd029d": "Baie d'Halong",
    "1528127269322-539801943592": "Hội An — lanternes",
    "1545172538-171a802bd867": "Rizières en terrasses, Sapa",
    "1772867342647-6e6d87a0b014": "Citadelle impériale de Huế",
    "1583417319070-4a69db38a482": "Ho Chi Minh-Ville",
    "1555979864-7a8f9b4fddf8": "Plage et skyline Đà Nẵng",
    "1480996408299-fc0e830b5db1": "Phú Quốc — eau turquoise",
}

ITINERARY_GALLERY: dict[str, list[dict]] = {
    "3-days-vietnam": [
        {"photo_id": "1555921015-5532091f6026"},
        {"photo_id": "1583417319070-4a69db38a482"},
        {"photo_id": "1521993117367-b7f70ccd029d"},
    ],
    "7-days-vietnam": [
        {"photo_id": "1555921015-5532091f6026"},
        {"photo_id": "1521993117367-b7f70ccd029d"},
        {"photo_id": "1528127269322-539801943592"},
        {"photo_id": "1555979864-7a8f9b4fddf8"},
    ],
    "10-days-vietnam": [
        {"photo_id": "1555921015-5532091f6026"},
        {"photo_id": "1521993117367-b7f70ccd029d"},
        {"photo_id": "1528127269322-539801943592"},
        {"photo_id": "1583417319070-4a69db38a482"},
    ],
    "15-days-vietnam": [
        {"photo_id": "1555921015-5532091f6026"},
        {"photo_id": "1545172538-171a802bd867"},
        {"photo_id": "1521993117367-b7f70ccd029d"},
        {"photo_id": "1772867342647-6e6d87a0b014"},
        {"photo_id": "1528127269322-539801943592"},
        {"photo_id": "1583417319070-4a69db38a482"},
    ],
}

DAY_PHOTO_DEFAULTS: dict[str, str] = {
    "hanoi": "1555921015-5532091f6026",
    "halong": "1521993117367-b7f70ccd029d",
    "sapa": "1545172538-171a802bd867",
    "ninh-binh": "1521993117367-b7f70ccd029d",
    "hue": "1772867342647-6e6d87a0b014",
    "hoi-an": "1528127269322-539801943592",
    "ho-chi-minh-city": "1583417319070-4a69db38a482",
    "mekong": "1528127269322-539801943592",
}


def attach_itinerary_media(itin: dict) -> dict:
    """Ajoute hero_image, image_alt et galerie résolue au dict itinéraire."""
    slug = itin.get("slug", "")
    itin = {**itin}
    if slug in ITINERARY_HERO:
        itin["hero_image"] = ITINERARY_HERO[slug]
        itin["image_alt"] = ITINERARY_HERO_ALT.get(slug, itin.get("title", "Vietnam"))
    gallery_raw = ITINERARY_GALLERY.get(slug, [])
    itin["gallery"] = [
        {
            "image": pool_img(item["photo_id"]),
            "caption": item.get("caption") or _PHOTO_CAPTIONS_FR.get(item["photo_id"], ""),
            "alt": item.get("alt") or _PHOTO_CAPTIONS_FR.get(item["photo_id"], "Vietnam"),
        }
        for item in gallery_raw
    ]
    days = []
    for day in itin.get("days", []):
        d = dict(day)
        if not d.get("image") and d.get("location_slug"):
            pid = DAY_PHOTO_DEFAULTS.get(d["location_slug"])
            if pid:
                d["image"] = pool_img(pid)
        days.append(d)
    itin["days"] = days
    return itin
