# Spécification — forever-core

## Objectif
Répondre à toute question sur WoW Forever avec des chiffres exacts pour la version en cours du jeu, adaptés aux personnages du joueur, et dire à chaque réponse sur quelle version et avec quelle certitude.

## Vocabulaire
- **Version du jeu** (build client) : numéro des fichiers publiés par Blizzard, par exemple 1.60.1.70009. Produit TACT de la bêta : `wow_classic_beta`.
- **Build de personnage** : talents, équipement, rotation d'un personnage.
- **Certitude** : `certain` (lu dans le client), `probable` (calculé par une formule du client, ou recoupé), `suppose` (hérité de Classic ou estimé).

## Utilisateur
Un joueur expert qui utilise Claude Code au quotidien. Il veut : savoir quoi jouer et comment, optimiser talents, équipement et consommables, préparer un raid, et être prévenu de ce que chaque nouvelle version change pour ses personnages.

## Fonctionnalités
| Priorité | Fonctionnalité | Détail |
| --- | --- | --- |
| P0 | Fraîcheur | `forever status` : version locale, dernière version publiée, statut `fresh`, `stale`, `unknown` ou `silent` |
| P0 | Consultation | Sorts, talents, objets, consommables, raciaux, avec provenance |
| P0 | Mécaniques | Registre d'environ 120 mécaniques, couvert par des tests |
| P0 | Leveling | Temps par monstre, XP par heure, ordre de talents optimal, conseil de respec |
| P1 | Raid | DPS analytique et Monte Carlo par build, comparaison au simulateur wowsims Forever |
| P1 | Graphiques | Images générées par outil : temps par niveau, comparaison de builds, gains d'équipement, écarts entre versions |
| P1 | Mémoire joueur | Fiches de personnages dans le vault, importées depuis l'addon d'export |
| P1 | Veille | Détection de version toutes les 6 h, diff, compte rendu d'impact par personnage |
| P2 | Équipement | Base d'objets par formules du client, optimiseur sous contraintes |
| P2 | Consommables | Plan par zone, métier et budget (flacons conditionnés par zone, non-cumuls, recharges partagées) |
| P2 | Autres classes | Paladin, puis Démoniste, puis les six autres |
| P3 | Autres surfaces | Serveur MCP distant pour Claude.ai et ChatGPT ; site statique par version |

## Hors périmètre
- Automatiser le jeu ou capturer le trafic réseau.
- Recopier le contenu protégé des guides (seulement des faits sourcés).
- Prédire un duel PvP : le PvP reste un profil comparatif, marqué `suppose`.

## Contraintes
- La bêta publie environ une version par semaine : tout doit se régénérer automatiquement.
- Le client ne contient ni PV des monstres, ni quêtes, ni taux de butin : ces données sont communautaires et marquées comme telles.
- Coût en tokens maîtrisé : les données ne passent jamais dans le contexte, seulement des résultats compacts.
