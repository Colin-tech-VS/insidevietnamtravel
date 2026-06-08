"""Analytics, revenus et clics affiliés — PostgreSQL (Supabase) ou SQLite local."""

from datetime import datetime, timedelta

from admin.database import get_connection, ensure_schema, init_schema, is_postgres

init_db = init_schema


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _since(minutes: int) -> str:
    return (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()


def _since_days(days: int) -> str:
    return (datetime.utcnow() - timedelta(days=days)).isoformat()


def _execute(conn, sql_pg: str, sql_sqlite: str, params=()):
    if is_postgres():
        cur = conn.cursor()
        cur.execute(sql_pg, params)
        return cur
    return conn.execute(sql_sqlite, params)


def log_page_view(path: str, referrer: str, user_agent: str, ip_hash: str):
    with get_connection() as conn:
        _execute(
            conn,
            "INSERT INTO page_views (path, referrer, user_agent, ip_hash, created_at) VALUES (%s,%s,%s,%s,%s)",
            "INSERT INTO page_views (path, referrer, user_agent, ip_hash, created_at) VALUES (?,?,?,?,?)",
            (path, referrer, user_agent, ip_hash, _now_iso()),
        )


def log_affiliate_click(provider: str, target_url: str, source_page: str):
    with get_connection() as conn:
        _execute(
            conn,
            "INSERT INTO affiliate_clicks (provider, target_url, source_page, created_at) VALUES (%s,%s,%s,%s)",
            "INSERT INTO affiliate_clicks (provider, target_url, source_page, created_at) VALUES (?,?,?,?)",
            (provider, target_url, source_page, _now_iso()),
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
    with get_connection() as conn:
        active = _execute(
            conn,
            "SELECT COUNT(DISTINCT ip_hash) AS c FROM page_views WHERE created_at >= %s",
            "SELECT COUNT(DISTINCT ip_hash) FROM page_views WHERE created_at >= ?",
            (_since(30),),
        ).fetchone()
        views_30m = _execute(
            conn,
            "SELECT COUNT(*) AS c FROM page_views WHERE created_at >= %s",
            "SELECT COUNT(*) FROM page_views WHERE created_at >= ?",
            (_since(30),),
        ).fetchone()
        clicks_30m = _execute(
            conn,
            "SELECT COUNT(*) AS c FROM affiliate_clicks WHERE created_at >= %s",
            "SELECT COUNT(*) FROM affiliate_clicks WHERE created_at >= ?",
            (_since(30),),
        ).fetchone()
        recent = _execute(
            conn,
            "SELECT path, created_at FROM page_views ORDER BY id DESC LIMIT 15",
            "SELECT path, created_at FROM page_views ORDER BY id DESC LIMIT 15",
        ).fetchall()
        top_pages = _execute(
            conn,
            """SELECT path, COUNT(*) AS c FROM page_views
               WHERE created_at >= %s GROUP BY path ORDER BY c DESC LIMIT 10""",
            """SELECT path, COUNT(*) as c FROM page_views
               WHERE created_at >= ? GROUP BY path ORDER BY c DESC LIMIT 10""",
            (_since(60 * 24),),
        ).fetchall()
    return {
        "active_visitors": active["c"] if isinstance(active, dict) else active[0],
        "views_30m": views_30m["c"] if isinstance(views_30m, dict) else views_30m[0],
        "clicks_30m": clicks_30m["c"] if isinstance(clicks_30m, dict) else clicks_30m[0],
        "recent": [dict(r) for r in recent],
        "top_pages": [dict(r) for r in top_pages],
    }


def get_daily_views(days: int = 30):
    with get_connection() as conn:
        rows = _execute(
            conn,
            """SELECT created_at::date AS day, COUNT(*) AS views
               FROM page_views WHERE created_at >= %s GROUP BY day ORDER BY day""",
            """SELECT date(created_at) as day, COUNT(*) as views
               FROM page_views WHERE created_at >= ? GROUP BY day ORDER BY day""",
            (_since_days(days),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_geo_view_rows(days: int = 30) -> list[dict]:
    """Page views avec referrer + UA pour classification GEO (LLM / moteurs IA)."""
    with get_connection() as conn:
        rows = _execute(
            conn,
            """SELECT path, referrer, user_agent, created_at::text AS created_at
               FROM page_views WHERE created_at >= %s ORDER BY id DESC""",
            """SELECT path, referrer, user_agent, created_at
               FROM page_views WHERE created_at >= ? ORDER BY id DESC""",
            (_since_days(days),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_daily_affiliate_clicks(days: int = 30):
    with get_connection() as conn:
        rows = _execute(
            conn,
            """SELECT created_at::date AS day, COUNT(*) AS clicks
               FROM affiliate_clicks WHERE created_at >= %s GROUP BY day ORDER BY day""",
            """SELECT date(created_at) as day, COUNT(*) as clicks
               FROM affiliate_clicks WHERE created_at >= ? GROUP BY day ORDER BY day""",
            (_since_days(days),),
        ).fetchall()
    return [dict(r) for r in rows]


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
    return [dict(r) for r in rows]


def get_affiliate_stats(days: int = 30):
    with get_connection() as conn:
        by_provider = _execute(
            conn,
            """SELECT provider, COUNT(*) AS clicks FROM affiliate_clicks
               WHERE created_at >= %s GROUP BY provider ORDER BY clicks DESC""",
            """SELECT provider, COUNT(*) as clicks FROM affiliate_clicks
               WHERE created_at >= ? GROUP BY provider ORDER BY clicks DESC""",
            (_since_days(days),),
        ).fetchall()
        total_clicks = _execute(
            conn,
            "SELECT COUNT(*) AS c FROM affiliate_clicks WHERE created_at >= %s",
            "SELECT COUNT(*) FROM affiliate_clicks WHERE created_at >= ?",
            (_since_days(days),),
        ).fetchone()
    tc = total_clicks["c"] if isinstance(total_clicks, dict) else total_clicks[0]
    return {"by_provider": [dict(r) for r in by_provider], "total_clicks": tc}


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
        "entries": [dict(r) for r in rows],
        "total": round(float(t), 2),
        "month_total": round(float(m), 2),
    }


def get_dashboard_totals():
    with get_connection() as conn:
        total_views = _execute(
            conn,
            "SELECT COUNT(*) AS c FROM page_views",
            "SELECT COUNT(*) FROM page_views",
        ).fetchone()
        today_views = _execute(
            conn,
            "SELECT COUNT(*) AS c FROM page_views WHERE created_at::date = CURRENT_DATE",
            "SELECT COUNT(*) FROM page_views WHERE date(created_at) = date('now')",
        ).fetchone()
        total_clicks = _execute(
            conn,
            "SELECT COUNT(*) AS c FROM affiliate_clicks",
            "SELECT COUNT(*) FROM affiliate_clicks",
        ).fetchone()
    def _v(row):
        return row["c"] if isinstance(row, dict) else row[0]
    return {
        "total_views": _v(total_views),
        "today_views": _v(today_views),
        "total_clicks": _v(total_clicks),
    }
