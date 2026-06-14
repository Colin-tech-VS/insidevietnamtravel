"""Calendrier événementiel Vietnam — saisons culturelles 2026-2027."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from locales.ui import t as ui_t

# Saison affichée : janvier 2026 → décembre 2027
CALENDAR_START = date(2026, 1, 1)
CALENDAR_END = date(2027, 12, 31)

CATEGORIES = ("national", "culture", "religious", "local", "recurring")

REGION_KEYS = ("north", "central", "south", "mekong", "nationwide")


def _pick(block: dict, lang: str) -> str:
    return block.get(lang, block.get("fr", ""))


def _parse(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()


def _status(start: date, end: date, today: date) -> str:
    if today < start:
        return "upcoming"
    if today > end:
        return "past"
    return "ongoing"


def _format_range(start: date, end: date, lang: str) -> str:
    locale = "en-GB" if lang == "en" else "fr-FR"
    if start == end:
        return start.strftime("%d/%m/%Y") if lang == "fr" else start.strftime("%b %d, %Y")
    same_month = start.year == end.year and start.month == end.month
    if lang == "fr":
        if same_month:
            return f"{start.day}–{end.day} {start.strftime('%b %Y').replace('.', '')}"
        return f"{start.strftime('%d %b %Y').replace('.', '')} – {end.strftime('%d %b %Y').replace('.', '')}"
    if same_month:
        return f"{start.strftime('%b')} {start.day}–{end.day}, {start.year}"
    return f"{start.strftime('%b %d, %Y')} – {end.strftime('%b %d, %Y')}"


# ── Événements (contenu bilingue + occurrences datées) ─────────────────

EVENTS: list[dict] = [
    {
        "key": "new_year",
        "icon": "🎆",
        "category": "national",
        "regions": ["nationwide"],
        "destinations": ["hanoi", "ho-chi-minh-city"],
        "must_see": False,
        "title": {
            "fr": "Nouvel An grégorien",
            "en": "New Year's Day",
        },
        "summary": {
            "fr": "Feux d'artifice à Hanoï et Saigon, ambiance festive en centre-ville.",
            "en": "Fireworks in Hanoi and Saigon, festive atmosphere downtown.",
        },
        "body": {
            "fr": "Le 1er janvier est férié. Les grandes villes organisent countdowns et feux "
                  "d'artifice (Hoàn Kiếm, Nguyễn Huệ). Réservez hôtels et trains à l'avance.",
            "en": "January 1 is a public holiday. Major cities host countdowns and fireworks "
                  "(Hoàn Kiếm, Nguyễn Huệ). Book hotels and trains early.",
        },
        "tip": {
            "fr": "Combinez avec le Têt quelques semaines plus tard pour une immersion totale.",
            "en": "Combine with Tết a few weeks later for full cultural immersion.",
        },
        "lunar": {"fr": "", "en": ""},
        "occurrences": [
            {"start": "2026-01-01", "end": "2026-01-01"},
            {"start": "2027-01-01", "end": "2027-01-01"},
        ],
    },
    {
        "key": "tet",
        "icon": "🧧",
        "category": "culture",
        "regions": ["nationwide"],
        "destinations": ["hanoi", "hoi-an", "ho-chi-minh-city"],
        "must_see": True,
        "title": {
            "fr": "Tết — Nouvel An lunaire",
            "en": "Tết — Lunar New Year",
        },
        "summary": {
            "fr": "LA fête du Vietnam : familles, temples, fleurs, feux d'artifice et traditions.",
            "en": "THE Vietnamese celebration: family, temples, flowers, fireworks and traditions.",
        },
        "body": {
            "fr": "Période la plus importante de l'année. Marchés aux fleurs (Hanoi : Quảng Ba ; "
                  "Saigon : Nguyễn Huệ), visites aux ancêtres, enveloppes rouges (lì xì), "
                  "danses de dragon/lion. Beaucoup de commerces ferment 3–7 jours.",
            "en": "The most important time of year. Flower markets (Hanoi: Quảng Ba; Saigon: "
                  "Nguyễn Huệ), ancestor visits, red envelopes (lì xì), dragon/lion dances. "
                  "Many businesses close for 3–7 days.",
        },
        "tip": {
            "fr": "Réservez transport et hébergement très tôt. Idéal pour l'ambiance, moins pour "
                  "plages bondées ou musées fermés.",
            "en": "Book transport and stays very early. Great for atmosphere, less for crowded "
                  "beaches or closed museums.",
        },
        "lunar": {
            "fr": "1er jour du calendrier lunaire (Mùng 1 Tết)",
            "en": "1st day of the lunar calendar (Mùng 1 Tết)",
        },
        "occurrences": [
            {"start": "2026-02-14", "end": "2026-02-23"},
            {"start": "2027-02-05", "end": "2027-02-14"},
        ],
    },
    {
        "key": "perfume_pagoda",
        "icon": "🏔️",
        "category": "religious",
        "regions": ["north"],
        "destinations": ["hanoi"],
        "must_see": True,
        "title": {
            "fr": "Pèlerinage Chùa Hương (Pagode des Parfums)",
            "en": "Perfume Pagoda pilgrimage (Chùa Hương)",
        },
        "summary": {
            "fr": "Plus grande procession bouddhiste du Nord — barques, grottes et montagne sacrée.",
            "en": "Northern Vietnam's largest Buddhist pilgrimage — boats, caves and sacred peaks.",
        },
        "body": {
            "fr": "Des milliers de pèlerins montent en barque sur la rivière Yen, puis en câble "
                  "ou à pied vers les grottes sacrées (Huong Tich). Ambiance authentique à 2 h "
                  "de Hanoï.",
            "en": "Thousands of pilgrims take boats on the Yen River, then cable car or hike to "
                  "sacred caves (Huong Tich). Authentic atmosphere, 2 h from Hanoi.",
        },
        "tip": {
            "fr": "Partez tôt un jour de semaine pour éviter la foule du week-end.",
            "en": "Go early on a weekday to avoid weekend crowds.",
        },
        "lunar": {
            "fr": "Du 6e jour du 1er mois lunaire à la fin du 3e mois",
            "en": "From the 6th day of the 1st lunar month through the 3rd month",
        },
        "occurrences": [
            {"start": "2026-02-22", "end": "2026-04-15"},
            {"start": "2027-02-11", "end": "2027-04-05"},
        ],
    },
    {
        "key": "lim_festival",
        "icon": "🎭",
        "category": "local",
        "regions": ["north"],
        "destinations": ["hanoi"],
        "must_see": True,
        "title": {
            "fr": "Hội Lim — quan họ (Bắc Ninh)",
            "en": "Lim Festival — quan họ folk singing (Bắc Ninh)",
        },
        "summary": {
            "fr": "Chants traditionnels en duo sur bateaux et pagodes — patrimoine UNESCO.",
            "en": "Traditional duet singing on boats and pagodas — UNESCO heritage.",
        },
        "body": {
            "fr": "Festival du quan họ : chants alternés entre « frères » et « sœurs » de villages "
                  "voisins, costumes traditionnels, jeux et processions. Excursion depuis Hanoï.",
            "en": "Quan họ festival: alternating songs between 'brother' and 'sister' villages, "
                  "traditional dress, games and processions. Day trip from Hanoi.",
        },
        "tip": {
            "fr": "Le jour le plus animé est le 13e jour du 1er mois lunaire.",
            "en": "The liveliest day is the 13th day of the 1st lunar month.",
        },
        "lunar": {
            "fr": "13e jour du 1er mois lunaire",
            "en": "13th day of the 1st lunar month",
        },
        "occurrences": [
            {"start": "2026-03-01", "end": "2026-03-01"},
            {"start": "2027-02-19", "end": "2027-02-19"},
        ],
    },
    {
        "key": "hung_kings",
        "icon": "🏛️",
        "category": "national",
        "regions": ["north"],
        "destinations": ["hanoi", "hue"],
        "must_see": False,
        "title": {
            "fr": "Giỗ Tổ Hùng Vương — ancêtres fondateurs",
            "en": "Hung Kings Commemoration Day",
        },
        "summary": {
            "fr": "Jour férié national — cérémonies au temple Den Hung (Phú Thọ).",
            "en": "National holiday — ceremonies at Den Hung temple (Phú Thọ).",
        },
        "body": {
            "fr": "Hommage aux rois Hùng, fondateurs légendaires du Vietnam. Processions, "
                  "offrandes de banh chung et bánh dày. Le temple Den Hung accueille des "
                  "milliers de visiteurs.",
            "en": "Tribute to the legendary Hùng kings. Processions and offerings of banh chung "
                  "and bánh dày. Den Hung temple draws thousands of visitors.",
        },
        "tip": {
            "fr": "Combinez avec une excursion vers la province de Phú Thọ depuis Hanoï.",
            "en": "Combine with a day trip to Phú Thọ province from Hanoi.",
        },
        "lunar": {
            "fr": "10e jour du 3e mois lunaire",
            "en": "10th day of the 3rd lunar month",
        },
        "occurrences": [
            {"start": "2026-04-27", "end": "2026-04-27"},
            {"start": "2027-04-16", "end": "2027-04-16"},
        ],
    },
    {
        "key": "reunification",
        "icon": "🇻🇳",
        "category": "national",
        "regions": ["south"],
        "destinations": ["ho-chi-minh-city"],
        "must_see": False,
        "title": {
            "fr": "30 avril — Réunification & 1er mai",
            "en": "April 30 — Reunification & May Day",
        },
        "summary": {
            "fr": "Double fête à Saigon : chute de Saigon (1975) et Fête du Travail.",
            "en": "Double holiday in Saigon: Fall of Saigon (1975) and Labour Day.",
        },
        "body": {
            "fr": "Cérémonies au Palais de la Réunification, défilés et long week-end très "
                  "fréquenté. Le centre-ville est animé ; réservez tôt.",
            "en": "Ceremonies at Reunification Palace, parades and a busy long weekend. "
                  "Downtown buzzes — book ahead.",
        },
        "tip": {
            "fr": "Visitez le Palais de la Réunification tôt le 30 avril.",
            "en": "Visit Reunification Palace early on April 30.",
        },
        "lunar": {"fr": "", "en": ""},
        "occurrences": [
            {"start": "2026-04-30", "end": "2026-05-01"},
            {"start": "2027-04-30", "end": "2027-05-01"},
        ],
    },
    {
        "key": "hue_festival",
        "icon": "👑",
        "category": "culture",
        "regions": ["central"],
        "destinations": ["hue"],
        "must_see": True,
        "title": {
            "fr": "Festival de Huế",
            "en": "Hue Festival",
        },
        "summary": {
            "fr": "Grand rendez-vous culturel impérial — spectacles, gastronomie et patrimoine.",
            "en": "Major imperial culture festival — shows, food and heritage.",
        },
        "body": {
            "fr": "Édition biennale (dates confirmées par la province). Défilés en costumes "
                  "impériaux, art royal, cuisine de la cour, spectacles nocturnes dans la "
                  "citadelle. Ambiance unique dans l'ancienne capitale.",
            "en": "Biennial edition (dates confirmed by the province). Imperial costume parades, "
                  "royal art, court cuisine, night shows in the citadel. Unique atmosphere in "
                  "the former capital.",
        },
        "tip": {
            "fr": "Vérifiez le programme officiel quelques mois avant — les dates varient.",
            "en": "Check the official programme a few months ahead — dates vary.",
        },
        "lunar": {"fr": "", "en": ""},
        "occurrences": [
            {"start": "2026-04-25", "end": "2026-05-05"},
        ],
    },
    {
        "key": "hoi_an_lantern",
        "icon": "🏮",
        "category": "recurring",
        "regions": ["central"],
        "destinations": ["hoi-an"],
        "must_see": True,
        "title": {
            "fr": "Hội An — nuits aux lanternes",
            "en": "Hội An — lantern nights",
        },
        "summary": {
            "fr": "Chaque soir et pleine lune : vieille ville illuminée, lanternes flottantes.",
            "en": "Every evening and full moon: old town lit up, floating lanterns.",
        },
        "body": {
            "fr": "Le centre piéton s'éteint le soir ; lumières tamisées et lanternes colorées. "
                  "Le 14e jour de chaque mois lunaire : festival des lanternes flottantes sur "
                  "la rivière Thu Bồn — le plus magique.",
            "en": "The pedestrian centre dims at night; soft lights and colourful lanterns. "
                  "On the 14th lunar day each month: floating lantern festival on the Thu Bồn "
                  "River — the most magical.",
        },
        "tip": {
            "fr": "Réservez 2 nuits minimum. Évitez le Tết si vous voulez les tailleurs ouverts.",
            "en": "Book at least 2 nights. Avoid Tết if you need tailors open.",
        },
        "lunar": {
            "fr": "14e jour de chaque mois lunaire (festival des lanternes flottantes)",
            "en": "14th day of each lunar month (floating lantern festival)",
        },
        "occurrences": [
            {"start": "2026-01-01", "end": "2027-12-31", "recurring": True},
        ],
    },
    {
        "key": "danang_fireworks",
        "icon": "🎇",
        "category": "culture",
        "regions": ["central"],
        "destinations": ["da-nang"],
        "must_see": False,
        "title": {
            "fr": "Festival international des feux d'artifice — Đà Nẵng",
            "en": "Đà Nẵng International Fireworks Festival (DIFF)",
        },
        "summary": {
            "fr": "Compétition de feux d'artifice sur la baie de Han — dates à confirmer.",
            "en": "Fireworks competition on Han Bay — dates to be confirmed.",
        },
        "body": {
            "fr": "L'un des plus grands événements de la côte Centre quand il est organisé. "
                  "Plages, Dragon Bridge et rivière Han en fête plusieurs soirs.",
            "en": "One of Central Vietnam's biggest events when held. Beaches, Dragon Bridge "
                  "and Han River celebrate for several nights.",
        },
        "tip": {
            "fr": "Consultez le site de la ville de Đà Nẵng pour l'édition en cours.",
            "en": "Check Đà Nẵng city website for the current edition.",
        },
        "lunar": {"fr": "", "en": ""},
        "occurrences": [
            {"start": "2026-06-01", "end": "2026-06-30"},
        ],
    },
    {
        "key": "vu_lan",
        "icon": "🕯️",
        "category": "religious",
        "regions": ["nationwide"],
        "destinations": ["hanoi", "ho-chi-minh-city", "hue"],
        "must_see": False,
        "title": {
            "fr": "Vu Lan — fête des morts (Rằm tháng 7)",
            "en": "Vu Lan — Wandering Souls Day (7th lunar month)",
        },
        "summary": {
            "fr": "Offrandes aux ancêtres, temples bondés, cérémonies bouddhistes.",
            "en": "Ancestor offerings, packed temples, Buddhist ceremonies.",
        },
        "body": {
            "fr": "Deuxième fête la plus importante après le Tết pour les familles vietnamiennes. "
                  "Pagodes et temples accueillent processions et repas végétariens.",
            "en": "Second most important family festival after Tết. Pagodas and temples host "
                  "processions and vegetarian meals.",
        },
        "tip": {
            "fr": "Respectez le recueillement dans les pagodes ; tenue couvrante.",
            "en": "Respect quiet devotion in pagodes; dress modestly.",
        },
        "lunar": {
            "fr": "15e jour du 7e mois lunaire",
            "en": "15th day of the 7th lunar month",
        },
        "occurrences": [
            {"start": "2026-08-28", "end": "2026-08-28"},
            {"start": "2027-08-18", "end": "2027-08-18"},
        ],
    },
    {
        "key": "national_day",
        "icon": "🎌",
        "category": "national",
        "regions": ["nationwide"],
        "destinations": ["hanoi", "ho-chi-minh-city"],
        "must_see": False,
        "title": {
            "fr": "Fête nationale — 2 septembre",
            "en": "National Day — September 2",
        },
        "summary": {
            "fr": "Indépendance (1945) : défilé à Ba Đình (Hanoï), feux d'artifice.",
            "en": "Independence (1945): parade at Ba Đình (Hanoi), fireworks.",
        },
        "body": {
            "fr": "Jour férié majeur. Cérémonie au mausolée Hô Chi Minh (Hanoï), drapeaux "
                  "rouges partout, feux d'artifice le soir. Long week-end très fréquenté.",
            "en": "Major public holiday. Ceremony at Ho Chi Minh Mausoleum (Hanoi), red flags "
                  "everywhere, evening fireworks. Busy long weekend.",
        },
        "tip": {
            "fr": "Le mausolée est fermé plusieurs jours — vérifiez avant de planifier.",
            "en": "Mausoleum closes for several days — check before planning.",
        },
        "lunar": {"fr": "", "en": ""},
        "occurrences": [
            {"start": "2026-09-02", "end": "2026-09-02"},
            {"start": "2027-09-02", "end": "2027-09-02"},
        ],
    },
    {
        "key": "mid_autumn",
        "icon": "🥮",
        "category": "culture",
        "regions": ["nationwide"],
        "destinations": ["hanoi", "hoi-an", "ho-chi-minh-city"],
        "must_see": True,
        "title": {
            "fr": "Tết Trung Thu — fête de la mi-automne",
            "en": "Mid-Autumn Festival (Tết Trung Thu)",
        },
        "summary": {
            "fr": "Lanternes, gâteaux de lune, danses de lion pour les enfants.",
            "en": "Lanterns, mooncakes, lion dances for children.",
        },
        "body": {
            "fr": "Fête familiale sous la pleine lune. Enfants défilent avec lanternes en forme "
                  "de poisson ou étoile ; gâteaux de lune (bánh trung thu) partout. "
                  "Hội An et les quartiers chinois de Saigon/Cholon sont particulièrement "
                  "festifs.",
            "en": "Family festival under the full moon. Children parade with fish- or star-shaped "
                  "lanterns; mooncakes (bánh trung thu) everywhere. Hội An and Saigon's "
                  "Cholon are especially festive.",
        },
        "tip": {
            "fr": "Goûtez les gâteaux de lune traditionnels (noix, pâte de haricot).",
            "en": "Try traditional mooncakes (nuts, bean paste).",
        },
        "lunar": {
            "fr": "15e jour du 8e mois lunaire (pleine lune)",
            "en": "15th day of the 8th lunar month (full moon)",
        },
        "occurrences": [
            {"start": "2026-09-25", "end": "2026-09-25"},
            {"start": "2027-09-15", "end": "2027-09-15"},
        ],
    },
    {
        "key": "kate_festival",
        "icon": "🛕",
        "category": "religious",
        "regions": ["south"],
        "destinations": ["da-nang"],
        "must_see": True,
        "title": {
            "fr": "Kate — fête des Cham (Ninh Thuận)",
            "en": "Kate Festival — Cham culture (Ninh Thuận)",
        },
        "summary": {
            "fr": "Plus grande célébration du peuple Cham — tours de briques et rituels.",
            "en": "Largest Cham people celebration — brick towers and rituals.",
        },
        "body": {
            "fr": "Hommage aux ancêtres et aux divinités dans les tours Cham (Po Klong Garai, "
                  "Po Rome). Costumes traditionnels, danses et musique. Excursion depuis "
                  "Đà Nẵng ou Nha Trang.",
            "en": "Tribute to ancestors and deities at Cham towers (Po Klong Garai, Po Rome). "
                  "Traditional dress, dance and music. Trip from Đà Nẵng or Nha Trang.",
        },
        "tip": {
            "fr": "Demandez permission avant de photographier les cérémonies.",
            "en": "Ask permission before photographing ceremonies.",
        },
        "lunar": {
            "fr": "Fin du 7e mois lunaire (calendrier Cham)",
            "en": "End of the 7th lunar month (Cham calendar)",
        },
        "occurrences": [
            {"start": "2026-10-11", "end": "2026-10-15"},
            {"start": "2027-10-01", "end": "2027-10-05"},
        ],
    },
    {
        "key": "ok_om_bok",
        "icon": "🌾",
        "category": "religious",
        "regions": ["mekong"],
        "destinations": ["delta-du-mekong"],
        "must_see": True,
        "title": {
            "fr": "Ok Om Bok — fête Khmer (Lễ Óc Om Bóc)",
            "en": "Ok Om Bok — Khmer water festival (Mekong Delta)",
        },
        "summary": {
            "fr": "Remerciements à la lune pour la récolte — courses de bateaux à Soc Trang.",
            "en": "Moon thanksgiving for the harvest — boat races in Soc Trang.",
        },
        "body": {
            "fr": "Communauté Khmer du delta : offrandes de riz au clair de lune, pagodes "
                  "animées, regatta traditionnelle (Ghe Ngo). Couleurs, musique et street food.",
            "en": "Mekong Khmer community: rice offerings by moonlight, lively pagodas, "
                  "traditional regatta (Ghe Ngo). Colour, music and street food.",
        },
        "tip": {
            "fr": "Base à Cần Thơ ou Sóc Trăng ; combinez avec un marché flottant.",
            "en": "Base in Cần Thơ or Sóc Trăng; combine with a floating market.",
        },
        "lunar": {
            "fr": "15e jour du 10e mois lunaire",
            "en": "15th day of the 10th lunar month",
        },
        "occurrences": [
            {"start": "2026-11-14", "end": "2026-11-14"},
            {"start": "2027-11-03", "end": "2027-11-03"},
        ],
    },
    {
        "key": "floating_market_peak",
        "icon": "🛶",
        "category": "local",
        "regions": ["mekong"],
        "destinations": ["delta-du-mekong"],
        "must_see": False,
        "title": {
            "fr": "Saison haute des marchés flottants",
            "en": "Floating markets peak season",
        },
        "summary": {
            "fr": "Cái Răng, Cai Be au lever du soleil — meilleure période nov.–jan.",
            "en": "Cái Răng, Cai Be at sunrise — best Nov.–Jan.",
        },
        "body": {
            "fr": "Après la mousson, le Mékong est généreux : fruits tropicaux, barges "
                  "chargées, café local à bord. Expérience incontournable du Sud.",
            "en": "After monsoon, the Mekong runs high: tropical fruit, loaded boats, local "
                  "coffee on board. Unmissable Southern experience.",
        },
        "tip": {
            "fr": "Départ 5h–6h du matin depuis Cần Thơ.",
            "en": "Leave 5–6 a.m. from Cần Thơ.",
        },
        "lunar": {"fr": "", "en": ""},
        "occurrences": [
            {"start": "2026-11-01", "end": "2027-01-31"},
        ],
    },
    {
        "key": "sapa_festival",
        "icon": "🌾",
        "category": "local",
        "regions": ["north"],
        "destinations": ["sapa"],
        "must_see": True,
        "title": {
            "fr": "Saison dorée — rizières de Sapa",
            "en": "Golden season — Sapa rice terraces",
        },
        "summary": {
            "fr": "Récolte et festivals ethniques (Hmong, Dao) — sept. à nov.",
            "en": "Harvest and ethnic festivals (Hmong, Dao) — Sept. to Nov.",
        },
        "body": {
            "fr": "Rizières en or, marchés hebdomadaires des minorités (Bac Ha, Muong Hum), "
                  "randonnées et homestays. Les villages célèbrent la fin des moissons.",
            "en": "Golden terraces, weekly minority markets (Bac Ha, Muong Hum), trekking and "
                  "homestays. Villages celebrate the end of harvest.",
        },
        "tip": {
            "fr": "Réservez guide et homestay à l'avance en octobre.",
            "en": "Book guides and homestays ahead for October.",
        },
        "lunar": {"fr": "", "en": ""},
        "occurrences": [
            {"start": "2026-09-01", "end": "2026-11-30"},
            {"start": "2027-09-01", "end": "2027-11-30"},
        ],
    },
    {
        "key": "halong_cruise_peak",
        "icon": "⛵",
        "category": "local",
        "regions": ["north"],
        "destinations": ["halong"],
        "must_see": False,
        "title": {
            "fr": "Haute saison croisières — baie d'Halong",
            "en": "Cruise peak season — Halong Bay",
        },
        "summary": {
            "fr": "Oct.–avr. : mer calme, ciel dégagé — réserver tôt pour le Tết.",
            "en": "Oct.–Apr.: calm seas, clear skies — book early for Tết.",
        },
        "body": {
            "fr": "Meilleure période pour une nuit sur jonque. Évitez juillet–août (typhons) "
                  "et le Tết si vous voulez moins de monde à bord.",
            "en": "Best time for an overnight junk cruise. Avoid July–August (typhoons) and "
                  "Tết if you want fewer crowds on board.",
        },
        "tip": {
            "fr": "Choisissez un opérateur certifié et une cabine avec hublot.",
            "en": "Pick a certified operator and a cabin with a porthole.",
        },
        "lunar": {"fr": "", "en": ""},
        "occurrences": [
            {"start": "2026-10-01", "end": "2027-04-30"},
        ],
    },
    {
        "key": "christmas",
        "icon": "🎄",
        "category": "culture",
        "regions": ["south", "central"],
        "destinations": ["ho-chi-minh-city", "hoi-an"],
        "must_see": False,
        "title": {
            "fr": "Noël & décorations — Saigon & Hội An",
            "en": "Christmas & decorations — Saigon & Hội An",
        },
        "summary": {
            "fr": "Cathédrale Notre-Dame, rue Nguyen Hue illuminée, ambiance festive.",
            "en": "Notre-Dame Cathedral, lit-up Nguyen Hue, festive mood.",
        },
        "body": {
            "fr": "Noël n'est pas férié mais très visible à Saigon (communauté catholique, "
                  "centres commerciaux). Hội An combine lanternes vietnamiennes et guirlandes.",
            "en": "Christmas isn't a public holiday but very visible in Saigon (Catholic "
                  "community, malls). Hội An mixes Vietnamese lanterns and fairy lights.",
        },
        "tip": {
            "fr": "Messe de minuit à la cathédrale Notre-Dame (places limitées).",
            "en": "Midnight mass at Notre-Dame Cathedral (limited seats).",
        },
        "lunar": {"fr": "", "en": ""},
        "occurrences": [
            {"start": "2026-12-20", "end": "2026-12-26"},
            {"start": "2027-12-20", "end": "2027-12-26"},
        ],
    },
]

# Dates clés 14e jour lunaire (lanternes flottantes Hội An) 2026-2027
HOI_AN_FULL_MOON_2026_2027: list[dict] = [
    {"start": "2026-03-02", "end": "2026-03-02", "label_fr": "Mars 2026", "label_en": "March 2026"},
    {"start": "2026-04-01", "end": "2026-04-01", "label_fr": "Avril 2026", "label_en": "April 2026"},
    {"start": "2026-04-30", "end": "2026-04-30", "label_fr": "Fin avril 2026", "label_en": "Late Apr 2026"},
    {"start": "2026-05-30", "end": "2026-05-30", "label_fr": "Mai 2026", "label_en": "May 2026"},
    {"start": "2026-06-28", "end": "2026-06-28", "label_fr": "Juin 2026", "label_en": "June 2026"},
    {"start": "2026-07-27", "end": "2026-07-27", "label_fr": "Juil. 2026", "label_en": "July 2026"},
    {"start": "2026-08-26", "end": "2026-08-26", "label_fr": "Août 2026", "label_en": "Aug 2026"},
    {"start": "2026-09-24", "end": "2026-09-24", "label_fr": "Sept. 2026", "label_en": "Sept 2026"},
    {"start": "2026-10-24", "end": "2026-10-24", "label_fr": "Oct. 2026", "label_en": "Oct 2026"},
    {"start": "2026-11-22", "end": "2026-11-22", "label_fr": "Nov. 2026", "label_en": "Nov 2026"},
    {"start": "2026-12-22", "end": "2026-12-22", "label_fr": "Déc. 2026", "label_en": "Dec 2026"},
    {"start": "2027-01-20", "end": "2027-01-20", "label_fr": "Janv. 2027", "label_en": "Jan 2027"},
    {"start": "2027-02-19", "end": "2027-02-19", "label_fr": "Fév. 2027", "label_en": "Feb 2027"},
    {"start": "2027-03-20", "end": "2027-03-20", "label_fr": "Mars 2027", "label_en": "March 2027"},
]


def _dest_label(slug: str, lang: str, destinations: dict | None) -> str:
    if destinations and slug in destinations:
        return destinations[slug].get("name", slug)
    return slug.replace("-", " ").title()


def build_events_calendar(
    lang: str,
    *,
    destinations: dict | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Calendrier localisé pour la page vitrine événements."""
    lang = "en" if lang == "en" else "fr"
    today = today or date.today()

    flat: list[dict] = []
    for ev in EVENTS:
        for occ in ev.get("occurrences", []):
            start = _parse(occ["start"])
            end = _parse(occ["end"])
            if end < CALENDAR_START or start > CALENDAR_END:
                continue
            is_recurring = bool(occ.get("recurring"))
            dest_slugs = ev.get("destinations") or []
            flat.append({
                "id": f"{ev['key']}-{occ['start']}",
                "event_key": ev["key"],
                "icon": ev.get("icon", "✦"),
                "category": ev["category"],
                "category_label": ui_t(f"events.cat.{ev['category']}", lang),
                "title": _pick(ev["title"], lang),
                "summary": _pick(ev["summary"], lang),
                "body": _pick(ev["body"], lang),
                "tip": _pick(ev.get("tip", {}), lang),
                "lunar_note": _pick(ev.get("lunar", {}), lang),
                "start": occ["start"],
                "end": occ["end"],
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "date_label": _format_range(start, end, lang),
                "year": start.year,
                "month": start.month,
                "regions": ev.get("regions") or [],
                "region_labels": [ui_t(f"events.region.{r}", lang) for r in ev.get("regions") or []],
                "destinations": [
                    {"slug": s, "name": _dest_label(s, lang, destinations)}
                    for s in dest_slugs
                ],
                "must_see": bool(ev.get("must_see")),
                "recurring": is_recurring,
                "status": "recurring" if is_recurring else _status(start, end, today),
            })

    flat.sort(key=lambda x: (x["start"], x["title"]))

    upcoming = [e for e in flat if e["status"] in ("upcoming", "ongoing", "recurring")]
    highlights = [e for e in flat if e["must_see"] and e["status"] != "past"]

    moon_dates = [
        {
            "start": d["start"],
            "label": d["label_en"] if lang == "en" else d["label_fr"],
            "status": _status(_parse(d["start"]), _parse(d["end"]), today),
        }
        for d in HOI_AN_FULL_MOON_2026_2027
    ]

    return {
        "season_label": "2026–2027",
        "today": today.isoformat(),
        "categories": [
            {"key": k, "label": ui_t(f"events.cat.{k}", lang)} for k in CATEGORIES
        ],
        "month_labels": [
            ui_t(f"events.month.{m}", lang) for m in range(1, 13)
        ],
        "events": flat,
        "upcoming": upcoming,
        "highlights": highlights[:8],
        "hoi_an_moon_dates": moon_dates,
        "stats": {
            "total": len(flat),
            "must_see": sum(1 for e in flat if e["must_see"]),
            "upcoming": len(upcoming),
        },
    }
