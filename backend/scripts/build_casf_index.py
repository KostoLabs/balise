"""Construit un snapshot CASF courant depuis le stock et les différentiels LEGI.

Usage :
  python scripts/build_casf_index.py /tmp/legi-global.tar.gz \
      --deltas-dir /tmp/legi-deltas --as-of 2026-09-15 \
      --out data/casf_index.json

Les archives différentielles doivent être nommées LEGI_YYYYMMDD-HHMMSS.tar.gz.
Elles sont appliquées dans l'ordre chronologique après le stock global.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

CASF_ID = "LEGITEXT000006074069"
LEGI_ARTICLE = re.compile(r"LEGIARTI\d{12}")
BASE_URL = "https://echanges.dila.gouv.fr/OPENDATA/LEGI/"


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join(" ".join(element.itertext()).split())


def article_from_xml(xml_bytes: bytes) -> dict | None:
    """Parse un XML ARTICLE DILA sans tronquer son texte normatif."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    context = root.find("CONTEXTE/TEXTE")
    if context is None or context.get("cid") != CASF_ID:
        return None
    article_id = (root.findtext("META/META_COMMUN/ID") or "").strip()
    if not LEGI_ARTICLE.fullmatch(article_id):
        return None
    meta = root.find("META/META_SPEC/META_ARTICLE")
    if meta is None:
        return None
    titles = [
        _text(element)
        for element in root.findall(".//CONTEXTE/TEXTE//TITRE_TM")
        if _text(element)
    ]
    return {
        "id": article_id,
        "num": (meta.findtext("NUM") or "").strip(),
        "etat": (meta.findtext("ETAT") or "").strip(),
        "date_debut": (meta.findtext("DATE_DEBUT") or "").strip(),
        "date_fin": (meta.findtext("DATE_FIN") or "").strip(),
        "breadcrumb": " > ".join(titles),
        "texte": _text(root.find("BLOC_TEXTUEL/CONTENU")),
        "nota": _text(root.find("NOTA/CONTENU")),
    }


def _read_member(tar: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    stream = tar.extractfile(member)
    return stream.read() if stream is not None else b""


def apply_archive(path: str | Path, articles: dict[str, dict]) -> dict[str, int]:
    """Applique suppressions puis mises à jour d'une archive LEGI."""
    updated = deleted = 0
    with tarfile.open(path, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            if not member.isfile() or not member.name.endswith("liste_suppression_legi.dat"):
                continue
            for raw_line in _read_member(tar, member).decode("utf-8", "replace").splitlines():
                if CASF_ID not in raw_line:
                    continue
                match = LEGI_ARTICLE.search(Path(raw_line).name)
                if match and articles.pop(match.group(0), None) is not None:
                    deleted += 1
        for member in members:
            filename = Path(member.name).name
            if (
                not member.isfile()
                or CASF_ID not in member.name
                or not filename.endswith(".xml")
                or not LEGI_ARTICLE.fullmatch(filename[:-4])
            ):
                continue
            article = article_from_xml(_read_member(tar, member))
            if article is not None:
                articles[article["id"]] = article
                updated += 1
    return {"updated": updated, "deleted": deleted}


def current_articles(articles: dict[str, dict], as_of: str) -> list[dict]:
    """Sélectionne les versions en vigueur à la date ISO donnée."""
    target = date.fromisoformat(as_of)
    selected = []
    for article in articles.values():
        if article.get("etat") != "VIGUEUR" or not article.get("texte") or not article.get("num"):
            continue
        try:
            start = date.fromisoformat(article.get("date_debut") or "0001-01-01")
            end = date.fromisoformat(article.get("date_fin") or "2999-01-01")
        except ValueError:
            continue
        if start <= target < end:
            selected.append(article)
    return sorted(selected, key=lambda article: (article["num"], article["id"]))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(base: Path, deltas: list[Path], as_of: str, out: Path) -> dict:
    articles: dict[str, dict] = {}
    archives = []
    for index, archive in enumerate([base, *deltas]):
        stats = apply_archive(archive, articles)
        archives.append(
            {
                "filename": archive.name,
                "url": BASE_URL + archive.name,
                "sha256": _sha256(archive),
                **stats,
            }
        )
        print(
            f"[{index + 1}/{len(deltas) + 1}] {archive.name}: "
            f"+{stats['updated']} -{stats['deleted']} ({len(articles)} versions)",
            flush=True,
        )
    current = current_articles(articles, as_of)
    payload = {
        "meta": {
            "publisher": "DILA",
            "dataset": "LEGI",
            "code_id": CASF_ID,
            "as_of": as_of,
            "archives": archives,
            "article_count": len(current),
        },
        "articles": current,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("--deltas-dir", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--out", type=Path, default=Path("data/casf_index.json"))
    args = parser.parse_args()
    date.fromisoformat(args.as_of)
    deltas = sorted(
        path
        for path in args.deltas_dir.glob("LEGI_*.tar.gz")
        if path.name[5:13] <= args.as_of.replace("-", "")
    )
    payload = build(args.base, deltas, args.as_of, args.out)
    print(f"{len(payload['articles'])} articles en vigueur → {args.out}")


if __name__ == "__main__":
    main()
