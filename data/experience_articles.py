"""Guides experience pilier que-faire — sync auto en prod (Postgres KV)."""

EXPERIENCE_ARTICLE_SLUGS = ['croisiere-baie-halong-vietnam', 'da-nang-plages-vietnam', 'excursion-delta-mekong-marches-flottants', 'hoi-an-lanternes-vieille-ville', 'hue-citadelle-imperiale-vietnam', 'phu-quoc-plages-ile-tropicale', 'trek-sapa-rizieres-vietnam']

EXPERIENCE_ARTICLES = [{'slug': 'croisiere-baie-halong-vietnam',
  'category': 'itinerary',
  'date': '2026-06-10',
  'city': 'Ha Long',
  'featured': False,
  'read_time': 7,
  'guide_type': 'Guide expérience',
  'ai_generated': False,
  'image': '/static/images/pool/1545172538-171a802bd867.webp',
  'image_photo_id': '1545172538-171a802bd867',
  'image_placeholder': False,
  'i18n': {'fr': {'title': "Croisière dans la baie d'Halong : comment choisir et organiser",
                  'excerpt': 'Karsts, kayak et nuit à bord : comparatif 1 jour / 2 jours, prix et '
                             'conseils pour réserver sans arnaque.',
                  'content': "<p>La baie d'Halong, classée à l'UNESCO, reste l'expérience la plus "
                             'iconique du Vietnam. Des milliers\n'
                             "d'îlots karstiques émergent d'une eau émeraude : le spectacle "
                             "justifie largement une nuit sur l'eau.</p>\n"
                             '<h2>1 jour ou 2 jours (1 nuit) ?</h2>\n'
                             "<p><strong>Excursion d'une journée</strong> depuis Hanoï (4 h de "
                             'route aller-retour) : aperçu correct si\n'
                             'vous manquez de temps, mais fatigant. <strong>Croisière 2 jours / 1 '
                             'nuit</strong> : le choix idéal —\n'
                             'coucher de soleil, kayak au lever du jour, baignade loin des flottes '
                             'du matin.</p>\n'
                             '<h2>Quel type de bateau ?</h2>\n'
                             '<ul>\n'
                             '<li><strong>Budget</strong> : jonque collective, cabine partagée, '
                             '80–120 €/pers.</li>\n'
                             '<li><strong>Confort</strong> : cabine privée, repas soignés, 130–200 '
                             '€/pers.</li>\n'
                             '<li><strong>Premium</strong> : yacht, suite, 250 €+ — excellent '
                             'rapport vs croisières méditerranéennes.</li>\n'
                             '</ul>\n'
                             '<h2>Conseils pratiques</h2>\n'
                             '<p>Réservez via un opérateur reconnu (évitez les vendeurs de rue à '
                             'Hanoï). Vérifiez ce qui est inclus :\n'
                             'transfert, kayak, entrée de la baie, pourboires. Saison idéale : '
                             'octobre à avril (mer plus calme).\n'
                             'Évitez le Tết si possible (affluence et tarifs majorés).</p>\n'
                             '<h3>Combien de temps sur place ?</h3>\n'
                             '<p>Comptez 2 à 3 jours au total avec le transfert depuis Hanoï. Pour '
                             'prolonger, combinez avec\n'
                             '<strong>Cat Ba</strong> ou un séjour à <strong>Hanoï</strong> avant '
                             'le départ.</p><p>Pour les adresses, hébergements et conseils '
                             'détaillés sur place, consultez notre <a href="/halong">guide complet '
                             'Halong</a>.</p>',
                  'category_label': 'Itinéraires',
                  'tags': ['Halong', 'croisière', 'baie', 'UNESCO'],
                  'image_alt': "Croisière dans la baie d'Halong : comment choisir et organiser — "
                               'Ha Long, Vietnam'},
           'en': {}},
  'title': "Croisière dans la baie d'Halong : comment choisir et organiser",
  'excerpt': 'Karsts, kayak et nuit à bord : comparatif 1 jour / 2 jours, prix et conseils pour '
             'réserver sans arnaque.',
  'content': "<p>La baie d'Halong, classée à l'UNESCO, reste l'expérience la plus iconique du "
             'Vietnam. Des milliers\n'
             "d'îlots karstiques émergent d'une eau émeraude : le spectacle justifie largement une "
             "nuit sur l'eau.</p>\n"
             '<h2>1 jour ou 2 jours (1 nuit) ?</h2>\n'
             "<p><strong>Excursion d'une journée</strong> depuis Hanoï (4 h de route aller-retour) "
             ': aperçu correct si\n'
             'vous manquez de temps, mais fatigant. <strong>Croisière 2 jours / 1 nuit</strong> : '
             'le choix idéal —\n'
             'coucher de soleil, kayak au lever du jour, baignade loin des flottes du matin.</p>\n'
             '<h2>Quel type de bateau ?</h2>\n'
             '<ul>\n'
             '<li><strong>Budget</strong> : jonque collective, cabine partagée, 80–120 '
             '€/pers.</li>\n'
             '<li><strong>Confort</strong> : cabine privée, repas soignés, 130–200 €/pers.</li>\n'
             '<li><strong>Premium</strong> : yacht, suite, 250 €+ — excellent rapport vs '
             'croisières méditerranéennes.</li>\n'
             '</ul>\n'
             '<h2>Conseils pratiques</h2>\n'
             '<p>Réservez via un opérateur reconnu (évitez les vendeurs de rue à Hanoï). Vérifiez '
             'ce qui est inclus :\n'
             'transfert, kayak, entrée de la baie, pourboires. Saison idéale : octobre à avril '
             '(mer plus calme).\n'
             'Évitez le Tết si possible (affluence et tarifs majorés).</p>\n'
             '<h3>Combien de temps sur place ?</h3>\n'
             '<p>Comptez 2 à 3 jours au total avec le transfert depuis Hanoï. Pour prolonger, '
             'combinez avec\n'
             '<strong>Cat Ba</strong> ou un séjour à <strong>Hanoï</strong> avant le '
             'départ.</p><p>Pour les adresses, hébergements et conseils détaillés sur place, '
             'consultez notre <a href="/halong">guide complet Halong</a>.</p>',
  'category_label': 'Itinéraires',
  'tags': ['Halong', 'croisière', 'baie', 'UNESCO'],
  'image_alt': "Croisière dans la baie d'Halong : comment choisir et organiser — Ha Long, Vietnam"},
 {'slug': 'da-nang-plages-vietnam',
  'category': 'itinerary',
  'date': '2026-06-10',
  'city': 'Đà Nẵng',
  'featured': False,
  'read_time': 7,
  'guide_type': 'Guide expérience',
  'ai_generated': False,
  'image': '/static/images/pool/1555979864-7a8f9b4fddf8.webp',
  'image_photo_id': '1555979864-7a8f9b4fddf8',
  'image_placeholder': False,
  'i18n': {'fr': {'title': 'Đà Nẵng et ses plages : ville balnéaire entre Hội An et Huế',
                  'excerpt': 'My Khe, Marble Mountains et pont du Dragon : 2 jours entre culture '
                             'et farniente.',
                  'content': '<p>Đà Nẵng est la ville la plus agréable à vivre du Centre : '
                             'moderne, propre, entre mer et montagnes.\n'
                             'Elle sert de base idéale pour Hội An (30 min) et la région de '
                             'Huế.</p>\n'
                             '<h2>Plages et baignade</h2>\n'
                             '<p><strong>My Khe</strong> (plage « américaine ») : 30 km de sable, '
                             'bars et resorts. <strong>Non Nuoc</strong>\n'
                             'au pied des Marble Mountains : plus calme. La baignade est possible '
                             'octobre–mai ; surveillez les\n'
                             'drapeaux de sécurité en saison des pluies.</p>\n'
                             '<h2>À voir en ville</h2>\n'
                             '<ul>\n'
                             '<li><strong>Marble Mountains</strong> : grottes, pagodes, vue sur la '
                             'côte.</li>\n'
                             '<li><strong>Pont du Dragon</strong> : spectacle de feu et eau le '
                             'week-end (20 h).</li>\n'
                             '<li><strong>Ba Na Hills</strong> : Golden Bridge (main géante), parc '
                             "d'attractions — journée complète.</li>\n"
                             '</ul>\n'
                             '<h2>Combien de temps ?</h2>\n'
                             '<p>2 nuits pour la ville + une excursion à <strong>Hội An</strong>. '
                             'Les voyageurs pressés font Đà Nẵng\n'
                             'en hub aérien entre le Nord et le Sud.</p><p>Pour les adresses, '
                             'hébergements et conseils détaillés sur place, consultez notre <a '
                             'href="/da-nang">guide complet Đà Nẵng</a>.</p>',
                  'category_label': 'Itinéraires',
                  'tags': ['Đà Nẵng', 'plage', 'My Khe', 'centre'],
                  'image_alt': 'Đà Nẵng et ses plages : ville balnéaire entre Hội An et Huế — Đà '
                               'Nẵng, Vietnam'},
           'en': {}},
  'title': 'Đà Nẵng et ses plages : ville balnéaire entre Hội An et Huế',
  'excerpt': 'My Khe, Marble Mountains et pont du Dragon : 2 jours entre culture et farniente.',
  'content': '<p>Đà Nẵng est la ville la plus agréable à vivre du Centre : moderne, propre, entre '
             'mer et montagnes.\n'
             'Elle sert de base idéale pour Hội An (30 min) et la région de Huế.</p>\n'
             '<h2>Plages et baignade</h2>\n'
             '<p><strong>My Khe</strong> (plage « américaine ») : 30 km de sable, bars et resorts. '
             '<strong>Non Nuoc</strong>\n'
             'au pied des Marble Mountains : plus calme. La baignade est possible octobre–mai ; '
             'surveillez les\n'
             'drapeaux de sécurité en saison des pluies.</p>\n'
             '<h2>À voir en ville</h2>\n'
             '<ul>\n'
             '<li><strong>Marble Mountains</strong> : grottes, pagodes, vue sur la côte.</li>\n'
             '<li><strong>Pont du Dragon</strong> : spectacle de feu et eau le week-end (20 '
             'h).</li>\n'
             "<li><strong>Ba Na Hills</strong> : Golden Bridge (main géante), parc d'attractions — "
             'journée complète.</li>\n'
             '</ul>\n'
             '<h2>Combien de temps ?</h2>\n'
             '<p>2 nuits pour la ville + une excursion à <strong>Hội An</strong>. Les voyageurs '
             'pressés font Đà Nẵng\n'
             'en hub aérien entre le Nord et le Sud.</p><p>Pour les adresses, hébergements et '
             'conseils détaillés sur place, consultez notre <a href="/da-nang">guide complet Đà '
             'Nẵng</a>.</p>',
  'category_label': 'Itinéraires',
  'tags': ['Đà Nẵng', 'plage', 'My Khe', 'centre'],
  'image_alt': 'Đà Nẵng et ses plages : ville balnéaire entre Hội An et Huế — Đà Nẵng, Vietnam'},
 {'slug': 'excursion-delta-mekong-marches-flottants',
  'category': 'itinerary',
  'date': '2026-06-10',
  'city': 'Mỹ Tho / Delta du Mékong',
  'featured': False,
  'read_time': 7,
  'guide_type': 'Guide expérience',
  'ai_generated': False,
  'image': '/static/images/pool/1583417319070-4a69db38a482.webp',
  'image_photo_id': '1583417319070-4a69db38a482',
  'image_placeholder': False,
  'i18n': {'fr': {'title': 'Delta du Mékong : marchés flottants et excursions depuis Saigon',
                  'excerpt': 'Can Tho, Cai Rang, Mỹ Tho : comment organiser une excursion 1 ou 2 '
                             'jours dans le delta.',
                  'content': '<p>Le delta du Mékong, au sud de Hô-Chi-Minh-Ville, est un '
                             'labyrinthe de canaux, de vergers et de\n'
                             "marchés flottants. C'est l'antithèse des mégalopoles : la vie "
                             "s'organise autour de l'eau.</p>\n"
                             '<h2>Excursion 1 jour depuis Saigon</h2>\n'
                             '<p>Les circuits classiques partent vers <strong>Mỹ Tho</strong> ou '
                             '<strong>Ben Tre</strong> : croisière en\n'
                             'sampan, dégustation de noix de coco, atelier de bonbons artisanaux. '
                             'Comptez 25–45 € avec transfert.\n'
                             'Idéal pour un premier aperçu, mais touristique.</p>\n'
                             '<h2>2 jours : le vrai delta</h2>\n'
                             '<p>Passez une nuit à <strong>Can Tho</strong> pour assister au '
                             '<strong>marché flottant de Cai Rang</strong>\n'
                             "à l'aube (5 h–8 h). Ajoutez une balade en sampan dans les petits "
                             'canaux et un homestay à Ben Tre\n'
                             'pour une immersion plus authentique.</p>\n'
                             '<h2>Conseils</h2>\n'
                             '<p>Partez tôt le matin pour les marchés. Prévoyez chapeau, '
                             'anti-moustiques et espèces pour les achats\n'
                             "sur l'eau. Combinez avec un séjour à <strong>Ho Chi "
                             'Minh-Ville</strong> (2–3 jours) avant ou après.</p><p>Pour les '
                             'adresses, hébergements et conseils détaillés sur place, consultez '
                             'notre <a href="/delta-du-mekong">guide complet Delta du '
                             'Mékong</a>.</p>',
                  'category_label': 'Itinéraires',
                  'tags': ['Mékong', 'delta', 'marché flottant', 'Can Tho'],
                  'image_alt': 'Delta du Mékong : marchés flottants et excursions depuis Saigon — '
                               'Mỹ Tho / Delta du Mékong, Vietnam'},
           'en': {}},
  'title': 'Delta du Mékong : marchés flottants et excursions depuis Saigon',
  'excerpt': 'Can Tho, Cai Rang, Mỹ Tho : comment organiser une excursion 1 ou 2 jours dans le '
             'delta.',
  'content': '<p>Le delta du Mékong, au sud de Hô-Chi-Minh-Ville, est un labyrinthe de canaux, de '
             'vergers et de\n'
             "marchés flottants. C'est l'antithèse des mégalopoles : la vie s'organise autour de "
             "l'eau.</p>\n"
             '<h2>Excursion 1 jour depuis Saigon</h2>\n'
             '<p>Les circuits classiques partent vers <strong>Mỹ Tho</strong> ou <strong>Ben '
             'Tre</strong> : croisière en\n'
             'sampan, dégustation de noix de coco, atelier de bonbons artisanaux. Comptez 25–45 € '
             'avec transfert.\n'
             'Idéal pour un premier aperçu, mais touristique.</p>\n'
             '<h2>2 jours : le vrai delta</h2>\n'
             '<p>Passez une nuit à <strong>Can Tho</strong> pour assister au <strong>marché '
             'flottant de Cai Rang</strong>\n'
             "à l'aube (5 h–8 h). Ajoutez une balade en sampan dans les petits canaux et un "
             'homestay à Ben Tre\n'
             'pour une immersion plus authentique.</p>\n'
             '<h2>Conseils</h2>\n'
             '<p>Partez tôt le matin pour les marchés. Prévoyez chapeau, anti-moustiques et '
             'espèces pour les achats\n'
             "sur l'eau. Combinez avec un séjour à <strong>Ho Chi Minh-Ville</strong> (2–3 jours) "
             'avant ou après.</p><p>Pour les adresses, hébergements et conseils détaillés sur '
             'place, consultez notre <a href="/delta-du-mekong">guide complet Delta du '
             'Mékong</a>.</p>',
  'category_label': 'Itinéraires',
  'tags': ['Mékong', 'delta', 'marché flottant', 'Can Tho'],
  'image_alt': 'Delta du Mékong : marchés flottants et excursions depuis Saigon — Mỹ Tho / Delta '
               'du Mékong, Vietnam'},
 {'slug': 'hoi-an-lanternes-vieille-ville',
  'category': 'itinerary',
  'date': '2026-06-10',
  'city': 'Hội An',
  'featured': False,
  'read_time': 7,
  'guide_type': 'Guide expérience',
  'ai_generated': False,
  'image': '/static/images/pool/1559592413-7cec4d0cae2b.webp',
  'image_photo_id': '1559592413-7cec4d0cae2b',
  'image_placeholder': False,
  'i18n': {'fr': {'title': 'Hội An : lanternes, vieille ville et atmosphère unique',
                  'excerpt': "Le joyau classé du Centre : lanternes, tailleurs, plage d'An Bang et "
                             'meilleur moment pour visiter.',
                  'content': '<p>Hội An, ancien comptoir marchand, est la ville la plus '
                             'photogénique du Vietnam. Ses maisons en\n'
                             'bois ocre, ses lanternes colorées et ses ruelles piétonnes créent '
                             'une atmosphère hors du temps.</p>\n'
                             '<h2>Que faire dans la vieille ville ?</h2>\n'
                             '<ul>\n'
                             '<li>Se perdre au <strong>quartier historique</strong> (ticket '
                             'monuments regroupé ~6 €).</li>\n'
                             '<li>Faire tailler un costume ou une robe en 24–48 h (tissus '
                             'abordables, qualité variable).</li>\n'
                             '<li>Assister au <strong>full moon lantern festival</strong> (14e '
                             'jour lunaire) si vos dates coïncident.</li>\n'
                             "<li>Aller à la plage d'<strong>An Bang</strong> à vélo (15 min) pour "
                             'un après-midi détente.</li>\n'
                             '</ul>\n'
                             '<h2>Combien de temps ?</h2>\n'
                             '<p>2 nuits minimum pour profiter du soir (lanternes allumées) et '
                             "d'une demi-journée libre. Hội An se\n"
                             'combine naturellement avec <strong>Đà Nẵng</strong> (30 min) et '
                             '<strong>Huế</strong> (2–3 h).</p>\n'
                             '<h3>Meilleure période</h3>\n'
                             '<p>Février à août : temps sec. Évitez la saison des pluies '
                             '(octobre–décembre) où les rues peuvent\n'
                             'être inondées ponctuellement.</p><p>Pour les adresses, hébergements '
                             'et conseils détaillés sur place, consultez notre <a '
                             'href="/hoi-an">guide complet Hội An</a>.</p>',
                  'category_label': 'Itinéraires',
                  'tags': ['Hội An', 'lanternes', 'UNESCO', 'vieille ville'],
                  'image_alt': 'Hội An : lanternes, vieille ville et atmosphère unique — Hội An, '
                               'Vietnam'},
           'en': {}},
  'title': 'Hội An : lanternes, vieille ville et atmosphère unique',
  'excerpt': "Le joyau classé du Centre : lanternes, tailleurs, plage d'An Bang et meilleur moment "
             'pour visiter.',
  'content': '<p>Hội An, ancien comptoir marchand, est la ville la plus photogénique du Vietnam. '
             'Ses maisons en\n'
             'bois ocre, ses lanternes colorées et ses ruelles piétonnes créent une atmosphère '
             'hors du temps.</p>\n'
             '<h2>Que faire dans la vieille ville ?</h2>\n'
             '<ul>\n'
             '<li>Se perdre au <strong>quartier historique</strong> (ticket monuments regroupé ~6 '
             '€).</li>\n'
             '<li>Faire tailler un costume ou une robe en 24–48 h (tissus abordables, qualité '
             'variable).</li>\n'
             '<li>Assister au <strong>full moon lantern festival</strong> (14e jour lunaire) si '
             'vos dates coïncident.</li>\n'
             "<li>Aller à la plage d'<strong>An Bang</strong> à vélo (15 min) pour un après-midi "
             'détente.</li>\n'
             '</ul>\n'
             '<h2>Combien de temps ?</h2>\n'
             "<p>2 nuits minimum pour profiter du soir (lanternes allumées) et d'une demi-journée "
             'libre. Hội An se\n'
             'combine naturellement avec <strong>Đà Nẵng</strong> (30 min) et <strong>Huế</strong> '
             '(2–3 h).</p>\n'
             '<h3>Meilleure période</h3>\n'
             '<p>Février à août : temps sec. Évitez la saison des pluies (octobre–décembre) où les '
             'rues peuvent\n'
             'être inondées ponctuellement.</p><p>Pour les adresses, hébergements et conseils '
             'détaillés sur place, consultez notre <a href="/hoi-an">guide complet Hội An</a>.</p>',
  'category_label': 'Itinéraires',
  'tags': ['Hội An', 'lanternes', 'UNESCO', 'vieille ville'],
  'image_alt': 'Hội An : lanternes, vieille ville et atmosphère unique — Hội An, Vietnam'},
 {'slug': 'hue-citadelle-imperiale-vietnam',
  'category': 'itinerary',
  'date': '2026-06-10',
  'city': 'Huế',
  'featured': False,
  'read_time': 7,
  'guide_type': 'Guide expérience',
  'ai_generated': False,
  'image': '/static/images/pool/1578662996442-48f60103fc96.webp',
  'image_photo_id': '1578662996442-48f60103fc96',
  'image_placeholder': False,
  'i18n': {'fr': {'title': 'Hué impériale : citadelle, tombeaux et rivière des Parfums',
                  'excerpt': 'Patrimoine impérial du Centre : citadelle, tombeaux des Nguyen et '
                             'croisière sur la rivière.',
                  'content': '<p>Huế fut la capitale impériale du Vietnam (1802–1945). Sa '
                             'citadelle, ses tombeaux et sa cuisine\n'
                             'impériale en font une étape culturelle incontournable entre Hội An '
                             'et le Nord.</p>\n'
                             '<h2>Les incontournables</h2>\n'
                             '<ul>\n'
                             '<li><strong>Citadelle impériale</strong> : palais, temples, '
                             'murailles — prévoyez une demi-journée.</li>\n'
                             '<li><strong>Tombeau de Minh Mạng</strong> : le plus harmonieux, lac '
                             'et architecture sereine.</li>\n'
                             '<li><strong>Tombeau de Khai Dinh</strong> : style art déco unique, '
                             'mosaïques colorées.</li>\n'
                             '<li><strong>Croisière sur la rivière des Parfums</strong> : pagode '
                             'Thien Mu au coucher du soleil.</li>\n'
                             '</ul>\n'
                             '<h2>Cuisine impériale</h2>\n'
                             '<p>Huế est réputée pour ses <strong>bún bò Huế</strong> (soupe '
                             'piquante) et ses assiettes royales\n'
                             'miniatures. Réservez une table dans un restaurant spécialisé pour '
                             "l'expérience complète.</p>\n"
                             '<h2>Organisation</h2>\n'
                             '<p>1 à 2 jours suffisent. Louez un cyclo-pousse ou un scooter pour '
                             'relier les tombeaux éloignés.\n'
                             'Combinez avec le train depuis <strong>Đà Nẵng</strong> (2 h, '
                             'paysages côtiers).</p><p>Pour les adresses, hébergements et conseils '
                             'détaillés sur place, consultez notre <a href="/hue">guide complet '
                             'Huế</a>.</p>',
                  'category_label': 'Itinéraires',
                  'tags': ['Huế', 'impérial', 'citadelle', 'patrimoine'],
                  'image_alt': 'Hué impériale : citadelle, tombeaux et rivière des Parfums — Huế, '
                               'Vietnam'},
           'en': {}},
  'title': 'Hué impériale : citadelle, tombeaux et rivière des Parfums',
  'excerpt': 'Patrimoine impérial du Centre : citadelle, tombeaux des Nguyen et croisière sur la '
             'rivière.',
  'content': '<p>Huế fut la capitale impériale du Vietnam (1802–1945). Sa citadelle, ses tombeaux '
             'et sa cuisine\n'
             'impériale en font une étape culturelle incontournable entre Hội An et le Nord.</p>\n'
             '<h2>Les incontournables</h2>\n'
             '<ul>\n'
             '<li><strong>Citadelle impériale</strong> : palais, temples, murailles — prévoyez une '
             'demi-journée.</li>\n'
             '<li><strong>Tombeau de Minh Mạng</strong> : le plus harmonieux, lac et architecture '
             'sereine.</li>\n'
             '<li><strong>Tombeau de Khai Dinh</strong> : style art déco unique, mosaïques '
             'colorées.</li>\n'
             '<li><strong>Croisière sur la rivière des Parfums</strong> : pagode Thien Mu au '
             'coucher du soleil.</li>\n'
             '</ul>\n'
             '<h2>Cuisine impériale</h2>\n'
             '<p>Huế est réputée pour ses <strong>bún bò Huế</strong> (soupe piquante) et ses '
             'assiettes royales\n'
             "miniatures. Réservez une table dans un restaurant spécialisé pour l'expérience "
             'complète.</p>\n'
             '<h2>Organisation</h2>\n'
             '<p>1 à 2 jours suffisent. Louez un cyclo-pousse ou un scooter pour relier les '
             'tombeaux éloignés.\n'
             'Combinez avec le train depuis <strong>Đà Nẵng</strong> (2 h, paysages '
             'côtiers).</p><p>Pour les adresses, hébergements et conseils détaillés sur place, '
             'consultez notre <a href="/hue">guide complet Huế</a>.</p>',
  'category_label': 'Itinéraires',
  'tags': ['Huế', 'impérial', 'citadelle', 'patrimoine'],
  'image_alt': 'Hué impériale : citadelle, tombeaux et rivière des Parfums — Huế, Vietnam'},
 {'slug': 'phu-quoc-plages-ile-tropicale',
  'category': 'itinerary',
  'date': '2026-06-10',
  'city': 'Phú Quốc',
  'featured': False,
  'read_time': 7,
  'guide_type': 'Guide expérience',
  'ai_generated': False,
  'image': '/static/images/pool/1555979864-7a8f9b4fddf8.webp',
  'image_photo_id': '1555979864-7a8f9b4fddf8',
  'image_placeholder': False,
  'i18n': {'fr': {'title': 'Phu Quoc : plages, île tropicale et séjour détente',
                  'excerpt': 'Sable blanc, couchers de soleil, poivre et pêche : organiser 3 à 5 '
                             "jours sur l'île du Sud.",
                  'content': '<p>Phu Quoc, la plus grande île du Vietnam, cumule plages de sable '
                             'blanc, eaux turquoise et\n'
                             "hôtels à tous budgets. C'est la conclusion idéale d'un voyage après "
                             'le rythme intense du Nord et\n'
                             'du Centre.</p>\n'
                             '<h2>Les meilleures plages</h2>\n'
                             '<ul>\n'
                             '<li><strong>Sao Beach</strong> : sable fin, eau calme, idéal '
                             'famille.</li>\n'
                             '<li><strong>Long Beach</strong> : longue, couchers de soleil, '
                             'restaurants en bord de mer.</li>\n'
                             '<li><strong>Bai Khem</strong> : plus préservée, eaux cristallines '
                             '(accès parfois payant).</li>\n'
                             '</ul>\n'
                             '<h2>Activités au-delà de la plage</h2>\n'
                             "<p>Snorkeling ou plongée au sud de l'île, visite des plantations de "
                             '<strong>poivre</strong> et de\n'
                             '<strong>nuoc mam</strong> (sauce de poisson), marché nocturne de '
                             'Duong Dong. Le <strong>Vinpearl\n'
                             'Safari</strong> plaît aux familles.</p>\n'
                             '<h2>Pratique</h2>\n'
                             '<p>Vols directs depuis Hanoï, HCMC ou Đà Nẵng. Saison sèche '
                             'novembre–avril. Comptez 3 à 5 jours.\n'
                             'Évitez la mousson (juin–octobre) : mer agitée et pluies '
                             'fréquentes.</p><p>Pour les adresses, hébergements et conseils '
                             'détaillés sur place, consultez notre <a href="/phu-quoc">guide '
                             'complet Phu Quoc</a>.</p>',
                  'category_label': 'Itinéraires',
                  'tags': ['Phu Quoc', 'plage', 'île', 'détente'],
                  'image_alt': 'Phu Quoc : plages, île tropicale et séjour détente — Phú Quốc, '
                               'Vietnam'},
           'en': {}},
  'title': 'Phu Quoc : plages, île tropicale et séjour détente',
  'excerpt': "Sable blanc, couchers de soleil, poivre et pêche : organiser 3 à 5 jours sur l'île "
             'du Sud.',
  'content': '<p>Phu Quoc, la plus grande île du Vietnam, cumule plages de sable blanc, eaux '
             'turquoise et\n'
             "hôtels à tous budgets. C'est la conclusion idéale d'un voyage après le rythme "
             'intense du Nord et\n'
             'du Centre.</p>\n'
             '<h2>Les meilleures plages</h2>\n'
             '<ul>\n'
             '<li><strong>Sao Beach</strong> : sable fin, eau calme, idéal famille.</li>\n'
             '<li><strong>Long Beach</strong> : longue, couchers de soleil, restaurants en bord de '
             'mer.</li>\n'
             '<li><strong>Bai Khem</strong> : plus préservée, eaux cristallines (accès parfois '
             'payant).</li>\n'
             '</ul>\n'
             '<h2>Activités au-delà de la plage</h2>\n'
             "<p>Snorkeling ou plongée au sud de l'île, visite des plantations de "
             '<strong>poivre</strong> et de\n'
             '<strong>nuoc mam</strong> (sauce de poisson), marché nocturne de Duong Dong. Le '
             '<strong>Vinpearl\n'
             'Safari</strong> plaît aux familles.</p>\n'
             '<h2>Pratique</h2>\n'
             '<p>Vols directs depuis Hanoï, HCMC ou Đà Nẵng. Saison sèche novembre–avril. Comptez '
             '3 à 5 jours.\n'
             'Évitez la mousson (juin–octobre) : mer agitée et pluies fréquentes.</p><p>Pour les '
             'adresses, hébergements et conseils détaillés sur place, consultez notre <a '
             'href="/phu-quoc">guide complet Phu Quoc</a>.</p>',
  'category_label': 'Itinéraires',
  'tags': ['Phu Quoc', 'plage', 'île', 'détente'],
  'image_alt': 'Phu Quoc : plages, île tropicale et séjour détente — Phú Quốc, Vietnam'},
 {'slug': 'trek-sapa-rizieres-vietnam',
  'category': 'itinerary',
  'date': '2026-06-10',
  'city': 'Sapa',
  'featured': False,
  'read_time': 7,
  'guide_type': 'Guide expérience',
  'ai_generated': False,
  'image': '/static/images/pool/1531737212413-667205e1cda7.webp',
  'image_photo_id': '1531737212413-667205e1cda7',
  'image_placeholder': False,
  'i18n': {'fr': {'title': 'Trek à Sapa : rizières, villages et randonnées dans le Nord',
                  'excerpt': 'Randonnée et villages ethniques du Nord : sentiers, guides locaux, '
                             'homestay et meilleure saison.',
                  'content': "<p>Sapa, perchée à 1 600 m d'altitude, offre des panoramas de "
                             'rizières en terrasses parmi les plus\n'
                             "photogéniques d'Asie. Le trek y est accessible aux marcheurs moyens, "
                             'avec des variantes faciles ou\n'
                             'sportives.</p>\n'
                             '<h2>Les meilleures randonnées</h2>\n'
                             '<ul>\n'
                             '<li><strong>Cat Cat → Y Linh Ho</strong> (½ journée) : villages '
                             'Hmong, rizières proches de Sapa ville.</li>\n'
                             '<li><strong>Ta Van → Giang Ta Chai</strong> (1 jour) : cascades, '
                             'ponts de bambou, rencontres locales.</li>\n'
                             '<li><strong>Fansipan</strong> (2 jours) : sommet du Vietnam (3 143 '
                             'm) — câble possible pour gagner du temps.</li>\n'
                             '</ul>\n'
                             '<h2>Guide local ou homestay ?</h2>\n'
                             "<p>Un guide Hmong ou Dao améliore l'expérience (sentiers, culture, "
                             "prix du marché). L'<strong>homestay</strong>\n"
                             'dans un village (Ta Van, Lao Chai) permet de vivre au rythme local — '
                             'réservez via votre hôtel ou\n'
                             'une agence sérieuse de Sapa.</p>\n'
                             '<h2>Quand partir ?</h2>\n'
                             '<p>Septembre à novembre : rizières dorées, ciel dégagé. Mars–mai : '
                             'verdure intense. Évitez la saison\n'
                             'des pluies (juin–août) : sentiers boueux et brume '
                             'fréquente.</p><p>Pour les adresses, hébergements et conseils '
                             'détaillés sur place, consultez notre <a href="/sapa">guide complet '
                             'Sapa</a>.</p>',
                  'category_label': 'Itinéraires',
                  'tags': ['Sapa', 'trek', 'rizières', 'montagne'],
                  'image_alt': 'Trek à Sapa : rizières, villages et randonnées dans le Nord — '
                               'Sapa, Vietnam'},
           'en': {}},
  'title': 'Trek à Sapa : rizières, villages et randonnées dans le Nord',
  'excerpt': 'Randonnée et villages ethniques du Nord : sentiers, guides locaux, homestay et '
             'meilleure saison.',
  'content': "<p>Sapa, perchée à 1 600 m d'altitude, offre des panoramas de rizières en terrasses "
             'parmi les plus\n'
             "photogéniques d'Asie. Le trek y est accessible aux marcheurs moyens, avec des "
             'variantes faciles ou\n'
             'sportives.</p>\n'
             '<h2>Les meilleures randonnées</h2>\n'
             '<ul>\n'
             '<li><strong>Cat Cat → Y Linh Ho</strong> (½ journée) : villages Hmong, rizières '
             'proches de Sapa ville.</li>\n'
             '<li><strong>Ta Van → Giang Ta Chai</strong> (1 jour) : cascades, ponts de bambou, '
             'rencontres locales.</li>\n'
             '<li><strong>Fansipan</strong> (2 jours) : sommet du Vietnam (3 143 m) — câble '
             'possible pour gagner du temps.</li>\n'
             '</ul>\n'
             '<h2>Guide local ou homestay ?</h2>\n'
             "<p>Un guide Hmong ou Dao améliore l'expérience (sentiers, culture, prix du marché). "
             "L'<strong>homestay</strong>\n"
             'dans un village (Ta Van, Lao Chai) permet de vivre au rythme local — réservez via '
             'votre hôtel ou\n'
             'une agence sérieuse de Sapa.</p>\n'
             '<h2>Quand partir ?</h2>\n'
             '<p>Septembre à novembre : rizières dorées, ciel dégagé. Mars–mai : verdure intense. '
             'Évitez la saison\n'
             'des pluies (juin–août) : sentiers boueux et brume fréquente.</p><p>Pour les '
             'adresses, hébergements et conseils détaillés sur place, consultez notre <a '
             'href="/sapa">guide complet Sapa</a>.</p>',
  'category_label': 'Itinéraires',
  'tags': ['Sapa', 'trek', 'rizières', 'montagne'],
  'image_alt': 'Trek à Sapa : rizières, villages et randonnées dans le Nord — Sapa, Vietnam'}]
