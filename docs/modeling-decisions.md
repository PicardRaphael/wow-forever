# Choix du modèle

Ce que **notre moteur choisit**, et non ce que Blizzard fait : poids, paramètres, conventions de départage, règles
du plugin et de la gestion des données. Ces choix ne sont pas des inconnues du jeu ; ils se règlent avec
l'utilisateur ou par l'usage, pas par une mesure en jeu. Les règles de jeu incertaines restent dans
[OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). Séparation faite le 2026-10-02 (pistes du 2026-10-01, section E) : les
entrées ci-dessous y sont déplacées sans changement de fond.

## Profil PvP

- I5 (T05, profil PvP, `pvp.weights`, suppose) : poids du contexte **monde ouvert** (`world` : burst 0,45, contrôle 0,2, survie 0,2, soutenu 0,15) supposés pour l'embuscade ; ceux des champs de bataille (`bg`) sont ceux du seed. Le profil PvP du seed est un modèle de scénarios (EST) sans simulation de duel. À régler avec l'utilisateur, puis par les journaux de champs de bataille (PV2).

## Respec

- I5 (T05, respec, suppose) : or gagné par heure selon le niveau (`respec.gold_per_hour`, table du seed) et trajet chez le maître de classe (6 min) ; à remplacer par le rythme réel du joueur (import de l'addon, T07).
- I5 (2026-10-02, respec de la bêta) : les notes de développement officielles du 24/09/2026 (<https://us.forums.blizzard.com/en/wow/t/2360696>, section Classes) annoncent un coût de respec réduit, **temporaire et propre à la bêta**, quand aucune réinitialisation récente n'a eu lieu (`respec.json`, `beta_observed.temporary_beta`). Le moteur garde le barème de Classic (`classic_schedule_gold`, `PC`) : un tarif temporaire de la bêta ne vaut pas pour le jeu lancé. Choix à revoir si Blizzard annonce un barème de lancement.

## Départage de l'optimiseur et talents modélisés

- I5, I8 (T06b, départage, décision 100) : un talent est « modélisé » s'il ne figure dans aucun angle mort `absent` ; I8 (« Rotations non modélisées », `absent`) liste `pyroblast`, `arcanePower`, `missileBarrage` et `improvedScorch`, en partie modélisés depuis T05 (Hot Streak, Arcane Power, décharge Arcane Missiles). À égalité statistique, ils sont traités comme non modélisés. Faut-il découper I8 (rotations absentes seulement) ou marquer ces talents modélisés dans les contextes où leur rotation l'est ?
- I5 (T06b, départage) : la règle ne s'applique qu'au leveling ; les builds de donjon et de raid à écart nul (raid 40 et 60 : points sur des talents sans effet, `docs/research/builds-T05.md`) restent départagés par l'ordre de l'optimiseur de contexte. L'étendre à `optimize_context` ?
- I5 (T06b, audit du registre) : `modeled_talents` ignore le contexte : Blast Wave et Improved Cone of Cold, lus seulement par les rencontres de zone et le profil PvP, comptent comme modélisés en leveling où leur effet est nul (à égalité, ils passent devant un talent de C9 ou F6). Filtrer par contexte (`angle_mort` limité au leveling) ?

## Plugin : contrôle des chiffres, hook Stop, longueur des réponses

- Plugin (T06, décision 93, **résolue** en T06b : `points`, `derived`, `monte_carlo_stats`, `advantage`) : le contrôle des chiffres compte comme alerte un chiffre juste calculé par le modèle (somme des points d'un build, effet au maximum des cumuls). Ajouter ces totaux aux sorties des outils (points par arbre dans `forever_build`) ou accepter certains calculs simples ? Et faut-il passer le hook Stop en reprise forcée (`decision: block`) maintenant que le passage 2 n'a aucune fausse alerte ?
- Plugin (T06, D3) : la longueur des réponses (courte par défaut) n'est pas mesurée par l'évaluation ; un correcteur de longueur (nombre de lignes avant le pied de réponse) serait à ajouter si les réponses restent longues à l'usage.

## Données : copies du seed

- Données (T06b, décision 98) : le mode seed d'une version future a besoin des copies `_seed_*.json` ; `forever decode` ne les hérite pas (comme `_source_gunba_mage_tree.json`). À reprendre par l'installation d'une nouvelle version (T08) : copier les copies du seed, ou limiter le mode seed à 1.60.1.70009.

## Correction Questie

- Correction Questie → Forever (T04b, registre H11 ; sensibilité relevée le 2026-10-06, T08d, question MON6) :
  médiane des rapports « PV mesuré / PV Questie » par niveau, moindres carrés **non pondérés** sur les médianes
  supérieures à 1, rapport hors mesure = max(1, droite). Chaque niveau pèse autant, qu'il compte 11 PNJ (niveau 19)
  ou un seul (niveaux 21 et 24 en r5), et le haut de la plage décide de la pente. Décomposition sur la révision 5
  corrigée (pente 0,0299) : garder Muglash, seul point du niveau 25, la ramène à 0,0261 ; Vorsha the Lasher, à
  0,0285 ; Ilkrud Magthrull, à 0,0312 ; Sarilus Foulborne, à 0,0323 ; Talen, Therylune, Gamon et Teo Hammerstorm
  n'y changent rien.
- **Retenue le 2026-10-06 : Theil-Sen pondéré** (décision 190, révision 6 de 1.60.1.70170). Comparaison faite avant le choix (sonde du 2026-10-06, mêmes paires que `fit_questie_correction`, intervalle à 95 %
  par rééchantillonnage des PNJ, 4 000 tirages, graine 12345 ; PV = médiane Questie des PNJ normaux × rapport) :

  | Méthode | Révision | Pente [IC 95 %] | Retrait d'un PNJ | PV 25 | PV 30 | PV 40 | PV 60 |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | actuelle | r4 | 0,0238 [0,0196 ; 0,0358] | 0,0232 à 0,0262 | 1 010 | 1 540 | 3 110 | 7 420 |
  | actuelle | r5 | 0,0299 [0,0211 ; 0,0339] | 0,0285 à 0,0312 | 1 064 | 1 647 | 3 404 | 8 374 |
  | pondérée par le nombre de PNJ | r4 | 0,0245 [0,0196 ; 0,0407] | 0,0243 à 0,0290 | 1 012 | 1 547 | 3 136 | 7 517 |
  | pondérée par le nombre de PNJ | r5 | 0,0318 [0,0219 ; 0,0371] | 0,0298 à 0,0325 | 1 080 | 1 680 | 3 494 | 8 669 |
  | Theil-Sen pondéré | r4 | 0,0248 [0,0240 ; 0,0340] | 0,0247 à 0,0250 | 1 013 | 1 550 | 3 144 | 7 547 |
  | Theil-Sen pondéré | r5 | 0,0251 [0,0245 ; 0,0351] | 0,0250 à 0,0262 | 1 016 | 1 555 | 3 159 | 7 597 |

  Les moindres carrés pondérés ne stabilisent pas : le niveau 19 (11 PNJ, rapport 1,42, au-dessus de ses voisins)
  pèse alors le plus. Theil-Sen pondéré (médiane des pentes entre paires de niveaux, poids n_i × n_j ; ordonnée =
  médiane des résidus) résiste à un point isolé : pente presque identique en r4 et en r5, amplitude au retrait d'un
  PNJ divisée par 2 (r5) à 10 (r4). Extrapolation bornée proposée : au-delà du dernier niveau mesuré, valeur centrale
  avec sa bande à 95 % dans `monsters.json`, certitude `suppose`, et le simulateur avertit quand le niveau joué est
  hors de la plage mesurée : **non retenue à ce jour** (seule la méthode d'ajustement a été choisie) ; les niveaux
  au-delà de la plage mesurée restent `suppose`.
