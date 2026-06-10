"""Ready-made travel itineraries."""

from copy import deepcopy

from data.itineraries_i18n import ITINERARIES_EN
from data.itinerary_3_days import ITINERARY_3_DAYS_FR
from data.itinerary_7_days import ITINERARY_7_DAYS_FR
from data.itinerary_10_days import ITINERARY_10_DAYS_FR
from data.itinerary_15_days import ITINERARY_15_DAYS_FR
from data.itinerary_media import attach_itinerary_media

_I18N_CONTENT_KEYS = (
    "title", "meta_title", "meta_description", "summary", "budget_hint",
    "overview", "highlights", "experiences", "faq", "affiliate_sections",
    "sample_hotel", "sample_activity", "days", "best_season", "includes", "practical",
)


def _build_itineraries() -> dict:
    base = {
        "3-days-vietnam": ITINERARY_3_DAYS_FR,
        "7-days-vietnam": ITINERARY_7_DAYS_FR,
        "10-days-vietnam": ITINERARY_10_DAYS_FR,
        "15-days-vietnam": ITINERARY_15_DAYS_FR,
    }
    for slug, itin in base.items():
        itin = attach_itinerary_media(itin)
        base[slug] = itin
        fr_block = {k: itin[k] for k in _I18N_CONTENT_KEYS if k in itin}
        en_overlay = ITINERARIES_EN.get(slug, {})
        en_block = deepcopy(fr_block)
        for key, val in en_overlay.items():
            if isinstance(val, dict) and key in en_block and isinstance(en_block[key], dict):
                en_block[key] = {**en_block[key], **val}
            else:
                en_block[key] = val
        itin["i18n"] = {"fr": fr_block, "en": en_block}
    return base


ITINERARIES = _build_itineraries()
