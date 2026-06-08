#!/usr/bin/env python3
"""Migre articles et destinations vers i18n FR+EN (traduction Groq)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from admin.groq_translate import translate_article_block, translate_destination_block
from admin.store import get_destinations_dict, get_articles, save_articles, save_destinations
from i18n_utils import wrap_article_i18n, wrap_destination_i18n


def _translate_with_retry(fn, data, retries: int = 5):
    for attempt in range(retries):
        try:
            return fn(data)
        except Exception as exc:
            if "rate_limit" in str(exc).lower() or "429" in str(exc):
                wait = 40 * (attempt + 1)
                print(f"    Rate limit — pause {wait}s...")
                time.sleep(wait)
                continue
            raise
    return {}


def migrate_articles() -> int:
    articles = get_articles()
    updated = 0
    for i, article in enumerate(articles):
        article = wrap_article_i18n(article)
        if article.get("i18n", {}).get("en", {}).get("content"):
            articles[i] = article
            continue
        fr = article["i18n"]["fr"]
        print(f"  Article: {article['slug']}")
        en = _translate_with_retry(translate_article_block, {**article, **fr})
        article["i18n"]["en"] = {
            k: en.get(k, fr.get(k, ""))
            for k in fr
        }
        articles[i] = article
        updated += 1
        save_articles(articles)
        time.sleep(5)
    return updated


def migrate_destinations() -> int:
    destinations = get_destinations_dict()
    updated = 0
    for slug, dest in list(destinations.items()):
        dest = wrap_destination_i18n(dest)
        if dest.get("i18n", {}).get("en", {}).get("overview"):
            destinations[slug] = dest
            continue
        fr = dest["i18n"]["fr"]
        print(f"  Destination: {slug}")
        en = _translate_with_retry(translate_destination_block, {**dest, **fr})
        dest["i18n"]["en"] = {
            k: en.get(k, fr.get(k, ""))
            for k in fr
        }
        destinations[slug] = dest
        updated += 1
        save_destinations(destinations)
        time.sleep(5)
    return updated


def main():
    print("Migration i18n FR -> EN")
    n_articles = migrate_articles()
    print(f"Articles traduits: {n_articles}")
    n_dest = migrate_destinations()
    print(f"Destinations traduites: {n_dest}")
    print("Termine.")


if __name__ == "__main__":
    main()
