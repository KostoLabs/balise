"""Corpus local : passages réels extraits des centres ressources publics.

Chaque passage est cité tel quel depuis la page du centre (extractions
vérifiées au 17/09/2026). Le corpus garantit les réponses aux questions
fréquentes ; la recherche live complète pour tout le reste. Sources = mêmes
ressources, jamais de rédaction maison.
"""

# key: (titre, centre, url, mots-clés de routing, [passages])
CORPUS = {
    "savs": {
        "titre": "Qu'est-ce qu'un service d'accompagnement à la vie sociale (SAVS) ?",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/logement/quest-ce-quun-service-daccompagnement-la-vie-sociale-savs",
        "kws": ["savs", "service d'accompagnement à la vie sociale", "accompagnement social adulte", "vie sociale"],
        "passages": [
            "Un service d'accompagnement à la vie sociale (SAVS) a pour mission de maintenir ou restaurer les liens familiaux, sociaux, scolaires, universitaires et professionnels des personnes en situation de handicap. Un SAVS facilite également l'accès à l'ensemble des services proposés par la collectivité.",
            "Un SAVS apporte : un accompagnement social et un apprentissage à l'autonomie ; une assistance ou une aide dans la réalisation et l'apprentissage des actes de la vie quotidienne et sociale (santé, alimentation, démarches administratives, aide à la gestion du budget, déplacements, loisirs, sports, etc.) ; un appui et un accompagnement contribuant à l'insertion scolaire, universitaire et professionnelle ou favorisant le maintien de cette insertion ; un suivi éducatif et psychologique.",
            "Un service d'accompagnement à la vie sociale (SAVS) s'adresse aux personnes en situation de handicap âgées de plus de 20 ans (voire 16 ou 18 ans selon l'agrément du service), vivant à domicile y compris en habitat intermédiaire comme un habitat inclusif.",
            "Pour bénéficier d'un accompagnement par un SAVS, vous devez être reconnu handicapé, avoir entre 20 ans et 60 ans au moment de la demande (voire plus de 60 ans si le handicap a été reconnu avant cet âge), et bénéficier d'une décision d'orientation vers un service d'accompagnement à la vie sociale, prononcée par la commission des droits et de l'autonomie des personnes handicapées (CDAPH) de la maison départementale des personnes handicapées (MDPH).",
            "Si vous remplissez les conditions pour bénéficier d'un SAVS, vous n'avez rien à payer. L'accompagnement d'un SAVS est intégralement financé par le conseil départemental.",
        ],
    },
    "samsah": {
        "titre": "SAMSAH : Service d'accompagnement médico-social pour adultes handicapés",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/glossaire/samsah",
        "kws": ["samsah", "médico-social pour adultes", "soins coordonnés", "accompagnement médical"],
        "passages": [
            "Le service d'accompagnement médico-social pour adultes handicapés (SAMSAH) est un dispositif médico-social destiné aux personnes adultes en situation de handicap.",
            "Il contribue à la réalisation du projet de vie par un accompagnement adapté favorisant les liens familiaux, sociaux, scolaires, universitaires ou professionnels.",
            "Le SAMSAH apporte une assistance ou un accompagnement des actes essentiels de la vie quotidienne des personnes en situation de handicap, comme une aide à la toilette.",
            "Le SAMSAH partage des missions identiques à celles du SAVS et dispense, en plus, selon les besoins de chaque personne, des soins réguliers et coordonnés, ainsi qu'un accompagnement et un suivi médical et paramédical en milieu ordinaire de vie.",
            "Le SAMSAH accompagne ses bénéficiaires sur décision de la Commission des droits et de l'autonomie des personnes handicapées (CDAPH). Aucune participation financière n'est demandée. Le coût de ce dispositif est financé par l'Assurance Maladie et le département.",
        ],
    },
    "mdph": {
        "titre": "La Maison départementale des personnes handicapées (MDPH) : missions et fonctionnement",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/aides/la-maison-departementale-des-personnes-handicapees-mdph-missions-et-fonctionnement",
        "kws": ["mdph", "maison départementale", "guichet unique", "première demande", "dossier"],
        "passages": [
            "La maison départementale des personnes handicapées (MDPH) est un guichet unique dont la mission est d'informer et d'accompagner les personnes en situation de handicap et leurs familles. C'est l'endroit où sont examinées les demandes de prestations et d'orientation : prestations financières, orientation en établissement ou service, aménagements de scolarité.",
            "L'équipe pluridisciplinaire de la MDPH évalue les besoins de la personne sur la base du dossier (volet médical, projet de vie) puis la commission des droits et de l'autonomie des personnes handicapées (CDAPH) prend la décision.",
        ],
    },
    "mdph_dossier": {
        "titre": "Le dépôt du dossier et le traitement de la demande par la MDPH",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/aides/le-depot-du-dossier-et-le-traitement-de-la-demande-par-la-maison-departementale-des-personnes",
        "kws": ["dossier", "dépôt", "cerfa", "volet médical", "projet de vie", "délai", "recours"],
        "passages": [
            "La demande se fait via le formulaire Cerfa n° 15692*01 accompagné d'éléments médicaux. Le dossier peut être déposé en ligne sur mdphenligne.cnsa.fr, par courrier ou au guichet de la MDPH.",
            "Le projet de vie est un document dans lequel la personne décrit son quotidien, ses difficultés et ses attentes. Il aide l'équipe pluridisciplinaire à comprendre la situation au-delà du volet médical.",
        ],
    },
    "pch": {
        "titre": "Prestation de compensation du handicap (PCH)",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/glossaire/pch",
        "kws": ["pch", "prestation de compensation", "aide humaine", "aide technique", "aménagement"],
        "passages": [
            "La prestation de compensation du handicap (PCH) est une aide financière destinée à financer les besoins liés à la perte d'autonomie des personnes handicapées : aides humaine, technique, animalière, ou encore l'aménagement du logement ou du véhicule.",
        ],
    },
    "cdaph": {
        "titre": "CDAPH : Commission des droits et de l'autonomie des personnes handicapées",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/glossaire/cdaph",
        "kws": ["cdaph", "commission", "décision", "orientation"],
        "passages": [
            "La commission des droits et de l'autonomie des personnes handicapées (CDAPH) est la commission au sein de la MDPH qui prend les décisions : attribution de prestations, orientation vers un établissement ou service, aménagements.",
        ],
    },
    "aeeh": {
        "titre": "Allocation d'éducation de l'enfant handicapé (AEEH)",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/glossaire/aeeh",
        "kws": ["aeeh", "allocation", "enfant", "éducation"],
        "passages": [
            "L'allocation d'éducation de l'enfant handicapé (AEEH) est une aide financière versée aux parents d'un enfant en situation de handicap, destinée à compenser les dépenses liées à son éducation et à son accompagnement.",
        ],
    },
    "esms": {
        "titre": "Des établissements et services médico-sociaux (ESMS) pour vous aider, vous orienter, vous former",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/aides/des-etablissements-et-services-medico-sociaux-pour-vous-aider-vous-orienter-vous-former-et",
        "kws": ["esms", "établissement", "service médico-social", "ime", "foyer", "esat"],
        "passages": [
            "Les établissements et services médico-sociaux (ESMS) sont les structures qui accueillent ou accompagnent les personnes en situation de handicap : établissements pour enfants (IME, ITEP), services d'accompagnement à domicile (SESSAD, SAVS, SAMSAH), établissements pour adultes (foyer, MAS, FAM, ESAT). L'accès se fait sur orientation de la CDAPH, sur décision de la MDPH.",
        ],
    },
    "ime": {
        "titre": "Comment s'effectue la scolarisation en établissement médico-social (EMS) ?",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/scolarite/comment-seeffectue-la-scolarisation-en-etablissement-medico-social-ems",
        "kws": ["ime", "institut médico-éducatif", "scolarisation", "établissement médico-social", "orientation"],
        "passages": [
            "L'institut médico-éducatif (IME) accueille des enfants et adolescents en situation de handicap, en général avec une déficience intellectuelle, et assure à la fois l'éducation, les soins et la scolarité adaptée.",
            "L'orientation en IME est prononcée par la CDAPH de la MDPH, qui précise le type d'établissement, le rythme d'accueil (internat, semi-internat) et la durée de la mesure.",
        ],
    },
    "rqth": {
        "titre": "Reconnaissance de la qualité de travailleur handicapé (RQTH)",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/glossaire/rqth",
        "kws": ["rqth", "travailleur handicapé", "emploi", "reconnaissance"],
        "passages": [
            "La reconnaissance de la qualité de travailleur handicapé (RQTH) est une protection officielle pour travailler. Elle est attribuée par la CDAPH de la MDPH et permet de bénéficier d'aménagements de poste, de l'obligation d'emploi, et de l'accès aux dispositifs dédiés (Cap emploi, Ésat).",
        ],
    },
    "pco": {
        "titre": "Plateforme de coordination et d'orientation (PCO) dans les troubles du neurodéveloppement",
        "centre": "GNCRA — centres ressources autisme",
        "url": "https://maisondelautisme.gouv.fr/fiches-pratiques-autisme/pco-autisme/",
        "kws": ["pco", "plateforme coordination", "neurodéveloppement", "précoce", "tnd", "avant diagnostic", "enfant"],
        "passages": [
            "Une plateforme de coordination et d'orientation (PCO) est un dispositif public. Elle organise le parcours des enfants présentant un écart de développement, avant tout diagnostic posé, pour les enfants qui n'ont pas encore de diagnostic de trouble du neurodéveloppement et ne bénéficient pas déjà d'aides de la MDPH pour financer des soins.",
            "Vous observez un écart de développement chez votre enfant ou un professionnel vous a parlé d'une PCO ? Un retard ou une différence observée ne signifie pas forcément qu'il s'agit d'un trouble du neurodéveloppement. En revanche, ces signes justifient toujours de demander un avis médical.",
            "Les PCO occupent une place centrale dans la Stratégie nationale 2023-2027 pour les troubles du neurodéveloppement. Cette stratégie a pour objectif de repérer plus précocement, de rendre les parcours plus souples, de réduire les délais de prise en charge et d'améliorer la coordination entre les secteurs médical, social et scolaire.",
        ],
    },
    "autisme": {
        "titre": "Qu'est-ce que l'autisme ?",
        "centre": "GNCRA — centres ressources autisme",
        "url": "https://maisondelautisme.gouv.fr/qu-est-ce-que-l-autisme/",
        "kws": ["autisme", "tsa", "trouble du spectre", "tnd", "neurodéveloppement"],
        "passages": [
            "L'autisme, ou trouble du spectre de l'autisme (TSA), est un trouble du neurodéveloppement. Il se caractérise par des différences de communication et d'interaction sociale, ainsi que par des centres d'intérêt ou comportements restreints et répétitifs.",
            "Le trouble du spectre de l'autisme fait partie des troubles du neurodéveloppement (TND), comme le TDAH ou les troubles dys.",
        ],
    },
    "sla": {
        "titre": "Sclérose latérale amyotrophique — protocole national de diagnostic et de soins",
        "centre": "HAS — Haute Autorité de Santé",
        "url": "https://www.has-sante.fr/jcms/c_2573383/fr/sclerose-laterale-amyotrophique",
        "kws": [
            "maladie de Charcot",
            "sclérose latérale amyotrophique",
            "sla",
            "maladie du motoneurone",
            "pnds",
            "centre de référence",
        ],
        "passages": [
            "Ce protocole national de diagnostic et de soins (PNDS) explicite aux professionnels concernés la prise en charge diagnostique et thérapeutique optimale et le parcours de soins d’un patient atteint de Sclérose latérale amyotrophique. Il a été élaboré par le centre de référence SLA à l’aide d’une méthodologie proposée par la HAS. Il n’a pas fait l’objet d’une validation par la HAS qui n’a pas participé à son élaboration.",
        ],
    },
    "conge_aidant": {
        "titre": "Congé de proche aidant",
        "centre": "Service-Public.fr",
        "url": "https://www.service-public.gouv.fr/particuliers/vosdroits/F16920",
        "kws": ["aidant", "congé", "proche aidant", "répit", "droits aidant", "salarié"],
        "passages": [
            "Le congé de proche aidant permet au salarié de s'occuper d'une personne handicapée ou âgée ou en perte d'autonomie. Il permet au salarié de cesser temporairement son activité professionnelle pour s'occuper d'une personne handicapée ou invalide ou âgée.",
            "Le congé de proche aidant remplace le congé de soutien familial depuis 2017.",
        ],
    },
    "pcpe": {
        "titre": "PCPE, Pôle de compétences et de prestations externalisées",
        "centre": "handicap.gouv.fr",
        "url": "https://handicap.gouv.fr/pcpe-pole-de-competences-et-de-prestations-externalisees",
        "kws": ["pcpe", "pôle de compétences", "prestations externalisées", "sans solution", "rupture de parcours", "plan d'intervention"],
        "passages": [
            "Suscités en 2016 à la suite du rapport de Denis Piveteau « Zéro sans solution », les Pôles de compétences et de prestations externalisées (PCPE) sont devenus un outil essentiel pour l'accompagnement des personnes handicapées.",
            "Aujourd'hui, on compte plus d'une centaine de PCPE sur l'ensemble du territoire national. Ces pôles permettent de prévenir les ruptures de parcours, à tout âge, en organisant un accompagnement adapté aux besoins des personnes.",
            "Il s'agit d'un dispositif souple, adaptable et innovant qui permet d'apporter une réponse ajustée aux besoins les plus complexes, en proposant aux personnes des plans d'interventions individualisées qui exigent la coordination d'une pluralité d'intervenants.",
            "Ce dispositif, à nouveau mis à l'honneur par la Stratégie nationale pour l'autisme au sein des troubles du neuro-développement, est une des briques de la transformation de l'offre.",
        ],
    },
    "annuaire_mdph": {
        "titre": "Annuaire des Maisons départementales des personnes handicapées (MDPH)",
        "centre": "Annuaire du service public",
        "url": "https://lannuaire.service-public.gouv.fr/navigation/maison_handicapees",
        "kws": ["contacts", "près de chez", "interlocuteurs", "annuaire", "qui contacter", "coordonnées", "guichet", "mes contacts", "nord", "meus", "loire", "contact"],
        "passages": [
            "Chaque département dispose d'une Maison départementale des personnes handicapées (MDPH) : guichet unique pour déposer le dossier, faire évaluer la situation et obtenir les décisions de la CDAPH. L'annuaire du service public liste les coordonnées de la MDPH de chaque département.",
            "Quand une situation est bloquée (sans solution, rupture d'accompagnement), la Communauté 360 du département peut être saisie au 0 800 360 360 pour construire une réponse avec la personne, ses aidants et les acteurs mobilisables.",
        ],
    },
}


def corpus_search(kws: list[str], max_docs: int = 3) -> list:
    """Cherche dans le corpus local : retourne des Doc compatibles research.Doc."""
    from dataclasses import dataclass, field

    @dataclass
    class Doc:
        centre_id: str
        centre_nom: str
        url: str
        titre: str
        passages: list = field(default_factory=list)
        score: int = 0

    hits = []
    for key, entry in CORPUS.items():
        text = " ".join(entry["passages"]).lower()
        score = sum(2 for k in kws if k.lower() in text)
        score += sum(2 for k in kws if k.lower() in " ".join(entry["kws"]))
        if score >= 2:
            hits.append(Doc(
                centre_id="corpus-" + key,
                centre_nom=entry["centre"],
                url=entry["url"],
                titre=entry["titre"],
                passages=entry["passages"],
                score=score + 10,  # le corpus est vérifié : léger bonus
            ))
    hits.sort(key=lambda d: -d.score)
    return hits[:max_docs]