# Feuille de route

État au 2026-10-22, réécrit avant la sortie de WoW Forever du 4 novembre. Trois parties : ce qui est fait (par
grands blocs), ce qui attend l'essai en jeu du 4 novembre, ce qui vient après la sortie ; puis les tranches devenues
caduques avec les décisions 288 à 297. Le détail de chaque tranche faite est dans son plan (`tasks/archive/`), ses
décisions (`docs/DECISIONS.md`) et l'historique de ce fichier (version tranche par tranche jusqu'au commit `64077cf`).

Règles qui gouvernent la suite (elles l'emportent sur tout texte plus ancien) :
- **Une tranche à la fois**, dans l'ordre de la partie 3, plan d'abord (`/tranche`), méthode de `CLAUDE.md`.
- **Lire et alimenter ce qui existe** (décision 288) : deux questions écrites dans chaque plan, « qui maintient déjà
  ça mieux que nous ? » et « que se passe-t-il au prochain patch ? » ; si tout casse au prochain patch, on ne le
  construit pas.
- **Calculs réutilisés** (décision 293) : les calculs viennent des simulateurs de la communauté par des adaptateurs
  minces, épinglés et mis à jour par la veille ; aucun nouveau code de calcul qui recopie une mécanique du jeu ; le
  moteur du Mage est **gelé** à la révision 7 de 1.60.1.70450 (décision 294) et ne sert plus que sous le niveau 60, en
  recoupement des journaux.
- **Forever seulement** (décision 294) : rien de la Classic ni de Season of Discovery, ni données ni mécanismes ; une
  source qui ne couvre pas Forever n'est pas prise.
- **Les addons installés d'abord** (décision 272) et **mon interface est la mienne** (décision 274).
- **Rien n'est fini sans l'essai en jeu** de l'utilisateur (décision 273), sauf les feuilles de route acceptées par la
  recette (décision 279).
- **Mise à jour automatique complète** (décisions 295 à 297) : la veille installe d'elle-même et prévient (carte
  « Mis à jour », `forever update status`, `forever update undo <id>`).

## 1. Ce qui est fait

### Données du client et mises à jour
- **Pipeline et installation** (T01, T03, T06b, T08a) : `forever builds|fetch|decode|diff|verify|report`, données
  versionnées par version du jeu (`forever/data/<version>/`), installation d'une nouvelle version ou d'une révision
  numérotée (`forever install`), provenance sur chaque sortie, `forever status`.
- **Ce qui doit suivre les mises à jour** (T08b) : ratios du personnage décodés du client, origine déclarée de chaque
  valeur (`origins.json`, contrôle dans `verify`), `forever addons status`, `Hotfix.log`, veille des notes officielles
  (à la main, décision 148), sonde de l'API Blizzard (`forever api probe`).
- **Correctifs du serveur** (T08c, décisions 207, 290) : `DBCache.bin` décodé et appliqué (origine
  `correctif_serveur`), lu aussi dans les caches vérifiés de Raidbots quand le jeu n'en a pas (`forever hotfixes
  --raidbots`) ; talent ou sort retiré marqué « probablement retiré » et exclu des recommandations (Piercing Ice).
- **Veille automatique** (T08d, T08e, décisions 263, 284, 286, 295 à 297) : `forever update` (jeu, correctifs,
  journaux, addons, guides de Polestar, simulateurs), clone dédié et CI, tâches planifiées ; règles de lecture et
  valeurs écrites à la main installées et reportées à chaque version ; descriptions de talents qui suivent le client ;
  installation sans accord, carte « Mis à jour » en mots de joueur, « Annuler » ; écarts de fusion tranchés par
  version (observation plus ancienne remplacée et dite, même version gardée et signalée) ; sort retiré gardé, marqué
  et jamais recommandé.
- **Sources d'abord** (décisions 288 à 291) : registre des sources et fraîcheur par le contenu (`forever/sources.py`,
  ligne « Sources » de `forever status`, repli « calcul en cours de mise à jour ») ; inversion de fixture
  (`VALUES_VERSION`) : une nouvelle version donne un rapport des valeurs qui changent, plus des tests rouges.
- **Lancement** (LN1) : découverte des installations (`forever wow list|adopt|forget`), produit jamais deviné,
  `forever doctor`, `forever backup`, personnages de la bêta archivés, `docs/LANCEMENT.md`.

### Calcul
- **Moteur du Mage** (T02, T04a à T04c, T04e, T05, refonte de 1.60.1.70450 et HF2, décisions 285, 292) : sorts et
  talents du client, simulateurs de leveling (Monte Carlo et analytique), builds par contexte avec départage au Monte
  Carlo, respec ; **gelé en r7** (décision 294) et dit comme tel dans chaque provenance.
- **Simulateur de la communauté au niveau 60** (décisions 293, 294 ; remplace SIM1 telle qu'écrite) :
  `wowsims/forever` compilé en local à un commit épinglé (`forever sims update|presets|races`), outil MCP
  `forever_simulate` (préréglages, races, classes comparées dans des conditions identiques), poids de l'équipement au
  60 pour toutes les spécialisations de dégâts (Naowh, Forever Companion), étape `simulateurs` de la veille.
- **Leveling et XP de Forever** (T04d, T04f) : XP des monstres et des quêtes lue dans le client (`QuestXP`,
  `PerKill`, `questcache.wdb`), livre des quêtes fusionné des sources Forever (plus la base Classic Era de Questie,
  décision 294), bonus d'XP cumulés (sac de couchage, nourriture, repos, perk Legacy, camp), `forever xp check`.
- **Mesures** (T04a) : journaux de combat et ForeverLogger (PV des monstres, coûts, intervalles, XP relevée),
  `forever measures refresh`, table des monstres ; valeurs héritées de la Classic recensées et dites
  (`forever origins classic`).

### Savoir des neuf classes et des domaines
- **Profil et PvP** (PV1) : `forever profile import` multi-sources, fiches PvP des neuf classes depuis le client
  (contrôles, catégories de rendement décroissant, défensifs, raciaux, bijoux), fiches d'affrontement.
- **Builds de toutes les classes** (PV1, FA1, sources (b)) : légalité sur le client, builds populaires de Talents
  Forever, guides et rotations de Forever Companion (`class_guide`), codes Talents Forever et Naowh.
- **Familiers du Chasseur** (CH0) ; **donjons** (DJ1 : livre des donjons fusionné, butin, placement) ; **métiers**
  lus dans SkillUp Forever (`forever_lookup profession`, assistant Métier du pont) ; **réputations** lues en jeu
  (liste des factions de l'assistant, étude `docs/research/reputations-forever.md`).
- **Équipement** (T10a faite comme blocs 4 à 4d de CJ1) : poids, liste BiS personnelle (`!NBIS1!`), poids exportés
  (`NFSW1:`, Pawn v1), équipement par niveau ou tranche, route d'équipement ; au 60, poids de wowsims/forever.
- **Exports** (EX1) : Talents Forever, builds Naowh (`!NFB1!`), macros (`!NFM1!`), profils EllesmereUI éteints par
  défaut (décision 274).

### Routes
- **Feuilles de route RestedXP** (RX1, RX1c, bloc 1 de CJ1, décisions 277 à 279, 289) : départ de la position
  réelle, quêtes faites retirées, donjons avec leurs quêtes et quêtes de classe par défaut, garde-fous, recette face
  aux parcours gratuits de RestedXP (`forever route recette`), base adaptée avec attribution, guides de Polestar comme
  squelette au-delà, livraison dans RestedXP par le pont ; zones disputées signalées selon le type de serveur déclaré.

### En jeu
- **Plugin Claude Code** (T06) : skills, routeur, hooks, évaluation.
- **Pont en jeu** (P06a, P06b, blocs 2, 3, 5, 6a et 6b partiel de CJ1) : fenêtre ForeverBridge à barre latérale,
  conversation et plusieurs conversations, boutons et actions sans le modèle, liens d'export, cartes de mise à jour.

## 2. En attente de l'essai en jeu du 4 novembre

Rien de ce qui suit n'est accepté avant l'essai de l'utilisateur (décision 273). La procédure unique est
`docs/LANCEMENT.md`, section « Essai en jeu de CJ1 », après l'installation de la version finale (sections « PC de
jeu » et « Portable ») ; un défaut passe devant tout le reste de la partie 3.

| Bloc livré | Procédure (`docs/LANCEMENT.md`) |
| --- | --- |
| Fenêtre et conversation (CJ1, blocs 6a et 2) | § 1 |
| Feuille de route de leveling (CJ1, bloc 1, RTE8) | § 2 |
| Équipement et route d'équipement (CJ1, blocs 4, 4b, 4c, 4d) | § 3 |
| Talents dès le niveau 1, EllesmereUI éteint (CJ1, blocs 3 et 5) | § 4 |
| Refonte du Mage de 1.60.1.70450, correctifs lus chez Raidbots, HF2 (décisions 285, 290, 292) | § 5 |
| Bloc 6b livré : PvP « Comment jouer contre lui », assistant par type de route, plusieurs conversations | § 6 |
| Sources d'abord : registre des sources, Forever Companion, SkillUp, Polestar (décisions 288 à 291) | § 7 |
| Simulateur au 60, Forever seulement, type de serveur (décisions 293, 294) | § 7b |
| Mise à jour automatique complète, écarts de fusion, sort retiré (décisions 295 à 297) | § 7c |

Le même jour : produit de la version finale adopté et numéro d'interface relevé (LNC1, LNC2, DON4), correctifs de la
version finale lus (HF1), puis les tests restés en attente (`docs/LANCEMENT.md`, « Tests en jeu restés en attente »,
tous facultatifs). CJ1 se clôt à l'accord de l'utilisateur, bloc par bloc (`tasks/plan-corrections-jeu.md`).

Pas encore livrés, à faire avant la sortie s'il reste du temps, sinon en tête de la partie 3 : fin du bloc 6b
(réponses en cartes et équipement en cartes repliables, derrière un réglage, décision 287) et bloc 1d (vols et pierre
de foyer dans nos trajets).

## 3. Après la sortie

Ordre de travail. Chaque tranche commence par l'étude de l'existant (décisions 264, 272) et les deux questions de la
décision 288 ; une tranche gardée par un événement extérieur est sautée tant que la condition n'est pas remplie.

| Tranche | But | Dépend de |
| --- | --- | --- |
| CJ1 (fin) | Corrections de l'essai du 4 novembre ; fin du bloc 6b (cartes, puis bascule du défaut après essai) ; clôture | essai du 4 novembre |
| VF1 | Version finale suivie : rapport des valeurs qui changent, `VALUES_VERSION` montée en une fois ; valeurs héritées de la Classic remplacées par des valeurs Forever lues ou mesurées | sortie, veille |
| BL1 | Base locale unique (`<cache>/kb/`) : pilote quêtes et donjons, puis objets, PNJ, sorts, zones | VF1 |
| SIM2 | Simulation sous le 60 par un simulateur de la communauté, selon la réponse des auteurs | condition : réponse de wowsims/forever#624 ou de SimsForeverExporter#1 |
| CM1 | Chaman calculé sans moteur à nous : 60 par wowsims, dessous par SIM2 ou mes journaux | SIM2 pour le dessous du 60 |
| RX2 | Routes : vols et foyer (si 1d n'est pas fait), quêtes lancées par un objet, optimiseur P1 à P6, monstres en chemin | VF1 |
| RP1 | Réputations : route de réputation (bloc 4e de CJ1) sur ce qui est lisible | BL1 souhaitable |
| PV2 | PvP : champs de bataille, récompenses, monde ouvert, rendements décroissants mesurés | condition : ouverture des champs de bataille |
| AN1 | Analyse PvP de mes combats, depuis mes journaux | PV2 |
| MT1 | Métiers : ce que SkillUp Forever ne fait pas | — |
| LG1, LG2 | Legacy : catalogue, conseil, suivi | — |
| T07 | Mémoire joueur : import complet | — |
| EC1 | API Blizzard : hôtel des ventes, personnages, PvP | condition : couverture de Forever par l'API vérifiée (LEG2) |
| AN2 | Analyse PvE de mes combats, depuis mes journaux | AN1 |
| T08 | Reste de la veille : note d'impact par personnage, comparaison de deux versions par le MCP | VF1 |
| T10 | Plan d'équipement complet : coûts, réputation, PvP, raid | RP1, PV2, EC1 |
| T11 | Consommables et préparation de raid | T10 |
| T13 | (Option) Serveur MCP distant pour Claude.ai et ChatGPT | — |

### CJ1 (fin) — Corrections de l'essai et réponses en cartes
- Défauts relevés à l'essai, dans l'ordre où ils gênent le jeu ; bloc « accepté » à l'accord de l'utilisateur.
- **Réponses en cartes** (décision 287) : historique en cartes (titre, certitude, boutons dans la carte), équipement
  en cartes repliables, aperçu de route dans l'écran Feuille de route ; derrière un réglage, puis défaut si l'essai
  est bon ; ancienne fenêtre gardée derrière `/fv classique` jusqu'à l'accord (décision 280), son sort se décide
  alors.

### VF1 — Version finale suivie
- La veille installe la version finale d'elle-même (décision 295) ; le rapport des valeurs qui changent est relu,
  puis `VALUES_VERSION` est montée en une fois, attentes des tests mises à jour ensemble (`tasks/plan-sources.md`,
  § 5.3).
- Valeurs héritées de la Classic (`forever origins classic`, `docs/research/valeurs-classic-2026-10-21.md`) : chacune
  remplacée par la valeur de Forever lue dans le client ou mesurée dans mes journaux, sinon gardée, marquée et dite
  (décision 294) ; questions concernées : LVL2, LVL7, LVL8, MON4, PVP1.
- Mesures de la bêta remesurées sur la version finale (`forever measures inherited`).

### BL1 — Base locale
- Conception faite (`docs/research/base-locale-2026-10-21.md`, `tasks/plan-sources.md` § 5.7, décision 291) : une
  seule base dans le cache, jamais dans le dépôt (décision 133) ; étage 1, une sortie par source avec sa clé
  d'empreintes ; étage 2, fusion SQLite `STRICT` par type d'entité, provenance par champ, recherche par mot sur les
  noms seulement ; reconstruction plutôt que migrations ; construite à la fin de la veille, au démarrage du pont et au
  premier appel.
- Pilote : quêtes et donjons (caches actuels de 194 Mo et 14 Mo sans arrêt anticipé), mesure, puis objets, PNJ,
  sorts, zones. Outils : résumé et identifiants d'abord, détail à la demande, sorties sous 10 000 jetons.

### SIM2 — Simulation sous le niveau 60
- Questions envoyées le 2026-10-21 (`tasks/messages-auteurs.md`) : wowsims/forever#624 (autres niveaux que le 60,
  publication des binaires) et Blueteak/SimsForeverExporter#1 (publication du moteur de leveling de Sims Forever).
- **Si l'un des deux répond oui** : adaptateur mince, épinglé et mis à jour par la veille, sur le modèle de
  `forever/sims/` ; il remplace le moteur du Mage gelé et donne le leveling des autres classes (temps par monstre, XP
  par heure, builds par niveau), certitude `suppose`, recoupé par mes journaux.
- **Sinon** : rien n'est construit (décision 293) ; sous le 60, le Mage reste au moteur gelé, les autres classes au
  temps par monstre mesuré dans mes journaux, sinon « non calculé » ; la veille regarde à chaque passage si l'une des
  deux sources change (question SIM1 de `docs/OPEN_QUESTIONS.md`).

### CM1 — Calcul du Chaman
- Plus de moteur du Chaman écrit par nous (décision 293 ; l'ancien contenu « table de mêlée, soins, totems,
  horions » est caduc). Au 60 : dégâts, poids et races par wowsims/forever (fait pour les spécialisations de dégâts) ;
  Restauration : non calculé tant qu'aucun simulateur ne couvre les soins.
- Sous le 60 : SIM2 dès qu'il existe ; d'ici là, temps par monstre et XP par heure du Chaman mesurés dans mes
  journaux de leveling (ForeverLogger), builds et rotations de Forever Companion, ordre de prise des talents généré et
  dit comme tel, fiche PvP du client (déjà faite).
- Même règle pour les autres classes (CH1, DE1, PA1, GU1, VO1, PR1, DR1), dans l'ordre de priorité de l'utilisateur
  (décision 232) : chaque classe gagne ce que SIM2 et mes journaux permettent, sans moteur à nous (partie 4).

### RX2 — Routes comme en jeu
- **Vols et pierre de foyer** (bloc 1d de CJ1 s'il n'est pas fait avant la sortie, RTE3, registre I19) : vols
  connus du personnage (vus par le pont ou gardés au profil), durée des vols du client, foyer et sa recharge ; la
  recherche choisit entre marche, vol et foyer.
- **Quêtes lancées par un objet ou sans donneur positionné** (RTE4) : objet de départ et lieu où il tombe.
- **Optimiseur** (`docs/research/routes-methodes-2026-10-21.md`, idées réécrites et citées, aucun code repris) :
  P1 évaluation incrémentale, P2 insertion dans le squelette avec codes de raison, P3 vols, foyer et monstres tués en
  chemin (RTE5), P4 objectif avec pénalités et acceptation tardive, P5 fenêtre glissante exacte, P6 trous (contenu
  30-60 de Forever) ; chaque point jugé sur la recette, jamais sur le seul temps simulé.
- Trajets exacts dans les capitales (tuiles de navigation de Journeys, RTE8) ; comparaisons à RestedXP, Polestar et
  Factoruide refaites avec ces trajets ; recette refaite sur la version finale.
- Autres routes sur demande (idées du chat du 2026-10-14 et du 2026-10-15) : métier (itinéraire de SkillUp Forever,
  maîtres, récolte sur le chemin), sous les mêmes garde-fous.

### RP1 — Réputations
- **Route de réputation** (bloc 4e de CJ1 ; `tasks/archive/idees-du-chat-2026-10-15-reputations.md`) : « monte ma
  réputation avec X » : palier actuel (lu en jeu, fait), palier visé, toutes les sources de la faction ordonnées
  (quêtes avec leur gain, objets à rendre, monstres avec leur nombre jusqu'au palier visé et le plafond éventuel),
  temps estimé, livraison dans RestedXP comme les autres routes.
- Seulement ce qui est lisible (client, Forever Guide, Naowh, Questie, Forever Companion, notes officielles) ; ce qui
  manque reste dit : REP1 à REP5. Gains réels relevés par ForeverLogger (relevé de DJ1).
- Hors périmètre : valeur chiffrée des récompenses (T10).

### PV2 — PvP : champs de bataille et monde ouvert
- Champs de bataille (liste, niveaux, objectifs, récompenses), équipement PvP et coûts (note du 01/10 : coûts
  relevés, plafond d'honneur, registre K6), monde ouvert selon le type de serveur (TERR1).
- Rendements décroissants **mesurés** dans mes journaux de champs de bataille (`forever logs pvp`,
  `docs/research/pvp-dr-protocole.md`), qui remplacent les règles héritées de la Classic (PVP1 à PVP4, PVP6).
- Fixture de journal anonymisée ; rien d'annoncé deviné.

### AN1 — Analyse PvP de mes combats
- Lecture de mes journaux, hors du jeu : contrôles donnés et subis avec leur rang, recharges gâchées ou tardives,
  interruptions, morts et leurs causes, cibles ; comparaison aux fiches d'affrontement de PV1 ; autres joueurs
  anonymisés (décision 49). `forever analyze`, outil MCP, skill `forever-analyse-pvp`, bouton « Analyse du dernier
  combat ». Aucun duel simulé.

### MT1 — Métiers
- S'appuie sur SkillUp Forever et Forever Companion (décisions 272, 276) ; déjà fait : métiers au profil, recettes qui
  montent encore. Reste : répartition des métiers entre mes personnages (existants et prévus), points Legacy des
  métiers (catalogue de LG1), coût par les prix (EC1).

### LG1, LG2 — Legacy
- LG1 : catalogue des défis, points et arbres de bonus (client, notes officielles, addons) ; conseil par personnage
  chiffré par mes mesures ou par wowsims au 60, jamais par un moteur à nous (LEG1, REP4).
- LG2 : suivi de ma progression Legacy, honneur et rang PvP, lus hors combat par l'addon.

### T07 — Mémoire joueur
- Import complet multi-sources sans changer le schéma du profil : équipement, métiers, réputations, historique,
  quêtes faites ; fiches datées ; écart signalé entre sources, la plus récente l'emporte.

### EC1 — API Blizzard
- Après vérification de la couverture de Forever (`forever api probe`, LEG2) : prix de l'hôtel des ventes, fiches de
  personnages, PvP ; chaque accès réseau demandé au plan et déclaré dans `CLAUDE.md` ; repli sur mes relevés
  d'Auctionator.

### AN2 — Analyse PvE de mes combats
- Lecture de mes journaux : rotation réelle, temps morts, recharge globale gâchée, ressources ; au 60, écart chiffré
  par wowsims/forever quand il sait rejouer le combat ; sous le 60, constat seulement (aucun rejeu par un moteur à
  nous). Skill `forever-analyse-pve`.

### T08 — Reste de la veille
- Note d'impact par personnage (prolonge la carte « Mis à jour »), comparaison de deux versions installées par le
  MCP, certitude abaissée sur un écart non relu ; durcissement du pipeline relevé à la relecture de T03.

### T10, T11, T13
- **T10** : plan d'équipement complet par personnage et par contexte (où l'obtenir, coût, réputation ou rang requis,
  temps estimé) sur les sources lues (addons, DJ1, RP1, PV2, EC1) ; gain d'un objet par wowsims au 60, par les poids
  lus ou gelés dessous. La base d'objets « par formules du client » est caduque (partie 4).
- **T11** : consommables et préparation de raid (listes et coûts ; leur effet au 60 vient de wowsims).
- **T13** : (option) serveur MCP distant.

### Idées notées, non planifiées
- Pouvoir réafficher les cartes masquées (une carte masquée ne revient que si son empreinte change, décision 240).
- Notifications Discord par webhook (adresse dans `.env`, nouvel accès réseau, accord à demander).
- Taille de la réserve du pont (200 emplacements) à revoir avec plus de sessions mesurées.
- FojjiCore : lisible seulement en local tant que ForeverAuras n'est pas installé.
- Lecteur d'AllTheThings (saveur `forever`) s'il est installé, pour les quêtes vues seulement chez Factoruide
  (LVL17).

## 4. Tranches caduques (décisions 288 à 297)

Gardées ici pour que leurs identifiants, encore cités ailleurs, renvoient à leur sort.

| Tranche | Sort | Ce qui la remplace |
| --- | --- | --- |
| T04d | Faite le 2026-10-13 | partie 1 (leveling et XP de Forever) |
| SIM1 | Faite autrement : `wowsims/forever` compilé (ElliotWood/Forever n'existe plus, décision 291) ; conversion des notations décodée chez nous abandonnée (PER8) | partie 1 (simulateur au 60), SIM2 |
| T10a | Faite comme blocs 4 à 4d de CJ1 | partie 1 (équipement) |
| T09 | Caduque : moteur de raid porté du seed, Monte Carlo et parité (décision 293) | wowsims/forever au 60 |
| CM1r, CH1r, PA1r, GU1r, VO1r, DR1r | Caduques avec T09 | wowsims/forever au 60 |
| T05b | Caduque : mana des combats longs ajoutée au moteur (décision 293) | wowsims/forever au 60 ; sous le 60, moteur du Mage gelé |
| CH1, DE1, PA1, GU1, VO1, PR1, DR1 | Caduques comme moteurs de classe (briques de mêlée, soins, mitigation, menace, familier comme entité) : décisions 252 et 293 ; formules reprises de wowsims (décision 233) abandonnées | même règle que CM1 (partie 3) : wowsims au 60, SIM2 ou mes journaux dessous, Forever Companion |
| Moteur générique des classes | Jamais construit (décision 252), confirmé par la décision 293 | — |
| Rencontres et poids du Mage au 60, optimiseur de fin de partie, PvP analytique | Retirés ou gelés (`tasks/plan-simulateurs.md`) | wowsims/forever au 60 |
| Eureka! actif (branche `races`) | Abandonné (nouveau code de calcul) | wowsims/forever |
| T10, base d'objets « par formules du client » | Caduque (formule recopiée) | objets lus (addons, client) |
| AN2, rejeu « à la rotation optimale du moteur de la classe » | Caduc | AN2 réduite (partie 3) |
| Données et règles de la Classic (base Classic Era de Questie, rapprochements Classic) | Retirées (décision 294) | sources Forever, puis VF1 |
| FA1p, ForeverAssist V2 et V3, comparaison d'équipement de ForeverAssist V1 | Fondues ou retirées (décision 202) | P06b, P06a, AN1, AN2, T10a |
| Mode « mise à jour automatique complète » (idée du 2026-10-13) | Refusé par la décision 259, puis adopté par la décision 295 | partie 1 (veille automatique) |
