"""Contenu FR de l'itinéraire 15 jours nord → sud (inspiré circuit agence locale)."""

ITINERARY_15_DAYS_FR = {
    "slug": "15-days-vietnam",
    "title": "Itinéraire 15 jours Vietnam — Nord au Sud",
    "meta_title": "Itinéraire 15 jours Vietnam — Circuit complet Hanoï, Sapa, Halong, Huế, Hội An, Saigon",
    "meta_description": (
        "Circuit 15 jours au Vietnam : Hanoï, Sapa, Ninh Bình, baie d'Halong, Huế, Hội An, "
        "Ho Chi Minh-Ville et delta du Mékong. Programme jour par jour, budget et réservations."
    ),
    "duration": 15,
    "summary": (
        "Le grand classique en 2 semaines : capitale millénaire, montagnes de Sapa, "
        "baie d'Halong, cité impériale de Huế, Hội An lanternes et delta du Mékong."
    ),
    "overview": (
        "<p>Cet itinéraire 15 jours couvre les trois régions du Vietnam en forme de S — "
        "comme le recommandent les agences locales pour un premier voyage complet. "
        "Au nord : Hanoï, Sapa et la baie d'Halong ; au centre : Huế et Hội An ; "
        "au sud : Ho Chi Minh-Ville et le delta du Mékong.</p>"
        "<p>Rythme équilibré avec 2 nuits chez l'habitant (montagnes du nord et Mékong), "
        "une croisière overnight à Halong et des vols intérieurs pour gagner du temps. "
        "Budget indicatif hors vol international — réservations via nos liens affiliés ci-dessous.</p>"
    ),
    "budget_hint": "900–1 400 € sur place (hors vol international)",
    "location_key": "hanoi",
    "highlights": [
        "Hanoï", "Sapa", "Ninh Bình", "Halong", "Huế", "Hội An", "Ho Chi Minh", "Delta Mékong",
    ],
    "experiences": [
        "Sites incontournables du nord au sud en 2 semaines",
        "Croisière en jonque sur la baie d'Halong avec nuit à bord",
        "Randonnées et rencontres ethniques à Sapa et Bac Ha",
        "Citadelle impériale de Huế et vieille ville UNESCO de Hội An",
        "Delta du Mékong : marché flottant, canaux et nuit chez l'habitant",
    ],
    "sample_hotel": {
        "name": "Hanoi La Siesta Premium",
        "search": "Hanoi La Siesta Premium Hang Be",
        "desc": "Boutique-hôtel Vieux Quartier — base idéale pour les premiers jours à Hanoï.",
        "price_hint": "dès 45 €/nuit",
        "provider": "booking",
    },
    "sample_activity": {
        "name": "Croisière Baie d'Halong 2J/1N",
        "search": "Halong Bay cruise 2 days 1 night from Hanoi",
        "desc": "Jonque, kayak et nuit à bord — incontournable du circuit 15 jours.",
        "price_hint": "dès 89 €",
        "provider": "viator",
    },
    "activity_location_key": "hanoi",
    "affiliate_sections": [
        {
            "title": "Hanoï — hébergement & activités",
            "location_key": "hanoi",
            "hotels": [
                {
                    "name": "Hanoi La Siesta Premium",
                    "search": "Hanoi La Siesta Premium",
                    "desc": "Vieux Quartier, excellent rapport qualité-prix.",
                    "price_hint": "dès 45 €/nuit",
                    "provider": "booking",
                },
            ],
            "activities": [
                {
                    "name": "Food tour street food matinal",
                    "search": "Hanoi street food walking tour morning",
                    "desc": "Phở, bún chả, bánh cuốn — le meilleur de la street food hanoïenne.",
                    "price_hint": "dès 35 €",
                    "provider": "getyourguide",
                },
                {
                    "name": "Spectacle marionnettes sur l'eau",
                    "search": "Hanoi water puppet show Thang Long",
                    "desc": "Art traditionnel du nord Vietnam — spectacle du soir.",
                    "price_hint": "dès 8 €",
                    "provider": "viator",
                },
            ],
        },
        {
            "title": "Sapa — trek & rizières",
            "location_key": "sapa",
            "hotels": [
                {
                    "name": "Sapa Clay House",
                    "search": "Sapa Clay House hotel",
                    "desc": "Vue rizières, confort après les randonnées.",
                    "price_hint": "dès 55 €/nuit",
                    "provider": "booking",
                },
            ],
            "activities": [
                {
                    "name": "Trek rizières & villages Hmong",
                    "search": "Sapa rice terrace trek day tour",
                    "desc": "Muong Hoa, Lao Chai, Ta Van — paysages et cultures locales.",
                    "price_hint": "dès 25 €",
                    "provider": "getyourguide",
                },
            ],
        },
        {
            "title": "Halong — croisière",
            "location_key": "hanoi",
            "hotels": [],
            "activities": [
                {
                    "name": "Croisière 2J/1N Baie d'Halong",
                    "search": "Halong Bay overnight cruise 2 days",
                    "desc": "Kayak, grottes, nuit sur jonque — cœur du voyage.",
                    "price_hint": "dès 89 €",
                    "provider": "viator",
                },
            ],
        },
        {
            "title": "Huế — cité impériale",
            "location_key": "hue",
            "hotels": [
                {
                    "name": "Pilgrimage Village Boutique Resort",
                    "search": "Pilgrimage Village Hue",
                    "desc": "Cadre verdoyant près de la citadelle impériale.",
                    "price_hint": "dès 70 €/nuit",
                    "provider": "booking",
                },
            ],
            "activities": [
                {
                    "name": "Visite citadelle & tombeaux impériaux",
                    "search": "Hue imperial city tomb tour",
                    "desc": "Citadelle Nguyen, tombeau de Minh Mang, pagode Thien Mu.",
                    "price_hint": "dès 30 €",
                    "provider": "getyourguide",
                },
            ],
        },
        {
            "title": "Hội An — culture & plage",
            "location_key": "hoi-an",
            "hotels": [
                {
                    "name": "La Siesta Hoi An Resort & Spa",
                    "search": "La Siesta Hoi An Resort",
                    "desc": "Piscine et navette vers la vieille ville.",
                    "price_hint": "dès 65 €/nuit",
                    "provider": "agoda",
                },
            ],
            "activities": [
                {
                    "name": "Cours de cuisine vietnamienne",
                    "search": "Hoi An cooking class market",
                    "desc": "Marché local + atelier — spécialité de Hội An.",
                    "price_hint": "dès 40 €",
                    "provider": "getyourguide",
                },
            ],
        },
        {
            "title": "Ho Chi Minh & Mékong",
            "location_key": "ho-chi-minh-city",
            "hotels": [
                {
                    "name": "La Siesta Premium Saigon",
                    "search": "La Siesta Premium Saigon District 1",
                    "desc": "Centre-ville, idéal avant le delta.",
                    "price_hint": "dès 50 €/nuit",
                    "provider": "booking",
                },
            ],
            "activities": [
                {
                    "name": "Excursion Delta du Mékong 2J/1N",
                    "search": "Mekong Delta 2 days homestay Can Tho floating market",
                    "desc": "Canaux, marché flottant Cai Rang, nuit chez l'habitant.",
                    "price_hint": "dès 75 €",
                    "provider": "viator",
                },
            ],
        },
    ],
    "faq": [
        {
            "q": "Quelle est la meilleure période pour ce circuit 15 jours ?",
            "a": "Octobre à avril : climat agréable sur tout le S. Évitez la saison des pluies intense (septembre–novembre au centre, été humide au sud). Mars–mai : rizières vertes à Sapa.",
        },
        {
            "q": "Faut-il un visa pour 15 jours au Vietnam ?",
            "a": "Les ressortissants de nombreux pays UE bénéficient d'une exemption (45 jours en 2024–2026 selon nationalité). Sinon : e-visa en ligne sur le site officiel de l'immigration vietnamienne, 3–5 jours ouvrés.",
        },
        {
            "q": "Peut-on faire ce circuit en sens inverse (sud → nord) ?",
            "a": "Oui — commencez par Ho Chi Minh-Ville et terminez à Hanoï. Les vols intérieurs et transferts s'adaptent ; prévoyez la croisière Halong avant le vol retour depuis Hanoï.",
        },
        {
            "q": "Comment ajouter des jours plage (Đà Nẵng, Phú Quốc) ?",
            "a": "Ajoutez 2–3 nuits à Đà Nẵng ou Phú Quốc après Hội An ou en fin de circuit. Nos guides destination détaillent les plages et hôtels.",
        },
        {
            "q": "Train de nuit Hanoï–Sapa : est-ce obligatoire ?",
            "a": "Non — beaucoup de voyageurs préfèrent le minibus VIP (5–6 h) ou un vol + route. Le train couchette reste une expérience authentique si vous aimez l'aventure.",
        },
    ],
    "days": [
        {
            "day": 1,
            "title": "Hanoï — arrivée & Vieux Quartier",
            "location": "Hanoï",
            "activities": [
                "Transfert aéroport → hôtel Vieux Quartier (chambre dès 14h)",
                "Lac Hoàn Kiếm, temple Ngoc Son et pont Thê Húc",
                "Balade 36 rues corporatives + maison ancienne type « tube »",
                "Dîner street food : phở ou bún chả",
            ],
            "stay": "Hanoï — Vieux Quartier",
            "tip": "Grab depuis l'aéroport Noi Bai — comptez 45 min hors heures de pointe.",
        },
        {
            "day": 2,
            "title": "Hanoï — culture & train de nuit",
            "location": "Hanoï",
            "activities": [
                "Temple de la Littérature (1000 ans d'histoire confucéenne)",
                "Musée d'Ethnographie — 54 ethnies du Vietnam",
                "Place Ba Dinh, maison sur pilotis de Hồ Chí Minh",
                "Spectacle marionnettes sur l'eau (soir)",
                "Train couchette Hanoï → Lao Cai (option Sapa)",
            ],
            "stay": "Train couchette ou hôtel Hanoï",
            "tip": "Réservez le train LC3/LC1 à l'avance en haute saison (nov–fév).",
        },
        {
            "day": 3,
            "title": "Lao Cai — Bac Ha & minorités",
            "location": "Bac Ha / Sapa",
            "activities": [
                "Arrivée matinale Lao Cai, douche & petit-déjeuner",
                "Route vers Bac Ha — randonnée villages Hmong & Phu La",
                "Marché hebdomadaire (dimanche = le plus coloré)",
                "Nuit chez l'habitant ethnie Tay",
            ],
            "stay": "Homestay Bac Ha",
        },
        {
            "day": 4,
            "title": "Bac Ha — Sapa",
            "location": "Sapa",
            "activities": [
                "Transfert vers Sapa (3 h)",
                "Villages Hang Da & Sa Seng — rizières en terrasses",
                "Vue sur les sommets Fansipan (téléphérique optionnel)",
                "Soirée libre marché Sapa",
            ],
            "stay": "Sapa",
        },
        {
            "day": 5,
            "title": "Sapa — trek Muong Hoa → Hanoï",
            "location": "Sapa → Hanoï",
            "activities": [
                "Randonnée vallée Muong Hoa : Y Linh Ho, Lao Chai, Ta Van",
                "Rencontre Hmong & Dzay au travail dans les rizières",
                "Route retour Hanoï (5–6 h) ou train de nuit",
            ],
            "stay": "Hanoï",
        },
        {
            "day": 6,
            "title": "Ninh Bình — baie terrestre",
            "location": "Ninh Bình",
            "activities": [
                "Excursion journée Tam Coc / Trang An",
                "Mont Mua — panorama 486 marches sur les pains de sucre",
                "Balade vélo entre rizières et rivières",
                "Barque sur la rivière Ngo Đồng (3 grottes)",
            ],
            "stay": "Hanoï",
            "tip": "Partez tôt (7h) pour éviter la foule à Tam Coc.",
        },
        {
            "day": 7,
            "title": "Baie d'Halong — croisière 2J/1N",
            "location": "Halong",
            "activities": [
                "Transfert 3–4 h, embarquement jonque",
                "Croisière Bai Tu Long ou baie d'Halong",
                "Kayak, grottes Thien Canh Son",
                "Cours cuisine à bord (nems, rouleaux de printemps)",
            ],
            "stay": "Nuit sur jonque",
        },
        {
            "day": 8,
            "title": "Halong — Huế",
            "location": "Halong → Huế",
            "activities": [
                "Tai chi au lever du soleil sur la baie",
                "Village flottant Vung Vieng (barque ou kayak)",
                "Retour Hanoï, vol intérieur vers Huế",
            ],
            "stay": "Huế",
        },
        {
            "day": 9,
            "title": "Huế — cité impériale",
            "location": "Huế",
            "activities": [
                "Citadelle impériale Nguyen (1802–1945)",
                "Tombeau de Minh Mang ou tombeau de Tu Duc",
                "Pagode Thien Mu au bord de la Perfume River",
                "Marché Dong Ba — spécialités et coniques",
            ],
            "stay": "Huế",
        },
        {
            "day": 10,
            "title": "Huế — Hội An via Hai Van Pass",
            "location": "Huế → Hội An",
            "activities": [
                "Route côtière : plages Thuan An, lagune Lang Co",
                "Col des Nuages (Hai Van Pass) — vue Da Nang",
                "Installation Hội An, balade lanternes en soirée",
            ],
            "stay": "Hội An",
        },
        {
            "day": 11,
            "title": "Hội An — journée libre",
            "location": "Hội An",
            "activities": [
                "Pont japonais, temple Phuc Kien, vieilles maisons bois",
                "Cours de cuisine ou atelier lanterne",
                "Plage An Bàng ou Cửa Đại (vélo 15 min)",
                "Tailleur sur mesure (24–48 h)",
            ],
            "stay": "Hội An",
        },
        {
            "day": 12,
            "title": "Hội An — Ho Chi Minh-Ville",
            "location": "Ho Chi Minh-Ville",
            "activities": [
                "Vol Đà Nẵng → Ho Chi Minh-Ville (1 h)",
                "Marché Bến Thành, cathédrale Notre-Dame",
                "Poste centrale (Gustave Eiffel), quartier Cholon",
            ],
            "stay": "Ho Chi Minh-Ville",
        },
        {
            "day": 13,
            "title": "Delta Mékong — Ben Tre & homestay",
            "location": "Delta du Mékong",
            "activities": [
                "Route Ben Tre — rivières et cocoteraies",
                "Vélo ou xe loi sous les palmiers",
                "Fabrication bonbons de coco, dégustation fruits locaux",
                "Nuit chez l'habitant île An Bình (Vinh Long)",
            ],
            "stay": "Homestay Mékong",
        },
        {
            "day": 14,
            "title": "Can Tho — marché flottant → Saigon",
            "location": "Can Tho → HCMC",
            "activities": [
                "Lever tôt : marché flottant Cai Rang",
                "Comparaison marché terrestre vs flottant",
                "Retour Ho Chi Minh-Ville, soirée libre",
            ],
            "stay": "Ho Chi Minh-Ville",
            "tip": "Le marché flottant est actif dès 6h — partez à 5h30.",
        },
        {
            "day": 15,
            "title": "Ho Chi Minh-Ville — départ",
            "location": "Ho Chi Minh-Ville",
            "activities": [
                "Matinée libre : souvenirs, café rooftop",
                "Transfert aéroport Tan Son Nhat (prévoir 3 h avant vol)",
            ],
            "stay": "—",
        },
    ],
}
