# Feuille de route — tranches verticales

Chaque tranche traverse toutes les couches (données → moteur → outil → test) et se termine par un résultat utilisable.
Une tranche = 1 à 3 sessions Claude Code. Ne commence la suivante que lorsque `uv run tasks.py verify` est vert.

| Tranche | But | Dépend de |
| --- | --- | --- |
| T01 | Squelette de bout en bout : `forever status` + consultation d'un sort, CLI + MCP + provenance + CI | — |
| T02 | Port du cœur de mécaniques du skill Mage + registre + tests de référence | T01 |
| T03 | Pipeline de données : builds, fetch, decode, diff, verify, report (tests hors ligne) | T01 |
| T04 | Simulateurs de leveling (MC + analytique) exposés en MCP + graphique | T02 |
| T05 | Optimiseur de talents et conseiller de respec | T04 |
| T06 | Plugin Claude Code : skills, hooks, statusline, commandes, sous-agents | T04 |
| T07 | Mémoire joueur : fiches du vault, import de l'addon | T06 |
| T08 | Veille : workflow planifié, PR de données, note d'impact par personnage | T03, T07 |
| T09 | Raid : moteur analytique porté, Monte Carlo, parité avec wowsims Forever | T02 |
| T10 | Équipement : base d'objets par formules du client, optimiseur | T09 |
| T11 | Consommables et préparation de raid | T10 |
| T12 | Paladin, puis Démoniste, puis les autres classes | T09 |
| T13 | (Option) Serveur MCP distant pour Claude.ai et ChatGPT | T06 |

## T01 — Squelette de bout en bout
- **Fait** : paquet `forever` installable avec `uv` ; `forever/data/1.60.1.70009/` initialisé depuis `seed/forever-mage/data/` ; `manifest.json` avec empreintes ; `forever status` (réseau simulé en test) ; `forever lookup spell frostbolt --rank 2` ; serveur MCP avec `forever_status` et `forever_lookup` ; bloc provenance ; `forever manifest --update` (recalcul des empreintes) ; la CI fournie (`.github/workflows/ci.yml`) passe.
- **Hors périmètre** : mécaniques, simulateurs.
- **Critères de fin** :
    - `uv run forever lookup spell frostbolt --rank 2` renvoie 34-38 dégâts, 1,8 s, 35 mana, version 1.60.1.70009, certitude `certain`.
    - `forever status` renvoie `fresh`, `stale`, `unknown` et `silent` selon les réponses simulées (4 tests).
    - Une empreinte modifiée dans `data/` est détectée (1 test).
    - Le serveur MCP liste ses deux outils et répond (test d'intégration).
    - Test de contrat : chaque sortie CLI et MCP contient un bloc `provenance` complet (schéma validé).

## T02 — Cœur de mécaniques et registre
- **Fait** : porter `seed/forever-mage/scripts/fm.py` dans `forever/engine/` (modules : talents, character, spells, hit, crit, damage, casting, mana, cast), en fonctions pures qui reçoivent `GameData` ; constantes absentes des tables dans `forever/data/<version>/mechanics.json` ; créer `forever/registry.py` qui lit et valide `docs/MECHANICS_REGISTRY.yaml` ; `uv run tasks.py verify` échoue si une entrée `modelise` ou mieux n'a pas de test ; porter les 5 tests du seed qui visent `fm.py` (`donnees_completes`, `valeurs_client_70009`, `prerequis`, `legalite`, `couverture_mecaniques` et ses 30 contrôles) plus un test de parité avec `fm.py` ; passer `STRICT_REGISTRY = True` dans `tasks.py` ; `forever explain-mechanic` et l'outil MCP `forever_explain_mechanic`.
- **Reporté** : les 5 autres tests du seed dépendent des simulateurs (T04 : `analytique_proche_du_monte_carlo`, `calibrage_cible_blizzard`, `monte_carlo_reproductible`) ou de l'optimiseur, du PvP et de la respec (T05 : `optimiseur_legal`, `pvp_et_respec`).
- **Critères de fin** :
    - Les 30 contrôles de mécaniques de `seed/forever-mage/tests/run_all.py` passent à l'identique.
    - Chaque entrée du registre marquée `teste` pointe vers au moins un test qui existe.
    - `forever explain-mechanic A5` affiche la formule, la certitude et les sources.

## T03 — Pipeline de données
- **Fait** : `forever builds` (API wago.tools, produit `wow_classic_beta`, tri par date) ; `forever fetch --version X --tables …` (cache, empreintes) ; `forever decode` (talents depuis les tables Trait*, sorts depuis Spell*, noms français et anglais) ; `forever diff A B` ; `forever verify` ; `forever report` (Markdown).
- **Critères de fin** :
    - Tests hors ligne sur des extraits CSV dans `tests/fixtures/`.
    - `decode` reproduit les 54 talents Mage de `seed/forever-mage/data/…/talents.json` (rangs identiques) à partir des fixtures.
    - `diff` signale un rang de talent modifié et un sort ajouté (tests).

## T04 — Leveling
- **Fait** : porter `sim_leveling.py` (Monte Carlo à impacts différés, jeu expert) et le modèle analytique ; outil MCP `forever_sim_leveling` ; `forever chart leveling` ; porter les tests du seed `analytique_proche_du_monte_carlo`, `calibrage_cible_blizzard` et `monte_carlo_reproductible` ; remonter dans le registre les entrées rétrogradées en T02 (B6, B7, B13, C1, C5, H2, I1, I6, J2) et compléter A18 (cumul d'Ignite), B11 (escalade d'Arcane Blast), C2 (talents de portée).
- **Critères de fin** :
    - Au niveau 12 avec 3 Improved Frostbolt, le Monte Carlo (graine fixe) reproduit le seed à ±1 %.
    - L'analytique reste à moins de 15 % du Monte Carlo aux niveaux 12, 16 et 24.
    - Le graphique est un fichier PNG déterministe (empreinte stable à graine fixe).

## T05 — Talents et respec
- **Fait** : porter les tests du seed `optimiseur_legal` et `pvp_et_respec` ; remonter I5 dans le registre.
- **Critères de fin** : `forever optimize talents --from 10 --to 30` produit un ordre légal à chaque niveau ; le barème de respec est paramétrable ; tests de légalité et de non-régression.

## T06 — Plugin Claude Code
- **Critères de fin** : installation locale du plugin ; SessionStart injecte une seule ligne de fraîcheur ; la statusline affiche version et statut ; jeu d'évaluation d'aiguillage de 30 requêtes (60 % doivent déclencher un skill, 40 % non) avec au moins 90 % de bonnes décisions.

## T07 — Mémoire joueur
- **Critères de fin** : import d'un export d'addon d'exemple ; fiche écrite dans le vault avec la version du jeu ; une fiche plus ancienne que la version courante est signalée.

## T08 — Veille
- **Critères de fin** : `build-watch.yml` simulé en test (nouvelle version fictive → PR et note) ; alerte `silent` après 14 jours sans version.

## T09 à T13
Détaillées au moment de les planifier, avec la même structure (fait, hors périmètre, critères de fin testables).
