"""Pack SEO aligné Search Console — titres CTR, FAQ, geo, articles.

Les requêtes GSC (3 mois) ont des impressions (Hanoï où dormir, transport,
Nha Trang, Ninh Binh, Hội An, visa prix, 10/15 jours) mais presque 0 clic.
Les packs ci-dessous calent title / H1 / description / FAQ / JSON-LD sur
cette intention, sans changer le contenu éditorial des fiches.
"""

from __future__ import annotations

from typing import Any

import config
from seo_utils import truncate_text

GSC_HOME_DESTS: tuple[str, ...] = (
    "tam-dao",
    "ninh-binh",
    "nha-trang",
    "hoi-an",
    "hanoi",
    "cat-ba",
    "ha-giang",
    "vung-tau",
    "cu-chi",
    "halong",
)


def _loc(fr: str, en: str) -> dict[str, str]:
    return {"fr": fr, "en": en}


def _faq(*rows: tuple[str, str, str, str]) -> dict[str, list[dict[str, str]]]:
    fr, en = [], []
    for qf, af, qe, ae in rows:
        fr.append({"question": qf, "answer": af})
        en.append({"question": qe, "answer": ae})
    return {"fr": fr, "en": en}


def _lang(lang: str) -> str:
    return "en" if lang == "en" else "fr"


# ── Destinations (requêtes GSC + fiches existantes) ─────────────────────

DEST_PACKS: dict[str, dict[str, Any]] = {
    "hanoi": {
        "geo": (21.0285, 105.8542),
        "contained": _loc("Ville de Hanoï", "Hanoi"),
        "alts": ["Hà Nội", "Ha Noi", "Hanoï"],
        "eat_slug": "meilleurs-restaurants-hanoi",
        "h1": _loc(
            "Guide Hanoï 2026 — que faire, où dormir, où manger",
            "Hanoi guide 2026 — things to do, where to stay, where to eat",
        ),
        "title": _loc(
            "Guide Hanoï 2026 : où dormir, où manger, que faire",
            "Hanoi guide 2026: where to stay, eat and what to do",
        ),
        "desc": _loc(
            "Où dormir à Hanoï (vieux quartier vs Tây Hồ), où manger (street food, cheap food), "
            "que faire en 2–3 jours. Hôtels, restaurants et conseils 2026.",
            "Where to stay in Hanoi (Old Quarter vs West Lake), where to eat (street food, cheap eats), "
            "and what to do in 2–3 days. Hotels and 2026 tips.",
        ),
        "kw": _loc(
            "où dormir à Hanoï, où manger à Hanoï, guide Hanoï, quartier à éviter Hanoï, visiter Hanoï 3 jours",
            "where to stay in Hanoi, where to eat in Hanoi, Hanoi food guide, cheap food in Hanoi, Hanoi 3 days",
        ),
        "faq": _faq(
            (
                "Où dormir à Hanoï ?",
                "Le Vieux Quartier (Hoàn Kiếm) pour l'ambiance et les repas ; Tây Hồ ou Ba Đình "
                "pour plus de calme. Comparez les hôtels ci-dessous avant de réserver.",
                "Where to stay in Hanoi?",
                "The Old Quarter (Hoàn Kiếm) for atmosphere and food; Tây Hồ or Ba Đình for a quieter stay. "
                "Compare the hotels on this page before booking.",
            ),
            (
                "Où manger à Hanoï ?",
                "Street food 2–4 € (phở, bún chả, bánh mì) dans le Vieux Quartier ; tables assises 8–15 €. "
                "Voir notre guide dédié des restaurants de Hanoï.",
                "Where to eat in Hanoi?",
                "Street food costs €2–4 (phở, bún chả, bánh mì) in the Old Quarter; sit-down meals €8–15. "
                "See our dedicated Hanoi food guide.",
            ),
            (
                "Combien de jours à Hanoï ?",
                "2 jours pour l'essentiel, 3 jours pour ajouter un musée, un lac et un quartier hors centre. "
                "Un circuit 10 ou 15 jours commence presque toujours ici.",
                "How many days in Hanoi?",
                "Two days cover the essentials, three if you add a museum, a lake and a quieter neighbourhood. "
                "Most 10- and 15-day itineraries start here.",
            ),
            (
                "Y a-t-il un quartier à éviter à Hanoï ?",
                "Pas de no-go. La nuit, restez dans les rues animées, utilisez Grab plutôt qu'un taxi de rue, "
                "et méfiez-vous des pickpockets autour du lac Hoàn Kiếm le week-end.",
                "Are there places to avoid in Hanoi?",
                "No no-go areas. At night stay on busy streets, use Grab instead of a street taxi, "
                "and watch for pickpockets around Hoàn Kiếm Lake at weekends.",
            ),
        ),
    },
    "nha-trang": {
        "geo": (12.2388, 109.1967),
        "contained": _loc("Province de Khánh Hòa", "Khánh Hòa province"),
        "alts": ["Nhatrang", "Nha Trang", "Nha Trang City"],
        "h1": _loc(
            "Guide Nha Trang 2026 — plages, que faire, quelle province",
            "Nha Trang guide 2026 — beaches, things to do, which province",
        ),
        "title": _loc(
            "Guide Nha Trang Vietnam 2026 — plages, itinerary, que faire",
            "Nha Trang Vietnam 2026 — beaches, itinerary, things to do",
        ),
        "desc": _loc(
            "Nha Trang (province de Khánh Hòa, Centre-Sud) : plages, îles, itinerary 2–4 jours, "
            "où dormir et comment y aller. Guide pratique 2026.",
            "Nha Trang (Khánh Hòa province, south-central Vietnam): beaches, islands, 2–4 day itinerary, "
            "where to stay and how to get there. Practical 2026 guide.",
        ),
        "kw": _loc(
            "Nha Trang, Nha Trang Vietnam, que faire Nha Trang, province Nha Trang, itinerary Nha Trang",
            "Nha Trang Vietnam, what is Nha Trang like, which province is Nha Trang, Nha Trang itinerary",
        ),
        "faq": _faq(
            (
                "Nha Trang est dans quelle province ?",
                "Nha Trang est la capitale de la province de Khánh Hòa, sur la côte Centre-Sud du Vietnam "
                "(entre Hội An et Ho Chi Minh-Ville).",
                "What province is Nha Trang in?",
                "Nha Trang is the capital of Khánh Hòa province, on Vietnam's south-central coast "
                "(between Hội An and Ho Chi Minh City).",
            ),
            (
                "Nha Trang, c'est le sud ou le centre ?",
                "Géographiquement c'est le Centre-Sud : plus au sud que Đà Nẵng / Hội An, plus au nord que Saigon. "
                "Les vols HAN/SGN et le train de la Réunification y passent.",
                "Is Nha Trang south or central Vietnam?",
                "South-central: south of Đà Nẵng / Hội An, north of Saigon. Domestic flights and the "
                "Reunification railway both stop here.",
            ),
            (
                "À quoi ressemble Nha Trang ?",
                "Grande ville balnéaire : plage urbaine, îles pour la journée, restauration abondante, "
                "ambiance plus « resort » que Hội An. Idéal 2–4 jours entre le Centre et le Sud.",
                "What is Nha Trang like?",
                "A large beach city: urban shoreline, day-trip islands, plenty of food, more resort-like than Hội An. "
                "Ideal for 2–4 days between the centre and the south.",
            ),
            (
                "Combien de jours à Nha Trang ?",
                "2 jours pour la plage et une île ; 3–4 jours si vous plongez ou enchaînez avec Đà Lạt / Mũi Né.",
                "How long to stay in Nha Trang?",
                "Two days for the beach and an island; 3–4 if you dive or continue to Đà Lạt / Mũi Né.",
            ),
        ),
    },
    "ninh-binh": {
        "geo": (20.2506, 105.9744),
        "contained": _loc("Province de Ninh Bình", "Ninh Bình province"),
        "alts": ["Ninh Bình", "Ninh Binh", "Tam Coc", "Trang An"],
        "h1": _loc(
            "Guide Ninh Binh 2026 — Tam Coc, Trang An, combien de jours",
            "Ninh Binh travel guide 2026 — Tam Coc, Trang An, how long to stay",
        ),
        "title": _loc(
            "Guide Ninh Binh Vietnam 2026 — Tam Coc, que faire, durée",
            "Ninh Binh Vietnam travel guide 2026 — Tam Coc, how long",
        ),
        "desc": _loc(
            "Ninh Binh travel guide : Tam Coc, Trang An, Hoa Lu. Combien de jours, où dormir, "
            "Cat Ba ou Ninh Binh, comment y aller depuis Hanoï. 2026.",
            "Ninh Binh travel guide: Tam Coc, Trang An, Hoa Lu. How long to stay, where to sleep, "
            "Cat Ba vs Ninh Binh, and how to get there from Hanoi. 2026.",
        ),
        "kw": _loc(
            "Ninh Binh, Ninh Binh Vietnam, Ninh Binh travel guide, que faire Ninh Binh, où dormir Ninh Binh",
            "Ninh Binh travel guide, Ninh Binh Vietnam, how long to stay in Ninh Binh, Ninh Binh itinerary",
        ),
        "faq": _faq(
            (
                "Combien de temps rester à Ninh Binh ?",
                "1 nuit / 2 jours suffisent pour Tam Coc ou Trang An + Hoa Lu. 2 nuits si vous ajoutez "
                "Bai Dinh ou un vélo dans les rizières. Idéal depuis Hanoï (2 h de route).",
                "How long to stay in Ninh Binh?",
                "One night / two days covers Tam Coc or Trang An plus Hoa Lu. Two nights if you add "
                "Bai Dinh or a rice-field bike ride. Easy from Hanoi (about 2 hours).",
            ),
            (
                "Cat Ba ou Ninh Binh ?",
                "Ninh Binh = karst, rizières, barques. Cat Ba = mer, île, randonnée, Halong. "
                "Sur 10 jours, beaucoup choisissent Ninh Binh ; sur 15 jours les deux sont possibles.",
                "Cat Ba or Ninh Binh?",
                "Ninh Binh is karst, rice fields and rowing boats. Cat Ba is sea, island hiking and Halong. "
                "On a 10-day trip many pick Ninh Binh; 15 days can fit both.",
            ),
            (
                "Où dormir à Ninh Binh ?",
                "Tam Coc pour les rizières et les barques ; Ninh Binh ville si vous arrivez tard en bus. "
                "Les hôtels ci-dessous sont des points de départ, pas des consignes.",
                "Where to stay in Ninh Binh?",
                "Tam Coc for rice fields and boats; Ninh Binh city if you arrive late by bus. "
                "The hotels below are starting points, not orders.",
            ),
            (
                "Comment aller à Ninh Binh depuis Hanoï ?",
                "Limousine / van 2 h, train ~2 h, ou excursion journée. Pour un circuit 15 jours, "
                "Ninh Binh s'insère souvent entre Hanoï et Halong / Sapa.",
                "How to get to Ninh Binh from Hanoi?",
                "Limousine van ~2 h, train ~2 h, or a day tour. On a 15-day itinerary it often sits "
                "between Hanoi and Halong / Sapa.",
            ),
        ),
    },
    "hoi-an": {
        "geo": (15.8801, 108.3380),
        "contained": _loc("Province de Quảng Nam", "Quảng Nam province"),
        "alts": ["Hội An", "Hoi An", "Faifo", "An Hội"],
        "h1": _loc(
            "Guide Hội An 2026 — où est Hội An, lanternes, que visiter",
            "Hoi An Vietnam 2026 — where it is, lanterns, what to visit",
        ),
        "title": _loc(
            "Hội An Vietnam 2026 — où est Hội An, lanternes, que faire",
            "Where is Hoi An in Vietnam? 2026 lanterns & travel guide",
        ),
        "desc": _loc(
            "Où est Hội An au Vietnam ? Vieille ville UNESCO, festival des lanternes, An Hội, "
            "My Son, que visiter et où dormir. Guide 2026.",
            "Where is Hoi An in Vietnam? UNESCO Old Town, lantern festival, An Hoi, My Son, "
            "what to visit and where to stay. 2026 guide.",
        ),
        "kw": _loc(
            "Hội An, Hoi An Vietnam, où est Hội An, lanternes Hội An, An Hội, que visiter Hội An",
            "where is Hoi An, Hoi An Vietnam, Hoi An location, lantern festival Hoi An, An Hoi",
        ),
        "faq": _faq(
            (
                "Où se trouve Hội An au Vietnam ?",
                "Hội An est sur la côte Centre, province de Quảng Nam, à ~30 min de Đà Nẵng. "
                "Ce n'est pas près de Hanoï ni de San Francisco : c'est le Vietnam central.",
                "Where is Hoi An in Vietnam?",
                "Hoi An is on the central coast in Quảng Nam province, about 30 minutes from Đà Nẵng. "
                "It is not near Hanoi — it is central Vietnam.",
            ),
            (
                "Quand a lieu le festival des lanternes à Hội An ?",
                "La vieille ville s'illumine surtout les soirs de pleine lune (calendrier lunaire). "
                "Notre calendrier d'événements liste les dates 2026–2027.",
                "When is the Hoi An lantern festival?",
                "The Old Town lights up especially on full-moon nights (lunar calendar). "
                "Our events calendar lists 2026–2027 dates.",
            ),
            (
                "Que visiter à Hội An ?",
                "Vieille ville, rive An Hội, plage An Bàng, ateliers de lanternes, et éventuellement "
                "My Son en demi-journée depuis Hội An.",
                "Where to visit in Hoi An?",
                "Old Town, An Hoi islet, An Bang beach, lantern workshops, and optionally My Son "
                "as a half-day trip from Hoi An.",
            ),
            (
                "Combien de jours à Hội An ?",
                "2 nuits minimum, 3 si vous voulez la plage et My Son. Un circuit 10 jours y passe "
                "presque toujours après Huế / Đà Nẵng.",
                "How long in Hoi An?",
                "Two nights minimum, three with the beach and My Son. A 10-day itinerary almost "
                "always stops here after Huế / Đà Nẵng.",
            ),
        ),
    },
    "tam-dao": {
        "geo": (21.4564, 105.6467),
        "contained": _loc("Province de Vĩnh Phúc", "Vĩnh Phúc province"),
        "alts": ["Tam Đảo", "Tam Dao"],
        "h1": _loc(
            "Tam Dao Vietnam 2026 — station d'altitude, que faire, où dormir",
            "Tam Dao Vietnam 2026 — hill station, things to do, where to stay",
        ),
        "title": _loc(
            "Tam Dao Vietnam 2026 — guide, que faire, où dormir",
            "Tam Dao Vietnam 2026 — travel guide, things to do, stay",
        ),
        "desc": _loc(
            "Tam Dao (Tam Đảo), station d'altitude à ~2 h de Hanoï : climat frais, randonnées, "
            "où dormir et que faire le week-end. Guide 2026.",
            "Tam Dao (Tam Đảo), a hill station about 2 hours from Hanoi: cool climate, hikes, "
            "where to stay and what to do for a weekend. 2026 guide.",
        ),
        "kw": _loc(
            "Tam Dao Vietnam, Tam Đảo, Tam Dao, que faire Tam Dao, séjour Tam Dao",
            "Tam Dao Vietnam, Tam Dao, Tam Dao travel, things to do Tam Dao",
        ),
        "faq": _faq(
            (
                "Où est Tam Dao au Vietnam ?",
                "Tam Đảo est une station d'altitude dans la province de Vĩnh Phúc, à environ 80 km "
                "au nord-ouest de Hanoï (2 h de route).",
                "Where is Tam Dao in Vietnam?",
                "Tam Dao is a hill station in Vĩnh Phúc province, about 80 km northwest of Hanoi "
                "(around 2 hours by road).",
            ),
            (
                "Pourquoi aller à Tam Dao ?",
                "Pour la fraîcheur, les brumes, les randonnées et un week-end hors de Hanoï — "
                "très différent d'une plage (Nha Trang) ou du karst (Ninh Binh).",
                "Why visit Tam Dao?",
                "For cool air, mist, hiking and a weekend out of Hanoi — very different from a beach "
                "(Nha Trang) or karst (Ninh Binh).",
            ),
            (
                "Combien de temps à Tam Dao ?",
                "1–2 nuits suffisent pour la plupart des voyageurs ; combinez avec Hanoï plutôt "
                "qu'avec un long circuit sud.",
                "How long in Tam Dao?",
                "One or two nights is enough for most travellers; pair it with Hanoi rather than a "
                "long southern itinerary.",
            ),
        ),
    },
    "cat-ba": {
        "geo": (20.7278, 107.0489),
        "contained": _loc("Province de Hải Phòng", "Hải Phòng province"),
        "alts": ["Cát Bà", "Cat Ba Island", "Cat Ba"],
        "h1": _loc(
            "Guide Cat Ba 2026 — île, parc national, itinerary",
            "Cat Ba island guide 2026 — national park, itinerary",
        ),
        "title": _loc(
            "Cat Ba Vietnam 2026 — île, parc national, que faire",
            "Cat Ba island Vietnam 2026 — guide, itinerary, park",
        ),
        "desc": _loc(
            "Cat Ba island : parc national, kayak, Halong alternatif, itinerary 2–3 jours. "
            "Cat Ba ou Ninh Binh ? Comment y aller. Guide 2026.",
            "Cat Ba island: national park, kayak, Halong alternative, 2–3 day itinerary. "
            "Cat Ba or Ninh Binh? How to get there. 2026 guide.",
        ),
        "kw": _loc(
            "Cat Ba, Cat Ba island, Cat Ba Vietnam, parc national Cat Ba, Cat Ba ou Ninh Binh",
            "Cat Ba island, Cat Ba Vietnam, Cat Ba itinerary, Cat Ba or Ninh Binh, Cat Ba national park",
        ),
        "faq": _faq(
            (
                "Cat Ba, c'est où ?",
                "Cát Bà est la plus grande île de la baie de Lan Ha / Halong, administrée par Hải Phòng. "
                "On y va depuis Hanoï en ~4–5 h (bus + bateau).",
                "Where is Cat Ba island?",
                "Cat Ba is the largest island in Lan Ha / Halong Bay, administered by Hải Phòng. "
                "From Hanoi allow about 4–5 hours (bus + boat).",
            ),
            (
                "Cat Ba ou Ninh Binh ?",
                "Mer et randonnée vs rizières et barques. Sur un premier voyage de 10 jours, Ninh Binh "
                "est plus simple ; Cat Ba brille si vous voulez l'eau sans croisière Halong classique.",
                "Cat Ba or Ninh Binh?",
                "Sea and hiking versus rice fields and rowing boats. On a first 10-day trip Ninh Binh "
                "is simpler; Cat Ba shines if you want water without a classic Halong cruise.",
            ),
            (
                "Combien de jours à Cat Ba ?",
                "2 nuits pour le village, le parc et un kayak ; 3 nuits si vous ajoutez une croisière Lan Ha.",
                "How long on Cat Ba island?",
                "Two nights for the town, the national park and kayaking; three if you add a Lan Ha cruise.",
            ),
        ),
    },
    "ha-giang": {
        "geo": (22.8233, 104.9784),
        "contained": _loc("Province de Hà Giang", "Hà Giang province"),
        "alts": ["Hà Giang", "Ha Giang"],
        "h1": _loc(
            "Guide Hà Giang 2026 — boucle, province, que faire",
            "Ha Giang travel guide 2026 — loop, province, things to do",
        ),
        "title": _loc(
            "Hà Giang Vietnam 2026 — boucle, guide, que faire",
            "Ha Giang Vietnam 2026 — loop, travel guide, province",
        ),
        "desc": _loc(
            "Hà Giang : boucle moto, cols, ethnies, ville vs province. Combien de jours, "
            "où dormir, comment venir de Hanoï. Guide 2026.",
            "Ha Giang: motorbike loop, passes, ethnic villages, city vs province. How long, "
            "where to stay, how to come from Hanoi. 2026 guide.",
        ),
        "kw": _loc(
            "Hà Giang, Ha Giang Vietnam, Ha Giang travel guide, boucle Hà Giang, Ha Giang city",
            "Ha Giang Vietnam, Ha Giang travel guide, Ha Giang loop, Ha Giang province, Ha Giang city",
        ),
        "faq": _faq(
            (
                "Hà Giang ville ou province ?",
                "Hà Giang est à la fois une province frontalière (Chine) et sa petite capitale. "
                "La « boucle » se parcourt hors de la ville, en 3–4 jours.",
                "Ha Giang city or province?",
                "Ha Giang is both a border province (China) and its small capital. The famous loop "
                "is ridden outside the city over 3–4 days.",
            ),
            (
                "Combien de jours pour Hà Giang ?",
                "3 jours minimum pour la boucle, 4 plus confort. Ajoutez 1 nuit Hanoï de chaque côté "
                "pour les bus de nuit.",
                "How many days for Ha Giang?",
                "Three days minimum for the loop, four more comfortably. Add a Hanoi night on each side "
                "for overnight buses.",
            ),
            (
                "Hà Giang est-il pour un premier voyage ?",
                "Plutôt non si vous n'avez que 10 jours nord-sud. Sur 15 jours ou un voyage « nord only », "
                "c'est un des plus beaux circuits du pays.",
                "Is Ha Giang for a first trip?",
                "Usually not if you only have 10 days north–south. On 15 days or a north-only trip, "
                "it is one of the country's finest routes.",
            ),
        ),
    },
    "cu-chi": {
        "geo": (11.0065, 106.5135),
        "contained": _loc("Hô Chi Minh-Ville", "Ho Chi Minh City"),
        "alts": ["Củ Chi", "Cu Chi", "Cuchi"],
        "h1": _loc(
            "Củ Chi Vietnam 2026 — tunnels, hôtels, excursion depuis Saigon",
            "Cu Chi Vietnam 2026 — tunnels, hotels, day trip from Saigon",
        ),
        "title": _loc(
            "Củ Chi Vietnam 2026 — tunnels, hôtels, que faire",
            "Cu Chi hotels & tunnels 2026 — guide from Ho Chi Minh City",
        ),
        "desc": _loc(
            "Củ Chi : tunnels, excursion depuis Ho Chi Minh-Ville, hôtels sur place si vous "
            "préférez éviter le centre. Guide pratique 2026.",
            "Cu Chi: tunnels, day trip from Ho Chi Minh City, hotels on site if you prefer "
            "to skip downtown. Practical 2026 guide.",
        ),
        "kw": _loc(
            "Củ Chi, Cu Chi hotels, Cu Chi Vietnam, tunnels Củ Chi, excursion Củ Chi",
            "Cu Chi hotels, Cu Chi Vietnam, Cu Chi tunnels, Cu Chi day trip",
        ),
        "faq": _faq(
            (
                "Faut-il dormir à Củ Chi ?",
                "La plupart des voyageurs font l'excursion à la journée depuis Saigon. Dormir à Củ Chi "
                "n'a d'intérêt que si vous voulez un départ tôt ou un hôtel moins cher hors centre.",
                "Do I need a hotel in Cu Chi?",
                "Most travellers visit as a day trip from Saigon. Staying in Cu Chi only helps if you "
                "want an early start or a cheaper hotel outside the centre.",
            ),
            (
                "Les tunnels de Củ Chi, ça prend combien de temps ?",
                "Demi-journée (matin) depuis le centre de Ho Chi Minh-Ville, souvent combinée avec "
                "le delta du Mékong — ce combo est long, mieux vaut les séparer.",
                "How long for the Cu Chi tunnels?",
                "A morning from downtown Ho Chi Minh City. Combining with the Mekong Delta makes a "
                "very long day — better split them.",
            ),
        ),
    },
    "vung-tau": {
        "geo": (10.3460, 107.0843),
        "contained": _loc("Bà Rịa–Vũng Tàu", "Bà Rịa–Vũng Tàu"),
        "alts": ["Vũng Tàu", "Vung Tau"],
        "h1": _loc(
            "Guide Vũng Tàu 2026 — où est Vung Tau, que faire",
            "Vung Tau Vietnam 2026 — where it is, things to do",
        ),
        "title": _loc(
            "Guide Vũng Tàu 2026 — que faire, où est Vung Tau",
            "Vung Tau Vietnam travel guide 2026 — location & things to do",
        ),
        "desc": _loc(
            "Vũng Tàu : plage à ~2 h de Ho Chi Minh-Ville, que faire, où est Vung Tau, "
            "week-end hors Saigon. Guide 2026.",
            "Vung Tau: beach about 2 hours from Ho Chi Minh City, things to do, where it is, "
            "weekend escape from Saigon. 2026 guide.",
        ),
        "kw": _loc(
            "Vũng Tàu, Vung Tau Vietnam, où est Vung Tau, Vung Tau que faire, Vung Tau guide",
            "Vung Tau Vietnam, where is Vung Tau located, Vung Tau travel guide, Vung Tau city",
        ),
        "faq": _faq(
            (
                "Où se trouve Vũng Tàu ?",
                "Sur la côte sud-est, province de Bà Rịa–Vũng Tàu, à environ 125 km de Ho Chi Minh-Ville "
                "(2 h en limousine ou hydrofoil selon les liaisons).",
                "Where is Vung Tau located?",
                "On the south-east coast in Bà Rịa–Vũng Tàu province, about 125 km from Ho Chi Minh City "
                "(around 2 hours by van, sometimes by hydrofoil).",
            ),
            (
                "Que faire à Vũng Tàu ?",
                "Plages (Back Beach / Front Beach), statue du Christ, phare, fruits de mer. "
                "C'est un week-end Saigonnais plus qu'une étape de 15 jours nord-sud.",
                "What to do in Vung Tau?",
                "Beaches (Back Beach / Front Beach), the Christ statue, lighthouse, seafood. "
                "It is a Saigon weekend more than a stop on a 15-day north–south trip.",
            ),
        ),
    },
    "phu-quoc": {
        "geo": (10.2899, 103.9840),
        "contained": _loc("Province de Kiên Giang", "Kiên Giang province"),
        "alts": ["Phú Quốc", "Phu Quoc"],
        "h1": _loc(
            "Guide Phú Quốc 2026 — île, plages, que faire",
            "Phu Quoc Vietnam 2026 — island, beaches, things to do",
        ),
        "title": _loc(
            "Phú Quốc Vietnam 2026 — plages, île, que faire",
            "Phu Quoc Vietnam 2026 — beaches, island travel guide",
        ),
        "desc": _loc(
            "Phú Quốc : plages, parc national, où dormir, combien de jours, vols depuis Saigon. "
            "Guide île 2026.",
            "Phu Quoc: beaches, national park, where to stay, how long, flights from Saigon. "
            "2026 island guide.",
        ),
        "kw": _loc(
            "Phú Quốc, Phu Quoc Vietnam, voyage Phu Quoc, plages Phú Quốc",
            "Phu Quoc Vietnam, Phu Quoc beaches, Phu Quoc 2026, Phu Quoc travel",
        ),
        "faq": _faq(
            (
                "Combien de jours à Phú Quốc ?",
                "4–5 jours pour plage + île du nord ; 3 jours si c'est une extension après Saigon / Mékong.",
                "How long in Phu Quoc?",
                "4–5 days for beach plus the north of the island; 3 days as an add-on after Saigon / Mekong.",
            ),
            (
                "Phú Quốc en 2026, ça reste sauvage ?",
                "L'ouest et Dương Đông sont très développés ; le nord et certaines plages restent plus calmes. "
                "Choisissez le quartier selon l'ambiance voulue.",
                "Is Phu Quoc still quiet in 2026?",
                "The west and Duong Dong are built up; the north and some beaches stay calmer. "
                "Pick your area according to the vibe you want.",
            ),
        ),
    },
    "ho-chi-minh-city": {
        "geo": (10.8231, 106.6297),
        "contained": _loc("Hô Chi Minh-Ville", "Ho Chi Minh City"),
        "alts": ["Saigon", "Sài Gòn", "Ho Chi Minh City", "HCMC"],
        "h1": _loc(
            "Guide Ho Chi Minh-Ville 2026 — Saigon, que faire, où dormir",
            "Ho Chi Minh City guide 2026 — Saigon, things to do, stay",
        ),
        "title": _loc(
            "Ho Chi Minh-Ville 2026 — Saigon, que faire, où dormir",
            "Ho Chi Minh City Vietnam 2026 — Saigon travel guide",
        ),
        "desc": _loc(
            "Ho Chi Minh-Ville (Saigon) : D1 vs Phú Nhuận, Củ Chi, Mékong, budget quotidien, "
            "sécurité et itinerary 2–3 jours. Guide 2026.",
            "Ho Chi Minh City (Saigon): District 1 vs Phu Nhuan, Cu Chi, Mekong, daily budget, "
            "safety and a 2–3 day itinerary. 2026 guide.",
        ),
        "kw": _loc(
            "Ho Chi Minh-Ville, Saigon, Ho Chi Minh Vietnam, budget Ho Chi Minh, conseils Hô Chi Minh-Ville",
            "Ho Chi Minh City, Saigon, Ho Chi Minh Vietnam, HCMC daily travel cost, Ho Chi Minh safety",
        ),
        "faq": _faq(
            (
                "Combien de jours à Ho Chi Minh-Ville ?",
                "2 jours centre + musées ; 3 jours avec Củ Chi ou le delta. Un circuit 10 jours "
                "y finit souvent.",
                "How many days in Ho Chi Minh City?",
                "Two days for downtown and museums; three with Cu Chi or the Mekong. A 10-day "
                "itinerary often ends here.",
            ),
            (
                "Ho Chi Minh-Ville est-elle sûre ?",
                "Oui avec les précautions urbaines : Grab, sac devant soi, trafic moto. "
                "Voir notre guide sécurité Vietnam.",
                "Is Ho Chi Minh City safe?",
                "Yes with normal city caution: Grab, bag in front, motorbike traffic. "
                "See our Vietnam safety guide.",
            ),
        ),
    },
    "da-nang": {
        "geo": (16.0544, 108.2022),
        "contained": _loc("Đà Nẵng", "Da Nang"),
        "alts": ["Đà Nẵng", "Da Nang", "Danang"],
        "h1": _loc(
            "Guide Đà Nẵng 2026 — plages, Hội An, que faire",
            "Da Nang Vietnam 2026 — beaches, Hoi An, things to do",
        ),
        "title": _loc(
            "Đà Nẵng Vietnam 2026 — plages, aéroport, que faire",
            "Da Nang Vietnam 2026 — beaches, airport, travel guide",
        ),
        "desc": _loc(
            "Đà Nẵng : plages, ponts, base pour Hội An et Huế, aéroport DAD. "
            "Où dormir et combien de jours. Guide 2026.",
            "Da Nang: beaches, bridges, base for Hoi An and Hue, DAD airport. "
            "Where to stay and how long. 2026 guide.",
        ),
        "kw": _loc(
            "Đà Nẵng, Da Nang Vietnam, plages Đà Nẵng, Da Nang Hội An",
            "Da Nang Vietnam, Da Nang beaches, Da Nang Hoi An",
        ),
        "faq": _faq(
            (
                "Đà Nẵng ou Hội An pour dormir ?",
                "Hội An pour le charme et les lanternes ; Đà Nẵng pour la plage, l'aéroport et un rythme ville. "
                "Beaucoup font les deux (30 min de route).",
                "Da Nang or Hoi An to stay?",
                "Hoi An for charm and lanterns; Da Nang for the beach, the airport and a city pace. "
                "Many do both (30 minutes apart).",
            ),
        ),
    },
    "hue": {
        "geo": (16.4637, 107.5909),
        "contained": _loc("Province de Thừa Thiên Huế", "Thừa Thiên Huế province"),
        "alts": ["Huế", "Hue", "Hué"],
        "h1": _loc(
            "Guide Huế 2026 — citadelle, que faire, combien de jours",
            "Hue Vietnam 2026 — citadel, things to do, how long",
        ),
        "title": _loc(
            "Huế Vietnam 2026 — citadelle, que faire, itinerary",
            "Hue Vietnam 2026 — imperial city, travel guide",
        ),
        "desc": _loc(
            "Huế : cité impériale, tombeaux, lagune, train depuis Hanoï. Que faire, "
            "visite 1–2 jours, lien avec Hội An. Guide 2026.",
            "Hue: imperial citadel, tombs, lagoon, train from Hanoi. Things to do, "
            "1–2 day visit, link with Hoi An. 2026 guide.",
        ),
        "kw": _loc(
            "Huế, Hue Vietnam, visiter Huế, citadelle Huế, travel Hue",
            "Hue Vietnam, travel to Hue, Hue citadel, visit Hue",
        ),
        "faq": _faq(
            (
                "Combien de temps à Huế ?",
                "1 journée complète ou 2 nuits. Sur 10 jours on y passe souvent 1 nuit entre Halong et Hội An.",
                "How long in Hue?",
                "One full day or two nights. On 10 days people often spend one night between Halong and Hoi An.",
            ),
        ),
    },
    "sapa": {
        "geo": (22.3364, 103.8440),
        "contained": _loc("Province de Lào Cai", "Lào Cai province"),
        "alts": ["Sa Pa", "Sapa", "Lao Cai Sapa"],
        "h1": _loc(
            "Guide Sapa 2026 — Lào Cai, rizières, que faire",
            "Sapa Lao Cai 2026 — rice terraces, things to do",
        ),
        "title": _loc(
            "Sapa Lào Cai 2026 — rizières, séjour, que faire",
            "Sapa Lao Cai Vietnam 2026 — terraces, travel guide",
        ),
        "desc": _loc(
            "Sapa (Lào Cai) : rizières, treks, train de nuit depuis Hanoï, que faire, "
            "combien de jours. Guide 2026.",
            "Sapa (Lao Cai): rice terraces, treks, overnight train from Hanoi, things to do, "
            "how long. 2026 guide.",
        ),
        "kw": _loc(
            "Sapa, Sapa Lào Cai, Lao Cai Sapa, que faire Sapa, séjour Sapa",
            "Sapa Lao Cai Vietnam, Sapa trek, Lao Cai Sapa, things to do Sapa",
        ),
        "faq": _faq(
            (
                "Sapa est dans quelle province ?",
                "Sapa (Sa Pa) est dans la province de Lào Cai, au nord-ouest, à ~6–8 h de Hanoï "
                "en train de nuit ou bus.",
                "What province is Sapa in?",
                "Sapa (Sa Pa) is in Lao Cai province, north-west Vietnam, about 6–8 hours from Hanoi "
                "by overnight train or bus.",
            ),
            (
                "Combien de jours à Sapa ?",
                "2 nuits pour un trek d'une journée ; 3 nuits pour un village plus loin. "
                "Un circuit 15 jours l'inclut souvent après Hanoï.",
                "How long in Sapa?",
                "Two nights for a day trek; three for a further village. A 15-day itinerary often "
                "puts it after Hanoi.",
            ),
        ),
    },
    "halong": {
        "geo": (20.9101, 107.1839),
        "contained": _loc("Province de Quảng Ninh", "Quảng Ninh province"),
        "alts": ["Hạ Long", "Ha Long", "Halong Bay", "Baie d'Halong"],
        "h1": _loc(
            "Guide baie d'Halong 2026 — croisière, Cat Ba, que faire",
            "Halong Bay guide 2026 — cruise, Cat Ba, things to do",
        ),
        "title": _loc(
            "Baie d'Halong 2026 — croisière, Quảng Ninh, Cat Ba",
            "Halong Bay Vietnam 2026 — cruise, Quang Ninh, Cat Ba",
        ),
        "desc": _loc(
            "Baie d'Halong (Hạ Long, Quảng Ninh) : croisière 1–2 nuits, alternative Cat Ba, "
            "depuis Hanoï. Guide 2026.",
            "Halong Bay (Ha Long, Quang Ninh): 1–2 night cruise, Cat Ba alternative, "
            "from Hanoi. 2026 guide.",
        ),
        "kw": _loc(
            "Hạ Long, Halong, baie d'Halong, Quảng Ninh, croisière Halong",
            "Halong Bay, Ha Long Vietnam, Quang Ninh, Halong cruise",
        ),
        "faq": _faq(
            (
                "Croisière Halong ou île de Cat Ba ?",
                "Croisière = confort et paysages classiques. Cat Ba = plus d'autonomie, randonnée, kayak. "
                "Les deux sont dans le même massif karstique marin.",
                "Halong cruise or Cat Ba island?",
                "A cruise is comfort and classic views. Cat Ba is more independent, with hiking and kayaks. "
                "Both sit in the same marine karst.",
            ),
        ),
    },
    "delta-du-mekong": {
        "geo": (10.2270, 105.9570),
        "contained": _loc("Delta du Mékong", "Mekong Delta"),
        "alts": ["Mekong Delta", "Mỹ Tho", "Cần Thơ", "My Tho"],
        "h1": _loc(
            "Guide delta du Mékong 2026 — Mỹ Tho, Cần Thơ, que faire",
            "Mekong Delta guide 2026 — My Tho, Can Tho, things to do",
        ),
        "title": _loc(
            "Delta du Mékong 2026 — Mỹ Tho, Cần Thơ, excursion",
            "Mekong Delta Vietnam 2026 — My Tho, Can Tho, day trip",
        ),
        "desc": _loc(
            "Delta du Mékong : Mỹ Tho, Cần Thơ, marchés flottants, excursion depuis Saigon "
            "ou 2 nuits. Guide 2026.",
            "Mekong Delta: My Tho, Can Tho, floating markets, day trip from Saigon "
            "or two nights. 2026 guide.",
        ),
        "kw": _loc(
            "delta du Mékong, Mỹ Tho, Cần Thơ, Mekong Delta Vietnam",
            "Mekong Delta Vietnam, My Tho, Can Tho, Mekong Delta day trip",
        ),
        "faq": _faq(
            (
                "Mỹ Tho ou Cần Thơ ?",
                "Mỹ Tho = excursion journée depuis Saigon. Cần Thơ = marchés flottants et 1–2 nuits "
                "pour voir le delta autrement qu'en tour bus.",
                "My Tho or Can Tho?",
                "My Tho is a day trip from Saigon. Can Tho is floating markets and 1–2 nights "
                "to see the delta beyond a bus tour.",
            ),
        ),
    },
    "mui-ne": {
        "geo": (10.9333, 108.2833),
        "contained": _loc("Phan Thiết, Bình Thuận", "Phan Thiet, Binh Thuan"),
        "alts": ["Mũi Né", "Mui Ne", "Phan Thiết"],
        "h1": _loc(
            "Guide Mũi Né 2026 — dunes, Phan Thiết, que faire",
            "Mui Ne Vietnam 2026 — dunes, Phan Thiet, things to do",
        ),
        "title": _loc(
            "Mũi Né Vietnam 2026 — dunes, Phan Thiết, que faire",
            "Mui Ne Vietnam 2026 — dunes, Phan Thiet travel guide",
        ),
        "desc": _loc(
            "Mũi Né / Phan Thiết : dunes, kite, plage, week-end depuis Saigon ou étape "
            "vers Nha Trang. Guide 2026.",
            "Mui Ne / Phan Thiet: dunes, kitesurf, beach, Saigon weekend or stop "
            "towards Nha Trang. 2026 guide.",
        ),
        "kw": _loc(
            "Mũi Né, Mui Ne, Phan Thiết, voyage Phan Thiet, Mũi Né Vietnam",
            "Mui Ne Vietnam, Phan Thiet Vietnam, Mui Ne dunes",
        ),
        "faq": _faq(
            (
                "Mũi Né ou Nha Trang ?",
                "Mũi Né = dunes, resorts étalés, kite. Nha Trang = vraie ville balnéaire, îles, plus d'animations. "
                "Selon que vous voulez calme ou ville.",
                "Mui Ne or Nha Trang?",
                "Mui Ne is dunes, spread-out resorts and kite. Nha Trang is a proper beach city with islands "
                "and more nightlife. Pick calm versus city.",
            ),
        ),
    },
    "can-tho": {
        "geo": (10.0452, 105.7469),
        "contained": _loc("Cần Thơ", "Can Tho"),
        "alts": ["Cần Thơ", "Can Tho"],
        "h1": _loc(
            "Guide Cần Thơ 2026 — marché flottant, delta du Mékong",
            "Can Tho Vietnam 2026 — floating market, Mekong Delta",
        ),
        "title": _loc(
            "Cần Thơ Vietnam 2026 — marché flottant, Mékong",
            "Can Tho Vietnam 2026 — floating market, Mekong guide",
        ),
        "desc": _loc(
            "Cần Thơ : capitale du delta, Cai Rang, où dormir, comment venir de Saigon. Guide 2026.",
            "Can Tho: Mekong capital, Cai Rang floating market, where to stay, from Saigon. 2026 guide.",
        ),
        "kw": _loc(
            "Cần Thơ, Can Tho Vietnam, marché flottant Cần Thơ, delta du Mékong",
            "Can Tho Vietnam, Cai Rang, Mekong Delta Can Tho",
        ),
        "faq": _faq(
            (
                "Pourquoi dormir à Cần Thơ ?",
                "Pour voir Cai Rang à l'aube sans partir de Saigon à 4 h. Une nuit suffit souvent.",
                "Why stay in Can Tho?",
                "To see Cai Rang at dawn without leaving Saigon at 4 a.m. One night is often enough.",
            ),
        ),
    },
    "phong-nha": {
        "geo": (17.5908, 106.2833),
        "contained": _loc("Province de Quảng Bình", "Quảng Bình province"),
        "alts": ["Phong Nha", "Phong Nha-Ke Bang"],
        "h1": _loc(
            "Guide Phong Nha 2026 — grottes, parc national",
            "Phong Nha Vietnam 2026 — caves, national park",
        ),
        "title": _loc(
            "Phong Nha Vietnam 2026 — grottes, parc national",
            "Phong Nha Vietnam 2026 — caves, national park guide",
        ),
        "desc": _loc(
            "Phong Nha-Ke Bang : grottes, parc UNESCO, entre Huế et Ninh Binh. Combien de jours. Guide 2026.",
            "Phong Nha-Ke Bang: caves, UNESCO park, between Hue and Ninh Binh. How long. 2026 guide.",
        ),
        "kw": _loc(
            "Phong Nha, Phong Nha Vietnam, parc national Phong Nha",
            "Phong Nha Vietnam, Phong Nha national park, Phong Nha caves",
        ),
        "faq": _faq(
            (
                "Combien de jours à Phong Nha ?",
                "2 nuits pour une grotte « grand public » (Paradise / Phong Nha cave) ; plus si expédition.",
                "How long in Phong Nha?",
                "Two nights for a visitor cave (Paradise / Phong Nha cave); more for expeditions.",
            ),
        ),
    },
    "con-dao": {
        "geo": (8.6930, 106.6096),
        "contained": _loc("Côn Đảo, Bà Rịa–Vũng Tàu", "Con Dao, Ba Ria–Vung Tau"),
        "alts": ["Côn Đảo", "Con Dao", "Côn Sơn"],
        "h1": _loc(
            "Guide Côn Đảo 2026 — île, plages, histoire",
            "Con Dao Vietnam 2026 — island, beaches, history",
        ),
        "title": _loc(
            "Côn Đảo Vietnam 2026 — île, Côn Sơn, que faire",
            "Con Dao island Vietnam 2026 — Con Son travel guide",
        ),
        "desc": _loc(
            "Côn Đảo (Côn Sơn) : île au large du sud, plages, parc, mémoire. Moins touristique que Phú Quốc. Guide 2026.",
            "Con Dao (Con Son): island off the south, beaches, park, memorial sites. Quieter than Phu Quoc. 2026 guide.",
        ),
        "kw": _loc(
            "Côn Đảo, Con Dao, Côn Sơn, Con Dao Vietnam",
            "Con Dao Vietnam, Con Son, Con Dao island",
        ),
        "faq": _faq(
            (
                "Côn Đảo ou Phú Quốc ?",
                "Phú Quốc = plus de vols, plus de resorts. Côn Đảo = plus calme, plus cher à atteindre, plus préservé.",
                "Con Dao or Phu Quoc?",
                "Phu Quoc has more flights and resorts. Con Dao is quieter, dearer to reach, more preserved.",
            ),
        ),
    },
}

DEST_PACKS["da-lat"] = {
    "geo": (11.9404, 108.4583),
    "contained": _loc("Lâm Đồng", "Lam Dong"),
    "alts": ["Đà Lạt", "Da Lat", "Dalat", "Lam Dong"],
    "h1": _loc(
        "Guide Đà Lạt 2026 — Lâm Đồng, séjour, que faire",
        "Da Lat Lam Dong 2026 — highlands, things to do",
    ),
    "title": _loc(
        "Đà Lạt Lâm Đồng 2026 — séjour, climat, que faire",
        "Da Lat Lam Dong Vietnam 2026 — highlands travel guide",
    ),
    "desc": _loc(
        "Đà Lạt (Lâm Đồng) : climat frais, collines, séjour 2–3 jours, lien avec Nha Trang. Guide 2026.",
        "Da Lat (Lam Dong): cool climate, hills, 2–3 day stay, link with Nha Trang. 2026 guide.",
    ),
    "kw": _loc(
        "Đà Lạt, Da Lat Lam Dong, séjour Đà Lạt, Lâm Đồng Vietnam",
        "Da Lat Lam Dong, Dalat Vietnam, Da Lat travel",
    ),
    "faq": _faq(
        (
            "Đà Lạt est dans quelle province ?",
            "Đà Lạt est la capitale de la province de Lâm Đồng, sur les hauts plateaux du Centre.",
            "What province is Da Lat in?",
            "Da Lat is the capital of Lam Dong province, in the central highlands.",
        ),
        (
            "Combien de jours à Đà Lạt ?",
            "2–3 nuits. Souvent combiné avec Nha Trang ou Ho Chi Minh-Ville, pas avec un 10 jours nord-sud serré.",
            "How long in Da Lat?",
            "Two or three nights. Often paired with Nha Trang or HCMC, not a tight 10-day north–south trip.",
        ),
    ),
}
DEST_PACKS["dalat"] = DEST_PACKS["da-lat"]


def _generic_faq(name: str, lang: str) -> list[dict[str, str]]:
    if lang == "en":
        return [
            {
                "question": f"Where is {name} in Vietnam?",
                "answer": (
                    f"{name} is covered in this Vietnam travel guide: location, things to do, "
                    "where to stay and how it fits a 10- or 15-day itinerary."
                ),
            },
            {
                "question": f"How long to stay in {name}?",
                "answer": (
                    f"Most travellers spend 2–3 days in {name}. Add a night if you use it as a base "
                    "for nearby nature or islands."
                ),
            },
            {
                "question": f"Where to stay in {name}?",
                "answer": (
                    f"See the hotel ideas on this {name} page and compare prices before you book. "
                    "Pick a neighbourhood that matches your pace (centre vs quieter)."
                ),
            },
        ]
    return [
        {
            "question": f"Où se trouve {name} au Vietnam ?",
            "answer": (
                f"{name} est détaillé dans ce guide : situation, que faire, où dormir "
                "et comment l'intégrer à un itinéraire 10 ou 15 jours."
            ),
        },
        {
            "question": f"Combien de jours à {name} ?",
            "answer": (
                f"Comptez 2–3 jours à {name} pour la plupart des voyageurs. Ajoutez une nuit "
                "si vous en faites une base pour la nature ou les îles autour."
            ),
        },
        {
            "question": f"Où dormir à {name} ?",
            "answer": (
                f"Les hôtels de cette page {name} sont des pistes : comparez les prix. "
                "Choisissez un quartier selon le rythme (centre vs plus calme)."
            ),
        },
    ]


def apply_destination_seo(dest: dict, slug: str, lang: str) -> dict:
    """Enrichit une fiche destination (copie) avec H1, meta, FAQ, geo GSC."""
    lang = _lang(lang)
    out = dict(dest)
    out["slug"] = slug
    name = dest.get("name") or slug.replace("-", " ").title()
    pack = DEST_PACKS.get(slug)

    if pack:
        out["h1"] = pack["h1"][lang]
        out["meta_title"] = pack["title"][lang]
        out["meta_description"] = truncate_text(pack["desc"][lang], 160)
        out["seo_keywords"] = pack["kw"][lang]
        out["seo_faq"] = pack["faq"][lang]
        out["seo_geo"] = pack.get("geo")
        out["seo_alts"] = list(pack.get("alts") or [])
        contained = pack.get("contained") or {}
        out["seo_contained"] = contained.get(lang) or contained.get("fr")
        out["eat_slug"] = pack.get("eat_slug")
    else:
        if lang == "en":
            out["h1"] = f"{name} Vietnam 2026 — things to do, where to stay"
            out.setdefault(
                "meta_title",
                dest.get("meta_title") or f"{name} Vietnam 2026 — travel guide",
            )
            desc = dest.get("meta_description") or (
                f"{name} travel guide: things to do, where to stay, how to get there. "
                "Practical Vietnam tips for 2026."
            )
        else:
            out["h1"] = f"Guide {name} 2026 — que faire, où dormir"
            out.setdefault(
                "meta_title",
                dest.get("meta_title") or f"Guide {name} Vietnam 2026 — que faire, où dormir",
            )
            desc = dest.get("meta_description") or (
                f"Guide {name} : que faire, où dormir, comment y aller. "
                "Conseils pratiques voyage Vietnam 2026."
            )
        out["meta_title"] = out["meta_title"][:70]
        out["meta_description"] = truncate_text(desc, 160)
        out["seo_keywords"] = (
            f"{name} Vietnam, {name} travel guide, things to do {name}"
            if lang == "en"
            else f"guide {name}, {name} Vietnam, que faire {name}, où dormir {name}"
        )
        out["seo_faq"] = _generic_faq(name, lang)
        out["seo_geo"] = None
        out["seo_alts"] = []
        out["seo_contained"] = None
        out["eat_slug"] = None
    return out


def tourist_destination_schema(
    dest: dict,
    canonical_url: str,
    image_abs: str | None,
    lang: str,
) -> dict:
    lang = _lang(lang)
    name = dest.get("name") or ""
    data: dict[str, Any] = {
        "@type": "TouristDestination",
        "name": name,
        "description": dest.get("meta_description") or dest.get("tagline") or "",
        "url": canonical_url,
        "touristType": "International travellers" if lang == "en" else "Voyageurs internationaux",
        "inLanguage": "en-GB" if lang == "en" else "fr-FR",
        "isAccessibleForFree": True,
        "containedInPlace": {
            "@type": "Country",
            "name": "Vietnam",
        },
    }
    alts = dest.get("seo_alts") or []
    if alts:
        data["alternateName"] = alts
    contained = dest.get("seo_contained")
    if contained:
        data["containedInPlace"] = [
            {"@type": "Country", "name": "Vietnam"},
            {"@type": "AdministrativeArea", "name": contained},
        ]
    geo = dest.get("seo_geo")
    if geo and len(geo) == 2:
        data["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": geo[0],
            "longitude": geo[1],
        }
    if image_abs:
        data["image"] = {
            "@type": "ImageObject",
            "url": image_abs,
            "width": 1200,
            "height": 675,
            "caption": dest.get("image_alt") or name,
        }
    return data


def destination_hotel_list_schema(dest: dict, canonical_url: str, lang: str) -> dict | None:
    hotels = dest.get("hotels") or []
    if not hotels:
        return None
    lang = _lang(lang)
    name = dest.get("name") or ""
    list_name = f"Where to stay in {name}" if lang == "en" else f"Où dormir à {name}"
    elements = []
    for i, hotel in enumerate(hotels, start=1):
        elements.append({
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "LodgingBusiness",
                "name": hotel.get("name") or "",
                "description": hotel.get("desc") or "",
                "url": f"{canonical_url}#ou-dormir",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": name,
                    "addressCountry": "VN",
                },
            },
        })
    return {
        "@type": "ItemList",
        "name": list_name,
        "itemListElement": elements,
        "numberOfItems": len(elements),
        "url": f"{canonical_url}#ou-dormir",
    }


# ── Articles (intention GSC) ────────────────────────────────────────────

ARTICLE_SEO: dict[str, dict[str, dict[str, Any]]] = {
    "meilleurs-restaurants-hanoi": {
        "fr": {
            "meta_title": "Où manger à Hanoï 2026 — street food, cheap food",
            "meta_description": (
                "Où manger à Hanoï : meilleurs restaurants, street food, cheap food, phở et bún chả. "
                "Adresses testées et budget 2–15 €."
            ),
            "tags": [
                "où manger à Hanoï", "best food in Hanoi", "cheap food in Hanoi",
                "Hanoi food guide", "street food Hanoï",
            ],
        },
        "en": {
            "title": "Where to eat in Hanoi 2026: street food, cheap eats, best spots",
            "meta_title": "Where to eat in Hanoi 2026 — street food & cheap eats",
            "meta_description": (
                "Where to eat in Hanoi: best Vietnamese food, cheap street food, phở and bún chả. "
                "Tested spots and prices."
            ),
            "tags": [
                "where to eat in Hanoi", "best food in Hanoi", "cheap food in Hanoi",
                "Hanoi food guide", "best Vietnamese food in Hanoi",
            ],
        },
    },
    "visa-vietnam-guide-complet-francais": {
        "fr": {
            "meta_title": "Prix visa Vietnam 2026 — e-visa, tarif, délai",
            "meta_description": (
                "Prix du visa Vietnam ≈ 25 $ (e-visa). Tarif, frais, délai d'obtention (3–5 jours) "
                "et démarches pour voyageurs français."
            ),
            "tags": ["prix visa Vietnam", "tarif visa Vietnam", "frais visa Vietnam", "e-visa"],
        },
        "en": {
            "title": "Vietnam visa price 2026: e-visa fee, time and how to apply",
            "meta_title": "Vietnam visa price 2026 — e-visa fee & processing time",
            "meta_description": (
                "Vietnam e-visa costs about USD 25. Fees, 3–5 day processing and how to apply "
                "on the official site."
            ),
            "tags": ["Vietnam visa price", "Vietnam e-visa fee", "Vietnam visa cost"],
        },
    },
    "transport-vietnam-train-bus-vol": {
        "fr": {
            "meta_title": "Transport Vietnam 2026 — train, bus, vol, Grab",
            "meta_description": (
                "Transport au Vietnam : train, bus de nuit, vols intérieurs, Grab. "
                "Comment se déplacer, prix et durées 2026."
            ),
            "tags": ["transport Vietnam", "se déplacer au Vietnam", "bus Vietnam", "Grab Vietnam"],
        },
        "en": {
            "title": "Transport in Vietnam 2026: train, bus, flights and Grab",
            "meta_title": "Transport in Vietnam 2026 — train, bus, flights, Grab",
            "meta_description": (
                "Getting around Vietnam: trains, night buses, domestic flights and Grab. "
                "Prices, times and how to book."
            ),
            "tags": ["transport Vietnam", "public transport Vietnam", "bus Vietnam", "Grab Vietnam"],
        },
    },
    "budget-voyage-vietnam-2026": {
        "fr": {
            "meta_title": "Budget voyage Vietnam 2026 — prix par jour",
            "meta_description": (
                "Budget voyage Vietnam : backpacker, confort, premium. Prix hébergement, "
                "nourriture, transport — coût 2026."
            ),
            "tags": ["budget voyage Vietnam", "prix voyage Vietnam", "coût Vietnam"],
        },
        "en": {
            "title": "Vietnam travel budget 2026: daily cost for hotels and food",
            "meta_title": "Vietnam travel budget 2026 — daily cost & prices",
            "meta_description": (
                "Vietnam trip budget 2026: backpacker to premium daily costs for hotels, food "
                "and transport."
            ),
            "tags": ["Vietnam travel budget", "Vietnam cost of travel", "Vietnam daily budget"],
        },
    },
    "carte-sim-esim-vietnam": {
        "fr": {
            "meta_title": "eSIM Vietnam 2026 — prix, SIM touriste vs eSIM",
            "meta_description": (
                "eSIM et carte SIM Vietnam pour touristes : Airalo, Holafly, Viettel. "
                "Prix, data et comparatif."
            ),
            "tags": ["eSIM Vietnam", "SIM Vietnam", "prix eSIM Vietnam"],
        },
        "en": {
            "title": "Vietnam eSIM 2026: tourist SIM vs eSIM prices",
            "meta_title": "Vietnam eSIM 2026 — tourist SIM vs eSIM prices",
            "meta_description": (
                "Vietnam tourist SIM vs eSIM: Airalo, Holafly, Viettel. Prices, data and "
                "which to pick in 2026."
            ),
            "tags": ["Vietnam eSIM", "Vietnam SIM card", "eSIM Vietnam price"],
        },
    },
    "securite-voyage-vietnam-conseils": {
        "fr": {
            "meta_title": "Sécurité Vietnam 2026 — dangers, arnaques, is it safe",
            "meta_description": (
                "Le Vietnam est-il sûr ? Dangers, arnaques, quartiers à éviter, conseils Hanoï "
                "et Ho Chi Minh-Ville."
            ),
            "tags": ["sécurité Vietnam", "is Vietnam safe", "dangers Vietnam", "arnaques Vietnam"],
        },
        "en": {
            "title": "Is Vietnam safe to travel in 2026? Warnings and tips",
            "meta_title": "Is Vietnam safe 2026? Travel warnings and tips",
            "meta_description": (
                "Is it safe to travel to Vietnam? Scams, places to avoid, Hanoi and Ho Chi Minh City tips."
            ),
            "tags": ["is Vietnam safe", "Vietnam travel safety", "dangers in Vietnam"],
        },
    },
    "plats-incontournables-vietnam": {
        "fr": {
            "meta_title": "Cuisine vietnamienne 2026 — street food & plats",
            "meta_description": (
                "Cuisine vietnamienne : phở, bánh mì, street food. Plats incontournables "
                "région par région, y compris Hanoï."
            ),
            "tags": ["cuisine vietnamienne", "street food Vietnam", "Vietnamese food"],
        },
        "en": {
            "title": "Vietnamese food 2026: must-try dishes and street food",
            "meta_title": "Best Vietnamese food 2026 — dishes & street food",
            "meta_description": (
                "Vietnamese food guide: phở, bánh mì, street food and must-try dishes by region."
            ),
            "tags": ["Vietnamese food", "Vietnam street food", "best Vietnam food"],
        },
    },
    "hoi-an-lanternes-vieille-ville": {
        "fr": {
            "meta_title": "Hội An 2026 — lanternes, où est Hội An, que visiter",
            "meta_description": (
                "Où est Hội An au Vietnam ? Vieille ville, festival des lanternes 2026–2027, "
                "que visiter. Guide pratique."
            ),
            "tags": ["Hội An", "where is Hoi An", "lantern festival Vietnam", "An Hội"],
        },
        "en": {
            "title": "Where is Hoi An in Vietnam? Lanterns and Old Town 2026",
            "meta_title": "Where is Hoi An? 2026 lanterns & Old Town guide",
            "meta_description": (
                "Where is Hoi An in Vietnam? Old Town, lantern festival 2026–2027, things to visit."
            ),
            "tags": ["where is Hoi An", "Hoi An Vietnam", "lantern festival Vietnam 2027"],
        },
    },
}


def apply_article_seo(article: dict, lang: str) -> dict:
    lang = _lang(lang)
    out = dict(article)
    pack = (ARTICLE_SEO.get(article.get("slug") or "") or {}).get(lang) or {}
    if pack.get("title"):
        out["title"] = pack["title"]
    if pack.get("meta_title"):
        out["meta_title"] = pack["meta_title"]
    if pack.get("meta_description"):
        out["meta_description"] = pack["meta_description"]
    if pack.get("tags"):
        # Garde les tags existants, ajoute les mots-clés GSC en tête.
        existing = [t for t in (out.get("tags") or []) if t not in pack["tags"]]
        out["tags"] = pack["tags"] + existing
    return out


# ── FAQ outils (saisons, budget, eSIM) ──────────────────────────────────

TOOL_FAQ: dict[str, dict[str, list[dict[str, str]]]] = {
    "season": _faq(
        (
            "Quelle est la meilleure période pour le Vietnam (météo) ?",
            "Il n'y a pas un seul « meilleur mois » : suivez la saison sèche région par région "
            "(nord oct.–avr., sud déc.–avr., centre janv.–août hors typhons). Notre calendrier ci-dessus détaille chaque zone.",
            "What is the best time to visit Vietnam for weather?",
            "There is no single best month: follow the dry season by region (north Oct–Apr, south Dec–Apr, "
            "centre Jan–Aug outside typhoons). The calendar above breaks it down.",
        ),
        (
            "Quand partir au Vietnam du Sud ?",
            "Décembre à avril est en général le plus sec autour de Ho Chi Minh-Ville, du Mékong et de Phú Quốc. "
            "Mai–novembre est plus pluvieux, avec des averses souvent courtes.",
            "When to visit south Vietnam?",
            "December to April is usually driest around Ho Chi Minh City, the Mekong and Phu Quoc. "
            "May–November is wetter, often with short downpours.",
        ),
        (
            "Quelle saison au Vietnam en ce moment ?",
            "Le pays a trois climats. Utilisez le planificateur ci-dessus pour le mois de votre voyage "
            "et la région (nord, centre, sud) — « maintenant » n'est jamais le même partout.",
            "What season is it in Vietnam right now?",
            "Vietnam has three climates. Use the planner above for your travel month and region "
            "(north, centre, south) — “right now” is never the same everywhere.",
        ),
    ),
    "budget": _faq(
        (
            "Quel budget pour un voyage au Vietnam ?",
            "Hors vols internationaux : environ 25–35 €/jour en backpacker, 45–70 € en confort, "
            "100 €+ en premium (hébergement, repas, transport local). Le calculateur ci-dessus affine selon la durée.",
            "How much does a Vietnam trip cost?",
            "Excluding international flights: about €25–35/day backpacker, €45–70 mid-range, "
            "€100+ premium (hotels, food, local transport). The calculator above scales by trip length.",
        ),
        (
            "Combien coûtent les choses au Vietnam en 2026 ?",
            "Street food 1,50–4 €, hôtel simple 12–25 €, Grab urbain quelques euros, vol intérieur 35–70 €. "
            "Les prix touristiques au centre de Hanoï ou Hội An sont plus élevés que les prix locaux.",
            "How much do things cost in Vietnam in 2026?",
            "Street food €1.50–4, simple hotel €12–25, inner-city Grab a few euros, domestic flight €35–70. "
            "Tourist prices in central Hanoi or Hoi An run higher than local prices.",
        ),
    ),
    "essentials": _faq(
        (
            "eSIM ou carte SIM touriste au Vietnam ?",
            "L'eSIM (Airalo, Holafly…) s'active avant l'atterrissage. Une SIM Viettel/Vinaphone à l'aéroport "
            "est souvent un peu moins chère au Go mais demande une file et votre passeport.",
            "Vietnam tourist SIM vs eSIM?",
            "An eSIM (Airalo, Holafly…) activates before landing. A Viettel/Vinaphone SIM at the airport "
            "can be a bit cheaper per GB but means a queue and your passport.",
        ),
        (
            "Combien coûte une eSIM Vietnam ?",
            "Comptez souvent 5–20 € selon le volume (1–20 Go) et la durée (7–30 jours). "
            "Comparez les lignes du tableau ci-dessus — les prix bougent.",
            "How much is an eSIM in Vietnam?",
            "Often €5–20 depending on data (1–20 GB) and length (7–30 days). "
            "Compare the table above — prices move.",
        ),
    ),
}


def tool_faq(page: str, lang: str) -> list[dict[str, str]]:
    block = TOOL_FAQ.get(page) or {}
    return list(block.get(_lang(lang)) or [])


def how_to_schema(
    name: str,
    description: str,
    steps: list[tuple[str, str]],
    url: str,
    lang: str = "fr",
) -> dict:
    return {
        "@type": "HowTo",
        "name": name,
        "description": description,
        "url": url,
        "inLanguage": "en-GB" if _lang(lang) == "en" else "fr-FR",
        "totalTime": "P5D",
        "estimatedCost": {
            "@type": "MonetaryAmount",
            "currency": "USD",
            "value": "25",
        },
        "step": [
            {
                "@type": "HowToStep",
                "position": i,
                "name": title,
                "text": text,
            }
            for i, (title, text) in enumerate(steps, start=1)
        ],
    }


def festival_event_schema(ev: dict, page_url: str) -> dict:
    dests = ev.get("destinations") or []
    loc_name = dests[0]["name"] if dests and isinstance(dests[0], dict) else "Vietnam"
    image = ev.get("image")
    if image and not str(image).startswith("http"):
        image = config.SITE_URL.rstrip("/") + str(image)
    data: dict[str, Any] = {
        "@type": "Event",
        "name": ev.get("title") or "",
        "startDate": ev.get("start_date") or ev.get("start"),
        "endDate": ev.get("end_date") or ev.get("end") or ev.get("start_date"),
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {
            "@type": "Place",
            "name": loc_name,
            "address": {"@type": "Country", "name": "Vietnam"},
        },
        "description": ev.get("summary") or "",
        "url": f"{page_url}#event-{ev.get('id', '')}",
        "organizer": {
            "@type": "Organization",
            "name": config.SITE_NAME,
            "url": config.SITE_URL.rstrip("/"),
        },
    }
    if image:
        data["image"] = image
    return data
