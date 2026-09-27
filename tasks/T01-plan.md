# T01 — Squelette de bout en bout : plan

> Plan issu de la session de cadrage du 2026-09-27. Exécution dans une nouvelle session : `/tranche T01`.

## Contexte
Le dépôt ne contient encore que le kit : docs, hooks, `tasks.py`, CI et `seed/`, mais pas de paquet `forever/`. T01 livre un premier chemin vertical : données versionnées et vérifiées, `forever status`, `forever lookup spell`, serveur MCP à deux outils, bloc provenance dans chaque sortie, CI verte sous Linux et Windows. Le moteur de mécaniques et les simulateurs restent pour T02 et T04.

## Décisions prises au cadrage
| # | Décision | Origine |
| --- | --- | --- |
| 1 | SDK MCP v2 (`mcp>=2,<3`, API `MCPServer` / `mcp.Client`), déjà résolu dans `uv.lock` (2.2.0) | Réponse Q1 |
| 2 | Réseau : seuls `forever status` et l'outil MCP `forever_status` interrogent wago, via un module unique `forever/pipeline/builds.py` (cache 6 h, délai 2 s). Les autres outils lisent le cache ; s'il a plus de 6 h, ils renvoient le dernier état connu avec son âge. `unknown` seulement s'il n'y a aucun cache. Dans les tests, le client HTTP est injecté et les réponses sont simulées. | Réponse Q2 |
| 3 | pytest-socket : `pytestmark = pytest.mark.allow_hosts(["127.0.0.1"])` en tête des modules de tests MCP ; ajout de `--allow-unix-socket` à `addopts` ; CI en matrice `ubuntu-latest` + `windows-latest` | Réponse Q3 |
| 4 | CLI : texte français par défaut + `--json` ; pas de `--line`. La statusline est retirée du projet ; la fraîcheur passe par SessionStart et le bloc provenance. Le test de contrat vérifie la ligne provenance (texte) et le schéma (`--json`). | Réponse Q4 |
| 5 | Aucune nouvelle dépendance d'exécution : `argparse`, `urllib.request`, `hashlib`, `TypedDict`, validateur de schéma maison. Seul ajout : le backend de construction `uv_build`, indispensable (`uv sync --dry-run` : « Skipping installation of entry points… not packaged »). | Cadrage |
| 6 | Données 70009 copiées octet pour octet depuis le seed (format positionnel à 8 cases conservé pour le portage de `fm.py` en T02). Les métadonnées de source et de certitude vont dans un fichier rédigé à côté, `sources.json`, pour ne pas toucher aux fichiers du seed. `overrides.json` va dans le dossier de version : un fichier mutable à la racine violerait l'immuabilité par version. | Cadrage |
| 7 | Correspondance des certitudes : FC→`certain`, FS→`probable`, PC et EST→`suppose` (définitions de SPEC.md) | Cadrage |
| 8 | La certitude porte sur la valeur *pour la `game_version` annoncée*. En T01, `stale` ne dégrade pas la certitude (pas de diff avant T03) mais ajoute une hypothèse. | Cadrage |
| 9 | Empreintes invalides : les outils qui lisent les données refusent de répondre (erreur `data_integrity`, commande de correction indiquée) ; `status` les signale sans échouer | Cadrage |
| 10 | « Manifeste signé » = empreintes sha256 + historique git ; pas de signature cryptographique en T01 | Cadrage |

## Existant réutilisé
- `seed/forever-mage/data/1.60.1.70009/*.json` (7 fichiers) et `seed/forever-mage/data/overrides.json` : copie brute.
- `seed/forever-mage/scripts/update_data.py::latest_wago_build` : logique à porter (réponse sous forme de dict par produit ou de liste, filtre `1.60.`, tri par `created_at`, User-Agent obligatoire).
- `seed/forever-mage/scripts/fm.py::_vkey` : comparaison de versions par tuple d'entiers.
- `scripts/check_registry.py` : liste des statuts à reprendre dans le lecteur minimal du registre.
- Pièges du seed à ne pas reproduire : `_build_data_70009.py` écrit sans `encoding=` (cp1252 sous Windows) ; `seed/grimoire-engine/` est un doublon exact de `seed/forever-mage/engine/`.

## Fichiers
```
pyproject.toml            [build-system] uv_build ; [tool.uv.build-backend] module-name="forever", module-root="" ;
                          mcp>=2,<3 ; addopts="--disable-socket --allow-unix-socket"
.python-version           3.13 (même interpréteur en local et en CI)
.gitattributes            forever/data/** -text  (octets stables → mêmes empreintes sur tous les OS)
.github/workflows/ci.yml  matrix os: [ubuntu-latest, windows-latest]
.claude/settings.json     retirer "statusLine" ; autoriser "Bash(uv run forever manifest --check:*)"
.claude/hooks/statusline.py  supprimé
forever/__init__.py       __version__
forever/__main__.py       python -m forever → cli.main
forever/config.py         Deps, default_deps(), constantes outil (CACHE_TTL=6 h, SILENT_AFTER=14 j, HTTP_TIMEOUT=2 s, USER_AGENT)
forever/errors.py         ForeverError(code, message, action) + sous-classes
forever/manifest.py       calcul et vérification des empreintes, écriture déterministe
forever/store.py          chargement d'une version (vérifie l'intégrité avant de lire)
forever/pipeline/__init__.py
forever/pipeline/builds.py  seul point d'accès réseau : fetch + parse des versions wago
forever/freshness.py      classify() pure + cache status.json + check_freshness()
forever/registry.py       lecteur minimal : couverture du registre (validation complète en T02)
forever/provenance.py     type, fabrique, validateur, rendu texte, correspondance des certitudes
forever/lookup.py         lookup_spell()
forever/status.py         status_report()
forever/cli.py            forever status | lookup | manifest | mcp
forever/mcp_server.py     build_server(deps) ; outils forever_status, forever_lookup
forever/data/1.60.1.70009/{spells,talents,racials,leveling,respec,meta,_source_gunba_mage_tree,overrides}.json  (copies)
forever/data/1.60.1.70009/sources.json   (rédigé)
forever/data/manifest.json               (généré UNIQUEMENT par `uv run forever manifest --update`, le hook bloque Write)
tests/unit/…, tests/integration/…, tests/fixtures/…   (voir « Tests »)
docs/ARCHITECTURE.md, docs/DECISIONS.md, CLAUDE.md, docs/MECHANICS_REGISTRY.yaml, docs/OPEN_QUESTIONS.md
```

## Interfaces

### Injection (`forever/config.py`)
```python
HttpGet = Callable[[str, dict[str, str], float], bytes]   # (url, en-têtes, délai) -> corps ; lève OSError

@dataclass(frozen=True)
class Deps:
    data_dir: Path            # forever/data
    registry_path: Path       # docs/MECHANICS_REGISTRY.yaml
    cache_dir: Path           # FOREVER_CACHE_DIR, sinon ~/.cache/forever
    http_get: HttpGet         # urllib en production ; faux client dans les tests
    now: Callable[[], datetime]   # UTC, avec fuseau
    offline: bool = False     # FOREVER_OFFLINE=1 ou --offline : aucun appel réseau

def default_deps() -> Deps
```
La CLI (`main(argv: list[str] | None = None, deps: Deps | None = None) -> int`) et le MCP (`build_server(deps: Deps) -> MCPServer`) reçoivent le même `Deps`.

### Erreurs (`forever/errors.py`)
`ForeverError(code: str, message: str, action: str)`, avec `code` parmi `data_integrity`, `unknown_spell`, `unknown_rank`, `unsupported_kind`, `manifest_missing`. Messages en français ; `action` dit quoi faire (ex. « lancer `uv run forever manifest --update` si la modification est voulue »). Codes de sortie CLI : 0 succès, 2 usage, 3 intégrité, 4 introuvable. En MCP : le résultat renvoyé est un `CallToolResult(is_error=True, structured_content={"error": {...}, "provenance": {...}}, content=[texte])`. Le SDK v2 le transmet tel quel (vérifié) ; une exception brute ne ferait voir au modèle qu'un message générique.

### Provenance (`forever/provenance.py`)
```python
Certainty = Literal["certain", "probable", "suppose"]
Freshness = Literal["fresh", "stale", "unknown", "silent"]
class Provenance(TypedDict):
    game_version: str; data_sha: str; generated_at: str; freshness: Freshness
    certainty: Certainty; assumptions: list[str]; registry_coverage: str
LEGACY_CERTAINTY: dict[str, Certainty] = {"FC": "certain", "FS": "probable", "PC": "suppose", "EST": "suppose"}
def make_provenance(deps, *, game_version, data_sha, freshness, certainty, assumptions) -> Provenance
def validate_provenance(obj: object) -> list[str]        # [] si valide ; messages en français
def format_provenance_line(p: Provenance) -> str
def min_certainty(values: Iterable[Certainty]) -> Certainty
```
Schéma (appliqué par `validate_provenance`, exactement 7 clés, aucune de plus) :
```json
{"type":"object","additionalProperties":false,
 "required":["game_version","data_sha","generated_at","freshness","certainty","assumptions","registry_coverage"],
 "properties":{
  "game_version":{"type":"string","pattern":"^\\d+\\.\\d+\\.\\d+\\.\\d+$"},
  "data_sha":{"type":"string","pattern":"^[0-9a-f]{12}$"},
  "generated_at":{"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$"},
  "freshness":{"enum":["fresh","stale","unknown","silent"]},
  "certainty":{"enum":["certain","probable","suppose"]},
  "assumptions":{"type":"array","items":{"type":"string"}},
  "registry_coverage":{"type":"string","pattern":"^\\d+/\\d+$"}}}
```
Ligne texte (dernière ligne de toute sortie texte, les 7 champs étiquetés) :
`Provenance · version 1.60.1.70009 · données 3f9a1c2b7d4e · générée 2026-09-27T10:00:00Z · fraîcheur fresh · certitude certain · registre 16/97 · hypothèses : aucune`
Pour `status` et `manifest`, la certitude vaut `certain` (sorties qui ne décrivent pas le jeu).

### Registre (`forever/registry.py`)
`coverage(path: Path) -> str` renvoie `"<n>/<total>"`, où n compte les entrées de statut `teste`, `valide-journal` ou `valide-jeu`. Valeur actuelle : **16/97**. Si le fichier est absent : `"0/0"`, avec une hypothèse « registre introuvable ».

### Manifeste (`forever/manifest.py`)
```python
def file_sha256(path: Path) -> str                          # octets bruts
def compute_manifest(data_dir: Path) -> dict[str, object]   # déterministe, sans horodatage
def write_manifest(data_dir: Path) -> Path                  # JSON trié, indent 2, LF, UTF-8, \n final
def verify(data_dir: Path) -> IntegrityReport               # ok, mismatched, missing, unexpected (chemins relatifs)
def data_sha(files: Mapping[str, str]) -> str               # sha256 des lignes "<nom> <sha>\n" triées → 12 premiers hex
```
```json
{"schema_version": 1, "game_version": "1.60.1.70009",
 "versions": {"1.60.1.70009": {
   "product": "wow_classic_beta", "version_prefix": "1.60.", "collected_at": "2026-09-26",
   "hotfixes": [], "data_sha": "<12 hex>", "data_sha256": "<64 hex>",
   "files": {"_source_gunba_mage_tree.json": "<sha256>", "leveling.json": "…", "…": "…"}}}}
```
`game_version` désigne le dossier de version le plus élevé (tri par tuple). `product`, `version_prefix` et `collected_at` sont recopiés depuis `sources.json`. `--update` est idempotent : deux exécutions donnent les mêmes octets.

### `sources.json` (rédigé, haché comme les autres)
```json
{"schema_version": 1, "game_version": "1.60.1.70009", "product": "wow_classic_beta",
 "version_prefix": "1.60.", "collected_at": "2026-09-26",
 "files": {
  "spells.json": {"source": "Client Forever 1.60.1.70009 via https://wowforevertalents.com/abilities/mage/ (lu le 26/09/2026)",
                  "certainty": "certain", "field_certainty": {"projectile_speed": "suppose"},
                  "notes": ["mana null : coût non publié pour le rang issu d'un talent (à relever en jeu)"]},
  "talents.json": {"source": "gunba/wow-forever-sim mage.json (MIT) + corrections foreverchanges.pro", "certainty": "probable",
                   "notes": ["certitude par talent dans le champ certainty (codes FC/FS)"]},
  "…": "un bloc par fichier ; certitude mixte → la plus basse, avec une note"}}
```
Seul le bloc `spells.json` est exposé par T01 ; les autres sont remplis de façon conservatrice et affinés en T02 et T03.

### Versions publiées (`forever/pipeline/builds.py`)
```python
@dataclass(frozen=True)
class Build: version: str; created_at: datetime          # UTC
class BuildsUnavailable(ForeverError): ...
BUILDS_URL = "https://wago.tools/api/builds"
def fetch_builds(http_get: HttpGet) -> object            # User-Agent, délai HTTP_TIMEOUT ; OSError/JSON invalide → BuildsUnavailable
def parse_builds(payload: object, product: str, prefix: str) -> list[Build]   # dict par produit OU liste
def latest_build(builds: Sequence[Build]) -> Build | None                    # max par created_at
def version_key(v: str) -> tuple[int, ...]
```
`created_at` est accepté sous la forme `AAAA-MM-JJ HH:MM:SS` ou ISO 8601 (Z ou décalage) ; une date sans fuseau est lue en UTC.

### Fraîcheur (`forever/freshness.py`)
```python
def classify(local_version: str, latest: Build | None, now: datetime, silent_after: timedelta) -> Freshness  # pure
def check_freshness(deps: Deps, local_version: str, *, allow_network: bool) -> FreshnessResult
class FreshnessResult(TypedDict):
    freshness: Freshness; checked_at: str | None; age_hours: float | None
    latest_version: str | None; latest_created_at: str | None; source: Literal["network", "cache", "none"]
```
**Priorité des statuts** (dans cet ordre) :
1. Aucune observation (réseau indisponible ou interdit, et aucun cache) → `unknown`.
2. `version_key(latest) > version_key(local)` → `stale`.
3. `now − latest.created_at > 14 j` (strictement), ou aucune version du produit n'a le préfixe → `silent`.
4. Sinon → `fresh`.

**`status` (réseau autorisé)** : cache de moins de 6 h → on l'utilise sans appel réseau. Sinon appel réseau : en cas de succès, on classe et on écrit le cache ; en cas d'échec, `unknown` avec le dernier état connu et son âge (le cache garde sa dernière observation réussie).
**Autres outils** : jamais de réseau. Avec un cache, ils reclassent son observation avec `now` (`silent` peut basculer) ; au-delà de 6 h, ils ajoutent l'hypothèse « fraîcheur vérifiée il y a 9 h (lancer `forever status`) ». Sans cache → `unknown`.

Cache `<cache_dir>/status.json` :
```json
{"schema_version": 1, "freshness": "fresh", "computed_at": "…Z", "local_version": "1.60.1.70009",
 "fetched_at": "…Z", "latest": {"version": "1.60.1.70009", "created_at": "…Z"} , "product": "wow_classic_beta"}
```

### Consultation (`forever/lookup.py`)
```python
def lookup_spell(deps: Deps, name: str, rank: int | None = None, *, detail: bool = False,
                 limit: int = 20, offset: int = 0) -> SpellLookup
class SpellRank(TypedDict):
    rank: int; level: int; damage_min: int; damage_max: int; dot_total: int; dot_duration_s: float
    cast_time_s: float; mana: int | None; mana_pct_base: float | None; cooldown_s: float
class SpellLookup(TypedDict):
    kind: Literal["spell"]; id: str; school: str; range_yd: float | None; ranks_total: int
    ranks: list[SpellRank]; total: int; next_offset: int | None
    details: dict[str, object] | None        # si detail=True : slow, slow_dur, binary, talent, projectile_speed…
    provenance: Provenance
```
- `rank` est la position dans le tableau, en base 1 (et non le niveau). Sans `rank`, tous les rangs sont renvoyés, paginés.
- Normalisation du nom : casse ignorée, espaces et tirets convertis en `_`. Nom inconnu → `unknown_spell` avec suggestions (`difflib`).
- Les entrées `utility` (format hétérogène) sont hors périmètre → `unsupported_kind` avec la liste des sorts disponibles.
- Certitude = minimum sur les champs renvoyés non nuls, d'après `sources.json`. `mana` à `null` → hypothèse du fichier ajoutée ; `projectile_speed` n'apparaît qu'avec `detail`, qui fait alors passer la certitude à `suppose`.
- Hypothèses : fraîcheur (âge, `stale`) et notes pertinentes du fichier.

Sortie texte de `forever lookup spell frostbolt --rank 2` :
```
Frostbolt (givre) — rang 2/11, appris au niveau 8
34-38 dégâts · incantation 1,8 s · 35 mana · portée 30 m
Provenance · version 1.60.1.70009 · … · certitude certain · …
```

### Statut (`forever/status.py`)
`status_report(deps: Deps, *, allow_network: bool = True) -> StatusReport` renvoie : `local_version`, `freshness` (FreshnessResult), `integrity` (`ok`, `mismatched`, `missing`, `unexpected`), `registry_coverage`, `provenance`. Si les empreintes sont invalides, le rapport le dit et le code de sortie vaut 3.

### CLI (`forever/cli.py`)
```
forever status [--json] [--offline]
forever lookup spell <nom> [--rank N] [--detail] [--limit N] [--offset N] [--json]
forever manifest (--update | --check) [--json]
forever mcp                      # serveur MCP en stdio
```
`python -m forever.cli` doit rester exécutable (`tasks.py status` l'utilise).

### MCP (`forever/mcp_server.py`)
`build_server(deps) -> MCPServer("forever")`, avec `@server.tool()` (parenthèses obligatoires) :
- `forever_status(offline: bool = False) -> StatusReport`
- `forever_lookup(kind: str, name: str, rank: int | None = None, detail: bool = False, limit: int = 20, offset: int = 0) -> SpellLookup`

Les annotations `TypedDict` produisent `outputSchema` et `structured_content`. Entrée stdio : `uv run forever mcp`.

## Tests à écrire d'abord (phase rouge)
Toutes les valeurs de jeu citent `seed/forever-mage/data/1.60.1.70009/spells.json` (source) ou viennent de `tests/fixtures/`. Aucun réseau ; `now` est injecté.

Fixtures :
- `tests/fixtures/wago/builds_fresh.json` : 70009 publiée le 2026-09-24.
- `builds_stale.json` : en plus, 1.60.1.70150 publiée le 2026-09-26.
- `builds_silent.json` : 70009 publiée le 2026-09-01.
- `builds_list_form.json` : forme liste.
- `builds_other_product.json` : aucune version `1.60.`.
- Toutes sont au format dict par produit, comme le seed ; une entrée `wow` sert de leurre.
- `tests/fixtures/registry_small.yaml` : 3 entrées, dont 1 `teste`.
- `tests/conftest.py` : fabrique `make_deps(tmp_path, http=FakeHttp(...), now=...)`, copie des données dans `tmp_path` quand un test doit les modifier.

| Fichier | Tests et valeurs attendues |
| --- | --- |
| `tests/unit/test_data_import.py` | les 8 fichiers copiés ont le même sha256 que le seed ; le dossier contient exactement ces 8 fichiers + `sources.json` |
| `tests/unit/test_manifest.py` | `verify(forever/data).ok` est vrai (manifeste du dépôt à jour) ; un octet modifié dans une copie de `spells.json` (`tmp_path`) → `mismatched == ["1.60.1.70009/spells.json"]` (**critère 3**) ; fichier supprimé → `missing` ; fichier ajouté → `unexpected` ; `write_manifest` appelé deux fois → mêmes octets ; `data_sha` fait 12 hex et change quand un fichier change ; `game_version` vaut la version la plus haute, avec un faux dossier `1.60.1.70150` |
| `tests/unit/test_builds.py` | forme dict et forme liste → mêmes `Build` ; filtre `1.60.` ; `latest_build` suit `created_at` et non l'ordre d'arrivée ; deux formats de date ; `OSError` et JSON invalide → `BuildsUnavailable` ; le faux client reçoit l'URL wago, un `User-Agent` et un délai de 2 s |
| `tests/unit/test_freshness.py` | (**critère 2**) avec `now=2026-09-27T12:00Z` : fixture fresh → `fresh` ; stale → `stale` ; client qui lève + aucun cache → `unknown` ; silent → `silent`. En plus : 14 j exactement → `fresh` ; aucune version préfixée → `silent` ; cache de 2 h → 0 appel réseau ; échec réseau avec un cache → `unknown`, `checked_at` et `age_hours` renseignés ; outil sans réseau avec un cache de 9 h → dernier état `fresh` + hypothèse contenant « 9 h » ; outil sans réseau sans cache → `unknown` ; `offline=True` → 0 appel |
| `tests/unit/test_provenance.py` | un bloc valide → `[]` ; clé manquante, clé en trop, `certainty="sure"`, `data_sha` de 11 caractères → erreurs ; `coverage(registry_small.yaml) == "1/3"` ; `coverage(docs/…) == "16/97"` ; `LEGACY_CERTAINTY` ; `min_certainty` ; la ligne texte contient les 7 étiquettes |
| `tests/unit/test_lookup.py` | (**critère 1**) `frostbolt` rang 2 → `level 8`, `damage_min 34`, `damage_max 38`, `cast_time_s 1.8`, `mana 35`, `cooldown_s 0`, `school "frost"`, `range_yd 30`, `ranks_total 11`, `game_version "1.60.1.70009"`, `certainty "certain"`. Sans rang → 11 rangs. `"Frostbolt"`, `"FROSTBOLT"` et `"fire blast"` sont résolus. Rang 12 → `unknown_rank`, message contenant « 1-11 ». `"frostbollt"` → suggestion `frostbolt`. `pyroblast` rang 1 → `mana None` + hypothèse. `arcane_blast` rang 1 → `mana_pct_base 0.15`. `detail=True` → `projectile_speed 28`, certitude `suppose`. `blink` → `unsupported_kind`. Données altérées dans `tmp_path` → `data_integrity` |
| `tests/unit/test_cli.py` | la sortie texte de `lookup spell frostbolt --rank 2` contient « 34-38 dégâts », « 1,8 s », « 35 mana », « 1.60.1.70009 », « certitude certain » ; `--json` se parse et porte les mêmes valeurs ; codes de sortie 0/2/3/4 ; `status` en texte et en JSON (faux client) ; `manifest --check` → 0, puis 3 après altération |
| `tests/unit/test_contract.py` | (**critère 5**) paramétré sur `status`, `lookup`, `manifest --check`, `manifest --update` (sur `tmp_path`) et leurs erreurs × {texte, `--json`} : en texte, la dernière ligne a les 7 champs ; en `--json`, `validate_provenance(out["provenance"]) == []` |
| `tests/integration/test_mcp.py` | `pytestmark = allow_hosts(["127.0.0.1"])`. (**critère 4**) `asyncio.run` + `Client(build_server(deps))` : `list_tools` → `{"forever_status","forever_lookup"}` avec `output_schema` ; `call_tool("forever_lookup", {"kind":"spell","name":"frostbolt","rank":2})` → `structured_content` avec 34/38/1.8/35 et une provenance valide ; `forever_status` avec un faux client → provenance valide ; nom inconnu → `is_error` et `structured_content.error.code == "unknown_spell"` + provenance valide |
| `tests/integration/test_mcp_stdio.py` | même marqueur ; `Client(StdioServerParameters(command=sys.executable, args=["-m","forever","mcp"], env={FOREVER_OFFLINE:"1", FOREVER_CACHE_DIR: tmp}))` → 2 outils ; `forever_lookup` répond (vérifie le vrai point d'entrée) |

`test-fast` et le hook Stop ne lancent que `tests/unit/` ; `tests/integration/` tourne dans `uv run tasks.py test` et `verify`.

## Étapes (session `/tranche T01`, dans un worktree, sur une branche)
1. **Socle** : `pyproject.toml` (build-system, `mcp>=2,<3`, `addopts`), `.python-version`, `.gitattributes`, matrice CI, retrait de la statusline (réglage + fichier) ; `uv sync` puis `uv run forever --help` échoue proprement (module absent). Commit `T01: socle de build et CI`.
2. **Données** : copie brute des 8 fichiers dans `forever/data/1.60.1.70009/` ; rédaction de `sources.json`. Commit `T01: données 1.60.1.70009 depuis le seed`.
3. **Squelettes** : modules et signatures ci-dessus, corps `raise NotImplementedError`, types complets (mypy strict vert). Commit `T01: squelettes`.
4. **Tests rouges** : fixtures, `conftest.py`, tous les tests du tableau ; chacun échoue pour la bonne raison (`NotImplementedError`, manifeste absent). Écrire `tasks/.rouge` et `tasks/.tests-verrouilles`. Commit `T01: tests`.
5. **Vert, bloc par bloc** : `manifest` → `uv run forever manifest --update` (Bash, jamais Write) → `builds` → `freshness` → `registry`/`provenance` → `store`/`lookup` → `status` → `cli` → `mcp_server`. Un commit par bloc (`T01: <bloc>`).
6. **Échantillon réel** (accès réseau, accord demandé au moment voulu) : capturer une réponse de `https://wago.tools/api/builds`, réduite à `wow_classic_beta` et à quelques entrées, dans `tests/fixtures/wago/builds_real_sample.json` ; ajouter un test de `parse_builds` dessus. Si le format réel diffère des fixtures synthétiques : s'arrêter et le signaler avant de toucher aux tests verrouillés.
7. **Documentation** :
   - `ARCHITECTURE.md` : statusline retirée ; fraîcheur via SessionStart et provenance ; règle réseau ; schémas du manifeste et de `sources.json` ; `overrides.json` par version.
   - `CLAUDE.md` : la ligne réseau devient « Seules `forever status`, `forever builds` et `forever fetch` touchent Internet (via `forever/pipeline/`) ».
   - `DECISIONS.md` : décisions 1 à 10 ci-dessus, en lignes 12 et suivantes.
   - `MECHANICS_REGISTRY.yaml` : J1 ajoute les tests `test_manifest.py` et `test_freshness.py` et reste `modelise` (hotfixes absents).
   - `OPEN_QUESTIONS.md` : format de `created_at` si l'étape 6 n'est pas faite.
8. Supprimer `tasks/.rouge` et `tasks/.tests-verrouilles` ; lancer `/verifier` ; push de la branche ; **vérifier les deux jobs CI (Ubuntu et Windows) et corriger jusqu'au vert**.
9. Résumé final : Bloqué sur moi, Fait, Tests ajoutés, Registre modifié, Questions ouvertes.

## Hors périmètre
- Mécaniques, formules et simulateurs (T02, T04) ; aucune formule dans `forever/`.
- Consultation des talents, raciaux, objets, sorts utilitaires ; noms français (données FR en T03).
- Commandes `forever builds`, `fetch`, `decode`, `diff`, `update` (T03) ; hotfixes.
- Baisse de certitude sur `stale` (exige le diff de T03).
- Plugin, hook SessionStart produit, `.mcp.json` (T06) ; serveur MCP distant (T13).
- Signature cryptographique du manifeste.

## Risques
| Risque | Parade |
| --- | --- |
| API MCP v2 récente, peu documentée | Essai à blanc déjà réussi (`Client(server)`, `output_schema`, `is_error`) ; code MCP confiné à `mcp_server.py` |
| asyncio bloqué par pytest-socket sous Windows | Marqueur `allow_hosts` par module (vérifié : boucle OK, connexion externe bloquée) |
| Fins de ligne → empreintes différentes selon l'OS | `.gitattributes -text` + matrice CI Windows + test d'identité avec le seed |
| Hook `protect_golden.py` bloque l'écriture de `manifest.json` | Génération uniquement par `uv run forever manifest --update` en Bash |
| Format réel de wago inconnu hors ligne | Parseur tolérant (dict ou liste, deux formats de date) + étape 6 |
| Tests dépendants de l'horloge ou du cache de l'utilisateur | `now` et `cache_dir` injectés ; `tmp_path` partout ; aucun test ne lit `~/.cache` |
| `docs/` hors du paquet (registre) | Lecture relative à la racine du dépôt ; repli `0/0` ; à reprendre en T13 |
| mypy 2.x strict sur les types `mcp` | `TypedDict` simples ; `# type: ignore[...]` ciblés et commentés si nécessaire |
| `uv_build` avec `module-root=""` | Vérifié à l'étape 1 par `uv sync` + `uv run forever --help` |
| Test stdio lent ou instable sous Windows | Délai de lecture du `Client` explicite ; un seul test de ce type |

## Accords demandés en validant ce plan
1. Backend de construction `uv_build` (build-system ; aucune dépendance d'exécution ajoutée).
2. Suppression de `.claude/hooks/statusline.py` et de `statusLine` dans `.claude/settings.json`.
3. Modification de la ligne réseau de `CLAUDE.md` (décision 2).
4. Un accès réseau ponctuel à l'étape 6 (confirmé au moment voulu).

## Critères de fin vérifiables
1. `uv run forever lookup spell frostbolt --rank 2` affiche « 34-38 dégâts · incantation 1,8 s · 35 mana », puis une ligne provenance avec `version 1.60.1.70009` et `certitude certain`. Avec `--json`, les mêmes valeurs en nombres.
2. `uv run pytest tests/unit/test_freshness.py -q` : les 4 statuts sont couverts (fresh, stale, unknown, silent), sans réseau.
3. `uv run pytest tests/unit/test_manifest.py -q` : l'altération d'une empreinte est détectée ; `uv run forever manifest --check` → code 0 sur le dépôt.
4. `uv run pytest tests/integration -q` : le serveur liste `forever_status` et `forever_lookup` et y répond (en mémoire et en stdio).
5. `uv run pytest tests/unit/test_contract.py -q` : provenance complète en texte et en `--json`, pour chaque commande et chaque outil.
6. `uv run forever status` affiche la fraîcheur réelle, l'intégrité `ok` et `registre 16/97`.
7. `uv run tasks.py verify` est vert en local (Windows) ; les jobs CI `ubuntu-latest` et `windows-latest` sont verts sur la branche.
