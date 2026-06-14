"""Connexion PostgreSQL (Supabase) — fallback SQLite local sans DATABASE_URL."""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

SQLITE_PATH = Path(__file__).parent.parent / "data" / "site.db"

_schema_lock = threading.Lock()
_schema_initialized = False

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS page_views (
    id SERIAL PRIMARY KEY,
    path TEXT NOT NULL,
    referrer TEXT,
    user_agent TEXT,
    ip_hash TEXT,
    country_code TEXT,
    country_name TEXT,
    city TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS affiliate_clicks (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    target_url TEXT NOT NULL,
    source_page TEXT,
    user_agent TEXT,
    ip_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS revenue (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency TEXT DEFAULT 'EUR',
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS app_kv (
    key TEXT PRIMARY KEY,
    data JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    subscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pv_created ON page_views(created_at);
CREATE INDEX IF NOT EXISTS idx_clicks_created ON affiliate_clicks(created_at);
CREATE INDEX IF NOT EXISTS idx_newsletter_email ON newsletter_subscribers(email);
CREATE TABLE IF NOT EXISTS visitor_profile_snapshots (
    id SERIAL PRIMARY KEY,
    visitor_hash TEXT NOT NULL,
    trip_group TEXT,
    trip_style TEXT,
    trip_duration TEXT,
    cities TEXT,
    interests TEXT,
    path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_vps_created ON visitor_profile_snapshots(created_at);
CREATE INDEX IF NOT EXISTS idx_vps_hash ON visitor_profile_snapshots(visitor_hash);
CREATE TABLE IF NOT EXISTS mai_chat_events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    ip_hash TEXT,
    visitor_hash TEXT,
    lang TEXT,
    path TEXT,
    had_profile BOOLEAN NOT NULL DEFAULT FALSE,
    message_length INTEGER DEFAULT 0,
    site_links_count INTEGER DEFAULT 0,
    affiliate_links_count INTEGER DEFAULT 0,
    error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mai_created ON mai_chat_events(created_at);
CREATE INDEX IF NOT EXISTS idx_mai_event ON mai_chat_events(event_type);
CREATE INDEX IF NOT EXISTS idx_mai_visitor ON mai_chat_events(visitor_hash);
"""


def normalize_database_url(url: str) -> str:
    """Convertit l'URL directe Supabase (IPv6) vers le pooler (IPv4, Scalingo-compatible)."""
    url = (url or "").strip()
    if not url:
        return url

    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not host.startswith("db.") or not host.endswith(".supabase.co"):
        return _ensure_sslmode(url)

    project_ref = host.removeprefix("db.").removesuffix(".supabase.co")
    pooler_host = os.environ.get("SUPABASE_POOLER_HOST", "").strip()
    if not pooler_host:
        region = os.environ.get("SUPABASE_POOLER_REGION", "eu-central-1").strip()
        aws_prefix = os.environ.get("SUPABASE_POOLER_AWS", "aws-1").strip()
        pooler_host = f"{aws_prefix}-{region}.pooler.supabase.com"
    pooler_port = os.environ.get("SUPABASE_POOLER_PORT", "6543").strip()

    username = parsed.username or "postgres"
    password = parsed.password or ""
    if username == "postgres":
        username = f"postgres.{project_ref}"

    auth = f"{username}:{password}" if password else username
    db_path = parsed.path or "/postgres"
    new_netloc = f"{auth}@{pooler_host}:{pooler_port}"
    normalized = urlunparse((
        parsed.scheme or "postgresql",
        new_netloc,
        db_path,
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))
    logger.info(
        "DATABASE_URL normalisée : pooler Supabase %s:%s (évite IPv6 db.*.supabase.co)",
        pooler_host,
        pooler_port,
    )
    return _ensure_sslmode(normalized)


def _ensure_sslmode(url: str) -> str:
    if not url or "sslmode=" in url:
        return url
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunparse(parsed._replace(query=urlencode(query)))


DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL", ""))


def is_postgres() -> bool:
    return bool(DATABASE_URL)


def init_schema():
    if is_postgres():
        _init_postgres()
    else:
        _init_sqlite()


def ensure_schema():
    """Initialisation paresseuse — ne bloque pas l'import du module."""
    global _schema_initialized
    if _schema_initialized or not is_postgres():
        if not _schema_initialized and not is_postgres():
            _init_sqlite()
            _schema_initialized = True
        return
    with _schema_lock:
        if _schema_initialized:
            return
        _init_postgres()
        _schema_initialized = True


def _migrate_page_views_columns(conn, *, postgres: bool) -> None:
    if postgres:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE page_views ADD COLUMN IF NOT EXISTS country_code TEXT")
            cur.execute("ALTER TABLE page_views ADD COLUMN IF NOT EXISTS country_name TEXT")
            cur.execute("ALTER TABLE page_views ADD COLUMN IF NOT EXISTS utm_source TEXT")
            cur.execute("ALTER TABLE page_views ADD COLUMN IF NOT EXISTS utm_campaign TEXT")
            cur.execute("ALTER TABLE page_views ADD COLUMN IF NOT EXISTS city TEXT")
    else:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(page_views)")}
        if "country_code" not in cols:
            conn.execute("ALTER TABLE page_views ADD COLUMN country_code TEXT")
        if "country_name" not in cols:
            conn.execute("ALTER TABLE page_views ADD COLUMN country_name TEXT")
        if "utm_source" not in cols:
            conn.execute("ALTER TABLE page_views ADD COLUMN utm_source TEXT")
        if "utm_campaign" not in cols:
            conn.execute("ALTER TABLE page_views ADD COLUMN utm_campaign TEXT")
        if "city" not in cols:
            conn.execute("ALTER TABLE page_views ADD COLUMN city TEXT")


def _migrate_affiliate_clicks_columns(conn, *, postgres: bool) -> None:
    if postgres:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE affiliate_clicks ADD COLUMN IF NOT EXISTS user_agent TEXT")
            cur.execute("ALTER TABLE affiliate_clicks ADD COLUMN IF NOT EXISTS ip_hash TEXT")
    else:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(affiliate_clicks)")}
        if "user_agent" not in cols:
            conn.execute("ALTER TABLE affiliate_clicks ADD COLUMN user_agent TEXT")
        if "ip_hash" not in cols:
            conn.execute("ALTER TABLE affiliate_clicks ADD COLUMN ip_hash TEXT")


def _migrate_visitor_profile_table(conn, *, postgres: bool) -> None:
    if postgres:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS visitor_profile_snapshots (
                    id SERIAL PRIMARY KEY,
                    visitor_hash TEXT NOT NULL,
                    trip_group TEXT,
                    trip_style TEXT,
                    trip_duration TEXT,
                    cities TEXT,
                    interests TEXT,
                    path TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )""")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_vps_created ON visitor_profile_snapshots(created_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_vps_hash ON visitor_profile_snapshots(visitor_hash)"
            )
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS visitor_profile_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_hash TEXT NOT NULL,
                trip_group TEXT,
                trip_style TEXT,
                trip_duration TEXT,
                cities TEXT,
                interests TEXT,
                path TEXT,
                created_at TEXT NOT NULL
            )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vps_created ON visitor_profile_snapshots(created_at)"
        )


def _migrate_mai_chat_table(conn, *, postgres: bool) -> None:
    if postgres:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mai_chat_events (
                    id SERIAL PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    ip_hash TEXT,
                    visitor_hash TEXT,
                    lang TEXT,
                    path TEXT,
                    had_profile BOOLEAN NOT NULL DEFAULT FALSE,
                    message_length INTEGER DEFAULT 0,
                    site_links_count INTEGER DEFAULT 0,
                    affiliate_links_count INTEGER DEFAULT 0,
                    error_code TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )""")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_mai_created ON mai_chat_events(created_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_mai_event ON mai_chat_events(event_type)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_mai_visitor ON mai_chat_events(visitor_hash)"
            )
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mai_chat_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                ip_hash TEXT,
                visitor_hash TEXT,
                lang TEXT,
                path TEXT,
                had_profile INTEGER NOT NULL DEFAULT 0,
                message_length INTEGER DEFAULT 0,
                site_links_count INTEGER DEFAULT 0,
                affiliate_links_count INTEGER DEFAULT 0,
                error_code TEXT,
                created_at TEXT NOT NULL
            )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mai_created ON mai_chat_events(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mai_event ON mai_chat_events(event_type)"
        )


def _init_postgres():
    import psycopg2

    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            for stmt in SCHEMA_SQL.split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        _migrate_page_views_columns(conn, postgres=True)
        _migrate_affiliate_clicks_columns(conn, postgres=True)
        _migrate_visitor_profile_table(conn, postgres=True)
        _migrate_mai_chat_table(conn, postgres=True)
        _migrate_email_tracking_table(conn, postgres=True)
        _migrate_partner_portal_tables(conn, postgres=True)
        conn.commit()
    finally:
        conn.close()


def _init_sqlite():
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS page_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                referrer TEXT,
                user_agent TEXT,
                ip_hash TEXT,
                country_code TEXT,
                country_name TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS affiliate_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                target_url TEXT NOT NULL,
                source_page TEXT,
                user_agent TEXT,
                ip_hash TEXT,
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
        _migrate_page_views_columns(conn, postgres=False)
        _migrate_affiliate_clicks_columns(conn, postgres=False)
        _migrate_visitor_profile_table(conn, postgres=False)
        _migrate_mai_chat_table(conn, postgres=False)
        _migrate_email_tracking_table(conn, postgres=False)
        _migrate_partner_portal_tables(conn, postgres=False)


def _migrate_email_tracking_table(conn, *, postgres: bool) -> None:
    if postgres:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS email_sends (
                    id SERIAL PRIMARY KEY,
                    send_token TEXT NOT NULL UNIQUE,
                    recipient_email TEXT NOT NULL,
                    recipient_name TEXT,
                    partner_id TEXT,
                    subject TEXT,
                    email_type TEXT NOT NULL DEFAULT 'newsletter',
                    tracking_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    open_count INTEGER NOT NULL DEFAULT 0,
                    first_opened_at TIMESTAMPTZ,
                    last_opened_at TIMESTAMPTZ,
                    click_count INTEGER NOT NULL DEFAULT 0,
                    first_clicked_at TIMESTAMPTZ,
                    last_clicked_at TIMESTAMPTZ
                )""")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS email_click_events (
                    id SERIAL PRIMARY KEY,
                    send_id INTEGER NOT NULL REFERENCES email_sends(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )""")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_sends_partner ON email_sends(partner_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_sends_recipient ON email_sends(recipient_email)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_clicks_send ON email_click_events(send_id)"
            )
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_sends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                send_token TEXT NOT NULL UNIQUE,
                recipient_email TEXT NOT NULL,
                recipient_name TEXT,
                partner_id TEXT,
                subject TEXT,
                email_type TEXT NOT NULL DEFAULT 'newsletter',
                tracking_enabled INTEGER NOT NULL DEFAULT 1,
                sent_at TEXT NOT NULL,
                open_count INTEGER NOT NULL DEFAULT 0,
                first_opened_at TEXT,
                last_opened_at TEXT,
                click_count INTEGER NOT NULL DEFAULT 0,
                first_clicked_at TEXT,
                last_clicked_at TEXT
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_click_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                send_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                clicked_at TEXT NOT NULL,
                FOREIGN KEY (send_id) REFERENCES email_sends(id) ON DELETE CASCADE
            )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_email_sends_partner ON email_sends(partner_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_email_sends_recipient ON email_sends(recipient_email)"
        )


def _migrate_partner_portal_tables(conn, *, postgres: bool) -> None:
    if postgres:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS partner_accounts (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    profile_type TEXT NOT NULL,
                    business_name TEXT,
                    phone TEXT,
                    city TEXT,
                    website TEXT,
                    languages TEXT,
                    bio TEXT,
                    services TEXT,
                    social_links TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )""")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS partner_pages (
                    id TEXT PRIMARY KEY,
                    partner_id TEXT NOT NULL UNIQUE,
                    slug TEXT UNIQUE,
                    status TEXT NOT NULL DEFAULT 'draft',
                    title TEXT,
                    tagline TEXT,
                    overview_html TEXT,
                    services_html TEXT,
                    seo_title TEXT,
                    seo_description TEXT,
                    image_url TEXT,
                    extra_json TEXT,
                    ai_review_json TEXT,
                    admin_notes TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    published_at TIMESTAMPTZ
                )""")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_partner_pages_slug ON partner_pages(slug)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_partner_pages_status ON partner_pages(status)"
            )
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS partner_accounts (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                profile_type TEXT NOT NULL,
                business_name TEXT,
                phone TEXT,
                city TEXT,
                website TEXT,
                languages TEXT,
                bio TEXT,
                services TEXT,
                social_links TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS partner_pages (
                id TEXT PRIMARY KEY,
                partner_id TEXT NOT NULL UNIQUE,
                slug TEXT UNIQUE,
                status TEXT NOT NULL DEFAULT 'draft',
                title TEXT,
                tagline TEXT,
                overview_html TEXT,
                services_html TEXT,
                seo_title TEXT,
                seo_description TEXT,
                image_url TEXT,
                extra_json TEXT,
                ai_review_json TEXT,
                admin_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_partner_pages_slug ON partner_pages(slug)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_partner_pages_status ON partner_pages(status)"
        )


@contextmanager
def get_connection():
    ensure_schema()
    if is_postgres():
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor,
            connect_timeout=10,
        )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
