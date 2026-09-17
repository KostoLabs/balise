"""Agent de synthèse Balise (Mistral) — citations strictes, zéro invention.

Contrat :
- la réponse est produite UNIQUEMENT à partir des passages fournis ;
- chaque affirmation porte un marqueur de citation [n] référençant une source ;
- si les passages ne suffisent pas, l'agent répond `unknown` (je ne sais pas)
  sans injecter de contenu ou contact non sourcé ;
- les marqueurs invalides sont supprimés à la validation (aucune citation
  ne peut pointer vers une source inexistante).
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any

from mistralai.client import Mistral

# mistral-medium-latest : réponses plus naturelles ; le périmètre reste
# strictement les centres ressources (system prompt + citations validées).
DEFAULT_MODEL = "mistral-medium-latest"

def _sources_block(docs) -> str:
    lines = []
    for i, d in enumerate(docs, 1):
        lines.append(f"[{i}] {d.titre} — {d.centre_nom} ({d.url})")
    return "\n".join(lines)


def _passages_block(docs) -> str:
    lines = []
    for i, d in enumerate(docs, 1):
        for p in d.passages:
            p = p.replace("\n", " ")
            lines.append(f"(source {i}) {p[:2200]}")
    return "\n".join(lines)


def _dept_ctx(dept) -> str:
    if dept is None:
        return ""
    if hasattr(dept, "model_dump"):
        d = dept.model_dump()
    elif isinstance(dept, dict):
        d = dept
    else:
        d = {"code": getattr(dept, "code", ""), "nom": getattr(dept, "nom", "")}
    nom, code = d.get("nom", ""), d.get("code", "")
    return f"département : {nom} ({code})" if nom else ""


def _system_prompt(profile: str, falc: bool, dept, situations, age, docs) -> str:
    ctx = []
    if dept:
        line = _dept_ctx(dept)
        if line:
            ctx.append(line)
    if situations:
        ctx.append("situations : " + ", ".join(situations))
    if age:
        ctx.append(f"âge de la personne concernée : {age}")
    ctx_line = ("Contexte de l'utilisateur : " + " ; ".join(ctx)) if ctx else ""

    falc_line = (
        "Mode FACILE À LIRE : phrases très courtes, mots simples, une idée par phrase, "
        "pas de jargon (sauf sigle expliqué), pas d'étapes numérotées."
        if falc
        else "Réponds en 2 à 3 paragraphes courts maximum."
    )

    profile_line = (
        "L'utilisateur est un PROFESSIONNEL (médecin, ESMS, coordinateur, travailleur social) : "
        "il connaît déjà la MDPH, la CDAPH et les bases. Ne lui explique PAS les notions de base, "
        "ne lui propose PAS de contacter la MDPH ou la Communauté 360 par défaut — il sait faire. "
        "Donne-lui du CONTENU MÉTIER : dispositifs précis, modalités, textes de référence (CASF, "
        "recommandations HAS, schémas nationaux, arrêtés), articulations entre acteurs, "
        "modalités de saisine des dispositifs experts (ARS, centres ressources, ERHR, PCPE…). "
        "Un contact n'est utile que s'il est un interlocuteur EXPERT du sujet "
        "(ex. ERHR pour handicap rare, CRA pour autisme, ARS pour les autorisations)."
        if profile == "pro"
        else "L'utilisateur est une famille ou un proche : vulgarise, explique les sigles, "
        "oriente vers les bons interlocuteurs."
    )

    return f"""Tu es le synthétiseur de Balise, un agent d'information et d'orientation sur le handicap en France.
{profile_line}
{ctx_line}

SÉPARATION ABSOLUE :
- Une étape précédente a pu utiliser de la connaissance générale pour trouver les documents. Tu n'y as pas accès.
- Dans cette étape, toute connaissance générale ou encyclopédique est INTERDITE.
- La question et le contexte utilisateur servent à comprendre le besoin, jamais de preuve.
- La réponse, le plan d'action et les contacts proviennent UNIQUEMENT des EXTRAITS AUTORISÉS ci-dessous (centres ressources, CASF et annuaires explicitement autorisés).

RÈGLES DE PREUVE :
1. Chaque paragraphe, étape et contact contient son ou ses numéros de source ET un extrait exact recopié depuis les EXTRAITS.
2. L'extrait exact doit soutenir directement le texte rédigé. N'ajoute aucun fait, délai, condition, rôle, droit, contact ou recommandation absent de cet extrait.
3. Si les extraits ne suffisent pas, mets "unknown": true. N'essaie pas de compléter depuis ta mémoire.
4. Pour un contact, le nom et le rôle doivent apparaître dans l'extrait exact. L'URL sera imposée par le serveur depuis la source : n'en invente pas.
5. Pour une étape d'action, l'action doit être directement fondée sur l'extrait ; ne transforme pas une information générale en obligation ou prescription.
6. Tu ne donnes jamais de conseil médical, juridique ou de décision à la place des institutions. Tu informes et orientes seulement selon les extraits.
7. Ne propose la MDPH que si les extraits la rendent pertinente pour la demande. Ne propose la Communauté 360 que si les extraits concernent une situation bloquée.
8. Ton direct, sobre, empathique. Français. VOUVOIE TOUJOURS l'utilisateur.
9. La relance contient une seule question courte et non factuelle, ou une chaîne vide.

{falc_line}

SOURCES AUTORISÉES :
{_sources_block(docs)}

EXTRAITS AUTORISÉS :
{_passages_block(docs)}

Réponds STRICTEMENT en JSON valide, sans texte autour :
{{
  "unknown": false,
  "paras": [
    {{"text": "reformulation prudente, sans marqueur [n]", "source_ids": [1], "quotes": ["extrait exact copié mot pour mot"]}}
  ],
  "steps": [
    {{"t": "étape courte", "d": "détail strictement soutenu", "source_ids": [1], "quotes": ["extrait exact copié mot pour mot"]}}
  ],
  "contacts": [
    {{"nom": "nom présent dans l'extrait", "role": "rôle présent dans l'extrait", "scope": "Local|Régional|National", "source_id": 1, "quote": "extrait exact copié mot pour mot"}}
  ],
  "followup": "une question courte pour préciser, ou chaîne vide"
}}
Si aucun élément n'est soutenu par un extrait exact, renvoie paras, steps et contacts vides avec "unknown": true."""


CITE_RE = re.compile(r"\[(\d+)\]")
BAD_CITE_RE = re.compile(r"\[[^\]\d][^\]]*\]")  # [Communauté 360], [source], etc.


def _validate_citations(text: str, n_sources: int) -> str:
    """Garde uniquement les marqueurs [n] valides (1..n_sources)."""

    def repl(m: re.Match) -> str:
        n = int(m.group(1))
        return m.group(0) if 1 <= n <= n_sources else ""

    text = BAD_CITE_RE.sub("", text)
    return CITE_RE.sub(repl, text)


def _norm_evidence(value: str) -> str:
    """Normalisation légère pour comparer une citation au passage source."""
    return " ".join(value.split()).casefold()


_SUPPORT_STOPWORDS = {
    "avec",
    "dans",
    "des",
    "elle",
    "entre",
    "est",
    "les",
    "leur",
    "leurs",
    "pour",
    "par",
    "plus",
    "que",
    "qui",
    "sont",
    "sur",
    "une",
    "vous",
}


def _support_tokens(value: str) -> set[str]:
    """Mots porteurs ramenés à un préfixe commun pour les flexions simples."""
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    tokens = set(re.findall(r"[a-z0-9]{3,}", value)) - _SUPPORT_STOPWORDS
    return {token[:7] if len(token) > 7 else token for token in tokens}


def _claim_text(item: dict) -> str:
    if item.get("text"):
        return str(item["text"])
    return " ".join(
        str(item.get(key, "")) for key in ("t", "d", "nom", "role") if item.get(key)
    )


def _claim_supported(item: dict, quotes: list[str]) -> bool:
    """Rejette une affirmation sans recouvrement lexical avec ses preuves."""
    claim = _support_tokens(_claim_text(item))
    evidence = _support_tokens(" ".join(quotes))
    if not claim or not evidence:
        return False
    overlap = len(claim & evidence)
    return overlap >= 1 and overlap / len(claim) >= 0.35


def _verified_evidence(item: dict, docs) -> list[int]:
    """Retourne uniquement les sources accompagnées d'un extrait littéral."""
    raw_ids = item.get("source_ids")
    if raw_ids is None and item.get("source_id") is not None:
        raw_ids = [item.get("source_id")]
    if not isinstance(raw_ids, list):
        raw_ids = []
    raw_quotes = item.get("quotes")
    if raw_quotes is None and item.get("quote") is not None:
        raw_quotes = [item.get("quote")]
    if not isinstance(raw_quotes, list):
        raw_quotes = []

    verified: list[int] = []
    for raw_id in raw_ids:
        try:
            source_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if not 1 <= source_id <= len(docs):
            continue
        haystack = _norm_evidence(" ".join(str(p) for p in docs[source_id - 1].passages))
        if not haystack:
            continue
        matched = [
            str(quote)
            for quote in raw_quotes
            if str(quote).strip() and _norm_evidence(str(quote)) in haystack
        ]
        if matched and _claim_supported(item, matched) and source_id not in verified:
            verified.append(source_id)
    return verified


def _refs(source_ids: list[int]) -> str:
    return "".join(f"[{n}]" for n in source_ids)


def _model_text(value: object, limit: int) -> str:
    """Retire les marqueurs libres du modèle avant d'ajouter les preuves vérifiées."""
    text = _validate_citations(str(value), n_sources=0)
    text = re.sub(r"\[[^\]\r\n]{0,100}\]", "", text)
    text = re.sub(r"https?://[^\s<>()]+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+([.,])", r"\1", text)
    return text.strip()[:limit]


def _clean(data: dict, docs) -> dict:
    """Fail-closed : aucun item n'est affiché sans extrait littéral vérifié."""
    paras: list[str] = []
    for raw in (data.get("paras") or [])[:5]:
        if not isinstance(raw, dict):
            continue
        source_ids = _verified_evidence(raw, docs)
        text = _model_text(raw.get("text", ""), 1600)
        if text and source_ids:
            paras.append(f"{text} {_refs(source_ids)}")

    steps: list[dict] = []
    for raw in (data.get("steps") or [])[:5]:
        if not isinstance(raw, dict):
            continue
        source_ids = _verified_evidence(raw, docs)
        title = _model_text(raw.get("t", ""), 120)
        detail = _model_text(raw.get("d", ""), 500)
        if title and detail and source_ids:
            steps.append({"t": title, "d": f"{detail} {_refs(source_ids)}"})

    contacts: list[dict] = []
    for raw in (data.get("contacts") or [])[:4]:
        if not isinstance(raw, dict):
            continue
        source_ids = _verified_evidence(raw, docs)
        nom = _model_text(raw.get("nom", ""), 120)
        role = _model_text(raw.get("role", ""), 300)
        if not (nom and role and source_ids):
            continue
        source_id = source_ids[0]
        contacts.append({
            "nom": nom,
            "role": f"{role} [{source_id}]",
            "scope": raw.get("scope")
            if raw.get("scope") in ("Local", "Régional", "National")
            else "National",
            # URL dérivée du document vérifié : jamais de lien libre du modèle.
            "url": docs[source_id - 1].url,
        })

    has_supported_content = bool(paras or steps or contacts)
    return {
        "unknown": not has_supported_content,
        "paras": paras,
        "steps": steps,
        "contacts": contacts,
        "followup": _model_text(data.get("followup", ""), 300),
    }


def build_messages(question: str, *, system_prompt: str, history=None) -> list[dict]:
    """Contexte B : extraits dans le système, historique utilisateur uniquement."""
    messages = [{"role": "system", "content": system_prompt}]
    for h in (history or [])[-6:]:
        role = h.get("role")
        content = str(h.get("content", ""))[:2000]
        if role == "user" and content:
            messages.append({"role": "user", "content": content})
    messages.append({"role": "user", "content": question})
    return messages


async def synthesize(
    question: str,
    docs,
    *,
    profile: str = "famille",
    falc: bool = False,
    dept=None,
    situations=None,
    age=None,
    history=None,
    effort: str = "medium",
) -> dict:
    """Appelle Mistral dans un contexte neuf puis applique le contrôle de preuves."""
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    from .planner import model_for_effort

    model = model_for_effort(effort)
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY manquante")

    messages = build_messages(
        question,
        system_prompt=_system_prompt(profile, falc, dept, situations, age, docs),
        history=history,
    )

    from typing import cast

    client = Mistral(api_key=api_key)
    resp = await client.chat.complete_async(
        model=model,
        messages=cast(Any, messages),
        temperature=0.2,
        max_tokens=1400,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    if not isinstance(raw, str):
        raw = "".join(getattr(c, "text", "") for c in raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return _clean(data, docs)


def unknown_answer(
    question: str,
    docs,
    profile: str = "famille",
    *,
    followup: str = "",
) -> dict:
    """Réponse neutre quand aucun élément n'a franchi le contrôle de preuves."""
    return {
        "unknown": True,
        "paras": [],
        "steps": [],
        "contacts": [],
        "followup": followup[:300],
        "glossary": {},
    }


def cited_payload(ans: dict, docs) -> list[dict]:
    """Sources réellement citées dans la réponse ([n] valides uniquement).

    Évite d'afficher des documents consultés mais jamais utilisés : ils donnent
    une impression de citations décoratives et polluent la traçabilité.
    """
    text = " ".join(ans.get("paras", []))
    for s in ans.get("steps", []):
        text += " " + s.get("t", "") + " " + s.get("d", "")
    for c in ans.get("contacts", []):
        text += " " + c.get("nom", "") + " " + c.get("role", "")
    used = {int(m) for m in CITE_RE.findall(text)}
    return [p for p in sources_payload(docs) if p["n"] in used]


def sources_payload(docs) -> list[dict]:
    return [
        {"n": i, "doc": d.titre, "centre": d.centre_nom, "url": d.url}
        for i, d in enumerate(docs, 1)
    ]