"""Annuaire des ESMS — recherche dans l'index FINESS local (données publiques ANS).

Index construit par scripts/build_esms_index.py depuis le fichier
« FINESS - Structures » de data.gouv.fr. Chaque résultat est un
établissement réel : nom, type, adresse, téléphone.
"""

import json
import re
import unicodedata
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
INDEX = DATA / "esms_index.json"
ORGANISMES = DATA / "organismes_index.json"

# Alias publics : marque d'usage courante -> raison sociale FINESS.
# Complété au fil des demandes ; les coordonnées viennent toujours de FINESS.
ORG_ALIASES = {
    "anaji": "HEBERGEMENT MEDICALISE POUR ENFANTS HANDICAPES",
    "papillons blancs": "UNAPEI",
    "uniopss": "UNIOPSS",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    # acronymes à points : A.N.A.J.I -> anaji
    s = re.sub(r"(?<=\b\w)\.(?=\w)", "", s)
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()

# requête → mots-clés à chercher dans le libellé de catégorie
TYPE_KW = [
    ("savs", ["accompagnement à la vie sociale"]),
    ("samsah", ["médico-social adultes", "médico-social pour adultes"]),
    ("sessad", ["éducation spéciale", "soins à domicile", "accompagnement à domicile", "ssead"]),
    ("ime", ["médico-éducatif", "i.m.e"]),
    ("iem", ["éducation motrice", "i.e.m"]),
    ("itep", ["therapeutique", "ITEP", "psychothér"]),
    ("esat", ["travail"]),
    ("mas ", ["accueil médicalisé"]),
    ("fam", ["accueil médicalisé"]),
    ("foyer", ["foyer"]),
    ("mecs", ["caractère social", "enfants à caractère"]),
    ("cmpp", ["psycho-pédagogique", "psycho-pédago"]),
    ("cmp", ["médico-psychologique"]),
    ("mdph", ["départementale des personnes handicapées"]),
]

_cache = None
_org_cache = None


def _load() -> list[dict]:
    global _cache
    if _cache is None:
        _cache = json.loads(INDEX.read_text()) if INDEX.exists() else []
    return _cache


def _load_organismes() -> dict:
    global _org_cache
    if _org_cache is None:
        _org_cache = json.loads(ORGANISMES.read_text()) if ORGANISMES.exists() else {}
    return _org_cache


def _commune_name(value: str) -> str:
    """La ligne d'acheminement FINESS peut comporter un suffixe CEDEX."""
    return re.sub(r"\s+cedex(?:\s+[0-9]+)?$", "", " ".join(_norm(value).split()))


def _detect_commune(query: str) -> str | None:
    """Détecte une seule ville, par termes entiers de l'index des communes."""
    q = " ".join(_norm(query).split())
    communes = {_commune_name(e.get("commune") or "") for e in _load()}
    matches = {
        c for c in communes if len(c) >= 4 and re.search(rf"\b{re.escape(c)}\b", q)
    }
    # « Saint André lez Lille » ne doit pas sélectionner « Lille ».
    matches = {
        c for c in matches
        if not any(c != other and re.search(rf"\b{re.escape(c)}\b", other) for other in matches)
    }
    return next(iter(matches)) if len(matches) == 1 else None


def search_organisme(query: str, limit: int = 3) -> list[dict]:
    """Cherche un organisme gestionnaire par son nom (raison sociale FINESS).

    Les alias de marque (ORG_ALIASES) court-circuitent la recherche :
    on cherche directement par la raison sociale complète.
    """
    orgs = _load_organismes()
    if not orgs:
        return []
    q = _norm(query)
    # 1) alias de marque reconnu -> cible directe par raison sociale
    for alias, raison in ORG_ALIASES.items():
        if all(a in q for a in alias.split()):
            raison_n = _norm(raison)
            for o in orgs.values():
                if _norm(o.get("nom")) == raison_n:
                    return [o]
            return []
    # 2) recherche générique par mots significatifs
    words = [w for w in q.split() if len(w) >= 4]
    GENERIC = {"handicap", "handicapes", "handicapés", "enfants", "enfant", "adultes",
               "adulte", "association", "famille", "familles", "pour", "donne", "coordonnees", "coordonnées",
               "integration", "jeunes", "personnes", "etablissements", "medicalise",
               "medicale", "medico", "social", "hebergement"}
    words = [w for w in words if w not in GENERIC]
    out = []
    for o in orgs.values():
        nom_n = _norm(o.get("nom"))
        if not nom_n or not words:
            continue
        hits = sum(1 for w in words if w in nom_n)
        if hits >= 2 or (len(words) == 1 and words[0] in nom_n):
            out.append((hits, o))
    out.sort(key=lambda x: -x[0])
    return [o for _, o in out[:limit]]


def search_esms(
    query: str, commune: str | None = None, limit: int = 4, *, dept_code: str | None = None,
) -> list[dict]:
    """Cherche par type/nom, commune et/ou code départemental explicite.

    Le périmètre départemental utilise le CP public FINESS, pas le n° FINESS.
    Seuls les codes métropolitains 01–95 hors Corse sont pris en charge ;
    aucun repli national pour un code invalide ou non pris en charge.
    """
    if dept_code is not None and not re.fullmatch(
        r"(?:0[1-9]|1[0-9]|2[1-9]|[3-8][0-9]|9[0-5])", dept_code,
    ):
        return []
    entries = _load()
    if not entries:
        return []
    q = _norm(query)
    # Une commune fournie reste contraignante même si la question ne la répète pas.
    ville = _commune_name(commune) if commune else _detect_commune(query)
    # détecte le(s) type(s) demandé(s)
    types = []
    for kw, libkws in TYPE_KW:
        normalized_kw = _norm(kw)
        if normalized_kw and re.search(rf"\b{re.escape(normalized_kw)}\b", q):
            types.extend(_norm(t) for t in libkws)
    # Sans localisation, les premiers résultats nationaux seraient arbitraires,
    # y compris quand plusieurs mots génériques correspondent au nom.
    if not ville and not dept_code:
        return []
    # mots génériques de la question à chercher dans le nom
    stop = {"dans", "les", "une", "que", "qui", "pour", "avec", "est", "il", "y", "a",
            "contact", "contacter", "etablissement", "etablissements", "existe", "pres",
            "chez", "moi", "je", "suis", "quelle", "quel", "adresses", "adresse",
            "lycee", "scolarite", "donne", "donner", "coordonnees", "numero", "numeros", "tel", "telephone", "appelle", "appeler", "trouve", "trouver"}
    wanted = [w for w in q.split() if len(w) >= 3 and w not in stop]
    if ville:
        wanted = [w for w in wanted if w != ville]
    # sans type demandé, il faut au moins un mot significatif qui matche le NOM
    # (sinon on renvoie du bruit : n'importe quel établissement de la ville)
    if not types and not wanted:
        return []

    out = []
    for e in entries:
        if dept_code:
            cp = str(e.get("cp") or "")
            if not re.fullmatch(r"[0-9]{5}", cp) or not cp.startswith(dept_code):
                continue
        nom_n = _norm(e["nom"])
        type_n = _norm(str(e.get("type") or ""))
        commune_n = _commune_name(e.get("commune") or "")
        score = 0
        if types:
            if not any(t in type_n for t in types):
                continue
            score += 3
        if wanted:
            name_hits = sum(1 for w in wanted if w in nom_n)
            score += 2 * name_hits
            # Sans type explicite, un mot courant isolé (par ex. « famille »
            # ou « accompagnement ») ne suffit pas à identifier un ESMS.
            if not types and name_hits < 2:
                continue
        if ville:
            if ville != commune_n:
                continue
            score += 5
        if score <= 0:
            continue
        out.append((score, e))
    out.sort(key=lambda x: -x[0])
    # diversité : garde les meilleurs scores
    return [dict(e) for _, e in out[:limit]]


def esms_passages(
    query: str, commune: str | None = None, *, dept_code: str | None = None,
) -> list[str]:
    """Passages formatés pour l'agent : coordonnées réelles à citer.

    D'abord les établissements par type+ville ; si la question cite un
    organisme gestionnaire, on ajoute son siège et la liste de ses
    établissements (avec question de filtre si trop nombreux).
    """
    docs = []
    idx = {e["finess"]: e for e in _load()}

    # 1) organismes gestionnaires cités dans la question
    for org in search_organisme(query):
        tel = org.get("tel") or ""
        if tel.startswith("0") and len(tel) == 10:
            tel = " ".join(tel[i:i + 2] for i in range(0, 10, 2))
        # relie le nom demandé à la raison sociale FINESS (les noms d'usage
        # diffèrent souvent de la raison sociale : le modèle doit savoir que
        # c'est la même entité)
        alias_note = ""
        qn = _norm(query)
        for alias, raison in ORG_ALIASES.items():
            if all(a in qn for a in alias.split()) and _norm(str(org.get("nom") or "")) == _norm(raison):
                alias_note = f" (correspond au nom demandé « {alias.upper()} » : c'est le même organisme)"
                break
        line = f"Organisme gestionnaire : {org['nom']}{alias_note}"
        if tel:
            line += f" — téléphone du siège {tel}"
        line += f" — siège : {org.get('adresse') or 'voir annuaire'} (FINESS {org['finess']}, base publique FINESS/ANS)"
        children = [idx[f] for f in org.get("etablissements", []) if f in idx]
        if children:
            line += f". Cet organisme exploite {len(children)} établissement(s) médico-sociaux :"
            for c in children[:6]:
                ctel = c.get("tel") or ""
                if ctel.startswith("0") and len(ctel) == 10:
                    ctel = " ".join(ctel[i:i + 2] for i in range(0, 10, 2))
                line += f" {c['nom']} ({c['type']}, {c['adresse']}"
                line += f", téléphone {ctel}) ;" if ctel else ") ;"
            if len(children) > 6:
                line += f" et {len(children) - 6} autres — demander à l'utilisateur lequel l'intéresse (ville ou type) pour donner ses coordonnées."
        docs.append(line)

    # 2) établissements par type + ville
    for h in search_esms(query, commune, dept_code=dept_code):
        tel = h.get("tel") or ""
        if tel.startswith("0") and len(tel) == 10:
            tel = " ".join(tel[i:i + 2] for i in range(0, 10, 2))
        line = f"{h['nom']} — {h['type']} — {h['adresse']}"
        if tel:
            line += f" — téléphone {tel}"
        line += f" (FINESS {h['finess']}, base publique FINESS/ANS)"
        docs.append(line)
    return docs