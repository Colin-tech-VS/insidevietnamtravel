"""Données tableau de bord affiliation."""

from data.affiliate_partners import BUILTIN_PARTNERS, PARTNER_BY_ID
from admin import db
from admin.store import get_affiliate_ids, get_custom_partners, get_settings, is_configured


def _provider_is_configured(provider: str, ids: dict | None = None) -> bool:
    """True si le partenaire a un vrai code affilié (pas PLACEHOLDER)."""
    ids = ids if ids is not None else get_affiliate_ids()
    builtin = PARTNER_BY_ID.get(provider)
    if builtin:
        return is_configured(ids.get(builtin["id_key"], ""))
    for p in get_custom_partners():
        if p["id"] == provider:
            return is_configured(p.get("affiliate_url", ""))
    return False


def compute_estimated_commission(days: int = 30) -> float:
    """Estimation uniquement pour les partenaires avec ID affilié réel."""
    aff = db.get_affiliate_stats(days)
    rates = get_settings().get("commission_estimates", {})
    ids = get_affiliate_ids()
    total = 0.0
    for row in aff["by_provider"]:
        if not _provider_is_configured(row["provider"], ids):
            continue
        rate = rates.get(row["provider"], PARTNER_BY_ID.get(row["provider"], {}).get("avg_per_click", 3.0))
        total += row["clicks"] * rate
    return round(total, 2)


def _clicks_map(days: int) -> dict:
    stats = db.get_affiliate_stats(days)
    return {row["provider"]: row["clicks"] for row in stats["by_provider"]}


def _revenue_map() -> dict:
    data = db.get_revenue_stats()
    totals: dict[str, float] = {}
    for entry in data["entries"]:
        src = entry["source"]
        totals[src] = totals.get(src, 0) + float(entry["amount"])
    return totals


def build_partner_rows(days: int = 30) -> list:
    ids = get_affiliate_ids()
    clicks = _clicks_map(days)
    revenue = _revenue_map()
    rows = []

    for p in BUILTIN_PARTNERS:
        pid = p["id"]
        aff_id = ids.get(p["id_key"], "")
        click_count = clicks.get(pid, 0)
        configured = is_configured(aff_id)
        est = round(click_count * p["avg_per_click"], 2) if configured else 0.0
        confirmed = round(revenue.get(pid, 0), 2)
        rows.append({
            **p,
            "builtin": True,
            "affiliate_id": aff_id,
            "configured": is_configured(aff_id),
            "clicks": click_count,
            "estimated_eur": est,
            "confirmed_eur": confirmed,
        })

    for p in get_custom_partners():
        pid = p["id"]
        click_count = clicks.get(pid, 0)
        avg = float(p.get("avg_per_click", 3.0))
        est = round(click_count * avg, 2) if is_configured(p.get("affiliate_url", "")) else 0.0
        confirmed = round(revenue.get(pid, 0), 2)
        rows.append({
            "id": pid,
            "id_key": None,
            "name": p["name"],
            "category": p.get("category", "Autre"),
            "icon": p.get("icon", "🔗"),
            "description": p.get("description", ""),
            "what_you_earn": p.get("what_you_earn", "Variable"),
            "avg_per_click": avg,
            "signup_url": p.get("signup_url", ""),
            "id_label": "Lien affilié complet",
            "id_placeholder": "https://...?ref=VOTRE_ID",
            "builtin": False,
            "affiliate_id": p.get("affiliate_url", ""),
            "configured": is_configured(p.get("affiliate_url", "")),
            "clicks": click_count,
            "estimated_eur": est,
            "confirmed_eur": confirmed,
        })

    rows.sort(key=lambda r: r["clicks"], reverse=True)
    return rows


def build_affiliate_summary(days: int = 30) -> dict:
    """Stats affiliation uniquement — pas le trafic général du site."""
    aff = db.get_affiliate_stats(days)
    partners = build_partner_rows(days)
    est_total = sum(p["estimated_eur"] for p in partners)
    confirmed_aff = sum(p["confirmed_eur"] for p in partners)

    return {
        "days": days,
        "clicks_period": aff["total_clicks"],
        "estimated_eur": round(est_total, 2),
        "confirmed_eur": round(confirmed_aff, 2),
        "daily_clicks": db.get_daily_affiliate_clicks(days),
        "partners": partners,
        "clicks_by_partner": [
            {"name": p["name"], "clicks": p["clicks"], "estimated": p["estimated_eur"]}
            for p in partners if p["clicks"] > 0
        ],
    }


def build_site_analytics(days: int = 30) -> dict:
    """Trafic du site — pour l'onglet Analytics."""
    realtime = db.get_realtime_stats()
    daily_views = db.get_daily_views(days)
    aff = db.get_affiliate_stats(days)

    return {
        "days": days,
        "active_visitors": realtime["active_visitors"],
        "views_30m": realtime["views_30m"],
        "clicks_30m": realtime["clicks_30m"],
        "views_period": sum(d["views"] for d in daily_views),
        "clicks_period": aff["total_clicks"],
        "daily_views": daily_views,
        "daily_clicks": db.get_daily_affiliate_clicks(days),
        "top_pages": realtime["top_pages"],
        "recent": realtime["recent"],
    }
