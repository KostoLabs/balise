"""Construction reproductible du snapshot CASF depuis LEGI/DILA."""

import io
import tarfile

from scripts.build_casf_index import apply_archive, article_from_xml, current_articles
from scripts.download_legi_deltas import list_delta_urls


def _xml(
    article_id="LEGIARTI000000000001",
    num="L114-1",
    etat="VIGUEUR",
    debut="2026-01-01",
    fin="2999-01-01",
    text="Texte intégral de l'article.",
):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ARTICLE><META><META_COMMUN><ID>{article_id}</ID></META_COMMUN>
<META_SPEC><META_ARTICLE><NUM>{num}</NUM><ETAT>{etat}</ETAT>
<DATE_DEBUT>{debut}</DATE_DEBUT><DATE_FIN>{fin}</DATE_FIN></META_ARTICLE></META_SPEC></META>
<CONTEXTE><TEXTE cid="LEGITEXT000006074069"><TITRE_TXT>CASF</TITRE_TXT>
<TM><TITRE_TM>Partie législative</TITRE_TM><TM><TITRE_TM>Livre Ier</TITRE_TM></TM></TM>
</TEXTE></CONTEXTE><BLOC_TEXTUEL><CONTENU><p>{text}</p></CONTENU></BLOC_TEXTUEL>
<NOTA><CONTENU><p>Note séparée.</p></CONTENU></NOTA></ARTICLE>""".encode()


def test_article_from_xml_keeps_dates_breadcrumb_and_full_text():
    long_text = "Disposition complète. " * 400
    article = article_from_xml(_xml(text=long_text))
    assert article["id"] == "LEGIARTI000000000001"
    assert article["num"] == "L114-1"
    assert article["date_debut"] == "2026-01-01"
    assert article["date_fin"] == "2999-01-01"
    assert article["breadcrumb"] == "Partie législative > Livre Ier"
    assert article["texte"] == long_text.strip()
    assert len(article["texte"]) > 4000
    assert article["nota"] == "Note séparée."


def test_apply_archive_updates_articles_and_honours_casf_deletions(tmp_path):
    archive = tmp_path / "delta.tar.gz"
    old_id = "LEGIARTI000000000001"
    new_id = "LEGIARTI000000000002"
    with tarfile.open(archive, "w:gz") as tar:
        deletion = (
            "legi/global/code_et_TNC_en_vigueur/code_en_vigueur/LEGI/TEXT/"
            "00/00/06/07/40/LEGITEXT000006074069/article/LEGI/ARTI/"
            f"00/00/00/00/00/{old_id}\n"
        ).encode()
        info = tarfile.TarInfo("delta/liste_suppression_legi.dat")
        info.size = len(deletion)
        tar.addfile(info, io.BytesIO(deletion))

        body = _xml(article_id=new_id, num="D312-162")
        path = (
            "delta/legi/global/code_et_TNC_en_vigueur/code_en_vigueur/LEGI/TEXT/"
            "00/00/06/07/40/LEGITEXT000006074069/article/LEGI/ARTI/"
            f"00/00/00/00/00/{new_id}.xml"
        )
        info = tarfile.TarInfo(path)
        info.size = len(body)
        tar.addfile(info, io.BytesIO(body))

    articles = {old_id: article_from_xml(_xml(article_id=old_id))}
    stats = apply_archive(archive, articles)
    assert old_id not in articles
    assert articles[new_id]["num"] == "D312-162"
    assert stats == {"updated": 1, "deleted": 1}


def test_current_articles_uses_state_and_validity_window():
    articles = {
        "current": article_from_xml(_xml()),
        "future": article_from_xml(
            _xml(article_id="LEGIARTI000000000002", debut="2027-01-01")
        ),
        "ended": article_from_xml(
            _xml(article_id="LEGIARTI000000000003", fin="2026-01-01")
        ),
        "abroge": article_from_xml(
            _xml(article_id="LEGIARTI000000000004", etat="ABROGE")
        ),
    }
    selected = current_articles(articles, "2026-09-16")
    assert [article["id"] for article in selected] == ["LEGIARTI000000000001"]


def test_delta_listing_is_bounded_after_base_and_by_snapshot_date():
    html = """
    <a href="LEGI_20250713-205013.tar.gz">same day after base</a>
    <a href="LEGI_20250712-211706.tar.gz">before base</a>
    <a href="LEGI_20260915-211944.tar.gz">latest expected</a>
    <a href="LEGI_20260916-210000.tar.gz">after requested snapshot</a>
    """
    urls = list_delta_urls(html, after="20250713-140000", as_of="2026-09-15")
    assert [url.rsplit("/", 1)[-1] for url in urls] == [
        "LEGI_20250713-205013.tar.gz",
        "LEGI_20260915-211944.tar.gz",
    ]
