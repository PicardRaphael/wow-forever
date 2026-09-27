# Extrait de l'addon Questie (fixture)

- Origine : addon Questie installé dans `C:\Program Files (x86)\World of Warcraft\_classic_beta_\Interface\AddOns\Questie`, `## Version: 11.38.0 Forever-v27`, interface 16001, relevé le 2026-09-27. Base Classic Era chargée sans correction Forever (`ForeverCompat.lua`).
- Extraction : `uv run python scripts/extract_questie_fixture.py` ; ne pas éditer à la main.
- Contenu minimal : lignes `## ` du `.toc` Camelot ; en-tête `npcKeys` et 24 PNJ de `classicNpcDB.lua` (3099, 5951 observés dans la première fixture ; leurres 3111 jamais observé, 1531 rare de rang 4 et 5945 élite de rang 1, écartés de l'agrégat ; T04b : les 19 PNJ observés dans la seconde fixture, pour la correction Questie -> Forever) ; 3 entrées de `xpDB-classic.lua` (787, 788, 789, commentaires compris).
- Zones (T04c, `--zones`, défaut 14,17,718) : en-tête `questKeys` et les 138 quêtes de `classicQuestDB.lua` de Durotar (14), des Tarides (17) et de Wailing Caverns (718) ; `Database/Zones/data/dungeons.lua` réduit à Wailing Caverns (718, parent 17) et deux leurres sans quête (The Deadmines 1581, alternatif 10029 ; Ragefire Chasm 2437) ; `Localization/lookups/lookupZones.lua` réduit aux noms de ces cinq zones.
- Licence : aucun fichier de licence dans l'addon installé ; licence amont à vérifier (docs/OPEN_QUESTIONS.md). La base complète n'est jamais copiée dans le dépôt.

## `journey/Questie.lua`
- Origine : SavedVariable de Questie `…\_classic_beta_\WTF\Account\<COMPTE>\SavedVariables\Questie.lua` (7,6 Mo, chaînes compressées), relevée le 2026-09-27 à 17:42 ; données personnelles de l'utilisateur, jamais copiées au-delà de cet extrait.
- Extraction (décision 3 du plan T04b) : `uv run python scripts/extract_questie_fixture.py --journey <Questie.lua> --guid <GUID du Mage>`. Garde, pour ce seul GUID, les événements `Level` de ses deux blocs `char` (« Jen - … » et « Unknown - … » : Questie écrit parfois un second bloc pour le même personnage ; le passage au niveau 15 à 1790515046, soit 15:17:26 heure locale, est dans le second) et un événement de quête par bloc. Nom, royaume et GUID anonymisés (`Moi`, `Royaume`, `Player-0000-00000000`).
- Heures Unix : ramenées à l'heure locale du journal par le décalage d'un instantané ForeverLogger (`time` 1790523688 ↔ `localtime` 17:41:28, soit +2 h), passé explicitement dans les tests.
