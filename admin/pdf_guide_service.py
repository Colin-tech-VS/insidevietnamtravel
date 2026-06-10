"""Génération du guide PDF Vietnam — édition premium Inside Vietnam Travel."""

from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    KeepTogether,
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

# Unicode fonts (Vietnamese diacritics: Hội An, Huế, Phở, Đà Nẵng…)
FONT_FAMILY = "NotoSans"
FONT_REGULAR = "NotoSans-Regular"
FONT_BOLD = "NotoSans-Bold"
FONT_ITALIC = "NotoSans-Italic"
FONT_BOLD_ITALIC = "NotoSans-BoldItalic"
_fonts_ready = False


def _ensure_pdf_fonts() -> None:
    global _fonts_ready
    if _fonts_ready:
        return
    fonts_dir = Path(__file__).resolve().parent / "fonts"
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(fonts_dir / "NotoSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(fonts_dir / "NotoSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_ITALIC, str(fonts_dir / "NotoSans-Italic.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD_ITALIC, str(fonts_dir / "NotoSans-BoldItalic.ttf")))
    pdfmetrics.registerFontFamily(
        FONT_FAMILY,
        normal=FONT_REGULAR,
        bold=FONT_BOLD,
        italic=FONT_ITALIC,
        boldItalic=FONT_BOLD_ITALIC,
    )
    _fonts_ready = True


def _pdf_bold(text: str) -> str:
    return f'<font name="{FONT_BOLD}">{text}</font>'


def _pdf_italic(text: str) -> str:
    return f'<font name="{FONT_ITALIC}">{text}</font>'

# Brand palette (site design system)
TEAL = colors.HexColor("#1B4D4A")
TEAL_DEEP = colors.HexColor("#0F3330")
TEAL_LIGHT = colors.HexColor("#2A6B66")
GOLD = colors.HexColor("#C4A053")
GOLD_LIGHT = colors.HexColor("#D4B86A")
RICE = colors.HexColor("#FAF7F2")
RICE_DARK = colors.HexColor("#F0EBE3")
INK = colors.HexColor("#1A1A18")
INK_SOFT = colors.HexColor("#4A4845")
INK_MUTED = colors.HexColor("#7A7772")
WHITE = colors.white
LOTUS = colors.HexColor("#E8D5C4")

PAGE_W, PAGE_H = A4
MARGIN_L = 2 * cm
MARGIN_R = 2 * cm
MARGIN_T = 2.4 * cm
MARGIN_B = 2.2 * cm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

ITINERARY_SLUGS = ("7-days-vietnam", "10-days-vietnam", "15-days-vietnam")

ITINERARY_14_DAYS = {
    "fr": {
        "title": "Itinéraire 14 jours",
        "subtitle": "Le Vietnam complet — Nord, Centre & Sud",
        "summary": "Hanoï, Halong, Sapa, Huế, Hội An, Ho Chi Minh-Ville et le delta du Mékong, à rythme confortable.",
        "budget_hint": "950–1 600 € (hors vol international)",
        "days": [
            {"day": 1, "title": "Arrivée à Hanoï", "location": "Hanoï", "activities": ["Installation Vieux Quartier", "Phở du soir au lac Hoàn Kiếm", "Première balade nocturne"], "stay": "Hanoï — Vieux Quartier"},
            {"day": 2, "title": "Hanoï culture & street food", "location": "Hanoï", "activities": ["Temple de la Littérature", "Musée d'Ethnographie", "Café egg coffee + street food"], "stay": "Hanoï"},
            {"day": 3, "title": "Baie d'Halong 2J/1N", "location": "Halong", "activities": ["Transfert matinal (3h)", "Embarquement croisière", "Kayak & grottes"], "stay": "Bateau croisière"},
            {"day": 4, "title": "Halong → Sapa", "location": "Sapa", "activities": ["Lever de soleil sur la baie", "Retour Hanoï", "Route ou train vers Sapa"], "stay": "Sapa"},
            {"day": 5, "title": "Sapa & rizières", "location": "Sapa", "activities": ["Trek Cat Cat ou Ta Van", "Marché local", "Vue Fansipan (téléphérique optionnel)"], "stay": "Sapa"},
            {"day": 6, "title": "Sapa → Huế", "location": "Huế", "activities": ["Descente vers Huế", "Citadelle impériale au coucher du soleil"], "stay": "Huế"},
            {"day": 7, "title": "Huế impérial", "location": "Huế", "activities": ["Citadelle & tombeaux", "Déjeuner cuisine impériale", "Promenade Perfume River"], "stay": "Huế"},
            {"day": 8, "title": "Huế → Hội An", "location": "Hội An", "activities": ["Train ou bus via Hai Van Pass", "Installation vieille ville"], "stay": "Hội An"},
            {"day": 9, "title": "Hội An UNESCO", "location": "Hội An", "activities": ["Pont japonais & temples", "Cours de cuisine", "Lanternes le soir"], "stay": "Hội An"},
            {"day": 10, "title": "Détente à Hội An", "location": "Hội An", "activities": ["Plage An Bàng", "Tailleur ou spa", "Marché nocturne"], "stay": "Hội An"},
            {"day": 11, "title": "Vol vers Ho Chi Minh-Ville", "location": "HCMC", "activities": ["Vol Đà Nẵng → SGN", "District 1 & rooftop", "Street food du soir"], "stay": "Ho Chi Minh-Ville"},
            {"day": 12, "title": "Ho Chi Minh-Ville", "location": "HCMC", "activities": ["War Museum", "Marché Bến Thành", "Food tour moto nocturne"], "stay": "HCMC"},
            {"day": 13, "title": "Delta du Mékong", "location": "Mékong", "activities": ["Excursion canaux", "Marché flottant", "Villages artisanaux"], "stay": "HCMC"},
            {"day": 14, "title": "Départ", "location": "HCMC", "activities": ["Derniers achats souvenirs", "Transfert aéroport — prévoir 3h avant le vol"], "stay": "—"},
        ],
    },
    "en": {
        "title": "14-day itinerary",
        "subtitle": "Complete Vietnam — North, Central & South",
        "summary": "Hanoi, Halong, Sapa, Huế, Hội An, Ho Chi Minh City and the Mekong Delta at a comfortable pace.",
        "budget_hint": "€950–1,600 (excluding international flights)",
        "days": [
            {"day": 1, "title": "Arrival in Hanoi", "location": "Hanoi", "activities": ["Old Quarter check-in", "Evening phở at Hoàn Kiếm Lake", "First night walk"], "stay": "Hanoi — Old Quarter"},
            {"day": 2, "title": "Hanoi culture & street food", "location": "Hanoi", "activities": ["Temple of Literature", "Ethnology Museum", "Egg coffee + street food"], "stay": "Hanoi"},
            {"day": 3, "title": "Halong Bay 2D/1N", "location": "Halong", "activities": ["Morning transfer (3h)", "Cruise boarding", "Kayaking & caves"], "stay": "Cruise boat"},
            {"day": 4, "title": "Halong → Sapa", "location": "Sapa", "activities": ["Sunrise on the bay", "Return to Hanoi", "Road or train to Sapa"], "stay": "Sapa"},
            {"day": 5, "title": "Sapa & rice terraces", "location": "Sapa", "activities": ["Cat Cat or Ta Van trek", "Local market", "Fansipan view (optional cable car)"], "stay": "Sapa"},
            {"day": 6, "title": "Sapa → Huế", "location": "Huế", "activities": ["Descent to Huế", "Imperial Citadel at sunset"], "stay": "Huế"},
            {"day": 7, "title": "Imperial Huế", "location": "Huế", "activities": ["Citadel & tombs", "Imperial cuisine lunch", "Perfume River walk"], "stay": "Huế"},
            {"day": 8, "title": "Huế → Hội An", "location": "Hội An", "activities": ["Train or bus via Hai Van Pass", "Old town check-in"], "stay": "Hội An"},
            {"day": 9, "title": "Hội An UNESCO", "location": "Hội An", "activities": ["Japanese Bridge & temples", "Cooking class", "Evening lanterns"], "stay": "Hội An"},
            {"day": 10, "title": "Relax in Hội An", "location": "Hội An", "activities": ["An Bàng beach", "Tailor or spa", "Night market"], "stay": "Hội An"},
            {"day": 11, "title": "Flight to Ho Chi Minh City", "location": "HCMC", "activities": ["Đà Nẵng → SGN flight", "District 1 & rooftop", "Evening street food"], "stay": "Ho Chi Minh City"},
            {"day": 12, "title": "Ho Chi Minh City", "location": "HCMC", "activities": ["War Museum", "Bến Thành Market", "Night motorbike food tour"], "stay": "HCMC"},
            {"day": 13, "title": "Mekong Delta", "location": "Mekong", "activities": ["Canal excursion", "Floating market", "Craft villages"], "stay": "HCMC"},
            {"day": 14, "title": "Departure", "location": "HCMC", "activities": ["Last souvenir shopping", "Airport transfer — allow 3h before flight"], "stay": "—"},
        ],
    },
}

CHECKLIST = {
    "fr": {
        "title": "Checklist avant départ",
        "intro": "Cochez chaque point avant votre départ — imprimez cette page ou gardez-la sur votre téléphone.",
        "sections": [
            {
                "icon": "01",
                "name": "Visa & documents",
                "items": [
                    "Passeport valide 6 mois après la date de retour",
                    "E-visa vietnamienne demandée 5–7 jours avant",
                    "Copies papier + cloud : passeport, visa, assurance, billets",
                    "2 photos d'identité format visa",
                    "Billets vol aller-retour + confirmations hôtels",
                ],
            },
            {
                "icon": "02",
                "name": "eSIM & connectivité",
                "items": [
                    "eSIM activée avant le départ (Airalo, Holafly…)",
                    "Forfait 10–20 Go pour 2 semaines",
                    "App Grab installée + carte bancaire liée",
                    "Google Maps hors-ligne (Hanoï, Hội An, HCMC)",
                    "Convertisseur de devises / carte sans frais étranger",
                ],
            },
            {
                "icon": "03",
                "name": "Assurance & santé",
                "items": [
                    "Couverture frais médicaux ≥ 50 000 €",
                    "Rapatriement sanitaire inclus",
                    "Activités couvertes (moto, trek, plongée)",
                    "Numéro d'urgence assurance enregistré",
                    "Trousse : anti-diarrhéique, répulsif, crème solaire",
                ],
            },
        ],
    },
    "en": {
        "title": "Pre-departure checklist",
        "intro": "Check off each item before you leave — print this page or keep it on your phone.",
        "sections": [
            {
                "icon": "01",
                "name": "Visa & documents",
                "items": [
                    "Passport valid 6 months beyond return date",
                    "Vietnam e-visa applied 5–7 days ahead",
                    "Paper + cloud copies: passport, visa, insurance, tickets",
                    "2 passport-format photos",
                    "Return flights + hotel confirmations",
                ],
            },
            {
                "icon": "02",
                "name": "eSIM & connectivity",
                "items": [
                    "eSIM activated before departure (Airalo, Holafly…)",
                    "10–20 GB plan for 2 weeks",
                    "Grab app installed + card linked",
                    "Offline Google Maps (Hanoi, Hội An, HCMC)",
                    "Currency converter / no-fee foreign card",
                ],
            },
            {
                "icon": "03",
                "name": "Insurance & health",
                "items": [
                    "Medical cover ≥ €50,000",
                    "Medical repatriation included",
                    "Activities covered (motorbike, trek, diving)",
                    "Insurance emergency number saved",
                    "Kit: anti-diarrheal, repellent, sunscreen",
                ],
            },
        ],
    },
}

BUDGET_ROWS = {
    "fr": [
        ("Backpacker", "25–40 €", "Auberges, street food, bus", "450–700 €", "Idéal 7–10 jours"),
        ("Confort", "55–85 €", "3* boutique, mix local/resto", "800–1 200 €", "Notre recommandation"),
        ("Premium", "110–180 €", "4*+, guides privés, vols int.", "1 400–2 500 €", "14 jours sans compromis"),
    ],
    "en": [
        ("Backpacker", "€25–40", "Hostels, street food, buses", "€450–700", "Ideal for 7–10 days"),
        ("Mid-range", "€55–85", "Boutique 3*, mix local/restaurants", "€800–1,200", "Our recommendation"),
        ("Premium", "€110–180", "4*+, private guides, domestic flights", "€1,400–2,500", "14 days, no compromise"),
    ],
}

CITY_SLUGS = ("hanoi", "hoi-an", "ho-chi-minh-city")

COPY = {
    "fr": {
        "edition": "Édition 2026",
        "tagline": "Itinéraires · Budgets · Adresses · Checklists",
        "welcome_title": "Bienvenue",
        "welcome_body": (
            "Ce guide a été conçu pour vous faire gagner des heures de recherche. "
            "Trois circuits testés, des budgets réalistes et des adresses que nous recommandons "
            "à nos lecteurs depuis Inside Vietnam Travel."
        ),
        "welcome_list": [
            "3 itinéraires jour par jour (7, 10 et 14 jours)",
            "Checklists visa, eSIM et assurance imprimables",
            "Budget détaillé par style de voyage",
            "Hôtels testés à Hanoï, Hội An et Ho Chi Minh-Ville",
            "Conseils pratiques et repères locaux",
        ],
        "toc": "Sommaire",
        "budget_title": "Budget par style",
        "budget_intro": "Estimations pour 2 semaines, hors vol international.",
        "budget_note": "Vols intérieurs : 40–80 €/trajet · Croisière Halong 2J/1N : 80–150 € · Visa e-visa : ~25 €",
        "addr_title": "Adresses testées",
        "addr_intro": "Sélection d'hôtels par ville — réservez en avance en haute saison (nov–mars).",
        "tip": "Conseil",
        "night": "Nuit",
        "day": "Jour",
        "budget_lbl": "Budget indicatif",
        "back_title": "Bon voyage au Vietnam",
        "back_body": "Retrouvez nos guides gratuits, articles et nouveautés sur insidevietnamtravel.fr",
        "footer": "Inside Vietnam Travel",
    },
    "en": {
        "edition": "2026 Edition",
        "tagline": "Itineraries · Budgets · Addresses · Checklists",
        "welcome_title": "Welcome",
        "welcome_body": (
            "This guide is designed to save you hours of research. "
            "Three tested routes, realistic budgets and addresses we recommend "
            "to our readers at Inside Vietnam Travel."
        ),
        "welcome_list": [
            "3 day-by-day itineraries (7, 10 and 14 days)",
            "Printable visa, eSIM and insurance checklists",
            "Detailed budget by travel style",
            "Tested hotels in Hanoi, Hội An and Ho Chi Minh City",
            "Practical tips and local reference points",
        ],
        "toc": "Contents",
        "budget_title": "Budget by style",
        "budget_intro": "Estimates for 2 weeks, excluding international flights.",
        "budget_note": "Domestic flights: €40–80/leg · Halong 2D/1N cruise: €80–150 · E-visa: ~€25",
        "addr_title": "Tested addresses",
        "addr_intro": "Hotel picks by city — book ahead in high season (Nov–Mar).",
        "tip": "Tip",
        "night": "Stay",
        "day": "Day",
        "budget_lbl": "Indicative budget",
        "back_title": "Have a wonderful trip",
        "back_body": "Find our free guides, articles and updates at insidevietnamtravel.fr",
        "footer": "Inside Vietnam Travel",
    },
}


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "welcome_lead": ParagraphStyle(
            "WelcomeLead", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=11, leading=16,
            textColor=INK_SOFT, spaceAfter=14,
        ),
        "welcome_item": ParagraphStyle(
            "WelcomeItem", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=15,
            textColor=INK, leftIndent=8, spaceBefore=4,
        ),
        "section_intro": ParagraphStyle(
            "SectionIntro", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14,
            textColor=INK_SOFT, spaceAfter=12,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=9.5, leading=13,
            textColor=INK,
        ),
        "muted": ParagraphStyle(
            "Muted", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=8.5, leading=11,
            textColor=INK_MUTED,
        ),
        "hotel_name": ParagraphStyle(
            "HotelName", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=13,
            textColor=TEAL, spaceBefore=2,
        ),
        "hotel_desc": ParagraphStyle(
            "HotelDesc", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=9, leading=12,
            textColor=INK_SOFT,
        ),
        "toc_item": ParagraphStyle(
            "TocItem", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14,
            textColor=INK,
        ),
        "check_item": ParagraphStyle(
            "CheckItem", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=9, leading=12,
            textColor=INK,
        ),
    }


def _draw_cover(c: canvas.Canvas, lang: str):
    c.saveState()
    # Background layers
    c.setFillColor(TEAL_DEEP)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, PAGE_H * 0.38, PAGE_W, PAGE_H * 0.62, fill=1, stroke=0)
    # Decorative arcs
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.circle(PAGE_W * 0.85, PAGE_H * 0.72, 4.5 * cm, fill=0, stroke=1)
    c.circle(PAGE_W * 0.12, PAGE_H * 0.28, 3 * cm, fill=0, stroke=1)
    c.setFillColor(GOLD)
    c.rect(0, PAGE_H - 5 * mm, PAGE_W, 5 * mm, fill=1, stroke=0)
    c.rect(MARGIN_L, PAGE_H * 0.36, CONTENT_W, 1.5 * mm, fill=1, stroke=0)
    # Edition badge
    badge_y = PAGE_H * 0.78
    c.setFillColor(GOLD)
    c.roundRect(PAGE_W / 2 - 2.8 * cm, badge_y, 5.6 * cm, 0.9 * cm, 4, fill=1, stroke=0)
    c.setFillColor(TEAL_DEEP)
    c.setFont(FONT_BOLD, 9)
    c.drawCentredString(PAGE_W / 2, badge_y + 0.28 * cm, COPY[lang]["edition"].upper())
    # Title block
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 32)
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.58, "Inside Vietnam")
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.58 - 1.1 * cm, "Travel")
    c.setFont(FONT_REGULAR, 15)
    c.setFillColor(GOLD_LIGHT)
    title = "Guide Voyage Vietnam" if lang == "fr" else "Vietnam Travel Guide"
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.58 - 2.2 * cm, title)
    c.setFont(FONT_REGULAR, 11)
    c.setFillColor(colors.HexColor("#E8E4DC"))
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.58 - 3.1 * cm, COPY[lang]["tagline"])
    # Feature pills
    features = COPY[lang]["welcome_list"][:3]
    y_pill = PAGE_H * 0.22
    for feat in features:
        c.setFillColor(colors.HexColor("#1a3d3a"))
        c.roundRect(MARGIN_L + 0.5 * cm, y_pill, CONTENT_W - 1 * cm, 0.75 * cm, 3, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_REGULAR, 9)
        c.drawString(MARGIN_L + 1 * cm, y_pill + 0.25 * cm, f"  {feat}")
        y_pill -= 1.05 * cm
    c.setFillColor(INK_MUTED)
    c.setFont(FONT_REGULAR, 8)
    c.drawCentredString(PAGE_W / 2, 1.8 * cm, "www.insidevietnamtravel.fr")
    c.restoreState()


def _draw_back_cover(c: canvas.Canvas, lang: str):
    c.saveState()
    c.setFillColor(RICE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, PAGE_H * 0.55, PAGE_W, PAGE_H * 0.45, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(MARGIN_L, PAGE_H * 0.54, CONTENT_W, 2 * mm, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.setFont(FONT_BOLD, 22)
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.68, COPY[lang]["back_title"])
    c.setFillColor(WHITE)
    c.setFont(FONT_REGULAR, 11)
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.68 - 1.2 * cm, COPY[lang]["back_body"])
    c.setFillColor(TEAL)
    c.setFont(FONT_BOLD, 14)
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.32, "Inside Vietnam Travel")
    c.setFont(FONT_REGULAR, 9)
    c.setFillColor(INK_MUTED)
    c.drawCentredString(PAGE_W / 2, PAGE_H * 0.32 - 0.8 * cm, "© 2026 — insidevietnamtravel.fr")
    c.restoreState()


def _page_frame(c: canvas.Canvas, doc, *, section: str = ""):
    c.saveState()
    # Rice background strip at top
    c.setFillColor(RICE)
    c.rect(0, PAGE_H - 1.6 * cm, PAGE_W, 1.6 * cm, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, PAGE_H - 1.65 * cm, PAGE_W, 1.5 * mm, fill=1, stroke=0)
    c.setFont(FONT_BOLD, 8)
    c.setFillColor(TEAL)
    c.drawString(MARGIN_L, PAGE_H - 1.1 * cm, COPY.get(getattr(doc, "_lang", "fr"), COPY["fr"])["footer"])
    if section:
        c.setFont(FONT_REGULAR, 8)
        c.setFillColor(INK_MUTED)
        c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 1.1 * cm, section)
    # Footer
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.4)
    c.line(MARGIN_L, 1.4 * cm, PAGE_W - MARGIN_R, 1.4 * cm)
    c.setFont(FONT_REGULAR, 7.5)
    c.setFillColor(INK_MUTED)
    c.drawString(MARGIN_L, 0.85 * cm, "insidevietnamtravel.fr")
    c.drawRightString(PAGE_W - MARGIN_R, 0.85 * cm, str(c.getPageNumber()))
    c.restoreState()


def _section_divider(title: str, subtitle: str, styles: dict) -> list:
    """Full-width section opener block."""
    header = Table(
        [[Paragraph(f'<font color="white">{_pdf_bold(title)}</font>', ParagraphStyle(
            "SecH", fontName=FONT_REGULAR, fontSize=18, leading=22, textColor=WHITE, alignment=TA_LEFT,
        ))],
         [Paragraph(f'<font color="#D4B86A">{subtitle}</font>', ParagraphStyle(
            "SecS", fontName=FONT_REGULAR, fontSize=10, leading=14, textColor=GOLD_LIGHT,
        ))]],
        colWidths=[CONTENT_W],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (0, 0), 18),
        ("BOTTOMPADDING", (0, 0), (0, 0), 6),
        ("TOPPADDING", (0, 1), (0, 1), 4),
        ("BOTTOMPADDING", (0, 1), (0, 1), 18),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return [Spacer(1, 6), header, Spacer(1, 14)]


def _welcome_page(lang: str, styles: dict) -> list:
    cp = COPY[lang]
    flow = [
        Paragraph(f'<font color="#1B4D4A">{_pdf_bold(cp["welcome_title"])}</font>', ParagraphStyle(
            "WTitle", fontName=FONT_REGULAR, fontSize=20, leading=26, textColor=TEAL, spaceAfter=10,
        )),
        Paragraph(cp["welcome_body"], styles["welcome_lead"]),
    ]
    for item in cp["welcome_list"]:
        row = Table(
            [["", Paragraph(item, styles["welcome_item"])]],
            colWidths=[0.5 * cm, CONTENT_W - 0.5 * cm],
        )
        row.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), GOLD),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [RICE_DARK]),
        ]))
        flow.append(row)
        flow.append(Spacer(1, 4))
    return flow


def _toc_page(lang: str, styles: dict) -> list:
    cp = COPY[lang]
    items = [
        CHECKLIST[lang]["title"],
        cp["budget_title"],
        cp["addr_title"],
        localize_itinerary(ITINERARIES["7-days-vietnam"], lang)["title"],
        localize_itinerary(ITINERARIES["10-days-vietnam"], lang)["title"],
        ITINERARY_14_DAYS[lang]["title"],
    ]

    rows = []
    for label in items:
        rows.append([
            Paragraph(f'<font color="#C4A053">■</font>  {label}', styles["toc_item"]),
        ])
    tbl = Table(rows, colWidths=[CONTENT_W])
    tbl.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, RICE_DARK),
    ]))
    return [
        Paragraph(f'<font color="#1B4D4A">{_pdf_bold(cp["toc"])}</font>', ParagraphStyle(
            "TocTitle", fontName=FONT_REGULAR, fontSize=20, leading=26, textColor=TEAL, spaceAfter=16,
        )),
        tbl,
    ]


def _checklist_section(lang: str, styles: dict) -> list:
    cl = CHECKLIST[lang]
    flow = _section_divider(cl["title"], cl["intro"], styles)
    flow.append(Paragraph(cl["intro"], styles["section_intro"]))

    for section in cl["sections"]:
        rows = [[
            Paragraph(f'<font color="white">{_pdf_bold(section["icon"])}</font>', ParagraphStyle(
                "Icon", fontName=FONT_BOLD, fontSize=11, alignment=TA_CENTER, textColor=WHITE,
            )),
            Paragraph(_pdf_bold(section["name"]), ParagraphStyle(
                "SecName", fontName=FONT_BOLD, fontSize=11, textColor=TEAL, leading=14,
            )),
        ]]
        sec_hdr = Table(rows, colWidths=[1.1 * cm, CONTENT_W - 1.1 * cm])
        sec_hdr.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), TEAL),
            ("BACKGROUND", (1, 0), (1, 0), RICE_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        flow.append(sec_hdr)

        check_rows = []
        for item in section["items"]:
            check_rows.append([
                "",
                Paragraph(item, styles["check_item"]),
            ])
        checks = Table(check_rows, colWidths=[0.7 * cm, CONTENT_W - 0.7 * cm])
        checks.setStyle(TableStyle([
            ("BOX", (0, 0), (0, -1), 0.8, TEAL_LIGHT),
            ("INNERGRID", (0, 0), (0, -1), 0.5, RICE_DARK),
            ("LEFTPADDING", (1, 0), (1, -1), 8),
            ("RIGHTPADDING", (1, 0), (1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (1, 0), (1, -1), [WHITE, RICE]),
        ]))
        flow.append(checks)
        flow.append(Spacer(1, 10))
    return flow


def _budget_section(lang: str, styles: dict) -> list:
    cp = COPY[lang]
    flow = _section_divider(cp["budget_title"], cp["budget_intro"], styles)
    hdr = (
        ["Style", "Par jour", "Profil", "2 sem.", "Note"]
        if lang == "fr"
        else ["Style", "Per day", "Profile", "2 wks", "Note"]
    )
    data = [hdr] + [list(row) for row in BUDGET_ROWS[lang]]
    col_w = [2.4 * cm, 2 * cm, 4.8 * cm, 2.4 * cm, 3.6 * cm]
    tbl = Table(data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL_DEEP),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 1), (0, -1), FONT_BOLD),
        ("TEXTCOLOR", (0, 1), (0, -1), TEAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, RICE, RICE_DARK]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ddd8d0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        # Highlight recommended row
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#eef6f5")),
        ("BOX", (0, 2), (-1, 2), 1, GOLD),
    ]))
    flow.append(tbl)
    flow.append(Spacer(1, 10))
    flow.append(Paragraph(cp["budget_note"], styles["muted"]))
    return flow


def _addresses_section(lang: str, styles: dict) -> list:
    cp = COPY[lang]
    flow = _section_divider(cp["addr_title"], cp["addr_intro"], styles)

    for slug in CITY_SLUGS:
        dest = localize_destination(DESTINATIONS.get(slug, {}), lang)
        name = dest.get("name", slug)
        city_hdr = Table(
            [[Paragraph(f'<font color="white">{_pdf_bold(name)}</font>', ParagraphStyle(
                "CityH", fontName=FONT_BOLD, fontSize=13, textColor=WHITE,
            ))]],
            colWidths=[CONTENT_W],
        )
        city_hdr.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        flow.append(city_hdr)

        hotel_rows = [["Hôtel" if lang == "fr" else "Hotel", "Description", "Prix" if lang == "fr" else "Price"]]
        for hotel in dest.get("hotels", [])[:3]:
            hotel_rows.append([
                hotel["name"],
                hotel.get("desc", ""),
                hotel.get("price_hint", ""),
            ])
        htbl = Table(hotel_rows, colWidths=[4.2 * cm, 7.8 * cm, 3.2 * cm])
        htbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), RICE_DARK),
            ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("FONTNAME", (0, 1), (0, -1), FONT_BOLD),
            ("TEXTCOLOR", (0, 1), (0, -1), TEAL),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, RICE]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ddd8d0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        flow.append(htbl)

        for tip in dest.get("tips", [])[:2]:
            tip_tbl = Table(
                [[Paragraph(f'{_pdf_bold(cp["tip"] + " —")} {tip}', styles["muted"])]],
                colWidths=[CONTENT_W],
            )
            tip_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#faf6ee")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, GOLD),
            ]))
            flow.append(Spacer(1, 4))
            flow.append(tip_tbl)
        flow.append(Spacer(1, 12))
    return flow


def _day_card(day: dict, lang: str, styles: dict) -> Table:
    cp = COPY[lang]
    acts = "<br/>".join(f"• {a}" for a in day.get("activities", []))
    stay = day.get("stay", "")
    stay_line = ""
    if stay and stay != "—":
        stay_line = f'<br/><font color="#7A7772">{_pdf_italic(f"{cp["night"]} : {stay}")}</font>'

    left = Paragraph(
        f'<font color="white">{_pdf_bold(str(day["day"]))}</font>',
        ParagraphStyle("DayNum", fontName=FONT_BOLD, fontSize=14, alignment=TA_CENTER, textColor=WHITE, leading=16),
    )
    title_html = f'<font color="#1B4D4A"><font name="{FONT_BOLD}">{day["title"]}</font></font>'
    right = Paragraph(
        f'{title_html}'
        f'<br/><font color="#C4A053">{day.get("location", "")}</font>'
        f'<br/><br/>{acts}{stay_line}',
        ParagraphStyle("DayBody", fontName=FONT_REGULAR, fontSize=9, leading=12, textColor=INK),
    )
    card = Table([[left, right]], colWidths=[1.4 * cm, CONTENT_W - 1.4 * cm])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), TEAL),
        ("BACKGROUND", (1, 0), (1, 0), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#ddd8d0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 4),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
        ("RIGHTPADDING", (1, 0), (1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return card


def _itinerary_section(itin: dict, lang: str, styles: dict) -> list:
    cp = COPY[lang]
    subtitle = itin.get("summary", "")
    title = itin.get("title", "")
    if "subtitle" in itin:
        title = itin["title"]
        subtitle = itin.get("subtitle", subtitle)

    flow = _section_divider(title, subtitle, styles)
    flow.append(Paragraph(
        f'{_pdf_bold(cp["budget_lbl"] + " :")} {itin.get("budget_hint", "")}',
        ParagraphStyle("BudgetHint", fontName=FONT_REGULAR, fontSize=10, textColor=TEAL, spaceAfter=12),
    ))

    for day in itin.get("days", []):
        flow.append(KeepTogether([_day_card(day, lang, styles), Spacer(1, 6)]))
    return flow


class _BackCoverPage(Flowable):
    """Page de fin pleine page."""

    def __init__(self, lang: str):
        super().__init__()
        self._lang = lang

    def wrap(self, availWidth, availHeight):
        return availWidth, availHeight

    def draw(self):
        _draw_back_cover(self.canv, self._lang)


def generate_pdf_bytes(lang: str = "fr") -> bytes:
    _ensure_pdf_fonts()
    lang = "en" if lang == "en" else "fr"
    styles = _styles()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B,
        title="Inside Vietnam Travel — Guide PDF 2026",
        author="Inside Vietnam Travel",
    )
    doc._lang = lang  # type: ignore[attr-defined]

    story: list = []
    story.append(PageBreak())  # cover is drawn on page 1 via callback
    story.extend(_welcome_page(lang, styles))
    story.append(PageBreak())
    story.extend(_toc_page(lang, styles))
    story.append(PageBreak())
    story.extend(_checklist_section(lang, styles))
    story.append(PageBreak())
    story.extend(_budget_section(lang, styles))
    story.append(PageBreak())
    story.extend(_addresses_section(lang, styles))
    story.append(PageBreak())

    for slug in ITINERARY_SLUGS:
        itin = localize_itinerary(ITINERARIES[slug], lang)
        story.extend(_itinerary_section(itin, lang, styles))
        story.append(PageBreak())

    story.extend(_itinerary_section(ITINERARY_14_DAYS[lang], lang, styles))
    story.append(PageBreak())
    story.append(_BackCoverPage(lang))

    doc.build(
        story,
        onFirstPage=lambda c, d: _draw_cover(c, lang),
        onLaterPages=_page_frame,
    )
    return buffer.getvalue()


def pdf_filename(lang: str = "fr") -> str:
    if lang == "en":
        return "inside-vietnam-travel-guide-2026-en.pdf"
    return "inside-vietnam-travel-guide-2026.pdf"
