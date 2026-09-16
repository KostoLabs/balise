"""Agent Balise : un "researcher" par centre ressource, exécutés en parallèle.

Chaque agent cherche sur le site d'un centre ressource, extrait les passages
pertinents, puis un agent "synthétiseur" rédige la réponse en citant ses
sources (contrat de citations strict).
"""

from __future__ import annotations

import asyncio
import html as html_mod
import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus, urljoin, urlparse

import httpx

from .ressources import SITES

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# ---- Extraction de texte (HTMLParser stdlib — pas de dépendance externe) ----
from html.parser import HTMLParser

BLOCK_TAGS = {
    "p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
    "td", "th", "figcaption", "section", "article", "div", "main",
}
NO_TEXT_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "svg", "form"}
WORD = re.compile(r"[\wÀ-ÿ]+")
TAG_BAD = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")


class _TextExtractor(HTMLParser):
    """Extrait les blocs de texte (p, li, h1-h6, td…) avec leurs positions."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._skip_depth = 0
        self._cur: list[str] | None = None
        self._block_tag: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in NO_TEXT_TAGS:
            self._skip_depth += 1
        elif tag in BLOCK_TAGS:
            if self._cur is not None:
                self._flush()
            self._cur = []
            self._block_tag = tag
            # <p> imbriqué dans <div> : on garde le div comme bloc
            if self._block_tag in ("div", "section", "article", "main") and tag == "p":
                self._block_tag = "p"

    def handle_endtag(self, tag: str) -> None:
        if tag in NO_TEXT_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip_depth or self._cur is None:
            return
        self._cur.append(data)

    def _flush(self) -> None:
        if self._cur is None:
            return
        text = WS.sub(" ", "".join(self._cur)).strip()
        if len(WORD.findall(text)) >= 4:
            self.blocks.append(text)
        self._cur = None
        self._block_tag = None

    def close(self) -> None:
        super().close()
        self._flush()


def html_blocks(html: str) -> list[str]:
    p = _TextExtractor()
    p.feed(html)
    p.close()
    return p.blocks


# ---- Recherche de liens pertinents dans une page de résultats ----
HREF_RE = re.compile(r'href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
TITLE_RE = re.compile(r"<[^>]+>")


def _netloc(url: str) -> str:
    return urlparse(url).netloc.lower()


def _allowed(url: str, allowed_domains: list[str]) -> bool:
    """Vrai si le domaine de l'URL fait partie de l'allowlist (ou du site lui-même)."""
    n = _netloc(url)
    return any(n == d or n.endswith("." + d) for d in allowed_domains)


def parse_search_results(
    html: str, base_url: str, result_link: str | None, allowed_domains: list[str] | None = None
) -> list[tuple[str, str]]:
    """Retourne [(url, titre)] candidats depuis une page de résultats de recherche."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    if not allowed_domains:
        allowed_domains = [_netloc(base_url).removeprefix("www.")]
    for m in HREF_RE.finditer(html):
        href, inner = m.group(1), m.group(2)
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        url = urljoin(base_url, href)
        if not url.startswith("http"):
            continue
        # Allowlist de domaines (un site peut servir ses fiches depuis un domaine jumeau)
        if not _allowed(url, allowed_domains):
            continue
        if result_link and result_link not in url:
            continue
        title = WS.sub(" ", TITLE_RE.sub("", inner)).strip()
        title = html_mod.unescape(title)
        if len(title) < 8 or len(title) > 200:
            continue
        # Écarte les liens de navigation génériques
        low = title.lower()
        if any(x in low for x in ("accueil", "mentions légales", "plan du site", "se connecter",
                                  "newsletter", "contact", "recherche", "cookie",
                                  "confidentialit", "rgpd", "données personnelles",
                                  "politique de")):
            continue
        if url not in seen:
            seen.add(url)
            out.append((url, title))
    return out


# ---- Recherche de passages pertinents dans une page ----
STOP_FR = {
    "le", "la", "les", "un", "une", "du", "de", "des", "et", "ou", "à", "au", "aux", "en",
    "que", "qui", "quoi", "quel", "quelle", "quels", "quelles", "pour", "par",
    "dans", "sur", "avec", "sans", "est", "sont", "peut", "être", "avoir", "plus", "moins",
    "comment", "faire", "faut", "il", "elle", "on", "nous", "vous", "je", "mon",
    "ma", "son", "sa", "ses", "leur", "leurs", "cette", "cet", "ce", "ces", "se", "si",
    "entre", "chez", "vers", "aussi", "alors", "quand", "après", "avant", "depuis", "très",
    "tout", "tous", "toutes", "toujours", "jamais", "peut-être", "beaucoup", "quelque",
}


def keywords(question: str, extra: list[str]) -> list[str]:
    words = [w.strip(".,;:!?()\"'«»").lower() for w in WORD.findall(question)]
    words = [w for w in words if len(w) >= 3 and w not in STOP_FR]
    for e in extra:
        if e:
            words.append(e.lower())
    # unique en conservant l'ordre
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def score_block(block: str, kws: list[str]) -> int:
    low = block.lower()
    score = 0
    for i, k in enumerate(kws):
        if k in low:
            score += max(1, 6 - min(5, i))  # les premiers mots comptent plus
    return score


@dataclass
class Page:
    url: str
    titre: str
    passages: list[str] = field(default_factory=list)


@dataclass
class Doc:
    """Document candidat retenu par un agent centre ressource."""
    centre_id: str
    centre_nom: str
    url: str
    titre: str
    passages: list[str] = field(default_factory=list)
    score: int = 0


async def fetch(client: httpx.AsyncClient, url: str) -> str:
    try:
        r = await client.get(url)
        if r.status_code == 200:
            return r.text
    except httpx.HTTPError:
        pass
    return ""


async def research_one(
    client: httpx.AsyncClient, site: dict, question: str, kws: list[str]
) -> list[Doc]:
    """Agent d'un centre ressource : recherche interne + extraction des passages.

    Retourne 0 à `max_docs` documents pertinents, avec passages extraits.
    """
    max_docs = 3
    docs: list[Doc] = []

    candidates: list[tuple[str, str]] = []
    if site.get("search_url"):
        q = quote_plus(" ".join(kws[:6]))
        url = site["search_url"].format(q=q)
        # httpx ré-encode le % : construire l'URL en deux temps pour l'éviter
        url = url.replace("%25", "%").replace("%2B", "+")
        html = await fetch(client, url)
        candidates = parse_search_results(
            html, site["url"], site.get("result_link"), site.get("allowed_domains")
        )

    # Extraction des passages pour les meilleurs candidats
    # (tri par pertinence du titre : les pages de résultats contiennent aussi des liens de menu)
    candidates = sorted(
        candidates, key=lambda c: -score_block(c[1], kws)
    )
    fetched: list[tuple[str, str, list[str]]] = []
    for page_url, title in candidates[: max_docs * 2]:
        html = await fetch(client, page_url)
        if not html:
            continue
        blocks = html_blocks(html)
        if blocks:
            fetched.append((page_url, title, blocks))
    if not fetched:
        return docs

    # Termes rares : présents dans au plus 1/3 des pages candidates.
    # Une page n'est pertinente que si elle contient un terme rare de la question —
    # sinon elle ne doit son score qu'à des mots fréquents (« première demande »…).
    bodies = [" ".join(bl).lower() for _, _, bl in fetched]
    n = len(bodies)
    df = {k: sum(1 for b in bodies if k in b) for k in kws}
    rare = [k for k in kws if 0 < df[k] <= max(1, n // 3)]

    for (page_url, title, blocks), body in zip(fetched, bodies):
        overlap = sum(1 for k in kws if k in body)
        if overlap < 2:
            continue
        scored = sorted(
            ((score_block(b, kws), b) for b in blocks), key=lambda x: -x[0]
        )
        top_score = scored[0][0] if scored else 0
        if top_score < 5:
            continue
        best = [b for s, b in scored if s >= 3][:4]
        if not best:
            continue
        # Un terme rare doit figurer dans un PASSAGE retenu (pas seulement dans
        # le gabarit de page : pied de page, menu, mentions…).
        if rare and not any(k in " ".join(best).lower() for k in rare):
            continue
        docs.append(Doc(centre_id=site["id"], centre_nom=site["nom"], url=page_url,
                        titre=title, passages=best, score=top_score + 2 * overlap))

    # Score global : bonus si le titre contient des mots-clés
    for d in docs:
        t = d.titre.lower()
        d.score += sum(3 for k in kws[:6] if k in t)
    return docs


async def research_all(question: str, extra_context: list[str], timeout: float = 12.0) -> list[Doc]:
    """Exécute en parallèle un agent par centre ressource. Retourne les documents retenus."""
    kws = keywords(question, extra_context)
    async with httpx.AsyncClient(
        headers={"User-Agent": UA, "Accept-Language": "fr"},
        follow_redirects=True,
        timeout=timeout,
    ) as client:
        results = await asyncio.gather(
            *(research_one(client, s, question, kws) for s in SITES if s.get("search_url"))
        )
    docs = [d for sub in results for d in sub]
    # Diversité : max 2 documents par centre ressource
    per_centre: dict[str, int] = {}
    diverse: list[Doc] = []
    for d in sorted(docs, key=lambda d: -d.score):
        if per_centre.get(d.centre_id, 0) < 2:
            per_centre[d.centre_id] = per_centre.get(d.centre_id, 0) + 1
            diverse.append(d)
    return diverse