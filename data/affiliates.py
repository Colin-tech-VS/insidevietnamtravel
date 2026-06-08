"""
Affiliate IDs — replace PLACEHOLDER values with your real affiliate codes.
URL building logic lives in data/affiliate_urls.py
"""

AFFILIATE_IDS = {
    "booking_aid": "PLACEHOLDER",
    "agoda_cid": "PLACEHOLDER",
    "gyg_partner_id": "PLACEHOLDER",
    "viator_pid": "PLACEHOLDER",
    "airalo_ref": "PLACEHOLDER",
    "holafly_ref": "PLACEHOLDER",
    "worldnomads_affiliate": "PLACEHOLDER",
    "pdf_checkout_url": "#pdf-guide",
}

PDF_GUIDE = {
    "title": "Guide Vietnam PDF — Édition 2026",
    "subtitle": "Itinéraires, budgets, adresses et checklists imprimables",
    "price": "9,90 €",
    "features": [
        "3 itinéraires jour par jour (7, 10 et 14 jours)",
        "Checklist visa, eSIM et assurance",
        "Budget détaillé par style de voyage",
        "Adresses testées à Hanoï, Hội An et HCMC",
    ],
    "i18n": {
        "en": {
            "title": "Vietnam PDF Guide — 2026 Edition",
            "subtitle": "Itineraries, budgets, addresses and printable checklists",
            "price": "€9.90",
            "features": [
                "3 day-by-day itineraries (7, 10 and 14 days)",
                "Visa, eSIM and insurance checklist",
                "Detailed budget by travel style",
                "Tested addresses in Hanoi, Hội An and HCMC",
            ],
        },
    },
}

NEWSLETTER = {
    "title": "Conseils voyage Vietnam",
    "subtitle": "1 email par semaine : itinéraires, bons plans et nouveautés. Sans spam.",
    "placeholder": "votre@email.com",
    "cta": "S'inscrire gratuitement",
    "i18n": {
        "en": {
            "title": "Vietnam travel tips",
            "subtitle": "1 email per week: itineraries, deals and updates. No spam.",
            "placeholder": "your@email.com",
            "cta": "Subscribe for free",
        },
    },
}
