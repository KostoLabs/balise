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

from . import agent, corpus, research
from .ressources import get_sources

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


async def _answer(req: ChatRequest, falc: bool) -> dict:
    kws = research.keywords(req.question, _context_kw(req) + _situations_ok(req))
    # 1) corpus local (passages vérifiés des centres ressources) — prioritaire
    docs = corpus.corpus_search(kws)
    # 2) recherche live en complément (fusion, dédoublonnée par URL)
    live = await research.research_all(req.question, _context_kw(req) + _situations_ok(req))
    seen = {d.url for d in docs}
    docs += [d for d in live if d.url not in seen]
    docs = docs[:10]
    if not docs:
        return agent.unknown_answer(req.question, docs)

    try:
        ans = await agent.synthesize(
            req.question,
            docs,
            profile=req.profile if req.profile in ("famille", "pro") else "famille",
            falc=falc,
            dept=req.dept,
            situations=_situations_ok(req),
            age=req.age,
            history=[h.model_dump() for h in req.history],
        )
    except Exception:
        log.exception("synthèse Mistral échouée")
        raise HTTPException(status_code=502, detail="synthesis_failed")

    if not ans["paras"]:
        # honnêteté : pas de contenu fabriqué sans source
        u = agent.unknown_answer(req.question, docs)
        u["sources"] = agent.sources_payload(docs)
        return u

    # unknown du modèle fiable seulement si les paras ne citent RIEN :
    # des paragraphes sourcés ([n] valides) prouvent que les extraits répondaient.
    cited = any(agent.CITE_RE.search(p) for p in ans["paras"])
    if ans["unknown"] and not cited:
        u = agent.unknown_answer(req.question, docs)
        u["sources"] = agent.sources_payload(docs)
        return u
    if cited:
        ans["unknown"] = False

    ans["sources"] = agent.sources_payload(docs)
    ans["glossary"] = agent.glossary_for(ans["paras"])
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