"""Calendrier événementiel Vietnam — saisons culturelles 2026-2027."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from locales.ui import t as ui_t
from i18n_utils import lang_url

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

def _pick_list(block: dict, lang: str) -> list[str]:
    return list(block.get(lang, block.get("fr", [])))


def _image_hd(path: str) -> str:
    """Variante haute résolution pour le modal (évite le flou des vignettes)."""
    if path.endswith("-640.webp"):
        return path.replace("-640.webp", "-960.webp")
    if path.endswith(".webp") and not path.endswith("-960.webp"):
        return path.replace(".webp", "-960.webp")
    return path


def _status_label(status: str, lang: str) -> str:
    key = {
        "upcoming": "events.status_upcoming",
        "ongoing": "events.status_ongoing",
        "past": "events.status_past",
        "recurring": "events.status_recurring",
    }.get(status, "")
    return ui_t(key, lang) if key else ""


# Images + contenu enrichi par événement (clé = EVENTS[].key)
EVENT_ENRICHMENT: dict[str, dict] = {
    "new_year": {
        "image": "/static/images/destinations/ho-chi-minh-city.webp",
        "image_alt": {
            "fr": "Saigon illuminée pour le Nouvel An",
            "en": "Saigon lit up for New Year",
        },
        "highlights": {
            "fr": [
                "Feux d'artifice sur la rue Nguyễn Huệ et au lac Hoàn Kiếm (Hanoï)",
                "Countdowns dans les centres commerciaux et bars des grandes villes",
                "Ambiance festive sans fermetures massives (contrairement au Tết)",
            ],
            "en": [
                "Fireworks on Nguyễn Huệ street and Hoàn Kiếm Lake (Hanoi)",
                "Countdowns in malls and bars in major cities",
                "Festive mood without mass closures (unlike Tết)",
            ],
        },
        "experience": {
            "fr": "Le 1er janvier est un jour férié officiel. À Hô-Chi-Minh-Ville, la "
                  "promenade Nguyễn Huệ — piétonne et bordée de gratte-ciel — devient le "
                  "théâtre des countdowns et des feux d'artifice. À Hanoï, le quartier du "
                  "lac Hoàn Kiếm accueille des concerts en plein air et une foule de "
                  "familles. C'est une bonne porte d'entrée avant le Têt, quelques semaines "
                  "plus tard, pour sentir l'énergie urbaine vietnamienne.",
            "en": "January 1 is an official public holiday. In Ho Chi Minh City, the pedestrian "
                  "Nguyễn Huệ boulevard — lined with skyscrapers — hosts countdowns and "
                  "fireworks. In Hanoi, the Hoàn Kiếm Lake area fills with outdoor concerts "
                  "and families. It's a good warm-up before Tết a few weeks later, to feel "
                  "Vietnam's urban energy.",
        },
        "practical": {
            "fr": [
                "Réservez hôtels et trains pour la nuit du 31 décembre",
                "Arrivez tôt pour les spots photo (Nguyễn Huệ, Hoàn Kiếm)",
                "Transport local limité après minuit — prévoyez Grab à l'avance",
            ],
            "en": [
                "Book hotels and trains for December 31 night",
                "Arrive early for photo spots (Nguyễn Huệ, Hoàn Kiếm)",
                "Limited local transport after midnight — plan Grab ahead",
            ],
        },
    },
    "tet": {
        "image": "/static/images/destinations/hanoi.webp",
        "image_alt": {
            "fr": "Hanoï pendant le Têt — marchés aux fleurs et décorations",
            "en": "Hanoi during Tết — flower markets and decorations",
        },
        "highlights": {
            "fr": [
                "Marchés aux fleurs de Quảng Ba (Hanoï) et Nguyễn Huệ (Saigon)",
                "Enveloppes rouges lì xì, danses de dragon et de lion",
                "Visites aux ancêtres, nettoyage des maisons, repas familiaux",
                "Feux d'artifice le soir du réveillon (Giao thừa)",
            ],
            "en": [
                "Flower markets at Quảng Ba (Hanoi) and Nguyễn Huệ (Saigon)",
                "Red lì xì envelopes, dragon and lion dances",
                "Ancestor visits, house cleaning, family meals",
                "Fireworks on New Year's Eve (Giao thừa)",
            ],
        },
        "experience": {
            "fr": "Le Tết Nguyên Đán marque le début du calendrier lunaire et rythme toute la "
                  "société vietnamienne pendant une à deux semaines. Les familles rentrent au "
                  "village, les temples sont bondés d'offrandes et les rues se parent de "
                  "kumquats, d'orchidées et de branches de pêcher. Pour le voyageur, c'est "
                  "l'immersion culturelle ultime — mais aussi la période la plus contrainte : "
                  "musées fermés, tarifs flottants, plages surbookées au Sud.",
            "en": "Tết Nguyên Đán marks the lunar new year and shapes Vietnamese society for "
                  "one to two weeks. Families return to their home villages, temples overflow "
                  "with offerings and streets fill with kumquat trees, orchids and peach "
                  "blossom. For travellers it's the ultimate cultural immersion — but also "
                  "the most constrained period: museums closed, surge pricing, packed beaches "
                  "in the South.",
        },
        "practical": {
            "fr": [
                "Réservez vols, trains et hôtels 2–3 mois à l'avance",
                "Prévoir 3–7 jours de fermetures commerciales autour du 1er jour lunaire",
                "Évitez si vous comptez sur musées, tailleurs ou formalités administratives",
                "Offrir un petit lì xì (enveloppe) est apprécié chez l'hôte",
            ],
            "en": [
                "Book flights, trains and hotels 2–3 months ahead",
                "Expect 3–7 days of business closures around lunar New Year's Day",
                "Avoid if you rely on museums, tailors or admin errands",
                "A small lì xì envelope is appreciated when visiting hosts",
            ],
        },
    },
    "perfume_pagoda": {
        "image": "/static/images/pool/1578662996442-48f60103fc96.webp",
        "image_alt": {
            "fr": "Paysage montagneux du site de Chùa Hương",
            "en": "Mountain landscape at Chùa Hương",
        },
        "highlights": {
            "fr": [
                "Traversée en barque sur la rivière Yen jusqu'au pied de la montagne",
                "Grotte sacrée Huong Tich — « paradis sur terre »",
                "Téléphérique ou montée à pied à travers la végétation karstique",
                "Ambiance de pèlerinage authentique, encens et offrandes",
            ],
            "en": [
                "Boat ride on the Yen River to the mountain foot",
                "Sacred Huong Tich cave — « heaven on earth »",
                "Cable car or hike through karst vegetation",
                "Authentic pilgrimage atmosphere, incense and offerings",
            ],
        },
        "experience": {
            "fr": "Chùa Hương est le plus grand pèlerinage bouddhiste du Nord. Des dizaines "
                  "de milliers de visiteurs — croyants et curieux — empruntent les barques "
                  "traditionnelles, gravissent les marches humides et pénètrent dans la "
                  "grotte Huong Tich, éclairée au néon et saturée d'encens. L'excursion "
                  "complète depuis Hanoï dure une journée ; l'atmosphère est à la fois "
                  "spectaculaire et profondément locale.",
            "en": "Chùa Hương is the largest Buddhist pilgrimage in the North. Tens of "
                  "thousands of visitors — believers and curious travellers — take "
                  "traditional boats, climb damp steps and enter Huong Tich cave, lit by "
                  "neon and thick with incense. The full day trip from Hanoi is both "
                  "spectacular and deeply local.",
        },
        "practical": {
            "fr": [
                "Excursion d'une journée depuis Hanoï (~2 h de route)",
                "Préférez un jour de semaine hors pic du Têt",
                "Chaussures antidérapantes, eau et cash pour barques + téléphérique",
                "Tenue couvrante pour les zones sacrées",
            ],
            "en": [
                "Day trip from Hanoi (~2 h drive)",
                "Prefer a weekday outside Tết peak",
                "Non-slip shoes, water and cash for boats + cable car",
                "Modest dress in sacred areas",
            ],
        },
    },
    "lim_festival": {
        "image": "/static/images/pool/1528127269322-539801943592.webp",
        "image_alt": {
            "fr": "Festival traditionnel dans la campagne du Nord Vietnam",
            "en": "Traditional festival in northern Vietnam countryside",
        },
        "highlights": {
            "fr": [
                "Quan họ : chants en duo entre villages « frères » et « sœurs »",
                "Patrimoine oral UNESCO du delta du fleuve Rouge",
                "Costumes traditionnels, chapeaux coniques et soieries",
                "Jeux populaires, processions et offrandes sur l'eau",
            ],
            "en": [
                "Quan họ: duet singing between 'brother' and 'sister' villages",
                "UNESCO oral heritage of the Red River Delta",
                "Traditional dress, conical hats and silk",
                "Folk games, processions and water offerings",
            ],
        },
        "experience": {
            "fr": "Le festival de Lim, dans la province de Bắc Ninh, célèbre le quan họ — "
                  "art lyrique pratiqué depuis des siècles sur les bateaux et les pagodes "
                  "de campagne. Les chanteurs s'interpellent de rive à rive, entrecoupant "
                  "mélodies et plaisanteries. C'est l'une des expressions culturelles les "
                  "plus pures du Nord, accessible en excursion d'une journée depuis Hanoï.",
            "en": "The Lim festival in Bắc Ninh province celebrates quan họ — a lyrical art "
                  "practised for centuries on boats and rural pagodas. Singers call across "
                  "the water, alternating melodies and banter. It's one of the purest "
                  "cultural expressions of the North, reachable on a day trip from Hanoi.",
        },
        "practical": {
            "fr": [
                "Date clé : 13e jour du 1er mois lunaire",
                "Excursion organisée ou location de voiture avec chauffeur",
                "Arrivez tôt le matin — affluence massive l'après-midi",
                "Respectez les espaces de cérémonie, demandez avant de filmer",
            ],
            "en": [
                "Key date: 13th day of the 1st lunar month",
                "Organised tour or car with driver",
                "Arrive early morning — huge crowds by afternoon",
                "Respect ceremony spaces, ask before filming",
            ],
        },
    },
    "hung_kings": {
        "image": "/static/images/destinations/hue.webp",
        "image_alt": {
            "fr": "Temple et patrimoine historique vietnamien",
            "en": "Vietnamese temple and historical heritage",
        },
        "highlights": {
            "fr": [
                "Jour férié national — hommage aux rois Hùng fondateurs",
                "Cérémonies au temple Den Hung (province de Phú Thọ)",
                "Offrandes de banh chung (gâteau de riz carré) et bánh dày",
                "Symbolique identitaire forte pour les Vietnamiens",
            ],
            "en": [
                "National holiday — tribute to founding Hùng kings",
                "Ceremonies at Den Hung temple (Phú Thọ province)",
                "Offerings of banh chung (square rice cake) and bánh dày",
                "Strong identity symbolism for Vietnamese people",
            ],
        },
        "experience": {
            "fr": "Le 10e jour du 3e mois lunaire, le Vietnam commémore les rois Hùng, "
                  "figures légendaires de la fondation du pays. Des milliers de pèlerins "
                  "montent vers le complexe de Den Hung, dans un paysage de collines "
                  "verdoyantes à ~90 km de Hanoï. Même sans assister à la cérémonie "
                  "officielle, la journée offre un aperçu de la mémoire collective "
                  "vietnamienne.",
            "en": "On the 10th day of the 3rd lunar month, Vietnam commemorates the Hùng "
                  "kings, legendary founders of the nation. Thousands of pilgrims climb to "
                  "the Den Hung complex in green hills ~90 km from Hanoi. Even without "
                  "attending the official ceremony, the day reveals Vietnam's collective "
                  "memory.",
        },
        "practical": {
            "fr": [
                "Jour férié : administrations fermées",
                "Excursion depuis Hanoï — comptez une journée",
                "Chaleur et foule possibles — chapeau et eau",
            ],
            "en": [
                "Public holiday: offices closed",
                "Day trip from Hanoi — allow a full day",
                "Heat and crowds possible — hat and water",
            ],
        },
    },
    "reunification": {
        "image": "/static/images/pool/1609412058473-c199497c3c5d.webp",
        "image_alt": {
            "fr": "Palais de la Réunification à Saigon",
            "en": "Reunification Palace in Saigon",
        },
        "highlights": {
            "fr": [
                "30 avril : chute de Saigon et réunification (1975)",
                "1er mai : Fête internationale du Travail",
                "Cérémonies au Palais de la Réunification",
                "Long week-end très animé dans le centre-ville",
            ],
            "en": [
                "April 30: Fall of Saigon and reunification (1975)",
                "May 1: International Labour Day",
                "Ceremonies at Reunification Palace",
                "Busy long weekend downtown",
            ],
        },
        "experience": {
            "fr": "À Hô-Chi-Minh-Ville, le double holiday du 30 avril–1er mai mêle "
                  "commémoration historique et fête populaire. Le Palais de la "
                  "Réunification — symbole de la fin de la guerre — accueille des "
                  "cérémonies officielles. Les rues adjacentes se remplissent de "
                  "familles, de drapeaux et de vendeurs ambulants. C'est l'occasion "
                  "idéale de visiter le palais et les monuments voisins en une journée.",
            "en": "In Ho Chi Minh City, the April 30–May 1 double holiday blends historical "
                  "commemoration and street celebration. Reunification Palace — symbol of "
                  "the war's end — hosts official ceremonies. Nearby streets fill with "
                  "families, flags and street vendors. Ideal timing to visit the palace "
                  "and neighbouring monuments in one day.",
        },
        "practical": {
            "fr": [
                "Réservez hébergement pour le long week-end",
                "Visitez le Palais tôt le 30 avril (fermetures partielles possibles)",
                "Circulation dense — privilégiez Grab ou métro",
            ],
            "en": [
                "Book accommodation for the long weekend",
                "Visit the Palace early on April 30 (partial closures possible)",
                "Heavy traffic — use Grab or metro",
            ],
        },
    },
    "hue_festival": {
        "image": "/static/images/destinations/hue.webp",
        "image_alt": {
            "fr": "Citadelle impériale de Huế",
            "en": "Imperial citadel of Huế",
        },
        "highlights": {
            "fr": [
                "Festival biennal de la culture impériale",
                "Défilés en costumes Nguyen, musique de cour",
                "Spectacles nocturnes dans la citadelle UNESCO",
                "Gastronomie royale et artisans locaux",
            ],
            "en": [
                "Biennial imperial culture festival",
                "Nguyen dynasty costume parades, court music",
                "Night shows in UNESCO citadel",
                "Royal cuisine and local crafts",
            ],
        },
        "experience": {
            "fr": "Huế, ancienne capitale des empereurs Nguyen, accueille périodiquement un "
                  "festival majeur mêlant patrimoine, spectacles vivants et gastronomie de "
                  "cour. Les remparts, pagodes et pavillons royaux deviennent scènes "
                  "ouvertes. Les dates exactes varient selon l'édition — consultez le "
                  "programme officiel, mais l'ambiance impériale de Huế vaut le détour "
                  "toute l'année.",
            "en": "Huế, former capital of the Nguyen emperors, periodically hosts a major "
                  "festival blending heritage, live performance and court cuisine. Ramparts, "
                  "pagodas and royal pavilions become open-air stages. Exact dates vary by "
                  "edition — check the official programme — but Huế's imperial atmosphere "
                  "rewards a visit any time of year.",
        },
        "practical": {
            "fr": [
                "Vérifiez les dates sur le site du Festival de Huế",
                "Réservez hôtel dans la cité impériale ou Perfume River",
                "Billets pour spectacles nocturnes souvent limités",
            ],
            "en": [
                "Check dates on the Huế Festival website",
                "Book hotels in the imperial city or Perfume River area",
                "Night show tickets often limited",
            ],
        },
    },
    "hoi_an_lantern": {
        "image": "/static/images/pool/1559592413-7cec4d0cae2b.webp",
        "image_alt": {
            "fr": "Lanternes colorées dans la vieille ville de Hội An",
            "en": "Colourful lanterns in Hội An old town",
        },
        "highlights": {
            "fr": [
                "Centre historique piéton éteint chaque soir — éclairage aux lanternes",
                "14e jour lunaire : lanternes flottantes sur la rivière Thu Bồn",
                "Musique live, stands de nourriture et tailleurs ouverts le jour",
                "UNESCO — architecture fusion vietnamienne, chinoise et japonaise",
            ],
            "en": [
                "Pedestrian old town dims each evening — lantern lighting",
                "14th lunar day: floating lanterns on Thu Bồn River",
                "Live music, food stalls and tailors open by day",
                "UNESCO — Vietnamese, Chinese and Japanese fusion architecture",
            ],
        },
        "experience": {
            "fr": "Hội An transforme chaque nuit son centre en théâtre de lumière tamisée. "
                  "Les façades jaunes, les ponts japonais et les rives de la Thu Bồn se "
                  "reflètent dans l'eau. Le festival mensuel des lanternes flottantes "
                  "(veille de pleine lune) est le moment le plus photogénique : les "
                  "visiteurs lâchent des lanternes en papier, créant un fleuve de "
                  "couleurs. Prévoyez au minimum deux nuits sur place.",
            "en": "Hội An turns its centre into a soft-lit theatre every night. Yellow "
                  "facades, Japanese Bridge and Thu Bồn banks mirror in the water. The "
                  "monthly floating lantern festival (eve of full moon) is the most "
                  "photogenic moment: visitors release paper lanterns, creating a river "
                  "of colour. Plan at least two nights.",
        },
        "practical": {
            "fr": [
                "Ticket d'entrée vieille ville (~120 000 VND) valable plusieurs jours",
                "Réservez 2–3 nuits, surtout en pleine lune",
                "Tailleurs fermés pendant le Têt",
                "Consultez le calendrier lunaire ci-dessous pour les dates précises",
            ],
            "en": [
                "Old town entry ticket (~120,000 VND) valid several days",
                "Book 2–3 nights, especially on full moon",
                "Tailors closed during Tết",
                "See lunar calendar below for exact dates",
            ],
        },
    },
    "danang_fireworks": {
        "image": "/static/images/destinations/da-nang.webp",
        "image_alt": {
            "fr": "Skyline de Đà Nẵng et baie de Han",
            "en": "Đà Nẵng skyline and Han Bay",
        },
        "highlights": {
            "fr": [
                "Compétition internationale de feux d'artifice (DIFF)",
                "Spectacle sur la baie de Han et le Dragon Bridge",
                "Plages de My Khe et vie nocturne animée",
                "Événement phare de la côte Centre quand organisé",
            ],
            "en": [
                "International fireworks competition (DIFF)",
                "Shows on Han Bay and Dragon Bridge",
                "My Khe beach and lively nightlife",
                "Central coast flagship event when held",
            ],
        },
        "experience": {
            "fr": "Quand il se tient, le Festival international des feux d'artifice de Đà Nẵng "
                  "attire des équipes du monde entier. Les nuits de compétition transforment "
                  "la baie de Han en amphithéâtre à ciel ouvert. Le Dragon Bridge crache le "
                  "feu le week-end, les terrasses des hôtels affichent complet et la ville "
                  "pulse d'énergie estivale.",
            "en": "When held, Đà Nẵng's International Fireworks Festival draws teams from "
                  "around the world. Competition nights turn Han Bay into an open-air "
                  "amphitheatre. Dragon Bridge breathes fire on weekends, hotel rooftops "
                  "sell out and the city pulses with summer energy.",
        },
        "practical": {
            "fr": [
                "Dates à confirmer sur le site officiel de Đà Nẵng",
                "Réservez hôtel avec vue baie plusieurs mois à l'avance",
                "Circulation bloquée le long du fleuve Han les soirs de spectacle",
            ],
            "en": [
                "Confirm dates on Đà Nẵng official website",
                "Book bay-view hotels months ahead",
                "Traffic blocked along Han River on show nights",
            ],
        },
    },
    "vu_lan": {
        "image": "/static/images/pool/1557750255-c76072a7aad1.webp",
        "image_alt": {
            "fr": "Pagode vietnamienne lors d'une cérémonie",
            "en": "Vietnamese pagoda during a ceremony",
        },
        "highlights": {
            "fr": [
                "Fête des morts bouddhiste — 15e jour du 7e mois lunaire",
                "Offrandes aux ancêtres et repas végétariens",
                "Processions dans les pagodes de tout le pays",
                "Deuxième fête familiale après le Tết",
            ],
            "en": [
                "Buddhist Wandering Souls Day — 15th of 7th lunar month",
                "Ancestor offerings and vegetarian meals",
                "Processions in pagodas nationwide",
                "Second most important family festival after Tết",
            ],
        },
        "experience": {
            "fr": "Vu Lan (Rằm tháng 7) est le moment où les Vietnamiens honorent les ancêtres "
                  "défunts. Les pagodes — de la Pagode des Jade à Saigon au temple Literature "
                  "à Hanoï — regorgent d'encens, de fruits et de fidèles en tenue sombre. "
                  "Les restaurants proposent des menus chay (végétariens). L'atmosphère est "
                  "recueillie ; idéal pour observer les rituels avec respect.",
            "en": "Vu Lan (7th month full moon) is when Vietnamese honour deceased ancestors. "
                  "Pagodas — from Jade Emperor in Saigon to Temple of Literature in Hanoi — "
                  "overflow with incense, fruit and devotees in dark clothing. Restaurants "
                  "serve chay (vegetarian) menus. The mood is contemplative; ideal for "
                  "observing rituals respectfully.",
        },
        "practical": {
            "fr": [
                "Tenue couvrante (épaules et genoux) dans les pagodes",
                "Retirez chaussures et chapeau à l'entrée",
                "Demandez avant de photographier les fidèles",
            ],
            "en": [
                "Modest dress (shoulders and knees) in pagodas",
                "Remove shoes and hat at entrance",
                "Ask before photographing worshippers",
            ],
        },
    },
    "national_day": {
        "image": "/static/images/destinations/hanoi.webp",
        "image_alt": {
            "fr": "Place Ba Đình et drapeaux vietnamiens à Hanoï",
            "en": "Ba Đình Square and Vietnamese flags in Hanoi",
        },
        "highlights": {
            "fr": [
                "Commémoration de l'indépendance (2 septembre 1945)",
                "Cérémonie au mausolée Hô Chi Minh",
                "Défilé militaire les années paires (selon édition)",
                "Feux d'artifice le soir à Hanoï et Saigon",
            ],
            "en": [
                "Independence commemoration (September 2, 1945)",
                "Ceremony at Ho Chi Minh Mausoleum",
                "Military parade on even years (when held)",
                "Evening fireworks in Hanoi and Saigon",
            ],
        },
        "experience": {
            "fr": "Le 2 septembre, le Vietnam célèbre la déclaration d'indépendance de Hô Chi "
                  "Minh sur la place Ba Đình. Drapeaux rouges à étoile jaune, portraits du "
                  "« Oncle Hô » et cérémonies officielles rythment la journée. C'est aussi "
                  "un long week-end très prisé des locaux — musées, lac Hoàn Kiếm et "
                  "centre-ville battent plein.",
            "en": "On September 2, Vietnam celebrates Ho Chi Minh's independence declaration "
                  "at Ba Đình Square. Red flags with gold stars, Uncle Hô portraits and "
                  "official ceremonies mark the day. It's also a popular long weekend for "
                  "locals — museums, Hoàn Kiếm Lake and downtown are packed.",
        },
        "practical": {
            "fr": [
                "Mausolée HCM fermé plusieurs jours autour du 2 septembre",
                "Réservez hôtels et trains pour le long week-end",
                "Évitez les déplacements inter-villes le 1er septembre soir",
            ],
            "en": [
                "Ho Chi Minh Mausoleum closed several days around September 2",
                "Book hotels and trains for the long weekend",
                "Avoid inter-city travel on the evening of September 1",
            ],
        },
    },
    "mid_autumn": {
        "image": "/static/images/pool/1559592413-7cec4d0cae2b.webp",
        "image_alt": {
            "fr": "Lanternes de la fête de la mi-automne",
            "en": "Mid-Autumn Festival lanterns",
        },
        "highlights": {
            "fr": [
                "Fête des enfants sous la pleine lune",
                "Lanternes en forme de poisson, étoile ou personnages",
                "Gâteaux de lune bánh trung thu (noix, haricot, jaune d'œuf)",
                "Danses de lion dans les rues de Hội An, Hanoï et Cholon",
            ],
            "en": [
                "Children's festival under the full moon",
                "Fish-, star- or character-shaped lanterns",
                "Mooncakes bánh trung thu (nuts, bean paste, egg yolk)",
                "Lion dances in Hội An, Hanoi and Cholon streets",
            ],
        },
        "experience": {
            "fr": "Tết Trung Thu est la fête la plus joyeuse pour les enfants vietnamiens. "
                  "Les familles défilent avec des lanternes illuminées, dégustent des "
                  "gâteaux de lune et regardent les danses de lion. Hội An combine "
                  "lanternes traditionnelles et décorations modernes ; le quartier chinois "
                  "de Cholon (Saigon) propose marchés nocturnes et spectacles de rue.",
            "en": "Tết Trung Thu is the happiest festival for Vietnamese children. Families "
                  "parade with lit lanterns, eat mooncakes and watch lion dances. Hội An "
                  "mixes traditional lanterns and modern decor; Cholon (Saigon) offers "
                  "night markets and street performances.",
        },
        "practical": {
            "fr": [
                "Goûtez les gâteaux artisanaux plutôt que les boîtes industrielles",
                "Hội An et Cholon très fréquentés — arrivez avant le coucher du soleil",
                "Parfait pour voyager en famille",
            ],
            "en": [
                "Try artisan mooncakes rather than industrial boxes",
                "Hội An and Cholon very busy — arrive before sunset",
                "Perfect for family travel",
            ],
        },
    },
    "kate_festival": {
        "image": "/static/images/pool/1583417319070-4a69db38a482.webp",
        "image_alt": {
            "fr": "Tour Cham en briques — patrimoine du centre Vietnam",
            "en": "Cham brick tower — Central Vietnam heritage",
        },
        "highlights": {
            "fr": [
                "Plus grande fête du peuple Cham (minorité du Sud-Centre)",
                "Rituels aux tours Po Klong Garai et Po Rome (Ninh Thuận)",
                "Costumes brodés, danses kate et musique traditionnelle",
                "Immersion dans une culture hindouiste-bouddhiste unique",
            ],
            "en": [
                "Largest festival of the Cham people (South-Central minority)",
                "Rituals at Po Klong Garai and Po Rome towers (Ninh Thuận)",
                "Embroidered dress, kate dances and traditional music",
                "Immersion in a unique Hindu-Buddhist culture",
            ],
        },
        "experience": {
            "fr": "Le Kate marque la fin de l'année rituelle cham. Les tours de briques "
                  "centenaires — vestiges du Champa — accueillent processions, sacrifices "
                  "symboliques et danses en costumes éclatants. Phan Rang et la province de "
                  "Ninh Thuận, entre les dunes et la mer, offrent un contraste saisissant "
                  "avec le Vietnam khmér ou viet majoritaire.",
            "en": "Kate marks the end of the Cham ritual year. Centuries-old brick towers — "
                  "Champa relics — host processions, symbolic offerings and dances in "
                  "vivid dress. Phan Rang and Ninh Thuận province, between dunes and sea, "
                  "contrast sharply with mainstream Vietnamese or Khmer culture.",
        },
        "practical": {
            "fr": [
                "Base à Phan Rang ou excursion depuis Đà Nẵng/Nha Trang (~3–4 h)",
                "Demandez permission avant de filmer les cérémonies",
                "Chaleur forte — chapeau, eau, tenue légère mais respectueuse",
            ],
            "en": [
                "Base in Phan Rang or day trip from Đà Nẵng/Nha Trang (~3–4 h)",
                "Ask permission before filming ceremonies",
                "Strong heat — hat, water, light but respectful clothing",
            ],
        },
    },
    "ok_om_bok": {
        "image": "/static/images/destinations/delta-du-mekong.webp",
        "image_alt": {
            "fr": "Rivière et campagne du delta du Mékong",
            "en": "River and countryside in the Mekong Delta",
        },
        "highlights": {
            "fr": [
                "Fête Khmer du Sud — remerciements à la lune pour la récolte",
                "Offrandes de riz au clair de lune (Bon Om Touk)",
                "Regatta traditionnelle Ghe Ngo à Sóc Trăng",
                "Pagodes Khmer décorées, musique et street food",
            ],
            "en": [
                "Southern Khmer festival — moon thanksgiving for harvest",
                "Moonlight rice offerings (Bon Om Touk)",
                "Traditional Ghe Ngo regatta in Sóc Trăng",
                "Decorated Khmer pagodas, music and street food",
            ],
        },
        "experience": {
            "fr": "Ok Om Bok (Lễ Óc Om Bóc) est le pendant mékongien du Bon Om Touk cambodgien. "
                  "La communauté Khmer du delta célèbre l'abondance du riz avec des "
                  "processions nocturnes, des bateaux-dragon colorés et une énergie "
                  "festive unique dans le Sud vietnamien. Sóc Trăng et Cần Thơ sont les "
                  "bases idéales pour vivre l'événement.",
            "en": "Ok Om Bok (Lễ Óc Om Bóc) is the Mekong counterpart to Cambodia's Bon Om "
                  "Touk. The delta's Khmer community celebrates rice abundance with night "
                  "processions, colourful dragon boats and festive energy unique in "
                  "southern Vietnam. Sóc Trăng and Cần Thơ are ideal bases.",
        },
        "practical": {
            "fr": [
                "15e jour du 10e mois lunaire — vérifiez la date exacte",
                "Réservez hébergement à Sóc Trăng ou Cần Thơ",
                "Combinez avec un marché flottant au lever du soleil",
            ],
            "en": [
                "15th day of 10th lunar month — confirm exact date",
                "Book stays in Sóc Trăng or Cần Thơ",
                "Combine with a sunrise floating market",
            ],
        },
    },
    "floating_market_peak": {
        "image": "/static/images/destinations/delta-du-mekong.webp",
        "image_alt": {
            "fr": "Marché flottant au lever du soleil dans le delta du Mékong",
            "en": "Floating market at sunrise in the Mekong Delta",
        },
        "highlights": {
            "fr": [
                "Cái Răng et Cai Be : les marchés les plus photogéniques",
                "Activité maximale de novembre à janvier (haute eau)",
                "Fruits tropicaux, café phin et vente depuis les sampans",
                "Expérience authentique du Sud vietnamien",
            ],
            "en": [
                "Cái Răng and Cai Be: most photogenic markets",
                "Peak activity November to January (high water)",
                "Tropical fruit, phin coffee and sampan trading",
                "Authentic southern Vietnam experience",
            ],
        },
        "experience": {
            "fr": "Après la mousson, le Mékong gonfle et les agriculteurs convergent vers "
                  "Cái Răng, à proximité de Cần Thơ. Dès 5 h du matin, des centaines de "
                  "barques chargées de papaye, de noix de coco et de soupe phở s'échangent "
                  "sur l'eau brumeuse. C'est l'une des images les plus emblématiques du "
                  "Vietnam — à vivre au moins une fois.",
            "en": "After monsoon, the Mekong swells and farmers converge on Cái Răng near "
                  "Cần Thơ. From 5 a.m., hundreds of boats loaded with papaya, coconut "
                  "and phở soup trade on misty water. One of Vietnam's most iconic sights "
                  "— worth experiencing at least once.",
        },
        "practical": {
            "fr": [
                "Départ obligatoire à 5h–6h du matin",
                "Nuit à Cần Thơ recommandée",
                "Excursion en sampan (~200 000–400 000 VND) via votre hôtel",
            ],
            "en": [
                "Must leave at 5–6 a.m.",
                "Overnight in Cần Thơ recommended",
                "Sampan tour (~200,000–400,000 VND) via your hotel",
            ],
        },
    },
    "sapa_festival": {
        "image": "/static/images/destinations/sapa.webp",
        "image_alt": {
            "fr": "Rizières en terrasses dorées à Sapa",
            "en": "Golden rice terraces in Sapa",
        },
        "highlights": {
            "fr": [
                "Rizières dorées de septembre à novembre",
                "Marchés hebdomadaires Hmong et Dao (Bac Ha, Muong Hum)",
                "Randonnées entre villages et homestays",
                "Fêtes de moisson dans les villages ethniques",
            ],
            "en": [
                "Golden terraces September to November",
                "Weekly Hmong and Dao markets (Bac Ha, Muong Hum)",
                "Trekking between villages and homestays",
                "Harvest celebrations in ethnic villages",
            ],
        },
        "experience": {
            "fr": "L'automne à Sapa est la saison des photographes : les terrasses en "
                  "cascades passent du vert à l'or avant la récolte. Les minorités Hmong "
                  "et Dao convergent vers les marchés dominicaux de Bac Ha — l'un des plus "
                  "colorés du Nord — en costumes brodés. Les homestays permettent de "
                  "partager repas et traditions au rythme local.",
            "en": "Autumn in Sapa is photographers' season: cascading terraces turn from "
                  "green to gold before harvest. Hmong and Dao minorities gather at "
                  "Sunday markets like Bac Ha — among the North's most colourful — in "
                  "embroidered dress. Homestays let you share meals and traditions at "
                  "local pace.",
        },
        "practical": {
            "fr": [
                "Réservez guide et homestay pour octobre",
                "Températures fraîches en altitude — veste imperméable",
                "Bac Ha : dimanche matin, départ tôt depuis Sapa",
            ],
            "en": [
                "Book guide and homestay for October",
                "Cool at altitude — waterproof jacket",
                "Bac Ha: Sunday morning, leave early from Sapa",
            ],
        },
    },
    "halong_cruise_peak": {
        "image": "/static/images/destinations/halong.webp",
        "image_alt": {
            "fr": "Jonques dans la baie d'Halong",
            "en": "Junk boats in Halong Bay",
        },
        "highlights": {
            "fr": [
                "Meilleure période : octobre à avril (mer calme, ciel dégagé)",
                "Nuit à bord d'une jonque traditionnelle ou premium",
                "Kayak, grottes et baignade entre les karsts",
                "Site UNESCO — 1 600 îles et îlots",
            ],
            "en": [
                "Best period: October to April (calm seas, clear skies)",
                "Overnight on traditional or premium junk boat",
                "Kayak, caves and swimming among karsts",
                "UNESCO site — 1,600 islands and islets",
            ],
        },
        "experience": {
            "fr": "La baie d'Halong concentre l'imaginaire du Vietnam. Entre octobre et avril, "
                  "la brume légère et la mer plate offrent les conditions idéales pour une "
                  "croisière d'une ou deux nuits. Les itinéraires incluent grottes "
                  "spectaculaires, villages flottants et kayak au lever du soleil. Évitez "
                  "juillet–août (typhons) et le Tết si vous préférez moins de monde.",
            "en": "Halong Bay captures Vietnam's imagination. Between October and April, light "
                  "mist and flat seas offer ideal conditions for one- or two-night cruises. "
                  "Routes include spectacular caves, floating villages and sunrise kayaking. "
                  "Avoid July–August (typhoons) and Tết if you prefer fewer crowds.",
        },
        "practical": {
            "fr": [
                "Choisissez un opérateur certifié (éviter les prix trop bas)",
                "Cabine avec hublot fortement recommandée",
                "Transfert depuis Hanoï inclus dans la plupart des forfaits (~3–4 h)",
            ],
            "en": [
                "Choose a certified operator (avoid suspiciously low prices)",
                "Cabin with porthole strongly recommended",
                "Transfer from Hanoi included in most packages (~3–4 h)",
            ],
        },
    },
    "christmas": {
        "image": "/static/images/destinations/hoi-an.webp",
        "image_alt": {
            "fr": "Hội An décorée pour les fêtes de fin d'année",
            "en": "Hội An decorated for the holiday season",
        },
        "highlights": {
            "fr": [
                "Noël non férié mais très visible à Saigon",
                "Cathédrale Notre-Dame et boulevard Dong Khoi illuminés",
                "Centres commerciaux Vincom et Landmark 81 décorés",
                "Hội An mêle lanternes vietnamiennes et guirlandes occidentales",
            ],
            "en": [
                "Christmas not a public holiday but very visible in Saigon",
                "Notre-Dame Cathedral and Dong Khoi boulevard lit up",
                "Vincom malls and Landmark 81 decorated",
                "Hội An mixes Vietnamese lanterns and Western fairy lights",
            ],
        },
        "experience": {
            "fr": "Le Vietnam n'est pas un pays catholique majoritaire, mais le Sud — et "
                  "Saigon en particulier — affiche fièrement décorations et crèches. La "
                  "cathédrale Notre-Dame (en restauration selon périodes) et le quartier "
                  "central deviennent promenades nocturnes. Hội An, déjà magique en "
                  "décembre, ajoute guirlandes et marchés artisanaux.",
            "en": "Vietnam isn't majority Catholic, but the South — especially Saigon — "
                  "proudly displays decorations and nativity scenes. Notre-Dame Cathedral "
                  "(under restoration at times) and the central district become evening "
                  "strolls. Hội An, already magical in December, adds fairy lights and "
                  "craft markets.",
        },
        "practical": {
            "fr": [
                "Messe de minuit : places limitées à Notre-Dame",
                "Haute saison touristique — réservez Hội An à l'avance",
                "Climat sec et agréable au Sud en décembre",
            ],
            "en": [
                "Midnight mass: limited seats at Notre-Dame",
                "Peak tourist season — book Hội An ahead",
                "Dry, pleasant weather in the South in December",
            ],
        },
    },
}


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


def build_events_mai_chunks(
    lang: str,
    page_url_fn: Callable[[str, str], str],
    *,
    today: date | None = None,
) -> list[dict]:
    """Index événements 2026–2027 pour Mai (RAG)."""
    lang = "en" if lang == "en" else "fr"
    today = today or date.today()
    chunks: list[dict] = []
    calendar_url = page_url_fn("events_calendar", lang)

    must_see: list[str] = []
    upcoming_lines: list[str] = []
    for ev in EVENTS:
        title = _pick(ev["title"], lang)
        if ev.get("must_see"):
            must_see.append(title)
        for occ in ev.get("occurrences", []):
            start = _parse(occ["start"])
            end = _parse(occ["end"])
            if end < CALENDAR_START or start > CALENDAR_END:
                continue
            if _status(start, end, today) == "past":
                continue
            upcoming_lines.append(f"{title} ({_format_range(start, end, lang)})")

    overview = " ".join(filter(None, [
        ui_t("events.lead", lang),
        ui_t("events.highlights_sub", lang),
        f"{'Incontournables' if lang == 'fr' else 'Must-see'}: {', '.join(must_see[:9])}." if must_see else "",
        f"{'Prochaines dates' if lang == 'fr' else 'Upcoming dates'}: {'; '.join(upcoming_lines[:14])}." if upcoming_lines else "",
    ]))
    chunks.append({
        "id": "guide-page:events_calendar",
        "title": ui_t("events.title", lang),
        "url": calendar_url,
        "group": "Événements Vietnam",
        "text": overview[:900],
    })

    for ev in EVENTS:
        dates: list[str] = []
        for occ in ev.get("occurrences", []):
            start = _parse(occ["start"])
            end = _parse(occ["end"])
            if end < CALENDAR_START or start > CALENDAR_END:
                continue
            dates.append(_format_range(start, end, lang))

        enrich = EVENT_ENRICHMENT.get(ev["key"], {})
        highlights = _pick_list(enrich.get("highlights", {}), lang)
        practical = _pick_list(enrich.get("practical", {}), lang)
        parts = [
            f"{'Dates' if lang == 'fr' else 'Dates'}: {' · '.join(dates)}" if dates else "",
            _pick(ev["summary"], lang),
            _pick(ev["body"], lang),
            _pick(ev.get("tip", {}), lang),
            _pick(ev.get("lunar", {}), lang),
        ]
        if highlights:
            parts.append(f"{'Points forts' if lang == 'fr' else 'Highlights'}: {'; '.join(highlights[:5])}")
        if practical:
            parts.append(f"{'Pratique' if lang == 'fr' else 'Practical'}: {'; '.join(practical[:4])}")
        region_labels = [ui_t(f"events.region.{r}", lang) for r in ev.get("regions") or []]
        if region_labels:
            parts.append(f"{'Régions' if lang == 'fr' else 'Regions'}: {', '.join(region_labels)}")

        chunks.append({
            "id": f"guide-events:{ev['key']}",
            "title": _pick(ev["title"], lang),
            "url": calendar_url,
            "group": "Événements Vietnam",
            "text": " ".join(p for p in parts if p)[:900],
        })

    return chunks


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
            enrich = EVENT_ENRICHMENT.get(ev["key"], {})
            image = enrich.get("image") or (
                f"/static/images/destinations/{dest_slugs[0]}.webp" if dest_slugs else
                "/static/images/destinations/hanoi.webp"
            )
            flat.append({
                "id": f"{ev['key']}-{occ['start']}",
                "event_key": ev["key"],
                "icon": ev.get("icon", "✦"),
                "image": image,
                "image_hd": _image_hd(image),
                "image_alt": _pick(enrich.get("image_alt", {}), lang) or _pick(ev["title"], lang),
                "category": ev["category"],
                "category_label": ui_t(f"events.cat.{ev['category']}", lang),
                "title": _pick(ev["title"], lang),
                "summary": _pick(ev["summary"], lang),
                "body": _pick(ev["body"], lang),
                "experience": _pick(enrich.get("experience", ev.get("body", {})), lang),
                "highlights": _pick_list(enrich.get("highlights", {}), lang),
                "practical": _pick_list(enrich.get("practical", {}), lang),
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
                    {
                        "slug": s,
                        "name": _dest_label(s, lang, destinations),
                        "url": lang_url("destination_page", lang, slug=s),
                    }
                    for s in dest_slugs
                ],
                "must_see": bool(ev.get("must_see")),
                "recurring": is_recurring,
                "status": "recurring" if is_recurring else _status(start, end, today),
                "status_label": _status_label(
                    "recurring" if is_recurring else _status(start, end, today), lang
                ),
                "must_see_label": ui_t("events.must_see", lang),
            })

    flat.sort(key=lambda x: (x["start"], x["title"]))

    upcoming = [e for e in flat if e["status"] in ("upcoming", "ongoing", "recurring")]
    highlights = [e for e in flat if e["must_see"] and e["status"] != "past"]

    year_groups: list[dict] = []
    for ev_item in flat:
        yr = ev_item["year"]
        if not year_groups or year_groups[-1]["year"] != yr:
            year_groups.append({"year": yr, "events": []})
        year_groups[-1]["events"].append(ev_item)

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
        "year_groups": year_groups,
        "upcoming": upcoming,
        "highlights": highlights[:8],
        "hoi_an_moon_dates": moon_dates,
        "stats": {
            "total": len(flat),
            "must_see": sum(1 for e in flat if e["must_see"]),
            "upcoming": len(upcoming),
        },
    }
