# Questions ouvertes : détail technique (texte d'origine du 2026-10-02)

Texte de chaque question restante tel qu'il figurait dans `docs/OPEN_QUESTIONS.md` avant sa réorganisation du
2026-10-02 (par domaine, une phrase, un test et une priorité). Chaque section porte l'identifiant de la question
dans `docs/OPEN_QUESTIONS.md`. Les questions résolues sont dans `docs/RESOLVED_QUESTIONS.md`. Ce texte est
archivé tel quel : les mises à jour se font dans `docs/OPEN_QUESTIONS.md`, ou dans le rapport de recherche du
domaine qu'il cite.

## Temps, incantation et canalisation

<a id="tps1"></a>
### TPS1

- Regroupement des actions serveur dans Forever : mesurer sur journaux (intervalles entre lancers). Test : 50 sorts instantanés enchaînés (protocole B1 de `docs/ADDON.md`) ; des intervalles groupés sur une grille fixe révéleraient un regroupement.

<a id="tps2"></a>
### TPS2

- Recul d'incantation : 0,5 s sans limite ? Mesurer. Test : Frostbolt incanté sous les coups d'un monstre de mêlée (journal : écart entre `SPELL_CAST_START` et `SPELL_CAST_SUCCESS` selon le nombre de coups reçus pendant l'incantation).

<a id="tps3"></a>
### TPS3

- B6, I1 (T04c, relecture) : en décharge de la rotation arcane, Arcane Missiles (canalisé) n'est plus prolongé par le recul d'incantation ; en Classic, le recul raccourcit une canalisation (tics perdus), non modélisé : `suppose`, à mesurer (journal : fins de canalisation sous les coups). Notes officielles du 24/09/2026 révisées le 01/10 (<https://us.forums.blizzard.com/en/wow/t/2360696>) : la ligne de vue d'Arcane Missiles n'est plus vérifiée qu'au début de la canalisation (non modélisée). Problèmes connus officiels du 01/10/2026 (<https://us.forums.blizzard.com/en/wow/t/2352687>) : sous les coups, Arcane Missiles tire un projectile à pleins dégâts au lieu d'un projectile tronqué. C'est un bug reconnu, jamais modélisé ; le comportement voulu (projectile tronqué) reste à mesurer une fois le bug corrigé.

<a id="tps4"></a>
### TPS4

- Durées d'incantation mesurées sous la table (Frostbolt r3 : 1,92, 2,07 et 1,98 s dans le journal de la fixture, pour 2,2 s dans `spells.json`) : talents (Improved Frostbolt), file d'attente des sorts ou horodatage serveur. Les intervalles entre instantanés enchaînés descendent à 1,41 s dans le second journal : gigue d'horodatage ? (B1, n à augmenter).
- T04b, B1 : validée par les journaux selon le critère de l'utilisateur (10e percentile ≥ 1,45 s et médiane à ±0,05 s de 1,5 s) : 50 intervalles, 10e percentile 1,4569 s, médiane 1,511 s. Les 3 intervalles sous 1,45 s (1,414, 1,418, 1,424 s) viennent probablement de la variation d'horodatage du journal (horodatage client à la milliseconde, file d'attente des sorts) ; à confirmer par une campagne dédiée (protocole de docs/ADDON.md) avant de viser `valide-jeu`.

## Sorts et dégâts du Mage

<a id="mag1"></a>
### MAG1

- G4, E2 (T04e) : pénalité des sorts de bas niveau dans Forever. Absente de la table du client (Frostbolt r1 : `EffectBonusCoefficient` 0,407 = 1,5 / 3,5 × 0,95, sans pénalité) ; règle Classic supposée appliquée par le serveur, gardée par défaut (`mechanics.json` `coefficient.low_level_default`, `suppose`), désactivable (`--low-level-penalty off`, option `low_level_penalty`). Appliquée aussi au coefficient par tic des DoT (Flamestrike r1, niveau 16 : `suppose`). Sens des doublons de Fire Blast 400616-400623 (`AcquireMethod` 3) à éclaircir. À trancher par le test en jeu E2 (`docs/ADDON.md`, protocole de collecte) ; l'utilisateur change la clé des données. Le coefficient brut du client ne tranche pas : en Classic aussi, la pénalité est appliquée par le serveur sur un coefficient brut voisin. Le client ne dit rien de la pénalité du serveur, E2 reste ouverte. Test retenu : Frostbolt rang 1 à deux puissances des sorts éloignées, la pente des dégâts dit si la réduction est réappliquée (protocole E2 de `docs/ADDON.md`).

<a id="mag3"></a>
### MAG3

- École Givre-feu (Frostfire Bolt) comptée à la fois en givre et en feu : double bénéfice des talents des deux écoles ; pour le multiplicateur de critique, la branche givre (Ice Shards) l'emporte (comportement de `fm.py`, conservé en T02). À vérifier en jeu. Texte du client 1.60.1.70124 (sort 401502, 2026-10-02) : résistance la plus basse entre Givre et Feu, compte comme les deux écoles : concordance avec le modèle ; le texte ne dit rien d'Ice Shards ni de Fire Vulnerability. Test : critiques de Frostfire Bolt avec Ice Shards pris (multiplicateur), et Frostfire Bolt sous cumuls de Fire Vulnerability (Improved Scorch) contre sans.
- A20 (T04e) : Fire Vulnerability (aura 22959, feu) appliquée à Frostfire Bolt, compté comme feu (même question que l'école double Givre-feu ci-dessus, `suppose`).

<a id="mag4"></a>
### MAG4

- G4, E4 (T04e) : coefficient d'Ice Lance nul dans le client (six rangs), retenu en mode forever (`probable`) ; 0,1429 (estimation) en mode seed. À confirmer par le test en jeu E4. Revérifié le 2026-10-02 sur 1.60.1.70124 : `EffectBonusCoefficient` nul sur l'effet de dégâts des rangs 1 et 2 (1312002, 400640), concordance ; à mesurer (E4).

<a id="mag5"></a>
### MAG5

- A17, E3 (T04e) : puissance des sorts par tic des DoT (Pyroblast 0,15, Flamestrike 0,032 ; Fireball et Frostfire Bolt 0) et période des tics du client (Pyroblast et Frostfire Bolt 3 s). Fireball r3 confirmé par le journal du 2026-09-27 (trois tics de 2 à 13 de puissance des sorts). Pyroblast à confirmer par le test en jeu E3.

<a id="mag6"></a>
### MAG6

- T08b, bloc B (2026-10-01) : **multiplicateur de critique des sorts et tics de DoT critiques** (`leveling.json` `combat_rules.crit_mult_spell`, `dot_can_crit`) : règles du serveur, absentes des tables. Mesure sur les 8 journaux du poste (`forever logs measure`) : 174 coups critiques, presque tous d'un Chasseur ; un seul critique de sort du Mage (Frostbolt), aucun tic de DoT du Mage : effectif bien sous `tolerance.n_min`. Les deux restent `suppose` (règle Classic) ; à mesurer sur une session de Mage (critiques de Frostbolt et de Fireball, tics de Pyroblast et d'Ignite).

<a id="mag7"></a>
### MAG7

- A20, E6 (T04e) : bonus de dégâts en pourcentage de deux sources distinctes (Arcane Power et cumuls d'Arcane Blast, tous deux aura 108) multipliés en mode forever (`probable` : les exemples V13 et V18 de la vidéo BVSgeHp3sWU ne tombent juste qu'ainsi), additionnés en mode seed. À confirmer par les journaux (E6).

<a id="mag8"></a>
### MAG8

- G7, E7 (T04e) : le jeu arrondit-il ou tronque-t-il les bornes de dégâts (min et max) ? Le moteur arrondit au demi supérieur (reproduit les rangs décodés, test G7) ; le tableur de la vidéo BVSgeHp3sWU tronque (Ice Lance r6 136-160, Arcane Explosion r6 238-258) : trois exemples de la vidéo exclus des tests pour cet écart (`tests/fixtures/community/BVSgeHp3sWU.json`, `exclu` E7). À trancher par les journaux de l'utilisateur : dégâts minimum et maximum observés pour un sort à puissance des sorts connue (protocole E7 de `docs/ADDON.md`).

<a id="mag9"></a>
### MAG9

- G4 (T04e) : coefficient de Blizzard. Le moteur prend celui du sort déclenché (8 × 0,042, `probable`) ; l'effet factice du sort parent porte 0,03. À trancher par un tic de Blizzard (sans variance) à deux niveaux de puissance des sorts.

<a id="mag10"></a>
### MAG10

- A18 (T04c, demandée par l'utilisateur) : règle d'Ignite de Forever (aura 412538, non cumulable, **roulante supposée**) à vérifier par les journaux : montant de chaque tic (`SPELL_PERIODIC_DAMAGE` de 412538) contre la part du talent × dégâts du critique + reste non infligé, et intervalles des tics (2 s attendues ; le compteur repart-il au second critique ?) après deux critiques de feu rapprochés ; talents d'Ignite relevés par ForeverLogger. `forever measures refresh` compare chaque épisode à la règle des données et à la variante « compteur conservé ». T05 : l'assiette est tranchée par les notes de Blizzard du 24/09/2026 (<https://us.forums.blizzard.com/en/wow/t/2360696/1>, « Ignite no longer double dips on % damage increase modifiers », build 70009) : part du critique final, bonus en pourcentage pris une fois ; le même épisode de journal le confirme si le montant d'un tic égale part × critique / tics, sans multiplicateur de dégâts supplémentaire.

<a id="mag11"></a>
### MAG11

- B11 (T04c) : coût d'Arcane Blast à `n` cumuls supposé additif (base × (1 + 1,75 n), `probable`) ; effet de Clearcasting sur le cumul (lancer gratuit, cumul pris : `suppose`) : relever les coûts par `SPELL_CAST_SUCCESS` et le bloc avancé. Client 1.60.1.70124 (2026-10-02) : aura 400573, coût +175 % par cumul, 4 cumuls, 8 s : concordance ; additif ou composé n'est pas dans le client (`suppose` pour la forme, test inchangé).

<a id="mag12"></a>
### MAG12

- B15 (T05, Arcane Power dans les rotations, suppose) : (1) la hausse de coût d'Arcane Power (+30 %) se multiplie-t-elle au coût croissant d'Arcane Blast (modèle) ou s'y ajoute-t-elle ? (2) l'aura s'applique-t-elle au lancer qui finit dans sa fenêtre (modèle) ou à celui qui commence dans sa fenêtre (coût payé au début de l'incantation) ? Test en jeu : relever le coût d'un Arcane Blast à 3 cumuls sous Arcane Power, et le coût d'un Frostbolt commencé 1 s avant la fin de l'aura.

<a id="mag13"></a>
### MAG13

- B15 (T05, Hot Streak, suppose) : les cumuls de Hot Streak (20 s) sont remis à zéro entre deux combats du leveling (modèle) ; s'ils passent d'un combat au suivant (repos plus court que 20 s), le Feu est un peu sous-évalué. Un critique de Fire Blast compte-t-il bien (description du talent : oui) ?

<a id="mag14"></a>
### MAG14

- B7 (T04c) : Arcane Meditation et Mage Armor **cumulées** (règle Classic, deux auras 134 du client, `suppose`) en `rules forever` ; le seed gardait le maximum (`rules seed`). Vérifier en jeu : mana régénérée en incantation avec les deux (ForeverLogger, protocole de collecte B7). Le bonus d'armure de Frost et Ice Armor (aura 22, lu dans le client) n'est pas ajouté à l'armure du personnage. Ice Armor reprend la durée et le ralenti des coups de Frost Armor (`spells.json.utility`), alors que son sort de ralenti est 7321 (Frost Armor : 6136) : lire ses valeurs dans le client ou les mesurer (C5, `suppose`).

<a id="mag15"></a>
### MAG15

- H2, B19 (T06b) : Arcane Subtlety (réduction des résistances de la cible) et Improved Flamestrike (critique de Flamestrike) sont des angles morts non chiffrés ; leur effet dépend des résistances des monstres (inconnues) et de la part de Flamestrike dans les rotations de zone.
- B19 (T06b, audit du registre) : Improved Flamestrike n'agit que dans les rotations de zone (donjon, raid) ; l'angle mort couvre les cinq contextes et reste non chiffré. Borne possible : critique du talent × part de Flamestrike dans les scénarios de paquet.

<a id="mag16"></a>
### MAG16

- Transfert (Blink) utilisable sous étourdissement ? Tester en jeu. Texte du client 1.60.1.70124 (sort 1953, 2026-10-02) : « libère des étourdissements et des immobilisations », concordance avec `spells.json` ; le texte ne dit pas si le sort se lance sous étourdissement.

<a id="mag18"></a>
### MAG18

- Rangs de sort au niveau du personnage : fait en T04a (`spell_scaling.json`, `rank_values_at_level`, registre G7) ; reste à confirmer en jeu que les dégâts d'un rang suivent le niveau du personnage jusqu'à `MaxLevel` (journal de leveling avec ForeverLogger).

## Personnage et ratios du client

<a id="per1"></a>
### PER1

- Audit des mises à jour (2026-10-01) : **critique de base des sorts** absente des GameTables de Forever (`chancetospellcritbase` vide) : portée par une aura passive de classe (`SpellEffect`) ? Sinon, mesure par `GetSpellCritChance` de ForeverLogger à Intelligence connue. **Mana par point d'Intelligence** introuvable dans le client : mesurer par `UnitPowerMax` à Intelligence connue.

<a id="per2"></a>
### PER2

  - `PlayerExpectedStat` : colonnes sans nom (`Field_1_60_1_69876_005`, lue comme PV par point d'Endurance, sens probable recoupé par la GameTable `hppersta` ; `Field_1_60_1_69876_006`, sens inconnu). Vérifier par `UnitHealthMax` à deux valeurs d'Endurance (ForeverLogger) ;
  - `ExpectedStat` porte aussi `PlayerHealth` et `PlayerMana` par niveau : servent-ils au joueur, ou seulement au calibrage des créatures ?
- T08b, bloc A (2026-10-01) : **colonne `Field_1_60_1_69876_006` de `PlayerExpectedStat`** (croît avec le niveau, sens inconnu) non décodée ; **`Field_1_60_1_69876_005`** lue comme PV par Endurance (sens probable, concorde avec la GameTable `hppersta` à tous les niveaux et pour les 9 classes). À confirmer par ForeverLogger (`UnitHealthMax` à Endurance connue).

<a id="per3"></a>
### PER3

  - `GlobalCurve` types 29 à 32 (courbes constantes, sans documentation WoWDBDefs) : régénération de mana par l'Esprit ? Les GameTables qui la portent en Classic (`regenmpperspt`, `octregenmp`) sont vides sur Forever. Vérifier par une mesure en jeu (mana regagnée hors de la règle des 5 secondes, Esprit connu, ForeverLogger) ;
  - `GlobalCurve` types 27 et 28 (régénération de PV par l'Esprit, sous-type = classe) : la courbe du Chasseur au type 27 ne concorde pas avec Classic ; la formule qui combine les deux courbes reste au serveur (`suppose`). Vérifier par la régénération hors combat d'un Chasseur et d'une autre classe à Esprit connu ;
  - `PlayerExpectedStat` : colonnes sans nom (`Field_1_60_1_69876_005`, lue comme PV par point d'Endurance, sens probable recoupé par la GameTable `hppersta` ; `Field_1_60_1_69876_006`, sens inconnu). Vérifier par `UnitHealthMax` à deux valeurs d'Endurance (ForeverLogger) ;
  - `ExpectedStat` porte aussi `PlayerHealth` et `PlayerMana` par niveau : servent-ils au joueur, ou seulement au calibrage des créatures ?

<a id="per4"></a>
### PER4

  - `GlobalCurve` types 27 et 28 (régénération de PV par l'Esprit, sous-type = classe) : la courbe du Chasseur au type 27 ne concorde pas avec Classic ; la formule qui combine les deux courbes reste au serveur (`suppose`). Vérifier par la régénération hors combat d'un Chasseur et d'une autre classe à Esprit connu ;
  - `PlayerExpectedStat` : colonnes sans nom (`Field_1_60_1_69876_005`, lue comme PV par point d'Endurance, sens probable recoupé par la GameTable `hppersta` ; `Field_1_60_1_69876_006`, sens inconnu). Vérifier par `UnitHealthMax` à deux valeurs d'Endurance (ForeverLogger) ;
  - `ExpectedStat` porte aussi `PlayerHealth` et `PlayerMana` par niveau : servent-ils au joueur, ou seulement au calibrage des créatures ?

<a id="per5"></a>
### PER5

  - `ExpectedStat` porte aussi `PlayerHealth` et `PlayerMana` par niveau : servent-ils au joueur, ou seulement au calibrage des créatures ?

<a id="per6"></a>
### PER6

- Modèle de personnage : `leveling.json.player_model` (texte) omet les termes `0,8 × max(0, niveau − 5)` (Intelligence) et `0,5 × max(0, niveau − 5)` (Esprit) que `fm.py` applique ; le code du seed fait foi pour la parité (`mechanics.json` : `late_bonus_per_level`). À trancher avec des fiches de personnage réelles.

<a id="per7"></a>
### PER7

- T08b (2026-10-01) : la fiche du personnage de Jen (interface EllesmereUI) affiche « Critical Strike » 4,9 % au niveau 19, alors que `GetSpellCritChance` (ForeverLogger) rend 4,62 % pour les sorts, valeur prédite par la révision 4 : la ligne de la fiche est probablement la critique générale (mêlée) ; à confirmer par l'infobulle du jeu de base.

## Monstres et rencontres

<a id="mon1"></a>
### MON1

- T04b, H11 (décision 5) : correction PV Questie → Forever ajustée sur 7 niveaux (10 à 17) d'une seule zone (les Tarides) ; extrapolée jusqu'à × 2,29 au niveau 60 (`suppose`). Forever donne-t-il une valeur commune par niveau aux PNJ normaux ? Inversions de l'agrégat listées aux niveaux 25 (Sarilus Foulborne mesuré), 56 et 60 (médianes Questie). Le troisième journal réel (`WoWCombatLog-092726_174130.txt`, 17:41, 635 événements) est intégré à `monsters.json` mais n'apporte aucun relevé de PV : de nouveaux journaux de leveling hors des Tarides restent nécessaires. **Modifiée le 2026-10-02** (1.60.1.70170 révision 2, journal `WoWCombatLog-100226_080035`) : correction ajustée sur 13 niveaux (1 à 22) de trois zones (Dun Morogh, Sombrivage, Forêt des Pins-Argentés), pente 0,0238 au lieu de 0,0248 ; les PNJ normaux d'un même niveau gardent une valeur commune (18 à 20). Reste l'extrapolation au-delà du niveau 22.
- Questie : licence amont (aucun fichier de licence dans l'addon installé ; CurseForge 334372, lignée cmangos) à vérifier avant tout élargissement ; base Classic Era : le 2026-09-27, 29 écarts sur 21 PNJ mesurés (Forever plus haut dès le niveau 10 ; les PV mesurés semblent ne dépendre que du niveau pour les PNJ normaux : 208, 239, 272, 307 aux niveaux 10 à 13, sauf Sunscale Lashtail). Les niveaux de `hp_by_level` venus de Questie (`suppose`) sont donc probablement trop bas.

<a id="mon2"></a>
### MON2

- H11 (2026-10-02) : **PNJ au-dessus des PNJ normaux de leur niveau** (`monsters.json` `curve_excluded`, écartés de la courbe sur décision de l'utilisateur) : Thistle Bear (299 PV au niveau 11 contre 239), Grizzled Thistle Bear (534 et 591 aux niveaux 16 et 17 contre 427 et 473), Dark Strand Enforcer et Wildthorn Stalker (642 au niveau 20 contre 629 ; Wildthorn Stalker seul mesuré au niveau 21, 691). Famille de créature (ours), rang caché ou PNJ renforcé ? Test : relever d'autres ours et d'autres PNJ de ces deux familles à niveau connu ; une règle commune (même facteur) justifierait un modèle par famille, sinon ils restent écartés un par un. Le niveau 22 ne repose que sur un PNJ (3774, 746 PV, `probable`) relevé pendant une session en cours.
- Sarilus Foulborne (3986) mesuré à 927 PV au niveau 25 (Questie : 573, rang 0) : PNJ de quête peut-être renforcé dans Forever ; il pèse seul sur `hp_by_level` du niveau 25.

<a id="mon3"></a>
### MON3

- Audit des mises à jour (2026-10-01) : **table d'armure et table de PV des monstres réellement lues par le serveur**. Armure : `ExpectedStat.ArmorConstant` suit la formule Classic du moteur, la GameTable `armormitigationbylvl` donne une valeur de retail incompatible ; laquelle le serveur applique-t-il ? Vérifier par la réduction de dégâts d'un coup de monstre de niveau connu contre une armure connue (journal, bloc avancé). PV : `ExpectedStat.CreatureHealth` et la GameTable `npctotalhp` sont en désaccord, `CreatureDifficulty` ne porte pas de PV ; comparer les deux tables aux PV mesurés dans les journaux (Tarides, niveaux 10 à 17) avant d'en utiliser une au-delà de la plage mesurée (H11).
- T08b, bloc A (2026-10-01) : **GameTable `npctotalhp`** (colonnes par classe, valeurs fractionnaires) téléchargée, sens non établi ; comparer à `ExpectedStat.CreatureHealth` et aux PV mesurés dans les journaux avant tout usage (question de l'audit ci-dessus).

<a id="mon4"></a>
### MON4

- Règles Classic supposées inchangées dans Forever (registre A3, B1, H1 : raté des sorts selon l'écart de niveau et son plancher, temps de recharge global, niveau de la cible d'un boss) : les observer dans Forever (journaux de combat sur mannequin et sur boss, intervalles entre lancers) avant de les repasser en `probable` ou `certain`.
- T04b, A3 (décision 4) : 0 raté de table sur 281 sorts directs du Mage (seconde fixture, niveau du lanceur par le carnet de Questie), cibles 2 à 8 niveaux plus bas : très improbable avec l'ancienne ligne « - » à 4 % (0,96^281 ≈ 1e-5), plausible avec la règle Classic désormais appliquée (4 % − 1 % par niveau d'écart, plancher 1 % : 0,99^281 ≈ 6 %) ; talents de toucher du Mage inconnus. Les écarts 0 à +3 restent à mesurer : campagne sur des cibles de niveau égal ou supérieur, avec ForeverLogger chargé.

<a id="mon5"></a>
### MON5

- H3, H5 (T05, scénarios provisoires, `build.scenarios`, suppose) : boss de donjon et de raid **insensibles au gel** (règle Classic supposée : pas de Frostbite ni de gel, donc pas d'Ice Lance sur cible gelée ; Fingers of Frost reste utilisable) ; durées, écarts de niveau et nombre de cibles inventés pour comparer les builds, à remplacer par les rencontres réelles (DJ1, T09). À vérifier : un boss de donjon de Forever peut-il être gelé par Frostbite ? Test : journal de donjon avec Frost Nova et Frostbite sur un boss (aura de gel appliquée, ou absorbée par une immunité dans le journal).

## Données du client et correctifs du serveur

<a id="don1"></a>
### DON1

- Hotfixes du client (`DBCache.bin`) non appliqués par le pipeline (T03) : une valeur décodée des tables wago peut différer du jeu en ligne. Comparer au jeu les valeurs installées ; voie autonome `db2tool` si l'écart se confirme.
- Hotfixes : `Hotfix.log` montre des lignes CurvePoint (144) et Curve (72) remplacées : les rangs de talent décodés en T03 peuvent différer du jeu en ligne ; CreatureDifficulty (3) : PV de créatures corrigés. Décodage de `DBCache.bin` en T08.
- Hotfixes (2026-10-02) : les talents du Guerrier annoncés le 2026-10-02 (« Warrior Updates in Today's Beta Build », Lingering Rage, Furious Precision, Gore Drinker…) sont absents des tables de 1.60.1.70170 (wago) ; `Logs/Hotfix.log` du lancement de 08:00 compte 87 enregistrements `Trait*` corrigés par le serveur. Ils restent hors des données tant que `DBCache.bin` n'est pas décodé (T08) : les builds du Guerrier relus sur `classes.json` peuvent différer du jeu.
- T08b, bloc E (2026-10-01) : **sens de `VALIDATION_RESULT_INVALID` dans `Logs/Hotfix.log`** (compté à part par `forever hotfixes`, jamais traité comme un correctif) ; et les enregistrements corrigés absents du cache (`CurvePoint` 363264 à 363412, `Curve` 124805 à 124878, relevés du 2026-10-01) sont probablement des **enregistrements ajoutés par le serveur** : ils ne se relient à aucune entité tant que `DBCache.bin` n'est pas lu (T08).

<a id="don3"></a>
### DON3

- Données (T08a, 2026-09-30) : que change 1.60.1.70124 **hors** des 22 tables décodées ? Les tables téléchargées sont identiques à celles de 1.60.1.70009, mais `Logs/Hotfix.log` montre 4 386 enregistrements de la table `Item` surchargés par le serveur le 2026-09-30 (`Item` n'est pas téléchargée, base d'objets en T10). Deux publications sont concernées (70058 et 70124). À reprendre quand T10 lira les tables d'objets, ou par les notes de version si Blizzard en publie.

<a id="don4"></a>
### DON4

- Produit TACT au lancement (wow_classic_forever ?). Le client installé est `wow_classic_beta` 1.60.1.70170 (`.build.info`, lu sur disque le 2026-10-02) ; le produit du lancement reste inconnu.

<a id="don6"></a>
### DON6

- Pièges, totems et portails (sorts dont l'effet est porté par un objet ou une créature invoqués, absents des tables lues) : non classés en PvP ; tables `GameObjects` ou `Creature*` à identifier.

<a id="don7"></a>
### DON7

- Conditions d'emploi des sorts (posture, forme, camouflage : SpellShapeshift, SpellAuraRestrictions téléchargées mais non décodées) et durées à points de combo (Kidney Shot : durée de base seule) : à décoder avant PV2.

<a id="don8"></a>
### DON8

- CH0 (2026-10-01) : **variables d'infobulle `$a` et `$x`** (rayon, nombre de cibles) non prises en charge par `forever/pipeline/tooltip.py` : textes de Furious Howl, Lava Breath, Swipe et Thunderstomp gardés bruts (`tooltip_error`).

<a id="don9"></a>
### DON9

- Donjons, métiers, réputations, économie : tables du client à identifier à l'inventaire de chaque tranche (journal de rencontre et butin, recettes et composants, factions et paliers, prix de vente) ; ne rien présumer de leur présence.

## Journaux, addons et sauvegardes

<a id="log1"></a>
### LOG1

- Bloc avancé du journal (format 22 de Forever, 19 champs contre 17 en Retail) : sens des deux champs entre l'absorption et le type de ressource (toujours 0 relevé) ; sens du dernier champ pour un **joueur** (niveau d'objet ?) : il vaut 7 pour le Mage du 2026-09-27, qui lance Frostbolt rang 3 (niveau de base 14). À comparer au niveau de `ForeverLoggerDB` (`forever logs measure --addon-sv`, champ `player_level_field`).

<a id="log2"></a>
### LOG2

- Suffixe de dégâts : `amount` et `base_amount` diffèrent parfois d'une unité hors critique (53 / 52) ; ordre des trois derniers champs (critique, glancing, écrasant) supposé celui de Retail. Les rapports de critique du second journal vont de 1,51 à 1,6 (arrondis sur de petits montants ?).

<a id="log3"></a>
### LOG3

- Mesures du journal, limites connues (relecture T04a) : un `SPELL_CAST_SUCCESS` sans START est compté comme instantané ; Presence of Mind, Arcane Power, une potion ou un sort hors recharge globale fausseraient les intervalles de B1 quand l'échantillon grossira (filtrer par la recharge globale des sorts, `SpellCooldowns.StartRecoveryTime`, avant de viser `valide-journal`) ; un START interrompu puis le même sort instantané reprend l'ancien START. `hit_tally` retient un seul niveau du lanceur par journal (début du journal) : l'écart est décalé d'un après un gain de niveau en cours de journal.

<a id="log4"></a>
### LOG4

- Addon ForeverLogger (modifiée le 2026-10-02) : chargé en jeu depuis le 2026-09-28 ; sa sauvegarde sur disque porte, hors combat, les rangs de talents par nœud (`C_ClassTalents.GetActiveConfigID`, `C_Traits.GetNodeInfo`), le bonus et la critique des sorts par école (`GetSpellBonusDamage`, `GetSpellCritChance`) ; reste à vérifier que ces API ne deviennent pas secrètes en combat ni en champ de bataille. Sondes `/dump` à faire avant toute conclusion : liste dans `docs/ADDON.md` (section 7, sondes).

<a id="log5"></a>
### LOG5

- PvP, addon : la classe de la cible (et les autres informations nécessaires à une fiche fixe) reste-t-elle lisible, non secrète, en champ de bataille ? Sonder avant FA1.

<a id="log6"></a>
### LOG6

- SavedVariables (recherche du 2026-09-30, sources de joueurs, aucun message de Blizzard) : sur 1.60.1.69893 et 69913, le client écrivait les SavedVariables à la déconnexion sans les relire au lancement ; des joueurs le disent corrigé sur 70009. À vérifier en jeu sur la version courante (un réglage de ForeverLogger survit-il à un redémarrage ?) avant de compter sur un addon collecteur (MobInfo2, KillDex, Forever Journal) ou sur les relevés de ForeverLogger d'une session à l'autre ; dater chaque relevé par build du client. Pas un bug reconnu par Blizzard : rien n'est modélisé. Observation du 2026-10-02 (fichier du poste, source primaire) : la sauvegarde de ForeverLogger, écrite le 2026-10-02, garde des instantanés datés du 2026-09-28 au 2026-10-02 (builds 70009 à 70170) : les SavedVariables sont relues d'une session à l'autre (`probable` : à confirmer par un réglage qui survit à un redémarrage complet du client).

<a id="log7"></a>
### LOG7

- Addons collecteurs sur Forever (recherche du 2026-09-30) : MobInfo2 relève-t-il vraiment PV, XP et résistances, ou seulement les morts et le butin (son auteur dit les PV secrets) ? Les PV max d'un ennemi (`UnitHealthMax`) sont-ils secrets hors combat ? Test : une session avec MobInfo2 ou KillDex hors instance, puis lecture de leurs SavedVariables sur disque.

<a id="log8"></a>
### LOG8

- Questie : licence amont (aucun fichier de licence dans l'addon installé ; CurseForge 334372, lignée cmangos) à vérifier avant tout élargissement ; base Classic Era : le 2026-09-27, 29 écarts sur 21 PNJ mesurés (Forever plus haut dès le niveau 10 ; les PV mesurés semblent ne dépendre que du niveau pour les PNJ normaux : 208, 239, 272, 307 aux niveaux 10 à 13, sauf Sunscale Lashtail). Les niveaux de `hp_by_level` venus de Questie (`suppose`) sont donc probablement trop bas.

<a id="log9"></a>
### LOG9

- Époque des jours d'Auctionator (`DAY_EPOCH`, jours depuis le 2020-01-01, probable) : confirmer par une seconde date de relevé.
- API Blizzard (EC1, élargie par la décision 126) : couverture de Forever après le lancement du 4 novembre (produit, espace de noms, hôtel des ventes par royaume ou région, profils de personnages avec équipement et talents, honneur, rang et classements PvP). Auctionator sur Forever : fonctionnement et format de sa base de prix dans les SavedVariables (format relevé le 2026-09-28, `tasks/inventaire-addons.md`, `probable`).

## Leveling, quêtes et donjons

<a id="lvl1"></a>
### LVL1

- T04d : source des quêtes propres à Forever (aucune dans Questie 11.38.0 ; piste locale : l'addon `GearQuestForever`, tables de quêtes du client) et modèle d'XP de Forever (XP des monstres et des quêtes).

<a id="lvl2"></a>
### LVL2

- I7 (T04c) : couleurs de quête de Forever identiques à Classic ? La plage verte vient de `GetQuestGreenRange` (API du client, absente sur disque), remplacée par le niveau gris communautaire de Classic ; ForeverLogger pourrait relever `UnitQuestTrivialLevelRange("player")` à chaque niveau. Niveaux des quêtes : base Classic Era de Questie sans correction Forever.

<a id="lvl3"></a>
### LVL3

- D7 et D5 (T04f, décision 199) : durée du Well-Rested donnée à 2 h par foreverchanges.pro (lecture du client revendiquée par le site) et à 1 h par des guides ; les deux sont des sources communautaires (`suppose`). La valeur se lit dans `SpellDuration` du sort de l'aura (index de durée de `SpellMisc`), décodée comme les durées des autres sorts ; la règle de cumul (repos, sac de couchage, nourriture, perks Legacy, camps) n'est écrite nulle part dans le client à notre connaissance et se mesure par le gain d'XP relevé hors combat. Chaîne de quêtes du sac : Naowh Forever (`SleepingBagData.lua`, Wowhead Forever, 4 octobre), `suppose`.

## PvP

<a id="pvp1"></a>
### PVP1

- PvP : rendements décroissants de Forever supposés identiques à Classic (catégories, fenêtre, paliers) : mesurer dans les journaux de champs de bataille (PV2) avant de quitter `suppose`. Le classement des contrôles par catégorie depuis les champs du client est-il fiable pour toutes les classes ? Les sorts non résolus sont listés en PV1.
- Rendements décroissants en PvP (PV1, registre K1, `pvp_rules.json`, suppose) : paliers, fenêtre de remise à zéro (fin de l'effet ou application ; fixe ou comprise entre deux bornes), immunité, plafond de durée sur un joueur, racines et silences (immunité dès la 2e application selon un wiki de fans de Forever), rendements contre les PNJ, catégorie 2 du client non identifiée : mesurer dans mes journaux de champ de bataille (PV2, `docs/research/pvp-dr-protocole.md`).
- Fenêtre des rendements décroissants relancée par une application en immunité (K1, choix supposé dans `forever/engine/diminishing.py`, noté dans `pvp_rules.json`) : vérifier en champ de bataille si répéter un contrôle sur une cible immunisée prolonge l'immunité.

<a id="pvp3"></a>
### PVP3

- Plafond de durée PvP (K3) appliqué aussi aux contrôles sans catégorie de rendement décroissant (choix supposé, `pvp_rules.json` : groupes concernés non établis) : mesurer sur un contrôle sans catégorie (Death Coil, Blind) en champ de bataille.

<a id="pvp4"></a>
### PVP4

- Recharge partagée entre un bijou PvP et un racial (Will of the Forsaken…) : non décidée par le client (registre K4, absent) ; tester en jeu. Test : Will of the Forsaken puis le bijou PvP (ou l'inverse) hors combat : le second sort est-il grisé, et pour combien de temps ?

<a id="pvp5"></a>
### PVP5

- PvP (PV1, PV2) : date d'ouverture des champs de bataille (« bientôt », aucune source dans le dépôt), liste des champs, système de récompenses (honneur, rangs, marques) et règles du monde ouvert (types de royaume, zones contestées) : attendre les annonces officielles. Sujets officiels du forum lus le 2026-10-02 (`forever notes` : notes de développement, problèmes connus, Guerrier du jour, annonce de la BlizzCon) : aucune date, aucune règle de royaume, aucun champ de bataille (Darkspear Islands compris). À chercher dans une autre source officielle (site d'actualités de Blizzard, non lu).

## Autres classes

<a id="cls2"></a>
### CLS2

- Mana rendue par Improved Seal of Fury : client 1.60.1.70124 (2026-10-02) : sort 1314103, `$m1` nul, `$m2` 15 (hausse par niveau de l'attaquant au-dessus du Paladin), `$m3` 3 (plafond `$m2 × $m3`) ; le sort 1314104 rend `$PL` de mana (variable non résolue par `forever/pipeline/tooltip.py`, effet d'énergie à 1 point de base). Le « 60 » d'un calculateur n'est pas dans le client : écart, rien n'est importé. Relever l'infobulle en jeu.

## Familiers du Chasseur

<a id="fam1"></a>
### FAM1

- CH0 (2026-10-01, modifiée le 2026-10-02) : **marge d'apprivoisement** (registre L13, découpée de L1 le 2026-10-02) : absente du client (`SpellTargetRestrictions` de Tame Beast sans borne de niveau). Notes de développement officielles du 24/09/2026 révisées le 01/10 (<https://us.forums.blizzard.com/en/wow/t/2360696>, Hunter > Pets) : Tame Beast refusé sur une bête de niveau supérieur au Chasseur. `pet_rules.json` passe à 0 niveau, `probable` (révision 6 ; remplace le relevé de joueurs, +2). Test : tenter d'apprivoiser une bête d'un niveau au-dessus du Chasseur (refus attendu), puis une de son niveau.

<a id="fam2"></a>
### FAM2

- CH0 (2026-10-01) : **gain des points d'entraînement** (L5, `null`) : aucune source ; les instantanés de ForeverLogger (points totaux et dépensés) le mesureront niveau après niveau.

<a id="fam3"></a>
### FAM3

- CH0 (2026-10-01) : **sens de la colonne `SkillLineAbility.Field_5_5_4_67090_014_1`** (L4, lue comme coût en points d'entraînement, `probable`) : non nulle seulement sur les lignes de familier, croissante pour Bite, mais constante pour Dismember et **nulle** pour 17 paires (famille, capacité) dont Dash chez le Crocilisk et les capacités nouvelles (Swipe, Pinch, Web…) ; 0 veut-il dire gratuit, inné ou non enseignable ? À trancher par le relevé de la fenêtre Beast Training.

<a id="fam4"></a>
### FAM4

- CH0 (2026-10-01) : **niveau requis d'un rang** appliqué au familier (règle de Classic, `pet_rules.json`, `manuel`) : à confirmer par le relevé de la fenêtre Beast Training.

<a id="fam5"></a>
### FAM5

- CH0 (2026-10-01) : **deux lignes « Pet - Bat »** (une seule visée par `CreatureFamily`) et **Core Hound** (ligne de familier du Chasseur, `PetTalentType` non nul, absente de Forever Bestiary) : la seconde ligne sert-elle, et le Core Hound est-il apprivoisable sur Forever ? Une entrée du client jamais vue en jeu reste marquée comme telle. Test : tenter d'apprivoiser un Core Hound au niveau requis ; tant que personne ne l'a vu en jeu, l'entrée reste marquée « jamais vue en jeu ».

<a id="fam6"></a>
### FAM6

- CH0 (2026-10-01) : **marques `t` de Forever Bestiary** : `p` (« beta »), `b` (« ? », jamais expliqué par l'addon) ; sens supposé, à demander à l'auteur ou à vérifier en jeu.

<a id="fam7"></a>
### FAM7

- CH0 (2026-10-01) : **effets de « Hunter Pet Scaling »** (`pets.json` `pet_scaling`) : types d'aura nommés, points de base presque tous nuls : valeurs calculées par le serveur ; l'héritage reste un relevé de joueurs (L10).

## Legacy et API

<a id="leg1"></a>
### LEG1

- Legacy (LG1, LG2) : noms des arbres (sources communautaires divergentes, `docs/research/architecture-agent.md`), état du système en bêta et au lancement (registre G5 : bonus « Talented » non actif en bêta), tables du client qui le décrivent, API d'addon qui expose la progression. Problèmes connus officiels (<https://us.forums.blizzard.com/en/wow/t/2352687>, lus le 2026-10-02) : le système Legacy s'ouvre par erreur avant le niveau 25 : signal d'un déblocage au niveau 25 (pas une valeur). Défis, rangs, réputations et perks : rien dans les sujets officiels lus.

<a id="leg2"></a>
### LEG2

- API Blizzard (EC1, élargie par la décision 126) : couverture de Forever après le lancement du 4 novembre (produit, espace de noms, hôtel des ventes par royaume ou région, profils de personnages avec équipement et talents, honneur, rang et classements PvP). Auctionator sur Forever : fonctionnement et format de sa base de prix dans les SavedVariables (format relevé le 2026-09-28, `tasks/inventaire-addons.md`, `probable`).
