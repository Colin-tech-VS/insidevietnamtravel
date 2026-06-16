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
    """Visiteurs uniques issus des réseaux sociaux (UTM), agrégés par source et campagne.

    Le maillage interne (utm_source='interne') porte aussi des UTM mais N'EST PAS du
    trafic social : on l'exclut ici pour ne pas fausser ce tableau.
    """
    from admin.internal_links import UTM_SOURCE as INTERNAL_UTM_SOURCE

    since = _since_days(days)
    bot = _human_traffic_sql()
    distinct = " AND COALESCE(ip_hash, '') <> ''"
    out = {"total": 0, "by_source": [], "by_campaign": []}
    with get_connection() as conn:
        cur = _execute(
            conn,
            f"SELECT COALESCE(utm_source,'') AS s, COUNT(DISTINCT ip_hash) AS n FROM page_views "
            f"WHERE created_at >= %s AND COALESCE(utm_source,'') NOT IN ('', %s){distinct}{bot} "
            f"GROUP BY s ORDER BY n DESC",
            f"SELECT COALESCE(utm_source,'') AS s, COUNT(DISTINCT ip_hash) AS n FROM page_views "
            f"WHERE created_at >= ? AND COALESCE(utm_source,'') NOT IN ('', ?){distinct}{bot} "
            f"GROUP BY s ORDER BY n DESC",
            (since, INTERNAL_UTM_SOURCE),
        )
        rows = [_row_dict(r) for r in cur.fetchall()]
        out["by_source"] = rows
        out["total"] = sum(r.get("n", 0) for r in rows)

        cur = _execute(
            conn,
            f"SELECT COALESCE(utm_campaign,'') AS c, COUNT(DISTINCT ip_hash) AS n FROM page_views "
            f"WHERE created_at >= %s AND COALESCE(utm_campaign,'') <> '' "
            f"AND COALESCE(utm_source,'') <> %s{distinct}{bot} "
            f"GROUP BY c ORDER BY n DESC LIMIT 20",
            f"SELECT COALESCE(utm_campaign,'') AS c, COUNT(DISTINCT ip_hash) AS n FROM page_views "
            f"WHERE created_at >= ? AND COALESCE(utm_campaign,'') <> '' "
            f"AND COALESCE(utm_source,'') <> ?{distinct}{bot} "
            f"GROUP BY c ORDER BY n DESC LIMIT 20",
            (since, INTERNAL_UTM_SOURCE),
        )
        out["by_campaign"] = [_row_dict(r) for r in cur.fetchall()]
    return out


def get_email_traffic(days: int = 30) -> dict:
    """Pages vues depuis les emails (UTM utm_medium=email via utm_source newsletter/partenariat…)."""
    from admin.email_tracking_service import EMAIL_UTM_SOURCES

    since = _since_days(days)
    bot = _human_traffic_sql()
    sources = tuple(sorted(EMAIL_UTM_SOURCES))
    placeholders_pg = ",".join(["%s"] * len(sources))
    placeholders_sql = ",".join(["?"] * len(sources))
    out = {"total": 0, "by_source": [], "by_campaign": []}
    with get_connection() as conn:
        cur = _execute(
            conn,
            f"SELECT COALESCE(utm_source,'') AS s, COUNT(*) AS n FROM page_views "
            f"WHERE created_at >= %s AND COALESCE(utm_source,'') IN ({placeholders_pg}) {bot} "
            f"GROUP BY s ORDER BY n DESC",
            f"SELECT COALESCE(utm_source,'') AS s, COUNT(*) AS n FROM page_views "
            f"WHERE created_at >= ? AND COALESCE(utm_source,'') IN ({placeholders_sql}) {bot} "
            f"GROUP BY s ORDER BY n DESC",
            (since, *sources),
        )
        rows = [_row_dict(r) for r in cur.fetchall()]
        out["by_source"] = rows
        out["total"] = sum(r.get("n", 0) for r in rows)

        cur = _execute(
            conn,
            f"SELECT COALESCE(utm_campaign,'') AS c, COUNT(*) AS n FROM page_views "
            f"WHERE created_at >= %s AND COALESCE(utm_campaign,'') <> '' "
            f"AND COALESCE(utm_source,'') IN ({placeholders_pg}) {bot} "
            f"GROUP BY c ORDER BY n DESC LIMIT 15",
            f"SELECT COALESCE(utm_campaign,'') AS c, COUNT(*) AS n FROM page_views "
            f"WHERE created_at >= ? AND COALESCE(utm_campaign,'') <> '' "
            f"AND COALESCE(utm_source,'') IN ({placeholders_sql}) {bot} "
            f"GROUP BY c ORDER BY n DESC LIMIT 15",
            (since, *sources),
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
    distinct = " AND COALESCE(ip_hash, '') <> ''"
    with get_connection() as conn:
        active = _execute(
            conn,
            f"SELECT COUNT(DISTINCT ip_hash) AS c FROM page_views WHERE created_at >= %s{distinct}{bot}",
            f"SELECT COUNT(DISTINCT ip_hash) FROM page_views WHERE created_at >= ?{distinct}{bot}",
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
            f"""SELECT path, COUNT(DISTINCT ip_hash) AS c FROM page_views
               WHERE created_at >= %s AND COALESCE(ip_hash, '') <> ''{bot}
               GROUP BY path ORDER BY c DESC LIMIT 10""",
            f"""SELECT path, COUNT(DISTINCT ip_hash) as c FROM page_views
               WHERE created_at >= ? AND COALESCE(ip_hash, '') <> ''{bot}
               GROUP BY path ORDER BY c DESC LIMIT 10""",
            (_since(60 * 24),),
        ).fetchall()
    active_n = active["c"] if isinstance(active, dict) else active[0]
    return {
        "active_visitors": active_n,
        "unique_visitors_30m": active_n,
        "clicks_30m": clicks_30m["c"] if isinstance(clicks_30m, dict) else clicks_30m[0],
        "recent": [_row_dict(r) for r in recent],
        "top_pages": [_row_dict(r) for r in top_pages],
    }


def get_realtime_timeline() -> list[dict]:
    """Visiteurs uniques par minute sur les 30 dernières minutes."""
    bot = _human_traffic_sql()
    distinct = " AND COALESCE(ip_hash, '') <> ''"
    now = datetime.utcnow()
    with get_connection() as conn:
        rows = _execute(
            conn,
            f"""SELECT date_trunc('minute', created_at) AS minute, COUNT(DISTINCT ip_hash) AS visitors
                FROM page_views
                WHERE created_at >= %s{distinct}{bot}
                GROUP BY minute
                ORDER BY minute""",
            f"""SELECT strftime('%Y-%m-%dT%H:%M', created_at) AS minute, COUNT(DISTINCT ip_hash) AS visitors
                FROM page_views
                WHERE created_at >= ?{distinct}{bot}
                GROUP BY minute
                ORDER BY minute""",
            (_since(30),),
        ).fetchall()
    data = {}
    for row in rows:
        d = _row_dict(row)
        key = d["minute"] if isinstance(d["minute"], str) else d["minute"].isoformat()
        data[key[:16]] = d["visitors"]
    timeline = []
    for i in range(30, 0, -1):
        m = (now - timedelta(minutes=i)).replace(second=0, microsecond=0)
        key = m.strftime("%Y-%m-%dT%H:%M")
        timeline.append({"minute": m.strftime("%H:%M"), "visitors": data.get(key, 0)})
    return timeline


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
                       COUNT(DISTINCT ip_hash) AS visitors
                FROM page_views
                WHERE created_at >= %s AND COALESCE(ip_hash, '') <> ''{bot}
                GROUP BY country_code, country_name
                ORDER BY visitors DESC
                LIMIT 15""",
            f"""SELECT COALESCE(NULLIF(country_code, ''), '??') AS country_code,
                       COALESCE(NULLIF(country_name, ''), 'Inconnu') AS country_name,
                       COUNT(DISTINCT ip_hash) AS visitors
                FROM page_views
                WHERE created_at >= ? AND COALESCE(ip_hash, '') <> ''{bot}
                GROUP BY country_code, country_name
                ORDER BY visitors DESC
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
                       COUNT(DISTINCT ip_hash) AS visitors
                FROM page_views
                WHERE created_at >= %s
                  AND COALESCE(NULLIF(city, ''), '') <> ''
                  AND COALESCE(ip_hash, '') <> ''{bot}
                GROUP BY city, country_code, country_name
                ORDER BY visitors DESC
                LIMIT 15""",
            f"""SELECT COALESCE(NULLIF(city, ''), 'Inconnu') AS city,
                       COALESCE(NULLIF(country_code, ''), '??') AS country_code,
                       COALESCE(NULLIF(country_name, ''), 'Inconnu') AS country_name,
                       COUNT(DISTINCT ip_hash) AS visitors
                FROM page_views
                WHERE created_at >= ?
                  AND COALESCE(NULLIF(city, ''), '') <> ''
                  AND COALESCE(ip_hash, '') <> ''{bot}
                GROUP BY city, country_code, country_name
                ORDER BY visitors DESC
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
            f"""SELECT path, referrer, user_agent, ip_hash, created_at::text AS created_at
               FROM page_views WHERE created_at >= %s{path_excl} ORDER BY id DESC""",
            f"""SELECT path, referrer, user_agent, ip_hash, created_at
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
            f"""SELECT path, referrer, user_agent, ip_hash, created_at::text AS created_at
                FROM page_views WHERE created_at >= %s{bot} ORDER BY id DESC""",
            f"""SELECT path, referrer, user_agent, ip_hash, created_at
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
    distinct = " AND COALESCE(ip_hash, '') <> ''"
    with get_connection() as conn:
        total_visitors = _execute(
            conn,
            f"SELECT COUNT(DISTINCT ip_hash) AS c FROM page_views WHERE 1=1{distinct}{bot}",
            f"SELECT COUNT(DISTINCT ip_hash) FROM page_views WHERE 1=1{distinct}{bot}",
        ).fetchone()
        today_visitors = _execute(
            conn,
            f"SELECT COUNT(DISTINCT ip_hash) AS c FROM page_views WHERE created_at::date = CURRENT_DATE{distinct}{bot}",
            f"SELECT COUNT(DISTINCT ip_hash) FROM page_views WHERE date(created_at) = date('now'){distinct}{bot}",
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
        "total_visitors": _v(total_visitors),
        "today_visitors": _v(today_visitors),
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


def _user_key_sql() -> str:
    """Identifiant visiteur : cookie profil prioritaire, sinon empreinte IP."""
    return "COALESCE(NULLIF(visitor_hash, ''), NULLIF(ip_hash, ''))"


def log_mai_chat_event(
    event_type: str,
    *,
    ip_hash: str = "",
    visitor_hash: str = "",
    lang: str = "fr",
    path: str = "",
    had_profile: bool = False,
    message_length: int = 0,
    site_links_count: int = 0,
    affiliate_links_count: int = 0,
    error_code: str = "",
    question_text: str = "",
):
    event_type = (event_type or "").strip()[:20]
    if event_type not in ("open", "message", "error"):
        return
    with get_connection() as conn:
        _execute(
            conn,
            """INSERT INTO mai_chat_events
               (event_type, ip_hash, visitor_hash, lang, path, had_profile,
                message_length, site_links_count, affiliate_links_count, error_code, question_text, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            """INSERT INTO mai_chat_events
               (event_type, ip_hash, visitor_hash, lang, path, had_profile,
                message_length, site_links_count, affiliate_links_count, error_code, question_text, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event_type,
                (ip_hash or "")[:32],
                (visitor_hash or "")[:32],
                (lang or "fr")[:5],
                (path or "")[:300],
                bool(had_profile),
                max(0, int(message_length or 0)),
                max(0, int(site_links_count or 0)),
                max(0, int(affiliate_links_count or 0)),
                (error_code or "")[:40],
                (question_text or "")[:500],
                _now_iso(),
            ),
        )


def get_unique_visitors_period(days: int = 30) -> int:
    bot = _human_traffic_sql()
    since = _since_days(days)
    with get_connection() as conn:
        row = _execute(
            conn,
            f"""SELECT COUNT(DISTINCT ip_hash) AS c FROM page_views
                WHERE created_at >= %s AND COALESCE(ip_hash, '') <> ''{bot}""",
            f"""SELECT COUNT(DISTINCT ip_hash) AS c FROM page_views
                WHERE created_at >= ? AND COALESCE(ip_hash, '') <> ''{bot}""",
            (since,),
        ).fetchone()
    return row["c"] if isinstance(row, dict) else row[0]


def get_daily_unique_visitors(days: int = 30) -> list[dict]:
    bot = _human_traffic_sql()
    since = _since_days(days)
    with get_connection() as conn:
        rows = _execute(
            conn,
            f"""SELECT created_at::date AS day, COUNT(DISTINCT ip_hash) AS visitors
                FROM page_views
                WHERE created_at >= %s AND COALESCE(ip_hash, '') <> ''{bot}
                GROUP BY day ORDER BY day""",
            f"""SELECT date(created_at) AS day, COUNT(DISTINCT ip_hash) AS visitors
                FROM page_views
                WHERE created_at >= ? AND COALESCE(ip_hash, '') <> ''{bot}
                GROUP BY day ORDER BY day""",
            (since,),
        ).fetchall()
    return [_row_dict(r) for r in rows]


def get_mai_chat_stats(days: int = 30, site_unique_visitors: int = 0) -> dict:
    since = _since_days(days)
    user_key = _user_key_sql()
    out = {
        "total_opens": 0,
        "total_messages": 0,
        "total_errors": 0,
        "unique_users": 0,
        "unique_messagers": 0,
        "unique_openers": 0,
        "messages_with_profile": 0,
        "messages_without_profile": 0,
        "active_30m": 0,
        "usage_rate_pct": 0.0,
        "daily_messages": [],
        "by_lang": [],
        "recent_errors": [],
        "recent_questions": [],
    }
    try:
        with get_connection() as conn:
            for et, key in (("open", "total_opens"), ("message", "total_messages"), ("error", "total_errors")):
                row = _execute(
                    conn,
                    "SELECT COUNT(*) AS c FROM mai_chat_events WHERE event_type = %s AND created_at >= %s",
                    "SELECT COUNT(*) AS c FROM mai_chat_events WHERE event_type = ? AND created_at >= ?",
                    (et, since),
                ).fetchone()
                out[key] = row["c"] if isinstance(row, dict) else row[0]

            row = _execute(
                conn,
                f"""SELECT COUNT(DISTINCT {user_key}) AS c FROM mai_chat_events
                    WHERE created_at >= %s AND {user_key} IS NOT NULL""",
                f"""SELECT COUNT(DISTINCT {user_key}) AS c FROM mai_chat_events
                    WHERE created_at >= ? AND {user_key} IS NOT NULL""",
                (since,),
            ).fetchone()
            out["unique_users"] = row["c"] if isinstance(row, dict) else row[0]

            row = _execute(
                conn,
                f"""SELECT COUNT(DISTINCT {user_key}) AS c FROM mai_chat_events
                    WHERE event_type = 'message' AND created_at >= %s AND {user_key} IS NOT NULL""",
                f"""SELECT COUNT(DISTINCT {user_key}) AS c FROM mai_chat_events
                    WHERE event_type = 'message' AND created_at >= ? AND {user_key} IS NOT NULL""",
                (since,),
            ).fetchone()
            out["unique_messagers"] = row["c"] if isinstance(row, dict) else row[0]

            row = _execute(
                conn,
                f"""SELECT COUNT(DISTINCT {user_key}) AS c FROM mai_chat_events
                    WHERE event_type = 'open' AND created_at >= %s AND {user_key} IS NOT NULL""",
                f"""SELECT COUNT(DISTINCT {user_key}) AS c FROM mai_chat_events
                    WHERE event_type = 'open' AND created_at >= ? AND {user_key} IS NOT NULL""",
                (since,),
            ).fetchone()
            out["unique_openers"] = row["c"] if isinstance(row, dict) else row[0]

            row = _execute(
                conn,
                """SELECT COUNT(*) AS c FROM mai_chat_events
                   WHERE event_type = 'message' AND had_profile = %s AND created_at >= %s""",
                """SELECT COUNT(*) AS c FROM mai_chat_events
                   WHERE event_type = 'message' AND had_profile = ? AND created_at >= ?""",
                (True if is_postgres() else 1, since),
            ).fetchone()
            out["messages_with_profile"] = row["c"] if isinstance(row, dict) else row[0]
            out["messages_without_profile"] = max(
                0, out["total_messages"] - out["messages_with_profile"]
            )

            row = _execute(
                conn,
                f"""SELECT COUNT(DISTINCT {user_key}) AS c FROM mai_chat_events
                    WHERE created_at >= %s AND {user_key} IS NOT NULL""",
                f"""SELECT COUNT(DISTINCT {user_key}) AS c FROM mai_chat_events
                    WHERE created_at >= ? AND {user_key} IS NOT NULL""",
                (_since(30),),
            ).fetchone()
            out["active_30m"] = row["c"] if isinstance(row, dict) else row[0]

            rows = _execute(
                conn,
                """SELECT created_at::date AS day, COUNT(*) AS n FROM mai_chat_events
                   WHERE event_type = 'message' AND created_at >= %s
                   GROUP BY day ORDER BY day""",
                """SELECT date(created_at) AS day, COUNT(*) AS n FROM mai_chat_events
                   WHERE event_type = 'message' AND created_at >= ?
                   GROUP BY day ORDER BY day""",
                (since,),
            ).fetchall()
            out["daily_messages"] = [_row_dict(r) for r in rows]

            rows = _execute(
                conn,
                """SELECT COALESCE(lang, 'fr') AS lang, COUNT(*) AS n FROM mai_chat_events
                   WHERE event_type = 'message' AND created_at >= %s
                   GROUP BY lang ORDER BY n DESC""",
                """SELECT COALESCE(lang, 'fr') AS lang, COUNT(*) AS n FROM mai_chat_events
                   WHERE event_type = 'message' AND created_at >= ?
                   GROUP BY lang ORDER BY n DESC""",
                (since,),
            ).fetchall()
            out["by_lang"] = [_row_dict(r) for r in rows]

            rows = _execute(
                conn,
                """SELECT error_code, COUNT(*) AS n FROM mai_chat_events
                   WHERE event_type = 'error' AND created_at >= %s
                   GROUP BY error_code ORDER BY n DESC LIMIT 5""",
                """SELECT error_code, COUNT(*) AS n FROM mai_chat_events
                   WHERE event_type = 'error' AND created_at >= ?
                   GROUP BY error_code ORDER BY n DESC LIMIT 5""",
                (since,),
            ).fetchall()
            out["recent_errors"] = [_row_dict(r) for r in rows]

            rows = _execute(
                conn,
                """SELECT created_at, lang, path, question_text, message_length
                   FROM mai_chat_events
                   WHERE event_type = 'message' AND COALESCE(question_text, '') <> ''
                     AND created_at >= %s
                   ORDER BY created_at DESC LIMIT 50""",
                """SELECT created_at, lang, path, question_text, message_length
                   FROM mai_chat_events
                   WHERE event_type = 'message' AND COALESCE(question_text, '') <> ''
                     AND created_at >= ?
                   ORDER BY created_at DESC LIMIT 50""",
                (since,),
            ).fetchall()
            out["recent_questions"] = [_row_dict(r) for r in rows]
    except Exception:
        pass

    if site_unique_visitors > 0 and out["unique_users"] > 0:
        out["usage_rate_pct"] = round(
            min(100.0, out["unique_users"] / site_unique_visitors * 100), 1
        )
    return out


# ── NPS / satisfaction contenu ────────────────────────────────────────
def log_nps_response(
    rating: int,
    *,
    path: str = "",
    comment: str = "",
    lang: str = "fr",
    ip_hash: str = "",
    visitor_hash: str = "",
    country_code: str = "",
    country_name: str = "",
):
    """Enregistre une notation 1-5 de pertinence du contenu d'une page."""
    rating = max(1, min(5, int(rating)))
    with get_connection() as conn:
        _execute(
            conn,
            """INSERT INTO nps_responses
               (rating, comment, path, lang, ip_hash, visitor_hash,
                country_code, country_name, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            """INSERT INTO nps_responses
               (rating, comment, path, lang, ip_hash, visitor_hash,
                country_code, country_name, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                rating,
                (comment or "")[:500],
                (path or "")[:300],
                (lang or "fr")[:5],
                (ip_hash or "")[:32],
                (visitor_hash or "")[:32],
                (country_code or "")[:5],
                (country_name or "")[:80],
                _now_iso(),
            ),
        )


def get_nps_stats(days: int = 30) -> dict:
    since = _since_days(days)
    out = {
        "total": 0,
        "average": 0.0,
        "satisfied_pct": 0.0,
        "distribution": [
            {"rating": 5, "count": 0},
            {"rating": 4, "count": 0},
            {"rating": 3, "count": 0},
            {"rating": 2, "count": 0},
            {"rating": 1, "count": 0},
        ],
        "by_page": [],
        "daily": [],
        "recent": [],
    }
    try:
        with get_connection() as conn:
            row = _execute(
                conn,
                "SELECT COUNT(*) AS c, AVG(rating) AS a FROM nps_responses WHERE created_at >= %s",
                "SELECT COUNT(*) AS c, AVG(rating) AS a FROM nps_responses WHERE created_at >= ?",
                (since,),
            ).fetchone()
            row = _row_dict(row)
            out["total"] = int(row.get("c") or 0)
            out["average"] = round(float(row.get("a") or 0), 2)

            if out["total"]:
                row = _execute(
                    conn,
                    "SELECT COUNT(*) AS c FROM nps_responses WHERE created_at >= %s AND rating >= 4",
                    "SELECT COUNT(*) AS c FROM nps_responses WHERE created_at >= ? AND rating >= 4",
                    (since,),
                ).fetchone()
                satisfied = (row["c"] if isinstance(row, dict) else row[0]) or 0
                out["satisfied_pct"] = round(satisfied / out["total"] * 100, 1)

            counts = {}
            rows = _execute(
                conn,
                "SELECT rating, COUNT(*) AS c FROM nps_responses WHERE created_at >= %s GROUP BY rating",
                "SELECT rating, COUNT(*) AS c FROM nps_responses WHERE created_at >= ? GROUP BY rating",
                (since,),
            ).fetchall()
            for r in rows:
                d = _row_dict(r)
                counts[int(d.get("rating") or 0)] = int(d.get("c") or 0)
            for item in out["distribution"]:
                item["count"] = counts.get(item["rating"], 0)

            rows = _execute(
                conn,
                """SELECT path, COUNT(*) AS responses, AVG(rating) AS avg_rating
                   FROM nps_responses WHERE created_at >= %s AND COALESCE(path, '') <> ''
                   GROUP BY path ORDER BY responses DESC, avg_rating ASC LIMIT 50""",
                """SELECT path, COUNT(*) AS responses, AVG(rating) AS avg_rating
                   FROM nps_responses WHERE created_at >= ? AND COALESCE(path, '') <> ''
                   GROUP BY path ORDER BY responses DESC, avg_rating ASC LIMIT 50""",
                (since,),
            ).fetchall()
            out["by_page"] = []
            for r in rows:
                d = _row_dict(r)
                out["by_page"].append({
                    "path": d.get("path") or "—",
                    "responses": int(d.get("responses") or 0),
                    "avg_rating": round(float(d.get("avg_rating") or 0), 2),
                })

            rows = _execute(
                conn,
                """SELECT created_at::date AS day, COUNT(*) AS c, AVG(rating) AS a
                   FROM nps_responses WHERE created_at >= %s
                   GROUP BY day ORDER BY day""",
                """SELECT date(created_at) AS day, COUNT(*) AS c, AVG(rating) AS a
                   FROM nps_responses WHERE created_at >= ?
                   GROUP BY day ORDER BY day""",
                (since,),
            ).fetchall()
            out["daily"] = []
            for r in rows:
                d = _row_dict(r)
                out["daily"].append({
                    "day": d.get("day"),
                    "count": int(d.get("c") or 0),
                    "avg_rating": round(float(d.get("a") or 0), 2),
                })

            rows = _execute(
                conn,
                """SELECT created_at, rating, comment, path, lang, country_name
                   FROM nps_responses WHERE created_at >= %s
                   ORDER BY created_at DESC LIMIT 100""",
                """SELECT created_at, rating, comment, path, lang, country_name
                   FROM nps_responses WHERE created_at >= ?
                   ORDER BY created_at DESC LIMIT 100""",
                (since,),
            ).fetchall()
            out["recent"] = [_row_dict(r) for r in rows]
    except Exception:
        pass
    return out
