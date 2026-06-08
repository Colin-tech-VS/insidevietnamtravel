"""
Catalogue des partenaires affiliés intégrés au site.
Chaque partenaire a un id (pour le tracking des clics) et un id_key (clé dans affiliate_ids.json).
"""

BUILTIN_PARTNERS = [
    {
        "id": "booking",
        "id_key": "booking_aid",
        "name": "Booking.com",
        "category": "Hôtel",
        "icon": "🏨",
        "description": "Liens affiliés vers des recherches hôtel (ville ou nom d'hôtel) — vous n'avez pas à louer ni lister de logement.",
        "what_you_earn": "~5 à 15 € par réservation confirmée (25-40% de la commission Booking).",
        "avg_per_click": 8.0,
        "signup_url": "https://signup.cj.com/member/signup/publisher/",
        "signup_note": (
            "Le « Affiliate Partner Centre » Booking est réservé aux anciens comptes directs — "
            "message « no access rights » = normal pour un nouveau site. "
            "En France : créez un compte éditeur sur CJ Affiliate, puis postulez au programme « Booking.com » "
            "dans le répertoire annonceurs CJ. "
            "« Promotional property » = URL du site (https://www.insidevietnamtravel.fr), pas un appartement. "
            "Une fois approuvé sur CJ, récupérez votre AID et collez-le ici."
        ),
        "id_label": "AID (affiliate ID)",
        "id_placeholder": "ex: 1234567",
    },
    {
        "id": "agoda",
        "id_key": "agoda_cid",
        "name": "Agoda",
        "category": "Hôtel",
        "icon": "🏩",
        "description": "Alternative populaire à Booking, forte en Asie.",
        "what_you_earn": "~4 à 12 € par nuitée réservée selon l'hôtel.",
        "avg_per_click": 6.0,
        "signup_url": "https://partners.agoda.com/",
        "id_label": "CID (campaign ID)",
        "id_placeholder": "ex: 987654",
    },
    {
        "id": "getyourguide",
        "id_key": "gyg_partner_id",
        "name": "GetYourGuide",
        "category": "Activité",
        "icon": "🎯",
        "description": "Tours, food tours, excursions et billets.",
        "what_you_earn": "~8% du prix de l'activité (~3-8 € par booking).",
        "avg_per_click": 4.0,
        "signup_url": "https://partner.getyourguide.com/",
        "id_label": "Partner ID",
        "id_placeholder": "ex: ABC123",
    },
    {
        "id": "viator",
        "id_key": "viator_pid",
        "name": "Viator",
        "category": "Activité",
        "icon": "🗺️",
        "description": "Tours et excursions (groupe TripAdvisor).",
        "what_you_earn": "~8% du prix (~3-8 € par réservation).",
        "avg_per_click": 4.0,
        "signup_url": "https://www.viator.com/affiliates",
        "id_label": "PID (partner ID)",
        "id_placeholder": "ex: P00012345",
    },
    {
        "id": "esim_airalo",
        "id_key": "airalo_ref",
        "name": "Airalo",
        "category": "eSIM",
        "icon": "📱",
        "description": "eSIM Vietnam — internet dès l'atterrissage.",
        "what_you_earn": "~10-15% par eSIM vendue (~1-3 €).",
        "avg_per_click": 2.0,
        "signup_url": "https://www.airalo.com/affiliate",
        "id_label": "Code ref",
        "id_placeholder": "ex: votre-ref",
    },
    {
        "id": "esim_holafly",
        "id_key": "holafly_ref",
        "name": "Holafly",
        "category": "eSIM",
        "icon": "📶",
        "description": "eSIM données illimitées pour le Vietnam.",
        "what_you_earn": "~10% par vente (~1-3 €).",
        "avg_per_click": 2.0,
        "signup_url": "https://esim.holafly.com/affiliates",
        "id_label": "Code ref",
        "id_placeholder": "ex: votre-ref",
    },
    {
        "id": "travel_insurance",
        "id_key": "worldnomads_affiliate",
        "name": "World Nomads",
        "category": "Assurance",
        "icon": "🛡️",
        "description": "Assurance voyage pour le Vietnam.",
        "what_you_earn": "~5 à 20 € par police d'assurance vendue.",
        "avg_per_click": 5.0,
        "signup_url": "https://www.worldnomads.com/affiliates",
        "id_label": "Affiliate code",
        "id_placeholder": "ex: votre-code",
    },
    {
        "id": "pdf",
        "id_key": "pdf_checkout_url",
        "name": "Guide PDF",
        "category": "Produit digital",
        "icon": "📄",
        "description": "Votre guide PDF vendu directement (Gumroad, LemonSqueezy…).",
        "what_you_earn": "100% du prix (ex: 9,90 €) moins frais plateforme.",
        "avg_per_click": 9.0,
        "signup_url": "https://gumroad.com/",
        "id_label": "URL de paiement",
        "id_placeholder": "https://gumroad.com/l/votre-guide",
    },
]

PARTNER_BY_ID = {p["id"]: p for p in BUILTIN_PARTNERS}
PARTNER_BY_KEY = {p["id_key"]: p for p in BUILTIN_PARTNERS}
