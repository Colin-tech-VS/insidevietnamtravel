"""Génération du guide PDF Vietnam — design Inside Vietnam Travel."""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from data.destinations import DESTINATIONS
from data.itineraries import ITINERARIES
from i18n_utils import localize_destination, localize_itinerary

TEAL = colors.HexColor("#1B4D4A")
TEAL_DEEP = colors.HexColor("#0F3330")
GOLD = colors.HexColor("#C4A053")
RICE = colors.HexColor("#FAF7F2")
INK = colors.HexColor("#1A1A18")
INK_SOFT = colors.HexColor("#4A4845")

ITINERARY_SLUGS = ("7-days-vietnam", "10-days-vietnam")

ITINERARY_14_DAYS = {
    "fr": {
        "title": "Itinéraire 14 jours — Vietnam complet",
        "summary": "Nord (Hanoï, Sapa), centre (Huế, Hội An) et sud (HCMC, Mékong) sans précipitation.",
        "budget_hint": "950–1 600 € (hors vol international)",
        "days": [
            {"day": 1, "title": "Hanoï — Arrivée", "location": "Hanoï", "activities": ["Installation Vieux Quartier", "Phở du soir", "Balade lac Hoàn Kiếm"], "stay": "Hanoï"},
            {"day": 2, "title": "Hanoï — Culture", "location": "Hanoï", "activities": ["Temple Littérature", "Musée Ethnographie", "Street food"], "stay": "Hanoï"},
            {"day": 3, "title": "Baie d'Halong 2J/1N", "location": "Halong", "activities": ["Transfert", "Croisière", "Kayak"], "stay": "Bateau"},
            {"day": 4, "title": "Halong → Sapa", "location": "Sapa", "activities": ["Retour Hanoï", "Bus/train nuit ou vol + route vers Sapa"], "stay": "Sapa"},
            {"day": 5, "title": "Sapa — Rizières", "location": "Sapa", "activities": ["Trek Cat Cat ou Ta Van", "Marché local", "Vue Fansipan (téléphérique)"], "stay": "Sapa"},
            {"day": 6, "title": "Sapa → Huế", "location": "Huế", "activities": ["Descente vers Huế", "Cité impériale au coucher du soleil"], "stay": "Huế"},
            {"day": 7, "title": "Huế — Impérial", "location": "Huế", "activities": ["Citadelle", "Tombeaux impériaux", "Délicatesse impériale"], "stay": "Huế"},
            {"day": 8, "title": "Huế → Hội An", "location": "Hội An", "activities": ["Train ou bus Hai Van Pass", "Installation vieille ville"], "stay": "Hội An"},
            {"day": 9, "title": "Hội An — UNESCO", "location": "Hội An", "activities": ["Pont japonais", "Cours cuisine", "Lanternes"], "stay": "Hội An"},
            {"day": 10, "title": "Hội An — Détente", "location": "Hội An", "activities": ["Plage An Bàng", "Tailleur ou spa", "Marché nocturne"], "stay": "Hội An"},
            {"day": 11, "title": "Vol vers HCMC", "location": "Ho Chi Minh-Ville", "activities": ["Vol Đà Nẵng → SGN", "District 1", "Rooftop bar"], "stay": "HCMC"},
            {"day": 12, "title": "Ho Chi Minh-Ville", "location": "HCMC", "activities": ["War Museum", "Marché Bến Thành", "Food tour moto"], "stay": "HCMC"},
            {"day": 13, "title": "Delta du Mékong", "location": "Mékong", "activities": ["Excursion canaux", "Marché flottant", "Villages artisanaux"], "stay": "HCMC"},
            {"day": 14, "title": "Départ", "location": "HCMC", "activities": ["Shopping souvenirs", "Vol retour — prévoir 3h avant"], "stay": "—"},
        ],
    },
    "en": {
        "title": "14-day itinerary — Complete Vietnam",
        "summary": "North (Hanoi, Sapa), central (Huế, Hội An) and south (HCMC, Mekong) at a relaxed pace.",
        "budget_hint": "€950–1,600 (excluding international flights)",
        "days": [
            {"day": 1, "title": "Hanoi — Arrival", "location": "Hanoi", "activities": ["Old Quarter check-in", "Evening phở", "Hoàn Kiếm Lake walk"], "stay": "Hanoi"},
            {"day": 2, "title": "Hanoi — Culture", "location": "Hanoi", "activities": ["Temple of Literature", "Ethnology Museum", "Street food"], "stay": "Hanoi"},
            {"day": 3, "title": "Halong Bay 2D/1N", "location": "Halong", "activities": ["Transfer", "Cruise", "Kayaking"], "stay": "Boat"},
            {"day": 4, "title": "Halong → Sapa", "location": "Sapa", "activities": ["Return to Hanoi", "Overnight bus/train or flight + road to Sapa"], "stay": "Sapa"},
            {"day": 5, "title": "Sapa — Rice terraces", "location": "Sapa", "activities": ["Cat Cat or Ta Van trek", "Local market", "Fansipan view (cable car)"], "stay": "Sapa"},
            {"day": 6, "title": "Sapa → Huế", "location": "Huế", "activities": ["Descent to Huế", "Imperial City at sunset"], "stay": "Huế"},
            {"day": 7, "title": "Huế — Imperial", "location": "Huế", "activities": ["Citadel", "Imperial tombs", "Royal cuisine"], "stay": "Huế"},
            {"day": 8, "title": "Huế → Hội An", "location": "Hội An", "activities": ["Hai Van Pass train or bus", "Old town check-in"], "stay": "Hội An"},
            {"day": 9, "title": "Hội An — UNESCO", "location": "Hội An", "activities": ["Japanese Bridge", "Cooking class", "Lanterns"], "stay": "Hội An"},
            {"day": 10, "title": "Hội An — Relax", "location": "Hội An", "activities": ["An Bàng beach", "Tailor or spa", "Night market"], "stay": "Hội An"},
            {"day": 11, "title": "Flight to HCMC", "location": "Ho Chi Minh City", "activities": ["Đà Nẵng → SGN flight", "District 1", "Rooftop bar"], "stay": "HCMC"},
            {"day": 12, "title": "Ho Chi Minh City", "location": "HCMC", "activities": ["War Museum", "Bến Thành Market", "Motorbike food tour"], "stay": "HCMC"},
            {"day": 13, "title": "Mekong Delta", "location": "Mekong", "activities": ["Canal excursion", "Floating market", "Craft villages"], "stay": "HCMC"},
            {"day": 14, "title": "Departure", "location": "HCMC", "activities": ["Souvenir shopping", "Return flight — allow 3h before"], "stay": "—"},
        ],
    },
}

CHECKLIST = {
    "fr": {
        "title": "Checklist avant départ",
        "sections": [
            {
                "name": "Visa & documents",
                "items": [
                    "Passeport valide 6 mois après la date de retour",
                    "E-visa vietnamienne (ou visa consulaire) — demande 5–7 jours avant",
                    "Copies papier + cloud : passeport, visa, assurance, billets",
                    "2 photos d'identité format visa (au cas où)",
                ],
            },
            {
                "name": "eSIM & connectivité",
                "items": [
                    "eSIM activée avant le départ (Airalo, Holafly…)",
                    "Forfait 10–20 Go pour 2 semaines",
                    "App Grab installée + carte bancaire liée",
                    "Google Maps hors-ligne des villes visitées",
                ],
            },
            {
                "name": "Assurance voyage",
                "items": [
                    "Couverture frais médicaux ≥ 50 000 €",
                    "Rapatriement sanitaire inclus",
                    "Activités couvertes (moto, trek, plongée si prévu)",
                    "Numéro d'urgence assurance enregistré dans le téléphone",
                ],
            },
        ],
    },
    "en": {
        "title": "Pre-departure checklist",
        "sections": [
            {
                "name": "Visa & documents",
                "items": [
                    "Passport valid 6 months beyond return date",
                    "Vietnam e-visa (or consular visa) — apply 5–7 days ahead",
                    "Paper + cloud copies: passport, visa, insurance, tickets",
                    "2 passport photos (just in case)",
                ],
            },
            {
                "name": "eSIM & connectivity",
                "items": [
                    "eSIM activated before departure (Airalo, Holafly…)",
                    "10–20 GB plan for 2 weeks",
                    "Grab app installed + card linked",
                    "Offline Google Maps for visited cities",
                ],
            },
            {
                "name": "Travel insurance",
                "items": [
                    "Medical cover ≥ €50,000",
                    "Medical repatriation included",
                    "Activities covered (motorbike, trek, diving if planned)",
                    "Insurance emergency number saved in phone",
                ],
            },
        ],
    },
}

BUDGET_ROWS = {
    "fr": [
        ("Backpacker", "25–40 €", "Auberges, street food, bus", "450–700 €"),
        ("Confort milieu", "55–85 €", "3* boutique, mix local/resto", "800–1 200 €"),
        ("Premium", "110–180 €", "4*+, guides privés, vols int.", "1 400–2 500 €"),
    ],
    "en": [
        ("Backpacker", "€25–40", "Hostels, street food, buses", "€450–700"),
        ("Mid-range", "€55–85", "Boutique 3*, mix local/restaurants", "€800–1,200"),
        ("Premium", "€110–180", "4*+, private guides, domestic flights", "€1,400–2,500"),
    ],
}

CITY_SLUGS = ("hanoi", "hoi-an", "ho-chi-minh-city")


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontSize=28,
            leading=34,
            textColor=colors.white,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=base["Normal"],
            fontSize=14,
            leading=20,
            textColor=colors.HexColor("#D4B86A"),
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontSize=20,
            leading=26,
            textColor=TEAL,
            spaceBefore=16,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontSize=14,
            leading=18,
            textColor=TEAL_DEEP,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=INK,
        ),
        "muted": ParagraphStyle(
            "Muted",
            parent=base["Normal"],
            fontSize=9,
            leading=12,
            textColor=INK_SOFT,
        ),
        "day_title": ParagraphStyle(
            "DayTitle",
            parent=base["Normal"],
            fontSize=11,
            leading=14,
            textColor=TEAL,
            spaceBefore=6,
        ),
    }


def _cover_page(canvas, doc, lang: str):
    canvas.saveState()
    canvas.setFillColor(TEAL_DEEP)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, A4[1] - 8 * mm, A4[0], 8 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 26)
    y = A4[1] * 0.55
    title = "Inside Vietnam Travel" if lang == "en" else "Inside Vietnam Travel"
    canvas.drawCentredString(A4[0] / 2, y, title)
    canvas.setFont("Helvetica", 14)
    canvas.setFillColor(colors.HexColor("#D4B86A"))
    subtitle = "Vietnam Travel Guide — 2026 Edition" if lang == "en" else "Guide Voyage Vietnam — Édition 2026"
    canvas.drawCentredString(A4[0] / 2, y - 28, subtitle)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 11)
    tagline = (
        "Itineraries · Budgets · Addresses · Checklists"
        if lang == "en"
        else "Itinéraires · Budgets · Adresses · Checklists"
    )
    canvas.drawCentredString(A4[0] / 2, y - 55, tagline)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#cccccc"))
    footer = "www.insidevietnamtravel.fr"
    canvas.drawCentredString(A4[0] / 2, 2.5 * cm, footer)
    canvas.restoreState()


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(INK_SOFT)
    canvas.drawString(2 * cm, 1 * cm, "Inside Vietnam Travel — insidevietnamtravel.fr")
    canvas.drawRightString(A4[0] - 2 * cm, 1 * cm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def _checkbox_list(items: list[str], styles: dict) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(f"☐ {item}", styles["body"]), leftIndent=12) for item in items],
        bulletType="bullet",
        start=None,
    )


def _itinerary_section(itin: dict, styles: dict, lang: str) -> list:
    flow = [
        Paragraph(itin["title"], styles["h1"]),
        Paragraph(itin.get("summary", ""), styles["body"]),
        Paragraph(
            f"{'Budget indicatif' if lang == 'fr' else 'Indicative budget'} : "
            f"<b>{itin.get('budget_hint', '')}</b>",
            styles["muted"],
        ),
        Spacer(1, 8),
    ]
    for day in itin.get("days", []):
        day_label = f"{'Jour' if lang == 'fr' else 'Day'} {day['day']} — {day['title']}"
        flow.append(Paragraph(day_label, styles["day_title"]))
        loc = day.get("location", "")
        if loc:
            flow.append(Paragraph(f"📍 {loc}", styles["muted"]))
        for act in day.get("activities", []):
            flow.append(Paragraph(f"• {act}", styles["body"]))
        stay = day.get("stay", "")
        if stay and stay != "—":
            stay_lbl = "Nuit" if lang == "fr" else "Stay"
            flow.append(Paragraph(f"🛏 {stay_lbl} : {stay}", styles["muted"]))
        flow.append(Spacer(1, 4))
    return flow


def _addresses_section(styles: dict, lang: str) -> list:
    flow = [
        Paragraph(
            "Adresses testées" if lang == "fr" else "Tested addresses",
            styles["h1"],
        ),
        Paragraph(
            "Sélection d'hôtels et repères utiles par ville — à réserver en avance en haute saison."
            if lang == "fr"
            else "Selected hotels and useful spots by city — book ahead in high season.",
            styles["body"],
        ),
        Spacer(1, 8),
    ]
    for slug in CITY_SLUGS:
        dest = localize_destination(DESTINATIONS.get(slug, {}), lang)
        name = dest.get("name", slug)
        flow.append(Paragraph(name, styles["h2"]))
        for hotel in dest.get("hotels", [])[:3]:
            line = f"<b>{hotel['name']}</b> — {hotel.get('desc', '')} ({hotel.get('price_hint', '')})"
            flow.append(Paragraph(line, styles["body"]))
        tips = dest.get("tips", [])[:2]
        if tips:
            tip_lbl = "Conseil" if lang == "fr" else "Tip"
            for tip in tips:
                flow.append(Paragraph(f"💡 {tip_lbl} : {tip}", styles["muted"]))
        flow.append(Spacer(1, 6))
    return flow


def generate_pdf_bytes(lang: str = "fr") -> bytes:
    lang = "en" if lang == "en" else "fr"
    styles = _styles()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2 * cm,
        title="Inside Vietnam Travel — Guide PDF",
        author="Inside Vietnam Travel",
    )

    story: list = []

    story.append(Spacer(1, 1))
    story.append(Paragraph(
        "Table des matières" if lang == "fr" else "Table of contents",
        styles["h1"],
    ))
    toc_items = CHECKLIST[lang]["title"]
    for label in (
        toc_items,
        "Budget par style de voyage" if lang == "fr" else "Budget by travel style",
        "Adresses testées" if lang == "fr" else "Tested addresses",
        "Itinéraire 7 jours" if lang == "fr" else "7-day itinerary",
        "Itinéraire 10 jours" if lang == "fr" else "10-day itinerary",
        "Itinéraire 14 jours" if lang == "fr" else "14-day itinerary",
    ):
        story.append(Paragraph(f"• {label}", styles["body"]))
    story.append(PageBreak())

    cl = CHECKLIST[lang]
    story.append(Paragraph(cl["title"], styles["h1"]))
    for section in cl["sections"]:
        story.append(Paragraph(section["name"], styles["h2"]))
        story.append(_checkbox_list(section["items"], styles))
        story.append(Spacer(1, 6))
    story.append(PageBreak())

    budget_title = "Budget par style de voyage" if lang == "fr" else "Budget by travel style"
    story.append(Paragraph(budget_title, styles["h1"]))
    hdr = (
        ["Style", "Par jour", "Profil", "2 semaines"]
        if lang == "fr"
        else ["Style", "Per day", "Profile", "2 weeks"]
    )
    table_data = [hdr] + [list(row) for row in BUDGET_ROWS[lang]]
    tbl = Table(table_data, colWidths=[3.2 * cm, 2.5 * cm, 5.5 * cm, 3 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, RICE]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 8))
    note = (
        "Hors vols internationaux. Vols intérieurs : 40–80 €/trajet. "
        "Croisière Halong 2J/1N : 80–150 €."
        if lang == "fr"
        else "Excluding international flights. Domestic flights: €40–80/leg. "
        "Halong 2D/1N cruise: €80–150."
    )
    story.append(Paragraph(note, styles["muted"]))
    story.append(PageBreak())

    story.extend(_addresses_section(styles, lang))
    story.append(PageBreak())

    for slug in ITINERARY_SLUGS:
        raw = ITINERARIES[slug]
        itin = localize_itinerary(raw, lang)
        story.extend(_itinerary_section(itin, styles, lang))
        story.append(PageBreak())

    itin14 = ITINERARY_14_DAYS[lang]
    story.extend(_itinerary_section(itin14, styles, lang))

    doc.build(
        story,
        onFirstPage=lambda c, d: _cover_page(c, d, lang),
        onLaterPages=_footer,
    )
    return buffer.getvalue()


def pdf_filename(lang: str = "fr") -> str:
    if lang == "en":
        return "inside-vietnam-travel-guide-2026-en.pdf"
    return "inside-vietnam-travel-guide-2026.pdf"
