"""Offline reproductions of review defects; only the model boundary is mocked."""

import asyncio

import pytest
from test_falc_grounding import document, fake_mistral

from app import agent


@pytest.mark.parametrize("source_operator,quote_operator", [("≥", "≤"), (">=", "<="), (">", "<"), ("≥", "")])
def test_reversed_or_removed_eligibility_operator_is_not_published(source_operator, quote_operator):
    source = f"Un taux {source_operator} 80 % est nécessaire pour cette aide."
    quote = f"Un taux {quote_operator} 80 % est nécessaire pour cette aide."
    answer = agent._clean({
        "steps": [{"t": "Taux nécessaire pour cette aide", "d": quote,
                   "source_ids": [1], "quotes": [quote]}],
    }, [document(source)])
    assert answer["unknown"] is True
    assert answer["steps"] == []


def test_evidence_does_not_turn_decimal_comma_into_word_separator():
    quote = "Un taux de 1 5 % est nécessaire pour cette aide."
    answer = agent._clean({"steps": [{"t": "Taux nécessaire", "d": quote,
                                       "source_ids": [1], "quotes": [quote]}]},
                          [document("Un taux de 1,5 % est nécessaire pour cette aide.")])
    assert answer["steps"] == []


def _retrieved_packet():
    return [document("Le service accueille les familles.", centre_id=centre_id,
                     titre=title) for centre_id, title in [
        ("corpus-other", "Autre service"),
        ("corpus-mdph", "MDPH"), ("corpus-pps", "PPS"),
        ("corpus-aeeh_child", "AEEH"), ("corpus-pch_child", "PCH"),
        ("casf", "CASF — article L146-3"), ("casf", "CASF — article L146-8"),
    ]]


def test_professional_abstention_adds_no_retrieved_artifacts(monkeypatch):
    data = {"unknown": True, "paras": [], "steps": [], "contacts": [], "followup": ""}
    calls = fake_mistral(monkeypatch, [data])
    answer = asyncio.run(agent.synthesize("Quels horaires d'ouverture ?", _retrieved_packet(), profile="pro"))
    assert answer == data
    assert len(calls["generation"]) == 1


def test_professional_keeps_model_selected_daily_life_steps_without_source_quota(monkeypatch):
    passages = ["La rubrique vie quotidienne décrit les difficultés de la personne.",
                "Le formulaire précise les attentes de la famille."]
    docs = [document(passages=passages, centre_id="corpus-mdph")] + _retrieved_packet()
    data = {"unknown": False, "paras": [], "contacts": [], "followup": "Quel besoin précisez-vous ?",
            "steps": [{"t": text, "d": text, "source_ids": [1], "quotes": [text]} for text in passages]}
    fake_mistral(monkeypatch, [data])
    answer = asyncio.run(agent.synthesize("Comment remplir la vie quotidienne ?", docs, profile="pro"))
    assert answer == agent._clean(data, docs)
    assert len(answer["steps"]) == 2
    assert [s["n"] for s in agent.cited_payload(answer, docs)] == [1]


def test_professional_prompt_has_no_presence_based_legal_or_step_quota():
    prompt = agent._system_prompt("pro", False, None, [], None, _retrieved_packet()).casefold()
    assert "au moins deux étapes" not in prompt
    assert "cinq à huit étapes" not in prompt
    assert "seulement si" in prompt and "pertinents pour la demande" in prompt


@pytest.mark.parametrize("falc", [False, True])
def test_synthesis_accepts_bounded_question_list_as_followup(monkeypatch, falc):
    questions = ["Votre enfant a-t-il déjà un diagnostic officiel ?", "Dans quel département résidez-vous ?"]
    quote = "Le service accueille les familles."
    data = {"unknown": False, "paras": [{"text": quote, "source_ids": [1], "quotes": [quote]}],
            "steps": [], "contacts": [], "followup": questions}
    calls = fake_mistral(monkeypatch, [data])
    answer = asyncio.run(agent.synthesize("Une orientation ?", [document(quote)], falc=falc))
    assert answer["followup"] == " ".join(questions)
    assert answer["unknown"] is False
    assert answer["paras"] == [f"{quote} [1]"]
    assert len(calls["generation"]) == 1


@pytest.mark.parametrize("value", [None, 3, {}, [], [""], ["  "], ["Question ?", 1], ["Question ?"] * 5, ["x" * 801]])
def test_followup_coercion_does_not_accept_arbitrary_schema(monkeypatch, value):
    data = {"unknown": True, "paras": [], "steps": [], "contacts": [], "followup": value}
    calls = fake_mistral(monkeypatch, [data])
    with pytest.raises(agent.SynthesisError, match="invalid_synthesis_schema"):
        asyncio.run(agent.synthesize("Question ?", [document()], profile="pro"))
    assert len(calls["generation"]) == 1
    assert calls["verification"] == []
