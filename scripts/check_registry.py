"""Contrôle du registre des mécaniques (docs/MECHANICS_REGISTRY.yaml).
Échec si : champ manquant, valeur inconnue, entrée 'teste' ou 'valide-*' sans test existant.
En mode --strict (à activer dès T02) : une entrée 'modelise' sans test échoue aussi."""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATUTS = ["absent", "modelise", "teste", "valide-journal", "valide-jeu"]
CERTITUDES = {"certain", "probable", "suppose"}
FOREVER = {"oui", "modifie", "inconnu"}
CHAMPS = ["id", "categorie", "description", "forever", "statut", "certitude", "sources", "tests"]


def main(strict: bool) -> int:
    reg = yaml.safe_load((ROOT / "docs/MECHANICS_REGISTRY.yaml").read_text(encoding="utf-8"))
    errors, warnings, ids = [], [], set()
    for m in reg.get("mechanics", []):
        mid = m.get("id", "?")
        for champ in CHAMPS:
            if champ not in m:
                errors.append(f"{mid} : champ '{champ}' manquant")
        if mid in ids:
            errors.append(f"{mid} : identifiant en double")
        ids.add(mid)
        if m.get("statut") not in STATUTS:
            errors.append(f"{mid} : statut inconnu '{m.get('statut')}'")
        if m.get("certitude") not in CERTITUDES:
            errors.append(f"{mid} : certitude inconnue '{m.get('certitude')}'")
        if m.get("forever") not in FOREVER:
            errors.append(f"{mid} : valeur 'forever' inconnue '{m.get('forever')}'")
        tests = m.get("tests") or []
        for t in tests:
            if not (ROOT / t.split("::")[0]).exists():
                errors.append(f"{mid} : test introuvable '{t}'")
        rang = STATUTS.index(m["statut"]) if m.get("statut") in STATUTS else 0
        if rang >= 2 and not tests:
            errors.append(f"{mid} : statut '{m['statut']}' sans test")
        elif rang == 1 and not tests:
            (errors if strict else warnings).append(f"{mid} : 'modelise' sans test")
        if rang >= 3 and not m.get("sources"):
            errors.append(f"{mid} : statut '{m['statut']}' sans source")
    total = len(ids)
    counts = {s: sum(1 for m in reg["mechanics"] if m.get("statut") == s) for s in STATUTS}
    print(f"Registre : {total} mécaniques | " + " | ".join(f"{s} {n}" for s, n in counts.items()))
    for w in warnings:
        print(f"  avertissement : {w}")
    for e in errors:
        print(f"  ERREUR : {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main("--strict" in sys.argv))
