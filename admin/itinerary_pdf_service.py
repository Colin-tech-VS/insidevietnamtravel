"""PDF téléchargeable par itinéraire (après inscription newsletter)."""

from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer

from admin.pdf_guide_service import (
    MARGIN_B,
    MARGIN_L,
    MARGIN_R,
    MARGIN_T,
    _draw_cover,
    _ensure_pdf_fonts,
    _itinerary_section,
    _page_frame,
    _styles,
)
from data.itineraries import ITINERARIES
from i18n_utils import localize_itinerary


def generate_itinerary_pdf_bytes(slug: str, lang: str = "fr") -> bytes:
    """Génère un PDF jour par jour pour un itinéraire publié."""
    if slug not in ITINERARIES:
        raise ValueError(f"Itinéraire inconnu : {slug}")

    _ensure_pdf_fonts()
    lang = "en" if lang == "en" else "fr"
    itin = localize_itinerary(ITINERARIES[slug], lang)
    styles = _styles()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B,
        title=itin.get("title", "Vietnam itinerary"),
        author="Inside Vietnam Travel",
    )
    doc._lang = lang  # type: ignore[attr-defined]

    story: list = []
    story.append(PageBreak())
    story.extend(_itinerary_section(itin, lang, styles))
    story.append(Spacer(1, 12))

    doc.build(
        story,
        onFirstPage=lambda c, d: _draw_cover(c, lang),
        onLaterPages=_page_frame,
    )
    return buffer.getvalue()


def itinerary_pdf_filename(slug: str, lang: str = "fr") -> str:
    lang = "en" if lang == "en" else "fr"
    if lang == "en":
        return f"inside-vietnam-itinerary-{slug}-en.pdf"
    return f"inside-vietnam-itineraire-{slug}.pdf"
