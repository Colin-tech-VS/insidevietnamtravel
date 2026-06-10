"""Injecte les guides expérience manquants dans app_kv (à lancer manuellement en prod).

Usage Scalingo :
  scalingo -a <app> run python scripts/sync_experience_articles.py
"""

from admin.store import ensure_builtin_articles


def main() -> None:
    added = ensure_builtin_articles()
    print(f"Synchronisation terminée : {added} article(s) ajouté(s).")


if __name__ == "__main__":
    main()
