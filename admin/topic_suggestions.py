"""Suggestions de sujets d'articles — rafraîchies à chaque visite."""

import json
import random
from datetime import date

from admin import ai_client
from admin.store import get_articles
from data.vietnam_cities import ALL_CITY_VALUES

SUGGEST_PROMPT = """Tu es éditeur SEO pour un blog voyage Vietnam (audience française).
Année actuelle : {year}, mois : {month}.

Articles déjà publiés (évite les doublons) :
{existing}

Propose exactement 8 idées d'articles NOUVELLES, utiles et actuelles pour {year}.
Varie les villes du Vietnam et les types (pratique, food, itinéraire, budget, activités).

Réponds en JSON uniquement :
{{
  "suggestions": [
    {{
      "topic": "Titre/sujet précis de l'article",
      "guide_type": "Article blog SEO|Guide pratique|Guide ville|Itinéraire|Conseils budget|Gastronomie",
      "city": "Une ville de la liste fournie",
      "reason": "Pourquoi cet article en 1 phrase courte",
      "priority": "haute|moyenne"
    }}
  ]
}}

Villes autorisées : {cities}
"""


def _fallback_pool(year: int, month: int) -> list[dict]:
    """Pool local — rotation par jour pour varier sans API."""
    pool = [
        {"topic": f"Visa Vietnam {year} : procédure e-visa pour les Français", "guide_type": "Guide pratique", "city": "Tout le Vietnam", "reason": "Recherche forte chaque année", "priority": "haute"},
    ]
    pool += [
        {"topic": f"Budget voyage {city} — combien prévoir par jour", "guide_type": "Conseils budget", "city": city, "reason": "Long-tail SEO par ville", "priority": "haute"}
        for city in ["Hanoï", "Hội An", "Ho Chi Minh-Ville", "Đà Nẵng", "Phú Quốc"]
    ]
    pool += [
        {"topic": "Carte eSIM Vietnam : quel forfait choisir avant le départ", "guide_type": "Guide pratique", "city": "Tout le Vietnam", "reason": "Question fréquente des voyageurs", "priority": "haute"},
        {"topic": "Street food à Hanoï : 10 plats à goûter absolument", "guide_type": "Gastronomie", "city": "Hanoï", "reason": "Fort potentiel affiliation food tours", "priority": "moyenne"},
        {"topic": "Que faire 3 jours à Hội An — itinéraire détaillé", "guide_type": "Itinéraire", "city": "Hội An", "reason": "Destination très recherchée", "priority": "haute"},
        {"topic": "Baie d'Halong ou Lan Ha : laquelle choisir en {year}", "guide_type": "Guide pratique", "city": "Ha Long / Quảng Ninh", "reason": "Comparatif evergreen", "priority": "moyenne"},
        {"topic": "Guide complet Sapa : trek, météo et logement", "guide_type": "Guide ville", "city": "Sapa / Lào Cai", "reason": "Saison trek printemps/automne", "priority": "moyenne"},
        {"topic": "Ho Chi Minh-Ville en 48h : incontournables", "guide_type": "Itinéraire", "city": "Ho Chi Minh-Ville", "reason": "City break populaire", "priority": "haute"},
        {"topic": "Delta du Mékong : excursion 1 ou 2 jours depuis HCMC", "guide_type": "Guide pratique", "city": "Mỹ Tho / Delta Mekong", "reason": "Affiliation tours", "priority": "moyenne"},
        {"topic": "Đà Lạt : guide de la ville fraîche du Vietnam", "guide_type": "Guide ville", "city": "Đà Lạt / Lâm Đồng", "reason": "Destination montagne tendance", "priority": "moyenne"},
        {"topic": "Phú Quốc {year} : plages, saison et hôtels", "guide_type": "Guide ville", "city": "Phú Quốc", "reason": "Affiliation hôtels forte", "priority": "haute"},
        {"topic": "Traverser la rue au Vietnam sans stress", "guide_type": "Article blog SEO", "city": "Tout le Vietnam", "reason": "Viral + utile débutants", "priority": "moyenne"},
        {"topic": "Meilleure période pour visiter le Vietnam en {year}", "guide_type": "Guide pratique", "city": "Tout le Vietnam", "reason": "SEO saisonnier", "priority": "haute"},
        {"topic": "Huế : cité impériale et gastronomie", "guide_type": "Guide ville", "city": "Huế", "reason": "Complète le cluster centre", "priority": "moyenne"},
        {"topic": "Nha Trang ou Đà Nẵng : quelle plage choisir", "guide_type": "Article blog SEO", "city": "Nha Trang", "reason": "Comparatif recherché", "priority": "moyenne"},
        {"topic": "Ha Giang Loop : guide moto et sécurité", "guide_type": "Guide pratique", "city": "Ha Giang", "reason": "Niche adventure travel", "priority": "moyenne"},
        {"topic": "Assurance voyage Vietnam : ce qu'il faut couvrir", "guide_type": "Guide pratique", "city": "Tout le Vietnam", "reason": "Affiliation assurance", "priority": "moyenne"},
        {"topic": "Où dormir à Hanoï : quartiers et budgets", "guide_type": "Guide ville", "city": "Hanoï", "reason": "Affiliation Booking/Agoda", "priority": "haute"},
    ]
    # Format year in topics
    formatted = []
    for s in pool:
        item = {**s}
        item["topic"] = item["topic"].format(year=year, city=item.get("city", ""))
        formatted.append(item)

    # Rotate by day of year + filter similar to existing
    existing_titles = {a["title"].lower() for a in get_articles()}
    available = [s for s in formatted if not any(s["topic"].lower()[:30] in t for t in existing_titles)]
    if len(available) < 8:
        available = formatted

    day_seed = date.today().toordinal()
    random.seed(day_seed)
    random.shuffle(available)
    return available[:8]


def get_topic_suggestions(use_ai: bool = True) -> list[dict]:
    """Retourne 8 suggestions — IA si une clé est dispo, sinon pool local rotatif."""
    today = date.today()
    existing = get_articles()
    existing_lines = "\n".join(f"- {a['title']}" for a in existing[:15]) or "(aucun)"

    if use_ai and ai_client.is_configured():
        try:
            cities_str = ", ".join(ALL_CITY_VALUES[:20]) + ", ..."
            prompt = SUGGEST_PROMPT.format(
                year=today.year,
                month=today.strftime("%B"),
                existing=existing_lines,
                cities=cities_str,
            )
            response = ai_client.chat_completion(
                fast=True,
                messages=[
                    {"role": "system", "content": "Tu réponds uniquement en JSON valide."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.85,
                max_tokens=1200,
            )
            data = json.loads(response.choices[0].message.content)
            suggestions = data.get("suggestions", [])[:8]
            # Valider les villes
            valid = []
            for s in suggestions:
                city = s.get("city", "Tout le Vietnam")
                if city not in ALL_CITY_VALUES:
                    # Match approximatif
                    match = next((c for c in ALL_CITY_VALUES if city.lower() in c.lower() or c.lower() in city.lower()), "Tout le Vietnam")
                    city = match
                valid.append({
                    "topic": s.get("topic", ""),
                    "guide_type": s.get("guide_type", "Article blog SEO"),
                    "city": city,
                    "reason": s.get("reason", ""),
                    "priority": s.get("priority", "moyenne"),
                })
            if len(valid) >= 5:
                return valid
        except Exception:
            pass

    return _fallback_pool(today.year, today.month)
