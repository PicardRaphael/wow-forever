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
| jeu ↔ forever (P06a) | Pont : bande de pixels lue par `forever bridge` (aller, de l'envoi à l'accusé), réserve d'addons chargés à la demande consultée à intervalles (retour ; aucun son : un fichier son vide « joue » sur Forever), secours `/reload` | quelques secondes | **Livré** (P06a, décisions 194, 197 et 212) |
| jeu ↔ forever (P06b) | Même pont : messages en parties (carrousel), liens Maj+clic et infobulles, export `/simc` collé, actions `a=` (Mettre à jour, Valider, Refuser, profil) traitées par le pont sans le modèle, cartes « À valider », conversation « addons » | quelques secondes (export : une dizaine) | **Livré** (P06b, décision 235) |
| forever → addons tiers | Chaînes d'import collées par le joueur (Talents Forever, Naowh Forever, EllesmereUI) | action humaine | **Prévu** (FA1, T10a, EX1, T10 ; décision 196) |
| à éviter | Journal de discussion (écrit à la sortie, ignore les `print` d'addon) ; pixels et lecture d'écran hors du pont de P06a | — | Non |

## 6. Contrat de données
- **ForeverLoggerDB** (retour, schéma 1) : par GUID, instantanés `{reason, time, localtime, level, talents, spell_bonus, spell_crit}` à la connexion, au gain de niveau et au changement de talents ; gains d'expérience `{time, localtime, level, text}` ; depuis CH0 (0.3.0), hors combat seulement, instantanés du familier et des statistiques du Chasseur au même instant (`pet_snapshots`, sur `UNIT_PET`, `PET_UI_UPDATE`, à la connexion, repris à `PLAYER_REGEN_ENABLED` s'ils tombaient en combat) et relevés de la fenêtre Beast Training (`training`, sur `CRAFT_SHOW` et `CRAFT_UPDATE`). [Supposé] API des familiers de Classic (`GetPetTrainingPoints`, `GetPetFoodTypes`, `GetPetLoyalty`, `GetCraftInfo`…) présentes sur Forever : toutes sous `pcall`, champ absent sinon. **T04d (0.4.0, schéma 2)** : chaque gain d'XP garde `seq`, montant, type (`monster`, `other`), monstre, cible (`target` : nom, niveau, classification, PNJ, type, source `target` | `nameplate` | `recent`) ou niveaux vus (`seen_levels`), état de l'XP et du repos au moment du message (`state` : `xp`, `max`, `rested`, `rest_state`), `resting`, `instance`, `group` (taille, raid, niveaux des membres), `map` ; `xp_states` (connexion, niveau, `PLAYER_XP_UPDATE`, changements du repos) ; `quests` (`accepted` et `turned_in` : ID, titre, niveau de la quête, `xp_reward`, `money_reward`, état, carte) ; instantanés avec `trivial_range` (`UnitQuestTrivialLevelRange`) et état ; `errors` (erreurs des gestionnaires comptées par événement) ; `/flog` affiche le résumé de la session. Détail : `addon/README.md`. Lecture : `forever/pipeline/addon_sv.py` ; jointure avec un journal par GUID et heure locale (`forever logs measure <journal> --addon-sv <fichier>`). **T04f (0.5.0, schéma 3)** : chaque gain d'XP et chaque `xp_states` gardent `auras` (auras utiles du joueur : `spell`, `stacks`, `remaining` en secondes, absent sans fin ; au plus 16 parmi les 40 premières, `C_UnitAuras.GetAuraDataByIndex` sous `pcall`) ; `legacy` (`trees` : arbre → nœud → rang acheté, `time`) lu hors combat à la connexion, au changement de talents et à la sortie du combat, pour les arbres que ForeverBridge écrit dans `ForeverBridgeStatus.xp.legacy_trees` (identifiants lus dans `xp_bonuses.json`, jamais écrits dans le Lua) ; API `C_Traits.GetConfigIDByTreeID` supposée présente sur Forever, champ absent sinon. **ForeverBridge 0.2.0** : contexte enrichi de `rested` (`GetXPExhaustion`), `resting` (`IsResting`), `xp_auras` (« sort:cumuls:secondes restantes », filtrées par `ForeverBridgeStatus.xp.auras`) et `xp_items` (« objet:nombre », `C_Item.GetItemCount` sur `ForeverBridgeStatus.xp.items`) ; lus par `forever/bridge/context.py` (`xp_context`). Relevé facultatif (LVL12, LVL13, décision 247) : en jouant, une séance avec puis sans le sac de couchage, avec puis sans nourriture nutritive ; `forever xp check` compare.
- **Fichier généré pour ForeverAssist** (aller, V1) : variable `ForeverAssistData` avec `schema`, `build`, `generated_at`, puis les données ; schéma versionné et validé par pytest, `Generated.sample.lua` versionné, `Generated.lua` ignoré par git.

- **ForeverBridgeDB** (retour, schéma 1, ForeverBridge) : `session` (jeton de l'addon), `next_id`, `history` (50
  derniers messages `{role, text, status, provenance, link}`), `waiting` (numéros accusés sans réponse), `outbox`
  (messages sans accusé, `{id, text, flags, slot, context}`, lus par le pont au `/reload`), `window` (position, taille,
  opacité), `cell` (taille de case de la bande).
- **ForeverBridgeSlot** (aller, P06a) : `Inbox.lua` de chaque emplacement `ForeverBridge_S001`… et de `ForeverBridge`,
  écrit par le pont : `{v, now, status = {line, version, freshness, pending, slots, …}, buttons, replies = {{session,
  id, status = "working" | "done" | "error", text, provenance, link}}}` ; `ForeverBridgeStatus` (`Status.lua`) : état
  des données et boutons, relu à la connexion et au `/reload`.
- **P06b, bloc A (décision 235)** :
  - **Message** : drapeaux `a=<action>[:<id>]` (action du jeu, traitée par le pont sans le modèle : liste fermée,
    identifiant apparié exactement à une carte publiée) et `k=simc` (export SimulationCraft collé, sans question) ;
    clé de contexte `links` (par lien, séparés par 0x1D : corps, nom, lignes de l'infobulle séparées par 0x1C ; 8 liens,
    30 lignes, 120 caractères au plus) ; `gear` en `emplacement=chaîne=nom` (`;` entre les pièces), la chaîne étant le
    corps du lien sans `item:` ni champs vides ou nuls de fin (enchantement, gemmes, suffixe aléatoire, identifiant
    unique) ; l'ancienne forme `emplacement:id:nom` reste lue.
  - **Parties** : un message plus long qu'une bande (1 792 octets) part en parties `F␟session␟numéro␟i␟n␟octets`
    (32 768 octets au plus par message), montrées en carrousel ; le pont publie `{session, id, status = "parts", got,
    total}` et l'addon ne montre plus que les parties manquantes ; abandon (boîte d'envoi) après trois relevés sans
    partie nouvelle, comptés une fois chaque partie montrée au moins une fois. Allègement : noms d'objets coupés, puis
    retirés, puis sous-zone, puis parties ; équipement, talents, liens et question jamais retirés.
  - **Cartes** : `cards = {{id, kind, title, lines, buttons = {{key, label, action, confirm} | {key, label,
    explain}}}}` dans chaque emplacement et dans `Status.lua` ; une action demande un second clic (« Confirmer ») dans
    les cinq secondes, puis part en `a=<action>` ; « Expliquer » pose une question fixe (`b=explain`).
  - **Journal du pont** : l'événement `message` porte le contexte complet (`context`) ; `parts`, `action` et
    `simc_export` (export anonymisé : nom et royaume remplacés sur l'en-tête, la ligne de la classe et `server=`,
    somme de contrôle vérifiée puis recalculée) ; lus par `forever bridge contexts last | export <dossier>`.

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
   0. **Synchroniser l'environnement** quand les dépendances changent : `uv sync`, lancé à la main. Depuis le plugin
      0.8.2 (2026-10-09), le serveur MCP du plugin, celui du pont et les hooks lancent forever par l'interpréteur du
      projet en module (`uv run --no-sync … python -m forever …`), jamais par `.venv/Scripts/forever.exe` : `uv sync`
      n'est plus bloqué par une session Claude Code ouverte ni par le pont. Une seule fois, pour passer à 0.8.2 : fermer
      les sessions Claude Code qui chargent le plugin forever, `uv sync`, puis le script d'installation du plugin
      (`docs/USAGE.md`, « Mise à jour »). Symptôme d'une session restée sur l'ancien plugin : « failed to remove file …
      forever.exe » au `uv sync`.
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
11. **Sonde en jeu E : le chat complet** (P06a, blocs C, D et E ; **à jouer avant le 2026-10-21**). Une vraie
    question, une vraie réponse de l'agent dans la fenêtre, puis le secours `/reload`. Commandes lancées dans un
    terminal à la racine du dépôt, branche `p06a` à jour. Chaque question coûte quelques centimes d'API (Claude Code).
    0. **Avant le jeu** : `uv run forever bridge ask "Quelle est la version des données ?"` (10 à 30 s) : une réponse
       courte suivie de « Données 1.60.1.… · certain ». Une erreur ici (`claude` introuvable, outil refusé, délai) :
       s'arrêter et me donner la sortie.
    1. **Jeu fermé** : `uv run forever bridge install` (met ForeverBridge à jour ; la réserve et ses fichiers déjà
       publiés sont gardés).
    2. **Pont lancé avant le jeu** : `uv run forever bridge start`, puis `uv run forever bridge status` → « Pont : en
       marche », la ligne des données et l'événement `start`. Le pont écrit `Status.lua` à son démarrage : lancé avant
       le jeu, la fenêtre a d'emblée l'état des données et les boutons (sinon, `/reload` une fois le pont lancé).
    3. Lancer le jeu, `/fv` : ligne d'état « Données 1.60.1.… · à jour · pont vu … », voyant vert, boutons selon la
       classe (Mage : Talents, Leveling, PvP ; Chasseur : Talents, Familiers, PvP ; autres : Talents, PvP).
    4. **Première question** (en français), Entrée : petite bande en haut à gauche pendant trois secondes environ,
       puis « réponse en cours… N s » ; la réponse arrive en 10 à 40 s (la première est la plus lente), mise en forme
       (titres en or, puces), suivie de sa ligne de provenance en gris. `uv run forever bridge status` : événements
       `message`, `agent`, `reply`.
    5. **Question de suite** : réponse qui tient compte de la précédente (journal : `"resumed": true`) ; « Nouvelle
       conversation » puis une question : `"resumed": false`.
    6. **Boutons** : Talents sur le Mage → réponse avec `[Talents Forever]` ; clic : zone copiable, Ctrl+C, coller dans
       Talents Forever (`/tf`) ; Leveling ; PvP avec un joueur en cible (sans cible : « prenez un joueur en cible »).
       Talents sur un personnage d'une autre classe, si possible : build populaire de Talents Forever avec son lien et
       la mention « pas encore calculé par le moteur de forever ».
    7. **Fenêtre fermée pendant une réponse** (`/fv` juste après l'envoi) : elle ne se rouvre pas seule ; `/fv` : la
       réponse est là. Rien dans la discussion générale.
    8. **Secours** : `uv run forever bridge stop`, puis une question : au bout d'une dizaine de secondes « Non reçu :
       pont injoignable … gardé pour le prochain /reload », bande retirée. `uv run forever bridge start`, puis
       `/reload` : la réponse arrive dans la fenêtre sans second `/reload` (le pont lit la sauvegarde écrite au
       rechargement, l'addon consulte la réserve).
    9. **Réserve** : la ligne d'état n'en parle qu'à partir de 10 emplacements restants (`/reload` proposé, jamais
       fait seul) ; il en faut environ 3 ou 4 par question.
    10. ForeverLogger toujours actif (`/reload`, puis `uv run forever logs scan`).
    11. **Relevé** : la sortie de l'étape 0 ; pour chaque question, le délai observé et ce qui ne va pas (texte,
        mise en forme, provenance, lien) ; les lignes `uv run forever bridge status` ou le journal du jour
        (`<cache>/bridge/journal/AAAA-MM-JJ.jsonl`, sans aucun pixel) en cas d'erreur.
    12. **Fait le 2026-10-09** (relevés de l'utilisateur) : le chat marche de bout en bout (question, réponse mise en forme, boutons Talents, Leveling et PvP, voyant vert, lien copiable) ; défauts relevés et corrigés le même jour (talents non reconnus, égalités de build, zone copiable, cible, nouvelle conversation, ligne d'état, durée), à rejouer à l'étape 13.

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
    9. **Fait le 2026-10-09** (relevés de l'utilisateur) : fenêtre complète, `/fv fond` ; « message n° 1 lu (576 octets) », « case de 1 pixel », emplacement annoncé 1, contexte attendu (sans `subzone` ni `target` à cet endroit), texte exact ; chargement du jeu pas plus long avec 200 emplacements (BR3) ; `/fv diag` confirmé dans la fenêtre et lignes présentes dans la discussion. Drapeau « n » non rejoué en jeu, couvert par `test_new_conversation_flags_only_the_next_message`.

13. **Sonde en jeu F : retours de la sonde E** (P06a, avant la fusion si possible, sinon non bloquante).
    1. Jeu fermé : `uv run forever bridge install` (Message.lua et ForeverBridge.lua à jour), puis
       `uv run forever bridge config` (attendu : modèle `sonnet`) et `uv run forever bridge start`, avant le jeu.
    2. `/fv` : ligne d'état « Données 1.60.1.70245 · client 1.60.1.70291 : mise à jour en attente · N mises à jour à
       valider sur le PC » tant que les données ne sont pas mises à jour.
    3. Bouton Talents : la réponse cite tes talents actuels (Improved Frostbolt 5/5, Elemental Precision 5/5) ; quand
       le calcul trouve deux builds à égalité statistique, la réponse le dit et donne les deux liens.
    4. Clic sur `[Talents Forever]` : la zone copiable s'ouvre à droite de la fenêtre et se déplace à la souris.
    5. PvP avec un joueur en cible : la réponse reprend son niveau réel (et sa race si le jeu la donne).
    6. « Nouvelle conversation » : la fenêtre se vide, puis une question repart de zéro.
    7. Fenêtre fermée juste après un envoi (`/fv`) : elle ne se rouvre pas ; `/fv` : la réponse est là.
    8. Secours : `uv run forever bridge stop`, question, « Non reçu : pont injoignable » ; `uv run forever bridge start`,
       `/reload` : la réponse arrive sans second `/reload`.
    9. `uv run forever bridge status` : les lignes `reply` portent `timings` (démarrage, chaque outil, fin) et
       `cost_usd` ; me donner ces lignes et le temps ressenti.
14. **Démarrage automatique du pont** (décision 226 ; plus de `forever bridge start` à la main). Sans droits
    administrateur, dans un terminal à la racine du dépôt.
    1. `uv run forever bridge autostart install` : crée la tâche « WoW Forever - pont » (ouverture de ta session
       Windows seulement) et la lance ; `uv run forever bridge autostart status` → « surveillance : en marche »,
       « pont : en marche », aucun problème.
    2. Fermer le terminal, en rouvrir un : `uv run forever bridge status` → « Pont : en marche » (le pont tourne avec
       l'interpréteur réel, plus avec le lanceur de l'environnement qui mourait avec le terminal).
    3. Fermer puis rouvrir la session Windows (ou redémarrer) : `uv run forever bridge autostart status` → pont en
       marche sans rien lancer ; jeu lancé, `/fv` répond.
    4. `uv run forever bridge stop` : le pont s'arrête et n'est pas relancé (« surveillance arrêtée jusqu'à la
       prochaine ouverture de session ») ; `uv run forever bridge start` le relance d'ici là.
    5. Retrait : `uv run forever bridge autostart remove` (le pont en marche continue jusqu'à `stop`).
    Au repos (jeu fermé, ou jeu en arrière-plan ou réduit), le pont ne capture rien ; voir `docs/USAGE.md`, « Chat en
    jeu », pour la mesure de sa consommation.
15. **Mise à jour à la fermeture du jeu** (décision 227 ; plus de `forever update` à la main). Pont en marche.
    1. Lancer le jeu, se connecter, jouer un combat, quitter le jeu.
    2. Une vingtaine de secondes après : `uv run forever bridge status` → lignes `game_closed`, `dbcache_written` et
       `update_launched` dans le journal ; `uv run forever update status` → « en cours » puis le nouveau passage.
    3. Nouveau build du client : après la fermeture, l'attente « correctifs du serveur à lire » se lève seule (le
       passage lit le `DBCache.bin` archivé).
16. **Liste des addons rangée** (décision 228). Les emplacements `ForeverBridge_S001`… et les sondes
    `ForeverBridge_Probe` et `ForeverBridge_Probe2` portent `## Group: ForeverBridge`, comme les modules d'AtlasLoot ou
    de Naowh Forever ; leur chargement à la demande ne change pas.
    1. Jeu fermé : `uv run forever bridge install` (réécrit les `.toc` de la réserve et des sondes, garde les
       `Inbox.lua`), puis `uv run python scripts/install_addon.py --backups-only` → « aucune sauvegarde dans le
       dossier des addons » (les `ForeverLogger.bak-*` sont dans `<cache>/addons/backups/`). Fait sur ce poste le
       2026-10-10.
    2. Lancer le jeu ; à l'écran de sélection des personnages, bouton AddOns : une seule ligne « ForeverBridge »
       repliable à la place de la réserve et des sondes ; dépliée, elle montre les emplacements et les deux sondes
       (chargés à la demande). Aucune ligne `ForeverLogger.bak-…`. Laisser la ligne du groupe cochée.
    3. En jeu : `/fv`, poser une question : la réponse arrive comme avant ; la ligne d'état donne toujours la réserve
       restante. `/fv poll` charge encore la sonde de consultation.
    4. Relevé : capture de la liste des addons (repliée et dépliée) et, si une réponse n'arrive pas, la sortie de
       `uv run forever bridge status`.

17. **Sonde en jeu G : liens, équipement complet, parties, export collé, carte de test** (P06b, bloc A, **avant le
    2026-10-14**). Elle répond à BR5, BR6 et BR7 et fournit les premiers contextes réels avec liens et le premier
    export SimulationCraft réel (fixtures). Dans un terminal PowerShell à la racine du dépôt.
    1. **Jeu fermé.** `git status -sb` : première ligne `## p06b` (le pont tourne sur le code de la branche de la
       tranche). Relancer le pont sur ce code : `uv run forever bridge stop`, puis `uv run forever bridge autostart
       status` jusqu'à « surveillance : arrêtée », puis `schtasks /Run /TN "WoW Forever - pont"`.
    2. `uv run forever bridge status` : « Pont : en marche », une ligne `start` récente, et **aucune** ligne
       « fichiers de l'addon à remplacer » (le pont réinstalle ForeverBridge seul, jeu fermé, en quelques secondes ;
       sinon `uv run forever bridge install`). Puis lancer le jeu et se connecter avec le personnage habituel.
    3. `/fv` : en haut à droite de la fenêtre, le bouton « Coller /simc » ; l'aide (`/fv aide`) cite Maj+clic et
       Coller /simc. `/console scriptErrors 1` pour voir une éventuelle erreur Lua.
    4. **Maj+clic (BR5)** : cliquer dans la zone de saisie de la fenêtre (curseur visible), puis Maj+clic sur : un
       objet d'un sac, un objet équipé (fenêtre du personnage, `C`), un sort du grimoire (`P`), une quête du journal
       (`L`). Pour chacun, noter : lien inséré dans la saisie, rien, ou inséré deux fois, et si une autre fenêtre
       s'ouvre en même temps (partage d'une pile pour un objet empilé). Vider la saisie entre deux essais si besoin.
    5. **Question avec deux liens** : dans la saisie, Maj+clic sur deux objets (un équipé, un d'un sac), puis taper
       autour, par exemple « Lequel de [objet 1] et [objet 2] est le mieux pour moi ? », Entrée. Attendu : « Vous : »
       avec les noms entre crochets ; ligne d'état « envoi du message n° … », éventuellement « (2 parties, … reçue(s)
       par le pont) » ; réponse en une vingtaine de secondes qui s'appuie sur les infobulles.
    6. Dans le terminal : `uv run forever bridge contexts last`. Attendu : « liens cités (2) » avec, sous chaque lien,
       les lignes de son infobulle ; « équipement (N pièce(s)) » avec, par pièce, l'objet, l'enchantement s'il y en a
       un et, pour un objet « of the … » équipé, la ligne « suffixe aléatoire ». Si aucun objet équipé n'a de suffixe,
       le noter (le suffixe sera vérifié plus tard).
    7. **Export SimulationCraft (BR6, BR7)** : `/simc`, le texte de la fenêtre de SimulationCraft est sélectionné :
       Ctrl+C, fermer cette fenêtre. Dans `/fv` : « Coller /simc », clic dans la zone, Ctrl+V (noter si le collage est
       lent), « Envoyer l'export ». Attendu : « Vous : export SimulationCraft (N lignes) », la ligne d'état compte les
       parties reçues par le pont, puis la réponse « Export SimulationCraft reçu (N lignes, somme de contrôle
       juste)… ». Noter le temps entre l'envoi et la réponse. « export trop long : utilisez /simc nobags » ou une
       réponse « export incomplet ou modifié » : recommencer avec `/simc nobags` et le noter.
    8. **Carte de test** : dans le terminal, `uv run forever bridge selftest --card`. En jeu : `/reload`, puis `/fv` :
       bouton « À valider (1) » ; clic : le panneau s'ouvre à droite (« Carte de test du pont », Valider, Refuser).
       Clic sur Valider : il devient « Confirmer » ; attendre une dizaine de secondes : il redevient « Valider ».
       Clic sur Valider puis, dans les cinq secondes, sur Confirmer : « Vous : Valider : Carte de test du pont », puis
       la réponse « Carte de test : « Valider » reçu par le pont ; rien n'est lancé. ». Dans le terminal,
       `uv run forever bridge status --json` : une ligne `action` au résultat « carte de test » ; rien d'autre n'est
       lancé (aucune ligne `update_launched`).
    9. **Relevé** : ce qui s'est passé à chaque étape (4 : par type de lien ; 5 et 7 : délais) ; la sortie de l'étape
       6 ; puis `uv run forever bridge contexts export "$env:TEMP\sonde-g"` et me donner le dossier : les contextes
       et l'export (anonymisé) deviennent les fixtures réelles et les tests de non-régression ajoutés après la
       sonde.
    10. **Fait le 2026-10-10** (relevés de l'utilisateur) : Maj+clic d'un objet d'un sac et d'un objet équipé insérés
        avec leur infobulle complète ; réponse qui lit les infobulles ; export `/simc` « reçu (73 lignes, somme de
        contrôle juste) », gardé anonymisé ; carte de test validée sans rien lancer. Défauts corrigés le même jour :
        objets fabriqués (champ de l'artisan `Player-…` dans le lien) lus comme mal formés ; liens aux couleurs
        nommées de Forever (`|cnIQ2:`) affichés en code brut dans l'historique ; fenêtre de collage non déplaçable
        (barre de titre, position gardée) ; aide de `/fv` à chaque ouverture (une seule fois, puis `/fv aide`).
        Relevés en fixtures : `tests/fixtures/bridge/contexts/mage19_sonde_g*.txt`, `tests/fixtures/simc/
        mage19_sonde_g.txt`. Non vérifiés, repris à la sonde H : Maj+clic d'un sort et d'une quête, partage de pile,
        délai de l'export.

18. **Sonde en jeu H : Mettre à jour, cartes, profil, export lu, Talents d'une autre classe, onglet Addons**
    (P06b, blocs B à G, **avant le 2026-10-19**). Dans un terminal PowerShell à la racine du dépôt.
    1. **Jeu fermé.** `git status -sb` : `## p06b` (ou `## main` après la fusion). Régler la conversation « addons » :
       `uv run forever bridge addons config --source "$env:FOREVER_WOW_DIR\Interface\AddOns\RaphCompletionist"`
       (réponse : « Conversation « addons » : dossier … ») ; `uv run forever bridge config` : « réflexion : on ·
       session gardée ouverte : on » (variante C retenue, décision 237).
    2. Relancer le pont : `uv run forever bridge stop`, `uv run forever bridge autostart status` jusqu'à
       « surveillance : arrêtée », `schtasks /Run /TN "WoW Forever - pont"`, puis `uv run forever bridge status` :
       « Pont : en marche », aucune ligne « fichiers de l'addon à remplacer ». Lancer le jeu.
    3. **Ligne d'état et Mettre à jour** : `/fv` ; la ligne dit `Données … · client … · … · n à valider · m en attente` ;
       l'aide n'apparaît plus d'elle-même (`/fv aide` la montre). Clic sur « Mettre à jour » : réponse « Mise à jour
       lancée » ; la ligne passe à « mise à jour en cours (étape) », puis, une à quelques minutes plus tard, l'historique
       gagne « Mise à jour terminée : n écrit(s), m à valider ». Noter la durée. Pendant un passage, un second clic
       répond « Rien de lancé : passage en cours ».
    4. **Carte d'une vraie attente** : « À valider (n) » ; lire la carte des mesures (PNJ, niveaux de PV, builds) ;
       « Expliquer » : réponse de la conversation « jeu » qui explique la carte. Puis, au choix : Valider (vraie
       approbation : `forever update approve` lance un passage qui peut installer une révision des données) ou Refuser
       (rejet noté « refusé en jeu ») ; chaque bouton demande « Confirmer » dans les cinq secondes. Dans le terminal,
       `uv run forever update status` montre l'état changé. Une attente « réseau » ou « correctifs à lire » n'a que
       « Expliquer ».
    5. **Écart avec le profil** : poser une question quelconque. Profil absent ou différent du jeu : la réponse finit
       par « Écart avec ton profil : voir À valider » et une carte « Créer le personnage … au profil » (ou « Écart avec
       ton profil ») apparaît. Clic sur « Mettre à jour le profil », puis « Confirmer » : « Profil mis à jour … ».
       `uv run forever profile show` : niveau, talents et équipement (source jeu). Une nouvelle question ne signale
       plus d'écart.
    6. **Export lu** : `/simc`, Ctrl+C, « Coller /simc », Ctrl+V, « Envoyer l'export » : « Export SimulationCraft reçu
       (… lignes, somme de contrôle juste) et lu : … objet(s), fiche … », écarts listés (la fiche, au premier envoi),
       note sur l'emplacement 18 ; carte « Mettre à jour le profil » ; après le clic, `uv run forever profile show`
       montre la fiche (source simulationcraft, lue avec les buffs actifs). Noter le délai entre l'envoi et la réponse
       (BR7) et la lenteur éventuelle du collage.
    7. **Talents d'une autre classe** (si un second personnage existe, de préférence avec des talents placés) : bouton
       Talents : la réponse cite le build populaire le plus proche (spécialisation, points absents, commande
       `/tf import`) et le lien `[Talents Forever]` publié est le sien ; sans talent placé : le build le plus joué.
    8. **Onglet « Addons »** : l'onglet « Addons (RaphCompletionist) » est visible ; une petite demande, par exemple
       « Ajoute un commentaire en tête de Core.lua qui dit ce que fait l'addon » ; réponse en une à trois minutes,
       suivie d'une ligne `<commit> · 1 fichier(s)` ; `/reload` : l'addon se charge comme avant (ou ne se charge pas,
       comme avant : `RequiredDeps: RXPGuides`). Dans le terminal : `uv run forever bridge addons log` (le commit),
       puis `uv run forever bridge addons restore` : le fichier revient à la sauvegarde ; `/reload`. L'onglet « Jeu »
       garde son historique à part.
    9. **Repris de la sonde G** : Maj+clic d'un sort du grimoire (`P`) et d'une quête du journal (`L`) dans la
       saisie ; Maj+clic d'un objet empilé d'un sac : la fenêtre de partage de la pile s'ouvre-t-elle aussi (BR5) ?
       Glisser la fenêtre « Coller /simc » par son titre, la fermer, la rouvrir : même place.
    10. **Durée ressentie** des réponses (session gardée ouverte, conversations sans hooks du plugin), comparée à
        celle d'avant : la première question d'une conversation reste la plus lente, les suivantes doivent arriver en
        quelques secondes ; bouton PvP : réponse courte (5 lignes au plus).
    11. **Relevé** : ce qui s'est passé à chaque étape, les durées des étapes 3, 6, 8 et 10, la sortie de
        `uv run forever bridge status`, et `uv run forever bridge contexts export "$env:TEMP\sonde-h"` (dossier à me
        donner).
    12. **Fait le 2026-10-10** (relevé de l'utilisateur) : ligne d'état, cartes, Expliquer, Valider, Mettre à jour
        pendant un passage, création du profil et fiche, export lu (emplacement 18 pris du contexte), onglet Addons
        (commit, journal, restauration), Maj+clic d'un sort et d'une quête, question de suite en 4 s, défilement de
        l'historique. Défauts corrigés (décision 238) : passage bloqué sans fin (rejeu parallèle, délai par étape,
        attente « erreur »), fenêtre de console de `gh`, étape affichée trompeuse, réponse en jargon interne et faute
        de frappe mal lue, petites fenêtres séparées (panneau unique), accents du journal des commits, version observée
        plus ancienne annoncée « plus récente ». Second export en fixture : `tests/fixtures/simc/mage19_sonde_h.txt`.
        Non vérifiés : Talents d'une autre classe, partage de pile (BR5).

19. **Panneau de droite** (P06b, décision 238). Relancer le pont après la fusion (`uv run forever bridge stop`,
    `uv run forever bridge autostart status` jusqu'à « surveillance : arrêtée », `schtasks /Run /TN "WoW Forever -
    pont"`), puis `/reload` en jeu.
    1. `/fv`, « Coller /simc » : le panneau s'ouvre collé à droite de la fenêtre, zone de collage en tête ; second clic
       sur « Coller /simc » : il se ferme.
    2. Bouton Talents, puis clic sur `[Talents Forever]` : la copie du lien apparaît en haut du panneau, texte
       sélectionné ; Ctrl+C, coller dans le navigateur.
    3. « À valider (n) » : les cartes sous les sections ouvertes ; avec plusieurs cartes, molette et barre de
       défilement ; Valider ou Expliquer marchent comme avant.
    4. Déplacer la fenêtre `/fv` : le panneau la suit. Échap : le panneau se ferme, la fenêtre reste.
20. **Avancement de la mise à jour, croix, Masquer** (P06b, décision 240). Pont relancé après la fusion comme au
    point 19 ; l'addon est remplacé à la fermeture suivante du jeu (sinon `uv run forever bridge install`, jeu fermé).
    1. `/fv`, « Mettre à jour » : la réponse dit « Mise à jour lancée. » et la ligne d'état montre aussitôt « Mise à
       jour en cours… lancement · 2 s », points animés et secondes qui défilent ; dans la minute, l'étape en mots
       simples (préparation, mesures de tes combats, vérification des données, attente de la validation sur
       GitHub…) ; à la fin, l'historique gagne « Mise à jour terminée en N min : rien de nouveau » (ou « données
       installées », « en erreur, voir À valider », « une validation t'attend dans À valider »). Un second clic
       pendant le passage répond « Une mise à jour est déjà en cours (étape) : attends sa fin. »
    2. « À valider (n) » : croix en haut à droite du panneau, qui le ferme ; un second clic sur « À valider (n) » le
       ferme aussi.
    3. Chaque carte a « Masquer » : la carte disparaît, le compteur « À valider (n) » et la ligne d'état baissent
       d'autant ; `uv run forever update status` montre toujours l'attente ; `/reload` : la carte reste masquée ; elle
       revient seule quand l'attente change.
    4. Deux attentes de la même branche (écriture bloquée) : une seule carte, textes sans jargon (« Une mise à jour
       attend une correction sur ton PC : ouvre une session Claude »).

21. **Sonde en jeu I : XP des monstres, des quêtes et du repos** (T04d, bloc A, décisions 245 et 246 ;
    **facultative depuis la décision 247** : T04d est finie sans elle ; jouer normalement avec ForeverLogger 0.4.0
    installé suffit, puis `uv run forever xp check` dit ce qui est vérifié et ce qui reste à vérifier). Elle
    dit l'XP réelle de chaque monstre selon son niveau (I6), l'XP réelle des quêtes rendues (`xpReward`, I9, LVL1),
    le bonus des monstres de donjon (LVL5), l'effet du repos (LVL10, D7) et la couleur des quêtes (LVL2).
    Personnages : le Mage orc (niveau 19) et le Chasseur orc (niveau 15). Durée : 1 h 15 à 1 h 30 en tout.
    0. **La veille** : déconnecter le Chasseur dans l'auberge d'Orgrimmar (Valley of Strength) et le Mage dans une
       auberge : le repos s'accumule hors ligne, la barre d'XP sera bleue à la connexion.
    1. **Jeu fermé** : `uv run python scripts/install_addon.py` (ForeverLogger 0.4.0 ; terminal administrateur si
       l'écriture est refusée).
    2. **À la connexion de chaque personnage** : dans la liste des addons, ForeverLogger en 0.4.0 ; taper `/flog` :
       une ligne « XP … / …, repos : … » s'affiche. Noter la couleur de la barre d'XP (bleue : reposé). Si `/flog` ne
       répond pas, s'arrêter et me le dire.
    3. **Règle pour chaque monstre** : le cibler avant de l'attaquer et **garder la cible jusqu'à sa mort** (c'est la
       cible morte qui donne son niveau à l'addon ; à défaut, la plaque de nom). Familier : il peut taper, le
       monstre reste en cible. Après chaque série, `/flog` : « Dernier gain : +N XP (monstre), niveau du monstre L
       (target) ». « niveau du monstre inconnu » : continuer, me le dire.
    4. **Mage, 20 à 30 min, seul, dehors, dans sa zone actuelle** :
       1. Reposé : 5 monstres normaux de son niveau, 5 de 2 à 3 niveaux en dessous, 3 de 1 à 2 niveaux au-dessus.
       2. Tuer des monstres de son niveau jusqu'à ce que `/flog` affiche « repos : aucun » (barre redevenue
          violette) ; au-delà de 15 min, passer à la suite sans attendre.
       3. Non reposé : 5 monstres de son niveau, et 2 monstres gris (5 niveaux ou plus en dessous) si le trajet en
          croise.
       4. Rendre au moins 3 quêtes de couleurs différentes : une jaune, une verte, une grise s'il en reste une.
          Avant chaque rendu, capture d'écran du journal de quêtes (couleur) ; après, `/flog` : « Dernière quête
          rendue : <ID> …, N XP ».
    5. **Chasseur, 20 à 30 min, seul, The Barrens** (autour du Crossroads et sur la côte) : même déroulé que le Mage
       (étapes 4.1 à 4.3), sur des monstres normaux de **niveau 13 et 14** (les niveaux des monstres de Ragefire
       Chasm) : Zhevra Runner, Razormane Mystic, Sunscale Screecher, Venture Co. Drudger, Southsea Cannoneer ; au
       moins 5 de niveau 13 et 5 de niveau 14 **non reposé** ; gris : monstres de Durotar sur le chemin d'Orgrimmar.
    6. **Chasseur, Ragefire Chasm** (non reposé de préférence : faire l'étape 5.2 avant ; entrée dans Orgrimmar,
       Cleft of Shadow) :
       1. Avant d'entrer : prendre **Slaying the Beast** (5761) chez Neeru Fireblade (Orgrimmar, The Drag, 49.5,
          50.6) ; si Thunder Bluff est sur le chemin (vol depuis Orgrimmar ou le Crossroads) : **Testing an Enemy's
          Strength** (5723 : 8 Ragefire Troggs et 8 Ragefire Shamans) et **Searching for the Lost Satchel** (5722 :
          fouiller le corps de Maur Grimtotem dans le donjon, puis 5724 au retour) chez Rahauro (Thunder Bluff, Elder
          Rise, 70.1, 29.5). **Hidden Enemies** (Thrall, Valley of Wisdom) seulement s'il la propose déjà (chaîne de
          trois quêtes). **The Power to Destroy...** (5725, Varimathras, Undercity) : non, trop loin.
       2. Dans le donjon, seul et prudemment (élites dans Questie Classic ; la classification de Forever est relevée
          par l'addon) : Ragefire Troggs et Ragefire Shamans un à un, cible gardée, au moins 5 de niveau 13 et 5 de
          niveau 14, 8 et 8 si possible (objectif de 5723). Noter si le portrait porte le dragon doré (élite). Boss
          (Taragaman, Bazzalan, Jergosh, Oggleflint) seulement en groupe. Fouiller Maur Grimtotem si 5722 est prise.
       3. Sortir et rendre ce qui est fini (5723 et 5724 chez Rahauro, 5761 chez Neeru si Taragaman est mort).
       4. Temps court : faire au moins l'étape 6.2 et les 5 + 5 monstres de même niveau dehors (étape 5).
    7. **Groupe, seulement si l'occasion se présente** (LVL4) : quelques monstres tués en groupe ; l'addon relève la
       taille du groupe et le niveau des membres.
    8. **Fin** : `/reload` (ou déconnexion), fermer le jeu, puis `uv run forever logs scan`. Me donner : date et heures
       de début et de fin de chaque partie (Mage, Chasseur dehors, Ragefire Chasm), les captures du journal de quêtes,
       les monstres vus élites, et tout `/flog` qui a montré « Erreurs relevées » ou « niveau du monstre inconnu ».
       Je lis moi-même `WTF/Account/<COMPTE>/SavedVariables/ForeverLogger.lua` et le journal de combat (lecture
       locale) et en tire des fixtures sans nom ni GUID ; `forever xp check` (bloc G) les compare au modèle.
    9. « Fait le AAAA-MM-JJ (relevés de l'utilisateur) » : règles confirmées, écarts, questions mises à jour.

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
Pont ForeverBridge : `/fv test` et `uv run forever bridge selftest --live` (case d'un pixel), une question dans la fenêtre `/fv` (réponse sans `/reload`), puis `/fv diag` (section 7, étapes 10 et 11). P06b : Maj+clic d'un objet dans la saisie (lien et infobulle, `uv run forever bridge contexts last`), « Coller /simc » (export reçu, somme juste), `uv run forever bridge selftest --card` (Valider, Confirmer, rien de lancé), « Mettre à jour » (section 7, étapes 17 et 18). Régénérer la référence d'API Forever ; relancer une sonde (`/dump` des API clés : `C_Traits`, `issecretvalue`, `GetSpellBonusDamage`) ; `uv run python scripts/check_addon.py` ; vérifier le numéro d'interface et le suffixe du `.toc` ; vérifier l'en-tête du journal (`COMBAT_LOG_VERSION`, bloc avancé à 19 champs).

## 9. Feuille de route des addons de forever-core
Ordre revu le 2026-10-07 (décisions 193 et 202, `docs/VISION.md`) : nos addons n'affichent que ce qu'aucun addon installé ne sait recevoir ; le reste passe par les points d'import des addons de la communauté (décision 196).
- **ForeverLogger** : relevés hors combat (profil, familier, observations de DJ1, auras de bonus d'XP de T04f).
- **ForeverBridge**, pont de conversation (**P06a**, juste après FA1, à jouer avant la fin de la bêta ; décisions 194, 197 et 212) : addon dédié, seul à dessiner (ForeverLogger ne dessine jamais rien), avec sa réserve de 200 emplacements `ForeverBridge_S001`… consultée à intervalles (décision 212 amendée le 2026-10-09) ; recodé dans ce dépôt en reprenant la technique de wow-ai (rapport section 3.5 ; licence MIT vérifiée au plan, mention de licence gardée dans chaque fichier repris et crédits ici), sans faire tourner wow-ai ni NeverQuestAlone. Bande de pixels seulement quand un message attend, réponses par une réserve d'addons chargés à la demande, secours `/reload` ; Claude Code non interactif, conversation « jeu » limitée aux outils forever ; contexte du personnage envoyé à chaque message (reprend l'ancienne V2) ; état des données visible. Aucune action de jeu ; fragile à chaque build (checklist de la section 8 à étendre au plan).
- **Boutons en jeu** (**P06b**) : une question prédéfinie par bouton, visible seulement quand sa tranche est faite ; Valider et Refuser des attentes de `forever update` (commandes fixées lancées par le pont) ; fiche PvP fixe de la cible (reprend FA1p) ; analyse du dernier combat après AN1 et AN2 (reprend V3, FA3) ; liens d'export.
- **Exports** (décision 196) : Talents Forever (FA1), Naowh Forever (BiS et poids en T10a, macros en EX1), EllesmereUI (profils et objet LibDataBroker en EX1).
- **Retiré** : la comparaison de l'équipement dans l'infobulle (ancienne V1 de ForeverAssist), que Naowh Forever et GearQuest Forever font déjà ; l'équipement passe par l'export vers Naowh Forever (T10a).

## 10. Crédits

Le pont de P06a reprend la technique de **wow-ai** (https://github.com/chelinho139/wow-ai, chelinho139/wow-ai, commit
3756eb5a du 2026-09-27, **licence MIT** vérifiée le 2026-10-08) et une partie de son code : codec de la bande, dessin
à l'échelle physique, capture de la zone client, format des messages, réserve d'emplacements chargés à la demande et
leur installation, cadre de la fenêtre. Chaque fichier repris porte la notice MIT complète en tête (liste fermée,
contrôlée par `tests/unit/test_bridge_license.py`) : `forever/bridge/codec.py`, `capture.py`, `record.py`,
`slots.py`, `install.py`, `addon/ForeverBridge/Codec.lua`, `ForeverBridge.lua`. Mesures du client citées sans reprise
de code : wow-forever-codex (0xinuarashi, dépôt sans licence, lu le 2026-10-09 : fichiers vus au lancement seulement,
canal par mesures de polices, piste de P06b).
