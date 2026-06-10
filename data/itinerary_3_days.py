"""Itinéraire 3 jours — contenu détaillé FR (focus Hanoï, variante Saigon en note)."""

ITINERARY_3_DAYS_FR = {
    "slug": "3-days-vietnam",
    "title": "Itinéraire 3 jours au Vietnam",
    "meta_title": "Itinéraire 3 jours Vietnam — City break Hanoï ou Saigon jour par jour",
    "meta_description": (
        "Que faire 3 jours au Vietnam ? Programme détaillé Hanoï (Vieux Quartier, street food, Halong) "
        "ou Ho Chi Minh-Ville avec hôtels, activités affiliées et budget."
    ),
    "duration": 3,
    "summary": "Parfait pour un premier aperçu — city break intense à Hanoï ou Saigon.",
    "overview": (
        "<p>Trois jours au Vietnam, c'est court mais suffisant pour <strong>goûter l'âme du pays</strong> "
        "dans une grande ville : street food, temples, marchés et une excursion d'une demi-journée "
        "dans les environs. Ce programme est calibré sur <strong>Hanoï</strong> (nord) — "
        "remplacez Halong par Củ Chi si vous atterrissez à Ho Chi Minh-Ville.</p>"
        "<p>Idéal en escale longue, week-end prolongé ou prolongation après un voyage d'affaires "
        "en Asie du Sud-Est.</p>"
    ),
    "budget_hint": "150–350 € sur place (hors vol international)",
    "best_season": "Octobre à avril — évitez la pluie torrentielle de juillet–août.",
    "location_key": "hanoi",
    "highlights": ["Hanoï", "Vieux Quartier", "Halong (option)"],
    "experiences": [
        "Street food hanoïenne au petit-déjeuner",
        "Temple de la Littérature et lac Hoàn Kiếm",
        "Spectacle de marionnettes sur l'eau",
        "Excursion express baie d'Halong",
    ],
    "includes": [
        "2 nuits hôtel centre-ville",
        "Food tour recommandé jour 2",
        "Excursion Halong ou Củ Chi jour 3",
    ],
    "practical": (
        "<p><strong>Hanoï :</strong> aéroport Noi Bai à 45 min — Grab ou taxi compteur. "
        "<strong>Saigon :</strong> même logique depuis Tan Son Nhat, remplacez les activités nord par "
        "District 1, marché Bến Thành et tunnels Củ Chi.</p>"
    ),
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
    "activity_location_key": "hanoi",
    "affiliate_sections": [
        {
            "title": "Hanoï — séjour express",
            "location_key": "hanoi",
            "hotels": [{
                "name": "Hanoi La Siesta Premium",
                "search": "Hanoi La Siesta Premium",
                "desc": "Vieux Quartier, spa et rooftop.",
                "price_hint": "dès 45 €/nuit",
                "provider": "booking",
            }],
            "activities": [
                {
                    "name": "Food tour street food",
                    "search": "Hanoi street food walking tour",
                    "desc": "Phở, bún chả, egg coffee.",
                    "price_hint": "dès 35 €",
                    "provider": "getyourguide",
                },
                {
                    "name": "Halong journée depuis Hanoï",
                    "search": "Halong Bay day trip from Hanoi",
                    "desc": "Croisière journée — idéal si 3 jours seulement.",
                    "price_hint": "dès 55 €",
                    "provider": "viator",
                },
            ],
        },
    ],
    "faq": [
        {
            "q": "Hanoï ou Saigon en 3 jours ?",
            "a": "Hanoï si vous aimez l'histoire et la street food du nord. Saigon si vous préférez l'énergie urbaine du sud et le War Museum.",
        },
        {
            "q": "Peut-on faire Halong en une journée ?",
            "a": "Oui — départ 7h, retour 20h. Moins immersif qu'une nuit à bord mais parfait pour 3 jours.",
        },
    ],
    "days": [
        {
            "day": 1,
            "title": "Arrivée & cœur historique de Hanoï",
            "location": "Hanoï",
            "location_slug": "hanoi",
            "transport": "Grab aéroport → Vieux Quartier (~15 €)",
            "stay": "Vieux Quartier",
            "narrative": (
                "<p>Première immersion dans le <strong>Vieux Quartier</strong> : ruelles étroites, "
                "étals de fruits et scooters qui slaloment entre les terrasses. Le lac "
                "<strong>Hoàn Kiếm</strong> est le poumon vert du centre — le pont Thê Húc rouge "
                "mène au petit temple Ngoc Son.</p>"
            ),
            "activities": [
                "Check-in et pause café (egg coffee au Café Giang si possible)",
                "Balade lac Hoàn Kiếm et temple Ngoc Son",
                "Découverte des 36 rues corporatives",
                {
                    "text": "Dîner phở ou bún chả dans un comptoir local",
                    "booking": {
                        "name": "Food tour Vieux Quartier",
                        "search": "Hanoi old quarter evening food tour",
                        "provider": "getyourguide",
                        "location_key": "hanoi",
                        "price_hint": "dès 30 €",
                    },
                },
                "Première bière bia hơi en terrasse",
            ],
            "hotel": {
                "name": "Hanoi La Siesta Premium",
                "search": "Hanoi La Siesta Premium",
                "provider": "booking",
                "location_key": "hanoi",
                "price_hint": "dès 45 €/nuit",
            },
            "tip": "Changez des dong à l'aéroport ; gardez l'adresse hôtel en vietnamien pour le taxi.",
        },
        {
            "day": 2,
            "title": "Culture, musées & street food",
            "location": "Hanoï",
            "location_slug": "hanoi",
            "stay": "Vieux Quartier",
            "narrative": (
                "<p>Journée la plus dense : le <strong>Temple de la Littérature</strong> (1070) "
                "et le <strong>Musée d'Ethnographie</strong> donnent une lecture claire du Vietnam "
                "avant de plonger dans la street food avec un guide local.</p>"
            ),
            "activities": [
                {
                    "text": "Food tour matinal (phở, bánh cuốn, egg coffee)",
                    "booking": {
                        "name": "Food tour matinal Hanoï",
                        "search": "Hanoi morning street food tour",
                        "provider": "getyourguide",
                        "location_key": "hanoi",
                        "price_hint": "dès 35 €",
                    },
                },
                "Temple de la Littérature",
                "Musée d'Ethnographie (2 h minimum)",
                {
                    "text": "Spectacle marionnettes sur l'eau (soir)",
                    "booking": {
                        "name": "Marionnettes Thang Long",
                        "search": "Hanoi water puppet show",
                        "provider": "viator",
                        "location_key": "hanoi",
                        "price_hint": "dès 8 €",
                    },
                },
            ],
            "tip": "Réservez les marionnettes la veille — spectacle à 18h ou 20h.",
        },
        {
            "day": 3,
            "title": "Excursion Halong & départ",
            "location": "Halong",
            "location_slug": "halong",
            "transport": "Minibus aller-retour Hanoï (3 h × 2)",
            "stay": "—",
            "narrative": (
                "<p>Dernière journée : <strong>excursion journée Halong</strong> depuis Hanoï — "
                "navigation entre les îlots karstiques, déjeuner à bord et retour en fin d'après-midi "
                "pour l'aéroport. Variante Saigon : tunnels Củ Chi le matin, déjeuner District 1.</p>"
            ),
            "activities": [
                {
                    "text": "Croisière journée baie d'Halong (départ 7h)",
                    "booking": {
                        "name": "Halong journée depuis Hanoï",
                        "search": "Halong Bay day trip from Hanoi",
                        "provider": "viator",
                        "location_key": "hanoi",
                        "price_hint": "dès 55 €",
                    },
                },
                "Kayak ou grottes selon la météo",
                "Retour Hanoï, transfert aéroport — prévoir 3 h avant le vol",
            ],
            "tip": "Si vol tardif, demandez un transfert direct aéroport depuis le port Halong.",
        },
    ],
}
