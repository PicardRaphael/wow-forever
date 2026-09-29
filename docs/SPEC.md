# Spécification — forever-core

## Objectif
Répondre à toute question sur WoW Forever avec des chiffres exacts pour la version en cours du jeu, adaptés aux personnages du joueur, et dire à chaque réponse sur quelle version et avec quelle certitude. L'agent couvre tout le jeu : combat et mécaniques, leveling et quêtes, talents, PvP (champs de bataille et monde ouvert), donjons, raids, équipement, consommables, Legacy, métiers, réputations et économie.

## Vocabulaire
- **Version du jeu** (build client) : numéro des fichiers publiés par Blizzard, par exemple 1.60.1.70009. Produit TACT de la bêta : `wow_classic_beta`.
- **Build de personnage** : talents, équipement, rotation d'un personnage. T05 : build du Mage par contexte (leveling, donjon, raid, PvP en champs de bataille et en monde ouvert) à un niveau donné, avec l'ordre des talents, la raison de chaque choix, l'alternative la plus proche et son écart chiffré, la stabilité, la sensibilité aux hypothèses incertaines, le conseil de respec et les angles morts (`forever build`, `forever_build`).
- **Certitude** : `certain` (lu dans le client), `probable` (calculé par une formule du client, ou recoupé), `suppose` (hérité de Classic ou estimé).
- **Fiche fixe** : information qui ne dépend pas de l'état du combat (sorts, recharges nominales, catégories de contrôle), seule forme d'aide PvP affichable en jeu.

## Utilisateur
Un joueur expert qui utilise Claude Code au quotidien, avec plusieurs personnages de toutes les classes (aujourd'hui un Mage, un Paladin et un Démoniste). Il veut : savoir quoi jouer et comment, optimiser talents, équipement et consommables, préparer ses champs de bataille, ses donjons et ses raids, analyser ses combats après coup, suivre sa progression (Legacy, métiers, réputations), et être prévenu de ce que chaque nouvelle version change pour ses personnages.
Priorités : PvP en champs de bataille, donjons et leveling d'abord ; raid ensuite.

## Fonctionnalités
| Priorité | Fonctionnalité | Détail | Tranche |
| --- | --- | --- | --- |
| P0 | Fraîcheur | `forever status` : version locale, dernière version publiée, statut `fresh`, `stale`, `unknown` ou `silent` | T01 |
| P0 | Consultation | Sorts, talents, objets, consommables, raciaux, avec provenance | T01 à T03 |
| P0 | Mécaniques | Registre d'environ 120 mécaniques, couvert par des tests | T02 |
| P0 | Leveling | Temps par monstre, XP par heure, quêtes et XP de Forever, zone ou donjon adapté au niveau (données de Questie), ordre de talents optimal, conseil de respec ; talent suivant et comparaison d'équipement en jeu | T04b, T04c, T05, FA1 |
| P0 | Profil | Profil du personnage actif (plusieurs personnages, toutes classes) rempli et mis à jour automatiquement depuis ForeverLogger et les journaux ; mise à jour proposée quand le joueur dit « j'ai … » | T06b, PV1 (import minimal), T07 (import complet) |
| P0 | PvP | Savoir des 9 classes (sorts, recharges, contrôles et durées, défensifs, raciaux de toutes les races et des nouvelles combinaisons race et classe, décodés du client, bijoux, rendements décroissants), fiches par affrontement ; champs de bataille (objectifs, récompenses, équipement PvP) et monde ouvert ; rendements décroissants mesurés dans les journaux ; fiche fixe de la classe adverse en jeu | PV1, PV2, FA1p |
| P0 | Analyse de mes combats | PvP (contrôles donnés et subis avec rendements décroissants, recharges utilisées, gâchées ou tardives, burst, interruptions, morts et leur cause, cibles, comparés aux fiches de PV1) ; PvE (rotation réelle, écarts avec la rotation optimale, perte chiffrée par rejeu du même combat, chaque boss) ; taux réels comparés au modèle ; `forever analyze`, outil MCP, rapport avec graphique ; en local, autres joueurs anonymisés | AN1, AN2, FA3 |
| P0 | Toutes les classes | Moteur de chacune des 8 autres classes (ressources, rotations, simulateurs, builds par contexte) pour le leveling, le donjon et le PvP ; raid avec T09 ou la partie raid de la classe ; avant son moteur, builds de la communauté vérifiés sur le client, certitude au mieux supposée | PA1, DE1, PR1, CH1, CM1, GU1, VO1, DR1 ; T09, PA1r à DR1r |
| P0 | Donjons | Niveaux, boss, butin | DJ1 |
| P1 | Legacy | Défis, points, arbres de bonus, conseil des bonus pour chacun de mes personnages, suivi de la progression | LG1, LG2 |
| P1 | Raid | DPS analytique et Monte Carlo par build, comparaison au simulateur wowsims Forever ; toutes les classes | T09, PA1r à DR1r |
| P1 | Graphiques | Images générées par outil : temps par niveau, comparaison de builds, gains d'équipement, écarts entre versions | T04b puis au fil des tranches |
| P1 | Mémoire joueur | Fiches de personnages dans le vault, importées depuis l'addon d'export | T07 |
| P1 | Veille | Détection de version toutes les 6 h, diff, compte rendu d'impact par personnage | T08 |
| P1 | Métiers | Recettes, plan de montée de compétence, points Legacy des métiers, répartition des métiers entre mes personnages | MT1 |
| P2 | Réputations | Factions, paliers, gains, récompenses, plan et suivi | RP1 |
| P2 | Économie | Prix de l'hôtel des ventes par l'API Blizzard, après le lancement du 4 novembre | EC1 |
| P2 | Équipement | Base d'objets par formules du client, optimiseur sous contraintes | T10 |
| P2 | Consommables | Plan par zone, métier et budget (flacons conditionnés par zone, non-cumuls, recharges partagées) | T11 |
| P3 | Autres surfaces | Serveur MCP distant pour Claude.ai et ChatGPT ; site statique par version | T13 |

## Domaines et sources
Chaque valeur garde sa source et sa certitude. « — » : la source n'apporte rien à ce domaine. Les noms de tables du client non encore relevés sont à identifier à l'inventaire de la tranche, jamais présumés.

| Domaine | Données du client | Annonces officielles | Communauté | Journaux de combat | Addon | Tranche |
| --- | --- | --- | --- | --- | --- | --- |
| Mécaniques, sorts, talents (Mage) | Tables Spell* et Trait* (`certain`) | Changements de classe | Recoupement (wowsims, ForeverChanges), `suppose` | Mesures et preuves du registre | Niveau et talents (ForeverLogger) | T02 à T04b |
| Autres classes (moteurs) | Sorts, talents, raciaux de chaque classe (décodés en PV1) | Changements de classe | Builds de la communauté (source et date, `suppose`), wowsims Forever | Mesures de mes journaux de la classe | Niveau et talents (ForeverLogger) | PA1 à DR1 |
| Profil du joueur | — | — | — | Personnages « à moi » | Classe, race, niveau, talents (ForeverLogger) | PV1, T07 |
| Leveling et quêtes | Sorts, points par niveau | Changements d'XP, quêtes de Forever | Questie (PV, quêtes), `suppose` | PV des monstres (`certain`) | Niveau du lanceur, carnet de Questie | T04a à T05 |
| PvP : savoir des classes | Sorts, talents, raciaux, bijoux des 9 classes | Règles PvP de Forever | Guides PvP, faits sourcés, `suppose` | — (mesures en PV2) | Fiches fixes seulement (extension FA1p) | PV1, FA1p |
| PvP : champs de bataille, monde ouvert, rendements décroissants | Cartes, objets PvP, monnaies | Dates, liste, récompenses, règles du monde ouvert | Vendeurs, coûts, stratégie | Mes parties : contrôles et durées, recharges observées après coup | Résultat de partie et honneur hors combat | PV2 |
| Donjons | Instances, niveaux, objets | Donjons nouveaux ou modifiés | Butin et taux (Wowhead), ForeverDungeonJournal en recoupement | Niveau et PV des boss (H1), durées | Butin observé hors combat | DJ1 |
| Legacy | Arbres et défis | Système Legacy, état au lancement | Icy Veins, Wowhead (noms divergents à recouper) | Validation d'un bonus mesurable | Progression du compte | LG1, LG2 |
| Métiers | Recettes, composants, seuils de couleur | Changements de métiers, points Legacy | Entraîneurs, sources de recettes, chance de gain | — | Compétences et recettes connues | MT1 |
| Réputations | Factions, paliers | Réputations de Forever | Gains par source, récompenses | — | Paliers et gains | RP1 |
| Économie | Prix de vente aux marchands | Ouverture et couverture de l'API | — | — | Base de prix d'Auctionator (à vérifier) ; source principale : API Blizzard | EC1 |
| Analyse de mes combats | Sorts, auras et leur classement (PV1) | — | — | Mes journaux (source principale, en local, autres joueurs anonymisés) | Niveau et talents à l'instant du combat | AN1, AN2 |
| Raid, équipement, consommables | Objets et formules du client | Calendrier des raids, changements | wowsims Forever, `alcaras/forever-ref` | DPS mesuré, niveaux des boss | Fiche du personnage | T09 à T11 |

## Réponses de l'agent
- L'agent répond selon la demande, quels que soient la classe et le contexte (leveling, donjon, raid, champs de bataille, monde ouvert), sans ordre imposé : le routeur choisit le skill du domaine ; un skill par domaine et par usage (builds, PvP, analyse PvP, analyse PvE, classes, donjons, Legacy, métiers…), chaque tranche ajoute le sien (décision 115).
- Question personnelle (« mon Mage », « mon perso ») : profil du personnage actif, sinon la donnée manquante est demandée. Question générale (« l'arbre optimal du Mage en raid ») : rien n'est demandé, le calcul part d'une hypothèse neutre annoncée et montre si la race ou une autre donnée personnelle change le résultat (décision 116).
- Planification (décisions 118, 119) : une question posée à un niveau plus haut que celui du profil part du build du profil et du chemin de leveling conseillé projeté jusqu'à ce niveau ; un personnage prévu (pas encore créé) reçoit un plan : builds par niveau, métiers, Legacy. Sans niveau dans une question générale, le niveau maximal vient des données (décision 121).
- Classe pas encore calculée (« donne-moi les talents optimaux du Paladin ») : réponse quand même, par des builds de la communauté trouvés par le sous-agent de recherche, avec source et date, vérifiés légaux sur les données du client et expliqués par ses descriptions de talents (à partir de PV1) ; l'agent annonce que la classe n'est pas encore calculée par le moteur et que la certitude est au mieux supposée ; il ne devine rien (décision 114).

## Hors périmètre
- Automatiser le jeu ou capturer le trafic réseau.
- Recopier le contenu protégé des guides (seulement des faits sourcés).
- Prédire un duel PvP : le PvP reste un profil comparatif, marqué `suppose`.
- Routes de leveling détaillées : le joueur suit RestedXP en jeu (exclu comme source de données) ; l'agent répond seulement « quelle zone ou quel donjon à mon niveau ».
- Suivre en direct les temps de recharge adverses dans un addon : impossible sur Forever (abonnement au journal de combat refusé aux addons, valeurs de combat secrètes, `docs/research/addon-forever.md`). En jeu, seules des fiches fixes s'affichent ; l'analyse des combats se fait après coup sur les journaux.
- Acheter ou vendre à l'hôtel des ventes à la place du joueur.

## Contraintes
- La bêta publie environ une version par semaine : tout doit se régénérer automatiquement.
- Le client ne contient ni PV des monstres, ni quêtes, ni taux de butin, ni listes d'entraîneurs ou de vendeurs, ni gains de réputation : ces données sont communautaires, mesurées ou relevées par l'addon, et marquées comme telles.
- Les prix de l'hôtel des ventes ne sont pas des données de version : ils vivent en cache daté, hors de `forever/data/`, et n'arrivent qu'après le lancement par l'API Blizzard (accès réseau soumis à accord).
- Coût en tokens maîtrisé : les données ne passent jamais dans le contexte, seulement des résultats compacts.
