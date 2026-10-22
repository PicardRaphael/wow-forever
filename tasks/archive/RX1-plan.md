# RX1 — Feuilles de route RestedXP : plan

> Plan rédigé le 2026-10-14 (`/tranche RX1`), sans code. Exécution : `/tranche RX1` dans une nouvelle session, sur la
> branche `rx1`, un cycle rouge → vert par bloc. **Calendrier** (décision 251) : LN1 commence **au plus tard le
> 2026-10-24** ; RX1 est découpée pour qu'une **première version utile (blocs A à E) soit finie le 2026-10-20**, la
> veille de la fin de la bêta, pour que la livraison en jeu (RXP1) puisse s'essayer en jouant ; les blocs F à H se font
> jusqu'au 2026-10-23 au plus tard, puis RX1 est mise en pause (reprise après LN1, à partir du bloc non commencé).
> **Aucune sonde en jeu exigée** (décision 247).

## Demande de l'utilisateur (2026-10-14)
1. Étude de l'existant d'abord (décision 264), puis intégrer `tasks/idees-du-chat-2026-10-13-factoruide.md` :
   Factoruide lu en lecture seule et comparé selon trois options (moteur, reprise des algorithmes, contribution),
   avec une recommandation et ses risques.
2. Mesurer la couverture de Forever par Factoruide et par VMaNGOS face à la liste fusionnée de T04d (556 nouvelles,
   183 retouchées) et au livre des donjons de DJ1 ; combler par nos données ce qui manque ou est périmé avant tout
   calcul de route ; VMaNGOS seulement pour ce que Forever ne change pas, « base Classic », `suppose`.
3. Le reste de RX1 selon la ROADMAP : questions à boutons, aperçu ajustable, classe et métiers, donjons à leur
   placement de DJ1, bonus de T04f, XP réelle de T04d, livraison par `ImportGuide` avec repli, bouton « Feuille de
   route ». Interdits inchangés.
4. Première version utile avant le 24 octobre, quitte à mettre le reste en pause.

## Réponses de l'utilisateur (2026-10-14)
1. **Réseau de l'étude** : lecture web et **clone superficiel en cache** (hors dépôt), rien compilé ni exécuté. Fait :
   Factoruide cloné dans `~/.cache/forever/third_party/factoruide` (commit `f7da6da`, 2026-10-14 01:51), bases
   `data/*.sqlite.zst` décompressées dans `third_party/factoruide-db/` par la `libzstd.dll` de Git for Windows (aucun
   code de Factoruide lancé) ; trois fichiers de QuestieDB (`a4cad87`) lus par `gh api` dans
   `third_party/questiedb/` ; la documentation officielle des guides personnels RestedXP répond 403 (non lue : la
   syntaxe vient du code local de RXPGuides, comme prévu par la ROADMAP).
2. **Factoruide** : **option 2** (porter en Python un sous-ensemble de ses algorithmes, MIT, cité), avec une
   contribution légère (option 3 : une issue pour nos écarts d'XP) après la première version.
3. **Trajets** : **les deux** : tables du client (`TaxiNodes`, `TaxiPath`, `TaxiPathNode`, `UiMapAssignment`) par la
   voie existante de `forever fetch` et `forever update`, épinglées, pour les vols et les coordonnées (le client
   prime) ; et, lus en local, Shortest Path Forever (`Taxi.lua`, `Walks.lua`, bateaux, zeppelins, portails) et le
   réseau de marche de Naowh Journeys pour la marche et les passages entre zones ; écarts signalés, rien recopié dans
   le dépôt (décision 133).
4. **Repli de livraison** : un seul dossier `Interface/AddOns/ForeverRoute/`, écrit jeu fermé seulement, sauvegarde
   avant, réécrit en entier à chaque livraison, jamais ailleurs.
5. **Base de Factoruide** : recoupement local, clone épinglé à `f7da6da`, jamais recopiée ni livrée dans un guide.
   **Les quêtes que Factoruide connaît et pas nous sont un défaut grave** : trouver pourquoi la liste fusionnée de
   T04d les manque (lecteur incomplet, comme `read_fdj` qui ne voyait que 3 donjons sur 14) et corriger nos lecteurs,
   pour qu'elles viennent de nos propres sources ; une quête qu'aucune de nos sources ni le client ne connaît reste
   signalée « vue seulement chez Factoruide », `suppose`, et n'entre dans aucune route.

## Étude de l'existant (décision 264 ; 2026-10-14, lecture seule)

| Trouvaille | Licence | Fraîcheur | Réutilisable pour RX1 | Verdict |
| --- | --- | --- | --- | --- |
| **Factoruide** (brouznouf, `crates/fg-route`) | MIT (code) ; GPL-2.0+ (`data/`, VMaNGOS) ; données Questie sans licence, Wowhead | 0.8.0, 2026-10-14 (8 versions en 5 jours) | planificateur complet (simulation, construction gloutonne et par régions, amélioration locale, ALNS, tournoi), binaire `fg route` en ligne de commande, guide JSON typé | **porter un sous-ensemble** (option 2) ; base en recoupement local |
| RXPGuides 4.11.23 (installé) | CC BY-NC-SA 4.0 | 2026-10 | `RXPGuides.ImportGuide` / `RegisterGuide` (`GuideLoader.lua:393`, `:416`, branchés `:1268-1273`), `ParseGuide` (`:973-1192`), ~150 commandes d'étape (`functions.lua`) | **cible de livraison** ; code lu pour la syntaxe seulement ; guides livrés jamais lus ni repris |
| Shortest Path Forever 1.14.1 (installé) | GPL-3.0+ | wago 1.60.1.70291 + CMaNGOS | API `ShortestPathForever.API.Estimate/EstimateDetail/NavigateRoute` (`Core/API.lua:264-408`), `Data/Taxi.lua`, `Walks.lua`, `Transports.lua`, `Portals.lua` ; suit la flèche de RestedXP (`Core/RestedXP.lua:140-155`) | **lu en local** (trajets, transports) ; en jeu, il guide déjà vers l'étape RestedXP |
| Naowh Journeys 1.1.12 (installé) | tous droits réservés | 2026-10 | réseau de marche (`graph`, `walks` en CBOR compressé, `Walk.lua:30-33`), `QuestSpots.lua` (2857 quêtes : rendu et camps d'objectifs) | **lu en local** (passages, camps) |
| Questie 11.38.0 Forever-v27 (installé) | sans licence | 2026-10 | positions des PNJ et objets (`spawns`, `classicNpcDB.lua:7-15`, `classicObjectDB.lua:10`), butin wowhead | **base Classic des positions** (`suppose`) : remplace VMaNGOS |
| QuestieDB (`a4cad87`, 2026-10-12) et Questie 12.1.0 (publié le 2026-10-12) | sans licence | 2026-10-12 | `data/Forever/foreverQuestDB.lua` : 4244 quêtes, aucune d'identifiant ≥ 90000 (même compte que notre Questie installé) | rien de plus que l'installé pour les quêtes nouvelles ; mise à jour de l'addon signalée au joueur |
| VMaNGOS (via Factoruide : `import_run` « 4433 quests, 104047 spawns, 234353 loot sources ») | GPL-2.0 | Classic 1.12 | positions et butin Classic | **écarté** : Questie installé donne déjà les positions ; aucun téléchargement |
| AllTheThings (source de Factoruide pour 2250 quêtes Forever) | MIT | 2026-10-13 | quêtes de Forever | **candidat** si un manque persiste (non installé, décision 131) |
| TUGs Leveling Guide (Guidelime) ; Guidelime 6.003 | divers | 2026-10-03 | guides écrits à la main | écarter (guides tiers, pas un format de livraison) |
| SkillUp Forever 0.9.3, Naowh Professions 1.1.12 (installés) | divers | wago 1.60.1.70338 | recettes, formateurs et vendeurs positionnés ; **aucun nœud de récolte positionné** | lus en local pour les formateurs (bloc H) |

Non trouvé : générateur de guides RestedXP pour Forever ; carte des nœuds de récolte de Forever sous licence ouverte ;
XP par heure de route mesurée sur Forever.

### Factoruide : trois options comparées

Constats (code lu, rien exécuté) : binaire `fg` (`crates/fg/src/main.rs:37-143`, sous-commandes `route`, `replay`,
`travel`…), sans Tauri, mais Rust **1.99.0** épinglé, `rusqlite` et `zstd` en bundled (MSVC Build Tools à installer),
519 paquets au `Cargo.lock` ; entrée `job::plan(conn, &Overrides, &PlanRequest)` (`job/mod.rs:82`) sur une base de
~30 tables (`m_*` aux colonnes JSON implicites, `client_*`) construite **hors dépôt par un outil non publié** ;
aucun test sur la base Forever ; ~20 000 lignes dans `fg-route`. Règles d'XP de Classic : XP de quête = valeur Classic
de la base (`xp.rs:129`), `QuestXP` du client seulement pour les quêtes sans XP (`sources.rs:204-209`) ; XP d'un
monstre plus bas sur la base du niveau du joueur (`xp.rs:207-216`), contraire à notre règle mesurée (décision 249) ;
facteurs de donjon « bêta, encore en réglage » (`xp.rs:141-152`). Sortie : JSON typé et `Routes.lua` propre à son
addon, aucun export RestedXP.

| | 1. Moteur nourri de nos données | 2. Reprise des algorithmes (choisie) | 3. Contribution seule |
| --- | --- | --- | --- |
| Travail | reproduire ~30 tables, patcher `xp.rs` (fork), installer Rust, traduire sa sortie en RestedXP | ~5 jours pour un sous-ensemble utile | faible |
| Qualité des routes | la meilleure (tournoi, ALNS, puissance, élites) | moindre : glouton par régions + amélioration locale, à réétalonner | la sienne, avec ses règles d'XP |
| Règles de Forever | via notre fork, à rebaser à chaque version | les nôtres, dans `forever/engine/` | dépend de l'auteur |
| Calcul | 2 min (normal) à 6 min (poussé), annoncé | à mesurer (cible : moins de 60 s pour 10 niveaux) | — |
| Risques | dérive (8 versions en 5 jours, schéma implicite), binaire externe hors `forever/engine/`, toolchain | routes moins bonnes que les siennes ; temps de calcul de Python | aucun contrôle ; nos règles en conflit avec ses tests Classic |

**Recommandation retenue (option 2)** : porter, cités (`MIT, brouznouf/factoruide@f7da6da, chemin`), la valeur d'une
quête avec sa chaîne (`plan/worth.rs`), la construction par régions (`plan/regions.rs`) puis gloutonne
(`plan/construct.rs`), et quatre mouvements d'amélioration locale à graine fixe (`plan/moves.rs`, `plan/search.rs`) ;
pas de tournoi, d'ALNS, de modèle de puissance ni de terrain en RX1. **Risque principal** : routes moins bonnes que
celles de Factoruide ; parade : `forever route compare` mesure l'écart sur le même personnage quand le joueur exporte
une route de Factoruide (`.fgguide`, lu en local), et les réglages vivent dans `mechanics.json`.

## Couverture mesurée (2026-10-14, liste fusionnée `e9ea35ee9b5847d2`, base Forever de Factoruide `f7da6da`)

Script hors dépôt (`sqlite3` sur la base décompressée) ; seuls ces agrégats entrent dans le plan.

**556 quêtes nouvelles** : 555 connues de Factoruide (480 `available`, 57 `incomplete`, 18 `removed`), 1 absente ;
31 sous un autre nom (identifiant réutilisé ou nom divergent) ; **XP absente pour 545** (Factoruide prend alors une
valeur par niveau de `QuestXP`, colonne `Difficulty_5`, sans l'indice de difficulté de la quête), XP observée pour 8 ;
70 sans donneur, 72 sans rendu ; 322 avec objectifs, 4 dont une cible n'a aucune position ; **24 connues de VMaNGOS**
(identifiants repris de la Classic).

**183 quêtes retouchées** : toutes connues de VMaNGOS, 178 `available` ; **périmées** chez Factoruide par rapport à nos
champs changés : `prereq_any` 115 (sur 142 changés), `min_level` 18 (sur 20), `level` 11 (sur 16), `xp` 11 à
recouper par `QuestXP`.

**Ce que Factoruide sait et pas nous** : 390 quêtes `available` absentes de notre liste (337 d'identifiant ≥ 90000 ;
372 dans la table `QuestV2` du client). Recherche de la cause (clé par clé dans les fichiers installés, RXPGuides,
fichiers MoP, SoD et de traduction exclus) : **79 sont citées dans un fichier local que nous lisons ou pourrions
lire** (Naowh Discovery 25, Forever Guide `Data.lua` 22, SavedVariables de Questie 19, base de Questie 17, Dungeon
Journal de Naowh 9, Naowh `Shared/Data/Forever.lua` 8, FojjiCore Dungeon Journal 4, Forever Guide `ChainData.lua` 3,
ForeverDungeonJournal 3 ; recouvrements et coïncidences numériques possibles, à trier au bloc A) ; **~311 ne sont dans
aucune source locale ni dans QuestieDB `a4cad87`** (Factoruide les tient de Wowhead Forever et d'AllTheThings).
Conclusion : il y a bien des **lecteurs incomplets** (au moins Forever Guide, Questie apprises en jeu, Naowh), à
corriger au bloc A ; le reste est « vue seulement chez Factoruide ».

**VMaNGOS** : il ne couvre aucune quête nouvelle (hors 24 identifiants repris) et tient les 183 retouchées dans leur
version Classic. Ses positions de monstres sont inutiles : Questie installé les a déjà (positions de Factoruide :
14 761 entités par Questie, 2 057 par VMaNGOS). Il n'est **pas téléchargé** ; les positions de Questie pour les
monstres et objets que Forever ne change pas sont marquées « base Classic », `suppose`.

**Livre des donjons (DJ1)** : les 23 donjons à 5 de `dungeons.json` sont chez Factoruide (Stockade et Sunken Temple
sous d'autres noms) ; sa durée de passage est la formule déjà reprise en DJ1 (`dungeon.run_defaults`), son XP de quête
de donjon la valeur Classic × facteur de bêta : **nos placements de DJ1 (XP de `QuestXP`, passages relevés) priment**.

## Constats (dépôt, addons installés, 2026-10-14)
- `forever/route.py` : `RouteStep` (`kind` ∈ goto, accept, turnin, click, use_item, note ; `map`, `x`, `y` en
  pourcentage de carte ; `source`, `certainty`), `sleeping_bag_steps`, `bonus_reminders`, `dungeon_steps`,
  `dungeon_placements` ; `forever/engine/dungeon.py` : `placement_level`, `first_pass`, `repeat_pass`.
- `forever/quests.py` : `build_quests` → `QuestBook` (cache `<cache>/quests/<empreinte>.json`), champs `giver`,
  `turn_in`, `objectives` (identifiants de Questie, camps de Journeys), `prereq_all|any`, `next`, `exclusive`, `chain`,
  `xp`, `classes`, `races` ; `order_quests` (tri topologique) ; priorité par champ de la décision 248.
- Moteur d'XP réutilisable : `quest_xp`, `mob_kill_xp`, `xp_multiplier`, `session_xp` (`forever/engine/xp.py`),
  `objectives()` (`forever/sim/objectives.py:271`), `kill_time` (`forever/kill_time.py:194`). **Aucun modèle de
  trajet** : `dungeon_travel_s` et `quest_overhead_s` sont des constantes de `mechanics.json` ; registre C4 (vitesse
  du joueur) et C6 (temps en mouvement) `absent`.
- Pont : boutons (`forever/bridge/buttons.py`, visibles quand `requires ⊆ DONE_SLICES`), actions fermées
  (`actions.py:19`), cartes à boutons (`cards.py`) : **aucun mécanisme de question à choix** ; emplacements
  `ForeverBridge_S001…S200` = une affectation de données Lua (`slots.py:73-124`), aucun code généré. Profil au schéma 3
  : `professions` existe déjà (`profile.py:58`, `set_character`) ; **le contexte de ForeverBridge n'envoie aucun
  métier** (`addon/ForeverBridge/Message.lua:28-29`). « voir À valider » : `profile_gap.py:33`, `loop.py:443`, `:570`,
  `status.py:51`, `:223`.
- RXPGuides : `ImportGuide(guide, text, defaultFor, cache)` analyse, ajoute et garde le guide dans
  `addon.db.profile.guides` avec un marqueur lié au compte (`GuideLoader.lua:371`, `:435`) ; rejet au chargement si
  le marqueur ne correspond pas (`:821`) : RXP1 reste la question ; le menu se régénère par
  `RXP:ScheduleTask(RXP.RXPFrame.GenerateMenuTable)` (`:1588`) ; chargement par `RXP:LoadGuide`. Sous Forever,
  l'en-tête `#forever` ou `#classic` est accepté (`:1054`). Le chiffré : `guideImporter:ImportString`, mode `:`
  (clé tirée de la BattleTag, `:484-540`).
- Tables `QuestLine` (3), `QuestLineXQuest` (22), `QuestPOIPoint` (99, sans quête : il faudrait `QuestPOIBlob`) :
  comptées en T04d, **non décodées en RX1** (trop peu de lignes, `docs/research/quetes-forever.md:107-111`).

## Conception

### Données et sources
- **Révision de 1.60.1.70338** (règles écrites avant `forever decode`, installées par `forever install`, décision
  263) : `TaxiNodes`, `TaxiPath`, `TaxiPathNode`, `UiMapAssignment` ajoutées à `forever/pipeline/tables.py`,
  téléchargées par `forever fetch` (voie existante), décodées en **`travel.json`** : points de vol (nom, continent,
  position monde, faction par `ConditionID`/drapeaux), trajets (de, vers, coût), longueur de chaque trajet (somme des
  segments de `TaxiPathNode`), passage carte ↔ monde (`UiMapAssignment` : bornes de la carte, région monde). Ajouté à
  `DECODED_FILES`, `sources.json`, `origins.json`.
- **`mechanics.json`** : `route.*` (vitesse de course et de vol, coûts fixes d'une prise, d'un rendu, d'un changement
  de zone, d'une pierre de foyer, poids confort contre XP par heure, plafonds d'XP de monstres en chemin, effort et
  graine de la recherche) avec source et certitude ; les valeurs reprises de Factoruide sont citées (`params.rs`,
  `suppose`).
- **Lecteurs locaux nouveaux** (`forever/pipeline/travel_sources.py`) : Shortest Path Forever (`Data/Taxi.lua`,
  `Walks.lua`, `Transports.lua`, `Portals.lua`) et Naowh Journeys (`Walk.lua` : base64 → inflate → CBOR ;
  `DataMap<map>.lua` : passages et trajets) ; branchés sur `forever addons status` ; cache
  `<cache>/travel/<empreinte>.json`, jamais dans le dépôt. **Décodeur CBOR et inflate** écrits en Python standard
  (`zlib` du stdlib, CBOR minimal : entiers, chaînes, tableaux, tables, flottants) : aucune dépendance.
- **Fusion des trajets** (`forever/travel.py`) : vols du client (prime), écart avec `Taxi.lua` signalé ; marche par le
  réseau de Journeys, sinon ligne droite dans la zone (`suppose`) ; bateaux, zeppelins et portails de Shortest Path
  (`suppose`, part CMaNGOS) ; positions des PNJ et objets : liste fusionnée, sinon `spawns` de Questie « base
  Classic » (`suppose`).
- **Factoruide en recoupement** (`forever/pipeline/factoruide.py`) : lecture de la base décompressée du cache
  (`sqlite3` du stdlib ; décompression par la `libzstd` trouvée sur le disque, sinon base absente signalée, jamais
  téléchargée), épinglée à `f7da6da` (empreinte de `forever.sqlite.zst` vérifiée) ; sert seulement à `forever quests
  diff --factoruide` (écarts) et au statut « vue seulement chez Factoruide ».

### Moteur de route (fonctions pures)
- `forever/engine/travel.py` : distance et temps d'un trajet (marche, vol, transport, foyer) sur un graphe déjà
  construit ; `travel_time(graph, a, b, *, flights_known, mounted) -> Leg(seconds, legs, certainty)`.
- `forever/engine/route.py` : **simulation** d'une suite d'arrêts (`Stop` : prendre, objectif, rendre, donjon, vol,
  foyer, entraînement) sur un état (`RouteState` : niveau, XP, position, journal plein ou non, quêtes faites, vols
  connus, bonus actifs) ; XP par `quest_xp` et `mob_kill_xp` (T04d, avec la règle du monstre plus bas), bonus par
  `xp_multiplier` et `session_xp` (T04f), temps par monstre par `kill_time` (mesure du joueur d'abord, décision 249),
  donjons par `first_pass` (DJ1) ; sortie `RouteResult(levels, seconds, xp_h, stops, warnings, certainty)` ; chaque
  terme garde sa source.
- `forever/optimize/route.py` (portage cité de Factoruide) : valeur d'une quête et de sa chaîne ; regroupement par
  pôle de quêtes et tranche de niveau ; construction par régions puis gloutonne ; amélioration locale (déplacer un
  arrêt, un bloc, retirer, insérer) à budget compté en essais et graine fixe (déterministe) ; contraintes dures :
  prérequis, exclusives, faction, race, classe, niveau minimal, journal (taille dans `mechanics.json`), donjon à son
  placement de DJ1 (`placement_level`), jamais deux passages d'un donjon sans raison (un passage suivant seulement si
  son XP par heure dépasse la meilleure zone, I14).
- `forever/route.py` (assemblage, hors moteur) : `plan_route(deps, request) -> RoutePlan` (personnage, profil,
  liste fusionnée, livre des donjons, trajets, bonus) ; `RouteRequest(start_level, end_level, dungeons, group,
  gather, upgrades_first, class_quests, reputations, exclude, include)` ; étapes `RouteStep` élargies (`fly`, `hs`,
  `train`, `dungeon`, `xp`) ; quêtes « vue seulement chez Factoruide » et `suppose` sans donneur jamais placées.

### Guide RestedXP
- `forever/rxp.py` : `encode_guide(plan, *, name, group) -> str`, déterministe, syntaxe relevée dans `ParseGuide`
  (en-tête `#forever`, `#name`, `#group`, `#version`, `#next`, `<< Faction` ; étapes `step`, `.accept`, `.turnin`,
  `.complete`, `.goto zone,x,y`, `.xp`, `.fly`, `.hs`, `.train`, `>>texte`, `+texte`) ; noms de zone de la carte
  (`uiMapID` → nom anglais du client) ; textes en anglais (client enUS) ; échappement des caractères réservés
  (`>>`, `<<`, `,`, `|`) ; jamais une chaîne d'import chiffrée.
- `tests/fixtures/rxp/parser.py` : **analyseur de test** écrit d'après la structure de `ParseGuide` (en-tête, étapes,
  commandes connues, arguments séparés par des virgules), sans aucun texte de RestedXP.

### Livraison
- **En jeu** (ForeverBridge **0.3.0**) : un emplacement de réponse peut porter `guide = {name, group, text, sha}` ;
  hors combat (`InCombatLockdown` sous `pcall`, sinon attente de `PLAYER_REGEN_ENABLED`, `RegisterEvent` sous
  `pcall`), le Lua appelle `pcall(RXPGuides.ImportGuide, text)` puis `pcall(RXP.ScheduleTask, RXP,
  RXP.RXPFrame.GenerateMenuTable)` s'ils existent, et répond au pont (succès, erreur, RestedXP absent) ; aucun
  `loadstring`, aucune fonction d'action, aucun `ImportString`.
- **Repli jeu fermé** (`forever/bridge/guide_addon.py`) : `Interface/AddOns/ForeverRoute/` = `ForeverRoute.toc`
  (`## Dependencies: RXPGuides`, ligne `## Interface` reprise du `.toc` de ForeverBridge installé, jamais devinée) et
  `Guide.lua` (`RXPGuides.RegisterGuide([==[…]==])`, niveau de crochets choisi pour ne pas apparaître dans le texte) ;
  écrit seulement si le jeu est fermé (même contrôle que `scripts/install_addon.py`), sauvegarde datée de l'ancien
  dossier, réécriture complète ; aucun autre chemin.
- CLI : `forever route plan --from N --to M [--dungeons auto|none|<liste>] [--group] [--class-quests]
  [--exclude …] [--include …] [--json]`, `forever route show <id>`, `forever route guide <id> [--out FILE]`,
  `forever route deliver <id> --addon` (repli), `forever route compare <fichier.fgguide>` (bloc G) ; plan gardé dans
  `<cache>/routes/<id>.json` ; MCP : outil **`forever_route`** (plan, aperçu, ajustement), chaque résultat avec
  `provenance`.

### Pont et panneau
- **Questions à choix générales** (décision 258) : `forever/bridge/choices.py` : `Choice(id, prompt, options,
  multi, default)` ; un emplacement porte `choices` ; le Lua affiche des boutons dans le panneau d'action, un clic
  envoie `c=<id>:<clé>` ; le pont transmet la réponse à la conversation en texte fixe (« Réponse : <libellé> ») ;
  ouvertes à toutes les conversations.
- **Bouton « Feuille de route »** (`requires=("RX1",)`, toutes les classes, décision 243) : ouvre les questions
  (niveaux de départ et d'arrivée, donjons, solo ou groupe, récolte, améliorations d'abord, quêtes de classe,
  réputations), puis l'aperçu (niveaux gagnés, temps, XP par heure, donjons placés, récompenses notables, bonus pris
  en compte, certitude) ; « Livrer dans RestedXP » et « Ajuster » en boutons ; ajustements en texte (« enlève
  Wailing Caverns ») traduits par la conversation en options de `forever_route`.
- **Métiers** (décision 254) : ForeverBridge envoie `professions` (`GetNumSkillLines`/`GetSkillLineInfo` sous
  `pcall`, métiers principaux et secondaires avec leur rang) ; écrits au profil au clic (`apply_game_fields`).
- **« voir À valider »** : n'est plus ajouté quand aucune carte n'est visible pour le joueur (cartes masquées
  comprises).

## Blocs (ordre d'utilité ; A à E = première version, finie le 2026-10-20)

### Bloc A — Quêtes manquantes et recoupement Factoruide (2026-10-15)
1. Lecteur de la base de Factoruide (cache, épinglé) et `forever quests diff --factoruide` : comptes par statut,
   « vue seulement chez Factoruide ».
2. Pour les 79 quêtes citées en local : trouver le lecteur fautif (Forever Guide `Data.lua` et `ChainData.lua`,
   QuestieForeverDB des SavedVariables, Naowh `Shared/Data/Forever.lua`, Dungeon Journal, Discovery) et le corriger
   (cause écrite dans `docs/research/quetes-forever.md`, comme `read_fdj` en DJ1) ; les coïncidences numériques sont
   écartées avec leur preuve.
3. Statut **`vue seulement chez Factoruide`** (`suppose`), jamais placée dans une route ; `MERGE_FORMAT` → 3.
4. Agrégats à jour dans `docs/research/quetes-forever.md` (statuts, couverture Factoruide et VMaNGOS de ce plan).

### Bloc B — Trajets, première forme (2026-10-16)
1. Tables du client : `TaxiNodes`, `TaxiPath`, `TaxiPathNode`, `UiMapAssignment` (fetch, règles, `travel.json`,
   révision installée par `forever install`).
2. `forever/engine/travel.py` : ligne droite dans une zone (vitesse de `route.*`), vols du client, foyer ; registre C4
   et C6 alimentés.
3. Lecteurs de Shortest Path Forever et de Journeys **en lecture de passages seulement** (changement de zone) ; le
   reste du réseau de marche au bloc F.

### Bloc C — Moteur et recherche de route (2026-10-17 et 18)
Simulation, valeur des chaînes, construction par régions et gloutonne, amélioration locale ; donjons à leur
placement ; bonus et rappels de T04f (`sleeping_bag_steps`, `bonus_reminders`) placés ; quêtes de classe de la liste
fusionnée (champ `classes`) au bon niveau ; `forever route plan|show`.

### Bloc D — Guide RestedXP et livraison (2026-10-19)
`forever/rxp.py`, analyseur de test, `forever route guide|deliver --addon`, ForeverBridge 0.3.0 (`guide` dans
l'emplacement, `ImportGuide` sous `pcall`), `scripts/check_addon.py` élargi (appel permis à `RXPGuides.ImportGuide`,
`RegisterGuide`, `RXP:ScheduleTask` seulement ; `ImportString` interdit) ; RXP1 décrite dans `docs/ADDON.md` comme
vérification facultative.

### Bloc E — Questions à choix, bouton, aperçu, métiers (2026-10-20)
`choices.py` et leur rendu Lua, bouton « Feuille de route », aperçu et ajustements, `forever_route` en MCP, skill
`forever-routes` (plugin 0.12.0), métiers dans le contexte et le profil, correction de « voir À valider ».
**Fin de la première version** : merge de `rx1` dans `main` après la CI (les blocs suivants sur `rx1b`).

### Bloc F — Trajets complets (2026-10-21 et 22)
Réseau de marche de Journeys (CBOR), bateaux, zeppelins et portails de Shortest Path ; détours vers un maître de vol
ou une auberge dans l'amélioration locale ; écarts client ↔ Shortest Path signalés.

### Bloc G — Comparaison et contribution (2026-10-23)
`forever route compare <fichier.fgguide>` (route de Factoruide exportée par le joueur, lue en local : XP, temps et
quêtes par notre simulation) ; texte de l'issue pour Factoruide (XP des quêtes par `QuestXP` et indice de difficulté ;
base au niveau du monstre plus bas) préparé dans `tasks/RX1-factoruide-issue.md`, **envoyé seulement sur accord**.

### Bloc H — Métiers et réputations sur le chemin (après LN1 si le temps manque)
Formateurs de métier (Naowh Professions, SkillUp) placés sur la route quand un rang s'ouvre ; quêtes de métier ;
quêtes de réputation connues (la route ne chiffre pas la réputation, RP1) ; récolte : faute de nœuds positionnés,
seulement une note par zone (« zone riche en … » si une source locale le dit), sinon rien. « monte mon herboristerie
de 75 à 150 » : réponse « non couvert » avec ce qui manque (MT1).

## Tests attendus (valeurs tirées des fixtures, aucun chiffre de jeu écrit dans un test)

### Bloc A (`tests/unit/test_quests_factoruide.py`, `tests/unit/test_quest_sources_rx1.py`)
- `test_factoruide_db_read_locally` : fixture `tests/fixtures/factoruide/forever.sqlite` (5 quêtes, schéma réduit
  `m_quest`, `m_quest_relation`, `import_run`) → 5 quêtes lues, provenance (commit, empreinte).
- `test_factoruide_absent_is_reported` : cache sans base → statut `absent`, aucune exception, aucun réseau.
- `test_seen_only_at_factoruide` : quête de la fixture inconnue de nos sources → statut `vue seulement chez
  Factoruide`, certitude `suppose`, exclue de `plan_route`.
- `test_forever_guide_reader_sees_all_quests` (et un test par lecteur corrigé) : fixture extraite du fichier réel
  (structure seulement, identifiants fictifs) contenant N quêtes dans la forme jusque-là ignorée → N lues.
- `test_merge_format_bumped` : `MERGE_FORMAT == 3`, l'ancien cache est rebâti.

### Bloc B (`tests/unit/test_travel.py`, `tests/unit/test_engine_travel.py`)
- `test_travel_tables_decoded` : fixture de 3 points de vol et 2 trajets → `travel.json` (longueur d'un trajet = somme
  des segments de la fixture).
- `test_map_to_world` : point (50 %, 50 %) d'une carte de fixture → coordonnées monde au centre de ses bornes.
- `test_straight_line_time` : deux points d'une même zone de fixture → distance / vitesse de `route.*` (valeur lue).
- `test_flight_used_when_known` / `test_flight_ignored_when_unknown` : même trajet, vol connu ou non.
- `test_zone_change_through_pass` : passage de Journeys de fixture emprunté entre deux zones.
- Mises à jour des comptes : `test_data_import.py`, `test_manifest.py`, `test_decode_version.py` (nouveau
  `travel.json`).

### Bloc C (`tests/unit/test_engine_route.py`, `tests/unit/test_optimize_route.py`)
Fixture `tests/fixtures/route/` : 12 quêtes sur 2 zones (une chaîne de 3, une exclusive, une quête de classe, une de
niveau minimal trop haut, une sans donneur), un donjon de fixture et son placement.
- `test_prerequisites_respected` : dans toute route rendue, chaque quête suit ses prérequis et sa chaîne.
- `test_exclusive_once` : une seule des deux exclusives.
- `test_min_level_respected` : aucune prise avant `min_level`.
- `test_dungeon_at_first_pass_with_quests` : le donjon est placé à `placement_level` de la fixture, ses quêtes prises
  avant, un seul passage.
- `test_no_repeat_dungeon_without_reason` : passage suivant seulement si son XP par heure dépasse la meilleure zone.
- `test_class_quest_only_for_class` : quête de classe présente pour la classe, absente pour une autre.
- `test_route_xp_uses_t04d_and_t04f` : XP de la route = somme des `quest_xp` et `mob_kill_xp` majorées par
  `xp_multiplier` sur la fixture (comparaison au calcul des fonctions du moteur, `pytest.approx(rel=1e-12)`).
- `test_route_deterministic` : deux appels, même graine → mêmes arrêts.
- `test_improvement_never_worse` : coût après amélioration ≤ coût de la construction.
- `test_route_provenance` : `provenance` (version, empreinte, date, certitude = la plus faible des termes).
- `test_route_cli_plan_json` : `forever route plan --from 1 --to 3 --json` sur les fixtures.

### Bloc D (`tests/unit/test_rxp.py`, `tests/unit/test_bridge_guide_lua.py`, `tests/unit/test_guide_addon.py`)
- `test_guide_parses` : le guide encodé de la route de fixture passe l'analyseur de test (en-tête `#forever`, `#name`,
  `#group` ; chaque étape connue ; arguments valides).
- `test_guide_roundtrip` : quêtes et ordre relus = ceux de la route.
- `test_guide_escaping` : un nom avec `>>`, `,` et `|` reste une seule étape.
- `test_never_encrypted` : aucune ligne au motif d'une chaîne d'import (`^\d+\|`, segments `(-?\d+)(\D)(base64)%`) ;
  aucun appel à `ImportString` ni écriture de `RXPString` dans `addon/` (grep).
- `test_no_rxpguides_text_in_fixtures` : aucune fixture ne contient une ligne d'un fichier de `RXPGuides/Guides`.
- `test_import_guide_called_under_pcall` (lupa, client simulé avec un faux `RXPGuides`) : l'emplacement porteur d'un
  guide appelle `ImportGuide` une fois avec le texte, puis `ScheduleTask` ; réponse « livré ».
- `test_import_guide_absent` : sans RXPGuides → réponse « RestedXP absent », aucune erreur Lua.
- `test_import_deferred_in_combat` : en combat, appel après `PLAYER_REGEN_ENABLED`.
- `test_guide_addon_written_only_when_game_closed` : jeu ouvert (processus simulé) → refus ; fermé → `.toc` et
  `Guide.lua` écrits sous `ForeverRoute/` seulement, sauvegarde de l'ancien dossier.
- `test_guide_addon_bracket_level` : texte contenant `]]` et `]=]` → niveau de crochets qui n'y apparaît pas.
- `test_addon_rules.py` vert (nouvelles règles de `check_addon.py`).

### Bloc E (`tests/unit/test_bridge_choices.py`, `tests/unit/test_bridge_choices_lua.py`, `tests/unit/test_bridge_professions.py`)
- `test_choice_payload` : `Choice` sérialisé dans l'emplacement (prompt, options, multi).
- `test_choice_click_sends_answer` (lupa) : clic → `c=<id>:<clé>` ; pont → texte « Réponse : <libellé> » à la
  conversation.
- `test_choice_unknown_key_refused` : clé hors options → ignorée, journalisée.
- `test_route_button_visible_when_rx1_done` : bouton absent sans `RX1` dans `DONE_SLICES`, présent avec ; pour toutes
  les classes.
- `test_preview_fields` : aperçu = niveaux, temps, XP par heure, donjons, récompenses notables, bonus, certitude.
- `test_professions_in_context` (lupa) : `GetSkillLineInfo` simulé → `professions` dans le message ; API absente →
  champ absent, aucune erreur.
- `test_professions_written_to_profile_on_click` : `apply_game_fields` écrit les métiers au profil.
- `test_no_pending_mention_without_visible_card` : aucune carte visible → pas de « voir À valider » (tests existants
  `test_bridge_loop_p06b_c.py:23` et `test_bridge_p06b_g.py:260-267` à adapter dans le commit « tests » si leur
  prémisse change ; sinon demande de correction).
- `test_mcp_forever_route` : outil MCP `forever_route` rend plan et `provenance`.

### Blocs F à H
- `test_cbor_decode` (cas : entiers, chaînes, tableaux, tables, flottants) ; `test_journeys_walk_graph` (fixture
  base64 + deflate + CBOR fabriquée par le test) ; `test_transport_leg` ; `test_flight_master_detour` ;
  `test_compare_fgguide` (fixture `.fgguide` fabriquée, structure seulement) ; `test_trainer_inserted_when_rank_opens`.

## Registre (`docs/MECHANICS_REGISTRY.yaml`)
- **C4** vitesse de déplacement du joueur : `absent` → `teste` (`route.*`, source et certitude au bloc B).
- **C6** temps en mouvement : `absent` → `teste` pour le trajet hors combat (sorts en mouvement hors périmètre).
- **I18** (nouvelle, optimisation) : feuille de route de leveling (simulation, construction, amélioration ; portage
  cité de Factoruide), `suppose`.
- **I19** (nouvelle, données) : trajets (vols du client, marche de Journeys, transports de Shortest Path), `suppose`
  sauf vols du client (`certain` pour l'existence et le coût, `probable` pour la durée).
- **I17** (placement d'un donjon dans une route) : tests de RX1 ajoutés.
- Comptes de `test_registry.py` sans total figé (décision 214) : rien à écrire, sauf le nombre d'entrées `teste` si un
  test le fige.

## Questions ouvertes (à ajouter à `docs/OPEN_QUESTIONS.md`)
- **RXP2** — Le menu de RestedXP montre-t-il le guide importé sans `/reload`, et `RXP:LoadGuide` le charge-t-il
  directement ? (vérification facultative en jouant, décision 260).
- **TRV1** — Vitesse de course, de vol et de monture de Forever (monture au niveau 40 selon Factoruide, non sourcé) :
  à lire dans le client ou dans les relevés de ForeverLogger.
- **TRV2** — Écarts entre les vols du client et `Taxi.lua` de Shortest Path (durées CMaNGOS).
- **RTE1** — Écart entre nos routes et celles de Factoruide sur un même personnage (bloc G).
- **LVL17** — Les ~311 quêtes vues seulement chez Factoruide (Wowhead Forever, AllTheThings) existent-elles dans
  Forever ? (une quête vue en jeu par ForeverLogger ou Questie l'établit).

## Hors périmètre
Tournoi, ALNS, modèle de puissance, terrain et foule de Factoruide ; montée de métier optimisée (MT1, EC1) ; plan de
réputation chiffré (RP1) ; suivi en direct (RestedXP le fait) ; décodage de `QuestLine`, `QuestLineXQuest`,
`QuestPOIPoint` ; téléchargement de VMaNGOS ; installation d'AllTheThings ; envoi de l'issue à Factoruide sans
accord ; tout guide payant ou chiffré.

## Risques
- **Routes moins bonnes que celles de Factoruide** (sous-ensemble porté) : mesuré au bloc G, réglages dans
  `mechanics.json`.
- **Temps de calcul de Python** : budget compté en essais, plafond de temps dans `route.*` ; cible moins de 60 s pour
  10 niveaux, mesurée au bloc C (hors hook de fin de tour, mémoire « hook d'arrêt et chronométrage »).
- **RXP1** : `ImportGuide` peut ne pas garder le guide d'une session à l'autre (marqueur lié au compte) : repli
  `ForeverRoute` ; la route reste aussi lisible dans le chat.
- **Licences** : base de Factoruide (GPL, Questie sans licence, Wowhead) jamais recopiée ni livrée ; RXPGuides
  (CC BY-NC-SA) : on n'appelle que son API, aucun texte repris ; Shortest Path (GPL-3) et Journeys (droits réservés)
  lus en local, agrégats seulement.
- **Positions « base Classic »** fausses pour des monstres déplacés par Forever : `suppose` affiché, corrigé par les
  relevés de ForeverLogger.
- **Calendrier** : si le bloc C déborde, la première version livre une route sans amélioration locale (construction
  seule) plutôt que de repousser D et E.

## Étapes d'exécution
0. Sur `main` avant la branche : décision **266** dans `docs/DECISIONS.md` (choix de ce plan : option 2, trajets des
   deux sources, repli `ForeverRoute`, base de Factoruide en recoupement, quêtes vues seulement chez Factoruide hors
   des routes, calendrier) ; Factoruide, VMaNGOS, QuestieDB et AllTheThings dans `docs/DATA_SOURCES.md` ; archiver
   `tasks/idees-du-chat-2026-10-13-factoruide.md` dans `tasks/archive/`.
1. `git switch -c rx1` ; blocs A à E, chacun rouge (`RX1: tests (bloc X)`) puis vert (`RX1: bloc X vert`).
2. Fin de la première version : `/verifier`, push, CI verte Ubuntu et Windows, fusion en avance rapide, branche
   supprimée ; résumé à l'utilisateur.
3. Blocs F à H sur `rx1b`, jusqu'au 2026-10-23 ; ce qui n'est pas fini est mis en pause (ROADMAP : « RX1 en pause
   après le bloc X »), LN1 commence au plus tard le 2026-10-24.
