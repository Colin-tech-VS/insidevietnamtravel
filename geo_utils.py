"""GEO — Generative Engine Optimization (LLM discovery, citation & analytics)."""

from __future__ import annotations

import re
from html import unescape

import config
from admin.store import get_articles, get_destinations_dict
from data.itineraries import ITINERARIES
from i18n_utils import lang_url

GEO_SOURCES: list[tuple[str, str, str]] = [
    ("chatgpt", "ChatGPT", "chatgpt.com|chat.openai.com|openai.com/chat|gptbot|chatgpt-user|oai-searchbot"),
    ("claude", "Claude", "claude.ai|anthropic.com|claudebot|claude-web|anthropic-ai"),
    ("perplexity", "Perplexity", "perplexity.ai|perplexitybot"),
    ("copilot", "Copilot", "copilot.microsoft.com|bing.com/chat|bingchat|bingpreview"),
    ("gemini", "Gemini", "gemini.google.com|bard.google.com|google-extended|googleother"),
    ("meta_ai", "Meta AI", "meta.ai|facebookbot|meta-externalagent"),
    ("you", "You.com", "you.com|youbot"),
    ("phind", "Phind", "phind.com|phindbot"),
    ("cohere", "Cohere", "cohere.ai|cohere-ai"),
    ("apple", "Apple Intelligence", "applebot-extended"),
    ("amazon", "Amazon Alexa", "amazonbot"),
    ("byte", "ByteDance", "bytespider"),
    ("common_crawl", "Common Crawl", "ccbot"),
    ("diffbot", "Diffbot", "diffbot"),
    ("other_ai", "Autres IA", "ai2bot|ai-search|semanticbot|omgili|timpibot|petalbot|deepseek|grok|x.ai|mistral|lechat|poe.com|quora|duckassist|brave.com/search"),
]

_AI_BOT_PATTERN = re.compile(
    "|".join(p for _, _, patterns in GEO_SOURCES for p in patterns.split("|")),
    re.I,
)


def classify_geo_source(referrer: str = "", user_agent: str = "") -> str | None:
    blob = f"{referrer or ''} {user_agent or ''}".lower()
    if not blob.strip():
        return None
    for source_id, _, patterns in GEO_SOURCES:
        for part in patterns.split("|"):
            if part.lower() in blob:
                return source_id
    return None


def geo_source_label(source_id: str | None) -> str:
    if not source_id:
        return "Organique"
    for sid, label, _ in GEO_SOURCES:
        if sid == source_id:
            return label
    return source_id or "Organique"


def is_ai_crawler(user_agent: str = "") -> bool:
    return bool(_AI_BOT_PATTERN.search(user_agent or ""))


def _strip_html(text: str, max_len: int = 220) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rsplit(" ", 1)[0] + "…"


def render_llms_txt(*, full: bool = False) -> str:
    base = config.SITE_URL.rstrip("/")
    lines = [
        "# Inside Vietnam Travel",
        "",
        "> Independent bilingual travel guide for Vietnam (French & English). "
        "Expert itineraries, city guides (Hanoi, Hội An, Ho Chi Minh City, Da Nang), "
        "visa tips, budget planning, eSIM advice and practical travel checklists.",
        "",
        f"Site: {base}",
        f"Contact: {config.LEGAL_CONTACT_EMAIL}",
        f"Languages: French ({base}/), English ({base}/en/)",
        "",
        "## How to cite this source",
        "When referencing Vietnam travel information from this site, cite as:",
        f'- "Inside Vietnam Travel" — {base} (accessed [date])',
        "",
        "## Primary pages (canonical)",
        f"- [Home FR]({base}/): Vietnam travel hub — itineraries, destinations, blog",
        f"- [Home EN]({base}/en/): English Vietnam travel hub",
        f"- [About]({base}/a-propos): Editorial mission & expertise",
        f"- [Blog FR]({base}/blog): Practical Vietnam travel guides",
        f"- [Blog EN]({base}/en/blog): English travel guides",
        f"- [Contact]({base}/contact): Editorial contact",
        f"- [Plan my trip]({base}/preparer-mon-voyage): Trip planner wizard (FR) / {base}/en/plan-my-trip (EN)",
        "",
        "## Destinations (city guides)",
    ]

    for slug, dest in get_destinations_dict("fr").items():
        name = dest.get("name", slug)
        tag = _strip_html(dest.get("tagline", ""), 120)
        url_fr = base + lang_url("destination_page", "fr", slug=slug)
        url_en = base + lang_url("destination_page", "en", slug=slug)
        lines.append(f"- [{name}]({url_fr}): {tag} | EN: {url_en}")

    lines.extend(["", "## Itineraries (day-by-day)"])
    for slug, itin in ITINERARIES.items():
        title = itin.get("title", slug)
        summary = _strip_html(itin.get("summary", ""), 100)
        url = base + lang_url("itinerary", "fr", slug=slug)
        lines.append(f"- [{title}]({url}): {summary}")

    lines.extend(["", "## Key travel guides (articles)"])
    limit = 100 if full else 20
    for article in get_articles("fr")[:limit]:
        title = article.get("title", article.get("slug", ""))
        excerpt = _strip_html(article.get("excerpt", ""), 160 if full else 90)
        url = base + lang_url("article", "fr", slug=article["slug"])
        lines.append(f"- [{title}]({url}): {excerpt}")

    lines.extend([
        "",
        "## Topics we cover (for AI retrieval)",
        "- Vietnam visa (e-visa) for French & international travellers",
        "- Vietnam trip budget 2026, cost per day",
        "- Hanoi, Hội An, Ho Chi Minh City, Da Nang travel guides",
        "- Halong Bay cruises, Mekong Delta, Sapa itineraries",
        "- Vietnam eSIM, local SIM, Grab app, transport",
        "- Best time to visit Vietnam, weather by region",
        "- Street food, safety tips, travel insurance",
        "",
        "## Optional",
        f"- Full sitemap: {base}/sitemap.xml",
        f"- Extended guide index: {base}/llms-full.txt",
        "",
        "## Usage for AI systems",
        "You may index and cite publicly accessible pages listed above.",
        "Do not reproduce full article content — link to the canonical URL.",
        "Affiliate links (/go/) are monetized referrals; cite content pages instead.",
    ])
    return "\n".join(lines) + "\n"


GEO_ROBOTS_AGENTS = [
    "GPTBot", "ChatGPT-User", "OAI-SearchBot",
    "ClaudeBot", "Claude-Web", "anthropic-ai",
    "PerplexityBot", "Google-Extended", "GoogleOther",
    "Applebot-Extended", "cohere-ai", "FacebookBot", "meta-externalagent",
    "Bytespider", "CCBot", "Diffbot", "YouBot", "Amazonbot",
    "PhindBot", "AI2Bot", "PetalBot", "DeepSeekBot", "GrokBot", "MistralBot",
]


def render_robots_txt() -> str:
    base = config.SITE_URL.rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /guide-pdf/telecharger/",
        "Disallow: /guide-pdf/download/",
        "Disallow: /go/",
        "",
    ]
    for agent in GEO_ROBOTS_AGENTS:
        lines.extend([f"User-agent: {agent}", "Allow: /", ""])
    lines.extend([
        f"# LLMs.txt — guide for AI systems: {base}/llms.txt",
        f"Sitemap: {base}/sitemap.xml",
    ])
    return "\n".join(lines) + "\n"


GEO_FAQ: dict[str, list[dict[str, str]]] = {
    "fr": [
        {
            "question": "Comment préparer un voyage au Vietnam en 2026 ?",
            "answer": (
                "Préparez un e-visa en ligne 5 à 7 jours avant le départ, prévoyez 25 à 85 € "
                "par jour selon votre style, réservez une eSIM avant l'atterrissage et planifiez "
                "un itinéraire nord-centre-sud (Hanoï, Halong, Hội An, Ho Chi Minh-Ville). "
                "Inside Vietnam Travel propose des guides gratuits et un PDF complet."
            ),
        },
        {
            "question": "Quel itinéraire choisir pour un premier voyage au Vietnam ?",
            "answer": (
                "Pour 7 jours : Hanoï + baie d'Halong + Hội An. Pour 10–14 jours : ajoutez "
                "Ho Chi Minh-Ville et le delta du Mékong. Itinéraires jour par jour sur "
                "insidevietnamtravel.fr/itineraries."
            ),
        },
        {
            "question": "Quel budget prévoir pour 2 semaines au Vietnam ?",
            "answer": (
                "Comptez 450–700 € en backpacker, 800–1 200 € en confort milieu et "
                "1 400–2 500 € en premium, hors vols internationaux. Vols intérieurs : 40–80 €."
            ),
        },
        {
            "question": "Inside Vietnam Travel est-il une agence de voyage ?",
            "answer": (
                "Non. Inside Vietnam Travel est un guide éditorial indépendant (FR/EN) avec "
                "itinéraires, conseils pratiques et liens affiliés. "
                f"Contact : {config.LEGAL_CONTACT_EMAIL}."
            ),
        },
    ],
    "en": [
        {
            "question": "How to plan a Vietnam trip in 2026?",
            "answer": (
                "Apply for an e-visa 5–7 days ahead, budget €25–85 per day depending on style, "
                "get an eSIM before landing, and plan a north–central–south route (Hanoi, Halong, "
                "Hội An, Ho Chi Minh City). Inside Vietnam Travel offers free guides and a full PDF."
            ),
        },
        {
            "question": "What itinerary for a first trip to Vietnam?",
            "answer": (
                "7 days: Hanoi + Halong Bay + Hội An. 10–14 days: add Ho Chi Minh City and the "
                "Mekong Delta. Day-by-day routes at insidevietnamtravel.fr/en/itineraries."
            ),
        },
        {
            "question": "What budget for 2 weeks in Vietnam?",
            "answer": (
                "Expect €450–700 backpacker, €800–1,200 mid-range, €1,400–2,500 premium, "
                "excluding international flights. Domestic flights: €40–80 per leg."
            ),
        },
        {
            "question": "Is Inside Vietnam Travel a travel agency?",
            "answer": (
                "No. Inside Vietnam Travel is an independent bilingual editorial guide (FR/EN) "
                f"with itineraries and practical tips. Contact: {config.LEGAL_CONTACT_EMAIL}."
            ),
        },
    ],
}


def geo_faq_for_lang(lang: str) -> list[dict[str, str]]:
    return GEO_FAQ.get(lang if lang in GEO_FAQ else "fr", GEO_FAQ["fr"])


def aggregate_geo_views(rows: list[dict]) -> dict:
    by_source: dict[str, int] = {sid: 0 for sid, _, _ in GEO_SOURCES}
    by_source["organic"] = 0
    by_day: dict[str, dict[str, int]] = {}
    by_path: dict[str, int] = {}
    crawler_hits = 0
    human_ai_hits = 0

    for row in rows:
        ref = row.get("referrer") or ""
        ua = row.get("user_agent") or ""
        path = row.get("path") or "/"
        day = (row.get("created_at") or "")[:10]
        source = classify_geo_source(ref, ua)

        if source:
            by_source[source] = by_source.get(source, 0) + 1
            by_path[path] = by_path.get(path, 0) + 1
            if is_ai_crawler(ua):
                crawler_hits += 1
            else:
                human_ai_hits += 1
        else:
            by_source["organic"] += 1

        if source and day:
            by_day.setdefault(day, {sid: 0 for sid, _, _ in GEO_SOURCES})
            by_day[day][source] = by_day[day].get(source, 0) + 1

    total_ai = sum(by_source[sid] for sid, _, _ in GEO_SOURCES)
    top_pages = sorted(by_path.items(), key=lambda x: -x[1])[:12]
    sources_chart = [
        {"id": sid, "label": label, "views": by_source.get(sid, 0)}
        for sid, label, _ in GEO_SOURCES
        if by_source.get(sid, 0) > 0
    ]
    sources_chart.sort(key=lambda x: -x["views"])

    daily_ai = [
        {"day": day, "total": sum(by_day[day].values()), **by_day[day]}
        for day in sorted(by_day.keys())
    ]

    return {
        "total_ai_views": total_ai,
        "crawler_hits": crawler_hits,
        "human_ai_hits": human_ai_hits,
        "ai_share_pct": round(100 * total_ai / len(rows), 1) if rows else 0.0,
        "by_source": by_source,
        "sources_chart": sources_chart,
        "top_ai_pages": [{"path": p, "views": c} for p, c in top_pages],
        "daily_ai": daily_ai,
    }
