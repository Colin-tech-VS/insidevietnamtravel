"""Build affiliate URLs with destination + product context."""

from urllib.parse import urlencode

def _get_affiliate_ids():
    try:
        from admin.store import get_affiliate_ids
        return get_affiliate_ids()
    except ImportError:
        from data.affiliates import AFFILIATE_IDS
        return AFFILIATE_IDS


def _ids():
    return _get_affiliate_ids()

# Per-city affiliate parameters (Booking search, Agoda city ID, GYG slug, Viator dest ID)
# GYG slugs vérifiés — l176 = Miami (incorrect pour HCMC), utiliser l272.
LOCATION_META = {
    "hanoi": {
        "label": "Hanoï",
        "booking_city": "Hanoi, Vietnam",
        "agoda_city_id": 2758,
        "gyg_location": "hanoi-l205",
        "viator_dest": "351",
    },
    "ho-chi-minh-city": {
        "label": "Ho Chi Minh-Ville",
        "booking_city": "Ho Chi Minh City, Vietnam",
        "agoda_city_id": 13170,
        "gyg_location": "ho-chi-minh-city-l272",
        "viator_dest": "352",
    },
    "hoi-an": {
        "label": "Hội An",
        "booking_city": "Hoi An, Vietnam",
        "agoda_city_id": 16552,
        "gyg_location": "hoi-an-l831",
        "viator_dest": "5229",
    },
    "da-nang": {
        "label": "Đà Nẵng",
        "booking_city": "Da Nang, Vietnam",
        "agoda_city_id": 16440,
        "gyg_location": "da-nang-l939",
        "viator_dest": "4680",
    },
}


def get_location_meta(slug: str, *, name: str | None = None) -> dict:
    """Métadonnées affiliées pour une destination — IDs vérifiés pour le Vietnam."""
    if slug in LOCATION_META:
        return dict(LOCATION_META[slug])
    label = name or slug.replace("-", " ").title()
    return {
        "label": label,
        "booking_city": f"{label}, Vietnam",
        "agoda_city_id": 0,
        "gyg_location": "",
        "viator_dest": "",
    }


def _booking(params: dict) -> str:
    params = {**params, "aid": _ids()["booking_aid"], "lang": "fr"}
    return f"https://www.booking.com/searchresults.html?{urlencode(params)}"


def _agoda(params: dict) -> str:
    params = {**params, "cid": _ids()["agoda_cid"], "locale": "fr-fr"}
    return f"https://www.agoda.com/search?{urlencode(params)}"


def _getyourguide(location_slug: str, query: str) -> str:
    q = query.strip()
    if "vietnam" not in q.lower():
        q = f"{q} Vietnam"
    params = {"q": q, "partner_id": _ids()["gyg_partner_id"]}
    if location_slug:
        return f"https://www.getyourguide.com/{location_slug}/?{urlencode(params)}"
    return f"https://www.getyourguide.com/s/?{urlencode(params)}"


def _viator(query: str, dest_id: str) -> str:
    q = query.strip()
    if "vietnam" not in q.lower():
        q = f"{q} Vietnam"
    params = {
        "text": q,
        "pid": _ids()["viator_pid"],
        "mcid": _ids()["viator_pid"],
    }
    if dest_id:
        params["destId"] = dest_id
    return f"https://www.viator.com/searchResults/all?{urlencode(params)}"


def booking_hotel(hotel_name: str, location: dict) -> str:
    return _booking({"ss": f"{hotel_name}, {location['booking_city']}"})


def booking_city(location: dict) -> str:
    return _booking({"ss": location["booking_city"]})


def agoda_hotel(hotel_name: str, location: dict) -> str:
    return _agoda({
        "city": location["agoda_city_id"],
        "searchText": hotel_name,
        "rooms": 1,
        "adults": 2,
        "children": 0,
    })


def agoda_city(location: dict) -> str:
    return _agoda({"city": location["agoda_city_id"]})


def getyourguide_activity(query: str, location: dict) -> str:
    return _getyourguide(location["gyg_location"], query)


def viator_activity(query: str, location: dict) -> str:
    return _viator(query, location["viator_dest"])


def build_hotel_link(provider: str, hotel: dict, location: dict) -> str:
    if provider == "booking":
        return booking_hotel(hotel.get("search", hotel["name"]), location)
    if provider == "agoda":
        return agoda_hotel(hotel.get("search", hotel["name"]), location)
    return booking_city(location)


def build_activity_link(provider: str, activity: dict, location: dict) -> str:
    query = activity.get("search", activity["name"])
    if not location.get("gyg_location") and not location.get("viator_dest"):
        query = f"{query} {location.get('label', 'Vietnam')}"
    if provider == "getyourguide":
        return getyourguide_activity(query, location)
    if provider == "viator":
        return viator_activity(query, location)
    return getyourguide_activity(query, location)


def build_city_link(provider: str, location: dict) -> str:
    if provider == "booking":
        return booking_city(location)
    if provider == "agoda":
        return agoda_city(location)
    if provider == "getyourguide":
        return f"https://www.getyourguide.com/{location['gyg_location']}/?partner_id={_ids()['gyg_partner_id']}"
    if provider == "viator":
        return f"https://www.viator.com/{location['booking_city'].split(',')[0].replace(' ', '-')}/d{location['viator_dest']}-ttd?pid={_ids()['viator_pid']}"
    return booking_city(location)


def esim_airalo() -> str:
    return f"https://www.airalo.com/vietnam-esim?ref={_ids()['airalo_ref']}"


def esim_holafly() -> str:
    return f"https://esim.holafly.com/data-plans/vietnam/?ref={_ids()['holafly_ref']}"


def travel_insurance() -> str:
    return (
        "https://www.worldnomads.com/travel-insurance/?"
        + urlencode({
            "affiliate": _ids()["worldnomads_affiliate"],
            "destination": "Vietnam",
        })
    )


def pdf_checkout() -> str:
    return _ids().get("pdf_checkout_url", "#pdf-guide")
