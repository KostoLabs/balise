"""The live E2E report must not hide missing/contact-only citations."""

from scripts.e2e_grounding import inspect_answer, visible_fields

DOC = {
    "centre_id": "corpus-mdph",
    "url": "https://www.monparcourshandicap.gouv.fr/aides/la-maison-departementale-des-personnes-handicapees-mdph-missions-et-fonctionnement",
}


def packet():
    return {
        "unknown": False,
        "paras": [],
        "steps": [],
        "contacts": [{"nom": "MDPH", "role": "Informe les familles. [1]"}],
        "sources": [{"n": 1, "url": DOC["url"], "doc": "MDPH"}],
    }


def test_live_check_includes_contact_only_citations():
    answer = packet()
    report = inspect_answer("falc", answer, [DOC])
    assert report["checks"]["citations_match_sources"]
    assert "Informe les familles. [1]" in visible_fields(answer)


def test_live_check_rejects_decorative_or_wrong_url_sources():
    answer = packet()
    answer["sources"].append({"n": 2, "url": "https://bad.invalid/", "doc": "invented"})
    report = inspect_answer("falc", answer, [DOC])
    assert not report["checks"]["citations_match_sources"]
    assert not report["checks"]["source_map"]
    assert not report["passed"]


def test_live_falc_measurement_does_not_concatenate_title_and_detail():
    answer = packet()
    answer["steps"] = [{"t": "x" * 180, "d": "MDPH " + "x" * 180 + " [1]"}]
    report = inspect_answer("falc", answer, [DOC])
    assert report["checks"]["short_visible_fields"]
    answer["contacts"][0]["role"] = "x" * 261 + " [1]"
    assert not inspect_answer("falc", answer, [DOC])["checks"]["short_visible_fields"]


def test_live_check_rejects_unlocalized_directory_contact():
    answer = packet()
    answer["sources"][0]["url"] = "https://finess.esante.gouv.fr/"
    docs = [{"centre_id": "finess", "url": answer["sources"][0]["url"]}]
    assert not inspect_answer("falc", answer, docs)["checks"]["no_unlocalized_finess"]
