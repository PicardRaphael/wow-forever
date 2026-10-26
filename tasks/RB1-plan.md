# RB1 : retrait de la recherche de build du Mage (2026-10-26, en attente de validation)

Demande du 2026-10-26 : retirer totalement la recherche de build du Mage, « car de base on a eu modification sur
les builds recherche ». Périmètre choisi : la **recherche de build seulement**. Le moteur gelé du Mage reste pour le
temps par monstre et l'XP/h sous le 60 (décision 294). Le build du Mage vient désormais, comme pour les huit autres
classes, des builds populaires de Talents Forever vérifiés sur les données du client, et de wowsims au 60.
Effet attendu : la suite complète perd environ 175 tests, parmi les plus lents (recherches de build de 20 à 37 s,
fixture de 71 s de `test_totals.py`) ; gain à mesurer après le retrait (profil `--durations`).

## 1. Les deux questions (décision 288)
- **Qui maintient déjà ça mieux que nous ?** Les builds populaires de Talents Forever (lus par
  `forever/talents_forever.py`, toutes classes) et wowsims/forever au 60 (`forever/sims/`). Notre optimiseur recopiait
  la mécanique des talents du Mage et se périmait à chaque patch (décision 293).
- **Que se passe-t-il au prochain patch ?** Plus rien à rejouer pour les builds : la veille n'a plus de cas
  `mage_build` ; les builds populaires sont relus et vérifiés (légalité, paliers) sur les nouvelles données. Le moteur
  gelé du leveling reste tel quel, dit comme tel.

## 2. Retiré
| Code | Note |
| --- | --- |
| `forever/build.py` | build par contexte (`forever build`, `forever_build`) |
| `forever/optimize/leveling.py`, `endgame.py`, `respec.py`, `decide.py` | ordre des talents, fin de partie, respec, décision au Monte Carlo |
| `forever/engine/respec.py` | coût de respec, lu seulement par l'optimiseur |
| `forever/replay.py`, `scripts/replay_builds.py` | rejeu des cas de build pour la veille |
| `forever/sim/community.py`, `scripts/build_community_fixture.py` | écart entre un build de la communauté et le nôtre |
| `gamedata.ABLATABLE`, `gamedata.ablated` | seulement pour `replay_builds.py` |
| CLI `forever build`, `render_build`, `_cmd_build` ; MCP `forever_build` | outil retiré des listes (`bridge/agent.py`, `plugin/agents/forever-sim-runner.md`, `forever/hooks.py`) |
| `talents_forever.attach_export`, `BuildWithExport` | appelés seulement par `forever build` et `forever_build` |
| moteur `mage_build` | `engine_inputs.ENGINES`, `select_tests.ENGINE_MODULES` (garder `forever.optimize.route` hors du préfixe), `tasks.py verify --engines` |
| rejeu de la veille | `update.py` : `_ProductionReplay`, rejeu après installation, clause `advice` des mesures et sa raison ; ligne « Builds » de la carte (`bridge/cards.py`) |

## 3. Gardé
- `forever/compare.py` : comparaison et livraison des routes (RestedXP, Polestar), sans code de build ;
  `forever/optimize/route.py` (planificateur des routes, toutes classes).
- `forever/sim/` (rencontres, leveling Monte Carlo et analytique, objectifs), `forever/engine/` sauf `respec.py`,
  `forever/sims/`, `forever/talents_forever.py` (builds populaires, codes, export Naowh), `forever export naowh-build`.
- Données : `respec.json` et les clés `respec.*` de `mechanics.json` restent installées (aucune suppression de
  données) ; seul le code qui les lit est retiré. Le chargeur (`gamedata`, `engine/model.RespecRules`, `decode`)
  est laissé tel quel.

## 4. Repointé
- **`forever/gear.py` (`talent_plan`, Mage sous le 60)** : talents du personnage connecté, sinon build populaire le
  plus proche (`talents_forever.closest_popular`), dit dans la provenance ; au 60, wowsims inchangé.
- **Pont** (`bridge/plans.py`, `buttons.py`, `exports.py`, `context.py`, `prompt.py`, `loop.py`) : le Mage suit le
  chemin des autres classes (boutons Talents et Leveling sur les builds populaires) ; plus de lien « build calculé ».
- **Plugin** : skills `forever-builds`, `forever-leveling`, `forever-mage`, `forever-pvp`, routeur et
  `format-reponse.md` ; agent `forever-sim-runner` ; 14 évaluations construites sur le build calculé retirées, 5
  réécrites (`bouton-talents`, `generale-mage-raid`, `personnelle-mage-donjon`, `planification-personnage-prevu`,
  `pont-question-de-suite-faute`) ; version 0.21.0.

## 5. Tests
1. **Rouges d'abord** (committés avant le retrait) :
   - `forever build` absent de la CLI et `forever_build` absent du serveur MCP ;
   - boutons Talents et Leveling du pont : le Mage reçoit les builds populaires comme les autres classes ;
   - `gear` du Mage sous le 60 : talents connectés, sinon build populaire le plus proche, dit dans la provenance ;
   - veille : plus de moteur `mage_build`, mesures sans clause `advice`, carte sans ligne « Builds ».
2. **Retirés** (environ 175) : parité du seed (optimize, pvp, respec), `test_build_*`, `test_departage`,
   `test_next_step`, `test_optimize_*`, `test_opens_tier`, `test_leveling_parallel`, `test_leveling_from_current`,
   `test_respec`, `test_replay_builds_*`, `test_replay_cache` ; et les tests qui en dépendent dans `test_totals`,
   `test_mc_stats`, `test_planning`, `test_pvp_profile`, `test_review_t06b`, `test_replay_scope`, `test_sonde_h`,
   `test_seed_data`, `test_community_builds`, `test_talents_forever_*`, `test_export_naowh_build`, `test_profile`,
   `test_sources`, `test_installed_invariants`, `test_engine_frozen`, `test_engine_inputs`,
   `test_engine_70450_frost_blast`.
3. **Ajustés** : « mage_build » dans les tests de la veille (`test_update_*`), listes d'outils (`test_mcp*`,
   `test_bridge_*`, `test_plugin_*`), `test_gear_talents`.
4. `uv run tasks.py e2e` une fois (la veille vérifie le clone avec `verify --data --engines=`).

## 6. Registre
- **I5** (optimiseur de talents et de respec) : retiré du calcul, statut `absent`, note « retiré, décision 299 ».
- **J2, G3, H5, I1** : on retire seulement les tests supprimés de leur liste ; leur statut reste.

## 7. Documents
Décision 299 dans `DECISIONS.md` ; `SPEC.md` (P0 : build du Mage par Talents Forever, plus d'ordre de talents ni
de conseil de respec calculés) ; `ARCHITECTURE.md`, `ROADMAP.md`, `USAGE.md`, `VISION.md` ;
`tasks/plan-simulateurs.md` (lignes de l'optimiseur : retiré).

## 8. Essai en jeu (décision 273)
1. Fermer le jeu, laisser le pont installer l'addon de `main` fusionné, relancer.
2. Sur le Mage : bouton **Talents** → un build populaire de Talents Forever, avec son lien ; aucune mention de
   « build calculé ».
3. Bouton **Leveling** → zones et XP/h comme avant (moteur gelé), talents tirés du build populaire.
4. `forever gear` sur le Mage sous le 60 → poids avec les talents connectés.
5. `forever update status` → carte sans ligne « Builds ».

## 9. Ordre d'exécution (nouvelle session, branche `rb1`)
Tests rouges → retrait du code et des tests → repointage de `gear` et du pont → plugin → registre et documents →
`quick`, `e2e` → push de la branche, CI → essai en jeu → fusion.
