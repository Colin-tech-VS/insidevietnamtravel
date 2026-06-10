"""Itinéraire 10 jours — contenu détaillé FR (nord → centre → sud)."""

ITINERARY_10_DAYS_FR = {
    "slug": "10-days-vietnam",
    "title": "Itinéraire 10 jours au Vietnam",
    "meta_title": "Itinéraire 10 jours Vietnam — Hanoï, Halong, Hội An, Saigon jour par jour",
    "meta_description": (
        "Circuit 10 jours Vietnam complet : Hanoï, baie d'Halong, Hội An UNESCO, Ho Chi Minh-Ville "
        "et delta du Mékong. Programme détaillé, transport, hôtels et activités."
    ),
    "duration": 10,
    "summary": "Le grand classique nord → centre → sud en 10 jours.",
    "overview": (
        "<p>Dix jours pour enchaîner les <strong>trois régions</strong> du Vietnam sans précipitation : "
        "Hanoï et Halong au nord, Hội An au centre, puis Ho Chi Minh-Ville et le "
        "<strong>delta du Mékong</strong> au sud. Deux vols intérieurs (Hanoï→Đà Nẵng, Đà Nẵng→SGN) "
        "évitent des journées entières en bus.</p>"
        "<p>Rythme équilibré : 2 nuits par grande étape, une croisière overnight et une excursion "
        "Mékong avant le départ.</p>"
    ),
    "budget_hint": "700–1 200 € sur place (hors vol international)",
    "best_season": "Novembre à avril — climat sec sur tout le S.",
    "location_key": "hanoi",
    "highlights": ["Hanoï", "Halong", "Hội An", "Ho Chi Minh", "Mékong"],
    "experiences": [
        "Croisière 2J/1N baie d'Halong",
        "Vieille ville UNESCO de Hội An",
        "Excursion temples Cham My Sơn",
        "War Remnants Museum et District 1",
        "Canaux et marchés du delta du Mékong",
    ],
    "includes": [
        "Croisière Halong avec repas",
        "Vols intérieurs HAN→DAD et DAD→SGN",
        "Excursion delta Mékong 1 jour",
    ],
    "practical": (
        "<p><strong>Vols :</strong> Vietnam Airlines, VietJet, Bamboo — réservez tôt en haute saison. "
        "<strong>Bagages :</strong> prévoyez un sac léger pour la croisière Halong.</p>"
    ),
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
    "affiliate_sections": [
        {
            "title": "Hanoï & Halong",
            "location_key": "hanoi",
            "hotels": [{
                "name": "Hanoi La Siesta Premium",
                "search": "Hanoi La Siesta Premium",
                "desc": "Base nord — Vieux Quartier.",
                "price_hint": "dès 45 €/nuit",
                "provider": "booking",
            }],
            "activities": [
                {
                    "name": "Food tour Hanoï",
                    "search": "Hanoi street food tour",
                    "desc": "Spécialités du nord.",
                    "price_hint": "dès 35 €",
                    "provider": "getyourguide",
                },
                {
                    "name": "Croisière Halong 2J/1N",
                    "search": "Halong Bay 2 day cruise",
                    "desc": "Jonque, kayak, nuit à bord.",
                    "price_hint": "dès 89 €",
                    "provider": "viator",
                },
            ],
        },
        {
            "title": "Hội An",
            "location_key": "hoi-an",
            "hotels": [{
                "name": "La Siesta Hoi An Resort",
                "search": "La Siesta Hoi An",
                "desc": "Piscine, navette vieille ville.",
                "price_hint": "dès 65 €/nuit",
                "provider": "agoda",
            }],
            "activities": [{
                "name": "My Sơn temples half-day",
                "search": "My Son sanctuary tour from Hoi An",
                "desc": "Sanctuaire Cham — UNESCO.",
                "price_hint": "dès 25 €",
                "provider": "getyourguide",
            }],
        },
        {
            "title": "Ho Chi Minh & Mékong",
            "location_key": "ho-chi-minh-city",
            "hotels": [{
                "name": "La Siesta Premium Saigon",
                "search": "La Siesta Premium Saigon",
                "desc": "District 1, proche Bến Thành.",
                "price_hint": "dès 50 €/nuit",
                "provider": "booking",
            }],
            "activities": [{
                "name": "Delta Mékong journée",
                "search": "Mekong Delta day tour Ben Tre",
                "desc": "Canaux, vélo, dégustation coco.",
                "price_hint": "dès 35 €",
                "provider": "viator",
            }],
        },
    ],
    "faq": [
        {
            "q": "10 jours ou 15 jours pour un premier voyage ?",
            "a": "10 jours couvre l'essentiel nord-centre-sud. 15 jours ajoute Sapa, Huế et homestay Mékong.",
        },
        {
            "q": "Peut-on sauter Halong ?",
            "a": "Oui — remplacez par Ninh Bình (Tam Coc) en 1 jour depuis Hanoï, puis vol vers Đà Nẵng.",
        },
    ],
    "days": [
        {
            "day": 1,
            "title": "Hanoï — arrivée & Vieux Quartier",
            "location": "Hanoï",
            "location_slug": "hanoi",
            "transport": "Grab Noi Bai → centre",
            "stay": "Hanoï",
            "narrative": (
                "<p>Bienvenue dans la capitale millénaire. Le <strong>Vieux Quartier</strong> concentre "
                "hôtels, restaurants et l'animation nocturne — idéal pour les deux premières nuits.</p>"
            ),
            "activities": [
                "Installation, balade lac Hoàn Kiếm",
                "Pont Thê Húc et temple Ngoc Son",
                "Dîner street food (phở, bún chả)",
            ],
            "hotel": {
                "name": "Hanoi La Siesta Premium",
                "search": "Hanoi La Siesta Premium",
                "provider": "booking",
                "location_key": "hanoi",
                "price_hint": "dès 45 €/nuit",
            },
        },
        {
            "day": 2,
            "title": "Hanoï — culture & gastronomie",
            "location": "Hanoï",
            "location_slug": "hanoi",
            "stay": "Hanoï",
            "narrative": (
                "<p>Journée musées et street food : le Temple de la Littérature et le Musée "
                "d'Ethnographie complètent parfaitement un food tour matinal.</p>"
            ),
            "activities": [
                {
                    "text": "Food tour matinal",
                    "booking": {
                        "name": "Food tour Hanoï",
                        "search": "Hanoi morning food tour",
                        "provider": "getyourguide",
                        "location_key": "hanoi",
                        "price_hint": "dès 35 €",
                    },
                },
                "Temple de la Littérature",
                "Musée d'Ethnographie",
                {
                    "text": "Marionnettes sur l'eau (soir)",
                    "booking": {
                        "name": "Marionnettes Thang Long",
                        "search": "Hanoi water puppet show",
                        "provider": "viator",
                        "location_key": "hanoi",
                        "price_hint": "dès 8 €",
                    },
                },
            ],
        },
        {
            "day": 3,
            "title": "Baie d'Halong — croisière 2J/1N",
            "location": "Halong",
            "location_slug": "halong",
            "transport": "Transfert Hanoï → port (3–4 h)",
            "stay": "Jonque",
            "narrative": (
                "<p>Classée UNESCO, la baie d'Halong est le <strong>clou du nord</strong>. "
                "Embarquement midi, navigation, kayak et nuit sur la jonque.</p>"
            ),
            "activities": [
                {
                    "text": "Croisière 2J/1N avec kayak",
                    "booking": {
                        "name": "Croisière Halong 2J/1N",
                        "search": "Halong Bay overnight cruise",
                        "provider": "viator",
                        "location_key": "hanoi",
                        "price_hint": "dès 89 €",
                    },
                },
                "Visite grotte Sung Sot ou équivalent",
                "Dîner fruits de mer à bord",
            ],
        },
        {
            "day": 4,
            "title": "Halong → Hội An",
            "location": "Transit",
            "location_slug": "hoi-an",
            "transport": "Vol HAN → DAD + taxi Hội An",
            "stay": "Hội An",
            "narrative": (
                "<p>Tai chi au lever du soleil, débarquement et <strong>vol vers Đà Nẵng</strong>. "
                "Hội An vous accueille avec ses lanternes et son rythme plus lent.</p>"
            ),
            "activities": [
                "Brunch sur la jonque, retour port",
                "Vol intérieur Hanoï → Đà Nẵng",
                "Installation Hội An, balade nocturne",
            ],
            "hotel": {
                "name": "La Siesta Hoi An Resort",
                "search": "La Siesta Hoi An",
                "provider": "agoda",
                "location_key": "hoi-an",
                "price_hint": "dès 65 €/nuit",
            },
        },
        {
            "day": 5,
            "title": "Hội An — vieille ville UNESCO",
            "location": "Hội An",
            "location_slug": "hoi-an",
            "stay": "Hội An",
            "narrative": (
                "<p>Comptoir marchand préservé : pont japonais, maisons en bois et ateliers "
                "d'artisans. Le ticket monument donne accès aux sites principaux.</p>"
            ),
            "activities": [
                "Pont japonais, temple Phuc Kien, maison Tan Ky",
                {
                    "text": "Cours de cuisine (marché + atelier)",
                    "booking": {
                        "name": "Cours cuisine Hội An",
                        "search": "Hoi An cooking class",
                        "provider": "getyourguide",
                        "location_key": "hoi-an",
                        "price_hint": "dès 40 €",
                    },
                },
                "Lanternes au crépuscule",
            ],
        },
        {
            "day": 6,
            "title": "My Sơn ou plage An Bàng",
            "location": "Hội An",
            "location_slug": "hoi-an",
            "stay": "Hội An",
            "narrative": (
                "<p>Choisissez : <strong>My Sơn</strong> (sanctuaire Cham, 1 h de route) ou "
                "journée détente à An Bàng avec vélo et fruits de mer.</p>"
            ),
            "activities": [
                {
                    "text": "Excursion My Sơn demi-journée",
                    "booking": {
                        "name": "My Sơn depuis Hội An",
                        "search": "My Son sanctuary tour Hoi An",
                        "provider": "getyourguide",
                        "location_key": "hoi-an",
                        "price_hint": "dès 25 €",
                    },
                },
                "Ou vélo plage An Bàng + tailleur",
                "Dernière soirée lanternes",
            ],
            "tip": "My Sơn : partez tôt (7h) pour éviter la chaleur et la foule.",
        },
        {
            "day": 7,
            "title": "Vol vers Ho Chi Minh-Ville",
            "location": "Ho Chi Minh-Ville",
            "location_slug": "ho-chi-minh-city",
            "transport": "Vol DAD → SGN (1 h)",
            "stay": "District 1",
            "narrative": (
                "<p>Le sud vous attend : <strong>Ho Chi Minh-Ville</strong> (ex-Saigon) pulse à un "
                "rythme différent — gratte-ciels, scooters et street food du delta.</p>"
            ),
            "activities": [
                "Vol Đà Nẵng → Ho Chi Minh-Ville",
                "Marché Bến Thành, cathédrale Notre-Dame",
                "Dîner District 1 (cơm tấm, bánh xèo)",
            ],
            "hotel": {
                "name": "La Siesta Premium Saigon",
                "search": "La Siesta Premium Saigon",
                "provider": "booking",
                "location_key": "ho-chi-minh-city",
                "price_hint": "dès 50 €/nuit",
            },
        },
        {
            "day": 8,
            "title": "Ho Chi Minh-Ville — histoire & quartiers",
            "location": "Ho Chi Minh-Ville",
            "location_slug": "ho-chi-minh-city",
            "stay": "District 1",
            "narrative": (
                "<p>Journée urbaine : le <strong>War Remnants Museum</strong> (prévoir 2 h), "
                "la Poste centrale Gustave Eiffel et le quartier chinois <strong>Cholon</strong>.</p>"
            ),
            "activities": [
                "War Remnants Museum",
                "Poste centrale & opéra",
                "Cholon — marché Binh Tay, temple Quan Am",
                "Rooftop bar ou café historique",
            ],
        },
        {
            "day": 9,
            "title": "Delta du Mékong — excursion",
            "location": "Delta du Mékong",
            "location_slug": "ho-chi-minh-city",
            "transport": "Minibus SGN → Ben Tre (2 h)",
            "stay": "Ho Chi Minh-Ville",
            "narrative": (
                "<p>Le <strong>delta du Mékong</strong> est le grenier du Vietnam : canaux, "
                "cocoteraies, fabrication artisanale et dégustations de fruits tropicaux.</p>"
            ),
            "activities": [
                {
                    "text": "Excursion journée Ben Tre / Mỹ Tho",
                    "booking": {
                        "name": "Delta Mékong journée",
                        "search": "Mekong Delta day tour from Ho Chi Minh",
                        "provider": "viator",
                        "location_key": "ho-chi-minh-city",
                        "price_hint": "dès 35 €",
                    },
                },
                "Barque sur les canaux, vélo sous les palmiers",
                "Retour Saigon en fin d'après-midi",
            ],
        },
        {
            "day": 10,
            "title": "Départ depuis Saigon",
            "location": "Ho Chi Minh-Ville",
            "location_slug": "ho-chi-minh-city",
            "transport": "Taxi → Tan Son Nhat (30 min)",
            "stay": "—",
            "narrative": (
                "<p>Dernière matinée : café, souvenirs (café robusta, soie, artisanat) et vol "
                "depuis <strong>Tan Son Nhat</strong>.</p>"
            ),
            "activities": [
                "Petit-déjeuner ca phe sua da",
                "Shopping Bến Thành ou Dong Khoi",
                "Transfert aéroport — 3 h avant vol international",
            ],
        },
    ],
}
