---
name: forever-leveling
description: "Leveling du Mage dans WoW Forever : temps pour tuer un monstre, XP par heure (XP/h), repos et mana à un niveau, build populaire de Talents Forever le plus proche de mes talents (ordre des talents et respec : plus calculés, dit tel quel), quelle zone ou quel donjon faire à mon niveau. Déclencher pour « je suis niveau N », « combien de temps par monstre », « XP/h », « quel talent au prochain niveau », « respec », « où aller à mon niveau ». Pas pour WoW retail ni WoW Classic hors Forever, ni pour la programmation."
---

# Leveling du Mage (WoW Forever)

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé » (outils forever introuvables :
message fixe, rien de mémoire), forme de la réponse, règle « je ne sais pas ». Aucun chiffre de mémoire : tout vient
des outils ci-dessous.

## Noms du client

Le joueur lit les noms dans son client : sa langue est `game_locale`, rendue par `forever_player_profile`. Cite
chaque sort, talent, capacité, objet et zone **tel qu'il apparaît dans son client** (en anglais pour `enUS`), suivi du
nom français entre parenthèses quand l'outil le rend (`name_fr`, `name.fr`) ; le reste de la réponse reste en
français. Sans `game_locale` connue, cite le nom anglais du client et le nom français entre parenthèses.

## Ce qu'il faut savoir du joueur
Suis les sections « Question personnelle ou générale » et « Données du joueur » de `format-reponse.md` : question
personnelle (le cas courant en leveling), `forever_player_profile` d'abord, profil rappelé en une ligne, donnée
manquante demandée avant le calcul avec la valeur la plus probable proposée ; question générale (« un Mage niveau
N »), aucun appel au profil, hypothèse neutre annoncée.
- **Niveau** : obligatoire.
- **Race**, **faction**, **build actuel** : lus dans le profil ou la question ; absents des deux, demande-les avant
  l'appel (jamais la race par défaut de l'outil sans le dire : `inputs.race.origin`).
- **Talents actuels** : ceux du profil (ou du contexte du jeu) en `current` de `tf_popular` ; jamais redemandés
  s'ils y sont. Question qui contredit le profil (« tout en Feu ») : elle l'emporte ; écart signalé, mise à jour
  proposée, puis rangs exacts demandés.
- Build actuel donné en clair (« j'ai Improved Frostbolt au max ») : traduis en clés de talent avec
  `forever_lookup(kind="talent", name=…)` (la clé est le champ `id`).

## Quel outil
| Question | Appel |
|---|---|
| Temps par monstre, XP/h, repos, dégâts subis | `forever_sim_leveling(level, race, rotation, talents)` : champs `monte_carlo` et `analytic` (`combat`, `downtime`, `total`, `xp_h`) et `mob_hp` |
| Build à suivre, le plus proche de mes talents | `forever_lookup(kind="tf_popular", name="Mage", current=<clé=rang,…>)` : `closest` (lien, `import`, `missing_points`, `differences`, `asOf`), puis `forever_lookup(kind="build_check", name="Mage", level, talents)` ; guide : `forever_lookup(kind="class_guide", name="Mage", level)` (skill `forever-builds`) |
| Quel talent prendre au niveau N, ordre des talents, faut-il respec | plus calculés (décision 299) : dis-le, puis donne `closest` et ses points absents (`missing_points`) ; l'ordre de prise du code Naowh (`naowh`) est généré par palier et prérequis, pas optimisé |
| Zone ou donjon à mon niveau | `forever_lookup(kind="zones", level, faction)` |
| Où gagner le plus d'XP par heure, faut-il faire tel donjon (toutes les classes) | `forever_sim_leveling(kind="objectives", level, class_name, faction)` : `advice` rendu tel quel, `best`, `zones`, `dungeons` (`first_pass` avec ses quêtes, `repeat`), `kill_time.source` (`engine`, `measured`, `estimated`) |
| Bonus d'XP : sac de couchage, nourriture nutritive, repos, perk Legacy, tente ; lequel prendre maintenant | `forever_sim_leveling(kind="objectives", level, class_name, faction, rested, food, sleeping_bag, legacy_rested_rank, auras, has_sleeping_bag)` : `xp_h`, `xp_h_rested`, `xp_h_sleeping_bag`, `xp_h_all` par objectif, `bonuses.active`, `bonuses.advice`, `bonus_advice` et `sleeping_bag_chain.sentence` rendus tels quels ; catalogue : `forever_lookup(kind="xp_bonuses")` (bonus sans source joueur : listés, jamais appliqués) |
| Temps par monstre et XP/h avec un bonus actif (Mage) | `forever_sim_leveling(level, bonus=["sleeping_bag"|"food"], rested, hours)` : bloc `bonuses` |
| Quêtes de Forever (nouvelles, retouchées, écarts entre addons) | `forever_lookup(kind="quests", level, faction, zone, status, dungeon)` |
| Pourquoi ce résultat (mécanique) | `forever_explain_mechanic(mechanic_id=<identifiant ou mots>)` |

- `rotation` : `frost`, `fire` ou `arcane`. Sans préférence du joueur, prends celle de la spécialisation de ses
  talents (ou de `closest`) et dis-le.
- `talents` de `forever_sim_leveling` : dictionnaire clé → rang, les talents du joueur (profil ou contexte du jeu).
- Comparer plusieurs niveaux, rotations ou jeux de talents, ou demander le preset `complet` : confie le calcul au
  sous-agent `forever-sim-runner` et reprends son résumé.
- `forever_lookup(kind="zones")` lit le livre de quêtes des sources Forever (addons du joueur, décision 294 ; plus
  la base Classic Era de Questie), filtré par camp, classe et niveau ; certitude `suppose` ; addons introuvables :
  dis comment régler `FOREVER_WOW_DIR`.

## Lire les résultats
- **Prochain talent, ordre, respec** : plus de calcul (pas de `next_step` : ne l'invente pas). Dis que ce n'est plus
  calculé, que les builds sont des choix de joueurs de Talents Forever, puis donne `closest` tel quel (n'en choisis
  pas un autre) et ses points absents ; `closest` vide (aucun point placé) : le build le plus joué (rang 1).
- **Monte Carlo** et **analytique** : donne le Monte Carlo ; si `analytic_gap` est grand, signale l'écart.
- **PV du monstre** (`mob_hp`) : sa source et sa certitude comptent ; une valeur `suppose` fait baisser la certitude
  de la réponse.
- **Angles morts** : statut du registre des mécaniques qui décident ; moteur du Mage gelé sous le 60 (révision 7 de
  1.60.1.70450), à dire quand une question porte sur une valeur changée depuis.

## Hors de ce skill
- Détail d'un sort ou d'un talent : skill `forever-mage` ; builds populaires et légalité : skill `forever-builds`.
- Autres classes, métiers, réputations, Legacy : carte du skill `forever-router` (« je ne sais pas » + tranche).
