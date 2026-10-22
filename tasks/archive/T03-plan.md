# T03 — Pipeline de données : plan

> Plan rédigé le 2026-09-27 (session de cadrage en arrière-plan, sans échange avec l'utilisateur). Les décisions 1 à 5 sont **à valider** avant l'exécution (`/tranche T03` dans une nouvelle session). Les recommandations sont indiquées ; une réponse différente modifie les sections concernées.

## Contexte
T01 a livré les données versionnées, le manifeste, `status` et le client HTTP injecté (`forever/pipeline/builds.py`, `http_client.py`). T02 a livré le moteur et `GameData`. Les données de la version 1.60.1.70009 ne viennent pas des tables du client : `talents.json` est l'arbre wowsims de gunba (49 talents lus sur le build 69893, 5 corrigés au build 70009, voir `seed/forever-mage/scripts/_build_data_70009.py`) et `spells.json` a été relevé sur wowforevertalents.com. T03 construit la chaîne qui lit le client lui-même (tables DB2 publiées par wago.tools) : `builds` → `fetch` → `decode` → `diff` → `verify` → `report`. Ce que T08 automatisera (veille, PR de données) s'appuiera sur ces six commandes.

Trois constats orientent le plan :
- **Aucune fixture CSV n'existe** dans le dépôt. Les tests doivent rester hors ligne, mais leurs entrées (extraits des tables 70009) ne peuvent venir que d'un accès réseau ponctuel, fait hors des tests.
- **Les noms de colonnes des tables et la forme exacte des infobulles ne sont pas connus aujourd'hui.** Les interfaces ci-dessous parlent en champs logiques ; l'étape 0 fixe les colonnes réelles sur les fixtures.
- **Le critère « 54 talents, rangs identiques » compare le client 70009 à des rangs lus sur 69893.** Un écart peut être un bogue du décodeur ou un vrai changement du client : on ne peut pas le savoir d'avance (voir la décision 2 et les risques).

## Décisions à valider
| # | Décision | Recommandation | Alternative écartée |
| --- | --- | --- | --- |
| 1 | Collecte des fixtures (accès réseau hors tests) | Une collecte ponctuelle des tables du build 1.60.1.70009 sur wago.tools avec `uv run forever fetch` (codé et testé d'abord contre un faux client HTTP). L'utilisateur la lance (`! uv run forever fetch --version 1.60.1.70009`) ou autorise la session à le faire. Un script hors ligne (`scripts/extract_wago_fixtures.py`) filtre ensuite les CSV du cache pour ne garder que les lignes du Mage, plus quelques lignes leurres, dans `tests/fixtures/wago/1.60.1.70009/` (quelques centaines de Ko au plus). | Fixtures synthétiques fabriquées depuis `talents.json` (test circulaire, ne prouve rien sur le client) ; tables complètes en fixtures (plusieurs Mo) |
| 2 | Sens de « rangs identiques » et règle d'arrêt | Égalité champ par champ avec `talents.json` sur `key`, `name`, `tree`, `tier`, `col`, `max`, `ranks`, `prereq`, et même ordre (arbre, puis palier, puis colonne). Sont exclus, parce que le client ne les fournit pas : `desc` (`{0}` chez wowsims, `$s1` dans le client), `wowsims_not_simulated`, `certainty` (recalculée), `spellIds` (comparés à part, voir les tests), `notes`. `key` est dérivée du nom anglais en camelCase (vérifié : les 54 clés actuelles suivent cette règle). **Si le décodage diffère de `talents.json` : ne jamais ajuster le décodeur pour coller, s'arrêter et rapporter l'écart** (c'est une règle de jeu à trancher). Les 5 talents FC-70009 (Pyroblast, Blast Wave, Arcane Blast, Ice Lance, Ice Barrier) servent d'oracle fiable et passent en premier. Même règle pour les sorts : `decode` reproduit les 99 rangs des 15 sorts de `spells.json` (champs de `rank_format`), un `null` de référence (coût non publié) n'étant pas un écart mais une valeur relevée, listée dans le rapport. | Égalité de structure seule (tier, col, max, prereq) sans les valeurs des rangs ; liste d'écarts tolérés dans le test (affaiblit le critère sans décision) |
| 3 | Où vivent les constantes de décodage | Nouveau fichier `forever/data/1.60.1.70009/decode_rules.json`, haché comme les autres et hérité par la version suivante : géométrie des arbres (onglets PosX, rangée de base, pas des rangées et des colonnes, correction des positions à zéro en trop ; valeurs de `docs/DATA_SOURCES.md`), lignes de compétence du Mage, noms anglais des 15 sorts suivis, liste des tables à télécharger, règle « nœuds qui partagent un sort : le plus récent gagne ». C'est un ajout au dossier d'une version passée, comme `mechanics.json` en T02 ; `sources.json` et le manifeste sont régénérés. | Constantes Python dans `forever/pipeline/` (viole l'invariant « aucun chiffre hors de `forever/data/` ») ; sous-dossier `forever/data/pipeline/` (ignoré par `version_dirs`, donc non haché) |
| 4 | Sortie de `decode` | `decode` produit une **version candidate** hors de `forever/data/` : `<cache>/candidates/<version>/` est un dossier de données complet (`manifest.json` + `<version>/`) qui contient `talents.json` et `spells.json` décodés, les fichiers non dérivables du client (`racials.json`, `leveling.json`, `mechanics.json`, `respec.json`, `overrides.json`, `meta.json`, `decode_rules.json`) hérités de la version locale la plus récente avec un champ `inherited_from`, et un `sources.json` généré. T03 n'écrit jamais dans `forever/data/` ; l'installation d'une version (copie + `forever manifest --update` + PR) revient à T08. `diff`, `verify` et `report` acceptent un identifiant de version (données du dépôt) ou le chemin d'une version candidate. | Écrire directement `forever/data/<version>/` (risque d'écraser 70009, contraire à l'immuabilité, et ce serait déjà la veille de T08) ; ne produire que `talents.json` et `spells.json` isolés (`diff` et `verify` devraient alors gérer un format à part) |
| 5 | Outil MCP `forever_diff_versions` | Reporté en T08 : la feuille de route de T03 ne le demande pas, et T08 en fixera la forme (impact par personnage). La fonction `diff_versions` est écrite pour qu'il n'ait qu'à l'envelopper. | L'ajouter en T03 (outil de plus, tests de contrat et d'intégration MCP en plus, sans usage avant T08) |

Décisions techniques (sans arbitrage attendu) :
- **Réseau** : `builds` et `fetch` passent par `Deps.http_get` (aucun nouvel `urlopen`, `test_network_boundary.py` inchangé). Délai propre aux CSV : `FETCH_TIMEOUT = 30.0` dans `forever/config.py` (constante d'outil, pas de jeu) ; `HTTP_TIMEOUT = 2.0` reste celui de `status`. `FOREVER_OFFLINE=1` ou `--offline` fait échouer `builds` et `fetch` avec l'erreur `offline`. `decode`, `diff`, `verify` et `report` ne touchent jamais au réseau (test avec un `http_get` qui lève).
- **Nouveau code de sortie** `EXIT_NETWORK = 5` pour `builds_unavailable`, `fetch_failed` et `offline`. `BuildsUnavailable` garde son code dans `status` (qui ne fait pas échouer la commande) ; seule la commande `builds` le transforme en code 5.
- **Cache des CSV** : `<cache>/wago/<version>/<locale>/<Table>.csv` et un index `<cache>/wago/<version>/fetch.json` (URL, sha256, taille, date de collecte par table). Un fichier déjà présent et conforme à son empreinte n'est pas retéléchargé ; `--refresh` force. Une réponse qui n'a pas d'en-tête CSV attendu (page HTML, JSON d'erreur) est refusée (`fetch_failed`) et rien n'est écrit. Le cache vit hors de `forever/data/` (`FOREVER_CACHE_DIR`, `cache/` déjà ignoré par git).
- **Locale** : le français s'obtient par un second téléchargement des tables de noms (`SpellName`, et la table des noms de talents si elle diffère) en `frFR`. La forme de l'URL wago pour une locale **n'est pas vérifiée** dans le dépôt : à confirmer à l'étape 0 (voir « Bloqué sur moi »). Le décodage ajoute `name_fr` aux talents et `name` / `name_fr` aux sorts ; `gamedata.py` ignore déjà les champs qu'il ne lit pas.
- **Lecture des CSV** : module `csv` de la bibliothèque standard (aucune dépendance, décision 16). Chaque table a un schéma déclaré (colonnes utilisées et type) dans `forever/pipeline/tables.py` ; colonne manquante ou valeur mal typée → `DataSchemaError` (`data_schema`, code 3) qui nomme la table, la colonne et la ligne. Les noms de colonnes sont des noms de format de fichier, pas des chiffres de jeu.
- **Valeurs des rangs de talent** : variables de l'infobulle du sort de chaque rang, dans leur ordre d'apparition, évaluées sur `SpellEffect` et les tables de durée (y compris les expressions `${…}` et leur arrondi `.N` si le client les emploie). C'est ce que produisent les `{0}`, `{1}` de wowsims (`[0.1]` pour Improved Frostbolt = une durée en ms divisée et changée de signe par l'infobulle). L'évaluateur est une fonction pure testée à part ; l'inventaire des motifs réellement présents se fait à l'étape 0, avant d'écrire le décodeur.
- **Certitude** : ce qui est décodé du client pour la version annoncée est `certain` (FC) ; les fichiers et champs hérités gardent leur certitude d'origine, avec une note « hérité de <version> » dans `sources.json`. Aucun `overrides.json` n'est appliqué en T03 (celui de 70009 est vide ; l'application des corrections manuelles viendra avec l'installation d'une version en T08).
- **`forever verify`** (à ne pas confondre avec `uv run tasks.py verify`) : sur une version du dépôt ou une candidate, contrôle d'intégrité (manifeste), schéma (`build_game_data`), puis cohérence générique sans chiffre de jeu : `len(ranks) == max` pour chaque talent, prérequis existant dans le même arbre à un palier inférieur, position (arbre, palier, colonne) unique, rangs de sort de longueur `len(rank_format)` et de niveau croissant, chaque fichier décrit dans `sources.json` avec une certitude valide. Les champs hérités deviennent des hypothèses de la provenance. Erreurs → code 3.
- **`diff`** exige l'intégrité des deux côtés (même règle que les consultations, décision 20).

## Existant réutilisé
- `forever/pipeline/builds.py` : `fetch_builds`, `parse_builds`, `latest_build`, `version_key`, `BuildsUnavailable` ; fixtures `tests/fixtures/wago/builds_*.json` (dont `builds_real_sample.json`).
- `forever/config.py` : `Deps` (`http_get`, `cache_dir`, `offline`, `now`), `USER_AGENT`.
- `forever/manifest.py` : `compute_manifest`, `write_manifest`, `verify`, `version_dirs`, `VERSION_DIR_RE` ; `forever/store.py` : `ensure_integrity`, `current_identity`, `VersionData`.
- `forever/gamedata.py::build_game_data` : contrôle de schéma d'une version (réutilisé par `verify`).
- `forever/provenance.py`, `forever/errors.py`, `forever/cli.py::_emit` / `_emit_error`.
- `seed/forever-mage/scripts/update_data.py` : forme de `diff` (champs `tier`, `col`, `max`, `ranks`, `prereq`), marqueur `inherited_from`, principe « jamais de remplacement sans trace ». `_build_data_70009.py` : conversion `rowIdx + 1`, `colIdx + 1`, format positionnel des rangs de sort.
- `tests/conftest.py` : `make_deps`, `data_copy`, `DATA_DIR` ; piège du skill : après modification d'une copie, `write_manifest(data_copy)`.

## Fichiers
```
forever/pipeline/builds.py      + list_builds(deps, product, prefix) -> list[Build] (tri par created_at décroissant)
forever/pipeline/fetch.py       fetch_tables, table_url, FetchIndex ; cache et empreintes
forever/pipeline/tables.py      schémas déclarés des tables, read_table(path, schema) -> list[Row]
forever/pipeline/tooltip.py     évaluation des variables d'infobulle (fonction pure)
forever/pipeline/decode.py      decode_talents, decode_spells, decode_version -> Candidate
forever/pipeline/diff.py        diff_versions(a, b) -> VersionDiff
forever/pipeline/verify.py      verify_version(source) -> VerifyReport
forever/pipeline/report.py      render_report(diff, verify) -> str (Markdown)
forever/pipeline/sources.py     résolution « identifiant de version ou chemin de candidate » -> dossier de données
forever/config.py               + FETCH_TIMEOUT
forever/errors.py               + EXIT_NETWORK, OfflineError (offline), FetchFailedError (fetch_failed),
                                  UnknownVersionError (unknown_version, code 4)
forever/cli.py                  + builds, fetch, decode, diff, verify, report
forever/data/1.60.1.70009/decode_rules.json   (rédigé) ; sources.json : bloc decode_rules.json ; manifest.json régénéré
scripts/extract_wago_fixtures.py   filtre hors ligne des CSV du cache vers tests/fixtures/wago/<version>/
tests/fixtures/wago/1.60.1.70009/*.csv   extraits filtrés (étape 0), avec README.md (date, URL, filtre)
tests/fixtures/wago/fetch/*.csv          réponses simulées (CSV minimal, page HTML d'erreur)
tests/unit/test_fetch.py, test_tables.py, test_tooltip.py, test_decode_talents.py, test_decode_spells.py,
tests/unit/test_decode_version.py, test_diff.py, test_verify_version.py, test_report.py, test_pipeline_cli.py
tests/unit/test_builds.py (+ list_builds, commande builds)
Tests T01/T02 modifiés : test_contract.py (+ 6 commandes), test_manifest.py (10 → 11 fichiers),
                         test_data_import.py (+ decode_rules.json), test_network_boundary.py (commandes hors ligne)
docs/ARCHITECTURE.md (§ fraîcheur point 4, pipeline, version candidate), docs/DATA_SOURCES.md (colonnes, URL de locale),
docs/DECISIONS.md (34 et suivantes), docs/OPEN_QUESTIONS.md, docs/ROADMAP.md (T03 : critères précisés ; T08 : forever_diff_versions)
.claude/settings.json : patch hors dépôt (autoriser `uv run forever decode:*` et `uv run forever report:*`), appliqué par l'utilisateur
```
Aucune entrée de `docs/MECHANICS_REGISTRY.yaml` n'est touchée : T03 ne modélise aucune mécanique (couverture inchangée, 21/101).

## Interfaces

### Versions publiées et téléchargement
```python
def list_builds(deps: Deps, product: str, prefix: str) -> list[Build]
    # réseau ; lève OfflineError, BuildsUnavailable ; tri par created_at décroissant

class TableFetch(TypedDict):
    table: str; locale: str; url: str; sha256: str; bytes: int; fetched_at: str; from_cache: bool

def table_url(table: str, version: str, locale: str | None) -> str
    # https://wago.tools/db2/<Table>/csv?build=<version> (+ paramètre de locale confirmé à l'étape 0)
def fetch_tables(deps: Deps, version: str, tables: Sequence[str], *, locales: Sequence[str] = ("enUS",),
                 refresh: bool = False) -> list[TableFetch]
    # écrit <cache>/wago/<version>/<locale>/<Table>.csv et fetch.json ; lève OfflineError, FetchFailedError,
    # InvalidArgumentError (version mal formée)
```

### Tables et infobulles
```python
class Column(NamedTuple): name: str; kind: type[int] | type[float] | type[str]
TABLES: Mapping[str, tuple[Column, ...]]       # colonnes réelles fixées à l'étape 0
Row = Mapping[str, int | float | str]
def read_table(path: Path, table: str) -> list[Row]     # DataSchemaError si colonne absente ou mal typée
def tooltip_values(template: str, effects: SpellEffects, durations: Mapping[int, float]) -> list[float | int]
    # variables dans l'ordre d'apparition ; ValueError sur une variable inconnue (le décodeur la signale)
```

### Décodage
```python
class DecodeRules(TypedDict):          # decode_rules.json (valeurs dans les données, jamais dans le code)
    tables: list[str]; locales: list[str]
    talent_geometry: TalentGeometry     # onglets PosX -> arbre, rangée de base, pas des rangées et colonnes, correction
    skill_lines: list[int]              # lignes de compétence du Mage (relevées à l'étape 0)
    spells: dict[str, str]              # clé de spells.json -> nom anglais du sort
    rank_format: list[str]              # celui de spells.json

class DecodedTalent(TypedDict):        # même forme que talents.json + name_fr, certainty "FC-<version>"
class Candidate(NamedTuple):
    root: Path                          # dossier de données : manifest.json + <version>/
    version: str
    talents: int; spells: int; spell_ranks: int
    observations: list[str]             # valeurs relevées là où la référence avait null, nœuds écartés, etc.

def decode_talents(tables: Mapping[str, Sequence[Row]], rules: DecodeRules, version: str) -> dict[str, object]
def decode_spells(tables: Mapping[str, Sequence[Row]], rules: DecodeRules, inherited: Mapping[str, object],
                  version: str) -> dict[str, object]
    # rangs décodés (rank_format) + name / name_fr ; autres champs (range, slow, talent, projectile_speed…) hérités
def decode_version(deps: Deps, version: str, *, csv_dir: Path | None = None, out: Path | None = None) -> Candidate
    # csv_dir : dossier de CSV (fixtures en test), sinon le cache de fetch ; out : sinon <cache>/candidates/<version>/
    # règles lues dans decode_rules.json de la version locale la plus récente ; refuse d'écraser une candidate
    # existante sans --force ; write_manifest(root) en fin de décodage
```

### Comparaison, vérification, rapport
```python
class Change(TypedDict):
    kind: Literal["talent", "spell", "file"]
    key: str
    change: Literal["added", "removed", "modified"]
    field: str | None                   # "ranks", "max", "tier", "col", "prereq", "ranks[3].mana"…
    old: object; new: object

class VersionDiff(TypedDict):
    a: str; b: str; changes: list[Change]; counts: dict[str, int]; provenance: Provenance

def diff_versions(deps: Deps, a: str, b: str) -> VersionDiff        # a, b : version du dépôt ou chemin de candidate
class VerifyReport(TypedDict):
    version: str; ok: bool; errors: list[str]; warnings: list[str]; inherited: list[str]; provenance: Provenance
def verify_version(deps: Deps, source: str) -> VerifyReport
def render_report(diff: VersionDiff, verify: VerifyReport | None) -> str
    # Markdown : titre « data: A → B », résumé chiffré, sections Talents / Sorts / Fichiers (tableaux),
    # hypothèses, ligne de provenance ; déterministe à horloge fixe
```

### CLI (texte français, `--json`, provenance sur chaque sortie)
| Commande | Réseau | Codes |
| --- | --- | --- |
| `forever builds [--limit N] [--json]` | oui | 0 ; 5 (`offline`, `builds_unavailable`) |
| `forever fetch --version X [--tables T,…] [--locale L] [--refresh] [--json]` | oui | 0 ; 2 (version mal formée) ; 5 |
| `forever decode --version X [--csv-dir D] [--out D] [--force] [--json]` | non | 0 ; 3 (`data_schema`) ; 4 (CSV absents : action « lancer forever fetch ») |
| `forever diff A B [--json]` | non | 0 ; 3 ; 4 (`unknown_version`) |
| `forever verify [VERSION\|CHEMIN] [--json]` | non | 0 ; 3 |
| `forever report A B [--out FICHIER] [--json]` | non | 0 ; 3 ; 4 |
`builds` marque la version locale et la dernière publiée ; `diff` en texte affiche une ligne par changement (`~ Improved Frostbolt : ranks … -> …`, `+ sort ajouté : …`) puis un total.

## Tests à écrire d'abord (phase rouge)
Valeurs de référence : `forever/data/1.60.1.70009/talents.json` et `spells.json` du dépôt (cités dans chaque test), ou les fixtures de l'étape 0 pour les valeurs propres au client (noms français, identifiants). Aucune valeur de CSV n'est inventée dans ce plan. Aucun réseau (faux `http_get`).

| Fichier | Tests et valeurs attendues |
| --- | --- |
| `tests/unit/test_builds.py` (ajouts) | `list_builds` sur `builds_mixed_dates.json` : ordre par `created_at` décroissant, filtre du produit et du préfixe ; `offline` → `OfflineError` sans appel à `http_get` ; commande `builds` : code 0, version locale marquée ; réseau en échec → code 5, `builds_unavailable` |
| `tests/unit/test_fetch.py` | URL construite (`table_url("SpellName", "1.60.1.70009", None)`) ; écriture du CSV et de `fetch.json` avec le sha256 du corps simulé ; second appel servi depuis le cache (`from_cache`, aucun appel HTTP) ; `refresh=True` retélécharge ; empreinte du cache altérée → retéléchargement ; réponse HTML → `fetch_failed`, rien d'écrit ; `OSError` → `fetch_failed` ; `offline` → aucun appel ; version `1.60.x` → `invalid_argument` ; délai transmis = `FETCH_TIMEOUT` |
| `tests/unit/test_tables.py` | lecture typée d'une fixture ; colonne manquante → `data_schema` qui nomme la table et la colonne ; entier mal formé → `data_schema` avec le numéro de ligne ; guillemets et virgules dans un texte (`SpellName` français) |
| `tests/unit/test_tooltip.py` | variables simples (`$s1`, `$d`), expressions `${…}` avec arrondi, ordre d'apparition, variable inconnue → `ValueError` ; cas tirés des infobulles réelles des fixtures (Improved Frostbolt → `0.1` au rang 1, Wand Specialization → `13` puis `25`, valeurs de `talents.json`) |
| `tests/unit/test_decode_talents.py` | **critère 2** : `decode_talents(fixtures)` → 54 talents, 18 Arcane, 17 Fire, 19 Frost ; pour chaque talent (paramétré par clé), égalité avec `talents.json` sur `key`, `name`, `tree`, `tier`, `col`, `max`, `ranks`, `prereq` ; même ordre que `talents.json` ; les 5 oracles FC-70009 d'abord : `iceLance` `[[26, 30, 300]]`, `pyroblast` `[[95, 125, 44, 12]]`, `arcaneBlast` `[[50, 58, 10, 175, 4, 8]]`, `blastWave` `[[148, 178, 50, 6]]`, `iceBarrier` `[[431, 1]]` ; 6 prérequis (arcaneMeditation ← arcaneConcentration, arcanePower ← presenceOfMind, hotStreak ← pyroblast, combustion ← criticalMass, fingersOfFrost ← iceLance, iceBarrier ← coldSnap) ; `coldSnap` → `[[]]` ; `name_fr` non vide pour les 54 (valeurs de la fixture `SpellName` frFR) ; `spellIds` égaux à `talents.json` là où ceux-ci ne contiennent pas `0` (arcaneResilience, incineration, burningSoul, elementalPrecision : comparés hors des `0`, écart rapporté en observation) ; nœud leurre d'une autre classe ignoré ; deux nœuds partageant un sort (wakeOfFire et flameThrowing partagent 11078 et 11080 dans `talents.json`) : règle « le plus récent » appliquée ; position avec un zéro en trop corrigée |
| `tests/unit/test_decode_spells.py` | 15 sorts, 99 rangs ; `frostbolt` 11 rangs, rang 2 `[8, 34, 38, 0, 0, 1.8, 35, 0]` ; `fireball` rang 3 `[12, 48, 66, 6, 6, 2.5, 65, 0]`, 12 rangs dont deux au niveau 60 ; pour chaque sort et chaque rang, égalité avec `spells.json` sur les champs de `rank_format` ; un `null` de référence (`pyroblast` r1, `ice_lance` r1, `blast_wave` r1, `arcane_blast`) n'est pas un écart : la valeur décodée figure dans `observations` ; sort leurre de PNJ de même nom (« Frostbolt » hors ligne de compétence) exclu ; champs non décodés (`range`, `slow`, `projectile_speed`, `talent`…) hérités à l'identique ; `name_fr` non vide |
| `tests/unit/test_decode_version.py` | `decode_version(deps, "1.60.1.70009", csv_dir=fixtures, out=tmp)` : candidate complète (`manifest.json` valide, 10 fichiers : ceux de la décision 4, sans `_source_gunba_mage_tree.json`, trace wowsims propre à 70009), `inherited_from == "1.60.1.70009"` dans les fichiers hérités, `sources.json` couvre chaque fichier, certitude `certain` pour `talents.json` décodé ; `build_game_data` accepte la candidate ; `forever/data/` inchangé (empreinte du dépôt identique avant et après) ; candidate existante sans `--force` → erreur ; CSV absent → code 4 avec l'action « lancer forever fetch » ; aucun appel à `http_get` |
| `tests/unit/test_diff.py` | **critère 3** (copie `data_copy` avec une version fictive `1.60.1.70010` copiée de 70009, puis `write_manifest`) : `improvedFrostbolt` rang 1 `[0.1]` → `[0.15]` donne un `Change(kind="talent", key="improvedFrostbolt", change="modified", field="ranks")` avec `old` et `new` ; un sort ajouté (`arcane_barrage`, fictif, rangs copiés de `arcane_blast`) donne `Change(kind="spell", change="added")` ; talent retiré, `max` modifié, rang de sort modifié (`ranks[1].mana`) ; versions identiques → aucun changement ; version inconnue → `unknown_version` (code 4) ; données altérées → `data_integrity` ; comparaison dépôt ↔ candidate (chemin) ; le diff 70009 dépôt ↔ candidate décodée des fixtures ne contient que les observations attendues (aucun changement de talent si le critère 2 passe) |
| `tests/unit/test_verify_version.py` | 70009 du dépôt → `ok` ; candidate des fixtures → `ok`, fichiers hérités listés ; copies altérées, un défaut par test : `len(ranks) != max`, prérequis vers une case vide, deux talents à la même position, rang de sort trop court, fichier absent de `sources.json`, certitude inconnue, empreinte modifiée → `data_integrity` |
| `tests/unit/test_report.py` | Markdown du diff du critère 3 : titre `data: 1.60.1.70009 → 1.60.1.70010`, sections Talents et Sorts, une ligne par changement, résumé chiffré, ligne de provenance en dernier ; sortie identique à horloge fixe (deux rendus égaux) ; diff vide → phrase « aucun changement » ; `--out` écrit le fichier |
| `tests/unit/test_pipeline_cli.py` | chaque commande en texte et en `--json` (codes du tableau CLI) ; `decode`, `diff`, `verify`, `report` avec un `http_get` qui lève : jamais appelé |
| Tests T01/T02 modifiés | `test_contract.py` : cas `builds`, `fetch`, `decode`, `diff`, `verify`, `report` (succès et une erreur chacun) × {texte, `--json`} ; `test_manifest.py` : 11 fichiers ; `test_data_import.py` : + `decode_rules.json` ; `test_network_boundary.py` : les commandes hors ligne n'appellent pas `http_get` |

## Étapes (session `/tranche T03`, dans un worktree, sur une branche)
0. **Collecte (bloquée sur l'utilisateur)**
   1. Tests rouges de `builds` et `fetch` (faux HTTP), commit `T03: tests de builds et fetch` ; implémentation jusqu'au vert, commit `T03: builds et fetch`.
   2. L'utilisateur lance (ou autorise) `uv run forever fetch --version 1.60.1.70009 --tables <liste>` puis, pour le français, `--locale frFR` sur les tables de noms. `decode_rules.json` n'existe pas encore à ce stade : `--tables` est obligatoire tant qu'aucune version locale n'a de liste de tables (sinon erreur `invalid_argument`), et la session donne la liste explicite (tables Trait*, CurvePoint, SkillLineAbility et Spell* de `docs/DATA_SOURCES.md`). Si wago n'a pas les tables de ce build ou si le paramètre de locale n'est pas le bon : s'arrêter et rapporter.
   3. Inventaire noté dans `tasks/T03-inventaire.md` : colonnes réelles de chaque table, identification de l'arbre du Mage, lignes de compétence, motifs d'infobulle rencontrés, sorts de rang manquants (les `0` de `spellIds`). Rédiger `decode_rules.json`, son bloc dans `sources.json`, puis `uv run forever manifest --update` (Bash, jamais Write).
   4. `scripts/extract_wago_fixtures.py` (hors ligne) → `tests/fixtures/wago/1.60.1.70009/` avec son README. Commit `T03: fixtures wago 70009 et règles de décodage`.
1. **Squelettes** : `tables`, `tooltip`, `decode`, `diff`, `verify`, `report`, `sources`, nouvelles erreurs et sous-commandes, corps `raise NotImplementedError`, types complets (mypy strict vert). Commit `T03: squelettes du pipeline`.
2. **Tests rouges** : tous les fichiers du tableau et les tests T01/T02 modifiés ; chaque test échoue pour la bonne raison. `tasks/.rouge` et `tasks/.tests-verrouilles`. Commit `T03: tests`. Les tests de `builds` et `fetch` de l'étape 0 sont déjà verts : ils ne figurent pas dans `.rouge`.
3. **Vert, bloc par bloc** (un commit par bloc) : `tables` → `tooltip` → `decode_talents` (les 5 oracles FC-70009, puis les 49 autres) → `decode_spells` → `decode_version` → `diff` → `verify` → `report` → CLI. **Au premier écart entre le décodage et `talents.json` ou `spells.json` qui ne relève pas d'un bogue démontré : arrêt, rapport de l'écart (talent, champ, valeur client, valeur de référence, certitude de la référence) et question à l'utilisateur.**
4. **Documentation** : `ARCHITECTURE.md` (point 4 de la fraîcheur : `builds` et `fetch` ; version candidate ; `decode_rules.json`) ; `DATA_SOURCES.md` (colonnes et URL de locale confirmées) ; `DECISIONS.md` 34 et suivantes (décisions 1 à 5 et techniques) ; `ROADMAP.md` (T03 : critères précisés ; T08 : `forever_diff_versions`, installation d'une candidate, application de `overrides.json`) ; `OPEN_QUESTIONS.md`.
5. **Permissions** : patch de `.claude/settings.json` (autoriser `uv run forever decode:*` et `uv run forever report:*`) écrit hors du dépôt (`$CLAUDE_JOB_DIR/tmp/T03-settings.patch`), commande `git apply` donnée à l'utilisateur (piège du skill).
6. Supprimer `tasks/.rouge` et `tasks/.tests-verrouilles` ; sous-agent `relecteur` (l'`auditeur-mecaniques` n'a rien à contrôler : aucune mécanique touchée, à confirmer par un `git diff --stat docs/MECHANICS_REGISTRY.yaml` vide) ; `/verifier` ; push de la branche ; CI Ubuntu et Windows verte ; commandes de fusion données à l'utilisateur.
7. Résumé final : Bloqué sur moi, Fait, Tests ajoutés, Registre modifié (aucun), Questions ouvertes.

## Questions ouvertes à ajouter (`docs/OPEN_QUESTIONS.md`)
- Paramètre de locale de l'API CSV de wago.tools (`frFR`) : forme exacte à confirmer ; repli si absent (noms français non disponibles).
- Talents dont un rang n'a pas de sort dans l'arbre wowsims (`0` dans `spellIds` : arcaneResilience, incineration, burningSoul, elementalPrecision) : d'où viennent leurs valeurs dans le client 70009 ?
- Écarts éventuels entre le décodage 70009 et les rangs lus sur 69893 (liste remplie à l'exécution, un point par talent, avec la décision prise).
- Coûts en mana relevés dans le client là où `spells.json` a `null` (Ice Lance r1, Pyroblast r1, Blast Wave r1, Arcane Blast) : à confirmer en jeu avant de remplacer l'estimation de `mechanics.json` (question existante, à relier).
- Hotfixes (`DBCache.bin`) non appliqués par le pipeline : une valeur décodée peut différer du jeu en ligne.

## Hors périmètre
- Installation d'une version candidate dans `forever/data/`, application de `overrides.json`, workflow `build-watch.yml`, PR de données, note d'impact par personnage, outil MCP `forever_diff_versions` (T08).
- Baisse ciblée de la certitude des entités touchées par un diff quand le statut est `stale` (décision 19 : prévue avec le diff, branchée en T08 avec la veille).
- Hotfixes du client (`DBCache.bin`), voie autonome `db2tool` / wow.tools.local.
- Sorts utilitaires (`spells.json.utility`), champs de sort non tabulaires (ralentissement, vitesse de projectile, portée des talents), objets, raciaux, autres classes (T10, T12).
- Toute correction de `talents.json` ou `spells.json` de 70009 : un écart constaté devient une question, jamais une modification du dossier de version.
- Réécriture de `update_data.py` du seed (arbres wowsims) : la source devient le client.

## Risques
| Risque | Parade |
| --- | --- |
| wago.tools ne publie pas (ou plus) les tables du build 1.60.1.70009, ou refuse les requêtes | Arrêt à l'étape 0 et rapport ; repli à décider avec l'utilisateur (dernier build publié, puis `diff` contre 70009 ; voie `db2tool` de DATA_SOURCES.md) |
| Écart réel entre le client 70009 et `talents.json` (49 talents lus sur 69893) | Oracles FC-70009 d'abord ; aucun ajustement du décodeur pour coller ; arrêt et question (décision 2) ; écarts consignés dans OPEN_QUESTIONS |
| Valeurs des rangs dépendant de transformations d'infobulle (signe, ms → s, +1 sur les points de base, arrondis) | Inventaire des motifs sur les fixtures avant le décodeur ; évaluateur pur testé à part ; variable inconnue signalée, jamais devinée |
| Association arbre ↔ classe et nœuds partagés (wakeOfFire et flameThrowing ont les mêmes sorts dans l'arbre wowsims) | Règles explicites dans `decode_rules.json` (géométrie, « le plus récent gagne ») ; tests dédiés avec lignes leurres |
| Sorts homonymes (PNJ, autres classes) | Filtrage par lignes de compétence du Mage ; leurre dans les fixtures |
| Fixtures trop lourdes ou non reproductibles | Script d'extraction versionné, filtre documenté dans le README des fixtures, empreintes dans `fetch.json` |
| Chiffres de jeu glissés dans `forever/pipeline/` (géométrie, identifiants) | Tout dans `decode_rules.json` ; relecture ciblée des littéraux par `relecteur` ; test : une copie de `decode_rules.json` avec une géométrie décalée change le résultat du décodage |
| Débordement de la tranche (décodage des sorts plus coûteux que prévu) | Blocs indépendants : `decode_talents` et les critères de la feuille de route d'abord ; `decode_spells` ensuite, dans une deuxième session si besoin |
| Nouvelles commandes refusées par les permissions de la session | Patch `.claude/settings.json` donné à l'utilisateur (étape 5) ; `fetch` et `builds` restent en `ask` |

## Bloqué sur moi (à valider avant `/tranche T03`)
1. Décisions 1 à 5 ci-dessus (recommandations ou alternatives).
2. Accès réseau ponctuel à wago.tools pour la collecte des fixtures (étape 0) : lancé par vous (`! uv run forever fetch --version 1.60.1.70009`) ou autorisé pour la session.
3. Ajout de `decode_rules.json` au dossier de la version 1.60.1.70009 (régénération de `sources.json` et du manifeste), et des fixtures CSV extraites du client dans `tests/fixtures/`.
4. Modification des tests T01/T02 listés (contrat, manifeste, import des données, frontière réseau).
5. Aucune dépendance ajoutée ; nouveau code de sortie 5 pour les erreurs réseau.

## Critères de fin vérifiables
1. Tests hors ligne : `uv run pytest tests/unit -q` vert avec le réseau bloqué (pytest-socket), les CSV venant de `tests/fixtures/wago/1.60.1.70009/`.
2. `uv run pytest tests/unit/test_decode_talents.py -q` : les 54 talents Mage de `talents.json` reproduits depuis les fixtures (`key`, `name`, `tree`, `tier`, `col`, `max`, `ranks`, `prereq`, ordre).
3. `uv run pytest tests/unit/test_diff.py -q` : un rang de talent modifié et un sort ajouté sont signalés.
4. `uv run forever decode --version 1.60.1.70009 --csv-dir tests/fixtures/wago/1.60.1.70009`, puis `uv run forever verify <candidate>` et `uv run forever report 1.60.1.70009 <candidate>` : code 0, provenance sur chaque sortie ; `forever/data/` inchangé.
5. `uv run forever status` affiche toujours `registre 21/101` ; `uv run tasks.py verify` vert en local (Windows) ; CI `ubuntu-latest` et `windows-latest` verte sur la branche.
