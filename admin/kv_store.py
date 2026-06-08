"""Stockage clé-valeur JSON — Supabase (app_kv) ou fichiers locaux."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from admin.database import get_connection, is_postgres

STORE_DIR = Path(__file__).parent.parent / "data" / "store"
_json_cache: dict[str, tuple[float, Any]] = {}


def _read_json_file(path: Path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return deepcopy(default)


def _write_json_file(path: Path, data):
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _invalidate_cache(*keys: str):
    for key in keys:
        _json_cache.pop(key, None)


def _pg_get(key: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT data FROM app_kv WHERE key = %s", (key,))
        row = cur.fetchone()
        if not row:
            return None
        return row["data"] if isinstance(row, dict) else row[0]


def _pg_set(key: str, data: Any):
    from psycopg2.extras import Json

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO app_kv (key, data, updated_at) VALUES (%s, %s, NOW())
            ON CONFLICT (key) DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
            """,
            (key, Json(data)),
        )
    _invalidate_cache(key)


def get_json(key: str, default, *, file_name: str | None = None) -> Any:
    file_name = file_name or f"{key}.json"
    file_path = STORE_DIR / file_name

    if is_postgres():
        cached = _json_cache.get(key)
        if cached and cached[0] == "pg":
            return deepcopy(cached[1])
        data = _pg_get(key)
        if data is None:
            return None
        _json_cache[key] = ("pg", data)
        return deepcopy(data)

    mtime = file_path.stat().st_mtime if file_path.exists() else -1.0
    cached = _json_cache.get(key)
    if cached and cached[0] == mtime:
        return deepcopy(cached[1])
    data = _read_json_file(file_path, default)
    if file_path.exists():
        _json_cache[key] = (mtime, data)
    return deepcopy(data)


def set_json(key: str, data: Any, *, file_name: str | None = None):
    file_name = file_name or f"{key}.json"
    file_path = STORE_DIR / file_name

    if is_postgres():
        _pg_set(key, data)
        return

    _write_json_file(file_path, data)
    _invalidate_cache(key)
