# Questions ouvertes

Inconnues du jeu de Forever, rangées par domaine. Pour chacune : la question, le test qui la tranche et sa priorité.
Le détail technique (valeurs relevées, tables, historique) est dans les rapports de `docs/research/` cités en lien,
en particulier [questions-ouvertes-detail.md](research/questions-ouvertes-detail.md) (texte d'origine de chaque
question, par identifiant). **Questions résolues** : [RESOLVED_QUESTIONS.md](RESOLVED_QUESTIONS.md), avec leur date,
leur réponse et leur source. Choix du modèle (poids, paramètres, départage, plugin) :
[modeling-decisions.md](modeling-decisions.md).

Priorité : **haute** = fausse aujourd'hui un résultat des outils ou bloque la prochaine tranche (T08c, FA1, PV2) ;
**moyenne** = touche un résultat chiffré, avec une variante, une option ou une borne déjà en place ; **basse** =
précision, outil ou après le lancement. Une question tranchée part dans `RESOLVED_QUESTIONS.md` avec sa source
primaire. Notes officielles citées : [24/09](research/notes-blizzard-2026-09-24.md),
[01/10](research/notes-blizzard-2026-10-01.md) (message n° 4, révision 4) et
[08/10](research/notes-blizzard-2026-10-08.md) (message n° 5, révision 1).

## Temps, incantation et canalisation
- **TPS1 — Forever regroupe-t-il les actions du serveur sur une grille de temps ?** Test : 50 sorts instantanés
  enchaînés (protocole B1 de `docs/ADDON.md`), intervalles groupés ou non. Priorité : basse. Registre B5.
  [Détail](research/questions-ouvertes-detail.md#tps1)
- **TPS2 — Le recul d'incantation vaut-il 0,5 s par coup, sans limite de nombre ?** Test : Frostbolt incanté sous
  les coups d'un monstre de mêlée, écart entre début et fin d'incantation selon le nombre de coups. Priorité :
  moyenne. Registre B6. [Détail](research/questions-ouvertes-detail.md#tps2)
- **TPS3 — Le recul raccourcit-il une canalisation (Arcane Missiles), comme en Classic ?** Test : fins de
  canalisation sous les coups, une fois corrigé le bug reconnu du projectile à pleins dégâts. Priorité : basse.
  Registre B6, I1. [Détail](research/questions-ouvertes-detail.md#tps3)
- **TPS4 — Pourquoi des durées d'incantation et des intervalles plus courts que les tables (horodatage, file
  d'attente des sorts) ?** Test : campagne B1 dédiée avec ForeverLogger. Priorité : basse. Registre B1, B3.
  [Détail](research/questions-ouvertes-detail.md#tps4)

## Sorts et dégâts du Mage
- **MAG1 — E2 : quelle formule suit la pénalité des rangs très inférieurs au niveau ?** *Modifiée le 2026-10-02* :
  l'existence de la pénalité est confirmée par la note officielle du 01/10 (fiche du personnage : un rang très
  inférieur au niveau profite moins de la puissance des sorts ; <https://us.forums.blizzard.com/en/wow/t/2360696/4>,
  révision 4), la formule n'y est pas ; le moteur garde la règle Classic par défaut. Test E2 : Frostbolt rang 1 à
  deux puissances des sorts éloignées, la pente des dégâts donne la réduction (protocole E2 de `docs/ADDON.md`).
  Priorité : haute. Registre G4. [Détail](research/questions-ouvertes-detail.md#mag1)
- **MAG2 — Quelle loi réduit la chance de déclenchement des effets de classe et de talents pour un rang bas ?**
  *Nouvelle le 2026-10-02* : même note officielle (exemples Frostbite et Omen of Clarity ; Frostbolt rang 1 au niveau
  60 ne déclenche jamais Frostbite) ; aucune table du client ne la porte. Test : au même niveau, Frostbolt rang 1
  contre le rang le plus haut, comptes de Frostbite, Winter's Chill et Fingers of Frost dans le journal. Priorité :
  basse (le moteur prend toujours le rang le plus haut) ; moyenne dès qu'une rotation descend de rang (T05b, AN1).
  Registre B20. [Note du 01/10](research/notes-blizzard-2026-10-01.md)
- **MAG3 — Givre-feu (Frostfire Bolt) profite-t-il des talents des deux écoles (Ice Shards pour le critique, Fire
  Vulnerability) ?** *Modifiée le 2026-10-02* : Fire Vulnerability ne fait plus de second jet de résistance (note du
  01/10 ; bit « ne peut pas rater » ajouté au sort 22959 dans 1.60.1.70170) ; la question des écoles reste entière.
  Test : critiques de Frostfire Bolt avec Ice Shards, puis Frostfire Bolt sous cumuls de Fire Vulnerability contre
  sans. Priorité : moyenne. Registre A20. [Détail](research/questions-ouvertes-detail.md#mag3)
- **MAG4 — E4 : Ice Lance a-t-il vraiment un coefficient de puissance des sorts nul ?** Test E4 de `docs/ADDON.md`.
  Priorité : moyenne. Registre G4. [Détail](research/questions-ouvertes-detail.md#mag4)
- **MAG5 — E3 : quelle puissance des sorts porte chaque tic des DoT (Pyroblast) ?** Test E3 de `docs/ADDON.md`.
  Priorité : moyenne. Registre A17. [Détail](research/questions-ouvertes-detail.md#mag5)
- **MAG6 — Quel est le multiplicateur de critique des sorts, et quels tics de DoT peuvent être critiques ?**
  *Modifiée le 2026-10-02* : piste du client 1.60.1.70170, le bit « effets périodiques critiques » (`Attributes_8`,
  sens communautaire, probable) que la note du 01/10 ajoute à Devouring Plague et Hellfire est posé sur Fireball,
  Pyroblast et Frostfire Bolt, pas sur Flamestrike ni Ignite ; rien n'est changé dans les données. Test : session de
  Mage, critiques de Frostbolt et de Fireball, tics de Pyroblast, de Flamestrike et d'Ignite. Priorité : moyenne.
  Registre A5, A17. [Détail](research/questions-ouvertes-detail.md#mag6)
- **MAG7 — E6 : deux bonus de dégâts en pourcentage se multiplient-ils ou s'additionnent-ils ?** Test : journaux
  (E6). Priorité : moyenne. Registre A20. [Détail](research/questions-ouvertes-detail.md#mag7)
- **MAG8 — E7 : le jeu arrondit-il ou tronque-t-il les bornes de dégâts ?** Test : dégâts minimum et maximum d'un
  sort à puissance des sorts connue (protocole E7). Priorité : basse. Registre G7.
  [Détail](research/questions-ouvertes-detail.md#mag8)
- **MAG9 — Le coefficient de Blizzard est-il celui du sort déclenché ou celui de l'effet factice du parent ?** Test :
  un tic de Blizzard à deux puissances des sorts. Priorité : basse. Registre G4.
  [Détail](research/questions-ouvertes-detail.md#mag9)
- **MAG10 — Ignite est-il roulant (reste reporté) dans Forever ?** Test : deux critiques de feu rapprochés, montant
  et intervalle des tics de l'aura 412538 (`forever measures refresh`). Priorité : moyenne. Registre A18.
  [Détail](research/questions-ouvertes-detail.md#mag10)
- **MAG11 — Le coût d'Arcane Blast croît-il de façon additive, et Clearcasting garde-t-il le cumul ?** Test : coûts
  relevés lancer par lancer (journal, bloc avancé). Priorité : moyenne. Registre B11.
  [Détail](research/questions-ouvertes-detail.md#mag11)
- **MAG12 — La hausse de coût d'Arcane Power se multiplie-t-elle au coût d'Arcane Blast, et vaut-elle au début ou à
  la fin de l'incantation ?** Test : Arcane Blast à 3 cumuls sous Arcane Power ; Frostbolt commencé 1 s avant la fin
  de l'aura. Priorité : basse. Registre B15. [Détail](research/questions-ouvertes-detail.md#mag12)
- **MAG13 — Les cumuls de Heating Up (ex-Hot Streak) passent-ils d'un combat au suivant, et un critique de Fire
  Blast compte-t-il ?** Test : journal de leveling Feu, cumuls relevés au début du combat suivant. Priorité : basse.
  Registre B15. [Détail](research/questions-ouvertes-detail.md#mag13)
- **MAG14 — Arcane Meditation et Mage Armor se cumulent-elles, et que valent la durée et le ralenti d'Ice Armor ?**
  Test : mana regagnée en incantation avec les deux (protocole B7) ; valeurs d'Ice Armor lues dans le client ou
  mesurées. Priorité : moyenne. Registre B7, C5. [Détail](research/questions-ouvertes-detail.md#mag14)
- **MAG15 — Quelles résistances ont les monstres de Forever (effet d'Arcane Subtlety, part d'Improved
  Flamestrike) ?** Test : résistances partielles relevées dans le journal. Priorité : basse. Registre H2, B19.
  [Détail](research/questions-ouvertes-detail.md#mag15)
- **MAG16 — Transfert (Blink) se lance-t-il sous étourdissement ?** Test en jeu. Priorité : basse.
  [Détail](research/questions-ouvertes-detail.md#mag16)
- **MAG17 — Que sont les doublons de Fire Blast 400616 à 400623 (`AcquireMethod` 3) ?** Test : lecture de
  `SkillLineAbility` et du livre des sorts en jeu. Priorité : basse. Registre G4.
  [Détail](research/questions-ouvertes-detail.md#mag1)
- **MAG18 — Les dégâts d'un rang suivent-ils le niveau du personnage jusqu'à `MaxLevel` ?** Test : journal de
  leveling avec ForeverLogger, même rang à plusieurs niveaux. Priorité : moyenne. Registre G7.
  [Détail](research/questions-ouvertes-detail.md#mag18)
- **MAG9 — Pourquoi l'optimiseur analytique retient-il au leveling 20 (1.60.1.70291) un build Feu que le Monte Carlo bat ?** Ajoutée le 2026-10-09 : au préréglage rapide du pont, depuis un Mage Givre de niveau 19, le build Feu retenu est plus lent que le build Givre projeté au Monte Carlo apparié (`respec.versus_optimal`, décision 217) ; au préréglage complet du rejeu, Feu et alternative sont à égalité et le build est instable. Écart analytique / Monte Carlo propre aux rangs bas lissés ? Test : comparer analytique et Monte Carlo cas par cas au niveau 20 (I6), puis un relevé en jeu de temps par monstre. Priorité : moyenne. Registre I5, I6.

## Personnage et ratios du client
- **PER1 — Où sont la critique de base des sorts et la mana par point d'Intelligence ?** Test : `GetSpellCritChance`
  et `UnitPowerMax` à Intelligence connue (ForeverLogger). Priorité : moyenne. Registre A5, B9.
  [Détail](research/questions-ouvertes-detail.md#per1), [audit](research/audit-mises-a-jour.md)
- **PER2 — Que portent les colonnes sans nom de `PlayerExpectedStat` (005 lue comme PV par Endurance, 006 ?) ?**
  Test : `UnitHealthMax` à deux valeurs d'Endurance. Priorité : basse. Registre G2.
  [Détail](research/questions-ouvertes-detail.md#per2)
- **PER3 — Les courbes `GlobalCurve` 29 à 32 portent-elles la régénération de mana par l'Esprit ?** Test : mana
  regagnée hors de la règle des 5 secondes, Esprit connu. Priorité : moyenne. Registre B7.
  [Détail](research/questions-ouvertes-detail.md#per3)
- **PER4 — Comment le serveur combine-t-il les courbes 27 et 28 de régénération de PV par l'Esprit ?** Test :
  régénération hors combat d'un Chasseur et d'une autre classe. Priorité : basse.
  [Détail](research/questions-ouvertes-detail.md#per4)
- **PER5 — `ExpectedStat.PlayerHealth` et `PlayerMana` servent-ils au joueur ?** Test : comparaison à `UnitHealthMax`
  et `UnitPowerMax` à plusieurs niveaux. Priorité : basse. [Détail](research/questions-ouvertes-detail.md#per5)
- **PER6 — Le modèle de personnage du seed doit-il garder les termes tardifs d'Intelligence et d'Esprit de `fm.py` ?**
  Test : fiches de personnages réels (mode seed seulement). Priorité : basse. Registre G2.
  [Détail](research/questions-ouvertes-detail.md#per6)
- **PER7 — La « Critical Strike » de la fiche (EllesmereUI) est-elle la critique de mêlée ?** Test : infobulle de la
  fiche du jeu de base. Priorité : basse. [Détail](research/questions-ouvertes-detail.md#per7)

## Monstres et rencontres
- **MON1 — Que valent les PV des monstres normaux au-delà du niveau 22 ?** La correction Questie vers Forever repose
  sur les niveaux 1 à 22 et le plafond de la bêta est 30. Test : journaux de leveling des niveaux 22 à 30 hors des
  zones déjà mesurées. Priorité : haute. Registre H11. [Détail](research/questions-ouvertes-detail.md#mon1),
  [révision 2](research/data-1.60.1.70170-r2.md)
- **MON6 — Quelle méthode d'ajustement pour la correction Questie → Forever ?** Ajoutée le 2026-10-06 (T08d,
  révision 5 de 70170). La droite des moindres carrés donne le même poids à chaque niveau, qu'il compte 11 PNJ ou un
  seul, et le haut de la plage décide de la pente : en r5, garder ou écarter un seul PNJ nommé la fait varier de
  0,0261 (Muglash gardé, seul point du niveau 25) à 0,0323 (Sarilus Foulborne gardé) autour de 0,0299 ; au niveau 60,
  les PV extrapolés (suppose) vont de 7 047 à 9 023 dans l'intervalle à 95 %. Une pondération par le nombre de PNJ ne
  stabilise pas la pente (amplitude au retrait d'un PNJ inchangée en r5, plus forte en r4) ; Theil-Sen pondéré la
  stabilise (0,0248 en r4, 0,0251 en r5) : **retenu le 2026-10-06 (décision 190, révision 6)**. Reste ouverte la
  validité de l'extrapolation au-delà du niveau 24 (MON1) et la bande d'incertitude :
  [modeling-decisions.md](modeling-decisions.md#correction-questie). Test : comparaison des méthodes sur chaque
  nouvelle mesure, puis journaux des niveaux 25 à 30 (MON1). Priorité : haute. Registre H11.
- **MON2 — Les PNJ au-dessus de la valeur de leur niveau (ours, PNJ renforcés, Sarilus Foulborne) suivent-ils une
  règle commune ?** Test : d'autres ours et PNJ des mêmes familles à niveau connu. Priorité : moyenne. Registre H11.
  [Détail](research/questions-ouvertes-detail.md#mon2)
- **MON3 — Quelles tables d'armure et de PV des monstres le serveur applique-t-il ?** Test : réduction d'un coup de
  monstre de niveau connu sur une armure connue ; PV mesurés comparés à `ExpectedStat` et `npctotalhp`. Priorité :
  moyenne. Registre H2, H11. [Détail](research/questions-ouvertes-detail.md#mon3)
- **MON4 — Le raté des sorts selon l'écart de niveau (A3) et le niveau d'un boss (H1) suivent-ils Classic ?** Test :
  sorts sur des cibles de niveau égal ou supérieur ; boss lu dans le bloc avancé. Priorité : moyenne. Registre A3,
  H1. [Détail](research/questions-ouvertes-detail.md#mon4)
- **MON5 — Un boss de donjon de Forever peut-il être gelé (Frost Nova, Frostbite) ?** Test : journal de donjon,
  aura de gel posée ou immunité. Priorité : moyenne (DJ1). Registre H3, H5.
  [Détail](research/questions-ouvertes-detail.md#mon5)

## Données du client et correctifs du serveur
- **DON1 — Quelles valeurs les correctifs du serveur changent-ils ?** *Répondue pour les tables décodées le
  2026-10-05 (T08c)* : `forever hotfixes --values` montre chaque valeur, avant et après ; `forever decode --hotfixes`
  les applique (poussées 112323, 112347, 112349 de 1.60.1.70170 : 175 enregistrements, refonte du Guerrier
  comprise). Restent hors des données : tables non décodées (`Curve`, `TraitNodeGroupXTraitNode`, `SpellScript`…).
  Priorité : basse. [Détail](research/questions-ouvertes-detail.md#don1),
  [note du 01/10](research/notes-blizzard-2026-10-01.md)
- **DON2 — Que veut dire `VALIDATION_RESULT_INVALID` dans `Hotfix.log` ?** *Répondue en partie le 2026-10-05
  (T08c)* : les entrées `INVALID` de `DBCache.bin` n'ont aucune donnée (taille 0) ; la valeur du build est gardée.
  Le sens de l'invalidation (refus du client, enregistrement absent) reste non établi. Priorité : basse. [Détail](research/questions-ouvertes-detail.md#don1)
- **DON3 — Que changent les milliers d'enregistrements `Item` corrigés par le serveur ?** *Modifiée le 2026-10-05
  (T08c)* : ce ne sont pas des poussées mais des réponses d'objets à la demande (DON12) et des réponses `DBReply`
  « absent » ; aucune ne touche un bijou PvP de `pvp_items.json`. Test : lecture des tables d'objets (T10).
  Priorité : basse.
  [Détail](research/questions-ouvertes-detail.md#don3)
- **DON4 — Quel produit TACT au lancement (`wow_classic_forever` ?) ?** Test : `.build.info` après le lancement du
  4 novembre. Priorité : basse. [Détail](research/questions-ouvertes-detail.md#don4)
- **DON6 — Quelles tables portent les pièges, totems et portails ?** Test : inventaire des tables `GameObjects` et
  `Creature*`. Priorité : basse. [Détail](research/questions-ouvertes-detail.md#don6)
- **DON7 — Que disent les conditions d'emploi des sorts (posture, forme, camouflage) et les durées à points de
  combo ?** Test : décodage de `SpellShapeshift` et `SpellAuraRestrictions` avant PV2. Priorité : moyenne. Registre
  K2, K3. [Détail](research/questions-ouvertes-detail.md#don7)
- **DON8 — Que valent les variables d'infobulle `$a` et `$x` (rayon, nombre de cibles) ?** Test : prise en charge
  dans `forever/pipeline/tooltip.py`, textes comparés au jeu. Priorité : basse.
  [Détail](research/questions-ouvertes-detail.md#don8)
- **DON9 — Quelles tables du client décrivent donjons, métiers, réputations et prix ?** *Modifiée le 2026-10-02* :
  la note du 01/10 annonce les donjons ouverts et leurs niveaux d'accès (à reprendre en DJ1). Test : inventaire au
  plan de chaque tranche (DJ1, MT1, RP1, T10). Priorité : basse. [Détail](research/questions-ouvertes-detail.md#don9)
- **DON10 — Que veut dire le premier champ des entrées de `DBCache.bin` (70 sur tout le fichier : région ?) ?**
  Ajoutée le 2026-10-05 (T08c). Test : `DBCache.bin` d'un autre compte ou d'une autre région. Priorité : basse.
- **DON11 — Une réponse `DBReply` « absent » peut-elle viser un enregistrement présent dans les fichiers du build ?**
  Ajoutée le 2026-10-05 (T08c). `Spell` 15147 est absent du CSV de 70170 (cohérent) ; les `ItemSparse` concernés
  restent à recouper. Test : réponses `DBReply` recoupées avec les CSV du build. Priorité : basse.
- **DON12 — À quoi servent les réponses d'objets de `DBCache.bin` (poussée = identifiant unique ≥ 0x01000000) ?**
  Ajoutée le 2026-10-05 (T08c) : 4 508 objets (`Item`, `ItemSparse`, `ItemSearchName` `VALID`, tables d'artisanat
  `INVALID`), déjà journalisées sous le build 70124 : elles ne viennent pas forcément du build de l'en-tête. Jamais
  appliquées. Test : comparaison des enregistrements `ItemSparse` envoyés avec le CSV du build (T10). Priorité : basse.
- **DON14 — Quand le client écrit-il `DBCache.bin` ?** Ajoutée le 2026-10-06 (T08d) : à la connexion, à la
  fermeture, à la réception d'une poussée ? Le fichier a été remplacé une minute après le lancement de 70235, puis de
  nouveau à 08:16 UTC le même matin (29 283 puis 30 284 entrées). Test : dates de `DBCache.bin` et de
  `DBCache.bin<pid>.tmp` relevées par l'archivage sur plusieurs sessions. Priorité : moyenne (archivage).
- **DON15 — Les tables de wago de 1.60.1.70235 sont-elles un vrai export de ce build ?** Ajoutée le 2026-10-06
  (T08d) : 46 des 47 CSV enUS sont identiques octet pour octet à ceux de 70170 ; seul l'en-tête de
  `PlayerExpectedStat` change (`HPPerStamina`). Si le build 70235 du client diffère, rien ne le montre. Test :
  comparer une table au `DBCache.bin` (enregistrements non poussés) ou au fichier CASC du client. Priorité : moyenne.
- **DON16 — Quelle table porte le hachage `0xc842493a` (poussée 112426, `DBCache.bin` de 70235) ?** Ajoutée le
  2026-10-06 (T08d) : aucun des noms Trait* essayés ; les autres tables de la poussée sont résolues. Test : hachage
  de tous les noms de WoWDBDefs. Priorité : basse.

## Journaux, addons et sauvegardes
- **LOG1 — Que portent les champs inconnus du bloc avancé du journal (dont le dernier pour un joueur) ?** Test :
  comparaison au niveau de `ForeverLoggerDB` (`forever logs measure --addon-sv`). Priorité : basse.
  [Détail](research/questions-ouvertes-detail.md#log1)
- **LOG2 — Pourquoi `amount` et `base_amount` diffèrent-ils parfois d'une unité, et dans quel ordre sont les trois
  derniers champs des dégâts ?** Test : coups critiques, glancing et écrasants identifiés dans un journal. Priorité :
  basse. [Détail](research/questions-ouvertes-detail.md#log2)
- **LOG3 — Les mesures du journal restent-elles justes avec des sorts hors recharge globale, des incantations
  interrompues ou un gain de niveau en cours de journal ?** Test : filtre par `SpellCooldowns.StartRecoveryTime`
  avant de viser `valide-jeu`. Priorité : moyenne. Registre B1, A3. [Détail](research/questions-ouvertes-detail.md#log3)
- **LOG4 — Les API lues par ForeverLogger (talents, bonus et critique des sorts) deviennent-elles secrètes en combat
  ou en champ de bataille ?** Test : sondes `/dump` de `docs/ADDON.md` (section 7). Priorité : moyenne.
  [Détail](research/questions-ouvertes-detail.md#log4)
- **LOG5 — La classe de la cible reste-t-elle lisible, non secrète, en champ de bataille ?** Test : `/dump
  UnitClass("target")` en champ de bataille. Priorité : moyenne (avant FA1p).
  [Détail](research/questions-ouvertes-detail.md#log5)
- **LOG6 — Les SavedVariables sont-elles relues d'une session à l'autre sur la version courante ?** Observation du
  2026-10-02 : oui (probable). Test : un réglage de ForeverLogger qui survit à un redémarrage complet. Priorité :
  basse. [Détail](research/questions-ouvertes-detail.md#log6)
- **LOG7 — Les addons collecteurs (MobInfo2, KillDex) relèvent-ils PV, XP et résistances, et les PV max d'un ennemi
  sont-ils secrets hors combat ?** Test : une session hors instance, puis lecture de leurs SavedVariables. Priorité :
  basse. [Détail](research/questions-ouvertes-detail.md#log7)
- **LOG8 — Quelle est la licence amont de Questie ?** Test : CurseForge 334372 et dépôt amont, avant tout
  élargissement de la lecture. Priorité : basse. [Détail](research/questions-ouvertes-detail.md#log8)
- **LOG9 — L'époque des jours d'Auctionator (`DAY_EPOCH`) et son format de prix sont-ils bien ceux relevés ?** Test :
  une seconde date de relevé. Priorité : basse. [Détail](research/questions-ouvertes-detail.md#log9)

## Leveling, quêtes et donjons
- **LVL1 — Quel est le modèle d'XP de Forever (monstres, quêtes propres à Forever, quêtes de donjon) ?** *Modifiée le
  2026-10-02* : la note du 01/10 réduit de 50 % le bonus d'XP des quêtes de donjon au-delà de la valeur normale
  (règle du serveur, probable, registre I9). *Modifiée le 2026-10-09* : la note du 08/10 (t/2360696/5, révision 1)
  relève d'environ 20 % l'XP des monstres tués en donjon (registre I10) et calcule l'XP en groupe sur le niveau de
  chaque joueur (registre I11), règles écrites en `probable` dans `mechanics.json` de 1.60.1.70291 ; elle retouche
  aussi l'XP et le niveau de quelques quêtes (Elixir of Pain, Shadowvale et Bandarion Keep, Gelkis et Magram). Le
  modèle d'XP des monstres reste la règle Classic (`suppose`). Test : XP relevée par quête et par monstre
  (ForeverLogger) et sources de T04d (ForeverDungeonJournal, GearQuestForever, tables de quêtes). Priorité :
  moyenne. Registre I6, I9, I10, I11. [Détail](research/questions-ouvertes-detail.md#lvl1)
- **LVL2 — Les couleurs de quête de Forever sont-elles celles de Classic ?** Test : `UnitQuestTrivialLevelRange`
  relevé à chaque niveau par ForeverLogger. Priorité : basse. Registre I7.
  [Détail](research/questions-ouvertes-detail.md#lvl2)
- **LVL3 — Combien de temps dure le Well-Rested du Cozy Sleeping Bag, et comment les bonus d'XP se cumulent-ils ?**
  Ajoutée le 2026-10-07 (décision 199) : 2 h selon le client d'après foreverchanges.pro, 1 h selon des guides ; rien
  n'entre dans les données sans lecture du client. Test : `SpellDuration` du sort de l'aura dans les tables du client
  (wago), puis temps restant de l'aura relevé hors combat par ForeverLogger ; cumul : gain d'XP d'un même monstre avec
  et sans chaque bonus. Priorité : moyenne (T04f). Registre D5, D7.
  [Détail](research/questions-ouvertes-detail.md#lvl3)
- **LVL4 — Comment l'XP en groupe est-elle ajustée pour chaque joueur, et à partir de quel écart un membre de niveau
  très supérieur au monstre coupe-t-il l'XP de tout le groupe ?** Ajoutée le 2026-10-09 : la note du 08/10
  (t/2360696/5, révision 1) revient au calcul de Classic Era (niveau de chaque joueur) et garde la coupure, sans en
  donner la formule ni le seuil. Test : XP d'un même monstre relevée par ForeverLogger en groupe, écarts de niveau
  connus, puis seul. Priorité : basse (T04d). Registre I11.
- **LVL5 — Sur quelle XP s'applique la hausse d'environ 20 % des monstres de donjon (élites, boss, avant ou après le
  repos et le groupe), et quelle est sa valeur exacte ?** Ajoutée le 2026-10-09 (note du 08/10, « environ 20 % »).
  Test : XP d'un monstre de donjon relevée seul, sans repos, comparée à l'XP de base de son niveau. Priorité :
  moyenne (T04d, DJ1). Registre I10.

## PvP
- **PVP1 — Les rendements décroissants de Forever suivent-ils Classic (catégories, fenêtre, paliers, immunité,
  racines et silences, PNJ) ?** Test : mes journaux de champs de bataille (PV2). Priorité : haute (PV2). Registre K1.
  [Détail](research/questions-ouvertes-detail.md#pvp1), [protocole](research/pvp-dr-protocole.md)
- **PVP2 — Le classement des contrôles par catégorie depuis les champs du client vaut-il pour toutes les classes ?**
  *Modifiée le 2026-10-09* : la note du 08/10 donne des rendements décroissants à Entrapment, et le client 1.60.1.70291
  lui pose une catégorie (`DiminishType` 0 → 1, recopiée dans les fiches PvP) : concordance du classement par les
  champs du client sur ce sort. Test : sorts non résolus de PV1 relevés en champ de bataille. Priorité : moyenne.
  Registre K1, K2. [Détail](research/questions-ouvertes-detail.md#pvp1)
- **PVP3 — Le plafond de durée PvP s'applique-t-il aux contrôles sans catégorie (Death Coil, Blind) ?** Test : durée
  observée en champ de bataille. Priorité : moyenne. Registre K3. [Détail](research/questions-ouvertes-detail.md#pvp3)
- **PVP4 — Un bijou PvP et un racial (Will of the Forsaken) partagent-ils leur recharge ?** Test : l'un puis l'autre
  hors combat, second sort grisé ou non. Priorité : moyenne. Registre K4.
  [Détail](research/questions-ouvertes-detail.md#pvp4)
- **PVP5 — Quels champs de bataille, récompenses et règles de monde ouvert à l'ouverture ?** *Modifiée le
  2026-10-02* : la note du 01/10 relève d'environ 50 % les coûts en honneur de l'équipement PvP et des jetons et porte
  le plafond d'honneur à 25 000 (règles du serveur, probable, registre K6) ; date, liste des champs et types de
  royaume restent absents des sources officielles lues. Test : annonces officielles, puis relevé en jeu des coûts.
  *Modifiée le 2026-10-09* : la note du 08/10 corrige l'emplacement d'un point de capture à Shipwreck Cove (signal
  d'un objectif PvP, sans règle) et retire la réduction des critiques en PvP (PVP6). Priorité : moyenne.
  [Détail](research/questions-ouvertes-detail.md#pvp5)
- **PVP6 — Quel multiplicateur de critique s'applique désormais en PvP ?** Ajoutée le 2026-10-09 : la note du 08/10
  (t/2360696/5, révision 1) dit que les critiques en PvP n'ont plus d'efficacité réduite, sans donner l'ancienne
  réduction ; règle du serveur, absente des tables. Test : critiques d'un même sort sur un joueur et sur un monstre
  dans mes journaux de champ de bataille. Priorité : moyenne (PV2). Registre K7, A21.

## Autres classes
- **CLS2 — Combien de mana rend Improved Seal of Fury (`$PL`) ?** *Modifiée le 2026-10-09* : la note du 08/10
  corrige Seal of Fury, qui rendait de la mana sans le talent, et retire la menace de cette mana (bit d'attribut
  ajouté sur 1314104 dans 1.60.1.70291) ; le montant reste inconnu. Test : infobulle relevée en jeu. Priorité :
  basse. [Détail](research/questions-ouvertes-detail.md#cls2)
- **CLS4 — Quelle formule de rage des dégâts subis Forever applique-t-il ?** Ajoutée le 2026-10-09 : la note du 08/10
  (t/2360696/5, révision 1) la recalcule sur les PV attendus d'une créature (plus sur ceux du joueur), avec les
  multiplicateurs de dégâts subis (critiques, coups écrasants), sans les absorptions, équilibrée sur une armure de
  20 à 40 % selon le niveau ; ni les PV attendus ni la courbe d'armure ne sont donnés (`ExpectedStat` du client est
  une piste). Test : rage gagnée par coup subi dans un journal de Guerrier ou de Druide ours, dégâts et niveau
  connus. Priorité : basse (GU1, DR1). Registre B21.

## Familiers du Chasseur
- **FAM1 — Une bête d'un niveau au-dessus du Chasseur est-elle refusée ?** Règle de la note du 24/09 (probable,
  révision 6 de 1.60.1.70124). Test : apprivoiser une bête d'un niveau au-dessus, puis une de son niveau. Priorité :
  basse. Registre L13. [Détail](research/questions-ouvertes-detail.md#fam1)
- **FAM2 — Combien de points d'entraînement le familier gagne-t-il par niveau ?** Test : instantanés de ForeverLogger
  niveau après niveau. Priorité : moyenne. Registre L5. [Détail](research/questions-ouvertes-detail.md#fam2)
- **FAM3 — La colonne de `SkillLineAbility` lue comme coût d'entraînement est-elle ce coût (et que veut dire 0) ?**
  Test : fenêtre Beast Training relevée (dont Sonic Blast d'une chauve-souris). Priorité : moyenne. Registre L4.
  [Détail](research/questions-ouvertes-detail.md#fam3), [recoupement](research/familiers-recoupement.md)
- **FAM4 — Le niveau requis d'un rang s'applique-t-il au familier, et quelles bêtes enseignent quels rangs depuis
  le correctif ?** *Modifiée le 2026-10-02* : la note du 01/10 dit corrigées les bêtes qui enseignaient des rangs trop
  élevés pour leur niveau, après la base de Forever Bestiary installée (0.5.0, base du 2026-09-25) ; le guide le
  signale. Test : fenêtre Beast Training et capacités d'une bête apprivoisée à niveau connu. Priorité : moyenne.
  Registre L2, L3. [Détail](research/questions-ouvertes-detail.md#fam4)
- **FAM5 — La seconde ligne « Pet - Bat » sert-elle, et le Core Hound est-il apprivoisable ?** Test : tenter
  d'apprivoiser un Core Hound au niveau requis. Priorité : basse. Registre L3.
  [Détail](research/questions-ouvertes-detail.md#fam5)
- **FAM6 — Que veulent dire les marques `t` de Forever Bestiary (`p`, `b`) ?** Test : question à l'auteur ou relevé
  en jeu. Priorité : basse. [Détail](research/questions-ouvertes-detail.md#fam6)
- **FAM7 — Que le familier hérite-t-il du Chasseur (« Hunter Pet Scaling », points de base calculés par le
  serveur) ?** Test : protocole de `docs/research/familiers-protocole.md`. Priorité : moyenne. Registre L10.
  [Détail](research/questions-ouvertes-detail.md#fam7)

## Pont en jeu (P06a)
- **BR2 — La bande d'une case par pixel est-elle lue sans erreur à toutes les échelles d'interface et résolutions ?**
  Lue au pixel près à 2 560 × 1 440, échelle d'interface 0,7111, en cases de 4 pixels (sonde A) puis d'un pixel
  (sonde B du 2026-10-09). Test : une autre résolution ou échelle d'interface. Priorité : moyenne (repli à 2
  pixels prévu, reconnu par le pont).
- **BR4 — Le canal de retour par mesures de polices (wow-forever-codex) peut-il servir de vérification rapide « est-ce
  prêt ? » ?** Mesuré par eux sur Forever 1.60.1.69913 (police jamais chargée relue, déjà chargée gardée en cache
  jusqu'au redémarrage) ; dépôt sans licence, polices TrueType à générer sans dépendance. Test : sonde dédiée en
  P06b. Priorité : basse.

## Legacy et API
- **LEG1 — Comment est fait Legacy (arbres, défis, état en bêta et au lancement, tables, API d'addon) ?**
  *Modifiée le 2026-10-09* : la note du 08/10 (t/2360696/5, révision 1) accorde à tous les joueurs de la bêta le défi
  Legacy (16 points) et fixe, pendant la bêta seulement, la respécialisation Legacy la moins chère à 1 pièce
  d'argent, le coût baissant d'une respécialisation par heure (comme les talents de classe) ; écrit en `probable`
  dans `mechanics.json` de 1.60.1.70291 (`legacy.beta_grant`). Le client 70291 ajoute un sort « Legacy Reputation
  Reward » (1324722) : signal, sens non établi. Test : sources officielles, tables du client à l'inventaire de LG1.
  Priorité : moyenne. Registre G5.
  [Détail](research/questions-ouvertes-detail.md#leg1)
- **LEG2 — Que couvre l'API Blizzard pour Forever après le lancement ?** Test : `forever api probe` après le
  4 novembre. Priorité : basse. [Détail](research/questions-ouvertes-detail.md#leg2)
