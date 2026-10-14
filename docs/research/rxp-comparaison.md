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
| Mydream, Orc Chasseur, 15 → 22 | 8,4 h · 16 359 XP/h · 55 quêtes | 11,2 h · 12 301 XP/h · 58 quêtes | 5,1 h / 7,4 h | 2,4 h / 2,0 h | 0,7 h / 1,5 h |
| Orc Chasseur, 1 → 22 | 13,4 h · 16 043 XP/h · 136 quêtes | 19,1 h · 11 264 XP/h · 107 quêtes | 7,1 h / 10,4 h | 5,3 h / 3,4 h | 0,3 h / 4,8 h |
| Orc Chasseur, 12 → 22 | 9,4 h · 18 334 XP/h · 96 quêtes | 13,3 h · 12 900 XP/h · 55 quêtes | 4,1 h / 6,3 h | 4,5 h / 1,9 h | 0,3 h / 4,8 h |
| Orc Mage, 1 → 22 | 15,3 h · 14 117 XP/h · 125 quêtes | 19,5 h · 11 048 XP/h · 126 quêtes | 9,5 h / 12,3 h | 5,1 h / 3,4 h | 0,0 h / 3,2 h |
| Orc Mage, 12 → 21 (Mage AoE) | 6,8 h · 21 589 XP/h · 78 quêtes | 9,0 h · 16 193 XP/h · 44 quêtes | 3,8 h / 5,1 h | 2,6 h / 1,0 h | 0,1 h / 2,7 h |

Partir au milieu d'un parcours (Mydream au niveau 15) le pénalise : 51 rendus de quêtes prises avant le niveau 15
sont impossibles dans le rejeu. Les tranches 1 → 22 sont les plus justes.

## 3. Pourquoi notre route paraît plus rapide

1. **Le farm du rejeu est surestimé.** RestedXP place des étapes « farm jusqu'au niveau N » (vers 16, 21, 22) en
   comptant sur les monstres tués en chemin ; notre rejeu ne crédite que les monstres des objectifs. Le rejeu arrive
   donc en retard à ces étapes et farme 4,8 h (35 % de l'XP) sur la tranche 1 → 22 du Chasseur. Sans le farm, l'écart
   tombe de 13,4 h contre 19,1 h à 13,2 h contre 14,3 h : **environ 8 % en notre faveur, pas 30 %**.
2. **Nos trajets ignorent les vols et la pierre de foyer.** Le parcours Horde 1 → 22 compte 39 vols, 24 usages de
   la pierre de foyer et 26 changements de lieu de foyer ; notre modèle de trajet marche partout (aucun vol connu,
   pas de foyer). Le trajet représente plus de la moitié du temps des deux côtés (7,1 h et 10,4 h sur 1 → 22) : c'est
   le poste le plus incertain (TRV1, RTE3).
3. **Notre optimiseur préfère les quêtes à tuer.** 119 arrêts d'objectif chez nous contre 59 chez RestedXP sur
   1 → 22 ; XP des objectifs 111 073 contre 52 936, XP des rendus 98 884 contre 87 129. Notre avance tient surtout à
   l'XP des monstres d'objectif, dont le nombre est souvent estimé (`kills_per_quest`, suppose) : à vérifier sur des
   mesures avant d'y croire.
4. **Quêtes que nous ne savons pas placer.** Sur 182 quêtes prises par le parcours du Chasseur 1 → 22, 26 manquent à
   notre monde de route : 10 d'une autre classe (RestedXP les liste toutes, le jeu trie : sans effet), 5 sans donneur
   positionné (quêtes lancées par un objet, nouvelles quêtes de Forever comme la série du camping), 6 écartées par une
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
