# Extrait de l'addon Questie (fixture)

- Origine : addon Questie installé dans `C:\Program Files (x86)\World of Warcraft\_classic_beta_\Interface\AddOns\Questie`, `## Version: 11.38.0 Forever-v27`, interface 16001, relevé le 2026-09-27. Base Classic Era chargée sans correction Forever (`ForeverCompat.lua`).
- Extraction : `uv run python scripts/extract_questie_fixture.py` ; ne pas éditer à la main.
- Contenu minimal : lignes `## ` du `.toc` Camelot ; en-tête `npcKeys` et 5 PNJ de `classicNpcDB.lua` (3099, 5951, 3111 observés dans le journal de la fixture ; leurres 1531 rare de rang 4 et 5945 élite de rang 1, écartés de l'agrégat) ; 3 entrées de `xpDB-classic.lua` (787, 788, 789, commentaires compris).
- Licence : aucun fichier de licence dans l'addon installé ; licence amont à vérifier (docs/OPEN_QUESTIONS.md). La base complète n'est jamais copiée dans le dépôt.
