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
        "resource_topics",
        "casf_topics",
        "resource_queries",
        "casf_queries",
        "missing_field",
    }
    assert "answer" not in plan and "steps" not in plan
    assert plan["resource_queries"][0].startswith("maladie de Charcot")


def test_planner_does_not_override_whole_situation_from_one_keyword():
    plan = _clean_plan(
        {
            "resource_queries": ["accompagnement familial après annonce médicale"],
            "casf_queries": ["évaluation besoins projet de vie"],
            "missing_field": "situation",
        },
        fallback_question="mon fils a une mutation de gene comment l orienter",
    )

    assert plan["missing_field"] == "situation"


def test_planner_keeps_only_controlled_retrieval_facets():
    plan = _clean_plan(
        {
            "resource_topics": [
                "family_support",
                "mdph_assessment",
                "schooling",
                "invented_diagnosis",
            ],
            "casf_topics": [
                "disability_definition",
                "needs_assessment",
                "cdaph_decisions",
                "invented_article",
            ],
        },
        fallback_question="accompagnement professionnel d'une famille",
        profile="pro",
    )

    assert plan["resource_topics"] == [
        "family_support",
        "mdph_assessment",
        "schooling",
    ]
    assert plan["casf_topics"] == [
        "disability_definition",
        "needs_assessment",
        "cdaph_decisions",
    ]


def test_planner_prompt_requires_whole_situation_and_distinct_facets():
    prompt = build_planner_prompt(
        "Je suis assistante sociale et j'accompagne une famille après une annonce médicale",
        profile="pro",
        dept=None,
        situations=[],
        age="adolescent",
        history=[],
    ).casefold()

    assert "situation dans son ensemble" in prompt
    assert "rôle du demandeur" in prompt
    assert "étape du parcours" in prompt
    assert "conséquences fonctionnelles" in prompt
    assert "resource_topics" in prompt
    assert "casf_topics" in prompt
    assert "prestations pour enfant" in prompt
    assert "child_benefits" in prompt


def test_answer_uses_available_professional_guidance_before_asking_for_details(monkeypatch):
    calls: list[str] = []

    async def fake_plan(*args, **kwargs):
        return {
            "audience": "pro",
            "profession": "assistante sociale",
            "intent": "orientation",
            "effort": "large",
            "resource_topics": [
                "family_support",
                "mdph_assessment",
                "schooling",
                "child_benefits",
            ],
            "casf_topics": [
                "disability_definition",
                "needs_assessment",
                "cdaph_decisions",
            ],
            "resource_queries": [
                "évaluation conséquences quotidiennes scolarité handicap",
            ],
            "casf_queries": [
                "équipe pluridisciplinaire évalue besoins projet de vie",
                "commission droits autonomie prestations orientation scolarisation",
            ],
            "missing_field": "subject",
        }

    async def fake_research(*args, **kwargs):
        calls.append("research")
        return []

    async def fake_synthesize(*args, **kwargs):
        calls.append("synthesize")
        assert len(args[1]) == 2
        return {
            "unknown": False,
            "paras": ["L’évaluation porte sur les besoins concrets de l’adolescent. [1]"],
            "steps": [
                {
                    "t": "Documenter les besoins",
                    "d": "Recueillir les conséquences familiales, scolaires et psychologiques. [2]",
                }
            ],
            "contacts": [],
            "followup": (
                "Quel diagnostic est associé à la mutation, quelles conséquences sont déjà "
                "observées et dans quel département vit la famille ?"
            ),
        }

    def fake_topic_documents(topics, max_docs=8):
        calls.append("resource_topics")
        assert "mdph_assessment" in topics
        assert max_docs >= 10
        return [D()]

    def fake_casf_topics(topics, limit=8):
        calls.append("casf_topics")
        assert "needs_assessment" in topics
        return [
            D(
                centre_id="casf",
                titre="CASF — évaluation des besoins",
                url=(
                    "https://www.legifrance.gouv.fr/codes/article_lc/"
                    "LEGIARTI000000000002"
                ),
                passages=[
                    (
                        "L'équipe pluridisciplinaire évalue les besoins en tenant compte de la "
                        "situation familiale, sanitaire, scolaire et psychologique."
                    )
                ],
            )
        ]

    monkeypatch.setattr(main.planner, "plan_question", fake_plan)
    monkeypatch.setattr(main.research, "research_queries", fake_research)
    monkeypatch.setattr(main.agent, "synthesize", fake_synthesize)
    monkeypatch.setattr(main.annuaire, "esms_passages", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.corpus, "topic_documents", fake_topic_documents)
    monkeypatch.setattr(main.casf, "search_topics", fake_casf_topics)
    monkeypatch.setattr(main.corpus, "corpus_search", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.casf, "search", lambda *args, **kwargs: [])

    answer = asyncio.run(
        main._answer(
            main.ChatRequest(
                question=(
                    "je suis assistante social comment puis je accompagné une famille dont "
                    "l'adolescent vient d'apprendre qu'il a une mutation génétique"
                ),
                profile="pro",
            ),
            falc=False,
        )
    )

    assert calls == ["resource_topics", "casf_topics", "research", "synthesize"]
    assert answer["unknown"] is False
    assert answer["paras"]
    assert answer["steps"]
    assert "diagnostic" in answer["followup"]
    assert "conséquences" in answer["followup"]
    assert "département" in answer["followup"]


def test_professional_synthesis_prompt_requires_practical_conditional_guidance():
    prompt = _system_prompt(
        "pro",
        False,
        dept=None,
        situations=[],
        age="adolescent",
        docs=[D()],
    ).casefold()

    assert "première orientation utile" in prompt
    assert "qui fait quoi" in prompt
    assert "branches conditionnelles" in prompt
    assert "conséquences fonctionnelles" in prompt
    assert "deux à quatre questions" in prompt
    assert "n'assimile jamais un résultat génétique à un handicap" in prompt
    assert "ne lui propose pas de contacter la mdph" not in prompt


def test_synthesis_prompt_requires_validator_compatible_atomic_evidence():
    prompt = _system_prompt(
        "pro",
        False,
        dept=None,
        situations=[],
        age="adolescent",
        docs=[D()],
    ).casefold()

    assert "caractère pour caractère" in prompt
    assert "passage contigu" in prompt
    assert "aucune ellipse" in prompt
    assert "une seule affirmation atomique" in prompt
    assert "exactement une phrase" in prompt
    assert "un seul passage par chaîne" in prompt
    assert "le champ d est une copie exacte" in prompt
    assert "le champ role est une copie exacte" in prompt
    assert "strictement identiques" in prompt
    assert "une seule source par élément" in prompt
    assert "sans minimum ni quota de sources" in prompt
    assert "aeeh et pch" in prompt and "étapes distinctes" in prompt
    assert "pertinents pour la demande" in prompt
    assert "ne change ni les apostrophes" in prompt


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


def test_followup_keeps_all_targeted_professional_questions():
    followup = (
        "Quel diagnostic ou quelle pathologie est associé à la mutation ? "
        "Quelles conséquences concrètes sont déjà observées sur l’autonomie, les soins et "
        "la vie familiale ? Quelles difficultés ou quels aménagements existent actuellement "
        "dans la scolarité ? Quels accompagnements sont déjà mobilisés et dans quel "
        "département la famille réside-t-elle ?"
    )
    answer = _clean(
        {
            "paras": [
                {
                    "text": "Le service coordonne les intervenants.",
                    "source_ids": [1],
                    "quotes": ["Le service coordonne les intervenants"],
                }
            ],
            "steps": [],
            "contacts": [],
            "followup": followup,
        },
        [D()],
    )

    assert answer["followup"] == followup


def test_synthesis_reserves_enough_tokens_for_a_professional_plan(monkeypatch):
    captured = {}

    class FakeChat:
        async def complete_async(self, **kwargs):
            captured.update(kwargs)
            message = type(
                "Message",
                (),
                {
                    "content": (
                        '{"unknown":true,"paras":[],"steps":[],"contacts":[],'
                        '"followup":""}'
                    )
                },
            )()
            return type("Response", (), {"choices": [type("Choice", (), {"message": message})()]})()

    class FakeMistral:
        def __init__(self, **kwargs):
            self.chat = FakeChat()

    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr(main.agent, "Mistral", FakeMistral)

    asyncio.run(main.agent.synthesize("question", [D()], profile="pro", effort="large"))

    assert captured["max_tokens"] >= 6000
    assert captured["temperature"] == 0.0


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
                "quotes": [
                    "Le service coordonne les intervenants et élabore avec la personne un projet individualisé."
                ],
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
                "nom": "Service",
                "role": "Coordonne les intervenants.",
                "scope": "National",
                "url": "https://evil.example",
                "source_id": 1,
                "quote": "Le service coordonne les intervenants",
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


def test_clean_rejects_a_supported_sentence_followed_by_an_invention():
    answer = _clean(
        {
            "paras": [
                {
                    "text": (
                        "Le service coordonne les intervenants avec la personne. "
                        "La Lune est constituée de fromage."
                    ),
                    "source_ids": [1],
                    "quotes": ["Le service coordonne les intervenants"],
                }
            ]
        },
        [D()],
    )

    assert answer["paras"] == []
    assert answer["unknown"] is True


def test_clean_rejects_a_contact_role_absent_from_the_quote():
    docs = [
        D(
            centre_id="corpus-rare-centres",
            centre_nom="Filières maladies rares",
            url="https://www.filieresmaladiesrares.fr/annuaires-des-centres/",
            passages=[
                "Annuaire des centres de référence et de compétence maladies rares."
            ],
        )
    ]
    answer = _clean(
        {
            "contacts": [
                {
                    "nom": "Centres de référence maladies rares",
                    "role": "Coordonnent les soins et établissent les protocoles thérapeutiques.",
                    "scope": "National",
                    "source_id": 1,
                    "quote": "Annuaire des centres de référence et de compétence maladies rares.",
                }
            ]
        },
        docs,
    )

    assert answer["contacts"] == []
    assert answer["unknown"] is True


def test_clean_accepts_only_typographic_apostrophe_normalization():
    docs = [
        D(passages=["Le médecin apporte une aide et l’accompagnement nécessaire."])
    ]
    answer = _clean(
        {
            "paras": [
                {
                    "text": "Le médecin apporte l'accompagnement nécessaire.",
                    "source_ids": [1],
                    "quotes": [
                        "Le médecin apporte une aide et l'accompagnement nécessaire."
                    ],
                }
            ]
        },
        docs,
    )

    assert answer["paras"] == [
        "Le médecin apporte l'accompagnement nécessaire. [1]"
    ]


def test_clean_preserves_eight_supported_steps_and_full_evidence():
    passages = [
        (
            "Le service coordonne les intervenants "
            + "et documente les besoins avec la personne " * 18
            + f"dans son projet individualisé numéro {index}."
        )
        for index in range(1, 9)
    ]
    docs = [D(passages=passages)]
    answer = _clean(
        {
            "steps": [
                {
                    "t": f"Coordonner les intervenants — étape {index}",
                    "d": passages[index - 1],
                    "source_ids": [1],
                    "quotes": [passages[index - 1]],
                }
                for index in range(1, 9)
            ]
        },
        docs,
    )

    assert len(answer["steps"]) == 8
    assert answer["steps"][0]["d"] == f"{passages[0]} [1]"


def test_clean_rejects_a_period_replacing_a_comma_in_evidence():
    docs = [
        D(
            passages=[
                "La maison départementale des personnes handicapées assure à la personne handicapée et à sa famille l'aide nécessaire à la formulation de son projet de vie, l'aide nécessaire à la mise en oeuvre des décisions."
            ]
        )
    ]
    quote = (
        "La maison départementale des personnes handicapées assure à la personne handicapée "
        "et à sa famille l'aide nécessaire à la formulation de son projet de vie."
    )
    answer = _clean(
        {
            "steps": [
                {
                    "t": "Faire accompagner la formulation du projet de vie par la MDPH",
                    "d": quote,
                    "source_ids": [1],
                    "quotes": [quote],
                }
            ]
        },
        docs,
    )

    assert answer["steps"] == []
    assert answer["unknown"] is True


def test_clean_accepts_literal_quotes_with_model_source_suffixes():
    answer = _clean(
        {
            "paras": [
                {
                    "text": "Le service coordonne les intervenants avec la personne.",
                    "source_ids": [1],
                    "quotes": ["Le service coordonne les intervenants (source 1)"],
                }
            ]
        },
        [D()],
    )

    assert answer["paras"] == [
        "Le service coordonne les intervenants avec la personne. [1]"
    ]


def test_clean_renders_step_detail_from_literal_evidence_not_paraphrase():
    passage = (
        "La commission des droits et de l'autonomie des personnes handicapées "
        "prend les décisions relatives aux prestations."
    )
    answer = _clean(
        {
            "steps": [
                {
                    "t": "Identifier le décideur des prestations",
                    "d": "La CDAPH décide seule de tous les droits demandés par la famille.",
                    "source_ids": [1],
                    "quotes": [passage],
                }
            ]
        },
        [D(passages=[passage])],
    )

    assert answer["steps"][0]["d"] == f"{passage} [1]"
    assert "tous les droits" not in answer["steps"][0]["d"]


def test_clean_splits_a_composite_step_into_one_step_per_source():
    docs = [
        D(
            passages=[
                "L'équipe pluridisciplinaire évalue les besoins de compensation sur la base du projet de vie."
            ]
        ),
        D(
            centre_id="corpus-mdph-daily-life",
            centre_nom="Maladies Rares Info Services",
            url="https://www.maladiesraresinfo.org/mdph",
            passages=[
                "La rubrique vie quotidienne décrit les difficultés et les attentes de la personne."
            ],
        ),
        D(
            centre_id="corpus-pps",
            centre_nom="Mon parcours handicap",
            url="https://www.monparcourshandicap.gouv.fr/pps",
            passages=[
                "Le projet personnalisé de scolarisation définit les aménagements répondant aux besoins de l'élève."
            ],
        ),
    ]
    answer = _clean(
        {
            "steps": [
                {
                    "t": "Documenter les besoins et la scolarité",
                    "d": (
                        "Faites évaluer les besoins de compensation à partir du projet de vie, "
                        "décrivez les difficultés quotidiennes et mobilisez les aménagements "
                        "scolaires répondant aux besoins de l'élève."
                    ),
                    "source_ids": [1, 2, 3],
                    "quotes": [
                        "L'équipe pluridisciplinaire évalue les besoins de compensation sur la base du projet de vie.",
                        "La rubrique vie quotidienne décrit les difficultés et les attentes de la personne.",
                        "Le projet personnalisé de scolarisation définit les aménagements répondant aux besoins de l'élève.",
                    ],
                }
            ]
        },
        docs,
    )

    assert len(answer["steps"]) == 3
    assert [step["d"].rsplit(" ", 1)[-1] for step in answer["steps"]] == [
        "[1]",
        "[2]",
        "[3]",
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


def test_resource_topics_return_diverse_professional_evidence():
    docs = corpus.corpus_search(
        ["mutation", "génétique", "adolescent", "résultat"], max_docs=2
    ) + corpus.topic_documents(
        [
            "family_support",
            "expert_centres",
            "mdph_assessment",
            "daily_life_impact",
            "schooling",
            "child_benefits",
        ],
        max_docs=12,
    )

    urls = {doc.url for doc in docs}
    assert "https://genetique-medicale.fr/parcours-de-soins-en-genetique/" in urls
    assert "https://genetique-medicale.fr/professionnels-de-la-genetique-medicale/" in urls
    assert "https://www.filieresmaladiesrares.fr/annuaires-des-centres/" in urls
    assert (
        "https://parcourssantevie.maladiesraresinfo.org/pages/"
        "comment-faire-une-demande-aupres-de-la-MDPH.html"
    ) in urls
    assert (
        "https://www.monparcourshandicap.gouv.fr/scolarite/"
        "quest-ce-que-le-pps-projet-personnalise-de-scolarisation"
    ) in urls
    assert any("AEEH" in doc.titre for doc in docs)
    assert any("PCH" in doc.titre for doc in docs)
    assert all(doc.centre_id.startswith("corpus-") for doc in docs)
    assert all(is_authorized_document(doc.centre_id, doc.url) for doc in docs)


def test_generic_medical_topics_do_not_inject_genetic_documents():
    generic = corpus.topic_documents(
        ["medical_context", "family_support", "care_coordination"], max_docs=10
    )
    specific = corpus.corpus_search(
        ["mutation", "génétique", "adolescent", "résultat"], max_docs=2
    )

    assert all("genetic" not in doc.centre_id for doc in generic)
    assert {doc.centre_id for doc in specific} == {
        "corpus-genetic_pathway",
        "corpus-genetic_professionals",
    }


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


def test_original_question_terms_survive_planner_reformulation(monkeypatch):
    seen = {}

    async def fake_plan(*args, **kwargs):
        return {
            "audience": "pro",
            "profession": "assistante sociale",
            "intent": "orientation",
            "effort": "large",
            "resource_topics": [],
            "casf_topics": [],
            "resource_queries": ["accompagnement familial global"],
            "casf_queries": [],
            "missing_field": "subject",
        }

    async def fake_research(*args, **kwargs):
        return []

    def fake_corpus_search(keywords):
        seen["keywords"] = keywords
        return [D()]

    async def fake_synthesize(*args, **kwargs):
        return {
            "unknown": False,
            "paras": ["Réponse fondée sur la source. [1]"],
            "steps": [],
            "contacts": [],
            "followup": "",
        }

    monkeypatch.setattr(main.planner, "plan_question", fake_plan)
    monkeypatch.setattr(main.research, "research_queries", fake_research)
    monkeypatch.setattr(main.corpus, "corpus_search", fake_corpus_search)
    monkeypatch.setattr(main.corpus, "topic_documents", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.casf, "search_topics", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.casf, "search", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.annuaire, "esms_passages", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.agent, "synthesize", fake_synthesize)

    request = main.ChatRequest(
        question=(
            "Je suis assistante sociale et l'adolescent vient d'apprendre "
            "qu'il a une mutation génétique."
        ),
        profile="pro",
    )
    asyncio.run(main._answer(request, falc=False))

    assert "mutation" in seen["keywords"]
    assert "génétique" in seen["keywords"]
    assert "global" in seen["keywords"]


def test_specific_corpus_evidence_is_not_crowded_out_by_facets(monkeypatch):
    seen = {}

    async def fake_plan(*args, **kwargs):
        return {
            "audience": "pro",
            "profession": "assistante sociale",
            "intent": "orientation",
            "effort": "large",
            "resource_topics": [
                "medical_context",
                "family_support",
                "expert_centres",
                "mdph_assessment",
                "schooling",
                "child_benefits",
                "establishment_search",
                "caregiver_support",
            ],
            "casf_topics": [
                "disability_definition",
                "needs_assessment",
                "pch",
                "mdph_missions",
                "right_to_compensation",
                "cdaph_decisions",
            ],
            "resource_queries": ["maladie de Charcot SLA orientation"],
            "casf_queries": [],
            "missing_field": "department",
        }

    async def fake_research(*args, **kwargs):
        return []

    async def fake_synthesize(question, docs, **kwargs):
        seen["docs"] = docs
        return {
            "unknown": False,
            "paras": ["Réponse fondée sur le document [1]"],
            "steps": [],
            "contacts": [],
            "followup": "",
        }

    monkeypatch.setattr(main.planner, "plan_question", fake_plan)
    monkeypatch.setattr(main.research, "research_queries", fake_research)
    monkeypatch.setattr(main.annuaire, "esms_passages", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.casf, "search", lambda *args, **kwargs: [])
    monkeypatch.setattr(main.agent, "synthesize", fake_synthesize)

    request = main.ChatRequest(
        question="Comment orienter un adolescent atteint de la maladie de Charcot ?",
        profile="pro",
    )
    asyncio.run(main._answer(request, falc=False))

    assert any(doc.centre_id == "corpus-sla" for doc in seen["docs"])


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
