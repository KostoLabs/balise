"""API Balise — FastAPI.

Routes :
- GET  /api/health  → l'état du service
- GET  /api/sources → centres ressources publics utilisés
- POST /api/chat    → réponse sourcée de l'agent
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import agent, annuaire, casf, corpus, planner, research
from .ressources import get_sources, is_authorized_document

log = logging.getLogger("balise")

load_dotenv()

log = logging.getLogger("balise")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

app = FastAPI(title="Balise", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

# CORS ouvert pour le dev local (le front est servi statiquement ailleurs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class Dept(BaseModel):
    code: str
    nom: str


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    profile: str = "famille"
    dept: Dept | None = None
    situations: list[str] = []
    age: str | None = None
    falc: bool = False
    deptSkipped: bool = False
    history: list[ChatHistoryItem] = []


class SimplifyRequest(ChatRequest):
    pass


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/sources")
async def sources() -> dict:
    return {"sources": get_sources()}


def _context_kw(req: ChatRequest) -> list[str]:
    kw: list[str] = []
    if req.situations:
        kw.append(" ".join(req.situations))
    if req.age:
        kw.append(req.age)
    if req.dept:
        kw.append(req.dept.nom)
    return kw


def _situations_ok(req: ChatRequest) -> list[str]:
    ok = {"Psychique", "Autisme / TND", "Handicap rare", "Moteur", "Sensoriel",
          "Polyhandicap", "Maladie rare"}
    return [s for s in req.situations if s in ok]


def _authorized_docs(docs: list) -> list:
    """Dernière frontière : aucun document hors registre n'atteint Mistral B."""
    return [
        doc
        for doc in docs
        if is_authorized_document(
            str(getattr(doc, "centre_id", "")), str(getattr(doc, "url", ""))
        )
    ]


def _merge_docs(*groups: list, limit: int = 16) -> list:
    """Fusionne les voies de recherche sans laisser les doublons prendre la place."""
    docs: list = []
    seen: set[str] = set()
    for group in groups:
        for doc in group:
            url = str(getattr(doc, "url", ""))
            if not url or url in seen:
                continue
            seen.add(url)
            docs.append(doc)
            if len(docs) == limit:
                return docs
    return docs


async def _answer(req: ChatRequest, falc: bool) -> dict:
    profile = req.profile if req.profile in ("famille", "pro") else "famille"
    history = [h.model_dump() for h in req.history]

    # A — compréhension libre, isolée : sa sortie ne pilote QUE la recherche.
    try:
        plan = await planner.plan_question(
            req.question,
            profile=profile,
            dept=req.dept,
            situations=_situations_ok(req),
            age=req.age,
            history=history,
        )
    except Exception:
        log.exception("planification Mistral échouée ; requête originale utilisée")
        plan = planner._clean_plan(
            {}, fallback_question=req.question, profile=profile
        )

    clarification = planner.clarification_for(plan)

    context = _context_kw(req) + _situations_ok(req)
    query_text = " ".join(plan["resource_queries"])
    lexical_text = " ".join(part for part in (req.question, query_text) if part)
    kws = research.keywords(lexical_text, context)
    docs = []

    # Annuaire explicitement autorisé : coordonnées verbatim si la question en cherche.
    try:
        passages = annuaire.esms_passages(
            req.question, dept_code=req.dept.code if req.dept else None
        )
    except Exception:
        log.exception("annuaire FINESS échoué")
        passages = []
    if passages:
        docs.append(type("D", (), {
            "centre_id": "finess",
            "centre_nom": "Annuaire FINESS (ANS)",
            "url": "https://finess.esante.gouv.fr/",
            "titre": "Annuaire public des établissements (FINESS)",
            "passages": passages,
            "score": 50,
        })())

    # Corpus et CASF par facettes : sélection contrôlée depuis la compréhension
    # globale de A. Seuls les documents sources, jamais le plan, atteignent B.
    topic_docs = corpus.topic_documents(plan.get("resource_topics", []), max_docs=10)
    casf_topic_docs = casf.search_topics(plan.get("casf_topics", []), limit=6)

    # Préserve les trois résultats de l'original avant une place complémentaire :
    # les reformulations de A ne peuvent pas évincer le troisième résultat.
    original_docs = corpus.corpus_search(research.keywords(req.question, []))
    corpus_docs = _merge_docs(original_docs, corpus.corpus_search(kws), limit=4)
    casf_docs = casf.search(plan["casf_queries"], limit=4)

    # Centres ressources live, en parallèle pour chaque reformulation de A.
    live = await research.research_queries(plan["resource_queries"], context)
    docs = _merge_docs(
        docs,
        corpus_docs,
        topic_docs,
        casf_topic_docs,
        casf_docs,
        live,
        limit=20,
    )
    docs = _authorized_docs(docs)

    if not docs:
        return agent.unknown_answer(
            req.question, docs, profile=profile, followup=clarification
        )

    # B — synthèse dans un contexte neuf : aucun fait produit par A n'est transmis.
    try:
        ans = await agent.synthesize(
            req.question,
            docs,
            profile=profile,
            falc=falc,
            dept=req.dept,
            situations=_situations_ok(req),
            age=req.age,
            history=history,
            effort=plan["effort"],
        )
    except Exception:
        log.exception("synthèse Mistral échouée")
        raise HTTPException(status_code=502, detail="synthesis_failed")

    if ans["unknown"] or not (ans["paras"] or ans["steps"] or ans["contacts"]):
        return agent.unknown_answer(
            req.question,
            docs,
            profile=profile,
            followup=ans.get("followup") or clarification,
        )

    if not ans.get("followup") and clarification:
        ans["followup"] = clarification
    ans["sources"] = agent.cited_payload(ans, docs)
    ans["glossary"] = {}
    return ans


@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict:
    if req.profile not in ("famille", "pro"):
        raise HTTPException(status_code=422, detail="profile invalide")
    return await _answer(req, falc=req.falc)


@app.post("/api/chat/simplify")
async def simplify(req: SimplifyRequest) -> dict:
    """Reformule la dernière réponse en mode facile à lire (FALC)."""
    if req.profile not in ("famille", "pro"):
        raise HTTPException(status_code=422, detail="profile invalide")
    return await _answer(req, falc=True)


# --- Dockerfile healthcheck ---
@app.get("/health")
async def root_health() -> dict:
    return {"status": "ok"}