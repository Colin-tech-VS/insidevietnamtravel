"""EN overlay for the 3-day Vietnam itinerary (full translation of the FR content)."""

ITINERARY_3_DAYS_EN = {
    "title": "3-day Vietnam itinerary",
    "meta_title": "Vietnam Itinerary 3 Days — Hanoi or Saigon City Break",
    "meta_description": (
        "What can you do with 3 days in Vietnam? Detailed Hanoi city break — Old Quarter, "
        "street food, Halong day cruise — with hotels, activities and a real budget."
    ),
    "summary": "Perfect for a first taste — an intense city break in Hanoi or Saigon.",
    "overview": (
        "<p>Three days in Vietnam is short, but it's enough to <strong>get a real feel for the "
        "country</strong> in one of its big cities: street food, temples, markets and a "
        "half-day excursion into the surrounding countryside. This plan is built around "
        "<strong>Hanoi</strong> (north) — swap Halong for the Củ Chi tunnels if you land "
        "in Ho Chi Minh City.</p>"
        "<p>Ideal for a long layover, an extended weekend or a few extra days tacked onto "
        "a business trip in Southeast Asia.</p>"
    ),
    "budget_hint": "€150–350 on the ground (international flights excluded)",
    "best_season": "October to April — avoid the torrential rains of July–August.",
    "highlights": ["Hanoi", "Old Quarter", "Halong (optional)"],
    "experiences": [
        "Hanoi street food for breakfast",
        "Temple of Literature and Hoàn Kiếm Lake",
        "Water puppet show",
        "Express Halong Bay excursion",
    ],
    "includes": [
        "2 nights in a city-centre hotel",
        "Recommended food tour on day 2",
        "Halong or Củ Chi excursion on day 3",
    ],
    "practical": (
        "<p><strong>Hanoi:</strong> Noi Bai airport is 45 min away — take a Grab or a metered "
        "taxi. <strong>Saigon:</strong> same logic from Tan Son Nhat; swap the northern "
        "activities for District 1, Bến Thành Market and the Củ Chi tunnels.</p>"
    ),
    "sample_hotel": {
        "name": "Hanoi La Siesta Premium",
        "search": "Hanoi La Siesta Premium Hang Be",
        "desc": "Old Quarter boutique hotel — ideal for a Hanoi city break.",
        "price_hint": "from €45/night",
        "provider": "booking",
    },
    "sample_activity": {
        "name": "Morning food tour",
        "search": "Hanoi street food walking tour morning",
        "desc": "Guided tasting of Hanoi's signature dishes.",
        "price_hint": "from €35",
        "provider": "getyourguide",
    },
    "affiliate_sections": [
        {
            "title": "Hanoi — express stay",
            "location_key": "hanoi",
            "hotels": [{
                "name": "Hanoi La Siesta Premium",
                "search": "Hanoi La Siesta Premium",
                "desc": "Old Quarter location, spa and rooftop bar.",
                "price_hint": "from €45/night",
                "provider": "booking",
            }],
            "activities": [
                {
                    "name": "Street food tour",
                    "search": "Hanoi street food walking tour",
                    "desc": "Phở, bún chả and egg coffee.",
                    "price_hint": "from €35",
                    "provider": "getyourguide",
                },
                {
                    "name": "Halong day trip from Hanoi",
                    "search": "Halong Bay day trip from Hanoi",
                    "desc": "Full-day cruise — perfect if you only have 3 days.",
                    "price_hint": "from €55",
                    "provider": "viator",
                },
            ],
        },
    ],
    "faq": [
        {
            "q": "Hanoi or Saigon for 3 days?",
            "a": "Hanoi if you're drawn to history and northern street food. Saigon if you prefer the urban energy of the south and the War Remnants Museum.",
        },
        {
            "q": "Can you visit Halong Bay in a single day?",
            "a": "Yes — departure at 7am, back by 8pm. Less immersive than a night on board, but perfect for a 3-day trip.",
        },
        {
            "q": "What budget do I need for 3 days in Vietnam?",
            "a": "Plan on €150–350 on the ground excluding international flights: a 3-star hotel (€45–60/night), street food meals (€2–5), a food tour (~€35) and a Halong day cruise (~€55).",
        },
        {
            "q": "Do I need a visa for a 3-day stay?",
            "a": "Many nationalities — including most EU citizens — get a visa exemption of up to 45 days. Otherwise, apply for the official e-visa online; it takes 3–5 business days.",
        },
        {
            "q": "When is the best season for a Hanoi city break?",
            "a": "October to April, with dry weather and mild temperatures. Avoid July–August, which are very hot and rainy in the north.",
        },
        {
            "q": "Should I book activities in advance?",
            "a": "Book the Halong excursion and the food tour a few days ahead, especially from November to February. The water puppet show can be booked the day before.",
        },
    ],
    "days": [
        {
            "day": 1,
            "title": "Arrival & Hanoi's historic heart",
            "location": "Hanoi",
            "location_slug": "hanoi",
            "transport": "Grab from the airport to the Old Quarter (~€15)",
            "stay": "Old Quarter",
            "narrative": (
                "<p>First immersion in the <strong>Old Quarter</strong>: narrow alleys, fruit "
                "stalls and scooters weaving between café terraces. <strong>Hoàn Kiếm</strong> "
                "Lake is the green lung of the city centre — the red Thê Húc bridge leads to "
                "the small Ngoc Son temple.</p>"
            ),
            "activities": [
                "Check-in and a coffee break (egg coffee at Café Giang if you can)",
                "Stroll around Hoàn Kiếm Lake and Ngoc Son temple",
                "Explore the 36 guild streets",
                {
                    "text": "Dinner of phở or bún chả at a local food stall",
                    "booking": {
                        "name": "Old Quarter food tour",
                        "search": "Hanoi old quarter evening food tour",
                        "provider": "getyourguide",
                        "location_key": "hanoi",
                        "price_hint": "from €30",
                    },
                },
                "Your first bia hơi beer on a street terrace",
            ],
            "hotel": {
                "name": "Hanoi La Siesta Premium",
                "search": "Hanoi La Siesta Premium",
                "provider": "booking",
                "location_key": "hanoi",
                "price_hint": "from €45/night",
            },
            "tip": "Change some dong at the airport; keep your hotel address written in Vietnamese for the taxi.",
        },
        {
            "day": 2,
            "title": "Culture, museums & street food",
            "location": "Hanoi",
            "location_slug": "hanoi",
            "stay": "Old Quarter",
            "narrative": (
                "<p>The busiest day: the <strong>Temple of Literature</strong> (1070) and the "
                "<strong>Museum of Ethnology</strong> give you a clear key to understanding "
                "Vietnam before you dive into the street food scene with a local guide.</p>"
            ),
            "activities": [
                {
                    "text": "Morning food tour (phở, bánh cuốn, egg coffee)",
                    "booking": {
                        "name": "Hanoi morning food tour",
                        "search": "Hanoi morning street food tour",
                        "provider": "getyourguide",
                        "location_key": "hanoi",
                        "price_hint": "from €35",
                    },
                },
                "Temple of Literature",
                "Museum of Ethnology (allow at least 2 h)",
                {
                    "text": "Water puppet show (evening)",
                    "booking": {
                        "name": "Thang Long water puppets",
                        "search": "Hanoi water puppet show",
                        "provider": "viator",
                        "location_key": "hanoi",
                        "price_hint": "from €8",
                    },
                },
            ],
            "tip": "Book the puppet show the day before — performances at 6pm and 8pm.",
        },
        {
            "day": 3,
            "title": "Halong excursion & departure",
            "location": "Halong",
            "location_slug": "halong",
            "transport": "Round-trip minibus from Hanoi (3 h each way)",
            "stay": "—",
            "narrative": (
                "<p>Last day: a <strong>full-day Halong Bay excursion</strong> from Hanoi — "
                "cruising between the karst islets, lunch on board and back by late afternoon "
                "in time for the airport. Saigon variant: Củ Chi tunnels in the morning, lunch "
                "in District 1.</p>"
            ),
            "activities": [
                {
                    "text": "Halong Bay day cruise (7am departure)",
                    "booking": {
                        "name": "Halong day trip from Hanoi",
                        "search": "Halong Bay day trip from Hanoi",
                        "provider": "viator",
                        "location_key": "hanoi",
                        "price_hint": "from €55",
                    },
                },
                "Kayaking or cave visit, weather permitting",
                "Back to Hanoi, airport transfer — allow 3 h before your flight",
            ],
            "tip": "If your flight leaves late, ask for a direct airport transfer from the Halong harbour.",
        },
    ],
}
