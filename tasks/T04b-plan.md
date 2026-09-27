# T04b — Leveling : seconde fixture de journal, modèle de PV Questie → Forever, simulateurs, MCP, graphique : plan

> Plan rédigé le 2026-09-27 (session de cadrage en arrière-plan). **Décisions 1 à 6 à valider par l'utilisateur** (recommandation en gras). Exécution : `/tranche T04b` dans une nouvelle session, sur la branche `t04b`.

## Contexte
T04a a livré la lecture des journaux, les mesures, `monsters.json` (21 PNJ mesurés, Questie en regard), `spell_scaling.json` et `rank_values_at_level`. L'utilisateur demande pour T04b : **d'abord** une seconde fixture anonymisée tirée du second journal réel, pour B1 et A3 ; puis le portage de `seed/forever-mage/scripts/sim_leveling.py` (Monte Carlo à impacts différés et modèle analytique) avec les PV mesurés par défaut (`mob_source`), les dégâts au niveau du personnage (`spell_level`), les 3 tests du seed reportés, l'outil MCP `forever_sim_leveling`, `forever chart leveling`, un **modèle de correction Questie → Forever par niveau** pour les monstres jamais mesurés, et la remontée du registre.

## Constats (relevés le 2026-09-27, lecture seule du client, hors tests)

### Second journal réel : `Logs/WoWCombatLog-092726_150346.txt`
- **25 902 lignes** aujourd'hui (6,4 Mo, 15:03:46 → 16:48:23, les Tarides, `uiMapID` 1413) : le fichier a grossi depuis T04a (10 713 lignes). Lecture complète en 0,35 s, mesures en 0,03 s. Événements inconnus : `ENCHANT_APPLIED`, `ENCHANT_REMOVED`.
- **Intervalles entre instantanés (B1)** : sans filtre, 89 (10 000 lignes) à 98 (journal entier), minimum parasite 0,001 s (Shoot 5019, sorts hors recharge globale). **Filtrés aux sorts sous recharge globale** (`SpellCooldowns.StartRecoveryTime` = 1500 dans les fixtures wago pour 122, 145, 837, 1449, 2137) : **42** sur les 10 000 premières lignes (c'est « environ 40 »), **47** sur le journal entier ; minimum 1,414 s, médiane 1,51 s, 20 des 47 sous 1,5 s (gigue d'horodatage probable). Avec les 3 intervalles de la première fixture : 45 ou **50** (`tolerance.n_min` de B1 : 50).
- **Ratés (A3) : la prémisse « 22 ratés » ne tient pas.** Les 22 « ratés » des 10 000 premières lignes sont des `SWING_MISSED … MISS` de créatures (mêlée), pas des ratés de sort du Mage. Le Mage a **1 seul** `SPELL_MISSED` : Chilled (6136, effet d'Armure de givre, pas un sort lancé), et **0 raté sur 281 sorts directs** (Frostbolt 101, Arcane Explosion 132, Frost Nova 24, Fire Blast 23, Fireball 1 ; plus 53 tirs de baguette `RANGE_DAMAGE`, table de toucher distincte). **Toutes les cibles sont 2 à 8 niveaux sous le Mage** : aucune case d'écart ≥ 0, A3 n'est pas mesurable avec ce journal. Observation utile néanmoins : la ligne « - » (cible plus basse) de `leveling.json.combat_rules.spell_miss_by_level_diff` vaut 4 % ; 0 raté sur 281 est très improbable à 4 % sans talent de toucher (0,96^281 ≈ 1e-5), plausible au plancher de 1 % (0,99^281 ≈ 6 %) ; talents du Mage inconnus.
- **Niveau du lanceur** : aucun `ForeverLoggerDB` sur disque (addon réinstallé à 17:14, après le journal). Le dernier champ du bloc avancé du joueur vaut 7 puis 8 (pas le niveau). Le **carnet de Questie** (`WTF/Account/<compte>/SavedVariables/Questie.lua`, clé `journey`, événements `Level` horodatés du Mage) donne **14 jusqu'à 15:17:26, puis 15** ; recoupé par le journal : PV max du Mage 347 → 362 entre 15:17:12 et 15:22:01. `hit_tally` actuel ne prend qu'un niveau par journal (question ouverte de T04a).
- **Monstres** : 29 observations (PNJ, niveau) sur le journal entier, 21 sur les 10 000 premières lignes, 0 conflit ; coûts relevés identiques à `spells.json` (837 : 50, 145 : 65, 1449 : 75, 2137 : 75, 122 : 55…).

### PV : Questie sous-estime Forever dès le niveau 10
Rapport PV mesuré / PV Questie (paires PNJ × niveau de `monsters.json`, médiane par niveau, Sarilus Foulborne exclu) : L1, L6, L7 **1,00** ; L10 1,0505 (3 paires) ; L11 1,0766 (7) ; L12 1,1012 (7) ; L13 1,1245 (6) ; L14 1,15 (3) ; L15 1,1738 (1) ; L17 1,2254 (1). Presque linéaire : droite des moindres carrés sur les médianes > 1 → pente ≈ 0,0248 par niveau, genou ≈ 7,95. Contrôle : L16 (Questie seul, 356) corrigé → 427, entre les mesures 385 (L15) et 473 (L17). Extrapolé : ≈ 1,30 à L20, 1,55 à L30, 2,29 à L60. Écarts : Sarilus Foulborne (3986, L25, 927 contre 573, rapport 1,62, PNJ de quête) hors droite ; Sunscale Lashtail (3254, L13, 246) a son propre niveau de PV mais un rapport normal (1,128). Les PNJ lanceurs de sorts (Geomancer, Toxicologist, Acolyte) ont des PV Questie plus bas que leurs voisins et la même valeur mesurée : Forever semble donner une valeur commune par niveau.

### Simulateur du seed
- Références (`repr()`, seed, `mob_source="seed"`, `spell_level="rank"`, Orc) : L12 frost `improvedFrostbolt=3`, n = 600, graine 12345 → MC total 25.51026932538584, combat 11.716904761904743 ; analytique total 23.85926190796625. L16 frost (IF 5, EP 2) : MC 29.895997677896577, analytique 28.543428650870247. L24 frost (IF 5, EP 3, Frostbite 3, Ice Lance, FC 3) : MC 32.33266309936493, analytique 32.16470423598942. L16 fire (IFb 5, EP 2) : MC 30.93969370799394, analytique 27.871038699049066 (écart 9,9 %). Calibrage L20 combat 14.127405952380936. Reproductibilité L16 IF 5, n = 200, graine 1 → 30.435373555182213. L12 n = 1500 (défaut de `mc`) → total 25.48655329665798, xp_h 14897.22498356594. 0,1 s par tranche de 600 combats.
- **Chiffres codés en dur dans `sim_leveling.py`** (à déplacer dans les données, `leveling.json` et `spells.json` restant des copies octet pour octet du seed) : dégâts d'un coup de monstre `0,8 L + 0,02 L²` ; armure `A / (A + 400 + 85 L)` ; XP `45 + 5 L` ; gel de Frostbite 5 s ; tic de DoT toutes les 2 s ; Ignite en 2 tics de 2 s ; recul à 10 m après Frost Nova ; régénération de vie au repos `0,02 × PV` ; seuil de Mage Armor 34 (déjà dans `utility.mage_armor.ranks`) ; vitesse de projectile par défaut 28 (analytique) et « infinie » (MC) ; analytique : fraction minimale d'incantation 0,2, plafond de gel 0,95, empilements moyens de Winter's Chill sur 3 lancers ; options par défaut (`level_diff` 0, `nova_break` 1,0, `run_between` 6 s). Pas numérique 0,05 s et garde de 500 lancers : paramètres de méthode, pas des chiffres de jeu.
- `GameData` n'expose ni `mob_model`, ni `utility`, ni `pushback_s` / `five_second_rule` ; `expected_cast` choisit toujours le rang de `spells.json`.
- Registre : `ENGINE_CATEGORIES` = A à H. B6, B7, B13, C1, C5 ne passent `teste` que si une fonction de `forever/engine/` les cite (`Registre : …`) : les formules du simulateur vont dans le moteur, `forever/sim/` n'orchestre que.
- H2 (« armure et résistances de la cible ») : le seed n'applique l'armure qu'aux coups du monstre sur le Mage ; la cible n'a ni armure ni résistance (`level_resist` non appliqué).

## Décisions (à valider)
| # | Décision | Recommandé | Alternative |
| --- | --- | --- | --- |
| 1 | Étendue de la seconde fixture | **Journal entier (25 902 lignes, 6,4 Mo)** : 47 intervalles filtrés (+3 = 50, B1 atteint `n_min`), 29 observations de monstres pour le modèle de PV | 10 000 premières lignes (≈ 2,5 Mo) : 42 intervalles (+3 = 45, B1 reste `teste`), 21 observations |
| 2 | Validation de B1 par journal | **Les preuves d'une même mesure se cumulent** (n total ≥ `n_min`) ; nouveau champ `tolerance.ecart_median_s` du registre (écart admis entre la médiane des intervalles et la recharge globale des données, valeur fixée par l'utilisateur, 0,05 s proposé) ; B1 passe `valide-journal`, certitude `probable`. Les intervalles sous 1,5 s (min 1,414) restent notés comme gigue d'horodatage | Chaque preuve seule doit atteindre `n_min` : B1 reste `teste` jusqu'à une campagne dédiée (protocole de `docs/ADDON.md`) |
| 3 | Niveau du lanceur (A3) | **Chronologie de niveaux** (instants et niveaux) lue dans `ForeverLoggerDB` **ou** dans le carnet `journey` de la SavedVariable Questie (données personnelles de l'utilisateur, lecture locale ; extension de la décision 3 de T04 qui ne visait que `Database/Classic/*.lua`) ; fixture : extrait minimal du carnet (événements `Level` seuls, personnage renommé) ; `hit_tally` prend le niveau à l'instant de chaque sort | `forever logs measure --caster-level N` (un seul niveau, saisi à la main) ; ou fixture `ForeverLoggerDB` synthétique écrite d'après le carnet |
| 4 | A3 au vu de la fixture 2 | **Aucune preuve A3** (aucune cible d'écart ≥ 0) ; observation « 0 raté sur 281 sorts directs, cibles 2 à 8 niveaux plus bas » en note de A3 et en question ouverte contre la ligne « - » à 4 % ; règle inchangée ; baguette et effets (Chilled) exclus de `hit_tally` | Remplacer dès maintenant la ligne « - » par la règle Classic (raté 4 % + écart, plancher 1 %) en `suppose` (règle de jeu : seulement sur votre décision) |
| 5 | Modèle de correction Questie → Forever | **Rapport par niveau** = médiane des rapports PV mesuré / PV Questie des PNJ normaux mesurés ; entre et au-delà des niveaux mesurés : droite des moindres carrés sur les médianes > 1, rapport = max(1, droite) ; appliqué à la médiane Questie des niveaux jamais mesurés. **Certitude `probable` sur la plage mesurée (L6 à L17), `suppose` au-delà** (extrapolation jusqu'à ×2,3 à L60) ; Sarilus Foulborne exclu de l'ajustement (listé) ; inversions restantes de l'agrégat (L56, L60) listées, jamais lissées ; coefficients reconstruits par `forever monsters build` | `probable` à tous les niveaux, comme demandé ; ou formule directe PV(L) de Forever sans Questie (valeur commune par niveau) |
| 6 | Périmètre | **T04b = demande de l'utilisateur** (fixture 2, simulateurs, correction de PV, MCP, graphique, remontée du registre, C2 par Arctic Reach, A18 selon ce que le seed modélise : Ignite en 2 tics par critique). **Reporté en T04c** : quêtes propres à Forever (`QuestieForeverDB`) et modèle d'XP, cumul et rafraîchissement d'Ignite, escalade d'Arcane Blast (B11) : ce sont des modélisations nouvelles, pas des portages | Tout dans T04b, comme dans `ROADMAP.md` (au-delà de 3 sessions) |

Décisions techniques (sans arbitrage attendu) :
- **Filtre de recharge globale sans chiffre en dur** : `forever decode` ajoute `start_recovery_ms` (`SpellCooldowns.StartRecoveryTime`) à chaque rang de `spell_scaling.json` ; `gcd_intervals` ne retient qu'un intervalle entre deux sorts dont `start_recovery_ms` > 0 (ensemble passé par l'appelant, construit depuis `GameData`).
- **`hit_tally`** ne compte que les sorts du lanceur connus des données (identifiants de `spell_scaling.json`) : ni baguette (`RANGE_*`), ni effets déclenchés (Chilled).
- **Simulateurs** dans `forever/sim/` (`leveling_mc.py`, `leveling_analytic.py`, comme prévu par `docs/ARCHITECTURE.md`) ; toutes leurs formules dans `forever/engine/` (fonctions pures citant le registre). Ordre des tirages `rng.random()` identique au seed : la parité se teste à 1e-12, pas à ±1 %.
- **Constantes** : nouvelles clés `leveling.*` de `mechanics.json` (valeur, certitude, entrée du registre, source « sim_leveling.py du seed (EST) ») ; `leveling.json` et `spells.json` inchangés (`test_seed_files_are_byte_identical`).
- **`spell_level`** : `expected_cast(..., spell_level="rank")` par défaut (parité T02 inchangée) ; `"character"` remplace dégâts min, max et DoT du rang par `rank_values_at_level` au niveau du personnage.
- **`mob_source`** : `measured` (défaut) lit `monsters.json.hp_by_level` (mesure, puis Questie corrigé) ; `seed` interpole `leveling.json.mob_model.hp_anchors`. La provenance donne la valeur, sa source et sa certitude.
- **Graphique** : matplotlib (déjà en dépendance), moteur `Agg`, `metadata={"Software": None}`, taille et résolution fixes ; déterminisme testé en comparant deux générations dans le même test (pas d'empreinte codée : polices différentes entre Ubuntu et Windows).
- **Provenance du simulateur** : certitude = minimum des certitudes utilisées (PV du monstre, constantes `leveling.*`, règles du registre) ; hypothèses : `mob_source`, `spell_level`, source des PV au niveau simulé, talents.

## Existant réutilisé
- `forever/pipeline/combatlog.py`, `measure.py` (`gcd_intervals`, `hit_tally`, `measure_log`), `questie.py`, `lua_table.py`, `addon_sv.py`, `monsters.py` (`build_monsters`, `write_monsters`), `decode.py` (lecture de `SpellCooldowns`).
- `scripts/extract_combatlog_fixture.py` (anonymisation), `scripts/extract_questie_fixture.py` (extrait de PNJ, à étendre aux PNJ observés et au carnet).
- `forever/engine/` : `expected_cast`, `best_rank`, `cast_time`, `mana_cost`, `talent_value`, `character`, `spell_power`, `coefficient`, `check_build`, `rank_values_at_level`.
- `forever/gamedata.py::build_game_data`, `forever/engine/model.py` (`GameData`, `MonsterTable`, `CombatRules`), `forever/provenance.py`, `forever/cli.py::_emit`, `forever/mcp_server.py::build_server`.
- `tests/parity/test_fm_parity.py` (import du seed par `importlib`), `tests/conftest.py` (`make_deps`, `data_copy`, `write_manifest`).

## Fichiers
```
tests/fixtures/combatlog/WoWCombatLog-092726_150346.anon.txt   seconde fixture (décision 1), README.md complété
tests/fixtures/questie/11.38.0/classicNpcDB.lua                + PNJ observés dans les deux fixtures (extrait)
tests/fixtures/questie/journey/Questie.lua                     extrait du carnet (décision 3)
scripts/extract_questie_fixture.py                             + --ids, + --journey
forever/pipeline/measure.py        gcd_intervals (ensemble de sorts), hit_tally (chronologie, sorts connus)
forever/pipeline/levels.py         chronologie de niveaux (ForeverLoggerDB, carnet Questie)
forever/pipeline/questie.py        + read_journey
forever/pipeline/decode.py         + start_recovery_ms dans scaling
forever/pipeline/monsters.py       + fit_questie_correction, hp_by_level corrigé, schéma 2
forever/engine/monsters.py         PV par niveau et source, coup de monstre, armure, XP, correction Questie
forever/engine/movement.py         temps de vol (C1), course, ralenti, gel (C5)
forever/engine/casting.py          + recul d'incantation (B6), recharges et talents (B13)
forever/engine/mana.py             + régénération en combat et règle des 5 s (B7), repos (I6)
forever/engine/cast.py, spells.py  + spell_level
forever/engine/model.py, forever/gamedata.py   + LevelingModel (mob_model, utility, pushback, constantes leveling.*)
forever/sim/__init__.py, leveling_mc.py, leveling_analytic.py
forever/chart.py                   graphique de leveling (PNG)
forever/cli.py                     + sim leveling, chart leveling, logs measure --levels
forever/mcp_server.py              + forever_sim_leveling
forever/data/1.60.1.70009/mechanics.json, spell_scaling.json, monsters.json, manifest.json
tests/unit/test_measure_second_log.py, test_levels.py, test_monsters_correction.py, test_engine_leveling.py,
tests/unit/test_sim_leveling.py, test_chart.py, test_sim_cli.py
tests/parity/test_sim_leveling_parity.py
Tests modifiés : test_registry.py (total, coverage, main ; tolerance, cumul des preuves), test_contract.py (+ 2 commandes),
                 tests/integration/test_mcp.py (+ 1 outil), test_gamedata.py, test_monsters.py (schéma 2),
                 test_decode_spells.py et test_spell_scaling.py (start_recovery_ms), test_measure.py (filtre, sorts connus)
docs/MECHANICS_REGISTRY.yaml, ARCHITECTURE.md, DECISIONS.md (53 et suivantes), OPEN_QUESTIONS.md, ROADMAP.md,
docs/DATA_SOURCES.md (carnet Questie)
```

## Interfaces
```python
# forever/pipeline/levels.py
class LevelTimeline(NamedTuple): points: tuple[tuple[datetime, int], ...]; source: str   # croissante
    # level_at(t) -> int | None (None avant le premier point connu)
def from_logger_db(db: LoggerDB, guid: str) -> LevelTimeline
def from_questie_journey(sv: Path, character: str) -> LevelTimeline     # événements Level ; heure locale

# forever/pipeline/measure.py
def gcd_intervals(events, caster, *, max_gap_s: float, gcd_spells: frozenset[int] | None = None) -> list[float]
def hit_tally(events, caster, levels: LevelTimeline | int | None, *, known_spells: frozenset[int] | None = None) -> HitTally

# forever/pipeline/monsters.py
def fit_questie_correction(npcs: Mapping[int, ...], *, exclude: Collection[int] = ()) -> QuestieCorrection
    # {"levels": {L: {"ratio", "n_pairs"}}, "fit": {"slope", "intercept"}, "range": [min, max], "excluded": [...]}

# forever/engine/monsters.py      (Registre : H3 nouvelle entrée PV des monstres, I6, C5)
def questie_ratio(gd, level) -> tuple[float, str]                    # rapport, certitude (probable / suppose)
def corrected_questie_hp(gd, questie_hp: float, level: int) -> MonsterHp
def mob_hp(gd, level, mob_source: Literal["measured", "seed"] = "measured") -> MonsterHp
def mob_hit_damage(gd, level) -> float ; armor_reduction(gd, armor, attacker_level) -> float ; mob_xp(gd, level) -> float

# forever/engine/movement.py      (Registre : C1, C5)
def travel_time(gd, key, distance_yd) -> float ; mob_speed(gd, slowed: bool, slow: float) -> float

# forever/sim/leveling_mc.py, leveling_analytic.py   (Registre : I1, I6, J2)
class LevelingOptions(TypedDict, total=False): level_diff; nova; nova_break; run_between_s; mob_source; spell_level
class KillResult(TypedDict): combat; mana; taken; downtime; total; xp_h
def kill_mc(gd, level, pts, ch, rotation="frost", rng=None, **options) -> KillResult
def mc(gd, level, pts, race="Orc", rotation="frost", n=1500, seed=12345, over=None, **options) -> KillResult
def kill_analytic(gd, level, pts, race="Orc", rotation="frost", over=None, **options) -> KillResult

# forever/chart.py
def leveling_chart(gd, levels: range, pts, *, race, rotation, n, seed, options, out: Path) -> ChartResult
```

### CLI et MCP (texte français, `--json`, provenance sur chaque sortie, aucun réseau)
| Commande | Codes |
| --- | --- |
| `forever sim leveling --level L [--race R] [--rotation frost\|fire] [--talents k=v,…] [--n N] [--seed S] [--mob-source measured\|seed] [--spell-level character\|rank] [--level-diff D] [--nova]` | 0 ; 2 build illégal ou paramètre hors bornes |
| `forever chart leveling --out F.png [--from 10] [--to 30] [mêmes options]` | 0 ; 2 |
| `forever logs measure … [--levels F]` (ForeverLoggerDB ou Questie.lua) | inchangés |
| MCP `forever_sim_leveling(level, race, rotation, talents, n, seed, mob_source, spell_level, level_diff, nova)` → Monte Carlo, analytique, PV du monstre (valeur, source, certitude), provenance | erreur structurée |

Le graphique trace, par niveau, le temps par monstre (MC total et combat, analytique total) et l'XP par heure ; le marqueur de chaque niveau indique la certitude des PV ; un niveau où le build est illégal est omis et cité dans les hypothèses.

## Tests attendus (valeurs tirées des fixtures et du seed)
- **Seconde fixture** (`test_measure_second_log.py`) : en-tête 22 / avancé / `1.60.1` / 18 ; 25 901 événements ; joueur « à moi » unique (`Moi-Royaume`) ; `gcd_intervals` filtré : n = 47, min 1,414, médiane 1,51 (à 1 ms) ; sans filtre : 98, dont 0,001 ; 29 observations de monstres, 0 conflit ; coûts {837 : 50, 145 : 65, 1449 : 75, 2137 : 75, 122 : 55} ; `hit_tally` avec la chronologie du carnet : 281 touchés, 0 raté de table, écarts tous négatifs (−8 à −2) ; baguette et Chilled exclus. (Valeurs de la variante 10 000 lignes si la décision 1 la retient : 42 intervalles, 264 touchés, 21 observations.)
- `test_levels.py` : carnet de la fixture → 14 avant 15:17:26, 15 après ; `ForeverLoggerDB` d'exemple → même interface ; `level_at` avant le premier point → None.
- `test_measure.py` (modifié) : `gcd_intervals` ignore un sort hors de `gcd_spells` ; `hit_tally` ignore un `RANGE_MISSED` et un effet absent des données ; niveau changeant en cours de journal → écart recalculé.
- `test_registry.py` : preuves cumulées sous `n_min` refusées, au-dessus acceptées ; `ecart_median_s` dépassé refusé ; B1 (3 + 47) accepté en `valide-journal` si la décision 2 est retenue ; comptes `total` 102 → 103 (H3), `coverage` recalculée.
- `test_monsters_correction.py` : sur les fixtures (deux journaux, extrait Questie étendu) : rapports médians L10 1,0505, L11 1,0766, L12 1,1012, L13 1,1245, L14 1,15, L15 1,1738, L17 1,2254 (valeurs exactes par `repr()` à l'exécution) ; L6 et L7 = 1 ; pente ≈ 0,0248, genou ≈ 7,95 ; Sarilus exclu et listé ; certitude `probable` dans [6, 17], `suppose` au-delà ; L16 corrigé entre les mesures L15 et L17 ; aucun niveau mesuré modifié ; inversions listées.
- `test_engine_leveling.py` : `mob_hp(gd, 12, "seed")` = 247 ; `mob_hp(gd, 12)` = 272 `certain` ; `mob_hp(gd, 20)` corrigé `suppose` ; `corrected_questie_hp` ; `mob_hit_damage`, `armor_reduction`, `mob_xp` = formules du seed ; `travel_time` Frostbolt 30 m à 28 m/s ; recul d'incantation ; régénération en combat (Arcane Meditation, Mage Armor dès son niveau de `utility`) ; `expected_cast(..., spell_level="character")` : Frostbolt r2 au niveau 12 = `rank_values_at_level`, identique à `"rank"` au plafond du rang.
- `tests/parity/test_sim_leveling_parity.py` (`mob_source="seed"`, `spell_level="rank"`, seed importé par `importlib`) : `mc` et `kill_analytic` égaux au seed à 1e-12 pour les 4 cas ci-dessus (MC 25.51026932538584, 29.895997677896577, 32.33266309936493, 30.93969370799394 ; analytique 23.85926190796625, 28.543428650870247, 32.16470423598942, 27.871038699049066) et L12 n = 1500 (25.48655329665798) ; critère de la feuille de route (±1 %) couvert.
- `test_sim_leveling.py`, **tests du seed portés à l'identique** en mode `seed` : `test_analytic_close_to_monte_carlo` (4 cas, < 15 %), `test_calibration_blizzard_target` (L12 et L20, combat entre 8 et 20 s : 11.7169… et 14.1274…), `test_monte_carlo_reproducible` (L16 IF 5, n = 200, graine 1, deux tirages égaux, 30.435373555182213) ; **mêmes assertions en mode par défaut** (`measured`, `character`) aux niveaux 12, 16 et 24 (critère de la feuille de route) : valeurs relevées à l'exécution ; si l'une échoue, s'arrêter et expliquer (aucun ajustement du modèle pour faire passer).
- `test_chart.py` : deux générations identiques octet pour octet ; signature PNG ; un niveau illégal omis et cité ; `forever/data/` inchangé.
- `test_sim_cli.py`, `test_contract.py`, `tests/integration/test_mcp.py` : `sim leveling` et `chart leveling` code 0, provenance complète, build illégal code 2, aucun appel réseau ; `forever_sim_leveling` listé et appelable ; quatre outils MCP.

## Étapes (un cycle rouge → vert par bloc, commits `T04b: tests (bloc X)` puis `T04b: bloc X vert`)
0. `git switch -c t04b`.
1. **Bloc A — seconde fixture, B1, A3** : extraire et anonymiser le journal (décision 1), extrait du carnet (décision 3), `start_recovery_ms` dans `decode` et `spell_scaling.json` (manifeste régénéré), filtre de `gcd_intervals`, chronologie de niveaux, `hit_tally` corrigé, `logs measure --levels` ; registre : preuve B1 (n = 47), cumul et `ecart_median_s` (décision 2), note A3 (décision 4).
2. **Bloc B — correction Questie → Forever** : extrait Questie étendu aux PNJ observés, `fit_questie_correction`, schéma 2 de `monsters.json`, `forever/engine/monsters.py` ; reconstruire `monsters.json` sur les deux journaux réels et Questie 11.38.0 locaux (`forever monsters build`, hors tests), installer, manifeste ; entrée H3 du registre.
3. **Bloc C — données et moteur du simulateur** : clés `leveling.*` de `mechanics.json`, `LevelingModel` dans `GameData`, fonctions du moteur (B6, B7, B13, C1, C5, I6), `spell_level`.
4. **Bloc D — Monte Carlo** : `forever/sim/leveling_mc.py`, parité avec le seed, reproductibilité (J2).
5. **Bloc E — analytique et tests du seed** : `leveling_analytic.py`, 3 tests du seed dans les deux modes (I1, I6).
6. **Bloc F — sorties** : `forever sim leveling`, `forever_sim_leveling`, `forever chart leveling`, contrat.
7. **Bloc G — registre et documentation** : remontées (B6, B7, B13, C1, C5, I1, I6, J2 → `teste` ; C2 complétée par Arctic Reach ; A18 : note sur les 2 tics du MC ; H2 reste `absent`, note sur l'armure du Mage rattachée à I6) ; `ARCHITECTURE.md` (`forever/sim/`, `forever/chart.py`), `DECISIONS.md` (53 et suivantes), `OPEN_QUESTIONS.md`, `DATA_SOURCES.md`, `ROADMAP.md` (T04b fait, T04c si décision 6).
8. `/verifier`, relecteur et auditeur des mécaniques, push, CI verte Ubuntu et Windows, fusion en avance rapide, suppression de la branche, résumé. Si le contexte se remplit : s'arrêter après un bloc vert committé.

## Hors périmètre
- `QuestieForeverDB` et modèle d'XP, cumul et rafraîchissement d'Ignite, escalade d'Arcane Blast (décision 6 : T04c).
- Optimiseur de talents et respec (T05) ; le graphique ne choisit pas les talents.
- Modification des règles de jeu du registre (ligne « - » de A3) sans décision de l'utilisateur.
- Lissage des PV Questie ; PV par PNJ non mesuré dans les données (seulement l'agrégat par niveau et les PNJ observés).
- Tout accès réseau nouveau ; copie de la base Questie ou du carnet complet dans le dépôt.

## Risques
- **Parité Monte Carlo** : un seul tirage déplacé casse l'égalité à 1e-12 ; porter l'ordre des tirages ligne à ligne.
- **Mode par défaut** : avec des PV mesurés plus hauts (272 contre 247 à L12) et les dégâts au niveau, l'analytique peut sortir des 15 % ou le combat des 8-20 s ; c'est un résultat à rapporter, pas à corriger.
- **Extrapolation des PV** au-delà de L17 fondée sur 7 niveaux d'une seule zone (Tarides) : `suppose`, à remplacer par des mesures (journaux de leveling futurs, `forever monsters build`).
- **Gigue d'horodatage** du journal (intervalles à 1,41 s) : le critère de B1 repose sur la médiane ; si la recharge globale de Forever n'était pas 1,5 s, la médiane le montrerait.
- **Taille de la fixture** (6,4 Mo) : lecture 0,35 s, acceptable ; pas d'édition à la main.
- **Carnet Questie** : format d'addon tiers, susceptible de changer ; lecture tolérante, source affichée ; `ForeverLoggerDB` reste la source première.
- **Temps de test** : Monte Carlo à n = 600 en 0,1 s par cas ; la parité complète et le graphique (21 niveaux) sous le marqueur `slow` si nécessaire.

## Critères de fin (T04b)
- Seconde fixture anonymisée installée ; `forever logs measure` y relève 47 intervalles filtrés et 29 observations, code 0, sans réseau.
- `monsters.json` porte la correction Questie → Forever (rapports, droite, plage, certitudes) ; `mob_hp` rend mesure, puis Questie corrigé, avec source et certitude.
- Au niveau 12 avec 3 Improved Frostbolt, le Monte Carlo (graine fixe, `mob_source="seed"`, `spell_level="rank"`) reproduit le seed (à 1e-12, donc à ±1 %).
- L'analytique reste à moins de 15 % du Monte Carlo aux niveaux 12, 16 et 24 (mode seed ; mode par défaut rapporté).
- `forever_sim_leveling` répond avec provenance ; `forever chart leveling` produit un PNG déterministe à graine fixe.
- Registre : B6, B7, B13, C1, C5, I1, I6, J2 `teste` ; H3 ajoutée ; B1 selon la décision 2 ; `uv run tasks.py verify` vert.

## Questions ouvertes à ajouter
- A3 : 0 raté sur 281 sorts directs contre des cibles 2 à 8 niveaux plus basses ; la ligne « - » à 4 % paraît trop haute (règle Classic : 4 % + écart, plancher 1 %) ; talents du Mage inconnus. Campagne à écart ≥ 0 avec ForeverLogger.
- B1 : intervalles sous 1,5 s (min 1,414) : gigue d'horodatage ou file d'attente des sorts.
- PV de Forever : valeur commune par niveau pour les PNJ normaux ? Sunscale Lashtail et Sarilus Foulborne à part ; extrapolation au-delà de L17.
- Carnet Questie : heure locale des horodatages (supposée identique à celle du journal).
