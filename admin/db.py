"""Analytics, revenus et clics affiliés — PostgreSQL (Supabase) ou SQLite local."""

from datetime import date, datetime, timedelta

from admin.analytics_filters import (
    not_excluded_path_sql,
    real_affiliate_click_sql,
    visitor_traffic_sql,
)
from admin.database import get_connection, ensure_schema, init_schema, is_postgres

init_db = init_schema


def _serialize_value(v):
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


def _row_dict(row) -> dict:
    if row is None:
        return {}
    if isinstance(row, dict):
        return {k: _serialize_value(v) for k, v in row.items()}
    return {k: _serialize_value(row[k]) for k in row.keys()}


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _since(minutes: int) -> str:
    return (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()


def _since_days(days: int) -> str:
    return (datetime.utcnow() - timedelta(days=days)).isoformat()


def _human_traffic_sql() -> str:
    """Exclut crawlers, robots, localhost et chemins infra des stats visiteurs."""
    return visitor_traffic_sql(postgres=is_postgres())


def _real_affiliate_click_sql() -> str:
    """Clics affiliés humains vérifiés (user-agent + IP, hors legacy sans métadonnées)."""
    return real_affiliate_click_sql(postgres=is_postgres())


def _execute(conn, sql_pg: str, sql_sqlite: str, params=()):
    if is_postgres():
        cur = conn.cursor()
        cur.execute(sql_pg, params)
        return cur
    return conn.execute(sql_sqlite, params)


def log_page_view(
    path: str,
    referrer: str,
    user_agent: str,
    ip_hash: str,
    country_code: str = "",
    country_name: str = "",
    city: str = "",
    utm_source: str = "",
    utm_campaign: str = "",
):
    with get_connection() as conn:
        _execute(
            conn,
            """INSERT INTO page_views
               (path, referrer, user_agent, ip_hash, country_code, country_name, city,
                utm_source, utm_campaign, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            """INSERT INTO page_views
               (path, referrer, user_agent, ip_hash, country_code, country_name, city,
                utm_source, utm_campaign, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (path, referrer, user_agent, ip_hash, country_code, country_name, city,
             utm_source, utm_campaign, _now_iso()),
        )


def get_social_traffic(days: int = 30):
    """Vues issues des réseaux sociaux (UTM), agrégées par source et campagne.

    Le maillage interne (utm_source='interne') porte aussi des UTM mais N'EST PAS du
    trafic social : on l'exclut ici pour ne pas fausser ce tableau.
    """
    from admin.internal_links import UTM_SOURCE as INTERNAL_UTM_SOURCE

    since = _since_days(days)
    bot = _human_traffic_sql()
    out = {"total": 0, "by_source": [], "by_campaign": []}
    with get_connection() as conn:
        cur = _execute(
            conn,
            f"SELECT COALESCE(utm_source,'') AS s, COUNT(*) AS n FROM page_views "
            f"WHERE created_at >= %s AND COALESCE(utm_source,'') NOT IN ('', %s) {bot} "
            f"GROUP BY s ORDER BY n DESC",
            f"SELECT COALESCE(utm_source,'') AS s, COUNT(*) AS n FROM page_views "
            f"WHERE created_at >= ? AND COALESCE(utm_source,'') NOT IN ('', ?) {bot} "
            f"GROUP BY s ORDER BY n DESC",
            (since, INTERNAL_UTM_SOURCE),
        )
        rows = [_row_dict(r) for r in cur.fetchall()]
        out["by_source"] = rows
        out["total"] = sum(r.get("n", 0) for r in rows)

        cur = _execute(
            conn,
            f"SELECT COALESCE(utm_campaign,'') AS c, COUNT(*) AS n FROM page_views "
            f"WHERE created_at >= %s AND COALESCE(utm_campaign,'') <> '' "
            f"AND COALESCE(utm_source,'') <> %s {bot} "
            f"GROUP BY c ORDER BY n DESC LIMIT 20",
            f"SELECT COALESCE(utm_campaign,'') AS c, COUNT(*) AS n FROM page_views "
            f"WHERE created_at >= ? AND COALESCE(utm_campaign,'') <> '' "
            f"AND COALESCE(utm_source,'') <> ? {bot} "
            f"GROUP BY c ORDER BY n DESC LIMIT 20",
            (since, INTERNAL_UTM_SOURCE),
        )
        out["by_campaign"] = [_row_dict(r) for r in cur.fetchall()]
    return out


def log_affiliate_click(
    provider: str,
    target_url: str,
    source_page: str,
    *,
    user_agent: str = "",
    ip_hash: str = "",
):
    with get_connection() as conn:
        _execute(
            conn,
            """INSERT INTO affiliate_clicks
               (provider, target_url, source_page, user_agent, ip_hash, created_at)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            """INSERT INTO affiliate_clicks
               (provider, target_url, source_page, user_agent, ip_hash, created_at)
               VALUES (?,?,?,?,?,?)""",
            (provider, target_url, source_page, user_agent, ip_hash, _now_iso()),
        )


def add_revenue(source: str, amount: float, note: str = "", currency: str = "EUR"):
    with get_connection() as conn:
        _execute(
            conn,
            "INSERT INTO revenue (source, amount, currency, note, created_at) VALUES (%s,%s,%s,%s,%s)",
            "INSERT INTO revenue (source, amount, currency, note, created_at) VALUES (?,?,?,?,?)",
            (source, amount, currency, note, _now_iso()),
        )


def get_realtime_stats():
    bot = _human_traffic_sql()
    with get_connection() as conn:
        active = _execute(
            conn,
            f"SELECT COUNT(DISTINCT ip_hash) AS c FROM page_views WHERE created_at >= %s{bot}",
            f"SELECT COUNT(DISTINCT ip_hash) FROM page_views WHERE created_at >= ?{bot}",
            (_since(30),),
        ).fetchone()
        views_30m = _execute(
            conn,
            f"SELECT COUNT(*) AS c FROM page_views WHERE created_at >= %s{bot}",
            f"SELECT COUNT(*) FROM page_views WHERE created_at >= ?{bot}",
            (_since(30),),
        ).fetchone()
        aff = _real_affiliate_click_sql()
        clicks_30m = _execute(
            conn,
            f"SELECT COUNT(*) AS c FROM affiliate_clicks WHERE created_at >= %s{aff}",
            f"SELECT COUNT(*) FROM affiliate_clicks WHERE created_at >= ?{aff}",
            (_since(30),),
        ).fetchone()
        recent = _execute(
            conn,
            f"""SELECT path, created_at, country_code, country_name, city
                FROM page_views WHERE 1=1{bot} ORDER BY id DESC LIMIT 15""",
            f"""SELECT path, created_at, country_code, country_name, city
                FROM page_views WHERE 1=1{bot} ORDER BY id DESC LIMIT 15""",
        ).fetchall()
        top_pages = _execute(
            conn,
            f"""SELECT path, COUNT(*) AS c FROM page_views
               WHERE created_at >= %s{bot} GROUP BY path ORDER BY c DESC LIMIT 10""",
            f"""SELECT path, COUNT(*) as c FROM page_views
               WHERE created_at >= ?{bot} GROUP BY path ORDER BY c DESC LIMIT 10""",
            (_since(60 * 24),),
        ).fetchall()
    return {
        "active_visitors": active["c"] if isinstance(active, dict) else active[0],
        "views_30m": views_30m["c"] if isinstance(views_30m, dict) else views_30m[0],
        "clicks_30m": clicks_30m["c"] if isinstance(clicks_30m, dict) else clicks_30m[0],
        "recent": [_row_dict(r) for r in recent],
        "top_pages": [_row_dict(r) for r in top_pages],
    }


def get_daily_views(days: int = 30):
    bot = _human_traffic_sql()
    with get_connection() as conn:
        rows = _execute(
            conn,
            f"""SELECT created_at::date AS day, COUNT(*) AS views
               FROM page_views WHERE created_at >= %s{bot} GROUP BY day ORDER BY day""",
            f"""SELECT date(created_at) as day, COUNT(*) as views
               FROM page_views WHERE created_at >= ?{bot} GROUP BY day ORDER BY day""",
            (_since_days(days),),
        ).fetchall()
    return [_row_dict(r) for r in rows]


def get_country_stats(days: int = 30) -> list[dict]:
    bot = _human_traffic_sql()
    with get_connection() as conn:
        rows = _execute(
            conn,
            f"""SELECT COALESCE(NULLIF(country_code, ''), '??') AS country_code,
                       COALESCE(NULLIF(country_name, ''), 'Inconnu') AS country_name,
                       COUNT(*) AS views
                FROM page_views
                WHERE created_at >= %s{bot}
                GROUP BY country_code, country_name
                ORDER BY views DESC
                LIMIT 15""",
            f"""SELECT COALESCE(NULLIF(country_code, ''), '??') AS country_code,
                       COALESCE(NULLIF(country_name, ''), 'Inconnu') AS country_name,
                       COUNT(*) AS views
                FROM page_views
                WHERE created_at >= ?{bot}
                GROUP BY country_code, country_name
                ORDER BY views DESC
                LIMIT 15""",
            (_since_days(days),),
        ).fetchall()
    return [_row_dict(r) for r in rows]


def get_city_stats(days: int = 30) -> list[dict]:
    bot = _human_traffic_sql()
    with get_connection() as conn:
        rows = _execute(
            conn,
            f"""SELECT COALESCE(NULLIF(city, ''), 'Inconnu') AS city,
                       COALESCE(NULLIF(country_code, ''), '??') AS country_code,
                       COALESCE(NULLIF(country_name, ''), 'Inconnu') AS country_name,
                       COUNT(*) AS views
                FROM page_views
                WHERE created_at >= %s
                  AND COALESCE(NULLIF(city, ''), '') <> ''{bot}
                GROUP BY city, country_code, country_name
                ORDER BY views DESC
                LIMIT 15""",
            f"""SELECT COALESCE(NULLIF(city, ''), 'Inconnu') AS city,
                       COALESCE(NULLIF(country_code, ''), '??') AS country_code,
                       COALESCE(NULLIF(country_name, ''), 'Inconnu') AS country_name,
                       COUNT(*) AS views
                FROM page_views
                WHERE created_at >= ?
                  AND COALESCE(NULLIF(city, ''), '') <> ''{bot}
                GROUP BY city, country_code, country_name
                ORDER BY views DESC
                LIMIT 15""",
            (_since_days(days),),
        ).fetchall()
    return [_row_dict(r) for r in rows]


def get_geo_view_rows(days: int = 30) -> list[dict]:
    """Page views avec referrer + UA pour classification GEO (LLM / moteurs IA)."""
    path_excl = not_excluded_path_sql(postgres=is_postgres())
    with get_connection() as conn:
        rows = _execute(
            conn,
            f"""SELECT path, referrer, user_agent, created_at::text AS created_at
               FROM page_views WHERE created_at >= %s{path_excl} ORDER BY id DESC""",
            f"""SELECT path, referrer, user_agent, created_at
               FROM page_views WHERE created_at >= ?{path_excl} ORDER BY id DESC""",
            (_since_days(days),),
        ).fetchall()
    return [_row_dict(r) for r in rows]


def get_seo_view_rows(days: int = 30) -> list[dict]:
    """Page views humaines avec referrer — analytics SEO (hors robots)."""
    bot = _human_traffic_sql()
    with get_connection() as conn:
        rows = _execute(
            conn,
            f"""SELECT path, referrer, user_agent, created_at::text AS created_at
                FROM page_views WHERE created_at >= %s{bot} ORDER BY id DESC""",
            f"""SELECT path, referrer, user_agent, created_at
                FROM page_views WHERE created_at >= ?{bot} ORDER BY id DESC""",
            (_since_days(days),),
        ).fetchall()
    return [_row_dict(r) for r in rows]


def get_daily_affiliate_clicks(days: int = 30):
    aff = _real_affiliate_click_sql()
    with get_connection() as conn:
        rows = _execute(
            conn,
            f"""SELECT created_at::date AS day, COUNT(*) AS clicks
               FROM affiliate_clicks WHERE created_at >= %s{aff} GROUP BY day ORDER BY day""",
            f"""SELECT date(created_at) as day, COUNT(*) as clicks
               FROM affiliate_clicks WHERE created_at >= ?{aff} GROUP BY day ORDER BY day""",
            (_since_days(days),),
        ).fetchall()
    return [_row_dict(r) for r in rows]


def get_revenue_by_source(days: int = 90):
    with get_connection() as conn:
        rows = _execute(
            conn,
            """SELECT source, SUM(amount) AS total, COUNT(*) AS count
               FROM revenue WHERE created_at >= %s GROUP BY source ORDER BY total DESC""",
            """SELECT source, SUM(amount) as total, COUNT(*) as count
               FROM revenue WHERE created_at >= ? GROUP BY source ORDER BY total DESC""",
            (_since_days(days),),
        ).fetchall()
    return [_row_dict(r) for r in rows]


def get_affiliate_stats(days: int = 30):
    aff = _real_affiliate_click_sql()
    with get_connection() as conn:
        by_provider = _execute(
            conn,
            f"""SELECT provider, COUNT(*) AS clicks FROM affiliate_clicks
               WHERE created_at >= %s{aff} GROUP BY provider ORDER BY clicks DESC""",
            f"""SELECT provider, COUNT(*) as clicks FROM affiliate_clicks
               WHERE created_at >= ?{aff} GROUP BY provider ORDER BY clicks DESC""",
            (_since_days(days),),
        ).fetchall()
        total_clicks = _execute(
            conn,
            f"SELECT COUNT(*) AS c FROM affiliate_clicks WHERE created_at >= %s{aff}",
            f"SELECT COUNT(*) FROM affiliate_clicks WHERE created_at >= ?{aff}",
            (_since_days(days),),
        ).fetchone()
    tc = total_clicks["c"] if isinstance(total_clicks, dict) else total_clicks[0]
    return {"by_provider": [_row_dict(r) for r in by_provider], "total_clicks": tc}


def get_revenue_stats():
    with get_connection() as conn:
        rows = _execute(
            conn,
            "SELECT * FROM revenue ORDER BY created_at DESC LIMIT 50",
            "SELECT * FROM revenue ORDER BY created_at DESC LIMIT 50",
        ).fetchall()
        total = _execute(
            conn,
            "SELECT COALESCE(SUM(amount),0) AS t FROM revenue",
            "SELECT COALESCE(SUM(amount),0) FROM revenue",
        ).fetchone()
        month_total = _execute(
            conn,
            "SELECT COALESCE(SUM(amount),0) AS t FROM revenue WHERE created_at >= %s",
            "SELECT COALESCE(SUM(amount),0) FROM revenue WHERE created_at >= ?",
            (_since_days(30),),
        ).fetchone()
    t = total["t"] if isinstance(total, dict) else total[0]
    m = month_total["t"] if isinstance(month_total, dict) else month_total[0]
    return {
        "entries": [_row_dict(r) for r in rows],
        "total": round(float(t), 2),
        "month_total": round(float(m), 2),
    }


def get_dashboard_totals():
    bot = _human_traffic_sql()
    with get_connection() as conn:
        total_views = _execute(
            conn,
            f"SELECT COUNT(*) AS c FROM page_views WHERE 1=1{bot}",
            f"SELECT COUNT(*) FROM page_views WHERE 1=1{bot}",
        ).fetchone()
        today_views = _execute(
            conn,
            f"SELECT COUNT(*) AS c FROM page_views WHERE created_at::date = CURRENT_DATE{bot}",
            f"SELECT COUNT(*) FROM page_views WHERE date(created_at) = date('now'){bot}",
        ).fetchone()
        aff = _real_affiliate_click_sql()
        total_clicks = _execute(
            conn,
            f"SELECT COUNT(*) AS c FROM affiliate_clicks WHERE 1=1{aff}",
            f"SELECT COUNT(*) FROM affiliate_clicks WHERE 1=1{aff}",
        ).fetchone()
    def _v(row):
        return row["c"] if isinstance(row, dict) else row[0]
    return {
        "total_views": _v(total_views),
        "today_views": _v(today_views),
        "total_clicks": _v(total_clicks),
    }


def log_visitor_profile_snapshot(
    *,
    visitor_hash: str,
    trip_group: str = "",
    trip_style: str = "",
    trip_duration: str = "",
    cities: str = "",
    interests: str = "",
    path: str = "",
):
    if not visitor_hash:
        return
    with get_connection() as conn:
        _execute(
            conn,
            """INSERT INTO visitor_profile_snapshots
               (visitor_hash, trip_group, trip_style, trip_duration, cities, interests, path, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            """INSERT INTO visitor_profile_snapshots
               (visitor_hash, trip_group, trip_style, trip_duration, cities, interests, path, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                visitor_hash[:32],
                (trip_group or "")[:20],
                (trip_style or "")[:20],
                (trip_duration or "")[:20],
                (cities or "")[:200],
                (interests or "")[:300],
                (path or "")[:300],
                _now_iso(),
            ),
        )


def get_visitor_profile_stats(days: int = 30) -> dict:
    since = _since_days(days)
    out = {
        "total_snapshots": 0,
        "unique_visitors": 0,
        "by_style": [],
        "by_group": [],
        "by_duration": [],
        "top_cities": [],
    }
    try:
        with get_connection() as conn:
            cur = _execute(
                conn,
                "SELECT COUNT(*) AS c FROM visitor_profile_snapshots WHERE created_at >= %s",
                "SELECT COUNT(*) AS c FROM visitor_profile_snapshots WHERE created_at >= ?",
                (since,),
            )
            row = cur.fetchone()
            out["total_snapshots"] = row["c"] if isinstance(row, dict) else row[0]

            cur = _execute(
                conn,
                "SELECT COUNT(DISTINCT visitor_hash) AS c FROM visitor_profile_snapshots WHERE created_at >= %s",
                "SELECT COUNT(DISTINCT visitor_hash) AS c FROM visitor_profile_snapshots WHERE created_at >= ?",
                (since,),
            )
            row = cur.fetchone()
            out["unique_visitors"] = row["c"] if isinstance(row, dict) else row[0]

            for field, key in (
                ("trip_style", "by_style"),
                ("trip_group", "by_group"),
                ("trip_duration", "by_duration"),
            ):
                cur = _execute(
                    conn,
                    f"SELECT COALESCE({field}, '') AS k, COUNT(*) AS n "
                    f"FROM visitor_profile_snapshots WHERE created_at >= %s AND COALESCE({field}, '') <> '' "
                    f"GROUP BY k ORDER BY n DESC LIMIT 8",
                    f"SELECT COALESCE({field}, '') AS k, COUNT(*) AS n "
                    f"FROM visitor_profile_snapshots WHERE created_at >= ? AND COALESCE({field}, '') <> '' "
                    f"GROUP BY k ORDER BY n DESC LIMIT 8",
                    (since,),
                )
                out[key] = [_row_dict(r) for r in cur.fetchall()]
    except Exception:
        pass
    return out
