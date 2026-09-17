"""Live checks catch publishing broken or unselected source excerpts."""

from scripts import e2e_grounding
from scripts.e2e_grounding import inspect_answer

DOC = {
    "centre_id": "casf",
    "centre_nom": "Légifrance",
    "url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000051188561",
    "titre": "CASF — article L146-8",
    "passages": ["L'équipe évalue les besoins de compensation de la personne handicapée."],
}


def test_live_check_rejects_incomplete_statutory_cross_reference():
    answer = {
        "unknown": False,
        "paras": [],
        "steps": [{"t": "Évaluation", "d": "Elle sollicite les services visés à l'article L. [1]"}],
        "contacts": [],
        "sources": [{"n": 1, "url": DOC["url"], "doc": DOC["titre"]}],
    }
    report = inspect_answer("famille", answer, [DOC])
    assert not report["checks"]["complete_legal_references"]


def test_trace_rejects_turning_abstention_into_automatic_steps():
    trace = {
        "request": {"profile": "pro", "falc": False},
        "documents": [DOC],
        "parsed_synthesis": {"unknown": True, "paras": [], "steps": [], "contacts": [], "followup": "Où résidez-vous ?"},
        "answer": {
            "unknown": False, "paras": [], "contacts": [],
            "steps": [{"t": DOC["titre"], "d": DOC["passages"][0] + " [1]"}],
        },
    }
    assert hasattr(e2e_grounding, "inspect_trace")
    checks = e2e_grounding.inspect_trace(trace)
    assert not checks["only_model_selected_steps"]
    assert not checks["preserves_supported_abstention"]


def test_trace_accepts_selected_supported_steps_without_injection():
    quote = DOC["passages"][0]
    trace = {
        "request": {"profile": "pro", "falc": False},
        "documents": [DOC],
        "parsed_synthesis": {
            "unknown": False, "paras": [], "contacts": [], "followup": "",
            "steps": [{"t": "Évaluer les besoins", "d": quote, "source_ids": [1], "quotes": [quote]}],
        },
        "answer": {
            "unknown": False, "paras": [], "contacts": [],
            "steps": [{"t": "Évaluer les besoins", "d": quote + " [1]"}],
        },
    }
    assert hasattr(e2e_grounding, "inspect_trace")
    assert all(e2e_grounding.inspect_trace(trace).values())
