# T05 — Builds du Mage par contexte (optimiseur, Arcane Power, sensibilité, respec, PvP) : plan

> Plan rédigé le 2026-09-28 (session de cadrage en arrière-plan), d'après la demande de l'utilisateur du même jour. **Décisions D1 à D10 à valider** (option recommandée en gras). Exécution : `/tranche T05` dans une nouvelle session, bloc par bloc (cycle rouge → vert par bloc) ; la tranche tiendra probablement en deux ou trois sessions.
> Préalables faits dans la session de cadrage : Improved Cone of Cold à 12 / 23 / 35 % en mode forever (décision 77, commit `fa1c533`) ; T04d placée après T06 (décision 78, commit `4524943`) ; rubrique « Angles morts » ajoutée au résumé de fin de tranche (`.claude/skills/tranche/SKILL.md`, `CLAUDE.md`, commit du plan).

## Validation (2026-09-28)
Plan accepté par l'utilisateur ; décisions reportées dans `docs/DECISIONS.md` (79 à 89). Amendements :
- **D5** : Hot Streak modélisé dès T05 : Pyroblast entre dans la rotation de feu quand le talent est pris ; le nombre de cumuls de Hot Streak avant de le lancer (`hs_stacks`) est un choix du build, comme `ab_stacks`. L'analytique porte aussi Hot Streak (l'optimiseur trie à l'analytique). Presence of Mind, Combustion et Cold Snap restent des angles morts chiffrés.
- **D8** : option `--talented-bonus N` (bonus Legacy « Talented », défaut 0, hypothèse affichée), aussi dans `forever_build`.
- **Ignite (bloc B)** : lire soi-même les notes de Blizzard du 24/09/2026 en source primaire, établir à quelle version du client elles s'appliquent (1.60.1.70009 ou suivante). Le moteur prend déjà Ignite sur le critique final (`ignite_damage` reçoit les dégâts multipliés, les tics ne sont pas remultipliés) : si les notes s'appliquent à 70009, un test verrouille cette assiette et A18 cite la source ; sinon, huitième hypothèse de sensibilité (variante : tics remultipliés, règle antérieure) et question ouverte. Wake of Fire, Hot Streak et Arcane Missiles vérifiés de même contre le client ; écart → `OPEN_QUESTIONS`, ou T08 s'il concerne une version suivante.
- **Certitude** : tout build au-delà du plafond de la bêta (niveau 20, clé de données `build.beta_level_cap`) affiche qu'il n'est pas vérifiable en jeu avant la sortie.
- Un test verrouillé faux : demandes regroupées dans `tasks/T05-corrections.md`, présentées avant la fusion. Contexte plein : arrêt après un bloc vert committé.
- Bloc A découpé : A1 (documentation, sans cycle rouge) puis A2 (données, `decode`, chargeurs).

## Contexte
Objectif de l'utilisateur : pouvoir demander « quel build pour tel contexte à tel niveau » et faire confiance à la réponse. Demande, dans l'ordre :
1. contextes : **leveling** (ordre des talents niveau par niveau, de 10 à 60), **donjon**, **raid**, **PvP** (champs de bataille, monde ouvert) ; donjon et raid sur des scénarios **provisoires** clairement marqués (cible unique prolongée, paquets de monstres), affinés en DJ1 et T09 ; équipement = fiche de base par niveau tant que T07 et T10 ne sont pas faits, hypothèse affichée ;
2. pour chaque build : talents et ordre d'apprentissage ; raison de chaque choix ; écart chiffré avec l'alternative la plus proche, avec intervalle de confiance ; certitude et hypothèses ; armure (`armor`) et nombre d'Arcane Blast (`ab_stacks`) traités comme des choix du build ; conseil de respec (coût, gain attendu, niveau conseillé) ; angles morts propres au build ;
3. Arcane Power dans les rotations des simulateurs (prévu par la feuille de route, décision 74) ;
4. méthode : tri des candidats par le modèle analytique, décision au Monte Carlo (graine fixe, intervalle de confiance), builds légaux seulement (prérequis, points disponibles par niveau) ;
5. vérification : stabilité (autres graines) ; sensibilité aux hypothèses incertaines (ratés A3, règle d'Ignite, PV corrigés, cumul de régénération, pénalité des sorts de bas niveau E2, cumul multiplicatif des bonus E6, coefficient d'Ice Lance E4), bascule signalée ; comparaison avec les builds de la communauté (sous-agent de recherche web, source et date ; chaque écart expliqué : mécanique non modélisée, nouvelle entrée du registre, ou source douteuse, signalée ; aucune source prise pour vérité) ;
6. intégrer les conclusions retenues de `docs/research/videos/BVSgeHp3sWU.md` et de `tasks/inventaire-addons.md` ;
7. portage du seed : optimiseur, profil PvP, respec, tests reportés `optimiseur_legal` et `pvp_et_respec`, parité en mode seed ;
8. sorties : `forever build <contexte> --level N` (texte et `--json`, provenance) et l'outil MCP correspondant (décision 63) ;
9. règle incertaine : `suppose` et `docs/OPEN_QUESTIONS.md`, jamais deviner.

## Constats (relevés le 2026-09-28, lecture seule)

### Seed (`seed/forever-mage/scripts/`)
- `optimize.py` : `leveling()` (faisceau sur les ordres légaux ; présélection analytique avec anticipation gloutonne `rollout_value` sur `depth` niveaux ; décision au Monte Carlo sur `shortlist` candidats, rotations `frost` et `fire` seulement ; score = Σ temps par monstre × `level_weight(L)` = `xp_to_next[L] / mob_xp(L)`) ; `score_plan()` ; `raid()` passe par `pve_raid.py` et un pont Node (`engine/pve_bridge.js`) ; `pvp()` : faisceau glouton noté par `pvp.score`.
- Valeurs de référence calculées avec le code du seed (`repr()`, script jetable hors dépôt) :
    - `op.leveling("Orc", 10, 14, beam=2, depth=2, mc_n=40)` : `hours_equiv` = **3.411975105216378**, points `{"improvedFrostbolt": 4, "elementalPrecision": 1}`, étapes `(10, improvedFrostbolt, 23.83, frost)`, `(11, improvedFrostbolt, 23.68, frost)`, `(12, improvedFrostbolt, 25.44, frost)`, `(13, elementalPrecision, 27.52, frost)`, `(14, improvedFrostbolt, 26.68, frost)` (0,5 s) ;
    - `pvp.score({"improvedFrostbolt": 5, "frostbite": 3, "elementalPrecision": 2, "iceLance": 1}, 20)` : `score` 45.1, `burst` 208.4, `control` 41.0, `survival` 8.3, `sustain` 26.0, séquence « Givre : Éclair, Nova, Javelot(s) sur gel », `statut` EST ;
    - `pvp.score({"improvedFrostbolt": 5, "frostbite": 3, "elementalPrecision": 3, "iceShards": 5}, 60)` : `score` 82.0, `burst` 1878.4, `control` 65.0, `survival` 8.3, `sustain` 263.5 ;
    - `respec.advise_leveling(20, {"improvedFireball": 5}, {"improvedFrostbolt": 5}, 5)` : `xp_h_actuel` 17643, `xp_h_cible` 16537, `heures_gagnees` -0.31, `cout_po` 1, `bilan_po_equiv` -2.7, verdict « garder » ; `respec.cost(i)` pour i = 0…11 : 1, 5, 10, …, 50, 50 ;
    - `op.pvp(None, 20, "Orc", beam=2)` : `{"frostWarding": 2, "arcaneFocus": 4, "elementalPrecision": 1, "wandSpecialization": 2, "arcaneResilience": 2}`, score 38.6. **Résultat absurde** (aucun point utile au burst ni au contrôle) : le faisceau glouton ne voit la valeur des talents qu'une fois le palier atteint. Preuve que l'optimiseur PvP du seed ne suffit pas au mode forever (D6).
- Tests reportés (`tests/run_all.py`) : `optimiseur_legal` (ordre légal à chaque niveau, `leveling("Orc", 10, 14, beam=2, depth=2, mc_n=40)`) ; `pvp_et_respec` (`score > 0`, `statut` EST, verdict dans « réinitialiser » / « garder »).
- Chiffres codés en dur, à déplacer dans `forever/data/` (invariant) :
    - `pvp.py` : `REF` (burst 2500, control 30, survival 30, sustain 350), `DEFAULT_W` (0,35 / 0,25 / 0,25 / 0,15), plafond 1,5 par composante, × 100 ; fenêtre de burst 6 s, pas de 1,5 s, 0,6 à partir du second Ice Lance, × 1,12 sous Combustion, × 1,30 sous Arcane Power (= talent, lu dans `talents.json`), 1,2 et 0,8 de la séquence arcane ; gel effectif 5 s, ralentis pondérés 0,5, 60 / 2,5 lancers par minute, moitié des sorts de givre pour Frostbite, ralenti d'Éclair 40 s par minute, Cone of Cold 6 × 6, Impact 2 s, Blast Wave 6 × 60 / 45, silence 60 / 30 et verrouillage 10 × 0,3, seuil `L >= 24` (Counterspell) ; survie : Ice Block 10 × 60 / 300 (× 1,6 avec Cold Snap), Ice Barrier absorbé / 300 × 60 / 30 × 3 (« 1 s ≈ 100 dégâts »), Blink `L >= 20` et 60 / 15 × 1,2, Frost Warding / 100 × 2, Arcane Resilience / 100 × 3, Improved Frost Nova × 0,5, Permafrost × 0,1, bonus racial (Human 6, Undead 3, Orc 3,5, Gnome 3, Troll 1,5, autres 1) ; `sustain` : part en mouvement 0,4, Ice Lance × 0,3 ; fiche de niveau 60 `{"sp": 400, "spell_crit": 0.12}`.
    - `respec.py` : `GOLD_PER_HOUR` (10 : 1, 20 : 4, 30 : 9, 40 : 16, 50 : 25, 60 : 40, EST), trajet 6 min ; ligne morte `cur = min(...)` écrasée par `cur = max(...)` (comportement effectif porté, noté comme `cyc_time` en T04b).
    - `optimize.py` : pondérations 0,5 / 0,5 (instant et anticipation), 0,25 (tri du faisceau) : paramètres de méthode, pas des chiffres de jeu (constantes nommées du module, comme `STEP_S`).
- `respec.json` (données) n'est pas lu par `forever/gamedata.py` ; certitude « PC » (vocabulaire du seed) à traduire (`probable`).

### Moteur et simulateurs aujourd'hui
- `forever/engine/talents.py` : `points_available`, `check_build`, `legal_additions`, `tree_split` (portés en T02). `forever/sim/leveling_mc.py` (`kill_mc`, `mc` : moyenne seule, aucune dispersion), `leveling_analytic.py` (`kill_analytic`, `arcane_cycle`), `forever/leveling.py` (`simulate_leveling`, hypothèses, provenance).
- Arcane Power : `forever/engine/buffs.py` `arcane_power_buffs` (durée 15 s, +30 % de dégâts, +30 % de coût, `talents.json`) ; hors rotations (décision 74). **Recharge 180 000 ms** dans le client (`SpellCooldowns`, ligne 53936, sort 12042, fixture `tests/fixtures/wago/1.60.1.70009/enUS/SpellCooldowns.csv` comprise) mais **absente de `forever/data/`**.
- Hypothèses incertaines, où elles vivent :

| Hypothèse | Registre | Aujourd'hui | Variante de comparaison |
| --- | --- | --- | --- |
| A3 ratés contre une cible plus basse | A3 | `hit.miss_per_level_below` (règle Classic, `suppose`) | 0 : raté à écart 0 à tout écart négatif (valeur du seed) |
| Règle d'Ignite | A18 | `leveling.ignite_rule` = `rolling` (seule valeur acceptée par `roll_ignite`) | `independent` : un Ignite par critique, tics fixes (règle du seed, `ignite_tick_times`) |
| PV corrigés | H11 | `mob_source` = `measured` (correction Questie → Forever) | `seed` (PV du seed) |
| Cumul de régénération | B7, I6 | codé par `rules` dans `mana.py` (`forever` : somme ; `seed` : maximum) | maximum |
| Pénalité des sorts de bas niveau (E2) | G4 | `coefficient.low_level_default` (`true`, `suppose`) | `false` |
| Cumul des bonus en pourcentage (E6) | A20 | codé par `rules` dans `damage.py` (`forever` : produit ; `seed` : somme) | somme |
| Coefficient d'Ice Lance (E4) | G4 | client : 0 (mode forever) | 0,1429 (`coefficient.ice_lance` de `mechanics.json`, estimation du seed) |

- Talents que le code de `forever/` ne lit pas (hors talents qui n'apprennent qu'un sort : Ice Lance, Pyroblast, Blast Wave, Arcane Blast) : `wandSpecialization`, `improvedChanneling`, `arcaneSubtlety`, `magicAbsorption`, `arcaneResilience`, `arcaneGeometry`, `arcaneShielding`, `improvedCounterspell`, `missileBarrage`, `presenceOfMind`, `flameThrowing`, `impact`, `improvedFlamestrike`, `improvedScorch`, `improvedFireWard`, `hotStreak`, `combustion`, `frostWarding`, `improvedBlizzard`, `iceBlock`, `coldSnap`, `iceBarrier`. Aucun n'a d'entrée propre au registre (A19 touche Hot Streak pour les critiques périodiques seulement). L'optimiseur leur donnerait une valeur nulle : c'est la première source d'angles morts.
- Descriptions utiles (`talents.json`) : Missile Barrage (Arcane Blast 40 %, Fireball, Frostbolt, Frostfire Bolt 20 % : prochain Arcane Missiles canalisé 50 % plus court, sans coût, un missile toutes les 0,5 s) ; Hot Streak de Forever (critique non périodique de Fireball, Frostfire Bolt, Fire Blast ou Scorch : incantation de Pyroblast réduite de 25 % par cumul, 3 cumuls, 15 s) ; Flame Throwing et Arcane Geometry (portée des sorts de feu et des arcanes, même mécanisme qu'Arctic Reach, C2).
- Registre : 104 mécaniques, dont 70 `absent` ; I5 (optimiseur et respec) `absent`. Entrées `absent` qui pèsent sur le classement des builds : A12-A14 (résistances, sorts binaires, résistance liée au niveau : frost contre fire en raid), B10 (Évocation, potions : combats longs), B14 (procs), C7 (plafond de cibles des zones), D1 (buffs de groupe), F6 (armes de lanceur), H2 (armure et résistances de la cible), H3 (nombre de cibles), H5 (durée et variance), H9 (menace).
- CLI : `forever sim leveling`, `forever chart leveling` ; MCP : `forever_status`, `forever_lookup`, `forever_explain_mechanic`, `forever_sim_leveling`. `docs/ARCHITECTURE.md` prévoit `forever_optimize_talents` (objectifs leveling, raid, PvP) et `forever_sim_raid`.

### Conclusions retenues des documents de recherche
- **Vidéo BVSgeHp3sWU** : coefficients du client (fait en T04e) ; questions ouvertes E2 (pénalité des bas niveaux), E4 (Ice Lance), E6 (cumul des bonus), E7 (arrondi des bornes) : E2, E4 et E6 entrent dans la sensibilité (E7 : effet ≤ 0,5 point de dégâts, sous le bruit du Monte Carlo, non retenu). Puissance des sorts de pré-raid 534 : **estimation de l'auteur, pas un chiffre de jeu** ; reprise comme fiche de comparaison du niveau 60 (`--sp`), jamais comme défaut. Chaîne multiplicative (V13, V18) : `probable`, déjà en place.
- **Inventaire des addons** : aucun addon installé ne publie de build de talents ; l'XP de Forever est réglée **par quête** (ForeverDungeonJournal, `questcache.wdb`), pas par un facteur global → `level_weight` garde `xp_to_next` et l'XP de monstre Classic, hypothèse affichée (T04d) ; les poids de stats de GearQuestForever sont ceux de TBC : exclus ; les calculateurs cités par ForeverDungeonJournal (`SOURCES.txt` : wowforevertalents, wowf.io, 60.tools) sont ajoutés aux sources de la recherche communautaire.
- **Recherche communautaire** (`docs/research/community-builds-mage.md`, 2026-09-28, sous-agent de recherche web) : 55 builds visant Forever (leveling 22, donjon 4, raid 25, PvP 4), 20 fiches détaillées (C1 à C20) et 35 courtes (A1 à A35), liens de calculateur décodés vers les clés de `talents.json`, légalité contrôlée (7 illégaux : C5, C14, C19, A11, A26, A27, A28). Aucun Discord ni Reddit lu. La bêta plafonne au niveau 20 : tout build de niveau 30 à 60 est théorique ou un preset de simulateur (ElliotWood, gunba, MythicSim). Tendances : Givre en leveling (Ice Lance ; désaccord sur Improved Frostbolt au niveau 20), Arcane en donjon, raid dispersé sur les trois arbres (Arcane Blast à 4 cumuls dans les guides, 3 dans l'APL ElliotWood), PvP Givre de contrôle. Elle sert de liste d'entrée au bloc J ; aucune de ses valeurs n'entre dans les données. Apports pour le plan :
    - **notes de développement de Blizzard du 24/09/2026** (citées par la recherche, à lire en source primaire au bloc B) : durées de Wake of Fire et de Hot Streak allongées, **Ignite ne cumule plus deux fois les bonus en pourcentage**, changement d'Arcane Missiles. Vérifier que le client 1.60.1.70009 et `ignite_damage` (part d'Ignite prise sur le critique déjà multiplié) les reflètent ; sinon question ouverte et variante de sensibilité (règle d'Ignite : assiette avant ou après les bonus) ;
    - **bonus Legacy « Talented »** (points de talent en plus, variantes à 16 points au niveau 20 chez Wowhead) : `points_available(…, talented_bonus)` existe ; option `--talented-bonus N` de `forever build` (défaut 0, hypothèse affichée) ;
    - **Molten Armor** recommandée par 8 entrées mais absente de Forever selon deux sources : nos choix d'armure (`auto`, `frost`, `mage`) n'en dépendent pas ; écart classé « source douteuse » au bloc J ;
    - **Shatter** à 5 rangs (Classic) dans wowforeverbuilds.com et d'anciens presets, 3 dans `talents.json` : cause de la plupart des builds illégaux ;
    - builds de simulateur (ElliotWood, gunba, MythicSim) = comparaison la plus utile en raid : mêmes presets repris d'un simulateur à l'autre, donc une seule source réelle par preset.

## Décisions (à valider)
1. **D1 — Arcane Power dans les rotations** (décision 74). **Politique « au pull dès que prête »** : en leveling, `mc()` tient une horloge de session (somme des `total` des combats) et `kill_mc` reçoit `arcane_power_ready` ; l'aura est posée au premier lancer du combat si la recharge est écoulée, dure `min(15 s, combat)`, et fait payer +30 % de coût ; aucune consommation de tirage (`rng`) ; l'analytique prend l'espérance : part des combats avec l'aura = `min(1, cycle / recharge)`, avec `cycle = combat + repos + trajet` (point fixe, deux itérations). Scénarios de donjon et de raid : aura à 0 s puis à chaque recharge. PvP : aura dans la fenêtre de burst si le talent est pris. Mode seed : jamais (parité) ; option `arcane_power` (`auto`, `off`) des simulateurs, `off` imposé en seed. Recharge lue dans le client (D2). Alternative écartée : taux de présence fixe sans horloge.
2. **D2 — Recharges des talents actifs dans les données** : `decode` lit `SpellCooldowns.RecoveryTime` des sorts de talent listés dans `decode_rules.json` (`talent_cooldowns` : Arcane Power seulement en T05 ; Presence of Mind, Combustion, Cold Snap, Ice Block, Ice Barrier, Blast Wave ajoutés à la même liste pour les angles morts) et les écrit dans `spell_scaling.json` (`talent_cooldowns`, en millisecondes, `certain`). Alternative écartée : clé de `mechanics.json` recopiée à la main.
3. **D3 — Hypothèses incertaines pilotées par les données, variantes par substitution** : deux règles aujourd'hui codées par `rules` deviennent des clés de `mechanics.json` : `mana.regen_stacking` (`sum`, `suppose` ; variante `max`) et `damage.bonus_stacking` (`multiplicative`, `probable` ; variante `additive`) ; `leveling.ignite_rule` accepte `independent` (règle du seed) en plus de `rolling`. Le mode seed force les valeurs du seed comme aujourd'hui (parité). Chaque clé incertaine porte sa plage dans un champ `range` (liste des variantes, avec la source de chacune) ; `forever/engine/variants.py` construit une `GameData` modifiée par `dataclasses.replace`, fonction pure, une hypothèse à la fois. Les sept hypothèses de la demande sont les seules variantes de T05.
4. **D4 — Scénarios provisoires de donjon et de raid** : clés `build.scenarios.*` de `mechanics.json` (`suppose`, source « scénario provisoire T05, affiné en DJ1 / T09 ») : `dungeon_boss` (cible unique, niveau + 2, 60 s), `dungeon_pack` (4 cibles, niveau + 1, PV du monstre normal du niveau, tank présent), `raid_boss` (cible unique, niveau + 3, 180 s, durée du seed). Tank présent partout : pas de coups du monstre sur le Mage, pas de recul, pas de course ; mana bornée (réserve + régénération, sans Évocation ni potion : B10 en angle mort). Métrique : dégâts par seconde sur la durée (dégâts nuls une fois la mana épuisée). Nouveau simulateur `forever/sim/encounter.py` (analytique et Monte Carlo, même moteur). Rotation de paquet : Frost Nova puis priorité Blast Wave, Cone of Cold, Arcane Explosion, Blizzard, Flamestrike selon les sorts appris (candidats évalués, le meilleur retenu comme pour `ab_stacks`) ; plafond de cibles (C7) et menace (H9) en angles morts. Pas de pont Node (`pve_raid.py` non porté : T09). Chaque sortie de donjon ou de raid porte la mention « scénario provisoire ».
5. **D5 — Talents non modélisés** : T05 modélise les trois dont la mécanique est déjà dans le moteur ou proche : **Flame Throwing et Arcane Geometry** (portée, comme Arctic Reach) et **Missile Barrage** (décharge Arcane Missiles de la rotation arcane : proc à l'impact des sorts listés, canalisation raccourcie et gratuite, `B14` passe `modelise` pour ce seul proc). Les autres deviennent des angles morts chiffrés : Hot Streak (demande Pyroblast dans la rotation de feu), Presence of Mind, Combustion, Cold Snap, Impact, Improved Scorch (T09), Improved Blizzard, Ice Barrier, Ice Block, Improved Counterspell, Wand Specialization (baguettes : F6). Alternative : modéliser aussi Hot Streak (Pyroblast dans la rotation de feu), plus coûteux ; à choisir si l'utilisateur veut que le Feu soit jugé sans réserve dès T05.
6. **D6 — Optimiseur** : leveling : faisceau du seed (paramètres `beam`, `depth`, `shortlist`, `mc_n`), étendu aux rotations `arcane` et aux choix de build `armor` (`auto`, `frost`, `mage` là où elle est apprise) et `ab_stacks` (0 au maximum du talent) avec `ab_dump`, évalués pour chaque candidat (meilleure combinaison à l'analytique) ; donjon, raid, PvP à un niveau N : départs multiples (un par arbre dominant et par hybride légal : Givre, Feu, Arcanes, Arcanes-Givre, Arcanes-Feu, Feu-Givre, construits par faisceau depuis chaque arbre), puis recherche locale (déplacer un point d'un talent à un autre en gardant la légalité) jusqu'à un optimum local ; tri à l'analytique, décision au Monte Carlo sur les `shortlist` meilleurs. Mode seed : méthodes du seed à l'identique (`leveling`, `pvp` glouton), parité.
7. **D7 — Règle de décision et stabilité** : Monte Carlo à tirages communs (même graine pour les candidats comparés) ; nouvelle fonction `mc_stats` (moyenne, écart-type, erreur standard, n) à côté de `mc()` inchangée (parité) ; différence appariée entre les deux premiers et son intervalle de confiance à 95 % (`build.confidence` = 0,95, paramètre de méthode dans `mechanics.json`) ; intervalle qui exclut 0 → gagnant ; sinon « égalité statistique, départagée par l'analytique » affichée. Stabilité : la décision finale (deux ou trois finalistes) rejouée sur `build.stability_seeds` graines (5 par défaut) ; « stable » si le même gagnant sort à chaque graine, sinon signalé.
8. **D8 — Sorties** : CLI `forever build <contexte> --level N` avec `contexte` ∈ `leveling`, `dungeon`, `raid`, `pvp-bg`, `pvp-world` ; options `--race`, `--current <talents>` (build actuel pour la respec), `--respecs <n>` (réinitialisations déjà faites), `--sp`, `--crit` (fiche remplacée), `--preset rapide|complet`, `--seed`, `--rules`, `--sensitivity` (défaut : oui), `--json`. `forever build leveling --level N` rend l'ordre de 10 à N **et** le build à N. MCP : un seul outil de calcul `forever_build(context, level, …)` (décision 63), qui remplace `forever_optimize_talents` prévu dans `docs/ARCHITECTURE.md` ; même service que le CLI. `forever_sim_raid` reste prévu pour T09.
9. **D9 — Respec** : coût = barème de `respec.json` (1, 5 po observés sur la bêta, puis barème Classic jusqu'à 50 po, `probable` pour les deux premiers, `suppose` au-delà) selon `--respecs` ; gain en leveling = heures économisées d'ici au niveau visé en passant du build actuel (ou du chemin de leveling) au meilleur build libre à L, puis au chemin réoptimisé ; valeur en or par `respec.gold_per_hour` (table du seed, `suppose`) et `respec.trip_minutes` ; **niveau conseillé** = niveau L où `gain × or/heure − coût − trajet` est le plus grand, s'il est positif (sinon « garder »). Pour un contexte hors leveling (donjon, raid, PvP) : coût + écart de métrique entre le build de leveling au niveau N et le build du contexte (avec intervalle de confiance), sans conversion en or.
10. **D10 — Angles morts lisibles par le code** : champ optionnel `angle_mort` des entrées du registre (`talents` : clés concernées ; `contextes` ; `estimation` : nom d'une fonction d'estimation de `forever/engine/blind_spots.py` ou `null`) ; `forever/registry.py` le valide ; chaque build liste les entrées dont un talent est dans le build ou parmi ses alternatives proches, et dont le contexte correspond, avec l'effet estimé par le moteur (borne haute, en % de la métrique) ou « non chiffré ». Nouvelles entrées du registre par famille : talents actifs à recharge (Presence of Mind, Combustion, Cold Snap, Ice Block, Ice Barrier), procs de talent (Hot Streak, Impact ; Missile Barrage modélisé), portée et utilitaires (Flame Throwing, Arcane Geometry modélisés ; Improved Counterspell, Frost Warding, Arcane Resilience, Magic Absorption, Arcane Shielding, Improved Fire Ward, Improved Channeling), baguettes. Une question ouverte par règle `suppose`.

## Existant réutilisé
- Moteur : `talents.py` (légalité), `cast.py` (`expected_cast`), `damage.py` (multiplicateurs, Ignite), `buffs.py` (Arcane Blast, `arcane_power_buffs`, `merge_buffs`), `mana.py`, `armor.py` (`worn_armor`, `ARMOR_CHOICES`), `movement.py` (`spell_range`), `monsters.py` (`mob_hp`, `mob_xp`, `MOB_SOURCES`).
- Simulateurs : `leveling_mc.py`, `leveling_analytic.py` (options `rules`, `armor`, `ab_stacks`, `ab_dump`, `low_level_penalty`) ; `forever/leveling.py` (`check_talents`, `check_level`, `check_race`, `assumptions`, `damage_assumptions`, provenance).
- Pipeline : `decode` et `decode_rules.json` (`utility_spells`, T04c) pour les recharges ; `write_manifest`.
- Tests : `tests/parity/test_fm_parity.py`, `tests/unit/test_sim_leveling.py` (parité à 1e-12, options du seed : `rules="seed"`, `mob_source="seed"`, `spell_level="rank"`, rotations `frost` et `fire`).

## Fichiers
```
forever/data/1.60.1.70009/mechanics.json      build.* (scénarios, confiance, graines de stabilité, préréglages), pvp.* (profil du seed),
                                              respec.gold_per_hour, respec.trip_minutes, mana.regen_stacking, damage.bonus_stacking,
                                              champs range des sept hypothèses ; leveling.ignite_rule accepte independent
forever/data/1.60.1.70009/decode_rules.json   talent_cooldowns (sorts de talent dont on lit la recharge)
forever/data/1.60.1.70009/spell_scaling.json  talent_cooldowns (produit par decode)
forever/data/1.60.1.70009/sources.json        description de talent_cooldowns ; manifest.json régénéré
forever/pipeline/decode.py                    lecture de SpellCooldowns pour talent_cooldowns
forever/engine/model.py, forever/gamedata.py  types et chargeurs : Respec (respec.json), PvpProfile, Scenarios, BuildMethod, talent_cooldowns,
                                              regen_stacking, bonus_stacking, plages d'hypothèses
forever/engine/mana.py, damage.py             règles lues dans les données (mode forever), seed inchangé
forever/engine/movement.py                    Flame Throwing, Arcane Geometry (portée)
forever/engine/buffs.py                       Arcane Power : fenêtre de l'aura (arcane_power_window), Missile Barrage (proc, décharge)
forever/engine/variants.py        (nouveau)   with_assumption(gd, name, value) -> GameData ; ASSUMPTIONS (sept noms)
forever/engine/pvp.py             (nouveau)   profil PvP porté du seed (burst, control, survival, sustain, score), fonctions pures
forever/engine/respec.py          (nouveau)   coût, valeur, conseil (formules pures)
forever/engine/blind_spots.py     (nouveau)   estimations bornées des angles morts chiffrables
forever/sim/leveling_mc.py                    arcane_power, horloge de session, Missile Barrage ; mc_stats ; mc() inchangée
forever/sim/leveling_analytic.py              Arcane Power (espérance), Missile Barrage
forever/sim/encounter.py          (nouveau)   scénarios de donjon et de raid : analytique et Monte Carlo
forever/optimize/__init__.py      (nouveau)
forever/optimize/leveling.py      (nouveau)   faisceau (seed et forever), score_plan, level_weight
forever/optimize/endgame.py       (nouveau)   départs multiples + recherche locale (donjon, raid, PvP) ; glouton du seed pour la parité PvP
forever/optimize/decide.py        (nouveau)   décision au Monte Carlo apparié, intervalle, stabilité
forever/optimize/sensitivity.py   (nouveau)   finalistes sous chaque variante ; tient ou bascule
forever/optimize/explain.py       (nouveau)   raison de chaque choix (valeur marginale), alternative la plus proche
forever/build.py                  (nouveau)   service : rapport de build complet, hypothèses, certitude, provenance
forever/cli.py, forever/mcp_server.py         forever build ; forever_build
forever/registry.py                           champ angle_mort
docs/MECHANICS_REGISTRY.yaml                  I5 teste ; I1, B15, B14, C2, A18, A20, B7 ; nouvelles entrées (D10)
docs/ROADMAP.md, ARCHITECTURE.md, DECISIONS.md, OPEN_QUESTIONS.md, SPEC.md (contextes de build)
docs/research/community-builds-mage.md        recherche (cadrage) + section « Comparaison » (bloc J)
tests/fixtures/community/mage_builds.json     builds de la communauté (bloc JSON de la recherche), explication par écart
tests/unit/test_arcane_power_rotation.py, test_variants.py, test_mc_stats.py, test_encounter.py, test_optimize_leveling.py,
test_optimize_endgame.py, test_pvp_profile.py, test_respec.py, test_build_report.py, test_build_cli.py, test_community_builds.py,
test_blind_spots.py (nouveaux) ; tests/parity/test_seed_optimize_parity.py (nouveau : optimiseur_legal, pvp_et_respec, parité)
```

## Interfaces
```
# forever/engine/variants.py                         (Registre : A3, A18, H11, B7, G4, A20)
ASSUMPTIONS = ("a3_miss", "ignite_rule", "mob_hp", "regen_stacking", "low_level_penalty", "bonus_stacking", "ice_lance_coef")
def assumption_range(gd, name) -> tuple[Variant, ...]          # valeurs et sources lues dans mechanics.json (range)
def with_assumption(gd, name, value) -> GameData               # copie ; mob_hp et low_level_penalty passent par les options

# forever/engine/buffs.py                            (Registre : B15, B14)
def arcane_power_window(gd, pts) -> tuple[float, float] | None # (durée s, recharge s) si le talent est pris
def missile_barrage_chance(gd, pts, key) -> float ; def missile_barrage_dump(gd, pts, rank) -> ...

# forever/sim/leveling_mc.py
kill_mc(…, arcane_power_ready: bool = False, **options) ; option arcane_power ("auto", "off")
def mc_stats(gd, level, pts, race, rotation, n, seed, over, **options) -> McStats   # mean (== mc()), sd, se, n, per-kill totals

# forever/sim/encounter.py                           (Registre : H3, H5, I1)
def encounter_analytic(gd, scenario, level, pts, race, over, **options) -> EncounterResult   # dps, dmg, oom_s, rotation
def encounter_mc(gd, scenario, level, pts, race, n, seed, over, **options) -> EncounterStats

# forever/optimize/leveling.py                       (Registre : I5, I6)
def level_weight(gd, level) -> float
def optimize_leveling(gd, race, lfrom, lto, *, beam, depth, shortlist, mc_n, seed, rules, start=None, over=None, **options) -> LevelingPath
def score_plan(gd, plan, race, **options) -> PlanScore

# forever/optimize/endgame.py                        (Registre : I5)
def optimize_context(gd, context, level, race, *, shortlist, mc_n, seed, over=None, **options) -> list[Candidate]
def seed_pvp_greedy(gd, level, race, beam, weights=None) -> Candidate                  # parité avec optimize.pvp

# forever/optimize/decide.py
def paired_gap(a: McStats, b: McStats, confidence) -> Gap      # moyenne, borne basse, borne haute, significatif
def stability(gd, finalists, seeds, evaluate) -> Stability

# forever/engine/pvp.py, forever/engine/respec.py     (Registre : I5)
def pvp_score(gd, pts, level, race, weights=None, over=None, rules="forever") -> PvpProfile
def respec_cost(gd, n_previous) -> float ; def advise_leveling(gd, level, current, target, hours, race, n_previous, gph=None) -> RespecAdvice

# forever/build.py
def build_report(deps, context, level, *, race, current, respecs, over, preset, seed, rules, sensitivity) -> BuildReport
```
`BuildReport` (JSON) : `context`, `level`, `scenario` (provisoire ou non), `talents`, `order` (leveling : niveau, talent, temps par monstre, rotation), `armor`, `rotation`, `ab_stacks`, `ab_dump`, `metric` (nom, valeur Monte Carlo, erreur standard, analytique), `reasons` (par talent : effet, valeur marginale, alternative du point), `alternative` (build, écart apparié, intervalle, significatif), `stability`, `sensitivity` (par hypothèse : tient / bascule, nouvel écart), `respec` (coût, gain, niveau conseillé, verdict, hypothèses), `blind_spots` (entrée, talents, effet estimé ou « non chiffré »), `certainty`, `assumptions`, `provenance`.

Texte (français) : en-tête « Build <contexte> niveau N (scénario provisoire / équipement : fiche de base par niveau) », talents par arbre, ordre, armure et rotation, raisons, alternative et écart ± intervalle, stabilité, tableau de sensibilité, respec, « Angles morts », « Hypothèses », provenance.

## Tests attendus (valeurs du seed par `repr()` ; `pytest.approx(rel=1e-12)` sauf mention)
- **Parité et tests reportés** (`tests/parity/test_seed_optimize_parity.py`, mode seed : `rules="seed"`, `mob_source="seed"`, `spell_level="rank"`) :
    - `test_optimiseur_legal` : `optimize_leveling(gd, "Orc", 10, 14, beam=2, depth=2, mc_n=40, rules="seed", …)` : `check_build` vide à chaque étape ; `hours_equiv` = 3.411975105216378 ; points `{"improvedFrostbolt": 4, "elementalPrecision": 1}` ; étapes et rotations ci-dessus (temps arrondis à 0,01 comme le seed, `==`) ;
    - `test_pvp_et_respec` : `pvp_score(… niveau 20, rules="seed")` = 45.1 et composantes (arrondies par le seed, `==`), `statut` EST ; niveau 60 : 82.0 ; `advise_leveling(20, …)` : 17643, 16537, -0.31, 1, -2.7, « garder » ; `respec_cost(i)` = barème ;
    - `test_seed_pvp_greedy_parity` : `seed_pvp_greedy(gd, 20, "Orc", beam=2)` = points et score 38.6 ci-dessus.
- **Arcane Power** (`test_arcane_power_rotation.py`) : durée et recharge lues (`talents.json`, `spell_scaling.json.talent_cooldowns` = 180000 ms, recoupé avec la fixture `SpellCooldowns.csv`) ; `kill_mc(arcane_power_ready=True)` avec le talent : le journal des lancers montre +30 % de coût sur les lancers de la fenêtre et aucun après ; dégâts × 1,30 dans la fenêtre (multiplicatif avec les cumuls d'Arcane Blast) ; sans le talent, `arcane_power="auto"` ne change rien (`==`) ; horloge de session : sur une suite de combats de cycle connu, l'aura revient une fois par `ceil(recharge / cycle)` combats ; analytique : part des combats = `min(1, cycle / recharge)` ; mode seed : `arcane_power="auto"` sans effet, `"on"` refusé ; parité du seed inchangée ; aucun tirage consommé (même suite de `rng.random()` avec et sans le talent, contrôlé par le journal).
- **Variantes** (`test_variants.py`) : pour chaque hypothèse, la variante ne change que sa cible : A3 → `hit_chance` à écart négatif = valeur à écart 0 ; E4 → `expected_cast("ice_lance")` gagne 0,1429 × puissance des sorts × multiplicateur ; E6 `additive` → `dmg_mult` = somme (mêmes valeurs que `rules="seed"` sur les buffs) ; régénération `max` → `in_combat_regen_fraction` = valeur seed ; Ignite `independent` → tics du seed ; `rules="seed"` ignore les variantes (parité) ; nom inconnu → `ValueError`.
- **Statistiques** (`test_mc_stats.py`) : `mc_stats(...).mean == mc(...)["total"]` (`==`, même graine) ; `se = sd / sqrt(n)` ; `paired_gap` de deux builds identiques = 0, non significatif ; sur deux builds d'écart connu à l'analytique (Improved Frostbolt 5/5 contre 0/5 au niveau 20), intervalle qui exclut 0 à n = 400, sur cinq graines.
- **Scénarios** (`test_encounter.py`) : clés `build.scenarios` lues, `suppose` ; cible unique : analytique à ±3 % du Monte Carlo (n = 400) pour Frostbolt, Fireball, Arcane Blast ; mana épuisée → dégâts nuls au-delà ; paquet de 4 : dégâts de zone = 4 × dégâts par cible (sans plafond, C7 en angle mort) ; tank présent : aucun dégât subi, aucun recul (contrôlé par le journal).
- **Optimiseur** (`test_optimize_leveling.py`, `test_optimize_endgame.py`) : ordre légal à chaque niveau (10 à 20, préréglage rapide) ; points dépensés = `points_available(L)` ; `armor` et `ab_stacks` du résultat appartiennent aux choix légaux (Mage Armor jamais sous son niveau) ; build de contexte légal à 60 (51 points) ; recherche locale : aucun déplacement d'un point n'améliore l'analytique du résultat ; déterminisme (deux appels, même graine, résultat `==`).
- **Rapport** (`test_build_report.py`) : chaque champ du schéma présent ; `reasons` couvre chaque talent du build ; `alternative` distincte du build ; hypothèses citent « équipement : fiche de base par niveau », « scénario provisoire » (donjon, raid), les hypothèses de `damage_assumptions`, l'XP Classic de `level_weight` ; certitude = minimum des certitudes utilisées ; `blind_spots` non vide dès qu'un talent de D5 est pris ou proche ; sensibilité : sept lignes.
- **CLI et MCP** (`test_build_cli.py`) : `forever build leveling --level 14 --preset rapide --json` : provenance présente, ordre de 10 à 14 ; texte : rubriques « Raisons », « Alternative », « Sensibilité », « Respec », « Angles morts », « Hypothèses » ; contexte inconnu, niveau hors plage, talents illégaux (`--current`) → erreur d'argument ; `forever_build` rend le même JSON que le CLI (même graine) ; aucun réseau (`test_network_boundary.py` inchangé).
- **Communauté** (`test_community_builds.py`) : chaque build de la fixture a source, date, contexte, niveau ; légalité recalculée par `check_build` (égale au champ `legal` de la fixture) ; chaque build porte une explication (`concorde`, `mecanique_non_modelisee` avec un identifiant du registre existant, ou `source_douteuse` avec son motif) ; écart calculé par le moteur dans le contexte du build.
- **Angles morts et registre** (`test_blind_spots.py`, `test_registry.py`) : le champ `angle_mort` est validé (talents existants, contextes connus, fonction d'estimation existante) ; les nouvelles entrées changent les trois assertions de `test_registry.py` ; chaque estimation est une borne haute positive calculée par le moteur (pas de chiffre dans le code).
- Registre : I5 `teste` ; B15 (aura et recharge dans les rotations), B14 (Missile Barrage), C2 (Flame Throwing, Arcane Geometry), A18 (variante `independent`), A20 et B7 (clés de données) mis à jour.

## Blocs et étapes (un cycle rouge → vert par bloc, commits « T05: tests (bloc X) » puis « T05: bloc X vert »)
1. **Bloc A — Documentation et données** (sur `main` avant la branche : rien ; sur `t05`) : `ROADMAP.md` (section T05 renommée « Builds du Mage par contexte », critères de fin ci-dessous), `ARCHITECTURE.md` (`forever_build` remplace `forever_optimize_talents`), `DECISIONS.md` (décisions validées) ; `decode_rules.json.talent_cooldowns`, `decode` et `spell_scaling.json.talent_cooldowns` ; clés `build.*`, `pvp.*`, `respec.*`, `mana.regen_stacking`, `damage.bonus_stacking`, `range` ; chargeurs (`respec.json` compris). Pièges : comptes de `test_data_import.py`, `test_manifest.py`, `test_decode_version.py`, `sources.json`, manifeste en LF.
2. **Bloc B — Hypothèses pilotées par les données et variantes** (`variants.py`, `mana.py`, `damage.py`, Ignite `independent`).
3. **Bloc C — Rotations** : Arcane Power (Monte Carlo, analytique, horloge de session), Missile Barrage, Flame Throwing et Arcane Geometry.
4. **Bloc D — Statistiques** : `mc_stats`, `paired_gap`, `stability`.
5. **Bloc E — Scénarios provisoires** : `encounter.py`.
6. **Bloc F — Optimiseur** : portage du faisceau (parité), extensions forever, départs multiples et recherche locale.
7. **Bloc G — PvP** : profil porté (parité), contextes `pvp-bg` et `pvp-world` (poids `pvp.weights.bg` et `pvp.weights.world`, `suppose`), glouton du seed.
8. **Bloc H — Respec** : portage (parité), conseil forever (D9).
9. **Bloc I — Rapport, CLI, MCP** : raisons (valeur marginale : retirer le point, le replacer au mieux, écart à l'analytique, confirmé au Monte Carlo pour les trois choix les plus lourds), alternative, stabilité, sensibilité, angles morts, respec, provenance.
10. **Bloc J — Communauté et angles morts** : fixture tirée de `docs/research/community-builds-mage.md` ; chaque build comparé au nôtre (même contexte, même niveau) ; écarts expliqués (entrée du registre ou source douteuse) ; section « Comparaison » du document ; nouvelles entrées du registre (D10).
11. **Bloc K — Fin** : `forever build` lancé pour les cinq contextes aux niveaux 20, 40, 60 (préréglage complet) ; résultats, stabilité et sensibilité consignés dans `docs/research/builds-T05.md` ; registre, `OPEN_QUESTIONS.md` ; `/verifier` ; CI Ubuntu et Windows ; fusion.

Critères de fin (ROADMAP) : `forever build <contexte> --level N` pour les cinq contextes, légal, avec provenance ; parité du seed (`optimiseur_legal`, `pvp_et_respec`, glouton PvP) ; Arcane Power dans les rotations ; décision au Monte Carlo avec intervalle ; stabilité et sensibilité affichées ; comparaison communautaire documentée ; `uv run tasks.py verify` vert.

## Vérification (ce que la fin de tranche montre)
- **Stabilité** : pour chaque contexte et niveau du bloc K, gagnant identique sur les graines de `build.stability_seeds` ; sinon, écrit tel quel.
- **Sensibilité** : pour chaque recommandation, les sept hypothèses, chacune seule à l'autre bout de sa plage ; finalistes réévalués (analytique puis Monte Carlo apparié) ; « tient » ou « bascule vers X (écart ± intervalle) ». Si une bascule dépend d'une hypothèse, la question ouverte correspondante le mentionne (le test en jeu devient prioritaire).
- **Communauté** : table build par build (source, date, version visée, écart chiffré, explication) ; aucune valeur communautaire dans `forever/data/`.

## Angles morts connus au cadrage (effet à chiffrer par le moteur au bloc J)
| Mécanique | Contextes | Sens attendu |
| --- | --- | --- |
| Hot Streak (Pyroblast absent des rotations) | leveling, donjon, raid (Feu) | sous-évalue le Feu |
| Presence of Mind, Combustion, Cold Snap | tous | sous-évalue le talent pris (burst surtout) |
| Impact, Ice Barrier, Ice Block, Improved Counterspell | leveling (dégâts subis), PvP | sous-évalue survie et contrôle (le profil PvP du seed en couvre une partie) |
| Improved Scorch et Fire Vulnerability dans la rotation (T09) | raid, donjon | sous-évalue le Feu en combat long |
| Évocation, potions (B10) | donjon, raid | surévalue les builds gourmands en mana moins qu'il n'y paraît : fin de mana plus tardive en jeu |
| Résistances, sorts binaires, résistance liée au niveau (A12-A14) | raid (niveau + 3) | peut déplacer Givre contre Feu |
| Plafond de cibles, menace (C7, H9) | paquets | surévalue les zones |
| Buffs de groupe (D1) | donjon, raid | change la valeur relative du critique et de l'Intelligence |
| Baguettes (F6, Wand Specialization) | leveling | sous-évalue la fin de combat à la baguette |
| XP par quête de Forever (T04d) | leveling | change le poids des niveaux, pas le classement à un niveau |

## Hors périmètre
- Pont Node et moteur de raid du seed (`pve_raid.py`, T09) ; `forever_sim_raid` (T09) ; Fire Vulnerability et Scorch dans les rotations (T09) ; Hot Streak, Presence of Mind, Combustion, Cold Snap modélisés (angles morts, sauf choix contraire en D5) ; équipement réel (T07, T10) ; scénarios de donjon réels (DJ1) ; skills du plugin (T06) ; export vers ForeverAssist (FA1, qui lira l'ordre de talents de T05) ; tout accès réseau dans le code (la recherche communautaire est faite par un sous-agent, hors code, sans test réseau).

## Risques
- **Temps de calcul** : leveling 10 → 60 avec trois rotations, trois armures, jusqu'à quatre `ab_stacks` et un Monte Carlo par finaliste : plusieurs minutes. Préréglage `rapide` (tests, MCP par défaut) et `complet` (CLI, bloc K) ; stabilité rejouée sur les finalistes seulement ; mesure du temps consignée.
- **Horloge de session d'Arcane Power** : rend les combats d'un même `mc()` dépendants ; l'erreur standard l'ignore (effet faible, une aura toutes les ~180 s) : noté dans les hypothèses.
- **Fiche de base au niveau 60** : puissance des sorts faible (`gear_sp`) ; favorise les sorts à forte base contre les forts coefficients ; hypothèse affichée, `--sp` pour comparer (534 de la vidéo : estimation de l'auteur).
- **Recherche locale** : optimum local seulement ; départs multiples par arbre pour limiter le risque ; les écarts avec la communauté le révéleront.
- **Scénarios provisoires** : chiffres de durée, de niveau et de nombre de cibles inventés pour comparer (`suppose`) ; affichés à chaque sortie.
- **Profil PvP** : modèle de scénarios du seed (EST), aucune simulation de duel ; pas d'intervalle de confiance (déterministe) ; sensibilité aux poids affichée à la place.
- **Missile Barrage** : proc sur Frostbolt et Fireball aussi ; seule la décharge de la rotation arcane est modélisée (tisser Arcane Missiles dans les rotations de givre ou de feu : angle mort).
- **Communauté** : sources Classic plutôt que Forever pour certains contextes (bêta récente) ; chacune signalée.
