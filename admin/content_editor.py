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
