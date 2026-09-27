---
name: tranche
description: Exécute une tranche de docs/ROADMAP.md en TDD (plan, tests rouges committés, implémentation jusqu'au vert, registre, vérification, résumé).
argument-hint: <Txx>
disable-model-invocation: true
---
# Tranche $ARGUMENTS

## 0. Plan
- Si `tasks/$ARGUMENTS-plan.md` n'existe pas : passer en mode plan, lire la section $ARGUMENTS de `docs/ROADMAP.md`, poser au plus 5 questions décisives, écrire le plan (fichiers, interfaces, tests attendus avec leurs valeurs, étapes, hors périmètre, risques) et s'arrêter pour validation.
- Sinon : lire le plan et l'exécuter.

## 1. Tests rouges
1. Écrire les tests des critères de fin. Les lancer : ils doivent échouer pour la bonne raison (fonction absente, valeur fausse), pas pour une erreur de syntaxe.
2. Écrire les identifiants des tests attendus rouges dans `tasks/.rouge` (un par ligne, forme `tests/unit/x.py::test_y`) et les fichiers de tests concernés dans `tasks/.tests-verrouilles`.
3. Commit « $ARGUMENTS: tests ».

## 2. Vert
1. Implémenter jusqu'à ce que tous les tests passent. Les fichiers listés dans `tasks/.tests-verrouilles` ne se modifient plus (un hook bloque). Si un test semble faux : s'arrêter et expliquer.
2. Supprimer `tasks/.rouge` et `tasks/.tests-verrouilles`.
3. Mettre à jour `docs/MECHANICS_REGISTRY.yaml` pour chaque mécanique touchée.

## 3. Fin
1. Lancer le skill `/verifier`.
2. Commit « $ARGUMENTS: <résumé> ».
3. Résumé final : Bloqué sur moi, Fait, Tests ajoutés, Registre modifié, Questions ouvertes (ajoutées à `docs/OPEN_QUESTIONS.md`).

## Pièges
<!-- Ajouter ici chaque erreur récurrente observée pendant les tranches. -->
- Ne pas démarrer la tranche suivante dans la même session : ouvrir une nouvelle session.
