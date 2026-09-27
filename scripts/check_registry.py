"""Contrôle du registre des mécaniques (docs/MECHANICS_REGISTRY.yaml) : enveloppe de `forever.registry.main`.
Échec si : champ manquant, valeur inconnue, référence de test hors de tests/ ou introuvable (fichier ou fonction),
entrée 'teste' ou mieux sans `::nom`, formule chiffrée, identifiant cité par le moteur absent du registre,
entrée testée des catégories A à H sans implémentation citée. `--strict` : une entrée 'modelise' sans test échoue aussi."""

import sys

from forever.registry import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
