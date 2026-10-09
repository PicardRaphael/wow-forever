# Addons de forever-core sur WoW: Forever

Source de rédaction : `docs/research/addon-forever.md` (rapport du 2026-09-27, sources en fin de fichier). Légende reprise du rapport : **[Certain]** source primaire ou mesure publiée sur le client Forever, **[Probable]** sources concordantes ou comportement Retail non remesuré, **[Supposé]** inférence ou source unique, **[À vérifier]** non établi. Code : `addon/` ; installation et contenu de la SavedVariable : `addon/README.md`.

## 1. Objectif et non-objectifs
- **Objectif** : afficher dans le jeu des données **précalculées par `forever`**, et rapporter hors du jeu le contexte du personnage ; analyser les journaux de combat **après** le combat, hors du jeu.
- **Non-objectifs** : aucune automatisation, aucun conseil de rotation en combat, aucun calcul sur des valeurs de combat dans l'addon, aucun canal temps réel.
- **PvP (PV1)** : aucun suivi en direct des recharges adverses dans un addon : le journal de combat est refusé aux addons sur Forever et les valeurs de combat y sont secrètes ; seules des fiches fixes (`forever pvp`, `forever_lookup(kind="pvp")`), consultées hors combat ou affichées en jeu par la tranche FA1p.

## 2. Règles
### Politique de Blizzard
- [Certain] Addons gratuits ; code ni caché ni obfusqué ; pas de publicité ni de dons ; pas d'usage excessif du chat ; Blizzard peut désactiver des fonctionnalités.
- [Certain] Interdiction des logiciels qui modifient le client ou contrôlent le jeu.

### Lignes rouges
- **Pas d'automatisation** : aucune fonction d'action (`CastSpell*`, `UseAction`, `RunMacro`, `RunMacroText`), aucun `SendChatMessage` automatique, aucune macro créée ni lancée par nos addons (`CreateMacro` compris). Exception (décision 195) : forever-core peut produire le **texte** de macros par classe, importé par le joueur dans Naowh Forever (`!NFM1!`) ou collé à la main ; `/cast`, `/use` et leurs conditions seulement, jamais `/run` ni `/script` (EX1).
- **Pas de lecture d'écran ni de pixels**, pas de lecture de la mémoire, pas d'injection. Exception unique (décision 194) : la bande de pixels du pont de P06a, dessinée par notre addon seulement quand un message attend, capturée par `forever bridge` dans la seule zone de la fenêtre du jeu et seulement quand un message attend ; aucune autre capture.
- **Pas d'entrées simulées** (touches, clics).
- Zone grise, à éviter : fenêtre externe qui conseille en direct pendant un combat ; messages de chat comme canal de données ; ponts pixels + lecture d'écran tiers (le pont de P06a est recodé dans le dépôt, dans le périmètre de la décision 194 ; section 9).
- **Addons de la communauté** (décision 196) : leur code n'est jamais modifié ni recopié ; on n'utilise que leurs points d'import (chaînes collées par le joueur) et leur API publique documentée (EllesmereUI `SwitchProfile`, par exemple), hors combat et sous `pcall` ; jamais d'écriture de leurs SavedVariables hors du jeu.

### Règles de code (contrôlées par `tests/unit/test_addon_rules.py` et `scripts/check_addon.py`)
- La SavedVariable s'initialise dans le gestionnaire d'`ADDON_LOADED` (nom de l'addon vérifié) ; **jamais d'alias local au niveau du fichier** : [Certain, build 70009] sans `## LoadSavedVariablesFirst: 1`, le client remplace la variable globale à `ADDON_LOADED` et un alias pointerait vers une table perdue.
- `pcall` autour de **chaque** `RegisterEvent` : [Certain] sur Forever, un événement inconnu lève une erreur et interrompt le fichier. `pcall` aussi autour de chaque API incertaine (talents `C_Traits`, bonus des sorts, critique) ; une valeur secrète ou une erreur donne un champ absent, jamais une erreur visible.
- **Aucun abonnement au journal de combat** : [Certain, mesuré sur Forever] `COMBAT_LOG_EVENT` et `COMBAT_LOG_EVENT_UNFILTERED` sont refusés (`ADDON_ACTION_FORBIDDEN`, même hors combat). L'addon ne lit ni n'analyse aucun combat ; l'analyse se fait toujours hors du jeu, sur `WoWCombatLog-*.txt`.
- Aucun chiffre de jeu dans `addon/` (`scripts/check_game_numbers.py` couvre `.lua` et `.toc`).
- `.toc` : `## Interface: 16001`, une directive par ligne, fichiers listés présents.

## 3. Plateforme
- [Certain] Forever partage l'architecture d'interface de Mainline et la grande majorité des API de 12.1.5 ; les restrictions de Midnight (valeurs secrètes) y sont actives.
- [Certain] Interface `16001` ; le client cherche `<Addon>_Camelot.toc` avant le `.toc` sans suffixe (Blizzard parle de renommer « Camelot » avant le lancement : [À vérifier] au lancement).
- [Certain] `WOW_PROJECT_ID == WOW_PROJECT_MAINLINE` ; l'en-tête du journal de combat porte `PROJECT_ID 18` : deux identifiants différents [Supposé] (vérifier avec `/dump WOW_PROJECT_ID`).
- [Certain] Fonctions globales anciennes disparues (`GetItemInfo`, `GetSpellInfo`, `GetTalentInfo`…) : utiliser `C_Item`, `C_Spell`, `C_Traits`.
- [Certain] Valeurs secrètes : les informations de combat sont affichables mais pas « connues » ; `UnitHealth` et `UnitPower` secrets même hors combat ; barres d'incantation fonctionnelles.
- Build de référence : 1.60.1.70009 (bêta).

## 4. API utiles
`C_Spell`, `C_Item`, `C_Traits` et `C_ClassTalents` (talents : arbre de traits), `TooltipDataProcessor` (lignes d'infobulle), `Settings`, `issecretvalue`, `InCombatLockdown`, `LoggingCombat` ([Certain] limité à 5 appels par 10 secondes), `GetServerTime`, `date`. [Probable] `GetSpellBonusDamage` et `GetSpellCritChance` répondent hors combat (sous `pcall`, valeur secrète traitée comme absente). Toute API se vérifie dans la référence Forever (`imperial64/forever-addon-dev`, `hated-wow-mcp` en saveur `mainline`) avant usage.

## 5. Canaux de données
| Sens | Canal | Latence | Statut |
| --- | --- | --- | --- |
| forever → addon | Fichier Lua généré par `forever` dans le dossier de l'addon, listé dans le `.toc`, relu au `/reload` (écriture atomique : `.tmp` puis renommage) | un `/reload` manuel (`ReloadUI()` est protégé) | **Recommandé** (V1) |
| addon → forever | SavedVariables (`WTF/Account/<COMPTE>/SavedVariables/<Addon>.lua`), lues par `forever` sans exécuter de Lua | au `/reload`, à la déconnexion, à la sortie | **Recommandé** ([Certain] bug de 69913 corrigé en 70009) |
| jeu → forever | Journal de combat `Logs/WoWCombatLog-*.txt` (format 22 avancé, activé par ForeverLogger) | écrit par paquets : secondes à minutes ([À vérifier] latence) | Analyse **après** le combat |
| appoint | Chaîne copiée dans une zone de saisie | action humaine | Format simple, jamais `loadstring` |
| jeu ↔ forever (P06a) | Pont : bande de pixels lue par `forever bridge` (aller), réserve d'addons chargés à la demande signalée par fichier son (retour), secours `/reload` | quasi direct | **Prévu** (P06a, décisions 194 et 197) |
| forever → addons tiers | Chaînes d'import collées par le joueur (Talents Forever, Naowh Forever, EllesmereUI) | action humaine | **Prévu** (FA1, T10a, EX1, T10 ; décision 196) |
| à éviter | Journal de discussion (écrit à la sortie, ignore les `print` d'addon) ; pixels et lecture d'écran hors du pont de P06a | — | Non |

## 6. Contrat de données
- **ForeverLoggerDB** (retour, schéma 1) : par GUID, instantanés `{reason, time, localtime, level, talents, spell_bonus, spell_crit}` à la connexion, au gain de niveau et au changement de talents ; gains d'expérience `{time, localtime, level, text}` ; depuis CH0 (0.3.0), hors combat seulement, instantanés du familier et des statistiques du Chasseur au même instant (`pet_snapshots`, sur `UNIT_PET`, `PET_UI_UPDATE`, à la connexion, repris à `PLAYER_REGEN_ENABLED` s'ils tombaient en combat) et relevés de la fenêtre Beast Training (`training`, sur `CRAFT_SHOW` et `CRAFT_UPDATE`). [Supposé] API des familiers de Classic (`GetPetTrainingPoints`, `GetPetFoodTypes`, `GetPetLoyalty`, `GetCraftInfo`…) présentes sur Forever : toutes sous `pcall`, champ absent sinon. Détail : `addon/README.md`. Lecture : `forever/pipeline/addon_sv.py` ; jointure avec un journal par GUID et heure locale (`forever logs measure <journal> --addon-sv <fichier>`).
- **Fichier généré pour ForeverAssist** (aller, V1) : variable `ForeverAssistData` avec `schema`, `build`, `generated_at`, puis les données ; schéma versionné et validé par pytest, `Generated.sample.lua` versionné, `Generated.lua` ignoré par git.

## 7. Installation et procédure de test en jeu
1. `uv run python scripts/install_addon.py --dry-run`, puis sans `--dry-run` (terminal administrateur si l'écriture dans `Program Files (x86)` est refusée).
2. En jeu : `/reload` ; le message « journal de combat activé » s'affiche à l'entrée dans le monde si le journal était arrêté.
3. Jouer, puis `/reload` (ou se déconnecter) pour écrire `ForeverLoggerDB`.
4. Hors du jeu : `uv run forever logs scan`, puis `uv run forever logs measure <journal> --addon-sv <SavedVariables>/ForeverLogger.lua`.
5. Familier du Chasseur (CH0) : familier appelé, hors combat, ouvrir la fenêtre du familier puis Beast Training ; changer une seule pièce d'équipement du Chasseur, rouvrir la fenêtre du familier ; `/reload` ; hors du jeu : `uv run forever pets measure --addon-sv <SavedVariables>/ForeverLogger.lua` (protocole complet : `docs/research/familiers-protocole.md`).
6. Code Talents Forever (FA1, à faire avant le 21 octobre, non bloquant pour la fusion) :
   1. Hors du jeu : `uv run forever build leveling --level 30 --preset rapide` ; noter la ligne « Talents Forever »
      (code avec ordre) et le build (talents, ordre).
   2. En jeu : `/tf`, puis `/tf import <code>` (ou coller le code ou le lien dans la fenêtre de partage).
   3. Vérifier dans Talents Forever : même classe, même niveau, mêmes rangs talent par talent, et le même ordre de
      prise niveau par niveau que la sortie de `forever build`.
   4. Refaire avec `uv run forever build dungeon --level 20 --preset rapide` (code sans ordre : points placés arbre
      par arbre par l'addon).
   5. Témoin indépendant : dans Talents Forever, construire un petit build en choisissant soi-même l'ordre, le
      partager (`/tf`, lien), coller le code relevé ; il entre en fixture et doit se relire
      (`uv run forever talents tf decode <code>`) sur les mêmes points et le même ordre.
   6. Tout concorde : la certitude de l'export passe de `probable` à `certain` (champ `verified_in_game`). Un écart :
      noter le code, ce que l'addon affiche et la sortie de `forever talents tf decode`.
   7. **Fait le 2026-10-08** (relevé de l'utilisateur) : `mage/20/--0530002001-klps-6` importé (rangs et positions
      conformes) et réexporté à l'identique, ordre compris (le `?a` ajouté par l'addon n'est pas dans le code) ;
      code du build au préréglage complet importé et conforme. Certitude du format v6 : `certain` (décision
      210) ; témoins dans `tests/fixtures/talents_forever/mage_builds.json`.
   8. **Fait le 2026-10-08** (relevé de l'utilisateur : les deux codes s'affichent exactement comme prévu, talents,
      rangs, rangées, colonnes, arbres vides et points totaux ; `verified_in_game` : `import` ; classes notées dans
      `CLASSES_VERIFIED_IN_GAME` de `forever/talents_forever.py`, champ `class_verified_in_game` de la provenance de
      l'export). Chasseur et Démoniste, codes de `tests/fixtures/talents_forever/class_witnesses.json` (`/tf import
      <code>`) ; vérifier chaque rang à sa rangée et sa colonne (la sortie de `uv run forever talents tf decode <code>`
      les donne), Improved Stings du Chasseur à 2/3 en Marksmanship, rangée 2, colonne 1 ; Improved Life Tap à 2/2
      (Affliction, rangée 1, colonne 1) et Amplify Curse à 1/1 (rangée 3, colonne 3) du Démoniste. Tout concorde :
      `verified_in_game` du cas passe à `import`.
9. **Sonde en jeu A du pont ForeverBridge** (P06a, bloc A ; **avant le 2026-10-14**). Elle dit si la bande de pixels
   est lue par le pont, quel format de son sert de drapeau (`.wav` ou `.ogg`), si le client voit un fichier son modifié
   ou ajouté pendant qu'il tourne, et si un addon chargé à la demande relit son fichier après `/reload`. Commandes
   lancées dans un terminal à la racine du dépôt. Après chaque `/fv diag`, une capture d'écran (touche Impr. écran,
   rangée dans `Screenshots/` du client) suffit comme relevé.
   0. **Une fois, après la mise à jour de la branche** (`lupa` ajouté) : fermer toute session Claude Code qui charge le
      plugin forever (son serveur MCP verrouille `.venv/Scripts/forever.exe`), puis `uv sync`. Symptôme si on l'oublie :
      « failed to remove file … forever.exe » à chaque `uv run`.
   1. **Jeu fermé.** Réglages du client (System > Graphics) : Display Mode `Windowed` ou `Windowed (Fullscreen)`, pas
      `Fullscreen` ; Render Scale à 100 % ; HDR coupé. La mise à l'échelle de Windows peut rester telle quelle. Son
      activé (System > Audio : Enable Sound coché, volume Master non nul, même bas) : sans son, `PlaySoundFile` répond
      « ne jouera pas » pour tout et l'autotest échoue à tort. L'autotest `.ogg` fait entendre un bref son (copie d'un
      son d'un autre addon).
   2. `uv run forever bridge install` : installe `ForeverBridge`, ses fichiers de contrôle (`ctl/`) et l'addon de sonde
      `ForeverBridge_Probe` ; la sortie nomme le `.ogg` copié d'un autre addon pour l'autotest `.ogg`.
   3. Lancer le jeu, entrer avec un personnage ; dans la liste des addons, `ForeverBridge` et `ForeverBridge_Probe`
      sont activés. `/fv` affiche l'aide de ForeverBridge.
   4. **Bande** : `/fv test` (carrés de couleur en haut à gauche, retirés au bout de deux minutes ou par un second
      `/fv test`). Dans le terminal : `uv run forever bridge selftest --live --save tests/fixtures/bridge/band_live.bmp`,
      puis **cliquer dans la fenêtre du jeu** dans la minute et y rester quelques secondes ; revenir au terminal.
      Attendu : « vecteur reconnu (1792 octets, 24 rangées, 4800 cellules) ». Sinon : garder toute la sortie (fenêtre,
      zone client, sonde lue, cellules différentes) et le fichier enregistré.
   5. **Fichiers son, avant modification** : `/fv diag`, capture d'écran. Attendu : `empty` ne joue pas, `valid` joue,
      `flip` et `late` ne jouent pas, en `.wav` comme en `.ogg` ; `ForeverBridge_Probe : chargé, valeur
      « installation »`.
   6. Jeu toujours lancé, dans le terminal : `uv run forever bridge selftest --touch` (remplit `flip`, crée `late`,
      réécrit `Probe.lua`).
   7. `/fv diag`, capture d'écran : `flip` joue-t-il (fichier modifié vu sans `/reload`) ? `late` joue-t-il (fichier
      ajouté vu) ? La valeur de la sonde reste « installation » (déjà chargée dans cette session).
   8. `/reload`, puis `/fv diag`, capture d'écran : valeur de la sonde « modifié à HH:MM:SS » attendue (un addon chargé
      à la demande relit son fichier modifié) ; `flip` et `late` après `/reload`.
   9. Fermer complètement le jeu, le relancer, `/fv diag`, capture d'écran (témoin : `late` doit jouer après un
      redémarrage).
   10. Relevé : la sortie de l'étape 4, les captures des étapes 5, 7, 8 et 9 (ou les lignes recopiées). Rien d'autre
       ne change : ForeverLogger continue ses relevés.

   11. **Fait le 2026-10-09** (relevés de l'utilisateur) : bande lue (« vecteur reconnu », écran 2 560 × 1 440,
       échelle de la bande 0,5333, de l'interface 0,7111) ; un fichier son vide « joue » sur Forever (autotests
       `.wav` et `.ogg` en échec) et un fichier ajouté pendant que le jeu tourne n'est pas vu ; un addon chargé à la
       demande relit son fichier modifié. Conséquence (décision 212 amendée) : retour par consultation de la réserve,
       sans son.
10. **Sonde en jeu B du pont** (P06a, bloc A2 ; **avant le bloc B**, idéalement avant le 2026-10-12). Elle dit si le
    premier chargement d'un emplacement modifié après le lancement du jeu, **sans `/reload`**, lit le nouveau contenu
    (le chemin exact des réponses), si la bande d'**une case par pixel** est lue, et vérifie la fenêtre dédiée.
    Commandes lancées dans un terminal à la racine du dépôt, branche `p06a` à jour.
    1. **Jeu fermé.** Fermer toute session Claude Code qui charge le plugin forever si `uv sync` est nécessaire
       (étape 9.0). Réglages inchangés depuis l'étape 9.1 (fenêtré, Render Scale 100 %, HDR coupé).
    2. `uv run forever bridge install` : réinstalle `ForeverBridge` (avec `Bindings.xml`), ses fichiers de contrôle,
       `ForeverBridge_Probe` et le nouvel emplacement de sonde `ForeverBridge_Probe2`.
    3. Lancer le jeu, entrer avec un personnage. **Ne rien taper de `/fv` encore.** Dans le terminal : `uv run forever
       bridge selftest --touch` (réécrit `Probe2.lua` après le lancement, avant tout chargement).
    4. **Premier chargement sans `/reload`** : `/fv poll`. La fenêtre ForeverBridge s'ouvre et affiche
       `ForeverBridge_Probe2 : chargé, valeur « modifié à HH:MM:SS »` : la consultation de la réserve marche.
       « installation » : le jeu a gardé le contenu du lancement (noter et s'arrêter là) ; « non chargé (…) » :
       noter la raison.
    5. **Bande d'une case par pixel** : `/fv test` (petit rectangle de couleurs de 200 × 24 pixels en haut à gauche ;
       les messages s'affichent dans la fenêtre, pas dans la discussion). Dans le terminal : `uv run forever bridge
       selftest --live --save tests/fixtures/bridge/band_live_1px.bmp`, puis cliquer dans la fenêtre du jeu dans la
       minute et y rester quelques secondes. Attendu : « vecteur reconnu (1792 octets, 24 rangées, 4800 cellules) »
       et « case de 1 pixel ». Sinon : `/fv test` (retire), `/fv test 2`, relancer avec `--save
       tests/fixtures/bridge/band_live_2px.bmp` ; garder les deux sorties.
    6. **Fenêtre** : `/fv` la ferme puis la rouvre ; la déplacer (glisser le titre), l'agrandir (coin bas droit),
       Échap la ferme. Options > Raccourcis > AddOns > ForeverBridge : assigner une touche, l'essayer deux fois.
       `/reload`, puis `/fv` : même position, même taille. Aucune ligne de ForeverBridge dans la discussion générale.
    7. `/fv diag` (seule commande qui écrit dans la discussion, diagnostic demandé) : capture d'écran ; attendu sur
       Forever : autotests `.wav` et `.ogg` en échec (rien n'en dépend désormais).
    8. Relevé : la ligne de l'étape 4, la sortie de l'étape 5 et le fichier `.bmp` enregistré, ce qui ne va pas à
       l'étape 6, la capture de l'étape 7.
    9. **Fait le 2026-10-09** (relevés de l'utilisateur) : `/fv poll` rend « modifié à 09:01:46 » (BR1 résolue) ; bande d'une case par pixel lue (« vecteur reconnu », « case de 1 pixel », 2 560 × 1 440, `tests/fixtures/bridge/band_live_1px.bmp`) ; fenêtre : ouverture, fermeture, déplacement, redimensionnement, Échap, position et taille gardées après `/reload` ; raccourci pas encore essayé. Défauts corrigés le même jour : aide affichée deux fois, fond trop transparent (opaque par défaut, `/fv fond N`), `/fv diag` sans rien de visible (la fenêtre couvrait sans doute la discussion : il confirme désormais son passage dans la fenêtre et y montre une erreur Lua ; `/console scriptErrors 1` affiche les erreurs Lua du jeu).
11. **Procédure du chat** (P06a, fin de tranche, **à jouer avant le 2026-10-21**, non bloquante pour la fusion) :
    1. Jeu fermé : `uv run forever bridge install` (réserve de 200 emplacements `ForeverBridge_S001`…`S200`, liste
       des addons plus longue : c'est attendu) ; relancer le jeu.
    2. `uv run forever bridge start` ; `/fv` : voyant vert après le premier relevé, ligne d'état des données
       (version, fraîcheur, attentes), boutons visibles selon la classe (Mage : Talents, Leveling, PvP ; Chasseur : Talents,
       Familiers, PvP).
    3. Question tapée (« Which talent should I take next? » ou en français), Entrée : bande visible quelques secondes
       en haut à gauche, retirée dès l'accusé ; « en cours » animé ; réponse courte mise en forme avec sa ligne de
       provenance ; journal du pont relu (`<cache>/bridge/journal/`).
    4. Maj+Entrée passe à la ligne ; question de suite : même session (journal) ; « Nouvelle conversation » puis
       une question : nouvelle session.
    5. Bouton Talents (Mage) : réponse avec `[Talents Forever]` ; clic : zone copiable, Ctrl+C, collé dans Talents
       Forever (`/tf`). Bouton Talents sur un personnage d'une autre classe : build populaire le plus proche, son lien,
       et la ligne « pas encore calculé par le moteur de forever ». Bouton PvP avec un joueur en cible ; Familiers sur
       un Chasseur si possible.
    6. Fenêtre fermée pendant une réponse : elle ne s'ouvre pas seule (voyant et compteur) ; rien dans la discussion
       générale.
    7. `uv run forever bridge stop`, question : après trois relevés, « pont injoignable », bande retirée ; `uv run
       forever bridge start`, `/reload` : réponse récupérée par la boîte d'envoi.
    8. Réserve : la ligne d'état donne les emplacements restants ; à 10, `/reload` est proposé (jamais fait seul).
    9. ForeverLogger toujours actif (`/reload` puis `forever logs scan`).

12. **Sonde en jeu C du pont** (P06a, fin du bloc B, **avant l'étape 11**). Elle dit si une question tapée dans la
    fenêtre part avec le bon contexte du personnage et si le pont la lit. Aucune réponse en jeu avant le bloc E.
    1. **Jeu fermé.** `uv run forever bridge install` : ForeverBridge à jour et réserve de 200 emplacements
       (`ForeverBridge_S001`…`S200`, liste des addons plus longue : c'est attendu). Relancer le jeu ; noter si le
       chargement paraît plus long qu'avant (question BR3).
    2. `/fv` : la fenêtre a sa zone de saisie, « Envoyer » et « Nouvelle conversation » ; fond opaque (`/fv fond 80`
       pour l'essayer, `/fv fond 100` pour revenir) ; aucun bouton de la barre tant que le pont n'a rien écrit
       (attendu). Assigner le raccourci (Options > Raccourcis > AddOns > ForeverBridge) et l'essayer.
    3. Dans le terminal : `uv run forever bridge selftest --live --message`, puis revenir au jeu dans la minute.
    4. Taper une question en français (par exemple « Quel talent dois-je prendre après Improved Frostbolt ? ») ;
       Maj+Entrée passe à la ligne, Entrée envoie. Petite bande en haut à gauche pendant au plus 30 s ; la fenêtre
       affiche « Vous : … » et « message n° … envoyé ».
    5. Sortie attendue du terminal : « message n° … lu », « case de 1 pixel », « emplacement annoncé : 1 »,
       « contexte : name, realm, level, class, race, faction, zone, subzone, map, talents, gear, client » (`target`
       en plus avec un joueur en cible) et le texte exact, accents compris.
    6. « Nouvelle conversation », puis une autre question avec `selftest --live --message` relancé : drapeaux « n ».
    7. `/fv diag` : la fenêtre confirme « résultats écrits dans la discussion générale » ; sinon noter la ligne
       « /fv diag en erreur » (`/console scriptErrors 1` montre aussi les erreurs Lua du jeu).
    8. Relevé : la sortie du terminal des étapes 5 et 6, ce qui ne va pas aux étapes 2 et 7.

### Protocole de collecte (mesures pour le registre)
- **Les plus rentables, à faire d'abord** (pistes du 2026-10-01, `tasks/pistes-open-questions-2026-10-01.md` ; chaque résultat est une mesure, source primaire) :
    1. **E2, pénalité des sorts de bas niveau (G4, T04e)** : Frostbolt **rang 1** sur un monstre gris, sans talent de dégâts, personnage de niveau 8 ou plus, base 20-22. **Deux séries d'une dizaine de coups non critiques à deux puissances des sorts éloignées** (S1 et S2, au moins 30 d'écart, lues dans le bloc avancé de `SPELL_CAST_SUCCESS`) : la pente (moyenne à S2 − moyenne à S1) / (S2 − S1) vaut 0,407 sans pénalité et 0,163 si le serveur la réapplique. Le coefficient du client (0,407) ne tranche pas : il est brut, la pénalité de Classic est appliquée par le serveur. Contrôle à une seule puissance : à 14 de puissance des sorts, 25,6-27,8 contre 22,2-24,4 (sans recouvrement).
    2. **E4, coefficient d'Ice Lance (T04e)** : sur cible **non gelée**, deux séries à au moins 30 de puissance des sorts d'écart : + 4,3 par coup attendu avec 0,1429, rien avec 0. Un seul coup au-dessus du maximum de base (× talents) réfute 0.
    3. **A18, Ignite** : leveling ou mannequin au Fireball avec Ignite pris, ForeverLogger installé (rangs de talents) ; relever des paires de critiques de feu à moins de 4 s l'une de l'autre et des critiques isolés ; pour chacun, montants et instants des tics de 412538 jusqu'à la fin de l'aura (le compteur repart-il au second critique ?) ; `forever measures refresh` relève les épisodes et les compare à la règle des données et à la variante (écart affiché, jamais écrit au registre).
    4. **B7, régénération pendant la règle des 5 s** (bascule du build de donjon au niveau 40, `docs/research/builds-T05.md`) : mana gagnée pendant une incantation continue de 30 s environ, sans consommable, dans **quatre** cas : sans rien, Arcane Meditation seule, Mage Armor seule, les deux à la fois. Les deux ensemble donnent la somme des deux parts (modèle, `mana.regen_stacking` = `sum`) ou la plus grande seulement (`max`). ForeverLogger installé (talents), journal de combat actif (`SPELL_ENERGIZE` absent : régénération lue par la différence de mana entre deux lancers). Le bonus d'armure de Frost et Ice Armor n'est pas modélisé.
    5. **Critique des sorts × 1,5 et tics de DoT critiques** (`leveling.json` `combat_rules.crit_mult_spell`, `dot_can_crit`, `suppose`) : au moins 100 critiques de Frostbolt (rapport critique / non critique à puissance des sorts connue), et les tics de Fireball, Pyroblast et Ignite d'une session de Mage (un tic critique existe-t-il ?) ; `forever logs measure`.
    - **Ratios encore estimés** (ForeverLogger, hors combat) : critique de base des sorts par `GetSpellCritChance` à Intelligence connue (déjà relevée une fois, Jen niveau 19, `tests/fixtures/observations/jen_niveau_19.json`) ; mana par point d'Intelligence par `UnitPowerMax` à **deux** valeurs d'Intelligence (une pièce d'équipement changée) ; PV par point d'Endurance par `UnitHealthMax` à deux valeurs d'Endurance.
- **Prioritaire aussi (sensibilité de T05)** :
    - **H11, PV des monstres de donjon vers le niveau 20** (bascule du build de donjon au niveau 20) : journaux de combat de donjons de niveau 18 à 22 environ, monstres normaux et boss tués entiers par le groupe ; `uv run forever monsters build --logs <dossier> --questie <addon Questie>` puis `uv run forever measures refresh` : les PV mesurés remplacent l'extrapolation (Questie corrigé) aux niveaux concernés.
- **B1** (recharge globale) : sur un mannequin ou des monstres faciles, 50 sorts instantanés enchaînés sans pause → intervalles minimaux ; `tolerance.n_min` de B1 dans le registre.
- **A3** (raté des sorts selon l'écart de niveau) : leveling ordinaire au Frostbolt, ForeverLogger installé (niveau du lanceur) ; il faut plusieurs centaines de lancers par écart de niveau pour distinguer des taux voisins ; noter les talents de toucher (instantané de l'addon).
- **H1** (niveau d'un boss) : un boss de donjon → niveau lu dans le bloc avancé du journal.
- **Monstres** : tout journal de leveling enrichit la table (`uv run forever monsters build --logs <dossier> --questie <addon Questie>`) ; `uv run forever measures refresh` relance toutes les mesures et n'écrit qu'après accord.
- **B11** : coût d'Arcane Blast à chaque cumul (1 + 1,75 n supposé additif) et effet de Clearcasting sur le cumul.
- **I7** : couleur des quêtes au niveau du personnage (vertes les plus basses), à comparer à `leveling.quest_band`.
- **Pyroblast r1 (E3, T04e)** : tic = 11 + 0,15 × puissance des sorts (× talents) ; à 20 de puissance des sorts, 14 au lieu de 11 ; un tic toutes les 3 s (4 tics).
- **Cumul des bonus (E6, T04e)**, journaux ordinaires : Arcane Missiles sous Arcane Power avec 4 cumuls d'Arcane Blast, contre Arcane Power seul : rapport 1,40 (multiplicatif) contre 1,31 (additif). Talent Arcane Power requis.
- **Bornes de dégâts (E7, T04e)** : arrondi au demi supérieur ou troncature ? Choisir un rang dont les bornes diffèrent entre les deux règles (points × (1 ∓ variance / 2) de `spell_scaling.json` à partie décimale ≥ 0,5 ; au niveau 60 : Ice Lance r6, maximum 161 arrondi ou 160 tronqué ; Arcane Explosion r6, minimum 239 ou 238). Au moins 50 coups non critiques à puissance des sorts connue S (bloc avancé de `SPELL_CAST_SUCCESS`), talents de dégâts notés (instantané de l'addon) : relever le minimum et le maximum observés ; bornes attendues (min + coefficient × S) × talents et (max + coefficient × S) × talents sous chaque règle ; un coup hors des bornes d'une règle la réfute.
- **Improved Cone of Cold (T04e)** : Cone of Cold avec le talent à **1/3** (× 1,12 attendu, courbe du client retenue par la décision 77 ; × 1,15 réfuterait la courbe au profit des valeurs Classic), coups non critiques à puissance des sorts connue, comparés aux mêmes coups sans le talent.
- **Blizzard (T04e)** : tics de Blizzard (sans variance) à deux niveaux de puissance des sorts : écart par tic de 0,042 × Δ (sort déclenché) ou 0,03 × Δ (effet factice du parent).

### Sondes `/dump` à faire en jeu (pistes du 2026-10-01, section D)
Signalées par un wiki de fans (warcraft.wiki.gg), qui n'est pas une source : rien n'est tenu pour établi avant la sonde. Chaque sonde se fait hors combat, puis en combat, avec `/dump issecretvalue(<expression>)` à côté de la valeur.
- `/dump C_ClassTalents.GetActiveConfigID()`, puis `/dump C_Traits.GetNodeInfo(<config>, <nœud>)` (champ `ranksPurchased`). Déjà lus hors combat par ForeverLogger : la sauvegarde du poste porte les rangs par nœud (instantanés du 2026-09-28 au 2026-10-02). Reste en combat.
- `/dump GetSpellBonusDamage(<école>)` et `/dump GetSpellCritChance(<école>)`. Déjà lus hors combat par ForeverLogger (six écoles, même sauvegarde ; critique recoupée avec la fiche de Jen). Restent les valeurs secrètes en combat ou en champ de bataille.
- `/dump UnitQuestTrivialLevelRange("player")` à plusieurs niveaux, comparé à la couleur des quêtes du journal : remplacerait l'émulation de `GetQuestGreenRange` (I7).
- `/dump UnitClass("target")` et `/dump UnitClassFromGUID(UnitGUID("target"))` sur un joueur adverse **en champ de bataille** : classe lisible et non secrète ? (fiche fixe de FA1).
- `/dump UnitHealthMax("target")` sur un PNJ, hors combat puis en combat (marquée `SecretWhenUnitHealthMaxRestricted` selon le wiki). ForeverLogger lit déjà `UnitHealthMax("pet")` (familier), pas un PNJ.
- Addons (pas de `/dump`) : Auctionator (prise en charge de Forever annoncée à partir de ses versions 337 à 339) et MobInfo2 (version Forever 1.60.1) : relever la version installée, puis lire leurs SavedVariables sur disque ; pour MobInfo2, vérifier si des PV absolus y figurent.
- SavedVariables : la sauvegarde de ForeverLogger du poste garde des instantanés du 2026-09-28 au 2026-10-02 dans un fichier écrit le 2026-10-02 (builds 70009 à 70170) : elles sont relues d'une session à l'autre. À confirmer par un réglage qui survit à un redémarrage complet du client.
- Produit TACT : `.build.info` du client installé indique `wow_classic_beta` (1.60.1.70170, lu sur disque le 2026-10-02) ; le produit du lancement reste inconnu.

## 8. Checklist à chaque build
Pont ForeverBridge : `/fv test` et `uv run forever bridge selftest --live` (case d'un pixel), une question dans la fenêtre `/fv` (réponse sans `/reload`), puis `/fv diag` (section 7, étapes 10 et 11). Régénérer la référence d'API Forever ; relancer une sonde (`/dump` des API clés : `C_Traits`, `issecretvalue`, `GetSpellBonusDamage`) ; `uv run python scripts/check_addon.py` ; vérifier le numéro d'interface et le suffixe du `.toc` ; vérifier l'en-tête du journal (`COMBAT_LOG_VERSION`, bloc avancé à 19 champs).

## 9. Feuille de route des addons de forever-core
Ordre revu le 2026-10-07 (décisions 193 et 202, `docs/VISION.md`) : nos addons n'affichent que ce qu'aucun addon installé ne sait recevoir ; le reste passe par les points d'import des addons de la communauté (décision 196).
- **ForeverLogger** : relevés hors combat (profil, familier, observations de DJ1, auras de bonus d'XP de T04f).
- **ForeverBridge**, pont de conversation (**P06a**, juste après FA1, à jouer avant la fin de la bêta ; décisions 194, 197 et 212) : addon dédié, seul à dessiner (ForeverLogger ne dessine jamais rien), avec sa réserve d'emplacements `ForeverBridge_S01`… ; recodé dans ce dépôt en reprenant la technique de wow-ai (rapport section 3.5 ; licence MIT vérifiée au plan, mention de licence gardée dans chaque fichier repris et crédits ici), sans faire tourner wow-ai ni NeverQuestAlone. Bande de pixels seulement quand un message attend, réponses par une réserve d'addons chargés à la demande, secours `/reload` ; Claude Code non interactif, conversation « jeu » limitée aux outils forever ; contexte du personnage envoyé à chaque message (reprend l'ancienne V2) ; état des données visible. Aucune action de jeu ; fragile à chaque build (checklist de la section 8 à étendre au plan).
- **Boutons en jeu** (**P06b**) : une question prédéfinie par bouton, visible seulement quand sa tranche est faite ; Valider et Refuser des attentes de `forever update` (commandes fixées lancées par le pont) ; fiche PvP fixe de la cible (reprend FA1p) ; analyse du dernier combat après AN1 et AN2 (reprend V3, FA3) ; liens d'export.
- **Exports** (décision 196) : Talents Forever (FA1), Naowh Forever (BiS et poids en T10a, macros en EX1), EllesmereUI (profils et objet LibDataBroker en EX1).
- **Retiré** : la comparaison de l'équipement dans l'infobulle (ancienne V1 de ForeverAssist), que Naowh Forever et GearQuest Forever font déjà ; l'équipement passe par l'export vers Naowh Forever (T10a).

