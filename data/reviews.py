"""Avis voyageurs par défaut (bilingue FR/EN).

Modifiables depuis l'admin (stockés dans settings → clé « reviews »).
Chaque avis : id, author, location, rating (1-5), date (ISO), text {fr, en}.
"""

DEFAULT_REVIEWS = [
    {
        "id": "r-claire-hanoi",
        "author": "Claire & Thomas",
        "location": "Lyon, France",
        "rating": 5,
        "date": "2026-03-12",
        "text": {
            "fr": "On a suivi l'itinéraire 10 jours presque à la lettre. Les "
                  "conseils sur Halong et la street food de Hanoï étaient parfaits. "
                  "Un gain de temps énorme pour préparer.",
            "en": "We followed the 10-day itinerary almost to the letter. The tips "
                  "on Halong and Hanoi street food were spot on. A huge time-saver "
                  "for planning.",
        },
    },
    {
        "id": "r-marie-budget",
        "author": "Marie L.",
        "location": "Bruxelles, Belgique",
        "rating": 5,
        "date": "2026-02-02",
        "text": {
            "fr": "Le calculateur de budget m'a évité les mauvaises surprises. "
                  "Mon estimation était à 50 € près du coût réel sur 2 semaines !",
            "en": "The budget calculator saved me from nasty surprises. My estimate "
                  "was within €50 of the real cost over 2 weeks!",
        },
    },
    {
        "id": "r-david-visa",
        "author": "David M.",
        "location": "Genève, Suisse",
        "rating": 4,
        "date": "2026-01-20",
        "text": {
            "fr": "Page visa très claire — j'ai compris en 2 minutes que l'e-visa "
                  "était nécessaire pour mon séjour de 5 semaines. Démarche faite "
                  "dans la foulée.",
            "en": "Very clear visa page — I understood in 2 minutes that the e-visa "
                  "was required for my 5-week stay. Applied right away.",
        },
    },
    {
        "id": "r-sophie-centre",
        "author": "Sophie & Karim",
        "location": "Nantes, France",
        "rating": 5,
        "date": "2025-12-08",
        "text": {
            "fr": "Grâce à la page « quand partir », on a décalé notre voyage de "
                  "trois semaines pour éviter la mousson au centre. Hội An sous le "
                  "soleil, magique.",
            "en": "Thanks to the “when to go” page, we shifted our trip by three "
                  "weeks to avoid the central monsoon. Hoi An in the sun — magical.",
        },
    },
]
