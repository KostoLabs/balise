"""Index local du Code de l'action sociale et des familles (CASF).

L'index est construit hors ligne depuis LEGI/DILA. À l'exécution, ce module ne
consulte pas le web : il sélectionne quelques articles verbatim et génère leur
URL Légifrance à partir de l'identifiant LEGIARTI validé.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .research import Doc

INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "casf_index.json"
LEGI_ID_RE = re.compile(r"^LEGIARTI\d{12}$")
ARTICLE_RE = re.compile(r"\b([LRD])\s*\.?\s*(\d+(?:\s*-\s*\d+)*)\b", re.IGNORECASE)
WORD_RE = re.compile(r"[a-z0-9]+")
STOP = {
    "article", "articles", "code", "casf", "action", "sociale", "familles",
    "dans", "avec", "pour", "une", "des", "les", "aux", "sur", "par",
    "quel", "quelle", "comment", "quoi", "faire", "être", "sont",
}


@dataclass(frozen=True)
class CASFIndex:
    meta: dict
    articles: list[dict]


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(WORD_RE.findall(value.casefold()))


def _num_norm(value: str) -> str:
    match = ARTICLE_RE.search(value)
    if not match:
        return re.sub(r"[^A-Z0-9-]", "", value.upper())
    return match.group(1).upper() + re.sub(r"\s+", "", match.group(2))


def load_index(path: str | Path = INDEX_PATH) -> CASFIndex:
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, dict):
        raise TypeError("index CASF invalide")
    meta = raw.get("meta")
    articles = raw.get("articles")
    required_meta = {"publisher", "dataset", "code_id", "as_of", "archives"}
    if not isinstance(meta, dict) or not required_meta.issubset(meta):
        raise ValueError("provenance CASF incomplète")
    if meta.get("publisher") != "DILA" or meta.get("dataset") != "LEGI":
        raise ValueError("provenance CASF non autorisée")
    if meta.get("code_id") != "LEGITEXT000006074069":
        raise ValueError("mauvais code LEGI")
    if not isinstance(meta.get("archives"), list) or not meta["archives"]:
        raise ValueError("archives CASF absentes")
    if not isinstance(articles, list) or not articles:
        raise ValueError("articles CASF absents")
    valid: list[dict] = []
    for article in articles:
        if not isinstance(article, dict):
            continue
        legi_id = str(article.get("id", ""))
        if (
            LEGI_ID_RE.fullmatch(legi_id)
            and article.get("etat") == "VIGUEUR"
            and str(article.get("num", "")).strip()
            and str(article.get("texte", "")).strip()
        ):
            valid.append(article)
    if not valid:
        raise ValueError("aucun article CASF valide")
    return CASFIndex(meta=meta, articles=valid)


def _query_terms(queries: list[str]) -> tuple[set[str], set[str]]:
    refs: set[str] = set()
    terms: set[str] = set()
    for query in queries:
        refs.update(_num_norm(m.group(0)) for m in ARTICLE_RE.finditer(query))
        terms.update(t for t in _norm(query).split() if len(t) >= 3 and t not in STOP)
    return refs, terms


def _best_passage(text: str, terms: set[str], max_chars: int = 1800) -> str:
    """Extrait un bloc complet autour des phrases les plus pertinentes."""
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    # L./R./D. introduisent une référence, pas une nouvelle phrase.
    sentences = re.split(r"(?<=[.!?;:])(?<!\b[LRD]\.)\s+", text)
    scored = []
    for i, sentence in enumerate(sentences):
        low = _norm(sentence)
        score = sum(1 for term in terms if term in low)
        scored.append((score, i))
    _, center = max(scored, default=(0, 0))
    selected = sentences[center]
    left, right = center - 1, center + 1
    while len(selected) < max_chars and (left >= 0 or right < len(sentences)):
        candidate = ""
        if right < len(sentences):
            candidate = selected + " " + sentences[right]
            right += 1
        elif left >= 0:
            candidate = sentences[left] + " " + selected
            left -= 1
        if len(candidate) > max_chars:
            break
        selected = candidate
    return selected.strip()


def search(
    queries: list[str],
    *,
    path: str | Path = INDEX_PATH,
    limit: int = 4,
) -> list[Doc]:
    """Recherche lexicale déterministe, avec priorité aux références exactes."""
    try:
        index = load_index(path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return []
    refs, terms = _query_terms(queries)
    if not refs and not terms:
        return []

    ranked: list[tuple[int, dict]] = []
    for article in index.articles:
        num = _num_norm(str(article["num"]))
        haystack = _norm(
            " ".join(
                [
                    str(article.get("num", "")),
                    str(article.get("breadcrumb", "")),
                    str(article.get("texte", "")),
                ]
            )
        )
        score = 1000 if num in refs else 0
        score += sum(8 if term in _norm(str(article.get("breadcrumb", ""))) else 2 for term in terms if term in haystack)
        if score:
            ranked.append((score, article))
    ranked.sort(key=lambda item: (-item[0], _num_norm(str(item[1]["num"])), str(item[1]["id"])))

    docs: list[Doc] = []
    for score, article in ranked[: max(0, limit)]:
        legi_id = str(article["id"])
        num = str(article["num"])
        passage = _best_passage(str(article["texte"]), terms)
        since = str(article.get("date_debut", "")).strip()
        suffix = f" — en vigueur depuis {since}" if since else ""
        docs.append(
            Doc(
                centre_id="casf",
                centre_nom="Légifrance — Code de l'action sociale et des familles",
                url=f"https://www.legifrance.gouv.fr/codes/article_lc/{legi_id}",
                titre=f"CASF — article {num}{suffix}",
                passages=[passage],
                score=score,
            )
        )
    return docs


CASF_TOPIC_ARTICLES = {
    "disability_definition": [
        ("L114", "limitation activité restriction participation altération durable")
    ],
    "right_to_compensation": [
        ("L114-1-1", "droit compensation besoins projet vie famille aidants")
    ],
    "mdph_missions": [
        ("L146-3", "accueil information accompagnement conseil projet vie")
    ],
    "needs_assessment": [
        ("L146-8", "évalue besoins compensation incapacité projet vie parents mineur"),
        (
            "R146-28",
            "situation matérielle familiale sanitaire scolaire professionnelle psychologique",
        ),
    ],
    "cdaph_decisions": [
        ("L241-6", "prestations orientation scolarisation enfant adolescent")
    ],
    "pch": [("L245-1", "prestation compensation enfant conditions besoins")],
    "esms_orientation": [
        ("L241-6", "orientation établissement service médico-social")
    ],
}


def search_topics(
    topics: list[str],
    *,
    path: str | Path = INDEX_PATH,
    limit: int = 8,
) -> list[Doc]:
    """Résout des facettes contrôlées vers les articles CASF exacts en vigueur."""
    try:
        index = load_index(path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return []

    articles = {_num_norm(str(article["num"])): article for article in index.articles}
    requested: list[tuple[str, str]] = []
    for topic in topics:
        for ref, focus in CASF_TOPIC_ARTICLES.get(topic, []):
            normalized_ref = _num_norm(ref)
            if all(existing_ref != normalized_ref for existing_ref, _ in requested):
                requested.append((normalized_ref, focus))

    docs: list[Doc] = []
    for normalized_ref, focus in requested[: max(0, limit)]:
        article = articles.get(normalized_ref)
        if article is None:
            continue
        legi_id = str(article["id"])
        num = str(article["num"])
        terms = {term for term in _norm(focus).split() if term not in STOP}
        passage = _best_passage(str(article["texte"]), terms)
        since = str(article.get("date_debut", "")).strip()
        suffix = f" — en vigueur depuis {since}" if since else ""
        docs.append(
            Doc(
                centre_id="casf",
                centre_nom="Légifrance — Code de l'action sociale et des familles",
                url=f"https://www.legifrance.gouv.fr/codes/article_lc/{legi_id}",
                titre=f"CASF — article {num}{suffix}",
                passages=[passage],
                score=1000,
            )
        )
    return docs
