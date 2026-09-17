"""FALC : simplification vérifiée, sans couper ni inventer les preuves."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app import agent

# Détail de 264 caractères, citation comprise, capturé par le vrai E2E FALC.
CAPTURED_QUOTE = (
    "Le formulaire de « Demande à la MDPH » contient plusieurs rubriques. "
    "Il est recommandé de remplir avec attention toutes les rubriques en lien avec "
    "la situation de la personne en situation de handicap et notamment la rubrique "
    "« Votre vie quotidienne » (page 8)."
)
SHORT_DETAIL = "Remplissez les rubriques du formulaire qui concernent votre situation."


def document(quote=CAPTURED_QUOTE, **kwargs):
    return SimpleNamespace(
        **{
            "centre_id": "corpus-mdph-daily-life",
            "centre_nom": "Maladies Rares Info Services",
            "titre": "Comment faire une demande auprès de la MDPH ?",
            "url": (
                "https://parcourssantevie.maladiesraresinfo.org/pages/"
                "comment-faire-une-demande-aupres-de-la-MDPH.html"
            ),
            "passages": [quote],
            **kwargs,
        }
    )


def payload(detail=SHORT_DETAIL, *, quote=CAPTURED_QUOTE, source_id=2):
    return {
        "unknown": False,
        "paras": [],
        "steps": [
            {
                "t": "Remplir le formulaire",
                "d": detail,
                "source_ids": [source_id],
                "quotes": [quote],
            }
        ],
        "contacts": [],
        "followup": "Avez-vous besoin d'aide ?",
    }


def fake_mistral(monkeypatch, generations, *, approve=None, verification_response=None):
    """Seule la frontière réseau est simulée ; validation et rendu sont réels."""
    calls = {"generation": [], "verification": []}
    queue = iter(generations)

    class Chat:
        async def complete_async(self, **kwargs):
            if "VÉRIFICATEUR FALC" in kwargs["messages"][0]["content"]:
                request = json.loads(kwargs["messages"][-1]["content"])
                calls["verification"].append(request)
                content = {
                    "checks": [
                        {
                            "id": claim["id"],
                            "supported": approve(claim) if approve else True,
                        }
                        for claim in request["claims"]
                    ]
                }
                reason = "stop"
                if verification_response:
                    content, reason = verification_response(content)
            else:
                calls["generation"].append(kwargs)
                item = next(queue)
                content, reason = item if isinstance(item, tuple) else (item, "stop")
            raw = json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=raw), finish_reason=reason
                    )
                ]
            )

    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr(agent, "Mistral", lambda **kwargs: SimpleNamespace(chat=Chat()))
    return calls


def test_falc_keeps_a_verified_simplification_of_the_captured_long_detail(monkeypatch):
    docs = [document("Une autre source sans rapport."), document()]
    calls = fake_mistral(monkeypatch, [payload()])

    answer = asyncio.run(agent.synthesize("Comment remplir le formulaire ?", docs, falc=True))

    assert len(f"{CAPTURED_QUOTE} [2]") > 260
    assert answer["steps"] == [
        {"t": "Remplir le formulaire", "d": f"{SHORT_DETAIL} [2]"}
    ]
    assert answer["unknown"] is False
    assert len(calls["verification"]) == 1
    claims = calls["verification"][0]["claims"]
    assert {claim["claim"] for claim in claims} == {"Remplir le formulaire", SHORT_DETAIL}
    assert all(claim["quote"] == CAPTURED_QUOTE for claim in claims)
    assert all(claim["source_id"] == 2 for claim in claims)
    assert [source["n"] for source in agent.cited_payload(answer, docs)] == [2]


@pytest.mark.parametrize("profile", ["famille", "pro"])
def test_falc_prompt_separates_short_visible_fields_from_literal_proof(profile):
    prompt = agent._system_prompt(profile, True, None, [], None, [document()]).casefold()

    assert "240 caractères" in prompt
    assert "phrases complètes" in prompt
    assert "conditions" in prompt
    assert "sigle" in prompt and "définition" in prompt and "extrait exact" in prompt
    assert "une seule source par élément" in prompt
    assert "caractère pour caractère" in prompt
    assert "le champ d est une copie exacte" not in prompt
    assert "strictement identiques" not in prompt
    assert "cinq à huit étapes" not in prompt
    assert "au moins deux étapes" not in prompt


@pytest.mark.parametrize(
    "invalid_field",
    ["captured_detail", "cut_word", "title", "paragraph", "contact_role", "followup"],
)
def test_falc_rejects_invalid_fields_and_regenerates_only_if_needed(monkeypatch, invalid_field):
    bad = payload()
    if invalid_field == "captured_detail":
        bad["steps"][0]["d"] = CAPTURED_QUOTE
    elif invalid_field == "cut_word":
        bad["steps"][0]["d"] = SHORT_DETAIL[:-5]
    elif invalid_field == "title":
        bad["steps"][0]["t"] = CAPTURED_QUOTE
    elif invalid_field == "paragraph":
        bad["paras"] = [{"text": CAPTURED_QUOTE, "source_ids": [2], "quotes": [CAPTURED_QUOTE]}]
    elif invalid_field == "contact_role":
        bad["contacts"] = [
            {"nom": "MDPH", "role": CAPTURED_QUOTE, "source_id": 2, "quote": CAPTURED_QUOTE}
        ]
    else:
        bad["followup"] = "Avez-vous besoin d'aide pour remplir votre formulaire ? " * 6
    calls = fake_mistral(monkeypatch, [bad, payload()])
    docs = [document("Un autre passage."), document()]

    answer = asyncio.run(agent.synthesize("Comment remplir le formulaire ?", docs, falc=True))

    assert answer["steps"] == [{"t": "Remplir le formulaire", "d": f"{SHORT_DETAIL} [2]"}]
    assert answer["followup"] == "Avez-vous besoin d'aide ?"
    assert answer["paras"] == []
    assert answer["contacts"] == []
    assert len(calls["generation"]) == (1 if invalid_field in {"paragraph", "contact_role"} else 2)
    assert len(calls["verification"]) == 1
    assert all(call["max_tokens"] == 6000 for call in calls["generation"])


@pytest.mark.parametrize("falc", [False, True])
@pytest.mark.parametrize("raw", ['{"paras": [', "[]", "{}", (payload(), "length")])
def test_bad_model_json_never_becomes_deterministic_professional_coverage(
    monkeypatch, falc, raw
):
    calls = fake_mistral(monkeypatch, [raw])

    with pytest.raises(ValueError, match="synthesis"):
        asyncio.run(agent.synthesize(
            "Comment remplir le formulaire ?", [document(), document()], profile="pro", falc=falc
        ))

    assert len(calls["generation"]) == 1
    assert calls["verification"] == []


@pytest.mark.parametrize("corruption", ["ellipsis", "cross_passage", "wrong_id"])
def test_falc_rejects_nonliteral_or_misattributed_quotes_on_both_attempts(monkeypatch, corruption):
    quote = "Le service peut vous aider si votre dossier est complet."
    bad_quote = quote
    docs = [document("Une autre source."), document(quote)]
    source_id = 2
    if corruption == "ellipsis":
        bad_quote = quote.replace("aider si", "aider... si")
    elif corruption == "cross_passage":
        docs[1].passages = ["Le service peut vous aider", "si votre dossier est complet."]
    else:
        source_id = 1
    bad = payload(quote, quote=bad_quote, source_id=source_id)
    bad["steps"][0]["t"] = "Une aide du service"
    calls = fake_mistral(monkeypatch, [bad, bad])

    with pytest.raises(ValueError, match="invalid_falc_response"):
        asyncio.run(agent.synthesize("Une aide ?", docs, falc=True))

    assert len(calls["generation"]) == 2
    assert calls["verification"] == []


def test_falc_verifies_conditions_against_the_unabridged_authorized_context(monkeypatch):
    full_quote = "Le service peut vous aider si votre dossier est complet."
    unconditional = "Le service peut vous aider."
    bad = payload(unconditional, quote="Le service peut vous aider", source_id=1)
    bad["steps"][0]["t"] = "Une aide du service"
    good = payload(full_quote, quote=full_quote, source_id=1)
    good["steps"][0]["t"] = "Une aide du service"

    def approve(claim):
        # Réponse du vérificateur indépendant : un fragment ne doit pas cacher
        # la condition contenue dans le passage autorisé d'origine.
        return claim.get("context") == [full_quote] and claim["claim"] != unconditional

    calls = fake_mistral(monkeypatch, [bad, good], approve=approve)
    answer = asyncio.run(agent.synthesize("Une aide ?", [document(full_quote)], falc=True))

    assert answer["steps"][0]["d"] == f"{full_quote} [1]"
    assert len(calls["verification"]) == 2
    assert all(
        claim["context"] == [full_quote]
        for request in calls["verification"]
        for claim in request["claims"]
    )
    assert calls["verification"][0]["claims"][1]["quote"] == "Le service peut vous aider"
    assert calls["verification"][1]["claims"][1]["quote"] == full_quote


@pytest.mark.parametrize("failure", ["length", "missing_checks", "bad_shape", "missing_id", "duplicate_id", "string_true"])
def test_falc_verifier_must_return_a_complete_boolean_verdict_for_every_claim(monkeypatch, failure):
    def broken_verdict(content):
        if failure == "length":
            return content, "length"
        if failure == "missing_checks":
            return {}, "stop"
        if failure == "bad_shape":
            return {"checks": [True]}, "stop"
        if failure == "missing_id":
            content["checks"].pop()
        elif failure == "duplicate_id":
            content["checks"][1] = content["checks"][0]
        else:
            content["checks"][0]["supported"] = "true"
        return content, "stop"

    calls = fake_mistral(
        monkeypatch, [payload(source_id=1), payload(source_id=1)],
        verification_response=broken_verdict,
    )
    with pytest.raises(ValueError, match="invalid_falc_response"):
        asyncio.run(agent.synthesize("Comment remplir le formulaire ?", [document()], falc=True))

    assert len(calls["generation"]) == 2
    assert len(calls["verification"]) == 2


@pytest.mark.parametrize("profile", ["famille", "pro"])
def test_falc_never_injects_professional_coverage_or_overwrites_followup(monkeypatch, profile):
    docs = [
        document(),
        document(
            CAPTURED_QUOTE * 3, centre_id="casf", titre="CASF — article L146-3",
            url="https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000000000001",
        ),
    ]
    calls = fake_mistral(monkeypatch, [payload(source_id=1)])

    answer = asyncio.run(agent.synthesize("Comment remplir le formulaire ?", docs, profile=profile, falc=True))

    assert answer["steps"] == [{"t": "Remplir le formulaire", "d": f"{SHORT_DETAIL} [1]"}]
    assert answer["followup"] == "Avez-vous besoin d'aide ?"
    assert len(calls["generation"]) == 1
    assert agent.cited_payload(answer, docs) == agent.sources_payload(docs)[:1]


def test_falc_revalidates_regenerated_evidence_and_uses_only_server_urls(monkeypatch):
    other_quote = "Le service accueille les familles."
    first = payload(CAPTURED_QUOTE)
    regenerated = {
        "unknown": False,
        "paras": [{"text": other_quote, "quotes": [other_quote], "source_ids": [1]}],
        "steps": [{"t": "Accueil des familles", "d": other_quote, "quotes": [other_quote], "source_ids": [1]}],
        "contacts": [{"nom": "Le service", "role": other_quote, "source_id": 1, "quote": other_quote, "url": "https://evil.example/"}],
        "followup": "Dans quel département vivez-vous ?",
    }
    docs = [document(other_quote, url="https://www.has-sante.fr/accueil"), document()]
    calls = fake_mistral(monkeypatch, [first, regenerated])
    answer = asyncio.run(agent.synthesize("Comment remplir le formulaire ?", docs, falc=True))

    assert answer["paras"] == [f"{other_quote} [1]"]
    assert answer["steps"] == [{"t": "Accueil des familles", "d": f"{other_quote} [1]"}]
    assert answer["contacts"][0]["url"] == docs[0].url
    assert answer["contacts"][0]["role"] == f"{other_quote} [1]"
    assert [source["n"] for source in agent.cited_payload(answer, docs)] == [1]
    assert len(calls["generation"]) == 2
    assert len(calls["verification"]) == 1
    assert all(claim["quote"] == other_quote for claim in calls["verification"][0]["claims"])
    assert all(claim["source_id"] == 1 for claim in calls["verification"][0]["claims"])


def test_falc_rejects_unsupported_short_paraphrases_even_with_lexical_overlap(monkeypatch):
    quote = "Le service examine votre dossier."
    invented = "Le service accepte votre dossier automatiquement."
    data = payload(invented, quote=quote, source_id=1)
    data["steps"][0]["t"] = "Votre dossier"
    # Le filtre lexical seul ne suffit pas : le vérificateur doit pouvoir opposer un veto.
    assert agent._verified_evidence(data["steps"][0], [document(quote)]) == [1]
    calls = fake_mistral(monkeypatch, [data, data], approve=lambda claim: claim["claim"] != invented)

    with pytest.raises(ValueError, match="invalid_falc_response"):
        asyncio.run(agent.synthesize("Mon dossier ?", [document(quote)], falc=True, profile="pro"))

    assert len(calls["generation"]) == 2
    assert len(calls["verification"]) == 2
    assert all(any(claim["claim"] == invented for claim in request["claims"]) for request in calls["verification"])


def test_falc_acronym_definition_requires_its_own_exact_evidence(monkeypatch):
    quote = "La maison départementale des personnes handicapées (MDPH) accueille les familles."
    invented = "MDPH signifie maison des prestations du handicap."
    definition = "MDPH signifie maison départementale des personnes handicapées."
    bad = payload(source_id=1)
    bad["steps"] = []
    bad["paras"] = [{"text": invented, "source_ids": [1], "quotes": [quote]}]
    good = {**bad, "paras": [{"text": definition, "source_ids": [1], "quotes": [quote]}]}
    calls = fake_mistral(monkeypatch, [bad, good], approve=lambda claim: claim["claim"] != invented)

    answer = asyncio.run(agent.synthesize("Que signifie MDPH ?", [document(quote)], falc=True))

    assert answer["paras"] == [f"{definition} [1]"]
    assert not answer.get("glossary")
    assert calls["verification"][0]["claims"][0]["quote"] == quote
    assert len(calls["generation"]) == 2


def test_regular_professional_synthesis_preserves_a_reasonable_model_followup(monkeypatch):
    docs = [document()]
    fake_mistral(monkeypatch, [payload(source_id=1)])

    completed = asyncio.run(agent.synthesize("Comment remplir le formulaire ?", docs, profile="pro"))

    assert completed["followup"] == "Avez-vous besoin d'aide ?"


@pytest.mark.parametrize(("group", "count"), [("paras", 6), ("steps", 6), ("contacts", 5)])
def test_falc_regenerates_oversized_bundles_instead_of_dropping_items(monkeypatch, group, count):
    quote = "Le service accueille les familles."
    items = {
        "paras": {"text": quote, "quotes": [quote], "source_ids": [1]},
        "steps": {"t": "Accueil des familles", "d": quote, "quotes": [quote], "source_ids": [1]},
        "contacts": {"nom": "Le service", "role": quote, "quote": quote, "source_id": 1},
    }
    bad = {"unknown": False, "paras": [], "steps": [], "contacts": [], "followup": ""}
    bad[group] = [items[group]] * count
    good = {**bad, group: [items[group]]}
    calls = fake_mistral(monkeypatch, [bad, good])

    answer = asyncio.run(agent.synthesize("Une aide ?", [document(quote)], falc=True))

    assert len(answer[group]) == 1
    assert len(calls["generation"]) == 2
    assert len(calls["verification"]) == 1


def test_falc_retry_cannot_reuse_the_first_attempts_valid_evidence(monkeypatch):
    first = payload(CAPTURED_QUOTE, source_id=1)
    second = payload(source_id=1, quote="Cet extrait est absent du document.")
    calls = fake_mistral(monkeypatch, [first, second])

    with pytest.raises(ValueError, match="invalid_falc_response"):
        asyncio.run(agent.synthesize("Comment remplir le formulaire ?", [document()], falc=True))

    assert len(calls["generation"]) == 2
    assert calls["verification"] == []
