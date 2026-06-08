"""Chaînes d'interface FR/EN."""

from __future__ import annotations

from flask import g

from i18n_utils import DEFAULT_LANG, get_lang

UI: dict[str, dict[str, str]] = {
    # Navigation
    "nav.home": {"fr": "Accueil", "en": "Home"},
    "nav.destinations": {"fr": "Destinations", "en": "Destinations"},
    "nav.itineraries": {"fr": "Itinéraires", "en": "Itineraries"},
    "nav.blog": {"fr": "Blog", "en": "Blog"},
    "nav.about": {"fr": "À propos", "en": "About"},
    "nav.contact": {"fr": "Contact", "en": "Contact"},
    "nav.open_menu": {"fr": "Ouvrir le menu", "en": "Open menu"},
    "nav.close_menu": {"fr": "Fermer le menu", "en": "Close menu"},
    "nav.main": {"fr": "Navigation principale", "en": "Main navigation"},
    "nav.days": {"fr": "jours", "en": "days"},
    "lang.switch": {"fr": "English", "en": "Français"},
    "lang.label": {"fr": "Langue", "en": "Language"},
    "skip.main": {"fr": "Aller au contenu principal", "en": "Skip to main content"},
    "logo.home": {"fr": "— Accueil", "en": "— Home"},

    # Footer
    "footer.destinations": {"fr": "Destinations", "en": "Destinations"},
    "footer.itineraries_blog": {"fr": "Itinéraires & Blog", "en": "Itineraries & Blog"},
    "footer.all_articles": {"fr": "Tous les articles", "en": "All articles"},
    "footer.copyright": {
        "fr": "Site indépendant — non affilié à une agence de voyage.",
        "en": "Independent site — not affiliated with a travel agency.",
    },
    "footer.privacy": {"fr": "Confidentialité", "en": "Privacy"},
    "footer.legal": {"fr": "Mentions légales", "en": "Legal notice"},
    "footer.unsubscribe": {"fr": "Désinscription newsletter", "en": "Unsubscribe newsletter"},
    "footer.cookies": {"fr": "Cookies", "en": "Cookies"},
    "footer.legal_nav": {"fr": "Informations légales", "en": "Legal information"},

    # Homepage
    "home.hero.eyebrow": {"fr": "Guide voyage Vietnam", "en": "Vietnam travel guide"},
    "home.hero.title": {"fr": "Votre guide voyage", "en": "Your travel guide"},
    "home.hero.title_em": {"fr": "au Vietnam", "en": "to Vietnam"},
    "home.hero.lead": {
        "fr": "Itinéraires prêts à l'emploi, guides par ville, conseils visa et budget — pour préparer votre séjour au Vietnam en toute sérénité.",
        "en": "Ready-made itineraries, city guides, visa and budget tips — plan your Vietnam trip with confidence.",
    },
    "home.hero.cta_dest": {"fr": "Explorer les destinations", "en": "Explore destinations"},
    "home.hero.cta_pdf": {"fr": "Télécharger le guide PDF", "en": "Download the PDF guide"},
    "home.dest.title": {"fr": "Destinations au Vietnam", "en": "Destinations in Vietnam"},
    "home.dest.sub": {
        "fr": "Guides complets par ville : que faire, où dormir, activités incontournables",
        "en": "Complete city guides: what to do, where to stay, must-see activities",
    },
    "home.dest.cta": {"fr": "Lire le guide →", "en": "Read the guide →"},
    "home.itin.title": {"fr": "Itinéraires Vietnam", "en": "Vietnam itineraries"},
    "home.itin.sub": {
        "fr": "Circuits jour par jour — 3, 7 ou 10 jours pour organiser votre voyage",
        "en": "Day-by-day routes — 3, 7 or 10 days to plan your trip",
    },
    "home.itin.cta": {"fr": "Voir l'itinéraire →", "en": "View itinerary →"},
    "home.blog.title": {"fr": "Guides pratiques voyage Vietnam", "en": "Practical Vietnam travel guides"},
    "home.blog.sub": {
        "fr": "Visa, budget, eSIM, sécurité — conseils pour voyageurs français",
        "en": "Visa, budget, eSIM, safety — tips for travellers",
    },
    "home.blog.cta": {"fr": "Tous les articles", "en": "All articles"},

    # Blog
    "blog.title": {"fr": "Blog voyage Vietnam", "en": "Vietnam travel blog"},
    "blog.sub": {
        "fr": "Visa, budget, transport, gastronomie — articles pratiques pour préparer votre séjour",
        "en": "Visa, budget, transport, food — practical articles to plan your trip",
    },
    "blog.all_categories": {"fr": "Toutes les catégories", "en": "All categories"},
    "blog.filter_by": {"fr": "Filtrer par catégorie", "en": "Filter by category"},

    # Category
    "category.articles": {"fr": "articles", "en": "articles"},
    "category.empty": {
        "fr": "Aucun article dans cette catégorie pour le moment.",
        "en": "No articles in this category yet.",
    },
    "category.view": {"fr": "Voir la catégorie", "en": "View category"},

    # Préparer mon voyage
    "nav.prepare": {"fr": "Préparer mon voyage", "en": "Plan my trip"},
    "prepare.title": {"fr": "Préparer mon voyage au Vietnam", "en": "Plan my Vietnam trip"},
    "prepare.sub": {
        "fr": "Répondez à 3 questions — nous vous proposons itinéraires, guides et articles adaptés à votre profil.",
        "en": "Answer 3 questions — we'll suggest itineraries, guides and articles tailored to your profile.",
    },
    "prepare.hero.eyebrow": {"fr": "Trip planner", "en": "Trip planner"},
    "prepare.hero.stat1": {"fr": "3 questions", "en": "3 questions"},
    "prepare.hero.stat2": {"fr": "Sur mesure", "en": "Tailored"},
    "prepare.hero.stat3": {"fr": "100 % gratuit", "en": "100% free"},
    "prepare.step1": {"fr": "Qui voyage ?", "en": "Who is travelling?"},
    "prepare.step_hint": {
        "fr": "Sélectionnez une option pour débloquer l'étape suivante.",
        "en": "Select an option to unlock the next step.",
    },
    "prepare.step2": {"fr": "Quel type de voyage ?", "en": "What kind of trip?"},
    "prepare.step3": {"fr": "Quelle durée ?", "en": "How long?"},
    "prepare.next": {"fr": "Continuer", "en": "Continue"},
    "prepare.back": {"fr": "Retour", "en": "Back"},
    "prepare.restart": {"fr": "Recommencer", "en": "Start over"},
    "prepare.see_all": {"fr": "Voir tout", "en": "See all"},
    "prepare.group.solo": {"fr": "Solo", "en": "Solo"},
    "prepare.group.couple": {"fr": "En couple", "en": "As a couple"},
    "prepare.group.family": {"fr": "En famille", "en": "With family"},
    "prepare.group.friends": {"fr": "Entre amis", "en": "With friends"},
    "prepare.style.culture.label": {"fr": "Culture & patrimoine", "en": "Culture & heritage"},
    "prepare.style.culture.desc": {"fr": "Temples, histoire, musées et villes anciennes", "en": "Temples, history, museums and old towns"},
    "prepare.style.food.label": {"fr": "Gastronomie", "en": "Food & dining"},
    "prepare.style.food.desc": {"fr": "Street food, marchés et tables locales", "en": "Street food, markets and local restaurants"},
    "prepare.style.adventure.label": {"fr": "Aventure", "en": "Adventure"},
    "prepare.style.adventure.desc": {"fr": "Trek, baie d'Halong, delta du Mékong", "en": "Trekking, Halong Bay, Mekong Delta"},
    "prepare.style.romantic.label": {"fr": "Romantique", "en": "Romantic"},
    "prepare.style.romantic.desc": {"fr": "Hội An, plages, couchers de soleil", "en": "Hội An, beaches, sunsets"},
    "prepare.style.roadtrip.label": {"fr": "Road trip", "en": "Road trip"},
    "prepare.style.roadtrip.desc": {"fr": "Nord au Sud, trains et paysages", "en": "North to South, trains and scenery"},
    "prepare.style.relax.label": {"fr": "Détente", "en": "Relaxation"},
    "prepare.style.relax.desc": {"fr": "Plages, spa, rythme lent", "en": "Beaches, spa, slow pace"},
    "prepare.style.budget.label": {"fr": "Petit budget", "en": "Budget travel"},
    "prepare.style.budget.desc": {"fr": "Backpacker, astuces économiques", "en": "Backpacker, money-saving tips"},
    "prepare.duration.short": {"fr": "7 jours", "en": "7 days"},
    "prepare.duration.medium": {"fr": "10 jours", "en": "10 days"},
    "prepare.duration.long": {"fr": "14 jours et +", "en": "14+ days"},
    "prepare.results.title": {"fr": "Votre voyage sur mesure", "en": "Your tailored trip"},
    "prepare.results.sub": {
        "fr": "Voici tout ce que nous recommandons pour votre profil — itinéraires, destinations et guides.",
        "en": "Here's everything we recommend for your profile — itineraries, destinations and guides.",
    },
    "prepare.results.itineraries": {"fr": "Itinéraires recommandés", "en": "Recommended itineraries"},
    "prepare.results.destinations": {"fr": "Destinations à explorer", "en": "Destinations to explore"},
    "prepare.results.articles": {"fr": "Guides à lire", "en": "Guides to read"},
    "prepare.results.categories": {"fr": "Catégories du blog", "en": "Blog categories"},
    "prepare.results.pdf": {"fr": "Télécharger le guide PDF complet", "en": "Download the full PDF guide"},
    "prepare.results.empty": {
        "fr": "Sélectionnez vos préférences pour voir nos recommandations.",
        "en": "Select your preferences to see our recommendations.",
    },
    "meta.prepare.title": {
        "fr": "Préparer mon voyage au Vietnam — itinéraires sur mesure",
        "en": "Plan my Vietnam trip — tailored itineraries",
    },
    "meta.prepare.desc": {
        "fr": "Quiz voyage : nombre de personnes, type de séjour et durée — obtenez itinéraires, destinations et guides adaptés.",
        "en": "Trip quiz: group size, travel style and duration — get matching itineraries, destinations and guides.",
    },

    # Article
    "article.read_time": {"fr": "min de lecture", "en": "min read"},
    "article.new": {"fr": "Nouveau", "en": "New"},
    "article.related": {"fr": "Articles similaires", "en": "Related articles"},
    "article.updated": {"fr": "Mis à jour le", "en": "Updated on"},

    # Destination
    "dest.things": {"fr": "À faire", "en": "Things to do"},
    "dest.hotels": {"fr": "Où dormir", "en": "Where to stay"},
    "dest.activities": {"fr": "Activités & tours", "en": "Activities & tours"},
    "dest.gyg_widget.title": {
        "fr": "Plus d'activités à {city} sur GetYourGuide",
        "en": "More activities in {city} on GetYourGuide",
    },
    "dest.gyg_widget.sub": {
        "fr": "Sélection dynamique pour {city} — réservation et paiement sur GetYourGuide.",
        "en": "Live selection for {city} — book and pay on GetYourGuide.",
    },
    "dest.tips": {"fr": "Conseils pratiques", "en": "Practical tips"},
    "dest.book": {"fr": "Réserver", "en": "Book"},
    "dest.from": {"fr": "dès", "en": "from"},

    # Itinerary
    "itin.day": {"fr": "Jour", "en": "Day"},
    "itin.budget": {"fr": "Budget indicatif", "en": "Estimated budget"},
    "itin.hotel": {"fr": "Hôtel recommandé", "en": "Recommended hotel"},
    "itin.activity": {"fr": "Activité recommandée", "en": "Recommended activity"},
    "itin.stay": {"fr": "Nuit", "en": "Overnight"},

    # About
    "about.title": {"fr": "À propos", "en": "About us"},

    # 404
    "404.title": {"fr": "Page introuvable", "en": "Page not found"},
    "404.lead": {
        "fr": "Cette page n'existe pas ou a été déplacée.",
        "en": "This page does not exist or has been moved.",
    },
    "404.cta": {"fr": "Retour à l'accueil", "en": "Back to home"},

    # Newsletter
    "newsletter.consent": {
        "fr": "J'accepte de recevoir la newsletter et j'ai lu la",
        "en": "I agree to receive the newsletter and have read the",
    },
    "newsletter.privacy_link": {"fr": "politique de confidentialité", "en": "privacy policy"},

    # Newsletter flash
    "flash.consent": {
        "fr": "Veuillez accepter la politique de confidentialité pour vous inscrire.",
        "en": "Please accept the privacy policy to subscribe.",
    },
    "flash.subscribed": {
        "fr": "Merci ! Vous êtes inscrit à la newsletter.",
        "en": "Thank you! You are subscribed to the newsletter.",
    },
    "flash.already": {
        "fr": "Cette adresse est déjà inscrite.",
        "en": "This email is already subscribed.",
    },
    "flash.invalid_email": {
        "fr": "Veuillez entrer une adresse email valide.",
        "en": "Please enter a valid email address.",
    },

    # Unsubscribe
    "unsub.invalid": {
        "fr": "Lien de désinscription invalide ou expiré.",
        "en": "Invalid or expired unsubscribe link.",
    },
    "unsub.invalid_short": {
        "fr": "Lien de désinscription invalide.",
        "en": "Invalid unsubscribe link.",
    },
    "unsub.success": {
        "fr": "Vous êtes désinscrit de la newsletter.",
        "en": "You have been unsubscribed from the newsletter.",
    },
    "unsub.confirm_title": {
        "fr": "Se désinscrire de la newsletter",
        "en": "Unsubscribe from newsletter",
    },
    "unsub.incomplete": {
        "fr": "Lien incomplet. Utilisez le lien reçu par email ou contactez-nous.",
        "en": "Incomplete link. Use the link from your email or contact us.",
    },

    # Affiliates
    "aff.badge.hotel": {"fr": "Hébergement", "en": "Accommodation"},
    "aff.badge.activity": {"fr": "Réserver", "en": "Book"},
    "aff.badge.esim": {"fr": "eSIM", "en": "eSIM"},
    "aff.badge.insurance": {"fr": "Assurance", "en": "Insurance"},
    "aff.disclosure": {
        "fr": "Certains liens sont affiliés : nous pouvons percevoir une commission sans surcoût pour vous.",
        "en": "Some links are affiliate links: we may earn a commission at no extra cost to you.",
    },
    "aff.sim.title": {"fr": "Internet au Vietnam", "en": "Internet in Vietnam"},
    "aff.sim.lead": {
        "fr": "eSIM recommandée avant le départ — activation à l'atterrissage.",
        "en": "eSIM recommended before departure — activate on landing.",
    },
    "aff.pdf.cta": {"fr": "Obtenir le guide PDF", "en": "Get the PDF guide"},

    "pdf.error.payment": {
        "fr": "Le paiement n'est pas encore disponible. Réessayez plus tard ou contactez-nous.",
        "en": "Payment is not available yet. Please try again later or contact us.",
    },
    "pdf.success.meta_title": {
        "fr": "Merci — votre guide PDF",
        "en": "Thank you — your PDF guide",
    },
    "pdf.success.meta_desc": {
        "fr": "Téléchargez votre guide Vietnam PDF Inside Vietnam Travel.",
        "en": "Download your Inside Vietnam Travel Vietnam PDF guide.",
    },
    "pdf.success.title": {"fr": "Merci pour votre achat !", "en": "Thank you for your purchase!"},
    "pdf.success.lead": {
        "fr": "Votre guide PDF est prêt à télécharger.",
        "en": "Your PDF guide is ready to download.",
    },
    "pdf.success.body": {
        "fr": "Le guide inclut 3 itinéraires (7, 10 et 14 jours), les checklists visa/eSIM/assurance, un budget détaillé et des adresses testées.",
        "en": "The guide includes 3 itineraries (7, 10 and 14 days), visa/eSIM/insurance checklists, a detailed budget and tested addresses.",
    },
    "pdf.success.download": {"fr": "Télécharger le PDF", "en": "Download PDF"},
    "pdf.success.downloading": {"fr": "Téléchargement…", "en": "Downloading…"},
    "pdf.success.download_again": {"fr": "Télécharger à nouveau", "en": "Download again"},
    "pdf.success.downloaded": {
        "fr": "Guide téléchargé — vous pouvez le retrouver dans vos fichiers.",
        "en": "Guide downloaded — check your downloads folder.",
    },
    "pdf.success.stay": {
        "fr": "Cette page reste accessible : vous pouvez retélécharger votre guide à tout moment.",
        "en": "This page stays available — you can download your guide again anytime.",
    },
    "pdf.success.email_note": {
        "fr": "Un lien de téléchargement vous a aussi été envoyé par email si vous en avez indiqué un lors du paiement.",
        "en": "A download link was also emailed to you if you provided an address at checkout.",
    },
    "pdf.success.pending": {
        "fr": "Paiement en cours de validation. Actualisez cette page dans quelques instants.",
        "en": "Payment is being validated. Refresh this page in a moment.",
    },
    "pdf.success.back": {"fr": "← Retour à l'accueil", "en": "← Back to home"},

    # Cookies
    "cookie.title": {"fr": "Cookies & confidentialité", "en": "Cookies & privacy"},
    "cookie.lead": {
        "fr": "Nous utilisons des cookies pour mesurer l'audience (Google Analytics) et améliorer le site. Vous pouvez accepter ou refuser.",
        "en": "We use cookies to measure traffic (Google Analytics) and improve the site. You can accept or decline.",
    },
    "cookie.accept": {"fr": "Tout accepter", "en": "Accept all"},
    "cookie.reject": {"fr": "Refuser", "en": "Decline"},
    "cookie.settings": {"fr": "Personnaliser", "en": "Customize"},
    "cookie.analytics": {"fr": "Mesure d'audience", "en": "Analytics"},
    "cookie.save": {"fr": "Enregistrer", "en": "Save"},

    # Loader
    "loader.text": {"fr": "Chargement…", "en": "Loading…"},

    # SEO meta (pages statiques)
    "meta.home.title": {
        "fr": "Voyage Vietnam 2026 : guides, itinéraires et conseils pratiques",
        "en": "Vietnam travel 2026: guides, itineraries and practical tips",
    },
    "meta.home.desc": {
        "fr": "Préparez votre voyage au Vietnam : itinéraires 3 à 10 jours, guides Hanoï, Hội An, Saigon, visa, budget et conseils pour voyageurs français.",
        "en": "Plan your Vietnam trip: 3 to 10-day itineraries, Hanoi, Hội An, Saigon guides, visa, budget and travel tips.",
    },
    "meta.home.kw": {
        "fr": "voyage Vietnam, guide Vietnam, itinéraire Vietnam, préparer voyage Vietnam, voyageurs français",
        "en": "Vietnam travel, Vietnam guide, Vietnam itinerary, plan Vietnam trip, Vietnam travel tips",
    },
    "meta.blog.title": {
        "fr": "Blog voyage Vietnam : visa, budget, transport, gastronomie",
        "en": "Vietnam travel blog: visa, budget, transport, food",
    },
    "meta.blog.desc": {
        "fr": "Articles pratiques pour préparer un voyage au Vietnam : e-visa, budget au jour, eSIM, sécurité, transport et street food.",
        "en": "Practical articles to plan a Vietnam trip: e-visa, daily budget, eSIM, safety, transport and street food.",
    },
    "meta.blog.kw": {
        "fr": "blog voyage Vietnam, visa Vietnam, budget Vietnam, conseils voyage Vietnam",
        "en": "Vietnam travel blog, Vietnam visa, Vietnam budget, Vietnam travel tips",
    },
    "meta.about.title": {
        "fr": "À propos — guide voyage Vietnam indépendant",
        "en": "About — independent Vietnam travel guide",
    },
    "meta.about.desc": {
        "fr": "Inside Vietnam Travel : guide indépendant pour préparer votre voyage au Vietnam. Itinéraires, conseils pratiques et transparence sur les liens affiliés.",
        "en": "Inside Vietnam Travel: independent guide to plan your Vietnam trip. Itineraries, practical tips and affiliate transparency.",
    },
    "meta.privacy.title": {
        "fr": "Politique de confidentialité — Inside Vietnam Travel",
        "en": "Privacy policy — Inside Vietnam Travel",
    },
    "meta.privacy.desc": {
        "fr": "Données personnelles, cookies, newsletter et vos droits RGPD sur Inside Vietnam Travel.",
        "en": "Personal data, cookies, newsletter and your GDPR rights on Inside Vietnam Travel.",
    },
    "meta.legal.title": {
        "fr": "Mentions légales — Inside Vietnam Travel",
        "en": "Legal notice — Inside Vietnam Travel",
    },
    "meta.legal.desc": {
        "fr": "Éditeur, hébergeur et informations légales du site Inside Vietnam Travel.",
        "en": "Publisher, hosting and legal information for Inside Vietnam Travel.",
    },
    "meta.contact.title": {
        "fr": "Contact — Inside Vietnam Travel",
        "en": "Contact — Inside Vietnam Travel",
    },
    "meta.contact.desc": {
        "fr": "Contactez Inside Vietnam Travel pour toute question sur votre voyage au Vietnam.",
        "en": "Contact Inside Vietnam Travel for any question about your Vietnam trip.",
    },
    "contact.title": {"fr": "Nous contacter", "en": "Contact us"},
    "contact.lead": {
        "fr": "Une question sur votre voyage au Vietnam ? Écrivez-nous — nous répondons sous 48 h ouvrées.",
        "en": "A question about your Vietnam trip? Write to us — we reply within 48 business hours.",
    },
    "contact.name": {"fr": "Nom", "en": "Name"},
    "contact.email": {"fr": "Email", "en": "Email"},
    "contact.subject": {"fr": "Sujet", "en": "Subject"},
    "contact.message": {"fr": "Message", "en": "Message"},
    "contact.send": {"fr": "Envoyer le message", "en": "Send message"},
    "contact.consent": {
        "fr": "J'accepte que mes données soient utilisées pour répondre à ma demande (voir la",
        "en": "I agree that my data will be used to reply to my request (see",
    },
    "contact.success": {
        "fr": "Merci ! Votre message a bien été envoyé. Nous vous répondrons rapidement.",
        "en": "Thank you! Your message was sent. We will reply shortly.",
    },
    "contact.error": {
        "fr": "Impossible d'envoyer le message. Vérifiez les champs ou réessayez plus tard.",
        "en": "Could not send your message. Check the fields or try again later.",
    },
    "meta.404.title": {"fr": "Page introuvable", "en": "Page not found"},
    "meta.404.desc": {
        "fr": "Cette page n'existe pas. Retournez à l'accueil pour préparer votre voyage au Vietnam.",
        "en": "This page does not exist. Return home to plan your Vietnam trip.",
    },
    "meta.category.suffix": {
        "fr": "— guides pratiques voyage",
        "en": "— practical travel guides",
    },
    "meta.category.desc_extra": {
        "fr": "Conseils pour voyageurs français préparant un séjour au Vietnam.",
        "en": "Tips for travellers planning a trip to Vietnam.",
    },
    "meta.itin.kw": {
        "fr": "itinéraire Vietnam {days} jours, voyage Vietnam, circuit Vietnam",
        "en": "Vietnam itinerary {days} days, Vietnam travel, Vietnam tour",
    },
    "meta.dest.kw": {
        "fr": "guide {name}, voyage {name}, que faire {name}, Vietnam",
        "en": "{name} guide, travel {name}, things to do {name}, Vietnam",
    },
    "meta.article.desc_extra_fr": {
        "fr": "Guide pratique pour voyageurs français",
        "en": "Practical guide for travellers",
    },
}


def t(key: str, lang: str | None = None, **fmt: str) -> str:
    lang = lang or get_lang()
    entry = UI.get(key, {})
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, ValueError):
            return text
    return text


def ui_for_lang(lang: str) -> dict[str, str]:
    return {key: vals.get(lang, vals.get(DEFAULT_LANG, "")) for key, vals in UI.items()}
