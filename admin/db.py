"""SQLite — analytics, revenus, clics affiliés."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "site.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS page_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                referrer TEXT,
                user_agent TEXT,
                ip_hash TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS affiliate_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                target_url TEXT NOT NULL,
                source_page TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS revenue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'EUR',
                note TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_pv_created ON page_views(created_at);
            CREATE INDEX IF NOT EXISTS idx_clicks_created ON affiliate_clicks(created_at);
        """)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def log_page_view(path: str, referrer: str, user_agent: str, ip_hash: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO page_views (path, referrer, user_agent, ip_hash, created_at) VALUES (?,?,?,?,?)",
            (path, referrer, user_agent, ip_hash, datetime.utcnow().isoformat()),
        )


def log_affiliate_click(provider: str, target_url: str, source_page: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO affiliate_clicks (provider, target_url, source_page, created_at) VALUES (?,?,?,?)",
            (provider, target_url, source_page, datetime.utcnow().isoformat()),
        )


def add_revenue(source: str, amount: float, note: str = "", currency: str = "EUR"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO revenue (source, amount, currency, note, created_at) VALUES (?,?,?,?,?)",
            (source, amount, currency, note, datetime.utcnow().isoformat()),
        )


def _since(minutes: int) -> str:
    return (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()


def _since_days(days: int) -> str:
    return (datetime.utcnow() - timedelta(days=days)).isoformat()


def get_realtime_stats():
    with get_db() as conn:
        active = conn.execute(
            "SELECT COUNT(DISTINCT ip_hash) FROM page_views WHERE created_at >= ?",
            (_since(30),),
        ).fetchone()[0]
        views_30m = conn.execute(
            "SELECT COUNT(*) FROM page_views WHERE created_at >= ?", (_since(30),)
        ).fetchone()[0]
        clicks_30m = conn.execute(
            "SELECT COUNT(*) FROM affiliate_clicks WHERE created_at >= ?", (_since(30),)
        ).fetchone()[0]
        recent = conn.execute(
            """SELECT path, created_at FROM page_views
               ORDER BY id DESC LIMIT 15"""
        ).fetchall()
        top_pages = conn.execute(
            """SELECT path, COUNT(*) as c FROM page_views
               WHERE created_at >= ? GROUP BY path ORDER BY c DESC LIMIT 10""",
            (_since(60 * 24),),
        ).fetchall()
    return {
        "active_visitors": active,
        "views_30m": views_30m,
        "clicks_30m": clicks_30m,
        "recent": [dict(r) for r in recent],
        "top_pages": [dict(r) for r in top_pages],
    }


def get_daily_views(days: int = 30):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT date(created_at) as day, COUNT(*) as views
               FROM page_views WHERE created_at >= ?
               GROUP BY day ORDER BY day""",
            (_since_days(days),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_daily_affiliate_clicks(days: int = 30):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT date(created_at) as day, COUNT(*) as clicks
               FROM affiliate_clicks WHERE created_at >= ?
               GROUP BY day ORDER BY day""",
            (_since_days(days),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_revenue_by_source(days: int = 90):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT source, SUM(amount) as total, COUNT(*) as count
               FROM revenue WHERE created_at >= ?
               GROUP BY source ORDER BY total DESC""",
            (_since_days(days),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_affiliate_stats(days: int = 30):
    with get_db() as conn:
        by_provider = conn.execute(
            """SELECT provider, COUNT(*) as clicks FROM affiliate_clicks
               WHERE created_at >= ? GROUP BY provider ORDER BY clicks DESC""",
            (_since_days(days),),
        ).fetchall()
        total_clicks = conn.execute(
            "SELECT COUNT(*) FROM affiliate_clicks WHERE created_at >= ?",
            (_since_days(days),),
        ).fetchone()[0]
    return {"by_provider": [dict(r) for r in by_provider], "total_clicks": total_clicks}


def get_revenue_stats():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM revenue ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        total = conn.execute("SELECT COALESCE(SUM(amount),0) FROM revenue").fetchone()[0]
        month_total = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM revenue WHERE created_at >= ?",
            (_since_days(30),),
        ).fetchone()[0]
    return {
        "entries": [dict(r) for r in rows],
        "total": round(total, 2),
        "month_total": round(month_total, 2),
    }


def get_dashboard_totals():
    with get_db() as conn:
        total_views = conn.execute("SELECT COUNT(*) FROM page_views").fetchone()[0]
        today_views = conn.execute(
            "SELECT COUNT(*) FROM page_views WHERE date(created_at) = date('now')"
        ).fetchone()[0]
        total_clicks = conn.execute("SELECT COUNT(*) FROM affiliate_clicks").fetchone()[0]
    return {"total_views": total_views, "today_views": today_views, "total_clicks": total_clicks}
