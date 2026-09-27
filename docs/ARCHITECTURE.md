# Architecture

## Vue d'ensemble
Option retenue : **cœur MCP + plugin mince**. Toute la logique et les données vivent dans le paquet Python `forever`,
exposé par une CLI (`forever …`) et un serveur MCP. Le plugin Claude Code ne contient que des skills courts,
des hooks, des commandes et des sous-agents. Le même serveur MCP servira plus tard Claude.ai et ChatGPT.

```
forever-core/
├── forever/
│   ├── data/<version>/        # JSON par version : spells, talents, …, overrides.json, sources.json
│   ├── data/manifest.json     # version courante, sha256 par fichier, date, source, hotfixes
│   ├── registry.py            # lecture et contrôle de docs/MECHANICS_REGISTRY.yaml
│   ├── engine/                # cœur de mécaniques (fonctions pures)
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
4. Règle réseau : seuls `forever status` et l'outil MCP `forever_status` appellent wago, via `forever/pipeline/builds.py` (unique module réseau avec `forever builds` et `forever fetch` en T03). Les autres outils relisent le cache ; au-delà de 6 h, ils renvoient le dernier état connu et ajoutent son âge aux hypothèses. `unknown` seulement sans aucun cache. `FOREVER_OFFLINE=1` ou `--offline` interdit tout appel.
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
- Les outils qui lisent les données refusent de répondre si les empreintes ne correspondent pas (`data_integrity`, code de sortie 3) ; `forever status` le signale sans échouer. `.gitattributes` fixe les octets (`-text`) pour que les empreintes soient les mêmes sous Windows et Linux.

## Outils MCP (peu nombreux, à fort levier)
| Outil | Rôle |
| --- | --- |
| `forever_status` | Fraîcheur et couverture du registre |
| `forever_lookup` | Sort, talent, objet, consommable, raciaux (paginé, `detail=false` par défaut) |
| `forever_explain_mechanic` | Entrée du registre, formule, certitude, sources |
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
