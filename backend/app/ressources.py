"""Centres ressources publics et associatifs — sources uniques de Balise.

Chaque centre expose un site public avec recherche interne ou annuaire.
`SITES` définit les points d'entrée de recherche (gabarit `{q}`) ; les sites
sans `search_url` sont utilisés via leurs pages stables (accueil/annuaire).
"""

SITES = [
    {
        "id": "service-public",
        "nom": "Service-Public.fr",
        "type": "Public",
        "url": "https://www.service-public.fr/",
        "desc": "Droits et démarches officiels de l'administration française.",
        "search_url": "https://www.service-public.fr/particuliers/recherche?keyword={q}",
        "result_link": "/particuliers/vosdroits/",
        "allowed_domains": ["service-public.fr", "service-public.gouv.fr"],
        "scope": "national",
    },
    {
        "id": "mdph-en-ligne",
        "nom": "MDPH en ligne (CNSA)",
        "type": "Public",
        "url": "https://mdphenligne.cnsa.fr/",
        "desc": "Téléservices MDPH et fiches pratiques de la CNSA.",
        "search_url": "https://mdphenligne.cnsa.fr/s/?q={q}",
        "result_link": None,
        "scope": "national",
    },
    {
        "id": "cnsa",
        "nom": "CNSA",
        "type": "Public",
        "url": "https://www.cnsa.fr/",
        "desc": "Caisse nationale de solidarité pour l'autonomie : publications et guides.",
        "search_url": "https://www.cnsa.fr/?s={q}",
        "result_link": None,
        "scope": "national",
    },
    {
        "id": "gncra",
        "nom": "GNCRA — centres ressources autisme",
        "type": "Public",
        "url": "https://maisondelautisme.gouv.fr/",
        "desc": "Groupement national des centres ressources autisme, via la Maison de l'autisme.",
        "search_url": "https://maisondelautisme.gouv.fr/?s={q}",
        "result_link": None,
        "scope": "national",
    },
    {
        "id": "crehpsy",
        "nom": "CReHPsy — handicap psychique",
        "type": "Public",
        "url": "https://centre-ressource-rehabilitation.org/",
        "desc": "Centres ressources sur le handicap psychique : parcours, réhabilitation, pair-aidance.",
        "search_url": "https://centre-ressource-rehabilitation.org/?s={q}",
        "result_link": None,
        "scope": "national",
    },
    {
        "id": "cnrhr",
        "nom": "CNRHR — handicaps rares",
        "type": "Public",
        "url": "https://cnrlapepiniere.fr/",
        "desc": "Centres nationaux de ressources handicaps rares (surdicécité, épilepsies sévères…).",
        "search_url": "https://cnrlapepiniere.fr/?s={q}",
        "result_link": None,
        "scope": "national",
    },
    {
        "id": "annuaire-mdph",
        "nom": "Annuaire des MDPH",
        "type": "Public",
        "url": "https://lannuaire.service-public.gouv.fr/navigation/maison_handicapees",
        "desc": "Coordonnées des MDPH de chaque département.",
        "search_url": None,
        "result_link": None,
        "scope": "national",
    },
    {
        "id": "unafam",
        "nom": "Unafam",
        "type": "Association",
        "url": "https://www.unafam.org/",
        "desc": "Association de familles et proches de personnes vivant un handicap psychique : guides aidants.",
        "search_url": "https://www.unafam.org/recherche?keys={q}",
        "result_link": None,
        "scope": "national",
    },
    {
        "id": "autisme-info-service",
        "nom": "Autisme Info Service",
        "type": "Association",
        "url": "https://autismeinfoservice.fr/",
        "desc": "Information et écoute sur l'autisme et les troubles du neurodéveloppement.",
        "search_url": "https://autismeinfoservice.fr/?s={q}",
        "result_link": None,
        "scope": "national",
    },
    {
        "id": "nephou",
        "nom": "Nephou",
        "type": "Association",
        "url": "https://www.nephou.org/",
        "desc": "Ressources sur le polyhandicap : repères, parcours, aidants.",
        "search_url": None,
        "result_link": None,
        "scope": "national",
    },
    {
        "id": "communaute-360",
        "nom": "Communauté 360",
        "type": "Public",
        "url": "https://solidarites-sante.gouv.fr/",
        "desc": "Dispositif d'appui aux situations complexes (0 800 360 360) — pages officielles.",
        "search_url": "https://solidarites-sante.gouv.fr/?s={q}",
        "result_link": None,
        "scope": "national",
    },
]


def get_sources() -> list[dict]:
    """Liste publique des centres ressources (pour GET /api/sources)."""
    return [
        {
            "id": s["id"],
            "nom": s["nom"],
            "type": s["type"],
            "url": s["url"],
            "desc": s["desc"],
        }
        for s in SITES
    ]