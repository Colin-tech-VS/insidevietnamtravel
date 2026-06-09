"""Contenu bilingue — guides pratiques (sécurité, coutumes, phrases)."""

from __future__ import annotations

from typing import Any, Callable


def _pick(value: dict | str, lang: str) -> str:
    if isinstance(value, str):
        return value
    return value.get(lang, value.get("fr", ""))


def _item(
    icon: str,
    title_fr: str,
    title_en: str,
    body_fr: str,
    body_en: str,
    *,
    tips: list[tuple[str, str]] | None = None,
) -> dict:
    item: dict[str, Any] = {
        "icon": icon,
        "title": {"fr": title_fr, "en": title_en},
        "body": {"fr": body_fr, "en": body_en},
    }
    if tips:
        item["tips"] = [{"fr": a, "en": b} for a, b in tips]
    return item


def _section(
    key: str,
    title_fr: str,
    title_en: str,
    intro_fr: str,
    intro_en: str,
    items: list[dict],
    *,
    affiliate: str | None = None,
) -> dict:
    return {
        "key": key,
        "title": {"fr": title_fr, "en": title_en},
        "intro": {"fr": intro_fr, "en": intro_en},
        "items": items,
        "affiliate": affiliate,
    }


def _faq(items: list[tuple[str, str, str, str]]) -> list[dict]:
    return [{"q": {"fr": qf, "en": qe}, "a": {"fr": af, "en": ae}} for qf, qe, af, ae in items]


def localize_sections(sections: list[dict], lang: str) -> list[dict]:
    out = []
    for sec in sections:
        items = []
        for it in sec["items"]:
            row = {
                "icon": it.get("icon", ""),
                "title": _pick(it["title"], lang),
                "body": _pick(it["body"], lang),
            }
            if it.get("tips"):
                row["tips"] = [_pick(t, lang) for t in it["tips"]]
            items.append(row)
        out.append({
            "key": sec["key"],
            "title": _pick(sec["title"], lang),
            "intro": _pick(sec["intro"], lang),
            "items": items,
            "affiliate": sec.get("affiliate"),
        })
    return out


def localize_faq(faq: list[dict], lang: str) -> list[dict]:
    return [{"question": _pick(f["q"], lang), "answer": _pick(f["a"], lang)} for f in faq]


# ── Sécurité & conseils pratiques ─────────────────────────────────────

SAFETY_SECTIONS: list[dict] = [
    _section(
        "overview",
        "Le Vietnam est-il sûr pour les touristes ?",
        "Is Vietnam safe for tourists?",
        "Dans l'ensemble, oui : le Vietnam accueille des millions de visiteurs chaque année "
        "et la criminalité violente contre les touristes reste rare. Les risques les plus "
        "fréquents sont les arnaques « douces », le trafic routier chaotique et les "
        "petits vols à la tire dans les zones très fréquentées.",
        "Overall, yes: Vietnam welcomes millions of visitors each year and violent crime "
        "against tourists is rare. The most common risks are soft scams, chaotic traffic "
        "and pickpocketing in busy areas.",
        [
            _item(
                "✅", "Restez vigilant, pas paranoïaque",
                "Stay alert, not paranoid",
                "Adoptez les réflexes d'une grande ville asiatique : sac devant vous, "
                "pas de téléphone au bout du bras sur le trottoir, négociez les prix "
                "avant de monter dans un taxi sans compteur.",
                "Use big-city habits: bag in front, phone not dangling on the pavement, "
                "agree prices before getting into a taxi without a meter.",
            ),
            _item(
                "📱", "Préparez votre téléphone",
                "Prepare your phone",
                "Téléchargez Grab, Google Maps (cartes hors-ligne) et une app de conversion "
                "AVANT le départ. Une eSIM active dès l'atterrissage change tout en cas "
                "d'imprévu.",
                "Download Grab, Google Maps (offline maps) and a currency converter BEFORE "
                "you leave. An eSIM active on landing makes a huge difference if something "
                "goes wrong.",
            ),
        ],
    ),
    _section(
        "scams",
        "Arnaques courantes (et comment les éviter)",
        "Common scams (and how to avoid them)",
        "La plupart des arnaques visent le portefeuille, pas la sécurité physique. "
        "Connaître les classiques vous fait gagner du temps et de l'argent.",
        "Most scams target your wallet, not physical safety. Knowing the classics saves "
        "time and money.",
        [
            _item(
                "🚕", "Taxi & cyclo sans compteur",
                "Taxi & cyclo without a meter",
                "Refusez les courses « au feeling ». Utilisez Grab ou Xanh SM avec prix "
                "affiché, ou exigez le compteur (« bật đồng hồ »).",
                "Refuse open-ended fares. Use Grab or Xanh SM with a shown price, or insist "
                "on the meter (« bật đồng hồ »).",
                tips=[
                    ("Comparez Grab et Be avant de valider.", "Compare Grab and Be before confirming."),
                    ("Méfiez-vous du « compteur cassé » à l'aéroport.", "Watch for the « broken meter » at the airport."),
                ],
            ),
            _item(
                "💱", "Change d'argent & faux billets",
                "Money exchange & fake notes",
                "Changez dans une banque ou un bureau reconnu ; comptez les liasses devant "
                "vous. Méfiez-vous des taux « trop beaux » dans la rue.",
                "Exchange at a bank or reputable desk; count notes in front of you. Beware "
                "street rates that look too good.",
            ),
            _item(
                "🎫", "Tours, billets & « amis » insistantes",
                "Tours, tickets & pushy « friends »",
                "Réservez trains, croisières Halong et excursions via des plateformes "
                "connues ou notre site. Méfiez-vous des agences improvisées près des gares.",
                "Book trains, Halong cruises and tours via known platforms or our site. "
                "Beware pop-up agencies near stations.",
            ),
            _item(
                "👜", "Vol à la tire & scooter-snatch",
                "Pickpockets & bag-snatching",
                "Traversées piétonnes bondées, marchés nocturnes, Old Quarter : sac fermé, "
                "bijoux discrets. Ne résistez jamais si on arrache un sac en scooter.",
                "Busy crossings, night markets, Old Quarter: closed bag, low-key jewellery. "
                "Never fight back if a bag is snatched from a scooter.",
            ),
        ],
    ),
    _section(
        "health",
        "Santé, vaccins & pharmacie",
        "Health, vaccines & pharmacy",
        "Aucun vaccin n'est obligatoire pour entrer au Vietnam, mais certains sont "
        "recommandés selon votre profil. Consultez votre médecin 4 à 8 semaines avant "
        "le départ.",
        "No vaccine is mandatory to enter Vietnam, but some are recommended depending on "
        "your profile. See your doctor 4–8 weeks before departure.",
        [
            _item(
                "💉", "Vaccins souvent conseillés",
                "Commonly advised vaccines",
                "Hépatite A, typhoïde ; hépatite B et rage si séjour long ou zones "
                "rurales. Rappel diphtérie-tétanos-poliomyélite à jour.",
                "Hepatitis A, typhoid; hepatitis B and rabies for long stays or rural "
                "areas. Keep diphtheria-tetanus-polio boosters up to date.",
            ),
            _item(
                "💊", "Trousse de base",
                "Basic kit",
                "Antidiarrhéique, antiseptique, pansements, répulsif moustiques, "
                "crème solaire, médicaments personnels en quantité suffisante.",
                "Anti-diarrhoea, antiseptic, plasters, mosquito repellent, sunscreen, "
                "enough personal medication.",
            ),
            _item(
                "🦟", "Dengue & chaleur",
                "Dengue & heat",
                "Pas de vaccin universel contre la dengue : répulsif le jour, vêtements "
                "couvrants au crépuscule, hydratation constante.",
                "No universal dengue vaccine: daytime repellent, cover at dusk, stay "
                "hydrated.",
            ),
        ],
    ),
    _section(
        "insurance",
        "Assurance voyage : indispensable",
        "Travel insurance: essential",
        "Les soins privés à Hanoï ou Saigon sont de bon niveau mais chers sans couverture. "
        "Une assurance avec rapatriement et responsabilité civile est fortement recommandée.",
        "Private care in Hanoi or Saigon is good but expensive without cover. Insurance "
        "with repatriation and liability is strongly recommended.",
        [
            _item(
                "🛡️", "Ce qu'il faut vérifier",
                "What to check",
                "Frais médicaux à l'étranger, rapatriement, sports/adventures si trek "
                "à Sapa, annulation vol/hôtel selon votre formule.",
                "Overseas medical costs, repatriation, adventure sports if trekking in "
                "Sapa, trip cancellation if needed.",
            ),
        ],
        affiliate="insurance",
    ),
    _section(
        "connectivity",
        "eSIM & carte SIM",
        "eSIM & local SIM",
        "Avoir du réseau dès l'atterrissage permet d'appeler un Grab, de montrer une "
        "adresse en vietnamien ou de contacter votre assurance.",
        "Having data on landing lets you call Grab, show an address in Vietnamese or "
        "contact your insurer.",
        [
            _item(
                "📶", "eSIM avant le départ",
                "eSIM before you fly",
                "Airalo et Holafly proposent des forfaits Vietnam activables en quelques "
                "minutes — idéal pour éviter les boutiques d'aéroport douteuses.",
                "Airalo and Holafly offer Vietnam plans activated in minutes — ideal to "
                "skip questionable airport shops.",
            ),
        ],
        affiliate="sim",
    ),
    _section(
        "traffic",
        "Route & déplacements",
        "Roads & getting around",
        "Le trafic moto est dense : traversez lentement, sans téléphone, en regardant "
        "dans les deux sens. Port du casque obligatoire si vous louez un scooter.",
        "Motorbike traffic is dense: cross slowly, phone away, look both ways. Helmet "
        "mandatory if you rent a scooter.",
        [
            _item(
                "🛵", "Scooter & permis",
                "Scooter & licence",
                "Un permis international moto est requis en théorie ; en pratique de "
                "nombreux voyageurs louent sans — sachez que l'assurance peut refuser "
                "de couvrir un accident sans permis valide.",
                "An international motorcycle licence is technically required; many "
                "travellers rent without one — know that insurance may refuse a claim "
                "without a valid licence.",
            ),
        ],
    ),
    _section(
        "emergency",
        "En cas de problème : numéros & démarches",
        "If something goes wrong: numbers & steps",
        "Gardez une copie numérique de votre passeport et de votre assurance. "
        "Contactez d'abord votre assureur pour l'orientation médicale.",
        "Keep digital copies of your passport and insurance. Contact your insurer "
        "first for medical guidance.",
        [
            _item(
                "🆘", "Numéros d'urgence (Vietnam)",
                "Emergency numbers (Vietnam)",
                "Police : 113 · Ambulance : 115 · Pompiers : 114. "
                "Ligne touristique nationale : 1800 1129 (info, pas toujours anglais).",
                "Police: 113 · Ambulance: 115 · Fire: 114. "
                "National tourism hotline: 1800 1129 (info, English not always available).",
            ),
            _item(
                "🏛️", "Consulats & ambassades",
                "Consulates & embassies",
                "En cas de vol de passeport ou d'accident grave, contactez votre "
                "ambassade/consulat (Paris → Ambassade de France à Hanoï / Consulat à "
                "Hô Chi Minh-Ville). Listes officielles sur diplomatie.gouv.fr ou gov.uk.",
                "For passport theft or serious accident, contact your embassy/consulate. "
                "Official lists on your government's foreign travel site.",
            ),
            _item(
                "🏥", "Hôpitaux privés fréquentés",
                "Hospitals travellers use",
                "Vinmec, FV Hospital (Saigon), Family Medical Practice — anglais courant, "
                "facturation élevée sans assurance.",
                "Vinmec, FV Hospital (Saigon), Family Medical Practice — English spoken, "
                "high bills without insurance.",
            ),
        ],
    ),
]

SAFETY_FAQ = _faq([
    (
        "Le Vietnam est-il sûr pour une femme seule ?",
        "Is Vietnam safe for solo female travellers?",
        "Oui, avec les précautions habituelles (quartiers centraux la nuit, Grab de nuit, "
        "alcool modéré). Le harcèlement reste rare comparé à d'autres destinations.",
        "Yes, with usual precautions (central areas at night, Grab after dark, moderate "
        "drinking). Harassment is relatively uncommon compared with other destinations.",
    ),
    (
        "Peut-on boire l'eau du robinet ?",
        "Can you drink tap water?",
        "Non — eau en bouteille ou filtrée uniquement. Glace dans les grandes villes "
        "généralement OK, prudence en campagne.",
        "No — bottled or filtered water only. Ice in major cities is usually fine; "
        "caution in rural areas.",
    ),
    (
        "Faut-il une assurance voyage pour le Vietnam ?",
        "Do you need travel insurance for Vietnam?",
        "Fortement recommandée : soins privés chers, rapatriement coûteux, sports "
        "à risque (trek, scooter).",
        "Strongly recommended: private care is costly, repatriation expensive, risky "
        "activities (trek, scooter).",
    ),
])


def build_safety_guide(lang: str) -> dict:
    return {
        "sections": localize_sections(SAFETY_SECTIONS, lang),
        "faq": localize_faq(SAFETY_FAQ, lang),
    }


# ── Coutumes & étiquette ──────────────────────────────────────────────

CUSTOMS_SECTIONS: list[dict] = [
    _section(
        "greetings",
        "Salutations & premier contact",
        "Greetings & first contact",
        "Les Vietnamiens sont accueillants ; quelques gestes simples ouvrent les portes "
        "et éviteront les malentendus.",
        "Vietnamese people are welcoming; a few simple gestures go a long way.",
        [
            _item(
                "🙏", "Bonjour & sourire",
                "Hello & a smile",
                "« Xin chào » (sin tchao) suffit. Poignée de main légère avec les hommes ; "
                "attendez qu'une femme tende la main en premier.",
                "« Xin chào » (sin chow) is enough. Light handshake with men; wait for "
                "a woman to offer her hand first.",
            ),
            _item(
                "🎂", "L'âge et le respect",
                "Age & respect",
                "On s'adresse aux aînés avec déférence ; laissez-les passer, servez-vous "
                "après eux à table si possible.",
                "Elders are shown deference; let them go first, serve yourself after "
                "them at meals when you can.",
            ),
        ],
    ),
    _section(
        "temples",
        "Temples, pagodes & sites sacrés",
        "Temples, pagodas & sacred sites",
        "Le Vietnam mélange bouddhisme, culte des ancêtres et temples communautaires. "
        "Tenue correcte et calme sont attendues.",
        "Vietnam blends Buddhism, ancestor worship and community temples. Modest dress "
        "and quiet behaviour are expected.",
        [
            _item(
                "👘", "Tenue",
                "Dress code",
                "Épaules et genoux couverts ; retirez chaussures et chapeau à l'entrée. "
                "Un foulard dans le sac est utile.",
                "Cover shoulders and knees; remove shoes and hats at the entrance. "
                "A scarf in your bag helps.",
            ),
            _item(
                "📸", "Photos",
                "Photos",
                "Demandez avant de photographier des fidèles ou des autels ; flash "
                "souvent interdit.",
                "Ask before photographing worshippers or altars; flash often forbidden.",
            ),
        ],
    ),
    _section(
        "dining",
        "À table & gastronomie",
        "At the table & food culture",
        "Partager des plats est la norme ; les baguettes ou cuillères circulent au centre.",
        "Sharing dishes is the norm; chopsticks or spoons go around the centre.",
        [
            _item(
                "🥢", "Baguettes",
                "Chopsticks",
                "Ne plantez pas les baguettes verticalement dans le riz (geste funéraire). "
                "Ne pointez pas quelqu'un avec.",
                "Don't stick chopsticks upright in rice (funeral gesture). Don't point "
                "at people with them.",
            ),
            _item(
                "🍻", "Toasts & alcool",
                "Toasts & alcohol",
                "« Một, hai, ba, dô! » (Mot, hai, ba, zo!) pour trinquer. Boire avec "
                "modération montre du respect.",
                "« Một, hai, ba, dô! » (Mot, hai, ba, zo!) to toast. Moderation shows respect.",
            ),
            _item(
                "💰", "L'addition",
                "The bill",
                "L'hôte paie souvent ; proposer de contribuer est apprécié. Pourboire "
                "5–10 % dans les restos touristiques si service soigné.",
                "The host often pays; offering to contribute is appreciated. Tip 5–10% "
                "in tourist restaurants for good service.",
            ),
        ],
    ),
    _section(
        "social",
        "Gestes du quotidien",
        "Everyday gestures",
        "Quelques tabous locaux à connaître pour voyager sereinement.",
        "A few local taboos worth knowing for smooth travel.",
        [
            _item(
                "👆", "Tête & mains",
                "Head & hands",
                "Ne touchez pas la tête d'une personne (surtout d'un enfant). Ne montrez "
                "pas la plante des pieds vers un autel ou une personne.",
                "Don't touch someone's head (especially a child). Don't point the soles "
                "of your feet at an altar or a person.",
            ),
            _item(
                "💬", "Sujets sensibles",
                "Sensitive topics",
                "Évitez les débats politiques ouvertement virulents avec des inconnus ; "
                "l'histoire récente reste personnelle pour beaucoup.",
                "Avoid heated political debates with strangers; recent history is personal "
                "for many.",
            ),
            _item(
                "🎁", "Cadeaux",
                "Gifts",
                "Offrir un petit cadeau de votre pays est bien vu ; évitez l'emballage "
                "blanc seul (couleur funéraire).",
                "A small gift from your country is appreciated; avoid plain white wrapping "
                "(funeral colour).",
            ),
        ],
    ),
    _section(
        "bargaining",
        "Marchés & négociation",
        "Markets & bargaining",
        "Le marchandage est courant sur les marchés et pour les cyclos ; fixez un prix "
        "avant, avec le sourire.",
        "Bargaining is normal in markets and for cyclos; agree a price first, with a smile.",
        [
            _item(
                "🛍️", "Comment négocier",
                "How to bargain",
                "Proposez 60–70 % du premier prix, montez progressivement. Un « non » "
                "poli avec sourire vaut mieux qu'un conflit.",
                "Offer 60–70% of the first price, move up gradually. A polite « no » "
                "with a smile beats conflict.",
            ),
        ],
    ),
]

CUSTOMS_FAQ = _faq([
    (
        "Faut-il parler vietnamien pour voyager ?",
        "Do you need to speak Vietnamese to travel?",
        "Non, mais quelques mots (xin chào, cảm ơn, bao nhiêu) facilitent les échanges "
        "et les prix. Voir notre guide de phrases.",
        "No, but a few words (xin chào, cảm ơn, bao nhiêu) help interactions and "
        "prices. See our phrase guide.",
    ),
    (
        "Quelle tenue à Hội An ou dans un temple ?",
        "What to wear in Hội An or a temple?",
        "Épaules et genoux couverts ; tissus légers et respirants. Évitez maillots "
        "de bain en ville.",
        "Cover shoulders and knees; light breathable fabrics. Avoid swimwear in town.",
    ),
])


def build_customs_guide(lang: str) -> dict:
    return {
        "sections": localize_sections(CUSTOMS_SECTIONS, lang),
        "faq": localize_faq(CUSTOMS_FAQ, lang),
    }


# ── Phrases utiles ────────────────────────────────────────────────────

PHRASE_CATEGORIES: list[dict] = [
    {
        "key": "basics",
        "title": {"fr": "Essentiels", "en": "Basics"},
        "intro": {
            "fr": "Politesse et salutations — toujours utiles.",
            "en": "Politeness and greetings — always useful.",
        },
        "phrases": [
            ("Bonjour / Salut", "Hello / Hi", "Xin chào", "sin tchao", "sin chow"),
            ("Merci", "Thank you", "Cảm ơn", "gam un", "gam un"),
            ("Merci beaucoup", "Thank you very much", "Cảm ơn nhiều", "gam un nyeu", "gam un nyew"),
            ("S'il vous plaît", "Please", "Làm ơn", "lam un", "lam un"),
            ("Excusez-moi / Pardon", "Excuse me / Sorry", "Xin lỗi", "sin loi", "sin loy"),
            ("Oui / Non", "Yes / No", "Vâng / Không", "vung / khom", "vung / khom"),
            ("Je ne comprends pas", "I don't understand", "Tôi không hiểu", "toy khom hiu", "toy khom hyoo"),
            ("Parlez-vous anglais / français ?", "Do you speak English / French?", "Bạn có nói tiếng Anh / Pháp không?", "ban co noi tieng anh / fap khom?", "ban co noi tyeng anh / fap khom?"),
        ],
    },
    {
        "key": "transport",
        "title": {"fr": "Transport & directions", "en": "Transport & directions"},
        "intro": {
            "fr": "Pour Grab, taxi ou demander votre chemin.",
            "en": "For Grab, taxis or asking directions.",
        },
        "phrases": [
            ("Où est… ?", "Where is…?", "… ở đâu?", "… o dau?", "… oh dow?"),
            ("Combien coûte la course ?", "How much is the ride?", "Bao nhiêu tiền?", "bao nyeu tien?", "bow nyew tyen?"),
            ("Arrêtez-vous ici", "Stop here", "Dừng lại đây", "zung lai day", "zoong lai day"),
            ("Trop cher", "Too expensive", "Đắt quá", "dat qua", "dat kwah"),
            ("Lentement / Doucement", "Slowly", "Chậm thôi", "cham thoy", "cham toy"),
        ],
    },
    {
        "key": "food",
        "title": {"fr": "Restaurant & street food", "en": "Restaurant & street food"},
        "intro": {
            "fr": "Commander, allergies et régimes.",
            "en": "Ordering, allergies and diets.",
        },
        "phrases": [
            ("L'addition, s'il vous plaît", "The bill, please", "Tính tiền", "tin tien", "tin tyen"),
            ("C'est délicieux", "It's delicious", "Ngon quá", "ngon qua", "ngon kwah"),
            ("Pas épicé / peu épicé", "Not spicy / mildly spicy", "Không cay / ít cay", "khom cay / it cay", "khom cay / it cay"),
            ("Je suis végétarien(ne)", "I'm vegetarian", "Tôi ăn chay", "toy an chay", "toy an chay"),
            ("Une bière / une eau", "A beer / water", "Một bia / nước", "mot bia / nuoc", "mot bia / nuok"),
        ],
    },
    {
        "key": "shopping",
        "title": {"fr": "Shopping & marchés", "en": "Shopping & markets"},
        "intro": {
            "fr": "Négocier avec le sourire.",
            "en": "Bargain with a smile.",
        },
        "phrases": [
            ("C'est combien ?", "How much is it?", "Bao nhiêu?", "bao nyeu?", "bow nyew?"),
            ("C'est trop cher", "It's too expensive", "Mắc quá", "mak qua", "mak kwah"),
            ("Un peu moins cher ?", "A bit cheaper?", "Bớt chút được không?", "bot chut duoc khom?", "bot chut dwok khom?"),
            ("Je regarde seulement", "Just looking", "Chỉ xem thôi", "chi sem thoy", "chi sem toy"),
        ],
    },
    {
        "key": "emergency",
        "title": {"fr": "Urgences & santé", "en": "Emergencies & health"},
        "intro": {
            "fr": "À garder dans votre téléphone.",
            "en": "Save these on your phone.",
        },
        "phrases": [
            ("Appelez la police / une ambulance", "Call the police / ambulance", "Gọi cảnh sát / xe cấp cứu", "goy can sat / se cap cuu", "goy can sat / se cap koo"),
            ("J'ai besoin d'un médecin", "I need a doctor", "Tôi cần bác sĩ", "toy can bak si", "toy can bak see"),
            ("Où est l'hôpital ?", "Where is the hospital?", "Bệnh viện ở đâu?", "benh vien o dau?", "ben vyen oh dow?"),
            ("J'ai perdu mon passeport", "I lost my passport", "Tôi mất hộ chiếu", "toy mat ho chieu", "toy mat ho chyoo"),
        ],
    },
    {
        "key": "numbers",
        "title": {"fr": "Chiffres utiles", "en": "Useful numbers"},
        "intro": {
            "fr": "Pour marchés et taxis.",
            "en": "For markets and taxis.",
        },
        "phrases": [
            ("1 – 5 – 10", "1 – 5 – 10", "Một – Năm – Mười", "mot – nam – muoi", "mot – nam – moo-ee"),
            ("100 – 1 000 – 10 000", "100 – 1,000 – 10,000", "Một trăm – nghìn – mười nghìn", "mot tram – ngin – muoi ngin", "mot tram – ngin – moo-ee ngin"),
        ],
    },
]


def build_phrases_guide(lang: str) -> dict:
    cats = []
    for cat in PHRASE_CATEGORIES:
        rows = []
        for fr_src, en_src, vi, pron_fr, pron_en in cat["phrases"]:
            rows.append({
                "source": fr_src if lang == "fr" else en_src,
                "vi": vi,
                "pron": pron_fr if lang == "fr" else pron_en,
            })
        cats.append({
            "key": cat["key"],
            "title": _pick(cat["title"], lang),
            "intro": _pick(cat["intro"], lang),
            "phrases": rows,
        })
    return {"categories": cats}


def _section_text(sec: dict) -> str:
    parts = [sec.get("intro", "")]
    for item in sec.get("items", []):
        parts.append(f"{item.get('title', '')}: {item.get('body', '')}")
        parts.extend(item.get("tips") or [])
    return " ".join(p for p in parts if p)


def build_mai_knowledge_chunks(lang: str, page_url_fn: Callable[[str, str], str]) -> list[dict]:
    """Index enrichi pour Mai — contenu des guides pratiques, visa, météo, phrases."""
    from locales.ui import t

    lang = "en" if lang == "en" else "fr"
    chunks: list[dict] = []

    def add(chunk: dict) -> None:
        chunks.append(chunk)

    def page(endpoint: str, title: str, text: str, *, group: str = "Guides pratiques") -> None:
        add({
            "id": f"guide-page:{endpoint}",
            "title": title,
            "url": page_url_fn(endpoint, lang),
            "group": group,
            "text": text[:900],
        })

    # ── Sécurité ──
    safety = build_safety_guide(lang)
    page("safety_guide", t("safety.title", lang), t("safety.lead", lang))
    for sec in safety["sections"]:
        add({
            "id": f"guide-safety:{sec['key']}",
            "title": f"{t('safety.nav', lang)} — {sec['title']}",
            "url": page_url_fn("safety_guide", lang) + f"#{sec['key']}",
            "group": "Sécurité Vietnam",
            "text": _section_text(sec)[:900],
        })
    for i, faq in enumerate(safety.get("faq") or []):
        add({
            "id": f"guide-safety-faq:{i}",
            "title": faq["question"],
            "url": page_url_fn("safety_guide", lang),
            "group": "Sécurité Vietnam",
            "text": faq["answer"][:500],
        })

    # ── Coutumes ──
    customs = build_customs_guide(lang)
    page("customs_guide", t("customs.title", lang), t("customs.lead", lang))
    for sec in customs["sections"]:
        add({
            "id": f"guide-customs:{sec['key']}",
            "title": f"{t('customs.nav', lang)} — {sec['title']}",
            "url": page_url_fn("customs_guide", lang) + f"#{sec['key']}",
            "group": "Coutumes Vietnam",
            "text": _section_text(sec)[:900],
        })

    # ── Phrases vietnamiennes ──
    phrases = build_phrases_guide(lang)
    phrase_samples = []
    for cat in phrases["categories"]:
        for p in cat["phrases"][:4]:
            phrase_samples.append(f"{p['source']} → {p['vi']} ({p['pron']})")
    page(
        "phrases_guide",
        t("phrases.title", lang),
        t("phrases.lead", lang) + " " + " | ".join(phrase_samples[:12]),
    )
    for cat in phrases["categories"]:
        sample = " ; ".join(
            f"{p['source']} = {p['vi']}" for p in cat["phrases"][:8]
        )
        add({
            "id": f"guide-phrases:{cat['key']}",
            "title": f"{t('phrases.nav', lang)} — {cat['title']}",
            "url": page_url_fn("phrases_guide", lang) + f"#{cat['key']}",
            "group": "Phrases vietnamiennes",
            "text": f"{cat['intro']} {sample}"[:900],
        })

    # ── Visa (contenu outil) ──
    try:
        from data.travel_tools import build_visa
        visa = build_visa(lang)
        page("visa_tool", t("visa.title", lang), t("visa.lead", lang), group="Formalités")
        for sec in visa.get("sections") or []:
            add({
                "id": f"guide-visa:{sec['key']}",
                "title": f"{t('tools.visa', lang)} — {sec['title']}",
                "url": page_url_fn("visa_tool", lang) + f"#{sec['key']}",
                "group": "Visa Vietnam",
                "text": _section_text(sec)[:900],
            })
        for i, faq in enumerate(visa.get("faq") or []):
            add({
                "id": f"guide-visa-faq:{i}",
                "title": faq["question"],
                "url": page_url_fn("visa_tool", lang),
                "group": "Visa Vietnam",
                "text": faq["answer"][:500],
            })
    except Exception:
        pass

    # ── Météo / quand partir ──
    try:
        from data.travel_tools import build_seasons
        seasons = build_seasons(lang)
        region_text = " ".join(
            f"{r['name']}: {r['best']}. {r['summary']}" for r in seasons["regions"]
        )
        page(
            "best_season",
            t("season.title", lang),
            t("season.lead", lang) + " " + region_text[:500],
            group="Météo Vietnam",
        )
        for dest in seasons.get("destinations") or []:
            months_txt = ", ".join(
                f"{seasons['month_labels'][i]}={dest['months'][i]}"
                for i in range(12)
            )
            add({
                "id": f"guide-season:{dest['slug']}",
                "title": f"{t('season.planner_dest', lang)} {dest['name']}",
                "url": page_url_fn("best_season", lang) + "#season-planner",
                "group": "Météo Vietnam",
                "text": (
                    f"{dest['name']} ({dest['region_name']}): {dest['best']}. "
                    f"{dest.get('hint', '')} Mois: {months_txt}"
                )[:900],
            })
        add({
            "id": "guide-season-planner",
            "title": t("season.planner_title", lang),
            "url": page_url_fn("best_season", lang) + "#season-planner",
            "group": "Météo Vietnam",
            "text": (
                f"{t('season.planner_sub', lang)} "
                f"{t('season.planner_ideal', lang)} / {t('season.planner_good', lang)} / "
                f"{t('season.planner_fair', lang)} / {t('season.planner_avoid', lang)}"
            )[:900],
        })
    except Exception:
        pass

    # ── Apps utiles ──
    page(
        "useful_apps",
        t("apps.title", lang),
        t("apps.lead", lang),
        group="Guides pratiques",
    )

    return chunks
