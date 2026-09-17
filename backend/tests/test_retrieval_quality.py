"""Deterministic retrieval regressions; no model or live network calls."""

import asyncio

import pytest

from app import corpus, main


def _entry(key, text, *, title="Guide", keywords=()):
    return {
        "titre": title,
        "centre": "Mon parcours handicap",
        "url": f"https://www.monparcourshandicap.gouv.fr/{key}",
        "kws": list(keywords),
        "passages": [text],
    }


def _retrieve(monkeypatch, question, plan):
    """Exercise real local retrieval; replace only the external boundaries."""
    seen: dict = {"docs": []}

    async def fake_plan(*args, **kwargs):
        return plan

    async def no_live_research(queries, context):
        seen["live_queries"] = queries
        return []

    async def capture_synthesis(original_question, docs, **kwargs):
        seen.update(question=original_question, docs=docs, synthesis_kwargs=kwargs)
        return main.agent.unknown_answer(original_question, [], profile="pro")

    monkeypatch.setattr(main.planner, "plan_question", fake_plan)
    monkeypatch.setattr(main.research, "research_queries", no_live_research)
    monkeypatch.setattr(main.agent, "synthesize", capture_synthesis)
    monkeypatch.setattr(main.annuaire, "esms_passages", lambda *args, **kwargs: [])

    seen["answer"] = asyncio.run(
        main._answer(main.ChatRequest(question=question, profile="pro"), falc=False)
    )
    return seen


def test_distinctive_term_outweighs_common_context(monkeypatch):
    common = "information orientation accompagnement"
    entries = {f"general-{i}": _entry(f"general-{i}", common) for i in range(4)}
    entries["subject"] = _entry("subject", "télescope")
    monkeypatch.setattr(corpus, "CORPUS", entries)

    docs = corpus.corpus_search(["télescope", *common.split()], max_docs=3)

    assert docs[0].centre_id == "corpus-subject"
    assert any(doc.centre_id.startswith("corpus-general-") for doc in docs[1:])


@pytest.mark.parametrize(
    ("term", "unrelated_word"),
    [("art", "cartographie"), ("port", "transport"), ("net", "internet")],
)
def test_matches_whole_tokens_not_substrings(monkeypatch, term, unrelated_word):
    monkeypatch.setattr(
        corpus,
        "CORPUS",
        {
            "decoy": _entry(
                "decoy", unrelated_word, title=unrelated_word, keywords=[unrelated_word]
            )
        },
    )

    assert corpus.corpus_search([term]) == []


@pytest.mark.parametrize("metadata", [{"title": "Calendrier"}, {"keywords": ["calendrier"]}])
def test_topic_metadata_outweighs_incidental_body_mention(monkeypatch, metadata):
    entries = {
        "incidental": _entry("incidental", "Consultez aussi le calendrier."),
        "subject": _entry("subject", "Dates et délais officiels.", **metadata),
    }
    monkeypatch.setattr(corpus, "CORPUS", entries)

    docs = corpus.corpus_search(["calendrier"])

    assert docs[0].centre_id == "corpus-subject"


@pytest.mark.parametrize("term", ["RE\u0301PIT", "repit"])
def test_accent_variants_match_without_changing_source_text(monkeypatch, term):
    entry = _entry("subject", "Le répit.")
    monkeypatch.setattr(corpus, "CORPUS", {"subject": entry})

    docs = corpus.corpus_search([term])

    assert [doc.centre_id for doc in docs] == ["corpus-subject"]
    assert docs[0].passages == entry["passages"]


@pytest.mark.parametrize(
    "partial_metadata",
    [{"title": "Balise maritime"}, {"keywords": ["balise maritime"]}],
)
def test_complete_metadata_label_beats_an_incidental_fragment(monkeypatch, partial_metadata):
    entries = {
        "partial": _entry("partial", "Information officielle.", **partial_metadata),
        "subject": _entry("subject", "Information officielle.", keywords=["balise"]),
    }
    monkeypatch.setattr(corpus, "CORPUS", entries)

    docs = corpus.corpus_search(["balise"])

    assert docs[0].centre_id == "corpus-subject"


@pytest.mark.parametrize(
    ("question", "expected_key"),
    [
        (
            (
                "Je suis assistante sociale : comment orienter et accompagner "
                "cet adolescent atteint de la maladie de Charcot ?"
            ),
            "sla",
        ),
        ("Quelle démarche pour une RQTH ?", "rqth"),
        ("Qui contacter pour un PCPE ?", "pcpe"),
        (
            (
                "Je suis assistante sociale comment accompagner une famille dont "
                "un adolescent vient d'apprendre la maladie de Charcot"
            ),
            "sla",
        ),
        (
            (
                "Je suis assistante sociale : comment accompagner une famille et orienter "
                "un adolescent atteint de Charcot pour sa scolarité, son autonomie, "
                "les aides et les démarches ?"
            ),
            "sla",
        ),
    ],
)
def test_original_subject_survives_broad_reformulations(monkeypatch, question, expected_key):
    plan = {
        "audience": "pro",
        "intent": "orientation",
        "effort": "large",
        "resource_topics": [
            "medical_context", "family_support", "mdph_assessment", "schooling",
            "child_benefits", "care_coordination", "establishment_search",
        ],
        "casf_topics": [
            "mdph_missions", "needs_assessment", "cdaph_decisions", "pch",
            "right_to_compensation",
        ],
        "resource_queries": [
            "accompagnement familial adolescent scolarité",
            "orientation médicale sociale dossier MDPH prestations",
            "aide démarches projet vie quotidienne",
        ],
        "casf_queries": [],
        "missing_field": "department",
        "private_reasoning": "PRIVATE PLANNER HYPOTHESIS, NOT EVIDENCE",
    }
    seen = _retrieve(monkeypatch, question, plan)

    docs = seen["docs"]
    assert f"corpus-{expected_key}" in {doc.centre_id for doc in docs}
    expected_broad = corpus.topic_documents(plan["resource_topics"], max_docs=10)
    expected_legal = main.casf.search_topics(plan["casf_topics"], limit=6)
    assert len(expected_legal) == 6
    assert {doc.url for doc in expected_broad + expected_legal} <= {doc.url for doc in docs}
    assert len(docs) == len({doc.url for doc in docs}) <= 20
    assert seen["question"] == question
    assert seen["live_queries"] == plan["resource_queries"]
    assert "plan" not in seen["synthesis_kwargs"]
    assert plan["private_reasoning"] not in repr(seen)


@pytest.mark.parametrize("keywords", [[], [""], ["  ", "?!"], ["xylophone"], ["xyzquux"]])
def test_empty_or_absent_keywords_return_no_documents(keywords):
    assert corpus.corpus_search(keywords) == []


def test_empty_corpus_returns_no_documents(monkeypatch):
    monkeypatch.setattr(corpus, "CORPUS", {})

    assert corpus.corpus_search(["orientation"]) == []


def test_repetition_does_not_inflate_ranking(monkeypatch):
    entries = {
        "budget": _entry("budget", "budget", keywords=["budget"]),
        "calendrier": _entry("calendrier", "calendrier", keywords=["calendrier"]),
    }
    monkeypatch.setattr(corpus, "CORPUS", entries)
    baseline = corpus.corpus_search(["budget", "calendrier"])
    entries["budget"]["passages"] *= 50
    entries["budget"]["kws"] *= 50

    repeated = corpus.corpus_search(["budget"] * 50 + ["calendrier", "xyzquux"])

    assert [(doc.centre_id, doc.score) for doc in repeated] == [
        (doc.centre_id, doc.score) for doc in baseline
    ]


def test_multiword_keywords_match_individual_whole_tokens(monkeypatch):
    monkeypatch.setattr(
        corpus, "CORPUS", {"subject": _entry("subject", "Le port : son calendrier.")}
    )

    docs = corpus.corpus_search(["PORT-calendrier"])

    assert [doc.centre_id for doc in docs] == ["corpus-subject"]


@pytest.mark.parametrize("question", ["télescope", "xyzquux"])
def test_reformulations_still_supply_complementary_evidence(monkeypatch, question):
    entries = {
        f"original-{i}": _entry(f"original-{i}", "télescope", title="Télescope")
        for i in range(3)
    }
    entries["expansion"] = _entry("expansion", "cartographie", title="Cartographie")
    monkeypatch.setattr(corpus, "CORPUS", entries)
    plan = {
        "resource_queries": ["cartographie"],
        "casf_queries": [],
        "resource_topics": [],
        "casf_topics": [],
        "missing_field": "",
        "effort": "small",
    }

    seen = _retrieve(monkeypatch, question, plan)

    ids = {doc.centre_id for doc in seen["docs"]}
    assert "corpus-expansion" in ids
    if question == "télescope":
        assert len(ids & {"corpus-original-0", "corpus-original-1", "corpus-original-2"}) == 3
    assert len(ids) <= 4


def test_no_evidence_returns_unknown_without_calling_synthesis(monkeypatch):
    plan = {
        "resource_queries": ["xyzquux"],
        "casf_queries": [],
        "resource_topics": [],
        "casf_topics": [],
        "missing_field": "subject",
        "effort": "small",
    }

    seen = _retrieve(monkeypatch, "xyzquux", plan)

    assert "synthesis_kwargs" not in seen
    assert seen["docs"] == []
    answer = seen["answer"]
    assert answer["unknown"] is True
    assert answer["paras"] == answer["steps"] == answer["contacts"] == []
    assert not answer.get("sources")
