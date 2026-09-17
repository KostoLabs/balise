"""Tests du noyau Balise : extraction, scoring, citations — sans réseau."""


from app.agent import _validate_citations, sources_payload
from app.research import html_blocks, keywords, parse_search_results, score_block


def test_html_blocks_extracts_paragraphs():
    html = """<html><body>
    <script>var x = "ignored";</script>
    <nav><a href="/">Accueil</a></nav>
    <main>
      <h1>La MDPH reçoit votre dossier</h1>
      <p>La Maison départementale des personnes handicapées évalue la situation
      et ouvre les droits après décision de la CDAPH.</p>
      <p>Courte.</p>
    </main>
    </body></html>"""
    blocks = html_blocks(html)
    assert any("MDPH" in b for b in blocks)
    assert all("ignored" not in b for b in blocks)
    assert all(len(b) >= 4 for b in blocks)


def test_parse_search_results_filters_same_site():
    html = """
    <a href="/particuliers/vosdroits/F16442">Allocation adulte handicapé</a>
    <a href="https://exemple.malin/vosdroits">Faux document</a>
    <a href="/particuliers/vosdroits/F10028">Prestation compensation</a>
    <a href="/particuliers/vosdroits/">Accueil droits</a>
    <a href="/actus">Actualités</a>
    """
    res = parse_search_results(
        html,
        "https://www.service-public.fr/particuliers/recherche?keyword=x",
        "/particuliers/vosdroits/",
    )
    urls = [u for u, _ in res]
    assert all(u.startswith("https://www.service-public.fr/") for u in urls)
    assert "https://exemple.malin/vosdroits" not in urls
    assert len(urls) >= 1


def test_keywords_and_scoring():
    kws = keywords("Comment constituer un dossier MDPH pour mon enfant ?", ["Autisme / TND"])
    assert "mdph" in kws and "dossier" in kws
    assert "comment" not in kws  # stopword
    b_hi = "Le dossier MDPH se dépose avec un certificat médical et le projet de vie."
    b_lo = "Le service public informe sur les impôts et la fiscalité locale."
    assert score_block(b_hi, kws) > score_block(b_lo, kws)


def test_validate_citations_drops_invalid_markers():
    out = _validate_citations("Les délais sont de 4 mois [1] et le recours existe [7].", n_sources=2)
    assert "[1]" in out and "[7]" not in out


def test_sources_payload_numbering():
    class D:
        def __init__(self, **kw):
            self.__dict__.update(kw)
    docs = [
        D(titre="Guide MDPH", centre_nom="CNSA", url="https://x/1"),
        D(titre="Fiche aidant", centre_nom="Unafam", url="https://x/2"),
    ]
    payload = sources_payload(docs)
    assert [p["n"] for p in payload] == [1, 2]
    assert payload[0]["doc"] == "Guide MDPH"
