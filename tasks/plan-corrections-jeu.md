# CJ1 — Corrections après les essais en jeu du 14 octobre : plan

Tranche hors de la table de la ROADMAP, demandée par l'utilisateur le 2026-10-14 après ses essais en jeu (personnage
neuf « Bob », Gnome, Alliance, niveau 1, Coldridge Valley). Code proposé : **CJ1** (lettres CJ, « corrections après le
jeu », à valider, question 1). Elle passe **avant toutes les autres tranches** jusqu'au 4 novembre (RX2, SIM1, T10a
telle qu'écrite) et reprend en elle T10a revue selon l'audit des addons. Plan écrit le 2026-10-14, sans code ; arrêt
pour validation.

Bases : `tasks/idees-du-chat-2026-10-14-ux-routes.md` (interface, routes, exports, talents) et
`tasks/audit-addons-capacites-2026-10-14.md` (ce que les addons installés font déjà), intégrées au bloc 0 puis
archivées dans `tasks/archive/`.

## Demande de l'utilisateur (2026-10-14)

**Règles de méthode, à consigner** (bloc 0) :
1. Avant de construire une fonction, regarder si un addon installé la fait déjà (Forever Companion, Naowh Forever,
   GearQuest Forever, Forever Guide, SkillUp Forever, Talents Forever, RestedXP, Shortest Path Forever…). Si oui,
   l'agent s'en sert (lecture locale, agrégats seulement, décision 133) et l'alimente par des exports ; il ne refait
   ni son interface ni ses données.
2. Rien n'est déclaré fini tant que l'utilisateur ne l'a pas essayé et accepté en jeu : chaque bloc se termine par une
   courte procédure en jeu, et la tranche ne se ferme qu'avec son accord.
3. « Mon interface est la mienne » : rien ne modifie EllesmereUI sans demande explicite.

**Contenu, dans l'ordre de priorité** :
1. Routes, priorité absolue : départ depuis la position du personnage et la zone de départ de sa race ; test par race
   de départ, Alliance et Horde ; garde-fous de vraisemblance ; recette de référence (la route 1 à 10 de chaque zone
   de départ suit le même enchaînement de zones que les parcours gratuits de RestedXP, sinon elle est refusée et
   l'écart expliqué) ; vols connus et pierre de foyer (RX2) si le temps le permet.
2. Conversation de la feuille de route : questions dans le chat, une à la fois, boutons de réponse sous le message,
   plus jamais dans « À valider » ; un seul aperçu à jour ; à la validation de l'aperçu, livraison d'office dans
   RestedXP (remplace la route précédente du même personnage), avec son nom et où la trouver.
3. Talents dès le niveau 1 : plan complet (niveau 10 à l'objectif, point par point dans l'ordre de prise), lien Talents
   Forever et code Naowh pour le Training Planner.
4. BiS et équipement appuyés sur les addons (T10a revue) : poids calculés exportés vers Forever Companion et Naowh ;
   liste BiS personnelle bâtie depuis Forever Companion, Naowh et FojjiCore, classée par nos poids, exportée vers Naowh
   (`!NBIS1!`) ; BiS de leveling appuyé sur GearQuest Forever ; « est-ce une amélioration ? » dans le chat.
5. EllesmereUI : lien de profil et bascule de rôle retirés par défaut, disponibles sur demande seulement.
6. Refonte de l'interface de ForeverBridge au niveau des meilleurs addons, après étude de Naowh Forever, Forever
   Companion, EllesmereUI et RestedXP (sans recopier leur code).

## Étude de l'existant (décision 264, étendue aux addons installés ; 2026-10-14, lecture locale seule)

Addons lus dans `C:\Program Files (x86)\World of Warcraft\_classic_beta_\Interface\AddOns` (aucun code recopié,
aucune écriture). **Partie web de la décision 264 non faite à ce stade** : proposée en tête des blocs 4 (formats de
poids, échelles publiques) et 6 (bonnes pratiques d'interface des addons), lecture seule.

| Besoin | Ce qui le fait déjà (version relevée) | Verdict |
| --- | --- | --- |
| Zone de départ d'une race, enchaînement de zones 1 à 10 | RestedXP 4.11.23 : parcours gratuits en clair par zone de départ (`Guides/Forever/`) | **Mesurer** (décision 268) : enchaînement de zones comparé, jamais repris ; la source de la zone de départ est ailleurs (question 2) |
| Route pas à pas suivie en jeu | RestedXP (`ImportGuide`, public) ; Shortest Path Forever (suit la cible de RestedXP) | **Alimenter** : notre route livrée dans RestedXP, rien à refaire |
| Retrait d'un guide | RestedXP : `addon.RemoveGuide(guideKey)` (`GuideLoader.lua:208`), **interne** (non exporté dans `_G.RXPGuides`, `GuideLoader.lua:1268-1273`) ; `ImportGuide` met en cache par clé de guide (`GuideLoader.lua:399-402`) | **Se servir** de la clé : nom stable par personnage, même clé, remplacement par `ImportGuide` (à confirmer en jeu, RXP3) ; jamais d'appel interne |
| Plan de talents niveau par niveau | Naowh Training 1.1.15 (« Level by level », `!NFB1!`) ; Talents Forever Book 0.38.2 (`TF.Decode` lit code et lien) | **Alimenter** : plan calculé exporté (déjà fait par EX1 dès le niveau 10) |
| Échelles de statistiques et score dans les infobulles | Forever Companion 1.0.0 (données v88 du 2026-10-12) : import et export **Pawn v1** (`Scales.lua:361-373`, Options, « Import scale… ») ; aucune API publique pour régler une échelle | **Alimenter** par une chaîne Pawn v1 que le joueur colle ; jamais d'écriture de `ForeverCompanionDB` |
| Poids chez Naowh | Naowh Forever 1.1.15 : « Import weights » (`NFSW1:` ou export EP de WoWSims, `StatWeights/Sharing.lua:95`) ; le Naowh Score **ne dépend pas des poids** (niveau d'objet, qualité, niveau requis : `NaowhScore/Data/Formula.lua`) | **Alimenter** (`NFSW1:`, format prêt depuis EX1) ; dire que le Naowh Score reste le leur |
| Listes BiS | Forever Companion (`ForeverCompanionData.bis[classe][spé]`, phase « BETA », sans niveau, source et taux par objet dans `Data/Dictionary.lua`) ; Naowh BiS (une liste par spécialisation, sans niveau, mise à jour le 11 octobre) ; **FojjiCore absent** (retiré entre le 10 et le 14 octobre) | **Se servir** des listes (lecture locale), **construire** la liste personnelle classée, **alimenter** Naowh (`!NBIS1!`) |
| Équipement de leveling par niveau | GearQuest Forever 0.5.5-beta (modules de classe 0.3.6-beta) : `GQ.Data.<classe>Picks` (objet, emplacement, plage de niveaux, rang, spécialisation, camp, score) dans des fichiers Lua générés ; **rien dans ses SavedVariables** ; `/gq` | **Se servir** : lecture locale des fichiers générés, réponse qui renvoie à sa chasse (`/gq`) ; rien recalculé |
| Comparaison d'équipement | Forever Guide 1.35.1 (GearAdvisor, GearCalc, GearExplain ; poids donnés en unités WoWSims) | **Recouper** seulement |
| Thème compatible | EllesmereUI 9.5.4 : API publique d'habillage (`SKINNING_API.md` : `RegisterSkin`, `GetAccentColor`, `GetFont`, `OnLooksChanged` ; `## OptionalDeps`) | **Se servir en lecture** pour habiller **notre** fenêtre ; EllesmereUI lui-même jamais modifié (question 9) |
| Organisation des fenêtres | Naowh (barre latérale, cartes, onglets, recherche, `Shared/UI/Window.lua`, `Panels.lua`) ; Forever Companion (onglets latéraux à icône, `Compat.lua:265-558`) ; EllesmereUI Options (barre latérale, en-tête, onglets, fabrique de contrôles) ; RestedXP (`GuideWindow.lua`, étapes empilées, thèmes) | **Étudier** (bloc 6), rien recopié |

Écarts de version avec nos documents, à corriger au bloc 0 : Naowh Forever 1.1.15 (EX1 : 1.1.12), Forever Guide 1.35.1
(inventaire : 1.25.7), Forever Companion données v88 (inventaire : v79), listes BiS de Naowh du 11 octobre, GearQuest
Forever 0.5.5-beta, FojjiCore absent.

## Constats (dépôt, 2026-10-14 ; chemins `fichier:ligne` pour la relecture)

### Routes (bloc 1)
- **Cause 1 : la position du personnage n'atteint jamais le planificateur.** `RouteRequest` ne porte ni race, ni carte,
  ni coordonnées (`forever/route.py:219-235`) ; l'outil MCP (`forever/mcp_server.py:428-441`), la CLI
  (`forever/cli.py:414-432`) non plus ; le pont n'envoie que classe, camp et niveaux (`forever/bridge/plans.py:243-249`).
  ForeverBridge envoie `race`, `zone`, `subzone` et `map` mais pas de coordonnées (`addon/ForeverBridge/Message.lua:370-374`),
  et `Resolved` ne garde que `zone` (`forever/bridge/context.py:209`).
- **Cause 2 : le départ est la quête de plus petit identifiant.** `start_quest` trie par (permise, écart de niveau,
  niveau minimal, id) (`forever/route.py:618-622`) ; toutes les quêtes de niveau 1 de l'Alliance sont à égalité et
  l'identifiant départage : une quête d'Elwynn Forest passe avant celle de Coldridge Valley. Le trajet initial vaut
  zéro, le départ étant posé sur ce donneur (`forever/route.py:740-746`, `forever/engine/route.py:312`).
- **Le masque de race seul ne suffirait pas** : ces deux quêtes ont le même masque (toute l'Alliance). Il faut la
  position réelle **et** une table race → zone de départ (pour la CLI, les tests et un personnage hors contexte).
- **Aucune table race → zone de départ** : `races.json` n'a pas de carte de départ, `ChrRaces` est lue sans elle
  (`forever/pipeline/tables.py:131-133`) ; question RTE3 ouverte. Dix races jouables dans les données (huit
  classiques et deux Skyborne, une par camp), sept zones de départ attendues.
- **Filtres absents** (`forever/route.py:386-450`) : masque de race (lu de Questie et Completo,
  `forever/quest_sources.py:344-346`, `:465`, jamais appliqué), répétable, effort de guerre, métier requis,
  événement (Foire de Sombrelune), capitale ou autre continent (seul un poids doux, `forever/optimize/route.py:188`).
  `specialFlags` et `requiredSkill` de Questie ne sont pas lus (`forever/quest_sources.py:99-113`).
- **Pourquoi les quêtes « The Alliance Needs… » passent** : connues de Questie seulement, de niveau maximal avec un
  niveau minimal de 1 et sans masque, donc « both » ; jamais grises ; acceptées par `_candidates`
  (`forever/optimize/route.py:134`). Deux artefacts du modèle les rendent attirantes : un rendu d'objets compté comme
  des combats au niveau de la quête (`forever/route.py:339-343`, `:428`) et l'XP de Questie (`suppose`) appliquée
  sans contrôle d'accessibilité. Les quêtes trop hautes ne sont écartées que dans `best_zone_xp_h`
  (`forever/engine/route.py:487`), pas dans la construction.
- **Farm** : seulement en fin de route, quand plus aucune quête ne vaut le détour (`forever/optimize/route.py:99-110`,
  `:192-193` ; `forever/engine/route.py:451-455`) ; rien ne vérifie qu'il ne reste pas de quête faisable dans la zone.
- **Recette** : `rxp_guides.coverage` donne déjà la chaîne des parcours gratuits par `#defaultfor`
  (`forever/rxp_guides.py:287`, `:307-345`), et `compare_rxp` part déjà du donneur de la première quête du parcours
  (`forever/compare.py:383-395`). Relevé local : Coldridge Valley → Dun Morogh pour les Nains et les Gnomes, Northshire
  → Elwynn Forest pour les Humains, Shadowglen → Teldrassil, Durotar, Tirisfal Glades, Mulgore, Zephras Isle
  (Skyborne, les deux camps) ; variantes du Mage (« AoE », « ADV »).

### Conversation et livraison (bloc 2)
- Les trois questions de `ROUTE_CHOICES` (`forever/bridge/choices.py:34-53`) partent **ensemble** en cartes de
  « À valider » (`forever/bridge/loop.py:201-203`), sans empreinte ni « Masquer ».
- **Deux sources de vérité pour « À valider »** : le compteur compte toutes les cartes visibles, questions comprises
  (`addon/ForeverBridge/ForeverBridge.lua:1025-1035`, `:1214-1215`) ; le modèle ne voit jamais les cartes publiées (seule
  la consigne de route les mentionne, `forever/bridge/plans.py:256-260` ; `forever_status` ne liste que les attentes de
  `forever update`, `forever/update.py:2685-2690`) et peut répondre « aucune question n'attend de validation ».
- L'historique est un `ScrollingMessageFrame` (`ForeverBridge.lua:272-294`) : pas de boutons enfants, seulement des
  liens `|H…|h` (aujourd'hui `foreverbridge:copy:N`).
- Le modèle ne peut pas émettre de question : `AgentResult` n'a pas de champ pour cela (`forever/bridge/agent.py:58-76`).
- **Aperçus** : un fichier par demande (`<cache>/routes/<id>.json`, `forever/route.py:793-853`), rien n'est lié à la
  conversation ni au personnage ; deux aperçus coexistent.
- **Livraison** : `_deliver_route` prend le plan le plus récent de même classe et même camp, pas du personnage
  (`forever/bridge/loop.py:467-489`) ; nom `Forever <Classe> a-b (<id6>)` (`forever/route.py:856-859`), donc un nouveau
  guide par plan, jamais de remplacement (`ForeverBridge.lua:1537-1552`).

### Talents (bloc 3)
- Au niveau 1, le bouton demande le point du niveau suivant (`forever/bridge/plans.py:51-57`) ; `forever_build` refuse
  sous le premier niveau de talent (`forever/build.py:278-284`) et le modèle paraphrase le refus. À partir du niveau 10,
  `forever_build` rend déjà l'ordre de prise, le lien Talents Forever et le code `!NFB1!`
  (`forever/talents_forever.py:575-603`) ; les builds populaires portent un ordre généré (`talents_forever.py:763-766`).

### EllesmereUI (bloc 5)
- Aucun réglage pour l'éteindre : lien `[EllesmereUI : rôle]` dans la réponse Exports (`forever/bridge/exports.py:126-151`,
  incitation même sans rôle `:129`), bascule `FB.SwitchProfile` à `/fb role`, à la connexion et en sortie de combat
  (`ForeverBridge.lua:2075-2152`, `:2311-2323`), ligne d'aide (`:2373`), aucune commande pour effacer un rôle.

### Fenêtre (bloc 6)
- ForeverBridge 0.4.0, fenêtre 520×360 redimensionnable ; « Nouvelle conversation » puis jusqu'à huit boutons de
  100 px enchaînés sans retour à la ligne (`ForeverBridge.lua:357-364`, `:492-503` ; `forever/bridge/buttons.py:46-90`) :
  la barre déborde et les libellés longs se chevauchent. Réponses en texte brut, trois mises en forme seulement
  (`ForeverBridge.lua:608-639`). Aide affichée une fois (`:2363-2417`). Banc lupa : `tests/unit/test_bridge_*_lua.py` et
  `tests/fixtures/bridge/wow_stub.lua`.

## À valider (dix questions ; défaut proposé en premier)

1. **Code, branches et acceptation.** *Défaut* : tranche **CJ1** ; une branche par bloc (`cj1-0`, `cj1-1`…) partie de
   `origin/main`, fusionnée en fast-forward dès la CI verte pour que le pont relancé sur `main` serve l'essai en jeu ;
   un bloc fusionné est « livré, en attente d'essai » (ROADMAP), puis « accepté » à ton accord ; un refus ouvre une
   branche de corrections ; la tranche se ferme quand les blocs sont tous acceptés. *Autre* : essai en jeu sur la
   branche (le pont lancé depuis le dépôt sur la branche) et fusion seulement après ton accord.
2. **Source de la table race → zone de départ** (`start_zones.json` dans les données de la version, origine déclarée
   dans `origins.json`). *Défaut* : zone vue en jeu par le pont à la création d'un personnage (carte du contexte au
   niveau 1, `certain`) d'abord ; à défaut, zone des quêtes de niveau 1 réservées à la race chez Questie et dans le
   client, recoupée avec Wowhead (`probable`) ; jamais écrite de mémoire. *Autre* : tu me donnes les sept zones.
3. **Recette de référence.** *Défaut* : commande locale `forever route recette` (forme au bloc) qui calcule la route 1
   à 10 de chaque race et compare son enchaînement de zones (zones dans l'ordre, doublons fusionnés) à celui du
   parcours gratuit de RestedXP de la même race (variante Mage comprise pour un Mage) ; écart = route **refusée** :
   pas d'aperçu proposé à la livraison, écart expliqué en une phrase (zone en trop, manquante ou dans le désordre) ;
   la même vérification tourne avant chaque livraison d'une route qui commence sous le niveau 10 ; sans RestedXP
   installé, garde-fous seuls, et la réponse le dit. Résultats consignés dans `docs/research/rxp-comparaison.md`.
   Tests sur guides fabriqués (décision 268). *Autre* : refus signalé mais livraison possible sur ta demande.
4. **Quêtes écartées par défaut** : d'une autre race ou d'un autre camp, d'effort de guerre, répétables, d'événement,
   de métier (sauf métier du personnage et route de métier demandée), trop hautes pour être faites au niveau du
   personnage, dans une capitale ou sur un autre continent sous le niveau 10 (sauf zone de départ de la race sur cet
   autre continent ou trajet de classe obligatoire). *Défaut* : catégories lues dans `specialFlags` et `requiredSkill`
   de Questie et dans les tables du client déjà téléchargées ; si une catégorie exige une table du client absente
   (`QuestInfo`, `QuestSort`), téléchargement par la voie existante de `forever fetch` (accès réseau : ton accord ici) ;
   une catégorie introuvable dans aucune source est marquée `suppose` et la question va dans `docs/OPEN_QUESTIONS.md`.
   L'XP des quêtes n'est pas touchée (règle de jeu incertaine). *Autre* : liste d'identifiants écartés à la main (non
   recommandé, ne suit pas les versions).
5. **Questions dans le chat.** *Défaut* : la question en cours s'affiche sous le dernier message, avec une rangée de
   vrais boutons de réponse ancrée sous l'historique (au plus quatre, plus « Autre » qui rend la main à la saisie) ;
   une seule question à la fois, posée par le pont dans l'ordre (niveaux, donjons, quêtes de classe), sautée quand la
   demande y répond déjà ; le modèle peut aussi poser une question par un bloc structuré de sa réponse, relu et borné
   par le pont ; plus aucune question dans « À valider », qui ne garde que mises à jour et profil. *Autre* : liens
   cliquables dans le texte du message (moins lisibles, mais sans nouveau cadre).
6. **Aperçu et livraison.** *Défaut* : une seule route « en cours » par personnage (dans l'état du pont, liée au
   personnage du contexte) ; chaque ajustement la remplace, l'aperçu précédent est marqué « remplacé » dans
   l'historique ; sous l'aperçu, « Valider et livrer » et « Ajuster » ; la validation livre d'office dans RestedXP sous
   le nom stable « Forever · <Personnage> · <a>-<b> » (groupe « Forever Routes ») qui remplace le guide précédent du
   même personnage par la même clé ; la réponse dit où le trouver dans RestedXP. Le bouton « Livrer dans RestedXP » est
   retiré. *Autre* : garder un bouton de livraison séparé.
7. **BiS (bloc 4)** : FojjiCore n'est plus installé. *Défaut* : liste personnelle bâtie depuis Forever Companion et
   Naowh (FojjiCore relu s'il revient, sans rien bloquer) ; classée par nos poids calculés pour le Mage, et pour les
   autres classes par l'échelle de Forever Companion de la spécialisation (`suppose`, « poids de la communauté ») ;
   exportée en `!NBIS1!` pour toutes les classes (amende la décision 250, qui ne réexportait pas les listes des
   autres classes) ; BiS de leveling lu dans GearQuest Forever. Tables d'objets du client (`Item`, `ItemSparse`
   complète, `ItemEffect`…) téléchargées par la voie existante (accès réseau : ton accord) ; si les objets de Forever
   portent des notations (toucher, critique, hâte), la conversion des notations (PER8) est avancée de SIM1 dans ce
   bloc. *Autre* : Mage seulement pour l'export, listes des addons laissées dans leur addon pour les autres classes.
8. **EllesmereUI.** *Défaut* : lien de profil et bascule retirés par défaut ; `/fb eui on` les rallume (réglage du
   compte dans `ForeverBridgeDB`), `/fb eui off` les éteint, `/fb role clear` efface un rôle ; les rôles déjà gardés
   restent sans effet tant que le réglage est éteint. *Autre* : retirer tout le code de bascule.
9. **Thème de la nouvelle fenêtre.** *Défaut* : si EllesmereUI est chargé, notre fenêtre s'habille par son API
   publique d'habillage (`## OptionalDeps: EllesmereUI`, couleur d'accent et police lues, aucune écriture dans
   EllesmereUI ni ses réglages) ; sinon thème sobre propre (fond sombre, une couleur d'accent, police du jeu). Les
   maquettes (texte et schémas) te sont montrées le 27 octobre avant tout code. *Autre* : thème propre toujours,
   sans lien avec EllesmereUI.
10. **Règles de méthode.** *Défaut* : trois décisions (272 à 274) et trois lignes dans la section « Façon de
    travailler » de `CLAUDE.md` ; la règle d'acceptation en jeu amende la décision 247 (les essais en jeu ne sont
    plus facultatifs pour clore un bloc qui touche au jeu ; ils restent courts) ; entre la fin de la bêta et la sortie,
    l'essai attend le 4 novembre et s'inscrit dans `docs/LANCEMENT.md`. *Autre* : décisions seulement, `CLAUDE.md`
    inchangé.

## Conception

### Bloc 1 — Routes
- **Requête** : `RouteRequest` gagne `race` et `start` (carte `uiMapID`, x, y, facultatifs) ; MCP `forever_route`, CLI
  `forever route plan --race --from-map --at x,y` (forme au bloc) ; le pont les remplit depuis le contexte
  (`Resolved` garde `map`, ForeverBridge envoie x et y hors combat par `C_Map.GetPlayerMapPosition` sous `pcall`).
- **Départ** (`start_position`, fonction pure) : position du contexte si présente ; sinon, au niveau 1, zone de départ
  de la race (table de la question 2) et premier donneur de cette zone ; sinon la règle de RX1c. Le trajet jusqu'au
  premier arrêt est compté. `start_quest` ne départage plus par l'identifiant : à égalité, le plus proche du départ.
- **Garde-fous** (`forever/route_guards.py` ou dans `route_world`, au bloc) : filtres de la question 4 avant la
  recherche ; contrôles **après** la recherche, qui refusent une route invraisemblable avec la raison : première zone
  ≠ zone de départ au niveau 1, quête d'une autre race ou d'un autre camp, capitale ou autre continent sous le niveau
  10 sans raison, farm alors qu'une quête faisable reste dans la zone ou une zone voisine prévue pour le camp.
- **Modèle** (registre I18) : un objectif « rapporter des objets » n'est plus compté comme des combats au niveau de la
  quête ; une quête trop haute pour ses objectifs n'est pas candidate (seuil lu dans les données, origine déclarée,
  `suppose` si aucune source).
- **Recette** (question 3) : `forever route recette` et contrôle avant livraison, sur `rxp_guides.coverage` et la
  chaîne de zones de `compare.breakdown` ; mesure seulement (décision 268).
- **Vols et foyer (bloc 7, facultatif)** : repris de RX2 seulement s'il reste du temps après l'acceptation des blocs 1
  à 3 ; sinon RX2 inchangée après la sortie.

### Bloc 2 — Conversation et livraison
- **Questions** (question 5) : `Choice` devient séquentiel (`next_choice`), une question par réponse du pont, avec un
  champ `choices` dans la réponse (`forever/bridge/loop.py:381-384`, `:650-668`) ; ForeverBridge dessine la rangée de
  boutons sous l'historique et envoie `a=choice:…` (action existante, `forever/bridge/actions.py:19-21`) ; bloc
  structuré du modèle relu par le pont (au plus quatre réponses, libellés courts, sinon ignoré et journalisé) ; les
  cartes de choix ne sont plus publiées (`loop.py:203`).
- **Compteur cohérent** : un seul calcul des cartes visibles, partagé par le bouton et la ligne d'état ; le pont donne
  au modèle, dans la consigne de chaque message, le nombre et le titre des cartes « À valider » réellement publiées ;
  test : jamais « aucune question » quand une carte est visible.
- **Route en cours par personnage** (question 6) ; `_deliver_route` prend la route du personnage, pas la plus récente
  de la classe ; nom stable ; remplacement par la clé de RestedXP (lecture de `BuildGuideKey` et `CacheGuide` au bloc
  pour confirmer, sinon repli : nom stable et question RXP3) ; message « Ta route “Forever · Bob · 1-10” est dans
  RestedXP : menu des guides, groupe Forever Routes » (libellés exacts relus dans RestedXP en anglais, client enUS).
- **Relecture humaine** : la première route de chaque zone de départ est montrée en texte (zones et quêtes dans
  l'ordre) dans l'aperçu avant d'être livrée.

### Bloc 3 — Talents dès le niveau 1
- Le bouton Talents demande le plan jusqu'à l'objectif (niveau visé du profil, sinon niveau maximal des données) quel
  que soit le niveau ; sous le premier niveau de talent, la réponse dit « ton premier point arrive au niveau N » (lu
  dans les données) et donne le plan complet, le lien Talents Forever et le code `!NFB1!` à coller dans Naowh Training
  (Builds, Import), à suivre « Level by level ». Mage calculé ; autres classes : build populaire ou de la communauté
  le plus proche, ordre généré signalé comme tel (EX1).

### Bloc 4 — BiS et équipement (T10a revue selon l'audit)
- **Poids** du Mage par le moteur (`forever/engine/`, fonctions pures) par niveau et par contexte (leveling, donjon),
  rendus en `NFSW1:` (Naowh, « Import weights ») et en Pawn v1 (Forever Companion, « Import scale… »), nommés
  « Forever · <Personnage> · <contexte> ».
- **Liste personnelle** : listes de Forever Companion et de Naowh lues en local à chaque demande (cache, jamais dans le
  dépôt), fusionnées par emplacement, classées par nos poids (ou l'échelle de Forever Companion, question 7), lieu de
  butin (DJ1, dictionnaire de Forever Companion), exportées en `!NBIS1!` (format prêt depuis EX1).
- **Leveling** : choix de GearQuest Forever lus dans ses fichiers générés pour la classe et la plage de niveaux,
  « prochain objet à viser » avec renvoi à `/gq` ; aucun classement recalculé.
- **« Est-ce une amélioration ? »** dans le chat (objet par Maj+clic, P06b) : score par nos poids (Mage) et par
  l'échelle active de Forever Companion lue dans ses données (`suppose`), Naowh Score cité comme le leur ; source et
  certitude affichées ; « non calculé » sans poids.
- Commande et outil MCP `forever gear` (forme au bloc), provenance complète.

### Bloc 5 — EllesmereUI éteint par défaut (question 8)
- `exports.py` ne propose plus le profil ni le rôle sauf réglage allumé ; `FB.SwitchProfile` jamais appelé réglage
  éteint ; aide mise à jour ; `/fb eui on|off`, `/fb role clear`.

### Bloc 6 — Refonte de l'interface de ForeverBridge
- **Étude** (lecture locale, puis web en lecture seule) : navigation, cartes, typographie, aides des quatre addons ;
  notes dans `docs/research/interface-addons.md` (organisation et principes, aucun code).
- **Maquettes** montrées le 27 octobre (question 9), puis code :
  - navigation à gauche ou en onglets : Chat, Feuille de route, Talents, Équipement, Exports, Mises à jour ;
  - barre d'actions hiérarchisée : trois actions principales visibles, le reste dans un menu « Plus » ; largeurs
    mesurées sur le texte, retour à la ligne ou menu, jamais de chevauchement (test lupa sur toutes les largeurs
    permises de la fenêtre) ;
  - assistant de feuille de route : niveaux de départ et d'arrivée (curseurs ou listes), cases à cocher (donjons,
    quêtes de classe, métiers, réputations), « Calculer », aperçu en carte, « Valider et livrer » ;
  - historique en cartes (titre, icône de certitude, listes courtes, liens), remplaçant le `ScrollingMessageFrame`
    par une liste défilante de cartes ; la rangée de réponses du bloc 2 y devient des boutons dans la carte ;
  - compteur « À valider » du bloc 2 ; aide d'accueil courte au premier lancement ; thème de la question 9.
- Aucune fonction protégée, rien en combat (`test_addon_rules.py`) ; `check_addon.py` vert.

## Blocs et calendrier (fin de la bêta annoncée le 21 octobre, sortie le 4 novembre)

| Dates | Bloc | Essai en jeu |
| --- | --- | --- |
| jeu. 15 oct. (matin) | **0** — Intégration des deux fichiers, décisions 272 à 276, ROADMAP, DATA_SOURCES, inventaire, `CLAUDE.md`, archivage | — |
| 15 → 17 oct. | **1** — Routes : départ et race (1a), garde-fous et filtres (1b), recette (1c) | sam. 17 et dim. 18 |
| 18 → 19 oct. | **2** — Conversation, aperçu unique, livraison d'office | 19 et 20 |
| mar. 20 oct. | **3** — Talents dès le niveau 1 ; **5** — EllesmereUI éteint (petit, avancé pour profiter de la bêta) | 20 et 21 |
| mer. 21 oct. au soir | Fin de la bêta : corrections des essais 1 à 3 et 5 avant la fermeture si possible | dernier jour |
| 22 → 23 oct. | Corrections restantes ; **7** — vols et foyer si les blocs 1 à 3 sont acceptés | au 4 nov. |
| 22 → 27 oct. | **4** — BiS et équipement | au 4 nov. |
| mar. 27 oct. | **6** — Étude et maquettes montrées pour accord | — |
| 28 oct. → 2 nov. | **6** — Code de la nouvelle fenêtre | au 4 nov. |
| mar. 3 nov. | Marge ; `docs/LANCEMENT.md` (essais restés en attente) | — |
| mer. 4 nov. | Sortie : essais des blocs 4, 6, 7 et de ce qui reste ; clôture de CJ1 à ton accord | 4 nov. et suivants |

Ce qui glisse : SIM1 et la suite de RX2 (quêtes lancées par un objet, comparaisons refaites) après le 4 novembre ;
CM1 dès la sortie, comme prévu (décision 261). Si un bloc de 1 à 3 n'est pas accepté le 21 au soir, ses corrections
passent devant les blocs 4 et 6.

### Bloc 0 — Intégration (après validation, avant tout code)
- `docs/DECISIONS.md` : 272 (addons d'abord, prolonge 264 et 133), 273 (acceptation en jeu, amende 247), 274
  (EllesmereUI intouché sans demande, amende 267 et 269), 275 (CJ1, ordre et calendrier jusqu'au 4 novembre, amende
  251, 267 et 270 ; SIM1 et la suite de RX2 après la sortie ; T10a revue dans CJ1), 276 (conséquences de l'audit :
  T10a revue, BiS de leveling par GearQuest Forever, MT1 sur SkillUp Forever et Forever Companion, la fenêtre du chat
  renvoie à l'affichage de chaque addon ; questions dans le chat, amende 258 et 266) ; réponses aux questions de ce
  plan reportées dans 275.
- `docs/ROADMAP.md` : ligne et section CJ1 en tête du calendrier ; T10a réécrite (renvoi à CJ1, bloc 4) ; RX2, SIM1,
  MT1 (s'appuyer sur SkillUp Forever) et l'idée « fenêtre du chat » mises à jour.
- `docs/DATA_SOURCES.md` : Forever Companion (BiS, échelles Pawn v1, rotations, onglet « BiS Talents »), GearQuest
  Forever (BiS de leveling), Naowh BiS et Stat Weights, FojjiCore absent ; section « Addons pilotés » complétée
  (Pawn v1 vers Forever Companion).
- `tasks/inventaire-addons.md` : relevé du 2026-10-14 (versions, capacités de la carte de l'audit, écarts).
- `docs/OPEN_QUESTIONS.md` : questions de la section plus bas.
- Archivage : `git mv` des deux fichiers de base vers `tasks/archive/`.

## Procédures d'essai en jeu (courtes ; écrites dans `docs/ADDON.md`, celles d'après le 21 dans `docs/LANCEMENT.md`)
- **CJ-1** (routes) : un Gnome neuf à Coldridge Valley et un personnage Horde neuf (Orc ou Troll à Valley of Trials) ;
  « Feuille de route » 1 à 10 ; attendu : la route part de la vallée de départ, puis la zone voisine de la race, sans
  capitale, sans quête d'une autre race ni d'effort de guerre ; enchaînement de zones conforme au parcours gratuit de
  RestedXP, ou refus expliqué. Les autres races : couvertes par les tests.
- **CJ-2** (conversation) : la question arrive dans le chat, une à la fois, avec ses boutons ; « À valider » ne la
  montre pas et son compteur dit la même chose que la réponse ; un ajustement remplace l'aperçu ; « Valider et
  livrer » met « Forever · <Personnage> · 1-10 » dans RestedXP ; une deuxième route du même personnage remplace la
  première (après `/reload` aussi).
- **CJ-3** (talents) : au niveau 1, le bouton Talents donne le plan complet, le lien Talents Forever et le code
  Naowh ; le code s'importe dans Naowh Training et s'affiche « Level by level ».
- **CJ-5** (EllesmereUI) : aucune proposition de profil ni bascule après connexion, combat et `/reload` ; `/fb eui on`
  les rallume.
- **CJ-4** (au 4 novembre) : poids importés dans Forever Companion et Naowh ; liste `!NBIS1!` visible dans la fenêtre
  BiS de Naowh ; « est-ce une amélioration ? » sur un objet par Maj+clic.
- **CJ-6** (au 4 novembre) : nouvelle fenêtre aux tailles minimale et maximale, aucun chevauchement, assistant de
  feuille de route de bout en bout, accueil, avec et sans EllesmereUI.

## Tests attendus (aucun chiffre de jeu dans un test : valeurs de `tests/fixtures/` ou de `forever/data/`)
- **Bloc 1** (`tests/unit/test_route_start.py` étendu, `test_route_guards.py`, `test_route_recette.py`) : départ par
  race pour les dix races (sept zones, deux camps pour Zephras Isle) sur un monde fabriqué ; position du contexte
  prioritaire ; trajet initial compté ; départage par distance, plus par identifiant ; chaque catégorie de quête de la
  question 4 écartée ; route refusée avec sa raison pour chaque garde-fou ; rendu d'objets non compté comme combat ;
  recette sur guides fabriqués : même enchaînement accepté, zone en trop, manquante ou dans le désordre refusée avec
  l'écart ; sortie sans texte de guide (décision 268) ; contexte du pont avec `map`, x et y jusqu'à la requête.
- **Bloc 2** (`test_bridge_choices*.py`, `test_bridge_route_session.py`, lupa) : une question à la fois, dans l'ordre,
  sautée quand la demande y répond ; boutons sous l'historique et `a=choice:` ; aucune carte de choix publiée ;
  compteur et ligne d'état égaux ; consigne au modèle avec les cartes réelles ; route en cours par personnage
  remplacée à l'ajustement ; livraison à la validation, nom stable, même clé, un seul guide par personnage ; bloc
  structuré du modèle borné.
- **Bloc 3** : bouton Talents au niveau 1, 9 et 10 pour le Mage et une autre classe ; plan, lien et code présents.
- **Bloc 4** (`test_gear_*.py`) : poids déterministes avec provenance ; va-et-vient `NFSW1:`, Pawn v1 et `!NBIS1!` ;
  fusion et classement sur fixtures fabriquées d'addons (structure seulement) ; rien des listes dans le dépôt ;
  amélioration avec source et certitude, « non calculé » sans poids.
- **Bloc 5** (lupa) : réglage éteint par défaut, aucune bascule à la connexion, en sortie de combat ni à `/fb role` ;
  `on`, `off`, `clear`.
- **Bloc 6** (lupa, stub étendu aux nouveaux contrôles) : aucun bouton hors de la barre ni chevauchement aux tailles
  extrêmes ; navigation ; assistant qui produit la même requête que la conversation ; cartes ; accueil au premier
  lancement seulement ; habillage EllesmereUI sur bouchon de son API, thème propre sans lui ; `test_addon_rules.py`.

## Registre (`docs/MECHANICS_REGISTRY.yaml`)
I18 (route : départ, filtres, objectifs d'objets, garde-fous, recette), I19 (trajets, si le bloc 7 est fait) ; entrée
nouvelle pour l'accessibilité d'une quête trop haute (statut `suppose` sans source) ; poids des statistiques du Mage
(bloc 4, nouvelle entrée ; A4, A5, A7, A8, B2 si PER8 est avancée). Comptes de `test_registry.py` écrits au commit
« tests » du bloc concerné.

## Questions ouvertes (à ajouter à `docs/OPEN_QUESTIONS.md`)
- **RTE3** (précisée) : zone de départ de chaque race, vue en jeu par le pont.
- **RTE6** : les quêtes d'effort de guerre de Forever sont-elles faisables et rémunérées à bas niveau ? Ne pas
  trancher sans relevé ; écartées des routes d'ici là.
- **RXP3** : `ImportGuide` avec la même clé remplace-t-il le guide précédent, y compris après `/reload` ?
- **FC1** : une échelle Pawn v1 produite par forever s'importe-t-elle dans Forever Companion, et devient-elle active ?
- **NBIS2** : la liste personnelle `!NBIS1!` s'affiche-t-elle dans la fenêtre BiS de Naowh avec ses lieux de butin ?
- **GQ1** : les fichiers générés de GearQuest Forever restent-ils stables d'une version à l'autre (modules de classe en
  retard sur le cœur) ?

## Hors périmètre
Vols et foyer au-delà du bloc 7 ; quêtes lancées par un objet (RX2) ; SIM1 ; poids et BiS calculés des autres classes
(leurs tranches) ; écriture dans les SavedVariables d'un addon tiers (Forever Companion, Naowh, RestedXP, GearQuest,
EllesmereUI) ; appel d'une fonction interne d'un addon tiers ; recopie de leur code ou de leurs données dans le dépôt ;
reprise d'étapes de RestedXP.

## Risques
- **Fenêtre de jeu courte** : sept jours de bêta pour les blocs 1, 2, 3 et 5 ; si un essai échoue tard, la correction
  ne sera essayée qu'au 4 novembre. Mitigation : routes d'abord, fusion dès la CI verte (question 1).
- **Recette trop stricte** : un parcours de RestedXP peut passer par une zone que nos données ne couvrent pas (quêtes
  sans donneur, RTE4) ; la comparaison porte sur les zones, pas sur les quêtes, et l'écart est expliqué plutôt que
  forcé.
- **Remplacement dans RestedXP** non garanti sans fonction publique de retrait : repli sur le nom stable et RXP3.
- **Formats tiers mouvants** (Naowh plusieurs versions par semaine, GearQuest en bêta) : version relevée dans la
  provenance, changement signalé par `forever addons status`.
- **Refonte de la fenêtre** sans jeu pour l'essayer avant le 4 novembre : maquettes validées d'abord, banc lupa étendu,
  ancienne fenêtre gardée derrière un réglage jusqu'à l'acceptation.

## Angles morts (prévus)
- Vols et pierre de foyer absents si le bloc 7 n'est pas fait : routes plus lentes en temps réel que leur estimation
  dès que RestedXP prend un vol (effet : sous-estimation du temps, surtout au-delà de la zone de départ).
- Monstres tués en chemin (RTE5) et quêtes lancées par un objet (RTE4) absents : XP par heure sous-estimée pour la
  première, quêtes manquantes pour la seconde.
- Poids des autres classes repris de Forever Companion (`suppose`) : classement BiS non calculé hors Mage.

## Étapes d'exécution
1. Validation du plan et réponses aux dix questions ; bloc 0 committé sur `main` (`CJ1: intégration…`).
2. Pour chaque bloc : `git fetch`, branche depuis `origin/main`, tests d'abord (`CJ1: tests (bloc N)`), puis
   `CJ1: bloc N vert` ; `uv run tasks.py quick` pendant le travail ; `uv run ruff check . --no-cache` et
   `uv run tasks.py verify` une fois avant de pousser ; CI verte sous Ubuntu et Windows ; fusion en fast-forward
   (revérifier `origin/main` juste avant, la veille y pousse) ; plugin et skills touchés mis à jour
   (`forever-routes`, `forever-builds`) ; ForeverBridge réinstallé ; pont arrêté puis relancé ; procédure d'essai
   donnée en une dizaine de lignes ; arrêt pour ton essai.
3. Fin de tranche : `/verifier`, résumé (Bloqué sur moi, Fait, Tests ajoutés, Registre modifié, Questions ouvertes,
   Angles morts), clôture à ton accord.

## Critères de fin
Blocs 0 à 6 (et 7 s'il est fait) fusionnés et **acceptés en jeu par l'utilisateur** ; route 1 à 10 de chaque race
conforme aux garde-fous et à la recette, ou refusée avec l'écart ; questions dans le chat, compteur cohérent, aperçu
unique, livraison d'office et remplacement ; plan de talents dès le niveau 1 ; poids et liste BiS exportés vers
Forever Companion et Naowh ; EllesmereUI éteint par défaut ; nouvelle fenêtre sans débordement ; registre à jour ;
`test_addon_rules.py` et `check_addon.py` verts ; `uv run tasks.py verify` vert.
