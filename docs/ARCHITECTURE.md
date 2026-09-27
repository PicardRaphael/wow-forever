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
│   ├── pipeline/              # builds.py, fetch.py, decode.py, diff.py, verify.py, report.py
│   ├── memory/                # fiches joueur (lecture/écriture dans le vault), import de l'addon
│   ├── provenance.py          # bloc provenance commun
│   ├── cli.py                 # commandes forever …
│   └── mcp_server.py          # outils MCP
├── plugin/                    # plugin Claude Code (skills, agents, hooks, commands, .mcp.json)
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
4. Règle réseau : seuls `forever status` et l'outil MCP `forever_status` appellent wago, via `forever/pipeline/builds.py` et le client HTTP `forever/pipeline/http_client.py` (seul `urlopen` du paquet, contrôlé par `tests/unit/test_network_boundary.py` ; `forever builds` et `forever fetch` s'y ajoutent en T03). Les autres outils relisent le cache ; au-delà de 6 h, ils renvoient le dernier état connu et ajoutent son âge aux hypothèses. `unknown` seulement sans aucun cache utilisable : un cache illisible ou daté dans le futur est traité comme absent (hypothèse ajoutée dans le second cas). `FOREVER_OFFLINE=1` ou `--offline` interdit tout appel.
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

## Moteur de mécaniques et registre
- `forever/gamedata.py` lit une version après contrôle d'intégrité (`store.load_version`) et construit un `GameData` gelé (sorts, talents dans l'ordre du fichier, règles de combat, raciaux, constantes). Seul module qui touche au JSON brut du moteur ; tout écart de schéma lève `data_schema` (code 3). En T02, `GameData` ne couvre que le Mage (un espace par classe en T12).
- `forever/engine/` : fonctions pures qui reçoivent `GameData` en premier paramètre (talents, personnage, sorts, toucher, critique, dégâts, incantation, mana, espérance d'un lancer). Aucun chiffre de jeu dans le code : seuls le lien talent → effet et la conversion d'unité `/ 100` (talents exprimés en %) y figurent. Chaque fonction cite ses identifiants de registre dans sa docstring (`Registre : A3, A4, H1`). `MECHANICS` (dans `forever/engine/__init__.py`) associe les 30 contrôles portés du seed à leurs identifiants.
- `mechanics.json` (par version, haché) : constantes absentes des tables du client, chacune avec `value`, `certainty`, `registry` (identifiant du registre) et `source`.
- Registre (`docs/MECHANICS_REGISTRY.yaml`) : champs obligatoires `id`, `categorie`, `description`, `forever`, `statut`, `certitude`, `sources`, `tests` ; champs optionnels `formule` (symbolique, seuls 0 et 1 admis) et `note` (périmètre couvert, reprise prévue). Une référence de test prend la forme `tests/…/fichier.py::test_nom` ; `teste` ou mieux en exige une dont la fonction existe (analyse `ast`). `forever.registry.validate` (via `scripts/check_registry.py --strict`, étape `registry` de `verify`) refuse aussi les chemins hors de `tests/`, les formules chiffrées, un identifiant cité par le moteur mais absent du registre, et une entrée testée des catégories A à H sans implémentation citée.
- `forever explain-mechanic <id>` / `forever_explain_mechanic` : entrée du registre, paramètres de la version courante (`mechanics.json` étiqueté par l'identifiant, règles de `combat_rules` associées), implémentations citées ; `certainty` reprend le registre, la certitude de la provenance est le minimum avec celles des paramètres.

## Outils MCP (peu nombreux, à fort levier)
| Outil | Rôle |
| --- | --- |
| `forever_status` | Fraîcheur et couverture du registre |
| `forever_lookup` | Sort, talent, objet, consommable, raciaux (paginé, `detail=false` par défaut) |
| `forever_explain_mechanic` | Entrée du registre, formule, certitude, paramètres de la version, implémentation, sources |
| `forever_sim_leveling` | Temps par monstre, XP/h, graphique optionnel |
| `forever_sim_raid` | DPS, intervalle de confiance, contributions |
| `forever_optimize_talents` | Ordre ou build optimal selon l'objectif (leveling, raid, PvP) |
| `forever_optimize_gear` | Ensemble réel simulé sous contraintes |
| `forever_consumables_plan` | Plan par zone, métier, budget |
| `forever_diff_versions` | Ce qui change entre deux versions, par classe |
| `forever_player_profile` | Lire ou mettre à jour une fiche joueur |

## Plugin Claude Code
- Skills : `forever-router` (aiguillage et règles), `forever-mage` puis une par classe, `forever-gear`, `forever-raid`, `forever-data`. Chaque SKILL.md fait moins de 200 lignes, sans aucun chiffre de jeu.
- Sous-agents produit : `data-updater`, `sim-runner`, `web-researcher`, `evaluator` (sorties courtes et structurées).
- Hooks produit : SessionStart (`forever status --json`).
- Commandes : `/forever`, `/forever-update`, `/forever-sim`, `/forever-raid-prep`, `/forever-respec`.

## Mémoire joueur
Fichiers du vault, suivis dans Git : `joueur/personnages/<nom>.json` (avec la version du jeu), `objectifs.md`, `decisions.md` (datées), `legacy.json`, `historique/`.
La mémoire de Claude ne garde que des pointeurs et des décisions, jamais de chiffres de jeu.

## Veille
`build-watch.yml` (cron 6 h) : `forever builds` ; si nouvelle version, `fetch`, `decode`, `diff`, `verify`, puis PR « data: A → B » avec le résumé du diff et une note pour le vault. Alerte si `silent`.
