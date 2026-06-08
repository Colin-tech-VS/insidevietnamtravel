"""Villes et régions du Vietnam — pour sélecteur admin."""

# value = nom affiché et envoyé à l'IA (orthographe correcte)
VIETNAM_CITIES = {
    "Tout le Vietnam": [
        {"value": "Tout le Vietnam", "label": "🇻🇳 Tout le Vietnam (guide national)"},
    ],
    "Nord": [
        {"value": "Hanoï", "label": "Hanoï"},
        {"value": "Ha Long / Quảng Ninh", "label": "Ha Long / Quảng Ninh"},
        {"value": "Ninh Bình", "label": "Ninh Bình"},
        {"value": "Sapa / Lào Cai", "label": "Sapa / Lào Cai"},
        {"value": "Ha Giang", "label": "Ha Giang"},
        {"value": "Mai Châu", "label": "Mai Châu"},
        {"value": "Cát Bà", "label": "Cát Bà"},
        {"value": "Tam Đảo", "label": "Tam Đảo"},
    ],
    "Centre": [
        {"value": "Huế", "label": "Huế"},
        {"value": "Hội An", "label": "Hội An"},
        {"value": "Đà Nẵng", "label": "Đà Nẵng"},
        {"value": "Nha Trang", "label": "Nha Trang"},
        {"value": "Đà Lạt / Lâm Đồng", "label": "Đà Lạt / Lâm Đồng"},
        {"value": "Quy Nhơn", "label": "Quy Nhơn"},
        {"value": "Phong Nha", "label": "Phong Nha / Quảng Bình"},
        {"value": "My Sơn", "label": "My Sơn"},
    ],
    "Sud": [
        {"value": "Ho Chi Minh-Ville", "label": "Ho Chi Minh-Ville (Saigon)"},
        {"value": "Mỹ Tho / Delta Mekong", "label": "Mỹ Tho / Delta du Mékong"},
        {"value": "Cần Thơ", "label": "Cần Thơ"},
        {"value": "Vũng Tàu", "label": "Vũng Tàu"},
        {"value": "Phú Quốc", "label": "Phú Quốc"},
        {"value": "Côn Đảo", "label": "Côn Đảo"},
        {"value": "Mũi Né / Phan Thiết", "label": "Mũi Né / Phan Thiết"},
        {"value": "Củ Chi", "label": "Củ Chi"},
    ],
}

ALL_CITY_VALUES = [
    c["value"]
    for cities in VIETNAM_CITIES.values()
    for c in cities
]

GUIDE_TYPES = [
    {"value": "Article blog SEO", "label": "Article blog SEO", "icon": "📝"},
    {"value": "Guide pratique", "label": "Guide pratique", "icon": "📋"},
    {"value": "Guide ville", "label": "Guide ville", "icon": "🏙️"},
    {"value": "Itinéraire", "label": "Itinéraire", "icon": "🗺️"},
    {"value": "Conseils budget", "label": "Conseils budget", "icon": "💰"},
    {"value": "Gastronomie", "label": "Gastronomie & street food", "icon": "🍜"},
]
