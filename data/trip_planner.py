"""Profils voyage — moteur de recommandations « Préparer mon voyage »."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable

GROUP_KEYS = ("solo", "couple", "family", "friends")

# ── Villes proposées à l'étape « Où aller ? » (ordre Nord → Sud) ──────
# region : north / central / south (sert aux conseils saisonniers + budget transport).
PLANNER_CITIES: list[dict] = [
    {"slug": "hanoi", "region": "north"},
    {"slug": "halong", "region": "north"},
    {"slug": "sapa", "region": "north"},
    {"slug": "hue", "region": "central"},
    {"slug": "da-nang", "region": "central"},
    {"slug": "hoi-an", "region": "central"},
    {"slug": "ho-chi-minh-city", "region": "south"},
    {"slug": "delta-du-mekong", "region": "south"},
    {"slug": "phu-quoc", "region": "south"},
]

CITY_REGION = {c["slug"]: c["region"] for c in PLANNER_CITIES}

REGION_ORDER = ("north", "central", "south")

REGION_LABELS_FR = {"north": "Nord", "central": "Centre", "south": "Sud"}


def _normalize_place(text: Any) -> str:
    """« Cát Bà » / « cat-ba » / « Cat Ba » → « cat ba » (clé de comparaison)."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _city_name_regions() -> dict[str, str]:
    from data.vietnam_cities import VIETNAM_CITIES

    group_region = {"Nord": "north", "Centre": "central", "Sud": "south"}
    out: dict[str, str] = {}
    for group, cities in VIETNAM_CITIES.items():
        region = group_region.get(group)
        if not region:
            continue
        for city in cities:
            for part in city["value"].split("/"):
                key = _normalize_place(part)
                if key:
                    out[key] = region
    return out


CITY_NAME_REGION = _city_name_regions()


def resolve_region(slug: str, dest: dict | None = None) -> str:
    """Région d'une destination : champ explicite > slug connu > ville/nom."""
    dest = dest or {}
    region = str(dest.get("region") or "").strip().lower()
    if region in REGION_ORDER:
        return region
    if slug in CITY_REGION:
        return CITY_REGION[slug]
    for candidate in (dest.get("city"), dest.get("name"), slug):
        key = _normalize_place(candidate)
        if key and key in CITY_NAME_REGION:
            return CITY_NAME_REGION[key]
    return "central"


def destinations_by_region(
    destinations: dict,
    lang: str = "fr",
    t_fn: Callable[[str, str], str] | None = None,
) -> list[dict]:
    """Regroupe les destinations publiées par région (Nord → Centre → Sud)."""
    if t_fn is None:
        from locales.ui import t as t_fn

    slug_order = {c["slug"]: i for i, c in enumerate(PLANNER_CITIES)}
    buckets: dict[str, list[dict]] = {k: [] for k in REGION_ORDER}

    for slug, dest in destinations.items():
        region = resolve_region(slug, dest)
        if region not in buckets:
            region = "central"
        buckets[region].append({
            "slug": slug,
            "name": dest.get("name", slug),
            "tagline": dest.get("tagline", ""),
            "_order": slug_order.get(slug, 999),
        })

    grouped: list[dict] = []
    for key in REGION_ORDER:
        items = buckets[key]
        if not items:
            continue
        items.sort(key=lambda x: (x["_order"], x["name"].lower()))
        grouped.append({
            "key": key,
            "label": t_fn(f"prepare.region.{key}", lang),
            "destinations": [
                {k: v for k, v in item.items() if k != "_order"}
                for item in items
            ],
        })
    return grouped


# ── Estimation budget ─────────────────────────────────────────────────
# Palier de budget par style de voyage (clé des paliers de data.travel_tools).
STYLE_BUDGET_TIER = {
    "culture": "comfort",
    "food": "comfort",
    "adventure": "comfort",
    "romantic": "comfort",
    "roadtrip": "comfort",
    "relax": "comfort",
    "budget": "backpacker",
}

# Taille du groupe par défaut (pour le total « groupe »).
GROUP_SIZE = {"solo": 1, "couple": 2, "family": 4, "friends": 3}

# Nombre de jours par durée.
DURATION_DAYS = {"short": 7, "medium": 10, "long": 14}

# Transport entre deux villes (par personne et par trajet : train/bus/vol interne).
INTERCITY_PER_LEG = 18

# ── Conseils contextuels (bilingues) ──────────────────────────────────
TIPS_GENERAL = [
    {
        "fr": "Demandez votre e-visa sur evisa.gov.vn 7 à 10 jours avant le départ (≈ 25 $).",
        "en": "Apply for your e-visa on evisa.gov.vn 7–10 days before departure (≈ $25).",
    },
    {
        "fr": "Installez l'application Grab pour vos trajets : bien moins cher que les taxis de rue.",
        "en": "Install the Grab app for getting around — far cheaper than street taxis.",
    },
    {
        "fr": "Activez une eSIM dès l'atterrissage pour rester connecté sans frais d'itinérance.",
        "en": "Activate an eSIM on landing to stay connected with no roaming fees.",
    },
    {
        "fr": "Retirez des dongs au distributeur et gardez du liquide pour les petits commerces.",
        "en": "Withdraw dong from ATMs and keep cash for small shops and markets.",
    },
]

TIPS_BY_STYLE = {
    "culture": [{
        "fr": "Prévoyez une tenue couvrant épaules et genoux pour les temples et pagodes.",
        "en": "Pack clothing that covers shoulders and knees for temples and pagodas.",
    }],
    "food": [{
        "fr": "Mangez là où il y a foule et rotation : c'est le gage d'une street food fraîche.",
        "en": "Eat where there are crowds and turnover — a sign of fresh street food.",
    }],
    "adventure": [{
        "fr": "Souscrivez une assurance couvrant trek et scooter avant les activités à risque.",
        "en": "Get insurance covering trekking and scooters before any adventure activity.",
    }],
    "romantic": [{
        "fr": "Réservez un dîner au coucher du soleil à Hội An et une nuit en jonque à Halong.",
        "en": "Book a sunset dinner in Hội An and a junk-boat night in Halong Bay.",
    }],
    "roadtrip": [{
        "fr": "Réservez les trains de nuit (couchettes molles) à l'avance sur les axes populaires.",
        "en": "Book night trains (soft sleepers) in advance on popular routes.",
    }],
    "relax": [{
        "fr": "Calez votre séjour sur la saison sèche de votre région pour profiter des plages.",
        "en": "Time your trip to your region's dry season to enjoy the beaches.",
    }],
    "budget": [{
        "fr": "Privilégiez bus de nuit et dortoirs ; un repas de rue coûte 1 à 3 €.",
        "en": "Favour night buses and dorms; a street meal costs €1–3.",
    }],
}

TIPS_BY_GROUP = {
    "solo": [{
        "fr": "Auberges et free walking tours facilitent les rencontres quand on voyage seul.",
        "en": "Hostels and free walking tours make it easy to meet people when solo.",
    }],
    "couple": [{
        "fr": "De nombreux hôtels offrent un surclassement « lune de miel » — pensez à demander.",
        "en": "Many hotels offer a free honeymoon upgrade — just ask at check-in.",
    }],
    "family": [{
        "fr": "Prévoyez un rythme plus lent et des hôtels avec piscine pour les enfants.",
        "en": "Plan a slower pace and hotels with a pool to keep kids happy.",
    }],
    "friends": [{
        "fr": "Réservez un logement entier (Booking/Agoda) pour partager les frais à plusieurs.",
        "en": "Book a whole place (Booking/Agoda) to split costs across the group.",
    }],
}

TIPS_BY_REGION = {
    "north": [{
        "fr": "Nord (Hanoï, Halong, Sapa) : idéal d'octobre à avril ; prévoyez une laine en hiver.",
        "en": "North (Hanoi, Halong, Sapa): best Oct–Apr; bring a layer in winter.",
    }],
    "central": [{
        "fr": "Centre (Huế, Đà Nẵng, Hội An) : évitez octobre–novembre (pluies et typhons).",
        "en": "Central (Hue, Da Nang, Hoi An): avoid October–November (rain and typhoons).",
    }],
    "south": [{
        "fr": "Sud (HCMV, Mékong, Phú Quốc) : saison sèche de novembre à avril, averses brèves sinon.",
        "en": "South (HCMC, Mekong, Phu Quoc): dry season Nov–Apr, brief showers otherwise.",
    }],
}

STYLE_KEYS = (
    "culture",
    "food",
    "adventure",
    "romantic",
    "roadtrip",
    "relax",
    "budget",
)

DURATION_KEYS = ("short", "medium", "long")

DURATION_ITINERARIES: dict[str, list[str]] = {
    "short": ["7-days-vietnam"],
    "medium": ["10-days-vietnam"],
    "long": ["15-days-vietnam", "10-days-vietnam"],
}

GROUP_BOOST: dict[str, dict] = {
    "family": {"duration": "medium"},
    "couple": {"duration": "medium"},
    "friends": {"duration": "medium"},
    "solo": {"duration": "short"},
}

TRIP_PROFILES: dict[str, dict] = {
    "culture": {
        "destination_slugs": ["hanoi", "hoi-an", "ho-chi-minh-city"],
        "itinerary_slugs": ["10-days-vietnam", "7-days-vietnam"],
        "article_slugs": [
            "visa-vietnam-guide-complet-francais",
            "transport-vietnam-train-bus-vol",
            "train-reunification-hanoi-saigon",
            "vols-interieurs-vietnam",
            "location-scooter-vietnam",
        ],
        "categories": ["practical", "itinerary"],
    },
    "food": {
        "destination_slugs": ["hanoi", "hoi-an", "ho-chi-minh-city"],
        "itinerary_slugs": ["7-days-vietnam", "10-days-vietnam"],
        "article_slugs": [
            "meilleurs-restaurants-hanoi",
            "plats-incontournables-vietnam",
            "cafe-vietnamien-guide",
            "budget-voyage-vietnam-2026",
        ],
        "categories": ["food", "practical"],
    },
    "adventure": {
        "destination_slugs": ["hanoi", "ho-chi-minh-city", "da-nang"],
        "itinerary_slugs": ["10-days-vietnam", "7-days-vietnam"],
        "article_slugs": [
            "securite-voyage-vietnam-conseils",
            "transport-vietnam-train-bus-vol",
            "train-reunification-hanoi-saigon",
            "vols-interieurs-vietnam",
            "location-scooter-vietnam",
        ],
        "categories": ["practical", "itinerary"],
    },
    "romantic": {
        "destination_slugs": ["hoi-an", "da-nang", "hanoi"],
        "itinerary_slugs": ["10-days-vietnam", "7-days-vietnam"],
        "article_slugs": ["budget-voyage-vietnam-2026", "carte-sim-esim-vietnam"],
        "categories": ["practical", "food"],
    },
    "roadtrip": {
        "destination_slugs": ["hanoi", "hoi-an", "ho-chi-minh-city", "da-nang"],
        "itinerary_slugs": ["10-days-vietnam"],
        "article_slugs": [
            "transport-vietnam-train-bus-vol",
            "train-reunification-hanoi-saigon",
            "vols-interieurs-vietnam",
            "location-scooter-vietnam",
            "budget-voyage-vietnam-2026",
            "carte-sim-esim-vietnam",
        ],
        "categories": ["practical", "itinerary"],
    },
    "relax": {
        "destination_slugs": ["hoi-an", "da-nang", "ho-chi-minh-city"],
        "itinerary_slugs": ["7-days-vietnam", "10-days-vietnam"],
        "article_slugs": ["budget-voyage-vietnam-2026", "securite-voyage-vietnam-conseils"],
        "categories": ["practical", "food"],
    },
    "budget": {
        "destination_slugs": ["hanoi", "hoi-an", "ho-chi-minh-city"],
        "itinerary_slugs": ["7-days-vietnam"],
        "article_slugs": [
            "budget-voyage-vietnam-2026",
            "carte-sim-esim-vietnam",
            "transport-vietnam-train-bus-vol",
            "train-reunification-hanoi-saigon",
            "vols-interieurs-vietnam",
            "location-scooter-vietnam",
        ],
        "categories": ["practical", "budget"],
    },
}


def _uniq(seq: list) -> list:
    seen: set = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def resolve_recommendations(
    group: str,
    style: str,
    duration: str,
    *,
    articles: list[dict],
    itineraries: dict,
    destinations: dict,
    categories: dict,
) -> dict:
    """Retourne itinéraires, destinations, articles et catégories pour le profil choisi."""
    group = group if group in GROUP_KEYS else "couple"
    style = style if style in STYLE_KEYS else "culture"
    duration = duration if duration in DURATION_KEYS else "medium"

    profile = TRIP_PROFILES.get(style, TRIP_PROFILES["culture"])
    boost = GROUP_BOOST.get(group, {})

    itin_slugs = _uniq(
        DURATION_ITINERARIES.get(duration, [])
        + profile.get("itinerary_slugs", [])
    )
    if boost.get("duration"):
        itin_slugs = _uniq(
            itin_slugs + DURATION_ITINERARIES.get(boost["duration"], [])
        )

    dest_slugs = _uniq(profile.get("destination_slugs", []))
    art_slugs = _uniq(profile.get("article_slugs", []))
    cat_keys = _uniq(profile.get("categories", []))

    articles_by_slug = {a["slug"]: a for a in articles}
    extra_articles = [
        a for a in articles
        if a.get("category") in cat_keys and a["slug"] not in art_slugs
    ][:4]

    return {
        "itineraries": [itineraries[s] for s in itin_slugs if s in itineraries],
        "destinations": [destinations[s] for s in dest_slugs if s in destinations],
        "articles": (
            [articles_by_slug[s] for s in art_slugs if s in articles_by_slug]
            + extra_articles
        ),
        "categories": [
            {"key": k, **categories[k]}
            for k in cat_keys
            if k in categories
        ],
    }


def _affiliate_links(lang: str, track_url_fn, destinations: dict) -> dict:
    """Liens affiliés (déjà trackés via track_url_fn) pour villes + produits globaux."""
    from data.affiliate_urls import (
        booking_city,
        esim_airalo,
        esim_holafly,
        get_location_meta,
        getyourguide_activity,
        travel_insurance,
    )

    def track(provider: str, url: str) -> str:
        return track_url_fn(provider, url) if track_url_fn else url

    per_city: dict[str, dict] = {}
    for slug in CITY_REGION:
        name = destinations.get(slug, {}).get("name", slug)
        meta = get_location_meta(slug, name=name)
        label = meta.get("label", name)
        per_city[slug] = {
            "hotel_url": track("booking", booking_city(meta)),
            "activity_url": track(
                "getyourguide", getyourguide_activity(f"{label} things to do", meta)
            ),
        }
    return {
        "cities": per_city,
        "esim_airalo_url": track("esim_airalo", esim_airalo()),
        "esim_holafly_url": track("esim_holafly", esim_holafly()),
        "insurance_url": track("travel_insurance", travel_insurance()),
    }


def _localized(items: list[dict], lang: str) -> list[str]:
    return [x.get(lang, x.get("fr", "")) for x in items]


def build_planner_catalog(
    lang: str,
    *,
    articles: list[dict],
    itineraries: dict,
    destinations: dict,
    categories: dict,
    lang_url_fn: Callable[..., str],
    t_fn: Callable[..., str],
    track_url_fn: Callable[..., str] | None = None,
) -> dict[str, Any]:
    """Catalogue JSON pour le wizard client (titres déjà localisés)."""
    from data.travel_tools import build_budget

    itin_cards = {}
    for slug, it in itineraries.items():
        itin_cards[slug] = {
            "slug": slug,
            "title": it.get("title", slug),
            "summary": it.get("summary", ""),
            "duration": it.get("duration", ""),
            "budget_hint": it.get("budget_hint", ""),
            "url": lang_url_fn("itinerary", lang, slug=slug),
        }

    affiliates = _affiliate_links(lang, track_url_fn, destinations)

    dest_cards = {}
    for slug, d in destinations.items():
        city_links = affiliates["cities"].get(slug, {})
        dest_cards[slug] = {
            "slug": slug,
            "name": d.get("name", slug),
            "tagline": d.get("tagline", ""),
            "url": lang_url_fn("destination_page", lang, slug=slug),
            "region": CITY_REGION.get(slug, ""),
            "hotel_url": city_links.get("hotel_url", ""),
            "activity_url": city_links.get("activity_url", ""),
        }

    art_cards = {}
    for a in articles:
        art_cards[a["slug"]] = {
            "slug": a["slug"],
            "title": a.get("title", ""),
            "excerpt": a.get("excerpt", ""),
            "category": a.get("category", ""),
            "category_label": a.get("category_label", ""),
            "url": lang_url_fn("article", lang, slug=a["slug"]),
        }

    cat_cards = {
        k: {
            "key": k,
            "label": v.get("label", k),
            "description": v.get("description", ""),
            "url": lang_url_fn("category", lang, category=k),
        }
        for k, v in categories.items()
    }

    # Villes proposées à l'étape « Où aller ? » (ordre Nord → Sud, présentes au catalogue).
    city_cards = [
        {
            "id": c["slug"],
            "name": destinations.get(c["slug"], {}).get("name", c["slug"]),
            "region": c["region"],
            "region_label": t_fn(f"prepare.region.{c['region']}", lang),
            "tagline": destinations.get(c["slug"], {}).get("tagline", ""),
        }
        for c in PLANNER_CITIES
        if c["slug"] in destinations
    ]

    budget = build_budget(lang)
    budget_block = {
        "tiers": {
            s["key"]: {"perday": s["perday"], "perday_total": s["perday_total"]}
            for s in budget["styles"]
        },
        "categories": budget["categories"],
        "oneoff": budget["oneoff"],
        "style_tier": STYLE_BUDGET_TIER,
        "group_size": GROUP_SIZE,
        "duration_days": DURATION_DAYS,
        "intercity_per_leg": INTERCITY_PER_LEG,
    }

    tips = {
        "general": _localized(TIPS_GENERAL, lang),
        "by_style": {k: _localized(v, lang) for k, v in TIPS_BY_STYLE.items()},
        "by_group": {k: _localized(v, lang) for k, v in TIPS_BY_GROUP.items()},
        "by_region": {k: _localized(v, lang) for k, v in TIPS_BY_REGION.items()},
    }

    recos = {
        "esim_airalo_url": affiliates["esim_airalo_url"],
        "esim_holafly_url": affiliates["esim_holafly_url"],
        "insurance_url": affiliates["insurance_url"],
    }

    return {
        "profiles": TRIP_PROFILES,
        "duration_itineraries": DURATION_ITINERARIES,
        "group_boost": GROUP_BOOST,
        "itineraries": itin_cards,
        "destinations": dest_cards,
        "articles": art_cards,
        "categories": cat_cards,
        "cities": city_cards,
        "budget": budget_block,
        "tips": tips,
        "recos": recos,
        "groups": [{"id": g, "label": t_fn(f"prepare.group.{g}", lang)} for g in GROUP_KEYS],
        "styles": [
            {"id": s, "label": t_fn(f"prepare.style.{s}.label", lang), "desc": t_fn(f"prepare.style.{s}.desc", lang)}
            for s in STYLE_KEYS
        ],
        "durations": [
            {"id": d, "label": t_fn(f"prepare.duration.{d}", lang)} for d in DURATION_KEYS
        ],
        "labels": {
            "results_title": t_fn("prepare.results.title", lang),
            "results_sub": t_fn("prepare.results.sub", lang),
            "itin_section": t_fn("prepare.results.itineraries", lang),
            "dest_section": t_fn("prepare.results.destinations", lang),
            "art_section": t_fn("prepare.results.articles", lang),
            "cat_section": t_fn("prepare.results.categories", lang),
            "budget_section": t_fn("prepare.results.budget", lang),
            "tips_section": t_fn("prepare.results.tips", lang),
            "recos_section": t_fn("prepare.results.recos", lang),
            "pdf_cta": t_fn("prepare.results.pdf", lang),
            "restart": t_fn("prepare.restart", lang),
            "next": t_fn("prepare.next", lang),
            "back": t_fn("prepare.back", lang),
            "see_all": t_fn("prepare.see_all", lang),
            "empty": t_fn("prepare.results.empty", lang),
            "days": t_fn("nav.days", lang),
            "step4": t_fn("prepare.step4", lang),
            "step4_hint": t_fn("prepare.step4_hint", lang),
            "budget_perperson": t_fn("prepare.budget.perperson", lang),
            "budget_group": t_fn("prepare.budget.group", lang),
            "budget_persons": t_fn("prepare.budget.persons", lang),
            "budget_daily": t_fn("prepare.budget.daily", lang),
            "budget_oneoff": t_fn("prepare.budget.oneoff", lang),
            "budget_intercity": t_fn("prepare.budget.intercity", lang),
            "budget_total": t_fn("prepare.budget.total", lang),
            "budget_note": t_fn("prepare.budget.note", lang),
            "reco_hotels": t_fn("prepare.reco.hotels", lang),
            "reco_hotels_desc": t_fn("prepare.reco.hotels_desc", lang),
            "reco_activities": t_fn("prepare.reco.activities", lang),
            "reco_activities_desc": t_fn("prepare.reco.activities_desc", lang),
            "reco_esim": t_fn("prepare.reco.esim", lang),
            "reco_esim_desc": t_fn("prepare.reco.esim_desc", lang),
            "reco_insurance": t_fn("prepare.reco.insurance", lang),
            "reco_insurance_desc": t_fn("prepare.reco.insurance_desc", lang),
            "reco_view": t_fn("prepare.reco.view", lang),
            "reco_disclosure": t_fn("prepare.reco.disclosure", lang),
        },
    }
