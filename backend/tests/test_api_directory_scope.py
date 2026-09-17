"""The API must forward a department code, not mislabel its name as a city."""

import asyncio

from app import main


def test_department_context_reaches_directory_as_department_code(monkeypatch):
    seen = {}

    async def plan(*args, **kwargs):
        return main.planner._clean_plan({}, fallback_question="MDPH", profile="famille")

    def directory(question, commune=None, *, dept_code=None):
        seen.update(commune=commune, dept_code=dept_code)
        return []

    async def live(*args, **kwargs):
        return []

    monkeypatch.setattr(main.planner, "plan_question", plan)
    monkeypatch.setattr(main.annuaire, "esms_passages", directory)
    monkeypatch.setattr(main.corpus, "topic_documents", lambda *a, **kw: [])
    monkeypatch.setattr(main.corpus, "corpus_search", lambda *a, **kw: [])
    monkeypatch.setattr(main.casf, "search_topics", lambda *a, **kw: [])
    monkeypatch.setattr(main.casf, "search", lambda *a, **kw: [])
    monkeypatch.setattr(main.research, "research_queries", live)

    request = main.ChatRequest(question="Où se trouve ma MDPH ?", dept=main.Dept(code="59", nom="Nord"))
    asyncio.run(main._answer(request, falc=False))

    assert seen == {"commune": None, "dept_code": "59"}
