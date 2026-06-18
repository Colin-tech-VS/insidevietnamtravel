"""Analytics SEO — trafic organique, moteurs de recherche et types de contenu."""

from __future__ import annotations

from collections import defaultdict

from geo_utils import classify_geo_source

SEARCH_ENGINES: list[tuple[str, str, str]] = [
    # Google est traité à part (voir _is_google_search) pour couvrir tous les
    # ccTLD (google.es, google.pt…) et l'app Android, sans matcher Gmail/Drive…
    ("google", "Google", ""),
    ("bing", "Bing", "bing.com|cn.bing.com"),
    ("duckduckgo", "DuckDuckGo", "duckduckgo.com"),
    ("yahoo", "Yahoo", "search.yahoo|yahoo.com|yahoo.co"),
    ("yandex", "Yandex", "yandex."),
    ("ecosia", "Ecosia", "ecosia.org"),
    ("qwant", "Qwant", "qwant.com"),
    ("brave", "Brave Search", "search.brave.com"),
    ("baidu", "Baidu", "baidu.com"),
    ("naver", "Naver", "naver.com"),
    ("startpage", "Startpage", "startpage.com"),
    ("seznam", "Seznam", "seznam.cz"),
    ("ask", "Ask", "ask.com"),
    ("aol", "AOL", "search.aol|aol.com"),
    ("sogou", "Sogou", "sogou.com"),
    ("mojeek", "Mojeek", "mojeek.com"),
    ("petal", "Petal Search", "petalsearch.com"),
]

# Sous-domaines/services Google qui NE SONT PAS de la recherche organique :
# on les exclut pour éviter de compter Gmail, Drive, Maps… comme du SEO.
_GOOGLE_NON_SEARCH = (
    "mail.google", "drive.google", "docs.google", "play.google",
    "translate.google", "photos.google", "calendar.google", "meet.google",
    "accounts.google", "myaccount.google", "sites.google", "groups.google",
    "chat.google", "classroom.google", "keep.google", "contacts.google",
    "ads.google", "adwords.google", "business.google", "domains.google",
    "gemini.google", "bard.google",  # IA générative, pas de la recherche
    "googleusercontent", "googleadservices", "googlesyndication",
)


def _is_google_search(ref: str) -> bool:
    """`ref` doit déjà être en minuscules. Vrai si c'est de la recherche Google."""
    # App Google Android (recherche organique sur mobile)
    if "googlequicksearchbox" in ref:
        return True
    # Tout domaine google.<tld> (google.com, google.fr, google.es, m.google…)
    if "google." not in ref:
        return False
    return not any(bad in ref for bad in _GOOGLE_NON_SEARCH)

SOCIAL_PATTERNS = (
    "facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "pinterest.com", "reddit.com", "tiktok.com",
    "youtube.com", "t.co", "threads.net",
)

CHANNEL_LABELS = {
    "organic": "Recherche (SEO)",
    "direct": "Direct",
    "social": "Réseaux sociaux",
    "referral": "Sites référents",
    "internal": "Navigation interne",
}


def classify_search_engine(referrer: str = "") -> str | None:
    ref = (referrer or "").lower()
    if not ref.strip():
        return None
    if _is_google_search(ref):
        return "google"
    for engine_id, _, patterns in SEARCH_ENGINES:
        if not patterns:
            continue
        for part in patterns.split("|"):
            if part.lower() in ref:
                return engine_id
    return None


def search_engine_label(engine_id: str | None) -> str:
    if not engine_id:
        return "Autre"
    for eid, label, _ in SEARCH_ENGINES:
        if eid == engine_id:
            return label
    return engine_id


def classify_traffic_channel(referrer: str = "", user_agent: str = "") -> str:
    ref = (referrer or "").lower().strip()
    if classify_geo_source(referrer, user_agent):
        return "referral"
    if not ref:
        return "direct"
    if "insidevietnamtravel" in ref:
        return "internal"
    if classify_search_engine(referrer):
        return "organic"
    if any(s in ref for s in SOCIAL_PATTERNS):
        return "social"
    return "referral"


def classify_content_type(path: str = "") -> str:
    p = (path or "/").rstrip("/") or "/"
    if "/blog/" in p or p in ("/blog", "/en/blog"):
        return "blog"
    if "/itineraries/" in p:
        return "itinerary"
    if "/categorie/" in p or "/category/" in p:
        return "category"
    if p in ("/", "/en"):
        return "home"
    if "preparer-mon-voyage" in p or "plan-my-trip" in p:
        return "prepare"
    if any(x in p for x in ("/contact", "/a-propos", "/about", "/legal", "/privacy")):
        return "info"
    segments = [s for s in p.split("/") if s]
    if len(segments) == 1 or (len(segments) == 2 and segments[0] == "en"):
        return "destination"
    return "other"


CONTENT_TYPE_LABELS = {
    "blog": "Articles blog",
    "destination": "Destinations",
    "itinerary": "Itinéraires",
    "category": "Catégories blog",
    "home": "Accueil",
    "prepare": "Préparer voyage",
    "info": "Pages info",
    "other": "Autres",
}


def _track(bucket: dict[str, set[str]], key: str, ip_hash: str) -> None:
    if ip_hash:
        bucket.setdefault(key, set()).add(ip_hash)


def aggregate_seo_views(rows: list[dict]) -> dict:
    by_channel: dict[str, set[str]] = defaultdict(set)
    by_engine: dict[str, set[str]] = defaultdict(set)
    by_day_organic: dict[str, set[str]] = defaultdict(set)
    by_path_organic: dict[str, set[str]] = defaultdict(set)
    by_content_organic: dict[str, set[str]] = defaultdict(set)
    all_visitors: set[str] = set()

    for row in rows:
        ip = (row.get("ip_hash") or "").strip()
        if not ip:
            continue
        ref = row.get("referrer") or ""
        ua = row.get("user_agent") or ""
        path = row.get("path") or "/"
        day = (row.get("created_at") or "")[:10]
        channel = classify_traffic_channel(ref, ua)
        content = classify_content_type(path)

        all_visitors.add(ip)
        by_channel[channel].add(ip)

        if channel == "organic":
            engine = classify_search_engine(ref) or "other"
            by_engine[engine].add(ip)
            by_path_organic[path].add(ip)
            by_content_organic[content].add(ip)
            if day:
                by_day_organic[day].add(ip)

    total = len(all_visitors)
    organic = len(by_channel.get("organic", set()))
    direct = len(by_channel.get("direct", set()))

    channels_chart = [
        {"id": cid, "label": CHANNEL_LABELS[cid], "views": len(by_channel.get(cid, set()))}
        for cid in ("organic", "direct", "social", "referral", "internal")
        if by_channel.get(cid)
    ]
    channels_chart.sort(key=lambda x: -x["views"])

    engines_chart = [
        {"id": eid, "label": search_engine_label(eid if eid != "other" else None), "views": len(visitors)}
        for eid, visitors in by_engine.items()
        if visitors
    ]
    engines_chart.sort(key=lambda x: -x["views"])

    content_organic = [
        {"id": cid, "label": CONTENT_TYPE_LABELS[cid], "views": len(by_content_organic.get(cid, set()))}
        for cid in CONTENT_TYPE_LABELS
        if by_content_organic.get(cid)
    ]
    content_organic.sort(key=lambda x: -x["views"])

    top_organic_pages = sorted(
        ((path, len(visitors)) for path, visitors in by_path_organic.items()),
        key=lambda x: -x[1],
    )[:12]
    daily_organic = [
        {"day": day, "views": len(by_day_organic[day])}
        for day in sorted(by_day_organic.keys())
    ]

    blog_organic = len(by_content_organic.get("blog", set()))
    dest_organic = len(by_content_organic.get("destination", set()))

    return {
        "total_organic_views": organic,
        "organic_share_pct": round(100 * organic / total, 1) if total else 0.0,
        "direct_views": direct,
        "direct_share_pct": round(100 * direct / total, 1) if total else 0.0,
        "blog_organic_views": blog_organic,
        "destination_organic_views": dest_organic,
        "by_channel": {k: len(v) for k, v in by_channel.items()},
        "channels_chart": channels_chart,
        "engines_chart": engines_chart,
        "content_organic": content_organic,
        "top_organic_pages": [{"path": p, "views": c} for p, c in top_organic_pages],
        "daily_organic": daily_organic,
    }
