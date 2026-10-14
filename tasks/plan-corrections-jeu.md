# CJ1 — Corrections après les essais en jeu du 14 octobre : plan

Tranche hors de la table d'origine de la ROADMAP, demandée par l'utilisateur le 2026-10-14 après ses essais en jeu
(personnage neuf « Bob », Gnome, Alliance, niveau 1, Coldridge Valley). Elle passe **avant toutes les autres tranches**
jusqu'au 4 novembre et reprend en elle T10a revue selon l'audit des addons et le cœur de RX2 (vols et pierre de foyer).
Décisions 272 à 279. Plan écrit le 2026-10-14 ; **révisé le même jour** après les deux corrections de cap de
l'utilisateur sur les routes (décision 277, qui amende 268).

Bases : `tasks/archive/idees-du-chat-2026-10-14-ux-routes.md` (interface, routes, exports, talents) et
`tasks/archive/audit-addons-capacites-2026-10-14.md` (ce que les addons installés font déjà), intégrées au bloc 0.

## Demande de l'utilisateur (2026-10-14)

**Règles de méthode** (décisions 272 à 274, section « Façon de travailler » de `CLAUDE.md`) :
1. Avant de construire une fonction, regarder si un addon installé la fait déjà ; si oui, l'agent s'en sert (lecture
   locale, agrégats seulement) et l'alimente par des exports, il ne refait ni son interface ni ses données.
2. Rien n'est déclaré fini tant que l'utilisateur ne l'a pas essayé et accepté en jeu : chaque bloc se termine par une
   courte procédure en jeu, et la tranche ne se ferme qu'avec son accord.
3. « Mon interface est la mienne » : rien ne modifie EllesmereUI sans demande explicite.

**Contenu, dans l'ordre de priorité** :
1. **Routes** (précisé par la correction de cap, décision 277) :
   - les parcours gratuits de RestedXP (jusqu'au niveau 22 environ, licence CC BY-NC-SA 4.0) servent surtout à
     **apprendre à notre moteur à bien choisir** : pour chaque zone de départ et chaque tranche qu'ils couvrent, notre
     route calculée doit retrouver leurs décisions (enchaînement des zones, regroupement des quêtes, moment des donjons
     et des quêtes de classe, retours en ville, vols et pierre de foyer) ; écarts mesurés, expliqués, règles et poids de
     l'optimiseur réglés jusqu'à ce que nos routes soient aussi bonnes ; ces réglages servent ensuite jusqu'au 60 ;
   - là où un parcours gratuit donne une meilleure route que notre calcul, il peut servir de base, avec l'attribution ;
     jamais aucun guide payant ni chiffré ;
   - une route de leveling inclut **toujours, par défaut et sans question**, les donjons avec leurs quêtes au niveau où
     ils rapportent le plus (DJ1) et les quêtes de classe au bon niveau ; retirables à la demande ;
   - une route part **toujours de la position réelle** et tient compte des **quêtes déjà faites** ;
   - autres routes sur demande : réputation, métier (avec SkillUp Forever), et **route d'équipement** (bloc 4b) ;
   - lire les addons qui calculent déjà : GearQuest Forever, Forever Guide, Questie, Naowh, SkillUp Forever.
2. **Conversation de la feuille de route** : questions dans le chat, une à la fois, boutons de réponse sous le
   message, plus jamais dans « À valider » ; un seul aperçu à jour ; à la validation, livraison d'office dans RestedXP
   (remplace la route précédente du même personnage), avec son nom et où la trouver ; **commande sûre qui retire de
   RestedXP les routes livrées par l'agent** (groupe « Forever Routes »).
3. **Talents dès le niveau 1** : plan complet, lien Talents Forever et code Naowh pour le Training Planner.
4. **BiS et équipement** appuyés sur les addons (T10a revue), puis **route d'équipement** (4b).
5. **EllesmereUI** : lien de profil et bascule de rôle retirés par défaut.
6. **Refonte de l'interface** de ForeverBridge, après étude de Naowh Forever, Forever Companion, EllesmereUI et
   RestedXP (sans recopier leur code).

## Étude de l'existant (décisions 264 et 272 ; 2026-10-14, lecture locale seule)

Addons lus dans `C:\Program Files (x86)\World of Warcraft\_classic_beta_\Interface\AddOns` (aucun code recopié,
aucune écriture). **Partie web de la décision 264 non faite à ce stade** : en tête des blocs 4 (formats de poids,
échelles publiques) et 6 (bonnes pratiques d'interface), lecture seule.

| Besoin | Ce qui le fait déjà (version relevée) | Verdict |
| --- | --- | --- |
| Décisions d'une bonne route 1 à 22 (zones, regroupements, donjons, classe, villes, vols, foyer) | RestedXP 4.11.23 : parcours gratuits en clair, `Guides/Forever/` (une chaîne par zone de départ, variantes Mage « AoE » et « ADV », Skyborne « 1-14 Zephras Isle ») ; licence CC BY-NC-SA 4.0 (`RXPGuides/LICENSE`) | **Référence d'apprentissage** de l'optimiseur, **base adaptée** là où elle est meilleure (décision 277) |
| Routes de leveling calculées par simulation (1 à 60, toutes les zones de départ) | **Polestar Guides** (0xFitz, `github.com/fitzforge/polestar`, GPL-3.0 et exception pour les paquets de guides, v0.2.3 au commit `80dda0b` du 2026-10-14, dépôt créé le 2026-10-13 ; lu en lecture seule dans `<cache>/third_party/polestar`, rien exécuté) : recherche hors ligne (construction gloutonne aléatoire, recherche locale et recuit, redémarrages, passe de robustesse, route commune 12-60 par camp), guides retouchés à la main ensuite ; données Questie (sans licence), pfQuest (MIT), tables du client 1.60.1.70338 ; aucun relevé en jeu encore | **Référence de calibrage** (ses guides relus en local et rejoués par nos règles, comme RestedXP) et **idées reprises** en les réécrivant, citées ; ni code ni données copiés ; **contribution** sur accord (section ci-dessous) |
| Route pas à pas suivie en jeu | RestedXP (`ImportGuide`, public) ; Shortest Path Forever (suit la cible de RestedXP) | **Alimenter** : notre route livrée dans RestedXP |
| Retrait d'un guide importé | RestedXP : `/rxp import`, liste « current guides » et bouton Remove avec confirmation (`UI/V2/GuideImporter.lua:575-597`, `:1048-1056`) ; mais l'entrée en cache est rangée sous `clé|n` (`GuideLoader.lua:371-388`) et le bouton efface `clé` (`GuideImporter.lua:1052`) : le guide revient très probablement au `/reload` ; `addon.RemoveGuide` est interne (`GuideLoader.lua:208`, absent de `_G.RXPGuides`, `:1268-1273`) ; cache dans la SavedVariable de compte `RXPDB` (`RXPGuides.lua:1477`), relu au démarrage entrée par entrée (`GuideLoader.lua:774-837`) | **Construire** une commande sûre (bloc 2, question 12) |
| Toutes les quêtes, chaînes, taux de butin | Questie, Naowh (Discovery, Dungeon Journal), Forever Guide 1.35.1 (chaînes, butin), ForeverDungeonJournal, AtlasLoot | **Se servir** (déjà lus par T04d, DJ1, RX1) |
| Équipement de leveling par quête | GearQuest Forever 0.5.5-beta (modules de classe 0.3.6-beta) : `GQ.Data.<classe>Picks` dans des fichiers Lua générés, rien dans ses SavedVariables ; `/gq` | **Se servir** : lecture locale, renvoi à sa chasse |
| Montée de métier | SkillUp Forever 0.9.3 (plan, itinéraire, courses) | **Se servir** (routes de métier sur demande, MT1) |
| Plan de talents niveau par niveau | Naowh Training 1.1.15 (« Level by level », `!NFB1!`) ; Talents Forever Book 0.38.2 | **Alimenter** (déjà fait par EX1 dès le niveau 10) |
| Échelles de statistiques | Forever Companion 1.0.0 (données v88 du 2026-10-12) : import et export **Pawn v1** (`Scales.lua:361-373`), aucune API publique | **Alimenter** par une chaîne Pawn v1 collée par le joueur |
| Poids chez Naowh | Naowh 1.1.15 : « Import weights » (`NFSW1:` ou export EP de WoWSims) ; le Naowh Score **ne dépend pas des poids** | **Alimenter** (`NFSW1:`) |
| Listes BiS | Forever Companion (par spécialisation, phase « BETA », sans niveau, source et taux par objet) ; Naowh BiS (une liste par spécialisation, mise à jour le 11 octobre) ; **FojjiCore absent** (retiré entre le 10 et le 14 octobre) | **Se servir**, **construire** la liste personnelle classée, **alimenter** Naowh (`!NBIS1!`) |
| Comparaison d'équipement | Forever Guide (GearAdvisor, GearCalc, GearExplain) | **Recouper** |
| Origine d'un objet (route d'équipement) | Naowh Forever (lieu de chute et quêtes des objets de sa liste BiS) ; Forever Guide (recherche d'objets avec lieu et chance, quêtes de donjon et leurs chaînes, butin des boss et des monstres ordinaires) ; GearQuest Forever (objets de leveling par quête) ; AtlasLoot (butin par boss) | **Se servir** (lecture locale), écarts signalés ; rien recalculé |
| Thème compatible | EllesmereUI 9.5.4 : API publique d'habillage (`SKINNING_API.md`) | **Se servir en lecture** pour notre fenêtre |
| Organisation des fenêtres | Naowh, Forever Companion, EllesmereUI Options, RestedXP | **Étudier** (bloc 6), rien recopié |

**Les parcours gratuits contiennent-ils les quêtes de classe ?** Relevé du 2026-10-14 (livre de quêtes fusionné face
aux étapes de chaque chaîne, filtres de classe et de race appliqués, jusqu'au niveau 20) : **en partie**. Les quêtes de
classe de la zone de départ (niveaux 1 à 6 : lettres du maître, premières quêtes du Chaman, du Druide, du Paladin) y
sont pour la plupart ; celles du niveau 10 et au-delà en sont **presque toutes absentes** : The Hunter's Path (familier
du Chasseur), quêtes du Guerrier au 10, du Voleur au 10 et au 16, du Prêtre au 10, Fire Sapta et Call of Fire du
Chaman, chaînes du Mage au 10 et au 15 — y compris dans les variantes Mage « AoE » et « ADV » (une ou deux quêtes de
classe sur dix). Bruit du relevé, écarté : quêtes de fête (cadeaux de Winter Veil), 792 (prérequis douteux, LVL18),
quêtes raciales du Prêtre. Conséquence : nos routes placent elles-mêmes les quêtes de classe (décision 277, point 4).

### Polestar Guides (étude du 2026-10-14, demandée par l'utilisateur ; lecture seule)
- **Simulation** (`docs/SIMULATION.md`, `tools/lib/sim/`) : objectif = heures de jeu jusqu'au niveau 60 ; unité de
  recherche = « paquet » (une visite de zone, quêtes par tranches de 5 niveaux, ordre interne par plus proche voisin
  et 2-opt), pôles de quêtes de 150 yards avec maître de vol, auberge et maître ; construction gloutonne aléatoire
  (choix pondéré par l'XP par heure, température), recherche locale (échanger, insérer, retirer, ajouter, remplacer,
  fusionner) et recuit simulé, redémarrages jusqu'à convergence, graines fixes ; passe de robustesse sur 2000 tirages
  des paramètres ; route commune 12-60 par camp. Politiques : farm compté 2,5 fois, changement de zone pénalisé,
  zone de départ d'abord, aucun changement de continent avant le niveau 10, filtre « solo » (sans donjon, élite,
  réputation, répétable). Modèle : vitesses, détours de marche, vols du client, foyer, temps par monstre par niveau et
  par classe, journal de 20 quêtes (le nôtre : 40, repris de Factoruide, RTE2), XP des quêtes de la table `QuestXP` du
  client avec une pénalité d'écart de niveau et un facteur d'échelle observé sur Forever (règles de jeu à ne pas
  reprendre sans source : `suppose`).
- **Couverture** : toutes les zones de départ (Skyborne compris) puis une chaîne par camp jusqu'au 60 (sans les zones
  nouvelles de Forever 30-60), 65 guides de classe, quêtes de classe ajoutées aux guides de leveling le 2026-10-14,
  quêtes nouvelles de Forever ; donjons seulement comme alternative au farm (pour leur modèle, un donjon ne bat jamais
  les quêtes en solo).
- **Fraîcheur et validation** : dépôt de deux jours, plusieurs versions par jour ; aucun enregistrement de partie réelle
  encore (temps absolus « non garantis » selon l'auteur) ; aucune comparaison à RestedXP.
- **Licence** : GPL-3.0 pour le code et les guides ; l'exception ne couvre que les paquets produits par leur compilateur.
  Lire leurs guides pour se calibrer n'est pas restreint ; reprendre du code imposerait la GPL à ce qui serait
  distribué ; leurs faits de quêtes viennent en partie de Questie, sans licence. Choix proposé : **ni code ni données
  repris**, idées réécrites et citées (comme Factoruide, décision 266).
- **Comparaison sur une zone de départ, niveaux 1 à 10** (Gnome et Orc Guerriers, sans donjon ; nos chiffres et le
  rejeu de RestedXP par nos règles, ceux de Polestar par leur modèle, non rejoués chez nous : à comparer avec prudence)
  :

  | Route | Gnome Guerrier (Coldridge Valley) | Orc Guerrier (Valley of Trials) |
  | --- | --- | --- |
  | **Notre route** (`forever route plan --race`) | 1,95 h ; Dun Morogh **puis Elwynn Forest** (défaut à corriger, 1b) | 1,76 h ; Durotar, Orgrimmar au niveau 9 (« Hidden Enemies ») |
  | **RestedXP gratuit**, rejoué par nos règles | 2,99 h ; Dun Morogh → Loch Modan → Dun Morogh | 2,74 h ; Durotar |
  | **Polestar**, d'après son modèle | environ 2,0 h jusqu'au 10 ; Coldridge Valley → Kharanos → Dun Morogh, foyer une fois, Ironforge seulement vers 12 | environ 2,3 h ; Valley of Trials → Razor Hill → Durotar, foyer une fois, Orgrimmar seulement pour le Démoniste et le Chasseur |

  Lecture : les deux références restent dans la zone de la race jusqu'au niveau 10 et ne passent par la capitale
  qu'après, ou pour une classe ; notre route est plus courte sur le papier mais sort de la zone (Gnome) ou passe par la
  capitale plus tôt (Orc) ; nos rejeux sautent encore des étapes (quêtes inconnues, objectifs), d'où un temps de
  RestedXP sans doute surestimé.
- **Recommandation** : (1) **référence de calibrage**, en seconde référence après RestedXP : un lecteur de leurs guides
  (`accept`, `turnin`, `zone`, `hearth`, `fly`, `level`), lus dans le clone en cache, rejoués par nos règles dans la
  recette (1c) ; (2) **idées à reprendre**, réécrites et citées : paquets par visite de zone et pôles de quêtes,
  pénalité de changement de zone et règle « zone de départ d'abord, pas de changement de continent avant le 10 »,
  construction aléatoire pondérée et recuit avec redémarrages, passe de robustesse, route commune par camp au-delà des
  zones de départ, **sauf sa règle sur les donjons** (pour son modèle, un donjon ne bat jamais les quêtes en solo) : nos
  routes incluent toujours par défaut les donjons avec leurs quêtes au premier passage et les quêtes de classe
  (décisions 277 et 278) ; (3) **contribution**, plus tard et sur ton accord : nos relevés réels (temps par monstre, XP des
  quêtes de Forever) leur manquent ; une issue pour les écarts que la recette trouvera.

## Constats (dépôt, 2026-10-14 ; chemins `fichier:ligne` pour la relecture)

### Routes (bloc 1)
- **Cause 1 : la position du personnage n'atteint jamais le planificateur.** `RouteRequest` ne porte ni race, ni carte,
  ni coordonnées (`forever/route.py:219-235`) ; MCP (`forever/mcp_server.py:428-441`) et CLI (`forever/cli.py:414-432`)
  non plus ; le pont n'envoie que classe, camp et niveaux (`forever/bridge/plans.py:243-249`) ; ForeverBridge envoie
  `race`, `zone`, `subzone` et `map` sans coordonnées (`addon/ForeverBridge/Message.lua:370-374`), et `Resolved` ne
  garde que `zone` (`forever/bridge/context.py:209`).
- **Cause 2 : le départ est la quête de plus petit identifiant.** `start_quest` trie par (permise, écart de niveau,
  niveau minimal, id) (`forever/route.py:618-622`) : à égalité, une quête d'Elwynn Forest passe avant celle de
  Coldridge Valley ; le trajet initial vaut zéro (`forever/route.py:740-746`, `forever/engine/route.py:312`).
- **Le masque de race seul ne suffirait pas** : ces deux quêtes ont le même masque (toute l'Alliance).
- **Jetons de race des Skyborne** : `who_for` donne `HighOrderSkyborne` (`forever/rxp_guides.py:353-357`) alors que
  RestedXP attend `Skyborne` (`#defaultfor Skyborne`), le `client_file` de `races.json` : la chaîne Skyborne est
  introuvable aujourd'hui.
- **Quêtes faites** : le champ `completed` du livre est l'**union de tous les personnages** (QuestieConfig lue sans
  nom, `forever/pipeline/quest_sources.py:397-407`) ; les quêtes faites **par personnage** sont au profil
  (`quests_completed`, par GUID de Questie, `forever/profile_import.py:311-317`), jamais lues par la route.
- **Filtres absents** (`forever/route.py:386-450`) : masque de race, répétable, effort de guerre, métier requis,
  événement, capitale ou autre continent ; `specialFlags` et `requiredSkill` de Questie non lus
  (`forever/pipeline/quest_sources.py:99-113`).
- **Artefacts du modèle** : un rendu d'objets compté comme des combats au niveau de la quête (`forever/route.py:339-343`,
  `:428`) ; quêtes trop hautes écartées seulement dans `best_zone_xp_h` (`forever/engine/route.py:487`).
- **Farm** : seulement en fin de route, sans contrôle des quêtes restantes (`forever/optimize/route.py:99-110`,
  `:192-193` ; `forever/engine/route.py:451-455`).
- **Déjà là pour la mesure** : lecteur des parcours (`forever/rxp_guides.py`), chaîne par personnage (`guide_chain`),
  rejeu par nos règles (`forever/compare.py`, `replay_rxp`, `breakdown` des zones `:314-337`), départ commun au
  donneur de la première quête du parcours (`:383-395`). Le lecteur jette le texte des étapes à dessein (décision 268) :
  la base adaptée exige de garder les lignes de chaque étape.
- **Choix du parcours par RestedXP** : le premier guide enregistré dont `#defaultfor` s'applique devient le guide par
  défaut (`GuideLoader.lua:201-203`, ordre de chargement du `.toc`) ; `guide_chain` prend au contraire le défaut de
  plus bas niveau, donc « 1-5 Coldridge Valley » pour un Gnome Mage au lieu de sa variante Mage.

### Conversation et livraison (bloc 2)
- Les trois questions de `ROUTE_CHOICES` (`forever/bridge/choices.py:34-53`) partent **ensemble** en cartes de
  « À valider » (`forever/bridge/loop.py:201-203`).
- **Deux sources de vérité pour « À valider »** : le compteur compte toutes les cartes visibles, questions comprises
  (`ForeverBridge.lua:1025-1035`, `:1214-1215`) ; le modèle ne voit jamais les cartes publiées
  (`forever/bridge/plans.py:256-260` ; `forever/update.py:2685-2690`).
- L'historique est un `ScrollingMessageFrame` (`ForeverBridge.lua:272-294`) : pas de boutons enfants.
- Le modèle ne peut pas émettre de question (`forever/bridge/agent.py:58-76`).
- **Aperçus** : un fichier par demande (`forever/route.py:793-853`), rien n'est lié au personnage ; deux aperçus
  coexistent.
- **Livraison** : `_deliver_route` prend le plan le plus récent de même classe et camp, pas du personnage
  (`forever/bridge/loop.py:467-489`) ; nom `Forever <Classe> a-b (<id6>)` (`forever/route.py:856-859`) ; chaque
  import ajoute une entrée `clé|n` au cache de RestedXP : deux imports du même guide laissent deux entrées, relues dans
  un ordre quelconque au démarrage (question RXP3).

### Talents, EllesmereUI, fenêtre (blocs 3, 5, 6)
- Au niveau 1, le bouton Talents demande le point du niveau suivant (`forever/bridge/plans.py:51-57`) et
  `forever_build` refuse (`forever/build.py:278-284`) ; à partir du niveau 10, lien et code sont déjà rendus
  (`forever/talents_forever.py:575-603`).
- EllesmereUI : lien dans la réponse Exports (`forever/bridge/exports.py:126-151`), bascule à `/fb role`, à la connexion
  et en sortie de combat (`ForeverBridge.lua:2075-2152`, `:2311-2323`), aucun réglage pour l'éteindre.
- Fenêtre : 520×360, jusqu'à huit boutons de 100 px enchaînés sans retour à la ligne (`ForeverBridge.lua:357-364`,
  `:492-503`), réponses en texte brut (`:608-639`).

## À valider

Réponses retenues le 2026-10-14 (décision 275) : **Q1** une branche par bloc, fusion dès la CI verte, bloc « accepté »
à ton accord ; **Q4** aucun téléchargement de table pour les catégories de quêtes (Questie et tables présentes, sinon
`suppose` et question ouverte) ; **Q10** règles de méthode dans les décisions et `CLAUDE.md`. **Q2 et Q3 caduques**
(décision 277 : zone de départ prise du parcours gratuit de la race, parcours comme référence et non comme recette).
Questions encore ouvertes, tranchées au début de leur bloc (défaut proposé en premier) :

5. **Questions dans le chat** (bloc 2). *Défaut* : la question en cours s'affiche sous le dernier message avec une
   rangée de vrais boutons ancrée sous l'historique (au plus quatre, plus « Autre ») ; une seule à la fois ; le modèle
   peut aussi poser une question par un bloc structuré, relu et borné par le pont. *Autre* : liens cliquables dans le
   texte.
6. **Aperçu et livraison** (bloc 2). *Défaut* : une seule route « en cours » par personnage ; « Valider et livrer » et
   « Ajuster » sous l'aperçu ; nom stable « Forever · <Personnage> · <a>-<b> », groupe « Forever Routes » ; le bouton
   « Livrer dans RestedXP » est retiré. *Autre* : garder un bouton de livraison séparé.
7. **BiS** (bloc 4). *Défaut* : liste personnelle depuis Forever Companion et Naowh (FojjiCore relu s'il revient) ;
   classée par nos poids (Mage) ou l'échelle de Forever Companion (`suppose`) ; exportée en `!NBIS1!` pour toutes les
   classes ; tables d'objets du client téléchargées par la voie existante (**accord réseau demandé**) ; PER8 avancée de
   SIM1 si les objets portent des notations. *Autre* : Mage seulement pour l'export.
8. **EllesmereUI** (bloc 5). *Défaut* : éteint par défaut, `/fb eui on|off`, `/fb role clear`. *Autre* : retirer le
   code de bascule.
9. **Thème** (bloc 6). *Défaut* : habillage par l'API publique d'EllesmereUI quand il est chargé, sinon thème sobre ;
   maquettes montrées avant tout code. *Autre* : thème propre toujours.
11. **« Aussi bonne »** (bloc 1). *Défaut* : sur chaque zone de départ et chaque tranche couverte, notre route est
    « aussi bonne » quand son temps simulé ne dépasse pas celui du parcours rejoué par nos règles (mêmes départ,
    personnage, donjons et quêtes de classe) et que son enchaînement de zones est le même, ou que l'écart est expliqué
    et chiffré ; tant qu'elle ne l'est pas, la base adaptée est livrée sur cette tranche. Variante du Mage : celle que
    RestedXP choisit lui-même (premier `#defaultfor` permis), l'autre sur demande. *Autre* : une tolérance de temps à
    fixer.
12. **Commande de retrait des routes livrées** (bloc 2). Le bouton Remove de `/rxp import` existe, mais n'efface
    probablement pas l'entrée en cache (constat plus haut) et `RemoveGuide` est interne. *Défaut* :
    `forever route rxp-clean` **jeu fermé** : liste d'abord (essai à blanc), puis, sur confirmation, retire de la
    SavedVariable de compte `RXPDB` (`SavedVariables/RXPGuides.lua`) **les seules entrées dont la clé commence par
    `Forever Routes|`**, après une copie datée du fichier ; refus si le jeu tourne ou si le fichier ne se relit pas à
    l'identique hors de ces entrées ; c'est une écriture dans la SavedVariable d'un addon tiers : **ton accord explicite
    est demandé ici** (décision 272). *Autre* : seulement documenter le bouton de RestedXP et le `/reload`, à vérifier
    en jeu (RXP3).

## Conception

### Bloc 1 — Routes (décision 277)

**1a. Départ réel et quêtes faites.**
- `RouteRequest` gagne `race`, `character` et `start` (carte `uiMapID`, x, y) ; MCP `forever_route`, CLI
  `forever route plan --race --character --at <carte>,<x>,<y>` (forme au bloc) ; le pont les remplit depuis le
  contexte (`Resolved` garde `map` ; ForeverBridge envoie x et y hors combat, `C_Map.GetPlayerMapPosition` sous
  `pcall`).
- Départ (`start_position`, fonction pure) : position du contexte ; sinon, au niveau 1, premier donneur du parcours
  gratuit de la race ; sinon la règle de RX1c, départagée par la distance, plus par l'identifiant. Trajet initial compté.
- `who_for` prend le `client_file` de `races.json` (Skyborne, Scourge → Undead).
- Quêtes faites : `quests_completed` du personnage au profil (Questie, par GUID), relu à chaque demande ; la quête
  en cours (journal envoyé par le pont, forme au bloc) comptée comme prise ; jamais le champ `completed` du livre.

**1b. Défauts et garde-fous.**
- Donjons avec leurs quêtes (DJ1, niveau où ils rapportent le plus) et quêtes de classe **inclus par défaut** ; la
  demande peut les retirer (« sans donjon », « sans quêtes de classe »).
- Filtres avant la recherche : autre race (masque), autre camp, effort de guerre, répétable, événement, métier (sauf
  route de métier), quête trop haute pour être faite au niveau du personnage (seuil des données, origine déclarée,
  `suppose` sans source) ; catégories lues dans `specialFlags` et `requiredSkill` de Questie (lus en plus par
  `quest_sources.py`).
- Objectif « rapporter des objets » plus jamais compté comme des combats ; registre I18.
- Contrôles après la recherche, avec raison : première zone ≠ zone du départ, quête d'une autre race ou d'un autre
  camp, capitale ou autre continent sous le niveau 10 sans raison (quête de classe, maître, donjon), farm alors qu'une
  quête faisable reste dans la zone ou une zone voisine.
- **Zone de départ d'abord** (constat du 2026-10-14 : le Gnome Guerrier part vers Elwynn Forest ; règle aussi tenue par
  Polestar et RestedXP) : sous le niveau des bas niveaux, l'optimiseur ne prend aucune quête dans la zone de départ
  d'une autre race ni dans une capitale, sauf quête de classe, maître ou quête que le parcours de référence de la race
  fait aussi ; à corriger **avant l'essai du samedi 17**.

**Acceptation des routes (décision 279, 2026-10-14)** : sans essai en jeu ; une route est acceptée si elle ressemble
au parcours gratuit de RestedXP de la même race et classe (même enchaînement de zones, mêmes quêtes à deux ou trois
différences près, chacune expliquée : quête de classe, donjon avec ses quêtes, gain mesuré), sinon refusée avec
l'écart expliqué ; Polestar au-delà des parcours gratuits ; contrôle sur toutes les zones de départ et classes.

**1c. Mesure des décisions face aux parcours gratuits (« recette »).**
- `forever route recette` (forme au bloc) : pour chaque race (dix races, sept zones de départ, variante Mage
  comprise) et chaque tranche couverte (1 à 10, puis jusqu'à la fin du parcours), notre route et le parcours rejoué par
  nos règles, même personnage et même départ ; **décisions comparées** : enchaînement des zones, regroupement des
  quêtes (quêtes prises et rendues au même passage), niveau d'entrée des donjons et des quêtes de classe, retours en
  ville (maître, capitale), vols et pierre de foyer, farm ; temps et XP par heure.
- Sortie : écarts chiffrés, chacun avec son explication (règle manquante, poids, donnée absente) ; aucun texte de guide
  dans la sortie ni dans le dépôt ; résultats agrégés dans `docs/research/rxp-comparaison.md`.
- **Seconde référence : Polestar Guides** (étude plus haut) : lecteur de leurs guides (clone en cache, commit épinglé
  dans la provenance, lecture locale, rien exécuté), rejoués par nos règles comme RestedXP ; trois colonnes (notre
  route, RestedXP, Polestar) ; leurs guides couvrent aussi 12 à 60, référence là où RestedXP gratuit s'arrête.
- `rxp-compare` passe la race au calcul de notre route (il ne la passait pas : un Gnome partait vers Elwynn Forest).

**1d. Trajets comme en jeu** (cœur de RX2, question RTE3, registre I19).
- Vols : points de vol découverts en passant au maître de vol (au niveau 1 aucun n'est connu), vols connus du personnage
  envoyés par le pont quand il les voit (forme au bloc) ou gardés au profil ; durée des vols du client (`TaxiPath`).
- Pierre de foyer : lieu lié (changeable à un aubergiste, arrêt de la route), recharge lue dans les données de la
  version (origine déclarée) ; la recherche choisit entre marche, vol, foyer.

**1e. Réglage de l'optimiseur.**
- Idées de Polestar à essayer en premier, réécrites et citées (GPL-3.0 : aucun code repris) : visite de zone comme
  unité (paquets par tranche de niveaux, pôles de quêtes), pénalité de changement de zone, construction aléatoire
  pondérée par l'XP par heure, recuit et redémarrages, passe de robustesse, route commune par camp au-delà du 12.
- Boucle : recette → écart le plus coûteux → règle ou poids changé (regroupement par pôle de quêtes, coût d'un retour
  en ville, valeur d'une quête de classe, seuil `_worth_it`, poids de zone) → recette refaite ; chaque réglage noté
  (avant, après, zones concernées) ; aucun réglage qui améliore une zone en dégradant une autre sans le dire.
- Les réglages sont des paramètres de l'optimiseur (données de méthode, pas des chiffres de jeu) ; ils servent tels
  quels au-delà des parcours, jusqu'au niveau maximal.

**1f. Base adaptée là où le parcours est meilleure** (question 11).
- Le lecteur garde les lignes de chaque étape (`Step.raw`) ; l'unité d'adaptation est **l'étape entière** : on retire
  une étape dont toutes les quêtes sont faites, on insère nos étapes (quêtes de classe absentes, donjons et leurs
  quêtes) encodées par `forever/rxp.py` ; les filtres `<<`, gardes `.xp` et `isonquest` restent tels quels (RestedXP
  les évalue).
- En-tête neuf : `#name Forever · <Personnage> · <a>-<b>`, `#group Forever Routes`, sans `#next` ni `#defaultfor`
  hérités ; commentaire d'attribution : parcours sources nommés, « RestedXP Guides, CC BY-NC-SA 4.0 », usage personnel
  non commercial, adaptation sous la même licence.
- **Jamais moins bonne** : un changement non demandé qui allonge le temps simulé est retiré et l'aperçu le dit ; un
  changement demandé (donjon, quête de classe) affiche son coût en temps.
- Fin de route à une frontière d'étape après le niveau visé (estimé par le rejeu, dit comme tel).

**1g. Autres routes sur demande** (après 1a à 1f) : réputation (quêtes de réputation connues), métier (itinéraire de
SkillUp Forever lu en local, visites aux maîtres, récolte sur le chemin), sous les mêmes garde-fous.

### Bloc 2 — Conversation, livraison et retrait
- **Questions** (question 5) : séquentielles, une par réponse du pont, champ `choices` dans la réponse, rangée de
  boutons sous l'historique, action `a=choice:` existante ; donjons et quêtes de classe ne sont plus demandés (inclus
  par défaut, décision 277) ; les cartes de choix ne sont plus publiées.
- **Compteur cohérent** : un seul calcul des cartes visibles ; le pont donne au modèle, à chaque message, le nombre et
  le titre des cartes réellement publiées.
- **Route en cours par personnage** (question 6) ; aperçu remplacé à l'ajustement ; validation → livraison d'office,
  nom stable ; avant l'import, retrait en jeu de la version précédente si RestedXP le permet par son API publique,
  sinon nom stable et `/reload` conseillé, puis `forever route rxp-clean` (question 12) pour les doublons ; message
  qui dit où trouver le guide (libellés de RestedXP relus en anglais, client enUS).
- **Retrait sûr** (question 12) : `forever route rxp-clean [--apply]` jeu fermé, essai à blanc par défaut, copie
  datée, seules les clés `Forever Routes|…`, relecture du fichier après écriture ; bouton ou commande du pont qui
  l'annonce (le pont ne l'exécute pas jeu ouvert).
- **Relecture humaine** : la première route de chaque zone de départ est montrée en texte (zones et quêtes dans
  l'ordre) avant d'être livrée.

### Bloc 3 — Talents dès le niveau 1
- Plan jusqu'à l'objectif quel que soit le niveau ; sous le premier niveau de talent, « ton premier point arrive au
  niveau N » (lu dans les données) et le plan complet, le lien Talents Forever et le code `!NFB1!` à coller dans Naowh
  Training (Builds, Import). Mage calculé ; autres classes : build populaire le plus proche, ordre généré signalé.

### Bloc 4 — BiS et équipement (T10a revue)
- Poids du Mage par le moteur (`forever/engine/`, fonctions pures), par niveau et contexte, rendus en `NFSW1:` et en
  Pawn v1, nommés « Forever · <Personnage> · <contexte> ».
- Liste personnelle : listes de Forever Companion et de Naowh lues en local (cache, jamais dans le dépôt), fusionnées
  par emplacement, classées (question 7), lieu de butin, exportées en `!NBIS1!`.
- Leveling : choix de GearQuest Forever lus dans ses fichiers générés, renvoi à `/gq`.
- « Est-ce une amélioration ? » dans le chat : nos poids (Mage) et l'échelle active de Forever Companion (`suppose`),
  Naowh Score cité comme le leur ; source et certitude ; « non calculé » sans poids.
- `forever gear` (commande et outil MCP, forme au bloc), provenance complète.

### Bloc 4b — Route d'équipement (décision 277, point 6)
- Entrée : liste BiS du personnage (Forever Companion, Naowh, puis notre liste du bloc 4), emplacements choisis.
- Source de chaque objet, **lue en local** dans les addons qui la connaissent déjà (décision 272 ; précision de
  l'utilisateur du 2026-10-14) :
  - **Naowh Forever** : où tombe chaque objet de sa liste BiS (boss, donjon, taux) et quelles quêtes le donnent ;
  - **Forever Guide** : recherche d'objets avec lieu et chance, récompenses et chaînes des quêtes de donjon, butin des
    boss **et des monstres ordinaires** ; GearAdvisor et GearCalc en recoupement seulement ;
  - **GearQuest Forever** : équipement de leveling par quête (objet, plage de niveaux, quête) ;
  - **AtlasLoot** : butin par boss ;
  - puis nos données : récompenses du livre des quêtes, donjons et boss de DJ1 (`dungeons.json`) ; marchand ou
    métier, sinon « source inconnue ».
  Les **écarts entre sources** (lieu, boss, taux, quête) sont signalés objet par objet, jamais tranchés au hasard ;
  relevés du joueur (ForeverLogger) premiers quand ils existent ; certitude au mieux `suppose` pour un addon.
- Ordre : l'optimiseur de routes ordonne quêtes, donjons et trajets (mêmes garde-fous) ; un objet de donjon à faible
  taux donne un **passage en boucle** avec le nombre de passages attendu (espérance et nombre pour une chance de 90 %,
  fonctions pures dans `forever/engine/`, registre) ; plusieurs objets d'un même donjon cumulés.
- Livraison dans RestedXP comme une route de leveling ; aperçu par objet (source, taux, passages, temps).

### Bloc 5 — EllesmereUI éteint par défaut (question 8)
- `exports.py` ne propose plus profil ni rôle sauf réglage allumé ; `FB.SwitchProfile` jamais appelé réglage éteint ;
  `/fb eui on|off`, `/fb role clear` ; aide mise à jour.

### Bloc 6 — Refonte de l'interface de ForeverBridge
- Étude (locale, puis web en lecture seule) dans `docs/research/interface-addons.md` (principes, aucun code).
- Maquettes montrées pour accord (question 9), puis : navigation (Chat, Feuille de route, Talents, Équipement, Exports,
  Mises à jour) ; barre d'actions hiérarchisée, jamais de chevauchement (test lupa à toutes les largeurs permises) ;
  assistant de feuille de route (niveaux, cases à cocher, « Calculer », aperçu en carte, « Valider et livrer ») ;
  historique en cartes ; compteur cohérent ; aide d'accueil courte ; thème ; ancienne fenêtre gardée derrière un
  réglage jusqu'à l'acceptation. Aucune fonction protégée, rien en combat.

## Blocs et calendrier (fin de la bêta annoncée le 21 octobre, sortie le 4 novembre)

| Dates | Bloc | Essai en jeu |
| --- | --- | --- |
| 14 oct. (soir) | **0** — Intégration : décisions 272 à 277, ROADMAP, DATA_SOURCES, inventaire, `CLAUDE.md`, archivage | — |
| 15 → 18 oct. | **1** — Routes : 1a départ réel et quêtes faites, 1b défauts et garde-fous, 1c recette, 1f base adaptée (ce qui sert dès l'essai), puis 1d vols et foyer | sam. 17 (1a, 1b, 1f) et dim. 18 |
| 19 → 20 oct. | **2** — Conversation, aperçu unique, livraison d'office, retrait sûr | 20 et 21 |
| 20 oct. | **3** — Talents dès le niveau 1 ; **5** — EllesmereUI éteint | 20 et 21 |
| 21 oct. au soir | Fin de la bêta : corrections des essais 1, 2, 3, 5 avant la fermeture si possible | dernier jour |
| 19 oct. → 3 nov. | **1e** — Réglage de l'optimiseur sur la recette (en continu, hors jeu), puis 1g | au 4 nov. |
| 22 → 26 oct. | **4** — BiS et équipement | au 4 nov. |
| 27 → 28 oct. | **4b** — Route d'équipement ; maquettes du bloc 6 montrées le 28 | au 4 nov. |
| 29 oct. → 2 nov. | **6** — Nouvelle fenêtre | au 4 nov. |
| 3 nov. | Marge ; `docs/LANCEMENT.md` (essais restés en attente) | — |
| 4 nov. | Sortie : essais des blocs 1e, 1g, 4, 4b, 6 ; clôture de CJ1 à ton accord | 4 nov. et suivants |

Ce qui glisse : SIM1 et la suite de RX2 (quêtes lancées par un objet, comparaison à Factoruide refaite) après le
4 novembre ; CM1 dès la sortie (décision 261). Si un essai des blocs 1, 2, 3 ou 5 échoue, sa correction passe devant
les blocs 4 à 6.

### Bloc 0 — Intégration (fait le 2026-10-14 avec cette révision)
- `docs/DECISIONS.md` : 272 à 277 ; 268 marquée « amendée par 277 ».
- `docs/ROADMAP.md` : CJ1 en tête du calendrier ; T10a, RX2, SIM1, MT1 et l'idée « fenêtre du chat » mises à jour.
- `docs/DATA_SOURCES.md` : Forever Companion, GearQuest Forever, Naowh BiS et Stat Weights, FojjiCore absent,
  RestedXP comme référence d'apprentissage (277) ; « Addons pilotés » : Pawn v1 vers Forever Companion.
- `tasks/inventaire-addons.md` : relevé du 2026-10-14.
- `docs/OPEN_QUESTIONS.md` : questions ci-dessous ; `CLAUDE.md` : trois règles de méthode.
- Archivage des deux fichiers de base dans `tasks/archive/`.

## Procédures d'essai en jeu (courtes ; `docs/ADDON.md`, celles d'après le 21 dans `docs/LANCEMENT.md`)
- **CJ-1** (routes) : un Gnome neuf à Coldridge Valley et un personnage Horde neuf (Orc ou Troll à Valley of Trials) ;
  « Feuille de route » 1 à 10 ; attendu : départ de ta position, zones dans l'ordre des parcours gratuits (ou écart
  expliqué), quêtes de classe et donjon au bon niveau, aucune capitale sans raison, aucune quête d'une autre race ni
  d'effort de guerre ; un personnage déjà avancé : ses quêtes faites absentes.
- **CJ-2** (conversation) : question dans le chat avec ses boutons, absente de « À valider », compteur cohérent ;
  ajustement qui remplace l'aperçu ; « Valider et livrer » ; une deuxième route du même personnage remplace la
  première (après `/reload` aussi) ; jeu fermé, `forever route rxp-clean` puis connexion : plus aucune route
  « Forever Routes ».
- **CJ-3** (talents) : niveau 1, plan complet, lien Talents Forever et code Naowh importable.
- **CJ-5** (EllesmereUI) : aucune proposition de profil ni bascule ; `/fb eui on` les rallume.
- **CJ-4**, **CJ-4b**, **CJ-6** (au 4 novembre) : poids importés dans Forever Companion et Naowh, liste `!NBIS1!`
  visible chez Naowh, « est-ce une amélioration ? » ; route d'équipement livrée, passages en boucle annoncés ; nouvelle
  fenêtre à toutes les tailles, avec et sans EllesmereUI.

## Tests attendus (aucun chiffre de jeu dans un test : valeurs de `tests/fixtures/` ou de `forever/data/`)
- **Bloc 1** : départ par position, puis par race pour les dix races (jetons de RestedXP, Skyborne compris) sur un monde
  et des guides fabriqués ; départage par distance ; trajet initial compté ; quêtes faites du seul personnage retirées ;
  donjons et quêtes de classe inclus par défaut, retirés à la demande ; chaque filtre et chaque garde-fou ; rendu
  d'objets non compté comme combat ; recette : décisions comparées et écarts nommés sur guides fabriqués, sortie sans
  texte de guide ; base adaptée : étapes faites retirées, insertions à la bonne place, en-tête et attribution, aucun
  `#next` hérité, changement non demandé plus lent retiré ; vols connus pris seulement s'ils sont plus courts, vol
  inconnu jamais, foyer et sa recharge.
- **Bloc 2** (Python et lupa) : une question à la fois ; boutons et `a=choice:` ; aucune carte de choix ; compteur et
  ligne d'état égaux ; route en cours par personnage ; livraison à la validation, nom stable ; `rxp-clean` : essai à
  blanc, seules les clés `Forever Routes|`, copie datée, refus jeu ouvert, fichier relu à l'identique hors de ces
  entrées (SavedVariable fabriquée dans `tmp_path`).
- **Bloc 3** : bouton Talents aux niveaux 1, 9 et 10, Mage et une autre classe.
- **Bloc 4** : poids déterministes ; va-et-vient `NFSW1:`, Pawn v1, `!NBIS1!` ; fusion et classement sur fixtures
  fabriquées ; rien des listes dans le dépôt ; amélioration avec source et certitude.
- **Bloc 4b** : source de chaque objet (quête, boss, inconnue) ; passages attendus (fonctions pures, registre) ; route
  ordonnée sous les garde-fous ; cumul de plusieurs objets d'un donjon.
- **Bloc 5** et **6** (lupa) : réglage éteint par défaut ; aucune bascule ; barre sans chevauchement aux tailles
  extrêmes ; assistant qui produit la même requête que la conversation ; habillage sur bouchon de l'API d'EllesmereUI.

## Registre (`docs/MECHANICS_REGISTRY.yaml`)
I18 (route : départ, quêtes faites, filtres, objectifs d'objets, garde-fous, recette, base adaptée), I19 (vols et
foyer) ; entrée nouvelle pour l'accessibilité d'une quête trop haute (`suppose` sans source) ; passages attendus d'un
donjon en boucle (bloc 4b) ; poids des statistiques du Mage (bloc 4 ; A4, A5, A7, A8, B2 si PER8 est avancée). Comptes
de `test_registry.py` écrits au commit « tests » du bloc concerné.

## Questions ouvertes (`docs/OPEN_QUESTIONS.md`)
- **RTE3** (précisée) : zone de départ et vols connus, vus en jeu par le pont.
- **RTE2** (complément) : Polestar compte un journal de 20 quêtes, Factoruide 40 « on WoW Forever » ; relevé en jeu attendu.
- **RTE7** : les guides de Polestar, rejoués par nos règles, battent-ils notre route sur les zones de départ et au-delà du 22 ? Réponse par la recette (1c).
- **RTE6** : les quêtes d'effort de guerre de Forever sont-elles faisables et rémunérées à bas niveau ? Écartées des
  routes d'ici là.
- **RXP3** : deux imports du même guide laissent deux entrées `clé|n` dans `RXPDB` : laquelle RestedXP charge-t-il au
  démarrage, et le bouton Remove de `/rxp import` efface-t-il vraiment un guide importé ?
- **FC1** : une échelle Pawn v1 produite par forever s'importe-t-elle dans Forever Companion ?
- **NBIS2** : la liste `!NBIS1!` personnelle s'affiche-t-elle chez Naowh avec ses lieux de butin ?
- **GQ1** : les fichiers générés de GearQuest Forever restent-ils stables d'une version à l'autre ?

## Hors périmètre
Quêtes lancées par un objet (RX2, après la sortie) ; SIM1 ; poids et BiS calculés des autres classes ; écriture dans
une SavedVariable d'un addon tiers autre que le retrait du bloc 2 accordé ; appel d'une fonction interne d'un addon
tiers ; texte des parcours de RestedXP dans le dépôt ; tout guide payant ou chiffré.

## Risques
- **Fenêtre de jeu courte** : routes d'abord, base adaptée pour que l'essai du 17 serve même si l'optimiseur n'est pas
  encore réglé ; fusion dès la CI verte.
- **Réglage de l'optimiseur long** : il continue hors jeu jusqu'au 3 novembre ; la base adaptée couvre les tranches où
  il reste moins bon, et l'aperçu dit laquelle des deux est livrée.
- **Licence** : adaptation pour l'usage personnel et non commercial de l'utilisateur seulement, attribution dans chaque
  guide livré ; rien n'est publié ni redistribué.
- **Cache de RestedXP** : doublons possibles avant le bloc 2 ; retrait sûr jeu fermé.
- **Formats tiers mouvants** : version relevée dans la provenance, changement signalé par `forever addons status`.
- **Refonte sans jeu avant le 4 novembre** : maquettes validées d'abord, banc lupa étendu, ancienne fenêtre gardée.

## Angles morts (prévus)
- Monstres tués en chemin (RTE5) et quêtes lancées par un objet (RTE4) : XP par heure sous-estimée, quêtes manquantes.
- Au-delà des parcours gratuits (après le niveau 22 environ), la qualité repose sur les réglages appris en dessous,
  sans référence pour la vérifier.
- Poids des autres classes repris de Forever Companion (`suppose`).

## Étapes d'exécution
1. Bloc 0 committé sur `main` avec cette révision.
2. Pour chaque bloc : `git fetch`, branche `cj1-N` depuis `origin/main`, tests d'abord (`CJ1: tests (bloc N)`), puis
   `CJ1: bloc N vert` ; `uv run tasks.py quick` pendant le travail ; `uv run ruff check . --no-cache` et
   `uv run tasks.py verify` une fois avant de pousser ; CI verte sous Ubuntu et Windows ; fusion en fast-forward
   (revérifier `origin/main` juste avant) ; plugin et skills touchés mis à jour (`forever-routes`, `forever-builds`) ;
   ForeverBridge réinstallé ; pont arrêté puis relancé ; procédure d'essai donnée ; arrêt pour ton essai.
3. Fin de tranche : `/verifier`, résumé (Bloqué sur moi, Fait, Tests ajoutés, Registre modifié, Questions ouvertes,
   Angles morts), clôture à ton accord.

## Critères de fin
Blocs 0 à 6 et 4b fusionnés et **acceptés en jeu par l'utilisateur** ; pour chaque zone de départ et tranche couverte,
notre route aussi bonne que le parcours gratuit (question 11) ou la base adaptée livrée avec l'écart dit ; départ
réel et quêtes faites ; donjons et quêtes de classe par défaut ; questions dans le chat, compteur cohérent, aperçu
unique, livraison d'office, retrait sûr ; plan de talents dès le niveau 1 ; poids et liste BiS exportés ; route
d'équipement ; EllesmereUI éteint par défaut ; nouvelle fenêtre sans débordement ; registre à jour ;
`test_addon_rules.py` et `check_addon.py` verts ; `uv run tasks.py verify` vert.
