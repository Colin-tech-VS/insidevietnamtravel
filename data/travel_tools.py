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
    """Matrice saison + résumés par région + destinations pour le planificateur."""
    from data.trip_planner import PLANNER_CITIES, CITY_REGION

    lang = "en" if lang == "en" else "fr"
    region_by_key = {r["key"]: r for r in _REGIONS}

    try:
        from admin.store import get_destinations_dict
        dest_names = get_destinations_dict(lang)
    except Exception:
        dest_names = {}

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

    destinations = []
    for city in PLANNER_CITIES:
        slug = city["slug"]
        region_key = CITY_REGION.get(slug, city["region"])
        region = region_by_key.get(region_key, _REGIONS[0])
        name = dest_names.get(slug, {}).get("name", slug.replace("-", " ").title())
        destinations.append({
            "slug": slug,
            "name": name,
            "region": region_key,
            "region_name": region["name"][lang],
            "best": region["best"][lang],
            "hint": region["summary"][lang][:220],
            "months": region["months"],
        })

    planner_destinations = {
        d["slug"]: {
            "slug": d["slug"],
            "name": d["name"],
            "region": d["region"],
            "months": d["months"],
        }
        for d in destinations
    }

    return {
        "regions": regions,
        "destinations": destinations,
        "month_labels": MONTHS[lang],
        "month_labels_full": MONTHS_FULL[lang],
        "legend": [
            {"rating": k, "label": RATING_LABELS[k][lang]}
            for k in ("ideal", "good", "fair", "avoid")
        ],
        "planner": {
            "destinations": planner_destinations,
            "month_labels": MONTHS[lang],
            "ratings": {k: RATING_LABELS[k][lang] for k in RATING_LABELS},
        },
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
    {"code": "NL", "fr": "Pays-Bas", "en": "Netherlands"},
    {"code": "OTHER", "fr": "Autre pays", "en": "Other country"},
]


def visa_exempt_days(code: str) -> int:
    for days, codes in _VISA_EXEMPT.items():
        if code in codes:
            return days
    return 0


def _visa_section(key, title_fr, title_en, intro_fr, intro_en, items):
    return {
        "key": key,
        "title": {"fr": title_fr, "en": title_en},
        "intro": {"fr": intro_fr, "en": intro_en},
        "items": items,
    }


def _visa_item(icon, title_fr, title_en, body_fr, body_en, *, tips=None):
    row = {
        "icon": icon,
        "title": {"fr": title_fr, "en": title_en},
        "body": {"fr": body_fr, "en": body_en},
    }
    if tips:
        row["tips"] = [{"fr": a, "en": b} for a, b in tips]
    return row


def _visa_faq(items):
    return [{"q": {"fr": qf, "en": qe}, "a": {"fr": af, "en": ae}} for qf, qe, af, ae in items]


_VISA_SECTIONS = [
    _visa_section(
        "passport",
        "Passeport & validité",
        "Passport & validity",
        "Votre passeport doit être valide au moins 6 mois après la date d'entrée prévue "
        "et comporter au moins 2 pages vierges.",
        "Your passport must be valid at least 6 months after your planned entry date "
        "and have at least 2 blank pages.",
        [
            _visa_item(
                "📘", "Validité 6 mois", "6-month validity",
                "Règle standard pour l'e-visa et l'entrée aux frontières aériennes, "
                "terrestres et maritimes.",
                "Standard rule for e-visa and entry at air, land and sea borders.",
            ),
            _visa_item(
                "👶", "Mineurs", "Minors",
                "Chaque enfant doit avoir son propre passeport (ou être inscrit sur "
                "un passeport parent selon les règles de votre pays).",
                "Each child needs their own passport (or be listed on a parent's "
                "passport per your country's rules).",
            ),
        ],
    ),
    _visa_section(
        "evisa",
        "E-visa officiel (evisa.gov.vn)",
        "Official e-visa (evisa.gov.vn)",
        "Depuis 2023, le Vietnam propose un e-visa unique valable 90 jours, entrées "
        "simples ou multiples, pour la plupart des nationalités non exemptées.",
        "Since 2023 Vietnam offers a single e-visa valid 90 days, single or multiple "
        "entry, for most non-exempt nationalities.",
        [
            _visa_item(
                "💵", "Frais & délai", "Fee & processing",
                "Environ 25 USD, paiement carte en ligne. Traitement souvent 3 à 5 "
                "jours ouvrés — demandez 7 à 10 jours avant le départ.",
                "About USD 25, card payment online. Processing often 3–5 business "
                "days — apply 7–10 days before departure.",
            ),
            _visa_item(
                "🖨️", "À l'arrivée", "On arrival",
                "Imprimez l'e-visa (ou gardez-le offline sur le téléphone) et présentez "
                "le même passeport que lors de la demande.",
                "Print the e-visa (or keep it offline on your phone) and present the "
                "same passport used in the application.",
            ),
        ],
    ),
    _visa_section(
        "exempt",
        "Exemptions sans visa (45 jours)",
        "Visa-free exemption (45 days)",
        "Depuis août 2023, de nombreuses nationalités (dont la France) bénéficient "
        "d'une exemption de 45 jours pour le tourisme — sans frais ni demande en ligne.",
        "Since August 2023 many nationalities (including France) get 45 days "
        "visa-free for tourism — no fee or online application.",
        [
            _visa_item(
                "🇫🇷", "Français & UE proches", "French & similar EU",
                "France, Allemagne, Italie, Espagne, Royaume-Uni, etc. : 45 jours "
                "maximum par entrée. Au-delà → e-visa obligatoire.",
                "France, Germany, Italy, Spain, UK, etc.: 45 days max per entry. "
                "Beyond that → e-visa required.",
            ),
            _visa_item(
                "🔄", "Re-entrées", "Re-entry",
                "L'exemption s'applique à chaque entrée ; un séjour de 46 jours "
                "nécessite un e-visa avant le départ.",
                "Exemption applies per entry; a 46-day stay requires an e-visa before "
                "you travel.",
            ),
        ],
    ),
    _visa_section(
        "tips",
        "Conseils pratiques",
        "Practical tips",
        "Évitez les sites « e-visa » non officiels qui surfacturent. Seul evisa.gov.vn "
        "est le portail gouvernemental.",
        "Avoid unofficial « e-visa » sites that overcharge. Only evisa.gov.vn is the "
        "government portal.",
        [
            _visa_item(
                "⚠️", "Arnaques en ligne", "Online scams",
                "Méfiez-vous des agences qui promettent un « visa express » hors "
                "du site officiel — arnaque fréquente.",
                "Beware agencies promising « express visa » outside the official "
                "site — a common scam.",
            ),
            _visa_item(
                "✈️", "Vol aller-retour", "Return ticket",
                "Les compagnies aériennes peuvent exiger un billet de sortie du "
                "Vietnam ; ayez une preuve de date de départ.",
                "Airlines may require proof of exit from Vietnam; have a return "
                "or onward ticket.",
            ),
        ],
    ),
]

_VISA_FAQ = _visa_faq([
    (
        "Les Français ont-ils besoin d'un visa pour 2 semaines ?",
        "Do French citizens need a visa for 2 weeks?",
        "Non pour un séjour touristique de 15 jours : exemption 45 jours. "
        "Au-delà de 45 jours, demandez un e-visa avant le départ.",
        "No for a 15-day tourist trip: 45-day exemption. Beyond 45 days, apply "
        "for an e-visa before you travel.",
    ),
    (
        "Combien coûte l'e-visa Vietnam ?",
        "How much does the Vietnam e-visa cost?",
        "Environ 25 USD sur evisa.gov.vn. Les sites tiers facturent souvent plus.",
        "About USD 25 on evisa.gov.vn. Third-party sites often charge more.",
    ),
    (
        "Peut-on prolonger un e-visa sur place ?",
        "Can you extend an e-visa in Vietnam?",
        "Les extensions sont limitées et soumises à l'administration locale — "
        "mieux vaut demander la bonne durée dès le départ (90 j max en e-visa).",
        "Extensions are limited and subject to local administration — better to "
        "apply for the right duration upfront (90 days max on e-visa).",
    ),
])


def _localize_visa_sections(sections, lang):
    out = []
    for sec in sections:
        items = []
        for it in sec["items"]:
            row = {
                "icon": it["icon"],
                "title": it["title"][lang],
                "body": it["body"][lang],
            }
            if it.get("tips"):
                row["tips"] = [t[lang] for t in it["tips"]]
            items.append(row)
        out.append({
            "key": sec["key"],
            "title": sec["title"][lang],
            "intro": sec["intro"][lang],
            "items": items,
        })
    return out


def build_visa(lang: str) -> dict:
    lang = "en" if lang == "en" else "fr"
    countries = [
        {"code": c["code"], "name": c[lang], "exempt_days": visa_exempt_days(c["code"])}
        for c in _VISA_COUNTRIES
    ]
    faq = [{"question": f["q"][lang], "answer": f["a"][lang]} for f in _VISA_FAQ]
    return {
        "countries": countries,
        "evisa_url": "https://evisa.gov.vn/",
        "evisa_max_days": 90,
        "sections": _localize_visa_sections(_VISA_SECTIONS, lang),
        "faq": faq,
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
