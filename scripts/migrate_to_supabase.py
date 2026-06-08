#!/usr/bin/env python3
"""Migre les données locales (JSON, SQLite, newsletter) vers Supabase PostgreSQL.

Usage:
  set DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres
  python scripts/migrate_to_supabase.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

if not os.environ.get("DATABASE_URL", "").strip():
    print("Erreur: DATABASE_URL manquant dans .env ou l'environnement.")
    print("Recuperez l'URI dans Supabase > Project Settings > Database > Connection string (URI).")
    sys.exit(1)

from admin.database import init_schema, is_postgres
from admin.kv_store import set_json
from admin.newsletter_service import add_newsletter_subscriber
from data.articles import ARTICLES as DEFAULT_ARTICLES
from data.destinations import DESTINATIONS as DEFAULT_DESTINATIONS

STORE_DIR = ROOT / "data" / "store"
SQLITE_PATH = ROOT / "data" / "site.db"
NEWSLETTER_FILE = ROOT / "data" / "newsletter_subscribers.txt"


def _load_json(path: Path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def migrate_kv():
    mappings = [
        ("articles", "articles.json", DEFAULT_ARTICLES),
        ("destinations", "destinations.json", DEFAULT_DESTINATIONS),
        ("settings", "settings.json", {}),
        ("affiliate_ids", "affiliate_ids.json", {}),
        ("custom_partners", "custom_partners.json", []),
    ]
    for key, filename, default in mappings:
        data = _load_json(STORE_DIR / filename, default)
        set_json(key, data, file_name=filename)
        print(f"  OK app_kv/{key}")


def migrate_sqlite():
    if not SQLITE_PATH.exists():
        print("  - pas de site.db local")
        return
    import psycopg2
    from psycopg2.extras import execute_batch

    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row
    dst = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with dst.cursor() as cur:
            for table, cols in (
                ("page_views", ("path", "referrer", "user_agent", "ip_hash", "country_code", "country_name", "created_at")),
                ("affiliate_clicks", ("provider", "target_url", "source_page", "created_at")),
                ("revenue", ("source", "amount", "currency", "note", "created_at")),
            ):
                rows = src.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
                if not rows:
                    print(f"  - {table}: vide")
                    continue
                placeholders = ", ".join(["%s"] * len(cols))
                col_list = ", ".join(cols)
                execute_batch(
                    cur,
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                    [tuple(r[c] for c in cols) for r in rows],
                )
                print(f"  OK {table}: {len(rows)} lignes")
        dst.commit()
    finally:
        src.close()
        dst.close()


def migrate_newsletter():
    if not NEWSLETTER_FILE.exists():
        print("  - pas de fichier newsletter")
        return
    count = 0
    for line in NEWSLETTER_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        _, email = line.split(",", 1)
        if add_newsletter_subscriber(email.strip()):
            count += 1
    print(f"  OK newsletter: {count} abonne(s) importe(s)")


def main():
    if not is_postgres():
        print("Erreur: DATABASE_URL invalide ou absent.")
        sys.exit(1)

    print("Creation du schema Supabase...")
    init_schema()

    print("Migration contenu (articles, destinations, settings)...")
    migrate_kv()

    print("Migration analytics SQLite vers PostgreSQL...")
    migrate_sqlite()

    print("Migration newsletter...")
    migrate_newsletter()

    print("\nMigration terminee.")


if __name__ == "__main__":
    main()
