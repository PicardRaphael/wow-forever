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
