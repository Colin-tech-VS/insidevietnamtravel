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
