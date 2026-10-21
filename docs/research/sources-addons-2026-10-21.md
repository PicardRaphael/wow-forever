# Sources des addons installés : ce que chacun fournit, pour les 9 classes (relevé du 2026-10-21)

Relevé demandé pour la décision 288 (« lire et alimenter ce qui existe ») : inventaire vérifié de ce que les addons
installés fournissent déjà, de ce que `forever/` en lit, et des trous qu'aucun addon ne comble.

- **Client installé** : 1.60.1.70450 (`C:\Program Files (x86)\World of Warcraft\.build.info`, branche `us`).
- **Dossier lu** : `C:\Program Files (x86)\World of Warcraft\_classic_beta_\Interface\AddOns` (abrégé `AddOns\`) et
  `C:\Program Files (x86)\World of Warcraft\_classic_beta_\WTF\Account\140740490#1\SavedVariables` (abrégé `SV\`).
- **Méthode** : lecture de fichiers seulement, sans réseau, sans exécuter de Lua. Seule commande du dépôt lancée :
  `uv run forever addons status`, sans `--save`, donc sans écriture. Décision 133 respectée : seuls des structures,
  des comptes et des exemples d'une ligne figurent ici, aucune table recopiée.
- **Relevés précédents** : `tasks/inventaire-addons.md` (jusqu'au 2026-10-14) et `tasks/plan-corrections-jeu.md`
  (section « Étude de l'existant »). `docs/research/addon-forever.md` (2026-09-27) parle de la création d'un addon et
  des canaux addon ↔ programme, pas des données des addons ; rien à y corriger pour cet inventaire, sinon que sa
  recommandation « ne pas réécrire de pont » a été dépassée par P06a.

## Trois réserves à garder en tête

1. **Les SavedVariables datent toutes du 2026-10-15 à 16:59.** Elles ont été écrites par les versions précédentes :
   - Talents Forever `addon = "0.38.2"` ;
   - SkillUp `v0.9.3` ;
   - Legacy `v0.6.19` ;
   - RestedXP `release = "v4.11.23"` ;
   - Forever Guide `itemDataBuild = 70291`.

   Aucune session de jeu n'a eu lieu depuis les mises à jour des 20 et 21 octobre. Tout ce qui vient d'une
   SavedVariable reflète l'état du 15 octobre.
2. **Les dates des fichiers sont des dates d'installation**, pas de publication. Les horodatages 2026-10-20 11:05 et
   2026-10-21 08:12 sont communs à des dizaines d'addons sans rapport entre eux. La date d'une version se lit dans son
   CHANGELOG, et celle des données dans leur en-tête.
3. **Les addons ne suivent pas tous le même build du jeu.** Ceux qui ne citent aucun build ne disent rien de leur
   fraîcheur. C'est la colonne « Build ou date dans les données » ci-dessous.

## Tableau principal : besoin → addon → donnée

« Lu » renvoie au module du dépôt qui lit la donnée ; « non » veut dire qu'aucun code de `forever/` ne l'ouvre.

| Besoin | Addon (version) | Donnée | Format | Classes et spés couvertes | Build ou date dans les données | Déjà lu par forever ? |
| --- | --- | --- | --- | --- | --- | --- |
| Poids de stats au 60, par spé | Naowh Forever 1.1.38 | `AddOns\NaowhForever_BiS\StatWeights\Data\Defaults.lua` | `Spec(classe, clé, nom, rôle, {stat=poids})`, gabarits MELEE, CASTER, HEALER, TANK | 9 classes, **28 spés** | « set by hand », `StatWeightDefaultsUpdated = "5 Oct 2026"` ; README : « defaults are for level 60 », estimations en attendant WoWSims | **non** : forever écrit des lignes `NFSW1:` pour le Mage (`forever/exports/naowh.py`, `forever/gear.py:96`) mais ne lit pas les défauts |
| Échelles de stats par classe | Forever Companion 1.0.0 (affiché 0.4.2) | `AddOns\ForeverCompanion\Data\Weights.lua` | `weights[CLASSE] = {{id, label, w={StatPawn=poids}}}`, normalisé à 100 | 9 classes, **20 échelles** (voir la section) | `dataVersion=91`, `updated="2026-10-20"`, aucun build | **oui** : `forever/pipeline/gear_sources.py` `read_companion_scales`, puis `forever/gear.py:174` `companion_weights` (classement BiS hors Mage, `suppose`) |
| Poids par rôle en unités WoWSims | Forever Guide 1.37.0 | `AddOns\ForeverGuide\Gear.lua:19-56` | `CLASSE = {{key=rôle, w={Stat=poids}, sta=…}}` | 9 classes, **18 rôles** | poids WoWSims Forever (client 70205) | **non** (forever lit les statistiques des objets, pas ces poids) |
| Poids sous le 60 | GearQuest Forever 1.0.0 | `AddOns\GearQuestForever\StatWeights.generated.lua`, `ScoringWeights.generated.lua` | par classe : `levelling_1_9`, `default`, une entrée par spé ; multiplicateurs `GQ.ScoringLeveling` jusqu'au 60 | 33 spés, dont 6 sans poids propres (battlemage ×3, shockadin, enhancement_tank : repli sur `default`) | « TBC stat priority », aucun build | **non** (seuls les choix et les fiches sont lus) |
| Poids par tranche de niveau | RestedXP 4.11.26 | `AddOns\RXPGuides\DB\forever\StatWeights.lua` | 192 profils `Class, Spec, MIN_LEVEL, MAX_LEVEL, Kind, ITEM_MOD_*` | 9 classes, 16 profils, 6 tranches | **copie exacte des poids Classic**, et **inactifs sous Forever** (`ItemUpgrades.lua:6` s'arrête hors CLASSIC, TBC et CATA) | non, et inutilisable |
| Rotation ou priorité de sorts | Forever Companion | `AddOns\ForeverCompanion\Data\Rotations.lua` | `rotations[classe][spé] = {single, aoe, intro, sections={{title, lv=30, kind, steps}}}` ; étape = jetons `{t="skill", v=nom, id=spellID}` ou `{t="text"}` ; conditions en prose | **28 spés**, monocible ; AoE pour 9 spés seulement | **une seule section par spé, au niveau 30** ; aucun build | **non** |
| Builds de talents par niveau | Forever Companion | `AddOns\ForeverCompanion\Data\Talents.lua` | `talentBuilds[classe][spé] = {name, lv?, tabs={[arbre]={[index]=points}}}` ; l'addon choisit le build selon `UnitLevel` | 28 spés : 28 « Level 30 (Beta) », 28 « Leveling 1-60 », 24 « Standard Build », des variantes | aucun build ; **aucun ordre de prise** | **non** |
| Builds populaires | Talents Forever Book 0.38.9 | `AddOns\TalentsForeverBook\Data.lua`, bloc `popular` | `top = {{code="classe/60/…-7", lead=spé, pts, rank, score…}}`, plus parts de chaque spé et taux de prise par talent | 9 classes, **5 builds par classe, tous au niveau 60**, sans contexte | `build = "1.60.1.70425"`, `generated = "2026-10-17"`, `codeVersion = "7"` ; fenêtre de comptage variable selon la classe | **oui** : `forever/pipeline/talents_forever.py` `read_popular`, `forever/talents_forever.py` (`popular_builds`, `closest_popular`, toutes les classes : CLI et MCP) |
| Arbres de talents, coefficients, sorts du maître | Talents Forever Book | `Data.lua` : `classes`, `learn`, `coef` (552), `pets`, `legacy`, `renames` | voir la section | 9 classes, 466 talents | 70425 | arbres **lus** (recoupement T08d, export v6 FA1) ; `learn`, `coef`, `pets` et `legacy` **non lus** |
| Plan de talents niveau par niveau | Naowh Forever, module Training | `AddOns\NaowhForever_Training\Data\TrainingBuilds.lua` | arbres seulement (`[nodeID]={spell, rangs, rangée, colonne, slot, requis}`) | 9 classes | 70425 | **rien de livré** : `ns.TrainingBuilds[classID]` est vide. Forever **alimente** par `!NFB1!` (EX1) |
| BiS du 60 | Naowh Forever | `AddOns\NaowhForever_BiS\BiS\Data\BiS.lua` | `specs[i] = {class, key, name, updated, slots={[slotID]={itemID…}}}` et `sources[itemID]="Boss · Donjon"` | **28 spés** | `updated = "11 Oct 2026"` sur les 28 ; généré depuis wowsrc.com ; **pas mis à jour** de 1.1.15 à 1.1.38 | **oui** : `gear_sources.read_naowh_bis` (`forever/gear.py` `personal_bis`, `forever/gear_route.py`, `forever/bridge/exports.py`, `forever/bridge/gear_level.py`) |
| BiS du 60 (variante) | Forever Companion | `AddOns\ForeverCompanion\Data\Bis.lua` | `bis[Classe][Spé]["BETA"] = {{s=emplacement, i={{id}…}}}` | **28 spés**, phase unique « BETA », sans niveau | `dataVersion 91` ; contient des objets d'Alterac (2869xx) **absents chez Naowh** | **oui** : `gear_sources.read_companion_bis` (`forever/gear.py` `personal_bis`) |
| BiS par niveau (leveling) | GearQuest Forever | `AddOns\GearQuestForever_<CLASSE>\Data.<Classe>.generated.lua` et `…Early.1to9.generated.lua` | `{itemId, slot, minLevel, maxLevel, rank, spec, faction, score, suffix…}` et fiches `ItemFacts` (source, zone, PNJ, quête) | 9 classes, 33 spés, niveaux 1 à 60, deux camps ; 607 927 choix de 10 à 60 et 70 562 de 1 à 9 | **aucun build ni date** dans les `.lua` | **oui** : `gear_sources.read_gearquest_picks` et `read_gearquest_facts` (`forever/gear.py` `leveling_gear`), `quest_sources.read_gearquest` |
| Comparaison d'équipement, DPS par incantation | Forever Guide | `AddOns\ForeverGuide\GearAdvisor.lua`, `GearCalc.lua`, `GearCalcData.lua`, `GearSpellBook.lua`, `GearExplain.lua` | calcul en jeu, aucune table de résultats | 18 rôles ; GearCalc chiffre Mind Blast, Mind Flay, Smite, Lightning Bolt, Fireball (partie directe), Frostbolt, Wrath, Shadow Bolt, des soins et l'attaque automatique | `GearCalcData` « Forever beta 70009 » | **non** (calcul en jeu, rien à lire sur disque) |
| Statistiques des objets | Forever Guide | `AddOns\ForeverGuide\GearData.lua` (`ns.GEAR_DATA`) | ligne `id slot sous-classe niveauRequis qualité raid masqueClasses stats` | 9 808 objets | « build 70291 », **corrigé à 70425 au chargement** par `ItemBuild70425.lua` (291 objets modifiés, 20 retirés) | **oui**, mais **sans la correction** : `gear_sources.read_guide_gear` lit `GearData.lua` brut (voir « Constats sur le dépôt ») |
| Butin des donjons, taux | Naowh Dungeon Journal | `AddOns\NaowhForever_DungeonJournal\Data\*.lua` | par boss : `loot = {itemIDs}`, `chance = {pourcentages}` | 35 donjons | `Build.lua` 1.60.1.70450, `DATA_DATE = "16 Oct 2026"` ; taux de Wowhead Forever, wowsrc.com prioritaire | **oui** : `forever/pipeline/dungeon_sources.py` `read_naowh_journal`, plus les SavedVariables `journalRun`, `journalKills`, `journalLoot`, `instanceTrackerChars` (`read_naowh_runs`) |
| Butin des donjons, taux | Forever Companion | `AddOns\ForeverCompanion\Data\Loot.lua`, `Data\Dictionary.lua` | `{id, n, lv, new?, raid?, b={{n=boss, i={{id, d}}}}}` ; `items[id] = {n, s, st, d, f}` | 37 instances, environ 2 800 taux ; 990 objets dont 216 avec un taux | `dataVersion 91` | `Loot.lua` **lu** (`dungeon_sources.read_companion`) ; `Dictionary.lua` **non** |
| Butin des donjons, taux | Forever Guide | `DungeonLoot.lua`, `DungeonTrash.lua`, `ItemSearchData.lua` | `p=` pourcentage ; `d=npc:%` | 35 donjons ; 949 taux de boss ; 11 139 objets avec lieu | `DungeonLoot` : « Classic loot/rates from ForeverChanges », 2026-10-10, build 70291 ; plus 575 relevés de joueurs (`CommunityUpdate70425/70450.lua`, des comptes et non des taux) | `DungeonData`, `DalaranData`, `DungeonLoot`, `DungeonTrash` **lus** (`dungeon_sources.read_guide_dungeons`) ; `ItemSearchData` et `CommunityUpdate*` **non** |
| Butin et niveaux des boss | AtlasLoot Classic Forever 1.60.1 | `AddOns\AtlasLootClassic_DungeonsAndRaids\data.lua`, `droprate.lua` | `{name, npcID, Level, [NORMAL_DIFF]={{n, itemID}}}` ; `DropRateData[npc][item] = %` | 45 instances ; 4 donjons Forever remplis, 5 vides, raids Forever vides | aucun build ; taux de Classic seulement | **oui** : `dungeon_sources.read_atlasloot` |
| Butin, niveaux des boss, quêtes de donjon | ForeverDungeonJournal 1.6.5 | `AddOns\ForeverDungeonJournal\Data\Dungeons.lua`, `Bosses.lua`, `QuestRewards.lua`, `QuestChains.lua` | `{itemID, nom, emplacement, qualité}` ; `BOSS_LEVELS` en chaînes ; quêtes avec `requires`, `pickup`, `turnin`, `rewardItems` | 14 donjons, 89 boss, environ 105 quêtes | tenu à la main ; `SOURCES.txt` « checked 22 September 2026 » | **oui** : `dungeon_sources.read_fdj_dungeons`, `quest_sources.read_fdj` |
| Niveaux des zones et donjons | Zone Info: Forever 1.9.1 | `AddOns\ZoneInfoForever\…` (`mapTable`) | `[uiMapID] = {minLevel, maxLevel, minFish, dungeons={{id, text}}, …}` | 43 zones, 33 donjons | saisi à la main, aucun build ; identique à `Leatrix_Maps` | **oui** : `dungeon_sources.read_zoneinfo` |
| Parcours de leveling, gratuits | RestedXP 4.11.26 | `AddOns\RXPGuides\Guides\Forever\*.lua`, `Guides\Forever\dungeon\` | `RXPGuides.RegisterGuide([[#name … step .accept …]])` | 9 classes (filtres `<<`) ; zones de départ des deux camps et Skyborne ; **jusqu'au niveau 20 à 22** | aucun build ; CHANGELOG du 2026-10-17 | **oui** : `forever/rxp_guides.py` (rejeu et comparaison, `forever/compare.py`), livraison de nos guides (`forever/bridge/guide_addon.py`) |
| Parcours de leveling, importés (1-60) | RestedXP, cache `RXPDB` | `SV\RXPGuides.lua`, `RXPDB.profiles.global.guides["groupe\|sous-groupe\|nom\|n"]` | contenu compressé (LibDeflate) | 1 à 60 pour les deux camps, Mage AoE et ADV | état du 2026-10-15 | **non**, par choix (`forever/rxp_guides.py` : « les guides importés ne sont jamais lus », décisions 227 et 268) |
| Parcours calculés (Polestar) | non installé | clone en cache seulement | — | — | — | **non** (`forever/compare.py:825`, `forever/route_check.py:5` : « à venir », décision 278) |
| Quêtes, PNJ, chaînes, XP des quêtes | Questie 11.38.0 Forever-v27 | `AddOns\Questie\Database\Classic\*.lua`, `QuestXP\DB\xpDB-classic.lua`, `DropTables\data\classicItemDrops.lua` | tables `[[return {…}]]` décrites par `questKeys` et `npcKeys` | base **Classic Era**, aucune base Forever ; observations du joueur dans `QuestieForeverDB` (444 quêtes, dont 92 propres à Forever) | fichiers du 2026-09-21, **inchangés** | **oui** : `forever/pipeline/questie.py`, `quest_sources.py` (`read_questie_quests`, `read_questie_forever`), `forever/pipeline/monsters.py`, `profile_import.py` ; `classicItemDrops` **non** |
| Quêtes et chaînes de Forever | Naowh (DiscoveryData, JourneysData, Dungeon Journal), Forever Guide | `NaowhForever_DiscoveryData\Quests.lua`, `NaowhForever_JourneysData\QuestSpots.lua`, `NaowhForever_DungeonJournal\Data\QuestChains.lua`, `ForeverGuide\DungeonData.lua`, `ChainData.lua`, `ClassData.lua` | voir les sections | environ 5 000 quêtes chez Naowh ; 550 quêtes de donjon et 801 quêtes de classe chez Forever Guide | Naowh 70450 ; Forever Guide : sources variées | **oui** : `quest_sources.py`, sauf `ForeverGuide\ClassData.lua` (quêtes de classe), **non lu** |
| Trajets, transports, vols | Shortest Path Forever 1.21.5 | `AddOns\ShortestPathForever\Data\Taxi.lua`, `Routes.lua`, `Portals.lua`, `Zones.lua`, `Nav\*.lua` | `TaxiNodes`, `TaxiPaths` (266 durées mesurées sur 286), `Routes[id] = {kind, period, stops}` | toutes classes | **build 1.60.1.70450** (wago.tools), CMaNGOS, InFlight | **non** (`forever/addons.py:125` : « lecteur à venir ») ; les trajets viennent de Naowh Journeys (`forever/pipeline/travel_sources.py`) |
| Sorts appris par niveau (maître de classe) | Naowh Training, Forever Companion, Forever Guide, Talents Forever | `NaowhForever_Training\Data\TrainingData.lua` ; `ForeverCompanion\Data\Training.lua` ; `ForeverGuide\ClassTrainData.lua` ; `TalentsForeverBook\Data.lua` `learn` | `{niveau, spellID, coût, drapeaux}` | 9 classes | Naowh 70178 ; Forever Guide CMaNGOS Classic ; Talents Forever 70425 | Naowh **lu** (`travel_sources.read_training_levels`) ; les trois autres **non** |
| Métiers : seuils, recettes, itinéraire de montée | SkillUp Forever 0.18.6 | `AddOns\SkillUpForever\Data\Thresholds.lua`, `Recipes.lua`, `Trainer.lua`, `Sources.lua`, `Vendor.lua` | `[spellID] = {orange, jaune, vert, gris}` ; recettes avec composants ; rangs des maîtres ; parchemins avec taux par PNJ | 12 métiers de Classic, 2 347 recettes ; les métiers nouveaux de Forever sont vides | **wago.tools 1.60.1.70450, 2026-10-17** | **non** (`forever/addons.py:126` : « lecteur à venir ») |
| Métiers (autres sources) | Naowh Professions ; Forever Companion ; Forever Guide ; AtlasLoot Crafting | `NaowhForever_Professions\Data\RecipeData.lua` ; `ForeverCompanion\Data\Professions.lua` ; `ForeverGuide\ProfessionData.lua` ; `AtlasLootClassic_Crafting` | seuils jaune et gris, maîtres, rangs | 11 à 12 métiers | Naowh sans build ; Forever Guide 2026-09-25 | Naowh **lu** pour les maîtres et les rangs (`travel_sources.read_profession_data`) ; les autres **non** |
| Réputations | Naowh Dungeon Journal (31 factions) ; AtlasLoot Factions (Classic et TBC) | `NaowhForever_DungeonJournal\Data\` (factions) ; `AtlasLootClassic_Factions\data.lua` | rendus, quartier-maître, niveau ; récompenses par palier | — | Naowh 70450 | **non** |
| Progression Legacy (compte) | Legacy Forever 0.11.3 | `AddOns\LegacyForever\Data\Legacy.lua` | `ns.Data = {build, rewards, feeds, zones, completion}` | compte, toutes classes | **wago.tools 1.60.1.70450, 2026-10-17** | **non** (`forever/addons.py:72` : « lecteur en LG1 ») |
| Familiers du Chasseur | Forever Bestiary 0.7.0 | `AddOns\ForeverBestiary\Data\Data.lua`, `Community.lua`, `Guide.lua` ; `SV\ForeverBestiary.lua` | familles, capacités par rang, 671 bêtes, observations | Chasseur | `clientBuild = "1.60.1.70450"`, `date = "2026-10-19"` ; communauté 2026-10-17 | **oui** : `forever/pipeline/bestiary.py`, `forever/pets_lookup.py` |
| Prix de l'hôtel des ventes | Auctionator 341 ; Forever Companion ; Forever Guide | `SV\Auctionator.lua` (`AUCTIONATOR_PRICE_DATABASE`) ; `ForeverCompanionDB.factionrealm[…].ah` ; `ForeverGuideDB.ah` | CBOR par royaume `{m, h, l, a}` | — | dernier prix vu le 2026-10-07 | Auctionator **lu** (`forever/pipeline/auctionator.py`, `profile_import.py`) ; les deux autres **non** |
| Export du personnage (stats, talents, Legacy) | SimulationCraft 12.1.5-02 | sortie `/simc` collée dans le chat | profil texte SimC | toutes classes, mais `spec=unknown` sur Forever | commit du 2026-10-19 « forever: Add legacy talents, ranged, ammo, and bags » | **oui**, mais par l'export collé et non par le dossier : `forever/simc.py` (`parse_simc`) |

## Fraîcheur et changements depuis le 2026-10-14

| Addon | 14 oct. | 21 oct. | Build ou date dans les données | Ce qui change pour nous |
| --- | --- | --- | --- | --- |
| Naowh Forever | 1.1.15 | **1.1.38** | Dungeon Journal 70450 (16 oct.) ; Naowh Score 70450 ; TrainingBuilds 70425 ; TrainingWeapons 70338 ; PvP et SpellEfficiency 70205 ; TrainingData 70178 | listes BiS **inchangées** (11 oct.) ; Training : arbres de nouveau conformes (1.1.27), toujours aucun build livré |
| Forever Companion | 1.0.0, `dataVersion` 88 | 1.0.0, **`dataVersion` 91 (2026-10-20)** | aucun build | builds « Level 30 (Beta) » et « Leveling 1-60 » choisis selon le niveau, absents du relevé du 14 (qui ne voyait que des builds par arbre) ; rotations déjà présentes au 14, au seul niveau 30 aujourd'hui ; BiS plus récent que celui de Naowh |
| Forever Guide | 1.35.1 | **1.37.0** | GearData 70291 corrigé à 70425 ; relevés de butin 70374 à 70450 | GearAdvisor, GearCalc et GearExplain inchangés depuis 1.31.2 ; README : « version non lancée dans le client » |
| GearQuest Forever | cœur 0.5.5-beta, modules 0.3.6-beta | **1.0.0** partout | aucun | niveaux 1 à 9 générés pour les deux camps (plus de saisie à la main pour l'Alliance) ; **aucune ligne `origin="guide"` au 60** (le relevé du 14 annonçait des guides au 60) ; spés battlemage, shockadin et enhancement_tank ajoutées |
| Talents Forever Book | 0.38.2 (70291, codeVersion 6) | **0.38.9 (70425, 2026-10-17, codeVersion 7)** | 70425 | liens `-7` ; arbres de 70425 ; **toujours en retard d'un build sur le client (70450)** |
| RestedXP | 4.11.23 | **4.11.26** | aucun | groupe « Dungeon Guide » nouveau ou non relevé ; Survival Guides de Classic chargés sous Forever |
| SkillUp Forever | 0.9.3 | **0.18.6** | 70450 | données 70450, itinéraire et coût par point |
| Shortest Path Forever | 1.14.0 (10 oct.) | **1.21.5** | 70450 | maillage de Zephras Isle, dangers par zone |
| Legacy Forever | 0.6.19 (dans la SavedVariable) | **0.11.3** | 70450 | — |
| ForeverDungeonJournal | 1.6.2 | **1.6.5** | 70170 (portraits seulement) | Dalaran : boss renommés, niveaux et butin |
| Forever Bestiary | 0.5.0 (1er oct.) | **0.7.0** | 70450, 2026-10-19 | 671 bêtes (606 au 1er oct.) ; carte communautaire à 418 joueurs |
| AtlasLoot Classic Forever | Forever 1.60.1 | Forever 1.60.1 | aucun | contenu changé à version égale (`data.lua`) ; 4 donjons Forever remplis |
| Questie | 11.38.0 Forever-v27 | inchangé | aucun (Classic) | rien |
| Zone Info: Forever | 1.9.1 | inchangé | aucun | `ZoneLevelForever` n'est que son ancien nom (SavedVariable orpheline du 9 octobre) |
| FojjiCore | absent | **absent** | — | lecteurs `read_fojji` et `sleeping_bag` rendent du vide |
| Polestar | non installé | **non installé** | — | — |

**Dernier fichier modifié** (date d'installation, pas de publication ; relevée le 2026-10-21) :

| Date | Addons |
| --- | --- |
| 2026-10-21 | Naowh Forever (13 dossiers), GearQuest Forever (10 dossiers), SkillUp Forever, Shortest Path Forever, Legacy Forever, Forever Bestiary, AppelSwingsForever |
| 2026-10-20 | Forever Companion, Forever Guide, Talents Forever Book, RestedXP, ForeverDungeonJournal, AtlasLoot Classic et ses modules, AtlasBIStooltips, AlexAtlasLoot, Zone Info: Forever, SimulationCraft, ExtendedVendorForever, EllesmereUI (tous les modules), Leatrix_Maps, BetterForeverChat |
| 2026-10-14 | Auctionator |
| 2026-10-09 | Tamed |
| 2026-09-21 | Questie, ForeverMapFix, ForeverCompletionist, RaphCompletionist |

`uv run forever addons status` (sans `--save`) compare au relevé enregistré du 2026-10-21 06:16Z : tout est
« inchangé ». Le relevé du cache est donc postérieur aux mises à jour. Les changements ci-dessus viennent de la
comparaison avec `tasks/inventaire-addons.md`.

## Section par addon

### Naowh Forever 1.1.38 (`AddOns\NaowhForever*`, 13 dossiers)

- **Identité** : auteur Naowh ; `LICENSE.md` « all rights reserved » ; SavedVariable `NaowhForeverDB` déclarée dans le
  seul `.toc` du cœur ; globale `_G.NaowhForever` (`Core/Core.lua:90`, avec `ns.ExportBisList`, `ns.ImportBisList`,
  `ns.OpenTrainingWindow`) ; commandes `/nf`, `/naowh`, `/nftraining`, `/nfquests`.
- **BiS** (`NaowhForever_BiS\BiS\Data\BiS.lua`) :
  - généré (« from wowsrc.com, Tools/build/bis_data.py ») ;
  - 28 spés (9 × 3, plus le Druide farouche dédoublé en DPS et en tank), jusqu'à 10 ou 11 objets classés par
    emplacement ;
  - sans niveau ni phase ;
  - `sources[itemID] = "Boss · Donjon"` (707 entrées, texte seulement) ;
  - `Spots.lua` (PNJ, carte, position) et `Enchants.lua` ;
  - export `!NBIS1!`.
- **Stat Weights** (`NaowhForever_BiS\StatWeights\Data\Defaults.lua`) :
  - faits à la main le 5 octobre, pour le niveau 60 seulement, 28 spés ;
  - exemple de forme : `Spec("MAGE","fire-mage","Fire",CASTER,{ fire=1, int=…, shit=…, scrit=… })` ;
  - import `NFSW1:` ou export EP de WoWSims ;
  - désactivés par défaut : le bloc `statWeights` des deux profils de la SavedVariable est vide.
- **Naowh Score** (`NaowhForever_BiS\NaowhScore\Data\Formula.lua`) : niveau d'objet × échelle + décalage par
  qualité et par emplacement, réajusté sur 70450 (4 313 objets). **Ne dépend pas des poids.**
- **Training** :
  - `TrainingData.lua` : `{niveau, spellID, coût, drapeaux}` pour les 9 classes, build 70178 ;
  - `TrainingWeapons.lua` : build 70338 ;
  - `TrainingBuilds.lua` : arbres seulement, build 70425 ;
  - **aucun build livré**, malgré le README. Les builds du joueur restent dans `account.trainingBuilds`, un point par
    niveau à partir du 10 (51 points) ; export `!NFB1!`.
- **Dungeon Journal** (`NaowhForever_DungeonJournal\Data\`) :
  - 35 donjons, `loot` et `chance` par boss (forme : `chance = {…}`, un pourcentage par objet) ;
  - 31 factions (rendus, quartier-maître, niveau) ;
  - `QuestChains.lua`, `BiSQuests.lua`, `Quests.lua` ;
  - `Build.lua` 70450, `DATA_DATE = "16 Oct 2026"`.
- **Journeys et JourneysData** :
  - un planificateur de trajets, **pas un parcours de leveling** ;
  - cartes de marche en CBOR et Base64 (environ 6,5 Mo) ;
  - `QuestSpots.lua` (environ 5 000 quêtes : position du rendu et camps d'objectifs).
- **Utilities, InstanceTracker** : visites (temps, butin, XP, morts, réputation) et plafond d'instances par
  heure, enregistrés dans la SavedVariable. Aucune donnée livrée.
- **Combat** : barre de consommables, ensembles d'équipement, bénédictions, menace, PvP (`Data/Spells.lua`, 70205),
  minuteur de swing. **Aucune aide à la rotation, aucun DPS simulé.** L'ancien compteur de dégâts est retiré (1.1.38).
- **Professions** (`RecipeData.lua`) : maîtres, rangs et seuils jaune et gris. Ce sont des plages, ni des
  probabilités ni un guide de montée (README l.96-101).
- **QoL** :
  - `ZoneLevelsData` ;
  - `SpellEfficiencyData` : rendement par rang de sort, build 70205 ;
  - Glimmer : points de récolte.
- **Fraîcheur** : selon le module, de 70178 à 70450.

### Forever Companion 1.0.0 (`AddOns\ForeverCompanion`)

- **Identité** :
  - auteur « Forever Companion » ;
  - **aucune licence** ;
  - SavedVariable `ForeverCompanionDB` ;
  - globales `ForeverCompanion`, `ForeverCompanionAPI` (`Compat.lua:7`), `ForeverCompanionData` ;
  - commandes `/fc`, `/bis`, `/fcrot`, `/fctalents`, `/fcconso` ;
  - le `.toc` dit 1.0.0, mais l'addon affiche 0.4.2 (`Core.lua:34`, tiré du fil de nouveautés).
- **Données générées** (« fichier généré par Forever Companion Studio ») : `Data\Meta.lua`
  `{dataVersion=91, updated="2026-10-20"}`. **Aucun build du jeu cité.**
- **Échelles** (`Data\Weights.lua`) : 20 échelles présentées comme celles de Wowhead (`Scales.lua:3`), sans niveau.

  | Classe | Échelles |
  | --- | --- |
  | Druide | Balance, Feral DPS, Healer, Feral Tank |
  | Chasseur | DPS |
  | Mage | DPS |
  | Paladin | Healer, Retribution |
  | Prêtre | Healer, Tier 2 Healer, Shadow |
  | Voleur | Combat, Daggers |
  | Chaman | 3 échelles |
  | Démoniste | DPS |
  | Guerrier | Fury, Threat Tank, Mitigation Tank |

  Les spés sans échelle propre prennent le rôle le plus proche (`Scales.lua:270`). Import et export Pawn v1
  (`Scales.lua:355-373`).
- **BiS** (`Data\Bis.lua`) : 28 spés, phase « BETA », 6 objets par emplacement. Même ordre que Naowh, plus les
  objets d'Alterac (2869xx).
- **Rotations** (`Data\Rotations.lua`) :
  - 28 spés, une section « Single Target — Level 30 » chacune, AoE pour 9 spés ;
  - jetons de sort avec identifiant (699 sorts) et texte libre (1 180 textes) ;
  - présentées comme des rotations de raid (`Rotation.lua:2`).
- **Talents** (`Data\Talents.lua`) :
  - 93 builds : par spé, « Level 30 (Beta) » (`lv=30`), « Leveling 1-60 » et « Standard Build », plus des variantes
    (Frostfire Bolt, Shockadin, Sweeping Strikes…) ;
  - choix automatique selon le niveau (`DataLoader.lua:191`) ;
  - points par arbre et par index, **sans ordre de prise** ;
  - pas de contexte donjon, raid ou PvP explicite.
- **Autres données** :
  - `Training.lua` : environ 1 408 sorts de maître, 9 classes ; le bloc `grimoires` est en français ;
  - `Nodes.lua` : 41 zones, 445 types de points de récolte ;
  - `Dictionary.lua` : 990 objets, 216 avec un taux ;
  - `Loot.lua` : 37 instances, environ 2 800 taux ;
  - `Professions.lua` : 11 métiers, environ 2 349 recettes ;
  - `Consumes.lua` est vide (`C = {}`).
- **Absents** : parcours de leveling, réputations, chaînes de quêtes.
- **SavedVariable** (718 Ko) :
  - `char` : 7 personnages, avec build, échelle et phase choisis ;
  - `global.custom_scales` : 1 échelle personnelle ;
  - `global.inventory`, `goldLog`, `factionrealm.ah` (l'essentiel de la taille) ;
  - `news_seen = "0.3.0"`.

### Forever Guide 1.37.0 (`AddOns\ForeverGuide`)

- **Identité** :
  - pas d'auteur dans le `.toc` ;
  - **aucune licence pour le projet**, seulement pour les briques reprises (LFG en MIT, Ace3 en BSD, cartes Atlas en
    GPL-2.0+) ;
  - SavedVariable `ForeverGuideDB` ;
  - journal des versions dans `README.txt`.
- **Équipement** :
  - poids par rôle en unités WoWSims (`Gear.lua`, 18 rôles), avec de l'endurance ajoutée pour le leveling ;
  - GearAdvisor : comparaison de l'équipement complet par objectif (balanced, damage, healing, sustain, survival,
    threat), plafonds de toucher ;
  - GearCalc : un sort à la fois, explicitement « not a rotation simulator » ; formule (base + coefficient × puissance)
    × multiplicateur, table d'attaque physique, boucle de mana ; coefficients de gunba/wow-forever-sim (2026-09-17) ;
  - GearExplain : « never present it as simulated DPS ».
- **Pas de BiS fixe** : meilleur objet par emplacement selon les poids, le niveau et la classe.
- **Autres données** :
  - `ClassTrainData.lua` : sorts de maître, CMaNGOS Classic ;
  - `ClassData.lua` : 801 quêtes de classe ;
  - `ProfessionData.lua` : 12 métiers, 2 495 recettes ;
  - `DungeonData.lua` : 35 donjons, 550 quêtes de donjon avec prérequis, suite et récompenses (réputation comprise) ;
  - `DungeonLoot.lua` : taux de Classic venus de ForeverChanges ;
  - `ItemSearchData.lua` : 11 139 objets avec lieu et chance ;
  - `RareData.lua` : 404 rares ;
  - `ChainData.lua` : Shadowforge Key et Cozy Sleeping Bag seulement ;
  - `VendorListsData.lua` : 70 listes de marchands de Classic.
- **Absents** : rotations, talents, parcours, temps par monstre.

### GearQuest Forever 1.0.0 (`AddOns\GearQuestForever` et 9 modules `GearQuestForever_<CLASSE>`)

- **Identité** :
  - auteur Henrik8210 dans le `.toc`, mais « Weber8210 » en jeu (`Core.lua:304`) ;
  - aucune licence ;
  - SavedVariables `GearQuestForeverDB` et `GearQuestForeverCharDB` : chasses et objets obtenus, **aucune
    recommandation**.
- **Spés** : 33.

  | Classe | Spés |
  | --- | --- |
  | Mage | 6, dont battlemage ×3 |
  | Paladin | 4, dont shockadin |
  | Chaman | 4, dont enhancement_tank |
  | Druide | 4 : feral, bear, balance, restoration |
  | Guerrier, Chasseur, Voleur, Prêtre, Démoniste | 3 |

- **Choix** :
  - forme : `{itemId, slot, minLevel, maxLevel, rank, spec, faction, score}` ;
  - exemple de forme : `{<itemId>,"Wrist",<min>,<max>,<rang>,"battlemage_arcane","Horde",<score>}` ;
  - les niveaux 1 à 9, de 10 à 59 et le 60 viennent tous du modèle (poids, valeur des effets, type d'armure) ;
  - fiches `ItemFacts` : source, zone, PNJ, quête, réputation et métier requis, **aucun taux**.
- **Fraîcheur** : aucun build ni date dans les `.lua`. Seule date : `_generated\data\items_random.*.json`, relevés le
  2026-09-14.

### Talents Forever Book 0.38.9 (`AddOns\TalentsForeverBook`)

- **Identité** : auteur talentsforever.com, aucune licence, SavedVariable `TalentsForeverBookDB`.
- **`Data.lua`** : généré par `addon/tools/gen_data.py` depuis le site ; build 70425, `generated = "2026-10-17"`,
  `codeVersion = "7"`. Tables :
  - `classes` : 9 classes, 466 talents ;
  - `legacy` : 3 arbres de compte, 25 bonus ;
  - `learn` : sorts de maître par niveau, avec coût ;
  - `coef` : 552 coefficients de puissance des sorts, en texte, de la forme `[spellID] = "<pourcentage> of spell power (direct)"` ;
  - `pets` : 31 capacités de Chasseur, 16 de Démoniste ;
  - `renames`, `racials`.
- **Builds populaires** :
  - `popular.<CLASSE>.top` : 5 builds par classe, au niveau 60, `asOf = "2026-10-17"` ;
  - parts des spés et taux de prise par talent ;
  - **sans contexte ni ordre** : l'ordre est déduit en jeu par `TF.GuessOrder` (`Core.lua:711-720`).

### RestedXP 4.11.26 (`AddOns\RXPGuides`)

- **Identité** : licence CC BY-NC-SA 4.0 (`LICENSE`). Le `.toc` générique déclare l'interface 16001 et
  `AllowLoadGameType camelot` ; il n'y a pas de `_Camelot.toc`.
- **Détection de Forever** : `RXPGuides.lua:201-203` (`game = "FOREVER"`, niveau maximal 60).
- **Guides gratuits** (`Guides\Forever\`, chargés par `Guides\GuideList-forever.xml`) :
  - Alliance : Humain 1-13, Nain et Gnome 1-14, Elfe de la nuit 1-10, puis 11-20 ;
  - Horde : Durotar 1-12, Mort-vivant 1-14, Mulgore 1-12, puis Barrens 12-22 ;
  - Skyborne : Zephras Isle 1-13 ;
  - Mage AoE : Alliance 1-21, Horde 12-21 ;
  - ADV AoE Mage Alliance : 1-22 ;
  - « Dungeon Guide » (`dungeon\`) : guides principaux avec donjons insérés.

  Les 9 classes sont filtrées par `<<`. 1 069 quêtes citées, dont 331 propres à Forever (identifiant ≥ 90000).
  **Plafond : niveau 20 à 22.** Au-delà, les `#next` renvoient à des guides importés.
- **Inertes sous Forever** :
  - talents : `Guides\Talents\classic-*.lua` s'arrêtent hors de CLASSIC ;
  - ItemUpgrades et ses poids : copie de Classic ;
  - `rares.lua` ;
  - les Survival Guides de Classic passent le filtre `#classic` mais ne sont pas adaptés à Forever.
- **Référence cassée** : `dungeon\RestedXP-Skyborne.lua:56,71` inclut des guides de quêtes de classe Skyborne qui
  n'existent pas.
- **Cache `RXPDB`** (`SV\RXPGuides.lua`, 3,3 Mo) :
  - 396 entrées, 158 guides distincts, couvrant les niveaux 1 à 60 pour les deux camps ;
  - dont 1 guide du projet (« Forever Routes ») ;
  - contenu compressé, pas chiffré.

### Questie 11.38.0 Forever-v27 (`AddOns\Questie`, `Questie_Camelot.toc`)

- **Bases** : base Classic Era générée, aucune base Forever.

  | Base | Entrées |
  | --- | --- |
  | Quêtes | 4 244 |
  | PNJ | 10 119 |
  | Objets du monde | 6 645 |
  | Objets | 14 889 |
  | Taux de butin Wowhead (`classicItemDrops.lua`) | 2 032 objets |
  | XP des quêtes | 3 494 quêtes |

- **Propre à Forever** : du code de compatibilité et la SavedVariable `QuestieForeverDB` (v6, 444 quêtes observées
  entre le 24 septembre et le 15 octobre, sans XP).
- **Fichier jamais chargé** : `Modules\ForeverObjectiveTracker.lua`, que n'appelle aucun `.toc`.
- **Licence** : aucune indiquée.

### Shortest Path Forever 1.21.5 (`AddOns\ShortestPathForever`)

- **Identité** : auteur cjber, licence GPL-3.0-or-later.
- **Données** : générées depuis wago.tools 1.60.1.70450, CMaNGOS et InFlight (MIT).
  - `Taxi.lua` : 65 nœuds, 286 trajets, dont 266 durées mesurées ;
  - `Routes.lua` : 13 bateaux et zeppelins, avec leur période ;
  - `Portals.lua` : 34 portails ;
  - `Teleports.lua` : 9 sorts ;
  - `Zones.lua` : plage de niveaux de 41 zones ;
  - `Nav\` : maillage de navigation de 12 Mo, Zephras Isle comprise.
- **Vitesse** : lue en jeu par `GetUnitSpeed`.
- **Intégration** : suit la cible de RestedXP.

### SkillUp Forever 0.18.6 (`AddOns\SkillUpForever`)

- **Identité** : auteur cjber, licence GPL-3.0-or-later.
- **Données** : générées depuis wago.tools 1.60.1.70450 (2026-10-17), CMaNGOS et Classic Era 1.15.9.
  - `Thresholds.lua` : 2 347 recettes, seuils `{orange, jaune, vert, gris}`. Les 12 métiers de Classic sont
    couverts ; les lignes 2937 à 2948 (métiers nouveaux de Forever) sont vides ;
  - `Recipes.lua` : composants ;
  - `Trainer.lua` : frais et rangs des maîtres, quêtes de rang ;
  - `Sources.lua` : 191 parchemins avec taux par PNJ, 198 objets du monde ;
  - `Vendor.lua`.
- **Calculs en jeu** : chance de gain de compétence, coût par point, itinéraire jusqu'à 300, liste de courses.

### Legacy Forever 0.11.3 (`AddOns\LegacyForever`)

- **Identité** : auteur cjber, GPL-3.0-or-later.
- **Données** (`Data\Legacy.lua`) : générées depuis wago.tools 70450 (2026-10-17).
  - `rewards` : 131 défis ;
  - `feeds` : hauts faits de soutien ;
  - `zones` : 549 objectifs d'exploration et 60 d'instance, dans 47 zones ;
  - `completion` : 43 zones.
- **Ce qui manque** : les quêtes, les éliminations et les réputations ne sont pas localisées, faute de données dans le
  client.

### SimulationCraft 12.1.5-02 (`AddOns\Simulationcraft`)

- **Identité** : domaine public (Unlicense).
- **Ce qu'il fait** : export `/simc` pour toutes les classes sur Forever (`extras.lua:6`). Contenu :
  - talents ;
  - `legacy_talents` ;
  - `character_stats` complets ;
  - arme à distance et munitions ;
  - sacs.
- **Limite** : `spec=unknown` est toujours écrit (`core.lua:1221`).
- **Ce qu'il ne fait pas** : ni poids, ni rotation, ni simulation dans l'addon.

### AtlasLoot Classic Forever 1.60.1 et modules (`AddOns\AtlasLootClassic*`)

- **Identité** : GPL-2.
- **Donjons et raids** (`data.lua`) :
  - 45 instances ;
  - 4 donjons Forever remplis : Hall of Thanes, Ruins of Lordaeron, Excavation Site, Dalaran ;
  - 5 donjons Forever vides (« Loot will be updated asap! ») ;
  - raids Forever sans butin ;
  - aucun `npcID` ni `Level` pour les boss Forever.
- **Taux** (`droprate.lua`) : 295 PNJ de Classic seulement.
- **Autres modules** : Factions (Classic et TBC), Crafting, PvP et Collections, avec un contenu de Classic. Aucune
  liste BiS.
- **Point à vérifier en jeu** : AtlasLoot se croit sur retail et rend les valeurs de BCC (`Init.lua:79-95`,
  `AtlasLoot.lua:106-114`). Notre lecteur prend la valeur de Classic.

### AtlasBIStooltips 1.0.1

Cet addon ne fournit aucune donnée :

- 22 spés sont déclarées (`ClassDataBase\*.lua`), mais aucun objet n'est jamais associé : `RECslot` n'est appelée
  nulle part.
- C'est un portage de l'addon de TBC.
- **Rien à lire.** La ligne « lecteur en T10a » de `forever/addons.py:114` n'a plus d'objet.

### ForeverDungeonJournal 1.6.5

- **Identité** : auteur Exehn, aucune licence.
- **Contenu** :
  - 14 donjons, 89 boss avec niveaux (`BOSS_LEVELS`) ;
  - 335 objets sans taux ;
  - environ 105 quêtes ;
  - `QUEST_PREREQ_CHAINS` (21) ;
  - `FOREVER_QUEST_XP_FALLBACK` (80 valeurs du cache du client).
- **Fraîcheur** : tenu à la main ; sources vérifiées le 22 septembre.

### Forever Bestiary 0.7.0

- **Identité** : auteur Ricardo, aucune licence.
- **Données** : générées, build 70450, 2026-10-19 ; 18 familles, 26 capacités, 671 bêtes ; carte communautaire de 418
  joueurs.
- **Absents** : PV et dégâts par bête.
- **Comportement à connaître** (inchangé) : `Core\Init.lua:476` réactive le partage à chaque chargement.

### Auctionator 341

- **Identité** : « All Rights Reserved ». `AGENTS.md` interdit de s'en servir comme référence. Son code n'est jamais
  lu (décision 123).
- **SavedVariable** : 2 royaumes utiles ; dernier prix vu le 2026-10-07.

### Addons d'interface ou sans données utiles

- **Zone Info: Forever 1.9.1** :
  - auteur Vaniron, aucune licence ;
  - `mapTable` : 50 entrées, saisies à la main, identiques à `Leatrix_Maps` 1.60.24 ;
  - nouveaux donjons Forever avec leur plage de niveaux.
- **Tamed 2.0.1** (MIT) : les fichiers Forever sont vides ; ce sont les données Vanilla qui se chargent (302 PNJ,
  13 capacités). **Pas pour Forever** (décision 228).
- **AppelSwingsForever 1.7.3** :
  - aucune table de vitesses d'arme, tout est lu en direct ;
  - sa SavedVariable par personnage garde `mob_speeds`, les vitesses de swing observées par monstre (donnée du joueur,
    utile en recoupement) ;
  - testé sur 69913.
- **ExtendedVendorForever 1.6** : aucune base de vendeurs.
- **EllesmereUI 9.6.1** (propriétaire), ForeverEssentials :
  - durées de vol, générées sur 69913 (périmées) ;
  - niveaux de 43 zones ;
  - transports.
- **EllesmereUI**, AuraBuffReminders : 11 familles de buffs de Forever (70425). CooldownManager : aucune liste par
  spé. **Aucune rotation.** EllesmereUI n'est jamais modifié (décision 274).
- **ForeverMapFix** : tuiles de carte seulement.
- **BetterForeverChat** : aucune donnée de jeu.
- **ForeverCompletionist** : pas un addon. C'est un projet Python de l'utilisateur, inchangé depuis le 21 septembre.
- **AlexAtlasLoot 1.8.0** : exclu par la décision 229 (« All rights reserved » ; copie des tables interdite, y compris
  par une IA). Voir « Points d'attention ».
- **Addons du projet** : ForeverBridge 0.6.0 (200 emplacements, 2 sondes), ForeverLogger 0.6.0, RaphCompletionist
  0.2.1.
  - RaphCompletionist n'a aucun parcours (`Guides\GuideList.lua` vide) ;
  - son `.toc` dit 0.2.1, mais le code dit 0.2.0 ;
  - sa copie de travail diffère du HEAD de son dépôt git local.

**Dossiers absents** : FojjiCore, Polestar, Pawn, WoWSims, Hekili, MaxDps, ZoneLevelForever, ShamanForever,
ShamanPower, SmartTotem, QuestMaster, AllTheThings, CraftingOrderClassic. Il en reste des SavedVariables orphelines
dans `SV\`.

## Constats sur le dépôt

1. **Statistiques des objets de Forever Guide lues sans leur correction de 70425.**
   - `forever/pipeline/gear_sources.py` `read_guide_gear` lit `AddOns\ForeverGuide\GearData.lua` brut, au build
     70291.
   - Or Forever Guide 1.36.0 applique au chargement `ItemBuild70425.lua` : 291 objets modifiés, 216 lignes
     remplacées ou ajoutées, 20 objets retirés.
   - Nos classements BiS et « est-ce une amélioration ? » (`forever/gear.py`) utilisent donc des statistiques plus
     anciennes que celles de l'addon.
2. **Les chaînes `reader` de `DATA_ADDONS` (`forever/addons.py:41-127`) sont périmées.**
   - Forever Companion n'y pointe que `dungeon_sources`, alors que `gear_sources` (BiS, échelles) le lit aussi.
   - Pour Naowh, il manque `gear_sources`, `travel_sources` et `exports/naowh.py`.
   - Pour GearQuest et Forever Guide, il manque `gear_sources`.
   - AtlasBIStooltips attend un « lecteur en T10a » pour un addon vide.
   - FojjiCore est absent, mais `read_fojji` et `sleeping_bag.py` le cherchent encore.
3. **Déjà lu**, avec le module du dépôt :

   | Module de `forever/` | Addons et données lus |
   | --- | --- |
   | `pipeline/questie.py`, `pipeline/monsters.py`, `profile_import.py` | Questie |
   | `pipeline/quest_sources.py` | Questie et sa SavedVariable, Naowh (Completo, Journeys, Dungeon Journal), Forever Guide, ForeverDungeonJournal, GearQuest |
   | `pipeline/dungeon_sources.py` | Naowh et sa SavedVariable, AtlasLoot, ForeverDungeonJournal, Forever Guide, Forever Companion (`Loot.lua`), Zone Info |
   | `pipeline/gear_sources.py` | Forever Guide (statistiques), Naowh (BiS), Forever Companion (BiS et échelles), GearQuest |
   | `pipeline/travel_sources.py` | Naowh Journeys, Training et Professions ; maîtres de Questie |
   | `pipeline/talents_forever.py`, `talents_forever.py` | Talents Forever : arbres et builds populaires |
   | `rxp_guides.py`, `compare.py` | RestedXP, guides gratuits en clair |
   | `pipeline/bestiary.py`, `pets_lookup.py` | Forever Bestiary |
   | `pipeline/auctionator.py` | Auctionator |
   | `simc.py` | export de SimulationCraft collé dans le chat |

4. **Pas encore lu**, alors que la donnée existe :
   - Naowh : poids par défaut, factions, `SpellEfficiencyData` ;
   - Forever Companion : rotations, builds de talents par niveau, `Training`, `Dictionary` (taux), `Professions`,
     `Nodes` ;
   - Forever Guide : poids des rôles, `ClassData` (quêtes de classe), `ClassTrainData`, `ItemSearchData`,
     `CommunityUpdate*`, `ProfessionData` ;
   - GearQuest : poids TBC et `ScoringLeveling` ;
   - Talents Forever : `learn`, `coef`, `pets`, `legacy` ;
   - SkillUp Forever : tout ;
   - Shortest Path Forever : tout ;
   - Legacy Forever : tout ;
   - AtlasLoot Factions ;
   - Questie : `classicItemDrops` ;
   - AppelSwings : `mob_speeds`.
5. **Ce que forever alimente** :
   - Naowh : `!NFB1!` (builds), `!NBIS1!` (BiS) et `NFSW1:` (poids du Mage), par `forever/exports/` ;
   - Forever Companion : Pawn v1 ;
   - RestedXP : guide `ForeverRoute` ou import ;
   - EllesmereUI : profil `!EUI_` ;
   - Talents Forever : code v6.

## Trous : ce qu'aucun addon ne fournit

### Grille par spécialisation

Les 28 spés suivent la liste de Naowh BiS.

Légende :
- **N** Naowh ; **C** Forever Companion ; **G** Forever Guide ; **Q** GearQuest ; **T** Talents Forever.
- « rôle » : échelle commune à plusieurs spés, sans échelle propre.
- « — » : rien.

| Classe | Spé | Poids au 60 | Poids sous le 60 | Rotation | Talents par niveau | BiS au 60 | Équipement par niveau | DPS chiffré | Temps par monstre |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Guerrier | Arms | N ; C rôle (Fury) ; G rôle dps | Q (TBC) | C niv. 30 | C (L30, 1-60, sans ordre) ; T 60 | N, C | Q | G attaque auto seulement | — |
| Guerrier | Fury | N ; C ; G rôle dps | Q | C niv. 30 | C ; T 60 | N, C | Q | G attaque auto | — |
| Guerrier | Protection | N ; C (2 échelles tank) ; G tank | Q | C niv. 30 | C ; T 60 | N, C | Q | — | — |
| Paladin | Holy | N ; C Healer ; G holy | Q | C niv. 30 | C ; T 60 | N, C | Q | G soins | — |
| Paladin | Protection | N ; C rôle ; G prot | Q | C niv. 30 | C ; T 60 | N, C | Q | — | — |
| Paladin | Retribution | N ; C ; G ret | Q | C niv. 30 | C ; T 60 | N, C | Q | G attaque auto | — |
| Chasseur | Beast Mastery | N ; C rôle (DPS) ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | — | — |
| Chasseur | Marksmanship | N ; C rôle ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | — | — |
| Chasseur | Survival | N ; C rôle ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | — | — |
| Voleur | Assassination | N ; C rôle (Daggers) ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | G attaque auto | — |
| Voleur | Combat | N ; C ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | G attaque auto | — |
| Voleur | Subtlety | N ; C rôle ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | G attaque auto | — |
| Prêtre | Discipline | N ; C rôle (Healer) ; G heal | Q | C niv. 30 | C ; T 60 | N, C | Q | G Smite, soins | — |
| Prêtre | Holy | N ; C Healer ; G heal | Q | C niv. 30 | C ; T 60 | N, C | Q | G Smite, soins | — |
| Prêtre | Shadow | N ; C ; G shadow | Q | C niv. 30 | C ; T 60 | N, C | Q | G Mind Blast, Mind Flay | — |
| Chaman | Elemental | N ; C ; G ele | Q | C niv. 30 | C ; T 60 | N, C | Q | G Lightning Bolt | — |
| Chaman | Enhancement | N ; C ; G enh | Q | C niv. 30 | C ; T 60 | N, C | Q | G attaque auto | — |
| Chaman | Restoration | N ; C ; G resto | Q | C niv. 30 | C ; T 60 | N, C | Q | G soins | — |
| Mage | Arcane | N ; C rôle (DPS) ; G dps (école arcane) | Q | C niv. 30 | C ; T 60 | N, C | Q | — (Arcane Missiles non modélisé) | — |
| Mage | Fire | N ; C rôle ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | G Fireball, partie directe | — |
| Mage | Frost | N ; C ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | G Frostbolt | — |
| Démoniste | Affliction | N ; C rôle (DPS) ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | G Shadow Bolt (sans DoT) | — |
| Démoniste | Demonology | N ; C rôle ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | G Shadow Bolt (sans démon) | — |
| Démoniste | Destruction | N ; C rôle ; G dps | Q | C niv. 30 | C ; T 60 | N, C | Q | G Shadow Bolt | — |
| Druide | Balance | N ; C ; G balance | Q | C niv. 30 | C ; T 60 | N, C | Q | G Wrath | — |
| Druide | Feral DPS | N ; C ; G cat | Q | C niv. 30 | C ; T 60 (Feral sans distinction) | N, C | Q | G attaque auto | — |
| Druide | Feral Tank | N ; C ; G bear | Q | C niv. 30 | C ; T 60 (idem) | N, C | Q | — | — |
| Druide | Restoration | N ; C Healer ; G resto | Q | C niv. 30 | C ; T 60 | N, C | Q | G soins | — |

Spés de Forever hors de cette liste, présentes chez GearQuest seulement : Mage battlemage (3), Shockadin, Enhancement
tank. Elles n'ont pas de poids propres chez GearQuest et n'ont ni rotation ni BiS ailleurs.

### Trous communs à toutes les classes

- **Temps par monstre, XP par heure, repos et mana pendant le leveling** : aucun addon. Seule exception :
  AppelSwings garde les vitesses de swing observées des monstres (donnée du joueur, `mob_speeds`). Notre moteur et
  nos relevés restent la seule source.
- **DPS chiffré d'une rotation** : aucun addon. GearCalc chiffre un sort à la fois, sans DoT ni HoT, sans talents,
  sans proc, avec des coefficients de septembre (70009, gunba/wow-forever-sim). WoWSims n'a pas encore de
  simulation Forever d'après le README de Naowh. SimulationCraft exporte, mais `spec=unknown`.
- **Poids sous le niveau 60** :
  - Naowh : 60 seulement ;
  - Companion : sans niveau ;
  - Forever Guide : sans niveau, de l'endurance ajoutée pour le leveling ;
  - GearQuest : priorités TBC transposées, une tranche 1-9 et des multiplicateurs jusqu'au 60 ;
  - RestedXP : poids de Classic, inactifs.

  **Aucun poids de Forever par niveau.**
- **Ordre de prise des talents** : aucun addon ne livre un ordre point par point.
  - Companion : points par arbre à 30 et un build « 1-60 » ;
  - Talents Forever : builds au 60 seulement, ordre deviné en jeu ;
  - Naowh : aucun build livré.

  Aucun contexte donjon, raid ou PvP séparé (Talents Forever le reconnaît dans son retour d'utilisateurs).
- **Rotations au-delà du niveau 30, rotations AoE** : 9 spés sur 28 pour l'AoE ; rien au-delà du 30.
- **BiS par phase ou par niveau au 60** : une seule phase (« BETA ») ; les objets d'Alterac ne sont que chez
  Companion.
- **Parcours de leveling en clair au-delà du niveau 20 à 22** :
  - RestedXP : jusqu'à 22 seulement en gratuit ; la suite n'est que dans le cache importé, non lu par choix ;
  - Polestar : non installé ;
  - **aucun parcours pour les zones nouvelles de Forever entre 30 et 60** ;
  - quêtes de classe au-delà du niveau 10 presque absentes des parcours gratuits (relevé du 2026-10-14), et guides de
    classe Skyborne cassés.
- **Réputations** : pas de guide. Seulement des récompenses de quêtes (Forever Guide), des factions de donjon (Naowh,
  31) et des paliers de Classic et TBC (AtlasLoot).
- **Métiers nouveaux de Forever** : vides chez SkillUp (« no SkillLineAbility rows »).
- **Taux de butin des donjons et raids nouveaux** :
  - raids Forever vides partout ;
  - 5 donjons Forever vides chez AtlasLoot ;
  - Forever Guide : taux de Classic ;
  - seuls Naowh (Wowhead Forever) et Companion portent des taux de Forever.
- **Familiers** : aucune donnée de PV ni de dégâts par bête (Bestiary) ; Tamed ne couvre pas Forever.
- **Monstres** : ni PV ni dégâts de Forever dans un addon. Questie et AtlasLoot portent des niveaux de Classic.

## Points d'attention

- **AlexAtlasLoot** : un sous-agent de ce relevé a ouvert ses fichiers et compté sa structure. Il n'a recopié aucune
  valeur : 37 instances, 328 boss, 287 découvertes de joueurs, 337 quêtes, aucun champ de taux. Cela va au-delà de la
  décision 229 (« exclu et jamais lu »). Rien de ce relevé n'est repris ici au-delà de ces comptes. La décision 229
  reste en vigueur, sauf si tu en décides autrement.
- **Naowh Training** : le README annonce des « builds that ship », mais l'addon n'en livre aucun. Les builds de
  naowh.gg ne s'importent que depuis le site (réseau), donc hors de notre lecture locale.
- **Forever Guide** : son README dit de la 1.37.0 « build non lancé dans le client WoW ». Ses chiffres d'équipement
  sont à recouper avant d'en dépendre.
- **AtlasLoot** :
  - on ne sait pas quel `.toc` le client charge : `_Forever.toc` ou le `.toc` sans suffixe, qui diffèrent pour quatre
    modules. `forever/toc.py` met `_Forever` en premier ;
  - la valeur de `GetForVersion` affichée en jeu (BCC) diffère de celle que lit notre lecteur (Classic).

  À vérifier en jeu avant de trancher.
