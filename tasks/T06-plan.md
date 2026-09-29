# T06 — Plugin Claude Code : plan

> Plan rédigé le 2026-09-29, d'après la demande de l'utilisateur du même jour. **Décisions D1 à D10 à valider** (option recommandée en premier). Exécution : `/tranche T06` dans une nouvelle session, un cycle rouge → vert par bloc. Le bloc A vérifie sur place les mécanismes de Claude Code dont dépend le plan (installation, hooks, skills, évaluation) avant tout code.

## Contexte
Objectif de l'utilisateur : poser ses questions sur WoW Forever en langage naturel, depuis n'importe quel dossier, et pouvoir faire confiance à la réponse. Demande :
1. plugin installable au niveau utilisateur, qui pointe vers ce dépôt (variable d'environnement), script d'installation pour deux PC sous Windows, **pas de statusLine** ;
2. skills : un routeur, le leveling, le Mage (les autres domaines ajoutent le leur, ROADMAP) ; descriptions précises qui disent quand déclencher ; aucun chiffre de jeu dans les skills ;
3. format de réponse imposé : réponse directe d'abord, chiffres issus des outils seulement, certitude, hypothèses, angles morts, provenance (version, fraîcheur) ; si le projet ne sait pas, le dire et indiquer comment le savoir, sans deviner ;
4. hooks : au démarrage, une ligne de fraîcheur (rapide, tolérante hors ligne) ; en fin de réponse, signaler tout chiffre de jeu qui ne vient d'aucun appel d'outil de la session ;
5. sous-agents : recherche web (sources communautaires étiquetées, jamais prises pour vérité), simulations lourdes ;
6. évaluation : une trentaine de questions réelles avec leurs attentes, une vingtaine de questions voisines qui ne doivent pas déclencher le plugin, rejouable en CI si possible, sinon procédure documentée ;
7. mode d'emploi court : `docs/USAGE.md`.

## Constats (relevés le 2026-09-29)
- **Aucun dossier `plugin/`** : tout est à créer. `scripts/check_game_numbers.py` contrôle déjà `plugin/` et `addon/` (nombre suivi d'une unité de jeu) ; `CLAUDE.md` : plugin sans logique de calcul, aucun chiffre de jeu dans un skill ou un prompt.
- Serveur MCP : `forever mcp` (stdio), cinq outils : `forever_status`, `forever_lookup` (`kind` = `spell` ou `zones` seulement), `forever_explain_mechanic`, `forever_sim_leveling`, `forever_build` (T05). **Pas de consultation des talents** : « que fait le talent X au rang r » n'a pas d'outil (D8). « Quel talent prendre au niveau X » : ordre de `forever_build leveling`.
- `forever status --json` : ~0,8 s ; `FOREVER_OFFLINE=1` ou `--offline` interdit le réseau ; la fraîcheur hors ligne vient du cache (âge affiché).
- `docs/ARCHITECTURE.md` (« Plugin Claude Code ») prévoit : skills `forever-router`, `forever-mage` (puis `forever-gear`, `forever-raid`, `forever-data`) ; sous-agents `data-updater`, `sim-runner`, `web-researcher`, `evaluator` ; hook SessionStart ; commandes `/forever`, `/forever-update`, `/forever-sim`, `/forever-raid-prep`, `/forever-respec`. Décision 15 : **pas de statusline**. La table « Outils et skills prévus » prévoit `forever-leveling` (T04c).
- `docs/ROADMAP.md` (T06) : critères de fin encore écrits avec une statusline et un jeu d'aiguillage de 30 requêtes (60 % / 40 %, ≥ 90 % de bonnes décisions) : à mettre à jour (D9).
- Mécanismes de Claude Code (sous-agent de documentation, 2026-09-29 ; **à confirmer au bloc A**, plusieurs points étaient douteux) : plugin = `.claude-plugin/plugin.json` + `skills/`, `agents/`, `hooks/hooks.json`, `.mcp.json` ; `claude plugin validate` ; marketplace locale (`marketplace.json`) puis `claude plugin marketplace add <chemin>` et `claude plugin install <plugin>@<marketplace> --scope user` ; `.mcp.json` accepte `${VAR}`, `${VAR:-défaut}`, `${CLAUDE_PLUGIN_ROOT}` ; hook SessionStart : sortie standard ajoutée au contexte (ou `hookSpecificOutput.additionalContext`) ; hook Stop : message sans blocage (`systemMessage`) ou reprise forcée (`decision: block`) ; **chemin du transcript dans l'entrée du hook Stop incertain** ; `claude plugin eval` : cas `evals/<cas>/prompt.md`, correcteurs `regex`, `tool_used`, `tool_order`, `llm`, bouchons d'outils MCP, sortie JSON, seuil, plafond de coût, même authentification que Claude Code.
- Pièges connus (skill `/tranche`) : le mode auto refuse d'écrire dans `.github/workflows/` et `.claude/settings.json` (préparer un patch) ; heredocs longs fragiles sous Windows.

## Décisions (à valider)
1. **D1 — Emballage** : le plugin vit dans le dépôt (`plugin/`, nom `forever`), déclaré par une marketplace locale à la racine (`.claude-plugin/marketplace.json`, source `./plugin`). Installation au niveau utilisateur par `scripts/install_plugin.ps1`, le même sur les deux PC, idempotent : contrôle `git`, `uv` et `claude` ; fixe la variable d'environnement utilisateur `FOREVER_HOME` (chemin du dépôt) ; `uv sync` ; `claude plugin marketplace add <dépôt>` puis `claude plugin install forever@<marketplace> --scope user` ; contrôle final (`claude plugin validate`, `forever status --offline`, liste des outils MCP). Mise à jour : `git pull` puis la commande de mise à jour de la marketplace (confirmée au bloc A). `.mcp.json` : `uv run --project ${FOREVER_HOME} forever mcp`. Aucune statusLine (décision 15). Alternative écartée : `claude --plugin-dir` à chaque session (pas « depuis n'importe quel dossier » sans alias).
2. **D2 — Trois skills** : `forever-router` (toute question sur WoW Forever : carte des domaines couverts et non couverts avec la tranche qui les couvrira, choix de l'outil, format de réponse, règle « je ne sais pas »), `forever-leveling` (temps par monstre, XP par heure, ordre des talents au leveling, respec, zone ou donjon à mon niveau), `forever-mage` (sorts, talents, builds par contexte, mécaniques du Mage). Descriptions en français avec les mots des questions réelles (« niveau », « talent », « build », « respec », « zone », « Givre », « Arcanes »…) et ce qui ne doit pas déclencher (autres jeux, WoW hors Forever, programmation). Chaque `SKILL.md` sous 200 lignes, aucun chiffre de jeu ; le format de réponse dans un fichier joint du routeur (`format-reponse.md`), lu par les deux autres.
3. **D3 — Format de réponse imposé**, dans cet ordre : (1) réponse directe en une ou deux phrases ; (2) chiffres, chacun tiré d'un résultat d'outil de la session, avec l'outil ; (3) certitude (`provenance.certainty`, et pour un build « vérifiable en jeu ou non ») ; (4) hypothèses (les plus importantes de `provenance.assumptions`) ; (5) angles morts (`blind_spots` de `forever_build`, statut du registre par `forever_explain_mechanic` quand une mécanique compte) ; (6) provenance (version du jeu, fraîcheur, date). Réponse courte permise pour une consultation simple, sans jamais omettre (3) et (6). **Règle « je ne sais pas »** : mécanique au statut `absent`, domaine non couvert, outil en erreur → le dire, citer ce qui manque (entrée du registre, tranche de la feuille de route, test en jeu du protocole de `docs/ADDON.md`, question de `docs/OPEN_QUESTIONS.md`) et ne rien estimer de mémoire.
4. **D4 — Hooks, logique dans `forever/`** : deux sous-commandes de la CLI, appelées par `plugin/hooks/hooks.json` (le plugin reste mince) :
    - `forever hook session-start` : une seule ligne, **cache seulement** (aucun réseau : rapide et hors ligne), par exemple « WoW Forever : données <version>, fraîcheur <état> (vérifiée il y a <âge>), registre <couverture> » ; toute erreur (dépôt introuvable, `FOREVER_HOME` absent, données altérées) donne une ligne qui dit quoi faire, code 0 ; délai du hook 10 s. La vérification réseau reste `forever status`.
    - `forever hook check-numbers` : lit l'entrée JSON du hook Stop et le transcript de la session ; relève les nombres des résultats des outils MCP `forever_*` de la session ; relève dans la dernière réponse de l'assistant les chiffres de jeu (nombre suivi d'une unité : même motif que `check_game_numbers`, virgule décimale française comprise) ; signale ceux qui n'apparaissent dans aucun résultat d'outil par un message à l'utilisateur, **sans bloquer** la réponse. Alternative écartée pour T06 : forcer une reprise (`decision: block`), à réexaminer après l'évaluation.
5. **D5 — Deux sous-agents** : `forever-web-researcher` (WebSearch, WebFetch seulement ; chaque source porte son type : officielle Blizzard, communautaire, simulateur ; sa date et son adresse ; un chiffre d'une source est rapporté comme une affirmation de la source, jamais comme un fait ; rien n'entre dans `forever/data/`) et `forever-sim-runner` (lance les calculs lourds, par exemple `forever build … --preset complet`, et rend un résumé court). `data-updater` et `evaluator` : plus tard (T08, et l'évaluation passe par `claude plugin eval`).
6. **D6 — Évaluation** : suite au format de `claude plugin eval` dans `plugin/evals/` (format confirmé au bloc A) :
    - **30 questions réelles**, en français : talent (que fait un talent à un rang, quel talent prendre à un niveau : 5), meilleur build de leveling ou de contexte (6), faut-il respec (4), zone ou donjon à mon niveau (4), explication d'une mécanique (5), temps par monstre ou XP par heure (3), hors du périmètre couvert (3 : Paladin, prix de l'hôtel des ventes, butin d'un donjon) ;
    - **20 questions voisines** qui ne doivent pas déclencher le plugin : WoW retail ou Classic hors Forever, autres jeux, programmation et questions sur ce dépôt ;
    - attentes par cas : skill déclenché (ou aucun), outil MCP appelé (`tool_used` avec argument), aucun chiffre inventé (même règle que `forever hook check-numbers`, correcteur déterministe), certitude et provenance affichées (`regex`), « je ne sais pas » pour le hors périmètre (`llm` + `regex`) ;
    - **CI** : l'évaluation appelle le modèle (authentification, coût) : hors de la CI de chaque push ; un workflow manuel `plugin-eval.yml` (déclenchement à la main, secret d'API, plafond de coût) préparé en patch (piège du mode auto) ; la CI ordinaire contrôle la suite sans modèle (schéma, nombre de cas, skills et outils cités existants). Procédure locale documentée dans `docs/USAGE.md`.
7. **D7 — `docs/USAGE.md`** : installation (les deux PC), mise à jour, comment poser une question (exemples par catégorie de l'évaluation), lire la réponse (certitude, hypothèses, angles morts), ce que le plugin ne sait pas encore, lancer l'évaluation.
8. **D8 — Consultation des talents** : `forever_lookup(kind="talent", name=…, rank=…)` et `forever lookup talent <nom>` (nom anglais ou clé, proches suggérés) : arbre, palier, prérequis, rangs et valeurs (description aux valeurs du rang), sort appris, certitude et provenance ; lu dans `talents.json`. Sans elle, les questions « que fait tel talent » n'ont pas d'outil et le plugin ne pourrait que deviner.
9. **D9 — Feuille de route** : critères de fin de T06 réécrits (plus de statusline ; évaluation 30 + 20 ; seuils de D10).
10. **D10 — Seuils de l'évaluation** : aiguillage ≥ 90 % de bonnes décisions sur les 50 cas ; sur les 30 cas positifs, outil attendu appelé ≥ 90 %, **aucun chiffre inventé 100 %**, certitude et provenance affichées ≥ 90 % ; hors périmètre : « je ne sais pas » 3 sur 3.

## Fichiers
```
.claude-plugin/marketplace.json            marketplace locale (plugin forever, source ./plugin)
plugin/.claude-plugin/plugin.json          manifeste (nom, version, description, auteur)
plugin/.mcp.json                           serveur forever : uv run --project ${FOREVER_HOME} forever mcp
plugin/hooks/hooks.json                    SessionStart -> forever hook session-start ; Stop -> forever hook check-numbers
plugin/skills/forever-router/SKILL.md      aiguillage, carte des domaines, règle « je ne sais pas »
plugin/skills/forever-router/format-reponse.md
plugin/skills/forever-leveling/SKILL.md
plugin/skills/forever-mage/SKILL.md
plugin/agents/forever-web-researcher.md
plugin/agents/forever-sim-runner.md
plugin/evals/<cas>/prompt.md (+ correcteurs)   50 cas (D6)
forever/hooks.py                (nouveau)  ligne de fraîcheur (cache seulement), contrôle des chiffres d'un transcript
forever/lookup.py, forever/cli.py, forever/mcp_server.py   kind="talent" ; forever hook session-start|check-numbers
scripts/install_plugin.ps1      (nouveau)  installation utilisateur (D1)
scripts/check_game_numbers.py              motif partagé avec forever/hooks.py (une seule définition)
docs/USAGE.md                   (nouveau) ; docs/ROADMAP.md, ARCHITECTURE.md, DECISIONS.md
tests/unit/test_lookup_talent.py, test_hooks.py, test_plugin_structure.py, test_plugin_evals.py, test_install_script.py
tests/fixtures/transcripts/*.jsonl          transcripts anonymisés du bloc A (réponse sourcée, chiffre inventé, hors ligne)
.github/workflows/plugin-eval.yml           patch préparé pour l'utilisateur (déclenchement manuel)
```

## Interfaces
```
# forever/hooks.py
def session_line(deps) -> str                                # une ligne, jamais d'exception, aucun réseau
def game_numbers(text) -> list[str]                          # chiffres de jeu d'un texte (nombre + unité)
def unsourced_numbers(transcript_lines) -> list[str]         # chiffres de la dernière réponse absents des résultats d'outils forever_*
# forever/cli.py
forever hook session-start            -> stdout : la ligne ; code 0
forever hook check-numbers            -> stdin : entrée JSON du hook Stop ; stdout : JSON de message (vide si rien)
forever lookup talent <nom> [--rank R] [--json]
# forever/mcp_server.py
forever_lookup(kind="talent", name, rank=None) -> talent, arbre, palier, prérequis, rangs, valeurs, provenance
```

## Tests attendus
- **Consultation des talents** (`test_lookup_talent.py`) : `improvedFrostbolt` et « Improved Frostbolt » trouvent le même talent ; `rank=3` rend la valeur du rang 3 de `talents.json` ; nom inconnu → erreur avec proches ; rang hors limite → erreur ; provenance présente ; MCP et CLI rendent le même JSON.
- **Hooks** (`test_hooks.py`) : `session_line` sur les données du dépôt contient la version, la fraîcheur et la couverture du registre, en une ligne ; données altérées, `FOREVER_HOME` absent, cache vide → une ligne qui dit quoi faire, sans exception ; aucun appel réseau (`FakeHttp.failing`) ; temps < 2 s. `unsourced_numbers` sur les transcripts du bloc A : réponse dont tous les chiffres viennent des outils → vide ; chiffre de jeu inventé → signalé ; nombre sans unité (niveau, rang) ignoré ; virgule décimale et point équivalents ; chiffres de la question de l'utilisateur non signalés ; résultat d'un outil hors `forever_*` ne compte pas comme source.
- **Plugin** (`test_plugin_structure.py`) : `plugin.json` et `marketplace.json` valides (champs requis) ; `.mcp.json` lance `forever mcp` par `${FOREVER_HOME}` ; `hooks.json` appelle les deux sous-commandes existantes ; chaque skill a `name` et `description` (longueur bornée, mots de déclenchement), moins de 200 lignes, aucun chiffre de jeu (`check_game_numbers`) ; les outils cités par les skills existent dans le serveur MCP ; le routeur cite les deux autres skills et chaque tranche de domaine non couverte ; aucune clé `statusLine`.
- **Évaluation** (`test_plugin_evals.py`, sans modèle) : 30 cas positifs et 20 négatifs, identifiants uniques ; chaque cas positif a ses attentes (skill, outil, chiffres, certitude) ; les skills et outils attendus existent ; les catégories de D6 ont leurs effectifs.
- **Installation** (`test_install_script.py`, lecture du script) : fixe `FOREVER_HOME` au niveau utilisateur, lance `uv sync`, ajoute la marketplace, installe en portée utilisateur, se termine par un contrôle ; aucune écriture dans `forever/data/` ; aucun chiffre de jeu.

## Blocs et étapes
1. **Bloc A — Vérifications sur place (sans code produit)** : plugin minimal hors dépôt (un skill, un hook qui enregistre son entrée) ; relever sous Windows : champs réels du frontmatter d'un skill, entrée JSON des hooks SessionStart et Stop (chemin du transcript), format du transcript (appels MCP, résultats, dernier message), sortie qui atteint l'utilisateur sans bloquer, commandes d'installation non interactives et de mise à jour, `claude plugin validate`, un cas de `claude plugin eval` (format, correcteurs, coût d'un cas). Résultats consignés en annexe de ce plan ; transcripts anonymisés gardés comme fixtures ; toute décision contredite est signalée avant le bloc B.
2. **Bloc B — Consultation des talents** (D8).
3. **Bloc C — Hooks** dans `forever/` (D4).
4. **Bloc D — Plugin** : manifeste, marketplace, `.mcp.json`, `hooks.json`, trois skills, deux sous-agents (D2, D3, D5).
5. **Bloc E — Installation et mode d'emploi** : `scripts/install_plugin.ps1`, `docs/USAGE.md` ; installation réelle sur le premier PC, procédure pour le second.
6. **Bloc F — Évaluation** : 50 cas, contrôle sans modèle en CI, patch du workflow manuel, un passage complet en local (coût relevé), résultats dans `docs/research/plugin-eval-T06.md` ; ajustement des descriptions de skills si les seuils ne sont pas atteints (les cas ne changent pas pour faire passer).
7. **Bloc G — Fin** : `docs/ROADMAP.md` (D9), `ARCHITECTURE.md` (plugin réel, sous-agents et commandes retenus), `DECISIONS.md` ; `/verifier` ; CI Ubuntu et Windows ; fusion.

Critères de fin (ROADMAP, D9) : plugin installé au niveau utilisateur par le script sur un PC, utilisable depuis un autre dossier ; SessionStart injecte une ligne de fraîcheur hors ligne ; le hook Stop signale un chiffre inventé sur la fixture ; skills sans chiffre de jeu ; `forever lookup talent` ; évaluation 30 + 20 aux seuils de D10 (passage local documenté) ; `uv run tasks.py verify` vert.

## Hors périmètre
- Skills des autres domaines (PvP, donjons, Legacy, métiers, réputations, économie) : chaque tranche ajoute le sien et met à jour la carte du routeur.
- Commandes `/forever…` de `docs/ARCHITECTURE.md` : pas dans T06 (le langage naturel suffit), à reprendre si l'évaluation le justifie.
- Statusline (décision 15) ; serveur MCP distant (T13) ; mémoire joueur (T07) ; sous-agents `data-updater` et `evaluator`.
- Tout chiffre de jeu dans le plugin ; tout calcul dans le plugin.

## Risques
- **Mécanismes de Claude Code mal connus** (entrée du hook Stop, frontmatter, évaluation) : le bloc A les vérifie avant le code ; une décision contredite est présentée avant d'aller plus loin.
- **Démarrage du serveur MCP** : `uv run` à chaque session (environ une seconde) ; `FOREVER_HOME` absent ou faux → serveur absent : la ligne de SessionStart le dit et renvoie au script d'installation.
- **Faux positifs du contrôle des chiffres** (niveaux, rangs, dates, chiffres de la question) : règles et fixtures au bloc C ; message seulement, sans blocage.
- **Déclenchement des skills imprévisible** : mesuré par l'évaluation ; on ajuste les descriptions, jamais les cas.
- **Coût de l'évaluation** : plafond de coût, nombre de passages par cas réduit en local ; hors de la CI de chaque push.
- **Windows** : shell des hooks, chemins avec espaces, variable d'environnement visible seulement dans les nouveaux terminaux après le script.

## Validation (2026-09-29)
Plan accepté par l'utilisateur, avec ces précisions (elles priment sur le texte ci-dessus) :
- **D4** : le plugin est installé au niveau utilisateur, ses hooks tournent dans toutes les sessions. Ils n'agissent que là où le plugin sert : la ligne de fraîcheur au démarrage **seulement dans le dépôt wow-forever** (ailleurs, rien ; le routeur appelle `forever_status` quand une question sur WoW arrive) ; la vérification des chiffres **seulement si la session a utilisé un outil MCP ou un skill de forever** (sinon, sortie vide). Un test pour chacun des deux cas.
- **D1** : le script d'installation détecte aussi WoW dans les deux dossiers Program Files (`C:\Program Files\World of Warcraft`, `C:\Program Files (x86)\World of Warcraft`) et fixe `FOREVER_WOW_DIR` sur chaque PC ; `scripts/install_addon.py` lit `FOREVER_WOW_DIR` et cherche lui aussi dans les deux dossiers. `docs/USAGE.md` donne la commande PowerShell qui contourne la politique d'exécution des scripts (`powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1`).
- **D3** : réponses en français, courtes par défaut, détail seulement sur demande.
- **D10** : ajout du seuil **100 % de réponses avec certitude affichée** (sur les cas positifs) ; mesure du **taux de fausses alertes** de la vérification des chiffres sur le jeu de questions (consigné dans `docs/research/plugin-eval-T06.md`).
- D2, D5, D6, D7, D8, D9 : acceptées telles quelles.
- Conduite : si le bloc A contredit une décision, la présenter avant d'aller plus loin ; un test verrouillé faux → demandes de correction regroupées avant la fusion ; contexte plein → arrêt après un bloc vert et committé.

## Annexe — Bloc A : vérifications sur place (2026-09-29, Claude Code 2.1.284, Windows 11)
Plugin de sonde hors dépôt (un skill, deux hooks qui enregistrent leur entrée, le vrai serveur `forever mcp`), sessions `claude -p --plugin-dir`, marketplace locale installée en portée `local` puis retirée, trois passages de `claude plugin eval`.

| Point | Constat | Effet sur le plan |
|---|---|---|
| Noms des outils | skill : `forever:<skill>` (outil `Skill`, entrée `{"skill": "forever:forever-router"}`) ; outil MCP d'un serveur de plugin : `mcp__plugin_<plugin>_<serveur>__<outil>`, ici `mcp__plugin_forever_forever__forever_lookup` | noms repris par les correcteurs et par le filtre du hook Stop |
| Entrée SessionStart | `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `source` | `cwd` décide si la ligne s'affiche (D4 précisé) |
| Entrée Stop | en plus : `last_assistant_message` (texte final), `stop_hook_active`, `permission_mode` | la réponse vient de `last_assistant_message`, les résultats d'outils du transcript |
| Transcript | JSONL ; `tool_use` (`name`, `input`) dans `message.content` des lignes `assistant`, `tool_result` (`tool_use_id`, `content` texte JSON) dans les lignes `user` ; la trace d'évaluation (flux JSON) a la même forme de messages | un seul lecteur pour les deux |
| Sortie des hooks | stdout texte ou `hookSpecificOutput.additionalContext` → contexte du modèle ; `systemMessage` → message à l'utilisateur, sans blocage (vu dans le transcript `hook_system_message`, et dans la trace d'évaluation « Stop says: … ») | SessionStart renvoie du JSON (ligne visible + contexte) au lieu d'un texte seul |
| Shell des hooks | forme `command` : Git Bash (`/usr/bin/bash`) ; `${FOREVER_HOME:-défaut}` développé par bash ; forme `args` (exec) : `${CLAUDE_PLUGIN_ROOT}` développé, `${VAR:-…}` **non** | forme `command` ; Git est déjà exigé par le script |
| `.mcp.json` | `${VAR}`, `${VAR:-défaut}` et défaut imbriqué `${FOREVER_HOME:-${CLAUDE_PLUGIN_ROOT}/..}` développés | défaut `${CLAUDE_PLUGIN_ROOT}/..` (le dépôt quand le plugin est chargé sur place : évaluation, `--plugin-dir`) |
| Installation | `claude plugin marketplace add <dossier>` puis `claude plugin install forever@<marketplace> --scope user`, non interactifs ; le plugin est **copié** dans `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>` | `FOREVER_HOME` indispensable une fois installé |
| Mise à jour | avec `version` dans `plugin.json`, `claude plugin update` ne recopie rien tant que la version ne change pas ; sans `version`, `claude plugin update forever@<marketplace>` recopie depuis la source (« refreshed from source ») | pas de `version` dans `plugin.json` ; mise à jour : `git pull`, `claude plugin marketplace update`, `claude plugin update`, redémarrer |
| `claude plugin validate` | valide plugin et marketplace ; `--strict` échoue sur un avertissement (auteur absent) | contrôle final du script avec `--strict` |
| Évaluation | cas `evals/<cas>/prompt.md` (frontmatter `max_turns`, `runs`, `allowed_tools`, `tags`) + `graders/*.md` (`regex` avec `target: trace` et `match: not_contains`, `tool_used` avec `input_match`, `min`/`max`, `arm: both`, `llm`) ; l'environnement de l'enfant est filtré (`FOREVER_HOME` absent : serveur MCP en échec sans le défaut ci-dessus) ; vrai serveur : `--mocks off --allow-tools mcp__plugin_forever_forever__…` ; coût relevé ≈ 0,05 à 0,06 $ par passage d'un cas simple | « aucun chiffre inventé » : correcteur `regex` sur la trace, qui cherche le message du hook Stop (même règle) |
| Comportement observé | sans outil disponible, le modèle a donné un chiffre de WoW Classic « de mémoire » ; avec l'outil, il a écrit « 30 m » pour une portée en mètres alors que l'outil donne `range_yd` (unité fausse, nombre juste) | le format de réponse impose l'unité de l'outil ; le contrôle compare les nombres, pas les unités (limite notée) |

Complément du bloc E (installation réelle) : dans un dépôt git, la version installée d'un plugin sans `version` est le commit courant (`88d548e70820`) ; relancer le script après un `git pull` passe par `claude plugin update`, qui recopie. Le « 30 m » de la sonde n'est pas une erreur du modèle : la CLI écrit elle-même la portée en « m » (usage du client français).

Aucune décision D1 à D10 n'est contredite. Ajustements de détail : `plugin.json` sans `version` ; sortie JSON de SessionStart ; défauts `${CLAUDE_PLUGIN_ROOT}/..`. Transcripts anonymisés et réduits dans `tests/fixtures/transcripts/`.
