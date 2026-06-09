"""Piliers SEO (silos thématiques) — architecture en clusters autour du Vietnam.

Chaque « pilier » est une page-hub qui regroupe et relie un cluster d'articles/outils
existants (maillage interne descendant). Deux natures :

- kind="hub"  → page-hub dédiée servie par la route `pillar` sous /guide/<slug>.
- kind="page" → le pilier EXISTE déjà comme page autonome (outil), on la référence
                telle quelle pour éviter la cannibalisation (pas de nouvelle URL).

Le contenu est bilingue (fr/en) et auto-suffisant : la route le localise et résout
les liens via `lang_url`. Aucun import applicatif ici (lang_url est injecté).
"""

from __future__ import annotations

from typing import Any, Callable

# Ordre d'affichage des piliers thématiques (nav, homepage, sitemap).
THEMATIC_ORDER = [
    "preparer-son-voyage",
    "quand-partir",
    "budget",
    "transport",
    "itineraires",
    "gastronomie",
    "que-faire",
]


def _link(ep: str | None, label_fr: str, label_en: str,
          desc_fr: str = "", desc_en: str = "", **kw: Any) -> dict:
    """Lien de cluster. ep=None → élément « bientôt » (pas de lien, signal de couverture)."""
    item: dict[str, Any] = {
        "ep": ep,
        "label": {"fr": label_fr, "en": label_en},
        "desc": {"fr": desc_fr, "en": desc_en},
    }
    item.update(kw)  # slug / category éventuels
    return item


PILLARS: dict[str, dict] = {
    # ── 1. Préparer son voyage ────────────────────────────────────────────
    "preparer-son-voyage": {
        "kind": "hub",
        "slug": "preparer-son-voyage",
        "photo_id": "1557750255-c76072a7aad1",
        "eyebrow": {"fr": "Guide pilier", "en": "Pillar guide"},
        "title": {"fr": "Préparer son voyage au Vietnam",
                  "en": "Plan your trip to Vietnam"},
        "lede": {
            "fr": "Visa, budget, saison, eSIM, sécurité : tout ce qu'il faut régler "
                  "avant de partir, réuni et relié pour ne rien oublier.",
            "en": "Visa, budget, season, eSIM, safety: everything to sort out before "
                  "you go, gathered and cross-linked so nothing slips through.",
        },
        "meta_title": {"fr": "Préparer son voyage au Vietnam — checklist complète 2026",
                       "en": "Plan your Vietnam trip — complete 2026 checklist"},
        "meta_description": {
            "fr": "Le guide pour préparer votre voyage au Vietnam : visa, formalités, "
                  "budget, meilleure saison, eSIM et sécurité. Checklist pas à pas.",
            "en": "The hub to plan your Vietnam trip: visa, paperwork, budget, best "
                  "season, eSIM and safety. A step-by-step checklist.",
        },
        "clusters": [
            {"title": {"fr": "Formalités & entrée", "en": "Paperwork & entry"},
             "links": [
                 _link("visa_tool", "Visa Vietnam : conditions & e-visa",
                       "Vietnam visa: rules & e-visa",
                       "Qui a besoin d'un visa, durées et démarche e-visa.",
                       "Who needs a visa, durations and the e-visa process."),
                 _link("article", "Visa Vietnam : guide complet",
                       "Vietnam visa: full guide",
                       "Le pas-à-pas détaillé pour obtenir votre visa.",
                       "The detailed walk-through to get your visa.",
                       slug="visa-vietnam-guide-complet-francais"),
                 _link(None, "Passeport, douane & objets interdits",
                       "Passport, customs & restricted items"),
             ]},
            {"title": {"fr": "À régler avant de partir", "en": "Sort out before you go"},
             "links": [
                 _link("best_season", "Quand partir au Vietnam",
                       "Best time to visit Vietnam",
                       "Climat région par région pour choisir vos dates.",
                       "Region-by-region climate to choose your dates."),
                 _link("budget_tool", "Estimer son budget",
                       "Estimate your budget",
                       "Calculez un budget réaliste selon votre style.",
                       "Work out a realistic budget for your style."),
                 _link("essentials_tool", "eSIM & assurance voyage",
                       "eSIM & travel insurance",
                       "Rester connecté et couvert dès l'arrivée.",
                       "Stay connected and covered from day one."),
                 _link("article", "Carte SIM & eSIM au Vietnam",
                       "SIM & eSIM in Vietnam",
                       "Quelle option data choisir, et comment l'activer.",
                       "Which data option to pick, and how to activate it.",
                       slug="carte-sim-esim-vietnam"),
                 _link("useful_apps", "Applications indispensables",
                       "Essential apps",
                       "Grab, Maps, traduction, eSIM : se débrouiller sans arnaque.",
                       "Grab, Maps, translation, eSIM: get around scam-free."),
             ]},
            {"title": {"fr": "Sur place en toute sérénité", "en": "Stay safe on the ground"},
             "links": [
                 _link("article", "Sécurité au Vietnam : nos conseils",
                       "Safety in Vietnam: our advice",
                       "Arnaques courantes, santé, numéros utiles.",
                       "Common scams, health, useful numbers.",
                       slug="securite-voyage-vietnam-conseils"),
                 _link(None, "Santé, vaccins & trousse à pharmacie",
                       "Health, vaccines & first-aid kit"),
                 _link(None, "Argent, paiements & pourboires",
                       "Money, payments & tipping"),
             ]},
        ],
        "related_destinations": ["hanoi", "ho-chi-minh-city"],
        "related_pillars": ["transport", "itineraires", "budget"],
        "faq": [
            {"q": {"fr": "Faut-il un visa pour voyager au Vietnam ?",
                   "en": "Do I need a visa to travel to Vietnam?"},
             "a": {"fr": "La plupart des voyageurs français passent par l'e-visa en ligne. "
                         "Les conditions et la durée d'exemption évoluent : vérifiez dans "
                         "notre guide visa avant de réserver.",
                   "en": "Most travellers use the online e-visa. Conditions and exemption "
                         "lengths change, so check our visa guide before booking."}},
            {"q": {"fr": "Combien de temps avant le départ faut-il s'y prendre ?",
                   "en": "How far ahead should I prepare?"},
             "a": {"fr": "Comptez 4 à 8 semaines : visa, vols, première nuit d'hôtel et "
                         "eSIM. Les itinéraires et activités peuvent se caler plus tard.",
                   "en": "Allow 4–8 weeks for visa, flights, first hotel night and eSIM. "
                         "Itineraries and activities can be finalised later."}},
        ],
    },

    # ── 2. Quand partir (page existante) ──────────────────────────────────
    "quand-partir": {
        "kind": "page",
        "endpoint": "best_season",
        "photo_id": "1531737212413-667205e1cda7",
        "eyebrow": {"fr": "Pilier", "en": "Pillar"},
        "title": {"fr": "Quand partir au Vietnam", "en": "Best time to visit Vietnam"},
        "lede": {"fr": "Le climat varie fortement du Nord au Sud : trouvez la meilleure "
                       "période selon votre région et vos envies.",
                 "en": "Climate varies sharply north to south: find the best window for "
                       "your region and plans."},
    },

    # ── 3. Budget (page existante) ────────────────────────────────────────
    "budget": {
        "kind": "page",
        "endpoint": "budget_tool",
        "photo_id": "1526139334526-f591a54b477c",
        "eyebrow": {"fr": "Pilier", "en": "Pillar"},
        "title": {"fr": "Budget voyage Vietnam", "en": "Vietnam travel budget"},
        "lede": {"fr": "Estimez précisément le coût de votre séjour selon votre style, "
                       "la durée et le nombre de voyageurs.",
                 "en": "Estimate your trip cost precisely by style, length and party size."},
    },

    # ── 4. Transport ──────────────────────────────────────────────────────
    "transport": {
        "kind": "hub",
        "slug": "transport-au-vietnam",
        "photo_id": "1555921015-5532091f6026",
        "eyebrow": {"fr": "Guide pilier", "en": "Pillar guide"},
        "title": {"fr": "Se déplacer au Vietnam", "en": "Getting around Vietnam"},
        "lede": {
            "fr": "Train de la Réunification, bus de nuit, vols intérieurs, Grab ou "
                  "scooter : comment relier vos étapes simplement et sans surcoût.",
            "en": "Reunification train, night buses, domestic flights, Grab or scooter: "
                  "how to connect your stops simply and without overpaying.",
        },
        "meta_title": {"fr": "Transport au Vietnam : train, bus, avion & scooter (2026)",
                       "en": "Transport in Vietnam: train, bus, plane & scooter (2026)"},
        "meta_description": {
            "fr": "Comment se déplacer au Vietnam : train Nord-Sud, bus de nuit, vols "
                  "intérieurs, Grab, location de scooter. Conseils, prix et pièges.",
            "en": "How to get around Vietnam: north–south train, night buses, domestic "
                  "flights, Grab, scooter rental. Tips, prices and pitfalls.",
        },
        "clusters": [
            {"title": {"fr": "Longue distance", "en": "Long distance"},
             "links": [
                 _link("article", "Train, bus ou vol : comment choisir",
                       "Train, bus or flight: how to choose",
                       "Comparatif temps/prix/confort pour chaque trajet.",
                       "Time/price/comfort comparison for each leg.",
                       slug="transport-vietnam-train-bus-vol"),
                 _link(None, "Le train de la Réunification (Hanoï–Saïgon)",
                       "The Reunification Express (Hanoi–Saigon)"),
                 _link(None, "Vols intérieurs : compagnies & astuces",
                       "Domestic flights: airlines & tips"),
             ]},
            {"title": {"fr": "En ville & au quotidien", "en": "In town & day to day"},
             "links": [
                 _link(None, "Grab, taxis & applications utiles",
                       "Grab, taxis & useful apps"),
                 _link(None, "Louer un scooter : permis & sécurité",
                       "Renting a scooter: licence & safety"),
             ]},
            {"title": {"fr": "Relier vos étapes", "en": "Connect your stops"},
             "links": [
                 _link("prepare_trip", "Construire mon itinéraire",
                       "Build my itinerary",
                       "Notre planificateur enchaîne les étapes pour vous.",
                       "Our planner sequences the stops for you."),
                 _link("itinerary", "Exemple : le Vietnam en 10 jours",
                       "Example: Vietnam in 10 days",
                       "Un parcours Nord-Sud déjà optimisé pour les transports.",
                       "A north–south route already optimised for transport.",
                       slug="10-days-vietnam"),
             ]},
        ],
        "related_destinations": ["hanoi", "sapa", "halong"],
        "related_pillars": ["itineraires", "preparer-son-voyage"],
        "faq": [
            {"q": {"fr": "Faut-il un permis pour conduire un scooter au Vietnam ?",
                   "en": "Do I need a licence to ride a scooter in Vietnam?"},
             "a": {"fr": "En théorie un permis moto international est requis. Roulez "
                         "casqué, assuré, et privilégiez les petites villes pour débuter.",
                   "en": "An international motorcycle licence is technically required. "
                         "Always wear a helmet, stay insured, and start in smaller towns."}},
        ],
    },

    # ── 5. Itinéraires ────────────────────────────────────────────────────
    "itineraires": {
        "kind": "hub",
        "slug": "itineraires-vietnam",
        "photo_id": "1772867342647-6e6d87a0b014",
        "eyebrow": {"fr": "Guide pilier", "en": "Pillar guide"},
        "title": {"fr": "Itinéraires au Vietnam", "en": "Vietnam itineraries"},
        "lede": {
            "fr": "Du city-break à la grande traversée Nord-Sud : des parcours testés "
                  "par durée, et un planificateur pour composer le vôtre.",
            "en": "From a city break to the full north–south crossing: road-tested "
                  "routes by length, plus a planner to build your own.",
        },
        "meta_title": {"fr": "Itinéraires Vietnam : 3, 7, 10 jours et plus",
                       "en": "Vietnam itineraries: 3, 7, 10 days and more"},
        "meta_description": {
            "fr": "Itinéraires au Vietnam par durée (3, 7, 10 jours), conseils Nord/Centre/"
                  "Sud et planificateur sur mesure pour composer votre voyage.",
            "en": "Vietnam itineraries by length (3, 7, 10 days), north/centre/south tips "
                  "and a tailored planner to build your trip.",
        },
        "clusters": [
            {"title": {"fr": "Par durée", "en": "By length"},
             "links": [
                 _link("itinerary", "Le Vietnam en 3 jours", "Vietnam in 3 days",
                       "Un city-break efficace pour une courte escale.",
                       "An efficient city break for a short stopover.",
                       slug="3-days-vietnam"),
                 _link("itinerary", "Le Vietnam en 7 jours", "Vietnam in 7 days",
                       "L'essentiel Nord ou Centre en une semaine.",
                       "The north or centre essentials in a week.",
                       slug="7-days-vietnam"),
                 _link("itinerary", "Le Vietnam en 10 jours", "Vietnam in 10 days",
                       "La traversée Nord-Sud la plus demandée.",
                       "The most popular north–south crossing.",
                       slug="10-days-vietnam"),
                 _link(None, "Le Vietnam en 15 jours et plus",
                       "Vietnam in 15 days and more"),
             ]},
            {"title": {"fr": "Composer le vôtre", "en": "Build your own"},
             "links": [
                 _link("prepare_trip", "Planificateur de voyage",
                       "Trip planner",
                       "4 questions, un itinéraire et des guides sur mesure.",
                       "4 questions, a tailored itinerary and guides."),
                 _link("article", "Hanoï en 7 jours pour débuter",
                       "Hanoi in 7 days for first-timers",
                       "Un exemple d'itinéraire pas à pas autour de Hanoï.",
                       "A step-by-step example itinerary around Hanoi.",
                       slug="decouvrez-hanoi-en-7-jours-itineraire-ideal-pour-les-debutants-au-vietnam"),
             ]},
        ],
        "related_destinations": ["hanoi", "halong", "hoi-an", "sapa"],
        "related_pillars": ["transport", "que-faire"],
        "faq": [
            {"q": {"fr": "Combien de jours faut-il pour visiter le Vietnam ?",
                   "en": "How many days do I need for Vietnam?"},
             "a": {"fr": "7 jours suffisent pour une région, 10 à 14 pour relier le Nord "
                         "et le Centre, 3 semaines pour toute la traversée Nord-Sud.",
                   "en": "7 days cover one region, 10–14 link the north and centre, and "
                         "3 weeks allow the full north–south crossing."}},
        ],
    },

    # ── 6. Gastronomie ────────────────────────────────────────────────────
    "gastronomie": {
        "kind": "hub",
        "slug": "gastronomie-vietnamienne",
        "photo_id": "1521993117367-b7f70ccd029d",
        "eyebrow": {"fr": "Guide pilier", "en": "Pillar guide"},
        "title": {"fr": "Cuisine & gastronomie du Vietnam", "en": "Vietnamese food & cuisine"},
        "lede": {
            "fr": "Phở, bánh mì, café à l'œuf : où, quoi et comment manger région par "
                  "région, des stands de rue aux tables incontournables.",
            "en": "Phở, bánh mì, egg coffee: where, what and how to eat region by region, "
                  "from street stalls to must-try tables.",
        },
        "meta_title": {"fr": "Cuisine vietnamienne : plats, street food & adresses",
                       "en": "Vietnamese cuisine: dishes, street food & spots"},
        "meta_description": {
            "fr": "Guide de la cuisine vietnamienne : plats incontournables, street food "
                  "sans risque et meilleures adresses ville par ville.",
            "en": "A guide to Vietnamese cuisine: must-try dishes, safe street food and "
                  "the best spots city by city.",
        },
        "clusters": [
            {"title": {"fr": "Les incontournables", "en": "The must-tries"},
             "links": [
                 _link("article", "Meilleurs restaurants de Hanoï",
                       "Best restaurants in Hanoi",
                       "Nos adresses testées dans la capitale.",
                       "Our tried-and-tested spots in the capital.",
                       slug="meilleurs-restaurants-hanoi"),
                 _link(None, "Phở, bún chả & plats à goûter absolument",
                       "Phở, bún chả & dishes you must try"),
                 _link(None, "Café vietnamien : à l'œuf, à la noix de coco…",
                       "Vietnamese coffee: egg, coconut and more"),
             ]},
            {"title": {"fr": "Manger par ville", "en": "Eat city by city"},
             "links": [
                 _link("destination_page", "Saveurs de Hanoï", "Flavours of Hanoi",
                       "La street food du vieux quartier.",
                       "The old quarter's street food.", slug="hanoi"),
                 _link("destination_page", "Hội An gourmand", "Tasty Hội An",
                       "Cao lầu, white rose et marchés.",
                       "Cao lầu, white rose and markets.", slug="hoi-an"),
                 _link("destination_page", "Saïgon street food",
                       "Saigon street food",
                       "Le Sud, ses bánh mì et ses marchés de nuit.",
                       "The south, its bánh mì and night markets.",
                       slug="ho-chi-minh-city"),
             ]},
        ],
        "related_destinations": ["hanoi", "hoi-an", "ho-chi-minh-city"],
        "related_pillars": ["que-faire", "preparer-son-voyage"],
        "faq": [
            {"q": {"fr": "La street food au Vietnam est-elle sans danger ?",
                   "en": "Is street food in Vietnam safe?"},
             "a": {"fr": "Oui si vous choisissez les stands fréquentés où la nourriture "
                         "est cuite minute. Évitez les plats tièdes laissés à l'air libre.",
                   "en": "Yes, if you pick busy stalls where food is cooked to order. "
                         "Avoid lukewarm dishes left out in the open."}},
        ],
    },

    # ── 7. Que faire / Expériences ────────────────────────────────────────
    "que-faire": {
        "kind": "hub",
        "slug": "que-faire-au-vietnam",
        "photo_id": "1602646993875-70bc0ba52c87",
        "eyebrow": {"fr": "Guide pilier", "en": "Pillar guide"},
        "title": {"fr": "Que faire au Vietnam", "en": "What to do in Vietnam"},
        "lede": {
            "fr": "Croisière dans la baie d'Halong, trek à Sapa, patrimoine de Hué, "
                  "plages de Phu Quoc : les expériences à ne pas manquer, par envie.",
            "en": "Halong Bay cruise, Sapa trek, Hué heritage, Phu Quoc beaches: the "
                  "experiences not to miss, sorted by mood.",
        },
        "meta_title": {"fr": "Que faire au Vietnam : nature, culture & plages",
                       "en": "What to do in Vietnam: nature, culture & beaches"},
        "meta_description": {
            "fr": "Les meilleures expériences au Vietnam : baie d'Halong, trek de Sapa, "
                  "delta du Mékong, patrimoine de Hué et plages de Phu Quoc.",
            "en": "The best experiences in Vietnam: Halong Bay, Sapa trekking, Mekong "
                  "Delta, Hué heritage and Phu Quoc beaches.",
        },
        "clusters": [
            {"title": {"fr": "Nature & aventure", "en": "Nature & adventure"},
             "links": [
                 _link("destination_page", "Croisière dans la baie d'Halong",
                       "Cruise Halong Bay",
                       "Karsts, kayak et nuit à bord.",
                       "Karsts, kayaking and a night aboard.", slug="halong"),
                 _link("destination_page", "Trek dans les rizières de Sapa",
                       "Trek the Sapa rice terraces",
                       "Randonnée et villages ethniques du Nord.",
                       "Hiking and ethnic villages in the north.", slug="sapa"),
                 _link("destination_page", "Delta du Mékong",
                       "Mekong Delta",
                       "Marchés flottants et bras de rivière.",
                       "Floating markets and river channels.",
                       slug="delta-du-mekong"),
             ]},
            {"title": {"fr": "Culture & patrimoine", "en": "Culture & heritage"},
             "links": [
                 _link("destination_page", "Hội An, lanternes & vieille ville",
                       "Hội An, lanterns & old town",
                       "Le joyau classé du Centre.",
                       "The listed gem of central Vietnam.", slug="hoi-an"),
                 _link("destination_page", "Hué impériale",
                       "Imperial Hué",
                       "Citadelle, tombeaux et rivière des Parfums.",
                       "Citadel, tombs and the Perfume River.", slug="hue"),
             ]},
            {"title": {"fr": "Détente & plages", "en": "Relax & beaches"},
             "links": [
                 _link("destination_page", "Phu Quoc, l'île plage",
                       "Phu Quoc, the beach island",
                       "Sable blanc et couchers de soleil.",
                       "White sand and sunsets.", slug="phu-quoc"),
                 _link("destination_page", "Đà Nẵng & ses plages",
                       "Đà Nẵng & its beaches",
                       "Ville balnéaire entre Hội An et Hué.",
                       "A seaside city between Hội An and Hué.", slug="da-nang"),
             ]},
        ],
        "related_destinations": ["halong", "sapa", "hoi-an", "phu-quoc"],
        "related_pillars": ["itineraires", "gastronomie"],
        "faq": [
            {"q": {"fr": "Quelle est l'expérience à ne pas manquer au Vietnam ?",
                   "en": "What is the one experience not to miss in Vietnam?"},
             "a": {"fr": "Une nuit en croisière dans la baie d'Halong reste l'incontournable, "
                         "idéalement combinée à un trek à Sapa pour varier les paysages.",
                   "en": "A night cruising Halong Bay is the classic, ideally paired with a "
                         "Sapa trek for contrasting scenery."}},
        ],
    },
}


def _pick(value: Any, lang: str) -> Any:
    if isinstance(value, dict) and ("fr" in value or "en" in value):
        return value.get(lang, value.get("fr", ""))
    return value


def hub_by_slug(slug: str) -> tuple[str, dict] | None:
    """Retourne (clé, données brutes) du pilier-hub correspondant au slug, ou None."""
    for key, raw in PILLARS.items():
        if raw.get("kind") == "hub" and raw.get("slug") == slug:
            return key, raw
    return None


def hub_slugs() -> list[str]:
    """Slugs des piliers-hub (pour le sitemap)."""
    return [raw["slug"] for raw in PILLARS.values() if raw.get("kind") == "hub"]


def pillar_url(raw: dict, lang: str, lang_url: Callable[..., str]) -> str:
    """URL publique d'un pilier (hub → /guide/<slug> ; page → endpoint existant)."""
    if raw.get("kind") == "hub":
        return lang_url("pillar", lang, slug=raw["slug"])
    return lang_url(raw["endpoint"], lang)


def localize_link(link: dict, lang: str, lang_url: Callable[..., str]) -> dict:
    out = {"label": _pick(link["label"], lang), "desc": _pick(link.get("desc", {}), lang)}
    if not link.get("ep"):
        return {**out, "url": None, "soon": True}
    kw = {k: link[k] for k in ("slug", "category") if k in link}
    return {**out, "url": lang_url(link["ep"], lang, **kw), "soon": False}


def localize_hub(key: str, raw: dict, lang: str, lang_url: Callable[..., str]) -> dict:
    """Vue prête pour le template : textes localisés + URLs résolues."""
    clusters = [
        {"title": _pick(c["title"], lang),
         "links": [localize_link(l, lang, lang_url) for l in c["links"]]}
        for c in raw.get("clusters", [])
    ]
    related = []
    for rk in raw.get("related_pillars", []):
        rp = PILLARS.get(rk)
        if rp:
            related.append({"title": _pick(rp["title"], lang),
                            "url": pillar_url(rp, lang, lang_url)})
    faq = [{"question": _pick(f["q"], lang), "answer": _pick(f["a"], lang)}
           for f in raw.get("faq", [])]
    return {
        "key": key,
        "slug": raw["slug"],
        "photo_id": raw["photo_id"],
        "eyebrow": _pick(raw["eyebrow"], lang),
        "title": _pick(raw["title"], lang),
        "lede": _pick(raw["lede"], lang),
        "meta_title": _pick(raw.get("meta_title", raw["title"]), lang),
        "meta_description": _pick(raw.get("meta_description", raw["lede"]), lang),
        "clusters": clusters,
        "related_pillars": related,
        "related_destinations": raw.get("related_destinations", []),
        "faq": faq,
    }


def find_pillars_for(ep: str, slug: str | None,
                     lang: str, lang_url: Callable[..., str]) -> list[dict]:
    """Piliers-hub qui référencent ce contenu (maillage RETOUR : contenu → pilier).

    Inverse les clusters : permet à une page article/destination/outil d'afficher un
    lien remontant vers le(s) pilier(s) de son silo, ce qui « ferme » le silo SEO.
    """
    out: list[dict] = []
    for raw in PILLARS.values():
        if raw.get("kind") != "hub":
            continue
        for cluster in raw.get("clusters", []):
            if any(l.get("ep") == ep and l.get("slug") == slug for l in cluster["links"]):
                out.append({"title": _pick(raw["title"], lang),
                            "url": pillar_url(raw, lang, lang_url)})
                break
    return out


def thematic_list(lang: str, lang_url: Callable[..., str]) -> list[dict]:
    """Liste légère des piliers thématiques (nav / homepage / maillage)."""
    items = []
    for key in THEMATIC_ORDER:
        raw = PILLARS.get(key)
        if not raw:
            continue
        items.append({
            "key": key,
            "title": _pick(raw["title"], lang),
            "lede": _pick(raw["lede"], lang),
            "url": pillar_url(raw, lang, lang_url),
            "photo_id": raw["photo_id"],
            "is_hub": raw.get("kind") == "hub",
        })
    return items
