"""Agent de synthèse Balise (Mistral) — citations strictes, zéro invention.

Contrat :
- la réponse est produite UNIQUEMENT à partir des passages fournis ;
- chaque affirmation porte un marqueur de citation [n] référençant une source ;
- si les passages ne suffisent pas, l'agent répond `unknown` (je ne sais pas)
  et propose des contacts de repère (publics, vérifiables) ;
- les marqueurs invalides sont supprimés à la validation (aucune citation
  ne peut pointer vers une source inexistante).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from mistralai.client import Mistral

# mistral-medium-latest : réponses plus naturelles ; le périmètre reste
# strictement les centres ressources (system prompt + citations validées).
DEFAULT_MODEL = "mistral-medium-latest"

# Repères publics, vérifiables — utilisés uniquement comme contacts d'orientation.
REPERES = [
    {
        "nom": "MDPH de votre département",
        "role": "Guichet unique : dépôt du dossier, évaluation, décisions (CDAPH).",
        "scope": "Local",
        "url": "https://lannuaire.service-public.gouv.fr/navigation/maison_handicapees",
    },
    {
        "nom": "Communauté 360",
        "role": "0 800 360 360 — appui départemental quand une situation est bloquée.",
        "scope": "Local",
        "url": "https://solidarites-sante.gouv.fr/affaires-sociales-et-familiales/handicap/article/communaute-360",
    },
    {
        "nom": "MDPH en ligne (CNSA)",
        "role": "Téléservices et fiches pratiques pour préparer les démarches.",
        "scope": "National",
        "url": "https://mdphenligne.cnsa.fr/",
    },
    {
        "nom": "Autisme Info Service",
        "role": "0 800 71 40 40 — information et écoute sur l'autisme et les TND.",
        "scope": "National",
        "url": "https://autismeinfoservice.fr/",
    },
]

GLOSSARY = {
    "MDPH": "Maison départementale des personnes handicapées : le guichet unique de votre département. C'est elle qui reçoit les demandes, évalue la situation et ouvre les droits.",
    "CDAPH": "Commission des droits et de l'autonomie des personnes handicapées : la commission, au sein de la MDPH, qui prend les décisions (droits, orientations).",
    "IME": "Institut médico-éducatif : établissement qui accueille en journée des enfants avec une déficience intellectuelle, avec école et soins sur place.",
    "ESMS": "Établissement ou service médico-social : la famille d'établissements et de services (IME, SESSAD, foyer, SAVS…) qui accompagnent au quotidien.",
    "SESSAD": "Service d'éducation spéciale et de soins à domicile : une équipe qui intervient là où vit et apprend l'enfant, y compris à l'école.",
    "SAVS": "Service d'accompagnement à la vie sociale : soutien social et éducatif pour un adulte qui vit chez lui.",
    "SAMSAH": "Service d'accompagnement médico-social pour adultes handicapés : comme un SAVS, mais avec en plus une équipe de soins coordonnés.",
    "DAC": "Dispositif d'appui à la coordination : appui aux professionnels et aux personnes pour les situations complexes, quel que soit l'âge ou la pathologie.",
    "PCPE": "Pôle de compétences et de prestations externalisées : finance et coordonne des interventions sur mesure quand aucune place n'est disponible.",
    "CRA": "Centre ressources autisme : ressource régionale d'information, d'appui au diagnostic et de formation sur l'autisme.",
    "CReHPsy": "Centre ressource handicap psychique : ressource régionale pour les situations de handicap d'origine psychique.",
    "PCO": "Plateforme de coordination et d'orientation : parcours de bilan et d'intervention précoce, avant diagnostic, pour les troubles du neurodéveloppement.",
    "AEEH": "Allocation d'éducation de l'enfant handicapé : aide financière versée aux parents d'un enfant en situation de handicap.",
    "PCH": "Prestation de compensation du handicap : aide qui finance les besoins liés au handicap (aide humaine, technique, aménagements).",
    "AESH": "Accompagnant d'élève en situation de handicap : la personne qui accompagne l'élève en classe.",
    "GEVA-Sco": "Document d'évaluation scolaire renseigné par l'équipe éducative et joint au dossier MDPH.",
}


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

    return f"""Tu es Balise, un agent d'information et d'orientation sur le handicap en France.
{profile_line}
{ctx_line}

RÈGLES ABSOLUES :
1. Tu ne t'appuies QUE sur les EXTRAITS ci-dessous, issus de centres ressources publics. Tu n'utilises aucune autre connaissance.
2. Chaque affirmation factuelle doit porter un marqueur de citation [n] correspondant à la source n listée. Aucune phrase factuelle sans marqueur.
3. Si les extraits ne permettent pas de répondre de façon fiable : mets "unknown": true et n'affirme rien. ATTENTION : si un extrait contient DIRECTEMENT la réponse demandée — en particulier des coordonnées d'établissement (annuaire FINESS : nom, adresse, téléphone), une définition, un texte de loi — il PERMET de répondre : unknown est interdit dans ce cas. Transcris la réponse depuis l'extrait.
4. Tu ne donnes jamais de conseil médical, juridique ou de décision à la place des institutions. Tu orientes.
5. La réponse doit être SUBSTANCIELLE et directement utile : ce que le dispositif est, à quoi il sert concrètement, pour qui, comment ça se passe, qui pilote/finance, points d'attention. Pas de remplissage, pas de généralités. Si la question est professionnelle, réponds au niveau professionnel.
6. Contacts : UNIQUEMENT des interlocuteurs directement utiles à la question posée, précisés dans les extraits. Si les extraits contiennent des coordonnées (ADRESSE, TÉLÉPHONE), transcris-les intégralement dans la réponse et le contact. Ne propose jamais MDPH/Communauté 360 par défaut : MDPH seulement si la question porte sur les droits/l'orientation, Communauté 360 seulement pour une situation bloquée. N'invente jamais de coordonnées.
7. Tonne : direct, sobre, empathique, sans pathos. Français. VOUVOIE TOUJOURS l'utilisateur, même s'il tutoie.
8. Question de relance : si la réponse gagnerait à être précisée (type de handicap, âge de la personne, ville, orientation déjà reçue…), pose exactement UNE question courte et utile dans "followup". Sinon renvoie une chaîne vide.

{falc_line}

CONTACTS DE REPÈRE (uniquement pour orienter, jamais comme source d'affirmation) :
""" + "\n".join(
        f"- {c['nom']} ({c['scope']}) — {c['role']} — {c['url']}" for c in REPERES
    ) + f"""

SOURCES (citations possibles) :
{_sources_block(docs)}

EXTRAITS :
{_passages_block(docs)}

Réponds STRICTEMENT en JSON valide, sans texte autour, avec ce schéma :
{{
  "unknown": bool,
  "paras": ["paragraphe de réponse, avec marqueurs [n]", "..."],
  "steps": [{{"t": "étape courte", "d": "détail de l'étape"}}],
  "contacts": [{{"nom": "MDPH du Rhône", "role": "ce que ce contact fait", "scope": "Local|Régional|National", "url": "https://..."}}],
  "followup": "une seule question de relance courte pour affiner la réponse, ou chaîne vide"
}}
Si tu n'as pas d'étapes ou de contacts utiles, renvoie des listes vides.
IMPORTANT : les marqueurs de citation sont des NUMÉROS entre crochets ([1], [2]…) qui référencent la source n de la liste SOURCES. Jamais de texte entre crochets."""


CITE_RE = re.compile(r"\[(\d+)\]")
BAD_CITE_RE = re.compile(r"\[[^\]\d][^\]]*\]")  # [Communauté 360], [source], etc.


def _validate_citations(text: str, n_sources: int) -> str:
    """Garde uniquement les marqueurs [n] valides (1..n_sources)."""

    def repl(m: re.Match) -> str:
        n = int(m.group(1))
        return m.group(0) if 1 <= n <= n_sources else ""

    text = BAD_CITE_RE.sub("", text)
    return CITE_RE.sub(repl, text)


def _clean(data: dict, docs) -> dict:
    """Valide et borne la sortie du modèle ; supprime toute citation invalide."""
    n = len(docs)
    paras = []
    for p in (data.get("paras") or [])[:5]:
        t = _validate_citations(str(p).strip(), n)
        if t:
            paras.append(t)
    steps = [
        {"t": str(s.get("t", ""))[:120], "d": str(s.get("d", ""))[:400]}
        for s in (data.get("steps") or [])[:5]
        if s and str(s.get("t", "")).strip()
    ]
    contacts = []
    for c in (data.get("contacts") or [])[:4]:
        nom = str(c.get("nom", "")).strip()
        if not nom:
            continue
        contacts.append({
            "nom": nom[:120],
            "role": str(c.get("role", ""))[:300],
            "scope": c.get("scope") if c.get("scope") in ("Local", "Régional", "National") else "National",
            "url": str(c.get("url", ""))[:500],
        })
    return {
        "unknown": bool(data.get("unknown")),
        "paras": paras,
        "steps": steps,
        "contacts": contacts,
        "followup": str(data.get("followup", "")).strip()[:300],
    }


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
) -> dict:
    """Appelle Mistral pour rédiger la réponse sourcée ; valide les citations."""
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    model = os.environ.get("CHAT_MODEL", DEFAULT_MODEL)
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY manquante")

    messages = [
        {"role": "system", "content": _system_prompt(profile, falc, dept, situations, age, docs)}
    ]
    for h in (history or [])[-4:]:
        role = h.get("role")
        content = str(h.get("content", ""))[:2000]
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})

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


def unknown_answer(question: str, docs, profile: str = "famille") -> dict:
    """Réponse honnête quand la recherche n'a rien trouvé : zéro invention.

    Pas de contacts plaqués : pour un pro, aucun encadré ne l'aide ; pour une
    famille, on renvoie uniquement le numéro national d'écoute.
    """
    paras = [
        "Je ne sais pas répondre de façon fiable à cette question avec les centres ressources publics que je consulte.",
        "Je préfère vous le dire plutôt que d'avancer une information incertaine. Une personne pourra vous répondre précisément.",
    ]
    if profile == "pro":
        contacts = []
        paras.append(
            "Reformulez avec le dispositif, le sigle ou le nom exact : j'interroge mieux les centres ressources avec des termes précis."
        )
    else:
        contacts = [REPERES[3]]  # Autisme Info Service : ligne d'écoute nationale, pas un guichet
        paras.append("Pour en parler avec une personne, une ligne d'écoute nationale existe : 0 800 71 40 40.")
    return {
        "unknown": True,
        "paras": paras,
        "steps": [],
        "contacts": contacts,
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
    used = {int(m) for m in CITE_RE.findall(text)}
    return [p for p in sources_payload(docs) if p["n"] in used]


def sources_payload(docs) -> list[dict]:
    return [
        {"n": i, "doc": d.titre, "centre": d.centre_nom, "url": d.url}
        for i, d in enumerate(docs, 1)
    ]


def glossary_for(paras: list[str]) -> dict[str, str]:
    """Ne renvoie que les sigles effectivement présents dans la réponse."""
    text = " ".join(paras)
    return {
        k: v for k, v in GLOSSARY.items()
        if re.search(r"\b" + re.escape(k) + r"\b", text)
    }