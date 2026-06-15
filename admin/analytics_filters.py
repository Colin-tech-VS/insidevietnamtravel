"""Filtres analytics — uniquement de vrais visiteurs humains."""

from __future__ import annotations

import hashlib
import os
import re

from geo_utils import GEO_SOURCES, is_ai_crawler

_ANALYTICS_EXCLUDED_PATH_PREFIXES: tuple[str, ...] = (
    "/.well-known/",
    "/partners/",  # espace partenaire (noindex)
    "/e/o/",  # pixel ouverture email
    "/e/c/",  # redirection clic email
)

# Chemins techniques / SEO / vérification — pas des visites utilisateur.
_INFRA_ANALYTICS_PATHS: frozenset[str] = frozenset({
    "/robots.txt",
    "/sitemap.xml",
    "/llms.txt",
    "/llms-full.txt",
    "/AgodaPartnerVerification.htm",
    "/site.webmanifest",
    "/healthz",
    "/feed.xml",
    "/en/feed.xml",
    "/search-index.json",
})

# Fragments de chemins typiques des scanners de vulnérabilités.
_SCANNER_PATH_FRAGMENTS: tuple[str, ...] = (
    ".env",
    ".git",
    ".php",
    ".asp",
    ".aspx",
    "wp-admin",
    "wp-login",
    "wp-content",
    "wp-includes",
    "/xmlrpc",
    "phpmyadmin",
    "config.js",
    "config.json",
    "settings.js",
    "bot-connect",
    "support_parent",
    "qr_modal",
    "twint_ch",
    "lkk_ch",
    "/assets/",
    "/css/",
    "/js/",
)

_INTERNAL_ANALYTICS_IPS: frozenset[str] = frozenset({
    "127.0.0.1",
    "::1",
})

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
    "python-urllib",
    "scrapy",
    "httpx/",
    "aiohttp/",
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
    "acme-challenge",
    "certbot",
    "letsencrypt",
    "caddy",
    "scalingo",
    "lwspanel",
    "prospectscope",
    "werkzeug/",
    "axios/",
    "cutycapt",
    "google-site-verification",
    "okhttp/",
    "java/",
    "libwww-perl",
    "node-fetch",
    "postman",
    "insomnia/",
    "nmap",
    "nikto",
    "sqlmap",
    "masscan",
    "undici",
    "applebot",
    "storebot",
    "google-inspectiontool",
    "chrome privacy preserving",
    "censysinspect",
    "zgrab",
    "libredtail",
    "zmeu",
    "sitelockspider",
    "siteauditbot",
    "seokicks",
    "serpstatbot",
    "dataforseo",
    "megaindex",
    "seranking",
    "serpstat",
)


def analytics_excluded_ips() -> frozenset[str]:
    env_ips = {
        ip.strip()
        for ip in os.environ.get("ANALYTICS_EXCLUDED_IPS", "").split(",")
        if ip.strip()
    }
    return _INTERNAL_ANALYTICS_IPS | env_ips


def analytics_ip_hash(client_ip: str = "") -> str:
    ip = (client_ip or "").strip() or "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def internal_ip_hashes() -> frozenset[str]:
    return frozenset(analytics_ip_hash(ip) for ip in _INTERNAL_ANALYTICS_IPS)


def is_analytics_internal_ip(client_ip: str = "") -> bool:
    ip = (client_ip or "").strip()
    return bool(ip and ip in _INTERNAL_ANALYTICS_IPS)


def is_analytics_excluded_ip(client_ip: str = "") -> bool:
    ip = (client_ip or "").strip()
    return bool(ip and ip in analytics_excluded_ips())


def is_analytics_infra_path(path: str = "") -> bool:
    p = (path or "").split("?", 1)[0]
    return p in _INFRA_ANALYTICS_PATHS


def is_analytics_scanner_path(path: str = "") -> bool:
    p = (path or "").lower()
    if not p or p == "/":
        return False
    if p.startswith("/."):
        return True
    return any(fragment in p for fragment in _SCANNER_PATH_FRAGMENTS)


def is_analytics_excluded_path(path: str = "") -> bool:
    p = path or ""
    if any(p.startswith(prefix) for prefix in _ANALYTICS_EXCLUDED_PATH_PREFIXES):
        return True
    if is_analytics_infra_path(p):
        return True
    return is_analytics_scanner_path(p)


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
        return True
    if is_ai_crawler(ua):
        return True
    low = ua.lower()
    return any(p in low for p in _EXTRA_BOT_PATTERNS)


def should_track_page_view(
    *,
    path: str,
    user_agent: str = "",
    client_ip: str = "",
) -> bool:
    """True uniquement pour un visiteur humain réel."""
    if is_analytics_excluded_path(path):
        return False
    if is_analytics_excluded_ip(client_ip):
        return False
    if is_analytics_bot(user_agent):
        return False
    return True


def is_same_site_referrer(referrer: str = "", host: str = "") -> bool:
    """True si le clic provient d'une page du site (referrer même domaine).

    Un clic affilié réel naît d'un bouton cliqué sur une page du site : le navigateur
    envoie alors un Referer du même hôte. Les bots à user-agent usurpé qui tapent
    directement /go/?to=... (ou viennent d'un domaine externe) n'ont pas ce referrer
    et sont donc exclus du revenu estimé.
    """
    from urllib.parse import urlparse

    ref = (referrer or "").strip()
    host = (host or "").strip().lower()
    if not ref or not host:
        return False
    try:
        ref_host = urlparse(ref).netloc.lower()
    except Exception:
        return False
    if not ref_host:
        return False
    # Tolère le préfixe www. de part et d'autre.
    return ref_host.removeprefix("www.") == host.removeprefix("www.")


def should_track_affiliate_click(
    *,
    user_agent: str = "",
    client_ip: str = "",
    referrer: str = "",
    host: str = "",
) -> bool:
    """True uniquement pour un clic affilié humain réel.

    Filtre : IP interne/exclue, user-agent bot/crawler/scanner, et exige un referrer
    du même site (preuve d'une navigation humaine depuis une page du site).
    """
    if is_analytics_excluded_ip(client_ip):
        return False
    if is_analytics_bot(user_agent):
        return False
    if not is_same_site_referrer(referrer, host):
        return False
    return True


def not_bot_pg_sql(column: str = "user_agent") -> str:
    pattern = "|".join(re.escape(p) for p in _all_bot_patterns())
    return f" AND COALESCE({column}, '') !~* '{pattern}' "


def not_bot_sqlite_sql(column: str = "user_agent") -> str:
    parts = []
    for p in _all_bot_patterns():
        safe = p.replace("'", "''")
        parts.append(f"LOWER(COALESCE({column}, '')) NOT LIKE '%{safe}%'")
    return " AND " + " AND ".join(parts)


def not_excluded_path_pg_sql(column: str = "path") -> str:
    clauses = " AND ".join(
        f"COALESCE({column}, '') NOT LIKE '{prefix}%%'"
        for prefix in _ANALYTICS_EXCLUDED_PATH_PREFIXES
    )
    infra = " AND ".join(
        f"COALESCE({column}, '') <> '{path}'"
        for path in sorted(_INFRA_ANALYTICS_PATHS)
    )
    scanner = " AND ".join(
        f"LOWER(COALESCE({column}, '')) NOT LIKE '%%{frag.replace(chr(39), chr(39)*2)}%%'"
        for frag in _SCANNER_PATH_FRAGMENTS
    )
    hidden = f" AND LOWER(COALESCE({column}, '')) NOT LIKE '/.%%' "
    return f" AND {clauses} AND {infra} AND {scanner}{hidden} "


def not_excluded_path_sqlite_sql(column: str = "path") -> str:
    parts = [
        f"COALESCE({column}, '') NOT LIKE '{prefix}%'"
        for prefix in _ANALYTICS_EXCLUDED_PATH_PREFIXES
    ]
    parts.extend(
        f"COALESCE({column}, '') <> '{path}'"
        for path in sorted(_INFRA_ANALYTICS_PATHS)
    )
    for frag in _SCANNER_PATH_FRAGMENTS:
        safe = frag.replace("'", "''")
        parts.append(f"LOWER(COALESCE({column}, '')) NOT LIKE '%{safe}%'")
    parts.append(f"LOWER(COALESCE({column}, '')) NOT LIKE '/.%'")
    return " AND " + " AND ".join(parts)


def not_internal_ip_pg_sql(column: str = "ip_hash") -> str:
    hashes = sorted(internal_ip_hashes())
    if not hashes:
        return ""
    quoted = ", ".join(f"'{h}'" for h in hashes)
    return f" AND COALESCE({column}, '') NOT IN ({quoted}) "


def not_internal_ip_sqlite_sql(column: str = "ip_hash") -> str:
    parts = []
    for h in sorted(internal_ip_hashes()):
        safe = h.replace("'", "''")
        parts.append(f"COALESCE({column}, '') <> '{safe}'")
    return " AND " + " AND ".join(parts) if parts else ""


def not_excluded_path_sql(column: str = "path", *, postgres: bool) -> str:
    if postgres:
        return not_excluded_path_pg_sql(column)
    return not_excluded_path_sqlite_sql(column)


def not_bot_sql(column: str = "user_agent", *, postgres: bool) -> str:
    if postgres:
        return not_bot_pg_sql(column)
    return not_bot_sqlite_sql(column)


def not_internal_ip_sql(column: str = "ip_hash", *, postgres: bool) -> str:
    if postgres:
        return not_internal_ip_pg_sql(column)
    return not_internal_ip_sqlite_sql(column)


def visitor_traffic_sql(
    *,
    postgres: bool,
    user_agent_column: str = "user_agent",
    path_column: str = "path",
    ip_hash_column: str = "ip_hash",
) -> str:
    return (
        not_bot_sql(user_agent_column, postgres=postgres)
        + not_excluded_path_sql(path_column, postgres=postgres)
        + not_internal_ip_sql(ip_hash_column, postgres=postgres)
    )


def real_affiliate_click_sql(*, postgres: bool) -> str:
    """Filtre clics affiliés — exige user_agent humain connu (pas de clics legacy sans UA)."""
    return (
        " AND user_agent IS NOT NULL AND TRIM(user_agent) <> '' "
        + not_bot_sql("user_agent", postgres=postgres)
        + not_internal_ip_sql("ip_hash", postgres=postgres)
    )
