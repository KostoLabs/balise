"""Invariants de grounding : compréhension libre, réponse exclusivement sourcée."""

import asyncio
from dataclasses import dataclass, field

import httpx
import pytest

from app import corpus, main, research
from app.agent import (
    _clean,
    _system_prompt,
    build_messages,
    cited_payload,
    unknown_answer,
)
from app.planner import _clean_plan, build_planner_prompt, model_for_effort
from app.ressources import get_sources, is_authorized_document


@dataclass
class D:
    centre_id: str = "casf"
    titre: str = "Fiche officielle"
    centre_nom: str = "Centre autorisé"
    url: str = "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000000000001"
    passages: list[str] = field(
        default_factory=lambda: [
            "Le service coordonne les intervenants et élabore avec la personne un projet individualisé."
        ]
    )


def test_planner_is_limited_to_internal_retrieval_queries():
    plan = _clean_plan(
        {
            "audience": "pro",
            "profession": "assistante sociale",
            "intent": "orientation",
            "effort": "large",
            "resource_queries": [
                "maladie de Charcot SLA orientation centre expert",
                "SLA accompagnement médico-social adolescent",
            ],
            "casf_queries": ["coordination parcours handicap projet personnalisé"],
            "missing_field": "department",
            # Un plan d'action produit à l'étape libre ne doit jamais survivre.
            "answer": "Contactez immédiatement la MDPH",
            "steps": ["Déposer un dossier"],
        },
        fallback_question="question originale",
    )

    assert set(plan) == {
        "audience",
        "profession",
        "intent",
        "effort",
        "resource_queries",
        "casf_queries",
        "missing_field",
    }
    assert "answer" not in plan and "steps" not in plan
    assert plan["resource_queries"][0].startswith("maladie de Charcot")


def test_planner_requires_subject_for_an_unspecified_gene_mutation():
    plan = _clean_plan(
        {
            "resource_queries": ["mutation génétique orientation"],
            "casf_queries": ["maladie génétique"],
            "missing_field": "department",
        },
        fallback_question="mon fils a une mutation de gene comment l orienter",
    )

    assert plan["missing_field"] == "subject"


def test_answer_asks_for_unspecified_gene_before_retrieval(monkeypatch):
    calls: list[str] = []

    async def fake_plan(*args, **kwargs):
        return _clean_plan(
            {
                "resource_queries": ["mutation génétique orientation"],
                "casf_queries": ["maladie génétique"],
                "missing_field": "",
            },
            fallback_question="mon fils a une mutation de gene comment l orienter",
        )

    async def fake_research(*args, **kwargs):
        calls.append("research")
        return []

    monkeypatch.setattr(main.planner, "plan_question", fake_plan)
    monkeypatch.setattr(main.research, "research_queries", fake_research)
    monkeypatch.setattr(main.annuaire, "esms_passages", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.corpus, "corpus_search", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.casf, "search", lambda *args, **kwargs: [])

    answer = asyncio.run(
        main._answer(
            main.ChatRequest(
                question="mon fils a une mutation de gene comment l orienter",
                profile="famille",
            ),
            falc=False,
        )
    )

    assert calls == []
    assert answer["unknown"] is True
    assert answer["paras"] == []
    assert answer["followup"] == (
        "Quel est le nom précis du gène, de la maladie ou du dispositif concerné ?"
    )


def test_planner_prompt_allows_understanding_but_forbids_action_plan():
    prompt = build_planner_prompt(
        "Que signifie cette mutation de gène ?",
        profile="pro",
        dept=None,
        situations=[],
        age=None,
        history=[],
    )
    low = prompt.lower()
    assert "connaissance générale" in low
    assert "uniquement" in low and "requêtes" in low
    assert "aucun plan d'action" in low
    assert "ne sera jamais transmis" in low


@pytest.mark.parametrize(
    ("effort", "expected"),
    [
        ("small", "mistral-small-latest"),
        ("medium", "mistral-medium-latest"),
        ("large", "mistral-large-latest"),
        ("invalid", "mistral-medium-latest"),
    ],
)
def test_model_is_selected_from_effort(effort, expected, monkeypatch):
    monkeypatch.delenv("CHAT_MODEL_SMALL", raising=False)
    monkeypatch.delenv("CHAT_MODEL_MEDIUM", raising=False)
    monkeypatch.delenv("CHAT_MODEL_LARGE", raising=False)
    assert model_for_effort(effort) == expected


def test_clean_rejects_every_item_without_exact_evidence():
    docs = [D()]
    data = {
        "unknown": False,
        "paras": [
            {
                "text": "Le service construit un projet individualisé avec la personne.",
                "source_ids": [1],
                "quotes": [
                    "Le service coordonne les intervenants et élabore avec la personne un projet individualisé."
                ],
            },
            {
                "text": "Une affirmation inventée.",
                "source_ids": [1],
                "quotes": ["Cette citation n'existe pas dans les passages."],
            },
            {
                "text": "La Lune est en fromage.",
                "source_ids": [1],
                "quotes": ["coordonne les intervenants"],
            },
            {"text": "Une affirmation sans preuve.", "source_ids": [], "quotes": []},
        ],
        "steps": [
            {
                "t": "Construire le projet",
                "d": "Coordonner les intervenants avec la personne.",
                "source_ids": [1],
                "quotes": ["coordonne les intervenants"],
            },
            {
                "t": "Action inventée",
                "d": "Faire une démarche absente des sources.",
                "source_ids": [1],
                "quotes": ["démarche absente"],
            },
        ],
        "contacts": [
            {
                "nom": "Centre autorisé",
                "role": "Coordonne les intervenants.",
                "scope": "National",
                "url": "https://evil.example",
                "source_id": 1,
                "quote": "coordonne les intervenants",
            },
            {
                "nom": "Contact inventé",
                "role": "Rôle inventé.",
                "scope": "National",
                "source_id": 8,
                "quote": "Rôle inventé",
            },
        ],
        "followup": "Dans quel département intervenez-vous ?",
    }

    answer = _clean(data, docs)

    assert len(answer["paras"]) == 1
    assert answer["paras"][0].endswith("[1]")
    assert len(answer["steps"]) == 1
    assert answer["steps"][0]["d"].endswith("[1]")
    assert len(answer["contacts"]) == 1
    assert answer["contacts"][0]["url"] == docs[0].url
    assert answer["contacts"][0]["role"].endswith("[1]")
    assert answer["unknown"] is False
    assert [s["n"] for s in cited_payload(answer, docs)] == [1]


def test_clean_keeps_only_sources_that_individually_support_the_claim():
    docs = [
        D(),
        D(
            centre_id="has",
            centre_nom="HAS",
            url="https://www.has-sante.fr/fiche",
            passages=["Un texte officiel totalement étranger sur la procédure administrative."],
        ),
    ]
    answer = _clean(
        {
            "paras": [
                {
                    "text": "Le service coordonne les intervenants avec la personne.",
                    "source_ids": [1, 2],
                    "quotes": [
                        "coordonne les intervenants",
                        "Un texte officiel totalement étranger sur la procédure administrative.",
                    ],
                }
            ]
        },
        docs,
    )

    assert answer["paras"] == [
        "Le service coordonne les intervenants avec la personne. [1]"
    ]


def test_clean_strips_model_supplied_markers_before_adding_verified_citations():
    answer = _clean(
        {
            "unknown": False,
            "paras": [
                {
                    "text": (
                        "Le service coordonne les intervenants et élabore avec la personne "
                        "un projet individualisé [99] [1a] https://evil.example/faux."
                    ),
                    "source_ids": [1],
                    "quotes": [
                        "Le service coordonne les intervenants et élabore avec la personne un projet individualisé."
                    ],
                }
            ],
            "steps": [],
            "contacts": [],
        },
        [D()],
    )

    assert "[99]" not in answer["paras"][0]
    assert "[1a]" not in answer["paras"][0]
    assert "evil.example" not in answer["paras"][0]
    assert answer["paras"][0].endswith("[1]")


def test_clean_fails_closed_when_nothing_is_supported():
    answer = _clean(
        {
            "unknown": False,
            "paras": [
                {
                    "text": "La Lune est en fromage.",
                    "source_ids": [1],
                    "quotes": ["preuve absente"],
                }
            ],
            "steps": [],
            "contacts": [],
            "followup": "Quel est le nom du gène concerné ?",
        },
        [D()],
    )
    assert answer["unknown"] is True
    assert answer["paras"] == []
    assert answer["steps"] == []
    assert answer["contacts"] == []
    assert answer["followup"] == "Quel est le nom du gène concerné ?"


def test_verified_corpus_routes_charcot_to_the_has_care_pathway():
    docs = corpus.corpus_search(
        ["maladie", "charcot", "sclérose", "latérale", "amyotrophique", "sla"]
    )

    assert docs
    assert docs[0].centre_nom == "HAS — Haute Autorité de Santé"
    assert docs[0].url == (
        "https://www.has-sante.fr/jcms/c_2573383/fr/sclerose-laterale-amyotrophique"
    )
    assert "parcours de soins" in " ".join(docs[0].passages)


def test_synthesis_prompt_requires_literal_quotes_for_every_output_item():
    prompt = _system_prompt("pro", False, None, [], None, [D()])
    low = prompt.lower()
    assert "extrait exact" in low
    assert '"source_ids"' in prompt
    assert '"quotes"' in prompt
    assert "contacts de repère" not in low
    assert "connaissance générale" in low and "interdite" in low


def test_assistant_history_never_reaches_grounded_synthesis():
    messages = build_messages(
        "Et dans le Nord ?",
        system_prompt="SYSTEM",
        history=[
            {"role": "user", "content": "Je cherche un SESSAD."},
            {"role": "assistant", "content": "Ancienne réponse potentiellement fausse."},
        ],
    )
    joined = "\n".join(str(m["content"]) for m in messages)
    assert "Je cherche un SESSAD" in joined
    assert "Ancienne réponse potentiellement fausse" not in joined


def test_unknown_answer_never_injects_unsourced_content_or_default_contacts():
    answer = unknown_answer("question", [], profile="famille", followup="Pouvez-vous préciser le sujet ?")
    assert answer["unknown"] is True
    assert answer["paras"] == []
    assert answer["contacts"] == []
    assert answer["steps"] == []
    assert answer["followup"] == "Pouvez-vous préciser le sujet ?"


def test_answer_uses_plan_only_for_retrieval_not_synthesis(monkeypatch):
    seen = {}

    async def fake_plan(*args, **kwargs):
        return {
            "audience": "pro",
            "profession": "assistante sociale",
            "intent": "orientation",
            "effort": "large",
            "resource_queries": ["maladie de Charcot SLA orientation"],
            "casf_queries": ["coordination parcours handicap enfant"],
            "missing_field": "department",
        }

    async def fake_research(queries, extra_context, timeout=12.0):
        seen["resource_queries"] = queries
        return []

    def fake_casf(queries, limit=4):
        seen["casf_queries"] = queries
        return [D()]

    async def fake_synthesize(question, docs, **kwargs):
        seen["synthesis_kwargs"] = kwargs
        seen["synthesis_docs"] = docs
        return {
            "unknown": False,
            "paras": ["Réponse fondée sur le document [1]"],
            "steps": [],
            "contacts": [],
            "followup": "",
        }

    monkeypatch.setattr(main.planner, "plan_question", fake_plan)
    monkeypatch.setattr(main.research, "research_queries", fake_research)
    monkeypatch.setattr(main.casf, "search", fake_casf)
    monkeypatch.setattr(main.annuaire, "esms_passages", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.corpus, "corpus_search", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.agent, "synthesize", fake_synthesize)

    req = main.ChatRequest(
        question="Je suis assistante sociale : comment orienter cet adolescent atteint de la maladie de Charcot ?",
        profile="pro",
    )
    answer = asyncio.run(main._answer(req, falc=False))

    assert seen["resource_queries"] == ["maladie de Charcot SLA orientation"]
    assert seen["casf_queries"] == ["coordination parcours handicap enfant"]
    assert seen["synthesis_kwargs"]["effort"] == "large"
    assert "plan" not in seen["synthesis_kwargs"]
    assert "SLA" not in repr(seen["synthesis_kwargs"])
    assert answer["unknown"] is False


def test_research_queries_fans_out_planner_queries_in_parallel(monkeypatch):
    calls = []
    sites = [
        {"id": "a", "nom": "A", "url": "https://a.example", "search_url": "https://a.example/?q={q}"},
        {"id": "b", "nom": "B", "url": "https://b.example", "search_url": "https://b.example/?q={q}"},
    ]

    async def fake_research_one(client, site, question, kws):
        calls.append((site["id"], question, tuple(kws)))
        return [
            research.Doc(
                centre_id=site["id"],
                centre_nom=site["nom"],
                url=f"https://{site['id']}.example/{question.split()[0]}",
                titre=question,
                passages=["passage vérifié suffisamment long"],
                score=10,
            )
        ]

    monkeypatch.setattr(research, "SITES", sites)
    monkeypatch.setattr(research, "research_one", fake_research_one)
    docs = asyncio.run(research.research_queries(["SLA orientation", "centre expert"], []))

    assert {(site, query) for site, query, _ in calls} == {
        ("a", "SLA orientation"),
        ("b", "SLA orientation"),
        ("a", "centre expert"),
        ("b", "centre expert"),
    }
    assert len(docs) == 4


def test_source_registry_explicitly_allows_casf_and_finess_only_on_canonical_domains():
    ids = {source["id"] for source in get_sources()}
    assert {"casf", "finess"}.issubset(ids)
    assert is_authorized_document(
        "casf", "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000000000001"
    )
    assert is_authorized_document("finess", "https://finess.esante.gouv.fr/")
    assert not is_authorized_document("casf", "https://evil.example/faux-article")
    assert not is_authorized_document("unknown", "https://evil.example/")


def test_unauthorized_documents_are_removed_before_synthesis():
    good = D()
    bad = D(centre_id="unknown", url="https://evil.example/faux")
    assert main._authorized_docs([good, bad]) == [good]


def test_fetch_rejects_a_redirect_outside_the_source_allowlist():
    async def scenario():
        async def handler(request):
            if request.url.host == "centre.example":
                return httpx.Response(
                    302, headers={"location": "https://evil.example/injection"}
                )
            return httpx.Response(200, text="contenu non autorisé")

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ) as client:
            return await research.fetch(
                client, "https://centre.example/fiche", ["centre.example"]
            )

    assert asyncio.run(scenario()) == ("", "")
