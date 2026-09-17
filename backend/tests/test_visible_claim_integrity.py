"""Visible numeric claims must agree with their otherwise valid evidence."""

import asyncio

import pytest
from test_falc_grounding import document, fake_mistral

from app import agent


@pytest.mark.parametrize("group,field", [
    ("paras", "text"), ("steps", "t"), ("contacts", "nom"), ("contacts", "role"),
])
@pytest.mark.parametrize("source_value,visible_value", [
    ("≥ 80 %", "≤ 80 %"), (">= 80 %", "< 80 %"),
    ("≥ 80 %", "80 %"), ("≥ 80 %", "≥ 81 %"),
    ("1,5 %", "1 5 %"), ("1,5 %", "1.5 %"),
    ("-5 %", "5 %"), ("80 %", "80"),
])
def test_altered_visible_quantity_is_not_published(group, field, source_value, visible_value):
    quote = f"Un taux {source_value} est nécessaire pour cette aide."
    visible = f"Un taux {visible_value} est nécessaire pour cette aide."
    item: dict = {"paras": {"text": quote}, "steps": {"t": quote, "d": quote},
            "contacts": {"nom": "Taux nécessaire", "role": quote}}[group]
    item.update({field: visible, "source_ids": [1], "quotes": [quote]})
    doc = document(quote)

    answer = agent._clean({group: [item]}, [doc])

    if group == "steps":
        assert answer["steps"] == [{"t": doc.titre, "d": f"{quote} [1]"}]
    else:
        assert answer[group] == []
        assert answer["unknown"] is True


@pytest.mark.parametrize("value", ["≥ 80 %", ">= 80 %", "1,5 %", "-5 %"])
def test_unchanged_visible_quantities_remain_supported(value):
    quote = f"Un taux {value} est nécessaire pour cette aide."
    answer = agent._clean({"paras": [{"text": quote, "source_ids": [1], "quotes": [quote]}]},
                          [document(quote)])
    assert answer["paras"] == [f"{quote} [1]"]
    assert answer["unknown"] is False


@pytest.mark.parametrize("group", ["paras", "steps"])
@pytest.mark.parametrize("quoted_amount", [False, True])
def test_falc_numeric_clause_is_rejected_or_verified_intact(monkeypatch, group, quoted_amount):
    base = "Le service accueille les familles."
    quote = f"{base} 1000 €." if quoted_amount else base
    item: dict = {"text": f"{base} 1000 €."} if group == "paras" else {"t": "1000 €", "d": base}
    item.update(source_ids=[1], quotes=[quote])
    data = {"unknown": False, "paras": [], "steps": [], "contacts": [], "followup": ""}
    data[group] = [item]
    calls = fake_mistral(monkeypatch, [data, data])
    if quoted_amount:
        answer = asyncio.run(agent.synthesize("Une aide ?", [document(quote)], falc=True))
        assert answer["unknown"] is False
        claims = calls["verification"][0]["claims"]
        assert any(claim["claim"] in {"1000 €", "1000 €."} for claim in claims)
    else:
        with pytest.raises(agent.SynthesisError, match="invalid_falc_response"):
            asyncio.run(agent.synthesize("Une aide ?", [document(quote)], falc=True))
        assert len(calls["generation"]) == 2
        assert calls["verification"] == []


@pytest.mark.parametrize("text", ["1000 €", "1000 €.", "80 %.", "-5 %.", "Oui."])
def test_claim_parts_never_erase_nonempty_visible_clauses(text):
    assert agent._claim_parts({"text": text}) == [text]


@pytest.mark.parametrize("profile", ["famille", "pro"])
def test_explicit_empty_falc_abstention_needs_no_verifier_or_retry(monkeypatch, profile):
    data = {"unknown": True, "paras": [], "steps": [], "contacts": [],
            "followup": "Quel besoin précisez-vous ?"}
    calls = fake_mistral(monkeypatch, [data, data])
    answer = asyncio.run(agent.synthesize("Une aide ?", [document()], profile=profile, falc=True))
    assert answer == data
    assert len(calls["generation"]) == 1
    assert calls["verification"] == []


@pytest.mark.parametrize("unknown", [False, True])
def test_nonempty_rejected_falc_output_is_not_honest_abstention(monkeypatch, unknown):
    quote = "Le service accueille les familles."
    data = {"unknown": unknown, "paras": [{"text": "Un taux ≥ 80 % est nécessaire.",
                                           "source_ids": [1], "quotes": [quote]}],
            "steps": [], "contacts": [], "followup": "Quel besoin précisez-vous ?"}
    calls = fake_mistral(monkeypatch, [data, data])
    with pytest.raises(agent.SynthesisError, match="invalid_falc_response"):
        asyncio.run(agent.synthesize("Une aide ?", [document(quote)], falc=True))
    assert len(calls["generation"]) == 2
    assert calls["verification"] == []
