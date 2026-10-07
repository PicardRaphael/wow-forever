# T08e — Installation seule des fiches recopiées du client : plan

Demande de l'utilisateur du 2026-10-07 (décision 198), section T08e de `docs/ROADMAP.md`, précisée par la commande
`/tranche T08e` du même jour et par la réponse de l'utilisateur à la question du plan (ci-dessous). Plan écrit sans
code ; exécution dans une nouvelle session, sur la branche `t08e`, un cycle rouge → vert par bloc.

## Constat du plan : 70245 r1 a défait la refonte du Guerrier

Lecture locale du 2026-10-07 (rapports `<cache>/update/report-20261007T*.json`, copie de préparation
`<cache>/update/stage-1.60.1.70245`, historique git) :

- Les deux attentes réelles touchent la même entrée : `pvp_dr` différent sur `classes.json` `/classes/Warrior`
  (297 feuilles), `mage_build` et `mage_leveling` identiques, report à la main sans perte (155 puis 152 gardés).
- **r1 (70170 r5 → 70245 r1) n'a pas apporté un arbre remanié : il a défait la refonte.** 70170 r5 portait la refonte
  du Guerrier par 49 règles `correctif_serveur` (`/classes/Warrior/spells/<clé>`, poussée 112347, T08c). 70245 r1 a
  été décodée à 06:00 sans `DBCache.bin` de 70245 (aucune règle `correctif_serveur`) : les tables de wago portent
  l'arbre d'avant la refonte. Fury : Furious Precision, Gore Drinker, Lingering Rage retirés, Boundless Rage, Improved
  Cleave, Iron Will, Precision rendus ; Protection : Iron Will retiré, Toughness rendu ; Berserker Rage rang 1 niveau
  30 → 32. Le rapport `docs/research/data-1.60.1.70245-r1.md` n'en dit rien (`classes.json` n'y est pas résumé), et
  r1 a été approuvée.
- **r3 (70245 r2 → r3) est l'inverse exact de r1** : le `DBCache.bin` de 70245, archivé ensuite, rend la refonte. Le
  sous-arbre du Guerrier de la copie r3 est identique, hors métadonnées, à celui de 70170 r5, avec les mêmes 49
  règles `correctif_serveur`.
- Le sous-arbre du Guerrier de 70245 r2 est identique à celui de r1 (r2 n'a changé que `monsters.json`).
- Lacune relevée : les arbres (`/classes/Warrior/trees/…`) sont couverts par la règle `client` de `classes.json`
  (`**`), même quand la refonte vient des correctifs ; seules les fiches des sorts (`/classes/<classe>/spells/<clé>`)
  portent l'origine `correctif_serveur` (granularité de T08c). Voir Risques et DON17.

## Question décisive et réponse (2026-10-07)

Avec la règle telle qu'écrite (entrées `client` ou `correctif_serveur` → installation seule), r1 se serait installée
seule : sept heures de fiches PvP du Guerrier fausses. Réponse de l'utilisateur (option 3, avec un délai et l'option 1
en secours) :

1. **Une nouvelle version attend que le `DBCache.bin` de son build soit archivé et lu** (attente « correctifs à
   lire »), puis s'installe avec ses correctifs du serveur, en une seule fois.
2. **Délai de 24 h** : si aucun `DBCache.bin` de ce build n'est archivé 24 h après la première vue du build (jeu pas
   lancé), la version s'installe sans ses correctifs **seulement si aucune valeur d'origine `correctif_serveur` ne
   serait perdue** ; sinon elle reste en attente avec la raison « correctifs du serveur non relus ».
3. Tests : 70245 r1 sans `DBCache.bin` → attente ; même cas avec le `DBCache.bin` archivé → installation seule avec
   ses correctifs ; r3 → installation seule ; délai dépassé sans perte → installation seule ; délai dépassé avec perte
   → attente.
4. La section T08e de la ROADMAP est corrigée et la règle consignée dans `docs/DECISIONS.md` (décision 207).

## Choix proposés (sans question, à confirmer à la validation)

- **Mode des moteurs** : champ obligatoire `mode` de `EngineSpec`, valeurs `"calcule"` ou `"recopie"` (valeurs en
  français comme les statuts du module), sans valeur par défaut. `mage_build` et `mage_leveling` : `calcule` ;
  `pvp_dr` : `recopie`.
- **Origines permises pour l'installation seule d'un moteur qui recopie** : `client` et `correctif_serveur`
  seulement. `manuel`, `journal`, `addon`, `parametre`, `copie_figee` et **feuille sans règle** gardent l'attente
  (défaut sûr). Une feuille changée est jugée sur son origine **avant** (version installée) et **après** (copie de
  préparation, qui porte les règles `correctif_serveur` de la candidate) ; une feuille ajoutée sur l'après seul, une
  feuille retirée sur l'avant seul. Les deux origines doivent être permises.
- **Jugement par feuille, pas par fichier** (décision 198) : `pvp_rules.json` est lu par `pvp_dr`, mais tant que ses
  feuilles `manuel` ne changent pas, il ne retient rien.
- **Rejeu** : un moteur qui recopie n'a pas de cas de rejeu (`cases` vide, `cases_to_replay` ne le rend jamais) ; le
  cas `matchup-Mage-Warlock-20`, jamais rejoué automatiquement (« cas sans rejeu automatique »), est retiré.
  `verify --data --engines=pvp_dr` du clone reste le contrôle des fiches.
- **Perte d'un correctif** (point 2 de la réponse) : feuille d'un fichier de données de la version installée, couverte
  par une règle `correctif_serveur`, dont la valeur change ou disparaît dans la copie de préparation et dont
  l'origine après n'est pas `correctif_serveur`. Jugée sur **tous** les fichiers de la version (pas seulement les
  entrées des moteurs : une recherche `forever lookup` lit aussi ces valeurs).
- **Première vue du build** : date du build dans le journal des versions du client (`client_builds.load_builds`,
  inscrit par l'archivage à chaque passage) ; build absent du journal → l'horloge part du passage (attente). Délai :
  `UPDATE_HOTFIX_WAIT = timedelta(hours=24)` dans `forever/config.py` (réglage de l'outil, comme `CACHE_TTL`).
- **Attente « correctifs à lire »** : genre nouveau `hotfixes_unread`, identifiant `hotfixes-<version>`, sans
  téléchargement ni décodage (rien à juger tant que le jeu n'a pas tourné sur le build), **non approuvable** (elle se
  lève seule : lancer le jeu et se connecter au royaume, puis `forever update`) ; liste `SELF_CLEARING_KINDS` à côté de
  `SESSION_KINDS`, avec son texte dans `forever update status` et la ligne de démarrage.
- **Attente « correctifs du serveur non relus »** (délai dépassé, perte) : attente `install_version` ordinaire,
  **approuvable** (l'utilisateur peut choisir d'installer sans les correctifs), clause nouvelle `hotfixes` à faux.
- **Clause `hotfixes`** ajoutée au verdict : vraie sauf perte d'un correctif ; l'ensemble des clauses devient
  `{verify, install, manual, inputs, hotfixes}`.
- **Résumé des valeurs changées** : éléments de liste alignés par clé stable (`key`, sinon `spell_id`, `node_id`,
  `id`, sinon l'indice), jamais par indice seul : la refonte décale les talents dans les listes
  (`/trees/1/talents/10` passe d'Enrage à Improved Execute), un résumé par indice serait faux. Lignes « classe, entité,
  champ, avant, après » ; entités nommées par le nom du client (enUS), sinon la clé ; plafond de 50 lignes dans les
  JSON (attente, rapport de passage) avec « et N autres », tableau complet dans le rapport de recherche du clone.
- **Phrase courte** pour la ligne de démarrage et `forever update status` : par classe, talents ajoutés ou retirés,
  talents modifiés, sorts modifiés (ex. « fiches PvP : Warrior, 9 talents ajoutés ou retirés, 18 talents et 4 sorts
  modifiés »).
- **Attentes closes par un passage** : une attente ouverte dont l'identifiant est écrit par un passage passe à
  `faite` (aujourd'hui seulement si elle était approuvée : l'attente r3 resterait `en_attente` après une installation
  seule) ; une attente ouverte de la même version et du même genre, remplacée par une attente d'un autre identifiant,
  passe à `périmée` (à vérifier contre le code de T08d à l'étape rouge, ajouté seulement s'il manque).
- **Le garde-fou de la première écriture** (décision 184) ne change pas ; `verify` rouge et valeur `perdu` restent
  jamais approuvables. Registre des mécaniques **inchangé** (aucune mécanique de jeu touchée).

## Contexte du code (lecture du plan)

- `forever/engine_inputs.py` : `EngineSpec(name, files, pointers, cases)`, `ENGINES`, `compare_inputs(before, after)`
  rend `InputsDiff(engine, identical, items)` ; chaque item porte `file`, `pointer`, `status`, `before`, `after`
  (empreintes), `leaves` (nombre de feuilles changées) mais pas les feuilles elles-mêmes.
- `forever/update.py` : `decide(verify_ok, carry, inputs, kind, *, install_ok)` (pure, clause `inputs` = aucun
  moteur changé) ; `_evaluate` installe dans la copie de préparation, appelle `carry_check`, `compare_inputs`,
  `targeted_replay`, `decide`, puis `_publish` (rapport `_research_report`, `run.written`) ou une attente ;
  `_step_new_version` lit l'archive `DBCache.bin` du build si elle existe, sinon décode sans correctifs.
- `forever/origins.py` : la résolution de l'origine d'une feuille (`_Rule.specificity`, `_match_prefix`,
  `not_game_values`) vit dans `_Checker._check_file`, sans fonction publique.
- `forever/pipeline/value_diff.py` : type `Line` et lignes par fichier (`scaling_lines`, `character_lines`) pour
  `forever diff`.
- `forever/hooks.py` `update_line` : « mise à jour : <version> r<N> installée » d'après `last.json` (`written`).

## Blocs et étapes

### Étape 0 — Fixtures du cas réel (avant tout autre travail)

La copie de préparation `stage-1.60.1.70245` est éphémère (réécrite par chaque passage, perdue si r3 est installée) :
extraire d'abord, par un script hors du paquet (dans `$CLAUDE_JOB_DIR/tmp`), avec `write_bytes` et des fins de ligne
LF, dans `tests/fixtures/update_origins/` :

- `warrior-70170-r5.json` : `/classes/Warrior` de `git show 14495a5~1:forever/data/1.60.1.70170/classes.json` ;
- `warrior-70245-r1.json` : `/classes/Warrior` de `git show 14495a5:forever/data/1.60.1.70245/classes.json` (égal à
  r2, contrôlé à l'extraction) ;
- `warrior-70245-r3.json` : `/classes/Warrior` de la copie de préparation ;
- `hotfix-rules-70170-r5.json` et `hotfix-rules-70245-r3.json` : les règles `correctif_serveur` de `classes.json` des
  `origins.json` correspondants (49 chemins, poussée 112347) ;
- `README.md` : origine de chaque fichier (commit, chemin, date, empreinte sha256 du sous-arbre canonique), et le
  contrôle « r3 = 70170 r5 hors métadonnées ».

JSON compact (un sous-arbre fait environ 190 ko en indenté). Si r3 a été installée entre-temps (approbation de
l'attente `1.60.1.70245-r3-f10e27912f08`), source la plus probable : `classes.json` et `origins.json` de
`forever/data/1.60.1.70245/` au commit de r3, dans git. Sinon, copie de préparation disparue : la refaire par
`forever update --dry-run --only correctifs` (archive de 70245 présente, aucun réseau si les tables sont en cache) ;
sinon s'arrêter et le signaler.

Montage des cas dans les tests (sur le modèle de la fixture `pair` de `test_engine_inputs.py`) : copie de
`LOCAL_VERSION` en « avant » et « après », sous-arbre du Guerrier remplacé de chaque côté par la fixture, règles
`correctif_serveur` remplacées par celles de la fixture, `origins.json` réécrit en LF. Les deux côtés viennent des
fixtures : le test ne dépend pas du Guerrier de la version installée du moment.

### Bloc 0 — Feuille de route et décisions (fait avec le plan)

Commités sur `main` avec le plan, à la demande de l'utilisateur : décision **207** dans `docs/DECISIONS.md` (amende
180 et 198), section T08e de `docs/ROADMAP.md` corrigée (« Fait », hors périmètre, critères de fin), DON17 dans
`docs/OPEN_QUESTIONS.md`. Reste pour l'exécution : la ligne « Réalisé » de la section (bloc D).

### Bloc A — Déclaration des moteurs et origine de chaque feuille changée

- `EngineSpec.mode` obligatoire ; `ENGINE_MODES = ("calcule", "recopie")` ; `check_engines(engines)` lève
  `EngineDeclarationError` (sous-classe de `ForeverError`, message en français nommant le moteur) pour un mode absent
  ou inconnu ; appelée au chargement du module et par `decide` pour tout moteur nommé dans `inputs` absent de
  `ENGINES`.
- `forever/origins.py` : `OriginResolver` public, construit sur `origins.json` d'un dossier de version, qui réutilise
  `_Rule`, la spécificité, `_match_prefix` et `not_game_values` ; `origin(file, pointer) -> str | None` (`None` :
  feuille sans règle ; `NOT_A_VALUE` pour une feuille de `not_game_values`). `_Checker._check_file` passe par lui
  (une seule résolution).
- `compare_inputs` : chaque item « différent » porte `changes`, liste de `ValueChange(file, pointer, before, after,
  origin_before, origin_after)` (feuilles hors métadonnées, pointeur complet dans le fichier, `ABSENT` pour une
  feuille ajoutée ou retirée), et `origins` (compte par origine) ; les items identiques n'en portent pas.
- `hotfix_losses(before_dir, after_dir) -> list[ValueChange]` (perte d'un correctif, définition plus haut), dans
  `forever/engine_inputs.py`.

### Bloc B — Règle d'automatisme et résumé des valeurs

- `decide(…, hotfix_losses=())` : clause `inputs` vraie quand chaque moteur changé est en mode `recopie` et que
  toutes ses feuilles changées ont leurs origines permises ; clause `hotfixes` vraie sans perte. Raisons :
  « moteurs aux entrées changées : mage_build » (calcule) ; « pvp_dr : entrée d'origine manuel changée :
  pvp_rules.json /diminishing_returns/… (et N autres) » ; « correctifs du serveur non relus : N valeur(s)
  correctif_serveur perdue(s) (classes.json /classes/Warrior/spells/berserkerRage/ranks/0/level…) ». Un item
  « différent » sans `changes` (appel sans origines) garde l'attente. Le résumé n'entre jamais dans `reasons`
  (`reasons == []` ⇔ `écrire` reste vrai).
- `hotfix_gate(archived, seen_at, now, wait) -> str` (pure) : `"lire"` (archive présente), `"attendre"` (pas
  d'archive, délai non écoulé ou première vue inconnue), `"sans_correctifs"` (pas d'archive, délai écoulé).
- `forever/pipeline/value_diff.py` : `copied_lines(file, before_doc, after_doc, pointer) -> list[CopiedLine]`
  (classe, entité, champ, avant, après ; entités alignées par clé stable) et `copied_summary(lines) -> dict` (comptes
  par classe : talents ajoutés, retirés, modifiés, sorts ajoutés, retirés, modifiés, autres) ; `summary_sentence`.

### Bloc C — Chaîne, rapport, statut et ligne de démarrage

- `_step_new_version` : passe par `hotfix_gate` avant `_fetch_version` ; `"attendre"` → attente `hotfixes_unread`
  (aucune requête wago) ; `"sans_correctifs"` → décodage sans correctifs puis `_evaluate(…, hotfix_check=True)` qui
  calcule `hotfix_losses` ; `"lire"` → chemin actuel (correctifs de l'archive, `network_dbd` si dispositions
  manquantes).
- `_evaluate` : verdict enrichi de `values` (lignes plafonnées) et `summary` (comptes et phrase) pour chaque moteur
  changé ; mêmes champs dans l'entrée d'attente ; `targeted_replay` ignore les moteurs `recopie`.
- `_research_report` : section « Valeurs changées » (tableau complet classe, entité, champ, avant, après) et
  « Correctifs du serveur » (lus, ou non relus avec la liste des pertes).
- `_publish` : `info["summary"]` (phrase) ajouté à `run.written` ; attente ouverte du même identifiant → `faite`.
- `forever/hooks.py` `update_line` : « mise à jour : 1.60.1.70245 r3 installée seule (fiches PvP : Warrior, …) » ;
  attente `hotfixes_unread` : « 1.60.1.70245 : correctifs du serveur à lire (lancer le jeu sur ce build) » ; une
  seule ligne.
- `forever/cli.py` (`forever update status`, sortie texte de `forever update`) : phrase du résumé sous chaque attente
  et pour la dernière écriture ; genre `hotfixes_unread` sans commande `approve` ; `approve` d'une attente
  `hotfixes_unread` refusé avec un message (« se lève seule : lancer le jeu sur ce build, puis forever update »).
- `forever_status` (MCP, lecture seule) : rien de nouveau à écrire ; le résumé passe par `update_summary` s'il le
  rend déjà, sinon ajouté en lecture seule.

### Bloc D — Documentation et fin

- Docstrings de `forever/engine_inputs.py` et `forever/update.py` (« décision 180, amendée par 198 et 207 »),
  `docs/ARCHITECTURE.md` §5, `docs/USAGE.md` (paragraphe de `forever update`), section T08e de la ROADMAP
  (« Réalisé »). `/verifier`. Registre inchangé.
- Après la fusion, hors de la tranche (« Bloqué sur moi ») : un passage réel `uv run forever update` doit installer
  1.60.1.70245 r3 seule (règle nouvelle) et clore l'attente `1.60.1.70245-r3-f10e27912f08` (`faite`) ; à lancer ou
  approuver par l'utilisateur, jamais par la session sans accord.

## Fichiers

- Modifiés : `forever/engine_inputs.py`, `forever/origins.py`, `forever/update.py`, `forever/pipeline/value_diff.py`,
  `forever/hooks.py`, `forever/cli.py`, `forever/config.py`, `docs/DECISIONS.md`, `docs/ROADMAP.md`,
  `docs/OPEN_QUESTIONS.md`, `docs/ARCHITECTURE.md`, `docs/USAGE.md`.
- Tests modifiés : `tests/unit/test_engine_inputs.py`, `tests/unit/test_update_rule.py`,
  `tests/unit/test_update_chain.py`, `tests/unit/test_update_hook.py`, `tests/unit/test_update_publish.py`,
  `tests/unit/test_origins.py`.
- Tests ajoutés : `tests/unit/test_update_origins.py` (cas réels sur fixtures, porte, perte, résumé).
- Fixtures ajoutées : `tests/fixtures/update_origins/` (étape 0).
- Aucun fichier de `forever/data/` modifié ; aucune dépendance ; aucun accès réseau nouveau.

## Interfaces

```
# forever/engine_inputs.py
ENGINE_MODES = ("calcule", "recopie")
class EngineSpec(NamedTuple): name; files; pointers; cases; mode: str
class EngineDeclarationError(ForeverError)
def check_engines(engines: Mapping[str, EngineSpec]) -> None
class ValueChange(NamedTuple): file; pointer; before; after; origin_before: str | None; origin_after: str | None
ABSENT  # marqueur d'une feuille ajoutée ou retirée
def compare_inputs(before: Path, after: Path) -> dict[str, InputsDiff]   # items « différent » : changes, origins
def hotfix_losses(before: Path, after: Path) -> list[ValueChange]

# forever/origins.py
NOT_A_VALUE = "non_valeur"
class OriginResolver:
    @classmethod
    def load(cls, version_dir: Path) -> OriginResolver
    def origin(self, file: str, pointer: str) -> str | None

# forever/update.py
AUTO_ORIGINS = frozenset({"client", "correctif_serveur"})
SELF_CLEARING_KINDS = ("hotfixes_unread",)
def decide(verify_ok, carry, inputs, kind, *, install_ok=True, hotfix_losses=()) -> Verdict
def hotfix_gate(archived: bool, seen_at: datetime | None, now: datetime, wait: timedelta) -> str

# forever/pipeline/value_diff.py
class CopiedLine(NamedTuple): cls; entity; field; before; after
def copied_lines(file: str, before: Any, after: Any, pointer: str) -> list[CopiedLine]
def copied_summary(lines: Sequence[CopiedLine]) -> dict[str, dict[str, int]]
def summary_sentence(summary: Mapping[str, Mapping[str, int]], engine: str) -> str

# forever/config.py
UPDATE_HOTFIX_WAIT = timedelta(hours=24)
```

## Tests attendus

Aucune valeur de jeu affirmée hors des fixtures : les valeurs ci-dessous sont lues dans les fixtures extraites
(étape 0) et relevées pendant le plan ; l'étape rouge les recompte sur les fixtures avant de verrouiller.

`tests/unit/test_engine_inputs.py`
- `test_engines_declare_their_mode` : `{n: s.mode for n, s in ENGINES.items()} == {"mage_build": "calcule",
  "mage_leveling": "calcule", "pvp_dr": "recopie"}` ; `ENGINES["pvp_dr"].cases == ()` ; les moteurs `calcule` ont des
  cas.
- `test_an_engine_without_mode_cannot_be_built` : `EngineSpec` sans `mode` → `TypeError`.
- `test_an_unknown_mode_is_refused` : `check_engines` sur un moteur au mode `"autre"` → `EngineDeclarationError`.
- `test_changed_items_carry_their_leaves_and_origins` (cas r3) : seul l'item `classes.json` `/classes/Warrior` de
  `pvp_dr` est différent ; `len(changes) == 297` ; origines ⊂ `{client, correctif_serveur}` ;
  `("/classes/Warrior/spells/berserkerRage/ranks/0/level", 32, 30)` présent, origines `client` → `correctif_serveur`.
- `test_targeted_replay_skips_copying_engines` : un changement de `classes.json` seul ne rejoue rien.
- Les tests existants qui comptent sur `ENGINES["pvp_dr"].cases` sont mis à jour au commit des tests.

`tests/unit/test_origins.py`
- `test_resolver_matches_the_checker` : sur `LOCAL_VERSION`, les comptes par origine du résolveur sur toutes les
  feuilles égalent `check_version(...).by_origin`.
- `test_resolver_examples` (fixture r3 montée) : `berserkerRage/ranks/0/level` → `correctif_serveur` ;
  `/classes/Warrior/trees/1/talents/0/name` → `client` ; `pvp_rules.json` `/diminishing_returns` (première feuille)
  → `manuel` ; `revisions.json` → `NOT_A_VALUE` ; feuille inventée sans règle → `None`.

`tests/unit/test_update_rule.py` (table de la règle ; clauses `{verify, install, manual, inputs, hotfixes}`)
- Lignes ajoutées, `pvp_dr` changé : feuilles `client` seules → `écrire` ; `correctif_serveur` seules → `écrire` ;
  `client` → `correctif_serveur` → `écrire` ; une feuille `manuel` (`pvp_rules.json`) → `attente` {inputs}, raison qui
  nomme `pvp_rules.json`, le pointeur et `manuel` ; une feuille `journal`, `addon`, `parametre`, `copie_figee` ou
  sans règle (paramétré) → `attente` {inputs} ; item différent sans `changes` → `attente` {inputs}.
- `mage_build` changé par des feuilles `client` seules → `attente` {inputs}, raison « moteurs aux entrées changées :
  mage_build » ; `pvp_dr` client et `mage_build` changés → `attente`, raison qui nomme `mage_build` et pas `pvp_dr`.
- Perte d'un correctif → `attente` {hotfixes}, raison « correctifs du serveur non relus » ; perte et `verify` rouge →
  `bloqué`.
- Moteur absent de `ENGINES` dans `inputs` → `EngineDeclarationError`.
- Lignes existantes inchangées sur l'action ; leur ensemble de clauses passe à cinq.

`tests/unit/test_update_origins.py` (cas réels sur fixtures, réponse 3)
- `test_gate_table` (paramétré, délai 24 h) : archive → `lire` ; pas d'archive, vu il y a 1 h → `attendre` ; 23 h 59
  → `attendre` ; 24 h → `sans_correctifs` ; première vue inconnue → `attendre`.
- `test_70245_r1_without_dbcache_waits` : build vu à 2026-10-07T00:35:33Z (journal des versions du client, source
  `.build.info`), passage de r1 à 06:00:14Z, pas d'archive → `attendre` (5 h 25 min < 24 h).
- `test_70245_r1_after_the_delay_waits_on_lost_hotfixes` : avant = 70170 r5 (Warrior et 49 règles), après = r1 →
  `hotfix_losses` non vide, contient `classes.json` `/classes/Warrior/spells/berserkerRage/ranks/0/level` 30 → 32 ;
  `decide` → `attente`, clauses fausses {hotfixes} seulement (`inputs` vraie : origines `client`/`correctif_serveur`).
- `test_70245_r1_with_its_dbcache_installs_alone` : avant = 70170 r5, après = r3 (même sous-arbre et mêmes règles) →
  `pvp_dr` identique, aucune perte, `écrire`.
- `test_70245_r3_installs_alone_with_a_summary` : avant = r1 (= r2), après = r3 → `écrire` ; résumé du Warrior :
  4 talents ajoutés (Fury : Furious Precision, Gore Drinker, Lingering Rage ; Protection : Iron Will), 5 retirés
  (Fury : Boundless Rage, Improved Cleave, Iron Will, Precision ; Protection : Toughness), 18 talents modifiés,
  4 sorts modifiés (Berserker Rage, Improved Cleave, Iron Will, Toughness), 1 autre (`tree_checks`) ; ligne
  `("Warrior", "sort Berserker Rage", "rang 1 niveau", 32, 30)` (forme exacte du champ fixée à l'étape rouge) ;
  aucune ligne ne nomme un indice de liste de talents.
- `test_after_the_delay_without_loss_installs_alone` : montage r3 → r3 avec une feuille `client` du Guerrier hors des
  49 chemins changée (`/classes/Warrior/trees/0/talents/0/max`), aucune règle `correctif_serveur` touchée →
  `hotfix_losses == []`, `écrire`.
- `test_summary_is_capped` : plus de 50 lignes → 50 lignes et « et N autres ».

`tests/unit/test_update_chain.py` (montage existant, version fictive `1.60.1.79999`)
- Le montage inscrit le build cible au journal des versions avec une première vue à `NOW - 25 h` (sans archive :
  porte `sans_correctifs`, aucune perte) : les tests existants gardent leur sens ; leurs ensembles de clauses passent
  à cinq.
- `test_a_new_version_waits_for_its_hotfixes` : première vue à `NOW - 1 h`, pas d'archive → étape `nouvelle_version`
  `attente`, une attente `hotfixes_unread` non approuvable (`commands` sans `approve`), aucune requête de table wago
  (`FakeHttp`), code 6.
- `test_an_archived_dbcache_is_read` : `DBCache.bin` de la fixture placé dans l'archive du build cible → la porte rend
  `lire` (attente `network_dbd` sans dispositions, ou installation avec correctifs si les dispositions de la fixture
  `tests/fixtures/dbd/` sont servies : choix par sonde à l'étape rouge).
- `test_a_warrior_value_changed_by_the_client_writes_alone` : une colonne d'un sort du Guerrier perturbée dans les
  CSV (`perturb`, sort et colonne choisis par sonde : passe l'installation, ne touche que `pvp_dr`) → `écrire` ;
  `verdict["summary"]["pvp_dr"]` nomme `Warrior` ; `verdict["values"]` non vide ; aucun rejeu.
- `test_a_mage_value_changed_by_the_client_waits_with_a_targeted_replay` : inchangé sur le fond.

`tests/unit/test_update_publish.py`
- Rapport de recherche : sections « Valeurs changées » (lignes classe, entité, champ, avant, après) et « Correctifs
  du serveur » ; `run.written[-1]["summary"]` présent ; attente ouverte du même identifiant passée à `faite` après une
  écriture par la règle.

`tests/unit/test_update_hook.py`
- `test_line_names_an_install_alone_with_its_summary` : `last.json` avec une écriture et son résumé → « installée
  seule » et la phrase ; `test_line_names_the_hotfixes_to_read` ; `test_session_start_stays_on_one_line` tenu.

## Hors périmètre

- Toute autre règle de T08d ; outil MCP qui écrit ou approuve ; rejeu des fiches PvP par des cas.
- Granularité des origines des arbres (`/classes/<classe>/trees/…` déclarés `client` même quand la refonte vient des
  correctifs) : question DON17, à trancher dans une tranche de données ; T08e s'appuie sur les fiches des sorts, que
  la refonte touche toujours.
- Moteurs de classe à venir : ils déclareront leur mode à leur tranche (garde de complétude).
- Installation de 70245 r3 dans le dépôt : après la fusion, par un passage réel, avec l'utilisateur.

## Risques

- **Copie de préparation perdue** avant l'étape 0 (un passage du démarrage la réécrit, ou l'installe) : l'étape 0 se
  fait en premier ; reconstruction possible hors ligne (voir étape 0).
- **Perte non vue** : une refonte qui ne toucherait que les arbres, sans fiche de sort, ne laisserait aucune feuille
  `correctif_serveur` perdue (DON17). Effet : une version sans ses correctifs s'installerait seule après 24 h. Sens :
  installation trop permissive, bornée par le délai (le jeu lancé une fois sur le build lève le risque).
- **Archive précoce** : un `DBCache.bin` archivé avant la connexion au royaume peut porter peu de correctifs ; la
  version s'installerait sans une partie d'entre eux, puis `correctifs` les ajouterait en révision suivante (chemin
  existant). Noté dans la décision 207, sans règle de plus.
- **Montage de la chaîne** : la porte change le chemin de tous les tests de nouvelle version ; inscrire la première vue
  dans le montage dès le commit des tests, sinon chaque test attendrait les correctifs.
- **Ordre des clés et listes** : l'alignement par clé suppose des clés uniques par arbre ; une clé dupliquée retombe
  sur l'indice, signalée dans la ligne (« position »).

## Angles morts attendus (à chiffrer en fin de tranche)

- Origine des arbres de talents (DON17) : effet sur la seule perte d'un correctif, voir Risques.
- Fiches PvP dont une règle écrite à la main (`pvp_rules.json` `/categories`) dépend d'une valeur du client changée :
  la fiche change sans que la règle change ; installation seule voulue (décision 198).

## Questions ouvertes à ajouter

- **DON17 — Faut-il déclarer `correctif_serveur` les arbres de talents (`/classes/<classe>/trees/…`) reconstruits
  depuis des tables `Trait*` corrigées par le serveur ?** Aujourd'hui seules les fiches des sorts portent cette
  origine ; la perte d'un correctif (décision 207) ne voit donc pas un correctif qui ne toucherait que les arbres.

## Critères de fin

- Tests par table de la règle (entrée `client` ou `correctif_serveur` seule d'un moteur qui recopie → écriture ;
  entrée `manuel` du même moteur → attente ; entrée d'un moteur qui calcule → attente ; moteur sans déclaration →
  erreur ; perte d'un correctif → attente).
- Cas réels sur fixtures : 70245 r1 sans `DBCache.bin` → attente ; avec son `DBCache.bin` → installation seule avec
  ses correctifs ; r3 → installation seule, avec son résumé ; délai dépassé sans perte → installation seule ; délai
  dépassé avec perte → attente.
- Résumé des valeurs changées dans le rapport et la ligne de démarrage (fixtures) ; attente `hotfixes_unread` visible
  et non approuvable.
- Décision 207, ROADMAP T08e, DON17, ARCHITECTURE et USAGE à jour ; registre inchangé ; `uv run tasks.py verify`
  vert ; CI verte sous Ubuntu et Windows.

## Validation

Plan à valider par l'utilisateur avant l'exécution (nouvelle session, `/tranche T08e`).
