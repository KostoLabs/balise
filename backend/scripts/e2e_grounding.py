"""Opt-in live grounding checks. Uses paid Mistral calls; never run in CI.

From backend: PYTHONPATH=. .venv/bin/python scripts/e2e_grounding.py \
    --env-file ../docker/.env --output-dir /tmp/balise-grounding
Each request records its real planner, retrieved evidence, model completions and
final answer. No API keys, HTTP headers or real user data are persisted.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv
from fastapi import HTTPException

from app import agent, main, planner
from app.ressources import is_authorized_document

SCENARIOS = {
    "professionnel_global": {
        "question": (
            "je suis assistante social comment puis je accompagné une famille dont "
            "l'adolescent vient d'apprendre qu'il a une mutation génétique"
        ),
        "profile": "pro",
    },
    "famille": {
        "question": (
            "Mon fils de 12 ans est autiste. Il est épuisé par l'école et "
            "n'arrive plus à suivre. Quelles démarches pouvons-nous faire "
            "pour sa scolarité et les aides ?"
        ),
        "profile": "famille",
        "age": "12 ans",
        "situations": ["Autisme / TND"],
    },
    "charcot": {
        "question": (
            "Je suis assistante sociale : comment orienter et accompagner "
            "cet adolescent atteint de la maladie de Charcot ?"
        ),
        "profile": "pro",
        "age": "adolescent",
        "situations": ["Maladie rare", "Moteur"],
    },
    "falc": {
        "question": (
            "Je suis en situation de handicap et j'ai besoin d'aide pour ma "
            "vie quotidienne. Comment faire une demande à la MDPH ?"
        ),
        "profile": "famille",
        "falc": True,
    },
    "pro_falc": {
        "question": (
            "Je suis assistante sociale. Expliquez simplement à la famille "
            "comment demander à la MDPH une évaluation des besoins de leur enfant."
        ),
        "profile": "pro",
        "falc": True,
    },
}


def visible_fields(answer: dict) -> list[str]:
    fields = list(answer.get("paras", []))
    fields.extend(
        value
        for step in answer.get("steps", [])
        for value in (step.get("t", ""), step.get("d", ""))
    )
    fields.extend(
        value
        for contact in answer.get("contacts", [])
        for value in (contact.get("nom", ""), contact.get("role", ""))
    )
    return fields


def inspect_answer(name: str, answer: dict, documents: list[dict]) -> dict:
    fields = visible_fields(answer)
    text = " ".join(fields).casefold()
    citations = {int(n) for n in agent.CITE_RE.findall(text)}
    sources = answer.get("sources", [])
    source_ids = {source["n"] for source in sources}
    checks = {
        "known": not answer.get("unknown", True),
        "content": bool(fields),
        "sources": bool(sources),
        "citations_match_sources": citations == source_ids,
        "unique_sources": len(source_ids) == len(sources),
        "complete_legal_references": not any(
            re.search(r"\b[LDR]\.\s*(?:\[\d+\]\s*)*$", value)
            for value in fields
        ),
        "source_map": all(
            1 <= source["n"] <= len(documents)
            and source["url"] == documents[source["n"] - 1]["url"]
            for source in sources
        ),
        "authorized_documents": all(
            is_authorized_document(doc["centre_id"], doc["url"])
            for doc in documents
        ),
        "no_unlocalized_finess": not any(
            documents[source_id - 1]["centre_id"] == "finess"
            for source_id in source_ids
            if 1 <= source_id <= len(documents)
        ),
    }
    source_text = json.dumps(sources, ensure_ascii=False).casefold()
    if name == "professionnel_global":
        checks.update({
            "substantial_plan": 5 <= len(answer.get("steps", [])) <= 8,
            "social_school_compensation": all(
                term in text for term in ("mdph", "cdaph", "pps", "aeeh", "pch")
            ),
            "casf_roles": "article l146-3" in source_text,
            "casf_assessment": any(
                ref in source_text for ref in ("article l146-8", "article r146-28")
            ),
            "followup": bool(answer.get("followup")),
        })
    elif name == "charcot":
        checks["specific_authoritative_source"] = (
            "has-sante.fr/jcms/c_2573383" in source_text
        )
        checks["no_unrelated_genetic_bundle"] = "genetique-medicale.fr" not in source_text
    elif name == "famille":
        checks["school_support"] = "scolar" in text or "pps" in text
        checks["social_support"] = "mdph" in text or "aeeh" in text
    if SCENARIOS[name].get("falc"):
        checks["short_visible_fields"] = bool(fields) and max(map(len, fields)) <= 260
        checks["supported_request"] = "mdph" in text
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "counts": {
            "paragraphs": len(answer.get("paras", [])),
            "steps": len(answer.get("steps", [])),
            "contacts": len(answer.get("contacts", [])),
            "sources": len(sources),
        },
        "max_visible_field_chars": max(map(len, fields), default=0),
        "source_docs": [source["doc"] for source in sources],
    }


def inspect_trace(trace: dict) -> dict:
    """Catch manufactured coverage that superficial keyword checks would accept."""
    if trace.get("request", {}).get("falc"):
        return {}  # FALC uses the fresh atomic verifier, not the literal renderer.
    raw = trace.get("parsed_synthesis")
    if not isinstance(raw, dict):
        return {"synthesis_trace_available": False}
    documents = [SimpleNamespace(**doc) for doc in trace.get("documents", [])]
    selected = agent._clean(raw, documents)
    answer = trace.get("answer", {})
    return {
        "only_model_selected_steps": answer.get("steps", []) == selected["steps"],
        "preserves_supported_abstention": (
            not selected["unknown"] or answer.get("unknown") is True
        ),
    }


@contextmanager
def trace_pipeline(trace: dict):
    """Instrument one sequential request without replacing real API results."""
    original_plan = planner.plan_question
    original_synthesize = agent.synthesize
    planner_client, agent_client = planner.Mistral, agent.Mistral

    def factory(original, stage):
        def make_client(*args, **kwargs):
            client = original(*args, **kwargs)

            async def complete_async(**request):
                result = await client.chat.complete_async(**request)
                trace.setdefault("completions", []).append({
                    "stage": stage,
                    "model": request.get("model"),
                    "messages": request.get("messages"),
                    "response": result.model_dump(mode="json"),
                })
                if stage == "synthesis":
                    try:
                        parsed = agent._response_json(result)
                    except agent.SynthesisError:
                        pass
                    else:
                        if "paras" in parsed and "steps" in parsed:
                            trace["parsed_synthesis"] = parsed
                return result

            return SimpleNamespace(chat=SimpleNamespace(complete_async=complete_async))
        return make_client

    async def capture_plan(*args, **kwargs):
        plan = await original_plan(*args, **kwargs)
        trace["plan"] = plan
        return plan

    async def capture_synthesis(question, docs, **kwargs):
        trace["documents"] = [
            {
                "centre_id": doc.centre_id,
                "centre_nom": doc.centre_nom,
                "url": doc.url,
                "titre": doc.titre,
                "passages": doc.passages,
                "score": getattr(doc, "score", None),
            }
            for doc in docs
        ]
        return await original_synthesize(question, docs, **kwargs)

    planner.plan_question, agent.synthesize = capture_plan, capture_synthesis
    planner.Mistral = factory(planner_client, "planner")
    agent.Mistral = factory(agent_client, "synthesis")
    try:
        yield
    finally:
        planner.plan_question, agent.synthesize = original_plan, original_synthesize
        planner.Mistral, agent.Mistral = planner_client, agent_client


async def run_scenario(name: str, output: Path, iteration: int) -> dict:
    request = main.ChatRequest(**SCENARIOS[name])
    attempts = []
    answer = None
    for attempt in range(3):
        trace = {"request": request.model_dump(), "attempt": attempt + 1}
        attempts.append(trace)
        try:
            with trace_pipeline(trace):
                answer = await asyncio.wait_for(
                    main._answer(request, falc=request.falc), timeout=210
                )
            trace["answer"] = answer
            break
        except (HTTPException, TimeoutError) as exc:
            trace["error"] = {"type": type(exc).__name__, "status": getattr(exc, "status_code", None)}
            if getattr(exc, "status_code", None) != 502 or attempt == 2:
                break
            await asyncio.sleep(2 ** (attempt + 1))
    report = (
        inspect_answer(name, answer, attempts[-1].get("documents", []))
        if answer is not None
        else {"passed": False, "checks": {"pipeline_completed": False}}
    )
    if answer is not None:
        report["checks"].update(inspect_trace(attempts[-1]))
    report["attempt_count"] = len(attempts)
    report["checks"]["first_request_completed"] = len(attempts) == 1 and answer is not None
    report["passed"] = all(report["checks"].values())
    artifact = output / f"{name}-{iteration}.json"
    artifact.write_text(json.dumps({"attempts": attempts, "report": report}, ensure_ascii=False, indent=2))
    return {"scenario": name, "iteration": iteration, "artifact": str(artifact), **report}


async def run(args) -> bool:
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = args.scenario or list(SCENARIOS)
    results = []
    for iteration in range(1, args.repeats + 1):
        for name in names:
            report = await run_scenario(name, output, iteration)
            results.append(report)
            (output / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
            print(json.dumps(report, ensure_ascii=False), flush=True)
    # Re-read collected data; missing or duplicate executions are not successes.
    saved = json.loads((output / "report.json").read_text())
    expected = {(name, iteration) for name in names for iteration in range(1, args.repeats + 1)}
    observed = {(r["scenario"], r["iteration"]) for r in saved}
    return observed == expected and len(saved) == len(expected) and all(r["passed"] for r in saved)


def cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--scenario", action="append", choices=list(SCENARIOS))
    parser.add_argument("--repeats", type=int, choices=range(1, 4), default=1)
    args = parser.parse_args()
    if args.env_file:
        if not args.env_file.is_file():
            parser.error("env file does not exist")
        load_dotenv(args.env_file, override=False)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return 0 if asyncio.run(run(args)) else 2


if __name__ == "__main__":
    raise SystemExit(cli())
