"""Profils voyage — moteur de recommandations « Préparer mon voyage »."""

from __future__ import annotations

from typing import Any, Callable

GROUP_KEYS = ("solo", "couple", "family", "friends")

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
    "long": ["10-days-vietnam", "7-days-vietnam"],
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
        ],
        "categories": ["practical", "itinerary"],
    },
    "food": {
        "destination_slugs": ["hanoi", "hoi-an", "ho-chi-minh-city"],
        "itinerary_slugs": ["7-days-vietnam", "10-days-vietnam"],
        "article_slugs": ["meilleurs-restaurants-hanoi", "budget-voyage-vietnam-2026"],
        "categories": ["food", "practical"],
    },
    "adventure": {
        "destination_slugs": ["hanoi", "ho-chi-minh-city", "da-nang"],
        "itinerary_slugs": ["10-days-vietnam", "7-days-vietnam"],
        "article_slugs": [
            "securite-voyage-vietnam-conseils",
            "transport-vietnam-train-bus-vol",
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


def build_planner_catalog(
    lang: str,
    *,
    articles: list[dict],
    itineraries: dict,
    destinations: dict,
    categories: dict,
    lang_url_fn: Callable[..., str],
    t_fn: Callable[..., str],
) -> dict[str, Any]:
    """Catalogue JSON pour le wizard client (titres déjà localisés)."""
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

    dest_cards = {}
    for slug, d in destinations.items():
        dest_cards[slug] = {
            "slug": slug,
            "name": d.get("name", slug),
            "tagline": d.get("tagline", ""),
            "url": lang_url_fn("destination_page", lang, slug=slug),
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

    return {
        "profiles": TRIP_PROFILES,
        "duration_itineraries": DURATION_ITINERARIES,
        "group_boost": GROUP_BOOST,
        "itineraries": itin_cards,
        "destinations": dest_cards,
        "articles": art_cards,
        "categories": cat_cards,
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
            "pdf_cta": t_fn("prepare.results.pdf", lang),
            "restart": t_fn("prepare.restart", lang),
            "next": t_fn("prepare.next", lang),
            "back": t_fn("prepare.back", lang),
            "see_all": t_fn("prepare.see_all", lang),
            "empty": t_fn("prepare.results.empty", lang),
            "days": t_fn("nav.days", lang),
        },
    }
