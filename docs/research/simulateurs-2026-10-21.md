# Simulateurs de la communauté pour Forever : étude de l'existant (2026-10-21, décision 264)

Lecture seule des sites et des dépôts, le 2026-10-21. Rien n'a été téléchargé ni exécuté. Toutes les affirmations
sont de certitude `suppose` (sources tierces).

## Tableau

| Simulateur | Licence, code | En local ou appelable | Niveaux, classes | Fraîcheur | Sortie utile |
| --- | --- | --- | --- | --- | --- |
| **wowsims/forever** (https://github.com/wowsims/forever) | MIT (lien de retour demandé), Go, ouvert | **oui** : binaires Windows, macOS et Linux publiés, ou `go run ./cmd/wowsimcli sim --infile <RaidSimRequest.json>` (protojson), interface locale `make host` | **niveau 60 seulement** (`sim/core/constants.go` : `const CharacterLevel = 60` ; pas de champ de niveau du joueur dans `proto/api.proto`) ; ennemis : niveau, nombre, durée réglables ; 9 classes ; races du proto dont High Order Skyborne, Gnome, Human, Dwarf | très active : « Update items to 1.60.1.70450 with hotfixes as of 2026-10-21 » ; Mage : Missile Barrage et Arcane Blast (16 et 17 oct.), Piercing Ice retiré et Frigid Power ajouté (commit 983ea6f, 20 oct.) | DPS par sort, journal ; `StatWeightsRequest` et `BulkSimRequest` dans le proto, **pas dans la ligne de commande** vue (poids par tirages appariés possibles) |
| **MythicSim** (https://mythicsim.com/wow-forever ; moteur https://github.com/sage3648/mythicsim-forever-engine-go) | MIT, fork Go de wowsims (par ElliotWood/Forever) ; moteur Rust expérimental à part | le fork se compile (Go, protobuf, Node) ; site : aucune API publique, `robots.txt` interdit `/api/` et `/sims/` | niveau 60, boss, 2 min, buffs de raid ; toutes classes | client **1.60.1.70425** (avant la refonte du Mage), commit 62b7445 du 21 oct. ; ses règles écrites ignorent Frigid Power et Piercing Ice | DPS par spé, **comparaison des races** publiée |
| **Sims Forever** (https://simsforever.com) | site : pas d'auteur, de licence ni de version ; « Powered by WoWSims » ; le compte GitHub Blueteak (18 dépôts) ne publie **pas** de moteur adapté au leveling | non : pas d'API, pas de moteur publié | presets « Level 20 » Guerrier, Paladin, Voleur, Démoniste, « Level 14 » Chasseur ; **Mage, Chaman, Prêtre, Druide : « No Test Export Yet »** ; rencontres Open World, élites, donjon, ennemis sur mesure, écart de niveau | inconnue (« Under construction ») | DPS ± marge à 95 % ; ni temps de mise à mort, ni repos, ni poids, ni races |
| addon **Sims Forever** (https://www.curseforge.com/wow/addons/sims-forever ; code https://github.com/Blueteak/SimsForeverExporter) | MIT, Lua, ouvert | lecture locale possible (SavedVariable) | toutes classes | 0.1.6, mis à jour le 2026-09-26 | export JSON brut (`schemaVersion` 1) : race, classe, niveau, talents, stats, vie et mana, équipement, sorts appris, sacs, familier, buffs, build ; pas de métiers |
| **DPS Forever** (https://dpsforever.com) | anonyme, aucune licence, aucun code publié | non : aucune API trouvée (appels réseau de la page non vérifiés : seul un navigateur le dirait) | race, classe, niveau, talents, rotation, ennemis | aucune version ni build affichés ; sa page Mage ne cite aucune mécanique de la refonte de 70450 | DPS, dégâts par sort, journal |
| **ForeverDB, simulateur du niveau 30** (https://foreverdb.net/sim) | auteur non nommé, code fermé, moteur non nommé | non pour le simulateur ; API de **données** seulement (clé, 60 requêtes/min, crédit obligatoire ; `robots.txt` interdit `/api/` aux robots) | niveau 30 (40 « Speculation ») ; 19 spés de dégâts sur 9 classes ; cible immobile qui ne frappe pas ; **raciaux non simulés** | build 70450 extrait le 19 oct., mais son changelog dit que 70450 ne change aucun sort (contredit la refonte du Mage) | DPS, poids appariés, comparaison de deux réglages |

## Comparaison avec nos résultats

Notre comparaison Mage, Chaman et races n'a **pas été calculée** : elle était à faire quand l'étude a été demandée
(rejeux en Orc seulement, `docs/research/rejeu-70450-r7.md`). Ce que les sources publient :

- MythicSim, niveau 60, Feu 16/32/3, client 70425, 10 000 combats : High Order Skyborne 860,1 dégâts/s (raciaux
  +1,72 %), Humain 859,3 (+1,68 %), Gnome 852,7 (+0,79 %, Eureka! en fenêtre de 8 s toutes les 2 min, hors dégâts
  périodiques) ; Chaman Amélioration, Nain 735,0 (Earth Fury ≈ +6,9 dégâts/s) ; spés du Mage au 60 : Feu 860,
  Arcanes 791, Givre 666 ; Chaman : Amélioration 741, Élémentaire 519.
- ForeverDB, niveau 30 (raciaux non simulés) : Feu 97,2, Givre 92,5, Arcanes 84,2 ; Chaman Amélioration 113,6,
  Élémentaire 84,1.
- Nous (r7, Orc, scénarios sans équipement ni buffs, `build.scenarios`) : raid 60 Givre et Arcanes à égalité, Feu
  absent du haut ; donjon 60 Givre. **Échelles incomparables** (équipement, buffs de raid, durée) et **ordre
  différent** : MythicSim met le Feu devant au 60, sur 70425 (sans la refonte du Mage ni le correctif 112753) ; nous
  sur 70450 r7, avec. À trancher par wowsims/forever, qui suit 70450 et ses correctifs.
- L'écart entre les trois races du Mage au 60 chez MythicSim tient en moins de 1 % ; aucune source ne chiffre le
  leveling.

## Ce qu'aucune source ne fait
Temps par monstre et XP par heure à un niveau donné (monstre qui frappe, repos, boisson), sous le niveau 60 avec les
raciaux ; PvP ; XP réelle de Forever, routes, quêtes, respécialisations.
