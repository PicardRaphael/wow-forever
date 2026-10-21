# Méthodes de calcul des routes de leveling : état de l'art et rôle restant de notre optimiseur (2026-10-21)

Recherche web en lecture seule du 2026-10-21 (aucun clone, téléchargement ni exécution). Prolonge les décisions 266
(Factoruide), 268 et 277 (parcours gratuits de RestedXP), 278 (Polestar), 279 (acceptation par ressemblance) et 288
(lire et alimenter ce qui existe). Les chiffres des outils extérieurs sont **leurs affirmations**, datées, de certitude
**suppose** au mieux : aucun n'est une règle de jeu ni n'entre dans `forever/data/` sans source et sans décision.
Aucun code n'est repris : les idées sont réécrites et citées.

## 1. Le problème qui reste à notre optimiseur

Les parcours maintenus par d'autres deviennent la base : parcours gratuits de RestedXP sur les niveaux qu'ils couvrent
(jusqu'à 21 ou 22, `rxp-comparaison.md` §1), guides de Polestar au-delà. La recette du 2026-10-14 livre déjà la base
adaptée de RestedXP dans 49 cas sur 56 (notre calcul accepté 7 fois). Notre optimiseur ne construit donc plus une
route 1 → 60 ; il résout trois sous-problèmes de taille et de forme différentes :

| Sous-problème | Entrée | Taille | Forme |
|---|---|---|---|
| **(a) Insertion dans un squelette fixe** | parcours de référence (étapes entières, décision 277) ; blocs à insérer : donjon avec ses quêtes (DJ1), quêtes de classe, visites de métier, maître de vol ou auberge | 20 à 60 étapes par tranche, 1 à 10 blocs | insertion au moindre coût sous précédence (prise avant le donjon, rendu après) et fenêtre de niveaux |
| **(b) Trous** | niveaux ou contenus qu'aucune référence ne couvre : au-delà de 22 sans Polestar, contenu 30-60 propre à Forever (Riverglades, Shen'dralas, Mount Hyjal, absents de Polestar au 2026-10-21), quêtes lancées par un objet, quêtes nouvelles de Forever | quelques centaines de quêtes, donc 600 à 1 500 arrêts | sélection et ordre complets, bornés par l'état de sortie du squelette précédent et l'entrée du suivant |
| **(c) Personnalisation et reprise** | position réelle, quêtes faites **du personnage**, bonus d'XP, équipement (temps par monstre) | 10 à 30 prochaines étapes | réordonner une fenêtre glissante depuis la position, retirer le déjà-fait, recoller au squelette |

Trois traits rendent le problème non standard, et pèsent sur le choix des méthodes :

- **Gain dépendant de l'état** : l'XP d'une quête dépend du niveau au moment du rendu (pénalité d'écart, quête grise),
  et le niveau dépend de l'XP déjà gagnée. Le gain n'est pas fixé d'avance par sommet comme dans l'orienteering
  classique, ni même fonction du seul temps comme dans les variantes « à profits dépendants du temps ».
- **Paires prise → rendu** et **chaînes** : chaque quête est une paire collecte-livraison (prise, objectif, rendu),
  avec des prérequis entre quêtes ; le journal limité est une **capacité** (Forever : 40 « on WoW Forever » dans
  `params.rs` de Factoruide lu le 2026-10-14, question RTE2 ; Polestar : 20 dans notre étude du 2026-10-14, **40**
  (`maxOpen`) dans leur `SIMULATION.md` lu le 2026-10-21 ; à noter dans RTE2, toujours `suppose`).
- **Coût d'évaluation** : la seule évaluation fidèle est la simulation de la route (trajets, combats, niveaux) ; les
  trois optimiseurs publics (Factoruide, Polestar, Ding) évaluent par simulation, aucun par modèle linéaire.

## 2. Ce que fait notre optimiseur aujourd'hui (`forever/optimize/route.py`, `forever/engine/route.py`)

- **Construction** : portage cité de Factoruide (`construct.rs`) ; arrêt le plus proche en temps, pondéré par sa sorte
  (rendu 0,7, objectif 1, prise 1,3, donjon 0,5) et par `zone_stay` hors de la zone courante ; une prise n'est gardée
  que si son XP, chaîne comprise (`quest_worth`, profondeur 8), bat `min_efficiency` fois le farm ; quêtes de donjon
  toujours prises tant que le donjon est à portée.
- **Amélioration** : montée stricte à graine fixe (un mouvement gardé seulement s'il raccourcit la route), cinq
  mouvements (déplacer un arrêt, un bloc de 2 à 5, échanger, retirer, insérer) ; depuis CJ1 elle ne retire plus une
  quête de la construction.
- **Évaluation** : `_cost` resimule **toute** la route à chaque essai et ne compte que les secondes : ni pénalité de
  changement de zone, ni poids du farm, ni retour en arrière dans une zone. Le regroupement par zone n'existe donc que
  dans la construction, et l'amélioration peut le défaire.
- **Contraintes dures** : prérequis, chaînes, exclusives, journal, fenêtre de placement des donjons (I17), quêtes de
  donjon avant le premier passage ; un donjon impossible à placer est retiré avec un avertissement.
- **Écarts mesurés** (`rxp-comparaison.md` §3-4 et recette) : trajets sans vols ni foyer à la date de la comparaison
  (le modèle `forever/engine/travel.py` les décrit, leur branchement dans les routes reste à vérifier), monstres tués en
  chemin non comptés, objectifs à nombre de monstres estimé trop valorisés, quêtes lancées par un objet absentes,
  notre calcul « prend d'autres quêtes » que la référence (différences sans explication).

## 3. Outils de routes pour WoW Forever et WoW Classic

État au 2026-10-21 (date de consultation) ; « IA » seulement quand le dépôt le dit. WoW Forever sort le 2026-11-04
(wowforever.be, Road to Sixty) : les outils Forever ont tous moins d'un mois et changent chaque jour.

### 3.1 Outils qui calculent

**Polestar Guides** (0xFitz, `fitzforge/polestar`, 136 étoiles, mise à jour le 2026-10-20 ; CurseForge 0.2.6 du
2026-10-19, 13 573 téléchargements). Algorithme lisible dans `docs/SIMULATION.md` :
- unité de recherche = **paquet** (une visite de zone pour un ensemble de quêtes, par bandes de 5 niveaux) ; les paquets
  de la zone de départ d'abord ;
- construction gloutonne aléatoire, paquet suivant tiré avec une probabilité proportionnelle à exp(XP/h, trajet compris
  / τ) ; recherche locale (échanger, insérer, retirer, ajouter, remplacer, fusionner) ; recuit (budget 6 000
  évaluations par tâche, 32 tâches par tour) ; redémarrages tant que la meilleure route progresse ; budget par défaut
  1 000 000 de routes, recherches mesurées de 3,5 à 30 millions par départ ;
- objectif = temps jusqu'au 60 + coûts de politique, temps affiché inchangé : changement de zone 450 s, farm compté
  2,5 fois (profil « time ») ; profil « smooth » ajouté le 2026-10-19 (changement de zone 900 s, retour dans une zone
  1 800 s, retour à un lieu 900 s, farm 4 fois, prise inutile 600 s) ; réglage de style Rapide, Équilibré, Routes
  (0.2.5, 2026-10-17) ;
- modèle (leurs hypothèses, `suppose` pour nous) : XP de quête de la table `QuestXP` du client réduite par écart de
  niveau, XP des monstres, monstres en plus tués en chemin (`extraKill`, prior 0,043 ± 0,038, ajusté le 2026-10-12),
  marche 7 yd/s avec détour 1,3 remplacé par des trajets routés, vols et transports du client, foyer avec recharge,
  risque de mort par zone trop haute (300 ± 150 s), journal de 40 avec abandon de la plus basse ;
- **robustesse** : 2 000 tirages des paramètres dans leurs priors, les 10 meilleures routes réévaluées, taux de
  victoire et intervalle à 90 % rapportés ;
- **consensus** : route propre à chaque départ jusqu'au 12, puis une route commune 12 → 60 par camp (recuit sur la
  somme des temps de tous les départs) ; les guides sont écrits à la main depuis ce squelette puis notés par le même
  modèle ;
- résultats annoncés (estimations du modèle, aucune partie enregistrée) : meilleures routes 116,3 à 121,2 h jusqu'au
  60, guides 0.2.4 130 à 134 h sans optionnels ; contenu 30-60 de Forever absent ; **donjons exclus** (route faisable
  seul) ;
- données : tables du client, QuestieDB (édition Forever), connexions de Carbonite, trajets de Shortest Path Forever
  (GPL-3.0-or-later) ; enregistreur optionnel qui remplace les priors ;
- licence GPL-3.0, exception pour les paquets de guides produits par leur compilateur ; fichier `AGENTS.md` présent.

**Factoruide** (`brouznouf/factoruide`, 68 étoiles, version 0.14.0 du 2026-10-21 ; Forever, Classic Era et Hardcore,
TBC Anniversary). Algorithme lisible dans `ARCHITECTURE.md` (crate `fg-route`) :
- état initial lu dans les SavedVariables de son addon (quêtes rendues, position, foyer, vols connus, XP reposée,
  équipement) ;
- simulation de toute la partie ; chaque prise, objectif, rendu est une étape ; prérequis, exclusions, journal ;
- construction gloutonne (arrêt utile le plus proche, s'il bat le farm chaîne comprise) **ou par régions** (quêtes
  groupées par point de départ et tranche de niveaux, meilleur bloc suivant en XP/h) ;
- recherche locale : déplacer un arrêt près de sa place, placer un objectif au plus petit détour, déplacer un bloc
  **ou un séjour de zone**, retirer, insérer près des arrêts proches, **ajouter un détour vers un maître de vol ou une
  auberge**, **ruine et recréation** ; recuit et acceptation tardive ; **poids des mouvements adaptés à leurs
  succès** ; **resimulation de la seule partie modifiée** ; post-traitement : retirer les quêtes prises jamais rendues,
  rapprocher les objectifs au même lieu ;
- 8 recherches parallèles qui se partagent la meilleure route ; budget compté en essais (même guide sur toute
  machine) ; mode par tours optionnel (la meilleure moitié continue avec deux fois plus d'essais) ;
- objectif = temps réel + pénalités : farm (poids 1,5, et 4 au-delà de 10 % de l'XP du niveau), or des vols,
  changement de zone 240 s, abandon 600 s, temps hors zones préférées, objectif imposé manquant 7 200 s ;
- évolutions récentes : monstres tués en chemin (80 % des monstres croisés, réglage, 0.11.0 du 2026-10-17), temps de
  réapparition par monstre, quêtes de classe planifiées pour le sort qu'elles apprennent, quête lancée par un butin de
  boss prise dans le donjon, trajets par routes et tunnels, vols appris en passant (0.14.0) ; export vers les paquets
  de Polestar (format 3, guides de 60 étapes au plus) ;
- résultats annoncés : **aucun temps 1 → 60** dans le README ni dans `ARCHITECTURE.md` ; l'auteur le présente comme
  une expérience qui ne remplacera pas les guides écrits à la main ;
- licence MIT pour le code, GPL-2.0-or-later pour `data/` (VMaNGOS) ; notre portage de la décision 266 vient du commit
  `f7da6da`.

**Ding** (`moust4ki/DingGuideWoWForever`, GPL-3.0, 192 commits ; CurseForge 1.8.1 du 2026-10-15, 419
téléchargements). Routes « optimisées pour l'XP/h » générées hors ligne ; leurs outils chargent l'addon dans une API
WoW simulée et **jouent chaque guide** pour le vérifier. Règles : quête au plus un ou deux niveaux au-dessus, monstres
au plus un. Données DingDB tirées de Questie et QuestieDB. Algorithme non décrit. Fichier `CLAUDE.md` et documentation
« créer un guide avec une IA ». Sources en désaccord sur son état : la page CurseForge le déclare **abandonné au
profit de Polestar** ; le dépôt GitHub (version 1.8 annoncée, tests à chaque demande de fusion, publication
automatique) ne montre aucun signe d'abandon.

**wow-leveler / sl0p.leveler** (`michael-slop/wow-leveler`, 0 étoile, 13 commits). Architecture la plus proche de notre
rôle restant : routes **converties des parcours de RestedXP** (outil `rxp2route.py`, fichiers sous CC BY-NC-SA 4.0) et
**optimiseur d'ordre** sur une **fenêtre glissante** des ~10 prochaines étapes depuis la position, recalculée toutes
les 2 s, « voyageur de commerce avec règles de quêtes » (prise, objectif, rendu ; niveaux ; chaînes) ; **hystérésis** :
la flèche ne change que si le nouvel ordre est nettement plus court, jamais pendant un objectif. Méthode de résolution
non décrite. Code sans licence (tous droits réservés).

**Adventure Guide Forever** (`cjber/adventure-guide-forever`, GPL-3.0-or-later, 179 commits, mis à jour le
2026-10-21 ; « Built with AI assistance », inspiré de Polestar sans copie selon son README). Pas une route complète
mais un **choix de la prochaine étape** à règles : difficulté maximale réglable (+2 par défaut, prises orange et
rouges écartées), rendus prêts et prises proches d'abord, étapes en ville regroupées, objectif déplacé vers un autre
lieu de la carte si ses monstres ont 3 niveaux de plus, quêtes du groupe favorisées ; **chaque choix explique
pourquoi**. Données QuestieDB (Forever), wago.tools, CMaNGOS.

### 3.2 Outils à routes écrites à la main

| Outil | Méthode | Couverture, fraîcheur | Licence |
|---|---|---|---|
| **RestedXP** | routes « faites à la main par des speedrunners » (page de vente), ajustées à la progression du personnage ; une route par race et classe | Forever : gratuit jusqu'à 21-22, payant 30 $ par camp, 35-60 « après la sortie » (wowforeverguides, 2026-10-18) ; Classic Era, SoD, Anniversary payants | guides gratuits CC BY-NC-SA 4.0 (fichier `LICENSE` de RXPGuides) ; payants exclus (décision 268) |
| **Zygor** | guides écrits ; le sélecteur classe les guides par distance de la zone et part déjà faite ; « Travel System » = plus court chemin vers l'objectif suivant | Forever annoncé pour la sortie | propriétaire, abonnement |
| **Leveldon** (+ Questdon) | routes non décrites ; **partage entre joueurs des durées d'étape et des étapes sautées** pour améliorer les routes | 1-30, 0.2.4-beta du 2026-10-18 | MIT |
| **Alenya's Guides** | route d'un speedrunner ; addon **Writer** qui **enregistre une partie et l'exporte en guide** | Alliance 1-20 (Forever, Classic 1.15.9), 2026-10-08 | tous droits réservés |
| **Guidelime** | guides écrits par des joueurs, éditeur ; pas de génération | Forever « bientôt » (v6.008 du 2026-10-15) | non indiquée sur la page |
| **Joana** | guide de speedrun écrit (12-60 Azeroth) | record vanilla 4 j 20 h 49 min /played (partie réelle, vanilla, pas Forever) | commercial |
| **Azeroth Pilot** | routes écrites ; version « Reloaded » donnée pour le retail ; un témoignage la dit limitée à 40 en Classic | peu d'information fiable | non vérifiée |

### 3.3 Outils de données, sans route

**Questie** (GPL-3.0, 2026-10-12, saveur Forever) : marqueurs de quêtes, XP en info-bulle ; **aucune route**.
**Shortest Path Forever** (`cjber`, GPL-3.0-or-later, 2026-10-21) : trajets (marche, vols, bateaux, zeppelins, tram,
portails), déjà source de trajets de la décision 266. **DungeonPro** (`Antrakt92`, 2026-10-21, licence non vérifiée) :
préparation des quêtes de donjon et de leurs chaînes. **Road to Sixty** (`Jordanburch101`) : enregistre le chemin réel
1 → 60 de chaque personnage. Outils web : aucun optimiseur de route en ligne trouvé (wowforever.be publie des routes
écrites ; « wow-min-max » est un projet de 2021 resté inachevé).

### 3.4 Communauté

Aucun fil Reddit (r/classicwow, r/WoWForever) ni de forum décrivant un optimiseur de route n'a été trouvé par la
recherche web du 2026-10-21. Les articles « meilleur addon de leveling 2026 » trouvés sont commerciaux et sans mesure.
Wago (addons.wago.io) : aucune fiche trouvée par la recherche ; la même recherche cite sur CurseForge Everleveling et
ForeverLeveling (routes Classic 1-60 « adaptées à Forever », non ouvertes) et ForeverGuide (talents et métiers, pas
de route).

## 4. Méthodes connues pour ce type de problème

| Famille | Ce qu'elle modélise | Ce qui manque pour nous | Références |
|---|---|---|---|
| **Orienteering (OP)**, TSP à profits, prize-collecting TSP | choisir un sous-ensemble de lieux et leur ordre pour maximiser le gain sous budget de temps (OP) ou minimiser trajet + pénalités des lieux omis (PCTSP) | gain fixé par sommet ; ni paires ni capacité | Balas 1989 ; Feillet et al. 2005 ; Vansteenwegen et al. 2011 ; Gunawan et al. 2016 ; Shen et al. 2025 |
| **OP avec fenêtres de temps (OPTW, TOPTW)** | visite permise dans un intervalle | nos fenêtres portent sur le **niveau** (donjon, quête grise), pas sur l'heure | Kantor et Rosenwein 1992 ; Vansteenwegen et al. 2009 (ILS) ; Gedik et al. 2017 (CP) |
| **OP à profits variables ou décroissants** | gain fonction du temps d'arrivée ou de la durée | le nôtre dépend du **niveau atteint**, donc de toute la route avant | Erdoğan et Laporte 2013 ; Afsar et Labadie 2013 ; Yu et al. 2019 |
| **Collecte-livraison sélective** (selective PDP, profitable tour with pickup and delivery) | paires prise → rendu optionnelles, capacité, gain | même limite sur le gain | Chentli et al. 2018 (ALNS sélective) ; Ropke et Pisinger 2006 (ALNS pour PDPTW) |
| **OP avec précédences** ; **ordonnancement séquentiel (SOP)** | ordre imposé entre tâches | chaînes de quêtes, prise avant rendu | Hanafi, Mansini et Zanotti 2020 |
| **Programmation par contraintes / routage OR-Tools** | paires `AddPickupAndDelivery`, capacité, visites optionnelles par `AddDisjunction` avec pénalité, temps | gain dépendant du niveau impossible à exprimer en coût d'arc ; utile sur une petite fenêtre seulement | documentation OR-Tools (2026-03-18) ; Gedik et al. 2017 |
| **MIP, branch-and-cut** | exact | OP déterministe exact jusqu'à ~100 nœuds environ selon le survey ; nos gains non linéaires l'excluent | Bianchessi et al. 2018 ; Kobeaga et al. 2024 (cités par Shen et al.) |

Heuristiques, du plus utile au moins utile à notre taille :

1. **Recherche locale** (2-opt, or-opt, relocate, échange, insertion et retrait) : base de tous les outils publics ; Croes
   1958, Or 1976 (références classiques, non consultées ici).
2. **Acceptation non stricte** : recuit simulé (Kirkpatrick et al. 1983) ou acceptation tardive (Burke et Bykov 2017,
   un seul paramètre, la longueur de l'historique) ; Polestar et Factoruide les utilisent ; nous non.
3. **Recherche locale itérée (ILS)** : perturbation puis recherche locale ; méthode de référence de l'OPTW
   (Vansteenwegen et al. 2009), reprise par de nombreuses variantes (Gunawan et al. 2017, SA-ILS).
4. **Grand voisinage (LNS, ALNS), ruine et recréation** : retirer un groupe cohérent de quêtes (une zone, une tranche
   de niveaux, une chaîne) et le réinsérer au moindre coût ; poids des opérateurs adaptés à leurs succès (Shaw 1998 ;
   Schrimpf et al. 2000 ; Ropke et Pisinger 2006 ; Santini 2019 pour l'OP, meilleur que EA4OP sur instances
   difficiles selon Shen et al.). Factoruide l'utilise.
5. **GRASP** (construction gloutonne aléatoire + recherche locale, Feo et Resende 1995) : c'est la construction de
   Polestar (tirage pondéré exp(XP/h / τ)) avec redémarrages.
6. **Colonies de fourmis, algorithmes génétiques, apprentissage par renforcement** : présents dans la littérature OP
   (Verbeeck et al. 2017 pour le TD-OPTW ; Kobeaga et al. 2018 EA4OP ; Gama et Fernandes 2021) mais aucun outil de WoW
   ne les emploie, chaque évaluation est une simulation coûteuse, et le croisement de deux routes viole presque
   toujours les chaînes et les fenêtres de donjon. **Non recommandés.**
7. **Exact sur petite fenêtre** : programmation dynamique sur sous-ensembles (Held-Karp) avec précédences pour 10 à 12
   arrêts (quelques dizaines de milliers d'états), ou CP-SAT ; adapté au sous-problème (c).

Ce qui marche à notre taille : en (b), quelques centaines de quêtes deviennent quelques dizaines de **paquets** de zone
et de niveaux (Polestar), espace où GRASP + recherche locale + recuit ou acceptation tardive + ruine et recréation
convergent en secondes avec une évaluation incrémentale ; en (a), la structure est presque fixée et l'**insertion au
moindre coût** suivie d'une réparation locale suffit ; en (c), une fenêtre de 10 à 12 arrêts se résout exactement pour
un gain figé dans la fenêtre, puis la simulation départage les meilleurs ordres.

## 5. Comparaison : idées réutilisables

| Outil ou méthode | Idée réutilisable | Bénéfice attendu (lié aux écarts mesurés) | Coût | Licence de la source |
|---|---|---|---|---|
| Factoruide | resimuler **depuis la première étape modifiée** (états mémorisés après chaque arrêt) | plus d'essais au même budget (en moyenne la moitié de la route resimulée au lieu du tout ; gain réel à mesurer) ; rend possible (b) et (c) | faible : cache des `RouteState` dans `simulate` | MIT (idée, portage cité déjà admis, 266) |
| Factoruide, Polestar | **objectif = temps + pénalités de politique** (changement de zone, farm pondéré, prise jamais rendue), temps affiché inchangé | l'amélioration ne défait plus le regroupement par zone ; moins de « quêtes prises d'un seul côté » dans la recette | faible : poids dans `mechanics.json` (`route.search`, `suppose`) | MIT ; GPL-3.0 (idée seulement) |
| Polestar | **paquets** zone × tranche de 5 niveaux, pôles de quêtes, zone de départ d'abord | espace de recherche réduit en (b) ; enchaînement de zones proche des références (critère de 279) | moyen | GPL-3.0 (idée seulement, 278) |
| Polestar | construction **GRASP** à température + **redémarrages** à graines fixes | diversité, sortie des optimums locaux de la montée stricte | faible | GPL-3.0 (idée) |
| Factoruide, Polestar ; Burke et Bykov 2017 | **recuit ou acceptation tardive** au lieu de la montée stricte | meilleures routes à budget égal | faible | publication |
| Factoruide ; Schrimpf 2000 ; Ropke et Pisinger 2006 | **ruine et recréation** par zone, chaîne ou tranche ; **poids adaptatifs** des mouvements | (b) surtout ; réparation après insertion d'un donjon en (a) | moyen | MIT ; publications |
| Factoruide | mouvement **« détour vers maître de vol ou auberge »** ; vols appris en passant ; foyer avec recharge | poste trajet, le plus gros écart mesuré (39 vols, 24 foyers sur 1 → 22 chez RestedXP) | moyen (dépend de `travel.py`) | MIT |
| Factoruide 0.11.0, Polestar `extraKill` | **monstres tués en chemin** comme paramètre mesuré | corrige le farm surestimé des rejeux et sous-estimé de nos routes (§3.1 de la comparaison) | faible ; valeur à mesurer par ForeverLogger, jamais reprise | MIT ; GPL-3.0 (idée) |
| Factoruide 0.11.0 | quête lancée par un butin (de boss ou de monstre) prise **au lieu du butin** | quêtes « sans donneur positionné » enfin plaçables | moyen | MIT |
| Polestar | **passe de robustesse** : réévaluer les k meilleures routes sous tirages des paramètres `suppose` (temps par monstre, monstres par objectif) | préférer une route qui reste bonne quand nos estimations sont fausses ; répond au point 4 de la comparaison | moyen (k × tirages simulations) | GPL-3.0 (idée) |
| Polestar | **profils de style** (rapide, régulier) = jeux de poids de politique | personnalisation demandée sans nouveau modèle | faible | GPL-3.0 (idée) |
| Polestar | **route commune par camp** au-delà du 12 | raccord RestedXP → Polestar simple : une seule route Polestar par camp à rejoindre | nul (lecture) | guides GPL-3.0, usage privé |
| wow-leveler | **fenêtre glissante** de ~10 étapes depuis la position + **hystérésis** | (c) : reprise depuis la position réelle sans recalculer la tranche | faible | aucune licence de code : idée seulement |
| Programmation dynamique, OR-Tools | **exact sur la fenêtre** : sous-ensembles + précédences (prise avant rendu, chaîne) ; ou `AddPickupAndDelivery` + `AddDisjunction` | ordre exact sur 10-12 arrêts **pour un gain figé dans la fenêtre** (le niveau y bouge peu, mais l'XP au rendu et le temps par monstre dépendent encore de l'ordre : ordre final confirmé par simulation) ; aucune dépendance si DP maison | faible (DP) ; dépendance à demander (OR-Tools, Apache-2.0) | publications ; Apache-2.0 |
| Factoruide | **placer un objectif au plus petit détour** ; post-traitement : rapprocher les objectifs au même lieu, retirer les prises jamais rendues | insertion de (a) ; routes plus propres | faible | MIT |
| Adventure Guide Forever | **chaque choix dit pourquoi** (codes de raison) | la recette 279 exige que chaque différence soit expliquée : l'explication sort de l'optimiseur au lieu d'être reconstruite | faible | GPL-3.0-or-later (idée) |
| Leveldon, Alenya's Writer, Road to Sixty, enregistreurs de Polestar et Factoruide | **durées réelles par étape** enregistrées, qui remplacent les priors | calibrage du temps par étape ; « gain mesuré » de la recette | nos ForeverLogger et profil le font déjà ; à brancher sur la route | idée |
| Ding | **jouer chaque guide** dans un client simulé pour le vérifier | équivaut à notre rejeu ; confirme le choix | nul | GPL-3.0 (idée) |
| Algorithmes génétiques, fourmis, RL | — | aucun bénéfice démontré à notre taille | élevé | — |

## Recommandation

**Les deux questions de la décision 288.**
- *Qui maintient déjà ça mieux que nous ?* L'enchaînement des zones et l'ordre des quêtes : RestedXP (gratuit jusqu'à
  21-22) puis Polestar (1 → 60 solo, route commune par camp, mise à jour quotidienne). Les faits de quêtes : le client
  et Questie/QuestieDB. Les trajets : Shortest Path Forever. La découverte des étapes ignorées et des durées réelles :
  nos propres relevés (ForeverLogger), comme Leveldon et Factoruide le font chez eux.
- *Que se passe-t-il au prochain patch ?* Le squelette est réparé par ses auteurs ; notre optimiseur ne porte que des
  **insertions et des réordonnancements** sur nos propres données (donjons de DJ1, quêtes de classe, quêtes faites,
  position), plus les trous. Il ne doit donc contenir aucune route codée en dur et aucun poids réglé sur une version :
  ses poids de politique vivent dans `mechanics.json` (`suppose`) et sa qualité se mesure par la recette, rejouée à
  chaque version.

**Architecture proposée** : un optimiseur en trois modes, une seule simulation (moteur actuel), une seule recherche
locale.

1. **Mode insertion (a), prioritaire.** Le squelette (base adaptée de RestedXP, puis guide Polestar lu en local pour
   l'usage privé, avec attribution) est figé à l'étape entière (décision 277). On y insère, dans l'ordre : quêtes de
   classe (prise au plus petit détour, chaîne entière), donjon avec ses quêtes (prises avant, passage au niveau où il
   rapporte le plus selon DJ1, rendus après), visites de métier, détours de vol et de foyer. Méthode : **insertion au
   moindre coût** évaluée par resimulation incrémentale, puis réparation **or-opt et relocate limitée aux arrêts
   insérés** (les étapes du squelette ne bougent pas ; seule la suppression d'une étape entière devenue inutile est
   permise, et elle est expliquée). Chaque insertion porte son code de raison (classe, donjon, gain mesuré de N min),
   ce qui rend la route acceptable par construction au sens de la décision 279. La règle de Polestar sur les donjons
   (« un donjon ne bat jamais les quêtes en solo ») **n'est pas reprise** (décisions 277 et 278).
2. **Mode personnalisation (c).** Retirer les quêtes faites du personnage (profil, jamais l'union), partir de la
   position réelle, puis **fenêtre glissante** : programmation dynamique sur les 10 à 12 prochains arrêts avec
   précédences et journal, exacte pour un gain figé au niveau du début de la fenêtre, les meilleurs ordres confirmés
   par la simulation ; raccord au squelette au premier arrêt commun ; hystérésis (changer d'ordre seulement si le
   gain dépasse un seuil) pour la livraison par le pont. Bonus d'XP et équipement agissent par la simulation (XP, temps
   par monstre), pas par l'ordre.
3. **Mode trous (b).** Construction par **paquets** (zone × tranche de 5 niveaux, pôles de quêtes), GRASP à
   température avec redémarrages à graines fixes, recherche locale actuelle + **ruine et recréation** + **acceptation
   tardive** (un paramètre, déterministe à graine fixe), objectif = temps + pénalités de politique, bornes : état de
   sortie du squelette précédent, entrée du suivant ; **passe de robustesse** sur les paramètres `suppose` avant de
   livrer. Le contenu 30-60 propre à Forever et les quêtes lancées par un objet sont les premiers trous à couvrir.

**Ordre de travail proposé** (chaque point se juge sur la recette, jamais sur le seul temps simulé) :

| Priorité | Changement | Écart mesuré visé | Effort |
|---|---|---|---|
| P1 | évaluation incrémentale (états mémorisés, resimulation depuis l'arrêt modifié) | rend les modes (a)-(c) rapides | faible |
| P2 | mode insertion (a) avec codes de raison | 49 routes sur 56 déjà livrées en base adaptée : y insérer donjons et quêtes de classe sans perdre l'acceptation | moyen |
| P3 | vols, foyer et détour vers maître de vol ou auberge dans la route ; monstres tués en chemin comme paramètre mesuré | trajet (plus de la moitié du temps) et farm, §3.1-3.2 de la comparaison | moyen |
| P4 | objectif = temps + pénalités de politique ; acceptation tardive ; ruine et recréation | « différences sans explication » de notre calcul | faible à moyen |
| P5 | fenêtre glissante exacte (c) | départ réel, quêtes faites | faible |
| P6 | paquets et passe de robustesse pour les trous (b) ; quêtes lancées par un objet | contenu 30-60 de Forever, quêtes sans donneur | moyen à élevé |

**À ne pas faire** : algorithmes génétiques, colonies de fourmis, apprentissage par renforcement, MIP exact sur une
tranche ; OR-Tools seulement si la programmation dynamique de la fenêtre ne suffit pas (nouvelle dépendance, donc sur
accord). Aucun chiffre extérieur (pénalité d'écart de niveau de Polestar, 80 % de monstres en chemin de Factoruide,
450 s ou 240 s de changement de zone) n'entre dans `forever/data/` comme règle de jeu : les poids de politique peuvent
y entrer comme réglages `suppose`, les règles de jeu seulement avec une source (décision 278).

**À trancher par l'utilisateur** : (1) lire les guides de Polestar comme squelette au-delà de RestedXP amende la
décision 278 (« référence de calibrage », « jamais installé ») : il faut une décision qui fixe la lecture (clone en
cache, commit épinglé), l'unité d'adaptation et l'attribution, et rien redistribué (GPL-3.0) ; (2) l'export vers le
format de paquets de Polestar, que Factoruide fait déjà, serait une autre voie de livraison, à n'envisager que sur
demande.

## Sources

Consultées le 2026-10-21 ; date propre à la source entre parenthèses quand elle est connue.

Outils :
- Polestar, dépôt et README : https://github.com/fitzforge/polestar (mise à jour le 2026-10-20 selon le sujet GitHub
  `wow-forever`)
- Polestar, méthode : https://raw.githubusercontent.com/fitzforge/polestar/next/docs/SIMULATION.md (run final du
  2026-10-13, trajets mesurés le 2026-10-17)
- Polestar, journal des versions : https://raw.githubusercontent.com/fitzforge/polestar/next/CHANGELOG.md (0.2.4 du
  2026-10-16, 0.2.5 du 2026-10-17, 0.2.6 du 2026-10-19)
- Polestar sur CurseForge : https://www.curseforge.com/wow/addons/polestar-guides (2026-10-19)
- Factoruide, dépôt : https://github.com/brouznouf/factoruide
- Factoruide, méthode : https://raw.githubusercontent.com/brouznouf/factoruide/main/ARCHITECTURE.md
- Factoruide, journal des versions : https://raw.githubusercontent.com/brouznouf/factoruide/main/CHANGELOG.md (0.11.0 du
  2026-10-17 à 0.14.0 du 2026-10-21)
- Ding : https://github.com/moust4ki/DingGuideWoWForever ; https://www.curseforge.com/wow/addons/ding-xp-and-leveling-guide
  (1.8.1 du 2026-10-15)
- wow-leveler : https://github.com/michael-slop/wow-leveler ; README :
  https://github.com/michael-slop/wow-leveler/blob/main/README.md
- Adventure Guide Forever : https://github.com/cjber/adventure-guide-forever
- Sujet GitHub `wow-forever` : https://github.com/topics/wow-forever?o=desc&s=updated
- Leveldon : https://github.com/WoW-Forever-Addons/leveldon ; https://www.curseforge.com/wow/addons/leveldon
  (0.2.4-beta du 2026-10-18)
- Alenya's Guides : https://www.curseforge.com/wow/addons/alenyas-guides (2026-10-08)
- Guidelime : https://github.com/max-ri/Guidelime
- Tableau des addons de leveling de Forever : https://wowforeverguides.com/leveling/addons (mise à jour le 2026-10-18)
- RestedXP, pages de vente Classic : https://shop.restedxp.com/classic-era/ ;
  https://shop.restedxp.com/?p=280809
- Zygor, manuel : https://zygorguides.com/support/manual/leveling
- Routes écrites, date de sortie de Forever : https://wowforever.be/routes/ (2026-09-15)
- Road to Sixty : https://github.com/Jordanburch101/road-to-sixty
- Record de Joana : https://www.warcrafttavern.com/wow-classic/guides/how-long-to-60/
- wow-min-max : https://github.com/D-T-Design/wow-min-max (2021)
- Dans le dépôt : `docs/research/rxp-comparaison.md` (2026-10-14), `tasks/plan-corrections-jeu.md` § Polestar
  (2026-10-14), `docs/DECISIONS.md` (266, 268, 277, 278, 279, 288), `forever/optimize/route.py`,
  `forever/engine/route.py`, `forever/engine/travel.py`

Méthodes (références vérifiées par leur notice ou par le survey de Shen et al. ; « classique » = non consultée ici) :
- Shen, Zhou, Lei, Wu, « A survey of the orienteering problem: model evolution, algorithmic advances, and future
  directions », arXiv:2512.16865 (2025-12-18) : https://arxiv.org/html/2512.16865v1
- Gunawan, Lau, Vansteenwegen, « Orienteering Problem: A survey of recent variants, solution approaches and
  applications », EJOR 255(2), 315-332 (2016) (notice trouvée par la recherche, page injoignable le 2026-10-21)
- Vansteenwegen, Souffriau, Van Oudheusden, « The orienteering problem: A survey », EJOR 209(1) (2011) (classique)
- Vansteenwegen, Souffriau, Vanden Berghe, Van Oudheusden, « Iterated local search for the team orienteering problem
  with time windows », Computers & OR 36(12) (2009) (classique)
- Feillet, Dejax, Gendreau, « Traveling salesman problems with profits », Transportation Science 39(2) (2005)
  (classique) ; Balas, « The prize collecting traveling salesman problem », Networks 19(6) (1989) (classique)
- Erdoğan, Laporte, « The orienteering problem with variable profits », Networks 61(2) (2013) (classique) ; Afsar,
  Labadie, team orienteering à profits décroissants (2013), cité par la recherche (classique, non consulté)
- Hanafi, Mansini, Zanotti, « The multi-visit team orienteering problem with precedence constraints », EJOR 282(2),
  515-529 (2020) : https://ideas.repec.org/a/eee/ejores/v282y2020i2p515-529.html
- Chentli, Ouafi, Cherif-Khettaf, ALNS sélective pour le profitable tour problem avec collecte et livraison
  simultanées, RAIRO-Oper. Res. 52 (2018) : https://www.rairo-ro.org/10.1051/ro/2018024
- Ropke, Pisinger, « An adaptive large neighborhood search heuristic for the pickup and delivery problem with time
  windows », Transportation Science 40(4) (2006) (classique) ; Shaw, LNS, CP-98 (1998) (classique) ; Schrimpf et al.,
  « Record breaking optimization results using the ruin and recreate principle », J. Comput. Phys. 159(2) (2000)
  (classique) ; Santini, ALNS pour l'OP (2019), cité par Shen et al.
- Burke, Bykov, « The late acceptance hill-climbing heuristic », EJOR 258(1) (2017) (classique) ; Kirkpatrick, Gelatt,
  Vecchi, recuit simulé, Science (1983) (classique) ; Feo, Resende, GRASP, J. Global Optim. 6 (1995) (classique) ;
  Croes (1958), 2-opt ; Or (1976), or-opt (classiques)
- Gedik et al. 2017 (CP pour TOPTW), Verbeeck et al. 2017 (fourmis, TD-OPTW), Kobeaga et al. 2018 (EA4OP), Gama et
  Fernandes 2021 (RL pour OPTW), Bianchessi et al. 2018 et Kobeaga et al. 2024 (branch-and-cut) : cités par Shen et al.
- OR-Tools, « Penalties and Dropping Visits » (mise à jour le 2026-03-18) :
  https://developers.google.com/optimization/routing/penalties ; collecte et livraison (non consultée) :
  https://developers.google.com/optimization/routing/pickup_delivery
- Autres addons cités par la recherche Wago : https://www.curseforge.com/wow/addons/everleveling ;
  https://www.curseforge.com/wow/addons/foreverleveling (non ouverts)
- LKH-3 (Helsgaun 2017) : page de l'auteur injoignable le 2026-10-21 (connexion refusée) ; non retenu.
