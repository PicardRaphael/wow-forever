# Idée du chat à intégrer (2026-10-13) : Factoruide, optimiseur de routes de leveling

Fichier d'entrée écrit depuis la conversation claude.ai de Raphaël, à sa demande. À traiter **au plan de RX1** (ou par
une étude en lecture seule juste avant), puis à archiver dans `tasks/archive/`. Rien ici n'autorise un accès réseau,
une dépendance, un téléchargement ou une exécution : ces accords se demandent au plan, comme d'habitude.

## Ce que c'est

- Dépôt : https://github.com/brouznouf/factoruide (signalé par Raphaël). Description : « WoW Classic leveling route
  optimizer: desktop app, planner and in-game addon ». Vise **WoW Forever**, Classic Era / Hardcore et TBC Anniversary.
- Licences : code sous **MIT** ; bases de quêtes (`data/`) sous **GPL-2.0-or-later** (données VMaNGOS incluses) ;
  sources et conditions dans `NOTICE.md`.
- Application de bureau Windows (Rust, `crates/`), planificateur `crates/fg-route`, addon en jeu (guide pas à pas,
  flèche, profil du personnage relevé à la déconnexion, collecteur d'XP et de positions), éditeur de guide, guides
  partageables (`.fgguide`). Installeur Windows **non signé** ; projet jeune (2 étoiles, 49 commits au 2026-10-13).

## Comment il calcule une route (d'après son ARCHITECTURE.md)

1. **Modèle** : quêtes jouables (donneur, rendu, objectifs et lieux, taux de butin, prérequis, exclusions, niveau, XP),
   géographie (coordonnées monde, passages entre zones, bateaux, zeppelins, réseau de vols), profil de départ lu dans
   la sauvegarde de son addon (quêtes rendues, position, pierre de foyer, vols connus, XP et repos, équipement, sorts),
   règles d'XP par version de jeu (`xp.rs` : pénalité d'XP de quête selon l'écart de niveau, XP des monstres en formule
   classique `5 × niveau + 45` ajustée, taille du journal de quêtes, niveau de monture).
2. **Simulation** d'une route (liste ordonnée d'arrêts : prendre, faire un objectif, rendre, visite) : trajets (ligne
   droite dans une zone, passages, vols, transports, pierre de foyer), combats et butin selon l'écart de niveau et la
   **puissance** du personnage (niveau + équipement + sorts ; chaque niveau de puissance en plus rend les combats 10 %
   plus rapides), élites, montée de niveau, entraînement de classe, donjons, monstres tués en chemin (plafond par niveau,
   10 % sur Forever), métiers (quêtes seulement), « spots » mesurés (points d'apparition, monstres par groupe,
   réapparition, serveur bondé), récompenses de quêtes et butin de donjon évalués par un petit modèle de combat par
   classe, quêtes de classe (familier, forme) comptées comme de la puissance.
3. **Recherche** : construction gloutonne ou par régions (groupes de quêtes par zone et tranche de niveau), puis
   amélioration locale (déplacer un arrêt ou un bloc, retirer ou insérer une quête, ajouter un détour vers un maître de
   vol ou une auberge, « ruin and recreate »), recuit simulé, acceptation tardive ; **tournoi** de recherches
   parallèles, déterministe à effort égal ; le guide retenu équilibre temps de jeu et confort (peu de farm, peu de
   changements de zone).
4. **Guide** : export en étapes (JSON pour l'application, Lua pour l'addon), en dix langues ; éditeur qui rejoue la
   route après chaque modification.

## Pourquoi c'est important pour RX1

- C'est exactement l'ambition de RX1 (route sur mesure : personnage, classe, métiers, zones, donjons, style de jeu,
  groupe), déjà construite et pensée en profondeur. Refaire tout cela en Python d'ici le 4 novembre n'a pas de sens.
- Nos forces que Factoruide n'a pas, ou moins : l'XP **réelle** de Forever lue dans le client (QuestXP, PerKill,
  `questcache.wdb`), mes mesures (ForeverLogger 0.4.0 : XP par monstre et par quête, repos, donjon), les règles de
  Forever écrites avec leur source (bonus de donjon, XP en groupe, bonus d'XP de T04f), la liste fusionnée des quêtes
  de Forever (556 nouvelles et 183 retouchées selon T04d, depuis Questie, Naowh, Forever Guide, ForeverDungeonJournal),
  le temps par monstre mesuré, et le chat en jeu pour demander une route.
- Son modèle d'XP des monstres est la formule classique ; T04d a mesuré que, sur Forever, l'XP d'un monstre plus bas
  suit la base au niveau du monstre (décision 249) et que la base vient de la table PerKill du client.

## Options à étudier au plan de RX1 (à trancher par Raphaël)

1. **Utiliser Factoruide comme moteur de routes** : notre agent lui fournit ses entrées (profil, choix posés par les
   questions de RX1) et lit sa sortie, puis livre la route dans RestedXP (API `ImportGuide`) ou laisse son propre addon
   la suivre. Vérifier : interface en ligne de commande ou appel des `crates` sans l'application graphique, format des
   entrées et des sorties, temps de calcul (2 à 6 minutes annoncées), qualité de sa base de quêtes pour Forever.
2. **Reprendre ses algorithmes** (code MIT, cité) dans notre RX1, avec nos données de Forever : plus de travail.
3. **Contribuer** : lui proposer nos corrections de Forever (XP du client, règles mesurées), par des issues ou des pull
   requests, si son auteur les accepte ; nos données restent sous nos règles (agrégats, sources citées).
4. Dans tous les cas : ne rien installer ni exécuter sans accord ; si on l'utilise, le **compiler depuis les sources**
   (MIT) plutôt qu'utiliser l'installeur non signé ; ses données GPL restent lues en local, jamais recopiées dans notre
   dépôt (décision 133).

## Données : on peut avoir les mêmes que lui

Selon son ARCHITECTURE.md, les données d'objets, de récompenses de quêtes, de butin des boss, de sorts d'entraîneurs et
de statistiques de base par niveau viennent de **VMaNGOS** (base de données libre d'un émulateur de la Classic, sous
GPL), complétée pour Forever. VMaNGOS contient en particulier ce qui nous manque : la **position de chaque monstre et de
chaque objet** (points d'apparition), les **tables de butin avec leurs taux**, les objets et leurs statistiques, les
quêtes, les maîtres de classe et leurs sorts. À étudier au plan de RX1 (et utile aussi à DJ1 et T10a) :
- source exacte (dépôt de la base VMaNGOS et sa licence, version), contenu et format ;
- lecture en local par notre pipeline, comme les addons : seuls nos agrégats entrent dans le dépôt (décision 133) ;
- recoupement avec le client de Forever (qui prime) et nos sources Forever (Questie, Naowh, Forever Guide,
  ForeverDungeonJournal, AtlasLoot) : ce que Forever change (quêtes nouvelles ou retouchées, monstres déplacés, butin)
  est signalé, jamais deviné ;
- accès réseau à demander au plan (téléchargement de la base), épinglé à une version.
- **Attention de Raphaël** : Forever ajoute beaucoup de quêtes et en modifie d'autres ; VMaNGOS est une base de la Classic
  et peut ne pas être à jour pour Forever, Factoruide non plus. Règle : VMaNGOS ne sert que de base pour ce que Forever
  ne change pas (positions et butin des monstres inchangés), marquée « base Classic » et `suppose` ; le client de Forever
  et nos sources Forever priment toujours. Au plan de RX1, mesurer la couverture de Forever par Factoruide et par VMaNGOS
  face à la liste fusionnée de T04d (556 quêtes nouvelles et 183 retouchées) : combien manquent ou sont périmées, et
  combler ces manques par nos données avant tout calcul de route.

## Règle de méthode proposée : étude de l'existant à chaque plan de tranche

Factoruide, MythicSim et wow-ai ont tous été trouvés par Raphaël, pas par nos plans. Proposition de décision : chaque plan
de tranche commence par une **recherche de l'existant** (GitHub, y compris les dépôts récents et peu étoilés, CurseForge,
Wago Addons, forums et Reddit de WoW Forever), avec la liste de ce qui peut être réutilisé (code, données, formats,
algorithmes), sa licence et sa fraîcheur, **avant** de concevoir quoi que ce soit ; lecture seule, accord réseau demandé
comme d'habitude ; le résultat est écrit dans le plan.
