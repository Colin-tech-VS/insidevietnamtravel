"""Données des outils voyageurs : saisons, budget, visa, comparateurs.

Contenu bilingue FR/EN. Chaque fonction ``build_*`` renvoie une structure
déjà localisée prête pour les templates (même esprit que data/trip_planner.py).
"""

from __future__ import annotations

# ── Mois ──────────────────────────────────────────────────────────────
MONTHS = {
    "fr": ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
           "Juil", "Août", "Sep", "Oct", "Nov", "Déc"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

MONTHS_FULL = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
}

# Niveaux de pertinence d'une période
RATING_LABELS = {
    "ideal": {"fr": "Idéal", "en": "Ideal"},
    "good": {"fr": "Favorable", "en": "Good"},
    "fair": {"fr": "Correct", "en": "Fair"},
    "avoid": {"fr": "À éviter", "en": "Avoid"},
}

# ── Saisons par région (12 mois, 1 = janvier) ─────────────────────────
# r = rating mensuel
_REGIONS = [
    {
        "key": "north",
        "name": {"fr": "Nord", "en": "North"},
        "cities": {
            "fr": "Hanoï · Sapa · Baie d'Halong · Ninh Bình",
            "en": "Hanoi · Sapa · Halong Bay · Ninh Binh",
        },
        "best": {"fr": "Octobre à avril", "en": "October to April"},
        "summary": {
            "fr": "Climat à 4 saisons. L'automne (oct.–déc.) et le printemps "
                  "(mars–avr.) sont secs et doux : la meilleure fenêtre pour la "
                  "baie d'Halong et les treks de Sapa. Janvier–février peuvent "
                  "être froids et brumeux, l'été (mai–sept.) est chaud et très "
                  "pluvieux.",
            "en": "Four-season climate. Autumn (Oct–Dec) and spring (Mar–Apr) "
                  "are dry and mild — the best window for Halong Bay and Sapa "
                  "treks. January–February can be cold and misty; summer "
                  "(May–Sep) is hot and very wet.",
        },
        "months": ["fair", "fair", "good", "good", "fair", "avoid",
                   "avoid", "avoid", "good", "ideal", "ideal", "good"],
    },
    {
        "key": "central",
        "name": {"fr": "Centre", "en": "Central"},
        "cities": {
            "fr": "Huế · Đà Nẵng · Hội An · Phong Nha",
            "en": "Hue · Da Nang · Hoi An · Phong Nha",
        },
        "best": {"fr": "Février à août", "en": "February to August"},
        "summary": {
            "fr": "Saison sèche de février à août, idéale pour les plages de "
                  "Đà Nẵng et les vieilles ruelles de Hội An (févr.–mai avant "
                  "la grosse chaleur). Octobre–novembre concentre les pluies et "
                  "le risque de typhons et d'inondations.",
            "en": "Dry season from February to August, ideal for Da Nang's "
                  "beaches and Hoi An's old town (Feb–May before peak heat). "
                  "October–November sees heavy rain and a risk of typhoons and "
                  "flooding.",
        },
        "months": ["fair", "good", "ideal", "ideal", "ideal", "good",
                   "good", "good", "fair", "avoid", "avoid", "fair"],
    },
    {
        "key": "south",
        "name": {"fr": "Sud", "en": "South"},
        "cities": {
            "fr": "Hô-Chi-Minh-Ville · Delta du Mékong · Phú Quốc",
            "en": "Ho Chi Minh City · Mekong Delta · Phu Quoc",
        },
        "best": {"fr": "Novembre à avril", "en": "November to April"},
        "summary": {
            "fr": "Deux saisons : sèche (nov.–avr.) chaude et ensoleillée — la "
                  "période rêvée pour le Mékong et l'île de Phú Quốc — et "
                  "humide (mai–oct.) avec des averses tropicales souvent brèves "
                  "en fin d'après-midi.",
            "en": "Two seasons: dry (Nov–Apr), hot and sunny — the dream window "
                  "for the Mekong and Phu Quoc — and wet (May–Oct) with "
                  "tropical showers, often short and in the late afternoon.",
        },
        "months": ["ideal", "ideal", "ideal", "good", "fair", "fair",
                   "fair", "fair", "fair", "good", "ideal", "ideal"],
    },
]


def build_seasons(lang: str) -> dict:
    """Matrice saison + résumés par région, localisée."""
    regions = []
    for r in _REGIONS:
        regions.append({
            "key": r["key"],
            "name": r["name"][lang],
            "cities": r["cities"][lang],
            "best": r["best"][lang],
            "summary": r["summary"][lang],
            "months": [
                {"label": MONTHS[lang][i], "rating": rating,
                 "rating_label": RATING_LABELS[rating][lang]}
                for i, rating in enumerate(r["months"])
            ],
        })
    return {
        "regions": regions,
        "month_labels": MONTHS[lang],
        "legend": [
            {"rating": k, "label": RATING_LABELS[k][lang]}
            for k in ("ideal", "good", "fair", "avoid")
        ],
    }


# ── Budget journalier par style de voyage (€/personne/jour) ───────────
_BUDGET_STYLES = [
    {
        "key": "backpacker",
        "icon": "🎒",
        "name": {"fr": "Routard", "en": "Backpacker"},
        "desc": {"fr": "Dortoirs, street food, bus de nuit",
                 "en": "Dorms, street food, night buses"},
        "perday": {"stay": 9, "food": 9, "transport": 6, "activities": 8, "misc": 3},
    },
    {
        "key": "comfort",
        "icon": "🛏️",
        "name": {"fr": "Confort", "en": "Comfort"},
        "desc": {"fr": "Hôtels 3*, restaurants, trains & vols internes",
                 "en": "3* hotels, restaurants, trains & domestic flights"},
        "perday": {"stay": 32, "food": 20, "transport": 14, "activities": 18, "misc": 6},
    },
    {
        "key": "premium",
        "icon": "✨",
        "name": {"fr": "Premium", "en": "Premium"},
        "desc": {"fr": "Boutique-hôtels 4-5*, guides privés, croisières",
                 "en": "4-5* boutique hotels, private guides, cruises"},
        "perday": {"stay": 85, "food": 45, "transport": 35, "activities": 45, "misc": 15},
    },
]

_BUDGET_CATEGORIES = [
    {"key": "stay", "icon": "🏨", "label": {"fr": "Hébergement", "en": "Accommodation"}},
    {"key": "food", "icon": "🍜", "label": {"fr": "Repas", "en": "Food"}},
    {"key": "transport", "icon": "🚆", "label": {"fr": "Transports", "en": "Transport"}},
    {"key": "activities", "icon": "🎟️", "label": {"fr": "Activités", "en": "Activities"}},
    {"key": "misc", "icon": "🛍️", "label": {"fr": "Extras", "en": "Extras"}},
]

# Coûts ponctuels (par personne, sur tout le séjour)
_BUDGET_ONEOFF = [
    {"key": "visa", "label": {"fr": "e-visa", "en": "e-visa"}, "amount": 23,
     "hint": {"fr": "≈ 25 $ — gratuit si exempté", "en": "≈ $25 — free if exempt"}},
    {"key": "esim", "label": {"fr": "eSIM / data", "en": "eSIM / data"}, "amount": 12,
     "hint": {"fr": "data illimitée 2 semaines", "en": "unlimited data for 2 weeks"}},
    {"key": "insurance", "label": {"fr": "Assurance voyage", "en": "Travel insurance"}, "amount": 35,
     "hint": {"fr": "≈ 2 semaines", "en": "≈ 2 weeks"}},
]


def build_budget(lang: str) -> dict:
    """Catalogue budget : styles, catégories, coûts ponctuels (localisé)."""
    styles = []
    for s in _BUDGET_STYLES:
        styles.append({
            "key": s["key"],
            "icon": s["icon"],
            "name": s["name"][lang],
            "desc": s["desc"][lang],
            "perday": s["perday"],
            "perday_total": sum(s["perday"].values()),
        })
    categories = [
        {"key": c["key"], "icon": c["icon"], "label": c["label"][lang]}
        for c in _BUDGET_CATEGORIES
    ]
    oneoff = [
        {"key": o["key"], "label": o["label"][lang], "amount": o["amount"],
         "hint": o["hint"][lang]}
        for o in _BUDGET_ONEOFF
    ]
    return {"styles": styles, "categories": categories, "oneoff": oneoff}


# ── Visa : assistant simplifié ────────────────────────────────────────
# Durées d'exemption connues (politique 2023-2024) — données indicatives.
_VISA_EXEMPT = {
    45: ["FR", "DE", "IT", "ES", "GB", "RU", "JP", "KR", "DK", "SE", "NO", "FI", "BY"],
    21: ["PH"],
    30: ["TH", "MY", "SG", "ID", "LA", "KH"],
    14: ["BN"],
}

_VISA_COUNTRIES = [
    {"code": "FR", "fr": "France", "en": "France"},
    {"code": "BE", "fr": "Belgique", "en": "Belgium"},
    {"code": "CH", "fr": "Suisse", "en": "Switzerland"},
    {"code": "CA", "fr": "Canada", "en": "Canada"},
    {"code": "DE", "fr": "Allemagne", "en": "Germany"},
    {"code": "IT", "fr": "Italie", "en": "Italy"},
    {"code": "ES", "fr": "Espagne", "en": "Spain"},
    {"code": "GB", "fr": "Royaume-Uni", "en": "United Kingdom"},
    {"code": "US", "fr": "États-Unis", "en": "United States"},
    {"code": "AU", "fr": "Australie", "en": "Australia"},
    {"code": "OTHER", "fr": "Autre pays", "en": "Other country"},
]


def visa_exempt_days(code: str) -> int:
    for days, codes in _VISA_EXEMPT.items():
        if code in codes:
            return days
    return 0


def build_visa(lang: str) -> dict:
    countries = [
        {"code": c["code"], "name": c[lang], "exempt_days": visa_exempt_days(c["code"])}
        for c in _VISA_COUNTRIES
    ]
    return {
        "countries": countries,
        "evisa_url": "https://evisa.gov.vn/",
        "evisa_max_days": 90,
    }


# ── Comparateurs eSIM & assurance ─────────────────────────────────────
_ESIM_ROWS = [
    {
        "key": "esim_airalo", "name": "Airalo", "best": {"fr": "Le moins cher", "en": "Cheapest"},
        "price": {"fr": "dès ~5 €", "en": "from ~€5"},
        "data": {"fr": "1–20 Go", "en": "1–20 GB"},
        "validity": {"fr": "7–30 jours", "en": "7–30 days"},
        "pros": {"fr": "Catalogue mondial, prix bas, appli simple",
                 "en": "Global catalogue, low prices, simple app"},
        "cons": {"fr": "Data seule (pas d'appels)", "en": "Data only (no calls)"},
    },
    {
        "key": "esim_holafly", "name": "Holafly", "best": {"fr": "Data illimitée", "en": "Unlimited data"},
        "price": {"fr": "dès ~19 €", "en": "from ~€19"},
        "data": {"fr": "Illimitée", "en": "Unlimited"},
        "validity": {"fr": "5–90 jours", "en": "5–90 days"},
        "pros": {"fr": "Vraiment illimité, partage possible",
                 "en": "Truly unlimited, sharing on some plans"},
        "cons": {"fr": "Plus cher pour les courts séjours",
                 "en": "Pricier for short trips"},
    },
]

_INSURANCE_POINTS = {
    "fr": [
        "Frais médicaux & hospitalisation (visez ≥ 100 000 €)",
        "Rapatriement sanitaire inclus",
        "Couverture scooter/moto si vous comptez conduire",
        "Annulation et bagages selon les formules",
        "Activités à risque (trek, plongée) à vérifier",
    ],
    "en": [
        "Medical & hospital costs (aim for ≥ €100,000)",
        "Medical repatriation included",
        "Scooter/motorbike cover if you plan to ride",
        "Cancellation and baggage depending on the plan",
        "Check adventure activities (trekking, diving)",
    ],
}


def build_comparators(lang: str) -> dict:
    esim = [
        {
            "key": r["key"], "name": r["name"], "best": r["best"][lang],
            "price": r["price"][lang], "data": r["data"][lang],
            "validity": r["validity"][lang], "pros": r["pros"][lang],
            "cons": r["cons"][lang],
        }
        for r in _ESIM_ROWS
    ]
    return {"esim": esim, "insurance_points": _INSURANCE_POINTS[lang]}
