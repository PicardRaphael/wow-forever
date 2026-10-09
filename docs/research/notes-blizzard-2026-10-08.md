# Notes de développement de Blizzard du 08/10/2026 : lecture et recoupement avec le client 1.60.1.70291

Relevé le 2026-10-09, à la demande de l'utilisateur. Pour chaque changement de la note : (a) visible dans les tables
du client 1.60.1.70291 (vérifié), (b) passé par un correctif du serveur (`Logs/Hotfix.log`, `DBCache.bin` du build
70291), ou (c) règle du serveur absente des données lues. Le texte du forum est sous licence CC BY-NC-SA 3.0 : il est
paraphrasé ici, jamais recopié.

## Source
- Sujet officiel « WoW Forever Beta Development Notes – Updated October 8 » (Community Manager), forum de Blizzard :
  <https://us.forums.blizzard.com/en/wow/t/2360696>.
- **Message n° 5** : créé le 2026-10-08, **révision 1** du 2026-10-08 :
  <https://us.forums.blizzard.com/en/wow/t/2360696/5>. C'est la provenance retenue partout dans le dépôt
  (« t/2360696/5, révision 1 »).
- Lecture : `uv run forever notes --post 2360696/5`, lancée à la main le 2026-10-09 avec l'accord réseau de
  l'utilisateur (décision 148).

## Version concernée : 1.60.1.70291 (probable)
La note annonce un nouveau build mis en ligne « aujourd'hui » (08/10). 1.60.1.70291 est le build suivant 70245 ; le
client de l'utilisateur l'a installé le 2026-10-09 à 06:04 UTC (`.build.info`). Les changements de sorts annoncés
(rangs de Frostbolt, Fireball, Arcane Missiles, Smite, Lightning Bolt, Shadow Bolt, Wrath, Penance…) sont tous
présents dans les tables de 70291 et absents de celles de 70245.

## Méthode
- (a) : comparaison des tables de wago.tools en cache, 1.60.1.70245 contre 1.60.1.70291 (`Spell*`, `Trait*`), ligne
  par ligne, reliée aux noms des sorts (789 sorts ou tables touchés).
- (b) : `DBCache.bin` du build 70291 (31 116 entrées, poussées 112444 à 112524) et `Logs/Hotfix.log` du lancement du
  2026-10-09 à 12:13 : les lignes de sorts corrigées par le serveur depuis le build portent sur Rend Flesh, Highland
  Venom, Cold Blood, Sacred Cleansing et deux lignes `SpellMisc` ; **aucune ne touche un changement de la note**. Les
  correctifs du Guerrier du 2026-10-02 (nœuds, arêtes, Berserker Rage au niveau 30, Rule of Rage) sont désormais dans
  les tables de 70291 : ils passent de (b) à (a).
- Sens des champs : `ProcChance`, `ProcCategoryRecovery` (recharge interne en millisecondes), `DiminishType`,
  `EffectAura` (numéros d'aura des émulateurs : 77 immunité à une mécanique, 107 et 108 modificateurs plat et en
  pourcentage, 230 et 34 PV maximum) : définitions communautaires, `probable`.

## Changements touchant le Mage et le moteur
| Changement (paraphrase) | Classe | Preuve | Moteur | Tranche |
| --- | --- | --- | --- | --- |
| Frostbolt : points de base et progression par niveau des rangs 1 à 5 lissés, chaque nouveau rang toujours meilleur | (a) | `SpellEffect` de 116, 205, 837, 7322, 8406 : `EffectBasePointsF` et `EffectRealPointsPerLevel` changés ; `spells.json` et `spell_scaling.json` de la candidate | **Entrée des moteurs** (`mage_build`, `mage_leveling`) : dégâts des rangs 1 à 5 | Installation de 70291 (révision 1), rejeu des builds |
| Fireball : même lissage des rangs 1 à 5 | (a) | `SpellEffect` de 133, 143, 145, 3140, 8400 | Entrée des moteurs | Installation de 70291 |
| Arcane Missiles : même lissage des rangs 1 à 3 | (a) | `SpellEffect` de 5143, 7269, 7270 (progression par niveau du rang 1, points de base et progression des rangs 2 et 3) | Entrée des moteurs | Installation de 70291 |

**Effet sur les recommandations** (rejeu des 16 cas de T05, 1.60.1.70245 r6 contre 1.60.1.70291, `docs/research/data-1.60.1.70291-r1.md`) : leveling 20 passe du Givre au Feu (égalité statistique, build instable), leveling 30 retouché, donjon et raid 20 passent des Arcanes au Givre (Frostbolt rang 4, appris au niveau 20, plus fort) ; ordre des talents changé en leveling 40 et 60 ; les autres cas sont inchangés. Le rejeu automatique de `forever update` avait comparé 70245 à elle-même (étiquette « après » de provenance 70245 r6) : son « aucun changement » ne valait rien.
| Impact ne se déclenche plus sur les dégâts périodiques de Flamestrike | (c) | Aucune ligne d'Impact (11103, 12355) ni de Flamestrike changée dans les tables ni corrigée par le serveur | Impact non modélisé (B19) : aucun effet | Aucune tant qu'Impact reste hors des simulateurs (B19) |
| Wake of Fire | — | **Absent de la note** ; aucun changement dans les tables de 70291 (talent 11078, sort 1312934) ni dans les correctifs du serveur | Inchangé | — |

## Règles du serveur (c) écrites dans les données
| Changement (paraphrase) | Classe | Données | Registre | Tranche qui le modélise |
| --- | --- | --- | --- | --- |
| XP des monstres tués en donjon augmentée d'environ 20 % | (c) | `mechanics.json` `xp.dungeon_kill_bonus` (révision de 70291, `manuel`, `probable`) | I10 (nouvelle) | **T04d** (modèle d'XP des monstres) ; DJ1 (XP par heure en donjon) |
| XP d'un monstre en groupe ajustée sur le niveau de **chaque** joueur (règle Classic Era), plus sur le plus haut niveau du groupe ; aucune XP pour personne si un membre est d'un niveau très supérieur au monstre | (c) | `mechanics.json` `xp.group_level_basis` (`manuel`, `probable`) | I11 (nouvelle) | **T04d** ; DJ1 (groupes de donjon) |
| Rage gagnée en subissant des dégâts recalculée : sur les PV attendus d'une créature (plus sur ceux du joueur), avec les multiplicateurs de dégâts subis (critiques, coups écrasants), sans tenir compte des absorptions ; équilibrage sur une armure de 20 à 40 % selon le niveau (au lieu de 50 %) | (c) | `mechanics.json` `rage.damage_taken_rule` (`manuel`, `probable`) | B21 (nouvelle) | **GU1** et **DR1** (moteurs du Guerrier et du Druide) |
| Défi Legacy accordé à tous les joueurs de la bêta (16 points Legacy) ; respécialisation Legacy la moins chère à 1 pièce d'argent, le coût baissant d'une respécialisation par heure ; **bêta seulement** | (c), état de la bêta | `mechanics.json` `legacy.beta_grant` (`manuel`, `probable`, valable pendant la bêta) | G5 | **LG1** (catalogue : coûts de réinitialisation) ; **LG2** (points du compte) |
| Butin : retour au comportement Classic, un monstre sans butin reste interactif | (c) | Aucune valeur (règle d'interaction, sans chiffre) | D8 (nouvelle) | Aucune tranche de calcul ; DJ1 pour le relevé du butin |
| Critiques en PvP : plus d'efficacité réduite | (c) | Aucune valeur : la note ne dit pas l'ancienne réduction | K7 (nouvelle) | **PV2** (affrontements chiffrés) ; AN1 |

## Autres classes et races (savoir du client, sans moteur)
| Changement (paraphrase) | Classe | Preuve | Tranche |
| --- | --- | --- | --- |
| Druide : potions de mana utilisables en forme d'ours et de félin | (c) | Aucune ligne changée | DR1 |
| Druide : rage des coups critiques à +100 % (au lieu de +75 %) | (a) | Rule of Rage (DND) 1322574, effet 1358385 à 100 dans les tables (valeur passée par correctif le 2026-10-02) ; options de déclenchement des passifs d'ours 1178 et 9635 retirées (`SpellAuraOptions` 248463, 248464) : sens probable, le déclencheur propre au Druide de 70170 disparaît au profit de la règle commune | DR1 |
| Druide : Thorns revient aux dégâts de base de Vanilla, part de la puissance des sorts à 6 % (au lieu de 13,3 %) | (a) et (c) | Points de base des rangs de Thorns baissés (`SpellEffect` de 467, 782, 1075, 8914, 9756, 9910) ; `EffectBonusCoefficient` inchangé : la part de la puissance des sorts est appliquée par le serveur | DR1 |
| Druide : Cat Form ne réduit plus les PV maximum | (c) | Aucune ligne de Cat Form changée | DR1 |
| Druide : bonus de menace des formes d'ours à 50 % (au lieu de 30 %) | (a) | Bear Form (Passive2) 21178 : `EffectBasePointsF` 30 → 50 | DR1 |
| Druide : transformations qui remplacent la forme limitées (comme en Classic) | (a) partiel | `EffectMiscValue_1` posé sur des dizaines d'effets de transformation (Peon Disguise, Hex, Furbolg Form…) : sens probable | DR1 |
| Druide : Demoralizing Roar génère de la menace | (a) | Nouvel effet sur les cinq rangs (`SpellEffect` 1361978 à 1361982) | DR1 |
| Druide : Wrath, rangs 1 à 5 lissés | (a) | `SpellEffect` de 5176 à 5180 | DR1 |
| Druide, Feral : Predatory Instincts renommé Natural Instinct, gagne des soins égaux à une part de l'Intelligence | (a) | `SpellName` 1223242, nouvel effet 1361117 | DR1 |
| Druide, Feral : Shifting Power interdit à pleine énergie | (c) | Aucune ligne changée | DR1 |
| Druide, Feral : Thick Hide géré dans le code du jeu | (a) | Effets de 1306459 et 16929 changés (aura 665 → 673, progression par niveau, niveau ajouté) | DR1 |
| Chasseur : Disengage réduit deux fois plus la menace | (c) | Aucune ligne changée | CH1 |
| Chasseur : familiers qui regagnaient des PV en boucle à faible vie | (c) | Serveur | CH1 |
| Chasseur, Beast Mastery : Unleashed Fury augmente bien les dégâts du familier | (a) | 19616 : aura 108 → 107 | CH1 |
| Chasseur, Marksmanship : chance d'Improved Concussive Shot corrigée | (a) | `ProcChance` 20 → 100 sur 19407, nouveau sort 1324511 | CH1 |
| Chasseur, Survival : chance d'Improved Wing Clip corrigée, réduite pour un rang très inférieur au niveau | (a) et (c) | `ProcChance` 4 → 100 sur 19228 ; la réduction pour un rang bas est la règle du serveur B20 | CH1 ; B20 |
| Chasseur, Survival : Expose Prey dure 10 s (au lieu de 5) | (a) | `SpellMisc.DurationIndex` de 1310726 : 28 → 1 | CH1 |
| Chasseur, Survival : Entrapment soumis aux rendements décroissants ; seulement à l'activation du piège | (a) et (c) | `SpellCategories.DiminishType` 0 → 1 sur 19185, recopié dans les fiches PvP (`diminish`) ; Frost Trap 13810 renommé, rayons changés : le déclenchement unique est probable | CH1 ; fiches PvP (PV1) |
| Paladin : Retribution Aura prend la puissance des sorts du Paladin | (c) | Serveur (le bug avait été reconnu dans la note du 01/10) | PA1 |
| Paladin : Retribution Aura revient aux dégâts de base de Vanilla (environ un tiers de moins), part de la puissance des sorts à 6 % | (a) et (c) | Points de base des cinq rangs baissés (`SpellEffect` de 7294, 10298 à 10301) ; coefficient inchangé dans les tables | PA1 |
| Paladin, Protection : Reckoning déclenché au plus une fois toutes les 1,5 s | (a) | `SpellAuraOptions.ProcCategoryRecovery` 0 → 1500 sur 20177 | PA1 |
| Paladin, Protection : Seal of Fury ne rend plus de mana sans Improved Seal of Fury ; Improved Seal of Fury et Shield Specialization ne génèrent plus de menace en rendant la mana | (c) et (a) | Bit `Attributes_1` 1024 ajouté sur 1314104 et 1310925 (sens probable : pas de menace) ; le reste au serveur | PA1 (CLS2) |
| Prêtre : Smite, rangs 1 à 4 lissés ; Lesser Heal rangs 1 à 3 et Heal rangs 1 et 2 lissés | (a) | `SpellEffect` de 585, 591, 598, 984 ; 2050, 2052, 2053 ; 2054, 2055 | PR1 |
| Prêtre, Discipline : Penance, dégâts et soins revus (canalisation de 2 s), coût du rang 1 + 50 %, soins des rangs 2 et 4 relevés | (a) | `EffectBonusCoefficient`, points de base et progression des effets de Penance ; `SpellPower.ManaCost` de 402174, 1240720, 1316995 | PR1 |
| Chaman : Flametongue Totem prend la vitesse d'attaque de la cible transformée | (c) | Serveur | CM1 |
| Chaman : Lightning Bolt, rangs 1 à 5 lissés | (a) | `SpellEffect` de 403, 529, 548, 915, 943 | CM1 |
| Chaman, Elemental : Elemental Focus n'est plus consommé par Fire Nova | (c) | Aucune ligne d'Elemental Focus changée | CM1 |
| Chaman, Restoration : infobulle de Water Shield ; visuel de Mana Tide Totem | — | Interface | — |
| Chaman : Mana Tide Totem appris au niveau 25 (au lieu de 40) | (a), **absent de la note** | `SpellLevels` de 16190 et 16191 : 40 → 25 | CM1 |
| Démoniste : le familier présent est étourdi pendant l'invocation d'un autre | (c) | Serveur | DE1 |
| Démoniste : Shadow Bolt, rangs 1 à 4 lissés | (a) | `SpellEffect` de 686, 695, 705, 1088 | DE1 |
| Démoniste, Demonology : Demonic Brand, menace élevée seulement sur dégâts d'ombre | (a) partiel | Infobulle de 1293695 ; la menace est au serveur | DE1 |
| Guerrier : Demoralizing Shout génère de la menace | (a) | Nouvel effet sur les cinq rangs (`SpellEffect` 1361983 à 1361987) | GU1 |
| Guerrier, Arms : Deep Wounds de nouveau requis pour Impale | (a) | Nouvelle arête `TraitEdge` 136737 (nœud 105950 → 105947, type 2) ; prérequis visible dans `classes.json` de la candidate | GU1 |
| Guerrier, Arms : Deep Wounds ne profite plus de la puissance d'attaque de la main gauche | (c) | Serveur | GU1 |
| Guerrier, Protection : Last Stand rend le bon nombre de PV | (a) | Last Stand 12976 : aura 230 → 34 | GU1 |
| Mort-vivant : Will of the Forsaken utilisable endormi ou charmé | (a) | 7744 : trois effets passés en immunité à une mécanique (aura 77), durée ajoutée ; recopié dans `races.json` | Fiches PvP (PV1), G1 |
| Wolfshead Helm : 5 d'énergie quand Shifting Power est utilisé (partie rage inchangée) | (a) | Effets de 17768 et 1310990 : 20 → 5 | DR1 ; T10 |

## Monde, objets, quêtes, PvP, divers
| Changement (paraphrase) | Classe | Preuve | Tranche |
| --- | --- | --- | --- |
| Nouveau donjon City of Dalaran | (c) | Tables de cartes et de donjons non téléchargées | DJ1 |
| Plusieurs armes échangeables dans un même temps de recharge global (macro) | (c) | Serveur | GU1, PA1 (rotations de mêlée) ; sans effet sur le Mage |
| Pulls involontaires à longue distance corrigés ; effets visuels | (c) / — | Serveur, rendu | — |
| Gestionnaire de recharges : toutes les classes, raciaux et bijoux pris en charge (consommables plus tard) | — | Interface | EX1 (sorts suivis du gestionnaire de recharges) |
| Récompenses de quêtes de donjon passées de Rare à Uncommon, stats ajustées ; récompenses de Gelkis et Magram retouchées ; prix de vente d'objets d'Enchantement ; Booty Bay Bruiser's Buckshot ; Transformative Cocoon ; enchantement Revelation | (b) probable, non vérifié | 4 721 lignes `Item` et `ItemSparse` corrigées par le serveur (`Hotfix.log`) ; tables d'objets non décodées | T10a, DJ1, MT1 |
| Truthseeker's Bow : niveau requis 40 | (b) probable, non vérifié | Idem | T10a |
| Potions de soins décolorées : leurs dégâts ne brisent plus les contrôles | (c) | Serveur | PV2 |
| PvP : point de capture de Shipwreck Cove | (c) | Serveur | PV2 |
| Métiers : kits d'armure (puissance d'attaque à distance) ; Enchant Weapon - Recovery en forme de Druide | (c) | Serveur | MT1 |
| Quêtes : Stanley ne donne plus d'XP, la quête « Elixir of Pain » la donne ; quêtes et créatures de Shadowvale et Bandarion Keep (Tirisfal) relevées de niveau ; quêtes de Gelkis et Magram au niveau 35 (au lieu de 30) ; Gloomrise Hatchlings à l'XP de leur difficulté ; réapparitions plus rapides (Durotar, Redridge, Badlands…) | (c) | Tables de quêtes non téléchargées | **T04d** (XP et niveaux des quêtes) ; I7 (zones à mon niveau) |
| Interface, manette, discussion vocale, barbiers | — | Hors données de jeu | — |

## Problèmes connus nouveaux dans ce build (bugs reconnus : jamais modélisés)
- Textures des Skyborne (Druide) et de créatures de Zephras Isle à venir : rendu, sans effet.
- Chasseurs avec le talent Ferocity : la fiche du personnage n'affiche pas la hausse du critique du familier.
  **Bug d'affichage seulement** : ne pas en tirer la valeur réelle du talent (CH1).
- Icônes cassées dans la fenêtre des métiers : sans effet.

## Suites dans le dépôt
- Données : 1.60.1.70291 installée avec ses correctifs du serveur ; les quatre règles du serveur chiffrées plus haut
  sont écrites à la main (`manuel`, `probable`, source t/2360696/5 révision 1) dans `mechanics.json` de 70291, avec
  leur entrée dans `origins.json`. Aucun moteur ne les lit encore : elles attendent T04d, GU1, DR1 et LG1.
- Registre : nouvelles entrées I10 (XP des monstres de donjon), I11 (XP en groupe), B21 (rage des dégâts subis),
  D8 (butin), K7 (critiques en PvP), toutes `absent`, `probable` ; G5 (Legacy, état de la bêta), I6 (XP du leveling
  solo : sans effet) et B19 (Impact, Wake of Fire inchangé) complétés.
- `docs/OPEN_QUESTIONS.md` : LVL1, PVP2, PVP5, CLS2 et LEG1 modifiées ; LVL4 (XP de groupe), LVL5 (hausse de l'XP
  des monstres de donjon), PVP6 (critiques en PvP) et CLS4 (formule de rage) ajoutées. Aucune question ouverte n'est
  tranchée par cette note : `docs/RESOLVED_QUESTIONS.md` inchangé.
