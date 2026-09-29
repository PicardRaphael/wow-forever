# Architecture

## Vue d'ensemble
Option retenue : **cœur MCP + plugin mince**. Toute la logique et les données vivent dans le paquet Python `forever`,
exposé par une CLI (`forever …`) et un serveur MCP. Le plugin Claude Code ne contient que des skills courts,
des hooks, des commandes et des sous-agents. Le même serveur MCP servira plus tard Claude.ai et ChatGPT.

```
forever-core/
├── forever/
│   ├── data/<version>/        # JSON par version : spells, talents, …, mechanics.json, overrides.json, sources.json
│   ├── data/manifest.json     # version courante, sha256 par fichier, date, source, hotfixes
│   ├── registry.py            # lecture et contrôle de docs/MECHANICS_REGISTRY.yaml
│   ├── gamedata.py            # GameData typé et gelé, construit depuis une version vérifiée
│   ├── engine/                # cœur de mécaniques (fonctions pures, GameData en paramètre)
│   ├── explain.py             # explication d'une mécanique (registre + paramètres de la version)
│   ├── sim/                   # leveling_mc.py, leveling_analytic.py, raid_analytic.py, raid_mc.py
│   ├── optim/                 # talents.py, gear.py, consumables.py, respec.py
│   ├── charts/                # graphiques déterministes (PNG/SVG)
│   ├── pipeline/              # builds, fetch, tables, tooltip, decode, sources, diff, verify, report ;
│   │                          # combatlog, measure, lua_table, questie, monsters, addon_sv, refresh (sources locales)
│   ├── memory/                # fiches joueur (lecture/écriture dans le vault), import de l'addon
│   ├── provenance.py          # bloc provenance commun
│   ├── cli.py                 # commandes forever …
│   └── mcp_server.py          # outils MCP
├── plugin/                    # plugin Claude Code (skills, agents, hooks, commands, .mcp.json)
├── addon/                     # addons du jeu (ForeverLogger ; ForeverAssist prévu), règles : docs/ADDON.md
├── tests/{unit,golden,parity,fixtures}/
└── .github/workflows/{ci.yml,build-watch.yml}
```

## Bloc provenance (dans chaque réponse d'outil)
```json
{"provenance": {"game_version": "1.60.1.70009", "data_sha": "<12 hex>", "generated_at": "2026-09-26T10:00:00Z",
                "freshness": "fresh|stale|unknown|silent", "certainty": "certain|probable|suppose",
                "assumptions": ["PV des monstres estimés (cible Blizzard 10-15 s)"], "registry_coverage": "87/120"}}
```

## Fraîcheur
1. `forever status` lit `data/manifest.json`, interroge la dernière version publiée du produit (wago.tools, expiration réseau 2 s, cache 6 h dans `~/.cache/forever/status.json`, ou `FOREVER_CACHE_DIR`) et vérifie les empreintes locales.
2. Statuts : `fresh` (versions égales), `stale` (plus récente disponible), `unknown` (réseau indisponible, dernier état affiché avec son âge), `silent` (aucune nouvelle version depuis plus de 14 jours : possible changement de produit au lancement).
3. Moments de contrôle : hook SessionStart (une ligne de contexte), champ `freshness` et bloc provenance de chaque outil, workflow planifié `build-watch.yml` toutes les 6 h. Pas de statusline (décision 15).
4. Règle réseau : seuls `forever status`, l'outil MCP `forever_status`, `forever builds` et `forever fetch` appellent wago, via `forever/pipeline/builds.py`, `forever/pipeline/fetch.py` et le client HTTP injecté `forever/pipeline/http_client.py` (seul `urlopen` du paquet, contrôlé par `tests/unit/test_network_boundary.py` ; délai 2 s pour `status` et `builds`, 30 s par table pour `fetch`). `builds` et `fetch` échouent avec le code 5 (`offline`, `builds_unavailable`, `fetch_failed`) ; `decode`, `diff`, `verify` et `report` ne touchent jamais au réseau. Les autres outils relisent le cache ; au-delà de 6 h, ils renvoient le dernier état connu et ajoutent son âge aux hypothèses. `unknown` seulement sans aucun cache utilisable : un cache illisible ou daté dans le futur est traité comme absent (hypothèse ajoutée dans le second cas). `FOREVER_OFFLINE=1` ou `--offline` interdit tout appel.
5. Priorité des statuts : aucune observation → `unknown` ; version publiée plus récente que la locale → `stale` ; dernière version publiée depuis plus de 14 jours, ou aucune version du préfixe → `silent` ; sinon `fresh`.
6. Si `stale` : l'agent répond quand même, étiquette la réponse, baisse la certitude des entités touchées par le diff et propose `forever update`. Jamais de mise à jour silencieuse.
7. Cache des résultats : clé `(game_version, data_sha, registry_version, profil, scénario, seed)`.

## Données versionnées et manifeste
- Un dossier par version (`forever/data/<version>/`), immuable ; `overrides.json` (corrections manuelles) vit dans le dossier de version, jamais à la racine.
- `sources.json` (par version, haché comme les autres fichiers) : produit, préfixe de version, date de collecte, et pour chaque fichier sa source, sa certitude (`certain`, `probable`, `suppose` ; FC→certain, FS→probable, PC et EST→suppose), `field_certainty` et `field_notes` par champ.
- `manifest.json` : déterministe (aucun horodatage), généré uniquement par `uv run forever manifest --update`.
  ```json
  {"schema_version": 1, "game_version": "1.60.1.70009",
   "versions": {"1.60.1.70009": {"product": "wow_classic_beta", "version_prefix": "1.60.", "collected_at": "2026-09-26",
     "hotfixes": [], "data_sha": "<12 hex>", "data_sha256": "<64 hex>", "files": {"spells.json": "<sha256>"}}}}
  ```
  `data_sha256` = sha256 des lignes `"<nom> <sha256>
"` triées ; `data_sha` en est le préfixe de 12 caractères.
- Les outils qui lisent les données refusent de répondre si les empreintes ne correspondent pas ou si le manifeste est présent mais illisible, mal formé ou incohérent (`data_integrity`, code de sortie 3 ; manifeste absent : `manifest_missing`) ; `forever status` le signale sans échouer. Le `data_sha` de la provenance est toujours calculé sur les fichiers présents ; s'il diffère du manifeste, l'écart figure dans les hypothèses. `.gitattributes` fixe les octets (`-text`) pour que les empreintes soient les mêmes sous Windows et Linux.

## Pipeline de données (T03)
- `forever builds` : versions publiées du produit (`sources.json` de la version locale), de la plus récente à la plus ancienne, version locale marquée.
- `forever fetch --version X [--tables …] [--locale frFR] [--refresh]` : CSV de `https://wago.tools/db2/<Table>/csv?build=X` (`&locale=frFR` pour une autre locale) dans `<cache>/wago/<version>/<locale>/<Table>.csv`, indexés par `fetch.json` (URL, sha256, taille, date). Un fichier conforme à son empreinte n'est pas retéléchargé ; une réponse sans en-tête CSV est refusée ; les tables réussies restent écrites si d'autres échouent. Sans `--tables`, la liste vient de `decode_rules.json`.
- `decode_rules.json` (dans le dossier de version, haché, hérité par les versions suivantes) : tables à télécharger, lignes de compétence du Mage, géométrie de l'arbre, identifiants d'effet et d'aura, niveaux d'évaluation, sélection des variables de rang (`rank_variables`), sorts suivis. `forever/pipeline/` ne contient aucune de ces valeurs.
- `forever/pipeline/tables.py` : lecture typée des CSV (colonnes déclarées par table, `data_schema` qui nomme la table, la colonne et la ligne). `tooltip.py` : évaluation pure des variables d'infobulle (`$s1`, `$d`, `$<sort>s1`, `$/1000;S1`, `${…}.N`), valeurs fournies par un résolveur ; tout autre motif lève une erreur, jamais de valeur devinée.
- `forever decode --version X [--csv-dir D] [--out D] [--force]` écrit une **version candidate** hors de `forever/data/` (défaut `<cache>/candidates/<version>/`) : `manifest.json` + `<version>/` avec `talents.json` et `spells.json` décodés, les fichiers non dérivables du client hérités de la version locale la plus récente (`inherited_from` dans le fichier et dans son entrée de `sources.json`) et un `sources.json` généré. Talents : `ranks` (forme de la référence, positions lues par le moteur) et `tooltip_values` (toutes les variables de l'infobulle). T03 n'installe jamais une candidate (T08).
- `forever diff A B`, `forever verify [SOURCE]`, `forever report A B [--out F]` acceptent un identifiant de version du dépôt ou le chemin d'une candidate (`unknown_version`, code 4) et exigent l'intégrité des deux côtés. `verify` : schéma du moteur, `len(ranks) == max`, prérequis, positions uniques, longueur et niveaux des rangs de sort, `sources.json` complet ; code 3 en cas d'écart. `report` : Markdown déterministe « data: A → B », futur corps de PR de T08.
- `confirmed_changes.json` (dossier de version) : écarts entre le décodage du client et la référence de la version, tranchés par l'utilisateur, avec leur nature (`client`, `format`, `convention`). Les tests vérifient la liste dans les deux sens ; l'installation de ces valeurs revient à T08.

## Sources locales du client (T04a)
- `forever logs scan [--dir D]` et `forever logs measure FICHIER|DOSSIER [--max-gap S] [--addon-sv F]` : lecture des journaux (`combatlog.py` : format 22 et bloc avancé décrits dans le code comme un format de fichier ; événement inconnu gardé brut ; `unsupported_log` code 3 ; ligne mal formée `data_schema` avec fichier et ligne), puis mesures pures (`measure.py`) : PV max par PNJ et niveau (créatures invoquées exclues, conflits listés), coûts, intervalles entre instantanés enchaînés (fenêtre `--max-gap`, paramètre de l'outil), durées d'incantation, critiques, touchés et ratés par école et écart de niveau (niveau du lanceur par `ForeverLoggerDB`).
- `forever questie info [--dir D]` et `forever monsters build --logs D [--questie D] [--out D] [--force]` : table des monstres écrite hors de `forever/data/` (`candidate_exists` code 2), puis installée à la main avec `forever manifest --update`.
- `lua_table.py` : analyseur pur des tables Lua littérales (Questie, SavedVariables) ; aucun Lua exécuté, aucune dépendance.
- Données : `monsters.json` (PNJ mesurés `certain`, agrégat `hp_by_level` : journal d'abord, sinon médiane Questie `suppose`) et `spell_scaling.json` (produit par `forever decode` : points de base, points par niveau, variance et ticks de chaque effet de dégâts ; `MaxLevel` 0 résolu au décodage). `GameData.monsters` et `GameData.scaling` ; moteur : `rank_values_at_level` (registre G7).
- Registre : champ optionnel `preuves` (journal sous `tests/fixtures/combatlog/`, date, mesure, `n`, test) ; `valide-journal` exige une preuve valide avec `n` ≥ `tolerance.n_min`.
- T04b : journaux `.txt.gz` lus comme les `.txt` (fixtures compressées) ; `forever logs measure … [--addon-sv F] [--questie-sv F] [--utc-offset H] [--caster-level N]` : niveau du lanceur à l'instant de chaque sort (`forever/pipeline/levels.py` : ForeverLoggerDB, puis carnet `journey` de la SavedVariable de Questie, lu par un balayage tolérant aux chaînes binaires, puis niveau saisi) ; intervalles limités aux sorts qui déclenchent la recharge globale (`start_recovery_ms` de `spell_scaling.json`, décodé de `SpellCooldowns`), touchés et ratés aux sorts des données. Preuves du registre : `journal` peut être une liste (mesure sur leur réunion), les preuves d'une même mesure se cumulent, `tolerance.ecart_s` contrôle `ecart_median_s` et `ecart_p10_s`.
- `forever monsters build … [--fit-exclude NPC]` : `monsters.json` schéma 2 avec `questie_correction` (rapports médians par niveau mesuré, droite, plage, PNJ exclus) appliquée aux niveaux connus seulement de Questie, et `inversions` listées.

## Moteur de mécaniques et registre
- `forever/gamedata.py` lit une version après contrôle d'intégrité (`store.load_version`) et construit un `GameData` gelé (sorts, talents dans l'ordre du fichier, règles de combat, raciaux, constantes). Seul module qui touche au JSON brut du moteur ; tout écart de schéma lève `data_schema` (code 3). En T02, `GameData` ne couvre que le Mage (un espace par classe en T12).
- `forever/engine/` : fonctions pures qui reçoivent `GameData` en premier paramètre (talents, personnage, sorts, toucher, critique, dégâts, incantation, mana, espérance d'un lancer). Aucun chiffre de jeu dans le code : seuls le lien talent → effet et la conversion d'unité `/ 100` (talents exprimés en %) y figurent. Chaque fonction cite ses identifiants de registre dans sa docstring (`Registre : A3, A4, H1`). `MECHANICS` (dans `forever/engine/__init__.py`) associe les 30 contrôles portés du seed à leurs identifiants.
- `mechanics.json` (par version, haché) : constantes absentes des tables du client, chacune avec `value`, `certainty`, `registry` (identifiant du registre) et `source` ; T04b : clés `leveling.*` (chiffres du simulateur du seed) et `hit.miss_per_level_below`.
- T04b, leveling : moteur `forever/engine/monsters.py` (PV par niveau et source, correction Questie, coup et XP des monstres, armure), `movement.py` (temps de vol, ralentis, gel, portée, cadence des coups), recul et recharges (`casting.py`), régénération en combat et repos (`mana.py`), tics de DoT et d'Ignite, tirage des dégâts (`damage.py`), dégâts au niveau du personnage (`spells.rank_damage`, `expected_cast(spell_level=…)`). Simulateurs `forever/sim/leveling_mc.py` (Monte Carlo, générateur injecté, ordre des tirages du seed) et `forever/sim/leveling_analytic.py` : orchestration seulement. Service commun CLI/MCP `forever/leveling.py` ; graphique `forever/chart.py` (matplotlib Agg sans pyplot, PNG déterministe, jamais dans `forever/data/`) ; `forever sim leveling`, `forever chart leveling`.
- Registre (`docs/MECHANICS_REGISTRY.yaml`) : champs obligatoires `id`, `categorie`, `description`, `forever`, `statut`, `certitude`, `sources`, `tests` ; champs optionnels `formule` (symbolique, seuls 0 et 1 admis) et `note` (périmètre couvert, reprise prévue). Une référence de test prend la forme `tests/…/fichier.py::test_nom` ; `teste` ou mieux en exige une dont la fonction existe (analyse `ast`). `forever.registry.validate` (via `scripts/check_registry.py --strict`, étape `registry` de `verify`) refuse aussi les chemins hors de `tests/`, les formules chiffrées, un identifiant cité par le moteur mais absent du registre, et une entrée testée des catégories A à H sans implémentation citée.
- `forever explain-mechanic <id>` / `forever_explain_mechanic` : entrée du registre, paramètres de la version courante (`mechanics.json` étiqueté par l'identifiant, règles de `combat_rules` associées), implémentations citées ; `certainty` reprend le registre, la certitude de la provenance est le minimum avec celles des paramètres.

## Builds par contexte (T05)
- `forever build <contexte> --level N` (`leveling`, `dungeon`, `raid`, `pvp-bg`, `pvp-world`) et l'outil MCP `forever_build` : même service, `forever/build.py` (validation, rapport, hypothèses, certitude = minimum des sources, provenance ; au-delà de `build.beta_level_cap`, « non vérifiable en jeu avant la sortie »).
- `forever/optimize/` : `leveling.py` (faisceau du seed, parité exacte en mode seed ; en mode forever, choix du build cherchés avec les talents et départs multiples par arbre), `endgame.py` (donjon, raid, PvP : départs par arbre et par paire d'arbres, recherche locale, décision au Monte Carlo apparié ; glouton PvP du seed pour la parité), `decide.py` (écart apparié, intervalle, stabilité), `respec.py` (conseil du seed et conseil forever par niveau).
- `forever/sim/encounter.py` : scénarios provisoires de donjon et de raid (`build.scenarios`), analytique et Monte Carlo ; règles dans `forever/engine/encounter.py`. `forever/sim/community.py` : écart d'un build de la communauté avec le nôtre (bloc J, `scripts/build_community_fixture.py`).
- Moteur : `variants.py` (hypothèses incertaines, plages `range` de `mechanics.json`), `pvp.py` (profil PvP du seed), `respec.py`, `blind_spots.py` (angles morts : champ `angle_mort` du registre, estimations bornées).

## Outils MCP (peu nombreux, à fort levier)
| Outil | Rôle |
| --- | --- |
| `forever_status` | Fraîcheur et couverture du registre |
| `forever_lookup` | Sort, talent (T06), zones (T04c) ; objet, consommable, raciaux à venir (paginé, `detail=false` par défaut) ; domaines prévus : section « Outils et skills prévus » |
| `forever_explain_mechanic` | Entrée du registre (par identifiant ou par mots de la description, T06), formule, certitude, paramètres de la version, implémentation, sources |
| `forever_sim_leveling` | Temps par monstre, XP/h : Monte Carlo et analytique, PV du monstre (valeur, source, certitude) ; graphique par `forever chart leveling` (T04b) |
| `forever_sim_raid` | DPS, intervalle de confiance, contributions |
| `forever_build` | Build par contexte (leveling, donjon, raid, PvP) : talents, ordre, raisons, alternative, stabilité, sensibilité, respec, angles morts (T05, décision 86) |
| `forever_optimize_gear` | Ensemble réel simulé sous contraintes |
| `forever_consumables_plan` | Plan par zone, métier, budget |
| `forever_diff_versions` | Ce qui change entre deux versions, par classe |
| `forever_player_profile` | Lire le profil du joueur (personnage actif ou nommé, `stale`, `missing`), en lecture seule ; écriture par `forever profile set` (T06b, décision 99) |

## Plugin Claude Code
Livré en T06 (`plugin/`, décisions 91 à 97), installé au niveau utilisateur par `scripts/install_plugin.ps1` depuis la
marketplace locale du dépôt (`.claude-plugin/marketplace.json`, `forever@wow-forever`) ; mode d'emploi : `docs/USAGE.md`.
- **Mince** : aucun calcul ni chiffre de jeu ; le serveur MCP (`plugin/.mcp.json`) et les hooks lancent le dépôt pointé
  par `FOREVER_HOME` (défaut `${CLAUDE_PLUGIN_ROOT}/..`, le dépôt quand le plugin est chargé sur place).
- **Skills** : `forever-router` (aiguillage, carte des domaines couverts et non couverts avec leur tranche, format de
  réponse `format-reponse.md`, règle « je ne sais pas »), `forever-leveling`, `forever-mage`. Chaque tranche de domaine
  ajoute son skill et met à jour la carte du routeur. Chaque SKILL.md fait moins de 200 lignes, sans chiffre de jeu.
- **Sous-agents** : `forever-web-researcher` (WebSearch, WebFetch ; sources étiquetées officielle, communautaire,
  simulateur ; rien n'entre dans `forever/data/`), `forever-sim-runner` (calculs lourds par les outils forever).
  `data-updater` (T08) et `evaluator` (remplacé par `claude plugin eval`) : plus tard ou abandonnés.
- **Hooks** (logique dans `forever/hooks.py`, sous-commandes `forever hook …`) : SessionStart → ligne de fraîcheur,
  cache seulement, **seulement dans le dépôt** ; Stop → chiffres de jeu de la réponse absents des résultats des outils
  `forever_*` de la session, message `[forever:chiffres]` sans blocage, **seulement si la session a utilisé forever**.
  Garde dans `hooks.json` : rien ne s'exécute sans `pyproject.toml` au chemin du dépôt (aucune erreur ailleurs).
- **Pas de statusline** (décision 15), pas de commandes `/forever…` en T06 (le langage naturel suffit ; à reprendre si
  l'évaluation le justifie).
- **Version** : semver dans `plugin.json` (0.2.0 en T06b), relevée à chaque changement de `plugin/`, gardée par
  `plugin/.claude-plugin/fingerprint.json` (`scripts/plugin_fingerprint.py`, décision 101).
- **Évaluation** : `plugin/evals/` (31 questions réelles, 20 voisines ; 51 cas depuis T06b), contrôlée sans modèle en CI
  (`tests/unit/test_plugin_evals.py`) ; passage avec le modèle à la main, rapport par `scripts/plugin_eval_report.py`
  (seuils de la décision 96), résultats dans `docs/research/plugin-eval-T06.md`.

## Outils et skills prévus (provisoires)
Nouveaux domaines de `docs/ROADMAP.md`. Tout ce qui suit est **provisoire** : la forme définitive (nom, paramètres, schéma de sortie) se fixe au plan de chaque tranche (décision 63).
- **Principe** : les consultations passent par `forever_lookup` avec un paramètre de domaine, plutôt que par un outil par domaine ; des outils séparés seulement pour les calculs (simulations, optimiseurs, prix). La liste d'outils reste courte et à fort levier ; chaque domaine renvoie des résultats compacts, paginés, avec provenance et certitude par champ.
- Un calcul peut aussi rejoindre un outil de calcul existant (par exemple `forever_build` avec le contexte `pvp-bg`) plutôt que créer un outil.

| Domaine | Consultation (`forever_lookup`, domaine) | Calcul (outil séparé) | Skill | Tranche |
| --- | --- | --- | --- | --- |
| Leveling : zone ou donjon à mon niveau | `zones` (données de Questie lues localement) | — | `forever-leveling` | T04c |
| PvP | `pvp` : savoir des 9 classes, fiches par affrontement, champs de bataille, équipement PvP, monde ouvert, rendements décroissants mesurés | Profil PvP du Mage : `forever_build`, contextes `pvp-bg` et `pvp-world` | `forever-pvp` | PV1, PV2 (fiches en jeu : FA1p) |
| Donjons | `dungeons` : niveaux, boss, butin | — | `forever-dungeons` | DJ1 |
| Legacy | `legacy` : catalogue, puis état importé | Conseil des bonus par personnage (appelle le simulateur de leveling) | `forever-legacy` | LG1, LG2 |
| Métiers | `professions` : recettes, sources, points Legacy | Plan de montée de compétence (coût en or avec EC1) | `forever-professions` | MT1 |
| Réputations | `reputations` : factions, paliers, gains, récompenses | Plan de montée (temps estimé) | `forever-reputations` | RP1 |
| Économie | — | `forever_prices` (seul outil qui ajoute un accès réseau, après accord) | rattaché à `forever-professions` ou skill propre | EC1 |

- Skills : chacun sous 200 lignes, sans chiffre de jeu, ajouté par sa tranche de domaine (T06 ne livre que le routeur, le leveling et le Mage) ; le routeur `forever-router` reçoit la carte des domaines à chaque ajout.
- Commandes CLI : `forever pvp …`, `forever dungeon …`, `forever legacy …`, `forever profession …`, `forever rep …`, `forever prices …` (détail dans chaque section de `docs/ROADMAP.md`), toutes branchées sur les mêmes services que le MCP.

## Mémoire joueur
Profil minimal (T06b, décision 99) : `forever/profile.py`, fichier `FOREVER_PROFILE` ou `~/.forever/profile.json`, **hors du dépôt** (écriture refusée sous le dépôt) : personnages (classe, race, faction, niveau, talents, métiers, version des données), un actif. Les outils de calcul ne le lisent jamais : l'agent le lit (`forever_player_profile`) et passe les valeurs ; chaque rapport rend `inputs` (origine `argument` ou `default`).
Vault de T07, hors du dépôt lui aussi (données personnelles) : fiches datées `personnages/<nom>.json` (avec la version du jeu), `objectifs.md`, `decisions.md`, `legacy.json`, `historique/`.
La mémoire de Claude ne garde que des pointeurs et des décisions, jamais de chiffres de jeu.

## Veille
`build-watch.yml` (cron 6 h) : `forever builds` ; si nouvelle version, `fetch`, `decode`, `diff`, `verify`, puis PR « data: A → B » avec le résumé du diff et une note pour le vault. Alerte si `silent`.

## T04c
- Moteur : `forever/engine/armor.py` (armure portée selon le niveau d'apprentissage lu dans le client, `worn_armor`), `buffs.py` (aura d'Arcane Blast), `leveling.py` (couleurs de quête, bande de niveaux), `damage.py` (Ignite roulant : `roll_ignite`, `ignite_ticks_due`, `predict_ignite_ticks`), `mana.py` (`arcane_blast_cost`, régénération selon `rules`).
- Simulateurs : options `rules` (`forever` ou `seed`), `armor`, `ab_stacks`, `ab_dump` ; rotation `arcane` ; journal des lancers `kill_mc(log=…)` pour les tests.
- Données : `spell_scaling.json.utility` (armures, produit par `decode` avec `decode_rules.json.utility_spells`), `mechanics.json` : `leveling.ignite` (client), `leveling.ignite_rule`, `leveling.quest_band`.
- `forever measures refresh` (`forever/pipeline/refresh.py`) : collecte sur disque, mesures, comparaison, écriture après accord (`Deps.confirm`) de `monsters.json`, de sa source dans `sources.json`, du manifeste et de l'instantané `<cache>/measures/last.json` ; `forever lookup zones` et `forever_lookup(kind="zones")` (`forever/lookup.py`, `forever/pipeline/questie.py`).
