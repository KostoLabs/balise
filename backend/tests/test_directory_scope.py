"""FINESS scoping regressions with a small, synthetic public-index fixture."""

import pytest

from app import annuaire


def entry(finess, commune, cp, nom="IME LES AMANDIERS"):
    return {
        "finess": finess,
        "nom": nom,
        "type": "Institut médico-éducatif",
        "commune": commune,
        "cp": cp,
        "adresse": f"1 rue Exemple {cp} {commune}",
        "tel": "",
    }


@pytest.fixture(autouse=True)
def directory(monkeypatch):
    rows = [
        entry("paris", "PARIS", "75012"),
        entry("lille", "LILLE", "59000"),
        entry("roubaix", "ROUBAIX", "59100"),
    ]
    monkeypatch.setattr(annuaire, "_cache", rows)
    monkeypatch.setattr(annuaire, "_org_cache", {})
    return rows


def test_supplied_commune_is_used_without_repeating_it_in_the_query():
    results = annuaire.search_esms("Un IME près de chez moi", commune="Lille")

    assert [row["finess"] for row in results] == ["lille"]


def test_supplied_department_scopes_passages_by_public_postal_code():
    passages = annuaire.esms_passages("Un IME près de chez moi", dept_code="59")

    assert len(passages) == 2
    assert any("FINESS lille," in passage for passage in passages)
    assert any("FINESS roubaix," in passage for passage in passages)
    assert all("FINESS paris," not in passage for passage in passages)


@pytest.mark.parametrize(
    "dept_code", ["", "5", "059", "59 ", " 59", "59?", "20", "2A", "2B", "971", "974", "976", "97", "99"],
)
def test_unsupported_or_malformed_department_fails_closed(dept_code, directory):
    directory.extend([
        entry("ajaccio", "AJACCIO", "20000"),
        entry("reunion", "SAINT DENIS", "97400"),
        entry("mayotte", "MAMOUDZOU", "97600"),
        entry("guadeloupe", "BASSE TERRE", "97100"),
    ])

    assert annuaire.search_esms("IME", dept_code=dept_code) == []
    assert annuaire.search_esms("IME Paris", dept_code=dept_code) == []


@pytest.mark.parametrize("query", ["Comparis : trouver un IME", "IME à Parisis"])
def test_town_substring_does_not_resolve_a_local_scope(query):
    assert annuaire.search_esms(query) == []


@pytest.mark.parametrize("supplied", [False, True])
def test_city_scope_matches_the_whole_town_not_neighbouring_town_names(directory, supplied):
    directory.extend([
        entry("lillers", "LILLERS", "62190"),
        entry("saint-andre", "SAINT ANDRE LEZ LILLE", "59350"),
        entry("lille-cedex", "LILLE CEDEX 9", "59000"),
    ])
    results = (
        annuaire.search_esms("IME", commune="Lille")
        if supplied else annuaire.search_esms("IME à Lille")
    )

    assert {row["finess"] for row in results} == {"lille", "lille-cedex"}


@pytest.mark.parametrize("cp", [None, "", "59", "5900", "590000", "59000 CEDEX", "59abc"])
def test_department_requires_a_valid_public_cp_not_a_finess_prefix(monkeypatch, cp):
    monkeypatch.setattr(annuaire, "_cache", [entry("590000001", "LILLE", cp)])

    assert annuaire.search_esms("IME", dept_code="59") == []


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("IME à Saint-André-lez-Lille", ["saint-andre"]),
        ("IME à SAINT  ANDRÉ LEZ LILLE", ["saint-andre"]),
        ("IME à Paris ou Lille", []),
    ],
)
def test_detected_city_is_unambiguous_and_not_a_shorter_town_name(directory, query, expected):
    directory.append(entry("saint-andre", "SAINT ANDRE LEZ LILLE", "59350"))

    assert [row["finess"] for row in annuaire.search_esms(query)] == expected


@pytest.mark.parametrize(
    ("query", "scope", "expected"),
    [
        ("IME", {}, []),
        ("IME à VilleInconnue", {}, []),
        ("IME", {"commune": "VilleInconnue"}, []),
        ("IME", {"commune": "Nord"}, []),
        ("IME à Lille", {"dept_code": "59"}, ["lille"]),
        ("IME à Paris", {"dept_code": "59"}, []),
        ("IME à Paris", {"commune": "Lille", "dept_code": "59"}, ["lille"]),
        ("IME", {"commune": "Lille", "dept_code": "75"}, []),
    ],
)
def test_search_never_broadens_past_supplied_geography(query, scope, expected):
    assert [row["finess"] for row in annuaire.search_esms(query, **scope)] == expected


def test_generic_name_words_cannot_bypass_the_location_gate(directory):
    directory.append(entry(
        "generic-service", "AMBERIEU EN BUGEY", "01500",
        "SERVICE D'ACCOMPAGNEM A LA VIE SOCIALE",
    ))
    question = (
        "je suis assistante social comment puis je accompagné une famille dont "
        "l'adolescent vient d'apprendre qu'il a une mutation génétique"
    )

    assert annuaire.esms_passages(question) == []


def test_named_establishment_search_keeps_the_supplied_geography(directory):
    for row in directory:
        row["nom"] = "Résidence Arc en Ciel"

    results = annuaire.search_esms("Résidence Arc en Ciel", commune="Lille")

    assert [row["finess"] for row in results] == ["lille"]


def test_department_filter_uses_cp_even_when_finess_has_another_prefix(monkeypatch):
    monkeypatch.setattr(annuaire, "_cache", [entry("590000001", "BOURG EN BRESSE", "01000")])

    assert len(annuaire.search_esms("IME", dept_code="01")) == 1
    assert annuaire.search_esms("IME", dept_code="59") == []


def test_department_filter_runs_before_the_existing_positional_limit():
    results = annuaire.search_esms("IME", None, 1, dept_code="59")

    assert [row["finess"] for row in results] == ["lille"]
