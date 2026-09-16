"""Construit l'index ESMS depuis le fichier public FINESS structures (JSON).

Source : data.gouv.fr — « FINESS - Structures » (fichier mensuel, ANS) :
entités géographiques (EGE) avec adresse, téléphone, commune, catégorie.
Les libellés des catégories viennent de categ_libelles.json (extraits du
référentiel t_finess). L'index ne garde que les catégories médico-sociales.

Usage :
    cd backend && .venv/bin/python scripts/build_esms_index.py [finess.json]
Écrit : data/esms_index.json
"""

import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# catégités médico-sociales pertinentes pour Balise (handicap + enfance),
# hors sanitaire strict et hors personnes âgées
MS_CATS = {
    "156", "189", "190",          # CMP, CMPP, CAMSP
    "175", "183", "188", "192", "193", "196", "198", "202", "203", "204",
    "205", "206", "207", "208",   # foyers enfance, IME, IEM, ITEP, SESSAD…
    "252", "253", "370", "377", "379", "380",
    "382", "390", "395", "396", "397", "437", "445", "446", "448", "449",
    "608", "609",                 # équipes mobiles, MDPH
}
# élargit : toute catégorie dont le libellé matche les mots médico-social/handicap
MS_LIB_KW = ("MEDICO", "MÉDICO", "HANDICAP", "I.M.E", "EDUCATION MOTRICE",
             "ITEP", "SESSAD", "SAVS", "SAMSAH", "ESAT", "POLYHANDICAP",
             "POLYHANDICAPÉ", "MDPH", "PERSONNES HANDICAP")


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else DATA / "finess.json")
    if not src.exists():
        print(f"!! {src} introuvable", file=sys.stderr)
        sys.exit(1)
    libelles = json.loads((DATA / "categ_libelles.json").read_text()) if (DATA / "categ_libelles.json").exists() else {}

    cats = set(MS_CATS)
    for code, lib in libelles.items():
        if any(k in lib.upper() for k in MS_LIB_KW):
            cats.add(code)

    d = json.loads(src.read_text())
    out = []
    for pmej in d.get("pmej", []):
        ig = pmej.get("informationsGeneralesPMEJ") or {}
        if ig.get("dateFermeture"):
            continue
        for ege in pmej.get("ege") or []:
            eig = ege.get("informationsGeneralesEGE") or {}
            if eig.get("dateFermeture"):
                continue
            cat = str(ege.get("categorieentiteGeographiqueExercice") or "")
            if cat not in cats:
                continue
            adrs = ege.get("adresse") or []
            a = next((x for x in adrs if x.get("codePostal")), {})
            tel = ""
            for c in (ege.get("contact") or []) + (pmej.get("contact") or []):
                t = ((c or {}).get("telecom") or {}).get("telephone")
                if t:
                    tel = t
                    break
            nom = (eig.get("nomEgeLong") or eig.get("nomEgeCourt") or ig.get("denominationLonguePmSmsse") or "").strip()
            if not nom:
                continue
            out.append({
                "finess": eig.get("numFinessEge") or ig.get("numFinessPm") or "",
                "nom": nom,
                "categ": cat,
                "type": libelles.get(cat, "ESMS"),
                "adresse": " ".join(x for x in (a.get("ligneQuatre"), a.get("codePostal"), a.get("ligneAcheminement")) if x),
                "commune": (a.get("ligneAcheminement") or "").strip(),
                "cp": a.get("codePostal") or "",
                "tel": tel,
            })
    seen = {}
    for e in out:
        seen.setdefault(e["finess"] or e["nom"], e)
    dest = DATA / "esms_index.json"
    dest.write_text(json.dumps(list(seen.values()), ensure_ascii=False))
    print(f"{len(seen)} ESMS indexés → {dest}")


if __name__ == "__main__":
    main()