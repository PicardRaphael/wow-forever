# Vidéo BVSgeHp3sWU : dégâts des sorts et puissance des sorts, confrontés au moteur

> Analyse du 2026-09-28 (Claude Code), données du client 1.60.1.70009. Rien n'est appliqué : ce rapport propose des corrections et des tests, à trancher par l'utilisateur.
> **Corrections C1 à C6 appliquées en T04e** (`tasks/T04e-plan.md`, 2026-09-28) ; les sections ci-dessous décrivent l'état d'avant T04e. Improved Cone of Cold : 15 / 25 / 35 % en mode forever (décision de l'utilisateur), courbe du client 12 / 23 / 35 (`docs/OPEN_QUESTIONS.md`).
> Légende : **[Certain]** lu dans les tables du client ou mesuré dans un journal ; **[Probable]** sources concordantes (client et tableur de l'auteur, règle Classic cohérente avec le client) ; **[Supposé]** source unique, inférence ou règle serveur non observée.

| Champ | Valeur |
|---|---|
| Source | « People don´t understand HOW Base Damage changes work - WoW Forever », chaîne Toleduck, <https://www.youtube.com/watch?v=BVSgeHp3sWU> |
| Publication | 2026-09-27, 17:49 |
| Document de travail | `~/Documents/videos/BVSgeHp3sWU/BVSgeHp3sWU.md` (transcription whisper horodatée, 24 images, toutes lues : 001 à 003 et 024 sans chiffre de calcul, 021 montre seulement la saisie « 400-600 ») |
| Outil montré | tableur web « Toleduck Theorycrafting » (non publié), valeurs de niveau 60, bêta |
| Certitude communautaire | **[Supposé]** dans l'ensemble : un seul créateur de contenu, outil non publié, hypothèse de 534 de puissance des sorts **estimée** par l'auteur (200 de pré-raid Vanilla + 334 de compensation), prévisions (pré-raid 500, raid 800) personnelles. **[Probable]** pour les coefficients et les dégâts de base affichés dans le tableur : ils coïncident, à l'arrondi près, avec les tables du client (section 4). La règle orale « incantation / 3,5 » est en revanche incomplète (section 2). |

## Résumé

- **Les tables du client donnent directement les coefficients** : `SpellEffect.EffectBonusCoefficient`, par rang et par effet (dégâts directs, tic de DoT, éclair d'un sort canalisé). Le cache local complet est dans `~/.cache/forever/wago/1.60.1.70009/enUS/`, les rangs du Mage sont aussi dans `tests/fixtures/wago/1.60.1.70009/enUS/SpellEffect.csv`. Le tableur de l'auteur utilise ces valeurs (Frostbolt 0,814, Cone of Cold 0,129, Mind Flay 0,167 par tic), pas sa règle orale.
- **Au niveau 60, notre moteur retrouve les chiffres de la vidéo à ±0,5 point** pour Frostbolt (trois niveaux de puissance des sorts), Frostfire Bolt, Fire Blast, Fireball, Pyroblast (coup direct), Arcane Blast, Arcane Missiles, Arcane Explosion et l'exemple générique (553,14 contre 552,97). L'ordre (base + coefficient × puissance) × talents × critique est le même.
- **Écarts réels chez nous** : quatre coefficients fixes faux (Frost Nova, Cone of Cold, Blast Wave, Blizzard) ; aucun coefficient sur les DoT (Pyroblast, Flamestrike) ; Improved Cone of Cold, Arcane Power et Fire Vulnerability absents du multiplicateur ; bonus de dégâts en pourcentage additionnés dans un seul champ `Buffs["dmg"]` là où l'auteur les multiplie ; Ice Lance à 0,1429 (estimé) quand le client dit 0.
- **À trancher par test** : la pénalité des sorts de bas niveau n'est pas dans la table (Frostbolt r1 à 0,407 = 1,5 / 3,5 × 0,95) ; elle peut être appliquée par le serveur. Les journaux existants ne départagent pas ; un test de quelques Frostbolt de rang 1 suffit (section 5).
- La vidéo ne dit rien du toucher, de la chance de critique, des résistances ni de l'Ignite.

## 1. Formules, règles et exemples chiffrés de la vidéo

| # | Horodatage | Énoncé | Chiffres |
|---|---|---|---|
| V1 | [01:37](https://youtu.be/BVSgeHp3sWU?t=97), image 004 | Puissance des sorts de pré-raid estimée = pré-raid Vanilla + compensation de la baisse de base de Lightning Bolt | 200 + 334 = 534 (estimation de l'auteur, pas un chiffre de jeu) |
| V2 | [12:44](https://youtu.be/BVSgeHp3sWU?t=764) | Coefficient = temps d'incantation / 3,5 ; 3,5 s est le maximum (100 %) | 2,5 s → 71,4 % ; 1,5 s (Mind Blast) → 43 % |
| V3 | [13:22](https://youtu.be/BVSgeHp3sWU?t=802) | Le coefficient se calcule sur l'incantation **sans talent** | 2,5 / 3,5 = 71,4 % |
| V4 | [12:44](https://youtu.be/BVSgeHp3sWU?t=764) | « Tant que le temps d'incantation ne change pas, le coefficient ne change pas » | — |
| V5 | [13:33](https://youtu.be/BVSgeHp3sWU?t=813) | Modificateurs de talents additifs ou multiplicatifs selon le talent | 1 + 0,1 + 0,1 = 1,2 ; 1 × 1,1 × 1,1 = 1,21 |
| V6 | [13:33](https://youtu.be/BVSgeHp3sWU?t=813)-[14:30](https://youtu.be/BVSgeHp3sWU?t=870), image 023 | Dégâts = (puissance × coefficient + base) × modificateurs | 500 × 0,714 = 357 ; + 100 = 457 ; × 1,21 = 552,97 |
| V7 | [16:26](https://youtu.be/BVSgeHp3sWU?t=986)-[16:46](https://youtu.be/BVSgeHp3sWU?t=1006) | Critique = 150 % ; un talent +100 % double le bonus (50 → 100) : 200 % ; tous les lanceurs l'ont sauf Mage feu et prêtre Smite | 1,5 → 2,0 |
| V8 | [09:22](https://youtu.be/BVSgeHp3sWU?t=562)-[10:10](https://youtu.be/BVSgeHp3sWU?t=610), images 012, 017 | Ice Lance ×4 sur cible gelée (+300 %) ; coefficient « habituel » 14,29 % non vérifié, exclu du tableur | 14,29 × 4 = 57,16 % ; 534 × 0,5716 = 305 ; 627 + 305 = 932 ; × 2 = 1 864 |
| V9 | [09:22](https://youtu.be/BVSgeHp3sWU?t=562), image 018 | Frostbolt r11 à 534, Piercing Ice 3/3 | base 457-493 (moy. 475), +434,7, +6 % → 964,3 ; critique 1 928,5 |
| V10 | image 023 | Frostbolt r11 à 500 | +407, → 934,9 |
| V11 | image 019 | Frostbolt r11 à 1 000 | +814, +77,3 → 1 366,3 |
| V11b | images 022, 020 | Frostbolt r11 à 800 et à 2 000 | +651,2 → 1 193,8 ; +1 628 → 2 229,2 (critique 4 458,4) |
| V12 | image 013 | Frostfire Bolt r3 à 534 | base 270-314, +434,7, +6 % → 770,3 ; critique 1 540,6 |
| V13 | image 013 | Cone of Cold r5 à 534, Improved Cone of Cold 3/3 et Piercing Ice 3/3 | base 328-358 (moy. 343), +68,9, +43,1 % → 589,4 ; critique 1 178,8 |
| V14 | image 013 | Fire Blast r7 à 534 | moy. 453, +229,1 → 682,1 |
| V15 | image 014 | Pyroblast r8 et Fireball r12 à 534, sans talent de feu | Pyroblast base 520-646, +534 → 1 117 (critique 1 675,5) ; Fireball 425-541, +534 → 1 017 (critique 1 525,5) |
| V16 | images 015, 017 | Arcane Blast r5 à 534, Arcane Instability 3/3 et Arcane Power | base 364-424, +381,3, +33,9 % → 1 038,1 ; critique 2 076,2 |
| V17 | image 015 | Arcane Missiles r8 à 534, mêmes talents | 209 par missile, +152,7, +33,9 % → 484,3 par missile, 2 421,7 au total ; critique 968,7 |
| V18 | [11:39](https://youtu.be/BVSgeHp3sWU?t=699), images 016, 017 | Arcane Missiles et Arcane Explosion avec les cumuls d'Arcane Blast | +87,5 % : Arcane Missiles 678,1 (critique 1 356,2) ; Arcane Explosion r6 base 238-258, +76,4 → 608 |
| V19 | [11:39](https://youtu.be/BVSgeHp3sWU?t=699) | Arcane Explosion sans cumul | 434, critique « 900 » |
| V20 | [10:48](https://youtu.be/BVSgeHp3sWU?t=648) | Build feu JcE (Fire Power 4/5, Improved Scorch, Ignite) | Pyroblast 1 400 / 2 080, Fireball 1 200 / 1 900, Frostfire Bolt 956 / 1 900, Scorch 500 / 760, Flamestrike 600 / 950, Blast Wave 700 / 1 000 (ordres de grandeur, détail non affiché) |
| V21 | [03:30](https://youtu.be/BVSgeHp3sWU?t=210) et suivantes, images 007, 013 | Sorts sur la durée : un tic affiché par sort, qui critique ; « Tick count assumes Classic timing » | Flame Shock 112 / 224, Corruption +106,8 par tic, Mind Flay 350,1 par tic |
| V22 | tout le tableur | Dégâts de base de niveau 60 avec min et max entiers ; affichage au dixième, sans arrondi des dégâts | Ice Lance 136-160, Arcane Explosion 238-258 |

Absents de la vidéo : toucher et raté, chance de critique, résistances, pénalité des sorts de bas niveau, Ignite, périodicité réelle des tics.

## 2. Comparaison avec le moteur

| # | Règle de la vidéo | Chez nous | Classement |
|---|---|---|---|
| V2, V3 | incantation / 3,5, bornée à 3,5 s, incantation sans talent | `forever/engine/spells.py` `coefficient` (G4) : `min(3,5, max(1,5, rank.cast_time_s)) / 3,5`, incantation du rang (sans talent) | **Concordant** pour les sorts directs à cible unique. La vidéo omet la borne basse (instantané = 1,5 s, Fire Blast 0,429) que nous avons. |
| V2 (tableur) | Frostbolt 0,814 (ralentissement) | facteur × 0,95 si `slow` (G4) | **Concordant** (0,8143 calculé, 0,814 dans le client). La règle orale l'oublie ; le tableur l'applique. |
| V4 | le coefficient ne dépend que de l'incantation | coefficients fixes pour les sorts de zone et instantanés (`mechanics.json` `coefficient.fixed`) | **Différent, la vidéo a tort** : le client fixe chaque coefficient (Mind Flay 0,5 au total pour 3 s de canalisation, Earth Shock 0,386, Cone of Cold 0,129) ; il peut changer sans toucher à l'incantation. |
| V5 | additif ou multiplicatif selon le talent | `forever/engine/damage.py` `dmg_mult` (A20) : (1 + Arcane Instability) × (1 + Piercing Ice ou Fire Power) × (1 + `buffs["dmg"]`) | **Concordant** entre familles (le tableur multiplie partout : Arcane Blast 1,03 × 1,30 = 1,339 ; Shadow Word: Death 1,1³ × 1,05 = 1,398). **Différent** à l'intérieur de `buffs["dmg"]` : nos bonus s'y additionnent (V18). |
| V5 (tableur) | Improved Cone of Cold +35 %, Arcane Power +30 %, cumuls d'Arcane Blast, Fire Vulnerability | Arcane Blast : `forever/engine/buffs.py` `arcane_blast_bonus` (B15). Improved Cone of Cold, Arcane Power, Fire Vulnerability : rien dans `dmg_mult` | **Absent** : Improved Cone of Cold (talent présent dans `talents.json`, 35 %), Arcane Power (15 s, +30 %), Fire Vulnerability d'Improved Scorch. |
| V6 | (base + puissance × coefficient) × modificateurs | `forever/engine/cast.py` `expected_cast` et `damage.py` `roll_base_damage` : `(moyenne + coef × SP) × dm` | **Concordant** (même ordre ; le multiplicateur de cible gelée d'Ice Lance s'applique aussi sur la part de puissance des sorts). |
| V7 | critique 1,5, +100 % du bonus avec le talent ; pas de talent pour le feu | `forever/engine/crit.py` `crit_mult` (A21) : 1 + 0,5 × (1 + Ice Shards ou Arcane Mind) ; feu 1,5 | **Concordant** (givre et arcane 2,0 à 5/5, feu 1,5). |
| V8 | Ice Lance ×4 sur cible gelée | `spells.json` `frozen_mult` 4 ; client : effet 1 d'Ice Lance, +300 % | **Concordant** [Certain]. |
| V8 | coefficient d'Ice Lance 14,29 % « habituel », non vérifié | `coefficient.fixed.ice_lance` 0,1429 (EST) | **Différent** : le client porte 0 sur les six rangs appris (section 4). |
| V21 | un DoT prend la puissance des sorts à chaque tic (Corruption +106,8 = 0,2 × 534) | `expected_cast` : `dot = r.dot_total × dm × …` ; `damage.py` `dot_tick_damage` : aucune puissance des sorts | **Absent** : sans effet pour Fireball et Frostfire Bolt (client 0), faux pour Pyroblast et Flamestrike. |
| V21 | les DoT critiquent | `leveling.json` `combat_rules.dot_can_crit` (A17) | **Concordant**. |
| V21 | « Classic timing » des tics | `damage.py` `dot_tick_times` : un tic toutes les `leveling.dot_tick_s` = 2 s (EST du seed) pour tous les DoT | **Différent** (hors vidéo) : période du client 3 s pour Pyroblast (4 tics) et Frostfire Bolt (3 tics). L'espérance ne change pas ; le Monte Carlo place mal les tics et compte trop de critiques indépendants. |
| V22 | min et max entiers, tronqués (Ice Lance 136-160) | `spells.py` `_half_up` (G7) : arrondi au demi supérieur (136-161) | **Différent**, effet ≤ 0,5 point sur la moyenne ; notre arrondi reproduit les rangs décodés (test G7). |
| — | (hors vidéo) pénalité des sorts de niveau < 20 | `coefficient` × (1 − 0,0375 × (20 − niveau du sort)) | **Non couvert par la vidéo** (tout est au niveau 60) ; question ouverte, section 5. |

## 3. Exemples de la vidéo refaits avec le moteur

Calcul : `best_rank`, `rank_damage(…, spell_level="character")` au niveau 60, `coefficient`, `dmg_mult`, `crit_mult` de `forever.engine`, personnage de niveau 60 avec la puissance des sorts indiquée ; talents cochés à l'écran. Arcane Power n'existant pas chez nous, son +30 % est passé en `buffs={"dmg": 0.30}`. Colonne « normal » : coup non critique moyen.

| Exemple | Vidéo | Moteur | Écart | Cause |
|---|---|---|---|---|
| V6 générique, 500, base 100, 2,5 s, × 1,21 | 552,97 | 553,14 | +0,17 | l'auteur arrondit le coefficient à 0,714 ; le client stocke 0,714 aussi |
| V6 à 534 | — | 582,53 | — | — |
| V5 variante additive × 1,2 | — | 548,57 (calcul manuel) | — | le moteur n'additionne pas deux talents de familles différentes |
| V9 Frostbolt r11, 534 | 964,3 / 1 928,5 | 964,4 / 1 928,8 | +0,1 | 0,8143 calculé contre 0,814 du client |
| V10 Frostbolt r11, 500 | 934,9 | 935,1 | +0,2 | idem |
| V11 Frostbolt r11, 1 000 | 1 366,3 | 1 366,6 | +0,3 | idem |
| V11b Frostbolt r11, 800 et 2 000 | 1 193,8 ; 2 229,2 | 1 194,0 ; 2 229,8 | +0,2 ; +0,6 | idem (l'écart croît avec la puissance des sorts : 0,0003 × SP × 1,06) |
| V12 Frostfire Bolt r3, 534 | 770,3 / 1 540,6 | 770,4 / 1 540,9 | +0,1 | idem |
| V8 Ice Lance r6 gelée, sans puissance (tableur) | 627,5 / 1 255 | 629,6 / 1 259,3 | +2,1 | moyenne de base 148 (troncature) contre 148,5 (demi supérieur) ; valeur exacte 148,6 |
| V8 Ice Lance r6 gelée, 534, calcul oral | 932 / 1 864 | 953,2 / 1 906,4 | +21 | l'auteur multiplie la part de puissance par 4 mais oublie Piercing Ice (× 1,06) ; avec le coefficient du client (0) : 629,6 |
| V13 Cone of Cold r5, 534 | 589,4 / 1 178,8 | 440,5 / 881,0 | −148,9 | Improved Cone of Cold absent (× 1,35) et coefficient 0,1358 au lieu de 0,129 ; corrigé : (343 + 0,129 × 534) × 1,06 × 1,35 = 589,4 |
| V14 Fire Blast r7, 534 | 682,1 | 681,9 | −0,2 | 0,4286 contre 0,429 |
| V15 Pyroblast r8, 534 (coup direct) | 1 117 / 1 675,5 | 1 117 / 1 675,5 | 0 | — |
| V15 Pyroblast r8, DoT | non affiché | 212 | — | client : 4 × (53 + 0,15 × 534) = 532,4 |
| V15 Fireball r12, 534 | 1 017 / 1 525,5 | 1 017 / 1 525,5 | 0 | DoT 60 sans puissance des sorts des deux côtés |
| V16 Arcane Blast r5, 534 | 1 038,1 / 2 076,2 | 1 038,3 / 2 076,6 | +0,2 | 0,7143 contre 0,714 |
| V17 Arcane Missiles r8, 534 | 484,3 par missile, 2 421,7 | 484,1, 2 420,7 | −1,0 au total | 5 × 0,286 = 1,43 contre 5 / 3,5 = 1,4286 |
| V18 Arcane Missiles r8, 4 cumuls d'Arcane Blast + Arcane Power | 678,1 / 1 356,2 | 633,1 | −45 | nous additionnons +30 % et +40 % (1,03 × 1,70) ; l'auteur multiplie (1,03 × 1,30 × 1,40 = 1,8746 → 678,1) |
| V18 Arcane Explosion r6, mêmes bonus | 608 | 568,8 | −39 | idem ; en multipliant : 609,0 |
| V19 Arcane Explosion r6, Arcane Power seul | 434 / « 900 » | 435,0 / 870,0 | +1 | « 900 » est un arrondi oral |
| V20 build feu | ordres de grandeur | non recalculable | — | Fire Vulnerability absente chez nous ; Pyroblast 1 117 × 1,08 × 1,15 = 1 387 ≈ 1 400 suggère Fire Power 4/5 et cinq cumuls, multipliés [Supposé] |

Coefficients des sorts de zone à 534, pour mémoire (pas d'exemple exact dans la vidéo) : Blast Wave r5 569,4 chez nous contre 561,9 avec 0,129 ; Frost Nova r4 104,4 contre 96,4 avec 0,029 ; Blizzard r6 1 426,6 contre 1 428,3 avec 8 × 0,042 ; DoT de Flamestrike r6 332 contre 400,4 avec 4 × 0,032.

## 4. Les coefficients dans les tables du client

**Oui, le client les contient.** Colonne `EffectBonusCoefficient` de `SpellEffect` (et `BonusCoefficientFromAP` pour la puissance d'attaque, à 0 sur tous ces sorts ; `PvpMultiplier` à 1 partout). Valeur par effet : un coup direct, **un tic** d'aura périodique (aura 3, 53), un éclair déclenché d'un sort canalisé (Arcane Missiles, Blizzard, Flamestrike par aura 226). Lecture : `SpellName` → `SpellEffect` (plus `EffectTriggerSpell` pour les sorts canalisés), `SpellMisc` → `SpellCastTimes` / `SpellDuration`, `SpellLevels`, rangs appris filtrés par `SkillLineAbility` (`AcquireMethod`). Les scripts de cette analyse étaient temporaires (non conservés) ; la lecture est à refaire dans `forever/pipeline/` si C1 est retenue.

Interprétation « par tic » **[Probable]** : Immolate (Démoniste) donne 0,2 direct + 5 × 0,13 = 0,65 pour le DoT, la répartition Classic connue ; le tableur affiche Corruption à +0,2 × 534 par tic ; le DoT de Fireball à 0 est confirmé par le journal (4 tics de 2 à 13-14 de puissance des sorts, Fireball r3, `WoWCombatLog-092726_150346.anon.txt.gz`) **[Certain]**.

### Mage, rangs appris (`AcquireMethod` 0), comparés à G4

| Sort | Client | G4 actuel | Écart |
|---|---|---|---|
| Frostbolt | r1-r4 : 0,407 ; 0,489 ; 0,597 ; 0,706 ; r5-r11 : 0,814 | 0,1629 ; 0,2687 ; 0,4628 ; 0,7057 ; 0,8143 | r1-r3 : notre pénalité de bas niveau (absente de la table) ; r4+ : arrondi. Le client inclut le × 0,95 du ralentissement (1,5 / 3,5 × 0,95 = 0,407). |
| Fireball | r1-r4 : 0,429 ; 0,571 ; 0,714 ; 0,857 ; r5+ : 1 ; DoT 0 | 0,1232 ; 0,2714 ; 0,5 ; 0,7929 ; 1 ; DoT 0 | pénalité seulement ; DoT concordant |
| Fire Blast | 0,429 à tous les rangs | 0,2036 ; 0,3321 ; puis 0,4286 | pénalité (nos r1-r2 valent exactement les doublons `AcquireMethod` 3 400618 et 400619 du client, qui intègrent la pénalité) |
| Scorch | 0,429 | 0,4286 | concordant |
| Pyroblast | direct 1 ; DoT 0,15 par tic, 4 tics de 3 s | direct 1 ; DoT 0 | **DoT absent** |
| Arcane Missiles | 0,286 par missile (3, 4 puis 5 missiles) | 0,4714 ; 0,9714 ; puis 1,4286 au total | pénalité r1-r2 ; sinon concordant (5 × 0,286) |
| Arcane Explosion | 0,143 | 0,1108 (r1) ; 0,143 | pénalité r1 |
| Arcane Blast | 0,714 | 0,7143 | concordant |
| Frostfire Bolt | direct 0,814 ; DoT 0 (3 tics de 3 s) | 0,8143 ; DoT 0 | concordant |
| Ice Lance | **0** (six rangs) | 0,1429 (EST) | **différent** |
| Frost Nova | 0,029 | 0,0269 (r1) ; 0,043 | **différent** |
| Cone of Cold | 0,129 | 0,1358 (0,143 × 0,95) | **différent** |
| Blast Wave | 0,129 | 0,143 | **différent** |
| Blizzard | 0,042 par tic × 8 = 0,336 (sort de dégâts déclenché 1279949) ; l'effet factice du sort canalisé porte 0,03 | 0,333 | **différent** (+1 %) ; Hurricane et Rain of Fire ont le même effet factice à 0,03, que le tableur applique à Hurricane (+16,0 par tic à 534, image 011) |
| Flamestrike | direct 0,157 ; DoT 0,032 par tic × 4 | 0,1334 (r1) ; 0,157 ; DoT 0 | **DoT absent** |

Les lignes à `AcquireMethod` 3 et les sorts de PNJ homonymes (Frostbolt 9672, Fireball 9053…) sont à écarter : ce sont les leurres déjà décrits dans `tests/fixtures/wago/1.60.1.70009/README.md`.

## 5. Écarts : qui a probablement raison, comment trancher

| # | Écart | Qui a raison | Comment trancher |
|---|---|---|---|
| E1 | Coefficients fixes de Frost Nova, Cone of Cold, Blast Wave, Blizzard | **Le client** [Probable → Certain à la lecture] : le client et le tableur concordent contre nous ; nos valeurs viennent de `fm.py` (valeurs Classic de mémoire) | Données du client : lire la colonne (correction C1). Contrôle dans un journal au niveau 60 si besoin. Pour Blizzard, le journal dit aussi lequel des deux coefficients s'applique (0,042 du sort déclenché, probable, ou 0,03 de l'effet factice) : tic de Blizzard (sans variance) à deux niveaux de puissance des sorts. |
| E2 | Pénalité des sorts de bas niveau (absente de la table, appliquée chez nous) | **Inconnu** [Supposé] : la règle Classic la fait appliquer par le serveur, hors table ; les doublons 400618-400619 montrent la même formule (0,0375 par niveau) dans les données de Forever | Journal : les fixtures ne départagent pas (98 Frostbolt r3, 127 Arcane Explosion r1, 24 Fire Blast r2, 22 Frost Nova r1, tous compatibles avec les deux hypothèses, 13-14 de puissance des sorts). **Test en jeu** : une dizaine de Frostbolt **de rang 1** sur un monstre gris, sans talent de dégâts : au niveau ≥ 8 du personnage, base 20-22 ; + 0,407 × SP sans pénalité, + 0,163 × SP avec. À 14 de puissance des sorts : 25,6-27,8 contre 22,2-24,4, sans recouvrement. La puissance des sorts se lit dans le bloc avancé des lignes `SPELL_CAST_SUCCESS` (champ 18, vérifié sur la fixture). |
| E3 | Pas de puissance des sorts sur les DoT | **Le client** [Probable] (interprétation par tic, voir section 4) | Journal : un tic de DoT n'a pas de variance, donc tout écart est lisible. Pyroblast r1 (niveau 20, sans pénalité) : tic = 11 + 0,15 × SP (× talents) ; à 20 de puissance des sorts, 14 au lieu de 11. |
| E4 | Ice Lance : client 0, nous 0,1429, l'auteur « non vérifié » | **Le client** [Probable] : le 0 est explicite alors que les autres sorts issus des runes portent un coefficient (Arcane Blast 0,714, Frostfire Bolt 0,814, Living Bomb 0,4) | Journal : Ice Lance sur cible non gelée, deux séries avec au moins 30 de puissance des sorts d'écart ; attendu + 4,3 par coup avec 0,1429, rien avec 0. Critère simple : un seul coup au-dessus du max de base (× talents) réfute 0. |
| E5 | Improved Cone of Cold, Arcane Power, Fire Vulnerability absents | **L'auteur** [Certain pour l'existence et les valeurs : `talents.json`, client] | Implémenter (C5). La position dans la chaîne (facteur séparé) est [Probable] : l'exemple V13 ne tombe juste qu'en multipliant 1,06 × 1,35. |
| E6 | Cumul de deux bonus en pourcentage de même nature (Arcane Power et cumuls d'Arcane Blast : tous deux aura 108, `SpellMod` 0 dans le client) | **Inconnu** [Supposé] : l'auteur multiplie ; le moteur additionne par construction (un seul champ `dmg`) | Journal : Arcane Missiles sous Arcane Power avec 4 cumuls d'Arcane Blast, contre Arcane Power seul ; rapport attendu 1,40 (multiplicatif) contre 1,70 / 1,30 = 1,31 (additif). Talent Arcane Power requis. |
| E7 | Arrondi des min et max (demi supérieur contre troncature) | **Nous** [Probable] : notre arrondi reproduit les rangs décodés (test G7) ; effet ≤ 0,5 sur la moyenne | Infobulle en jeu d'Ice Lance r6 au niveau 60 (160 ou 161) ; max observé dans un journal. |
| E8 | Précision du coefficient (0,8143 calculé contre 0,814 stocké) | **Le client** [Certain] ; effet 0,03 % | Disparaît avec C1. |
| E9 | Période des tics fixe à 2 s (hors vidéo) | **Le client** [Certain] : `EffectAuraPeriod` 3 000 ms pour Pyroblast et Frostfire Bolt | Disparaît avec C4. |

## 6. Corrections proposées (non appliquées) et tests à ajouter

### Corrections

- **C1, données** : le décodeur écrit `bonus_coefficient` pour chaque composant de `spell_scaling.json` (il lit déjà `SpellEffect` pour G7), sorts déclenchés compris (Arcane Missiles, Blizzard, Flamestrike), avec `tick_period_ms` pour les DoT. Certitude `certain` (client).
- **C2, moteur** (`spells.py` `coefficient`) : coefficient direct = somme des composants directs (× nombre d'éclairs pour un sort canalisé), lue dans les données. Retirer `coefficient.cast_divisor`, `cast_bounds_s`, `slow_factor`, `channel_cap_s` et `coefficient.fixed` de `mechanics.json`, ou les garder comme repli marqué pour un sort sans donnée du client. Garder la pénalité de bas niveau comme règle séparée `suppose` jusqu'au test d'E2.
- **C3, moteur** (`cast.py` `expected_cast`, `damage.py` `dot_tick_damage`) : DoT = (total du rang + tics × coefficient par tic × SP) × multiplicateur × critique.
- **C4, moteur** (`damage.py` `dot_tick_times`) : période des tics par sort depuis les données, au lieu de `leveling.dot_tick_s`.
- **C5, moteur** (`damage.py` `dmg_mult`, `buffs.py`) : Improved Cone of Cold (Cone of Cold seul), Arcane Power (aura temporaire), Fire Vulnerability (cumuls d'Improved Scorch), chacun en facteur séparé ; `Buffs` distingue les sources au lieu d'un seul `dmg` si E6 conclut au multiplicatif.
- **C6, données** : Ice Lance au coefficient du client (0), `probable`, en attendant E4.

Ce qui cassera, **à décider par l'utilisateur** (parité volontairement rompue avec le seed) : `tests/unit/test_engine_values.py::test_coefficient_values` (Frostbolt r2 et r11), `tests/parity/test_fm_parity.py::test_rank_and_coefficient_parity` et `::test_expected_cast_parity`, `tests/parity/test_sim_leveling_parity.py` (les simulateurs utilisent les coefficients), `tests/unit/test_gamedata.py::test_coefficient_reads_data`. Aucun `tests/golden/` n'existe aujourd'hui.

### Registre (`docs/MECHANICS_REGISTRY.yaml`) à modifier avec ces corrections

- **G4** : source « Tables du client SpellEffect (EffectBonusCoefficient) », certitude `certain` pour les coefficients, formule réécrite ; la pénalité de bas niveau reste `suppose`.
- **A17** : puissance des sorts par tic et période des tics du client.
- **A20** : Improved Cone of Cold, Arcane Power, Fire Vulnerability ; règle de cumul.
- **B15** : cumul des bonus d'Arcane Blast avec Arcane Power.

### Questions à ajouter à `docs/OPEN_QUESTIONS.md`

1. G4 : la pénalité des sorts de niveau < 20 est-elle appliquée par le serveur de Forever ? (test E2 ; que sont les Fire Blast 400616-400623 à `AcquireMethod` 3, qui l'intègrent ?)
2. G4 : Ice Lance a-t-elle un coefficient nul dans Forever ? (test E4)
3. A20 / B15 : deux bonus de dégâts en pourcentage de même nature (aura 108) s'additionnent-ils ou se multiplient-ils ? (test E6)
4. G7 : arrondi des bornes de dégâts de base (demi supérieur ou troncature) ? (E7)

### Tests à ajouter (valeurs prises dans `tests/fixtures/`)

- `test_coefficient_matches_client_table` : chaque rang des 15 sorts du Mage contre `EffectBonusCoefficient` de la fixture wago (Frostbolt r1 0,407 hors pénalité, Frost Nova 0,029, Cone of Cold 0,129, Blast Wave 0,129, Ice Lance 0, Blizzard 8 × 0,042).
- `test_pyroblast_dot_scales_with_spell_power` : Pyroblast r8 au niveau 60, 534 de puissance des sorts : DoT = 4 × (53 + 0,15 × 534).
- `test_flamestrike_dot_scales_with_spell_power` : 4 tics de (83 + 0,032 × SP).
- `test_improved_cone_of_cold` : Cone of Cold r5, Piercing Ice 3/3 et Improved Cone of Cold 3/3, 534 : (343 + 0,129 × 534) × 1,06 × 1,35 (concordance avec V13, source citée).
- `test_dot_ticks_follow_client_period` : Pyroblast 4 tics de 3 s, Frostfire Bolt 3 tics de 3 s, Fireball 2 s.
- `test_fireball_dot_has_no_spell_power_in_log` : fixture `WoWCombatLog-092726_150346.anon.txt.gz`, les 4 tics de Fireball r3 valent la base du rang malgré 13-14 de puissance des sorts (possible dès maintenant).
- Après décision : `test_damage_bonuses_stack` (E6), `test_low_level_penalty_from_log` (E2, sur un journal du test Frostbolt r1 anonymisé en fixture).

## 7. Autres classes (pour PV1 et T12)

Aucun calcul de dégâts hors Mage n'est prévu avant T12 ; ces lignes servent au décodage étendu de PV1 et aux moteurs de T12. Rang le plus haut appris (`AcquireMethod` 0), coefficient par effet.

| Classe | Sort | Client | Règle orale (incantation / 3,5) | Tableur de l'auteur | Remarque |
|---|---|---|---|---|---|
| Chaman | Lightning Bolt (15208) | 0,714, incantation 2,5 s | 0,714 | +381,3 | concordant ; lignes `AcquireMethod` 3 (408477…) à 0,357 et base moitié : Overload (« 300 » à [02:40](https://youtu.be/BVSgeHp3sWU?t=160)) |
| Chaman | Lava Burst (1238300) | 0,714 ; effet 1 : +20 % | 0,714 | 691 ; 829,8 avec Flame Shock = 601,3 × 1,2 × 1,15 | le +20 % avec Flame Shock se multiplie |
| Chaman | Chain Lightning (10605) | 0,571 ; **r3 (2860) 0,517** | 0,571 | +304,9 | anomalie du r3 à vérifier ; Overload 0,2855 |
| Chaman | Earth Shock (10414), Frost Shock (10473) | 0,386 | 0,429 | +206,1 | la règle orale est fausse pour les horions |
| Chaman | Flame Shock (29228) | direct 0,214 ; DoT 0,1 par tic × 4 | 0,429 | tic 112 | sort hybride |
| Prêtre | Mind Blast (10947), Shadow Word: Death (1309636) | 0,429 | 0,429 | +229,1 | concordant (exemple de la vidéo) |
| Prêtre | Mind Flay (18807) | 0,167 par tic × 3 = 0,5 | 0,857 | +89,2 par tic | la règle orale est fausse pour les canalisations |
| Prêtre | Shadow Word: Pain (10894), Devouring Plague (19280) | 0,2 × 6 ; 0,1 × 8 | — | — | DoT par tic |
| Prêtre | Smite (10934), Holy Fire (15261) | 0,714 ; 0,75 + 0,05 × 5 | 0,714 ; 1 | — | Holy Fire hybride ; Penance 0,285 par éclair ; Holy Nova 0,107 |
| Druide | Starfire (25298), Wrath (9912) | 1 ; 0,571 (2 s) | 1 ; 0,571 | +534 ; +304,9 | concordant ; « Wrath à 75 % de Vanilla » invérifiable sans données Vanilla |
| Druide | Moonfire (9835), Insect Swarm (24977) | 0,15 + 0,13 × 4 ; 0,158 × 6 | — | — | hybride et DoT |
| Démoniste | Shadow Bolt (25307), Soul Fire (17924), Incinerate (1293813) | 0,857 ; 1 (6 s) ; 0,714 | idem | +457,6 ; +534 ; +381,3 | concordant |
| Démoniste | Conflagrate (18932), Searing Pain (17923), Shadowburn (18871) | 0,429 | 0,429 (instantané borné à 1,5 s) | +229,1 | concordant ; « Conflagrate getting the short end of the stick » est une appréciation, pas une règle |
| Démoniste | Immolate (25309), Corruption (25311) | 0,2 + 0,13 × 5 ; 0,2 × 6 = 1,2 | — | +106,8 par tic de Corruption | DoT par tic |
| Démoniste | Drain Life (11700), Siphon Life (18881), Bane of Agony (11713), Bane of Doom (603), Hellfire (11684) | 0,1 × 5 ; 0,05 × 10 ; 0,133 par tic de 2 s ; 4 (un tic à 60 s) ; 0,022 par tic | — | — | Bane of Agony monte en puissance (tics inégaux, [06:45](https://youtu.be/BVSgeHp3sWU?t=405)) : répartition à lire dans le client |
| Démoniste | réglages du tableur (images 008 à 011) | — | — | puissance des sorts effective 594 avec un démon actif (image 009 : +60, Demonic Knowledge ou démon, à vérifier) ; Immolate direct +65 % en Destruction (image 011) ; Corruption +33,4 % puis +43,9 % avec Wrack (images 008, 009) | options JcE / JcJ de l'auteur, pas des règles |
| Druide | Hurricane (17402) | effet factice 0,03 ; dégâts par aura 226 (tic de 1 s) | — | +16,0 par tic | voir Blizzard (section 4) : coefficient du sort déclenché à lire |

Leçon pour T12 : lire le coefficient de chaque effet dans le client. La règle « incantation / 3,5 » ne vaut que pour les sorts directs à cible unique ; elle se trompe pour les horions, les canalisations, les sorts hybrides, les DoT et les sorts de zone. Le tableur de l'auteur multiplie tous ses modificateurs (Shadowform, Darkness, Shadow Weaving, Twin Disciplines : 1,1 × 1,1 × 1,1 × 1,05 = 1,398) ; l'ordre de cumul par classe reste à confirmer par les journaux.

## Sources

- Vidéo : Toleduck, « People don´t understand HOW Base Damage changes work - WoW Forever », 2026-09-27, <https://www.youtube.com/watch?v=BVSgeHp3sWU> ; transcription et images : `~/Documents/videos/BVSgeHp3sWU/`.
- Client 1.60.1.70009 : tables `SpellEffect`, `SpellName`, `SpellMisc`, `SpellCastTimes`, `SpellDuration`, `SpellLevels`, `SkillLineAbility`, `Spell` (infobulles) de wago.tools, cache local `~/.cache/forever/wago/1.60.1.70009/enUS/` (collecte du 2026-09-27 par `forever fetch`) et extraits `tests/fixtures/wago/1.60.1.70009/`.
- Journaux : `tests/fixtures/combatlog/WoWCombatLog-092726_150346.anon.txt.gz` et `WoWCombatLog-092726_145346.anon.txt` (Mage de bas niveau, 13-14 de puissance des sorts).
- Moteur : `forever/engine/spells.py`, `damage.py`, `cast.py`, `crit.py`, `buffs.py` ; données `forever/data/1.60.1.70009/mechanics.json`, `spells.json`, `spell_scaling.json`, `talents.json`, `leveling.json`.
