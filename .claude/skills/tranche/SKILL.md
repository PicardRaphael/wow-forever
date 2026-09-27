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
- Le mode auto refuse d'écrire dans `.github/workflows/` et `.claude/settings.json` : préparer un patch (`git diff` du changement voulu, enregistré hors du dépôt) et donner à l'utilisateur la commande pour l'appliquer (`git apply <fichier>.patch`).
- Le plan (`tasks/$ARGUMENTS-plan.md`) s'écrit et se committe sur `main`, avant de créer la branche ou le worktree de la tranche.
- Fin de tranche dans un worktree : depuis le dépôt principal, fusion fast-forward dans `main` (`git merge --ff-only <branche>`), `git push`, puis suppression du worktree (`git worktree remove <chemin>`) et des branches locale et distante (`git branch -d <branche>`, `git push origin --delete <branche>`).
- Une session isolée dans un worktree ne peut pas faire cette fusion (commandes visant le dépôt principal refusées) : pousser la branche, vérifier la CI (`gh run watch`), puis donner à l'utilisateur les commandes de fusion et de suppression.
- `/tranche Txx` : tout texte ajouté après l'identifiant entre dans `$ARGUMENTS` (et donc dans les noms de fichiers du skill) ; le plan reste `tasks/Txx-plan.md`.
- En worktree, les commandes Bash composées (heredoc + `cd`, longues chaînes `&&` avec git) peuvent être refusées : écrire le script dans `$CLAUDE_JOB_DIR/tmp` et le lancer avec `uv run python <chemin>` ; ne jamais faire `cd` dans une commande (cela déplace le répertoire de la session).
- `tasks/.rouge` et `tasks/.tests-verrouilles` sont ignorés par git : le commit « tests » ne les porte pas et `git rm` échoue ; `rm` suffit en fin de phase verte.
- Valeurs attendues d'un portage : les calculer avec le code du seed (`repr()`), pas avec les arrondis du plan ; comparer avec `pytest.approx(rel=1e-12)` sauf là où le seed lui-même utilise `==`.
- Un test qui modifie une copie des données doit régénérer le manifeste de la copie (`write_manifest(data_copy)`) pour atteindre l'erreur de schéma plutôt que `data_integrity`.
