"""Génération de pages destination via Groq AI."""

import json
import os
import re
from datetime import date

from groq import Groq

from admin.store import get_settings, slugify

MIN_WORDS = 1200
TARGET_WORDS = 1500

SYSTEM_PROMPT = """Tu es un expert SEO voyage Vietnam pour "Inside Vietnam Travel".

PUBLIC : voyageurs français qui préparent un séjour au Vietnam.

Rédige une page destination COMPLÈTE en JSON valide uniquement :
{
  "name": "Nom affiché (ex: Sapa)",
  "meta_title": "Guide [Ville] 2026 — que faire, où dormir (50-65 car.)",
  "meta_description": "140-160 caractères SEO",
  "tagline": "Accroche courte et poétique (1 phrase)",
  "overview": "<p>HTML...</p> — minimum 400 mots, intro riche SEO",
  "things_to_do": [{"title": "...", "desc": "..."}],
  "hotels": [{"name": "...", "desc": "...", "price_hint": "dès X €/nuit", "provider": "booking|agoda"}],
  "activities": [{"name": "...", "search": "English search query GYG/Viator", "desc": "...", "price_hint": "dès X €", "provider": "getyourguide|viator"}],
  "tips": ["conseil 1", "..."],
  "image_prompt": "Unique English photo prompt: iconic [city] Vietnam landmark scene, photorealistic, 16:9, no text",
  "location_meta": {
    "label": "Nom ville",
    "booking_city": "Ville, Vietnam",
    "agoda_city_id": 0,
    "gyg_location": "slug-gyg-if-known-or-empty",
    "viator_dest": ""
  }
}

Règles :
- Minimum """ + str(MIN_WORDS) + """ mots au TOTAL (overview + texte des sections si besoin enrichir overview).
- things_to_do : 5 à 7 entrées concrètes.
- hotels : 3 hôtels réalistes (budget, milieu, confort).
- activities : 3 activités/tours avec search en anglais.
- tips : 4 à 6 conseils pratiques locaux.
- overview en HTML : <p>, pas de <h1>.
- Prix en euros. Ton honnête. Pas de noms de personnes fictives.
- Contenu 100% centré sur la destination Vietnam demandée.
"""


def _count_words(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len(re.sub(r"\s+", " ", text).strip().split())


def _total_words(dest: dict) -> int:
    n = _count_words(dest.get("overview", ""))
    for item in dest.get("things_to_do", []):
        n += len((item.get("title", "") + " " + item.get("desc", "")).split())
    for tip in dest.get("tips", []):
        n += len(str(tip).split())
    return n


def _build_destination(data: dict, city: str, slug: str) -> dict:
    from data.affiliate_urls import get_location_meta

    loc = get_location_meta(slug, name=data.get("name", city))
    ai_loc = data.get("location_meta") or {}
    for key in ("label", "booking_city"):
        if ai_loc.get(key):
            loc[key] = ai_loc[key]

    return {
        "slug": slug,
        "name": data.get("name", city),
        "meta_title": data.get("meta_title", f"Guide {city} — Vietnam"),
        "meta_description": data.get("meta_description", "")[:160],
        "tagline": data.get("tagline", ""),
        "overview": data.get("overview", ""),
        "things_to_do": data.get("things_to_do", [])[:8],
        "hotels": data.get("hotels", [])[:5],
        "activities": data.get("activities", [])[:5],
        "tips": data.get("tips", [])[:8],
        "image_prompt": data.get("image_prompt", ""),
        "location_meta": loc,
        "ai_generated": True,
        "city": city,
        "updated_at": date.today().isoformat(),
    }


def generate_destination(city: str, notes: str = "") -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY manquante dans le fichier .env")

    settings = get_settings()
    client = Groq(api_key=api_key)
    model = settings.get("groq_model", "llama-3.3-70b-versatile")
    year = date.today().year
    slug = slugify(city)

    user_prompt = f"""Crée une page destination complète pour : {city}

Année : {year}
URL slug : {slug}
Notes éditoriales : {notes or "Guide complet pour voyageurs français"}

Minimum {MIN_WORDS} mots (cible {TARGET_WORDS}).
La page doit convaincre un voyageur de visiter {city} et l'aider à planifier : durée idéale, budget, meilleure période."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.65,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)
    dest = _build_destination(data, city, slug)

    if _total_words(dest) < MIN_WORDS:
        expand = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"L'overview est trop court ({_total_words(dest)} mots). "
                        f"Enrichis pour atteindre {MIN_WORDS}+ mots. "
                        f"Destination : {city}\n\n{json.dumps(dest, ensure_ascii=False)}"
                    ),
                },
            ],
            temperature=0.5,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
        data = json.loads(expand.choices[0].message.content)
        dest = _build_destination(data, city, slug)

    return dest
