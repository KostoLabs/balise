"""Recherche CASF locale : provenance, références exactes et absence de troncature."""

import json

import pytest

from app import casf


def _fixture(tmp_path):
    long_text = "Le projet personnalisé coordonne les interventions. " * 120
    payload = {
        "meta": {
            "publisher": "DILA",
            "dataset": "LEGI",
            "code_id": "LEGITEXT000006074069",
            "as_of": "2026-09-15",
            "archives": [{"filename": "snapshot.tar.gz", "url": "https://echanges.dila.gouv.fr/OPENDATA/LEGI/", "sha256": "abc"}],
        },
        "articles": [
            {
                "id": "LEGIARTI000000000001",
                "num": "L114-1-1",
                "etat": "VIGUEUR",
                "date_debut": "2026-01-01",
                "date_fin": "2999-01-01",
                "breadcrumb": "Personnes handicapées > Compensation",
                "texte": long_text,
            },
            {
                "id": "LEGIARTI000000000002",
                "num": "D312-162",
                "etat": "VIGUEUR",
                "date_debut": "2025-01-01",
                "date_fin": "2999-01-01",
                "breadcrumb": "Services d'accompagnement à la vie sociale",
                "texte": "Les services d'accompagnement à la vie sociale contribuent à la réalisation du projet de vie.",
            },
        ],
    }
    path = tmp_path / "casf_index.json"
    path.write_text(json.dumps(payload, ensure_ascii=False))
    return path, long_text


def test_load_index_requires_provenance_and_keeps_full_text(tmp_path):
    path, long_text = _fixture(tmp_path)
    index = casf.load_index(path)
    assert index.meta["publisher"] == "DILA"
    assert index.meta["as_of"] == "2026-09-15"
    assert index.articles[0]["texte"] == long_text
    assert len(index.articles[0]["texte"]) > 4000


def test_search_prefers_exact_article_reference_and_generates_legifrance_url(tmp_path):
    path, _ = _fixture(tmp_path)
    docs = casf.search(["article D. 312-162"], path=path, limit=3)
    assert docs
    assert docs[0].titre.startswith("CASF — article D312-162")
    assert docs[0].url == "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000000000002"
    assert docs[0].centre_id == "casf"
    assert docs[0].passages == [
        "Les services d'accompagnement à la vie sociale contribuent à la réalisation du projet de vie."
    ]


def test_search_by_legal_theme_returns_relevant_article(tmp_path):
    path, _ = _fixture(tmp_path)
    docs = casf.search(["coordination projet personnalisé interventions"], path=path, limit=2)
    assert docs[0].titre.startswith("CASF — article L114-1-1")


def test_invalid_root_type_is_rejected_and_search_fails_closed(tmp_path):
    path = tmp_path / "bad-root.json"
    path.write_text(json.dumps([]))

    with pytest.raises(TypeError, match="index CASF invalide"):
        casf.load_index(path)
    assert casf.search(["PCH"], path=path) == []


def test_invalid_or_incomplete_index_is_disabled(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"meta": {"publisher": "DILA"}, "articles": []}))
    assert casf.search(["PCH"], path=path) == []


def test_controlled_topics_resolve_exact_current_casf_articles():
    docs = casf.search_topics(
        [
            "disability_definition",
            "right_to_compensation",
            "mdph_missions",
            "needs_assessment",
            "cdaph_decisions",
            "pch",
        ],
        limit=10,
    )

    titles = "\n".join(doc.titre for doc in docs)
    assert "article L114 —" in titles
    assert "article L114-1-1 —" in titles
    assert "article L146-3 —" in titles
    assert "article L146-8 —" in titles
    assert "article R146-28 —" in titles
    assert "article L241-6 —" in titles
    assert "article L245-1 —" in titles
    assert len(docs) == 7


@pytest.mark.parametrize("prefix", ["L", "R", "D"])
def test_best_passage_never_splits_an_article_reference_or_its_condition(prefix):
    sentence = f"L'équipe évalue les besoins selon l'article {prefix}. 312-1 si la condition est remplie."
    text = "Introduction. " + sentence + " Une autre phrase."
    passage = casf._best_passage(text, {"evalue", "besoins"}, max_chars=60)
    assert passage == sentence
    assert passage in text


def test_live_l146_8_passage_does_not_end_at_article_abbreviation():
    doc = next(doc for doc in casf.search_topics(["needs_assessment"])
               if "article L146-8" in doc.titre)
    assert not doc.passages[0].endswith("article L.")
    original = next(a["texte"] for a in casf.load_index().articles if a["num"] == "L146-8")
    assert doc.passages[0] in " ".join(original.split())
