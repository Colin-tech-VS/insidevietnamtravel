"""Applications utiles pour voyager au Vietnam — page guide anti-arnaque, SEO.

Données bilingues (fr/en). Chaque app : nom, accroche, « pourquoi » (souvent un angle
anti-arnaque : prix affiché, vrai taux de change, communication…), lien et badge.

Liens : `url` = lien externe direct ; `affiliate` = token résolu côté template via les
helpers d'affiliation existants (eSIM Airalo/Holafly), pour conserver le tracking.
"""

from __future__ import annotations

from typing import Any


def _app(name: str, icon: str, tagline_fr: str, tagline_en: str,
         why_fr: str, why_en: str, *, url: str | None = None,
         affiliate: str | None = None, badge: str = "free") -> dict:
    return {
        "name": name,
        "icon": icon,
        "tagline": {"fr": tagline_fr, "en": tagline_en},
        "why": {"fr": why_fr, "en": why_en},
        "url": url,
        "affiliate": affiliate,
        "badge": badge,  # free | affiliate | essential
    }


# Catégories ordonnées (clé, titre fr/en, intro fr/en, apps)
APP_CATEGORIES: list[dict] = [
    {
        "key": "transport",
        "title": {"fr": "Se déplacer (sans arnaque au taxi)",
                  "en": "Getting around (no taxi scams)"},
        "intro": {
            "fr": "Le réflexe n°1 anti-arnaque : commander une course avec le prix affiché "
                  "AVANT de monter. Fini la négociation et le compteur trafiqué.",
            "en": "The #1 anti-scam habit: book a ride with the price shown BEFORE you get "
                  "in. No more haggling or rigged meters.",
        },
        "apps": [
            _app("Grab", "🚗",
                 "VTC, taxi, moto-taxi et livraison — prix fixe affiché.",
                 "Ride-hailing, taxi, motorbike and delivery — fixed price shown.",
                 "Le prix est affiché et payé dans l'app : impossible de gonfler la course. "
                 "L'app incontournable au Vietnam.",
                 "The price is shown and paid in-app: the fare can't be inflated. The "
                 "must-have app in Vietnam.",
                 url="https://www.grab.com/vn/en/", badge="essential"),
            _app("Xanh SM", "🟢",
                 "Taxis et motos 100 % électriques, prix au compteur honnête.",
                 "All-electric taxis and bikes with an honest meter.",
                 "Alternative locale fiable à Grab, voitures récentes et tarifs clairs.",
                 "A reliable local alternative to Grab, with newer cars and clear fares.",
                 url="https://www.xanhsm.com/", badge="free"),
            _app("Be", "🅱️",
                 "Appli VTC vietnamienne, utile en complément de Grab.",
                 "Vietnamese ride-hailing app, handy alongside Grab.",
                 "Comparez les prix entre Be et Grab pour payer le juste tarif.",
                 "Compare prices between Be and Grab to pay the fair rate.",
                 url="https://be.com.vn/", badge="free"),
            _app("Google Maps", "🗺️",
                 "Itinéraires, horaires de bus et cartes téléchargeables hors-ligne.",
                 "Directions, bus times and downloadable offline maps.",
                 "Téléchargez la carte de chaque ville AVANT d'y aller : vous gardez le "
                 "nord même sans réseau et évitez les détours « touristiques ».",
                 "Download each city's map BEFORE you go: you stay oriented offline and "
                 "avoid the scenic-route detour.",
                 url="https://www.google.com/maps", badge="essential"),
        ],
    },
    {
        "key": "money",
        "title": {"fr": "Argent & change (connaître le vrai taux)",
                  "en": "Money & exchange (know the real rate)"},
        "intro": {
            "fr": "Le đồng a beaucoup de zéros : une app de conversion évite les erreurs et "
                  "les « arrondis » à votre désavantage.",
            "en": "The đồng has a lot of zeros: a converter avoids mistakes and "
                  "“rounding” that never favours you.",
        },
        "apps": [
            _app("XE Currency", "💱",
                 "Taux de change officiel, fonctionne hors-ligne.",
                 "Official exchange rate, works offline.",
                 "Vérifiez en 2 s si un prix ou un bureau de change est correct.",
                 "Check in 2 seconds whether a price or exchange counter is fair.",
                 url="https://www.xe.com/apps/", badge="free"),
            _app("Wise", "💳",
                 "Carte et retraits au taux réel, frais transparents.",
                 "Card and withdrawals at the real rate, transparent fees.",
                 "Évite les frais cachés des banques et les DAB qui « proposent » un "
                 "taux maison. Retirez en VND, refusez la conversion proposée à l'écran.",
                 "Avoids hidden bank fees and ATMs pushing their own rate. Withdraw in "
                 "VND and decline the on-screen conversion.",
                 url="https://wise.com/", badge="free"),
        ],
    },
    {
        "key": "language",
        "title": {"fr": "Communiquer & comprendre",
                  "en": "Communicate & understand"},
        "intro": {
            "fr": "Peu de Vietnamiens parlent anglais hors des zones touristiques : pouvoir "
                  "traduire vous rend autonome et plus difficile à arnaquer.",
            "en": "Few Vietnamese speak English outside tourist areas: being able to "
                  "translate makes you self-reliant and harder to scam.",
        },
        "apps": [
            _app("Google Translate", "🈯",
                 "Traduction texte, voix et PHOTO (menus, panneaux) hors-ligne.",
                 "Text, voice and PHOTO translation (menus, signs) offline.",
                 "Téléchargez le pack vietnamien : traduisez un menu en le photographiant, "
                 "négociez clairement, lisez les panneaux.",
                 "Download the Vietnamese pack: translate a menu by photographing it, "
                 "negotiate clearly, read signs.",
                 url="https://translate.google.com/", badge="essential"),
            _app("Zalo", "💬",
                 "La messagerie n°1 au Vietnam — hôtels, guides et chauffeurs l'utilisent.",
                 "Vietnam's #1 messaging app — hotels, guides and drivers use it.",
                 "Beaucoup de prestataires confirment et envoient un point GPS via Zalo "
                 "plutôt que par email. Pratique pour garder une trace écrite.",
                 "Many providers confirm and share a GPS pin over Zalo rather than email. "
                 "Handy to keep a written record.",
                 url="https://zalo.me/", badge="free"),
        ],
    },
    {
        "key": "connectivity",
        "title": {"fr": "Rester connecté (eSIM)",
                  "en": "Stay connected (eSIM)"},
        "intro": {
            "fr": "Toutes les apps ci-dessus supposent d'avoir Internet à l'arrivée. Une "
                  "eSIM s'active avant le départ : data dès l'atterrissage, sans chercher "
                  "une boutique ni risquer une carte SIM hors de prix à l'aéroport.",
            "en": "All the apps above assume you have internet on arrival. An eSIM "
                  "activates before departure: data the moment you land, with no shop "
                  "hunting and no overpriced airport SIM.",
        },
        "apps": [
            _app("Airalo", "📶",
                 "eSIM data au Vietnam, installation en 2 minutes.",
                 "Vietnam data eSIM, set up in 2 minutes.",
                 "Forfaits clairs au prix affiché, sans engagement ni dépôt de garantie.",
                 "Clear plans at the price shown, no contract or deposit.",
                 affiliate="airalo", badge="affiliate"),
            _app("Holafly", "♾️",
                 "eSIM data illimitée, idéale pour les gros consommateurs.",
                 "Unlimited-data eSIM, ideal for heavy users.",
                 "Data illimitée à prix fixe : aucune mauvaise surprise sur la facture.",
                 "Unlimited data at a fixed price: no bill-shock.",
                 affiliate="holafly", badge="affiliate"),
        ],
    },
    {
        "key": "book",
        "title": {"fr": "Réserver au juste prix",
                  "en": "Book at the fair price"},
        "intro": {
            "fr": "Réserver hébergements et activités via une plateforme = prix affiché, "
                  "avis vérifiés et annulation claire, plutôt qu'un rabatteur dans la rue.",
            "en": "Booking stays and activities through a platform means a shown price, "
                  "verified reviews and clear cancellation — not a street tout.",
        },
        "apps": [
            _app("Booking.com", "🏨",
                 "Hôtels et guesthouses, annulation gratuite fréquente.",
                 "Hotels and guesthouses, free cancellation often available.",
                 "Prix et conditions transparents ; lisez les avis récents avant de payer.",
                 "Transparent price and terms; read recent reviews before paying.",
                 url="https://www.booking.com/", badge="free"),
            _app("Klook", "🎟️",
                 "Activités, transferts et billets à prix affiché.",
                 "Activities, transfers and tickets at a shown price.",
                 "Évite l'achat de billets « gonflés » sur place : croisière baie d'Halong, "
                 "bus, entrées… réservés au tarif réel.",
                 "Avoids inflated on-site tickets: Halong cruises, buses, entries… booked "
                 "at the real price.",
                 url="https://www.klook.com/", badge="free"),
        ],
    },
]


def app_categories(lang: str) -> list[dict]:
    """Vue localisée pour le template (textes fr/en aplatis)."""
    def pick(v: Any) -> Any:
        return v.get(lang, v.get("fr")) if isinstance(v, dict) else v

    out = []
    for cat in APP_CATEGORIES:
        out.append({
            "key": cat["key"],
            "title": pick(cat["title"]),
            "intro": pick(cat["intro"]),
            "apps": [
                {
                    "name": a["name"],
                    "icon": a["icon"],
                    "tagline": pick(a["tagline"]),
                    "why": pick(a["why"]),
                    "url": a["url"],
                    "affiliate": a["affiliate"],
                    "badge": a["badge"],
                }
                for a in cat["apps"]
            ],
        })
    return out


APP_FAQ: list[dict] = [
    {"q": {"fr": "Grab fonctionne-t-il partout au Vietnam ?",
           "en": "Does Grab work everywhere in Vietnam?"},
     "a": {"fr": "Grab couvre toutes les grandes villes (Hanoï, Hô Chi Minh, Da Nang, "
                 "Hoi An…) pour les voitures et motos-taxis. Dans les zones rurales, "
                 "l'offre est plus limitée : prévoyez Xanh SM ou un taxi compteur.",
           "en": "Grab covers all major cities (Hanoi, Ho Chi Minh City, Da Nang, Hoi "
                 "An…) for cars and motorbike taxis. In rural areas coverage is thinner: "
                 "consider Xanh SM or a metered taxi."}},
    {"q": {"fr": "Quelle application pour éviter les arnaques de taxi ?",
           "en": "Which app helps avoid taxi scams?"},
     "a": {"fr": "Grab ou Xanh SM : le prix est affiché et payé dans l'application, donc "
                 "impossible de gonfler la course ou de « trafiquer » le compteur.",
           "en": "Grab or Xanh SM: the price is shown and paid in-app, so the fare can't "
                 "be inflated or the meter rigged."}},
    {"q": {"fr": "Faut-il une eSIM ou une carte SIM locale ?",
           "en": "Do I need an eSIM or a local SIM?"},
     "a": {"fr": "Une eSIM (Airalo, Holafly) s'active avant le départ et vous donne du "
                 "réseau dès l'atterrissage — pratique pour Grab et Maps tout de suite. "
                 "Une SIM locale peut être moins chère mais oblige à trouver une boutique "
                 "fiable à l'arrivée.",
           "en": "An eSIM (Airalo, Holafly) activates before departure and gives you data "
                 "the moment you land — handy for Grab and Maps right away. A local SIM "
                 "can be cheaper but means finding a trustworthy shop on arrival."}},
]


def app_faq(lang: str) -> list[dict]:
    def pick(v):
        return v.get(lang, v.get("fr"))
    return [{"question": pick(f["q"]), "answer": pick(f["a"])} for f in APP_FAQ]


def all_app_names() -> list[str]:
    return [a["name"] for cat in APP_CATEGORIES for a in cat["apps"]]
