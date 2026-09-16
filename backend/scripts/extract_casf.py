"""Extrait le Code de l'action sociale et des familles (CASF) du dump LEGI DILA.

Le dump Freemium LEGI (echanges.dila.gouv.fr) contient l'arborescence des codes :
  LEGITEXT000006074069 = CASF (Code de l'action sociale et des familles)
Chaque article est un fichier XML LEGIARTI*.xml. On extrait les articles du
CASF avec numéro, état, texte — vers backend/data/casf_articles.json.

Usage (après téléchargement du tar.gz, ~1,2 Go) :
    cd backend && .venv/bin/python scripts/extract_casf.py /tmp/legi-global.tar.gz
Écrit : data/casf_articles.json
"""

import json
import sys
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
CASF_TEXTE = "LEGITEXT000006074069"

# Livres du CASF utiles pour Balise (tout sauf le très réglementaire financier)
# on garde tout, le filtre se fera à l'usage
FIELDS = ("ID", "NUM", "ETAT", "TITRE", "SM", "CONTEXTE", "TEXTE", "LIENS", "HIST")


def article_from_xml(xml_bytes: bytes) -> dict | None:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    meta = root.find("META_SPEC/META_TEXTE")
    if meta is None:
        return None
    titres = root.find("META_TEXTE")
    num = meta.findtext("TITRE") or meta.findtext("NUM") or ""
    etat = meta.findtext("ETAT") or ""
    titre_txt = titres.findtext("TITRE") if titres is not None else ""
    contexte = meta.findtext("CONTEXTE") or ""
    # structure: TEXTE/CONTENU avec <p> etc.
    contenu = root.find("TEXTE/CONTENU")
    texte = ""
    if contenu is not None:
        for p in contenu.iter():
            if p.text:
                texte += p.text.strip() + " "
            if p.tail:
                texte += p.tail.strip() + " "
    return {
        "id": root.findtext(".//ID") or "",
        "num": num.strip(),
        "etat": etat.strip(),
        "contexte": contexte.strip()[:400],
        "titre": (titre_txt or "").strip()[:200],
        "texte": " ".join(texte.split())[:4000],
    }


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/legi-global.tar.gz"
    out = []
    n_scanned = 0
    with tarfile.open(src, "r:gz") as tar:
        for m in tar:
            if not m.isfile():
                continue
            path = m.name
            # articles du CASF uniquement
            if not path.endswith(".xml"):
                continue
            if "LEGIARTI" not in path.split("/")[-1]:
                continue
            # le dump range par LEGITEXT : chemin contient le texte
            if CASF_TEXTE not in path and "074069" not in path:
                continue
            n_scanned += 1
            f = tar.extractfile(m)
            if f is None:
                continue
            art = article_from_xml(f.read())
            if art and art["texte"] and art["etat"] == "VIGUEUR":
                out.append(art)
    dest = DATA / "casf_articles.json"
    dest.write_text(json.dumps(out, ensure_ascii=False))
    print(f"{n_scanned} articles CASF scannés, {len(out)} en vigueur → {dest}")


if __name__ == "__main__":
    main()