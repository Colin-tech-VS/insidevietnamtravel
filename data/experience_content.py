"""Contenu SEO enrichi pour les 7 guides expérience (pilier que-faire)."""

from __future__ import annotations

from urllib.parse import quote

from data.affiliate_urls import (
    agoda_city,
    booking_city,
    esim_airalo,
    get_location_meta,
    getyourguide_activity,
    travel_insurance,
    viator_activity,
)


def _go(provider: str, url: str) -> str:
    return f"/go/{provider}?to={quote(url, safe='')}"


def _aff(loc_slug: str, query: str, *, hotel: bool = False) -> dict[str, str]:
    meta = get_location_meta(loc_slug)
    return {
        "gyg": _go("getyourguide", getyourguide_activity(query, meta)),
        "viator": _go("viator", viator_activity(query, meta)),
        "booking": _go("booking", booking_city(meta)),
        "agoda": _go("agoda", agoda_city(meta)),
    }


def _aff_box(title: str, items: list[tuple[str, str]]) -> str:
    lis = "".join(
        f'<li><a href="{href}" rel="sponsored noopener noreferrer" target="_blank">{label}</a></li>'
        for label, href in items
    )
    return f"<blockquote><p><strong>{title}</strong></p><ul>{lis}</ul></blockquote>"


def _common_footer(*, dest_href: str, dest_label: str, loc_slug: str) -> str:
    aff = _aff(loc_slug, "Vietnam")
    return (
        f"<h2>Aller plus loin</h2>"
        f"<p>Consultez notre <a href=\"{dest_href}\">guide complet {dest_label}</a>, "
        f"le pilier <a href=\"/guide/que-faire-au-vietnam\">Que faire au Vietnam</a> "
        f"et nos conseils <a href=\"/guide/preparer-son-voyage\">Préparer son voyage</a> "
        f"(visa, budget, eSIM).</p>"
        + _aff_box(
            "Préparer le voyage",
            [
                ("Assurance voyage Vietnam (Heymondo)", _go("travel_insurance", travel_insurance())),
                ("eSIM Vietnam — internet dès l'atterrissage (Airalo)", _go("esim_airalo", esim_airalo())),
                (f"Hôtels à {dest_label} (Booking)", aff["booking"]),
                (f"Hôtels à {dest_label} (Agoda)", aff["agoda"]),
            ],
        )
    )


# ── 1. Halong ─────────────────────────────────────────────────────────────

def _halong_content() -> str:
    a = _aff("hanoi", "Halong Bay cruise")
    return (
        "<p>La <strong>baie d'Halong</strong>, classée à l'UNESCO, reste l'expérience la plus "
        "iconique du Vietnam. Des milliers d'îlots karstiques émergent d'une eau émeraude : "
        "kayak, grottes, baignade et nuit à bord transforment un simple paysage en souvenir "
        "marquant. Que vous partiez de <a href=\"/hanoi\">Hanoï</a> pour une journée ou que vous "
        "combiniez Halong avec <a href=\"/sapa\">Sapa</a> dans le Nord, ce guide vous aide à "
        "choisir la bonne formule sans mauvaise surprise.</p>"
        "<h2>Pourquoi faire une croisière à Halong ?</h2>"
        "<p>Halong n'est pas qu'une carte postale : c'est un archipel vivant où pêcheurs et "
        "fermiers de palétuviers cohabitent avec une flotte de jonques. Une <strong>nuit sur "
        "l'eau</strong> permet de sortir des couloirs touristiques du matin, d'admirer le "
        "coucher de soleil entre les rochers et de profiter du kayak avant l'arrivée des "
        "excursions d'une journée. C'est aussi l'une des rares activités au Vietnam où "
        "réserver à l'avance est vraiment recommandé en haute saison.</p>"
        "<h2>1 jour ou 2 jours / 1 nuit ?</h2>"
        "<p><strong>Excursion d'une journée</strong> depuis Hanoï (4 h de route aller-retour) : "
        "correct si vous manquez de temps, mais fatigant et souvent bondé. "
        "<strong>2 jours / 1 nuit</strong> : le meilleur compromis — coucher de soleil, "
        "matinée kayak, baignade. <strong>3 jours / 2 nuits</strong> : pour explorer la "
        "baie de Bai Tu Long ou Lan Ha, plus calmes que le cœur d'Halong.</p>"
        "<ul>"
        "<li><strong>Budget</strong> : jonque collective, cabine partagée, 80–120 €/pers.</li>"
        "<li><strong>Confort</strong> : cabine privée, repas soignés, 130–200 €/pers.</li>"
        "<li><strong>Premium</strong> : yacht, suite, 250 €+ — excellent rapport vs Méditerranée.</li>"
        "</ul>"
        "<h2>Quel type de bateau choisir ?</h2>"
        "<p>Vérifiez toujours : transfert depuis Hanoï, entrée de la baie, activités (kayak, "
        "grotte), repas et pourboires. Les jonques « luxe » à 150 € offrent souvent plus de "
        "confort qu'une croisière méditerranéenne à 400 €. Évitez les vendeurs de rue à Hanoï "
        "et les offres trop belles dans la vieille ville — privilégiez un opérateur avec avis "
        "récentes et politique d'annulation claire.</p>"
        + _aff_box(
            "Réserver une croisière Halong",
            [
                ("Croisières baie d'Halong (GetYourGuide)", a["gyg"]),
                ("Excursions Halong (Viator)", a["viator"]),
                ("Nuit à Hanoï avant le départ (Booking)", a["booking"]),
            ],
        )
        + "<h2>Itinéraire conseillé</h2>"
        "<ol>"
        "<li><strong>Jour 1</strong> : matinée libre à Hanoï, départ vers Halong (~12 h), "
        "embarquement, grottes et kayak, nuit à bord.</li>"
        "<li><strong>Jour 2</strong> : lever tôt, baignade, brunch, retour Hanoï en fin "
        "d'après-midi.</li>"
        "<li><strong>Option</strong> : +1 nuit à <a href=\"/halong\">Halong</a> ou ferry vers "
        "<strong>Cat Ba</strong> pour randonnée au parc national.</li>"
        "</ol>"
        "<h2>Conseils pratiques</h2>"
        "<ul>"
        "<li><strong>Meilleure saison</strong> : octobre à avril (mer plus calme, ciel dégagé).</li>"
        "<li><strong>À éviter</strong> : Tết et week-ends vietnamiens (affluence, tarifs majorés).</li>"
        "<li><strong>À emporter</strong> : crème solaire, chapeau, chaussures antidérapantes, "
        "antinauséeux si sensible.</li>"
        "<li><strong>Éthique</strong> : refusez les dauphins en cage et les attractions animales.</li>"
        "</ul>"
        "<h2>Questions fréquentes</h2>"
        "<h3>Faut-il réserver sa croisière Halong à l'avance ?</h3>"
        "<p>Oui, surtout de novembre à mars et pendant les vacances. Les meilleures jonques "
        "affichent complet plusieurs jours à l'avance ; réserver sur place à Hanoï laisse "
        "peu de choix sur les cabines et les itinéraires.</p>"
        "<h3>La baie d'Halong vaut-elle le détour en 1 jour ?</h3>"
        "<p>Oui pour un premier aperçu, mais la route depuis Hanoï grignote une large part de "
        "la journée. Si votre planning le permet, une nuit à bord change vraiment l'expérience.</p>"
        "<h3>Halong ou Lan Ha / Bai Tu Long ?</h3>"
        "<p>Halong central est le plus spectaculaire mais le plus fréquenté. Lan Ha (près de Cat Ba) "
        "et Bai Tu Long, au nord, offrent des eaux plus calmes avec des paysages très proches.</p>"
        + _common_footer(dest_href="/halong", dest_label="Halong", loc_slug="hanoi")
    )


# ── 2. Sapa ───────────────────────────────────────────────────────────────

def _sapa_content() -> str:
    a = _aff("hanoi", "Sapa trekking tour")
    return (
        "<p><strong>Sapa</strong>, perchée à 1 600 m dans les montagnes du Nord, offre des "
        "rizières en terrasses parmi les plus photogéniques d'Asie. Entre villages Hmong, Dao "
        "et Tay, le trek reste accessible aux marcheurs moyens tout en plongeant dans une "
        "culture montagnarde encore très vivante. Ce guide détaille les sentiers, l'intérêt "
        "d'un guide local, les homestays et la meilleure saison — indispensable avant de "
        "quitter <a href=\"/hanoi\">Hanoï</a>.</p>"
        "<h2>Comprendre le trek à Sapa</h2>"
        "<p>Sapa ville est très touristique, mais dix minutes de marche suffisent pour retrouver "
        "des sentiers entre rizières et forêts de bambous. Les randonnées vont de la demi-journée "
        "facile aux ascensions sportives vers le <strong>Fansipan</strong> (3 143 m, « toit du "
        "Vietnam »). Le climat change vite : prévoyez des couches même en été.</p>"
        "<h2>Les meilleures randonnées</h2>"
        "<ul>"
        "<li><strong>Cat Cat → Y Linh Ho</strong> (½ journée) : villages Hmong, rizières proches, "
        "idéal pour débuter.</li>"
        "<li><strong>Ta Van → Giang Ta Chai</strong> (1 jour) : cascades, ponts de bambou, "
        "rencontres locales.</li>"
        "<li><strong>Muong Hoa Valley</strong> (1–2 jours) : le grand classique des terrasses.</li>"
        "<li><strong>Fansipan</strong> (2 jours à pied ou câble) : panorama sur le Nord vietnamien.</li>"
        "</ul>"
        "<h2>Guide local, agence ou homestay ?</h2>"
        "<p>Un guide Hmong ou Dao connaît les sentiers boueux, évite les pièges à touristes et "
        "facilite les échanges dans les villages. L'<strong>homestay</strong> (Ta Van, Lao Chai) "
        "reste l'expérience la plus immersive : repas partagés, riz local, réveil dans la brume. "
        "Réservez via votre hôtel ou une agence établie — méfiez-vous des vendeuses insistantes "
        "dès la gare de Sapa.</p>"
        + _aff_box(
            "Réserver trek et hébergement",
            [
                ("Trek et tours Sapa (GetYourGuide)", a["gyg"]),
                ("Randonnées Sapa (Viator)", a["viator"]),
                ("Hôtels à Sapa (Booking)", a["booking"]),
            ],
        )
        + "<h2>Comment s'y rendre depuis Hanoï ?</h2>"
        "<p>Train de nuit jusqu'à <strong>Lao Cai</strong> (8–9 h) puis minibus 1 h — atmosphérique "
        "et reposant. Alternative : bus direct 5–6 h depuis Hanoï. Comptez au minimum "
        "<strong>2 nuits à Sapa</strong> après le trajet pour profiter d'une randonnée complète.</p>"
        "<h2>Quand partir à Sapa ?</h2>"
        "<ul>"
        "<li><strong>Septembre–novembre</strong> : rizières dorées, ciel dégagé — haute saison.</li>"
        "<li><strong>Mars–mai</strong> : verdure intense, floraisons.</li>"
        "<li><strong>Juin–août</strong> : pluies, brume, sentiers glissants — paysages mystiques "
        "mais conditions difficiles.</li>"
        "<li><strong>Décembre–février</strong> : froid possible (5–10 °C), peu de touristes.</li>"
        "</ul>"
        "<h2>Questions fréquentes</h2>"
        "<h3>Faut-il un guide obligatoire pour trekker à Sapa ?</h3>"
        "<p>Non légalement pour les sentiers proches, mais fortement recommandé pour les "
        "randonnées d'une journée ou plus : orientation, météo, accueil dans les villages et "
        "prix équitables aux homestays.</p>"
        "<h3>Combien de jours prévoir à Sapa ?</h3>"
        "<p>2 nuits minimum (1 jour de trek), 3 nuits idéal pour combiner vallée de Muong Hoa "
        "et marché du dimanche à Bac Ha si votre calendrier le permet.</p>"
        "<h3>Le trek à Sapa convient-il aux enfants ?</h3>"
        "<p>Oui pour les circuits faciles (Cat Cat, portion de Muong Hoa). Au-delà, les pentes "
        "et l'humidité fatiguent vite — privilégiez une demi-journée et un retour en taxi.</p>"
        + _common_footer(dest_href="/sapa", dest_label="Sapa", loc_slug="hanoi")
    )


# ── 3. Delta du Mékong ────────────────────────────────────────────────────

def _mekong_content() -> str:
    a = _aff("ho-chi-minh-city", "Mekong Delta tour")
    return (
        "<p>Le <strong>delta du Mékong</strong>, au sud de <a href=\"/ho-chi-minh-city\">Hô-Chi-Minh-Ville</a>, "
        "est un labyrinthe de canaux, de vergers de noix de coco et de <strong>marchés flottants</strong>. "
        "Là où les mégalopoles accélèrent, la vie s'organise encore autour de l'eau : sampans, "
        "maisons sur pilotis, plantations de fruits. Ce guide compare excursion d'une journée "
        "et séjour de 2 jours pour vivre le delta sans se contenter d'un circuit trop formaté.</p>"
        "<h2>Comprendre le delta</h2>"
        "<p>Le Mékong se divise en innombrables bras avant de rejoindre la mer. Les provinces "
        "de <strong>Ben Tre</strong>, <strong>Mỹ Tho</strong>, <strong>Cần Thơ</strong> et "
        "<strong>Vĩnh Long</strong> offrent chacune une facette différente : artisanat du coco, "
        "vergers, marchés à l'aube. Plus vous dormez sur place, plus l'expérience s'éloigne "
        "du « tour bus » classique.</p>"
        "<h2>Excursion 1 jour depuis Saigon</h2>"
        "<p>Les circuits populaires partent vers Mỹ Tho ou Ben Tre : croisière en sampan, "
        "dégustation de fruits, atelier de bonbons à la noix de coco, balade à vélo sur île. "
        "Comptez <strong>25–45 €</strong> avec transfert et déjeuner. Idéal pour un premier "
        "aperçu si vous n'avez qu'une journée libre dans le Sud.</p>"
        "<h2>2 jours : le vrai delta</h2>"
        "<p>Passez une nuit à <strong>Cần Thơ</strong> pour le <strong>marché flottant de Cai Rang</strong> "
        "à l'aube (5 h–8 h) : c'est le moment le plus authentique. Ajoutez une balade en petit "
        "canal et, si possible, un <strong>homestay</strong> à Ben Tre pour la nuit au rythme "
        "local. Le delta mérite au moins cette nuit pour justifier le trajet depuis Saigon.</p>"
        + _aff_box(
            "Réserver une excursion dans le delta",
            [
                ("Tours delta du Mékong (GetYourGuide)", a["gyg"]),
                ("Excursions Mékong (Viator)", a["viator"]),
                ("Hôtels à Ho Chi Minh-Ville (Booking)", a["booking"]),
            ],
        )
        + "<h2>Que voir et quoi goûter</h2>"
        "<ul>"
        "<li><strong>Marchés flottants</strong> : Cai Rang (le plus grand), Cai Be (plus proche de Saigon).</li>"
        "<li><strong>Îles</strong> : Phoenix, Tortoise, Unicorn près de Mỹ Tho.</li>"
        "<li><strong>Spécialités</strong> : bonbons coco, huîtres grillées, canard fermenté, fruits exotiques.</li>"
        "<li><strong>Artisanat</strong> : nattes, poteries, confiserie de riz soufflé.</li>"
        "</ul>"
        "<h2>Conseils pratiques</h2>"
        "<ul>"
        "<li>Partez <strong>très tôt</strong> pour les marchés — l'activité retombe vers 9 h.</li>"
        "<li>Prévoyez chapeau, anti-moustiques, espèces pour achats sur l'eau.</li>"
        "<li>Combinez avec 2–3 jours à <a href=\"/ho-chi-minh-city\">Ho Chi Minh-Ville</a> avant ou après.</li>"
        "<li>Saison sèche (décembre–mai) : canaux plus accessibles, moins de pluie.</li>"
        "</ul>"
        "<h2>Questions fréquentes</h2>"
        "<h3>Le delta du Mékong vaut-il le détour en 1 jour ?</h3>"
        "<p>Oui pour une première découverte depuis Saigon, mais attendez-vous à un rythme "
        "touristique. Une nuit à Cần Thơ transforme l'expérience grâce au marché de l'aube.</p>"
        "<h3>Comment rejoindre Cần Thơ depuis Saigon ?</h3>"
        "<p>Bus 3–4 h (10–15 €) ou voiture privée 3 h. Beaucoup de tours incluent le transfert ; "
        "sinon, réservez un car partagé via votre hôtel.</p>"
        "<h3>Peut-on visiter le delta sans agence ?</h3>"
        "<p>Oui en allant à Cần Thơ par vos moyens et en louant un sampan sur place le matin, "
        "mais un guide local facilite l'accès aux petits canaux et évite les pièges tarifaires.</p>"
        + _common_footer(dest_href="/delta-du-mekong", dest_label="Delta du Mékong", loc_slug="ho-chi-minh-city")
    )


# ── 4. Hoi An ─────────────────────────────────────────────────────────────

def _hoian_content() -> str:
    a = _aff("hoi-an", "Hoi An tour")
    return (
        "<p><strong>Hội An</strong>, ancien comptoir marchand classé à l'UNESCO, est la ville "
        "la plus photogénique du Vietnam. Maisons en bois ocre, <strong>lanternes</strong> "
        "colorées, tailleurs sur mesure et plage d'<strong>An Bang</strong> à vélo : l'atmosphère "
        "est unique, surtout au crépuscule. Située à 30 min de <a href=\"/da-nang\">Đà Nẵng</a>, "
        "Hội An se combine naturellement avec Huế et la côte du Centre.</p>"
        "<h2>La vieille ville et ses monuments</h2>"
        "<p>Le cœur piéton est accessible avec un <strong>ticket monuments</strong> (~120 000 VND, "
        "valable plusieurs jours) donnant accès à pont japonais, assemblées communales et "
        "maisons historiques. Perdez-vous dans les ruelles avant 9 h ou après 17 h pour éviter "
        "les groupes. Le quartier est plat — idéal à pied ou en vélo.</p>"
        "<h2>Expériences à ne pas manquer</h2>"
        "<ul>"
        "<li><strong>Soirée lanternes</strong> : chaque soir, le centre s'illumine ; le 14e jour "
        "lunaire, festival des lanternes flottantes.</li>"
        "<li><strong>Tailleur sur mesure</strong> : costume ou robe en 24–48 h, tissus abordables.</li>"
        "<li><strong>Cours de cuisine</strong> : marché + atelier (banh xeo, cao lau).</li>"
        "<li><strong>Plage d'An Bang</strong> : 15 min à vélo, bars de plage et couchers de soleil.</li>"
        "<li><strong>Excursion</strong> : Cham Islands (snorkeling) ou My Son (sanctuaires Cham).</li>"
        "</ul>"
        + _aff_box(
            "Activités et hébergement à Hội An",
            [
                ("Visites et ateliers Hội An (GetYourGuide)", a["gyg"]),
                ("Tours Hội An (Viator)", a["viator"]),
                ("Hôtels à Hội An (Booking)", a["booking"]),
                ("Hôtels à Hội An (Agoda)", a["agoda"]),
            ],
        )
        + "<h2>Où dormir ?</h2>"
        "<p>Le centre historique pour l'ambiance (mais bruyant le soir), ou An Bang / Cam Chau "
        "pour la plage. Les hôtels-boutiques en maison ancienne sont la spécialité de la ville — "
        "réservez tôt en haute saison (février–août).</p>"
        "<h2>Combien de temps et quand y aller ?</h2>"
        "<p><strong>2 nuits minimum</strong> pour profiter d'une soirée et d'une demi-journée "
        "libre. <strong>Meilleure période</strong> : février–août (temps sec). Octobre–décembre : "
        "pluies possibles et rues parfois inondées. Évitez le Tết si vous voulez des tailleurs "
        "disponibles.</p>"
        "<h2>Questions fréquentes</h2>"
        "<h3>Faut-il un ticket pour entrer dans Hội An ?</h3>"
        "<p>La circulation piétonne du centre est contrôlée en soirée ; le ticket monuments couvre "
        "les sites historiques mais pas la simple balade dans les rues illuminées.</p>"
        "<h3>Hội An ou Đà Nẵng pour dormir ?</h3>"
        "<p>Hội An pour l'ambiance et les soirées ; Đà Nẵng pour les plages longues, l'aéroport "
        "et un hub plus moderne — les deux villes sont complémentaires à 30 min.</p>"
        "<h3>Combien coûte un costume sur mesure ?</h3>"
        "<p>Comptez 80–200 € selon le tissu et le délai. Demandez toujours un essayage final et "
        "vérifiez les finitions avant le départ.</p>"
        + _common_footer(dest_href="/hoi-an", dest_label="Hội An", loc_slug="hoi-an")
    )


# ── 5. Hué ────────────────────────────────────────────────────────────────

def _hue_content() -> str:
    a = _aff("da-nang", "Hue imperial tour")
    return (
        "<p><strong>Huế</strong> fut la capitale impériale du Vietnam (1802–1945). Entre "
        "<strong>citadelle</strong>, tombeaux des empereurs Nguyễn, pagode Thien Mu et "
        "<strong>rivière des Parfums</strong>, la ville offre une immersion culturelle rare "
        "entre <a href=\"/hoi-an\">Hội An</a> et le Nord. Sa cuisine impériale — bún bò Huế, "
        "assiettes royales — mérite à elle seule le détour.</p>"
        "<h2>La citadelle impériale</h2>"
        "<p>Enceinte de 10 km, palais, temples et jardins : prévoyez une <strong>demi-journée</strong>. "
        "Une partie des bâtiments a été endommagée pendant la guerre puis restaurée — l'échelle "
        "reste impressionnante. Louez un audio-guide ou un guide francophone pour comprendre "
        "la symbolique des portes et des pavillons.</p>"
        "<h2>Tombeaux et pagodes</h2>"
        "<ul>"
        "<li><strong>Tombeau de Minh Mạng</strong> : le plus harmonieux, lac et architecture sereine.</li>"
        "<li><strong>Tombeau de Khải Định</strong> : style art déco, mosaïques colorées, très photogénique.</li>"
        "<li><strong>Tombeau de Tự Đức</strong> : promenade forestière autour du tombeau.</li>"
        "<li><strong>Pagode Thien Mu</strong> : symbole de la ville, vue sur la rivière des Parfums.</li>"
        "</ul>"
        "<h2>Croisière et cuisine</h2>"
        "<p>Une <strong>croisière au coucher du soleil</strong> sur la rivière des Parfums relie "
        "souvent Thien Mu et dîner traditionnel. Côté assiette, goûtez le <strong>bún bò Huế</strong> "
        "dans une rue locale, puis réservez un restaurant de cuisine impériale pour les "
        "bouchées royales miniatures.</p>"
        + _aff_box(
            "Réserver visites et hôtels à Huế",
            [
                ("Visites impériales Huế (GetYourGuide)", a["gyg"]),
                ("Excursions Huế (Viator)", a["viator"]),
                ("Hôtels à Huế (Booking)", a["booking"]),
            ],
        )
        + "<h2>Organisation du séjour</h2>"
        "<p><strong>1 à 2 jours</strong> suffisent pour citadelle + 2 tombeaux. Louez un "
        "cyclo-pousse, taxi ou scooter pour relier les sites éloignés. Le train depuis "
        "<a href=\"/da-nang\">Đà Nẵng</a> (2 h, littoral spectaculaire) est une belle entrée "
        "en matière. Combinez Huế avec Hội An et Đà Nẵng pour un triangle classique du Centre.</p>"
        "<h2>Questions fréquentes</h2>"
        "<h3>Combien de temps pour visiter Huế ?</h3>"
        "<p>Une journée intense couvre citadelle et Thien Mu ; deux jours permettent d'ajouter "
        "deux tombeaux et un repas impérial sans courir.</p>"
        "<h3>Huế est-elle une ville pour les gourmands ?</h3>"
        "<p>Oui : bún bò Huế, nem lụi, banh beo et cuisine de rue raffinée. C'est l'une des "
        "capitales gastronomiques du Vietnam.</p>"
        "<h3>Comment rejoindre Huế depuis Hội An ?</h3>"
        "<p>Minibus 3–4 h via col de Hải Vân, ou train depuis Đà Nẵng. Le bus est direct ; "
        "le train offre les plus beaux paysages.</p>"
        + _common_footer(dest_href="/hue", dest_label="Huế", loc_slug="da-nang")
    )


# ── 6. Phu Quoc ───────────────────────────────────────────────────────────

def _phuquoc_content() -> str:
    a = _aff("ho-chi-minh-city", "Phu Quoc island tour")
    return (
        "<p><strong>Phu Quoc</strong>, plus grande île du Vietnam, cumule plages de sable blanc, "
        "eaux turquoise et resorts à tous budgets. Après le rythme intense de <a href=\"/hanoi\">Hanoï</a>, "
        "<a href=\"/hoi-an\">Hội An</a> ou <a href=\"/ho-chi-minh-city\">Saigon</a>, c'est la "
        "conclusion idéale : farniente, snorkeling et marchés nocturnes. Ce guide détaille les "
        "plages, activités et la saison pour organiser 3 à 5 jours sur l'île.</p>"
        "<h2>Les meilleures plages</h2>"
        "<ul>"
        "<li><strong>Sao Beach</strong> : sable fin, eau calme, idéal famille.</li>"
        "<li><strong>Long Beach</strong> : longue, couchers de soleil, restaurants en bord de mer.</li>"
        "<li><strong>Bai Khem</strong> : eaux cristallines, accès parfois régulé — plus préservée.</li>"
        "<li><strong>Ganh Dau</strong> : nord de l'île, plus sauvage, couchers de soleil.</li>"
        "</ul>"
        "<h2>Au-delà de la plage</h2>"
        "<ul>"
        "<li><strong>Snorkeling / plongée</strong> : îles An Thoi au sud, eaux claires mars–août.</li>"
        "<li><strong>Plantations</strong> : poivre de Phu Quoc (IGP) et sauce nuoc mam.</li>"
        "<li><strong>Marché nocturne Duong Dong</strong> : fruits de mer, street food.</li>"
        "<li><strong>Vinpearl Safari</strong> : famille, demi-journée.</li>"
        "<li><strong>Kayak mangrove</strong> : rivière Cua Can, calme et ombragé.</li>"
        "</ul>"
        + _aff_box(
            "Vols, hôtels et activités à Phu Quoc",
            [
                ("Excursions île Phu Quoc (GetYourGuide)", a["gyg"]),
                ("Tours Phu Quoc (Viator)", a["viator"]),
                ("Hôtels à Phu Quoc (Booking)", a["booking"]),
                ("Hôtels à Phu Quoc (Agoda)", a["agoda"]),
            ],
        )
        + "<h2>Pratique : vols, saison, budget</h2>"
        "<p>Vols directs depuis Hanoï, HCMC ou Đà Nẵng (1–2 h). <strong>Saison sèche</strong> "
        "novembre–avril : mer calme, ciel bleu. Mousson juin–octobre : mer agitée, pluies "
        "fréquentes — tarifs bas mais plage limitée. Budget : 40–80 €/jour confort (hôtel + "
        "restaurants), hors resort luxe.</p>"
        "<h2>Questions fréquentes</h2>"
        "<h3>Combien de jours à Phu Quoc ?</h3>"
        "<p>3 jours pour se poser, 5 jours pour alterner plages, snorkeling et exploration "
        "de l'île sans précipitation.</p>"
        "<h3>Phu Quoc ou Nha Trang pour la plage ?</h3>"
        "<p>Phu Quoc est plus « île tropicale » avec resorts et nature ; Nha Trang plus urbaine "
        "et animée. Phu Quoc convient mieux en fin de voyage détente.</p>"
        "<h3>Faut-il louer un scooter à Phu Quoc ?</h3>"
        "<p>Oui si vous voulez explorer hors du littoral principal — routes correctes, "
        "locations ~5–8 €/jour. Grab existe aussi autour de Duong Dong.</p>"
        + _common_footer(dest_href="/phu-quoc", dest_label="Phu Quoc", loc_slug="ho-chi-minh-city")
    )


# ── 7. Da Nang ────────────────────────────────────────────────────────────

def _danang_content() -> str:
    a = _aff("da-nang", "Da Nang beach tour")
    return (
        "<p><strong>Đà Nẵng</strong> est la ville la plus agréable à vivre du Centre : moderne, "
        "propre, entre mer et montagnes. Base idéale pour <a href=\"/hoi-an\">Hội An</a> (30 min), "
        "<a href=\"/hue\">Huế</a> (2 h) et les plages de <strong>My Khe</strong>, elle combine "
        "urbanité vietnamienne et farniente. Pont du Dragon, Marble Mountains et Ba Na Hills "
        "complètent un séjour où plage et culture coexistent.</p>"
        "<h2>Plages et baignade</h2>"
        "<p><strong>My Khe</strong> : 30 km de sable, surf occasionnel, bars et resorts — la "
        "plage « américaine » iconique. <strong>Non Nuoc</strong>, au pied des Marble Mountains : "
        "plus calme, idéale en famille. Baignade confortable <strong>octobre–mai</strong> ; "
        "surveillez les drapeaux de sécurité pendant la mousson.</p>"
        "<h2>À voir en ville et aux alentours</h2>"
        "<ul>"
        "<li><strong>Marble Mountains</strong> : grottes, pagodes, vue panoramique sur la côte.</li>"
        "<li><strong>Pont du Dragon</strong> : spectacle feu et eau week-end vers 21 h.</li>"
        "<li><strong>Ba Na Hills</strong> : Golden Bridge (main géante), parc — journée complète.</li>"
        "<li><strong>Musée Cham</strong> : sculpture cham unique au Vietnam.</li>"
        "<li><strong>Han Market</strong> : street food et produits locaux.</li>"
        "</ul>"
        + _aff_box(
            "Activités et hôtels à Đà Nẵng",
            [
                ("Excursions Đà Nẵng (GetYourGuide)", a["gyg"]),
                ("Tours Đà Nẵng (Viator)", a["viator"]),
                ("Hôtels à Đà Nẵng (Booking)", a["booking"]),
                ("Hôtels à Đà Nẵng (Agoda)", a["agoda"]),
            ],
        )
        + "<h2>Itinéraire 2–3 jours</h2>"
        "<ol>"
        "<li><strong>Jour 1</strong> : Marble Mountains le matin, plage My Khe l'après-midi, "
        "pont du Dragon le soir.</li>"
        "<li><strong>Jour 2</strong> : excursion <a href=\"/hoi-an\">Hội An</a> (vieille ville + "
        "lanternes).</li>"
        "<li><strong>Jour 3</strong> : Ba Na Hills ou train vers <a href=\"/hue\">Huế</a>.</li>"
        "</ol>"
        "<h2>Questions fréquentes</h2>"
        "<h3>Đà Nẵng est-elle une bonne base pour Hội An ?</h3>"
        "<p>Oui : 30 min en taxi/Grab, plages supérieures à An Bang pour la baignade, aéroport "
        "international pratique. Beaucoup de voyageurs divisent nuits entre les deux villes.</p>"
        "<h3>Quand voir le Dragon Bridge ?</h3>"
        "<p>Le week-end vers 21 h (feu et eau) — arrivez 30 min en avance, foule importante. "
        "Le pont est illuminé tous les soirs même sans spectacle.</p>"
        "<h3>Ba Na Hills vaut-il une journée ?</h3>"
        "<p>Oui pour la Golden Bridge et la vue ; c'est un parc à thème avec files d'attente. "
        "Réservez tôt et partez à l'ouverture.</p>"
        + _common_footer(dest_href="/da-nang", dest_label="Đà Nẵng", loc_slug="da-nang")
    )


# ── Builder ─────────────────────────────────────────────────────────────────

_EXPERIENCE_SPECS = [
    {
        "slug": "croisiere-baie-halong-vietnam",
        "city": "Ha Long",
        "image": "/static/images/pool/1545172538-171a802bd867.webp",
        "image_photo_id": "1545172538-171a802bd867",
        "read_time": 14,
        "title": "Croisière dans la baie d'Halong : guide complet 2026 (prix, durée, conseils)",
        "excerpt": "Karsts, kayak et nuit à bord : comparatif 1 jour / 2 jours, budgets, arnaques à éviter et bons plans pour réserver votre croisière à Halong.",
        "tags": ["Halong", "croisière", "baie d'Halong", "UNESCO", "jonque", "kayak"],
        "content_fn": _halong_content,
    },
    {
        "slug": "trek-sapa-rizieres-vietnam",
        "city": "Sapa",
        "image": "/static/images/pool/1531737212413-667205e1cda7.webp",
        "image_photo_id": "1531737212413-667205e1cda7",
        "read_time": 14,
        "title": "Trek à Sapa : rizières, villages et randonnées dans le Nord (guide 2026)",
        "excerpt": "Sentiers, guides Hmong, homestay, train de nuit depuis Hanoï et meilleure saison pour randonner à Sapa dans les rizières en terrasses.",
        "tags": ["Sapa", "trek", "rizières", "montagne", "Fansipan", "homestay"],
        "content_fn": _sapa_content,
    },
    {
        "slug": "excursion-delta-mekong-marches-flottants",
        "city": "Mỹ Tho / Delta du Mékong",
        "image": "/static/images/pool/1583417319070-4a69db38a482.webp",
        "image_photo_id": "1583417319070-4a69db38a482",
        "read_time": 13,
        "title": "Delta du Mékong : marchés flottants et excursions depuis Saigon (guide 2026)",
        "excerpt": "Can Tho, Cai Rang, Mỹ Tho : organiser une excursion 1 ou 2 jours dans le delta, éviter les pièges et vivre les marchés à l'aube.",
        "tags": ["Mékong", "delta", "marché flottant", "Can Tho", "Saigon", "sampan"],
        "content_fn": _mekong_content,
    },
    {
        "slug": "hoi-an-lanternes-vieille-ville",
        "city": "Hội An",
        "image": "/static/images/pool/1559592413-7cec4d0cae2b.webp",
        "image_photo_id": "1559592413-7cec4d0cae2b",
        "read_time": 13,
        "title": "Hội An : lanternes, vieille ville UNESCO et meilleures expériences (guide 2026)",
        "excerpt": "Vieille ville, tailleurs, plage d'An Bang, festival des lanternes : quand partir, combien de temps et quoi faire à Hội An.",
        "tags": ["Hội An", "lanternes", "UNESCO", "vieille ville", "An Bang", "tailleur"],
        "content_fn": _hoian_content,
    },
    {
        "slug": "hue-citadelle-imperiale-vietnam",
        "city": "Huế",
        "image": "/static/images/pool/1578662996442-48f60103fc96.webp",
        "image_photo_id": "1578662996442-48f60103fc96",
        "read_time": 13,
        "title": "Huế impériale : citadelle, tombeaux et rivière des Parfums (guide 2026)",
        "excerpt": "Citadelle Nguyen, tombeaux de Minh Mạng et Khải Định, cuisine impériale : organiser 1 à 2 jours à Huế entre Hội An et le Nord.",
        "tags": ["Huế", "impérial", "citadelle", "tombeaux", "patrimoine", "bún bò"],
        "content_fn": _hue_content,
    },
    {
        "slug": "phu-quoc-plages-ile-tropicale",
        "city": "Phú Quốc",
        "image": "/static/images/pool/1555979864-7a8f9b4fddf8.webp",
        "image_photo_id": "1555979864-7a8f9b4fddf8",
        "read_time": 12,
        "title": "Phu Quoc : plages, île tropicale et séjour détente (guide 2026)",
        "excerpt": "Sao Beach, Long Beach, snorkeling et saison sèche : organiser 3 à 5 jours sur l'île la plus grande du Vietnam.",
        "tags": ["Phu Quoc", "plage", "île", "détente", "snorkeling", "Duong Dong"],
        "content_fn": _phuquoc_content,
    },
    {
        "slug": "da-nang-plages-vietnam",
        "city": "Đà Nẵng",
        "image": "/static/images/pool/1555979864-7a8f9b4fddf8.webp",
        "image_photo_id": "1555979864-7a8f9b4fddf8",
        "read_time": 12,
        "title": "Đà Nẵng et ses plages : My Khe, Marble Mountains et pont du Dragon (guide 2026)",
        "excerpt": "Ville balnéaire entre Hội An et Huế : plages, Ba Na Hills, itinéraire 2–3 jours et bons plans hébergement.",
        "tags": ["Đà Nẵng", "plage", "My Khe", "Marble Mountains", "Dragon Bridge", "centre"],
        "content_fn": _danang_content,
    },
]


def _build_article(spec: dict) -> dict:
    content = spec["content_fn"]()
    title = spec["title"]
    excerpt = spec["excerpt"]
    image_alt = f"{title} — {spec['city']}, Vietnam"
    fr = {
        "title": title,
        "excerpt": excerpt,
        "content": content,
        "category_label": "Itinéraires",
        "tags": spec["tags"],
        "image_alt": image_alt,
    }
    return {
        "slug": spec["slug"],
        "category": "itinerary",
        "date": "2026-06-10",
        "updated_at": "2026-06-10",
        "builtin_version": "2026-06-10-v2",
        "city": spec["city"],
        "featured": False,
        "read_time": spec["read_time"],
        "guide_type": "Guide expérience",
        "ai_generated": False,
        "image": spec["image"],
        "image_photo_id": spec["image_photo_id"],
        "image_placeholder": False,
        "i18n": {"fr": fr, "en": {}},
        **fr,
    }


def build_experience_articles() -> list[dict]:
    return [_build_article(s) for s in _EXPERIENCE_SPECS]


EXPERIENCE_ARTICLE_SLUGS = [s["slug"] for s in _EXPERIENCE_SPECS]
