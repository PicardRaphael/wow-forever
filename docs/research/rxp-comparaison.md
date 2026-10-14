# Nos routes face aux parcours gratuits de RestedXP (RX1c, 2026-10-14)

Décision 268 : **une mesure, pas une source**. Seuls des chiffres et des leçons ici : aucune étape, aucun texte, aucun
ordre de quêtes de RestedXP. Parcours lus en local dans RXPGuides 4.11.23 (`Guides/Forever`, gratuits, en clair),
rejoués par notre simulation (`forever route rxp-compare`) ; données 1.60.1.70374 r2 (`643f5d4aa256`) ; certitude
**suppose** partout (temps par monstre, trajets et objectifs du moteur de route, registre I18 et I19).

## 1. Jusqu'où vont les parcours en clair (`forever route rxp-coverage`)

45 guides en clair, aucun bloc chiffré ou encodé dans `Guides/Forever`.

| Camp | Parcours | Dernier niveau en clair | Suite annoncée, absente en clair |
|---|---|---|---|
| Alliance | Speedrun (Elfe de la nuit, Humain, Nain et Gnome, Skyborne) | 21 | 21-23 Stonetalon/Ashenvale |
| Alliance | Mage AoE | 21 | 21-22 Duskwood |
| Alliance | Mage AoE « ADV » (Humain, Gnome) | 22 | 22-26 Wetlands |
| Horde | Speedrun (Orc et Troll, Mort-vivant, Tauren) | 22 | 22-24 Hillsbrad |
| Horde | Mage AoE | 21 | 21-30 Silverpine/Hillsbrad |

Parcours de donjon (`(WIP)`, marqués bêta) : Horde jusqu'à 22 ; Alliance 20 (Humain, Nain et Gnome) ou 21 (Elfe de la
nuit). La branche Horde à taux d'XP double (`#xprate >1.99`) va jusqu'à 24 mais ne s'applique pas au taux 1 (défaut de
RestedXP). Au-delà, tout est payant : la comparaison s'arrête donc au niveau 21 ou 22.

## 2. Comparaisons (même personnage, même tranche, sans donjon des deux côtés, même départ)

| Personnage, tranche | forever | RestedXP rejoué | Trajet (forever / RXP) | Objectifs | Farm |
|---|---|---|---|---|---|
| Mydream, Orc Chasseur, 15 → 22 | 8,4 h · 16 359 XP/h · 55 quêtes | 11,2 h · 12 214 XP/h · 60 quêtes | 5,1 h / 7,5 h | 2,4 h / 2,1 h | 0,7 h / 1,3 h |
| Orc Chasseur, 1 → 22 | 13,4 h · 16 043 XP/h · 136 quêtes | 18,9 h · 11 428 XP/h · 111 quêtes | 7,1 h / 11,3 h | 5,3 h / 3,5 h | 0,3 h / 3,5 h |
| Orc Chasseur, 12 → 22 | 9,4 h · 18 334 XP/h · 96 quêtes | 13,3 h · 12 917 XP/h · 57 quêtes | 4,1 h / 6,4 h | 4,5 h / 2,0 h | 0,3 h / 4,6 h |
| Orc Mage, 1 → 22 | 15,3 h · 14 117 XP/h · 125 quêtes | 19,4 h · 11 090 XP/h · 127 quêtes | 9,5 h / 12,2 h | 5,1 h / 3,5 h | 0,0 h / 3,1 h |
| Orc Mage, 12 → 21 (Mage AoE) | 6,8 h · 21 589 XP/h · 78 quêtes | 9,0 h · 16 193 XP/h · 44 quêtes | 3,8 h / 5,1 h | 2,6 h / 1,0 h | 0,1 h / 2,7 h |

Partir au milieu d'un parcours (Mydream au niveau 15) le pénalise : 46 objectifs ou rendus de quêtes prises avant
le niveau 15 sont impossibles dans le rejeu. Les tranches 1 → 22 sont les plus justes.

## 3. Pourquoi notre route paraît plus rapide

1. **Le farm du rejeu est surestimé.** RestedXP place des étapes « farm jusqu'au niveau N » (vers 16, 21, 22) en
   comptant sur les monstres tués en chemin ; notre rejeu ne crédite que les monstres des objectifs. Le rejeu arrive
   donc en retard à ces étapes et farme 3,5 h (32 % de l'XP) sur la tranche 1 → 22 du Chasseur. Sans le farm, l'écart
   tombe de 13,4 h contre 18,9 h à 13,2 h contre 15,4 h : **environ 15 % en notre faveur, pas 30 %**.
2. **Nos trajets ignorent les vols et la pierre de foyer.** Le parcours Horde 1 → 22 compte 39 vols, 24 usages de
   la pierre de foyer et 26 changements de lieu de foyer ; notre modèle de trajet marche partout (aucun vol connu,
   pas de foyer). Le trajet représente plus de la moitié du temps des deux côtés (7,1 h et 10,4 h sur 1 → 22) : c'est
   le poste le plus incertain (TRV1, RTE3). Une fois les vols comptés, l'écart restant de l'Orc Chasseur 1 → 22
   (11,3 h de trajet contre 7,1 h) peut s'inverser.
3. **Notre optimiseur préfère les quêtes à tuer.** 119 arrêts d'objectif chez nous contre 61 chez RestedXP sur
   1 → 22 ; XP des objectifs 111 073 contre 54 844, XP des rendus 98 884 contre 92 389. Notre avance tient surtout à
   l'XP des monstres d'objectif, dont le nombre est souvent estimé (`kills_per_quest`, suppose) : à vérifier sur des
   mesures avant d'y croire.
4. **Quêtes que nous ne savons pas placer.** Sur 171 quêtes prises par le parcours du Chasseur 1 → 22, 16 manquent à
   notre monde de route : 5 sans donneur positionné (quêtes lancées par un objet, nouvelles quêtes de Forever comme la série du camping), 6 écartées par une
   chaîne qui en dépend, 3 de donjon (comparaison sans donjon), 1 sans niveau connu, 1 autre.
5. **Ordre des zones.** Les deux routes font les Tarides puis Stonetalon ; RestedXP revient trois fois à
   Orgrimmar (maître de classe, foyer), nous passons par Mulgore et Thunder Bluff.

## 4. Réglages tirés pour notre optimiseur (proposés, rien n'est changé dans `forever/data`)

1. **Vols et pierre de foyer dans les trajets** (I19, TRV1, RTE3) : vols connus du personnage (ForeverLogger ou
   profil), foyer avec son temps de recharge lu dans les données ; le plus gros poste, et celui où RestedXP est
   meilleur que notre modèle ne le dit.
2. **Monstres tués en chemin** : créditer l'XP des monstres croisés sur les trajets (densité par zone, mesurée), des
   deux côtés ; sans cela nos routes sont trop optimistes pour le farm et pessimistes pour les parcours à trajets.
3. **Quêtes lancées par un objet et nouvelles quêtes sans donneur** (question RTE4) : donneur placé au lieu où
   l'objet tombe (objectif du monstre qui le lâche), quêtes nouvelles de Forever placées par les relevés du joueur ;
   rend aussi leurs chaînes (831, 821…).
4. **Poids des objectifs estimés** : un objectif dont le nombre de monstres est estimé ne devrait pas valoir autant
   qu'un objectif connu dans la recherche (part de `min_efficiency` ou certitude dans la valeur d'une quête), tant que
   les mesures manquent.
5. **Rejeu plus juste** : partir d'un état où les quêtes antérieures du parcours sont faites quand la tranche commence
   au milieu (Mydream au niveau 15).

## 5. Partie payante (plus tard)

Quand le joueur suivra un guide payant en jouant, la comparaison se fera sur ses mesures réelles (ForeverLogger,
niveau par niveau), jamais sur le guide lui-même (décision 268).

## Recette des routes 1 → 10 (CJ1, décision 279, 2026-10-14)

`forever route recette` sur les 56 combinaisons race et classe jouables (`races.json`), données 1.60.1.70374, parcours gratuits de RestedXP 4.11.23 lus en local et rejoués par nos règles depuis le même départ (zone de départ de la race) ; temps par monstre au camp pour les routes ; donjons et quêtes de classe inclus par défaut. Acceptée : mêmes zones et au plus trois différences, chacune expliquée. Chiffres seulement, aucun texte de guide.

Bilan : notre calcul accepté **7 fois sur 56** ; base adaptée acceptée **56 fois sur 56** ; la route livrée est donc la base adaptée partout où notre calcul est refusé.

| Race | Classe | Notre calcul | Différences | Parcours rejoué | Base adaptée | Ajouts de la base | Route livrée |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Human | Warrior | refusée, 2.4 h | 16 (14 sans explication ; zones différentes) | 2.9 h | acceptée, 2.9 h | aucun | base adaptée |
| Human | Paladin | refusée, 2.4 h | 14 (12 sans explication ; zones identiques) | 3.1 h | acceptée, 3.1 h | aucun | base adaptée |
| Human | Hunter | refusée, 3.9 h | 16 (16 sans explication ; zones identiques) | 4.2 h | acceptée, 4.2 h | aucun | base adaptée |
| Human | Rogue | refusée, 2.4 h | 14 (12 sans explication ; zones identiques) | 3.0 h | acceptée, 3.0 h | aucun | base adaptée |
| Human | Priest | refusée, 2.2 h | 13 (12 sans explication ; zones différentes) | 3.2 h | acceptée, 3.2 h | aucun | base adaptée |
| Human | Mage | refusée, 2.6 h | 11 (9 sans explication ; zones identiques) | 3.8 h | acceptée, 3.8 h | aucun | base adaptée |
| Human | Warlock | refusée, 2.3 h | 15 (14 sans explication ; zones identiques) | 2.8 h | acceptée, 2.8 h | 1 quête de classe | base adaptée |
| Orc | Warrior | refusée, 2.0 h | 22 (20 sans explication ; zones identiques) | 2.7 h | acceptée, 2.7 h | aucun | base adaptée |
| Orc | Hunter | refusée, 2.0 h | 16 (14 sans explication ; zones identiques) | 3.4 h | acceptée, 3.4 h | 1 quête de classe | base adaptée |
| Orc | Rogue | refusée, 2.0 h | 22 (20 sans explication ; zones identiques) | 2.8 h | acceptée, 2.8 h | aucun | base adaptée |
| Orc | Shaman | refusée, 1.8 h | 23 (20 sans explication ; zones différentes) | 3.4 h | acceptée, 3.4 h | 3 quête de classe | base adaptée |
| Orc | Mage | acceptée, 3.5 h | 0 (0 sans explication ; zones identiques) | 3.5 h | acceptée, 3.5 h | aucun | notre calcul |
| Orc | Warlock | refusée, 1.5 h | 19 (17 sans explication ; zones identiques) | 2.9 h | acceptée, 2.9 h | 1 quête de classe | base adaptée |
| Dwarf | Warrior | refusée, 2.9 h | 21 (20 sans explication ; zones différentes) | 3.0 h | acceptée, 3.0 h | 1 quête de classe | base adaptée |
| Dwarf | Paladin | refusée, 2.9 h | 21 (20 sans explication ; zones différentes) | 2.7 h | acceptée, 2.7 h | 1 quête de classe | base adaptée |
| Dwarf | Hunter | acceptée, 3.2 h | 0 (0 sans explication ; zones identiques) | 3.2 h | acceptée, 3.2 h | 1 quête de classe | notre calcul |
| Dwarf | Rogue | refusée, 2.8 h | 21 (20 sans explication ; zones différentes) | 2.9 h | acceptée, 2.9 h | aucun | base adaptée |
| Dwarf | Priest | refusée, 2.5 h | 24 (22 sans explication ; zones différentes) | 3.0 h | acceptée, 3.0 h | 1 quête de classe | base adaptée |
| Dwarf | Shaman | refusée, 2.9 h | 22 (21 sans explication ; zones identiques) | 2.9 h | acceptée, 2.9 h | 1 quête de classe | base adaptée |
| Night Elf | Warrior | acceptée, 2.1 h | 0 (0 sans explication ; zones identiques) | 2.1 h | acceptée, 2.1 h | aucun | notre calcul |
| Night Elf | Hunter | acceptée, 2.8 h | 0 (0 sans explication ; zones identiques) | 3.0 h | acceptée, 3.0 h | aucun | notre calcul |
| Night Elf | Rogue | refusée, 2.1 h | 2 (1 sans explication ; zones identiques) | 2.1 h | acceptée, 2.0 h | 1 quête de classe | base adaptée |
| Night Elf | Priest | refusée, 2.2 h | 1 (1 sans explication ; zones identiques) | 2.1 h | acceptée, 2.1 h | 2 quête de classe | base adaptée |
| Night Elf | Druid | acceptée, 2.1 h | 0 (0 sans explication ; zones identiques) | 2.2 h | acceptée, 2.2 h | aucun | notre calcul |
| Undead | Warrior | refusée, 2.5 h | 18 (17 sans explication ; zones identiques) | 2.8 h | acceptée, 2.8 h | aucun | base adaptée |
| Undead | Paladin | refusée, 2.5 h | 17 (17 sans explication ; zones identiques) | 2.7 h | acceptée, 2.7 h | aucun | base adaptée |
| Undead | Rogue | refusée, 2.5 h | 18 (17 sans explication ; zones identiques) | 2.8 h | acceptée, 2.8 h | aucun | base adaptée |
| Undead | Priest | refusée, 2.5 h | 18 (17 sans explication ; zones identiques) | 2.8 h | acceptée, 2.8 h | aucun | base adaptée |
| Undead | Mage | acceptée, 3.5 h | 0 (0 sans explication ; zones identiques) | 3.5 h | acceptée, 3.5 h | 1 quête de classe | notre calcul |
| Undead | Warlock | refusée, 2.5 h | 16 (15 sans explication ; zones identiques) | 2.8 h | acceptée, 2.8 h | 3 quête de classe | base adaptée |
| Tauren | Warrior | refusée, 4.1 h | 8 (7 sans explication ; zones identiques) | 3.5 h | acceptée, 3.5 h | aucun | base adaptée |
| Tauren | Hunter | refusée, 4.3 h | 7 (6 sans explication ; zones identiques) | 4.1 h | acceptée, 4.1 h | 1 quête de classe | base adaptée |
| Tauren | Shaman | refusée, 4.4 h | 8 (7 sans explication ; zones identiques) | 3.8 h | acceptée, 3.8 h | 7 quête de classe | base adaptée |
| Tauren | Druid | refusée, 4.1 h | 8 (7 sans explication ; zones identiques) | 3.5 h | acceptée, 3.5 h | 1 quête de classe | base adaptée |
| Gnome | Warrior | refusée, 2.9 h | 21 (20 sans explication ; zones différentes) | 3.0 h | acceptée, 3.0 h | 1 quête de classe | base adaptée |
| Gnome | Rogue | refusée, 2.8 h | 21 (20 sans explication ; zones différentes) | 2.9 h | acceptée, 2.9 h | aucun | base adaptée |
| Gnome | Priest | refusée, 2.8 h | 20 (20 sans explication ; zones différentes) | 3.0 h | acceptée, 3.0 h | aucun | base adaptée |
| Gnome | Mage | refusée, 3.2 h | 12 (10 sans explication ; zones identiques) | 3.1 h | acceptée, 3.1 h | aucun | base adaptée |
| Gnome | Warlock | refusée, 2.8 h | 21 (20 sans explication ; zones différentes) | 3.4 h | acceptée, 3.4 h | 1 quête de classe | base adaptée |
| Troll | Warrior | refusée, 2.0 h | 22 (20 sans explication ; zones identiques) | 2.7 h | acceptée, 2.7 h | aucun | base adaptée |
| Troll | Hunter | refusée, 2.0 h | 16 (14 sans explication ; zones identiques) | 3.4 h | acceptée, 3.4 h | 1 quête de classe | base adaptée |
| Troll | Rogue | refusée, 2.0 h | 22 (20 sans explication ; zones identiques) | 2.8 h | acceptée, 2.8 h | aucun | base adaptée |
| Troll | Priest | refusée, 2.1 h | 25 (22 sans explication ; zones identiques) | 2.8 h | acceptée, 2.8 h | aucun | base adaptée |
| Troll | Shaman | refusée, 1.8 h | 23 (20 sans explication ; zones différentes) | 3.4 h | acceptée, 3.4 h | 4 quête de classe | base adaptée |
| Troll | Mage | acceptée, 3.5 h | 0 (0 sans explication ; zones identiques) | 3.5 h | acceptée, 3.5 h | 1 quête de classe | notre calcul |
| Troll | Warlock | refusée, 1.5 h | 19 (17 sans explication ; zones identiques) | 2.9 h | acceptée, 2.9 h | 2 quête de classe | base adaptée |
| High Order Skyborne | Warrior | refusée, 5.4 h | 24 (22 sans explication ; zones identiques) | 5.7 h | acceptée, 5.7 h | 1 quête de classe | base adaptée |
| High Order Skyborne | Hunter | refusée, 5.8 h | 24 (23 sans explication ; zones identiques) | 6.3 h | acceptée, 6.3 h | aucun | base adaptée |
| High Order Skyborne | Rogue | refusée, 5.4 h | 24 (22 sans explication ; zones identiques) | 5.7 h | acceptée, 5.7 h | aucun | base adaptée |
| High Order Skyborne | Mage | refusée, 4.1 h | 1 (1 sans explication ; zones différentes) | 3.5 h | acceptée, 3.5 h | aucun | base adaptée |
| High Order Skyborne | Druid | refusée, 5.0 h | 24 (22 sans explication ; zones identiques) | 5.3 h | acceptée, 5.3 h | aucun | base adaptée |
| Windshaper Skyborne | Warrior | refusée, 3.4 h | 27 (27 sans explication ; zones identiques) | 3.8 h | acceptée, 3.8 h | aucun | base adaptée |
| Windshaper Skyborne | Hunter | refusée, 4.2 h | 32 (32 sans explication ; zones identiques) | 4.3 h | acceptée, 4.3 h | 1 quête de classe | base adaptée |
| Windshaper Skyborne | Rogue | refusée, 5.5 h | 26 (24 sans explication ; zones identiques) | 5.9 h | acceptée, 5.9 h | aucun | base adaptée |
| Windshaper Skyborne | Shaman | refusée, 3.7 h | 31 (31 sans explication ; zones identiques) | 3.9 h | acceptée, 3.9 h | 6 quête de classe | base adaptée |
| Windshaper Skyborne | Druid | refusée, 3.6 h | 27 (27 sans explication ; zones identiques) | 3.9 h | acceptée, 3.9 h | 1 quête de classe | base adaptée |

Lecture : notre calcul prend surtout d'autres quêtes que le parcours (les différences sans explication sont des quêtes prises d'un seul côté) ; il est plus court sur le papier, mais la décision 279 juge la ressemblance, pas le temps simulé. Le réglage de l'optimiseur (CJ1, bloc 1e) vise à faire accepter notre calcul ; d'ici là, la base adaptée est livrée, avec l'attribution à RestedXP dans le guide.
