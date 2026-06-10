"""Traductions EN des itinéraires — fusionnées au chargement."""

from data.itinerary_15_days_en import ITINERARY_15_DAYS_EN

ITINERARIES_EN = {
    "3-days-vietnam": {
        "title": "3-day Vietnam itinerary",
        "meta_title": "3-day Vietnam itinerary — Hanoi or Saigon mini city break",
        "meta_description": (
            "What to do in 3 days in Vietnam? Express itinerary for Hanoi or Ho Chi Minh City "
            "with hotels, activities and budget."
        ),
        "summary": "Perfect for a first taste — choose Hanoi (north) or Saigon (south).",
        "budget_hint": "€150–350 all-in (flights excluded)",
        "sample_hotel": {
            "desc": "Old Quarter boutique hotel — ideal for a Hanoi city break.",
            "price_hint": "from €45/night",
        },
        "sample_activity": {
            "name": "Morning food tour",
            "desc": "Guided discovery of Hanoi specialities.",
            "price_hint": "from €35",
        },
        "days": [
            {
                "day": 1,
                "title": "Arrival & historic centre",
                "location": "Hanoi or HCMC",
                "activities": [
                    "Check-in and first stroll (Old Quarter or District 1)",
                    "Lunch street food — phở or cơm tấm",
                    "Iconic temple / museum in the afternoon",
                    "Local dinner + first bia hơi beer or rooftop",
                ],
                "stay": "City-centre hotel (see recommendations)",
            },
            {
                "day": 2,
                "title": "Culture & food immersion",
                "location": "Hanoi or HCMC",
                "activities": [
                    "Morning food tour (recommended)",
                    "Museum or secondary district (Ethnography / War Museum)",
                    "Handicraft shopping or local market",
                    "Show or evening stroll",
                ],
                "stay": "Same hotel",
            },
            {
                "day": 3,
                "title": "Excursion & departure",
                "location": "Surroundings",
                "activities": [
                    "Half-day excursion (Halong if Hanoi, Củ Chi if HCMC)",
                    "Lunch with sea or countryside views",
                    "Return to airport — allow 3h before flight",
                ],
                "stay": "—",
            },
        ],
    },
    "7-days-vietnam": {
        "title": "7-day Vietnam itinerary",
        "meta_title": "7-day Vietnam itinerary — North + Central in one week",
        "meta_description": (
            "7-day Vietnam circuit: Hanoi, Halong Bay, Hội An. Day-by-day plan "
            "with domestic flights and budget."
        ),
        "summary": "Hanoi → Halong → Hội An — the most popular north-central combo.",
        "budget_hint": "€450–800 (international flights excluded)",
        "sample_hotel": {
            "desc": "Hanoi base for the first 2 nights of the circuit.",
            "price_hint": "from €40/night",
        },
        "sample_activity": {
            "name": "Halong 2D/1N cruise",
            "desc": "Circuit highlight — transport from Hanoi included.",
            "price_hint": "from €89",
        },
        "days": [
            {"day": 1, "title": "Hanoi — Old Quarter", "location": "Hanoi", "activities": ["Arrival, Hoàn Kiếm Lake stroll", "Morning phở day 2", "Street food dinner"], "stay": "Old Quarter"},
            {"day": 2, "title": "Hanoi — Culture", "location": "Hanoi", "activities": ["Temple of Literature", "Ethnography Museum", "Train street"], "stay": "Old Quarter"},
            {"day": 3, "title": "Halong Bay", "location": "Halong", "activities": ["3h transfer", "Cruise departs midday", "Kayak & caves"], "stay": "Cruise boat"},
            {"day": 4, "title": "Halong → Hội An", "location": "Transit", "activities": ["Sunrise on the bay", "Flight Hanoi → Đà Nẵng", "Transfer to Hội An"], "stay": "Hội An"},
            {"day": 5, "title": "Hội An — Old town", "location": "Hội An", "activities": ["Japanese bridge & temples", "Cooking class", "Lanterns at night"], "stay": "Hội An"},
            {"day": 6, "title": "Hội An — Beach & cycling", "location": "Hội An", "activities": ["An Bàng bike ride", "Tailor or spa", "Night market"], "stay": "Hội An"},
            {"day": 7, "title": "Departure", "location": "Đà Nẵng", "activities": ["Local breakfast", "Return flight from Đà Nẵng"], "stay": "—"},
        ],
    },
    "10-days-vietnam": {
        "title": "10-day Vietnam itinerary",
        "meta_title": "10-day Vietnam itinerary — Complete North, Central & South",
        "meta_description": (
            "10-day Vietnam trip: Hanoi, Halong, Hội An, Ho Chi Minh City. "
            "Detailed day-by-day itinerary with transport tips."
        ),
        "summary": "The classic north → central → south route in 10 days.",
        "budget_hint": "€700–1,200 (international flights excluded)",
        "sample_hotel": {
            "desc": "Central hotel for nights in Ho Chi Minh City.",
            "price_hint": "from €55/night",
        },
        "sample_activity": {
            "name": "Mekong Delta excursion",
            "desc": "Day trip through canals, floating markets and villages.",
            "price_hint": "from €35",
        },
        "days": [
            {"day": 1, "title": "Hanoi", "location": "Hanoi", "activities": ["Arrival & Old Quarter"], "stay": "Hanoi"},
            {"day": 2, "title": "Hanoi in depth", "location": "Hanoi", "activities": ["Food tour", "Temple of Literature"], "stay": "Hanoi"},
            {"day": 3, "title": "Halong 2D/1N", "location": "Halong", "activities": ["Cruise departure", "Kayak"], "stay": "Boat"},
            {"day": 4, "title": "Halong → Hội An", "location": "Transit", "activities": ["Flight to Đà Nẵng", "Settle in Hội An"], "stay": "Hội An"},
            {"day": 5, "title": "Hội An", "location": "Hội An", "activities": ["Old town", "Cooking"], "stay": "Hội An"},
            {"day": 6, "title": "Hội An / My Sơn", "location": "Hội An", "activities": ["My Sơn excursion or beach"], "stay": "Hội An"},
            {"day": 7, "title": "Flight to HCMC", "location": "Ho Chi Minh City", "activities": ["Flight Đà Nẵng → SGN", "District 1"], "stay": "HCMC"},
            {"day": 8, "title": "Ho Chi Minh City", "location": "HCMC", "activities": ["War Museum", "Bến Thành Market"], "stay": "HCMC"},
            {"day": 9, "title": "Mekong Delta", "location": "Mekong", "activities": ["1-day canals & markets excursion"], "stay": "HCMC"},
            {"day": 10, "title": "Departure", "location": "HCMC", "activities": ["Last-minute shopping", "Return flight"], "stay": "—"},
        ],
    },
    "15-days-vietnam": ITINERARY_15_DAYS_EN,
}
