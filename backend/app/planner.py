"""Planification interne de la recherche, isolée de la réponse utilisateur.

Le planificateur peut employer la connaissance générale de Mistral pour
reconnaître un terme, développer un sigle ou rapprocher un nom courant d'un
terme spécialisé. Sa sortie ne sert qu'à construire des requêtes. Elle n'est
jamais transmise au synthétiseur comme preuve ou contenu de réponse.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, cast

from mistralai.client import Mistral

_ALLOWED_INTENTS = {"definition", "orientation", "droits", "coordonnees", "comparaison", "autre"}
_ALLOWED_EFFORTS = {"small", "medium", "large"}
_ALLOWED_MISSING = {"", "subject", "department", "age", "situation"}
_QUERY_CLEAN = re.compile(r"[^\wÀ-ÿ .,'()/-]+")


def model_for_effort(effort: str) -> str:
    """Modèle de synthèse configuré selon la complexité du besoin."""
    defaults = {
        "small": "mistral-small-latest",
        "medium": "mistral-medium-latest",
        "large": "mistral-large-latest",
    }
    effort = effort if effort in defaults else "medium"
    return os.environ.get(f"CHAT_MODEL_{effort.upper()}", defaults[effort])


def _queries(value: object, fallback: list[str] | None = None) -> list[str]:
    if not isinstance(value, list):
        value = []
    out: list[str] = []
    for raw in value[:5]:
        q = _QUERY_CLEAN.sub(" ", str(raw))
        q = " ".join(q.split()).strip()
        if 3 <= len(q) <= 120 and q.lower() not in {x.lower() for x in out}:
            out.append(q)
        if len(out) == 3:
            break
    return out or list(fallback or [])


def _clean_plan(data: object, *, fallback_question: str, profile: str = "famille") -> dict:
    """Ne conserve que les champs autorisés à piloter la recherche."""
    if not isinstance(data, dict):
        data = {}
    audience = data.get("audience")
    if audience not in ("famille", "pro"):
        audience = profile if profile in ("famille", "pro") else "famille"
    intent = str(data.get("intent", "autre"))
    if intent not in _ALLOWED_INTENTS:
        intent = "autre"
    effort = str(data.get("effort", "medium"))
    if effort not in _ALLOWED_EFFORTS:
        effort = "medium"
    missing = str(data.get("missing_field", ""))
    if missing not in _ALLOWED_MISSING:
        missing = ""
    normalized_question = fallback_question.casefold()
    generic_mutation = re.search(
        r"\bmutation\b.*\bg[eè]ne\b(?:\s+(?:comment|quel(?:le)?|pour|chez|et|orienter)\b|\s*$)",
        normalized_question,
    )
    if generic_mutation:
        missing = "subject"
    profession = " ".join(str(data.get("profession", "")).split())[:80]
    fallback = " ".join(fallback_question.split())[:120]
    return {
        "audience": audience,
        "profession": profession,
        "intent": intent,
        "effort": effort,
        "resource_queries": _queries(data.get("resource_queries"), [fallback] if fallback else []),
        "casf_queries": _queries(data.get("casf_queries")),
        "missing_field": missing,
    }


def build_planner_prompt(
    question: str,
    *,
    profile: str,
    dept,
    situations: list[str],
    age: str | None,
    history: list[dict],
) -> str:
    """Prompt de compréhension ; son résultat ne devient jamais une preuve."""
    if dept is None:
        dept_text = "non précisé"
    elif hasattr(dept, "model_dump"):
        d = dept.model_dump()
        dept_text = f"{d.get('nom', '')} ({d.get('code', '')})"
    elif isinstance(dept, dict):
        dept_text = f"{dept.get('nom', '')} ({dept.get('code', '')})"
    else:
        dept_text = str(dept)

    # Une ancienne réponse de l'agent ne doit jamais contaminer le nouveau plan.
    previous_users = [
        str(h.get("content", ""))[:1000]
        for h in history[-6:]
        if h.get("role") == "user" and h.get("content")
    ]
    context = "\n".join(f"- {x}" for x in previous_users) or "- aucun"

    return f"""Tu planifies la recherche interne de Balise, sans répondre à l'utilisateur.

Tu peux utiliser ta connaissance générale ou encyclopédique (comme Wikipédia) UNIQUEMENT pour :
- reconnaître et catégoriser un terme, une maladie ou un gène ;
- développer un sigle et trouver des synonymes utiles ;
- produire des requêtes vers les centres ressources autorisés et le CASF.

Cette analyse ne sera jamais transmise au synthétiseur comme fait ou preuve.
Produis uniquement des requêtes. Ne rédige aucun plan d'action, aucun droit,
aucun contact, aucun conseil médical ou social. Ces éléments devront provenir
exclusivement des extraits retrouvés dans les centres ressources et le CASF.

Contexte déclaré : profil={profile}; département={dept_text}; situations={situations or 'non précisées'}; âge={age or 'non précisé'}.
Messages utilisateur précédents (contexte seulement) :
{context}
Question actuelle : {question}

Réponds STRICTEMENT en JSON :
{{
  "audience": "famille|pro",
  "profession": "métier explicitement indiqué ou chaîne vide",
  "intent": "definition|orientation|droits|coordonnees|comparaison|autre",
  "effort": "small|medium|large",
  "resource_queries": ["1 à 3 requêtes courtes avec synonymes utiles"],
  "casf_queries": ["0 à 3 thèmes juridiques à rechercher, sans inventer de numéro d'article"],
  "missing_field": "|subject|department|age|situation"
}}

Effort : small pour une définition ou une coordonnée directe ; medium pour une
orientation courante ; large pour une situation professionnelle, rare,
multidisciplinaire ou juridiquement complexe."""


async def plan_question(
    question: str,
    *,
    profile: str,
    dept=None,
    situations: list[str] | None = None,
    age: str | None = None,
    history: list[dict] | None = None,
) -> dict:
    """Appelle Mistral dans un contexte dédié à la seule planification."""
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY manquante")
    prompt = build_planner_prompt(
        question,
        profile=profile,
        dept=dept,
        situations=situations or [],
        age=age,
        history=history or [],
    )
    client = Mistral(api_key=api_key)
    resp = await client.chat.complete_async(
        model=os.environ.get("PLANNER_MODEL", "mistral-medium-latest"),
        messages=cast(Any, [{"role": "user", "content": prompt}]),
        temperature=0.1,
        max_tokens=700,
        response_format={"type": "json_object"},
    )
    if not resp.choices or not resp.choices[0].message:
        return _clean_plan({}, fallback_question=question, profile=profile)
    raw = resp.choices[0].message.content or "{}"
    if not isinstance(raw, str):
        raw = "".join(getattr(c, "text", "") for c in raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    return _clean_plan(data, fallback_question=question, profile=profile)


def clarification_for(plan: dict) -> str:
    """Relance déterministe et non factuelle selon le champ manquant."""
    return {
        "subject": "Quel est le nom précis du gène, de la maladie ou du dispositif concerné ?",
        "department": "Dans quel département la personne concernée réside-t-elle ?",
        "age": "Quel âge a la personne concernée ?",
        "situation": "À quelle étape du parcours êtes-vous actuellement ?",
    }.get(str(plan.get("missing_field", "")), "")
