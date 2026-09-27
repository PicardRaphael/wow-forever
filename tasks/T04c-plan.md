# T04c — Simulateur fiable pour comparer les builds : fins de ligne, Ignite, Arcane Blast, recharges, régénération et armure, `forever measures refresh`, zone ou donjon à mon niveau : plan

> Plan rédigé le 2026-09-27 (session de cadrage en arrière-plan). **Décisions 1 à 5 à valider par l'utilisateur** (recommandation en gras). Exécution : `/tranche T04c` dans une nouvelle session, sur la branche `t04c`.

## Contexte
T04b a livré les simulateurs de leveling (Monte Carlo et analytique, parité à 1e-12 avec le seed en mode seed). T05 comparera des builds avec ces simulateurs : il faut d'abord corriger ce que le seed simplifie. Demande de l'utilisateur pour T04c, dans l'ordre :
1. `.gitattributes` (`* text=auto eol=lf`), puis retirer le piège CRLF du skill tranche s'il n'est plus utile ;
2. mécaniques : cumul d'Ignite, escalade d'Arcane Blast, B13 (l'analytique tient compte des recharges), B7 (cumul d'Arcane Meditation et de Mage Armor selon la règle Classic, `suppose` ; armure choisie selon le niveau d'apprentissage lu dans les données du client) ;
3. `forever measures refresh` : relance toutes les mesures sur les nouveaux journaux et sauvegardes, affiche ce qui change, n'écrit qu'après confirmation ;
4. « quelle zone ou quel donjon à mon niveau », à partir des données de Questie ;
5. quêtes propres à Forever et modèle d'XP ensuite, reportés si la tranche devient trop grosse : **reportés en T04d** (voir « Report »).

## Constats (relevés le 2026-09-27, lecture seule du client et du cache local, hors tests)

### Fins de ligne
- `.gitattributes` existe déjà (T01) : `forever/data/** -text`, `seed/forever-mage/data/** -text`, `tests/fixtures/** -text` (octets stables pour les empreintes du manifeste). `core.autocrlf` = false.
- `git ls-files --eol` : 295 fichiers `i/lf`. Hors `lf` : `.claude/settings.json` (`i/crlf`, seul fichier texte concerné par une renormalisation) ; sous `-text`, donc intouchés : `tests/fixtures/wago/fetch/SpellName_min.csv` (crlf), `tests/fixtures/wago/1.60.1.70009/enUS/Spell.csv` (mixte), la fixture `.gz` et `synthetic/empty.txt`.
- Conséquence : `* text=auto eol=lf` normalise le code, les tests, la documentation et les skills, mais **pas** les chemins `-text`, qui sont justement ceux qu'écrivent les scripts (`monsters.json`, `mechanics.json`, `spell_scaling.json`, `manifest.json`, fixtures). Le piège CRLF ne disparaît pas : il se restreint à ces chemins.

### Ignite (A18)
- Talent : 8/16/24/32/40 % « over $412538d » (`talents.json`, `Spell.csv` 11119). Aura **412538** (nouvel identifiant, pas le 12654 de Classic Era) : `SpellEffect` aura 226 (périodique factice), période 2000 ms ; `SpellMisc.DurationIndex` 35 → `SpellDuration` 4000 ms ; **`SpellAuraOptions.CumulativeAura` = 1** (Classic Era : 5 cumuls). Une seule aura, sans cumul par empilement : indice d'un Ignite « roulant » (le reste non infligé s'ajoute au nouveau montant et l'aura repart), dont la règle exacte est côté serveur, invisible dans le client.
- Aujourd'hui : `leveling.ignite` = 2 tics de 2 s par critique, sans cumul ni rafraîchissement (`suppose`, seed) ; chaque critique ajoute ses propres tics (`leveling_mc.py`, `ignite_tick_times`). L'analytique compte Ignite en espérance par lancer (`expected_cast`), sans perte à la mort du monstre.

### Arcane Blast (B11, B15)
- `talents.json` (`arcaneBlast`, FC-70009) : `ranks = [[50, 58, 10, 175, 4, 8]]` = dégâts min, max, +10 % de dégâts des **autres** sorts par cumul, +175 % de coût d'Arcane Blast par cumul, 4 cumuls, 8 s. Client : aura 400573 (`SpellEffect` aura 108 : 10, 175 sur le masque d'Arcane Blast, 10 sur un troisième masque ; `CumulativeAura` 4 ; `ProcCharges` 1 ; durée 8000 ms), « or until any other damage spell is cast ». Coût : `mana_pct_base` 0,15 (`spells.json`), rang 1 au niveau 20 (talent de palier 3).
- Aucune rotation arcane dans les simulateurs (`ROTATIONS` = frost, fire) : l'escalade n'est utilisée nulle part.

### B13 et B7 dans les simulateurs
- B13 : `spell_cooldown` (Improved Frost Nova, Wake of Fire) est appliqué par le Monte Carlo ; l'analytique lit `fbl["cooldown_s"]` (recharge du rang, sans Wake of Fire). Frost Nova n'est pas modélisée par l'analytique (option `nova` ignorée).
- B7 : `in_combat_regen_fraction` = `min(1, max(Arcane Meditation, Mage Armor))`, Mage Armor dès `utility.mage_armor_level` (34, copie du seed), **et** le Monte Carlo applique en même temps le ralenti des attaquants de Frost Armor (`farmor`), l'analytique `attacker_swing_s(frost_armor=True)` : deux armures qui s'excluent (« Only one type of Armor spell can be active »).
- Client (cache local `~/.cache/forever/wago/1.60.1.70009`, absent des fixtures) : Mage Armor 6117 / 22782 / 22783 appris aux niveaux **34 / 46 / 58** (`SpellLevels.BaseLevel`, une ligne `SkillLineAbility` chacun), effet aura 134 (`MOD_MANA_REGEN_INTERRUPT`) à 50 ; Arcane Meditation 18462 : même aura 134. Frost Armor 168 / 7300 / 7301 : **1 / 10 / 20** ; Ice Armor 7302 / 7320 / 10219 / 10220 : **30 / 40 / 50 / 60**. Mêmes niveaux que `spells.json.utility` (seed). Deux auras de même type 134 : la règle Classic les additionne (total des modificateurs), plafonnée à 100 %.
- Parité : aucune de ces corrections ne consomme de tirage ; la parité à 1e-12 reste atteignable si le mode seed garde l'ancien comportement.

### Mesures existantes
- `forever logs measure` (lecture, aucune écriture), `forever monsters build` (écrit dans `<cache>/monsters` par défaut ; l'installation dans `forever/data/` s'est faite à la main en T04b, manifeste régénéré). `monsters.json` liste les journaux utilisés (`logs`). Preuves du registre (B1 : n = 50, médiane, 10e percentile) écrites à la main dans le YAML, commentaires en ligne compris ; elles citent des fixtures et un test.
- Sur disque : `Logs/` contient 3 journaux (`WoWCombatLog-092726_145346`, `_150346`, `_174130`), tous déjà dans `monsters.json`. SavedVariables : carnet `journey` de Questie ; `ForeverLoggerDB` pas encore écrit en jeu.

### Questie (zones et donjons)
- `Database/Classic/classicQuestDB.lua` (4 301 lignes) : `questKeys` `requiredLevel` (4), `questLevel` (5), `requiredRaces` (6, masque), `requiredClasses` (7, masque), `zoneOrSort` (17 : > 0 zone `AreaTable`, < 0 catégorie `QuestSort`). `classicNpcDB.lua` : `minLevel`, `maxLevel`, `rank`, `zoneID` (déjà lus).
- `Database/Zones/data/dungeons.lua` : `[areaId] = {nom, identifiants de zone alternatifs, zone parente, entrées}` (Shadowfang Keep 209, Wailing Caverns 718, Razorfen Kraul 491…), les quêtes de donjon portant l'un de ces identifiants dans `zoneOrSort`. `Localization/lookups/lookupZones.lua` : noms de zones **en anglais** (`[14]="Durotar"`), pas de table française. `zoneIds.lua` : constantes (`DUROTAR = 14`).
- **Aucune base propre à Forever dans Questie 11.38.0** (« Forever » n'apparaît que dans des fichiers MoP et des bibliothèques) ; seule piste locale : l'addon `GearQuestForever` (à inventorier). D'où le report des quêtes de Forever.

## Décisions (à valider)
| # | Décision | Recommandé | Alternative |
| --- | --- | --- | --- |
| 1 | Garde de la parité avec le seed | **Nouvelle option `rules` des simulateurs : `"forever"` (défaut, corrections de T04c) ou `"seed"` (comportement du seed à l'identique)** ; `SEED_MODE` des tests de parité et de `test_sim_leveling.py` reçoit `"rules": "seed"` dans le commit « tests » ; la rotation arcane, absente du seed, n'existe qu'en `forever` | Déduire les règles du seed de `mob_source="seed"` (couplage implicite de deux options) |
| 2 | Règle d'Ignite (A18, règle de jeu) | **Ignite roulant, `suppose`** : à chaque critique de feu, montant = part du talent × dégâts du critique + reste non infligé de l'Ignite en cours ; l'aura repart pour sa durée (4 s, client), le reste se répartit sur ses tics (période 2 s, client), **le compteur de tics repart du critique** ; aucun cumul par empilement (`CumulativeAura` 1, `certain`) ; le reste en cours à la mort du monstre est perdu (Monte Carlo) | Compteur de tics conservé (le prochain tic garde sa date, le reste s'ajoute aux tics restants) ; ou cumul de Classic Era (5 empilements), contredit par le client |
| 3 | Armure portée et régénération (B7, I6) | **`armor="auto"` par défaut** : Frost Armor puis Ice Armor au plus haut rang appris, **Mage Armor dès le niveau d'apprentissage de son premier rang lu dans le client** (34) ; sous Mage Armor, plus de ralenti des attaquants ; part gardée en combat = `min(1, Arcane Meditation + Mage Armor portée)` (règle Classic, `suppose`) ; `armor="frost"` ou `"mage"` pour forcer ; l'armure (bonus d'armure de Frost ou Ice Armor) n'est pas ajoutée à l'armure du personnage (comme le seed, question ouverte) | Garder Ice Armor au-delà de 34 (ralenti et armure contre régénération : c'est l'optimiseur T05 qui trancherait) |
| 4 | Rotation arcane | **Rotation `arcane` dans le Monte Carlo et dans l'analytique** : Arcane Blast jusqu'à `ab_stacks` cumuls (option, défaut : maximum du talent), puis un sort de décharge (`ab_dump`, défaut `frostbolt`) qui profite de +10 % par cumul et consomme l'aura ; expiration à 8 s entre deux Arcane Blast ; l'analytique calcule un cycle stationnaire (k Arcane Blast à coûts croissants + une décharge) | Escalade dans le moteur seulement (fonctions testées) ; T05 compare les builds arcanes au Monte Carlo seul, ou pas du tout |
| 5 | Ce qu'écrit `forever measures refresh` après confirmation | **`monsters.json` de la version installée + manifeste, et un instantané des autres mesures dans le cache (`<cache>/measures/last.json`, état de l'outil, pas une donnée du jeu)** ; les preuves du registre (B1, A3) ne sont jamais écrites : la commande affiche l'écart avec la preuve enregistrée et le bloc `preuves` proposé, à reporter à la main avec une fixture ; les PNJ d'un journal disparu du dossier sont conservés (jamais de suppression) | Écrire aussi les preuves du registre par un correctif texte ciblé du bloc `preuves` ; ou `ruamel.yaml` (nouvelle dépendance, accord nécessaire) ; ou un fichier de données `measures.json` par version |

Décisions techniques (sans arbitrage attendu) :
- **Constantes du client** : `leveling.ignite` devient `{"duration_s": 4.0, "tick_s": 2.0, "cumulative": 1}` (source : tables 412538 du client 70009, `certain`) et `leveling.ignite_rule` porte la règle roulante (`suppose`) ; en mode `seed`, le moteur garde 2 tics de 2 s par critique (`duration_s / tick_s` = 2, même résultat). Arcane Blast : tout vient de `talents.json` (`talent_value(gd, pts, "arcaneBlast", i)`, indices 2 à 5) ; coût à `n` cumuls = `mana_pct_base × mana_base × (1 + n × 175 / 100)` (ajout des montants de l'aura par cumul : `probable`) ; Clearcasting rend le lancer gratuit sans retirer de cumul (`suppose`).
- **Armures lues dans le client** : `decode_rules.json` gagne une section `utility_spells` (`frost_armor`, `ice_armor`, `mage_armor` : identifiants et effets retenus) ; `forever decode` ajoute à `spell_scaling.json` une section `utility` (rang, identifiant, niveau d'apprentissage, valeurs d'effet : armure, part de régénération) ; lignes ajoutées aux fixtures wago (`scripts/` d'extraction, depuis le cache local) **sans toucher** aux 15 sorts et 99 rangs de `spells` ; manifeste régénéré. Aucun nouveau fichier de données : pas de changement de `DECODED_FILES` ni des comptes de fichiers.
- **B13 dans l'analytique** : en `rules="forever"`, le cycle de feu prend `spell_cooldown(gd, "fire_blast", rang, pts)` ; Frost Nova reste hors de l'analytique (note au registre).
- **`forever measures refresh`** : `forever/pipeline/refresh.py` (fonctions pures : collecte, mesure, comparaison) ; la CLI demande confirmation par `Deps.confirm` (injectée ; par défaut `input()` si l'entrée est un terminal, sinon refus) ; `--yes` écrit sans demander, `--dry-run` n'écrit jamais ; sans confirmation : code 0, « rien écrit ». Pas d'outil MCP (écriture). Lecture sur disque seulement (`FOREVER_WOW_DIR/Logs`, `WTF/Account/*/SavedVariables/{ForeverLogger,Questie}.lua`), jamais de réseau.
- **Zones et donjons** : lecture de Questie à l'exécution (jamais copiée, décision 3 de T04) ; règle de niveau dans le moteur (`forever/engine/leveling.py`, fonction pure) et ses chiffres dans `mechanics.json` (`leveling.quest_band` : couleurs de quête de Classic, plage verte par tranche de niveau, seuils orange et rouge ; valeurs relevées dans le code d'interface de Classic Era et citées, `suppose`) ; masques de race et de classe : constantes du format de Questie dans `questie.py`, à côté de `NPC_FIELDS` ; noms en anglais (Questie), indiqués comme tels.

## Existant réutilisé
- `forever/sim/leveling_mc.py`, `leveling_analytic.py` (`options_with_defaults`, `ROTATIONS`, `OPTIONS`) ; `forever/engine/damage.py` (`ignite_damage`, `ignite_tick_times`), `mana.py` (`mana_cost`, `in_combat_regen_fraction`), `casting.py` (`spell_cooldown`), `movement.py` (`attacker_swing_s`), `cast.py` (`expected_cast`, buffs `dmg` et `cost`).
- `forever/pipeline/decode.py` (`duration_ms`, `SpellAuraOptions`, `spell_scaling`), `measure.py` (`measure_log`, `gcd_intervals`, `hit_tally`), `monsters.py` (`build_monsters`, `write_monsters`), `levels.py`, `questie.py` (`read_questie`, `_items`, `read_journey`), `lua_table.py`, `addon_sv.py`.
- `forever/cli.py` (`_cmd_logs_measure`, `_cmd_monsters_build`, `_emit`, `_log_provenance`), `forever/mcp_server.py` (`forever_lookup`, `forever_sim_leveling`), `forever/manifest.py` (`write_manifest`), `forever/config.py` (`Deps`).
- `scripts/extract_questie_fixture.py`, extraction wago des fixtures (T03), `tests/conftest.py` (`data_copy`, `write_manifest`, `make_deps`).

## Fichiers
```
.gitattributes                                  + « * text=auto eol=lf » en tête, lignes -text gardées après
.claude/skills/tranche/SKILL.md                  piège CRLF restreint aux chemins -text (et aux scripts d'écriture)
forever/data/1.60.1.70009/decode_rules.json     + utility_spells (armures)
forever/data/1.60.1.70009/spell_scaling.json    + utility (niveaux et effets des armures, lus dans le client)
forever/data/1.60.1.70009/mechanics.json        leveling.ignite (client), leveling.ignite_rule, leveling.quest_band
forever/data/1.60.1.70009/manifest.json
tests/fixtures/wago/1.60.1.70009/enUS|frFR/*.csv   + lignes des armures (SpellLevels, SkillLineAbility, SpellEffect, SpellName, SpellMisc)
tests/fixtures/questie/11.38.0/                 + extraits classicQuestDB.lua (Durotar, les Tarides, Wailing Caverns), dungeons.lua, lookupZones.lua
scripts/extract_questie_fixture.py              + --quests, --zones
forever/engine/damage.py                        + roll_ignite (état roulant, pur)
forever/engine/mana.py                          in_combat_regen_fraction(…, armor, rules) ; + arcane_blast_cost
forever/engine/buffs.py                         (nouveau) aura d'Arcane Blast : cumuls, expiration, consommation, bonus
forever/engine/armor.py                         (nouveau) armure portée selon le niveau (client), ralenti, régénération
forever/engine/leveling.py                      (nouveau) bande de niveaux des quêtes, zone et donjon adaptés
forever/engine/model.py, forever/gamedata.py    + UtilitySpells (armures du client), IgniteRule, QuestBand
forever/sim/leveling_mc.py, leveling_analytic.py   options rules, armor, ab_stacks, ab_dump ; rotation arcane
forever/pipeline/decode.py                      + section utility de spell_scaling
forever/pipeline/questie.py                     + quêtes, donjons, noms de zones
forever/pipeline/refresh.py                     (nouveau) collecte, mesures, comparaison
forever/config.py                               Deps.confirm
forever/cli.py                                  + measures refresh, lookup zones ; sim leveling --rules --armor --rotation arcane --ab-stacks --ab-dump
forever/lookup.py, forever/mcp_server.py        domaine zones de forever_lookup ; forever_sim_leveling + rules, armor, ab_stacks, ab_dump
tests/unit/test_gitattributes.py, test_engine_ignite.py, test_engine_arcane_blast.py, test_engine_armor.py,
tests/unit/test_sim_rules.py, test_measures_refresh.py, test_questie_zones.py, test_zones_cli.py
Tests modifiés : tests/parity/test_sim_leveling_parity.py et tests/unit/test_sim_leveling.py (SEED_MODE + rules),
                 test_spell_scaling.py (section utility), test_decode_version.py si la candidate change, test_registry.py
                 (total, coverage, main), test_contract.py (+ 2 commandes), tests/integration/test_mcp.py (domaine zones),
                 test_network_boundary.py (measures refresh et lookup zones sans réseau), test_engine_leveling.py (B7)
docs/MECHANICS_REGISTRY.yaml, ARCHITECTURE.md, DECISIONS.md (64 et suivantes), OPEN_QUESTIONS.md, ROADMAP.md (T04c, T04d),
docs/DATA_SOURCES.md (quêtes et zones de Questie)
```

## Interfaces
```python
# forever/engine/damage.py      (Registre : A18)
class IgniteState(NamedTuple): remaining: float; ticks: tuple[float, ...]     # instants des tics restants
def roll_ignite(gd, state: IgniteState | None, now: float, amount: float) -> IgniteState
    # rules forever : remaining + amount réparti sur duration_s / tick_s tics à partir de now
def ignite_ticks_due(state, until: float) -> tuple[float, IgniteState | None]   # dégâts dus, état restant

# forever/engine/buffs.py       (Registre : B11, B15)
class ArcaneBlastAura(NamedTuple): stacks: int; expires: float
def arcane_blast_after_cast(gd, pts, aura: ArcaneBlastAura | None, now: float) -> ArcaneBlastAura
def arcane_blast_active(aura, now) -> int                                     # cumuls actifs (0 si expirée)
def arcane_blast_bonus(gd, pts, stacks: int) -> Buffs                         # {"dmg": …} pour les autres sorts

# forever/engine/mana.py        (Registre : B7, B11)
def arcane_blast_cost(gd, rank, pts, ch, stacks: int) -> float
def in_combat_regen_fraction(gd, pts, level, *, armor: str = "auto", rules: str = "forever") -> float
    # forever : min(1, AM + Mage Armor portée) ; seed : min(1, max(AM, Mage Armor dès son niveau))

# forever/engine/armor.py       (Registre : B7, I6)
def worn_armor(gd, level, armor: Literal["auto", "frost", "mage"] = "auto") -> WornArmor
    # WornArmor(kind, rank, learned_level, slows_attackers: bool, regen_while_casting: float, source)

# forever/engine/leveling.py    (Registre : I7)
def quest_color(gd, player_level, quest_level) -> Literal["gray", "green", "yellow", "orange", "red"]
def level_band(gd, player_level) -> tuple[int, int]                           # niveaux de quête utiles

# forever/pipeline/questie.py
class QuestieQuest(NamedTuple): id; name; required_level; quest_level; required_races; required_classes; zone_or_sort
class QuestieDungeon(NamedTuple): area_id; name; alternative_ids: tuple[int, ...]; parent_zone
QuestieDB.quests, .dungeons, .zone_names                                      # lus à la première demande
def zones_for_level(db, gd, level, *, faction=None, player_class="mage") -> ZoneAdvice
    # zones et donjons classés par nombre de quêtes utiles, plages de niveau des quêtes et des PNJ, certitude suppose

# forever/pipeline/refresh.py
def collect_sources(wow_dir: Path) -> RefreshSources                          # journaux, SavedVariables trouvés
def remeasure(gd, sources, questie) -> MeasureSnapshot                        # monstres, B1, A3, coûts, incantations, critiques
def compare(installed_monsters, registry, previous: MeasureSnapshot | None, new: MeasureSnapshot) -> RefreshDiff
def apply_refresh(diff, data_dir, cache_dir) -> list[Path]                    # monsters.json, manifeste, instantané
```

### CLI et MCP (texte français, `--json`, provenance sur chaque sortie, aucun réseau)
| Commande | Codes |
| --- | --- |
| `forever measures refresh [--logs DIR] [--sv DIR] [--questie DIR] [--yes \| --dry-run] [--json]` | 0 (écrit, rien à écrire, ou refusé) ; 2 dossier absent |
| `forever lookup zones --level L [--faction horde\|alliance] [--questie DIR] [--json]` | 0 ; 2 niveau hors bornes, Questie absent |
| `forever sim leveling … [--rules forever\|seed] [--armor auto\|frost\|mage] [--rotation frost\|fire\|arcane] [--ab-stacks N] [--ab-dump frostbolt\|fireball\|arcane_missiles]` | inchangés |
| MCP `forever_lookup(kind="zones", level, faction)` ; `forever_sim_leveling(…, rules, armor, ab_stacks, ab_dump)` | erreur structurée |

`measures refresh` affiche : journaux et sauvegardes trouvés (nouveaux, modifiés, disparus) ; par PNJ, PV ajoutés ou changés ; agrégat `hp_by_level` et coefficients de la correction Questie avant et après ; B1 (n, médiane, 10e percentile) et A3 (touchés et ratés par écart) contre la preuve du registre ; coûts, incantations et critiques contre le dernier instantané ; puis « Écrire ces changements ? [o/N] ».

## Tests attendus (valeurs tirées des fixtures et des données)
- **Bloc A** `test_gitattributes.py` : la première règle est `* text=auto eol=lf`, les trois lignes `-text` suivent ; `git ls-files --eol` ne montre aucun `i/crlf` hors des chemins `-text` (test sauté si git est absent).
- **Bloc B** `test_sim_rules.py` : `rules="seed"` redonne les valeurs de parité de T04b (MC L12 25.51026932538584, analytique L12 23.85926190796625…, via les tests de parité existants) ; option inconnue refusée. `test_engine_armor.py` (fixtures wago étendues, puis données installées) : niveaux d'apprentissage lus Frost Armor 1/10/20, Ice Armor 30/40/50/60, Mage Armor 34/46/58, régénération de Mage Armor 50 % ; `worn_armor` : L20 Frost Armor r3, L30 Ice Armor r1, L33 Ice Armor, L34 Mage Armor r1, L58 Mage Armor r3 ; `armor="frost"` à L40 → Ice Armor r2. `test_engine_leveling.py` (B7) : `rules="forever"` : AM 0 + Mage Armor = 0,5 ; AM 1 + MA = min(1, 0,17 + 0,5) = 0,67 ; AM 3 + MA = 1,0 ; sous L34, AM 3 seul = 0,5 ; `rules="seed"` : max inchangé. Simulateurs, `rules="forever"` : sous Mage Armor, `attacker_swing_s` sans ralenti (MC et analytique) ; un test vérifie qu'ignorer la règle change le résultat (déterministe, analytique). B13 : analytique L20 fire avec Wake of Fire pris : combat plus court qu'avec la recharge du rang en `forever`, identique en `seed` (effet déterministe, pas de Monte Carlo).
- **Bloc C** `test_engine_ignite.py` (constantes lues dans `mechanics.json`, montants de test cités) : critique à t = 0 de 80 → tics 40 à 2 s et 40 à 4 s ; second critique de 60 à t = 1 → reste 80 + 60 = 140, tics 70 à 3 s et 70 à 5 s (décision 2 ; variante « compteur conservé » : 70 à 2 s et 70 à 4 s) ; somme des tics = somme des montants ; décodage des fixtures : 412538 durée 4000 ms, période 2000 ms, `CumulativeAura` 1, égaux à `leveling.ignite`. Monte Carlo L16 fire, graine fixe : `rules="seed"` inchangé (parité) ; `rules="forever"` : dégâts d'Ignite perdus à la mort ≥ 0, total d'Ignite infligé ≤ total posé ; valeurs relevées à l'exécution, écart au seed rapporté (ni sens attendu imposé sur le temps par monstre : effet à mesurer contre le bruit sur plusieurs graines, sinon test par différence).
- **Bloc D** `test_engine_arcane_blast.py` : coût à 0, 1, 2, 3, 4 cumuls = coût de base × 1 ; 2,75 ; 4,5 ; 6,25 ; 8 (L20, coût de base = 0,15 × mana de base, relevé à l'exécution) ; 5e Arcane Blast : cumuls bornés à 4 ; aura expirée après 8 s sans Arcane Blast ; bonus +10 % × cumuls sur un autre sort, pas sur Arcane Blast ; consommée par la décharge ; Clearcasting : lancer gratuit, cumul pris. Simulateurs `rotation="arcane"` : refusée sous L20 ou sans le talent (code 2 en CLI) ; MC reproductible à graine fixe ; analytique à moins de 15 % du MC à L24 et L30 avec un build arcane légal (valeurs relevées ; si l'écart dépasse, s'arrêter et rapporter) ; `ab_stacks=0` = rotation de décharge seule.
- **Bloc E** `test_measures_refresh.py` (dossier temporaire : copie des fixtures de journaux et du carnet de Questie, `data_copy` avec un `monsters.json` construit sur la première fixture seule) : la seconde fixture apparaît « nouvelle » ; PNJ ajoutés et niveaux changés listés ; B1 : n = 50 égal à la preuve (aucun écart) ; `confirm` refusé → aucun fichier modifié (empreintes identiques) ; accepté → `monsters.json` égal à `monsters build` sur les deux fixtures, manifeste valide, instantané écrit dans le cache ; relance → « rien à écrire » ; journal disparu → ses PNJ conservés et signalés ; `--dry-run` n'appelle pas `confirm` ; aucun appel réseau.
- **Bloc F** `test_questie_zones.py` (extraits de fixture) : quêtes lues (niveaux, masques, `zoneOrSort`) ; Wailing Caverns reconnu par son identifiant et ses alternatifs ; `quest_color` selon les chiffres de `leveling.quest_band` (valeurs de la règle Classic citées dans les données, pas dans le test) ; `zones_for_level` L12 Horde : les Tarides en tête, Durotar derrière (quêtes grises), Wailing Caverns listé avec ses plages ; quêtes d'une autre faction ou d'une autre classe exclues ; certitude `suppose`, source Questie et version. `test_zones_cli.py`, `test_contract.py`, `tests/integration/test_mcp.py` : `lookup zones` code 0, provenance complète ; `forever_lookup(kind="zones")` ; Questie absent → erreur structurée.
- **Bloc G** `test_registry.py` : `total` 103 → 104 (I7), `coverage` 31/103 → 33/104 (I7 ajoutée et testée, B15 passe de `absent` à `teste` ; A18, B7, B11, B13, I1, I6 déjà comptées) ; sortie de `main`.

## Étapes (un cycle rouge → vert par bloc, commits `T04c: tests (bloc X)` puis `T04c: bloc X vert`)
0. `git switch -c t04c`.
1. **Bloc A — fins de ligne** : `.gitattributes` (`* text=auto eol=lf` en tête), `git add --renormalize .` (seul `.claude/settings.json` change dans l'index ; la copie de travail n'est pas réécrite, aucune écriture refusée par le mode auto), `git ls-files --eol` contrôlé ; piège CRLF du skill restreint aux chemins `-text` et aux scripts d'écriture (`write_manifest`, `write_monsters`, `decode` : vérifier `newline="\n"` ou `write_bytes`) ; commit `T04c: fins de ligne normalisées par Git`.
2. **Bloc B — règles Forever, B13, B7, armure** : option `rules`, armures dans `decode_rules.json` et `spell_scaling.json` (fixtures wago étendues depuis le cache local, manifeste), `worn_armor`, cumul de la régénération, ralenti retiré sous Mage Armor, recharge de Fire Blast dans l'analytique.
3. **Bloc C — Ignite roulant** : `leveling.ignite` et `leveling.ignite_rule`, `roll_ignite`, Monte Carlo (mode `forever`), note sur l'analytique (espérance inchangée, perte à la mort non modélisée).
4. **Bloc D — Arcane Blast** : `buffs.py`, `arcane_blast_cost`, rotation `arcane` (MC puis analytique), options CLI et MCP.
5. **Bloc E — `forever measures refresh`** : `refresh.py`, `Deps.confirm`, CLI, tests sur fixtures.
6. **Bloc F — zone ou donjon à mon niveau** : extraits Questie, lecture des quêtes et des donjons, `leveling.quest_band`, `forever/engine/leveling.py`, `lookup zones`, domaine `zones` de `forever_lookup`.
7. **Bloc G — registre et documentation** : A18 (`suppose`, règle roulante, `CumulativeAura` 1 `certain`), B7 (cumul Classic, armure), B11 (escalade), B13 (analytique), B15 (aura d'Arcane Blast), I1 (rotation arcane), I6 (armure), I7 (nouvelle) ; `ARCHITECTURE.md`, `DECISIONS.md` (64 et suivantes), `OPEN_QUESTIONS.md`, `DATA_SOURCES.md`, `ROADMAP.md` (T04c fait, ligne T04d).
8. `/verifier`, relecteur et auditeur des mécaniques, push, CI verte Ubuntu et Windows, fusion en avance rapide, suppression de la branche, résumé. Si le contexte se remplit : s'arrêter après un bloc vert committé (ordre de priorité : A, B, C, D ; E et F peuvent glisser en T04d).

## Report en T04d (tranche suivante, avant T05 dans la table)
- Quêtes propres à Forever : aucune base Forever dans Questie 11.38.0 ; inventaire des sources locales (`GearQuestForever`, tables de quêtes du client par wago, annonces), licence, puis ingestion.
- Modèle d'XP de Forever (XP des monstres et des quêtes) : `leveling.mob_xp` reste la règle Classic (`suppose`) ; l'XP par heure des simulateurs a la même échelle pour tous les builds, ce qui ne gêne pas leur comparaison en T05.
- T05 dépend de T04c seulement ; T04d s'intercale sans bloquer (à confirmer par l'utilisateur).

## Hors périmètre
- Frost Nova et contrôle de foule dans l'analytique ; bonus d'armure de Frost et Ice Armor sur l'armure du personnage (question ouverte) ; Missile Barrage (400588) et autres effets d'Arcane Blast.
- Optimiseur de talents et respec (T05) : la rotation arcane n'est pas optimisée ici (`ab_stacks` est un paramètre).
- Écriture du registre par un outil ; outil MCP de rafraîchissement ; suppression de données.
- Traduction française des noms de zones (Questie n'en fournit pas) ; butin et boss des donjons (DJ1).
- Tout accès réseau nouveau ; copie de la base Questie.

## Risques
- **Parité** : l'option `rules` doit couvrir toutes les branches modifiées ; un oubli casse le 1e-12 (les tests de parité existants le montrent).
- **Mode `forever` et critère des 15 %** : Ignite roulant, régénération cumulée et armure changent l'écart analytique / MC ; résultat à rapporter, pas à corriger ; les tests du seed en mode par défaut (T04b) peuvent tomber : s'arrêter et montrer les valeurs.
- **Règles `suppose`** (Ignite roulant, cumul de la régénération, coût d'Arcane Blast, Clearcasting) : campagnes de journaux à prévoir (Ignite : `SPELL_PERIODIC_DAMAGE` de 412538 après deux critiques rapprochés ; Arcane Blast : coûts relevés par `SPELL_CAST_SUCCESS` et bloc avancé).
- **Bruit du Monte Carlo** : les effets de B7 et d'Ignite sont petits ; ils se testent sur l'analytique ou par différence (piège du skill).
- **Questie** : format d'addon tiers ; quêtes Classic Era sans correction Forever (niveaux et zones peut-être modifiés) ; `suppose` partout.
- **Confirmation interactive** : l'entrée standard de la session est nulle ; les tests injectent `confirm`, la vraie exécution se fait par l'utilisateur (`! uv run forever measures refresh`).

## Critères de fin (T04c)
- `.gitattributes` normalise le texte en LF ; `git ls-files --eol` : aucun `i/crlf` hors des chemins `-text` ; piège du skill restreint.
- `rules="seed"` : parité à 1e-12 avec le seed inchangée ; `rules="forever"` : Ignite roulant, régénération cumulée et armure choisie selon le niveau lu dans le client, recharge de Fire Blast dans l'analytique ; rotation `arcane` avec escalade du coût et du bonus, dans les deux simulateurs.
- `forever measures refresh` affiche les changements et n'écrit qu'après confirmation (tests : refus, accord, relance sans changement, journal disparu).
- `forever lookup zones --level 12` et `forever_lookup(kind="zones")` répondent avec provenance, certitude `suppose`, source Questie.
- Registre : A18, B7, B11, B13, B15, I1, I6 à jour, I7 ajoutée ; `uv run tasks.py verify` vert.

## Questions ouvertes à ajouter
- A18 : Ignite de Forever (aura 412538, non cumulable) : le compteur de tics repart-il au rafraîchissement ? Mesurer deux critiques rapprochés dans un journal.
- B7 : cumul d'Arcane Meditation et de Mage Armor (règle Classic supposée) ; bonus d'armure de Frost et Ice Armor non modélisé.
- B11 : coût d'Arcane Blast à `n` cumuls (1 + 1,75 n supposé additif) et effet de Clearcasting sur le cumul.
- I7 : couleurs de quête de Forever identiques à Classic ? Niveaux de quête de Forever (Questie Classic Era sans correction).
- T04d : source des quêtes propres à Forever (aucune dans Questie 11.38.0).
