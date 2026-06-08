"""Traduction FR→EN du contenu via Groq."""

from __future__ import annotations

import json
import os

from groq import Groq

from admin.store import get_settings
from i18n_utils import ARTICLE_I18N_FIELDS, DESTINATION_I18N_FIELDS

TRANSLATE_SYSTEM = """You translate Vietnam travel website content from French to English.

Rules:
- Keep HTML tags and structure unchanged
- Keep Vietnamese place names (Hanoi, Hội An, Ho Chi Minh City, Đà Nẵng)
- Keep prices in euros
- Natural British/international English for travellers
- Return valid JSON only with the requested fields translated
"""


def _client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY manquante dans le fichier .env")
    settings = get_settings()
    return Groq(api_key=api_key), settings.get("groq_model", "llama-3.3-70b-versatile")


def translate_article_block(fr_data: dict) -> dict:
    fields = {k: fr_data.get(k, "") for k in ARTICLE_I18N_FIELDS if fr_data.get(k)}
    if not fields:
        return {}

    client, model = _client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Translate these French article fields to English:\n"
                    + json.dumps(fields, ensure_ascii=False)
                ),
            },
        ],
        temperature=0.3,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def translate_destination_block(fr_data: dict) -> dict:
    payload = {
        k: fr_data.get(k)
        for k in DESTINATION_I18N_FIELDS + ("things_to_do", "tips", "hotels", "activities")
        if fr_data.get(k)
    }
    if not payload:
        return {}

    client, model = _client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": TRANSLATE_SYSTEM + "\nFor activities, keep 'search' and 'provider' fields in English unchanged if present."},
            {
                "role": "user",
                "content": (
                    "Translate this French destination page content to English. "
                    "Keep arrays structure for things_to_do, tips, hotels, activities:\n"
                    + json.dumps(payload, ensure_ascii=False)
                ),
            },
        ],
        temperature=0.3,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    for item in data.get("activities", []) or []:
        for orig in fr_data.get("activities", []):
            if item.get("name") == orig.get("name") or item.get("search") == orig.get("search"):
                item["search"] = orig.get("search", item.get("search", ""))
                item["provider"] = orig.get("provider", item.get("provider", ""))
    for item in data.get("hotels", []) or []:
        for orig in fr_data.get("hotels", []):
            if item.get("name") == orig.get("name"):
                item["provider"] = orig.get("provider", item.get("provider", ""))
    return data
