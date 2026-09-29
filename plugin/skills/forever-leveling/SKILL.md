---
name: forever-leveling
description: "Leveling du Mage dans WoW Forever : temps pour tuer un monstre, XP par heure (XP/h), repos et mana à un niveau, ordre des talents pendant la montée de niveau, faut-il respec et à quel niveau, quelle zone ou quel donjon faire à mon niveau. Déclencher pour « je suis niveau N », « combien de temps par monstre », « XP/h », « quel talent au prochain niveau », « respec », « où aller à mon niveau ». Pas pour WoW retail ni WoW Classic hors Forever, ni pour la programmation."
---

# Leveling du Mage (WoW Forever)

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé » (outils forever introuvables :
message fixe, rien de mémoire), forme de la réponse, règle « je ne sais pas ». Aucun chiffre de mémoire : tout vient
des outils ci-dessous.

## Ce qu'il faut savoir du joueur
- **Niveau** : obligatoire. S'il manque, demande-le (une question courte) avant d'appeler un outil.
- **Race**, **faction**, **build actuel** : utiles ; sans eux, garde le défaut de l'outil et écris-le en hypothèse.
- Build actuel donné en clair (« j'ai Improved Frostbolt au max ») : traduis en clés de talent avec
  `forever_lookup(kind="talent", name=…)` (la clé est le champ `id`).

## Quel outil
| Question | Appel |
|---|---|
| Temps par monstre, XP/h, repos, dégâts subis | `forever_sim_leveling(level, race, rotation, talents)` : champs `monte_carlo` et `analytic` (`combat`, `downtime`, `total`, `xp_h`) et `mob_hp` |
| Quel talent prendre maintenant, ordre des talents | `forever_build(context="leveling", level, race)` : `talents`, `order`, `reasons` |
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
- **Monte Carlo** et **analytique** : donne le Monte Carlo ; si `analytic_gap` est grand, signale l'écart.
- **PV du monstre** (`mob_hp`) : sa source et sa certitude comptent ; une valeur `suppose` fait baisser la certitude
  de la réponse.
- **Respec** : donne le conseil du bloc `respec` (coût, gain, niveau conseillé), sans le recalculer.
- **Angles morts** : `blind_spots` du rapport de build ; XP de Forever et quêtes propres au serveur : non modélisées
  (tranche T04d), à dire quand la question porte sur l'XP.

## Hors de ce skill
- Détail d'un sort ou d'un talent, build de donjon, de raid ou de PvP : skill `forever-mage`.
- Autres classes, métiers, réputations, Legacy : carte du skill `forever-router` (« je ne sais pas » + tranche).
