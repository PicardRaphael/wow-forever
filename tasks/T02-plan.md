# T02 — Cœur de mécaniques et registre : plan

> Plan issu de la session de cadrage du 2026-09-27. Exécution dans une nouvelle session : `/tranche T02`.

## Contexte
T01 a livré les données versionnées, la provenance, `status`, `lookup spell` et le serveur MCP, sans aucune formule. T02 porte le cœur de calcul du skill Mage (`seed/forever-mage/scripts/fm.py`, 287 lignes) dans `forever/engine/`, en fonctions pures qui reçoivent les données de la version en paramètre. Il ajoute aussi la validation complète du registre (`forever/registry.py`, mode strict dans `verify`) et la commande `forever explain-mechanic`. Les simulateurs (`sim_leveling.py`), l'optimiseur, le PvP et la respec restent pour T04 et T05.

Deux écarts entre la feuille de route et le seed sont à trancher :
- **« Porter les 10 tests existants »** : seuls 5 des 10 tests de `seed/forever-mage/tests/run_all.py` visent `fm.py` (`donnees_completes`, `valeurs_client_70009`, `prerequis`, `legalite`, `couverture_mecaniques`). Les 5 autres (`analytique_proche_du_monte_carlo`, `calibrage_cible_blizzard`, `monte_carlo_reproductible`, `optimiseur_legal`, `pvp_et_respec`) exigent les simulateurs, l'optimiseur, le PvP et la respec.
- **Modules** : la feuille de route cite hit, crit, damage, casting, mana. `fm.py` contient aussi la légalité des talents, le modèle de personnage, le choix du rang, les coefficients et l'agrégateur `expected_cast`.

## Décisions prises au cadrage (accords donnés le 2026-09-27)
| # | Décision | Recommandation | Alternative écartée |
| --- | --- | --- | --- |
| 1 | Périmètre des tests portés | Porter les 5 tests du moteur, dont les 30 contrôles. Les 5 autres passent en T04 (MC, analytique, calibrage, reproductibilité) et T05 (optimiseur, PvP, respec) ; la feuille de route est corrigée en ce sens. | Porter les simulateurs dès T02 (double la tranche et empiète sur T04) |
| 2 | Constantes de `fm.py` | Nouveau fichier rédigé `forever/data/1.60.1.70009/mechanics.json` : chaque constante absente des tables y figure avec sa valeur, sa certitude, sa source et son identifiant de registre. Les raciaux se lisent dans `racials.json`, les règles structurées dans `leveling.json.combat_rules`. Le moteur n'a plus aucun littéral de jeu (`.claude/rules/engine.md`). | Constantes Python dans `forever/engine/` (viole l'invariant de CLAUDE.md) ; reformuler `leveling.json` (fichier copié octet pour octet du seed, décision 17) |
| 3 | Registre honnête en mode strict | Rétrograder en `absent` les entrées dont le code n'existe pas encore dans `forever/`, avec une `note` qui renvoie à T04 ou T05 : B6, B7, B13, C1, C5, H2, I1, I5, I6, J2. Passer G1, G2 et C2 en `teste` (portés et testés ; C2 avec la note « portée de base ; talents de portée en T04 »). Ajouter 4 entrées pour des contrôles du seed qui n'avaient pas d'entrée : A20, A21, B16, B17. | Garder `modelise` sans test (fait échouer le mode strict) ; tests factices |
| 4 | Références de test | Une référence de test prend la forme `tests/…/fichier.py::test_nom`. La fonction doit exister (analyse `ast`, sans import). Les chemins `seed/` sont refusés. Une référence au fichier seul reste tolérée pour `modelise` (J1). | Contrôle du fichier seul (actuel) |
| 5 | `explain-mechanic` | Champs optionnels `formule` (symbolique : seuls 0 et 1 sont admis, comme bornes mathématiques ; tout autre nombre est refusé par un contrôle) et `note` dans le registre. Les valeurs s'affichent depuis `mechanics.json` (entrées étiquetées par identifiant) pour la version courante. CLI **et** outil MCP `forever_explain_mechanic` (déjà prévu dans ARCHITECTURE.md et autorisé dans `.claude/settings.json`). | Formule chiffrée dans `docs/` ; CLI seule |

Décisions techniques (sans arbitrage attendu) :
- **Pureté** : les données passent dans un objet `GameData` gelé, construit **hors** du moteur par `forever/gamedata.py` (via `store.load_version`, donc après contrôle d'intégrité), et reçu en premier paramètre par chaque fonction du moteur. Pas de singleton `data()`.
- **Fidélité** : l'ordre des opérations de `fm.py` est conservé ; les 30 contrôles gardent leurs égalités exactes (`==`). Un test de parité importe le `fm.py` du seed en lecture seule et compare le moteur porté sur une grille de cas, avec une tolérance relative de 1e-12.
- **Inventaire** : `mechanics_used()` devient `forever/engine/__init__.py::MECHANICS`, un dict qui associe chacun des 30 libellés à un identifiant de registre. Un test lie les 30 contrôles, cet inventaire et le registre.
- **Certitude de `explain-mechanic`** : le champ `certainty` de l'explication reprend la certitude du registre. Celle de la provenance est le minimum entre cette certitude et celles des paramètres affichés (même règle que `lookup`).
- **`GameData` mono-classe** : T02 ne charge que le Mage (talents, sorts) ; un espace par classe (`GameData` par classe ou clé de classe) est à prévoir en T12.
- `scripts/check_registry.py` devient une simple enveloppe de `forever.registry.main`, et `tasks.py` passe `STRICT_REGISTRY = True`.

## Existant réutilisé
- `seed/forever-mage/scripts/fm.py` : logique à porter fonction par fonction. `seed/forever-mage/tests/run_all.py` : les 5 tests et les 30 contrôles, avec leurs valeurs.
- `forever/store.py::load_version`, `VersionData.read_json` : chargement après contrôle d'intégrité.
- `forever/lookup.py::_rank` : analyse d'un rang via `spells.json.rank_format`. Même principe et mêmes noms de champs (`damage_min`, `cast_time_s`…) pour le `Rank` du moteur.
- `forever/registry.py::coverage` et `COVERED_STATUSES` : conservés. `scripts/check_registry.py` : règles actuelles (champs, statuts, certitudes, doublons), à déplacer dans le paquet.
- `forever/provenance.py` (`make_provenance`, `min_certainty`, `error_payload`, `format_provenance_line`), `forever/errors.py` (modèle de `UnknownSpellError` avec suggestions `difflib`), `forever/cli.py::_emit` / `_emit_error`, `forever/mcp_server.py` (motif `CallToolResult(is_error=True)`).
- `tests/conftest.py` (`make_deps`, `DATA_DIR`, `REGISTRY_PATH`, `SEED_DATA`, copie des données dans `tmp_path`).
- `seed/forever-mage/references/mechanics.md` et `meta.json.sources` : sources à reporter dans le registre pour les entrées portées.

## Fichiers
```
forever/engine/__init__.py     MECHANICS (30 libellés → id du registre), réexports publics
forever/engine/model.py        types : Points, Rank, Spell, Talent, CombatRules, Constants (+ sous-types), Racials,
                               GameData, CharacterOverrides, Character, Buffs, CastEstimate ; SCHOOL_FROST, SCHOOL_FIRE
forever/engine/talents.py      talent_value, points_available, check_build, legal_additions, tree_split      (G3)
forever/engine/character.py    int_per_crit, character                                              (A5, B9, G1, G2)
forever/engine/spells.py       best_rank, coefficient                                               (G4)
forever/engine/hit.py          hit_chance                                                           (A3, A4, H1)
forever/engine/crit.py         crit_chance, crit_mult                                               (A5, D4, A21)
forever/engine/damage.py       dmg_mult, spell_power                                                (A20)
forever/engine/casting.py      cast_time                                                            (B1, B2, B16)
forever/engine/mana.py         mana_cost                                                            (B11, B17)
forever/engine/cast.py         expected_cast (DoT qui critiquent, Ignite, MoE, Clearcasting)        (A17, A18, B12, B17, C2)
forever/gamedata.py            load_game_data(deps) -> GameData ; build_game_data(version: VersionData) -> GameData
forever/registry.py            load, validate, implementations, find_entry, coverage, main (enveloppe CLI)
forever/explain.py             explain_mechanic(deps, mechanic_id) -> MechanicExplanation
forever/errors.py              + UnknownMechanicError (unknown_mechanic, code 4), DataSchemaError (data_schema, code 3)
forever/cli.py                 + forever explain-mechanic <id> [--json]
forever/mcp_server.py          + forever_explain_mechanic(mechanic_id: str)
forever/data/1.60.1.70009/mechanics.json   (rédigé) ; sources.json : bloc mechanics.json ; manifest.json régénéré
scripts/check_registry.py      enveloppe : sys.exit(forever.registry.main(sys.argv[1:]))
tasks.py                       STRICT_REGISTRY = True
docs/MECHANICS_REGISTRY.yaml   statuts, tests, sources, formule, note ; A20, A21, B16, B17 ; en-tête mis à jour
docs/ROADMAP.md                T02 : 5 tests portés ; T04/T05 : reprise des 5 autres
docs/ARCHITECTURE.md, docs/DECISIONS.md (25 et suivantes), docs/OPEN_QUESTIONS.md
tests/unit/test_gamedata.py, test_engine_talents.py, test_engine_character.py, test_engine_values.py,
tests/unit/test_engine_mechanics.py, test_registry.py, test_explain.py ; tests/parity/test_fm_parity.py
tests/fixtures/registry/*.yaml  (registres invalides, un défaut par fichier) ; tests/fixtures/engine_cites/ (faux moteur)
Tests T01 modifiés : test_cli.py, test_provenance.py (16/97 → coverage(REGISTRY_PATH)), test_data_import.py (+ mechanics.json),
                     test_manifest.py (9 → 10 fichiers), test_contract.py (+ explain-mechanic),
                     tests/integration/test_mcp.py et test_mcp_stdio.py (3 outils)
```

## Interfaces

### Types du moteur (`forever/engine/model.py`)
```python
Points = Mapping[str, int]                      # clé de talent -> rang
SCHOOL_FROST = frozenset({"frost", "frostfire"}); SCHOOL_FIRE = frozenset({"fire", "frostfire"})

class Rank(NamedTuple):
    position: int            # base 1, comme `lookup`
    level: int; damage_min: float; damage_max: float; dot_total: float; dot_duration_s: float
    cast_time_s: float; mana: float | None; cooldown_s: float

@dataclass(frozen=True)
class Spell:
    key: str; school: str; ranks: tuple[Rank, ...]; range_yd: float | None; talent: str | None
    channel: bool; slow: float | None; mana_pct_base: float | None; frozen_mult: float | None
    projectile_speed: float | None

@dataclass(frozen=True)
class Talent:
    key: str; name: str; tree: str; tier: int; col: int; max_rank: int
    ranks: tuple[tuple[float, ...], ...]; prereq: tuple[int, int] | None     # (palier, colonne)

@dataclass(frozen=True)
class CombatRules:        # leveling.json.combat_rules (champs structurés seulement)
    gcd_s: float; spell_miss_by_level_diff: Mapping[str, float]; min_miss: float
    crit_mult_spell: float; dot_can_crit: bool

@dataclass(frozen=True)
class Racials:            # racials.json
    sword_crit: Mapping[str, float]; spirit_pct: Mapping[str, float]; mana_pct: Mapping[str, float]  # par race

@dataclass(frozen=True)
class GameData:
    game_version: str; spells: Mapping[str, Spell]; talents: Mapping[str, Talent]
    talent_at: Mapping[tuple[str, int, int], str]; trees: tuple[str, ...]
    rules: CombatRules; constants: Constants; racials: Racials

class CharacterOverrides(TypedDict, total=False):
    intellect: float; spirit: float; sp: float; base_mana: float; mana: float; spell_crit: float
    crit_gear: float; sword: bool; hit_gear: float; haste: float; hp: float; armor: float

@dataclass(frozen=True)
class Character:
    level: int; race: str; intellect: float; spirit: float; sp: float; base_mana: float; mana: float
    crit: float; hit_gear: float; haste: float; hp: float; armor: float; spirit_regen: float   # mana/s
    overrides: CharacterOverrides

class Buffs(TypedDict, total=False):
    crit: float; dmg: float; haste: float; cost: float; sp_pct: float; sp_flat: float

class CastEstimate(TypedDict):
    key: str; rank: Rank; school: str; hit: float; crit: float; crit_mult: float; dmg_mult: float
    dmg: float; direct_per_hit: float; dot: float; ignite: float; mana: float; cast_s: float
    range_yd: float; cooldown_s: float
```
`Constants` regroupe des sous-types gelés lus dans `mechanics.json` : `CoefficientRules`, `CharacterModel`, `TalentRules`, `crit_per_winters_chill_stack`, `talent_rank_mana_ratio`, `talent_rank_mana_default`, `default_range_yd`.

### Fonctions du moteur (pures, `gd: GameData` en premier ; docstring « Registre : <id> »)
```python
talent_value(gd, pts, key, i=0, default=0.0) -> float          # valeur i du rang pris ; rang borné au nombre de rangs
points_available(gd, level, talented_bonus=0) -> int            # max(0, level - (first_level - 1) + bonus)
check_build(gd, pts, level, talented_bonus=0) -> list[str]      # erreurs en français, [] si légal
legal_additions(gd, pts, level, talented_bonus=0) -> list[str]  # ordre de talents.json
tree_split(gd, pts) -> dict[str, int]                           # arbres lus dans les données
int_per_crit(gd, level) -> float
character(gd, level, race="Orc", overrides=None) -> Character
best_rank(gd, key, level, pts) -> Rank | None
coefficient(gd, key, rank) -> float
hit_chance(gd, school, level_diff, pts, ch) -> float
crit_chance(gd, key, school, pts, ch, *, frozen=False, wc_stacks=0, buffs=None) -> float
crit_mult(gd, school, pts) -> float
dmg_mult(gd, school, pts, buffs=None) -> float
spell_power(ch, buffs=None) -> float
cast_time(gd, key, rank, pts, ch, buffs=None) -> float
mana_cost(gd, key, rank, pts, ch, buffs=None) -> float
expected_cast(gd, key, level, pts, ch, level_diff=0, *, frozen=False, wc_stacks=0, buffs=None,
              frozen_mult=True) -> CastEstimate | None
```
Le lien talent → effet (Elemental Precision sur givre et feu, Incineration sur ses 4 sorts, Winter's Chill sur Frostbolt et Ice Lance, Improved Frostbolt/Fireball) reste dans le code : c'est la formule, pas un chiffre.

### `mechanics.json` (rédigé, haché comme les autres)
```json
{"schema_version": 1, "game_version": "1.60.1.70009",
 "source": "Portage de seed/forever-mage/scripts/fm.py (T02) ; règles détaillées dans seed/forever-mage/references/mechanics.md",
 "values": {
  "coefficient.cast_divisor":          {"value": 3.5,    "certainty": "suppose", "registry": "G4", "source": "règle Classic (PC)"},
  "coefficient.cast_bounds_s":         {"value": [1.5, 3.5], "...": "..."},
  "coefficient.slow_factor":           {"value": 0.95, "...": "..."},
  "coefficient.channel_cap_s":         {"value": 5.0, "...": "..."},
  "coefficient.low_level":             {"value": {"threshold": 20, "penalty_per_level": 0.0375}, "...": "..."},
  "coefficient.fixed":                 {"value": {"fire_blast": {"cast_s": 1.5}, "scorch": {"cast_s": 1.5},
                                         "ice_lance": {"value": 0.1429}, "cone_of_cold": {"value": 0.143, "slowed": true},
                                         "arcane_explosion": {"value": 0.143}, "frost_nova": {"value": 0.043},
                                         "blast_wave": {"value": 0.143}, "blizzard": {"value": 0.333},
                                         "flamestrike": {"value": 0.157}}, "...": "..."},
  "talents.first_level":               {"value": 10, "certainty": "certain", "registry": "G3", "...": "..."},
  "talents.points_per_tier":           {"value": 5, "...": "..."},
  "character.crit_base":               {"value": 0.002, "registry": "A5", "...": "..."},
  "character.int_per_crit":            {"value": {"level_min": 1, "at_min": 6.0, "level_max": 60, "at_max": 59.5}, "registry": "A5", "...": "..."},
  "character.intellect":               {"value": {"base": 21, "per_level": 1.76, "late_bonus_per_level": 0.8, "late_from_level": 5}, "registry": "G2", "...": "..."},
  "character.spirit":                  {"value": {"base": 22, "per_level": 1.66, "late_bonus_per_level": 0.5, "late_from_level": 5}, "...": "..."},
  "character.spell_power":             {"value": {"per_level": 0.4, "from_level": 10}, "...": "..."},
  "character.base_mana":               {"value": {"base": 100, "per_level": 18.9}, "registry": "B9", "...": "..."},
  "character.mana_from_intellect":     {"value": {"first_points": 20, "per_point_after": 15}, "registry": "B9", "...": "..."},
  "character.hp":                      {"value": {"base": 40, "per_level": 12, "per_level_squared": 0.25}, "...": "..."},
  "character.armor":                   {"value": {"agility_base": 20, "agility_per_level": 0.5, "armor_per_agility": 2, "per_level": 4}, "...": "..."},
  "character.spirit_regen":            {"value": {"base": 13, "spirit_divisor": 4, "tick_s": 2}, "registry": "G2", "...": "..."},
  "crit.winters_chill_per_stack":      {"value": 0.02, "certainty": "certain", "registry": "D4", "...": "..."},
  "mana.talent_rank_cost":             {"value": {"ratio_of_next_rank": 0.75, "default": 50.0}, "certainty": "suppose", "registry": "B11",
                                        "source": "estimation du seed (EST) ; voir OPEN_QUESTIONS"},
  "spell.default_range_yd":            {"value": 30, "certainty": "suppose", "registry": "C2", "...": "..."}}}
```
Chaque entrée porte `value`, `certainty` (`certain`, `probable` ou `suppose`, reprise du statut FC/FS/PC/EST de `fm.py` et de `references/mechanics.md`), `registry` et `source`. Les coefficients fixes de Fire Blast et Scorch sont décrits par leur durée équivalente (1,5 s ÷ diviseur) et celui de Cone of Cold par `slowed: true`, pour reproduire les opérations exactes du seed. `build_game_data` lève `DataSchemaError` si une clé attendue manque ou n'a pas le bon type.

### Registre (`forever/registry.py`)
```python
STATUSES = ("absent", "modelise", "teste", "valide-journal", "valide-jeu")
@dataclass(frozen=True)
class Mechanic: id; category; description; forever; status; certainty; sources: tuple[str, ...]
                tests: tuple[str, ...]; tolerance: object; formula: str | None; note: str | None
def load(path: Path) -> list[Mechanic]                     # lève RegistryError si illisible
def validate(path: Path, repo_root: Path, *, strict: bool, engine_dirs: Sequence[Path] = ...) -> ValidationReport
                                                            # errors: list[str], warnings: list[str], counts
def implementations(dirs: Sequence[Path], repo_root: Path) -> dict[str, list[str]]   # id -> ["forever/engine/crit.py::crit_chance"]
def find_entry(mechanics: Sequence[Mechanic], mechanic_id: str) -> Mechanic          # casse ignorée ; UnknownMechanicError
def coverage(path: Path) -> str                             # inchangé
def main(argv: Sequence[str]) -> int                        # sortie identique à l'actuelle + nouvelles erreurs
```
Règles de `validate` : les règles actuelles, plus les suivantes :
- une référence `::nom` doit désigner une fonction ou une classe définie dans le fichier (`ast`, suffixe `[param]` ignoré) ;
- les chemins hors de `tests/` sont refusés, `seed/` compris ;
- `teste` ou mieux exige au moins une référence `::nom` ;
- `modelise` sans test est une erreur en mode strict ;
- `formule` ne contient aucun nombre isolé autre que 0 et 1 (regex `(?<![\w.])\d+(?:[.,]\d+)?(?![\w])`, correspondances `0` et `1` admises) : la formule de A5 (« bornée à [0, 1] ») passe, « 1,5 » ou « 3.5 » échouent ;
- tout identifiant cité en docstring (`Registre : X`) dans `forever/engine/` doit exister dans le registre ;
- une entrée `teste` de catégorie A à H doit avoir au moins une implémentation citée dans le moteur.

### Explication (`forever/explain.py`)
```python
class MechanicParameter(TypedDict): key: str; value: object; certainty: Certainty; source: str
class MechanicExplanation(TypedDict):
    id: str; category: str; description: str; forever: str; status: str; certainty: Certainty
    formula: str | None; note: str | None; parameters: list[MechanicParameter]
    implementations: list[str]; sources: list[str]; tests: list[str]; provenance: Provenance
def explain_mechanic(deps: Deps, mechanic_id: str) -> MechanicExplanation
```
- Paramètres : les entrées de `mechanics.json` dont `registry` vaut l'identifiant, plus les règles de `combat_rules` associées par une table de `gamedata.py` (A3 → `spell_miss_by_level_diff`, `min_miss` ; B1 → `gcd` ; A21 → `crit_mult_spell` ; A17 → `dot_can_crit`), avec la certitude du champ.
- Entrée `absent` : explication rendue, `formula` None, hypothèse « mécanique non modélisée dans forever-core ».
- Registre introuvable : `DataSchemaError`.

Sortie texte de `forever explain-mechanic A5` :
```
A5 — Critique unifié ; critique des sorts par Intellect et niveau
Statut teste · certitude probable · Forever : modifié
Formule : crit = crit_base + Int / int_par_crit(niveau) + crit_équipement + talents (…) + buffs, bornée à [0, 1]
Paramètres (version 1.60.1.70009) :
  character.crit_base = 0.002 (suppose) — …
  character.int_per_crit = {…} (suppose) — …
Implémentation : forever/engine/character.py::character, forever/engine/crit.py::crit_chance
Sources : …
Tests : tests/unit/test_engine_mechanics.py::…, tests/unit/test_engine_character.py::…
Provenance · version 1.60.1.70009 · … · certitude suppose · registre 21/101 · …
```

### CLI et MCP
- `forever explain-mechanic <id> [--json]` : code 0 ; identifiant inconnu → 4 (`unknown_mechanic`, suggestions) ; données altérées → 3.
- `forever_explain_mechanic(mechanic_id: str) -> MechanicExplanation` ; erreur → `CallToolResult(is_error=True)` avec erreur et provenance structurées (décision 12).

### Registre après T02 (statuts)
| Statut | Entrées |
| --- | --- |
| `teste` (21) | A3, A4, A5, A17, A18, **A20**, **A21**, B1, B2, B9, B11, B12, **B16**, **B17**, **C2**, D4, **G1**, **G2**, G3, G4, H1 |
| `modelise` (1) | J1 (inchangé) |
| `absent` ← `modelise` / `teste` (10) | B6, B7, B13, C1, C5, H2, I1, I5 (T04 ou T05) ; I6, J2 (T04) |

Nouvelles entrées :
- **A20** : multiplicateurs de dégâts des sorts (talents d'école, bonus globaux) ;
- **A21** : multiplicateur de critique des sorts et talents qui l'augmentent ;
- **B16** : temps d'incantation réduits par talents ;
- **B17** : réductions et remboursements de coût (Frost Channeling, Master of Elements).

Couverture : 16/97 → **21/101**.

Notes de périmètre :
- A4 : poisons et pièges hors Mage ;
- A18 : espérance seule, cumul et rafraîchissement en T04 ;
- B11 : escalade d'Arcane Blast en T04 ;
- C2 : portée de base ; talents de portée en T04 (implémentation citée : `forever/engine/cast.py::expected_cast`, champ `range_yd`, repli `spell.default_range_yd`) ;
- G1 : passifs Humain et Gnome seulement ;
- G3 : 4e talent doré non modélisé.

Correspondance des 30 contrôles (`MECHANICS`) :

| Identifiant | Contrôles |
| --- | --- |
| A3 | toucher/écart de niveau, plafond de toucher |
| A4 | Elemental Precision, Arcane Focus |
| A5 | critique Int/niveau, critique d'équipement, Arcane Instability, Critical Mass, Arcane Impact, Incineration, Shatter (gelé) |
| G1 | critique épée Humain |
| D4 | Winter's Chill |
| A21 | multiplicateur de critique, Ice Shards, Arcane Mind |
| A17 | DoT qui critiquent |
| A18 | Ignite |
| A20 | Piercing Ice, Fire Power |
| G4 | coefficients, pénalité < 20 |
| B16 | Improved Frostbolt, Improved Fireball |
| B2 | hâte |
| B1 | temps de recharge global |
| B17 | Frost Channeling, Master of Elements |
| B12 | Arcane Concentration |
| B11 | sorts en % du mana de base |

B9, C2, G2, G3 et H1 sont couverts par les tests de personnage, de talents et de valeurs.

## Tests à écrire d'abord (phase rouge)
Toutes les valeurs de jeu citent `seed/forever-mage/tests/run_all.py`, `seed/forever-mage/data/1.60.1.70009/*.json`, ou « calculé avec `seed/forever-mage/scripts/fm.py` le 2026-09-27 ». Personnage de référence du seed : `CH = character(gd, 60, "Orc", {"sp": 500, "spell_crit": 0.10})`, niveau 60. Fixture de session `game_data` dans `tests/conftest.py` (données du dépôt). Aucun réseau.

| Fichier | Tests et valeurs attendues |
| --- | --- |
| `tests/unit/test_gamedata.py` | arbres `{"Arcane": 18, "Fire": 17, "Frost": 19}` ; au moins 15 sorts ; frostbolt rang 2 = `Rank(2, 8, 34, 38, 0, 0, 1.8, 35, 0)` ; fireball rang 3 = `(12, 48, 66, 6, 6, 2.5, 65, 0)` ; `iceLance.ranks == ((26, 30, 300),)` ; premières valeurs d'improvedFrostbolt `[0.1, 0.2, 0.3, 0.4, 0.5]` ; shatter 17 → 50 ; `racials.sword_crit["Human"] == 0.02`, `mana_pct["Gnome"] == 0.05` ; clé manquante dans une copie de `mechanics.json` → `data_schema` ; données altérées → `data_integrity` |
| `tests/unit/test_engine_talents.py` | `prerequis` : fingersOfFrost→iceLance, arcanePower→presenceOfMind, hotStreak→pyroblast, combustion→criticalMass, iceBarrier→coldSnap. `legalite` : `{improvedFrostbolt 5, iceLance 1}` au niveau 20 → erreurs ; `{improvedFrostbolt 5, elementalPrecision 2, frostbite 3, iceLance 1}` → `[]` au niveau 20, erreurs au niveau 19 ; `improvedFrostbolt 6` → erreur. `points_available(20) == 11`, `(9) == 0`. `legal_additions({}, 10)` → les 9 talents de palier 1 (wandSpecialization, arcaneFocus, improvedChanneling, wakeOfFire, incineration, improvedFireball, frostWarding, improvedFrostbolt, elementalPrecision). `tree_split({improvedFrostbolt 5, arcaneFocus 2}) == {"Arcane": 2, "Fire": 0, "Frost": 5}`. `talent_value` : talent absent → défaut ; rang supérieur au nombre de rangs → dernier rang |
| `tests/unit/test_engine_character.py` | `character(60, "Orc")` : intellect 168.84, spirit 147.44, sp 24.0, base_mana 1215.1, mana 3467.7, crit 0.030376 (±1e-6), hp 1660, armor 340, spirit_regen 24.93 ; `character(12, "Gnome").mana == 753.165` ; `int_per_crit` : niveau 1 → 6.0, 30 → 32.29661016949153, 60 → 59.5, bornes 0 → 6.0 et 70 → 59.5 ; surcharge `spell_crit 0.10` → crit 0.10 ; Humain : esprit ×1,05 par rapport à l'Orc ; `sword` → +0,02 de critique |
| `tests/unit/test_engine_values.py` | avec `CH` : frostbolt → hit 0.96, crit 0.1, crit_mult 1.5, direct_per_hit 926.25, dmg 889.2, mana 290, cast_s 3.0, range_yd 30 ; fireball → dot 63.0, dmg 1051.344 ; arcane_blast (talent pris) → mana 182.265 = 0,15 × 1215.1 ; pyroblast rang 1 → mana 112.5 (0,75 × 150, estimation) ; hit à +3 → 0.83, à +7 → 0.61, à −2 → 0.96 ; `coefficient` frostbolt rang 2 → 0.26871428571428574, rang 11 → 0.8142857142857142 ; frostbolt rang 2 avec improvedFrostbolt 3 → cast 1.5 (plancher GCD) ; C2 : range_yd frostbolt 30, fireball 35, fire_blast 20 (spells.json), frost_nova sans portée → 30 (`spell.default_range_yd`, suppose) ; ice_lance sans talent → `None` ; ice_lance avec talent au niveau 20 → rang 1 |
| `tests/unit/test_engine_mechanics.py` | **critère 1** : les 30 contrôles de `couverture_mecaniques`, paramétrés par libellé, avec les mêmes expressions et les égalités exactes du seed (`hit == 0.99`, `crit_mult == 1.5` et `2.0`, `cast == 2.5`, `3.0`, `1.5`, `coefficient == 3.0 / 3.5 * 0.95`, mana d'Arcane Blast à 1e-6 de 0,15 × base_mana) ; `set(MECHANICS) == set(CHECKS)` (30) ; chaque identifiant de `MECHANICS` existe dans le registre, a le statut `teste` et référence ce fichier |
| `tests/parity/test_fm_parity.py` | import du `fm.py` du seed (`importlib`, version `1.60.1.70009` explicite). Grille : 15 sorts × niveaux {10, 20, 40, 60} × 6 jeux de talents (vide, givre, feu, arcane, talents de sort, tout au maximum légal du seed) × écart {0, 3} × gelé {non, oui} × Winter's Chill {0, 5} × buffs {aucun, tous}. Chaque champ d'`expected_cast` est égal au seed (tolérance relative 1e-12, rang comparé champ par champ). `character` égal sur niveaux 1-60 × 5 races × avec et sans surcharges. `check_build` et `legal_additions` égaux sur 20 builds |
| `tests/unit/test_registry.py` | le registre du dépôt est valide en mode strict (`errors == []`) ; **critère 2** : chaque entrée `teste` a au moins une référence `::nom` qui existe ; une fixture par défaut, chacune signalée : champ manquant, doublon, statut inconnu, `teste` sans test, fichier introuvable, fonction introuvable, chemin `seed/`, `modelise` sans test (erreur en strict, avertissement sinon), `formule` chiffrée, faux moteur citant `Registre : Z99` ; `find_entry("a5").id == "A5"` ; `coverage` du dépôt `== "21/101"` (seul test qui fige cette valeur) ; formule avec `0` et `1` acceptée, avec `1,5` refusée ; `main(["--strict"])` → 0 sur le dépôt |
| `tests/unit/test_explain.py` | **critère 3** : `explain_mechanic(deps, "A5")` → certainty `probable`, formule non vide sans nombre, paramètres `character.crit_base` (0.002) et `character.int_per_crit`, sources non vides, implémentations contenant `forever/engine/crit.py::crit_chance` et `forever/engine/character.py::character`, tests non vides, provenance valide avec certitude `suppose`. `"a5"` accepté. `"Z9"` → `unknown_mechanic` (code 4, suggestions). `"A1"` → statut `absent`, formule `None`, hypothèse « non modélisée ». CLI texte : « A5 », « Formule », « certitude probable », « Sources », provenance en dernière ligne. `--json` se parse |
| Tests T01 modifiés | `test_contract.py` : `explain-mechanic A5` et `explain-mechanic Z9` × {texte, `--json`} ; `test_mcp.py` : 3 outils, `forever_explain_mechanic` A5 → contenu structuré et provenance valide, Z9 → `is_error` ; `test_mcp_stdio.py` : 3 outils ; `test_cli.py`, `test_provenance.py` : comparaison à `coverage(REGISTRY_PATH)` au lieu du littéral `16/97` ; `test_data_import.py` : + `mechanics.json` ; `test_manifest.py` : 10 fichiers |

## Étapes (session `/tranche T02`, dans un worktree, sur une branche)
1. **Squelettes** : `forever/engine/*`, `gamedata.py`, `explain.py`, nouvelles erreurs, signatures de `registry.py`, avec des corps `raise NotImplementedError` et des types complets (mypy strict vert). `mechanics.json` rédigé, bloc ajouté dans `sources.json`, puis `uv run forever manifest --update` (Bash, jamais Write). Commit `T02: squelettes du moteur et constantes de mécaniques`.
2. **Tests rouges** : fixtures, fixture `game_data`, tous les tests du tableau, modifications des tests T01. Chaque test échoue pour la bonne raison (`NotImplementedError`, valeur de couverture, outil absent). Écrire `tasks/.rouge` et `tasks/.tests-verrouilles`. Commit `T02: tests`.
3. **Vert, bloc par bloc**, un commit par bloc (`T02: <bloc>`) : `gamedata` → `talents` → `character` → `spells` → `hit`/`crit` → `damage`/`casting`/`mana` → `cast` → parité → `registry` (validation) → registre YAML (statuts, tests, sources, formules, notes, A20, A21, B16, B17) → `explain` → CLI → MCP.
4. `tasks.py` : `STRICT_REGISTRY = True` ; `scripts/check_registry.py` devient une enveloppe ; `uv run tasks.py registry` vert.
5. **Documentation** :
   - `ROADMAP.md` : T02 porte les 5 tests du moteur ; T04 reprend `analytique_proche_du_monte_carlo`, `calibrage_cible_blizzard` et `monte_carlo_reproductible` ; T05 reprend `optimiseur_legal` et `pvp_et_respec`.
   - `ARCHITECTURE.md` : `GameData`, `mechanics.json`, champs `formule` et `note` du registre.
   - `DECISIONS.md` : décisions 1 à 5 et décisions techniques, en lignes 25 et suivantes ; `GameData` mono-classe (Mage) en T02, espace par classe à prévoir en T12.
   - `OPEN_QUESTIONS.md` : voir « Questions ouvertes à ajouter ».
6. Supprimer `tasks/.rouge` et `tasks/.tests-verrouilles` ; sous-agent `auditeur-mecaniques`, puis `relecteur` ; `/verifier` ; push de la branche ; CI Ubuntu et Windows verte ; fusion fast-forward dans `main` (pièges du skill).
7. Résumé final : Bloqué sur moi, Fait, Tests ajoutés, Registre modifié, Questions ouvertes.

## Questions ouvertes à ajouter (`docs/OPEN_QUESTIONS.md`)
- École Givre-feu comptée à la fois en givre et en feu : double bénéfice des talents ; pour le multiplicateur de critique, la branche givre (Ice Shards) l'emporte. À vérifier en jeu.
- Winter's Chill : source de +2 % de critique par cumul dans Forever.
- `int_per_crit` entre les niveaux 1 et 60 : interpolation linéaire estimée ; remplacer par la table du client.
- Modèle de personnage : `leveling.json.player_model` (texte) omet les termes `0,8 × max(0, niveau − 5)` (Int) et `0,5 × max(0, niveau − 5)` (Esprit), que `fm.py` applique. Le code du seed fait foi pour la parité.
- (existante) Coût en mana des rangs issus de talents : repli estimé à 0,75 × rang suivant, sinon 50.

## Hors périmètre
- Simulateurs Monte Carlo et analytique, régénération, recul, projectiles, déplacements (T04) ; optimiseur, respec, PvP (T05) ; raid (T09).
- Les 5 tests du seed qui en dépendent (reportés, voir la décision 1).
- Nouvelles règles de jeu : aucune formule n'est ajoutée ou corrigée par rapport à `fm.py`, même quand elle semble discutable. Ce type d'écart part dans les questions ouvertes.
- Conversion notation → pourcentage (hâte, critique, toucher), résistances, armure de la cible.
- Refonte de `lookup.py` sur `GameData` (possible plus tard).

## Risques
| Risque | Parade |
| --- | --- |
| Écart numérique avec le seed (ordre des opérations, conversions int/float) | Ordre de `fm.py` conservé ; égalités exactes des 30 contrôles ; test de parité à 1e-12 ; constantes stockées pour reproduire les mêmes opérations (1,5 ÷ 3,5, 0,143 × 0,95) |
| Import du `fm.py` du seed dans les tests (état global, chemins) | Import isolé par `importlib` dans le seul test de parité ; version explicite ; lecture seule |
| Rétrogradations jugées comme une perte d'information | `note` renvoyant à T04/T05 ; reprise prévue dans la feuille de route |
| `teste` sur une couverture partielle (A18, B11, G1, G3) | `note` de périmètre affichée par `explain-mechanic` ; relue par `auditeur-mecaniques` |
| Littéraux de jeu oubliés dans le moteur | Test de parité avec des données modifiées : dans une copie de `mechanics.json`, `cast_divisor` passé à 4.0 doit changer `coefficient` (preuve que la valeur vient des données) ; relecture ciblée des littéraux par `relecteur` |
| Tests T01 à modifier | Liste fermée ci-dessus ; justification dans le message de commit ; aucun fichier `tests/golden/` touché |
| mypy strict sur les données JSON | Conversion typée dans `gamedata.py` (seul endroit qui touche au JSON brut) ; `DataSchemaError` sur tout écart |
| Hook `protect_golden.py` et `manifest.json` | Génération uniquement par `uv run forever manifest --update` |

## Accords donnés (2026-09-27)
1. Décision 1 : 5 tests du seed reportés en T04/T05, feuille de route corrigée.
2. Décision 2 : nouveau fichier de données `forever/data/1.60.1.70009/mechanics.json`, modification de `sources.json` et du manifeste.
3. Décision 3 : rétrogradation en `absent` de 10 entrées, promotion de G1, G2 et C2, ajout de A20, A21, B16, B17 (couverture 16/97 → 21/101).
4. Modification des tests T01 listés (valeurs de couverture, liste des fichiers de données, jeu d'outils MCP, cas de contrat).
5. Aucune dépendance ajoutée, aucun accès réseau.

Ajustements demandés à la validation : formules du registre limitées aux nombres 0 et 1 ; C2 reste `teste` (portée de base) ; valeur exacte de couverture figée seulement dans `test_registry.py` ; `GameData` mono-classe notée dans DECISIONS.md (espace par classe en T12).

## Critères de fin vérifiables
1. `uv run pytest tests/unit/test_engine_mechanics.py -q` : les 30 contrôles passent avec les expressions du seed. `uv run pytest tests/parity -q` : parité avec `fm.py`.
2. `uv run pytest tests/unit/test_registry.py -q` : chaque entrée `teste` pointe vers une fonction de test qui existe. `uv run tasks.py registry` est vert en mode strict.
3. `uv run forever explain-mechanic A5` affiche la formule, `certitude probable`, les paramètres de la version 1.60.1.70009, les sources et une ligne provenance. Avec `--json`, provenance valide. L'outil MCP `forever_explain_mechanic` répond de même.
4. `uv run forever status` affiche `registre 21/101`.
5. `uv run tasks.py verify` est vert en local (Windows) ; les jobs CI `ubuntu-latest` et `windows-latest` sont verts sur la branche.
