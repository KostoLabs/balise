"""Construit l'index des organismes gestionnaires (PMEJ) depuis FINESS Structures.

Un organisme (PMEJ, n° FINESS 9 chiffres) peut exploiter plusieurs
établissements (EGE, n° FINESS 9 chiffres). Cet index relie les deux :
organisme -> liste de ses établissements ESMS (EGE actifs du médico-social).

Usage :
    cd backend && .venv/bin/python scripts/build_esms_index.py [finess.json]
Écrit : data/esms_index.json (EGE) et data/organismes_index.json (PMEJ→EGE)
"""

import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

MS_CATS = {
    "156", "175", "182", "183", "188", "189", "190", "192", "193", "196",
    "198", "202", "203", "204", "205", "206", "207", "208", "252", "253",
    "297", "298", "299", "300", "301", "302", "340", "354", "360", "361",
    "362", "363", "364", "365", "366", "367", "368", "370", "377", "378",
    "379", "380", "382", "390", "395", "396", "397", "437", "445", "446",
    "448", "449", "608", "609",
}
MS_LIB_KW = ("MEDICO", "MÉDICO", "HANDICAP", "I.M.E", "EDUCATION MOTRICE",
             "ITEP", "SESSAD", "SAVS", "SAMSAH", "ESAT", "POLYHANDICAP",
             "POLYHANDICAPÉ", "MDPH", "PERSONNES HANDICAP")


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else DATA / "finess.json")
    if not src.exists():
        print(f"!! {src} introuvable", file=sys.stderr)
        sys.exit(1)
    libelles = json.loads((DATA / "categ_libelles.json").read_text()) if (DATA / "categ_libelles.json").exists() else {}
    cats = set(MS_CATS) | {c for c, l in libelles.items() if any(k in l.upper() for k in MS_LIB_KW)}

    d = json.loads(src.read_text())
    eges = []
    organismes = {}
    for pmej in d.get("pmej", []):
        ig = pmej.get("informationsGeneralesPMEJ") or {}
        if ig.get("dateFermeture"):
            continue
        pmej_nom = (ig.get("denominationLonguePmSmsse") or ig.get("denominationPm") or "").strip()
        pmej_finess = ig.get("numFinessPm") or ""
        pmej_tel = ""
        for c in pmej.get("contact") or []:
            t = ((c or {}).get("telecom") or {}).get("telephone")
            if t:
                pmej_tel = t
                break
        pmej_adrs = {}
        for a in pmej.get("adresse") or []:
            if a.get("codePostal"):
                pmej_adrs = a
                break
        children = []
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
            for c in (ege.get("contact") or pmej.get("contact") or []):
                t = ((c or {}).get("telecom") or {}).get("telephone")
                if t:
                    tel = t
                    break
            nom = (eig.get("nomEgeLong") or eig.get("nomEgeCourt") or pmej_nom or "").strip()
            if not nom:
                continue
            entry = {
                "finess": eig.get("numFinessEge") or "",
                "nom": nom,
                "categ": cat,
                "type": libelles.get(cat, "ESMS"),
                "adresse": " ".join(x for x in (a.get("ligneQuatre"), a.get("codePostal"), a.get("ligneAcheminement")) if x),
                "commune": (a.get("ligneAcheminement") or "").strip(),
                "cp": a.get("codePostal") or "",
                "tel": tel,
                "organisme_finess": pmej_finess,
            }
            eges.append(entry)
            children.append(entry["finess"])
        if children:
            organismes[pmej_finess] = {
                "finess": pmej_finess,
                "nom": pmej_nom,
                "siren": ig.get("siren") or "",
                "tel": pmej_tel,
                "adresse": " ".join(x for x in (pmej_adrs.get("ligneQuatre"), pmej_adrs.get("codePostal"), pmej_adrs.get("ligneAcheminement")) if x),
                "etablissements": children,
            }

    seen = {}
    for e in eges:
        seen.setdefault(e["finess"] or e["nom"], e)
    (DATA / "esms_index.json").write_text(json.dumps(list(seen.values()), ensure_ascii=False))
    (DATA / "organismes_index.json").write_text(json.dumps(organismes, ensure_ascii=False))
    print(f"{len(seen)} ESMS indexés, {len(organismes)} organismes gestionnaires")


if __name__ == "__main__":
    main()