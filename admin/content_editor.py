"""Jobs admin : amélioration IA et image de couverture sur contenus publiés."""

from __future__ import annotations

from admin.assistant_service import (
    _exec_improve_article,
    _exec_improve_destination,
    _exec_update_image,
)


def improve_published_article(slug: str, instructions: str, report=None) -> dict:
    return _exec_improve_article(
        {"slug": slug, "instructions": instructions},
        report,
    )


def improve_published_destination(slug: str, instructions: str, report=None) -> dict:
    return _exec_improve_destination(
        {"slug": slug, "instructions": instructions},
        report,
    )


def update_published_image(
    target: str,
    slug: str,
    *,
    image_url: str = "",
    query: str = "",
    alt: str = "",
    report=None,
) -> dict:
    return _exec_update_image(
        {
            "target": target,
            "slug": slug,
            "image_url": image_url,
            "query": query,
            "alt": alt,
        },
        report,
    )


def update_published_image_upload(
    target: str,
    slug: str,
    raw: bytes,
    *,
    alt: str = "",
    report=None,
) -> dict:
    from admin.assistant_service import _resolve_destination_slug
    from admin.image_service import (
        set_uploaded_image_for_article,
        set_uploaded_image_for_destination,
    )
    from admin.store import (
        get_article_by_slug,
        update_article_image,
        update_destination_image,
    )

    if report:
        report("Optimisation de l'image importée…")
    if target == "destination":
        resolved_slug, dest = _resolve_destination_slug(slug)
        meta = set_uploaded_image_for_destination(dest, raw, alt or None)
        update_destination_image(resolved_slug, meta)
        return {
            "message": f"✅ Photo importée pour la destination « {dest.get('name', resolved_slug)} ».",
            "url": f"/{resolved_slug}",
        }
    article = get_article_by_slug(slug)
    if not article:
        raise ValueError(f"Article introuvable : « {slug} ».")
    meta = set_uploaded_image_for_article(article, raw, alt or None)
    update_article_image(slug, meta)
    return {
        "message": f"✅ Photo importée pour l'article « {article.get('title', slug)} ».",
        "url": f"/blog/{slug}",
    }
