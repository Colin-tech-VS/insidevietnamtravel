"""Profil visiteur cookie-only — parsing, enrichissement, recommandations, contexte Mai."""

from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Callable
from urllib.parse import unquote

PROFILE_COOKIE = "ivt_vp"
PROFILE_VERSION = 2
MAX_AGE_SECONDS = 395 * 24 * 3600

GROUP_KEYS = frozenset({"solo", "couple", "family", "friends"})
STYLE_KEYS = frozenset({
    "culture", "food", "adventure", "romantic", "roadtrip", "relax", "budget",
})
DURATION_KEYS = frozenset({"short", "medium", "long"})

# Segments d'URL → tags d'intérêt (FR + EN).
PATH_INTEREST_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"/(visa|e-?visa)", re.I), "visa"),
    (re.compile(r"/(securite|travel-safety|safety)", re.I), "safety"),
    (re.compile(r"/(coutumes|customs|etiquette)", re.I), "customs"),
    (re.compile(r"/(phrases|vietnamese-phrases)", re.I), "phrases"),
    (re.compile(r"/(quand-partir|best-time|season)", re.I), "season"),
    (re.compile(r"/(budget|estimer)", re.I), "budget"),
    (re.compile(r"/(preparer|plan-my-trip|prepare)", re.I), "prepare"),
    (re.compile(r"/(applications|useful-apps|apps)", re.I), "apps"),
    (re.compile(r"/(essentiels|essentials|esim|assurance)", re.I), "essentials"),
    (re.compile(r"/blog/", re.I), "blog"),
    (re.compile(r"/itineraire|/itinerary", re.I), "itinerary"),
]

DEST_SLUGS = (
    "hanoi", "halong", "sapa", "hue", "da-nang", "hoi-an",
    "ho-chi-minh-city", "delta-du-mekong", "phu-quoc",
)

INTEREST_TOOL_ENDPOINTS: dict[str, str] = {
    "visa": "visa_tool",
    "safety": "safety_guide",
    "customs": "customs_guide",
    "phrases": "phrases_guide",
    "season": "best_season",
    "budget": "budget_tool",
    "prepare": "prepare_trip",
    "apps": "useful_apps",
    "essentials": "essentials_tool",
}


def hash_visitor_id(visitor_id: str) -> str:
    raw = (visitor_id or "").strip()
    if not raw:
        return ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _now_ts() -> int:
    return int(time.time())


def _compact_list(items: list, limit: int) -> list:
    out: list = []
    seen = set()
    for x in items:
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
        if len(out) >= limit:
            break
    return out


def parse_cookie(raw: str | None) -> dict | None:
    """Désérialise le cookie ivt_vp (JSON compact URI-encodé)."""
    if not raw:
        return None
    try:
        text = unquote(raw.strip())
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("v") != PROFILE_VERSION:
        return None
    return normalize_profile(data)


def normalize_profile(data: dict) -> dict:
    vid = str(data.get("id") or "").strip()[:36]
    if not vid:
        vid = hashlib.sha256(f"{_now_ts()}-anon".encode()).hexdigest()[:12]

    g = data.get("g") if data.get("g") in GROUP_KEYS else None
    s = data.get("s") if data.get("s") in STYLE_KEYS else None
    d = data.get("d") if data.get("d") in DURATION_KEYS else None

    cities_raw = data.get("c") if isinstance(data.get("c"), list) else []
    cities = _compact_list([c for c in cities_raw if c in DEST_SLUGS], 8)

    interests_raw = data.get("i") if isinstance(data.get("i"), list) else []
    interests = _compact_list([i for i in interests_raw if isinstance(i, str)][:16], 16)

    pages_raw = data.get("p") if isinstance(data.get("p"), list) else []
    pages: dict[str, int] = {}
    for entry in pages_raw[:12]:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            path, count = str(entry[0]), entry[1]
            try:
                pages[path] = min(int(count), 99)
            except (TypeError, ValueError):
                continue
        elif isinstance(entry, str):
            pages[entry] = pages.get(entry, 0) + 1

    tools_raw = data.get("u") if isinstance(data.get("u"), list) else []
    tools = _compact_list([u for u in tools_raw if isinstance(u, str)], 8)

    lang = "en" if data.get("l") == "en" else "fr"

    return {
        "v": PROFILE_VERSION,
        "id": vid,
        "l": lang,
        "g": g,
        "s": s,
        "d": d,
        "c": cities,
        "i": interests,
        "p": [[path, n] for path, n in list(pages.items())[:10]],
        "u": tools,
        "t": int(data.get("t") or _now_ts()),
    }


def serialize_profile(profile: dict) -> str:
    compact = normalize_profile(profile)
    return json.dumps(compact, separators=(",", ":"), ensure_ascii=False)


def merge_profile(existing: dict | None, updates: dict) -> dict:
    base = normalize_profile(existing or {"v": PROFILE_VERSION, "id": updates.get("id") or ""})
    for key in ("g", "s", "d", "l"):
        if updates.get(key) is not None:
            base[key] = updates[key]
    if updates.get("c"):
        base["c"] = _compact_list(list(base.get("c") or []) + list(updates["c"]), 8)
    if updates.get("i"):
        base["i"] = _compact_list(list(base.get("i") or []) + list(updates["i"]), 16)
    if updates.get("u"):
        base["u"] = _compact_list(list(base.get("u") or []) + list(updates["u"]), 8)
    if updates.get("p"):
        pages = {p: n for p, n in base.get("p") or []}
        for path, count in updates["p"]:
            pages[path] = pages.get(path, 0) + int(count)
        base["p"] = [[p, n] for p, n in sorted(pages.items(), key=lambda x: -x[1])[:10]]
    base["t"] = _now_ts()
    return normalize_profile(base)


def _path_interests(path: str) -> list[str]:
    tags: list[str] = []
    path_l = (path or "").lower()
    for pattern, tag in PATH_INTEREST_RULES:
        if pattern.search(path_l):
            tags.append(tag)
    for slug in DEST_SLUGS:
        if f"/{slug}" in path_l or path_l.rstrip("/").endswith(f"/{slug}"):
            tags.append(f"dest:{slug}")
    return tags


def enrich_from_path(profile: dict, path: str) -> dict:
    tags = _path_interests(path)
    if not tags:
        return profile
    pages = {p: n for p, n in profile.get("p") or []}
    pages[path] = pages.get(path, 0) + 1
    return merge_profile(profile, {
        "i": tags,
        "p": [[path, 1]],
    })


def _label(key: str, lang: str, t_fn: Callable[[str, str], str]) -> str:
    return t_fn(key, lang)


def profile_summary(profile: dict, lang: str, t_fn: Callable[[str, str], str]) -> str:
    lang = "en" if lang == "en" else "fr"
    parts: list[str] = []
    g, s, d = profile.get("g"), profile.get("s"), profile.get("d")
    if g:
        parts.append(_label(f"prepare.group.{g}", lang, t_fn))
    if s:
        parts.append(_label(f"prepare.style.{s}", lang, t_fn))
    if d:
        parts.append(_label(f"prepare.duration.{d}", lang, t_fn))
    cities = profile.get("c") or []
    if cities:
        parts.append(", ".join(c.replace("-", " ").title() for c in cities[:4]))
    interests = [i for i in (profile.get("i") or []) if not i.startswith("dest:")][:4]
    if interests:
        parts.append(" · ".join(interests))
    if not parts:
        return _label("profile.summary_default", lang, t_fn)
    return " · ".join(parts)


def profile_for_mai(profile: dict, lang: str, t_fn: Callable[[str, str], str]) -> str:
    """Bloc texte injecté dans le prompt Mai."""
    lang = "en" if lang == "en" else "fr"
    if not profile or not _has_signal(profile):
        return ""

    lines = [
        "VISITOR PROFILE (cookie, no account — tailor advice & links to this):",
        f"- Summary: {profile_summary(profile, lang, t_fn)}",
    ]
    if profile.get("g"):
        lines.append(f"- Travellers: {profile['g']}")
    if profile.get("s"):
        lines.append(f"- Travel style: {profile['s']}")
    if profile.get("d"):
        lines.append(f"- Trip length: {profile['d']}")
    if profile.get("c"):
        lines.append(f"- Cities of interest: {', '.join(profile['c'])}")
    interests = profile.get("i") or []
    if interests:
        lines.append(f"- Pages/topics viewed: {', '.join(interests[:12])}")
    tools = profile.get("u") or []
    if tools:
        lines.append(f"- Tools used: {', '.join(tools)}")
    top_pages = profile.get("p") or []
    if top_pages:
        paths = ", ".join(f"{p}({n})" for p, n in top_pages[:5])
        lines.append(f"- Most visited paths: {paths}")
    lines.append(
        "Use this profile to prioritize destinations, seasons, budget level, and site links. "
        "Do not mention cookies or tracking — speak naturally (« d'après vos recherches… »)."
        if lang == "fr"
        else "Use this profile to prioritize destinations, seasons, budget level, and site links. "
        "Do not mention cookies or tracking — speak naturally (« based on what you've explored… »)."
    )
    return "\n".join(lines)


def _has_signal(profile: dict) -> bool:
    return bool(
        profile.get("g") or profile.get("s") or profile.get("d")
        or profile.get("c") or profile.get("i") or profile.get("u")
    )


def mai_suggestions(profile: dict, lang: str, t_fn: Callable[[str, str], str]) -> list[str]:
    """Suggestions dynamiques pour le widget Mai."""
    lang = "en" if lang == "en" else "fr"
    if not profile or not _has_signal(profile):
        return [
            t_fn("chat.suggest1", lang),
            t_fn("chat.suggest2", lang),
            t_fn("chat.suggest3", lang),
        ]

    out: list[str] = []
    cities = profile.get("c") or []
    interests = profile.get("i") or []

    if cities:
        city = cities[0].replace("-", " ").title()
        out.append(
            f"Que faire à {city} en {t_fn('prepare.duration.' + (profile.get('d') or 'medium'), lang).lower()} ?"
            if lang == "fr"
            else f"What to do in {city} for a {profile.get('d') or 'medium'} trip?"
        )
    if "visa" in interests or profile.get("g"):
        out.append(t_fn("chat.suggest_visa", lang) if _has_key(t_fn, "chat.suggest_visa", lang)
                     else ("Ai-je besoin d'un visa ?" if lang == "fr" else "Do I need a visa?"))
    if "season" in interests or cities:
        out.append(t_fn("chat.suggest_season", lang) if _has_key(t_fn, "chat.suggest_season", lang)
                     else ("Quand partir ?" if lang == "fr" else "Best time to visit?"))
    if profile.get("s") == "budget" or "budget" in interests:
        out.append(t_fn("chat.suggest_budget", lang) if _has_key(t_fn, "chat.suggest_budget", lang)
                     else ("Budget réaliste ?" if lang == "fr" else "Realistic budget?"))
    if "safety" in interests:
        out.append(t_fn("chat.suggest_safety", lang) if _has_key(t_fn, "chat.suggest_safety", lang)
                     else ("Arnaques à éviter ?" if lang == "fr" else "Scams to avoid?"))

    defaults = [
        t_fn("chat.suggest1", lang),
        t_fn("chat.suggest2", lang),
        t_fn("chat.suggest3", lang),
    ]
    for d in defaults:
        if len(out) >= 3:
            break
        if d not in out:
            out.append(d)
    return out[:3]


def _has_key(t_fn, key: str, lang: str) -> bool:
    try:
        val = t_fn(key, lang)
        return bool(val) and val != key
    except Exception:
        return False


def resolve_from_profile(
    profile: dict,
    lang: str,
    *,
    destinations: dict,
    itineraries: dict,
    articles: list[dict],
    categories: dict,
    lang_url_fn: Callable[..., str],
    t_fn: Callable[[str, str], str],
) -> dict[str, Any]:
    """Recommandations structurées pour la home et l'API."""
    from data.trip_planner import (
        DURATION_ITINERARIES,
        GROUP_BOOST,
        TRIP_PROFILES,
        _uniq,
        resolve_recommendations,
    )

    lang = "en" if lang == "en" else "fr"
    g = profile.get("g") or "couple"
    s = profile.get("s") or "culture"
    d = profile.get("d") or "medium"
    cities = profile.get("c") or []

    base = resolve_recommendations(
        g, s, d,
        articles=articles,
        itineraries=itineraries,
        destinations=destinations,
        categories=categories,
    )

    trip_profile = TRIP_PROFILES.get(s, TRIP_PROFILES["culture"])
    boost = GROUP_BOOST.get(g, {})
    itin_slugs = _uniq(
        list(DURATION_ITINERARIES.get(d, []))
        + list(trip_profile.get("itinerary_slugs", []))
    )
    if boost.get("duration"):
        itin_slugs = _uniq(itin_slugs + list(DURATION_ITINERARIES.get(boost["duration"], [])))

    dest_slugs = _uniq(list(cities) + list(trip_profile.get("destination_slugs", [])))

    dest_items: list[dict] = []
    for slug in dest_slugs[:6]:
        if slug not in destinations:
            continue
        dd = destinations[slug]
        dest_items.append({
            "slug": slug,
            "name": dd.get("name", slug),
            "tagline": dd.get("tagline", ""),
            "image": dd.get("image", ""),
            "url": lang_url_fn("destination_page", lang, slug=slug),
        })

    itin_items = []
    for slug in itin_slugs[:4]:
        it = itineraries.get(slug)
        if not it:
            continue
        itin_items.append({
            "slug": slug,
            "title": it.get("title", slug),
            "duration": it.get("duration", ""),
            "url": lang_url_fn("itinerary", lang, slug=slug),
        })

    tool_titles = {
        "visa": "tools.visa",
        "safety": "safety.nav",
        "customs": "customs.nav",
        "phrases": "phrases.nav",
        "season": "tools.season",
        "budget": "tools.budget",
        "prepare": "nav.prepare",
        "apps": "tools.apps",
        "essentials": "tools.essentials",
    }
    tool_items = []
    interest_set = set(profile.get("i") or [])
    seen_tools: set[str] = set()
    for tag, endpoint in INTEREST_TOOL_ENDPOINTS.items():
        if tag not in interest_set and not (tag == "prepare" and profile.get("g")):
            if tag not in ("visa", "season", "prepare"):
                continue
        if tag in seen_tools:
            continue
        seen_tools.add(tag)
        title_key = tool_titles.get(tag, "nav.prepare")
        tool_items.append({
            "key": tag,
            "title": t_fn(title_key, lang),
            "url": lang_url_fn(endpoint, lang),
        })
    if not tool_items:
        tool_items = [
            {"key": "prepare", "title": t_fn("nav.prepare", lang), "url": lang_url_fn("prepare_trip", lang)},
            {"key": "season", "title": t_fn("tools.season", lang), "url": lang_url_fn("best_season", lang)},
            {"key": "visa", "title": t_fn("tools.visa", lang), "url": lang_url_fn("visa_tool", lang)},
        ]

    return {
        "personalized": _has_signal(profile),
        "summary": profile_summary(profile, lang, t_fn),
        "destinations": dest_items[:6],
        "itineraries": itin_items[:4],
        "tools": tool_items[:5],
        "prepare_url": lang_url_fn("prepare_trip", lang),
        "profile": {
            "group": g,
            "style": s,
            "duration": d,
            "cities": cities,
        },
    }


def retrieve_boost_tags(profile: dict | None) -> set[str]:
    """Tokens supplémentaires pour le RAG Mai."""
    if not profile:
        return set()
    tags: set[str] = set()
    for key in ("g", "s", "d"):
        if profile.get(key):
            tags.add(str(profile[key]))
    tags.update(profile.get("c") or [])
    for interest in profile.get("i") or []:
        tags.add(interest.replace("dest:", ""))
        if ":" in interest:
            tags.add(interest.split(":", 1)[1])
        else:
            tags.add(interest)
    return tags
