# Plan LV1 — Talents de leveling niveau par niveau et resets (2026-11-05, en attente de validation)

Demande de l'utilisateur (2026-11-05) : « de tel à tel niveau tu fais ça, ensuite tu reset », pour le leveling, « à la
perfection », après datamining et recherche complète. Recherche faite le même jour (sources ci-dessous, chacune
datée).

## 1. Les deux questions (décision 288)
- **Qui maintient déjà ça mieux que nous ?**
  - **Sharpie's Gear Judge Talents** (addon, CurseForge v1.2.5-forever du 2026-11-04, MIT selon CurseForge, dépôt
    `Supersharpie/SharpiesGearJudge_Talents` sans licence déclarée) : un point par niveau de 10 à 60, pour chaque spé
    de chaque classe (`Builds.lua`), et un modèle de vitesse de leveling (temps par monstre, dégâts subis, repos, écart
    en % avec le build le plus rapide de la classe), recalé sur des journaux de la bêta. Son modèle de calcul n'est pas
    publié ; ses builds le sont, dans l'addon.
  - Talents Forever (builds populaires, sans tranches), Warcraft Tavern et Method (pas de tranches au-delà de la
    bêta), Everloot (arbres du client, aucun build de départ pour le Chaman).
  - wowsims/forever et MythicSim : niveau 60 seulement (`CharacterLevel = 60`, README de MythicSim), vérifié le
    2026-11-05.
  - Personne ne publie de plan de reset payant chiffré : toutes les sources disent « pas de reset en leveling »,
    seule bascule citée : la double spécialisation au niveau 40 (prix inconnu).
- **Que se passe-t-il au prochain patch ?** Sharpie publie une version par patch (version « -forever » le jour de la
  sortie) ; nous lisons son fichier, rien ne casse chez nous. Un moteur de leveling à nous casserait à chaque patch
  (décisions 288 et 293) : non construit.

## 2. Ce qui change
### a) Lecteur de Sharpie (décision 272, mes addons d'abord)
- L'utilisateur installe l'addon lui-même (l'agent n'installe rien). Lecture locale de `Builds.lua` (et
  `Data/TalentSpellIDs_Forever.lua` pour relier les noms aux sorts du client), comme les autres addons
  (`forever/addons.py`, `AddonSpec`).
- Chaque build : classe, spé, contexte (solo, AoE), talent pris à chaque niveau, écart de vitesse annoncé.
  Légalité contrôlée sur nos arbres du client 70790 (`build_check`) ; un talent inconnu du client est dit, jamais
  corrigé.

### b) Plan de leveling par tranches (`forever_lookup(kind="leveling_plan", name, …)`)
- Rend, pour une classe et un contexte : talents par tranche de niveaux (paliers clés : talent majeur pris, bascule
  d'arbre), l'écart annoncé avec les autres builds, et le moment des bascules.
- **Resets** : proposés seulement quand une source les donne ou à la double spécialisation (niveau 40). Coût du
  reset lu dans les données (`respec.json`, aujourd'hui relevés de la bêta, certitude `suppose`) ; prix réel à
  relever en jeu (essai ci-dessous). Aucun reset inventé pour « gagner » sans chiffre d'une source.
- Recoupements dits à côté : build populaire de Talents Forever le plus proche ; pour le Mage, temps par monstre du
  moteur gelé aux niveaux mesurés ; pour toutes les classes, mes journaux (ForeverLogger) quand ils existent.
- Provenance : version et date de l'addon, certitude `probable` (modèle d'un tiers recalé sur la bêta).

### c) Équipement de leveling
- Inchangé : GearQuest Forever (`forever_gear action="leveling"`), poids de la spé du plan à chaque tranche.

### d) Tests (d'abord, sans réseau)
- Extrait de `Builds.lua` dans `tests/fixtures/addons/` (version figée) : lecture, ordre des points, bascule d'arbre.
- Légalité sur les arbres du client ; talent absent du client signalé.
- Plan par tranches : tranches et bascules, reset seulement sourcé, provenance.

### e) Documents
- Décision 303 (source des talents de leveling ; la décision 299 tient : aucun calcul à nous). Skills `forever-leveling`,
  `forever-builds`, routeur. `docs/OPEN_QUESTIONS.md` : prix du reset et de la double spécialisation dans la version
  finale.

## 3. Essai en jeu (décision 273)
- Chez le maître de classe : prix affiché du premier reset ; prix de la double spécialisation si proposée.
- Addon de Sharpie : comparer son build affiché à celui que rend `forever_lookup` pour Chaman et Mage.

## 4. Ce qui reste hors de portée (dit, pas caché)
- « Parfait » au sens d'un calcul : aucun moteur de leveling ouvert n'existe pour Forever sous le 60 ; le modèle de
  Sharpie est fermé. Le plan est le meilleur avis sourcé disponible, recoupé par nos mesures.
- Si l'utilisateur veut un calcul à nous malgré la décision 293, c'est une autre tranche, à décider par lui.

## 5. Durée et dépendances
- Une demi-journée ; aucune dépendance ; aucun accès réseau (lecture de l'addon installé).
