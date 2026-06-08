"""Ready-made travel itineraries."""

from copy import deepcopy

from data.itineraries_i18n import ITINERARIES_EN


def _build_itineraries() -> dict:
    base = {
    "3-days-vietnam": {
        "slug": "3-days-vietnam",
        "title": "Itinéraire 3 jours au Vietnam",
        "meta_title": "Itinéraire 3 jours Vietnam — Mini-city break Hanoï ou Saigon",
        "meta_description": (
            "Que faire 3 jours au Vietnam ? Itinéraire express Hanoï ou Ho Chi Minh-Ville "
            "avec hôtels, activités et budget."
        ),
        "duration": 3,
        "summary": "Parfait pour un premier aperçu — choisissez Hanoï (nord) ou Saigon (sud).",
        "budget_hint": "150–350 € tout compris (hors vol)",
        "location_key": "hanoi",
        "sample_hotel": {
            "name": "Hanoi La Siesta Premium",
            "search": "Hanoi La Siesta Premium Hang Be",
            "desc": "Boutique-hôtel Vieux Quartier — idéal pour un city break à Hanoï.",
            "price_hint": "dès 45 €/nuit",
            "provider": "booking",
        },
        "sample_activity": {
            "name": "Food tour matinal",
            "search": "Hanoi street food walking tour morning",
            "desc": "Découverte guidée des spécialités hanoïennes.",
            "price_hint": "dès 35 €",
            "provider": "getyourguide",
        },
        "days": [
            {
                "day": 1,
                "title": "Arrivée & centre historique",
                "location": "Hanoï ou HCMC",
                "activities": [
                    "Check-in et première balade (Vieux Quartier ou District 1)",
                    "Street food du midi — phở ou cơm tấm",
                    "Temple / musée emblématique l'après-midi",
                    "Dîner local + première bière bia hơi ou rooftop",
                ],
                "stay": "Hôtel centre-ville (voir recommandations)",
            },
            {
                "day": 2,
                "title": "Immersion culture & food",
                "location": "Hanoï ou HCMC",
                "activities": [
                    "Food tour matinal (recommandé)",
                    "Musée ou quartier secondaire (Ethnographie / War Museum)",
                    "Shopping artisanat ou marché local",
                    "Spectacle ou balade nocturne",
                ],
                "stay": "Même hôtel",
            },
            {
                "day": 3,
                "title": "Excursion & départ",
                "location": "Environs",
                "activities": [
                    "Demi-journée excursion (Halong si Hanoï, Củ Chi si HCMC)",
                    "Déjeuner vue mer ou campagne",
                    "Retour aéroport — prévoir 3h avant le vol",
                ],
                "stay": "—",
            },
        ],
    },
    "7-days-vietnam": {
        "slug": "7-days-vietnam",
        "title": "Itinéraire 7 jours au Vietnam",
        "meta_title": "Itinéraire 7 jours Vietnam — Nord + Centre en une semaine",
        "meta_description": (
            "Circuit 7 jours Vietnam : Hanoï, baie d'Halong, Hội An. Plan jour par jour "
            "avec vols intérieurs et budget."
        ),
        "duration": 7,
        "summary": "Hanoï → Halong → Hội An — le combo nord-centre le plus populaire.",
        "budget_hint": "450–800 € (hors vol international)",
        "location_key": "hanoi",
        "sample_hotel": {
            "name": "Hanoi Old Quarter Hotel",
            "search": "Hanoi Old Quarter hotel Hoan Kiem",
            "desc": "Base à Hanoï pour les 2 premières nuits du circuit.",
            "price_hint": "dès 40 €/nuit",
            "provider": "booking",
        },
        "sample_activity": {
            "name": "Croisière Halong 2J/1N",
            "search": "Halong Bay cruise 2 days 1 night from Hanoi",
            "desc": "Incontournable du circuit — transport depuis Hanoï inclus.",
            "price_hint": "dès 89 €",
            "provider": "viator",
        },
        "activity_location_key": "hanoi",
        "days": [
            {"day": 1, "title": "Hanoï — Vieux Quartier", "location": "Hanoï", "activities": ["Arrivée, balade lac Hoàn Kiếm", "Phở matinal jour 2", "Dîner street food"], "stay": "Vieux Quartier"},
            {"day": 2, "title": "Hanoï — Culture", "location": "Hanoï", "activities": ["Temple Littérature", "Musée Ethnographie", "Train street"], "stay": "Vieux Quartier"},
            {"day": 3, "title": "Baie d'Halong", "location": "Halong", "activities": ["Transfert 3h", "Croisière départ midi", "Kayak & grottes"], "stay": "Bateau croisière"},
            {"day": 4, "title": "Halong → Hội An", "location": "Transit", "activities": ["Lever soleil sur la baie", "Vol Hanoï → Đà Nẵng", "Transfert Hội An"], "stay": "Hội An"},
            {"day": 5, "title": "Hội An — Vieille ville", "location": "Hội An", "activities": ["Pont japonais & temples", "Cours cuisine", "Lanternes le soir"], "stay": "Hội An"},
            {"day": 6, "title": "Hội An — Plage & vélo", "location": "Hội An", "activities": ["Vélo An Bàng", "Tailleur ou spa", "Marché nocturne"], "stay": "Hội An"},
            {"day": 7, "title": "Départ", "location": "Đà Nẵng", "activities": ["Petit-déjeuner local", "Vol retour depuis Đà Nẵng"], "stay": "—"},
        ],
    },
    "10-days-vietnam": {
        "slug": "10-days-vietnam",
        "title": "Itinéraire 10 jours au Vietnam",
        "meta_title": "Itinéraire 10 jours Vietnam — Nord, Centre et Sud complet",
        "meta_description": (
            "Voyage 10 jours Vietnam : Hanoï, Halong, Hội An, Ho Chi Minh-Ville. "
            "Itinéraire détaillé jour par jour avec conseils transport."
        ),
        "duration": 10,
        "summary": "Le grand classique nord → centre → sud en 10 jours.",
        "budget_hint": "700–1 200 € (hors vol international)",
        "location_key": "hanoi",
        "sample_hotel": {
            "name": "Liberty Central Saigon Citypoint",
            "search": "Liberty Central Saigon Citypoint District 1",
            "desc": "Hôtel central pour les nuits à Ho Chi Minh-Ville.",
            "price_hint": "dès 55 €/nuit",
            "provider": "booking",
        },
        "sample_activity": {
            "name": "Excursion Delta du Mékong",
            "search": "Mekong Delta full day tour from Ho Chi Minh",
            "desc": "Journée canaux, marchés flottants et villages.",
            "price_hint": "dès 35 €",
            "provider": "viator",
        },
        "activity_location_key": "ho-chi-minh-city",
        "days": [
            {"day": 1, "title": "Hanoï", "location": "Hanoï", "activities": ["Arrivée & Vieux Quartier"], "stay": "Hanoï"},
            {"day": 2, "title": "Hanoï approfondi", "location": "Hanoï", "activities": ["Food tour", "Temple Littérature"], "stay": "Hanoï"},
            {"day": 3, "title": "Halong 2J/1N", "location": "Halong", "activities": ["Croisière départ", "Kayak"], "stay": "Bateau"},
            {"day": 4, "title": "Halong → Hội An", "location": "Transit", "activities": ["Vol vers Đà Nẵng", "Installation Hội An"], "stay": "Hội An"},
            {"day": 5, "title": "Hội An", "location": "Hội An", "activities": ["Vieille ville", "Cuisine"], "stay": "Hội An"},
            {"day": 6, "title": "Hội An / My Sơn", "location": "Hội An", "activities": ["Excursion My Sơn ou plage"], "stay": "Hội An"},
            {"day": 7, "title": "Vol vers HCMC", "location": "Ho Chi Minh-Ville", "activities": ["Vol Đà Nẵng → SGN", "District 1"], "stay": "HCMC"},
            {"day": 8, "title": "Ho Chi Minh-Ville", "location": "HCMC", "activities": ["War Museum", "Marché Bến Thành"], "stay": "HCMC"},
            {"day": 9, "title": "Delta Mékong", "location": "Mékong", "activities": ["Excursion 1 jour canaux & marchés"], "stay": "HCMC"},
            {"day": 10, "title": "Départ", "location": "HCMC", "activities": ["Shopping dernier moment", "Vol retour"], "stay": "—"},
        ],
    },
    }
    for slug, itin in base.items():
        fr_block = {
            k: itin[k]
            for k in (
                "title", "meta_title", "meta_description", "summary", "budget_hint",
                "sample_hotel", "sample_activity", "days",
            )
            if k in itin
        }
        en_overlay = ITINERARIES_EN.get(slug, {})
        en_block = deepcopy(fr_block)
        for key, val in en_overlay.items():
            if isinstance(val, dict) and key in en_block and isinstance(en_block[key], dict):
                en_block[key] = {**en_block[key], **val}
            else:
                en_block[key] = val
        itin["i18n"] = {"fr": fr_block, "en": en_block}
    return base


ITINERARIES = _build_itineraries()
