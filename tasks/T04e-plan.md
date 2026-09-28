# T04e — Calculs de dégâts fidèles au client (coefficients du client, DoT, multiplicateurs, cumul) : plan

> Plan rédigé le 2026-09-28 (session de cadrage en arrière-plan), d'après `docs/research/videos/BVSgeHp3sWU.md` (section 6) et la demande de l'utilisateur (points 1 à 9 ci-dessous). **Décisions 1 à 5 à valider par l'utilisateur** (options recommandées en gras). Exécution : `/tranche T04e` dans une nouvelle session, sur la branche `t04e`.

## Contexte
L'analyse de la vidéo BVSgeHp3sWU (Toleduck, 2026-09-27) montre que les tables du client portent directement les coefficients de puissance des sorts, par rang et par effet, et que notre moteur (formule du seed) se trompe sur plusieurs sorts. Demande de l'utilisateur, dans l'ordre :
1. lire les coefficients dans `SpellEffect.EffectBonusCoefficient`, par rang et par effet (coup direct, tic, éclair canalisé), au lieu de la formule ; la formule reste utilisée en mode seed ;
2. DoT : puissance des sorts par tic et intervalle des tics lus dans le client (Pyroblast et Frostfire Bolt à 3 s) ;
3. ajouter au calcul Improved Cone of Cold, Arcane Power et Fire Vulnerability ;
4. Ice Lance : coefficient du client (0), à confirmer par un test en jeu ;
5. cumul des bonus de dégâts en pourcentage : multiplicatif en mode forever (`probable`), additif en mode seed ; à confirmer par les journaux ;
6. pénalité des sorts de bas niveau : paramétrable, gardée par défaut (comportement Classic, `suppose`) jusqu'au test en jeu ;
7. parité avec le seed rompue en mode forever seulement ; le mode seed reste identique à 1e-12 ; les tests listés en section 6 sont mis à jour, avec une justification dans chaque commit ;
8. exemples chiffrés de la vidéo transformés en tests (valeurs de la vidéo, certitude communautaire, tolérance ±0,5) ;
9. trois tests en jeu (Frostbolt rang 1, Ice Lance à deux niveaux de puissance des sorts, tics de Pyroblast rang 1) ajoutés au protocole de collecte de `docs/ADDON.md` et à `docs/OPEN_QUESTIONS.md`.

T04e n'est pas encore dans `docs/ROADMAP.md` : le premier commit de la tranche ajoute la ligne (après T04c, avant T04d, « Dépend de : T04c ») et la section T04e, et ajoute T04e aux dépendances de T05 (l'optimiseur compare des builds sur ces dégâts).

## Constats (relevés le 2026-09-28 dans `tests/fixtures/wago/1.60.1.70009/enUS/` et le cache local, lecture seule)

### Coefficients et périodes (fixture `SpellEffect.csv`, `DifficultyID` 0, composants de `spell_scaling.json`)
| Sort | Effet de dégâts (`EffectBonusCoefficient`) | Période (`EffectAuraPeriod` de l'aura du sort parent) | Formule actuelle (G4) |
| --- | --- | --- | --- |
| Frostbolt | direct : r1 0.40700000525, r2 0.48899999261, r3 0.59700000286, r4 0.70599997044, r5-r11 0.81400001049 | — | 0,1629 … 0,8143 |
| Fireball | direct : r1 0.42899999022, r2 0.57099997997, r3 0.71399998665, r4 0.85699999332, r5-r12 1 ; DoT 0 | 2000 ms (aura 3) | idem, pénalité en plus ; DoT 0 |
| Fire Blast, Scorch | 0.42899999022 à tous les rangs | — | 0,4286 (pénalité en plus aux r1-r2 de Fire Blast) |
| Pyroblast | direct 1 ; **DoT 0.15000000596 par tic** | **3000 ms** (4 tics) | direct 1 ; DoT sans puissance ; tics de 2 s |
| Frostfire Bolt | direct 0.81400001049 ; DoT 0 | **3000 ms** (3 tics) | tics de 2 s |
| Ice Lance | **0** (six rangs) | — | 0,1429 (EST) |
| Arcane Blast | 0.71399998665 | — | 0,7143 |
| Arcane Missiles | 0.28600001335 **par missile** (sort déclenché 7268 … 25346), 3, 4 puis 5 missiles | 1000 ms (aura 23 du parent) | durée / 3,5 |
| Arcane Explosion | 0.14300000668 | — | 0,143 (pénalité en plus au r1) |
| Frost Nova | **0.02899999917** | — | 0,043 |
| Cone of Cold | **0.12899999321** (ralentissement déjà compris) | — | 0,143 × 0,95 |
| Blast Wave | **0.12899999321** | — | 0,143 |
| Blizzard | **0.04199999943 par tic** (sort déclenché 1279949 …), 8 tics ; l'effet factice du parent porte 0.02999999933 | 1000 ms (aura 226 du parent, effet 2) | 0,333 au total |
| Flamestrike | direct 0.15700000525 ; **DoT 0.03200000152 par tic** (sort 1279983 …), 4 tics | 2000 ms (aura 226 du parent) | direct 0,157 ; DoT sans puissance |

- La période d'un DoT porté par un sort déclenché (Blizzard, Flamestrike, Arcane Missiles) est celle de l'effet d'aura du **sort parent** ; le coefficient est celui de l'effet de dégâts du **sort déclenché**. `_components` (`forever/pipeline/decode.py`) a les deux sous la main quand il construit le composant.
- Le coefficient du client comprend déjà le × 0,95 des sorts qui ralentissent (1,5 / 3,5 × 0,95 = 0,407 pour Frostbolt r1) et **pas** la pénalité des sorts de bas niveau (Frostbolt r1 0,407 au lieu de 0,163) : elle reste une règle séparée (`suppose`).
- Journal `WoWCombatLog-092726_150346.anon.txt.gz` : les tics de Fireball r3 (sort 145) valent tous 2, à 13-14 de puissance des sorts : compatible avec un coefficient de DoT nul, `certain`.

### Multiplicateurs absents (client et `talents.json`)
- **Improved Cone of Cold** : `talents.json` `improvedConeOfCold`, rangs 12 / 23 / 35 % (tables Trait*, T03). Le sort de talent 11190 porte 15 au rang 1 dans `SpellEffect` (aura 108, masque de Cone of Cold) : on retient `talents.json`, comme pour tous les talents depuis T03 (décodage Trait*, écart relevé dans les risques).
- **Arcane Power** : `talents.json` `arcanePower`, `ranks = [[15, 30, 30]]` (durée 15 s, +30 % de dégâts, +30 % de coût) ; client 12042 : trois effets aura 108 à 30 (dégâts, coût, troisième masque), `SpellMisc.DurationIndex` 8 → 15 000 ms, `SpellCooldowns` 180 000 ms. Tout est dans les fixtures.
- **Fire Vulnerability** : aura 22959 posée par Improved Scorch (11095, `EffectTriggerSpell` 22959, chance 33 / 66 / 100 dans `talents.json`) : `SpellEffect` aura 270, 3 (par cumul), masque d'école 4 (feu) ; `SpellAuraOptions.CumulativeAura` 5 ; `DurationIndex` 9 → 30 000 ms. Ces chiffres ne sont **pas** des rangs de `talents.json` (le « 3 % … 5 fois » n'y est que du texte) : ils doivent être décodés. Toutes les lignes sont déjà dans les fixtures (`SpellEffect`, `SpellMisc`, `SpellAuraOptions`, `SpellDuration`, `SpellName`, `Spell`).

### Moteur et tests aujourd'hui
- `coefficient`, `expected_cast`, `roll_base_damage`, `dmg_mult`, `dot_tick_times`, `dot_tick_damage` n'ont pas de paramètre `rules` ; seuls les simulateurs (`options_with_defaults`, défaut `forever`) et `in_combat_regen_fraction` (défaut `forever`) en ont un. `expected_cast` a déjà `spell_level` (défaut `rank`, parité).
- `Buffs["dmg"]` : un seul champ additif ; `dmg_mult` = (1 + Arcane Instability) × (1 + Piercing Ice ou Fire Power) × (1 + `dmg`).
- `dot_tick_times(gd, duration_s)` : un tic toutes les `leveling.dot_tick_s` (2 s, seed) pour tout DoT ; `dot_tick_damage` sans puissance des sorts.
- Rotations des simulateurs : frost (Frostbolt, Ice Lance si le talent est pris, Frost Nova si `nova`), fire (Fireball et son DoT, Fire Blast), arcane (Arcane Blast puis décharge) ; ni Pyroblast, ni Cone of Cold, ni Scorch, ni Arcane Power.
- La provenance de `forever sim leveling` et de `forever_sim_leveling` vaut déjà `suppose` au plus (`min_certainty([…, "suppose"])`).

### Exemples de la vidéo recalculés avec les coefficients du client (niveau 60, `spell_level="character"`)
Frostbolt r11 à 534 / 500 / 1 000 / 800 / 2 000 : 964,257 / 934,920 / 1 366,340 / 1 193,772 / 2 229,180 (vidéo 964,3 / 934,9 / 1 366,3 / 1 193,8 / 2 229,2) ; Frostfire Bolt r3 770,277 (770,3) ; Cone of Cold r5 589,409 (589,4) ; Fire Blast r7 682,086 (682,1) ; Pyroblast r8 1 117 ; Fireball r12 1 017 ; Arcane Blast r5 1 038,095 (1 038,1) ; Arcane Missiles r8 484,348 par missile et 2 421,742 au total (484,3 ; 2 421,7) ; Arcane Missiles r8 avec 4 cumuls d'Arcane Blast et Arcane Power, multipliés : 678,088 (678,1). Tous à moins de 0,05. **Hors de ±0,5** : Arcane Explosion r6 avec les mêmes bonus 608,986 (608, +0,99), Arcane Explosion r6 sous Arcane Power 434,990 (434, +0,99), Ice Lance r6 gelée sans puissance 629,640 (627,5, +2,14) : le tableur tronque les bornes (238-258, 136-160), nous arrondissons au demi supérieur (239-258, 136-161), arrondi qui reproduit les rangs décodés (G7, écart E7 du rapport).

## Décisions (à valider)
| # | Décision | Recommandé | Alternative |
| --- | --- | --- | --- |
| 1 | Où vit `rules` et son défaut | **Paramètre `rules` (mot-clé, défaut `"forever"`, comme `in_combat_regen_fraction` et les simulateurs) sur `coefficient`, `dot_coefficient`, `expected_cast`, `roll_base_damage`, `dmg_mult`, `dot_tick_period_s`, `dot_tick_damage` ; les simulateurs transmettent `o["rules"]`.** Les tests qui documentent le seed passent `rules="seed"` explicitement (parité `test_fm_parity`, contrôles portés du seed, valeurs de T02) : ils restent verts sans changer de valeur ; les tests qui comparaient forever et seed sur une autre règle neutralisent la puissance des sorts (`over={"sp": 0}`), seule entrée par laquelle T04e change ces rotations | Défaut `"seed"` dans le moteur (comme `spell_level="rank"`) : aucun test ne casse, mais tout futur appelant (T05, CLI) qui oublie `rules` calcule avec la formule du seed |
| 2 | Pénalité des sorts de bas niveau (point 6) | **Nouvelle clé `coefficient.low_level_default` = `true` dans `mechanics.json` (`suppose`, règle Classic) ; paramètre `low_level_penalty: bool \| None = None` du moteur (None : la clé des données), option `low_level_penalty` des simulateurs, `--low-level-penalty on\|off` de `forever sim leveling`, argument de `forever_sim_leveling`.** En forever : coefficient du client × max(0, 1 − 0,0375 × (20 − niveau du rang)) (chiffres de `coefficient.low_level`, inchangés), appliqué **aussi au coefficient par tic** (Flamestrike r1, niveau 16 : `suppose`, règle Classic) ; en seed : toujours appliquée ; `low_level_penalty=False` avec `rules="seed"` refusé (ValueError, code 2), comme `armor`. Après le test en jeu, l'utilisateur tranche en changeant la clé | Paramètre seul, défaut vrai écrit dans le code (le trancher demande alors un commit de code, pas de données) |
| 3 | Cumul des bonus en pourcentage (point 5) | **`Buffs` gagne `dmg_sources: tuple[float, ...]` (une fraction par source distincte : Arcane Power…) et `fire_vulnerability: int` (cumuls sur la cible) ; `dmg` reste une source unique (bonus d'Arcane Blast, buffs de l'appelant).** Forever : `mult` = talents × (1 + `dmg`) × Π(1 + s) × (1 + Improved Cone of Cold si Cone of Cold) × (1 + cumuls × part de Fire Vulnerability si feu) ; seed : talents × (1 + `dmg` + Σ s + cumuls × part), Improved Cone of Cold ignoré (le seed ne le connaît pas : parité garantie). `arcane_blast_bonus` inchangé | Une clé par source (`dmg_arcane_power`, `dmg_arcane_blast`…) : chaque nouvelle aura change le type |
| 4 | Arcane Power et Fire Vulnerability dans les simulateurs | **Hors des simulateurs en T04e** : fonctions du moteur (`arcane_power_buffs`, `fire_vulnerability_buffs`) consommées par `expected_cast` par `buffs` (Arcane Power : +30 % de dégâts en source distincte, +30 % de coût par `cost`) ; aucune rotation ne lance Arcane Power (recharge 180 s, politique d'usage : T05 ou T09) ni Scorch (cumuls de Fire Vulnerability) | Option `arcane_power` des simulateurs (lancé à la recharge, aura 15 s, recharge du client) ; rotation feu avec Scorch jusqu'à 5 cumuls |
| 5 | Exemples de la vidéo hors de ±0,5 (écart d'arrondi E7) | **Exclus des tests à ±0,5 et gardés dans la fixture avec `exclu: "E7"` et l'écart calculé** ; un test vérifie que l'écart s'explique par l'arrondi seul : avec les bornes tronquées du tableur, la même formule donne la valeur de la vidéo à ±0,5 ; question E7 ajoutée à `OPEN_QUESTIONS` | Tolérance élargie à 2,5 pour ces trois exemples (moins lisible, masque une vraie divergence plus petite) |

Décisions techniques (sans arbitrage attendu) :
- **Formule forever** (G4) : coefficient direct = Σ `bonus_coefficient` des composants `direct` + Σ `bonus_coefficient` × `ticks` des composants `channel` (Arcane Missiles 5 × 0,286, Blizzard 8 × 0,042) ; coefficient par tic de DoT = `bonus_coefficient` du composant `dot` ; puis pénalité (décision 2). Ni diviseur, ni bornes, ni `slow_factor`, ni `coefficient.fixed` : ces clés de `mechanics.json` restent, pour le mode seed seulement (source réécrite « mode seed »). Blizzard : coefficient du sort déclenché (0,042), `probable` (question ouverte, test par journal).
- **DoT** (A17) : total du DoT = (total du rang + tics × coefficient par tic × puissance des sorts) × multiplicateur × (1 + critique × (mult_crit − 1)) si les DoT critiquent ; tic = total du rang / tics + coefficient par tic × puissance des sorts, × multiplicateur. Période du tic : `period_ms` du composant (forever) ; `leveling.dot_tick_s` (seed). Nombre de tics : `ticks` du composant (forever), `durée / dot_tick_s` (seed).
- **Données** : `spell_scaling.json` passe au schéma 2 ; chaque composant gagne `bonus_coefficient` (flottant du client) et `period_ms` (0 pour `direct`) ; section `utility` : `fire_vulnerability` (identifiant lu par l'`EffectTriggerSpell` d'Improved Scorch, jamais écrit en dur : part par cumul aura 270, cumuls `SpellAuraOptions.CumulativeAura`, durée `SpellDuration`). `decode_rules.json` : `utility_spells` gagne l'effet `damage_taken_pct` (aura 270, `EffectBasePointsF`) et les champs d'aura `max_stacks` et `duration_s` ; l'entrée Fire Vulnerability est désignée par le talent qui la déclenche. Réinstallation par `forever decode` sur les fixtures (écriture en octets LF), manifeste régénéré ; `test_decode_reproduces_installed_spell_scaling` reste l'oracle. Aucun nouveau fichier de données : pas de changement de `DECODED_FILES` ni des comptes de fichiers. Chargement (`gamedata.py`) : schéma 1 refusé (`DataSchemaError`), champs obligatoires.
- **Ice Lance** (point 4) : coefficient du client (0) en forever, `probable` (note au registre, question ouverte, test en jeu E4) ; 0,1429 reste en mode seed.
- **Provenance** : `forever sim leveling` et `forever_sim_leveling` ajoutent aux hypothèses « coefficients du client (EffectBonusCoefficient) », « pénalité des sorts de bas niveau : appliquée / non appliquée (suppose) », « bonus de dégâts multipliés entre sources (probable) » en `rules forever` ; certitude inchangée (`suppose` au plus).
- **Registre** : on modifie G4, A17, A20 et B15 (aucune entrée ajoutée, donc aucune assertion de `test_registry.py` à changer) ; listes `tests:` mises à jour dans le même commit que les tests, sinon `verify` échoue.

## Existant réutilisé
- `forever/pipeline/decode.py` (`_component`, `_components`, `decode_scaling`, `utility_spells`, `duration_ms`, `SpellAuraOptions`), `forever/gamedata.py` (`_scaling`, lecture de `utility`), `forever/engine/model.py` (`ScalingComponent`, `RankScaling`, `Buffs`, `CoefficientRules`).
- `forever/engine/spells.py` (`coefficient`, `rank_values_at_level`, `best_rank`), `damage.py` (`dmg_mult`, `roll_base_damage`, `dot_tick_times`, `dot_tick_damage`), `cast.py` (`expected_cast`), `buffs.py` (`arcane_blast_bonus`), `mana.py` (`mana_cost`, buff `cost`), `talents.py` (`talent_value`), `crit.py`.
- `forever/sim/leveling_mc.py`, `leveling_analytic.py` (`options_with_defaults`, `OPTIONS`), `forever/cli.py` (`_cmd_sim_leveling`), `forever/mcp_server.py` (`forever_sim_leveling`), `forever/provenance.py` (`min_certainty`).
- Tests : `tests/conftest.py` (`game_data`, `data_copy`, `write_manifest`, `make_deps`), `tests/unit/test_spell_scaling.py` (`candidate`), fixture de journal `WoWCombatLog-092726_150346.anon.txt.gz`, `forever/pipeline/combatlog.py` (lecture des événements).

## Fichiers
```
docs/ROADMAP.md                                 + ligne et section T04e (après T04c) ; T05 dépend de T04e
forever/data/1.60.1.70009/decode_rules.json     utility_spells : + effet damage_taken_pct (aura 270), + max_stacks, duration_s, + fire_vulnerability (par le talent improvedScorch)
forever/data/1.60.1.70009/spell_scaling.json    schéma 2 : bonus_coefficient et period_ms par composant ; utility.fire_vulnerability
forever/data/1.60.1.70009/mechanics.json        + coefficient.low_level_default (suppose) ; sources des clés coefficient.* : « mode seed »
forever/data/1.60.1.70009/sources.json          description de spell_scaling.json (schéma 2)
forever/data/1.60.1.70009/manifest.json
forever/pipeline/decode.py                      _component : bonus_coefficient, period_ms (aura du parent) ; utility : aura 270, cumuls, durée
forever/engine/model.py, forever/gamedata.py    ScalingComponent.bonus_coefficient, .period_ms ; FireVulnerability ; Buffs.dmg_sources, .fire_vulnerability ; low_level_default
forever/engine/spells.py                        coefficient(…, rules, low_level_penalty) ; + dot_coefficient, + dot_ticks
forever/engine/damage.py                        dmg_mult(…, key, rules) ; roll_base_damage(…, rules, low_level_penalty) ; + dot_tick_period_s ; dot_tick_times(…, period_s) ; dot_tick_damage(…, sp_per_tick)
forever/engine/buffs.py                         + arcane_power_buffs, fire_vulnerability_buffs, merge_buffs
forever/engine/cast.py                          expected_cast(…, rules, low_level_penalty) : DoT avec puissance des sorts, clé du sort à dmg_mult
forever/engine/__init__.py                      exports
forever/sim/leveling_mc.py, leveling_analytic.py   rules transmis au moteur ; option low_level_penalty ; tics à la période du client
forever/cli.py, forever/mcp_server.py           --low-level-penalty on|off ; low_level_penalty ; hypothèses de provenance
tests/fixtures/community/BVSgeHp3sWU.json       (nouveau) exemples chiffrés de la vidéo (valeurs, horodatage ou image, talents, certitude communautaire)
tests/unit/test_client_coefficients.py          (nouveau) coefficients, DoT, périodes, pénalité, Ice Lance, preuve du journal
tests/unit/test_damage_modifiers.py             (nouveau) Improved Cone of Cold, Arcane Power, Fire Vulnerability, cumul
tests/unit/test_video_examples.py               (nouveau) exemples de la vidéo à ±0,5
Tests modifiés (justification dans le commit « tests » de leur bloc) :
  tests/unit/test_spell_scaling.py              + champs du schéma 2, utility.fire_vulnerability
  tests/unit/test_engine_values.py              test_coefficient_values et test_frostbolt_values en rules="seed" (+ équivalents forever dans les nouveaux fichiers)
  tests/unit/test_engine_mechanics.py           contrôles « coefficients » et « pénalité < 20 » en rules="seed" (contrôles portés du seed, critère T02)
  tests/unit/test_gamedata.py                   test_coefficient_reads_data en rules="seed" ; schéma 1 de spell_scaling refusé
  tests/parity/test_fm_parity.py                expected_cast et coefficient en rules="seed"
  tests/unit/test_engine_ignite.py              test_forever_monte_carlo_differs_from_the_seed_only_through_ignite : over + {"sp": 0}
  tests/unit/test_sim_rules.py                  test_analytic_fire_blast_cooldown_includes_wake_of_fire, test_seed_rules_keep_the_frost_armor_slow : over={"sp": 0}
  tests/unit/test_sim_cli.py, tests/integration/test_mcp.py, test_contract.py   option low_level_penalty
docs/MECHANICS_REGISTRY.yaml (G4, A17, A20, B15), docs/OPEN_QUESTIONS.md, docs/ADDON.md (protocole de collecte), docs/DECISIONS.md,
docs/research/videos/BVSgeHp3sWU.md (corrections C1 à C6 : « appliquées en T04e »)
```
`tests/parity/test_sim_leveling_parity.py` et `tests/unit/test_sim_leveling.py` ne changent pas (`SEED_MODE` porte déjà `rules="seed"`, désormais transmis au moteur). `test_engine_values.py::test_ice_lance_frozen_multiplier` non plus (rapport × 4 entre deux appels, vrai avec un coefficient nul) ; aucun test d'`explain` ne lit la formule de G4.

## Interfaces
```python
# forever/engine/model.py
@dataclass(frozen=True)
class ScalingComponent:  # + deux champs (spell_scaling.json, schéma 2)
    ...; bonus_coefficient: float; period_ms: int          # period_ms : 0 pour direct
class Buffs(TypedDict, total=False):  # + deux clés
    ...; dmg_sources: tuple[float, ...]; fire_vulnerability: int
@dataclass(frozen=True)
class FireVulnerability: pct_per_stack: float; max_stacks: int; duration_s: float; spell_id: int

# forever/engine/spells.py      (Registre : G4)
def coefficient(gd, key, rank, *, rules="forever", low_level_penalty: bool | None = None) -> float
    # forever : Σ direct + Σ channel × ticks (client) × pénalité ; seed : formule actuelle, inchangée
def dot_coefficient(gd, key, rank, *, rules="forever", low_level_penalty=None) -> float   # par tic ; seed : 0
def dot_ticks(gd, key, rank, *, rules="forever") -> int                                     # forever : ticks du composant dot

# forever/engine/damage.py      (Registre : A17, A20, G4)
def dmg_mult(gd, school, pts, buffs=None, *, key: str | None = None, rules="forever") -> float
def roll_base_damage(gd, key, rank, ch, u, *, frozen=False, rules="forever", low_level_penalty=None) -> float
def dot_tick_period_s(gd, key, rank, *, rules="forever") -> float    # forever : period_ms / 1000 ; seed : leveling.dot_tick_s
def dot_tick_times(gd, duration_s, period_s: float | None = None) -> list[float]   # None : leveling.dot_tick_s (inchangé)
def dot_tick_damage(gd, dot_total, dmg_mult, ticks, *, sp_per_tick: float = 0.0) -> float
    # (dot_total / ticks + sp_per_tick) × dmg_mult ; sp_per_tick = dot_coefficient × puissance des sorts

# forever/engine/buffs.py       (Registre : A20, B15)
def arcane_power_buffs(gd, pts) -> Buffs              # {} sans le talent ; {"dmg_sources": (0.30,), "cost": 0.30} (talents.json)
def fire_vulnerability_buffs(gd, stacks: int) -> Buffs   # {"fire_vulnerability": n}, n borné à max_stacks du client
def merge_buffs(*buffs: Buffs | None) -> Buffs        # somme des scalaires, concaténation de dmg_sources, max des cumuls

# forever/engine/cast.py        (Registre : A17, A18, A20, B12, B17, C2, G4, G7)
def expected_cast(gd, key, level, pts, ch, level_diff=0, *, frozen=False, wc_stacks=0, buffs=None,
                  frozen_mult=True, spell_level="rank", rules="forever", low_level_penalty=None) -> CastEstimate | None
    # dot = (dot_total + dot_ticks × dot_coefficient × SP) × dm × facteur de critique

# simulateurs : options_with_defaults(…) accepte low_level_penalty (None, True, False) ; refus avec rules seed
```

### CLI et MCP (texte français, `--json`, provenance sur chaque sortie, aucun réseau)
| Commande | Codes |
| --- | --- |
| `forever sim leveling … [--low-level-penalty on\|off]` (défaut : la clé des données) | 0 ; 2 si `off` avec `--rules seed` |
| MCP `forever_sim_leveling(…, low_level_penalty: bool \| None = None)` | erreur structurée si `False` avec `rules="seed"` |

## Tests attendus (valeurs tirées des fixtures et des données, `pytest.approx(rel=1e-12)` sauf mention)
Chaque bloc suit le cycle rouge → vert de la tranche (commit « T04e: tests (bloc X) », puis « T04e: bloc X vert »). Valeurs du plan : recalculées à l'écriture des tests par `repr()` sur les données, jamais recopiées d'un arrondi.

- **Bloc A — données** (`test_spell_scaling.py`, `test_gamedata.py`) : décodage des fixtures : Frostbolt r1 composant direct `bonus_coefficient` 0.40700000525, `period_ms` 0 ; Pyroblast r8 composant dot 0.15000000596, 3000 ; Frostfire Bolt r3 dot 0, 3000 ; Fireball r12 dot 0, 2000 ; Arcane Missiles r8 channel 0.28600001335, 1000 ; Blizzard r6 channel 0.04199999943, 1000 (période de l'aura du parent 10187) ; Flamestrike r6 dot 0.03200000152, 2000 ; `utility.fire_vulnerability` : spell_id 22959 (par Improved Scorch), 3 %, 5 cumuls, 30 s ; décodage = données installées (oracle existant) ; `schema_version` 2 ; une copie de données au schéma 1 (manifeste régénéré) est refusée (`DataSchemaError`) ; `coefficient.low_level_default` lu (`true`).
- **Bloc B — coefficients** (`test_client_coefficients.py`) :
    - `test_coefficient_matches_client_table` : pour chaque rang des 15 sorts, `coefficient(…, low_level_penalty=False)` = somme lue **par le test** dans `SpellEffect.csv` de la fixture (direct + channel × ticks) ; Frost Nova 0.02899999917, Cone of Cold 0.12899999321, Blast Wave 0.12899999321, Ice Lance 0, Blizzard 8 × 0.04199999943, Arcane Missiles r8 5 × 0.28600001335 ;
    - pénalité : Frostbolt r1 0.40700000525 × (1 − 0,0375 × 16) = 0.1628000021 par défaut, 0.40700000525 avec `low_level_penalty=False` ; Frostbolt r5 et au-delà : pénalité sans effet ; une copie de données avec `coefficient.low_level_default` à `false` donne 0.40700000525 sans argument ;
    - Ice Lance : 0 en forever, 0,1429 en seed ;
    - `test_client_coefficient_reads_data` : `bonus_coefficient` de Frostbolt r11 changé dans une copie (manifeste régénéré) → le coefficient suit ;
    - seed : `test_coefficient_values` (0.26871428571428574, 0.8142857142857142) inchangé en `rules="seed"` ; parité `test_fm_parity` à 1e-12 en `rules="seed"` ;
    - forever, `test_frostbolt_forever_values` (SP 500, critique 0,10, niveau 60) : `direct_per_hit` = (475 + 0.81400001049 × 500) × 1,05 = 926.1000055072501, `dmg` = 889.05600528696 ; Fireball r12 identique au seed (coefficient 1, DoT 0).
    - Vérification avant verrouillage : chaque test échoue si le moteur garde la formule du seed.
- **Bloc C — DoT** (`test_client_coefficients.py`) :
    - `test_pyroblast_dot_scales_with_spell_power` : Pyroblast r8, niveau 60, SP 534, critique 0 : `dot` = 4 × (53 + 0.15000000596 × 534) = 532.40001273056 ; en seed : 212 ;
    - `test_flamestrike_dot_scales_with_spell_power` : Flamestrike r6, SP 534 : 4 × (83 + 0.03200000152 × 534) = 400.35200324672 ;
    - `test_pyroblast_r1_tick` : tic de Pyroblast r1 à SP 20 = 11 + 0.15000000596 × 20 = 14.0000001192 (prédiction du test en jeu E3) ;
    - `test_dot_ticks_follow_client_period` : Pyroblast r8 [3, 6, 9, 12], Frostfire Bolt r3 [3, 6, 9], Fireball r12 [2, 4, 6, 8] ; seed : Pyroblast r8 [2, 4, 6, 8, 10, 12] ; `dot_tick_times(gd, 8)` et `dot_tick_damage(gd, 12, 1.1, 4)` inchangés sans les nouveaux arguments ;
    - `test_fireball_dot_has_no_spell_power_in_log` : tous les tics de 145 (Fireball r3) du journal `WoWCombatLog-092726_150346.anon.txt.gz` valent 2 = tic forever du rang au niveau du journal avec la puissance des sorts relevée dans le bloc avancé (13-14) ; un coefficient de 0,15 par tic en prédirait au moins 4 (le test calcule les deux et montre qu'une seule hypothèse tient) ;
    - Monte Carlo forever, rotation fire, graine fixe : nombre de tics de DoT tirés = somme des `ticks` des composants (compteur relevé par un journal de test, pas de sens imposé sur le temps par monstre).
- **Bloc D — multiplicateurs et cumul** (`test_damage_modifiers.py`) :
    - `test_improved_cone_of_cold` : Cone of Cold r5, niveau 60, SP 534, Piercing Ice 3/3, Improved Cone of Cold 3/3, critique 0 : `direct_per_hit` = (343 + 0.12899999321 × 534) × 1,06 × 1,35 = 589.4088608113944 (concordance avec V13, source citée) ; talent sans effet sur Frostbolt ; ignoré en seed ;
    - `test_arcane_power_buffs` : +30 % de dégâts en source distincte, +30 % de coût (`mana_cost` × 1,3), vides sans le talent ; valeurs lues dans `talents.json` ;
    - `test_fire_vulnerability` : 5 cumuls → × 1,15 sur Fireball, rien sur Frostbolt ni Arcane Missiles ; cumuls bornés à 5 (6 demandés → 5) ; parts lues dans `utility.fire_vulnerability` ;
    - `test_damage_bonuses_stack_multiplicatively_in_forever` : Arcane Instability 3/3, `dmg` 0,40 et `dmg_sources` (0,30,) : forever 1,03 × 1,40 × 1,30 = 1.8746 ; seed 1,03 × (1 + 0,40 + 0,30) = 1.751 ; le test échoue si l'on additionne en forever ;
    - `arcane_blast_bonus` et les tests B15 existants inchangés.
- **Bloc E — simulateurs, CLI, MCP** (`test_sim_rules.py`, `test_sim_cli.py`, `tests/integration/test_mcp.py`, `test_contract.py`) :
    - parité : `test_sim_leveling_parity.py` vert sans modification (le moteur reçoit `rules="seed"`) ;
    - `low_level_penalty=False` change le résultat analytique forever à L12 frost (Frostbolt r2, niveau 8 : effet déterministe) ; refus avec `rules="seed"` (ValueError, code 2 en CLI, erreur structurée MCP) ; `--low-level-penalty on` = défaut ;
    - Ice Lance à coefficient nul : analytique forever L24 frost avec Ice Lance, dégâts d'Ice Lance indépendants de la puissance des sorts (deux SP, même `direct_per_hit` d'Ice Lance) ;
    - hypothèses de provenance : les trois notes de T04e présentes en forever, absentes en seed ;
    - tests d'égalité forever = seed réécrits avec `over={"sp": 0}` (T04e ne change ces rotations que par la puissance des sorts : Fireball DoT 0 et période 2 s identiques, Frostbolt direct seul) ; relancés et verts avant verrouillage ;
    - tolérances existantes (analytique à 15 % du Monte Carlo, calibrage 8-20 s, `default > seed` au niveau 12) relancées en forever : si l'une tombe, s'arrêter et rapporter (pas de changement de tolérance sans accord).
- **Bloc F — exemples de la vidéo** (`tests/fixtures/community/BVSgeHp3sWU.json`, `test_video_examples.py`) :
    - fixture : pour chaque exemple, identifiant (V9 à V19 du rapport), horodatage ou image, sort, rang, niveau 60, puissance des sorts, talents cochés (Piercing Ice 3/3, Improved Cone of Cold 3/3, Arcane Instability 3/3 ; talent de critique +100 % pour givre et arcane, V7 : Ice Shards 5/5, Arcane Mind 5/5 ; talents d'apprentissage pyroblast, arcaneBlast), bonus (Arcane Power, cumuls d'Arcane Blast), valeur normale et critique de la vidéo, certitude `communautaire` (sens : `suppose`, source unique), URL ;
    - `test_video_example[...]` paramétré : `expected_cast(rules="forever", spell_level="character")` avec critique 0 ; coup normal = `direct_per_hit` (÷ tics pour un missile d'Arcane Missiles), critique = normal × `crit_mult` ; `abs(moteur − vidéo) <= 0,5` pour : Frostbolt r11 à 534, 500, 1 000, 800, 2 000 (et critiques 1 928,5 ; 4 458,4) ; Frostfire Bolt r3 (770,3 ; 1 540,6) ; Cone of Cold r5 (589,4 ; 1 178,8) ; Fire Blast r7 (682,1) ; Pyroblast r8 (1 117 ; 1 675,5) ; Fireball r12 (1 017 ; 1 525,5) ; Arcane Blast r5 (1 038,1 ; 2 076,2) ; Arcane Missiles r8 par missile et au total (484,3 ; 968,7 ; 2 421,7) ; Arcane Missiles r8 avec 4 cumuls et Arcane Power (678,1 ; 1 356,2) ;
    - exclus (décision 5, `exclu: "E7"`) : Arcane Explosion r6 avec bonus (608) et sous Arcane Power (434, critique « 900 » orale), Ice Lance r6 gelée (627,5) ; `test_video_rounding_gap` : avec les bornes du tableur (238-258, 136-160), la formule du moteur redonne ces valeurs à ±0,5 ; exemples non chiffrables (V1 à V7, V20, V21, autres classes) absents de la fixture, avec la raison dans son en-tête ;
    - vérification avant verrouillage : en seed, au moins Cone of Cold (440,5) et les exemples sous Arcane Power multiplié tombent hors de ±0,5 (le test mesure bien T04e).
- **Bloc G — documents et registre** (pas de test nouveau ; `uv run tasks.py verify` vert) :
    - G4 : source « Tables du client SpellEffect (EffectBonusCoefficient), 1.60.1.70009 », formule forever et seed, coefficients `certain`, pénalité `suppose`, Ice Lance 0 `probable`, Blizzard 0,042 `probable` ; tests : nouveaux fichiers ;
    - A17 : puissance des sorts par tic, période du client ; A20 : Improved Cone of Cold, Arcane Power, Fire Vulnerability, cumul multiplicatif `probable` (entrée `probable`) ; B15 : aura d'Arcane Power (talents.json, 12042 : 15 s, recharge 180 s non modélisée), cumul avec Arcane Blast ;
    - `docs/ADDON.md`, protocole de collecte, quatre lignes reprises de la section 5 du rapport, seuils compris : **G4 pénalité (E2)** une dizaine de Frostbolt **rang 1** sur un monstre gris, sans talent de dégâts, personnage de niveau ≥ 8 : base 20-22, + 0,407 × SP sans pénalité, + 0,163 × SP avec ; à 14 de puissance des sorts, 25,6-27,8 contre 22,2-24,4 (sans recouvrement) ; puissance des sorts lue dans le bloc avancé de `SPELL_CAST_SUCCESS` ; **Ice Lance (E4)** sur cible non gelée, deux séries à au moins 30 de puissance des sorts d'écart : + 4,3 par coup attendu avec 0,1429, rien avec 0 ; un seul coup au-dessus du maximum de base (× talents) réfute 0 ; **Pyroblast r1 (E3)** : tic = 11 + 0,15 × SP (× talents), à 20 de puissance des sorts 14 au lieu de 11, un tic toutes les 3 s ; **cumul (E6)**, journaux ordinaires : Arcane Missiles sous Arcane Power avec 4 cumuls d'Arcane Blast contre Arcane Power seul, rapport 1,40 (multiplicatif) contre 1,31 (additif) ;
    - `docs/OPEN_QUESTIONS.md` : pénalité des sorts de bas niveau dans Forever (E2, et sens des Fire Blast 400616-400623 à `AcquireMethod` 3) ; coefficient nul d'Ice Lance (E4) ; puissance des sorts et période des tics de Pyroblast (E3) ; cumul de deux bonus aura 108 (E6) ; arrondi des bornes (E7, exemples exclus de la vidéo) ; coefficient de Blizzard (0,042 du sort déclenché ou 0,03 de l'effet factice : tic de Blizzard à deux niveaux de puissance des sorts) ;
    - `docs/DECISIONS.md` : décisions 1 à 5 ; `docs/research/videos/BVSgeHp3sWU.md` : en-tête « corrections C1 à C6 appliquées en T04e » (le reste du rapport inchangé).

## Étapes
1. `git switch -c t04e` ; commit « T04e: feuille de route » (ligne et section T04e dans `docs/ROADMAP.md`, dépendance de T05).
2. Bloc A (données) : tests rouges → commit → décodeur, modèle, chargement → `forever decode` sur les fixtures, installation en octets LF, `write_manifest` → contrôle `git diff --stat` (seul `spell_scaling.json` réécrit, avec les deux champs) → vert → commit.
3. Bloc B (coefficients, `rules` et pénalité dans le moteur) : tests rouges (nouveaux + tests seed passés en `rules="seed"`, justification dans le message de commit) → vert.
4. Bloc C (DoT : puissance par tic, période) : moteur, puis Monte Carlo et analytique.
5. Bloc D (multiplicateurs, cumul, `Buffs`).
6. Bloc E (simulateurs, CLI, MCP, provenance ; tests d'égalité forever = seed réécrits avec `sp` 0, justification dans le commit).
7. Bloc F (fixture de la vidéo, tests paramétrés).
8. Bloc G (registre, `ADDON.md`, `OPEN_QUESTIONS.md`, `DECISIONS.md`, rapport de la vidéo).
9. `/verifier`, sous-agents `auditeur-mecaniques` et `relecteur` ; push de `t04e`, CI verte sous Ubuntu et Windows, fusion en fast-forward dans `main`, push, suppression de la branche ; résumé final (Bloqué sur moi, Fait, Tests ajoutés, Registre modifié, Questions ouvertes).

## Hors périmètre
- Arcane Power et Scorch (cumuls de Fire Vulnerability) dans les rotations des simulateurs (décision 4) ; politique d'usage des recharges longues (T05, T09).
- Changer l'arrondi des bornes de dégâts (E7) : question ouverte seulement.
- Analyse automatique des journaux des trois tests en jeu (`forever measures`) : protocole et questions seulement ; l'analyse viendra avec les journaux.
- Autres classes (section 7 du rapport : PV1, T12) ; coefficients de puissance d'attaque (`BonusCoefficientFromAP`, 0 sur ces sorts) ; `PvpMultiplier` (1 partout).
- Résistances, toucher, critique et Ignite : inchangés.

## Risques
- **Fire Vulnerability dans le décodeur** : 22959 n'est pas un sort appris ; si `utility_spells` exige une ligne `SkillLineAbility` apprise, la désignation par l'`EffectTriggerSpell` d'Improved Scorch contourne le filtre. Si une table manque dans les fixtures, relancer `scripts/extract_wago_fixtures.py` (jamais d'édition à la main) et mettre à jour les comptes de fixtures.
- **Improved Cone of Cold** : 15 % au rang 1 dans `SpellEffect` 11190 contre 12 % dans `talents.json` ; on garde `talents.json` (convention T03 ; 35 % à 3/3 concorde avec V13). À signaler dans la note de A20.
- **Givre-feu et Fire Vulnerability** : Frostfire Bolt compte en feu (`SCHOOL_FIRE`) et profiterait de la vulnérabilité ; même question que la double école (OPEN_QUESTIONS), notée `suppose`.
- **Tests des simulateurs en forever** : les coefficients du client sont proches de la formule aux bas niveaux (Frostbolt r2 : 0,489 × 0,55 = 0,269 contre 0,2687), l'effet sur les tolérances devrait être faible ; Ice Lance passe à 0 (frost L24). Si une tolérance ou une relation existante tombe, s'arrêter et rapporter (règle des tests verrouillés).
- **Tirages du Monte Carlo** : Fireball garde 2 s de période et le même nombre de tics ; aucun sort des rotations ne change de nombre de tics : l'ordre des tirages reste celui d'aujourd'hui (la parité seed n'en dépend pas, elle passe par `rules="seed"`).
- **Pénalité sur les tics** (décision 2) : règle Classic supposée ; le test E3 (Pyroblast r1, niveau 20) ne la départage pas ; Flamestrike r1 (niveau 16) le ferait.
- **Taille** : sept blocs ; si le contexte se remplit, s'arrêter après un bloc vert committé et reprendre dans une nouvelle session.
