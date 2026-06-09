"""Traduction FR→EN du contenu via l'IA (modèle rapide, quota séparé)."""

from __future__ import annotations

import json

from admin import ai_client
from i18n_utils import ARTICLE_I18N_FIELDS, DESTINATION_I18N_FIELDS

TRANSLATE_SYSTEM = """You translate Vietnam travel website content from French to English.

Rules:
- Keep HTML tags and structure unchanged
- Keep Vietnamese place names (Hanoi, Hội An, Ho Chi Minh City, Đà Nẵng)
- Keep prices in euros
- Natural British/international English for travellers
- Return valid JSON only with the requested fields translated
"""


def translate_article_block(fr_data: dict, *, pause_before: float = 0, deadline: float | None = 120) -> dict:
    fields = {k: fr_data.get(k, "") for k in ARTICLE_I18N_FIELDS if fr_data.get(k)}
    if not fields:
        return {}

    response = ai_client.chat_completion(
        fast=True,
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
        max_tokens=5120,
        pause_before=pause_before,
        # La traduction EN est secondaire : si elle traîne, on abandonne vite pour
        # livrer quand même le brouillon FR (l'appelant retombe sur du FR seul).
        deadline=deadline,
    )
    return ai_client.parse_json(response.choices[0].message.content)


def translate_destination_block(fr_data: dict, *, pause_before: float = 0) -> dict:
    payload = {
        k: fr_data.get(k)
        for k in DESTINATION_I18N_FIELDS + ("things_to_do", "tips", "hotels", "activities")
        if fr_data.get(k)
    }
    if not payload:
        return {}

    response = ai_client.chat_completion(
        fast=True,
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
        max_tokens=6144,
        pause_before=pause_before,
    )
    data = ai_client.parse_json(response.choices[0].message.content)
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
