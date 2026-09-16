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


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()

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


def _load() -> list[dict]:
    global _cache
    if _cache is None:
        _cache = json.loads(INDEX.read_text()) if INDEX.exists() else []
    return _cache


def _detect_commune(query: str) -> str | None:
    """Détecte une ville citée dans la question (match sur l'index des communes)."""
    q = _norm(query)
    communes = {}
    for e in _load():
        c = _norm(str(e.get("commune")))
        if len(c) >= 4:
            communes.setdefault(c, True)
    for c in communes:
        if c in q:
            return c
    return None


def search_esms(query: str, commune: str | None = None, limit: int = 4) -> list[dict]:
    """Cherche des établissements médico-sociaux par type/nom et commune."""
    entries = _load()
    if not entries:
        return []
    q = _norm(query)
    # ville citée dans la question ? (prioritaire sur le paramètre)
    ville = _detect_commune(query) or (commune if commune and _norm(commune) in q else None)
    # détecte le(s) type(s) demandé(s)
    types = []
    for kw, libkws in TYPE_KW:
        if kw in q:
            types.extend(_norm(t) for t in libkws)
    # mots génériques de la question à chercher dans le nom
    stop = {"dans", "les", "une", "que", "qui", "pour", "avec", "est", "il", "y", "a",
            "contact", "contacter", "etablissement", "etablissements", "existe", "pres",
            "chez", "moi", "je", "suis", "quelle", "quel", "adresses", "adresse",
            "lycee", "scolarite"}
    wanted = [w for w in q.split() if len(w) >= 3 and w not in stop]
    if ville:
        wanted = [w for w in wanted if w != ville]

    out = []
    for e in entries:
        nom_n = _norm(e["nom"])
        type_n = _norm(str(e.get("type") or ""))
        commune_n = _norm(str(e.get("commune"))) + " " + _norm(str(e.get("cp")))
        score = 0
        if types:
            if not any(t in type_n for t in types):
                continue
            score += 3
        if wanted:
            score += sum(2 for w in wanted if w in nom_n)
            if not types and score == 0:
                continue
        if ville:
            if ville not in commune_n:
                continue
            score += 5
        if score <= 0:
            continue
        out.append((score, e))
    out.sort(key=lambda x: -x[0])
    # diversité : garde les meilleurs scores
    return [dict(e) for _, e in out[:limit]]


def esms_passages(query: str, commune: str | None = None) -> list[str]:
    """Passages formatés pour l'agent : coordonnées réelles à citer."""
    hits = search_esms(query, commune)
    docs = []
    for h in hits:
        tel = h.get("tel") or ""
        if tel.startswith("0") and len(tel) == 10:
            tel = " ".join(tel[i:i + 2] for i in range(0, 10, 2))
        line = f"{h['nom']} — {h['type']} — {h['adresse']}"
        if tel:
            line += f" — téléphone {tel}"
        line += f" (FINESS {h['finess']}, base publique FINESS/ANS)"
        docs.append(line)
    return docs