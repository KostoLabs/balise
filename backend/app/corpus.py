"""Corpus local : passages réels extraits des centres ressources publics.

Chaque passage est cité tel quel depuis la page du centre (extractions
vérifiées au 17/09/2026). Le corpus garantit les réponses aux questions
fréquentes ; la recherche live complète pour tout le reste. Sources = mêmes
ressources, jamais de rédaction maison.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from math import log1p

from .research import keywords


@dataclass
class Doc:
    centre_id: str
    centre_nom: str
    url: str
    titre: str
    passages: list[str] = field(default_factory=list)
    score: float = 0


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
    "genetic_pathway": {
        "titre": "Parcours de soins en génétique",
        "centre": "Agence de la biomédecine — Génétique médicale",
        "url": "https://genetique-medicale.fr/parcours-de-soins-en-genetique/",
        "kws": [
            "annonce résultat génétique",
            "mutation génétique",
            "parcours génétique",
            "médecin prescripteur",
            "soutien social",
        ],
        "passages": [
            "L’objectif premier d’une consultation de génétique est l’information.",
            "Le laboratoire transmet le résultat au médecin prescripteur qui communiquera à son tour le résultat au patient lors d’une consultation individuelle, afin de garantir un accompagnement personnalisé de ce résultat.",
            "Si un diagnostic est établi : Le médecin généticien oriente son patient, dont la prise en charge peut nécessiter de consulter de nombreux autres spécialistes ; Le médecin apporte une aide dans le soutien psychologique et social du patient, en le mettant en relation avec des professionnels spécialisés et en l’aidant à trouver des structures d’accueil pour la vie quotidienne.",
            "En l’absence de diagnostic : Le médecin peut être amené à prescrire des examens complémentaires.",
        ],
    },
    "genetic_professionals": {
        "titre": "Professionnels de la génétique médicale",
        "centre": "Agence de la biomédecine — Génétique médicale",
        "url": "https://genetique-medicale.fr/professionnels-de-la-genetique-medicale/",
        "kws": [
            "adolescent mutation génétique",
            "famille résultat génétique",
            "conseiller génétique",
            "psychologue",
        ],
        "passages": [
            "Il informe le patient, ou ses parents s’il est mineur, des modalités de l’examen génétique et de ses conséquences psychologiques et thérapeutiques.",
            "Le conseiller en génétique exerce sous la responsabilité d’un médecin généticien.",
            "Aider le patient à mieux comprendre les conséquences des résultats de l’examen génétique pour lui et pour sa famille ;",
            "Le psychologue est là pour apporter le soutien nécessaire aux patients afin de les préparer et de les accompagner au mieux, à la fois pour gérer eux-mêmes la maladie, mais aussi pour en gérer les répercussions familiales.",
            "La consultation avec le psychologue est proposée au patient et à sa famille.",
        ],
    },
    "rare_centres": {
        "titre": "Annuaires des centres de référence et de compétence maladies rares",
        "centre": "Filières de santé maladies rares",
        "url": "https://www.filieresmaladiesrares.fr/annuaires-des-centres/",
        "kws": [
            "centre référence maladie rare",
            "centre compétence maladie rare",
            "crmr",
            "ccmr",
            "orientation spécialiste",
        ],
        "passages": [
            "Trouver le bon spécialiste, telle est la principale difficulté des patients souffrant de maladies rares et des professionnels de santé.",
            "Pour pallier les difficultés d’orientation, retrouverez ci-dessous le lien par filière qui vous permettra d’accéder à sa cartographie ou son annuaire des centres de référence (CRMR) et de compétence maladies rares (CCMR).",
        ],
    },
    "rare_mdph_daily_life": {
        "titre": "Comment faire une demande auprès de la MDPH ?",
        "centre": "Maladies Rares Info Services — parcours Santé & Vie",
        "url": "https://parcourssantevie.maladiesraresinfo.org/pages/comment-faire-une-demande-aupres-de-la-MDPH.html",
        "kws": [
            "conséquences vie quotidienne",
            "maladie rare mdph",
            "assistante sociale dossier mdph",
            "difficultés attentes",
        ],
        "passages": [
            "Le formulaire de « Demande à la MDPH » contient plusieurs rubriques. Il est recommandé de remplir avec attention toutes les rubriques en lien avec la situation de la personne en situation de handicap et notamment la rubrique « Votre vie quotidienne » (page 8).",
            "Cette rubrique aide la MDPH à prendre en compte la singularité de chaque personne. Elle apporte les éléments de compréhension qui vont permettre d'adapter les réponses à la situation. Il s'agit d'une information importante pour les équipes d'évaluation de la MDPH car cela les aide à comprendre comment vit la personne, quelles sont ses difficultés et ses attentes.",
            "Ce document n'est pas obligatoire, mais il donne la possibilité de communiquer des informations complémentaires utiles à la MDPH pour lui permettre de mieux comprendre les conséquences de la maladie rare dans les différents actes de la vie quotidienne, souvent méconnue de tous les services administratifs.",
            "A SAVOIR : Il est possible de se faire aider par la MDPH, le Centre communal d'action sociale (CCAS) ou tout autre type de service social, ou bien d'une association pour remplir ce formulaire.",
        ],
    },
    "pps": {
        "titre": "Projet personnalisé de scolarisation (PPS)",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/scolarite/quest-ce-que-le-pps-projet-personnalise-de-scolarisation",
        "kws": [
            "adolescent scolarité handicap",
            "pps",
            "aménagement scolarité",
            "accompagnement humain école",
        ],
        "passages": [
            "Le projet personnalisé de scolarisation (PPS) permet de garantir à tout enfant ou adolescent en situation de handicap, un parcours de scolarité adapté à ses besoins.",
            "Le projet personnalisé de scolarisation s’adresse aux élèves reconnus en situation de handicap par la MDPH sur décision de la CDAPH. Il concerne tous les enfants dont les situations nécessitent une compensation et des aménagements sur le plan scolaire relevant d’une décision de la CDAPH, y compris pour les élèves accueillis dans un établissement médico-social.",
            "Le projet personnalisé de scolarisation définit les modalités de déroulement de la scolarité et les actions pédagogiques, psychologiques, éducatives, sociales, médicales et paramédicales répondant aux besoins particuliers de l’élève en situation de handicap dans un contexte donné.",
        ],
    },
    "aeeh_child": {
        "titre": "AEEH : allocation d’éducation de l’enfant handicapé",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/aides/lallocation-deducation-de-lenfant-handicape-aeeh-et-ses-complements",
        "kws": [
            "aeeh adolescent",
            "allocation enfant handicapé",
            "dépenses handicap enfant",
            "taux incapacité",
        ],
        "passages": [
            "L’allocation d’éducation de l’enfant handicapé (AEEH) est une prestation familiale qui permet de compenser en partie les dépenses liées à la situation de handicap de votre enfant de moins de 20 ans.",
            "Une condition liée à son handicap qui est évaluée par la maison départementale des personnes handicapées (MDPH).",
            "La durée d’attribution de l’AEEH dépend des perspectives d’évolution de la situation de votre enfant et de son taux d’incapacité pour le complément.",
        ],
    },
    "pch_child": {
        "titre": "PCH pour les enfants et adolescents de moins de 20 ans",
        "centre": "Mon parcours handicap",
        "url": "https://www.monparcourshandicap.gouv.fr/aides/la-pch-pour-les-enfants-et-adolescents-de-moins-de-20-ans",
        "kws": [
            "pch adolescent",
            "compensation perte autonomie enfant",
            "aide humaine technique",
            "difficulté activité quotidienne",
        ],
        "passages": [
            "La PCH intervient sur des charges précises liées à un besoin : d’aide humaine, d’aides techniques, d’aménagement du logement, du véhicule ou de surcoûts de transport, de frais spécifiques ou exceptionnels, ou d’aides animalières.",
            "Vous pouvez en faire une demande de PCH pour vos enfants et adolescents de moins de 20 ans sous réserve de remplir trois conditions.",
            "Il faut au moins rencontrer : soit une difficulté absolue pour au moins 1 des 20 activités du référentiel d’accès à la PCH : la difficulté est absolue si l’enfant ou l’adolescent ne peut pas du tout réaliser l’activité sans aide ; soit une difficulté grave pour au moins 2 des 20 activités du référentiel d’accès à la PCH : l'activité est réalisée difficilement et avec un résultat altéré.",
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


RESOURCE_TOPIC_KEYS = {
    "medical_context": [],
    "family_support": ["conge_aidant"],
    "expert_centres": ["rare_centres"],
    "mdph_assessment": ["rare_mdph_daily_life", "mdph", "mdph_dossier"],
    "daily_life_impact": ["rare_mdph_daily_life", "mdph_dossier"],
    "schooling": ["pps"],
    "child_benefits": ["aeeh_child", "pch_child"],
    "care_coordination": ["mdph"],
    "establishment_search": ["esms"],
    "caregiver_support": ["conge_aidant"],
}


def _doc_for(key: str, score: float) -> Doc:
    entry = CORPUS[key]
    return Doc(
        centre_id="corpus-" + key,
        centre_nom=entry["centre"],
        url=entry["url"],
        titre=entry["titre"],
        passages=entry["passages"],
        score=score,
    )


def topic_documents(topics: list[str], max_docs: int = 8) -> list[Doc]:
    """Résout des facettes contrôlées vers des documents vérifiés, sans inférence."""
    keys: list[str] = []
    for topic in topics:
        for key in RESOURCE_TOPIC_KEYS.get(topic, []):
            if key not in keys:
                keys.append(key)
    return [_doc_for(key, 100 - index) for index, key in enumerate(keys[:max_docs])]


def _tokens(text: str) -> set[str]:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return set(re.findall(r"[^\W_]+", text))


def corpus_search(kws: list[str], max_docs: int = 3) -> list[Doc]:
    """IDF de BM25, occurrences binaires et bonus pour les libellés complets.

    Un terme compte une fois par document, sans cumul passage/titre/routing.
    Le poids double seulement si la requête couvre tous les mots significatifs
    d'un titre ou d'un libellé de routing : un fragment contextuel ne suffit pas.
    Si un libellé complet est reconnu, les simples mentions incidentes ne sont
    pas ajoutées pour remplir le quota. Les facettes complètent les autres besoins.
    Les reformulations répétées n'ajoutent aucun poids ; aucun sujet particulier
    n'intervient dans ce classement.
    """
    query_terms = _tokens(" ".join(kws))
    if not query_terms:
        return []
    terms = sorted(query_terms)
    fields = {}
    for key, entry in CORPUS.items():
        labels = [entry["titre"], *entry["kws"]]
        tokens = _tokens(" ".join([*entry["passages"], *labels]))
        boosted: set[str] = set()
        for label in labels:
            label_terms = _tokens(" ".join(keywords(label, [])))
            if label_terms and label_terms <= query_terms:
                boosted.update(label_terms)
        fields[key] = (tokens, boosted)

    weights = {}
    for term in terms:
        frequency = sum(term in tokens for tokens, _ in fields.values())
        weights[term] = log1p((len(fields) - frequency + 0.5) / (frequency + 0.5))

    hits = []
    has_complete_label = any(boosted for _, boosted in fields.values())
    for key, (tokens, boosted) in fields.items():
        if has_complete_label and not boosted:
            continue
        score = sum(
            weights[term] * (1 + (term in boosted))
            for term in terms if term in tokens
        )
        if score > 0:
            hits.append(_doc_for(key, score + 10))
    hits.sort(key=lambda d: -d.score)
    return hits[:max_docs]