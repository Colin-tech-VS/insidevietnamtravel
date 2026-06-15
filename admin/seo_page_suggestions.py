"""Propositions de pages SEO landing — locales + IA + GSC."""

from __future__ import annotations

import random
from datetime import date

from admin import ai_client
from admin.partner_seo_keywords import gsc_top_queries, seed_keywords
from admin.seo_pages_service import get_published_seo_pages
from admin.store import get_articles
from data.vietnam_cities import ALL_CITY_VALUES

SUGGEST_PROMPT = """Tu es stratège SEO senior pour Inside Vietnam Travel (voyage Vietnam, audience française).
Année : {year}.

Pages SEO déjà publiées (/seo/…) — NE PAS dupliquer :
{existing_seo}

Articles blog existants (éviter le même angle) :
{existing_blog}

Requêtes Search Console récentes (prioriser si pertinent) :
{gsc}

Propose exactement 10 idées de PAGES SEO LANDING (pas des articles blog) — chacune cible
un cluster de 3 à 6 mots-clés complémentaires (long-tail + intention de recherche).

JSON uniquement :
{{
  "suggestions": [
    {{
      "topic": "Titre H1 / angle de la landing",
      "keywords": ["mot-clé 1", "mot-clé 2", "mot-clé 3"],
      "city": "Ville ou Tout le Vietnam",
      "page_type": "landing|guide|comparison|faq",
      "priority": "haute|moyenne",
      "reason": "Potentiel SEO en 1 phrase",
      "volume_hint": "fort|moyen|niche"
    }}
  ]
}}

Villes autorisées : {cities}
"""


def _existing_titles() -> set[str]:
    titles: set[str] = set()
    for p in get_published_seo_pages():
        titles.add((p.get("title") or "").lower())
        for kw in p.get("target_keywords") or []:
            titles.add(str(kw).lower())
    for a in get_articles()[:40]:
        titles.add((a.get("title") or "").lower())
    return titles


def _is_duplicate(topic: str, existing: set[str]) -> bool:
    t = (topic or "").lower()
    if not t:
        return True
    head = t[:35]
    return any(head in e or e[:35] in t for e in existing if e)


def _fallback_pool(year: int) -> list[dict]:
    gsc = list(gsc_top_queries(limit=6))
    seeds = list(seed_keywords("fr")[:12])
    pool = [
        {
            "topic": f"Visa Vietnam {year} : e-visa et formalités pour Français",
            "keywords": ["visa vietnam", "evisa vietnam", f"visa vietnam {year}", "formalités vietnam", "voyage vietnam visa"],
            "city": "Tout le Vietnam",
            "page_type": "landing",
            "priority": "haute",
            "reason": "Requête annuelle très forte",
            "volume_hint": "fort",
        },
        {
            "topic": "Budget voyage Vietnam : prix réels par jour en euros",
            "keywords": ["budget vietnam", "prix voyage vietnam", "combien coûte vietnam", "voyage vietnam pas cher", "coût séjour vietnam"],
            "city": "Tout le Vietnam",
            "page_type": "comparison",
            "priority": "haute",
            "reason": "Intention transactionnelle + affiliation",
            "volume_hint": "fort",
        },
        {
            "topic": "Quand partir au Vietnam : meilleures saisons par région",
            "keywords": ["quand partir vietnam", "meilleure période vietnam", "météo vietnam voyage", "saison sèche vietnam", "climat vietnam"],
            "city": "Tout le Vietnam",
            "page_type": "guide",
            "priority": "haute",
            "reason": "Evergreen + complète l'outil saison",
            "volume_hint": "fort",
        },
        {
            "topic": "Croisière baie d'Halong : laquelle choisir en {year}",
            "keywords": ["croisière halong", "baie halong voyage", "excursion halong", "halong 1 jour 2 jours", "meilleure croisière halong"],
            "city": "Ha Long / Quảng Ninh",
            "page_type": "comparison",
            "priority": "haute",
            "reason": "Comparatif très recherché",
            "volume_hint": "fort",
        },
        {
            "topic": "Que faire à Hanoï : incontournables et itinéraire 3 jours",
            "keywords": ["que faire hanoi", "visite hanoi", "guide hanoi", "itinéraire hanoi 3 jours", "voyage hanoi vietnam"],
            "city": "Hanoï",
            "page_type": "landing",
            "priority": "haute",
            "reason": "Cluster ville Nord",
            "volume_hint": "fort",
        },
        {
            "topic": "Hội An en 2 ou 3 jours : guide complet ancienne ville",
            "keywords": ["que faire hoi an", "visite hoi an", "guide hoi an", "hoi an 2 jours", "ancienne ville hoi an"],
            "city": "Hội An",
            "page_type": "landing",
            "priority": "haute",
            "reason": "Destination phare centre Vietnam",
            "volume_hint": "fort",
        },
        {
            "topic": "eSIM Vietnam : forfait data et connexion avant le départ",
            "keywords": ["esim vietnam", "carte sim vietnam", "internet vietnam voyage", "forfait data vietnam", "connexion vietnam"],
            "city": "Tout le Vietnam",
            "page_type": "landing",
            "priority": "moyenne",
            "reason": "Affiliation eSIM",
            "volume_hint": "moyen",
        },
        {
            "topic": "Assurance voyage Vietnam : couverture et choix pour Français",
            "keywords": ["assurance voyage vietnam", "assurance santé vietnam", "mutuelle voyage vietnam", "rapatriement vietnam"],
            "city": "Tout le Vietnam",
            "page_type": "faq",
            "priority": "moyenne",
            "reason": "Affiliation assurance",
            "volume_hint": "moyen",
        },
        {
            "topic": "Phú Quốc : plages, saison et où dormir",
            "keywords": ["phu quoc voyage", "plage phu quoc", "sejour phu quoc", "hotel phu quoc", "que faire phu quoc"],
            "city": "Phú Quốc",
            "page_type": "landing",
            "priority": "moyenne",
            "reason": "Cluster îles Sud",
            "volume_hint": "moyen",
        },
        {
            "topic": "Sapa trek et rizières : guide pratique randonnée",
            "keywords": ["trek sapa", "rizières sapa", "randonnée sapa", "guide sapa vietnam", "sapa 2 jours"],
            "city": "Sapa / Lào Cai",
            "page_type": "guide",
            "priority": "moyenne",
            "reason": "Niche adventure + forte saisonnalité",
            "volume_hint": "moyen",
        },
        {
            "topic": "Ho Chi Minh-Ville : que voir en 2 jours (Saigon)",
            "keywords": ["que faire saigon", "visite ho chi minh", "guide saigon", "ho chi minh 2 jours", "voyage saigon vietnam"],
            "city": "Ho Chi Minh-Ville",
            "page_type": "landing",
            "priority": "haute",
            "reason": "Hub Sud indispensable",
            "volume_hint": "fort",
        },
        {
            "topic": "Delta du Mékong : excursion 1 jour depuis HCMC",
            "keywords": ["delta mekong excursion", "croisière mekong", "mekong 1 jour", "visite delta mekong", "mekong depuis saigon"],
            "city": "Mỹ Tho / Delta Mekong",
            "page_type": "guide",
            "priority": "moyenne",
            "reason": "Tours affiliés",
            "volume_hint": "moyen",
        },
    ]
    for i, q in enumerate(gsc[:4]):
        pool.insert(i, {
            "topic": f"{q.strip().capitalize()} — guide voyage Vietnam",
            "keywords": [q, f"{q} vietnam", "voyage vietnam", "guide voyage vietnam"],
            "city": "Tout le Vietnam",
            "page_type": "landing",
            "priority": "haute",
            "reason": "Requête réelle Search Console",
            "volume_hint": "fort",
        })
    for s in pool:
        s["topic"] = s["topic"].format(year=year)
    existing = _existing_titles()
    available = [s for s in pool if not _is_duplicate(s["topic"], existing)]
    random.seed(date.today().toordinal())
    random.shuffle(available or pool)
    return (available or pool)[:10]


def get_seo_page_suggestions(*, use_ai: bool = True) -> list[dict]:
    today = date.today()
    existing_seo = "\n".join(
        f"- {p.get('title', '')} ({', '.join((p.get('target_keywords') or [])[:4])})"
        for p in get_published_seo_pages()[:20]
    ) or "(aucune)"
    existing_blog = "\n".join(f"- {a.get('title', '')}" for a in get_articles()[:15]) or "(aucun)"
    gsc_lines = "\n".join(f"- {q}" for q in gsc_top_queries(limit=12)) or "(GSC non connecté)"

    if use_ai and ai_client.is_configured():
        try:
            prompt = SUGGEST_PROMPT.format(
                year=today.year,
                existing_seo=existing_seo,
                existing_blog=existing_blog,
                gsc=gsc_lines,
                cities=", ".join(ALL_CITY_VALUES[:18]) + ", …",
            )
            response = ai_client.chat_completion(
                fast=True,
                messages=[
                    {"role": "system", "content": "Tu réponds uniquement en JSON valide."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=2000,
            )
            data = ai_client.parse_json(response.choices[0].message.content)
            out: list[dict] = []
            existing = _existing_titles()
            for s in data.get("suggestions", [])[:12]:
                topic = (s.get("topic") or "").strip()
                if not topic or _is_duplicate(topic, existing):
                    continue
                city = s.get("city", "Tout le Vietnam")
                if city not in ALL_CITY_VALUES:
                    city = next(
                        (c for c in ALL_CITY_VALUES if city.lower() in c.lower() or c.lower() in city.lower()),
                        "Tout le Vietnam",
                    )
                kws = s.get("keywords") or []
                if isinstance(kws, str):
                    kws = [k.strip() for k in kws.split(",") if k.strip()]
                out.append({
                    "topic": topic,
                    "keywords": [str(k).strip() for k in kws if str(k).strip()][:8],
                    "city": city,
                    "page_type": s.get("page_type", "landing"),
                    "priority": s.get("priority", "moyenne"),
                    "reason": s.get("reason", ""),
                    "volume_hint": s.get("volume_hint", "moyen"),
                })
            if len(out) >= 5:
                return out
        except Exception:
            pass

    return _fallback_pool(today.year)
