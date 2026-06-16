"""Audit analytics: raw vs filtered, bots, excluded IP."""
import hashlib
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from admin.analytics_filters import is_analytics_bot, _all_bot_patterns
from admin.database import get_connection, is_postgres
from admin.db import _human_traffic_sql

excluded_ip = os.environ.get("ANALYTICS_EXCLUDED_IPS", "").split(",")[0].strip()
excluded_hash = hashlib.sha256((excluded_ip or "unknown").encode()).hexdigest()[:16]

print("=== CONFIG ===")
print(f"Excluded IP: {excluded_ip or '(none)'}")
print(f"Excluded ip_hash: {excluded_hash}")
print(f"Postgres: {is_postgres()}")
print(f"Bot patterns count: {len(_all_bot_patterns())}")

today = datetime.utcnow().date().isoformat()
since_30m = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
bot_sql = _human_traffic_sql()

with get_connection() as conn:
    cur = conn.cursor() if is_postgres() else conn

    def q(sql_pg, sql_sqlite, params=()):
        if is_postgres():
            cur.execute(sql_pg, params)
            rows = cur.fetchall()
            if not rows:
                return []
            if isinstance(rows[0], dict):
                return list(rows)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        rows = cur.execute(sql_sqlite, params).fetchall()
        return [dict(r) for r in rows]

    def count(sql_pg, sql_sqlite, params=()):
        row = q(sql_pg, sql_sqlite, params)[0]
        return int(row.get("c") or row.get("count") or list(row.values())[0])

    raw_today = count(
        "SELECT COUNT(*) AS c FROM page_views WHERE created_at::date = %s::date",
        "SELECT COUNT(*) as c FROM page_views WHERE date(created_at) = date(?)",
        (today,),
    )

    human_today = count(
        f"SELECT COUNT(*) AS c FROM page_views WHERE created_at::date = %s::date{bot_sql}",
        f"SELECT COUNT(*) as c FROM page_views WHERE date(created_at) = date(?){bot_sql}",
        (today,),
    )

    active = count(
        f"SELECT COUNT(DISTINCT ip_hash) AS c FROM page_views WHERE created_at >= %s AND COALESCE(ip_hash, '') <> ''{bot_sql}",
        f"SELECT COUNT(DISTINCT ip_hash) as c FROM page_views WHERE created_at >= ? AND COALESCE(ip_hash, '') <> ''{bot_sql}",
        (since_30m,),
    )

    excl_today = count(
        "SELECT COUNT(*) AS c FROM page_views WHERE created_at::date = %s::date AND ip_hash = %s",
        "SELECT COUNT(*) as c FROM page_views WHERE date(created_at) = date(?) AND ip_hash = ?",
        (today, excluded_hash),
    )

    excl_all = count(
        "SELECT COUNT(*) AS c FROM page_views WHERE ip_hash = %s",
        "SELECT COUNT(*) as c FROM page_views WHERE ip_hash = ?",
        (excluded_hash,),
    )

    print()
    print("=== TODAY ===")
    print(f"Raw views today: {raw_today}")
    print(f"Human-filtered views today: {human_today}")
    print(f"Bots filtered out today: {raw_today - human_today}")
    print(f"Active visitors (30m, human): {active}")
    print(f"Views from excluded IP hash today: {excl_today}")
    print(f"Views from excluded IP hash (all time): {excl_all}")

    print()
    print("=== TOP USER AGENTS TODAY (raw) ===")
    for row in q(
        """SELECT user_agent, COUNT(*) AS c FROM page_views
           WHERE created_at::date = %s::date GROUP BY user_agent ORDER BY c DESC LIMIT 15""",
        """SELECT user_agent, COUNT(*) as c FROM page_views
           WHERE date(created_at) = date(?) GROUP BY user_agent ORDER BY c DESC LIMIT 15""",
        (today,),
    ):
        ua = (row["user_agent"] or "")[:80]
        bot = is_analytics_bot(row["user_agent"] or "")
        label = "BOT" if bot else "HUMAN"
        print(f"  [{label:5}] {row['c']:4} | {ua}")

    print()
    print("=== TOP PATHS TODAY (human-filtered) ===")
    for row in q(
        f"""SELECT path, COUNT(*) AS c FROM page_views
            WHERE created_at::date = %s::date{bot_sql} GROUP BY path ORDER BY c DESC LIMIT 15""",
        f"""SELECT path, COUNT(*) as c FROM page_views
            WHERE date(created_at) = date(?){bot_sql} GROUP BY path ORDER BY c DESC LIMIT 15""",
        (today,),
    ):
        print(f"  {row['c']:4} | {row['path']}")

    print()
    print("=== COUNTRIES TODAY (human-filtered) ===")
    for row in q(
        f"""SELECT country_code, country_name, COUNT(*) AS c FROM page_views
            WHERE created_at::date = %s::date{bot_sql}
            GROUP BY country_code, country_name ORDER BY c DESC LIMIT 10""",
        f"""SELECT country_code, country_name, COUNT(*) as c FROM page_views
            WHERE date(created_at) = date(?){bot_sql}
            GROUP BY country_code, country_name ORDER BY c DESC LIMIT 10""",
        (today,),
    ):
        cc = row.get("country_code", "??")
        cn = row.get("country_name", "")
        print(f"  {row['c']:4} | {cc} {cn}")

    print()
    print("=== DISTINCT VISITORS TODAY (human, by ip_hash) ===")
    for row in q(
        f"""SELECT ip_hash, COUNT(*) AS c, MAX(country_code) AS cc FROM page_views
            WHERE created_at::date = %s::date{bot_sql} GROUP BY ip_hash ORDER BY c DESC LIMIT 20""",
        f"""SELECT ip_hash, COUNT(*) as c, MAX(country_code) as cc FROM page_views
            WHERE date(created_at) = date(?){bot_sql} GROUP BY ip_hash ORDER BY c DESC LIMIT 20""",
        (today,),
    ):
        mark = " <-- YOUR IP" if row["ip_hash"] == excluded_hash else ""
        print(f"  {row['c']:4} views | hash={row['ip_hash']} | {row.get('cc', '??')}{mark}")

    print()
    print("=== LAST 20 PAGE VIEWS (raw) ===")
    for row in q(
        """SELECT path, user_agent, country_code, ip_hash, created_at::text AS ts
           FROM page_views ORDER BY id DESC LIMIT 20""",
        """SELECT path, user_agent, country_code, ip_hash, created_at AS ts
           FROM page_views ORDER BY id DESC LIMIT 20""",
    ):
        ua = (row["user_agent"] or "")[:50]
        bot = is_analytics_bot(row["user_agent"] or "")
        kind = "BOT" if bot else "HUM"
        excl = " EXCL-IP" if row["ip_hash"] == excluded_hash else ""
        ts = (row["ts"] or "")[:19]
        cc = row.get("country_code", "??")
        path = (row["path"] or "")[:40]
        print(f"  {ts} | {kind}{excl} | {cc} | {path} | {ua}")

    localhost_hash = hashlib.sha256(b"127.0.0.1").hexdigest()[:16]
    localhost_today = count(
        f"SELECT COUNT(*) AS c FROM page_views WHERE created_at::date = %s::date AND ip_hash = %s{bot_sql}",
        f"SELECT COUNT(*) as c FROM page_views WHERE date(created_at) = date(?) AND ip_hash = ?{bot_sql}",
        (today, localhost_hash),
    )
    print()
    print("=== LOCALHOST / SCANNERS (human-filtered but not real) ===")
    print(f"127.0.0.1 (health checks / serveur): {localhost_today} views today")
    for label, pattern in [
        ("Lwspanel (scanner hebergeur)", "lwspanel"),
        ("ProspectScope (crawler SEO)", "prospectscope"),
        ("Werkzeug (requetes Python internes)", "werkzeug"),
        ("Google-Site-Verification", "google-site-verification"),
        ("axios (client HTTP programme)", "axios/"),
    ]:
        n = count(
            f"SELECT COUNT(*) AS c FROM page_views WHERE created_at::date = %s::date AND LOWER(user_agent) LIKE %s{bot_sql}",
            f"SELECT COUNT(*) as c FROM page_views WHERE date(created_at) = date(?) AND LOWER(user_agent) LIKE ?{bot_sql}",
            (today, f"%{pattern}%"),
        )
        print(f"{label}: {n}")

    est_real = human_today - localhost_today
    for _, pattern in [
        ("", "lwspanel"),
        ("", "prospectscope"),
        ("", "werkzeug"),
        ("", "google-site-verification"),
        ("", "axios/"),
    ]:
        est_real -= count(
            f"SELECT COUNT(*) AS c FROM page_views WHERE created_at::date = %s::date AND LOWER(user_agent) LIKE %s{bot_sql}",
            f"SELECT COUNT(*) as c FROM page_views WHERE date(created_at) = date(?) AND LOWER(user_agent) LIKE ?{bot_sql}",
            (today, f"%{pattern}%"),
        )
    print(f"Estimation trafic reel (apres exclusions): ~{max(est_real, 0)} vues")

    print()
    print("=== DAILY VIEWS LAST 7 DAYS (human-filtered) ===")
    since_7d = (datetime.utcnow() - timedelta(days=7)).isoformat()
    for row in q(
        f"""SELECT created_at::date AS day, COUNT(*) AS views FROM page_views
            WHERE created_at >= %s{bot_sql} GROUP BY day ORDER BY day""",
        f"""SELECT date(created_at) as day, COUNT(*) as views FROM page_views
            WHERE created_at >= ?{bot_sql} GROUP BY day ORDER BY day""",
        (since_7d,),
    ):
        print(f"  {row['day']}: {row['views']} views")
