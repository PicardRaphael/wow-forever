---
name: forever-leveling
description: "Leveling du Mage dans WoW Forever : temps pour tuer un monstre, XP par heure (XP/h), repos et mana à un niveau, ordre des talents pendant la montée de niveau, faut-il respec et à quel niveau, quelle zone ou quel donjon faire à mon niveau. Déclencher pour « je suis niveau N », « combien de temps par monstre », « XP/h », « quel talent au prochain niveau », « respec », « où aller à mon niveau ». Pas pour WoW retail ni WoW Classic hors Forever, ni pour la programmation."
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
- **Respec ou prochain talent à un niveau plus haut que celui du profil** : planification (section du même nom
  de `format-reponse.md`) : talents du profil en `current`, chemin projeté `respec.projected` ; le build n'est
  demandé que si le profil n'en a aucun. Question qui contredit le profil (« tout en Feu ») : elle l'emporte ;
  écart signalé, mise à jour proposée, puis rangs exacts demandés ou build conseillé de ce type supposé et annoncé.
- Build actuel donné en clair (« j'ai Improved Frostbolt au max ») : traduis en clés de talent avec
  `forever_lookup(kind="talent", name=…)` (la clé est le champ `id`).

## Quel outil
| Question | Appel |
|---|---|
| Temps par monstre, XP/h, repos, dégâts subis | `forever_sim_leveling(level, race, rotation, talents)` : champs `monte_carlo` et `analytic` (`combat`, `downtime`, `total`, `xp_h`) et `mob_hp` |
| Quel talent prendre au niveau N depuis mon build | `forever_build(context="leveling", level=N, race, current=<build actuel du niveau précédent>)` : bloc `next_step` (`choice`, `decided_by`, `candidates` avec écart et intervalle) |
| Ordre des talents depuis le premier niveau de talent | `forever_build(context="leveling", level, race)` : `talents`, `order` (avec `decided_by`), `reasons` |
| Suivre cet ordre en jeu avec Talents Forever | même appel : bloc `export.talents_forever` (`link`, `import` : `/tf import <code>`, ordre compris), recopié tel quel |
| Faut-il respec, à quel niveau | `forever_build(context="leveling", level, current=<build actuel>, respecs=<nombre déjà fait>)` : bloc `respec` |
| Zone ou donjon à mon niveau | `forever_lookup(kind="zones", level, faction)` |
| Pourquoi ce résultat (mécanique) | `forever_explain_mechanic(mechanic_id=<identifiant ou mots>)` |

- `rotation` : `frost`, `fire` ou `arcane`. Sans préférence du joueur, prends la rotation du build conseillé par
  `forever_build` (bloc `choices`).
- `talents` de `forever_sim_leveling` : dictionnaire clé → rang, par exemple le champ `talents` d'un rapport de
  `forever_build`.
- Comparer plusieurs niveaux, rotations ou builds, ou demander le preset `complet` : confie le calcul au sous-agent
  `forever-sim-runner` et reprends son résumé.
- `forever_lookup(kind="zones")` lit l'addon Questie sur le disque du joueur (dossier `FOREVER_WOW_DIR`) : en erreur,
  dis que Questie est introuvable et comment régler `FOREVER_WOW_DIR` ; la liste est à certitude `suppose`
  (base Classic Era, quêtes propres à Forever non couvertes : tranche T04d).

## Lire les résultats
- **Prochain talent** (`next_step`) : donne `choice` et sa raison (`decided_by` : `monte_carlo`, écart significatif ;
  `modelise`, égalité départagée en faveur du talent modélisé ; `non_departage`, choix non départagé par le calcul :
  cite les candidats à égalité). Pas de `current` : `next_step` est vide, demande le build actuel.
- **Monte Carlo** et **analytique** : donne le Monte Carlo ; si `analytic_gap` est grand, signale l'écart.
- **PV du monstre** (`mob_hp`) : sa source et sa certitude comptent ; une valeur `suppose` fait baisser la certitude
  de la réponse.
- **Respec** : donne le conseil du bloc `respec` (coût, gain, niveau conseillé), sans le recalculer ; chemin
  projeté depuis le build actuel : `respec.projected` (`steps` : talent de chaque niveau ; `talents` et `points` au
  niveau demandé).
- **Angles morts** : `blind_spots` du rapport de build ; XP de Forever et quêtes propres au serveur : non modélisées
  (tranche T04d), à dire quand la question porte sur l'XP.

## Hors de ce skill
- Détail d'un sort ou d'un talent, build de donjon, de raid ou de PvP : skill `forever-mage`.
- Autres classes, métiers, réputations, Legacy : carte du skill `forever-router` (« je ne sais pas » + tranche).
