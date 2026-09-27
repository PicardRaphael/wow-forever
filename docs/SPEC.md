# Spécification — forever-core

## Objectif
Répondre à toute question sur WoW Forever avec des chiffres exacts pour la version en cours du jeu, adaptés aux personnages du joueur, et dire à chaque réponse sur quelle version et avec quelle certitude. L'agent couvre tout le jeu : combat et mécaniques, leveling et quêtes, talents, PvP (champs de bataille et monde ouvert), donjons, raids, équipement, consommables, Legacy, métiers, réputations et économie.

## Vocabulaire
- **Version du jeu** (build client) : numéro des fichiers publiés par Blizzard, par exemple 1.60.1.70009. Produit TACT de la bêta : `wow_classic_beta`.
- **Build de personnage** : talents, équipement, rotation d'un personnage.
- **Certitude** : `certain` (lu dans le client), `probable` (calculé par une formule du client, ou recoupé), `suppose` (hérité de Classic ou estimé).
- **Fiche fixe** : information qui ne dépend pas de l'état du combat (sorts, recharges nominales, catégories de contrôle), seule forme d'aide PvP affichable en jeu.

## Utilisateur
Un joueur expert qui utilise Claude Code au quotidien, avec un Mage, un Paladin et un Démoniste. Il veut : savoir quoi jouer et comment, optimiser talents, équipement et consommables, préparer ses champs de bataille, ses donjons et ses raids, suivre sa progression (Legacy, métiers, réputations), et être prévenu de ce que chaque nouvelle version change pour ses personnages.
Priorités : PvP en champs de bataille, donjons et leveling d'abord ; raid ensuite.

## Fonctionnalités
| Priorité | Fonctionnalité | Détail | Tranche |
| --- | --- | --- | --- |
| P0 | Fraîcheur | `forever status` : version locale, dernière version publiée, statut `fresh`, `stale`, `unknown` ou `silent` | T01 |
| P0 | Consultation | Sorts, talents, objets, consommables, raciaux, avec provenance | T01 à T03 |
| P0 | Mécaniques | Registre d'environ 120 mécaniques, couvert par des tests | T02 |
| P0 | Leveling | Temps par monstre, XP par heure, quêtes et XP de Forever, ordre de talents optimal, conseil de respec | T04b, T04c, T05 |
| P0 | PvP | Savoir des 9 classes (sorts, recharges, contrôles et durées, défensifs, raciaux, bijoux, rendements décroissants), fiches par affrontement ; champs de bataille (objectifs, récompenses, équipement PvP) et monde ouvert ; rendements décroissants mesurés dans les journaux | PV1, PV2 |
| P0 | Donjons | Niveaux, boss, butin | DJ1 |
| P1 | Legacy | Défis, points, arbres de bonus, conseil des bonus par personnage, suivi de la progression | LG1, LG2 |
| P1 | Raid | DPS analytique et Monte Carlo par build, comparaison au simulateur wowsims Forever | T09 |
| P1 | Graphiques | Images générées par outil : temps par niveau, comparaison de builds, gains d'équipement, écarts entre versions | T04b puis au fil des tranches |
| P1 | Mémoire joueur | Fiches de personnages dans le vault, importées depuis l'addon d'export | T07 |
| P1 | Veille | Détection de version toutes les 6 h, diff, compte rendu d'impact par personnage | T08 |
| P1 | Métiers | Recettes, plan de montée de compétence, points Legacy des métiers | MT1 |
| P2 | Réputations | Factions, paliers, gains, récompenses, plan et suivi | RP1 |
| P2 | Économie | Prix de l'hôtel des ventes par l'API Blizzard, après le lancement du 4 novembre | EC1 |
| P2 | Équipement | Base d'objets par formules du client, optimiseur sous contraintes | T10 |
| P2 | Consommables | Plan par zone, métier et budget (flacons conditionnés par zone, non-cumuls, recharges partagées) | T11 |
| P2 | Autres classes | Moteurs de Paladin, puis Démoniste, puis les six autres (le savoir PvP des 9 classes n'attend pas ces moteurs) | T12 |
| P3 | Autres surfaces | Serveur MCP distant pour Claude.ai et ChatGPT ; site statique par version | T13 |

## Domaines et sources
Chaque valeur garde sa source et sa certitude. « — » : la source n'apporte rien à ce domaine. Les noms de tables du client non encore relevés sont à identifier à l'inventaire de la tranche, jamais présumés.

| Domaine | Données du client | Annonces officielles | Communauté | Journaux de combat | Addon | Tranche |
| --- | --- | --- | --- | --- | --- | --- |
| Mécaniques, sorts, talents (Mage) | Tables Spell* et Trait* (`certain`) | Changements de classe | Recoupement (wowsims, ForeverChanges), `suppose` | Mesures et preuves du registre | Niveau et talents (ForeverLogger) | T02 à T04b |
| Leveling et quêtes | Sorts, points par niveau | Changements d'XP, quêtes de Forever | Questie (PV, quêtes), `suppose` | PV des monstres (`certain`) | Niveau du lanceur, carnet de Questie | T04a à T05 |
| PvP : savoir des classes | Sorts, talents, raciaux, bijoux des 9 classes | Règles PvP de Forever | Guides PvP, faits sourcés, `suppose` | — (mesures en PV2) | Fiches fixes seulement (FA1) | PV1 |
| PvP : champs de bataille, monde ouvert, rendements décroissants | Cartes, objets PvP, monnaies | Dates, liste, récompenses, règles du monde ouvert | Vendeurs, coûts, stratégie | Mes parties : contrôles et durées, recharges observées après coup | Résultat de partie et honneur hors combat | PV2 |
| Donjons | Instances, niveaux, objets | Donjons nouveaux ou modifiés | Butin et taux (Wowhead), ForeverDungeonJournal en recoupement | Niveau et PV des boss (H1), durées | Butin observé hors combat | DJ1 |
| Legacy | Arbres et défis | Système Legacy, état au lancement | Icy Veins, Wowhead (noms divergents à recouper) | Validation d'un bonus mesurable | Progression du compte | LG1, LG2 |
| Métiers | Recettes, composants, seuils de couleur | Changements de métiers, points Legacy | Entraîneurs, sources de recettes, chance de gain | — | Compétences et recettes connues | MT1 |
| Réputations | Factions, paliers | Réputations de Forever | Gains par source, récompenses | — | Paliers et gains | RP1 |
| Économie | Prix de vente aux marchands | Ouverture et couverture de l'API | — | — | Base de prix d'Auctionator (à vérifier) ; source principale : API Blizzard | EC1 |
| Raid, équipement, consommables | Objets et formules du client | Calendrier des raids, changements | wowsims Forever, `alcaras/forever-ref` | DPS mesuré, niveaux des boss | Fiche du personnage | T09 à T11 |

## Hors périmètre
- Automatiser le jeu ou capturer le trafic réseau.
- Recopier le contenu protégé des guides (seulement des faits sourcés).
- Prédire un duel PvP : le PvP reste un profil comparatif, marqué `suppose`.
- Suivre en direct les temps de recharge adverses dans un addon : impossible sur Forever (abonnement au journal de combat refusé aux addons, valeurs de combat secrètes, `docs/research/addon-forever.md`). En jeu, seules des fiches fixes s'affichent ; l'analyse des combats se fait après coup sur les journaux.
- Acheter ou vendre à l'hôtel des ventes à la place du joueur.

## Contraintes
- La bêta publie environ une version par semaine : tout doit se régénérer automatiquement.
- Le client ne contient ni PV des monstres, ni quêtes, ni taux de butin, ni listes d'entraîneurs ou de vendeurs, ni gains de réputation : ces données sont communautaires, mesurées ou relevées par l'addon, et marquées comme telles.
- Les prix de l'hôtel des ventes ne sont pas des données de version : ils vivent en cache daté, hors de `forever/data/`, et n'arrivent qu'après le lancement par l'API Blizzard (accès réseau soumis à accord).
- Coût en tokens maîtrisé : les données ne passent jamais dans le contexte, seulement des résultats compacts.
