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
        "dashboard_url": "https://members.cj.com/",
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
        "dashboard_url": "https://partners.agoda.com/",
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
        "dashboard_url": "https://partner.getyourguide.com/",
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
        "signup_url": "https://partners.viator.com/signup",
        "dashboard_url": "https://partners.viator.com/",
        "signup_note": (
            "Inscription : partners.viator.com → Widgets → Créer un widget (type Destination). "
            "Collez le PID (data-vi-partner-id) et la réf. widget (data-vi-widget-ref) "
            "ou le code embed complet — le widget s'affiche sur chaque page destination."
        ),
        "id_label": "PID (partner ID)",
        "id_placeholder": "ex: P00304778",
        "widget_id_key": "viator_widget_ref",
        "widget_id_label": "Réf. widget Viator",
        "widget_id_placeholder": "W-e126cc1a-… ou code embed complet",
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
        "dashboard_url": "https://affiliates.airalo.com/",
        "id_label": "Lien d'affiliation ou code ref",
        "id_placeholder": "ex: https://airalo.pxf.io/c/XXXX/XXXX/XXXX (lien complet) ou code ref",
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
        "dashboard_url": "https://affiliates.holafly.com/",
        "id_label": "Lien d'affiliation ou code ref",
        "id_placeholder": "ex: lien d'affiliation complet ou code ref",
    },
    {
        "id": "travel_insurance",
        "id_key": "heymondo_ref",
        "name": "Heymondo",
        "category": "Assurance",
        "icon": "🛡️",
        "description": "Assurance voyage (France & international) — rapatriement, frais médicaux, annulation.",
        "what_you_earn": "~8 à 25 € par police vendue (commission variable selon formule).",
        "avg_per_click": 5.0,
        "signup_url": "https://heymondo.fr/programme-affiliation/",
        "dashboard_url": "https://heymondo.fr/programme-affiliation/",
        "signup_note": (
            "Inscription sur heymondo.fr/programme-affiliation — une fois accepté, collez ici "
            "votre lien d'affiliation complet (recommandé, ex. lien Impact/CJ) ou votre code partenaire."
        ),
        "id_label": "Lien d'affiliation ou code partenaire",
        "id_placeholder": "ex: https://… (lien complet) ou code cod=",
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
        "dashboard_url": "https://dashboard.stripe.com/",
        "id_label": "URL de paiement",
        "id_placeholder": "https://gumroad.com/l/votre-guide",
    },
]

PARTNER_BY_ID = {p["id"]: p for p in BUILTIN_PARTNERS}
PARTNER_BY_KEY = {p["id_key"]: p for p in BUILTIN_PARTNERS}
