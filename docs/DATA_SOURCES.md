# Sources de données

## Client Forever (vérité)
- Versions : `https://wago.tools/api/builds` (produit `wow_classic_beta`, versions `1.60.x` ; liste non triée : trier par `created_at`). Produit de lancement : inconnu, prévoir l'alerte `silent`.
- Tables : `https://wago.tools/db2/<Table>/csv?build=<version>` (enUS) ; autre locale : `&locale=frFR` (vérifié le 2026-09-27 sur `SpellName`). Liste des tables, colonnes utilisées et règles de lecture : `forever/data/<version>/decode_rules.json`, `forever/pipeline/tables.py`, inventaire `tasks/T03-inventaire.md`. `TraitTreeLoadout*` : HTTP 400 sur 1.60.1.70009 (inutile).
    - Talents : SkillLineXTraitTree (ligne de compétence → arbre), TraitNode, TraitNodeEntry, TraitNodeXTraitNodeEntry, TraitDefinition, TraitDefinitionEffectPoints (points par rang via CurvePoint), TraitEdge (prérequis), CurvePoint. Ignorer Talent et TalentTab (reliquats Classic). Valeurs d'un rang : variables de l'infobulle du sort du nœud (`Spell.Description_lang`).
    - Géométrie des arbres : onglets à PosX 1020 / 5020 / 9080, rangées à PosY 2130 + 600 par rangée, colonnes espacées de 600 ; quelques positions ont un zéro en trop ; si deux nœuds partagent un sort, le plus récent est le bon.
    - Sorts : SkillLineAbility (rangs par ligne de compétence), Spell (rang dans NameSubtext, infobulle), SpellName, SpellEffect (points de base, RealPointsPerLevel, variance, période, sort déclenché), SpellLevels, SpellMisc (attributs, index d'incantation et de durée), SpellCastTimes, SpellDuration, SpellPower, SpellCooldowns, SpellAuraOptions (cumuls, charges).
    - Objets : Item*, formules RandPropPoints, ItemDamage*, ItemArmor*.
- Hotfixes : `DBCache.bin` du client, à faire correspondre à la version, la région et la langue.
- Absent du client : PV des monstres, quêtes, positions des PNJ, taux de butin, stocks, listes d'entraîneurs.

## Voie autonome (si wago est indisponible)
- `db2tool` (wowsims) : lecture du client installé, superposition des hotfixes ; mode hors ligne sur fichiers extraits.
- wow.tools.local (TACTSharp, DBCD, WoWDBDefs) ; définitions de tables : WoWDBDefs.

## Données dérivées et simulateurs (MIT, garder le lien vers wowsims/classic)
- Arbres de talents au format wowsims : `gunba/wow-forever-sim` (`ui/core/talents/trees/mage.json`), rangs confirmés : `ElliotWood/Forever` (`assets/confirmed_talents.json`).
- Simulateur de référence : fork `ElliotWood/Forever` ; `SimOptions.ruleset` vaut `RulesetClassic` par défaut : toujours passer la règle Forever. Le dépôt amont `wowsims/forever` a été injoignable (404) : **épingler les commits et copier les arbres utilisés**.
- Base d'objets de référence : `alcaras/forever-ref` (calcul des stats par formules du client).
- Recoupements lisibles : ForeverChanges, WoW Forever Talents, Wowhead Forever.

## Client installé (sources locales, sans réseau ; T04a)
Dossier du client : `FOREVER_WOW_DIR` (défaut `C:\Program Files (x86)\World of Warcraft\_classic_beta_`), lu en lecture seule.
- **Journaux de combat** `Logs/WoWCombatLog-*.txt` : format 22, bloc avancé à 19 champs (dont PV max, coût du sort, position, niveau) ; lecteur `forever/pipeline/combatlog.py`, mesures `forever/pipeline/measure.py` (`forever logs scan`, `forever logs measure`). L'en-tête ne donne que `1.60.1` (pas le build) : la provenance retient la version locale de même préfixe, avec une hypothèse. Source de premier rang pour les PV des monstres (`certain`). Warcraft Logs n'a pas de support Forever documenté.
- **Hotfix.log** : index des hotfixes appliqués au démarrage (push, table, RecID, validité), **sans valeur** ; utilisable en T08 comme index de changements. Les valeurs sont dans `Cache/ADB/<locale>/DBCache.bin` (en-tête `XFTH`, build en octets 4-7) : décodage en T08 (WoWDBDefs).
- **QuestCache.log** : journal de requêtes du cache de quêtes, **aucune donnée** ; le contenu est dans `Cache/WDB/<locale>/questcache.wdb` (`WQST`) et `creaturecache.wdb` (`WMOB`, sans PV) : format binaire non documenté, hors T04.
- **SavedVariables** `WTF/Account/<COMPTE>/SavedVariables/` : `ForeverLogger.lua` (`ForeverLoggerDB`, niveau et talents du personnage, `forever/pipeline/addon_sv.py`) ; lus sans exécuter de Lua (`forever/pipeline/lua_table.py`).
- **Carnet de Questie** (T04b, décision 3) : `SavedVariables/Questie.lua`, table `QuestieConfig.char.<Nom - Royaume>.journey` (événements `Level` : heure Unix, nouveau niveau). Données personnelles de l'utilisateur, lues localement seulement (`forever/pipeline/questie.py : read_journey`), jamais copiées au-delà d'un extrait anonymisé de fixture. Le fichier contient des chaînes compressées (octets quelconques) : lecture octet pour octet et balayage table par table ; Questie écrit parfois plusieurs blocs `char` pour un même GUID (« Unknown ») : réunis par GUID. Heures ramenées à l'heure locale du journal par le décalage d'un instantané ForeverLogger, sinon par le fuseau du système. Repli après ForeverLoggerDB pour le niveau du lanceur.

## Addons installés (sources communautaires)
- **Questie** (`Interface/AddOns/Questie`, version lue dans `Questie_Camelot.toc`, ici 11.38.0 Forever-v27) : base **Classic Era sans correction Forever** (PNJ : PV min/max, niveaux, rang ; XP de quête). Lecture locale seulement (`forever/pipeline/questie.py`), jamais copiée : le dépôt ne garde que l'agrégat par niveau et les PNJ observés dans un journal avec la valeur Questie en regard (`monsters.json`). Certitude `suppose`, étiquette « communautaire », version de l'addon dans la provenance. **Licence amont à vérifier** avant tout élargissement. Relire quand la version change (veille, T08). Écart mesuré le 2026-09-27 : Questie sous-estime les PV de Forever à partir du niveau 10 environ (29 écarts sur 21 PNJ mesurés).
- ForeverDungeonJournal (niveaux de boss, recoupement de H1), GearQuestForever (fiches d'objets, T10) : notés, non ingérés. EllesmereUI : non utilisé.
- **RestedXP (RXPGuides) : exclu en entier** (guides payants).

## API Blizzard
Clés dans `.env` (ignoré par git, jamais lu par les tests). Couverture de Forever à vérifier au lancement ; le client futur vivra dans `forever/pipeline/bnet.py` (via `Deps.http_get`) et sera ajouté à la liste réseau de CLAUDE.md et de `tests/unit/test_network_boundary.py` ce jour-là. Aucun code en T04.
