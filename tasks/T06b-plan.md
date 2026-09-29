# T06b — Données du client installées, totaux, profil joueur, recommandations départagées : plan

> Plan rédigé le 2026-09-29 d'après la demande de l'utilisateur du même jour (neuf points) et la section T06b de
> `docs/ROADMAP.md`. **Décisions D1 à D10 à valider**, option recommandée en premier ; les cinq questions décisives
> sont en tête. Exécution : `/tranche T06b` dans une nouvelle session, branche `t06b`, un cycle rouge → vert par bloc.

## Questions décisives (réponse attendue avant l'exécution)
1. **D1, méthode d'installation** : réviser le dossier `1.60.1.70009` en place (révision 2, recommandé) ou créer une
   nouvelle version de données ? Tableau des coûts en D1.
2. **D2, données figées du mode seed** : copies `_seed_talents.json` et `_seed_spells.json` dans le dossier de version
   (recommandé), ou lecture de `seed/forever-mage/data/` à l'exécution ?
3. **D5, profil** : fichier `%USERPROFILE%\.forever\profile.json` (variable `FOREVER_PROFILE` pour le déplacer), lu
   **explicitement** par l'agent (outil `forever_player_profile`), les outils de calcul ne le lisant jamais d'eux-mêmes
   (recommandé) ; ou lecture implicite par `forever_build` et `forever_sim_leveling` ?
4. **D7, point de passage vers un palier** : un point dans un talent non modélisé reste-t-il permis quand il est le
   seul moyen d'ouvrir le palier d'un talent modélisé que l'anticipation choisit (recommandé : oui, signalé « point de
   passage, effet non modélisé ») ?
5. **D3, accord avant l'écriture des données** : la validation de ce plan vaut-elle accord pour les changements listés
   en D3 (recommandé : oui ; tout changement du rapport `--dry-run` absent de cette liste arrête l'exécution et vous
   est présenté) ?

## Contexte
Demande (2026-09-29), après l'évaluation du plugin (`docs/research/plugin-eval-T06.md`) et un usage réel
(« quel talent au niveau 22 ») :
1. données décodées du client installées pour 1.60.1.70009 : talents redécodés (valeurs et variables d'infobulle,
   certitude du client), sorts décodés dont les coûts en mana là où `spells.json` avait `null` (fin de l'estimation
   B11), changements confirmés appliqués, Hot Streak à 20 s ;
2. décision « réviser 70009 » ou « nouvelle version », avec trace complète : diff avant/après, source de chaque valeur,
   révision visible dans la provenance ;
3. mode seed toujours identique au seed, parité verte ;
4. rejeu des builds de T05 (cinq contextes × niveaux 20, 40, 60), `docs/research/builds-T05.md` à jour, chaque
   recommandation changée signalée avec sa raison ;
5. totaux dans les sorties des outils (points par arbre et au total, tout total que le modèle calculait) ;
6. profil joueur minimal hors du dépôt, plusieurs personnages, un actif : `forever profile` + lecture MCP ;
7. règle des skills : donnée personnelle manquante demandée avant le calcul, valeur la plus probable proposée, jamais
   de défaut silencieux ; profil rappelé en une ligne ;
8. recommandations : à égalité, talents modélisés d'abord, jamais un non modélisé à la place d'un modélisé, « choix non
   départagé par le calcul » si l'écart n'est pas significatif ; comparer à mesure égale (Monte Carlo contre Monte
   Carlo, intervalle) ; cas ajouté à l'évaluation ;
9. version semver dans `plugin.json`.

## Constats (relevés le 2026-09-29, explorations du dépôt)
- **Aucune commande d'installation** : `forever decode` écrit une candidate dans `<cache>/candidates/<version>/`
  (refuse `forever/data`) ; aucune candidate sur disque, tables du client en cache (`~/.cache/forever/wago/1.60.1.70009/`,
  enUS et frFR). Décodage en mémoire (cache réel = fixtures) : 6 écarts de talents, 12 de sorts (9 confirmés + 3 coûts).
- **`confirmed_changes.json` n'est lu par aucun code** (15 écarts, `tasks/T03-ecarts.md`) ; `overrides.json` non plus
  (ses 5 valeurs sont déjà dans `talents.json`).
- **talents.json** : 54 talents, 49 `FC-69893`, 5 `FC-70009` ; pas de champ `source` ni `tooltip_values` ;
  `lookup talent` rend `certain` seulement pour `FC-<build courant>`. Hot Streak : `ranks [[15,25,3]]` et
  `duration_s: 20` (lu par `gamedata.py:223`, note « durée corrigée » de `lookup.py:235-237`) ; client : `[[20,25,3]]`.
- **Forme de la candidate** : `desc` au gabarit brut du client (`$s1`, `$400625d`) alors que le dépôt et
  `lookup._describe` utilisent `{i}` ; un seul `spellIds` (42 talents du dépôt en ont plusieurs) ; en plus `name_fr`,
  `tooltip_values` ; en moins `wowsims_not_simulated`, `duration_s`. Candidate : 12 fichiers (sans
  `_source_gunba_mage_tree.json` ni `confirmed_changes.json`), dépôt : 14.
- **Coûts en mana** (`SpellPower.ManaCost` du client) : pyroblast r1 (11366) 125, ice_lance r1 (1312002) 45,
  blast_wave r1 (11113) 215 ; estimation actuelle `mana.talent_rank_cost` (0,75 / 50, `suppose`, B11) : 112,5 / 41,25 /
  202,5. Arcane Blast r1-r5 : coût fixe 0, `PowerCostPct` 15, déjà `mana_pct_base` (reste `null`).
- **Le mode seed ne change que des branches de code** : il lit `forever/data/1.60.1.70009/` ; la parité (45 tests de
  `tests/parity/` + 3 de `test_engine_leveling.py`) ne passe que parce que `talents.json` et `spells.json` sont
  identiques octet pour octet au seed (`test_data_import.py::test_seed_files_are_byte_identical`). `rules` n'atteint
  pas le chargement (`store.load_version` sans sélecteur). Installer les valeurs du client casse la parité
  (`test_fm_parity` : égalité stricte des rangs, Blast Wave r1 niveau 36 → 30 ; `test_seed_pvp_parity` : `impact`,
  `iceLance` ; `test_sim_leveling_parity` : L24 avec `iceLance`).
- **Règles** : `.claude/rules/data.md` (« ne jamais modifier les fichiers d'une version passée : une correction crée
  une nouvelle version de données »), décisions 17 (copie du seed), 37 (« `talents.json` et `spells.json` de 70009
  inchangés »), 58 (« `spells.json` reste une copie du seed »). Précédent : `measures refresh` (T04c, décision 68)
  réécrit déjà `monsters.json` de la version courante, après accord. `VERSION_DIR_RE = ^\d+\.\d+\.\d+\.\d+$` ;
  `status` et `freshness` comparent le nom du dossier à la dernière build de wago ; le regex de provenance du plugin
  attend `\d+\.\d+\.\d+\.\d{4,}`. `tests/golden/` n'existe pas ; le hook bloque `manifest.json` (Edit/Write seulement).
- **Sorties** : `forever_build` a `talents_by_tree` sans total ; `engine/talents.py::tree_split` existe, testé, non
  appelé par `build.py` ; `test_build_report.py` fige l'ordre des clés (`FIELDS`). `forever_explain_mechanic` ne rend ni
  le coût d'Arcane Blast par cumul (`engine/mana.py::arcane_blast_cost` existe) ni Winter's Chill au maximum
  (`crit.winters_chill_per_stack` seul) ; « Arcane Blast » n'est pas trouvé par son nom (suggère B11 et I8).
  `forever_sim_leveling` ne rend que des moyennes Monte Carlo (`mc_stats` existe, non exposé).
- **Optimiseur** : à égalité, le premier de `talents.json` gagne sans signal ; aucune significativité par niveau
  (`order[]`) ; au dernier niveau, pas d'anticipation ; **le build actuel n'est pas le point de départ** (`current` ne
  sert qu'au respec) : « quel talent au niveau 22 » lit la fin d'un chemin libre depuis le niveau 10. Pas de drapeau
  « modélisé » : seuls les `angle_mort.talents` des entrées `absent` (B18, B19, C9, F6, I8) ; `arcaneSubtlety` n'est ni
  lu par le code ni dans un angle mort (présent dans les builds donjon 60 et raid 60 de T05).
- **Race par défaut** `Orc` de `forever_build` et `forever_sim_leveling` : absente des `assumptions` (défaut
  silencieux).
- **Plugin** : `plugin.json` sans `version`, voulu (annexe du plan T06 : avec `version`, `claude plugin update` ne
  recopie rien tant que la version ne change pas) ; `test_plugin_manifest` impose `"version" not in p` ;
  `docs/USAGE.md:27` le dit ; `install_plugin.ps1:112` valide sans `--strict` (le plan T06 le prévoyait).
- **Profil** : aucun vault ; `ARCHITECTURE.md:105` réserve `forever_player_profile` ; `ARCHITECTURE.md:146-148` place
  le vault `joueur/` dans git (contredit « hors du dépôt ») ; pas de `platformdirs` (dépendance = accord).
- **Évaluation** : 50 cas (30 + 20) figés par `test_plugin_evals.py` (`== 50`, `POSITIVE_COUNTS` talent 5,
  `test_report_loads_the_real_suite`), `LABELS` « (50 cas) » de `scripts/plugin_eval_report.py`, décision 96,
  `ARCHITECTURE.md:124`. Dernière décision : 97. Registre : 108 entrées, 37/108.

## Décisions (à valider)
1. **D1 — Méthode d'installation : révision 2 du dossier `1.60.1.70009` en place** (A, recommandé).

   | Critère | A : révision en place | B : nouvelle version de données |
   |---|---|---|
   | Règle `data.md`, décisions 17, 37, 58 | à amender : une version *passée* reste immuable, la version *courante* se révise par révision numérotée et journalisée ; décision 98 remplace 17, 37, 58 | respectées telles quelles |
   | Nom et schéma | inchangés (`game_version` = build du jeu) | séparer build du jeu et version des données : `VERSION_DIR_RE`, `status`/`freshness` (comparaison à wago), manifeste, regex de provenance du plugin, tests de comptage de versions |
   | Données figées du mode seed | deux copies à créer (D2) | l'ancien dossier, gratuit ; mais tout ajout futur de clé à `mechanics.json` (exigée par `build_game_data`) devra être reporté dans l'ancien dossier, ou le chargeur tolérer son absence |
   | Diff avant/après | `forever report` entre la candidate et l'installé, avant l'écriture ; git ; `revisions.json` | `forever report r1 r2` rejouable à tout moment |
   | Précédent | `measures refresh` réécrit déjà la version courante après accord (décision 68) | aucun |

   Raison : le besoin figé du seed se limite à deux fichiers, alors qu'un ancien dossier complet devrait suivre le
   schéma de tous les autres ; B touche la fraîcheur et le plugin pour une seule build de jeu. Prix de A : amender la
   règle et trois décisions, et poser D2. **Trace (A)** : champ `revision` (entier, 1 = état actuel, 2 = T06b) et
   `revised_at` dans `sources.json` → entrée du manifeste → provenance `data_revision` (nouvelle clé de
   `make_provenance`, affichée par `forever status` et le pied de réponse du plugin : « Version 1.60.1.70009 r2 ») ;
   `forever/data/1.60.1.70009/revisions.json` (numéro, date, motif, commande, rapport, liste des valeurs changées
   `{fichier, chemin, avant, après, source, certitude}`) ; rapport lisible `docs/research/data-1.60.1.70009-r2.md`
   (sortie de `forever report`). Si B est choisi : dossier `1.60.1.70009.r2` refusé par le regex actuel, nom à fixer
   à l'exécution (champ `data_version` du manifeste + `game_version` inchangé) et blocs A et B réécrits.
2. **D2 — Données figées du mode seed** : `_seed_talents.json` et `_seed_spells.json` dans le dossier de version
   (fichiers plats, donc couverts par `version_files` et le manifeste), identiques octet pour octet à
   `seed/forever-mage/data/1.60.1.70009/` (test). `build_game_data(version, rules="forever"|"seed")` : en seed,
   `spells`, `talents` (et leurs dérivés, dont `talent_at`) viennent des copies, le reste est partagé ;
   `mana.talent_rank_cost` reste dans `mechanics.json` pour le seed (qui lit `mana: null` et code 0,75 / 50 en dur),
   noté « mode seed seulement ». `rules` atteint le chargement : `build.py`, `leveling.py`, `cli.py` (`build`, `sim`),
   `mcp_server.py` (`forever_build`, `forever_sim_leveling`) ; fixture de session `seed_game_data` dans
   `tests/conftest.py` ; `tests/parity/*` et les trois tests seed de `test_engine_leveling.py` basculent dessus.
   Alternative écartée : lire `seed/` à l'exécution (produit couplé au code de référence, hors manifeste).
3. **D3 — Installation : `forever install <candidate> [--dry-run | --yes]`** (reprise de T08). `--dry-run` écrit le
   rapport sans toucher `forever/data` ; `--yes` fusionne, écrit `revisions.json`, puis `manifest --update` (écriture
   par la CLI, hors du hook). Refus si la candidate n'est pas de la version courante ou si une valeur change hors des
   règles ci-dessous. Règles de fusion :
   - **talents.json** : `ranks` et `tooltip_values` du client ; `certainty` `FC-70009` pour les 54 ; nouveau champ
     `source` par talent (tables et identifiants du client, build, date de lecture) ; `name_fr` ajouté ; `desc` garde
     le gabarit `{i}` du dépôt (le gabarit brut `$sN` va dans `source.client_desc`) ; `spellIds` du dépôt gardés, ceux
     du client dans `source.client_spell_ids` (rien ne lit `spellIds`, décision 40) ; `wowsims_not_simulated` gardé ;
     Hot Streak : `ranks [[20,25,3]]`, `duration_s` retiré (repli de `buffs.py:164` sur le rang ; `gamedata.py:223` et
     la note de `lookup.py:235-237` retirés).
   - **spells.json** : `min`, `max`, `level` du client (convention de la décision 39) et `mana` 125 / 45 / 215 ;
     `source` par rang (identifiant du sort, `SpellPower.ManaCost`) ; Arcane Blast : `mana` `null` gardé,
     `mana_pct_base` sourcé (`PowerCostPct`). En mode forever, les dégâts viennent de `spell_scaling.json`
     (`spell_level="character"`) : les changements « convention » ne touchent que les chemins `spell_level="rank"`
     (PvP, D9 le vérifie).
   - **confirmed_changes.json** : gardé comme trace ; chaque entrée reçoit `applied_in_revision: 2` ; trois entrées
     ajoutées (coûts en mana, nature `client`) : 18 entrées. `_source_gunba_mage_tree.json` et `overrides.json`
     gardés (aucune suppression).
   - **sources.json** : `talents.json` et `spells.json` `certain`, source « client 1.60.1.70009, installé en
     révision 2 » ; `field_notes.mana` réécrit (seul Arcane Blast reste en pourcentage) ; `_seed_*.json` décrits.
   - Changements attendus, et seuls permis : les 15 de `confirmed_changes.json`, les 3 coûts, `certainty` des 49
     talents `FC-69893`, champs ajoutés ci-dessus, retrait de `duration_s`. Tout autre écart du `--dry-run` arrête
     l'exécution (question 5).
4. **D4 — Totaux, calculés dans `forever/engine/`** (`tree_split`, `points_available`, `arcane_blast_cost`, nouvelle
   `winters_chill_crit`) :
   - `forever_build` : `points` = `{by_tree, total, available, unspent}` pour le build et `alternative.points` ;
     `order[]` : `points_by_tree` et `points_total` cumulés à chaque étape ; chaque `gap` gagne `advantage`
     (écart orienté vers le meilleur, positif) à côté de `mean`, pour qu'aucun signe ne se retourne à la main ;
     `alternative.monte_carlo` et `sd`, `se`, `n` (la même mesure que le build).
   - `forever_explain_mechanic` : bloc `derived` : B11, coût d'Arcane Blast de 0 au maximum des cumuls en part du mana
     de base (et en mana à un niveau si `level` est donné, `base_mana`) ; B15, bonus aux autres sorts par cumul et au
     maximum ; D4, critique de Winter's Chill par cumul et au maximum, par rang du talent. Champ `alias` du registre
     (« Arcane Blast », « Winter's Chill », « Hot Streak ») lu par `_resolve`.
   - `forever_lookup(kind="talent")` : `derived` par rang quand un talent a des cumuls (Arcane Blast, Winter's Chill,
     Hot Streak), mêmes fonctions.
   - `forever_sim_leveling` : `monte_carlo_stats` = `{mean, sd, se, n, low, high, confidence}` sur `total`.
   - Consigne « aucun calcul » du plugin inchangée.
5. **D5 — Profil joueur minimal** (`forever/profile.py`) :
   - Fichier `FOREVER_PROFILE`, sinon `Path.home() / ".forever" / "profile.json"` (jamais le cache, jamais sous le
     dépôt : test) ; écriture atomique, `newline="\n"`. Schéma 1 :
     `{schema_version, active, characters: {<nom>: {class, race, faction, level, talents {clé: rang}, professions
     {métier: compétence}, game_version, updated_at}}}`.
   - Validation : niveau entier dans les bornes de `leveling.json` ; classe parmi Mage, Paladin, Démoniste (`Mage`,
     `Paladin`, `Warlock`) ; pour le Mage : race dans `racials.json`, talents par `check_build` au niveau ; autres
     classes : race et talents gardés tels quels, `validated: false` (T12) ; faction donnée par le joueur, jamais
     déduite (règle de jeu non tranchée, Skyborne) ; métiers : nom et compétence entière, sans contrôle (MT1).
   - CLI : `forever profile show [--json] [<nom>]`, `list`, `set <nom> [--class] [--race] [--faction] [--level]
     [--talents "clé=rang,…"] [--profession "Métier=N"]…` (création ou mise à jour partielle), `use <nom>`,
     `remove <nom>` (confirmation `Deps.confirm`, `--yes`).
   - MCP : `forever_player_profile(name=None)`, lecture seule : personnage actif (ou nommé), liste des noms, `stale`
     si `game_version` ≠ version des données, `missing` (champs vides), provenance. Pas d'écriture par MCP.
   - **Lecture explicite** (question 3) : `forever_build` et `forever_sim_leveling` ne lisent jamais le profil ;
     l'agent le lit et passe les valeurs. Défauts visibles : `race` sans valeur → `Orc` gardé mais écrit dans
     `assumptions` et dans un bloc `inputs` (`{valeur, origine: argument|défaut}`) des deux outils.
   - Décision 99 : les données personnelles vivent hors du dépôt ; `ARCHITECTURE.md` (vault de T07) mis à jour en ce
     sens.
6. **D6 — Règle des skills (point 7)**, dans `format-reponse.md` (section « Données du joueur ») et le routeur :
   question qui dépend de race, faction, niveau, talents actuels ou métiers → `forever_player_profile` d'abord ;
   donnée présente → utilisée sans redemander, rappelée en une ligne (« Profil : <nom>, <classe> <race>, niveau <n>
   (profil actif) ») ; donnée absente → demandée **avant** tout calcul, avec la valeur la plus probable proposée et la
   commande `forever profile set` pour l'enregistrer ; jamais d'appel avec une donnée personnelle par défaut (un
   `inputs.*.origine = défaut` sur une donnée personnelle = réponse refusée) ; classe hors Mage → profil lu, calcul
   « non couvert » (carte du routeur). `forever-leveling/SKILL.md` (« garde le défaut de l'outil ») réécrit.
   Comparaisons : jamais un Monte Carlo contre un analytique ; entre deux builds, l'écart apparié de `forever_build`
   (`alternative.gap`, `order[].gap`, `next_step`) ou deux `monte_carlo_stats` avec intervalle ; intervalle qui contient
   zéro → « choix non départagé par le calcul ».
7. **D7 — Recommandations départagées (point 8)**, mode forever seulement (le seed garde ses méthodes, parité) :
   - **Modélisé** : talent absent de tout `angle_mort.talents` d'une entrée `absent` du registre (fonction
     `modeled_talents` dans `forever/engine/blind_spots.py`). Test structurel remplaçant la liste `UNMODELED` de
     `test_blind_spots.py` : toute clé de `talents.json` est lue dans `forever/engine|sim|optimize` ou figure dans un
     angle mort. `arcaneSubtlety` ajouté à `angle_mort.talents` de H2 (résistances de la cible, `absent`) : aucune
     entrée nouvelle, total 108 et 37/108 inchangés.
   - **Par niveau** : `_decide_step` garde les échantillons Monte Carlo des candidats (mêmes graines) ; chaque étape de
     `order[]` gagne `runner_up`, `gap` (apparié, intervalle), `significant`, `modeled`, `decided_by` ∈
     {`monte_carlo`, `modelise`, `non_departage`, `passage_palier`}. Règle : meilleur au Monte Carlo si significatif ;
     sinon, si un seul des deux est modélisé, le modélisé ; sinon le meilleur, marqué `non_departage` (« choix non
     départagé par le calcul »). Un non modélisé ne passe devant un modélisé que comme point de passage vers un palier
     (question 4), marqué `passage_palier`.
   - **Prochain talent depuis le build actuel** : avec `current` (build légal au niveau N − 1), `forever_build leveling
     --level N` rend `next_step` : toutes les additions légales au niveau N, chacune avec Monte Carlo apparié contre la
     meilleure, intervalle, `significant`, `modeled`, et le choix selon la règle ci-dessus. Le skill leveling s'en sert
     pour « quel talent au niveau N ».
   - **Évaluation** : cas `talent-niveau-22` (positif, catégorie talent) : question en français avec niveau 22, Givre,
     race et build actuel écrits en toutes lettres (aucune unité de jeu) ; correcteurs standard (skill, outil
     `forever_build` avec `"current"` et `"level"\s*:\s*22`, chiffres, certitude, provenance) + juge `llm`
     `mesure-et-modelise.md` (aucun talent non modélisé recommandé à la place d'un modélisé ; comparaison Monte Carlo
     contre Monte Carlo avec intervalle ; « non départagé » quand l'intervalle contient zéro). Suite : 51 cas, 31
     positifs, talent 6.
8. **D8 — Version du plugin** : `"version": "0.2.0"` (0.1.0 : T06). Politique : version relevée (mineure) à chaque
   tranche qui touche `plugin/`. Garde : `plugin/.claude-plugin/fingerprint.json` (`version`, empreinte des fichiers de
   `plugin/` hors `evals/results`) ; un test recalcule l'empreinte et échoue si elle change sans nouvelle version
   (`scripts/plugin_fingerprint.py` la réécrit). Script d'installation : `claude plugin validate --strict`. À vérifier
   au bloc F avant d'y croire : `claude plugin update` recopie après un changement de version, `validate --strict` ne
   lève plus d'avertissement. `docs/USAGE.md:27` réécrit.
9. **D9 — Rejeu des builds** : `scripts/replay_builds.py` (15 cas, préréglage complet, graine 12345, Orc) écrit les
   JSON dans `<cache>/builds/<étiquette>/` et un tableau Markdown. Trois passages : `r1` (données et règles actuelles,
   au bloc A), `r2-donnees` (après le bloc B), `r2-departage` (après le bloc E). Chaque recommandation changée (talents,
   ordre, `choices`, alternative, verdict de sensibilité ou de stabilité) est attribuée au passage qui la change, avec
   la valeur de données ou la règle en cause (révision 2 : ligne de `revisions.json` ; départage : `decided_by` de
   l'étape). `builds-T05.md` : ancien tableau gardé (historique), section « Rejeu T06b (révision 2) » avec le nouveau
   tableau et la liste des changements. Durée : relevée au passage `r1`, reportée dans le document.
10. **D10 — Documents** : décisions 98 (D1, D2, D3), 99 (D5), 100 (D7), 101 (D8) ; `.claude/rules/data.md` amendé ;
    ROADMAP (critères de T06b, reste de T08 : chaîne automatique et PR de données) ; ARCHITECTURE (versionnement,
    `forever/profile.py`, vault hors dépôt, outil `forever_player_profile`, 51 cas) ; `docs/USAGE.md` (profil,
    version du plugin) ; `docs/research/plugin-eval-T06.md` (passage T06b).

## Fichiers
```
forever/pipeline/install.py      (nouveau)  fusion candidate -> version courante, rapport, revisions.json (D3)
forever/data/1.60.1.70009/       talents.json, spells.json, confirmed_changes.json, sources.json (révision 2) ;
                                 _seed_talents.json, _seed_spells.json, revisions.json (nouveaux) ; manifest.json
forever/gamedata.py              build_game_data(..., rules) ; Hot Streak sans duration_s
forever/store.py, provenance.py, manifest.py, status.py   révision dans le manifeste et la provenance
forever/engine/talents.py, mana.py, crit.py, blind_spots.py   totaux, winters_chill_crit, modeled_talents
forever/optimize/leveling.py, build.py   order[] enrichi, next_step, départage, points, advantage
forever/explain.py, lookup.py, leveling.py   derived, alias, monte_carlo_stats, inputs
forever/profile.py               (nouveau)  profil joueur (D5)
forever/cli.py, mcp_server.py    forever install, forever profile, forever_player_profile ; rules jusqu'au chargement
plugin/skills/forever-router/{SKILL.md,format-reponse.md}, forever-leveling/SKILL.md, forever-mage/SKILL.md
plugin/.claude-plugin/plugin.json, fingerprint.json ; plugin/evals/talent-niveau-22/
scripts/replay_builds.py, scripts/plugin_fingerprint.py (nouveaux) ; scripts/plugin_eval_report.py ; install_plugin.ps1
docs/MECHANICS_REGISTRY.yaml (B11, B15, D4, G3, H2) ; DECISIONS, ROADMAP, ARCHITECTURE, USAGE, OPEN_QUESTIONS
docs/research/data-1.60.1.70009-r2.md (nouveau), builds-T05.md, plugin-eval-T06.md ; .claude/rules/data.md
tests/unit/test_install.py, test_seed_data.py, test_totals.py, test_profile.py, test_next_step.py,
test_plugin_version.py (nouveaux) ; tests existants à mettre à jour ci-dessous
```

## Interfaces
```
# forever/pipeline/install.py
def plan_install(candidate_dir, data_dir) -> InstallPlan        # changements {fichier, chemin, avant, après, source, certitude}
def apply_install(plan, data_dir, deps) -> Revision             # écrit, journalise, régénère le manifeste
# forever/gamedata.py
def build_game_data(version, rules="forever") -> GameData        # seed : _seed_talents.json, _seed_spells.json
# forever/engine
def tree_split(gd, pts) -> dict[str, int]                        # existant
def build_points(gd, pts, level, talented_bonus=0) -> Points     # by_tree, total, available, unspent
def winters_chill_crit(gd, stacks) -> float
def modeled_talents(gd, rules) -> frozenset[str]
# forever/profile.py
def profile_path(env) -> Path ; load_profile(path) -> Profile ; set_character(...) ; use(...) ; remove(...)
# CLI
forever install <candidate> [--dry-run | --yes]
forever profile show|list|set|use|remove ...
forever build leveling --level N --current "clé=rang,…"   -> next_step
# MCP
forever_player_profile(name=None) -> {active, character, characters, stale, missing, provenance}
forever_explain_mechanic(mechanic_id, level=None) -> ... derived
```

## Tests attendus (valeurs tirées des données ou des constats ci-dessus)
- **Mode seed figé** (`test_seed_data.py`, `test_data_import.py`) : `_seed_talents.json` et `_seed_spells.json`
  identiques au seed (sha256 `b1dcf6e696ea5783…` et `49272dc659d468dd…`) ; sur une copie des données où
  `talents.json` et `spells.json` prennent les valeurs du client (manifeste régénéré), `rules="seed"` rend les mêmes
  résultats qu'avant (`expected_cast`, `sim_leveling`, glouton PvP) et `rules="forever"` change ; toute la parité
  (`tests/parity/*`, 45 tests) verte sur `seed_game_data`, sans changer une valeur attendue.
- **Installation** (`test_install.py`, fixtures du client déjà présentes) : `--dry-run` n'écrit rien dans
  `forever/data` ; le plan de la fixture contient exactement les 15 changements confirmés, les 3 coûts, 49 changements
  de certitude, le retrait de `duration_s` ; un écart hors règles → refus ; `--yes` sur une copie : `revisions.json`
  (révision 2), manifeste valide, provenance `data_revision == 2`.
- **Données installées** : `lookup talent` à `certain` pour les 54 talents (Improved Frostbolt `FC-70009`, au lieu de
  `FC-69893` / `probable` dans `test_lookup_talent.py:86-95`) ; `hot_streak_rules == (20.0, 0.25, 3)` sans
  `duration_s` ; aucun `15` dans les rangs de Hot Streak ; Pyroblast r1 `mana == 125`, Ice Lance r1 `45`, Blast Wave
  r1 `215` en mode forever, et 112,5 / 41,25 / 202,5 en mode seed (`test_talent_rank_mana_estimate` migré sur
  `seed_game_data`) ; Impact rangs 2 et 3 : 7 et 10 ; Improved Scorch r2 67 ; Improved Blizzard r2 25 ; Presence of
  Mind r1 `[]` ; Blast Wave r1 niveau 30 ; décodage du client ↔ données installées : aucun écart hors champs gardés ;
  décodage ↔ `_seed_*` : exactement les écarts de `confirmed_changes.json` (18) ; description d'un talent sans `$`.
- **Totaux** (`test_totals.py`, `test_build_report.py` : `FIELDS` augmenté de `points` et `inputs`) : leveling 20 →
  `points.total == 11 == points.available`, `unspent == 0`, somme de `by_tree` = total ; PvP BG 40 → 31 ; raid 60 → 51
  (`points_available`, `mechanics.json`) ; dernier `order[].points_total` = `points.total` ; `advantage >= 0` et
  égal à `abs(mean)` ; B11 `derived` : 15 ; 41,25 ; 67,5 ; 93,75 ; 120 (% du mana de base, depuis `mana_pct_base` et le
  talent) ; D4 au rang 5 : 5 cumuls, 0,10 (`crit.winters_chill_per_stack` × cumuls maximum du rang, `talents.json`) ; `explain_mechanic("Arcane Blast")`
  trouve B11 ; `monte_carlo_stats` : `low <= mean <= high`, `n` égal à l'argument.
- **Profil** (`test_profile.py`, dossier temporaire par `FOREVER_PROFILE`) : trois personnages (Mage, Paladin,
  Démoniste), `use` change l'actif ; mise à jour partielle garde les autres champs ; race inconnue pour le Mage → erreur
  avec proches ; talents illégaux au niveau → erreur de `check_build` ; Paladin gardé `validated: false` ; chemin par
  défaut hors de `REPO_ROOT` ; `forever_player_profile` et `forever profile show --json` rendent le même JSON ; profil
  absent → `active: null` sans exception ; aucun réseau.
- **Défaut visible** : `forever_build` sans `race` → `inputs.race == {valeur: Orc, origine: défaut}` et une hypothèse
  qui le dit ; avec `race` → `origine: argument`.
- **Départage** (`test_next_step.py`, `test_blind_spots.py`, `test_optimize_leveling.py`) : chaque clé de
  `talents.json` est lue par le code ou dans un angle mort ; `arcaneSubtlety` dans H2 ; sur un cas construit où un
  talent modélisé sans effet sur la rotation et un non modélisé sont à égalité, le modélisé est choisi et marqué
  `modelise` ; deux non modélisés → `non_departage` ; `next_step` depuis un build légal au niveau 21 : tous les
  candidats légaux, intervalle, `significant` ; mode seed : `order` identique à `test_seed_optimize_parity`.
- **Plugin** : `plugin.json` a une version semver ; empreinte à jour (`test_plugin_version.py`) ; `test_plugin_manifest`
  inverse son assertion ; les skills citent `forever_player_profile`, la règle des données du joueur, « non départagé »
  et la comparaison à mesure égale (`test_plugin_structure.py`) ; `test_plugin_evals.py` : 51 cas, 31 positifs,
  talent 6, `talent-niveau-22` avec 6 correcteurs ; `LABELS` sans nombre en dur.
- **Registre** (`test_registry.py`) : total 108, 37/108, nombre de `teste` inchangés (aucun statut ne change : B11,
  B15, D4, G3 gagnent tests et sources, H2 son angle mort).

## Blocs et étapes
1. **Bloc A — Mode seed figé** : `_seed_*.json`, `build_game_data(..., rules)`, points d'entrée, fixture, parité
   basculée ; `scripts/replay_builds.py` et passage `r1`. Aucune valeur de jeu ne change.
2. **Bloc B — Installation** : `forever install` ; `forever decode` → candidate ; `--dry-run` → rapport
   `docs/research/data-1.60.1.70009-r2.md`, comparé à D3 (arrêt si écart) ; `--yes` ; tests des données installées ;
   tests de sens inverse repointés sur `_seed_*` ; passage `r2-donnees`.
3. **Bloc C — Totaux** (D4).
4. **Bloc D — Profil et défauts visibles** (D5), outil MCP avant les skills.
5. **Bloc E — Départage** (D7) : modélisé, `order[]` enrichi, `next_step` ; passage `r2-departage` ; `builds-T05.md`.
6. **Bloc F — Plugin** : skills (D6), cas `talent-niveau-22`, version et empreinte (D8, vérification de `update` et
   `--strict` sur place) ; évaluation rejouée en local (`--runs 1`, plafond 15 $, environ 6,5 $), résultats dans
   `plugin-eval-T06.md` : zéro alerte du contrôle des chiffres visée.
7. **Bloc G — Fin** : registre, documents (D10), `/verifier`, CI Ubuntu et Windows, fusion.

Critères de fin : `forever lookup talent` à `certain` pour les 54 talents ; Hot Streak à 20 s partout (données, moteur,
consultation) ; coûts en mana du client en mode forever, estimation B11 réservée au seed ; révision 2 visible dans la
provenance, `revisions.json` et le rapport de diff ; parité du seed verte sans valeur attendue changée ; totaux présents
dans `forever_build`, `forever_explain_mechanic`, `forever_lookup` et `forever_sim_leveling`, avec tests ;
`forever profile` et `forever_player_profile` ; départage et `next_step` ; builds de T05 rejoués et documentés ;
évaluation du plugin (51 cas) sans alerte du contrôle des chiffres ; `plugin.json` versionné, `validate --strict` vert ;
`uv run tasks.py verify` vert.

## Hors périmètre
- Vault, import de l'addon, fiches datées (T07) ; écriture du profil par MCP ; calculs Paladin et Démoniste (T12) ;
  métiers au-delà du nom et de la compétence (MT1).
- Chaîne automatique de veille et PR de données (T08) ; `forever_diff_versions` (T08, décision 41).
- Nouveaux effets de talents (Presence of Mind, Combustion, Cold Snap, Arcane Subtlety restent des angles morts).
- Coût absolu d'Arcane Blast dans `spells.json` (reste en pourcentage du mana de base).

## Risques
- **Convention des sorts** : `min`/`max` au niveau min(MaxLevel, 60) touchent les chemins `spell_level="rank"` (PvP) :
  les builds PvP peuvent changer ; attribué au passage `r2-donnees`.
- **Départage et parité** : la nouvelle règle ne doit jamais s'appliquer en seed (`test_seed_optimize_parity`) ;
  `order[]` plus coûteux (échantillons gardés) : durée relevée au rejeu.
- **Tests de sens inverse** (`test_decode_talents`, `test_decode_spells`, `test_client_decisions`, `test_diff.py:131`)
  : repointés sur `_seed_*`, sinon ils échouent faute d'écart ; plusieurs tests en mode forever à valeurs figées
  (`test_client_coefficients`, `test_rotations_t05`, `test_damage_modifiers`, `test_pvp_profile`, `test_build_*`)
  peuvent bouger : écrits au rouge avec les valeurs recalculées et la raison (révision 2), jamais ajustés après coup.
- **Évaluation et profil réel** : l'enfant de l'évaluation lit `~/.forever/profile.json` ; le cas `talent-niveau-22`
  donne toutes les données dans la question et le juge ne dépend pas du profil ; noter tout effet observé.
- **Mise à jour du plugin versionné** : si `update` ne recopie pas après changement de version, arrêt et question.
- **Fins de ligne** : écriture des données par `write_bytes` / `newline="\n"` ; `git diff --stat` avant chaque commit.

## Validation (2026-09-29)
Plan accepté par l'utilisateur avec l'option recommandée aux cinq questions (elles priment sur toute autre lecture du
texte ci-dessus) :
1. **D1** : révision 2 du dossier `1.60.1.70009` en place (`data_revision` dans la provenance, `revisions.json`,
   rapport de diff, `.claude/rules/data.md` amendée, décisions 17, 37 et 58 remplacées).
2. **D2** : copies figées `_seed_talents.json` et `_seed_spells.json`, contrôlées par le manifeste.
3. **D5** : profil dans `%USERPROFILE%\.forever\profile.json`, déplaçable par `FOREVER_PROFILE`, lu explicitement par
   `forever_player_profile`, jamais par les outils de calcul eux-mêmes.
4. **D7** : talent non modélisé permis comme point de passage vers un palier quand c'est le seul moyen d'ouvrir un
   talent modélisé, signalé (`passage_palier`).
5. **D3** : la validation du plan vaut accord pour les changements listés en D3 ; tout autre écart du rapport
   `forever install --dry-run` arrête l'exécution et est présenté à l'utilisateur.
- Conduite : un test verrouillé faux → demandes de correction regroupées (`tasks/T06b-corrections.md`) et présentées
  avant la fusion ; contexte plein → arrêt après un bloc vert et committé, avec l'état d'avancement.
