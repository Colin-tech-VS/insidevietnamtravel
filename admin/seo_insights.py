"""Croisement Search Console (requêtes, clics) et analytics site (visiteurs par page)."""

from __future__ import annotations

from collections import defaultdict
from urllib.parse import urlparse

from admin import db
from admin.seo_analytics import classify_traffic_channel


def gsc_page_to_path(page_url: str) -> str:
    url = (page_url or "").strip()
    if not url:
        return "/"
    if url.startswith("/"):
        return url.rstrip("/") or "/"
    parsed = urlparse(url)
    path = parsed.path or "/"
    return path.rstrip("/") or "/"


def _lookup_visitors(path: str, counts: dict[str, int]) -> int:
    if not path:
        return 0
    if path in counts:
        return counts[path]
    alt = path.rstrip("/") or "/"
    if alt in counts:
        return counts[alt]
    if alt != "/" and f"{alt}/" in counts:
        return counts[f"{alt}/"]
    return 0


def _visitor_counts_by_path(days: int) -> tuple[dict[str, int], dict[str, int], int]:
    """Visiteurs uniques par chemin (tous canaux + organique referrer) + total site."""
    all_by_path: dict[str, set[str]] = defaultdict(set)
    organic_by_path: dict[str, set[str]] = defaultdict(set)
    all_ips: set[str] = set()

    for row in db.get_seo_view_rows(days):
        ip = (row.get("ip_hash") or "").strip()
        if not ip:
            continue
        path = (row.get("path") or "/").rstrip("/") or "/"
        ref = row.get("referrer") or ""
        ua = row.get("user_agent") or ""
        all_ips.add(ip)
        all_by_path[path].add(ip)
        if classify_traffic_channel(ref, ua) == "organic":
            organic_by_path[path].add(ip)

    return (
        {p: len(visitors) for p, visitors in all_by_path.items()},
        {p: len(visitors) for p, visitors in organic_by_path.items()},
        len(all_ips),
    )


def build_mixed_insights(gsc_report: dict, site_days: int) -> dict:
    """Enrichit un rapport GSC avec les visiteurs réels du site par page."""
    all_visitors, organic_visitors, site_unique_total = _visitor_counts_by_path(site_days)

    query_pages_raw = gsc_report.get("query_pages") or []
    query_pages: list[dict] = []
    by_page_queries: dict[str, list[dict]] = defaultdict(list)

    for row in query_pages_raw:
        path = gsc_page_to_path(row.get("page", ""))
        item = {
            "query": row.get("query") or "",
            "page": row.get("page") or "",
            "path": path,
            "clicks": int(row.get("clicks") or 0),
            "impressions": int(row.get("impressions") or 0),
            "ctr": row.get("ctr", 0),
            "position": row.get("position", 0),
            "site_visitors": _lookup_visitors(path, all_visitors),
            "site_organic": _lookup_visitors(path, organic_visitors),
        }
        query_pages.append(item)
        by_page_queries[path].append(item)

    query_pages.sort(key=lambda r: (-r["clicks"], -r["impressions"], -r["site_visitors"]))

    for path in by_page_queries:
        by_page_queries[path].sort(key=lambda r: (-r["clicks"], -r["impressions"]))

    pages_mixed: list[dict] = []
    for row in gsc_report.get("pages") or []:
        path = gsc_page_to_path(row.get("page", ""))
        top_q = by_page_queries.get(path, [])[:6]
        pages_mixed.append({
            "page": row.get("page") or "",
            "path": path,
            "clicks": int(row.get("clicks") or 0),
            "impressions": int(row.get("impressions") or 0),
            "ctr": row.get("ctr", 0),
            "position": row.get("position", 0),
            "site_visitors": _lookup_visitors(path, all_visitors),
            "site_organic": _lookup_visitors(path, organic_visitors),
            "top_queries": [
                {"query": q["query"], "clicks": q["clicks"], "position": q["position"]}
                for q in top_q
            ],
        })

    queries_mixed: list[dict] = []
    by_query: dict[str, list[dict]] = defaultdict(list)
    for row in query_pages:
        by_query[row["query"]].append(row)

    for query, rows in by_query.items():
        rows_sorted = sorted(rows, key=lambda r: (-r["clicks"], -r["impressions"]))
        landing = rows_sorted[0] if rows_sorted else {}
        queries_mixed.append({
            "query": query,
            "clicks": sum(r["clicks"] for r in rows),
            "impressions": sum(r["impressions"] for r in rows),
            "pages_count": len(rows),
            "top_page": landing.get("path") or "",
            "top_page_clicks": landing.get("clicks", 0),
            "site_visitors_top": landing.get("site_visitors", 0),
        })
    queries_mixed.sort(key=lambda r: (-r["clicks"], -r["impressions"]))

    gsc_clicks = int((gsc_report.get("totals") or {}).get("clicks") or 0)
    site_organic_total = sum(organic_visitors.values())

    return {
        "site_days": site_days,
        "gsc_start": gsc_report.get("start_date") or "",
        "gsc_end": gsc_report.get("end_date") or "",
        "query_pages": query_pages[:150],
        "pages_mixed": pages_mixed,
        "queries_mixed": queries_mixed[:80],
        "totals": {
            "gsc_clicks": gsc_clicks,
            "site_unique": site_unique_total,
            "site_organic": site_organic_total,
        },
    }
