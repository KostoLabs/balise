"""Partial FALC answers keep only wholly supported items, never clauses."""

import asyncio

import pytest
from test_falc_grounding import document, fake_mistral

from app import agent

QUOTE = "Le service accueille les familles."
OTHER_QUOTE = "Le service examine votre dossier."
LAST_QUOTE = "Le service informe les familles."
INVENTED = "Le service accepte votre dossier automatiquement."


def item(group, quote, source_id):
    fields = {
        "paras": {"text": quote},
        "steps": {"t": "Le service", "d": quote},
        "contacts": {"nom": "Le service", "role": quote},
    }
    return {**fields[group], "source_ids": [source_id], "quotes": [quote]}


def mixed_payload(group):
    data = {
        "unknown": False,
        **{key: [item(key, QUOTE, 1)] for key in ("paras", "steps", "contacts")},
        "followup": "Avez-vous besoin d'aide ?",
    }
    data[group].extend([item(group, OTHER_QUOTE, 2), item(group, LAST_QUOTE, 3)])
    return data


def assert_survivors(answer, group, docs):
    expected = {
        "paras": [f"{QUOTE} [1]"],
        "steps": [{"t": "Le service", "d": f"{QUOTE} [1]"}],
        "contacts": [{"nom": "Le service", "role": f"{QUOTE} [1]", "scope": "National", "url": docs[0].url}],
    }
    last = {
        "paras": f"{LAST_QUOTE} [3]",
        "steps": {"t": "Le service", "d": f"{LAST_QUOTE} [3]"},
        "contacts": {"nom": "Le service", "role": f"{LAST_QUOTE} [3]", "scope": "National", "url": docs[2].url},
    }
    expected[group].append(last[group])
    assert answer == {"unknown": False, **expected, "followup": "Avez-vous besoin d'aide ?"}
    assert [source["n"] for source in agent.cited_payload(answer, docs)] == [1, 3]


@pytest.mark.parametrize("group,field", [
    ("paras", "text"), ("steps", "t"), ("steps", "d"),
    ("contacts", "nom"), ("contacts", "role"),
])
def test_semantic_veto_drops_whole_item_not_supported_siblings(monkeypatch, group, field):
    data = mixed_payload(group)
    data[group][1][field] = f"{OTHER_QUOTE} {INVENTED}"
    docs = [document(QUOTE), document(OTHER_QUOTE), document(LAST_QUOTE)]
    assert agent._verified_evidence(data[group][1], docs) == [2]
    calls = fake_mistral(monkeypatch, [data, data], approve=lambda claim: "automatiquement" not in claim["claim"])

    answer = asyncio.run(agent.synthesize("Une aide ?", docs, falc=True))

    assert_survivors(answer, group, docs)
    assert len(calls["generation"]) == len(calls["verification"]) == 1
    claims = calls["verification"][0]["claims"]
    assert any(claim["claim"] == INVENTED for claim in claims)
    assert all(claim["quote"] == docs[claim["source_id"] - 1].passages[0] for claim in claims)


@pytest.mark.parametrize("group,field", [("paras", "text"), ("steps", "d"), ("contacts", "role")])
@pytest.mark.parametrize("failure", ["lexical_clause", "format", "wrong_source", "nonliteral"])
def test_invalid_item_is_skipped_without_truncating_other_items(monkeypatch, group, field, failure):
    data = mixed_payload(group)
    bad = data[group][1]
    if failure == "lexical_clause":
        bad[field] = f"{OTHER_QUOTE} Achetez une voiture rouge."
    elif failure == "format":
        bad[field] = OTHER_QUOTE.rstrip(".")
    elif failure == "wrong_source":
        bad["source_ids"] = [1]
    else:
        bad["quotes"] = ["Le service examine... votre dossier."]
    docs = [document(QUOTE), document(OTHER_QUOTE), document(LAST_QUOTE)]
    calls = fake_mistral(monkeypatch, [data, data])

    answer = asyncio.run(agent.synthesize("Une aide ?", docs, falc=True))

    assert_survivors(answer, group, docs)
    assert len(calls["generation"]) == len(calls["verification"]) == 1
    assert all(claim["source_id"] != 2 for claim in calls["verification"][0]["claims"])


@pytest.mark.parametrize("failure", ["missing_id", "duplicate_id", "unknown_id", "string_false", "integer_true"])
def test_partial_answer_still_rejects_inauthentic_verifier_bundle(monkeypatch, failure):
    data = mixed_payload("steps")
    docs = [document(QUOTE), document(OTHER_QUOTE), document(LAST_QUOTE)]

    def corrupt(content):
        checks = content["checks"]
        checks[0]["supported"] = False
        if failure == "missing_id":
            checks.pop()
        elif failure == "duplicate_id":
            checks[-1] = checks[0]
        elif failure == "unknown_id":
            checks[-1]["id"] = "paras.999.text.0"
        else:
            checks[-1]["supported"] = "false" if failure == "string_false" else 1
        return content, "stop"

    calls = fake_mistral(monkeypatch, [data, data], verification_response=corrupt)
    with pytest.raises(agent.SynthesisError, match="invalid_falc_response"):
        asyncio.run(agent.synthesize("Une aide ?", docs, falc=True))
    assert len(calls["generation"]) == len(calls["verification"]) == 2
