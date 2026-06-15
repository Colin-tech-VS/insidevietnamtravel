"""Chaînes d'interface FR/EN."""

from __future__ import annotations

from flask import g

from i18n_utils import DEFAULT_LANG, get_lang

UI: dict[str, dict[str, str]] = {
    # Navigation
    "nav.home": {"fr": "Accueil", "en": "Home"},
    "nav.destinations": {"fr": "Destinations", "en": "Destinations"},
    "nav.destinations_all": {"fr": "Toutes les destinations", "en": "All destinations"},
    "nav.itineraries": {"fr": "Itinéraires", "en": "Itineraries"},
    "nav.guides": {"fr": "Guides", "en": "Guides"},
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
    "home.hero.search_label": {"fr": "Destination, itinéraire, article…", "en": "Destination, itinerary, article…"},
    "home.hero.search_btn": {"fr": "Rechercher sur le site", "en": "Search the site"},
    "home.hero.discover": {"fr": "Trouvez votre réponse", "en": "Find your answer"},
    "home.hero.or": {"fr": "ou", "en": "or"},
    "home.hero.mai_label": {"fr": "Posez votre question à Mai", "en": "Ask Mai your question"},
    "home.hero.mai_cta": {"fr": "Discuter avec Mai", "en": "Chat with Mai"},
    "home.dest.see_all": {"fr": "Voir toutes les destinations", "en": "See all destinations"},
    "home.itin.see_all": {"fr": "Voir tous les itinéraires", "en": "See all itineraries"},
    "home.partner.eyebrow": {"fr": "Programme partenaires", "en": "Partner program"},
    "home.partner.title": {"fr": "Devenir partenaire Inside Vietnam Travel", "en": "Become an Inside Vietnam Travel partner"},
    "home.partner.sub": {
        "fr": "Guides locaux, créateurs, blogueurs et agences — rejoignez notre réseau vérifié et bénéficiez d'une page dédiée, d'une visibilité éditoriale et d'opportunités de co-marketing.",
        "en": "Local guides, creators, bloggers and agencies — join our verified network with a dedicated page, editorial visibility and co-marketing opportunities.",
    },
    "home.partner.benefit1": {"fr": "Fiche partenaire gratuite", "en": "Free partner page"},
    "home.partner.benefit2": {"fr": "Validation éditoriale IA", "en": "AI editorial review"},
    "home.partner.benefit3": {"fr": "Espace partenaire dédié", "en": "Dedicated partner dashboard"},
    "home.partner.cta_apply": {"fr": "Candidater", "en": "Apply now"},
    "home.partner.cta_directory": {"fr": "Voir nos partenaires", "en": "Browse our partners"},
    "home.hero.stat_dest": {"fr": "guides destinations", "en": "destination guides"},
    "home.hero.stat_itin": {"fr": "itinéraires clés en main", "en": "ready-made itineraries"},
    "home.hero.stat_free": {"fr": "planificateur gratuit", "en": "free trip planner"},
    "home.hero.slide.halong": {"fr": "Baie d'Halong, Vietnam", "en": "Halong Bay, Vietnam"},
    "home.hero.slide.hoi_an": {"fr": "Hội An, ville ancienne", "en": "Hội An ancient town"},
    "home.hero.slide.hanoi": {"fr": "Hanoï, capitale du Vietnam", "en": "Hanoi, Vietnam capital"},
    "home.hero.showcase_label": {"fr": "Destinations à explorer", "en": "Destinations to explore"},
    "home.pillars.title": {"fr": "Par où commencer", "en": "Where to start"},
    "home.pillars.sub": {
        "fr": "Nos guides piliers pour préparer chaque facette de votre voyage au Vietnam",
        "en": "Our pillar guides to plan every part of your trip to Vietnam",
    },
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
        "fr": "Répondez à 5 questions — nous vous proposons itinéraires, guides et articles adaptés à votre profil.",
        "en": "Answer 5 questions — we'll suggest itineraries, guides and articles tailored to your profile.",
    },
    "prepare.hero.eyebrow": {"fr": "Trip planner", "en": "Trip planner"},
    "prepare.hero.stat1": {"fr": "5 questions", "en": "5 questions"},
    "prepare.hero.stat2": {"fr": "Sur mesure", "en": "Tailored"},
    "prepare.hero.stat3": {"fr": "100 % gratuit", "en": "100% free"},
    "prepare.step1": {"fr": "Qui voyage ?", "en": "Who is travelling?"},
    "prepare.step_hint": {
        "fr": "Sélectionnez une option pour débloquer l'étape suivante.",
        "en": "Select an option to unlock the next step.",
    },
    "prepare.step2": {"fr": "Combien de voyageurs ?", "en": "How many travellers?"},
    "prepare.step2_hint": {
        "fr": "Ajustez le nombre exact — sert à estimer le budget total du groupe.",
        "en": "Adjust the exact number — used to estimate your group's total budget.",
    },
    "prepare.step3": {"fr": "Quel type de voyage ?", "en": "What kind of trip?"},
    "prepare.step4": {"fr": "Quelle durée ?", "en": "How long?"},
    "prepare.step5": {"fr": "Où aller ?", "en": "Where to go?"},
    "prepare.step5_hint": {
        "fr": "Choisissez une ou plusieurs destinations (sélection multiple).",
        "en": "Pick one or more destinations (multiple choice).",
    },
    "prepare.next": {"fr": "Continuer", "en": "Continue"},
    "prepare.back": {"fr": "Retour", "en": "Back"},
    "prepare.restart": {"fr": "Recommencer", "en": "Start over"},
    "prepare.see_all": {"fr": "Voir tout", "en": "See all"},
    "prepare.group.solo": {"fr": "Solo", "en": "Solo"},
    "prepare.group.couple": {"fr": "En couple", "en": "As a couple"},
    "prepare.group.family": {"fr": "En famille", "en": "With family"},
    "prepare.group.friends": {"fr": "Entre amis", "en": "With friends"},
    "prepare.group.solo.hint": {"fr": "Voyageur solo", "en": "Solo traveller"},
    "prepare.group.couple.hint": {"fr": "2 voyageurs", "en": "2 travellers"},
    "prepare.group.family.hint": {"fr": "Famille (souvent 3–5 pers.)", "en": "Family (often 3–5 people)"},
    "prepare.group.friends.hint": {"fr": "Groupe d'amis", "en": "Group of friends"},
    "prepare.travelers.decrease": {"fr": "Retirer un voyageur", "en": "Remove one traveller"},
    "prepare.travelers.increase": {"fr": "Ajouter un voyageur", "en": "Add one traveller"},
    "prepare.results.summary": {"fr": "Votre profil", "en": "Your profile"},
    "prepare.results.back": {"fr": "Modifier mes réponses", "en": "Edit my answers"},
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
    "prepare.view_results": {"fr": "Voir mes résultats", "en": "See my results"},
    "prepare.gate.title": {
        "fr": "Dernière étape : votre email",
        "en": "Last step: your email",
    },
    "prepare.gate.sub": {
        "fr": "Entrez votre adresse pour débloquer votre programme sur mesure. "
              "Vous serez aussi inscrit(e) à notre newsletter (conseils voyage Vietnam, désinscription en un clic).",
        "en": "Enter your address to unlock your tailored trip plan. "
              "You'll also be subscribed to our newsletter (Vietnam travel tips, one-click unsubscribe).",
    },
    "prepare.gate.cta": {"fr": "Voir mon programme", "en": "View my trip plan"},
    "prepare.gate.free_note": {
        "fr": "Aperçu gratuit instantané : budget estimé, itinéraires et conseils sur mesure.",
        "en": "Instant free preview: estimated budget, itineraries and tailored tips.",
    },
    "prepare.gate.pdf_hint": {
        "fr": "Ensuite, option guide PDF complet ({price}) — checklists imprimables et itinéraires jour par jour.",
        "en": "Then, optional full PDF guide ({price}) — printable checklists and day-by-day itineraries.",
    },
    "prepare.pdf.eyebrow": {"fr": "Guide PDF premium", "en": "Premium PDF guide"},
    "prepare.pdf.title": {
        "fr": "Passez à la vitesse supérieure",
        "en": "Take it to the next level",
    },
    "prepare.pdf.sub": {
        "fr": "Votre aperçu gratuit est un excellent départ. Le guide PDF ajoute les détails jour par jour, "
              "les checklists à imprimer et les adresses testées.",
        "en": "Your free preview is a great start. The PDF guide adds day-by-day details, "
              "printable checklists and tested addresses.",
    },
    "prepare.pdf.cta": {
        "fr": "Obtenir le guide — {price}",
        "en": "Get the guide — {price}",
    },
    "prepare.gate.privacy": {
        "fr": "Pas de spam. Désinscription en un clic.",
        "en": "No spam. Unsubscribe in one click.",
    },
    "prepare.gate.error": {
        "fr": "Une erreur est survenue. Réessayez dans un instant.",
        "en": "Something went wrong. Please try again in a moment.",
    },
    "prepare.gate.loading": {
        "fr": "Génération de votre programme…",
        "en": "Building your trip plan…",
    },

    # Piliers SEO (hubs thématiques)
    "pillar.soon": {"fr": "Bientôt", "en": "Coming soon"},
    "pillar.part_of": {"fr": "Ce guide fait partie de", "en": "Part of the guide"},
    "pillar.related_destinations": {"fr": "Destinations associées", "en": "Related destinations"},
    "pillar.faq": {"fr": "Questions fréquentes", "en": "Frequently asked questions"},
    "pillar.related": {"fr": "Guides liés", "en": "Related guides"},
    "pillar.cta.title": {
        "fr": "Prêt à passer à l'action ?",
        "en": "Ready to take the next step?",
    },
    "pillar.cta.text": {
        "fr": "Répondez à 4 questions et obtenez un itinéraire et des guides adaptés à votre voyage.",
        "en": "Answer 4 questions and get an itinerary and guides tailored to your trip.",
    },
    "prepare.region.north": {"fr": "Nord", "en": "North"},
    "prepare.region.central": {"fr": "Centre", "en": "Central"},
    "prepare.region.south": {"fr": "Sud", "en": "South"},
    "prepare.results.budget": {"fr": "Budget estimé", "en": "Estimated budget"},
    "prepare.results.tips": {"fr": "Conseils pour votre profil", "en": "Tips for your profile"},
    "prepare.results.recos": {"fr": "Nos recommandations", "en": "Our recommendations"},
    "prepare.budget.perperson": {"fr": "par personne", "en": "per person"},
    "prepare.budget.group": {"fr": "pour le groupe", "en": "for the group"},
    "prepare.budget.persons": {"fr": "pers.", "en": "ppl"},
    "prepare.budget.daily": {"fr": "Coûts sur place", "en": "On-the-ground costs"},
    "prepare.budget.oneoff": {"fr": "Frais ponctuels", "en": "One-off costs"},
    "prepare.budget.intercity": {"fr": "Transport inter-villes", "en": "Inter-city transport"},
    "prepare.budget.total": {"fr": "Total estimé", "en": "Estimated total"},
    "prepare.budget.note": {
        "fr": "Estimation indicative hors vols internationaux ; varie selon la saison et vos réservations.",
        "en": "Indicative estimate excluding international flights; varies by season and your bookings.",
    },
    "prepare.reco.hotels": {"fr": "Hébergement", "en": "Accommodation"},
    "prepare.reco.hotels_desc": {
        "fr": "Hôtels et auberges aux meilleurs prix dans vos villes.",
        "en": "Best-priced hotels and hostels in your chosen cities.",
    },
    "prepare.reco.activities": {"fr": "Activités & excursions", "en": "Tours & activities"},
    "prepare.reco.activities_desc": {
        "fr": "Visites guidées, croisières et expériences à réserver à l'avance.",
        "en": "Guided tours, cruises and experiences to book ahead.",
    },
    "prepare.reco.esim": {"fr": "Carte SIM / eSIM", "en": "SIM card / eSIM"},
    "prepare.reco.esim_desc": {
        "fr": "Restez connecté dès l'arrivée, sans frais d'itinérance.",
        "en": "Stay connected on arrival, with no roaming fees.",
    },
    "prepare.reco.insurance": {"fr": "Assurance voyage", "en": "Travel insurance"},
    "prepare.reco.insurance_desc": {
        "fr": "Frais médicaux, rapatriement et activités à risque couverts.",
        "en": "Medical costs, repatriation and adventure activities covered.",
    },
    "prepare.reco.view": {"fr": "Voir", "en": "View"},
    "prepare.reco.disclosure": {
        "fr": "Liens partenaires — sans surcoût pour vous, ils soutiennent le site.",
        "en": "Affiliate links — at no extra cost to you, they support the site.",
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
    "article.by": {"fr": "Par", "en": "By"},
    "article.updated": {"fr": "Mis à jour le", "en": "Updated on"},
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
    "dest.viator_widget.title": {
        "fr": "Plus d'activités à {city} sur Viator",
        "en": "More activities in {city} on Viator",
    },
    "dest.viator_widget.sub": {
        "fr": "Tours et excursions pour {city} — réservation sur Viator (8 % commission affilié).",
        "en": "Tours and experiences in {city} — book on Viator (8% affiliate commission).",
    },
    "dest.tips": {"fr": "Conseils pratiques", "en": "Practical tips"},
    "dest.book": {"fr": "Réserver", "en": "Book"},
    "dest.from": {"fr": "dès", "en": "from"},

    # Itinerary
    "itin.day": {"fr": "Jour", "en": "Day"},
    "itin.budget": {"fr": "Budget indicatif", "en": "Estimated budget"},
    "itin.hotel": {"fr": "Hôtel recommandé", "en": "Recommended hotel"},
    "itin.book": {"fr": "Réserver", "en": "Book"},
    "itin.gallery": {"fr": "Aperçu du circuit", "en": "Route preview"},
    "itin.best_season": {"fr": "Meilleure période", "en": "Best season"},
    "itin.includes": {"fr": "Ce circuit comprend", "en": "This route includes"},
    "itin.practical": {"fr": "Infos pratiques", "en": "Practical info"},
    "itin.activity": {"fr": "Activité recommandée", "en": "Recommended activity"},
    "itin.stay": {"fr": "Nuit", "en": "Overnight"},
    "itin.highlights": {"fr": "Étapes du circuit", "en": "Route highlights"},
    "itin.experiences": {"fr": "Expériences du voyage", "en": "Trip highlights"},
    "itin.faq": {"fr": "Questions fréquentes", "en": "Frequently asked questions"},
    "itin.bookings": {"fr": "Réservations par région", "en": "Bookings by region"},
    "itin.guide.title": {
        "fr": "Télécharger le guide PDF complet",
        "en": "Download the full PDF guide",
    },
    "itin.guide.sub": {
        "fr": "Programme jour par jour imprimable — inscription newsletter gratuite (pas de compte).",
        "en": "Printable day-by-day programme — free newsletter signup (no account).",
    },
    "itin.guide.cta": {"fr": "Recevoir le PDF", "en": "Get the PDF"},
    "itin.guide.success": {
        "fr": "Merci ! Votre guide PDF se télécharge — vous êtes inscrit(e) à la newsletter.",
        "en": "Thanks! Your PDF guide is downloading — you're subscribed to the newsletter.",
    },

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
    "aff.hotel.see_on": {"fr": "Voir sur {provider}", "en": "See on {provider}"},
    "aff.hotel.search_title": {
        "fr": "Rechercher {name} à {city} sur {provider}",
        "en": "Search {name} in {city} on {provider}",
    },
    "aff.activity.book_title": {
        "fr": "Réserver {name} à {city}",
        "en": "Book {name} in {city}",
    },
    "aff.sim.aria": {"fr": "Offre eSIM Vietnam", "en": "Vietnam eSIM offer"},
    "aff.insurance.aria": {"fr": "Assurance voyage", "en": "Travel insurance"},
    "aff.transport.aria": {"fr": "Réservation transport Vietnam", "en": "Vietnam transport booking"},
    "aff.visa.aria": {"fr": "E-visa Vietnam en ligne", "en": "Vietnam e-visa online"},
    "aff.insurance.eyebrow": {"fr": "Protection", "en": "Protection"},
    "aff.insurance.title": {
        "fr": "Assurance voyage Vietnam",
        "en": "Vietnam travel insurance",
    },
    "aff.insurance.text": {
        "fr": "Frais médicaux, rapatriement, annulation — indispensable pour voyager l'esprit tranquille.",
        "en": "Medical fees, repatriation, cancellation — essential for worry-free travel.",
    },
    "aff.insurance.cta": {
        "fr": "Devis assurance Vietnam",
        "en": "Get an insurance quote",
    },
    "aff.pdf.aria": {"fr": "Guide PDF Vietnam", "en": "Vietnam PDF guide"},
    "aff.pdf.eyebrow": {"fr": "Produit numérique", "en": "Digital product"},
    "breadcrumb.aria": {"fr": "Fil d'Ariane", "en": "Breadcrumb"},

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
        "fr": "Nous utilisons des cookies pour mesurer l'audience, mémoriser vos préférences de voyage "
              "et améliorer le site. Vous pouvez accepter ou personnaliser.",
        "en": "We use cookies to measure traffic, remember your travel preferences "
              "and improve the site. You can accept or customize.",
    },
    "cookie.accept": {"fr": "Tout accepter", "en": "Accept all"},
    "cookie.reject": {"fr": "Refuser", "en": "Decline"},
    "cookie.settings": {"fr": "Personnaliser", "en": "Customize"},
    "cookie.analytics": {"fr": "Mesure d'audience", "en": "Analytics"},
    "cookie.personalization": {"fr": "Expérience personnalisée", "en": "Personalized experience"},
    "cookie.personalization_desc": {
        "fr": "Mémorise vos destinations consultées, votre profil voyage (durée, style) et adapte "
              "Mai et les recommandations — cookie ivt_vp, sans compte.",
        "en": "Remembers destinations viewed, your trip profile (length, style) and adapts "
              "Mai and recommendations — ivt_vp cookie, no account.",
    },
    "cookie.save": {"fr": "Enregistrer", "en": "Save"},

    # Profil visiteur (UI)
    "profile.summary_default": {
        "fr": "Voyageur curieux du Vietnam",
        "en": "Curious Vietnam traveller",
    },
    "profile.for_you": {"fr": "Pour vous", "en": "For you"},
    "profile.for_you_sub": {
        "fr": "Suggestions basées sur votre navigation et vos préférences (cookie local, sans compte).",
        "en": "Suggestions based on your browsing and preferences (local cookie, no account).",
    },
    "profile.continue": {"fr": "Reprendre votre exploration", "en": "Continue exploring"},
    "profile.destinations": {"fr": "Destinations pour vous", "en": "Destinations for you"},
    "profile.partners": {"fr": "Partenaires pour vous", "en": "Partners for you"},
    "profile.itineraries": {"fr": "Itinéraires adaptés", "en": "Matching itineraries"},
    "profile.tools": {"fr": "Outils utiles pour votre profil", "en": "Tools for your profile"},
    "profile.prepare_cta": {"fr": "Affiner mon profil voyage", "en": "Refine my trip profile"},

    "chat.suggest_visa": {"fr": "Ai-je besoin d'un visa ?", "en": "Do I need a visa?"},
    "chat.suggest_season": {"fr": "Quelle est la meilleure saison ?", "en": "What's the best season?"},
    "chat.suggest_budget": {"fr": "Quel budget prévoir ?", "en": "What budget should I plan?"},
    "chat.suggest_safety": {"fr": "Quelles arnaques éviter ?", "en": "What scams should I avoid?"},

    # Loader
    "loader.text": {"fr": "Chargement…", "en": "Loading…"},
    "loader.hint": {
        "fr": "Préparation de votre voyage…",
        "en": "Preparing your trip…",
    },
    "loader.aria": {"fr": "Chargement en cours", "en": "Loading"},

    # SEO meta (pages statiques)
    "meta.destinations.title": {
        "fr": "Destinations Vietnam — guides complets par ville",
        "en": "Vietnam destinations — complete city guides",
    },
    "meta.destinations.desc": {
        "fr": "Toutes nos destinations au Vietnam : guides par ville, que faire, où dormir et activités incontournables — Nord, Centre et Sud.",
        "en": "All our Vietnam destinations: city guides, what to do, where to stay and must-see activities — North, Central and South.",
    },
    "meta.destinations.kw": {
        "fr": "destinations Vietnam, guide voyage Vietnam, villes Vietnam, Hanoi, Hoi An, Halong",
        "en": "Vietnam destinations, Vietnam travel guide, Vietnam cities, Hanoi, Hoi An, Halong",
    },
    "destinations.page.title": {"fr": "Toutes les destinations au Vietnam", "en": "All destinations in Vietnam"},
    "destinations.page.sub": {
        "fr": "Guides complets par ville et par région — que faire, où dormir, activités incontournables",
        "en": "Complete guides by city and region — what to do, where to stay, must-see activities",
    },
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

    # ── Navigation : outils ──────────────────────────────────────────
    "nav.tools": {"fr": "Outils", "en": "Tools"},
    "tools.season": {"fr": "Quand partir", "en": "Best time to go"},
    "tools.budget": {"fr": "Calculateur de budget", "en": "Budget calculator"},
    "tools.visa": {"fr": "Visa Vietnam", "en": "Vietnam visa"},
    "tools.essentials": {"fr": "eSIM & assurance", "en": "eSIM & insurance"},
    "tools.apps": {"fr": "Applications utiles", "en": "Useful apps"},
    "tools.safety": {"fr": "Sécurité & arnaques", "en": "Safety & scams"},
    "tools.customs": {"fr": "Coutumes", "en": "Customs"},
    "tools.phrases": {"fr": "Phrases vietnamiennes", "en": "Vietnamese phrases"},
    "tools.events": {"fr": "Événements & festivals", "en": "Events & festivals"},
    "footer.tools": {"fr": "Outils voyage", "en": "Travel tools"},

    # ── Page Applications utiles ─────────────────────────────────────────
    "apps.eyebrow": {"fr": "Guide pratique", "en": "Practical guide"},
    "apps.title": {
        "fr": "Applications indispensables pour voyager au Vietnam",
        "en": "Essential apps for travelling in Vietnam",
    },
    "apps.lead": {
        "fr": "Notre sélection d'applications pour vous débrouiller seul au Vietnam — et "
              "surtout éviter les arnaques au taxi, au change et aux billets « gonflés ».",
        "en": "Our pick of apps to get around Vietnam on your own — and above all avoid "
              "taxi, exchange and inflated-ticket scams.",
    },
    "apps.why": {"fr": "Pourquoi", "en": "Why"},
    "apps.open": {"fr": "Ouvrir", "en": "Open"},
    "apps.get": {"fr": "Obtenir l'app", "en": "Get the app"},
    "apps.badge.essential": {"fr": "Indispensable", "en": "Must-have"},
    "apps.badge.affiliate": {"fr": "Partenaire", "en": "Partner"},
    "apps.badge.free": {"fr": "Gratuit", "en": "Free"},
    "apps.faq": {"fr": "Questions fréquentes", "en": "Frequently asked questions"},
    "apps.disclosure": {
        "fr": "Certains liens sont des liens partenaires : nous pouvons toucher une "
              "commission sans surcoût pour vous. Cela n'influence pas notre sélection.",
        "en": "Some links are partner links: we may earn a commission at no extra cost to "
              "you. It does not influence our selection.",
    },

    # ── Recherche ────────────────────────────────────────────────────
    "search.label": {"fr": "Rechercher", "en": "Search"},
    "search.open": {"fr": "Ouvrir la recherche", "en": "Open search"},
    "search.close": {"fr": "Fermer la recherche", "en": "Close search"},
    "search.placeholder": {
        "fr": "Destination, hôtel, activité, itinéraire…",
        "en": "Destination, hotel, activity, itinerary…",
    },
    "search.bar": {
        "fr": "Rechercher",
        "en": "Search",
    },
    "search.hint": {
        "fr": "Tapez pour trouver une destination, un hôtel, une activité, un guide ou un outil.",
        "en": "Type to find a destination, hotel, activity, guide or tool.",
    },
    "search.empty": {
        "fr": "Aucun résultat — essayez « Hanoï », « food tour » ou « budget ».",
        "en": "No result — try “Hanoi”, “food tour” or “budget”.",
    },
    "search.group.destination": {"fr": "Destinations", "en": "Destinations"},
    "search.group.itinerary": {"fr": "Itinéraires", "en": "Itineraries"},
    "search.group.hotel": {"fr": "Hôtels", "en": "Hotels"},
    "search.group.activity": {"fr": "Activités & tours", "en": "Activities & tours"},
    "search.group.article": {"fr": "Articles", "en": "Articles"},
    "search.group.tool": {"fr": "Outils", "en": "Tools"},

    # ── Chat IA (Mai) ────────────────────────────────────────────────
    "chat.name": {"fr": "Mai — conseillère Vietnam", "en": "Mai — Vietnam advisor"},
    "chat.subtitle": {
        "fr": "Votre guide indépendant au Vietnam",
        "en": "Your independent Vietnam travel guide",
    },
    "chat.open": {"fr": "Discuter avec Mai", "en": "Chat with Mai"},
    "chat.close": {"fr": "Fermer le chat", "en": "Close chat"},
    "chat.send": {"fr": "Envoyer", "en": "Send"},
    "chat.placeholder": {
        "fr": "Posez votre question sur le Vietnam…",
        "en": "Ask anything about Vietnam…",
    },
    "chat.greeting": {
        "fr": "Xin chào ! 👋 Je suis Mai, votre conseillère voyage chez Inside Vietnam Travel. "
              "Itinéraires, **visa**, **budget**, gastronomie… je connais tout le site et je suis là pour "
              "vous donner envie — et les **bons plans** — pour votre aventure au **Vietnam** ! 🇻🇳✨",
        "en": "Xin chào! 👋 I'm Mai, your travel advisor at Inside Vietnam Travel. "
              "Itineraries, **visa**, **budget**, food… I know every page on the site and I'm here to "
              "inspire your **Vietnam** adventure with **practical tips**! 🇻🇳✨",
    },
    "chat.typing": {"fr": "Mai réfléchit…", "en": "Mai is thinking…"},
    "chat.error": {
        "fr": "Oups, je n'ai pas pu répondre. Réessayez dans un instant.",
        "en": "Sorry, I couldn't reply. Please try again in a moment.",
    },
    "chat.affiliate_badge": {"fr": "Partenaire", "en": "Partner"},
    "chat.links_site": {"fr": "À lire sur le site", "en": "Read on the site"},
    "chat.links_partner": {"fr": "Bons plans partenaires", "en": "Partner picks"},
    "chat.map_subtitle": {"fr": "Carte interactive", "en": "Interactive map"},
    "chat.map_cta": {"fr": "Voir la carte complète", "en": "View full map"},
    "chat.map_on": {"fr": "Sur la carte", "en": "On the map"},
    "chat.map_error": {"fr": "Carte indisponible", "en": "Map unavailable"},
    "chat.photo_credit_site": {"fr": "Inside Vietnam Travel", "en": "Inside Vietnam Travel"},
    "chat.photo_credit_web": {"fr": "Pixabay", "en": "Pixabay"},
    "chat.resize": {
        "fr": "Redimensionner le chat — glisser le coin ou double-clic pour réinitialiser",
        "en": "Resize chat — drag corner or double-click to reset",
    },
    "chat.resize_reset": {"fr": "Taille réinitialisée", "en": "Size reset"},
    "chat.disclaimer": {
        "fr": "Conseils IA à titre informatif — vérifiez visa & santé auprès des sources officielles.",
        "en": "AI tips for guidance only — check visa & health with official sources.",
    },
    "chat.suggest1": {
        "fr": "Que faire 10 jours au Vietnam ?",
        "en": "What to do in 10 days in Vietnam?",
    },
    "chat.suggest2": {
        "fr": "Quelle est la meilleure saison ?",
        "en": "What's the best season to visit?",
    },
    "chat.suggest3": {
        "fr": "Comment préparer mon visa ?",
        "en": "How do I prepare my visa?",
    },

    # ── Filtres blog ─────────────────────────────────────────────────
    "blog.filter.all": {"fr": "Tout", "en": "All"},
    "blog.filter.label": {"fr": "Filtrer par thème", "en": "Filter by topic"},
    "blog.filter.none": {
        "fr": "Aucun article pour ce filtre.",
        "en": "No article for this filter.",
    },
    "blog.readtime": {"fr": "min de lecture", "en": "min read"},

    # ── Quand partir ─────────────────────────────────────────────────
    "season.eyebrow": {"fr": "Météo & saisons", "en": "Weather & seasons"},
    "season.title": {"fr": "Quand partir au Vietnam ?", "en": "When to visit Vietnam?"},
    "season.lead": {
        "fr": "Le Vietnam s'étire sur 1 700 km et compte trois climats distincts. "
              "Repérez la meilleure période région par région avant de réserver.",
        "en": "Vietnam stretches over 1,700 km across three distinct climates. "
              "Find the best period region by region before you book.",
    },
    "season.matrix_title": {"fr": "Calendrier des saisons", "en": "Season calendar"},
    "season.matrix_sub": {
        "fr": "Pertinence mois par mois pour chaque grande région.",
        "en": "Month-by-month suitability for each main region.",
    },
    "season.region": {"fr": "Région", "en": "Region"},
    "season.best": {"fr": "Meilleure période", "en": "Best period"},
    "season.tip_title": {"fr": "Le bon réflexe", "en": "Smart tip"},
    "season.tip": {
        "fr": "Un même voyage traverse souvent plusieurs climats. Suivez la saison "
              "sèche du nord au sud (oct.–avr.) pour maximiser le beau temps.",
        "en": "A single trip often crosses several climates. Follow the dry season "
              "from north to south (Oct–Apr) to maximise good weather.",
    },
    "season.planner_title": {
        "fr": "Planificateur météo personnalisé",
        "en": "Personal weather planner",
    },
    "season.planner_sub": {
        "fr": "Sélectionnez vos destinations et un mois de voyage pour voir si c'est "
              "une bonne période (idéal, correct ou à éviter).",
        "en": "Pick your destinations and travel month to see if it's a good time "
              "(ideal, fair or avoid).",
    },
    "season.planner_month": {"fr": "Mois de voyage", "en": "Travel month"},
    "season.planner_dest": {"fr": "Destinations", "en": "Destinations"},
    "season.planner_result": {"fr": "Verdict pour votre trip", "en": "Verdict for your trip"},
    "season.planner_pick": {
        "fr": "Choisissez au moins une destination et un mois.",
        "en": "Choose at least one destination and a month.",
    },
    "season.planner_ideal": {
        "fr": "Excellente période pour votre sélection !",
        "en": "Excellent timing for your selection!",
    },
    "season.planner_good": {
        "fr": "Bonne période — météo généralement favorable.",
        "en": "Good period — weather usually favourable.",
    },
    "season.planner_fair": {
        "fr": "Période correcte — prévoyez pluie ou chaleur selon la région.",
        "en": "Fair period — expect rain or heat depending on the region.",
    },
    "season.planner_avoid": {
        "fr": "Période difficile pour au moins une destination — envisagez de décaler.",
        "en": "Tricky period for at least one destination — consider shifting dates.",
    },
    "season.destinations_title": {
        "fr": "Météo ville par ville",
        "en": "Weather city by city",
    },

    # ── Calculateur de budget ────────────────────────────────────────
    "budget.eyebrow": {"fr": "Budget voyage", "en": "Trip budget"},
    "budget.title": {"fr": "Calculateur de budget Vietnam", "en": "Vietnam budget calculator"},
    "budget.lead": {
        "fr": "Estimez un budget détaillé : style, régions, repas, transports, activités "
              "et change EUR → dong en temps réel. Hors vol international.",
        "en": "Estimate a detailed budget: style, regions, meals, transport, activities "
              "and live EUR → dong exchange. Excluding international flights.",
    },
    "budget.style": {"fr": "Style de voyage", "en": "Travel style"},
    "budget.trip_params": {"fr": "Votre voyage", "en": "Your trip"},
    "budget.travellers": {"fr": "Voyageurs", "en": "Travellers"},
    "budget.days": {"fr": "Durée (jours)", "en": "Duration (days)"},
    "budget.cities": {"fr": "Villes visitées", "en": "Cities visited"},
    "budget.internal_flights": {"fr": "Vols intérieurs", "en": "Domestic flights"},
    "budget.scooter_days": {"fr": "Jours scooter", "en": "Scooter days"},
    "budget.guide_days": {"fr": "Jours guide privé", "en": "Private guide days"},
    "budget.refine": {"fr": "Affiner l'estimation", "en": "Fine-tune estimate"},
    "budget.region": {"fr": "Région principale", "en": "Main region"},
    "budget.meals": {"fr": "Niveau repas", "en": "Meal level"},
    "budget.transport_mode": {"fr": "Déplacements", "en": "Getting around"},
    "budget.activity_level": {"fr": "Niveau activités", "en": "Activity level"},
    "budget.currency": {"fr": "Affichage", "en": "Display"},
    "budget.currency_both": {"fr": "EUR + dong (₫)", "en": "EUR + dong (₫)"},
    "budget.fx_label": {"fr": "Taux de change", "en": "Exchange rate"},
    "budget.fx_loading": {"fr": "Chargement des taux…", "en": "Loading rates…"},
    "budget.fx_updated": {"fr": "Taux du jour (source open.er-api.com)", "en": "Today's rate (open.er-api.com)"},
    "budget.vnd": {"fr": "dong vietnamien", "en": "Vietnamese dong"},
    "budget.intercity": {"fr": "Inter-villes / pers.", "en": "Inter-city / person"},
    "budget.oneoff_selected": {"fr": "Frais ponctuels sélectionnés", "en": "Selected one-off costs"},
    "budget.internal_flight_line": {"fr": "Vols intérieurs", "en": "Domestic flights"},
    "budget.scooter_line": {"fr": "Location scooter", "en": "Scooter rental"},
    "budget.guide_line": {"fr": "Guide privé", "en": "Private guide"},
    "budget.flight_note": {
        "fr": "Vol international Europe ↔ Vietnam non inclus (souvent 500–900 € A/R).",
        "en": "International flights Europe ↔ Vietnam not included (often €500–900 return).",
    },
    "budget.perday": {"fr": "par jour / pers.", "en": "per day / person"},
    "budget.breakdown": {"fr": "Détail par poste (jour)", "en": "Daily cost breakdown"},
    "budget.daily_total": {"fr": "Sous-total journalier", "en": "Daily subtotal"},
    "budget.oneoff": {"fr": "Options ponctuelles", "en": "One-off options"},
    "budget.total": {"fr": "Budget total estimé", "en": "Estimated total budget"},
    "budget.per_person": {"fr": "par personne", "en": "per person"},
    "budget.note": {
        "fr": "Estimation indicative en euros avec conversion dong (taux actualisé ~1 h). "
              "Les prix varient selon la saison, les réservations et le change.",
        "en": "Indicative estimate in euros with dong conversion (rates refreshed ~hourly). "
              "Prices vary by season, bookings and exchange rates.",
    },
    "budget.cta_book": {"fr": "Voir les hôtels recommandés", "en": "See recommended hotels"},
    "budget.cta_prepare": {"fr": "Affiner avec le planificateur", "en": "Refine with trip planner"},

    # ── Visa ─────────────────────────────────────────────────────────
    "visa.eyebrow": {"fr": "Formalités", "en": "Formalities"},
    "visa.title": {"fr": "Avez-vous besoin d'un visa ?", "en": "Do you need a visa?"},
    "visa.lead": {
        "fr": "Indiquez votre nationalité et la durée de votre séjour pour savoir "
              "si l'e-visa est nécessaire.",
        "en": "Enter your nationality and trip length to find out whether the "
              "e-visa is required.",
    },
    "visa.q_country": {"fr": "Votre nationalité", "en": "Your nationality"},
    "visa.q_days": {"fr": "Durée du séjour (jours)", "en": "Length of stay (days)"},
    "visa.check": {"fr": "Vérifier", "en": "Check"},
    "visa.result.exempt": {
        "fr": "Bonne nouvelle : vous êtes exempté de visa jusqu'à {days} jours.",
        "en": "Good news: you are visa-exempt for up to {days} days.",
    },
    "visa.result.exempt_over": {
        "fr": "Exemption jusqu'à {days} jours, mais votre séjour est plus long : "
              "demandez un e-visa (jusqu'à 90 jours).",
        "en": "Exempt up to {days} days, but your stay is longer: apply for an "
              "e-visa (up to 90 days).",
    },
    "visa.result.evisa": {
        "fr": "Un e-visa est nécessaire. Demande 100 % en ligne, ≈ 25 $, "
              "délai 3 à 5 jours ouvrés.",
        "en": "An e-visa is required. Fully online application, ≈ $25, "
              "3 to 5 business days.",
    },
    "visa.result.over90": {
        "fr": "Au-delà de 90 jours, l'e-visa ne suffit pas : passez par un visa "
              "consulaire classique.",
        "en": "Beyond 90 days the e-visa is not enough: apply for a standard "
              "consular visa.",
    },
    "visa.apply": {"fr": "Site officiel e-visa", "en": "Official e-visa site"},
    "visa.steps_title": {"fr": "Demander l'e-visa en 4 étapes", "en": "Apply for the e-visa in 4 steps"},
    "visa.disclaimer": {
        "fr": "Information indicative — les règles de visa évoluent. Vérifiez toujours "
              "le portail officiel evisa.gov.vn avant de réserver.",
        "en": "Indicative information — visa rules change. Always check the official "
              "evisa.gov.vn portal before booking.",
    },
    "visa.faq_title": {"fr": "Questions fréquentes visa", "en": "Visa FAQ"},
    "visa.guide_title": {"fr": "Tout savoir sur le visa Vietnam", "en": "Vietnam visa essentials"},

    # ── Sécurité voyage ──────────────────────────────────────────────
    "safety.nav": {"fr": "Sécurité & conseils", "en": "Safety & tips"},
    "safety.eyebrow": {"fr": "Voyage serein", "en": "Travel safely"},
    "safety.title": {
        "fr": "Sécurité au Vietnam : arnaques, santé & numéros utiles",
        "en": "Safety in Vietnam: scams, health & emergency numbers",
    },
    "safety.lead": {
        "fr": "Le Vietnam est globalement sûr pour les touristes. Voici les arnaques "
              "courantes à connaître, les réflexes santé/vaccins, l'assurance, l'eSIM "
              "et qui contacter en cas de problème.",
        "en": "Vietnam is generally safe for tourists. Common scams, health & vaccine "
              "tips, insurance, eSIM and who to contact if something goes wrong.",
    },
    "safety.cta_title": {"fr": "Évitez les arnaques au quotidien", "en": "Avoid everyday scams"},
    "safety.cta_text": {
        "fr": "Grab, Maps, conversion de devises : notre guide apps pour voyager sans mauvaise surprise.",
        "en": "Grab, Maps, currency conversion: our apps guide to travel without nasty surprises.",
    },

    # ── Coutumes ─────────────────────────────────────────────────────
    "customs.nav": {"fr": "Coutumes & étiquette", "en": "Customs & etiquette"},
    "customs.eyebrow": {"fr": "Respect & culture", "en": "Respect & culture"},
    "customs.title": {
        "fr": "Coutumes au Vietnam : ce qu'il faut savoir",
        "en": "Vietnamese customs: what you should know",
    },
    "customs.lead": {
        "fr": "Salutations, temples, table, négociation : les bons gestes pour voyager "
              "respectueusement et être bien accueilli.",
        "en": "Greetings, temples, dining, bargaining: the right gestures to travel "
              "respectfully and be welcomed.",
    },
    "customs.cta_title": {"fr": "Parlez quelques mots de vietnamien", "en": "Speak a few words of Vietnamese"},
    "customs.cta_text": {
        "fr": "Xin chào, cảm ơn, bao nhiêu ? — notre guide de phrases FR→vietnamien et EN→vietnamien.",
        "en": "Xin chào, cảm ơn, bao nhiêu? — our FR→Vietnamese and EN→Vietnamese phrase guide.",
    },

    # ── Phrases vietnamiennes ────────────────────────────────────────
    "phrases.nav": {"fr": "Phrases utiles", "en": "Useful phrases"},
    "phrases.eyebrow": {"fr": "Survival vietnamien", "en": "Vietnamese survival kit"},
    "phrases.title": {
        "fr": "Phrases utiles en vietnamien (FR & EN → vietnamien)",
        "en": "Useful Vietnamese phrases (FR & EN → Vietnamese)",
    },
    "phrases.lead": {
        "fr": "Salutations, transport, restaurant, urgences : l'essentiel à prononcer "
              "avec translittération pour vous débrouiller sur place.",
        "en": "Greetings, transport, dining, emergencies: essentials with "
              "pronunciation to get by on the ground.",
    },
    "phrases.col_source": {"fr": "Français / English", "en": "French / English"},
    "phrases.col_vi": {"fr": "Vietnamien", "en": "Vietnamese"},
    "phrases.col_pron": {"fr": "Prononciation", "en": "Pronunciation"},
    "phrases.listen": {"fr": "Écouter la prononciation", "en": "Listen to pronunciation"},
    "phrases.listen_stop": {"fr": "Arrêter la lecture", "en": "Stop playback"},
    "phrases.audio_hint": {
        "fr": "Cliquez sur l'icône haut-parleur pour entendre la prononciation en vietnamien.",
        "en": "Tap the speaker icon to hear the Vietnamese pronunciation.",
    },
    "phrases.audio_error": {
        "fr": "Audio indisponible — réessayez dans un instant.",
        "en": "Audio unavailable — please try again in a moment.",
    },

    # ── Comparateurs ─────────────────────────────────────────────────
    "compare.eyebrow": {"fr": "Avant de partir", "en": "Before you go"},
    "compare.title": {"fr": "eSIM & assurance pour le Vietnam", "en": "eSIM & insurance for Vietnam"},
    "compare.lead": {
        "fr": "Restez connecté dès l'atterrissage et voyagez couvert. Notre comparatif "
              "des solutions les plus utilisées.",
        "en": "Stay connected on landing and travel covered. Our comparison of the "
              "most-used options.",
    },
    "compare.esim_title": {"fr": "Quelle eSIM choisir ?", "en": "Which eSIM to choose?"},
    "compare.col_offer": {"fr": "Offre", "en": "Provider"},
    "compare.col_best": {"fr": "Idéal pour", "en": "Best for"},
    "compare.col_price": {"fr": "Prix", "en": "Price"},
    "compare.col_data": {"fr": "Data", "en": "Data"},
    "compare.col_validity": {"fr": "Validité", "en": "Validity"},
    "compare.col_pros": {"fr": "Points forts", "en": "Pros"},
    "compare.col_cons": {"fr": "Limites", "en": "Cons"},
    "compare.see_offer": {"fr": "Voir l'offre", "en": "See offer"},
    "compare.insurance_title": {"fr": "Assurance voyage : l'essentiel", "en": "Travel insurance: the essentials"},
    "compare.insurance_cta": {"fr": "Comparer les assurances", "en": "Compare insurance plans"},

    # ── Avis voyageurs ───────────────────────────────────────────────
    "reviews.title": {"fr": "Ils ont préparé leur voyage avec nous", "en": "They planned their trip with us"},
    "reviews.sub": {
        "fr": "Retours de voyageurs ayant utilisé nos guides et itinéraires.",
        "en": "Feedback from travellers who used our guides and itineraries.",
    },

    # ── Meta des nouvelles pages ─────────────────────────────────────
    "meta.season.title": {
        "fr": "Quand partir au Vietnam ? Météo et meilleure saison par région 2026",
        "en": "When to visit Vietnam? Weather and best season by region 2026",
    },
    "meta.season.desc": {
        "fr": "Meilleure période pour voyager au Vietnam région par région : nord, "
              "centre, sud. Calendrier des saisons, météo et conseils mois par mois.",
        "en": "Best time to travel to Vietnam region by region: north, central, "
              "south. Season calendar, weather and month-by-month advice.",
    },
    "meta.budget.title": {
        "fr": "Calculateur de budget voyage Vietnam 2026 — estimez votre coût",
        "en": "Vietnam travel budget calculator 2026 — estimate your cost",
    },
    "meta.budget.desc": {
        "fr": "Calculez le budget de votre voyage au Vietnam selon votre style et la "
              "durée : hébergement, repas, transport, activités. Estimation gratuite.",
        "en": "Calculate your Vietnam trip budget by style and duration: "
              "accommodation, food, transport, activities. Free estimate.",
    },
    "meta.visa.title": {
        "fr": "Visa Vietnam 2026 — avez-vous besoin d'un visa ? Test en ligne",
        "en": "Vietnam visa 2026 — do you need a visa? Online checker",
    },
    "meta.visa.desc": {
        "fr": "Vérifiez en 10 secondes si vous avez besoin d'un visa pour le Vietnam "
              "selon votre nationalité, et comment demander l'e-visa étape par étape.",
        "en": "Check in 10 seconds whether you need a visa for Vietnam based on your "
              "nationality, and how to apply for the e-visa step by step.",
    },
    "meta.essentials.title": {
        "fr": "eSIM & assurance voyage Vietnam 2026 — comparatif",
        "en": "Vietnam eSIM & travel insurance 2026 — comparison",
    },
    "meta.essentials.desc": {
        "fr": "Comparez les eSIM (Airalo, Holafly) et choisissez votre assurance "
              "voyage pour le Vietnam : data, prix, validité et garanties.",
        "en": "Compare eSIMs (Airalo, Holafly) and choose your travel insurance for "
              "Vietnam: data, price, validity and cover.",
    },
    "meta.apps.title": {
        "fr": "Applications utiles au Vietnam (2026) — Grab & anti-arnaque",
        "en": "Useful apps for Vietnam (2026) — Grab & anti-scam",
    },
    "meta.apps.desc": {
        "fr": "Les applications indispensables pour voyager au Vietnam sans se faire "
              "arnaquer : Grab, Google Maps, XE, Google Translate, eSIM et plus.",
        "en": "The essential apps to travel Vietnam without getting scammed: Grab, "
              "Google Maps, XE, Google Translate, eSIM and more.",
    },
    "meta.safety.title": {
        "fr": "Sécurité Vietnam 2026 — arnaques, santé, assurance, numéros d'urgence",
        "en": "Vietnam safety 2026 — scams, health, insurance, emergency numbers",
    },
    "meta.safety.desc": {
        "fr": "Guide sécurité Vietnam : arnaques taxi et change, vaccins, assurance "
              "voyage, eSIM, numéros d'urgence et consulats. Conseils pratiques 2026.",
        "en": "Vietnam safety guide: taxi & exchange scams, vaccines, travel insurance, "
              "eSIM, emergency numbers and consulates. Practical 2026 tips.",
    },
    "meta.safety.kw": {
        "fr": "sécurité Vietnam, arnaques Vietnam, santé voyage Vietnam, vaccins Vietnam",
        "en": "Vietnam safety, Vietnam scams, Vietnam travel health, Vietnam vaccines",
    },
    "meta.customs.title": {
        "fr": "Coutumes Vietnam — étiquette, temples, repas & tabous",
        "en": "Vietnam customs — etiquette, temples, dining & taboos",
    },
    "meta.customs.desc": {
        "fr": "Coutumes et étiquette au Vietnam : salutations, tenue dans les temples, "
              "baguettes, pourboires, négociation et gestes à éviter.",
        "en": "Customs and etiquette in Vietnam: greetings, temple dress, chopsticks, "
              "tipping, bargaining and gestures to avoid.",
    },
    "meta.customs.kw": {
        "fr": "coutumes Vietnam, étiquette Vietnam, respect Vietnam voyage",
        "en": "Vietnam customs, Vietnam etiquette, Vietnam travel respect",
    },
    "meta.phrases.title": {
        "fr": "Phrases utiles vietnamien — guide prononciation FR & EN",
        "en": "Useful Vietnamese phrases — FR & EN pronunciation guide",
    },
    "meta.phrases.desc": {
        "fr": "Lexique voyage vietnamien : bonjour, merci, transport, restaurant, "
              "urgences avec translittération pour francophones et anglophones.",
        "en": "Vietnamese travel phrasebook: hello, thanks, transport, dining, "
              "emergencies with pronunciation for French and English speakers.",
    },
    "meta.phrases.kw": {
        "fr": "phrases vietnamien, parler vietnamien voyage, vocabulaire Vietnam",
        "en": "Vietnamese phrases, learn Vietnamese travel, Vietnam vocabulary",
    },
    "events.nav": {"fr": "Événements Vietnam", "en": "Vietnam events"},
    "events.eyebrow": {"fr": "Calendrier culturel", "en": "Cultural calendar"},
    "events.title": {
        "fr": "Événements & festivals au Vietnam (2026–2027)",
        "en": "Vietnam events & festivals (2026–2027)",
    },
    "events.lead": {
        "fr": "Têt, fêtes lunaires, festivals régionaux et rendez-vous incontournables — "
              "dates, lieux et conseils pratiques pour planifier votre voyage.",
        "en": "Tết, lunar festivals, regional celebrations and unmissable dates — "
              "when, where and how to plan your trip around them.",
    },
    "events.season_label": {"fr": "Saison", "en": "Season"},
    "events.filter_title": {"fr": "Filtrer le calendrier", "en": "Filter the calendar"},
    "events.filter_sub": {
        "fr": "Par année, mois ou type d'événement. Affichez uniquement ce qui reste à venir.",
        "en": "By year, month or event type. Show upcoming events only.",
    },
    "events.filter_year": {"fr": "Année", "en": "Year"},
    "events.filter_month": {"fr": "Mois", "en": "Month"},
    "events.filter_category": {"fr": "Catégorie", "en": "Category"},
    "events.filter_upcoming": {"fr": "À venir uniquement", "en": "Upcoming only"},
    "events.filter_all": {"fr": "Tous", "en": "All"},
    "events.filter_none": {
        "fr": "Aucun événement ne correspond à ces filtres.",
        "en": "No events match these filters.",
    },
    "events.filter_count": {
        "fr": "{n} événement(s) affiché(s)",
        "en": "{n} event(s) shown",
    },
    "events.stat_total": {"fr": "Événements listés", "en": "Events listed"},
    "events.stat_upcoming": {"fr": "À venir ou en cours", "en": "Upcoming or ongoing"},
    "events.stat_must_see": {"fr": "Incontournables", "en": "Must-see"},
    "events.highlights_title": {"fr": "Les incontournables", "en": "Must-see highlights"},
    "events.highlights_sub": {
        "fr": "Les rendez-vous culturels les plus marquants de la saison.",
        "en": "The most memorable cultural dates of the season.",
    },
    "events.timeline_title": {"fr": "Calendrier détaillé", "en": "Full calendar"},
    "events.timeline_sub": {
        "fr": "Dates solaires confirmées pour 2026–2027 ; certaines éditions (Hue Festival, DIFF) "
              "peuvent être ajustées par les autorités locales.",
        "en": "Confirmed solar dates for 2026–2027; some editions (Hue Festival, DIFF) may be "
              "adjusted by local authorities.",
    },
    "events.must_see": {"fr": "Incontournable", "en": "Must-see"},
    "events.status_upcoming": {"fr": "À venir", "en": "Upcoming"},
    "events.status_ongoing": {"fr": "En cours", "en": "Ongoing"},
    "events.status_past": {"fr": "Passé", "en": "Past"},
    "events.status_recurring": {"fr": "Récurrent", "en": "Recurring"},
    "events.regions": {"fr": "Régions", "en": "Regions"},
    "events.tip_label": {"fr": "Conseil", "en": "Tip"},
    "events.section_highlights": {"fr": "À ne pas manquer", "en": "Highlights"},
    "events.section_detail": {"fr": "En détail", "en": "In detail"},
    "events.section_practical": {"fr": "Infos pratiques", "en": "Practical info"},
    "events.section_meta": {"fr": "Où & quand", "en": "Where & when"},
    "events.destinations_label": {"fr": "Destinations liées", "en": "Related destinations"},
    "events.year_label": {"fr": "Année", "en": "Year"},
    "events.view_event": {"fr": "Voir la fiche", "en": "View details"},
    "events.close_modal": {"fr": "Fermer", "en": "Close"},
    "events.modal_aria": {"fr": "Détail de l'événement", "en": "Event details"},
    "events.hoi_an_title": {
        "fr": "Hội An — pleines lunes & lanternes flottantes",
        "en": "Hội An — full moons & floating lanterns",
    },
    "events.hoi_an_sub": {
        "fr": "Le 14e jour de chaque mois lunaire : festival des lanternes sur la rivière Thu Bồn.",
        "en": "On the 14th lunar day each month: lantern festival on the Thu Bồn River.",
    },
    "events.hoi_an_note": {
        "fr": "La vieille ville est illuminée chaque soir ; ces dates sont les soirées les plus "
              "spectaculaires.",
        "en": "The old town is lit every evening; these are the most spectacular nights.",
    },
    "events.tip_title": {
        "fr": "Planifier autour d'un festival",
        "en": "Plan around a festival",
    },
    "events.tip_body": {
        "fr": "Réservez transport et hébergement 2–3 mois à l'avance pour le Têt et les longs "
              "week-ends. Croisez avec notre guide « Quand partir » pour le climat.",
        "en": "Book transport and stays 2–3 months ahead for Tết and long weekends. Cross-check "
              "with our best-time guide for weather.",
    },
    "events.cat.national": {"fr": "Fête nationale", "en": "National holiday"},
    "events.cat.culture": {"fr": "Culture & tradition", "en": "Culture & tradition"},
    "events.cat.religious": {"fr": "Religieux & spirituel", "en": "Religious & spiritual"},
    "events.cat.local": {"fr": "Local & régional", "en": "Local & regional"},
    "events.cat.recurring": {"fr": "Récurrent", "en": "Recurring"},
    "events.region.north": {"fr": "Nord", "en": "North"},
    "events.region.central": {"fr": "Centre", "en": "Central"},
    "events.region.south": {"fr": "Sud", "en": "South"},
    "events.region.mekong": {"fr": "Delta du Mékong", "en": "Mekong Delta"},
    "events.region.nationwide": {"fr": "Tout le pays", "en": "Nationwide"},
    "events.month.1": {"fr": "Janvier", "en": "January"},
    "events.month.2": {"fr": "Février", "en": "February"},
    "events.month.3": {"fr": "Mars", "en": "March"},
    "events.month.4": {"fr": "Avril", "en": "April"},
    "events.month.5": {"fr": "Mai", "en": "May"},
    "events.month.6": {"fr": "Juin", "en": "June"},
    "events.month.7": {"fr": "Juillet", "en": "July"},
    "events.month.8": {"fr": "Août", "en": "August"},
    "events.month.9": {"fr": "Septembre", "en": "September"},
    "events.month.10": {"fr": "Octobre", "en": "October"},
    "events.month.11": {"fr": "Novembre", "en": "November"},
    "events.month.12": {"fr": "Décembre", "en": "December"},
    "meta.events.title": {
        "fr": "Événements Vietnam 2026–2027 — Têt, festivals & calendrier lunaire",
        "en": "Vietnam events 2026–2027 — Tết, festivals & lunar calendar",
    },
    "meta.events.desc": {
        "fr": "Calendrier des festivals et événements au Vietnam : Nouvel An lunaire, Hội An, "
              "Huế, Cham, Mékong. Dates 2026–2027 et conseils voyage.",
        "en": "Vietnam festival calendar: Lunar New Year, Hội An, Huế, Cham, Mekong. "
              "2026–2027 dates and travel tips.",
    },
    "meta.events.kw": {
        "fr": "événements Vietnam, Têt 2026, festivals Vietnam, calendrier Vietnam voyage",
        "en": "Vietnam events, Tết 2026, Vietnam festivals, Vietnam travel calendar",
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
