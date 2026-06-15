"""Mots-clés SEO voyage Vietnam — vitrine partenaires (GSC + intentions recherche)."""

from __future__ import annotations

# Requêtes & intentions typiques (complétées par GSC si connecté)
SEED_KEYWORDS_FR = (
    "voyage vietnam",
    "voyage au vietnam",
    "partir au vietnam",
    "guide voyage vietnam",
    "guide local vietnam",
    "guide francophone vietnam",
    "circuit vietnam",
    "itinéraire vietnam",
    "excursion vietnam",
    "visite guidée vietnam",
    "agence locale vietnam",
    "agence voyage vietnam",
    "préparer voyage vietnam",
    "séjour vietnam",
    "tour privé vietnam",
    "que faire vietnam",
    "blog voyage vietnam",
    "influenceur voyage vietnam",
)

SEED_KEYWORDS_EN = (
    "vietnam travel",
    "trip to vietnam",
    "vietnam travel guide",
    "local guide vietnam",
    "vietnam tour",
    "vietnam itinerary",
    "private tour vietnam",
    "vietnam travel agency",
    "vietnam holiday",
    "things to do vietnam",
    "vietnam travel blogger",
    "vietnam travel influencer",
    "plan vietnam trip",
    "vietnam vacation",
)

CITY_KEYWORDS_FR: dict[str, str] = {
    "hanoi": "guide Hanoï, visite Hanoï Vietnam, que faire à Hanoï",
    "hà nội": "guide Hanoï, visite Hanoï Vietnam",
    "ho chi minh": "guide Ho Chi Minh-Ville, Saigon voyage, que faire à Saigon",
    "hô chi minh": "guide Ho Chi Minh-Ville, Saigon voyage",
    "saigon": "guide Saigon, voyage Saigon Vietnam",
    "hoi an": "guide Hội An, visite Hội An Vietnam, ancienne ville",
    "hội an": "guide Hội An, circuit Hội An",
    "da nang": "guide Đà Nẵng, voyage Đà Nẵng",
    "đà nẵng": "guide Đà Nẵng Vietnam",
    "hue": "guide Huế, cité impériale Vietnam",
    "huế": "guide Huế, voyage Huế",
    "halong": "croisière Halong, baie d'Halong voyage",
    "ha long": "baie d'Halong, excursion Halong",
    "sapa": "trek Sapa, rizières Sapa Vietnam",
    "phu quoc": "séjour Phú Quốc, plage Vietnam",
    "phú quốc": "voyage Phú Quốc",
    "mekong": "delta du Mékong, excursion Mékong",
    "nha trang": "guide Nha Trang, plage Vietnam",
    "dalat": "guide Da Lat, hauts plateaux Vietnam",
    "đà lạt": "voyage Da Lat Vietnam",
}

CITY_KEYWORDS_EN: dict[str, str] = {
    "hanoi": "Hanoi guide, Hanoi Vietnam travel, things to do Hanoi",
    "ho chi minh": "Ho Chi Minh City guide, Saigon travel Vietnam",
    "saigon": "Saigon guide, Saigon Vietnam trip",
    "hoi an": "Hoi An guide, Hoi An ancient town Vietnam",
    "da nang": "Da Nang guide, Da Nang Vietnam travel",
    "hue": "Hue guide, imperial city Vietnam",
    "halong": "Halong Bay cruise, Halong Bay tour",
    "sapa": "Sapa trek, Sapa rice terraces Vietnam",
    "phu quoc": "Phu Quoc island, Phu Quoc beach Vietnam",
    "mekong": "Mekong Delta tour Vietnam",
    "nha trang": "Nha Trang guide, beach Vietnam",
    "dalat": "Da Lat guide, Vietnam highlands",
}


def gsc_top_queries(*, limit: int = 25) -> list[str]:
    """Requêtes Search Console (si OAuth actif) — sinon liste vide."""
    try:
        from admin import gsc_service as gsc

        if not gsc.is_connected():
            return []
        site = gsc.ensure_locked_site()
        start, end = gsc._date_range(28)
        payload = gsc.search_analytics_query(
            site, start_date=start, end_date=end, dimensions=["query"], row_limit=limit
        )
        rows = gsc._rows_to_list(payload, ["query"])
        return [r["query"] for r in rows if r.get("query")]
    except Exception:  # noqa: BLE001
        return []


def seed_keywords(lang: str) -> tuple[str, ...]:
    base = SEED_KEYWORDS_EN if lang == "en" else SEED_KEYWORDS_FR
    gsc = gsc_top_queries(limit=15)
    merged: list[str] = []
    seen: set[str] = set()
    for kw in (*gsc, *base):
        key = kw.strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(kw.strip())
    return tuple(merged[:28])


def city_keyword_phrases(city: str, lang: str) -> str:
    city_low = (city or "").strip().lower()
    if not city_low:
        return ""
    mapping = CITY_KEYWORDS_EN if lang == "en" else CITY_KEYWORDS_FR
    for needle, phrase in mapping.items():
        if needle in city_low or city_low in needle:
            return phrase
    label = city.strip()
    if lang == "en":
        return f"{label} Vietnam travel, local guide {label}, things to do {label}"
    return f"voyage {label} Vietnam, guide {label}, que faire {label}"


def _truncate(text: str, max_len: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;—-") + "…"


def _contains_vietnam_intent(text: str, lang: str) -> bool:
    t = (text or "").lower()
    if "vietnam" in t or "viêt nam" in t or "viêt-nam" in t:
        return True
    if lang == "fr" and any(w in t for w in ("voyage", "guide", "circuit", "séjour")):
        return len(t) > 20
    if lang == "en" and any(w in t for w in ("travel", "guide", "tour", "trip")):
        return len(t) > 20
    return False
