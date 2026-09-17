"""Centres ressources publics et associatifs — sources uniques de Balise.

Chaque centre expose un site public avec recherche interne ou annuaire.
`SITES` définit les points d'entrée de recherche (gabarit `{q}`) ; les sites
sans `search_url` sont utilisés via leurs pages stables (accueil/annuaire).
"""

from urllib.parse import urlparse

SITES = [
    {
        "id": "casf",
        "nom": "Légifrance — Code de l'action sociale et des familles",
        "type": "Public",
        "url": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006074069",
        "desc": "Texte officiel consolidé du CASF, fourni par la DILA.",
        "search_url": None,
        "result_link": None,
        "allowed_domains": ["legifrance.gouv.fr"],
        "scope": "national",
    },
    {
        "id": "finess",
        "nom": "Annuaire FINESS",
        "type": "Public",
        "url": "https://finess.esante.gouv.fr/",
        "desc": "Annuaire public des établissements et organismes sanitaires et médico-sociaux.",
        "search_url": None,
        "result_link": None,
        "allowed_domains": ["finess.esante.gouv.fr", "data.gouv.fr"],
        "scope": "national",
    },
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
        "id": "agence-biomedecine-genetique",
        "nom": "Agence de la biomédecine — Génétique médicale",
        "type": "Public",
        "url": "https://genetique-medicale.fr/",
        "desc": "Parcours de soins, professionnels et accompagnement en génétique médicale.",
        "search_url": "https://genetique-medicale.fr/?s={q}",
        "result_link": None,
        "allowed_domains": ["genetique-medicale.fr"],
        "scope": "national",
    },
    {
        "id": "filieres-maladies-rares",
        "nom": "Filières de santé maladies rares",
        "type": "Public",
        "url": "https://www.filieresmaladiesrares.fr/",
        "desc": "Annuaires nationaux des centres de référence et de compétence maladies rares.",
        "search_url": "https://www.filieresmaladiesrares.fr/?s={q}",
        "result_link": None,
        "allowed_domains": ["filieresmaladiesrares.fr"],
        "scope": "national",
    },
    {
        "id": "maladies-rares-info",
        "nom": "Maladies Rares Info Services",
        "type": "Association",
        "url": "https://www.maladiesraresinfo.org/",
        "desc": "Information et accompagnement des personnes concernées par une maladie rare.",
        "search_url": "https://www.maladiesraresinfo.org/recherche.html?q={q}",
        "result_link": None,
        "allowed_domains": ["maladiesraresinfo.org"],
        "scope": "national",
    },
    {
        "id": "has",
        "nom": "HAS — Haute Autorité de Santé",
        "type": "Public",
        "url": "https://www.has-sante.fr/",
        "desc": "Recommandations professionnelles et parcours de soins (autisme, TND, ESMS).",
        "search_url": "https://www.has-sante.fr/?s={q}",
        "result_link": "/jcms/",
        "allowed_domains": ["has-sante.fr"],
        "scope": "national",
    },
    {
        "id": "agefiph",
        "nom": "Agefiph",
        "type": "Association",
        "url": "https://www.agefiph.fr/",
        "desc": "Emploi des travailleurs handicapés : aides, RQTH, obligation d'emploi, conseils employeurs.",
        "search_url": "https://www.agefiph.fr/recherche?texte-recherche={q}",
        "result_link": None,
        "allowed_domains": ["agefiph.fr", "espace-emploi.agefiph.fr"],
        "scope": "national",
    },
    {
        "id": "handicap-gouv",
        "nom": "handicap.gouv.fr",
        "type": "Public",
        "url": "https://handicap.gouv.fr/",
        "desc": "Ministère chargé des questions de handicap : dispositifs, plans, PCPE, guides officiels.",
        "search_url": "https://handicap.gouv.fr/?s={q}",
        "result_link": None,
        "allowed_domains": ["handicap.gouv.fr"],
        "scope": "national",
    },
    {
        "id": "mon-parcours-handicap",
        "nom": "Mon parcours handicap",
        "type": "Public",
        "url": "https://www.monparcourshandicap.gouv.fr/",
        "desc": "Référentiel public des fiches handicap : MDPH, ESMS, SAVS, IME, PCH, RQTH, FALC.",
        "search_url": None,
        "result_link": None,
        "scope": "national",
    },
    {
        "id": "ffdys",
        "nom": "FFDys — troubles du langage et apprentissages",
        "type": "Association",
        "url": "https://www.ffdys.com/",
        "desc": "Fédération française des Dys : troubles du langage et des apprentissages, centres référents TSLA.",
        "search_url": "https://www.ffdys.com/?s={q}",
        "result_link": None,
        "allowed_domains": ["ffdys.com"],
        "scope": "national",
    },
    {
        "id": "apf",
        "nom": "APF France handicap",
        "type": "Association",
        "url": "https://www.apf-francehandicap.org/",
        "desc": "Association nationale : accès aux droits, aides techniques, inclusion scolaire et professionnelle.",
        "search_url": "https://www.apf-francehandicap.org/?s={q}",
        "result_link": None,
        "allowed_domains": ["apf-francehandicap.org"],
        "scope": "national",
    },
    {
        "id": "unapei",
        "nom": "Unapei",
        "type": "Association",
        "url": "https://www.unapei.org/",
        "desc": "Fédération de 550 associations : déficience intellectuelle, inclusion, droits des familles.",
        "search_url": "https://www.unapei.org/?s={q}",
        "result_link": None,
        "allowed_domains": ["unapei.org"],
        "scope": "national",
    },
    {
        "id": "psycom",
        "nom": "Psycom",
        "type": "Association",
        "url": "https://www.psycom.org/",
        "desc": "Santé mentale et handicap psychique : repères, lutte contre la stigmatisation, guides.",
        "search_url": "https://www.psycom.org/?s={q}",
        "result_link": None,
        "allowed_domains": ["psycom.org"],
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


_SOURCE_BY_ID = {source["id"]: source for source in SITES}


def _domain_allowed(url: str, domains: list[str]) -> bool:
    host = urlparse(url).hostname or ""
    host = host.casefold()
    return url.startswith("https://") and any(
        host == domain or host.endswith("." + domain) for domain in domains
    )


def is_authorized_document(source_id: str, url: str) -> bool:
    """Politique unique pour les documents live, CASF, FINESS et corpus."""
    source = _SOURCE_BY_ID.get(source_id)
    if source is not None:
        domains = source.get("allowed_domains") or [
            (urlparse(source["url"]).hostname or "").removeprefix("www.")
        ]
        return _domain_allowed(url, domains)
    if source_id.startswith("corpus-"):
        # Le corpus garde ses identifiants de routage mais son URL doit appartenir
        # à l'un des organismes explicitement inscrits au registre.
        return any(
            _domain_allowed(
                url,
                source.get("allowed_domains")
                or [(urlparse(source["url"]).hostname or "").removeprefix("www.")],
            )
            for source in SITES
        )
    return False


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