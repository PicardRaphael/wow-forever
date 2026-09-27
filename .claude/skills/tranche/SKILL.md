---
name: tranche
description: Exécute une tranche de docs/ROADMAP.md en TDD (plan, tests rouges committés, implémentation jusqu'au vert, registre, vérification, résumé).
argument-hint: <Txx>
disable-model-invocation: true
---
# Tranche $ARGUMENTS

## 0. Plan
- Si `tasks/$ARGUMENTS-plan.md` n'existe pas : ne pas passer en mode plan. Lire la section $ARGUMENTS de `docs/ROADMAP.md`, poser au plus 5 questions décisives, écrire directement `tasks/$ARGUMENTS-plan.md` (fichiers, interfaces, tests attendus avec leurs valeurs, étapes, hors périmètre, risques ; aucun code), le committer sur `main` (« $ARGUMENTS: plan ») et s'arrêter pour validation.
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
- Le plan (`tasks/$ARGUMENTS-plan.md`) s'écrit et se committe sur `main`, avant de créer la branche de la tranche.
- Déroulé (`worktree.bgIsolation` à `none`, pas de worktree) : travailler dans le dépôt principal sur une branche `txx` (`git switch -c txx`). En fin de tranche : pousser la branche (`git push -u origin txx`), attendre la CI verte sous Ubuntu et Windows (`gh run watch`), puis fusionner soi-même en fast-forward (`git switch main`, `git merge --ff-only txx`), `git push`, et supprimer la branche locale et distante (`git branch -d txx`, `git push origin --delete txx`).
- `/tranche Txx` : tout texte ajouté après l'identifiant entre dans `$ARGUMENTS` (et donc dans les noms de fichiers du skill) ; le plan reste `tasks/Txx-plan.md`.
- Les commandes Bash composées (heredoc + `cd`, longues chaînes `&&` avec git) peuvent être refusées : écrire le script dans `$CLAUDE_JOB_DIR/tmp` et le lancer avec `uv run python <chemin>` ; ne jamais faire `cd` dans une commande (cela déplace le répertoire de la session).
- `tasks/.rouge` et `tasks/.tests-verrouilles` sont ignorés par git : le commit « tests » ne les porte pas et `git rm` échoue ; `rm` suffit en fin de phase verte.
- Valeurs attendues d'un portage : les calculer avec le code du seed (`repr()`), pas avec les arrondis du plan ; comparer avec `pytest.approx(rel=1e-12)` sauf là où le seed lui-même utilise `==`.
- Un test qui modifie une copie des données doit régénérer le manifeste de la copie (`write_manifest(data_copy)`) pour atteindre l'erreur de schéma plutôt que `data_integrity`.
- Un fichier ajouté dans `forever/data/<version>/` change des comptes à mettre à jour dès le commit « tests » : `test_data_import.py` (ensemble exact), `test_manifest.py` (nombre et sous-ensemble), `test_decode_version.py` (fichiers de la candidate) ; il faut aussi l'ajouter à `DECODED_FILES` ou `INHERITED_FILES` (`forever/pipeline/decode.py`) et le décrire dans `sources.json`.
- Une entrée ajoutée au registre change trois assertions de `test_registry.py` (`total`, `coverage`, sortie de `main`) : les mettre à jour dans le commit « tests ».
- Tranche longue : un cycle rouge → vert par bloc (commit « Txx: tests (bloc X) », puis « Txx: bloc X vert »), `tasks/.rouge` et `tasks/.tests-verrouilles` réécrits à chaque bloc et supprimés en fin de bloc vert ; si le contexte se remplit, s'arrêter après un bloc vert committé.
- Un module absent casse la collecte de tout le fichier de tests : poser un squelette (types et signatures, corps `NotImplementedError`) pour que chaque test échoue individuellement.
- Les heredocs Bash (`<<'EOF'`) longs échouent parfois dans cet outil : écrire le script avec Write dans `$CLAUDE_JOB_DIR/tmp` et le lancer. Ne jamais enchaîner `lint ; git commit` : un `;` committe malgré un lint rouge (utiliser `&&`).
