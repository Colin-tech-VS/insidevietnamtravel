"""Filtres trafic humain — exclut crawlers et robots des analytics généraux."""

from __future__ import annotations

import re

from geo_utils import GEO_SOURCES, is_ai_crawler

_EXTRA_BOT_PATTERNS: tuple[str, ...] = (
    "googlebot",
    "bingbot",
    "slurp",
    "duckduckbot",
    "baiduspider",
    "yandexbot",
    "facebookexternalhit",
    "facebot",
    "twitterbot",
    "linkedinbot",
    "pinterestbot",
    "whatsapp",
    "telegrambot",
    "semrushbot",
    "ahrefsbot",
    "mj12bot",
    "dotbot",
    "rogerbot",
    "screaming frog",
    "uptimerobot",
    "pingdom",
    "statuscake",
    "headlesschrome",
    "curl/",
    "wget/",
    "python-requests",
    "scrapy",
    "httpx/",
    "go-http-client",
    "adsbot-google",
    "mediapartners-google",
    "feedfetcher",
    "lighthouse",
    "chrome-lighthouse",
    "ia_archiver",
    "archive.org",
    "netcraft",
    "blexbot",
    "sogou",
    "exabot",
    "petalbot",
    "discordbot",
)


def _all_bot_patterns() -> list[str]:
    seen: set[str] = set()
    patterns: list[str] = []
    for item in _EXTRA_BOT_PATTERNS:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            patterns.append(key)
    for _, _, pats in GEO_SOURCES:
        for part in pats.split("|"):
            key = part.lower().strip()
            if key and key not in seen:
                seen.add(key)
                patterns.append(key)
    return patterns


def is_analytics_bot(user_agent: str = "") -> bool:
    ua = user_agent or ""
    if not ua.strip():
        return False
    if is_ai_crawler(ua):
        return True
    low = ua.lower()
    return any(p in low for p in _EXTRA_BOT_PATTERNS)


def not_bot_pg_sql(column: str = "user_agent") -> str:
    pattern = "|".join(re.escape(p) for p in _all_bot_patterns())
    return f" AND COALESCE({column}, '') !~* '{pattern}' "


def not_bot_sqlite_sql(column: str = "user_agent") -> str:
    parts = []
    for p in _all_bot_patterns():
        safe = p.replace("'", "''")
        parts.append(f"LOWER(COALESCE({column}, '')) NOT LIKE '%{safe}%'")
    return " AND " + " AND ".join(parts)


def not_bot_sql(column: str = "user_agent", *, postgres: bool) -> str:
    if postgres:
        return not_bot_pg_sql(column)
    return not_bot_sqlite_sql(column)
