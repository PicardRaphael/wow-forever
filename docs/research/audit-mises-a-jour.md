# Audit : ce qui suit seul une mise à jour du jeu ou des addons, et ce qui ne suit pas

Audit en lecture seule du 2026-10-01, sur `main` (`cd60768`), données `forever/data/1.60.1.70124/` en révision 3. Rien
n'a été modifié dans le code ni dans les données. Demande de l'utilisateur du 2026-10-01.

Méthode : lecture du code de la chaîne de données (`forever/pipeline/decode.py`, `install.py`, `diff.py`,
`refresh.py`, `forever/freshness.py`, `.github/workflows/build-watch.yml`), des fichiers de données et de leurs
métadonnées (`certainty`, `source`, `inherited_from`), du registre (`docs/MECHANICS_REGISTRY.yaml`) et de
`docs/OPEN_QUESTIONS.md` ; consultation de wago.tools et du forum de Blizzard (adresses et dates dans les sections 2
et 4). Les affirmations marquées **(vérifié)** ont été contrôlées dans le code par une lecture directe ; les autres
viennent d'un inventaire complet fait par un sous-agent et recoupé par sondage.

Les valeurs de jeu ne sont pas recopiées ici : chaque famille est désignée par son fichier et sa clé.

## Résumé

- **Se met à jour seul** à l'installation d'une nouvelle version (`forever install --new-version`) : ce qui est
  décodé des tables du client sur wago.tools, soit les rangs des sorts et des talents du Mage (`spells.json`,
  champ `ranks` seulement ; `talents.json`), les valeurs au niveau du personnage et les coefficients
  (`spell_scaling.json`), et le savoir des 9 classes (`classes.json`, `races.json`, `pvp_items.json`).
- **Ne se met pas à jour** : tout le reste, recopié de version en version avec la mention `inherited_from`. Soit
  tous les ratios du personnage (statistiques par niveau, mana de base, Intelligence par point de critique,
  régénération), les règles de combat (toucher, recharge globale, recul), l'XP, les monstres, le respec, les
  rendements décroissants, le profil PvP du Mage, les rencontres, et les champs de `spells.json` autres que les
  rangs (utilitaires, ralentis, portées, coût en pourcentage du mana de base).
- **Aucune GameTable n'est lue aujourd'hui** : la liste des tables téléchargées (`decode_rules.json`, `tables` et
  `class_tables`) ne contient aucune table `gt*`. Or le client porte plusieurs ratios dans des tables **DB2**
  (section 2), décodables par la même adresse wago.tools que les tables actuelles : l'Intelligence par point de
  critique (seulement dans `PlayerExpectedStat` : la GameTable `chancetospellcrit` est vide), la mana de base et
  l'XP par niveau (aussi présentes en GameTables). Les deux premières **diffèrent nettement des estimations du moteur en début de leveling**
  et concordent au niveau 60. La régénération de mana par l'Esprit, la critique de base et les statistiques de
  base par race restent côté serveur.
- **Trou principal** : les correctifs du serveur (hotfixes) arrivent sans nouveau build. `Logs/Hotfix.log` en montre
  déjà (CurvePoint, Curve, CreatureDifficulty, 4 386 lignes `Item`), mais ni `Hotfix.log` ni `DBCache.bin` ne sont lus
  par le code **(vérifié : aucune occurrence dans `forever/`)**. Une valeur décodée `certain` peut donc différer du
  jeu en ligne sans qu'aucun détecteur ne bouge.
- **Les addons** ne sont suivis par rien d'automatique : `forever addons status` (décision 124) n'existe pas encore
  (DJ1, T08) ; Questie est relu sur disque à chaque `forever measures refresh` et à chaque `forever lookup zones`,
  sans détection de changement de version.

## 1. Origine de chaque famille de chiffres et mise à jour à l'installation

### 1.1 La chaîne d'installation

| Étape | Ce qu'elle fait | Ce qu'elle ne fait pas |
|---|---|---|
| `forever builds` (réseau) | liste des builds `wow_classic_beta` 1.60.x sur wago.tools ; fraîcheur `fresh`, `stale`, `silent` (`forever/freshness.py`) | ne dit rien des hotfixes ni des règles du serveur |
| `build-watch.yml` (CI, quotidien) | nouvelle version → `fetch`, `decode`, `verify`, `diff`, `report`, PR `data/<version>` ; silence de 14 jours → issue | n'installe rien (voulu) ; ne couvre pas les addons (poste de l'utilisateur) |
| `forever fetch` | télécharge les tables de `decode_rules.json` : 19 tables du Mage (Trait*, CurvePoint, SkillLineAbility, Spell*, SpellPower, SpellCooldowns…) et 18 tables des classes (ChrClasses, ChrRaces, SpellCategories, Item*…) | aucune GameTable ; pas `ExpectedStat`, pas `CreatureDifficulty` |
| `forever decode` | candidate dans le cache : `talents.json`, `spells.json` (rangs, noms, identifiants), `spell_scaling.json`, `classes.json`, `races.json`, `pvp_items.json` | recopie avec `inherited_from` **(vérifié, `decode.py:28-38`)** : `mechanics.json`, `leveling.json`, `monsters.json`, `respec.json`, `pvp_rules.json`, `overrides.json`, `meta.json`, `decode_rules.json`, `_seed_racials.json` ; les champs non-rang de `spells.json` sont une copie profonde de la version précédente (`decode.py:1173`) |
| `forever install --new-version` | nouveau dossier ; `talents.json` et `spells.json` fusionnés : une valeur changée n'entre que si `confirmed_changes.json` la prévoit, sinon **refus de toute l'installation** | `spell_scaling.json` et les trois fichiers des classes sont copiés **sans contrôle de valeur** ; une révision de la même version ne rafraîchit jamais `spell_scaling.json` |
| `forever diff` / `forever report` | fichiers ajoutés ou retirés, talents (champs, rangs, valeurs d'infobulle), rangs des sorts **(vérifié, `diff.py:90-126`)** | ne compare pas les valeurs de `spell_scaling.json`, `classes.json`, `races.json`, `pvp_items.json` : un coefficient ou des points par niveau changés n'apparaissent que comme « fichier remplacé » (empreinte) |
| `forever measures refresh` | seul écrivain de `monsters.json` (PV mesurés dans les journaux, Questie en regard), après accord, pour la version installée seulement | les autres mesures (recharge globale B1, ratés A3, coûts, incantations, critiques, épisodes d'Ignite) restent dans `<cache>/measures/last.json` et n'entrent jamais dans les données ; les PNJ mesurés sous une ancienne version restent dans la table |

### 1.2 Verdict par fichier

| Fichier | Mise à jour à l'installation d'une nouvelle version |
|---|---|
| `spell_scaling.json` | **Oui**, redécodé ; remplacé sans garde-fou de valeur |
| `classes.json`, `races.json`, `pvp_items.json` | **Oui** si toutes les tables des classes sont téléchargées (sinon les trois sont recopiés) |
| `talents.json` | **Oui, sous condition** : tout écart non confirmé bloque l'installation |
| `spells.json` | **Partielle** : `ranks` sous la même condition ; tout le reste recopié |
| `monsters.json` | **Non** à l'installation ; par `forever measures refresh` (journaux, Questie) |
| `mechanics.json`, `leveling.json`, `respec.json`, `pvp_rules.json`, `overrides.json`, `meta.json`, `decode_rules.json`, `_seed_*`, `_source_gunba_mage_tree.json` | **Non**, recopiés ; leur `build` ou `game_version` interne reste 1.60.1.70009 |
| `confirmed_changes.json` | recopié ; sert de filtre à l'installation |

`overrides.json` est recopié mais **aucun module ne le lit** (son application reste à faire en T08) **(vérifié)**.

### 1.3 Par famille de chiffres

Légende de la dernière colonne : **auto** = redécodé à chaque version ; **figé** = recopié tel quel ;
**mesure** = mis à jour par les journaux, pas par la version.

| Famille | Fichier et clé | Source réelle | Certitude affichée | Mise à jour |
|---|---|---|---|---|
| Rangs des sorts : niveau, dégâts min et max, DoT, incantation, coût fixe, recharge | `spells.json` `spells.<k>.ranks` | client : SpellEffect, SpellLevels, SpellMisc, SpellCastTimes, SpellDuration, SpellPower.ManaCost, SpellCooldowns | certain | **auto**, sous condition |
| Valeurs au niveau du personnage (points par niveau, niveau maximal, variance, tics) | `spell_scaling.json` `components` | client (SpellEffect, SpellLevels) ; niveau maximal 0 remplacé par `decode_rules.levels.level_cap`, écrit à la main | certain | **auto** (le plafond écrit à la main : figé) |
| Coefficients de puissance des sorts (direct, par tic, canalisé) | `spell_scaling.json` `bonus_coefficient` | client, `SpellEffect.EffectBonusCoefficient` | certain ; Ice Lance (zéro du client) en hypothèse E4 | **auto**, sans alerte de valeur |
| Coefficients du mode seed | `mechanics.coefficient.*` | règle Classic et estimations de `fm.py` | suppose | figé |
| Pénalité des sorts de bas niveau | `mechanics.coefficient.low_level`, `low_level_default` | règle Classic, absente du client (G4) | suppose | figé |
| Talents : rangs, valeurs, palier, colonne, prérequis | `talents.json` | client : Trait*, CurvePoint, variables d'infobulle ; géométrie et variables écrites dans `decode_rules.json` | certain (FC-70124) | **auto**, sous condition |
| Règles des points de talent | `mechanics.talents.first_level`, `points_per_tier` | `fm.py`, écrit à la main | certain | figé |
| Coût en pourcentage du mana de base (Arcane Blast, Blink) | `spells.json` `mana_pct_base` | **recopié du seed**, alors que le bloc `source` du sort annonce `SpellPower.PowerCostPct` (`install.py:246`) ; la colonne n'est lue que pour `classes.json` (`decode.py:589`) **(vérifié)** | aucune propre | figé (malgré la source affichée) |
| Coût des rangs de talent sans coût publié | `mechanics.mana.talent_rank_cost` | estimation du seed (mode seed seulement) | suppose | figé |
| Recharge globale | `leveling.combat_rules.gcd` | règle Classic ; `start_recovery_ms` et `gcd_s` décodés ne servent qu'à filtrer les mesures | suppose (registre B1 : probable, `valide-journal`) | figé |
| Recharges des talents actifs | `spell_scaling.talent_cooldowns` | client, SpellCooldowns | certain | **auto** |
| Utilitaires du Mage : Blink, Evocation, Counterspell, Ice Barrier, Polymorph, protections, armures, gemmes | `spells.json` `utility.*` | seed (wowforevertalents.com, build 70009) | aucune balise | figé, **alors que `classes.json` en porte des copies décodées** (section 1.4) |
| Ralentis, gel, portées, rayon, multiplicateur sur cible gelée | `spells.json` `slow`, `slow_dur`, `freeze`, `range`, `radius`, `frozen_mult` | seed | aucune balise | figé |
| Vitesse des projectiles | `spells.json` `projectile_speed`, `mechanics.leveling.projectile_speed` | estimation (EST) | suppose | figé |
| Période des tics | `spell_scaling.json` `period_ms` ; `mechanics.leveling.dot_tick_s` (seed) | client / estimation | certain / suppose | auto / figé |
| Fire Vulnerability (cumuls, durée) | `spell_scaling.auras.fire_vulnerability` | client | certain | **auto** |
| Winter's Chill par cumul | `mechanics.crit.winters_chill_per_stack` | relevé du client 70009 recopié à la main | probable | figé (le nombre de cumuls vient du talent : auto) |
| Ignite (aura, durée, période) | `mechanics.leveling.ignite` | tables 70009 recopiées à la main | certain | **figé** : un changement du client ne serait pas vu |
| Armures du Mage (niveau, régénération en incantation, ralenti) | `spell_scaling.utility.*` | client | certain | **auto** ; `armor` et `frost_resistance` décodés mais jamais lus |
| Raciaux du moteur du Mage | `races.json` `mage_values` | client (`racial_values` de `decode_rules.json`) | certain | **auto** |
| Raciaux du mode seed | `_seed_racials.json` | foreverchanges.pro, Icy Veins | suppose | figé (voulu : copie figée) |
| Raciaux dans le profil PvP | `mechanics.pvp.profile.racial_s` | estimation (EST) | suppose | figé |
| Statistiques de base par niveau (Intelligence, Esprit, PV, armure, puissance des sorts d'équipement) | `mechanics.character.intellect`, `spirit`, `hp`, `armor`, `spell_power` | estimations de `fm.py` (aucun lien Endurance → PV) | suppose (G2) | figé |
| Mana de base, mana par Intelligence | `mechanics.character.base_mana`, `mana_from_intellect` | règle Classic | suppose (B9 : probable) | figé |
| Critique de base, Intelligence par point de critique | `mechanics.character.crit_base`, `int_per_crit` | règle Classic, interpolation linéaire estimée entre 1 et 60 | suppose (A5 : probable) | figé |
| Raté des sorts selon l'écart de niveau, plancher | `leveling.combat_rules.spell_miss_by_level_diff`, `min_miss` ; `mechanics.hit.miss_per_level_below` | règle Classic | suppose (A3) | figé |
| Multiplicateur de critique, DoT qui critiquent | `leveling.combat_rules.crit_mult_spell`, `dot_can_crit` | écrits à la main | certain | figé |
| Cumul des bonus de dégâts en pourcentage | `mechanics.damage.bonus_stacking` | vidéo communautaire | probable (A20) | figé |
| Régénération par l'Esprit | `mechanics.character.spirit_regen` | règle Classic | suppose | figé |
| Règle des 5 secondes | `leveling.combat_rules.five_second_rule` | texte **jamais lu** **(vérifié)** ; la règle passe par la part gardée en incantation | — | sans objet |
| Mage Armor, Arcane Meditation, leur cumul | aura du client + talent ; `mechanics.mana.regen_stacking` | client / règle Classic | certain / suppose (B7) | auto / figé |
| Boisson, nourriture, repos | `spells.json` `utility.conjure_water`, `conjure_food` ; `mechanics.leveling.rest_hp_regen_fraction` | valeurs Classic et estimations | PC, EST, suppose | figé |
| PV des monstres mesurés | `monsters.json` `npcs`, `hp_by_level`, `questie_correction` | journaux de combat (bloc avancé) + Questie 11.38.0 corrigé | certain (mesures), probable dans la plage mesurée, suppose au-delà | **mesure** |
| PV des monstres, mode seed | `leveling.mob_model.hp_anchors` | estimation (EST) | suppose | figé |
| Combat des monstres (coups, critique, esquive, vitesse, allonge) | `leveling.mob_model.*`, `mechanics.leveling.mob_hit_damage`, `armor_reduction` | estimations, règle Classic | suppose | figé |
| Armure et résistances des monstres | — | non modélisées (H2 `absent`) | — | sans objet |
| XP pour passer un niveau | `leveling.json` `xp_to_next.values` | courbe Classic marquée « FC », sans chemin de décodage | suppose (fichier) | figé |
| XP par monstre | `mechanics.leveling.mob_xp` | règle Classic (même niveau seulement) | suppose | figé |
| XP selon l'écart de niveau, XP de repos | `leveling.json` `mob_xp.*` | texte **jamais lu** **(vérifié)** | — | sans objet (non modélisé) |
| XP des quêtes | lu à l'exécution dans Questie (`questie.py`) | communautaire, base Classic Era | suppose | relu à chaque appel, sans détection de version |
| Couleurs de quête | `mechanics.leveling.quest_band` | Questie + règle Classic | suppose (I7) | figé |
| Respec | `respec.json`, `mechanics.respec.*` | règle Classic, observations de la bêta, estimations | PC, probable, suppose | figé |
| Mouvement en leveling | `mechanics.leveling.frost_nova_retreat_yd`, `frostbite_freeze_s`, `defaults`, `analytic` | estimations | suppose | figé |
| Rencontres de fin de partie | `mechanics.build.scenarios` | inventées pour comparer les builds | suppose | figé |
| Plafond de niveau de la bêta | `mechanics.build.beta_level_cap` ; `decode_rules.levels.level_cap` | écrit à la main | probable | figé (section 4 : le forum annonce un changement le 2026-10-01) |
| Rendements décroissants (paliers, fenêtre, plafond) | `pvp_rules.json` | Classic (vmangos, forum de 2019) | suppose (K1, K3) | figé |
| Classement PvP des sorts des 9 classes | `classes.json` | client (DiminishType, mécanique, durées) ; classement par `decode_rules.json` | valeurs certain, classement probable (K2) | **auto** |
| Bijoux PvP | `pvp_items.json` | client (Item*) | certain | **auto** (mais `Item` est surchargé par des hotfixes, section 3) |
| Profil PvP du Mage | `mechanics.pvp.profile`, `pvp.weights` | modèle du seed (EST) | suppose | figé |

### 1.4 Écarts de provenance relevés en passant

1. **Une même grandeur, deux sources.** `classes.json` porte des valeurs décodées du client pour les sorts
   utilitaires du Mage (portée, recharge, recharge globale, coût en pourcentage, Evocation, Counterspell) ; le moteur
   du Mage lit à la place les copies du seed de `spells.json` `utility`. Écart relevé, **non tranché** : Ice Barrier
   rang 1 est au niveau 40 dans `classes.json` et au niveau 20 dans `spells.json` `utility` **(vérifié)**.
2. **Valeurs `certain` qui ne suivent pas le client** parce qu'elles vivent dans des fichiers écrits à la main :
   `mechanics.leveling.ignite`, `crit_mult_spell`, `dot_can_crit`, `mechanics.talents.*`.
3. **Fichiers recopiés avec un `build` interne de 70009** : seuls `inherited_from` et `sources.json` montrent la
   lignée ; `talents.json` et `spells.json` gardent aussi l'en-tête `build` 70009 et `spells.json.source` cite encore
   wowforevertalents.com (seul le bloc `source` de chaque entrée nomme 70124).
4. **Clés de `leveling.json` jamais lues** **(vérifié)** : `player_model`, `five_second_rule`, `pushback_limit`,
   `armor_dr`, `level_resist`, `haste_rating_per_pct`, `crit_rating_per_pct`, `mob_xp` (les chiffres utilisés sont
   leurs doublons de `mechanics.json`).
5. **Asymétrie des garde-fous** : un rang de talent ou de sort changé bloque toute l'installation jusqu'à une
   décision dans `confirmed_changes.json` ; un coefficient changé dans `spell_scaling.json` passe sans alerte de
   valeur.

### 1.5 Addons

| Addon | Ce qui en dépend | Détection d'une nouvelle version |
|---|---|---|
| Questie (11.38.0 Forever-v27) | correction des PV (`monsters.json`), quêtes et zones, XP des quêtes, couleurs | aucune : relu sur disque à chaque appel, version lue dans le `.toc` et citée dans la provenance, mais aucun relevé précédent n'est comparé |
| ForeverLogger (addon du projet) | niveau, talents, observations hors combat | sans objet ; **jamais chargé en jeu à ce jour** (`docs/OPEN_QUESTIONS.md`) |
| AtlasLoot, ForeverDungeonJournal, Forever Guide, Legacy Forever, Zone Level: Forever, Auctionator | DJ1, LG1, EC1, profil | aucune : empreintes de référence notées à la main dans `tasks/inventaire-addons.md` ; `forever addons status` reste à écrire (DJ1, automatisation en T08) |

## 2. Ratios encore estimés : le client les contient-il ?

Recherche du 2026-10-01 (vers 06 h 20 UTC) sur wago.tools, build 1.60.1.70124. Faits **vérifiés** : présence
et contenu des tables ci-dessous, lus ce jour ; `PlayerExpectedStat` et `LevelExperience` relus une seconde fois
pour ce rapport. Les tables téléchargées sont restées dans le dossier temporaire de la session, rien n'est entré
dans le dépôt ni dans le cache du projet.

### 2.1 Où le client range ses ratios

- **Tables DB2** : même adresse que celle de `forever/pipeline/fetch.py`
  (`https://wago.tools/db2/<Table>/csv?build=1.60.1.70124`). Elles s'ajoutent à `decode_rules.json` sans nouveau
  format ni nouvel hôte. Les tables utiles sont `PlayerExpectedStat`, `GlobalCurve` (avec `CurvePoint`, déjà
  téléchargée), `ExpectedStat`, `LevelExperience` et `Exhaustion`.
- **GameTables (`gt`, fichiers texte à tabulations)** : `https://wago.tools/gt` répond 404. Elles se lisent fichier
  par fichier par `https://wago.tools/api/casc/<fdid>?version=<build>` ; les identifiants de fichier se trouvent
  par `https://wago.tools/files?search=gametables`. Une réponse 200 de 0 octet veut dire « absente du build »
  (témoin : `regenmpperspt` fait 0 octet sur 1.60.1.70124 et environ 10 Ko sur Classic Era 1.15.9). C'est un second
  format et une nouvelle adresse sur le même hôte, donc un nouvel accès réseau à faire accepter.
- **Forever a réécrit ses tables de statistiques** : `PlayerExpectedStat` a une disposition propre aux builds
  1.60.1.69876 à 70124 (définition WoWDBDefs, colonnes `Field_1_60_1_69876_*`), identique octet pour octet entre
  70009 et 70124. Ses valeurs pour le Mage au niveau 60 sont celles de Classic 1.12.
- **Absentes du client** : les fichiers `gametablesserver/*` ne sont jamais livrés (aucune version sur wago) :
  statistiques de base par race et classe (`pcbase*`, `racestats`), esquive et parade, bonus d'XP, mana des PNJ.

### 2.2 Ratio par ratio

| Ratio du moteur (clé, certitude) | Dans le client 1.60.1.70124 ? | Décodable | Ce que ça changerait |
|---|---|---|---|
| Intelligence par point de critique, `mechanics.character.int_per_crit` (suppose, A5 probable) : interpolation linéaire entre le niveau 1 et le niveau 60 (EST, `fm.py`) | **Oui** : `PlayerExpectedStat.SpellCritPerIntellect`, par classe et par niveau (9 classes × 123 niveaux), fraction de critique par point ; WoWDBDefs : « used by GetSpellCritChanceFromStat » | Oui, DB2 | Le niveau 60 concorde avec l'estimation. **Entre les deux, la courbe du client n'est pas linéaire** : au niveau 10, le client donne environ 7,5 Intelligence par point de critique contre environ 14 pour l'interpolation, soit presque deux fois plus de critique tirée de l'Intelligence en début de leveling (calcul de l'audit sur les lignes 871 et 921 de la table). Effet sur tout le leveling du Mage (`character.py`, `crit.py`, simulateurs), et sur l'Ignite et Hot Streak qui dépendent du critique. A5 passerait de `probable` à `certain` pour ce terme ; la question de `docs/OPEN_QUESTIONS.md` sur `int_per_crit` serait close |
| Critique de base, `mechanics.character.crit_base` (suppose) | **Non** : aucune colonne, `chancetospellcritbase` vide (0 octet) | Non | Reste `suppose`. Piste non vérifiée : une aura passive de classe dans `SpellEffect` ; sinon, mesure par `GetSpellCritChance` de ForeverLogger à Intelligence connue |
| Mana de base par niveau, `mechanics.character.base_mana` (suppose, B9 probable) : droite de 100 au niveau 1 à environ 1 215 au niveau 60 | **Oui**, deux sources concordantes : `PlayerExpectedStat.BaseMana` (DB2) et `basemp.txt` (gt) | Oui, DB2 | Le niveau 60 concorde à deux points près ; **au niveau 10, le client donne 196 contre environ 270 pour la droite** (la droite surestime le mana de début de partie d'un bon tiers). Effet sur le mana disponible, le repos et le temps par monstre en leveling, et sur les coûts en pourcentage du mana de base (Arcane Blast, Blink, B11). B9 passerait à `certain` pour ce terme ; vaut aussi pour les 9 classes (0 pour Guerrier et Voleur) |
| Mana par point d'Intelligence, `mechanics.character.mana_from_intellect` (suppose) | Non trouvé | — | Reste `suppose` ; mesurable par ForeverLogger (`UnitPowerMax` à Intelligence connue) |
| Régénération de mana par l'Esprit, `mechanics.character.spirit_regen` (suppose, G2) | **Non** : `regenmpperspt` et `octregenmp` vides sur Forever alors que Classic Era 1.15.9 les a. Les types 29 à 32 de `GlobalCurve` (constantes, sans documentation) sont des candidats **non prouvés** | Non | Reste `suppose`. Les types 29 à 32 méritent une question ouverte ; la mesure en jeu (mana regagnée hors de la règle des 5 secondes, Esprit connu) reste la voie sûre |
| Régénération de PV par l'Esprit (non modélisée ; `mechanics.leveling.rest_hp_regen_fraction` suppose) | **Oui** : `GlobalCurve` types 27 et 28, sous-type = classe (WoWDBDefs : « health regen from spirit ») | Oui, DB2 | Permettrait de remplacer la fraction de repos estimée par la régénération réelle hors combat ; la formule qui combine les deux courbes reste au serveur (`suppose`) ; le type 27 du Chasseur ne concorde pas avec Classic |
| PV par Endurance et PV de base, `mechanics.character.hp` (suppose, G2 : polynôme du niveau, sans Endurance) | **Partiel** : PV par point d'Endurance dans `hppersta.txt` et `PlayerExpectedStat` (colonne `Field_..._005`, sens probable) ; **PV de base par classe absents** (`octbasehpbyclass` vide) | Partiel | Le lien Endurance → PV deviendrait `certain`, la base resterait estimée ou mesurée (ForeverLogger, `UnitHealthMax` à Endurance connue) |
| Statistiques de base par race, classe et niveau (Intelligence, Esprit, Agilité), `mechanics.character.intellect`, `spirit`, `armor` (suppose, G2) | **Non** : fichiers serveur ; `RaceStat` présente mais vide | Non | Reste `suppose` ; seule voie : relevés de fiches de personnage (ForeverLogger, `UnitStat` par niveau) |
| Critique en mêlée par Agilité (9 classes, PV1 et classes futures) | **Oui** : `PlayerExpectedStat.CritPerAgility` | Oui, DB2 | Sert aux tranches de classe ; valeurs de Classic |
| Constante d'armure, `mechanics.leveling.armor_reduction` (suppose) : 400 + 85 × niveau | **Oui** : `ExpectedStat.ArmorConstant` (niveaux 1 à 123) suit exactement cette formule ; une seconde table, `armormitigationbylvl.txt`, donne une valeur de retail incompatible | Oui, DB2 | La formule serait confirmée par le client (`probable` : on ne sait pas laquelle des deux tables le serveur lit) |
| XP pour passer un niveau, `leveling.json` `xp_to_next` (suppose, marqué « FC ») | **Oui** : `LevelExperience.Experience` (DB2) et `xp.txt` (gt) | Oui, DB2 | **Concorde** aux niveaux relus (1, 2, 10, 30, 59) : la courbe passerait de `suppose` à `certain` et se mettrait à jour seule |
| XP par monstre de même niveau, `mechanics.leveling.mob_xp` (suppose, I6) : 45 + 5 × niveau | **Partiel** : colonne `PerKill` de `xp.txt` (gt), même formule | Oui, gt (nouveau format) | Confirme la base ; la modulation par l'écart de niveau, les monstres gris et les bonus reste au serveur |
| XP de repos (non modélisée, D7) | **Oui** : `Exhaustion` (paliers, facteur, heures en auberge et dehors) | Oui, DB2 | Rendrait possible la modélisation de l'XP de repos dans le leveling (I6, D7) ; l'accumulation exacte reste au serveur |
| Raté des sorts selon l'écart de niveau, `leveling.combat_rules.spell_miss_by_level_diff` (suppose, A3) | Non (serveur) | Non | Reste `suppose` ; mesure par les journaux (campagne A3 déjà prévue) |
| PV des monstres par niveau, `monsters.json` `hp_by_level` (suppose au-delà des niveaux mesurés, H11) | **Ambigu** : `ExpectedStat.CreatureHealth` et `npctotalhp.txt` présents mais en désaccord ; `CreatureDifficulty` sans PV | À tester | Comparer les deux tables aux PV mesurés dans les journaux (Tarides, niveaux 10 à 17) : si l'une concorde, elle remplace l'extrapolation de Questie au-delà de la plage mesurée |
| Notations (hâte, critique, toucher), `leveling.json` `combat_rules.*_rating_per_pct` (non lues) | `combatratings.txt` présente mais constante à tous les niveaux (probablement inerte) | — | Aucun changement tant que le moteur ne les lit pas |

### 2.3 Conséquences pour le projet

- **Gain possible sans nouvel accès réseau** : ajouter `PlayerExpectedStat`, `LevelExperience`, `Exhaustion`,
  `ExpectedStat` et `GlobalCurve` à `decode_rules.json`. Ces valeurs passeraient alors dans la colonne
  « auto » de la section 1.3, au lieu d'être recopiées de version en version.
- **Gain avec un nouvel accès** (accord nécessaire) : les GameTables par l'API `casc` (`xp.txt` pour `PerKill`,
  `hppersta.txt`, `basemp.txt` en recoupement).
- **Ce que ça casserait** : remplacer `int_per_crit` et `base_mana` change les résultats du leveling en mode
  forever. Les tests qui épinglent les valeurs du personnage (`tests/unit/test_engine_character.py`,
  `test_engine_values.py`, `test_engine_mechanics.py`, `test_engine_arcane_blast.py`) et la parité avec le seed
  (`tests/parity/test_fm_parity.py`) seraient touchés : le mode seed doit garder les estimations de `fm.py`
  (séparation `rules forever` / `rules seed`, comme pour les autres règles). Ce sont des tests écrits d'abord : à
  traiter dans une tranche, avec l'accord de l'utilisateur sur les tests verrouillés. Les builds de T05 seraient à
  rejouer (le critique pèse sur le choix Feu ou Givre en leveling).
- **Questions ouvertes à ajouter** (non ajoutées par cet audit, qui ne modifie rien) : sens des types 29 à 32 de
  `GlobalCurve` (régénération de mana ?) ; table d'armure et table de PV des créatures réellement lues par le
  serveur ; écart du Chasseur au type 27 ; critique de base portée par une aura passive ?

## 3. Ce qu'une mise à jour ne peut pas détecter, et les détecteurs existants

### 3.1 Ce que les données d'une nouvelle version ne montrent pas

| Catégorie | Exemples (registre) | Pourquoi invisible |
|---|---|---|
| **Correctifs du serveur sans nouveau build** | CurvePoint et Curve (rangs de talent), CreatureDifficulty (PV), 4 386 lignes `Item` le 2026-09-30 | poussés au client au démarrage (`Hotfix.log`, `DBCache.bin`) ; wago.tools publie les tables du build, pas les surcharges ; le pipeline ne lit ni l'un ni l'autre |
| Règles de toucher et de résistance | A3 (raté selon l'écart de niveau), A12 à A14 (résistances) | calculées par le serveur |
| Rythme du combat | B1 (recharge globale), B3 (file d'attente), B5 (regroupement des actions), B6 (recul) | serveur et client exécutable, pas des tables |
| Règles d'interaction des effets | A18 (Ignite : la note du 24/09 « no longer double dips » n'a changé aucune table), A20 (cumul des bonus), B15 (rafraîchissement des buffs), B7 (cumul des régénérations) | logique du serveur |
| Pénalité des sorts de bas niveau | G4, E2 | absente de la table ; règle Classic supposée appliquée par le serveur |
| Formules du personnage | G2, A5, B9 (statistiques, ratios) | côté serveur en Classic ; présence dans les GameTables de Forever traitée en section 2 |
| XP | I6, T04d (XP par monstre, selon l'écart de niveau, de repos, des quêtes) | serveur |
| Monstres | H11 (PV), H2 (armure, résistances), comportement | PV absents du client hors `CreatureDifficulty` (non lu) ; le reste au serveur |
| PvP | K1, K3, K4 (rendements décroissants, plafond, recharges partagées) | serveur |
| Ligne de vue, portée effective, hitbox | C3, C8 (la note du 24/09 sur Arcane Missiles) | serveur |
| Taux de butin, réputation, prix des entraîneurs | DJ1, RP1, MT1 | serveur |
| Bugs reconnus | liste « Known Issues » de Blizzard | à ne jamais modéliser : ne se voient pas dans les tables |

### 3.2 Détecteurs existants

| Détecteur | Ce qu'il voit | Limite |
|---|---|---|
| `forever builds`, fraîcheur, `build-watch.yml` | un nouveau build publié ; un silence de 14 jours | rien sur les hotfixes ni sur les règles |
| `forever diff` / `forever report` (PR de données) | talents et rangs des sorts changés, fichiers ajoutés ou retirés | `spell_scaling.json` et les fichiers des classes comparés par empreinte seulement |
| `client_builds.json` (`.build.info`, T08a) | quand le client local change de build ; attribue chaque session de journal à sa version | n'analyse rien en soi |
| `Logs/Hotfix.log` | **index** des surcharges (table, enregistrement, date), sans valeur | lu à la main jusqu'ici (`docs/OPEN_QUESTIONS.md`), aucun code ; valeurs dans `DBCache.bin`, non décodé (T08) |
| Journaux de combat (`forever logs measure`, `forever measures refresh`) | PV des monstres, intervalles de recharge globale (B1), ratés (A3), coûts, temps d'incantation, rapports de critique, épisodes d'Ignite comparés à la règle des données et à sa variante | seul `monsters.json` est écrit ; le reste est affiché et gardé dans le cache, sans alerte si la mesure s'écarte de la règle ; échantillons petits (J5) ; dépend du jeu de l'utilisateur |
| ForeverLogger (SavedVariables) | niveau, talents, bonus de sort et critique lus dans l'interface | jamais chargé en jeu ; APIs peut-être secrètes ; relecture des SavedVariables à vérifier sur la version courante |
| Questie et addons de données | XP des quêtes, PV Classic en regard, butin, niveaux de zone | aucune détection de version ; données Classic sans correction Forever |
| Wowhead Forever | contrôle des valeurs de sorts, alerte si divergence avec le client | consultation manuelle par le sous-agent de recherche ; aucune aspiration (conditions du site) |
| Sous-agent `forever-web-researcher` | notes de patch, annonces, guides, vidéos, à la demande | **ponctuel** : seulement quand l'utilisateur le demande ; exemple : `docs/research/notes-blizzard-2026-09-24.md` |
| Communauté (foreverchanges.pro, calculateurs, vidéos, fils de joueurs) | recoupements, signalements | `suppose` ; un fil de joueur peut précéder la note officielle (exemple : le fil de joueur 2367562 du 2026-09-30, catégorie 349, affirme qu'un changement de la rage des Guerriers sur les critiques a été annulé ; non vérifié) |

**Conclusion de la partie 3.** Un changement de règle du serveur n'est aujourd'hui vu que si l'utilisateur pense à
demander une recherche, ou si une mesure de journal s'écarte assez pour qu'il le remarque à l'affichage. Aucun
détecteur ne tourne seul sur les notes officielles ni sur les hotfixes.

## 4. Proposition : lire les notes de patch officielles dans la veille

Proposition seulement : rien n'est implémenté. C'est un **nouvel accès réseau**, qui demande l'accord de
l'utilisateur (CLAUDE.md), puis l'ajout à la liste réseau de CLAUDE.md et de `tests/unit/test_network_boundary.py`.

### 4.1 Ce que la source offre (relevé du 2026-10-01)

- Le forum de Blizzard est un Discourse dont chaque page a une version JSON publique :
  - catégorie de la bêta : <https://us.forums.blizzard.com/en/wow/c/wow-forever-beta-discussion/349.json> (HTTP 200,
    30 sujets ; sujets épinglés par le Community Manager : notes de développement, problèmes connus, maintenances) ;
  - catégorie générale de Forever : catégorie 347, « World of Warcraft: Forever General Discussion », sous-catégorie
    de 346 « WoW: Forever » (les « Class Deep Dives » des classes y paraissent le 2026-09-30) ;
  - un sujet : <https://us.forums.blizzard.com/en/wow/t/2360696.json> (notes du 24/09) : titre, `created_at`,
    `last_posted_at`, et pour chaque message `username`, `user_title` (« Community Manager »), `created_at`,
    `updated_at`, `version` (nombre de révisions) et le texte HTML (`cooked`).
- **Les notes sont révisées en place** : le sujet « WoW Forever Beta Known Issues » a été créé le 2026-09-17 et
  modifié le 2026-09-24 (`version` 4). Surveiller les nouveaux sujets ne suffit pas : il faut comparer
  `updated_at` et `version` du premier message.
- `robots.txt` (lu le 2026-10-01) **autorise** `/en/wow/t/<id>.json` et `/en/wow/c/<slug>/<id>.json`, **interdit**
  les `.rss` des sujets et des catégories et le préfixe `/en/wow/g`, qui couvre le traqueur des messages bleus
  (`/en/wow/groups/blizzard-tracker/posts.json` répond 200 mais n'est pas permis) : le traqueur est donc exclu.
- Exemple de ce que la veille aurait signalé aujourd'hui : le sujet « Beta Update Maintenance - October 1 »
  (2367661, Community Manager, 2026-10-01) annonce un nouveau build avec un plafond de niveau relevé et des notes
  détaillées « tomorrow ». Le plafond de niveau vit dans `mechanics.build.beta_level_cap` (probable) et
  `decode_rules.levels.level_cap`, tous deux écrits à la main et **figés** à l'installation (section 1.3).

### 4.2 Détecteur proposé

- **Code** : `forever/pipeline/notes.py` (accès par `Deps.http_get`, comme `builds`), commande
  `forever notes [--since <date>]`, outil MCP en option. Une requête par catégorie suivie, puis une par sujet
  nouveau ou révisé ; une fois par jour au plus ; identifiant de client explicite.
- **Filtre** : sujets épinglés ou dont le premier message vient d'un `user_title` de Blizzard (Community Manager…)
  dans les catégories 349 et 347 (et la catégorie du jeu au lancement du 4 novembre, à ajouter quand elle existera).
- **État** : dernier `(topic_id, updated_at, version)` vu, dans le cache hors du dépôt (comme la fraîcheur).
- **Sortie** : pour chaque note nouvelle ou révisée : adresse, date, auteur, différence de texte depuis la dernière
  lecture, et une **liste des entités du projet nommées** dans le texte (noms anglais des sorts et talents de
  `spells.json`, `talents.json`, `classes.json` ; noms des classes ; mots-clés reliés aux entrées du registre :
  « Ignite » → A18, « diminishing returns » → K1, « level cap » → `beta_level_cap`, « experience » → I6…).
- **Dans la CI** : une étape de `build-watch.yml` qui ouvre ou met à jour une issue `veille` « notes officielles »
  avec ce rapport. **Rien n'entre dans `forever/data/`** : la note est un signal qui déclenche une vérification
  (diff du client, mesure de journal, question dans `docs/OPEN_QUESTIONS.md`), comme la note du 24/09 dans
  `docs/research/notes-blizzard-2026-09-24.md`.
- **Liens avec les règles du projet** :
  - le sujet « Known Issues » **est** la liste des bugs reconnus par Blizzard : la veille l'y relit pour que le
    projet ne modélise jamais un bug reconnu (CLAUDE.md) ;
  - une note qui touche une règle du serveur (section 3.1) ouvre la question correspondante et propose le
    protocole de mesure (`docs/ADDON.md`) ;
  - une note qui annonce un changement de table est recoupée avec le `forever diff` du build suivant
    (concordance ou écart, comme le tableau des notes du 24/09).
- **Tests** : fixtures JSON du forum dans `tests/fixtures/` (aucun réseau dans les tests) : nouveau sujet, sujet
  révisé (`version` qui monte), message non officiel ignoré, entités reconnues.

### 4.3 Décisions qui reviennent à l'utilisateur

1. Accord pour ce nouvel accès réseau (`us.forums.blizzard.com`, JSON seulement), et lecture des conditions
   d'utilisation de Blizzard au-delà de `robots.txt`.
2. Rang de la source dans la hiérarchie de `docs/DATA_SOURCES.md` : une note officielle n'y figure pas. Proposition :
   signal qui ne change jamais une valeur, mais qui peut faire passer une règle du serveur sans autre source de
   `suppose` à `probable` (texte officiel), la mesure en jeu restant seule à donner `certain`.
3. Autres sources officielles à ajouter au lancement : page des actualités et des correctifs de
   worldofwarcraft.blizzard.com, forum européen ou français si les notes y diffèrent.
4. Tranche d'accueil : T08 (veille) semble la bonne place, à côté de `Hotfix.log` et `DBCache.bin`.
