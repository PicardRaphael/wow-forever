# P06a — Chat en jeu : question, réponse, état des données : plan

Tranche de `docs/ROADMAP.md` (section P06a), premier pari de `docs/VISION.md`, décisions 193, 194, 197 et 202.
Objectif de l'utilisateur : poser une question en jeu et recevoir la réponse de son agent en jeu **avant la fin de la
bêta, le 2026-10-21**. Plan écrit le 2026-10-08 ; aucun code ici.

## Réponses de l'utilisateur (2026-10-08)

1. **Réseau** : lecture seule de `chelinho139/wow-ai` accordée (licence, arbre, code ; rien exécuté). Recherches web
   en lecture seule accordées pendant toute la tranche pour le Lua des addons (dépôts GitHub d'addons, documentation de
   l'API sur warcraft.wiki.gg), sources citées.
2. **Addon dédié `ForeverBridge`** : l'exception des pixels (décision 194) reste confinée à l'addon du pont ;
   ForeverLogger ne dessine jamais rien ; couper le pont ne coupe pas les relevés ; chaque addon garde sa sauvegarde.
3. **Sonde du marqueur** : le pont lit à intervalle fixe les seuls pixels du marqueur (cinq cellules dans le rectangle
   de la bande, dans la fenêtre du jeu) et ne lit la bande entière que si le marqueur est présent ; rien de la sonde
   n'est gardé ni journalisé.
4. **Liens Maj+clic et écart avec le profil (décision 122) : reportés en P06b**, comme la conversation « addons »
   (demande de lancement de la tranche).
5. **`lupa` en dépendance de développement seulement, moteur Lua 5.1** (`lupa.lua51`, celui de WoW), pour exécuter
   le vrai Lua de l'addon dans les tests ; aucune dépendance d'exécution ni réseau ajoutée à forever.
6. **Skill de développement** dans `.claude/skills/` si le savoir-faire Lua et addons sert à plusieurs tranches
   (P06a, P06b, EX1) : oui, il y sert (contenu prévu plus bas, étape 0.3).

## Constat du plan

### wow-ai (lu le 2026-10-08)
- Dépôt `https://github.com/chelinho139/wow-ai`, commit `3756eb5a5e7858bf9e38786bc89f889a523dd55e` du 2026-09-27,
  non dérivé d'un autre dépôt. **Licence MIT vérifiée** (`LICENSE` : « Copyright (c) 2026 chelinho139 »).
- Architecture (`docs/ARCHITECTURE.md` du dépôt) : addon `WoWAI` (Lua, un fichier de 3 153 lignes, codec à part),
  programme compagnon Node (`bridge.js`, `protocol.js`, `agents.js`) et capture PowerShell (`capture.ps1`, GDI
  `CopyFromScreen` du coin haut gauche de la zone client, 800 × 192 px toutes les 250 ms).
- **Faits du client mesurés par wow-ai et wow-forever-codex** (à revérifier en jeu, procédure plus bas) :
  1. seuls les fichiers présents **au lancement du client** sont vus (addons, sons) ; un fichier déjà lu reste en
     cache pour tout le processus, même après `/reload`, sauf le **code Lua des addons**, relu au `/reload` et au
     `LoadAddOn` ;
  2. `PlaySoundFile` rend « jouera » pour un `.wav` valide, « ne jouera pas » pour un fichier vide : un `.wav` vide
     préinstallé que le pont remplit devient un **drapeau** lisible gratuitement ; un drapeau levé le reste jusqu'à la
     fermeture du client ;
  3. un addon `LoadOnDemand` se charge une fois par session d'interface (`/reload` les décharge tous) et lit son
     `.lua` sur le disque au chargement ;
  4. `ReloadUI()` exige un événement matériel ; wow-ai le déclenche par un cadre qui capte le clavier (**non repris**).
- Codec (`addon/WoWAI/Codec.lua`, 67 lignes, Lua arithmétique pur, sans `bit`) : octets
  `[C7 1A] [id fort, faible] [longueur forte, faible] [charge] [Fletcher-16 s1, s2]`, somme sur id…charge, octets
  découpés en cellules de 3 bits (bit 2 = R, 1 = G, 0 = B), chaque canal tout allumé ou tout éteint (8 couleurs,
  résistantes au gamma), cellule de 4 × 4 px, 200 cellules par rangée ; cadre à l'échelle `768 / hauteur physique`
  pour qu'une unité d'interface fasse un pixel.
- Ce qu'on **reprend** (portage, notice MIT dans chaque fichier repris) : le codec (Lua et décodeur en Python porté
  de `capture.ps1`), le dessin de la bande à l'échelle physique, le drapeau sonore et son autotest (`ctl/empty.wav`,
  `ctl/valid.wav`), le WAV silencieux de 124 octets, la réserve d'emplacements écrite en entier à chaque publication,
  l'accusé de réception (`ack/NN.wav`) qui retire la bande, la boîte d'envoi `/reload`. Ce qu'on **ne reprend pas** :
  plusieurs conversations et agents, dossiers de travail, ajout de règles d'autorisation depuis le jeu (« Allow »),
  macros, carte, battements de présence et d'activité, restauration après effacement des SavedVariables, capte-clavier
  et `ReloadUI` automatique, `/r` détourné dans le chat du jeu.

### forever-core
- `forever.spawn.spawn_detached(args, log_path)` : relais qui coupe la filiation (le passage survit à son lanceur) ;
  `pid_alive(pid)` sans `os.kill` sous Windows.
- `forever.status.status_report(deps, allow_network=False)` et `forever.update.update_summary(cache_dir, now)` :
  version, fraîcheur, intégrité, couverture du registre, attentes, passage en cours (lus **dans le processus du pont**,
  jamais par le modèle ni par un sous-processus).
- `forever.pipeline.live_logs.client_executables(wow_dir)` : exécutables du client (pour trouver la fenêtre).
- `forever.pipeline.lua_table.parse_lua_assignments` : lecture des SavedVariables sans exécuter de Lua.
- `scripts/check_addon.py` : câblé sur `ForeverLoggerDB` ; `FORBIDDEN` sans `CreateMacro` (pourtant interdit par
  `CLAUDE.md`).
- `tests/unit/test_network_boundary.py::test_subprocess_only_in_gitops_and_the_detached_launch` : ensemble exact des
  modules qui importent `subprocess` ; le lanceur de `claude` y entre (phase rouge).
- Plugin : serveur MCP `forever` (six outils : `forever_status`, `forever_lookup`, `forever_player_profile`,
  `forever_explain_mechanic`, `forever_sim_leveling`, `forever_build`, tous en lecture) ; hook `SessionStart`
  (`forever hook session-start` : archivage des fichiers du client et lancement détaché de `forever update` si dû) ;
  hook `Stop` (`forever hook check-numbers`, contrôle des chiffres non sourcés).
- `claude` 2.1.294 : `-p`, `--output-format stream-json --verbose`, `--resume <id>`, `--tools ""` (aucun outil
  intégré), `--allowedTools`, `--permission-mode dontAsk`, `--permission-prompts none`, `--plugin-dir`,
  `--mcp-config`, `--strict-mcp-config`, `--append-system-prompt`, `--system-prompt-snapshot` (**`on` par défaut** :
  le prompt système est figé à la première requête d'une conversation et réutilisé à chaque reprise), `--model`.

### API du client (recherche du 2026-10-08, sources)
Certitude : **wiki** = page API de warcraft.wiki.gg (référence de la communauté, signatures fiables, comportement
parfois daté) ; **wow-ai** = mesuré par wow-ai sur Forever, non revérifié ; **forum** = source unique.
- `PlaySoundFile(sound [, channel])` rend `willPlay, soundHandle` ; `StopSound(handle)` existe sur Forever ; non
  protégée. **Formats documentés : `.ogg` et `.mp3`** ; wow-ai utilise des `.wav` sur Forever et dit l'avoir mesuré ;
  un fil de forum signale `willPlay` vrai pour un fichier absent. D'où l'**autotest obligatoire** (`ctl/empty`,
  `ctl/valid`) avant de se fier aux drapeaux, et le relevé de la réserve à horaire fixe en repli. Format des drapeaux
  (`.wav` de wow-ai ou `.ogg`) tranché par la sonde en jeu A (`/fv diag` essaie les deux). (wiki :
  https://warcraft.wiki.gg/wiki/API_PlaySoundFile, https://warcraft.wiki.gg/wiki/API_StopSound ; forum :
  https://www.wowinterface.com/forums/showthread.php?p=298900)
- `C_AddOns.LoadAddOn(name)` rend `loaded, reason` (`MISSING`, `DISABLED`, `DEMAND_LOADED`, `INTERFACE_VERSION`,
  `DEP_*`…) ; un second appel sur un addon chargé rend vrai sans relire son Lua ; ne pas l'appeler dans le
  gestionnaire d'`ADDON_LOADED` (l'addon chargé perdrait le sien) ; `C_AddOns.IsAddOnLoaded` ; `## LoadOnDemand: 1`.
  (wiki : https://warcraft.wiki.gg/wiki/API_C_AddOns.LoadAddOn, https://warcraft.wiki.gg/wiki/API_C_AddOns.IsAddOnLoaded,
  https://warcraft.wiki.gg/wiki/TOC_format)
- Fichiers ajoutés pendant que le client tourne : le wiki se contredit (TOC_format : vus au `/reload` ; ReloadUI :
  redémarrage nécessaire) et wow-ai a mesuré qu'il faut redémarrer pour les sons. **Règle retenue : installation puis
  redémarrage complet du client**, à reconfirmer en jeu. (wiki : https://warcraft.wiki.gg/wiki/TOC_format,
  https://warcraft.wiki.gg/wiki/API_ReloadUI)
- Pixel parfait : `GetPhysicalScreenSize()` ; `PixelUtil.GetPixelToUIUnitFactor()` vaut `768 / hauteur physique` dans
  le code de Blizzard ; `Region:SetIgnoreParentScale` restreinte en combat sur un cadre **protégé** (le nôtre ne l'est
  pas ; appel fait une fois à la création, hors combat) ; `SetColorTexture` présente sur Forever 1.60.1. (wiki :
  https://warcraft.wiki.gg/wiki/API_GetPhysicalScreenSize, https://warcraft.wiki.gg/wiki/API_Region_SetIgnoreParentScale,
  https://warcraft.wiki.gg/wiki/API_TextureBase_SetColorTexture ; code de Blizzard :
  https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_SharedXML/PixelUtil.lua)
- `ReloadUI()` (alias `C_UI.Reload`) : restreinte, exige un événement matériel ; `/reload` tapé par le joueur
  convient. (wiki : https://warcraft.wiki.gg/wiki/API_ReloadUI)
- Contexte : `C_ClassTalents.GetActiveConfigID`, `C_Traits.GetConfigInfo` / `GetTreeNodes` / `GetNodeInfo`
  (`ranksPurchased`, hors rangs accordés d'office), `GetInventoryItemLink`, `C_Map.GetBestMapForUnit`,
  `GetRealZoneText`, `GetSubZoneText`, `UnitClass`, `UnitRace`, `UnitLevel` listées pour Forever 1.60.1 ;
  `UnitClass` et `UnitRace` peuvent être secrètes (`SecretWhenUnitIdentityRestricted`), supposées lisibles pour
  `"player"` hors combat : chacune sous `pcall` et `issecretvalue`, clé absente sinon. (wiki :
  https://warcraft.wiki.gg/wiki/API_C_Traits.GetNodeInfo, https://warcraft.wiki.gg/wiki/API_UnitClass,
  https://warcraft.wiki.gg/wiki/Secret_Values)
- Liens (pour P06b) : `C_TooltipInfo.GetHyperlink` présente sur Forever ; `ChatFrameUtil.InsertLink` à accrocher par
  `hooksecurefunc`, `ChatEdit_InsertLink` en repli. (wiki : https://warcraft.wiki.gg/wiki/API_C_TooltipInfo.GetHyperlink)
- Lua du jeu : Lua 5.1 sans `os` ni `io`, `bit` sur 32 bits fourni par le jeu, pas d'`utf8` (`strlenutf8`
  seulement), nombres en double. (wiki : https://warcraft.wiki.gg/wiki/Lua_functions)
- `lupa` 2.8 (2026-04-15) embarque Lua 5.1.5 à 5.5, compilés en `lupa.lua51`… ; présence de `lupa.lua51` dans les
  roues Windows et Linux à confirmer à l'étape 0.2. (https://pypi.org/project/lupa/, https://github.com/scoder/lupa)

## Choix proposés (sans question, à confirmer à la validation)

1. **Réserve de 64 emplacements** (`ForeverBridge_S01` … `ForeverBridge_S64`), réglable à l'installation
   (`--slots`, 8 à 200). wow-ai en installe 200, lourds dans la liste des addons du jeu et du gestionnaire. Une réponse
   coûte un emplacement quand le drapeau marche (environ quatre sinon), l'ouverture de la fenêtre un ; 64 couvrent une
   longue session de jeu, puis `/reload` rend toute la réserve.
2. **Aucun `ReloadUI` dans nos addons** : le secours affiche « tapez /reload » ; le joueur le tape. Interdits par
   `check_addon` dans nos addons : `ReloadUI`, `EnableKeyboard`, `SetPropagateKeyboardInput` (pas de capte-clavier),
   en plus des fonctions d'action.
3. **Capture** par l'API de Windows en `ctypes` (aucune dépendance) : fenêtre du jeu trouvée par ses exécutables,
   rectangle de la bande pris **dans la zone client**, lu par `BitBlt` depuis l'écran **seulement si la fenêtre du
   jeu est au premier plan et non réduite** (sinon une fenêtre posée par-dessus serait lue : capture hors du jeu).
   Processus marqué « DPI aware » pour des coordonnées physiques. Mode fenêtré ou plein écran fenêtré requis (le plein
   écran exclusif rend une capture noire, wow-ai).
4. **Sonde** : cinq premières cellules de la rangée 0 (20 × 4 px, les 15 premiers bits du marqueur `C7 1A` : cellules
   `6, 1, 6, 1, 5`) toutes les 250 ms ; bande entière (200 × 24 cellules au plus, 800 × 96 px) lue seulement si la
   sonde reconnaît le marqueur ; la somme de contrôle écarte un faux marqueur. Fenêtre absente : recherche toutes les
   3 s, aucune capture.
5. **Bande** : 200 cellules par rangée, 24 rangées au plus, soit 1 792 octets de charge (1 800 − 8 d'en-tête et de
   somme). Montrée tant que le message n'a pas d'accusé de réception, 30 s au plus, trois fois au plus ; ensuite
   boîte d'envoi pour `/reload` et bande retirée.
6. **Message** (charge de la bande) : champs séparés par `0x1F` : version du protocole `1`, jeton de session de
   l'addon, numéro du message, drapeaux (`n` nouvelle conversation, `h` bonjour sans question), contexte, texte.
   Contexte en lignes `clé=valeur` : `name`, `realm`, `level`, `class` (jeton anglais), `race` (jeton anglais),
   `faction`, `zone`, `subzone`, `map` (uiMapID), `talents` (`nœud:rang` séparés par des virgules, rangs achetés
   seulement), `gear` (`emplacement:objet:nom` séparés par `;`), `client` (version du client). Question limitée à
   255 caractères (zone de saisie). Contexte envoyé à chaque message (pas seulement quand il change : plus simple, il
   tient dans la bande).
7. **Signaux** : `sig/NN.wav` (réponse prête), `ack/NN.wav` (message reçu), `NN = ((id − 1) mod 64) + 1` ; avant
   d'envoyer le message `id`, l'addon vérifie que `sig/NN` et `ack/NN` ne jouent pas déjà (sinon signaux « non
   fiables » pour ce message : relevé de la réserve à horaire fixe, comme wow-ai : 5, 10, 16, 24, 34, 46, 60 s puis
   toutes les 30 s) ; le pont vide les drapeaux des 8 numéros suivants à chaque message reçu et tous les drapeaux à
   son démarrage quand le jeu est fermé.
8. **Retour** : à chaque publication, le pont écrit le même `Inbox.lua` dans les 64 emplacements (écriture atomique),
   puis dans `ForeverBridge/Inbox.lua` (lu au `/reload`), puis lève `sig/NN`. Contenu : `ForeverBridgeSlot = {
   now, status = {…}, replies = { { id, session, status = "done" | "error" | "working", text, provenance, link } } }`
   (dix dernières réponses).
9. **Conversation « jeu »** : `claude -p --output-format stream-json --verbose --tools "" --permission-mode dontAsk
   --permission-prompts none --allowedTools <les six outils forever> --plugin-dir <dépôt>/plugin
   --append-system-prompt <consignes fixes> [--resume <session>] [--model <modèle>]`, dans le dépôt, question sur
   l'entrée standard. Jamais `bypassPermissions` ni `--dangerously-skip-permissions`. **Le contexte du personnage va
   dans le message**, pas dans le prompt système (figé par `--system-prompt-snapshot`). Délai 180 s, arbre de
   processus tué au-delà (le seul processus que le pont tue est le sien).
10. **`--tools ""` retire aussi l'outil `Skill`** : les skills du plugin ne servent pas à la conversation « jeu ».
    Les règles de réponse viennent des instructions du serveur MCP forever (aucun chiffre sans outil, certitude et
    provenance, « je ne sais pas ») et des consignes fixes du pont. Si les réponses en jeu en souffrent, autoriser
    `Skill` est une décision de P06b.
11. **Environnement de la conversation** : `FOREVER_HOME=<dépôt>`, `FOREVER_OFFLINE=1` (aucun outil forever ne touche
    Internet depuis le jeu ; l'état des données vient du pont), `FOREVER_BRIDGE=1` (le hook `session-start` n'archive
    rien et ne lance pas `forever update` : il tournerait à chaque message repris ; il rend toujours sa ligne d'état).
    Le hook `Stop` (`check-numbers`) reste actif.
12. **Provenance ajoutée par le pont** : le pont lit le flux `stream-json`, garde les blocs `provenance` des résultats
    d'outils forever et ajoute à la réponse une ligne normalisée `Données <version> · <certitudes>` (la plus faible
    d'abord) ou `Aucun outil forever appelé : réponse sans chiffre de jeu.` Le lien Talents Forever d'un résultat de
    `forever_build` (champ du lien) est rendu à part (`link`) pour la zone copiable.
13. **Consignes fixes** (prompt système ajouté, en français) : réponse de 600 caractères au plus, texte brut sans
    Markdown, noms du jeu tels qu'ils apparaissent dans le client anglais de l'utilisateur (décision 177), lien Talents
    Forever quand la réponse donne un build, aucun conseil en combat, rien sur les actions à la place du joueur.
14. **Session reprise** : `<cache>/bridge/sessions.json` garde l'identifiant de session de la conversation « jeu »
    (rendu par l'événement `result`) ; `/fv nouveau` en jeu pose le drapeau `n` (nouvelle session).
15. **Un seul message traité à la fois** (file), un seul pont à la fois (verrou `<cache>/bridge/bridge.lock`, pid et
    date, verrou mort repris) ; arrêt propre par fichier `<cache>/bridge/stop` (`forever bridge stop`), jamais par
    signal.
16. **Journal du pont** : `<cache>/bridge/journal/<AAAA-MM-JJ>.jsonl`, un objet par ligne : `start`, `stop`,
    `window` (fenêtre trouvée ou perdue : titre, pid), `band_rejected` (raison seulement, au plus une ligne par 5 s),
    `message` (session, id, voie `pixels` ou `reload`, texte, clés du contexte), `command` (argv sans la question,
    dossier), `denied` (outils refusés), `reply` (id, durée, longueur, provenance), `published` (emplacements, signal),
    `error`. **Aucun pixel** ni image n'y est écrit.
17. **État des données** : `status_payload(deps)` (version, fraîcheur et âge, couverture du registre, nombre
    d'attentes et leurs trois premiers libellés, passage en cours) écrit dans chaque publication et dans
    `ForeverBridge/Status.lua` au démarrage du pont puis toutes les 10 min (relu à la connexion et au `/reload`).
    L'addon l'affiche en tête de la fenêtre, toujours ; « état inconnu » tant qu'aucun fichier n'a été lu.
18. **Décision 212** pour ces choix, ROADMAP mise à jour (P06a et P06b).

## Contexte du code (lecture du plan)
- Les identifiants sont en anglais ; commentaires, docstrings et messages en français ; textes affichés en jeu en
  français, noms du jeu en anglais.
- `addon/` ne contient aucun chiffre de jeu (`scripts/check_game_numbers.py` couvre `.lua` et `.toc`) : vérifier que
  les constantes du protocole (4 px, 200 cellules, 64 emplacements) ne le déclenchent pas, sinon documenter
  l'exemption dans le script (constantes d'outil, pas de jeu).

## Blocs et étapes

Ordre fixé par la date : le **transport d'abord**, avec une première sonde en jeu dès le bloc A vert.

### Étape 0 — Préalables (avant tout test)
1. **Feuille de route et décision 212** : ROADMAP P06a (conversation « addons », liens Maj+clic, écart avec le profil
   déplacés en P06b ; addon `ForeverBridge` nommé) et P06b (les reçoit) ; décision 212 (choix 1 à 17 ci-dessus) ;
   `docs/ADDON.md` §9 nomme `ForeverBridge`.
2. **`uv add --dev lupa`** (accord du 2026-10-08) ; contrôle : `from lupa import lua51` puis
   `lua51.LuaRuntime().execute("return _VERSION")` rend `Lua 5.1` ; sinon arrêt et retour à l'utilisateur (repli
   accepté : contrôles statiques).
3. **Skill `.claude/skills/addon-forever/SKILL.md`** (développement, pas le plugin) : quand le charger (tout travail
   dans `addon/`, P06a, P06b, EX1) ; règles du dépôt (renvoi à `docs/ADDON.md`, `check_addon`, décisions 194 à 196) ;
   pièges de l'API de Forever : Lua 5.1 (pas d'entiers 64 bits, `bit` fourni par le jeu et absent de Lua 5.1 nu, pas
   d'`utf8`, `#` sur les chaînes en octets), valeurs secrètes (`issecretvalue`, `UnitHealth` et `UnitPower` même hors
   combat), fonctions protégées (`ReloadUI`, actions) et `InCombatLockdown`, `pcall` sur chaque `RegisterEvent` et
   API incertaine, SavedVariables initialisées à `ADDON_LOADED` sans alias, API retirées (`GetSpellInfo`…, utiliser
   `C_Spell`, `C_Item`, `C_Traits`), fichiers vus au lancement seulement, cache des sons, `LoadOnDemand` une fois par
   session, échelle pixel parfaite, séquences `|` dans les textes ; tests sous `lupa.lua51` avec le client simulé ;
   sources (warcraft.wiki.gg, wow-ai, `docs/research/addon-forever.md`).
4. **Sonde de `claude`** (avec l'accord de l'utilisateur à l'exécution : elle parle à l'API d'Anthropic) : une
   question fixe (« Quelle est la version des données ? ») lancée avec la ligne de commande du choix 9, puis reprise
   par `--resume`. Elle fixe : le préfixe des outils sous `--plugin-dir` (attendu `mcp__plugin_forever_forever__`) ;
   si `--strict-mcp-config` garde le serveur du plugin (sinon il n'est pas utilisé : la liste d'autorisations et
   `dontAsk` suffisent à refuser tout autre outil) ; la forme des événements `system`, `assistant`, `user`
   (`tool_result`) et `result` (`session_id`, `permission_denials`, `is_error`). Sa sortie, identifiants remplacés,
   devient la fixture `tests/fixtures/bridge/claude_stream_status.jsonl` et `claude_stream_resume.jsonl` ; une
   troisième, écrite à la main d'après la forme relevée, porte un refus d'outil (`claude_stream_denied.jsonl`).

### Bloc A — Codec, bande, capture, bande de test (puis première sonde en jeu)
- `forever/bridge/codec.py`, `forever/bridge/image.py`, `forever/bridge/capture.py`, `addon/ForeverBridge/Codec.lua`,
  `addon/ForeverBridge/ForeverBridge.toc`, premier `addon/ForeverBridge/ForeverBridge.lua` (initialisation,
  `/fv test` qui montre la bande du vecteur de test pendant 30 s puis la retire), `forever bridge selftest`.
- `/fv diag` dès ce bloc : autotest des drapeaux en `.wav` et en `.ogg` (fichiers `ctl/` installés à la main pour la
  sonde) ; il fixe le format des drapeaux du bloc B.
- **Sonde en jeu A** (utilisateur, dès le bloc vert, procédure §7 étape 9.1 à 9.3) : la bande de test est lue par le
  pont. Une image de la vraie bande, enregistrée par `selftest --live --save`, entre en fixture
  (`tests/fixtures/bridge/band_live.bmp`) et en test de non-régression (test ajouté après la sonde, hors du commit
  rouge du bloc).

### Bloc B — Message, emplacements, drapeaux, installation
- `forever/bridge/record.py`, `forever/bridge/slots.py`, `forever/bridge/install.py`, `forever bridge install`,
  `addon/ForeverBridge/Inbox.lua` et `Status.lua` (fichiers d'attente), extension de `scripts/install_addon.py`
  (installe aussi ForeverBridge, ou renvoie à `forever bridge install`).

### Bloc C — Conversation « jeu »
- `forever/bridge/agent.py` (argv, lancement, flux, délai), `forever/bridge/prompt.py` (consignes fixes, message avec
  contexte), sessions, provenance ajoutée ; `forever/hooks.py` respecte `FOREVER_BRIDGE=1`.

### Bloc D — Boucle du pont
- `forever/bridge/loop.py` (boucle, file, verrou, arrêt, boîte d'envoi `/reload`, publication), `forever/bridge/
  journal.py`, `forever/bridge/state.py` (messages traités par session, sessions), `forever/bridge/status.py` (état
  des données), CLI `forever bridge {install,start,run,stop,status,selftest}`, lancement par `forever.spawn`.

### Bloc E — Addon complet
- `addon/ForeverBridge/ForeverBridge.lua` : fenêtre de chat (`/fv`, `/forever`), ligne d'état des données toujours
  visible, ligne du pont (vu il y a…, en attente depuis…, réserve restante, secours), historique (50 derniers
  messages dans `ForeverBridgeDB`), zone copiable du lien Talents Forever, envoi, contexte, drapeaux et autotest,
  réserve, secours `/reload` ; `check_addon` généralisé ; tests `lupa`.

### Bloc F — Documentation et procédure en jeu
- `docs/ADDON.md` (§2 règles du pont, §5 canal « fait », §6 contrat `ForeverBridgeDB` et `ForeverBridgeSlot`, §7
  étape 9 procédure, §8 checklist étendue, §9, **crédits wow-ai**), `docs/VISION.md` (crédits faits),
  `docs/ARCHITECTURE.md` (module `forever/bridge/`), `docs/USAGE.md` (`forever bridge`), `addon/README.md`
  (ForeverBridge), `docs/OPEN_QUESTIONS.md`, `CLAUDE.md` (liste des sous-processus : `claude` lancé par le pont ;
  liste réseau inchangée).

## Fichiers

| Fichier | Rôle | Repris de wow-ai |
| --- | --- | --- |
| `forever/bridge/__init__.py` | paquet du pont | non |
| `forever/bridge/codec.py` | Fletcher-16, cellules, encodage (tests, bande de test), décodage d'une bande, sonde du marqueur | oui (`Codec.lua`, `capture.ps1`) |
| `forever/bridge/image.py` | image BGRA minimale, lecture et écriture BMP 24 et 32 bits (fixtures, sans Pillow) | non |
| `forever/bridge/capture.py` | fenêtre du jeu, zone client, premier plan, rectangle de la bande, `BitBlt` en `ctypes` | oui (logique de `capture.ps1`) |
| `forever/bridge/record.py` | message de la bande : construction, lecture, contexte | oui (format inspiré, simplifié) |
| `forever/bridge/slots.py` | WAV silencieux, noms et numéros d'emplacement, échappement Lua, `Inbox.lua`, `Status.lua`, drapeaux | oui (`protocol.js`, `bridge.js`) |
| `forever/bridge/install.py` | installation de l'addon, des emplacements et des drapeaux (fichiers absents seulement) | oui (`install-slots.js`) |
| `forever/bridge/agent.py` | argv de `claude`, lancement, lecture du flux, délai, provenance | non (inspiré de `agents.js`) |
| `forever/bridge/prompt.py` | consignes fixes, message avec contexte | non |
| `forever/bridge/state.py` | messages traités, session de la conversation | non |
| `forever/bridge/status.py` | état des données pour l'addon | non |
| `forever/bridge/journal.py` | journal JSONL | non |
| `forever/bridge/loop.py` | boucle, file, verrou, arrêt, boîte d'envoi, publication | non |
| `forever/cli.py` | sous-commande `bridge` | non |
| `forever/hooks.py` | `FOREVER_BRIDGE=1` : ni archivage ni lancement de `forever update` | non |
| `addon/ForeverBridge/ForeverBridge.toc` | `## Interface: 16001`, `## SavedVariables: ForeverBridgeDB` | non |
| `addon/ForeverBridge/Codec.lua` | codec Lua | oui (`Codec.lua`, presque tel quel) |
| `addon/ForeverBridge/ForeverBridge.lua` | fenêtre, bande, drapeaux, réserve, contexte, état, secours | oui en partie (bande, drapeaux, réserve) |
| `addon/ForeverBridge/Inbox.lua`, `Status.lua` | fichiers d'attente écrasés par le pont dans l'addon installé | non |
| `scripts/check_addon.py` | SavedVariable lue dans le `.toc`, nouvelles interdictions, dessin réservé à ForeverBridge | non |
| `.claude/skills/addon-forever/SKILL.md` | skill de développement (étape 0.3) | non |
| `tests/fixtures/bridge/` | flux `claude`, SavedVariables avec boîte d'envoi, client simulé Lua, bandes BMP | `wow_stub.lua` inspiré (réécrit) |
| `tests/fixtures/addon/bad/` | nouveaux cas négatifs | non |

**Licence** : chaque fichier marqué « oui » porte en tête, en commentaire, la mention « Contient du code adapté de
wow-ai (https://github.com/chelinho139/wow-ai, commit 3756eb5a) » suivie de la **notice MIT complète** (copyright
et permission) ; crédits dans `docs/ADDON.md` (section « Crédits ») et `docs/VISION.md` (« Crédits prévus » devient
« Crédits »). Un test vérifie la présence de la notice dans chaque fichier repris (liste fermée).

## Interfaces

```python
# forever/bridge/codec.py
CELL_PX = 4; CELLS_PER_ROW = 200; MAX_ROWS = 24; MAGIC = (0xC7, 0x1A)
MAX_PAYLOAD = 1792; MARKER_CELLS = (6, 1, 6, 1, 5)
def fletcher16(data: bytes) -> tuple[int, int]: ...
def encode_cells(message_id: int, payload: bytes) -> list[int]: ...        # ValueError si payload > MAX_PAYLOAD
def cell_color(value: int) -> tuple[int, int, int]: ...                     # (255|0, 255|0, 255|0)
def render_band(cells: Sequence[int]) -> Image: ...                         # bande de test et tests
def cell_values(image: Image, rows: int) -> list[int]: ...                  # centre de chaque cellule, seuil 128
def marker_present(probe: Image) -> bool: ...                               # cinq cellules de la sonde
def decode_band(image: Image) -> Decoded | BandError | None: ...            # None : pas de marqueur
# Decoded(message_id: int, payload: bytes) ; BandError(reason: Literal["length", "truncated", "checksum"])

# forever/bridge/image.py
@dataclass(frozen=True)
class Image: width: int; height: int; bgra: bytes
def read_bmp(path: Path) -> Image: ...; def write_bmp(image: Image, path: Path) -> None: ...

# forever/bridge/capture.py
@dataclass(frozen=True)
class Rect: left: int; top: int; width: int; height: int
def probe_rect(client: Rect) -> Rect | None: ...      # None si la zone client est plus petite que la sonde
def band_rect(client: Rect) -> Rect | None: ...       # bornée à la zone client
def may_capture(game_hwnd: int | None, foreground_hwnd: int | None, iconic: bool) -> bool: ...
class WindowsCapture:                                 # seul code non testé hors Windows ; `grab(rect)` refuse un
    def find(self) -> int | None: ...                 # rectangle hors de la zone client ou plus grand que la bande
    def grab(self, rect: Rect) -> Image | None: ...

# forever/bridge/record.py
PROTOCOL = "1"
@dataclass(frozen=True)
class Record: session: str; message_id: int; flags: frozenset[str]; context: dict[str, str]; text: str
def build_payload(record: Record) -> bytes: ...       # séparateurs retirés du texte et du contexte
def parse_payload(payload: bytes) -> Record: ...      # RecordError si version, champs ou numéro invalides
def context_lines(context: Mapping[str, str]) -> str: ...   # texte du contexte pour le message à Claude

# forever/bridge/slots.py
SILENT_WAV: bytes                                     # 124 octets
def slot_name(index: int) -> str: ...                 # 1 -> "ForeverBridge_S01"
def slot_number(message_id: int, slots: int) -> int: ...
def lua_string(text: str) -> str: ...
def inbox_lua(now: int, status: Mapping, replies: Sequence[Mapping]) -> str: ...
def status_lua(status: Mapping) -> str: ...
def publish(addons_dir: Path, inbox: str, slots: int) -> int: ...           # nombre de fichiers écrits
def raise_signal(addons_dir: Path, kind: Literal["sig", "ack"], message_id: int, slots: int) -> None: ...
def lower_ahead(addons_dir: Path, message_id: int, slots: int, ahead: int = 8) -> None: ...
def lower_all(addons_dir: Path, slots: int) -> None: ...

# forever/bridge/install.py
def install_bridge(wow_dir: Path, slots: int = 64, *, dry_run: bool = False) -> InstallReport: ...

# forever/bridge/agent.py
FOREVER_TOOLS: tuple[str, ...]                        # six noms complets, préfixe fixé par la sonde 0.4
def claude_argv(*, claude: str, plugin_dir: Path, session_id: str | None, model: str | None) -> list[str]: ...
def claude_env(environ: Mapping[str, str], repo_root: Path) -> dict[str, str]: ...
def parse_stream(lines: Iterable[str]) -> AgentResult: ...
# AgentResult(text, session_id, denied: list[str], provenances: list[dict], link: str | None, is_error: bool)
def provenance_line(provenances: Sequence[Mapping]) -> str: ...
def run_claude(argv, prompt, *, cwd, env, timeout_s=180.0, popen=subprocess.Popen) -> AgentResult: ...

# forever/bridge/status.py
def status_payload(deps: Deps) -> dict[str, Any]: ...
def status_line(payload: Mapping[str, Any]) -> str: ...

# forever/bridge/loop.py
class Bridge:
    def __init__(self, deps, *, addons_dir, capture, agent, journal, slots=64, clock=time.monotonic): ...
    def step(self) -> None: ...      # une itération : sonde, bande, boîte d'envoi, file, publication
    def run(self) -> int: ...        # boucle jusqu'au fichier d'arrêt
def acquire_lock(cache_dir: Path, now: datetime) -> bool: ...
```

Côté Lua (`ForeverBridge.lua`, table globale `ForeverBridge`) : `Send(text)`, `Tick()` (minuterie de 0,25 s),
`GameContext()`, `RefreshBand()`, `SelfTestSignals()`, `TryLoadSlot(why)`, `ProcessInbox()`, `RenderStatus()` ;
SavedVariable `ForeverBridgeDB = { schema = 1, session, next_id, history, outbox, window }`.

## Tests attendus

Tous sans réseau, sans jeu ni écran ; écrits dans `tmp_path`. Valeurs calculées au plan (script hors dépôt).

### `tests/unit/test_bridge_codec.py` (bloc A)
- `fletcher16(b"abcde") == (240, 200)`, `b"abcdef"` → `(87, 32)`, `b"abcdefgh"` → `(39, 6)` (valeurs publiées de
  Fletcher-16 : 0xC8F0, 0x2057, 0x0627).
- `encode_cells(1, b"")` = `[6, 1, 6, 1, 5, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 1, 4]` (22 cellules ;
  octets `C7 1A 00 01 00 00 01 03`).
- `encode_cells(1, b"A")` = `[6, 1, 6, 1, 5, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1, 2, 0, 2, 4, 1, 5, 0, 7]` (24).
- `encode_cells(258, "Talent?".encode())` : 40 cellules, octets `C7 1A 01 02 00 07 54 61 6C 65 6E 74 3F B3 15`,
  cellules `[6, 1, 6, 1, 5, 0, 0, 1, 0, 0, 4, 0, 0, 0, 0, 7, 2, 5, 0, 6, 0, 5, 5, 4, 3, 1, 2, 6, 7, 1, 6, 4, 1, 7, 7,
  3, 1, 4, 2, 5]`.
- `cell_color(5) == (255, 0, 255)` ; `cell_color(0) == (0, 0, 0)` ; `cell_color(7) == (255, 255, 255)`.
- Aller-retour : `decode_band(render_band(encode_cells(42, p)))` rend `(42, p)` pour `p` de 0, 1, 1 000 et 1 792
  octets (UTF-8 accentué compris) ; 1 793 octets → `ValueError`.
- Bruit : chaque canal décalé de ±40 (graine fixe) puis gamma 0,8 et 1,25 : même décodage (repris du test de wow-ai).
- Rejets : premier octet altéré → `None` ; une cellule de la charge altérée → `BandError("checksum")` ; image coupée
  après l'en-tête → `BandError("truncated")` ; longueur déclarée 0xFFFF → `BandError("length")`.
- `marker_present` : vrai sur les cinq cellules `6, 1, 6, 1, 5`, faux sur une image noire, sur une image blanche et si
  une seule des cinq cellules diffère.
- `read_bmp(write_bmp(img))` rend la même image (24 et 32 bits, lignes de bas en haut).

### `tests/unit/test_bridge_capture.py` (bloc A)
- `band_rect(Rect(100, 50, 1920, 1080)) == Rect(100, 50, 800, 96)` ; `probe_rect(…) == Rect(100, 50, 20, 4)` ;
  zone client de 640 × 80 → bande bornée `Rect(…, 640, 80)` ; zone client de 16 × 4 → `probe_rect` rend `None`.
- `may_capture(7, 7, False)` vrai ; `may_capture(7, 9, False)` faux (autre fenêtre au premier plan) ;
  `may_capture(7, 7, True)` faux (réduite) ; `may_capture(None, 7, False)` faux.
- `WindowsCapture.grab` refuse un rectangle plus grand que la bande (test sur une capture simulée, sans écran).

### `tests/unit/test_bridge_record.py` (bloc B)
- `parse_payload(build_payload(r)) == r` pour un message avec contexte (`level=19`, `class=MAGE`, `race=Human`,
  `zone=Westfall`, `talents=…`, `gear=…`) et pour un bonjour (`h`, texte vide).
- Un `0x1F` ou `0x1E` dans le texte est remplacé par une espace ; version `2` → `RecordError` ; numéro non
  numérique → `RecordError`.
- `context_lines` rend les lignes dans un ordre fixe (`name`, `level`, `class`, `race`, `zone`, `subzone`, `map`,
  `talents`, `gear`, `client`), clés inconnues ignorées.
- Un message type (question de 255 caractères, 51 nœuds de talents, 17 pièces d'équipement aux noms de 40
  caractères) tient dans `MAX_PAYLOAD`.

### `tests/unit/test_bridge_slots.py` (bloc B)
- `SILENT_WAV` : 124 octets, commence par `RIFF`, `WAVE` à l'octet 8, 80 échantillons à 128 (si la sonde A retient
  `.ogg`, ce test vise à la place un `.ogg` silencieux versionné dans `addon/ForeverBridge/ctl/`, écrit avant le
  commit rouge du bloc B).
- `slot_name(1) == "ForeverBridge_S01"`, `slot_name(64) == "ForeverBridge_S64"` ; `slot_number(1, 64) == 1`,
  `slot_number(64, 64) == 64`, `slot_number(65, 64) == 1`.
- `lua_string` : `"` → `\"`, `\` → `\\`, saut de ligne → `\n`, `]]` sans effet (chaîne entre guillemets), `|` →
  `||` (séquences d'interface neutralisées), octets de contrôle retirés.
- `publish` écrit le même contenu dans les 64 emplacements et dans `ForeverBridge/Inbox.lua` (65 fichiers), par
  renommage atomique (aucun `.tmp` restant).
- `raise_signal("sig", 65, 64)` écrit `SILENT_WAV` dans `ForeverBridge/sig/01.wav` ; `lower_ahead(10, 64)` vide
  `sig` et `ack` de 11 à 18 (0 octet) ; `lower_all` vide tout.

### `tests/unit/test_bridge_install.py` (bloc B)
- `install_bridge(tmp, slots=4)` crée `ForeverBridge/` (copie de `addon/ForeverBridge`), `ForeverBridge_S01` à
  `S04` (`.toc` avec `## Interface: 16001`, `## LoadOnDemand: 1`, `## Dependencies: ForeverBridge`, `Inbox.lua`),
  `sig/01..04.wav` et `ack/01..04.wav` vides, `ctl/empty.wav` vide et `ctl/valid.wav` = `SILENT_WAV`.
- Deuxième appel : aucun fichier réécrit sauf l'addon principal ; `dry_run` n'écrit rien et rend la liste prévue ;
  `slots=7` ou `201` → erreur nommée.

### `tests/unit/test_bridge_agent.py` (bloc C)
- `claude_argv(session_id=None)` contient `-p`, `--output-format stream-json`, `--verbose`, `--tools ""` (élément
  vide), `--permission-mode dontAsk`, `--permission-prompts none`, `--plugin-dir <dépôt>/plugin`,
  `--append-system-prompt`, et `--allowedTools` suivi **exactement** des six outils forever ; ne contient ni
  `--resume`, ni `bypassPermissions`, ni `--dangerously-skip-permissions`, ni `--allow-dangerously-skip-permissions`,
  ni `Bash`, `Edit`, `Write`, `WebFetch`, `WebSearch`, `Skill`.
- `claude_argv(session_id="abc")` ajoute `--resume abc`.
- `claude_env` pose `FOREVER_HOME`, `FOREVER_OFFLINE=1`, `FOREVER_BRIDGE=1`.
- `parse_stream(claude_stream_status.jsonl)` : texte final, `session_id` relevé, une provenance (version du jeu de la
  fixture), `denied == []`, `is_error` faux.
- `parse_stream(claude_stream_denied.jsonl)` : `denied` porte le nom de l'outil refusé.
- `provenance_line` : deux provenances `probable` et `suppose` → `Données <version> · suppose, probable` ; aucune →
  `Aucun outil forever appelé : réponse sans chiffre de jeu.`
- `run_claude` avec un faux `Popen` qui ne finit pas → résultat en erreur « délai dépassé (180 s) » et processus tué ;
  faux `Popen` qui rend le flux de la fixture → même résultat que `parse_stream`.
- Le prompt système ne contient aucun champ de contexte ; le message (entrée standard) commence par le bloc de contexte
  puis la question.

### `tests/unit/test_bridge_loop.py` (bloc D)
- Capture simulée qui rend une bande valide (message 3, question) : un `message` et un `command` journalisés ;
  `ack/03.wav` levé avant le lancement de l'agent ; après l'agent simulé : 65 `Inbox.lua` contenant la réponse,
  la ligne de provenance et l'état des données, puis `sig/03.wav` levé ; `sessions.json` garde la session.
- Même bande vue deux fois : un seul traitement (dédoublonnage par session et numéro).
- Message suivant sans drapeau `n` : l'agent reçoit `--resume <session>` ; avec `n` : pas de `--resume`.
- Capture simulée qui rend une image sans marqueur pendant 100 pas : aucune lecture de la bande entière (compteur des
  lectures pleine bande à 0), rien de journalisé.
- `may_capture` faux (autre fenêtre au premier plan) : aucune lecture, même la sonde.
- Boîte d'envoi : fixture `ForeverBridge_outbox.lua` (SavedVariables) avec le message 5 → traité une fois ; relu
  après modification de la date du fichier sans nouveau numéro → rien.
- Agent en erreur → réponse `status = "error"` publiée et `error` journalisé.
- Verrou : un second `acquire_lock` avec un pid vivant échoue ; avec un pid mort, réussit. Fichier `stop` → `run()`
  rend 0 et journalise `stop`.
- Journal : chaque ligne est un objet JSON avec `at` et `event` ; aucune ligne ne contient de clé `pixels`, `image` ou
  `bgra`.
- `forever bridge start` appelle `spawn_detached` avec `[python, "-u", "-m", "forever", "bridge", "run"]` et un
  journal `<cache>/bridge/run-<horodatage>.log` (faux `spawn`) ; refus si le verrou est vivant.
- `forever bridge status --json` porte un bloc `provenance`.

### `tests/unit/test_bridge_status.py` (bloc D)
- Sur les données de fixture et un cache simulé avec une attente : `status_payload` rend la version installée, la
  fraîcheur, `pending == 1` et son libellé ; `status_line` → `Données <version> · <fraîcheur> · 1 attente : forever
  update status`. Sans attente : pas de partie « attente ». `status_payload` n'appelle pas le réseau (`http_get`
  qui lève).

### `tests/unit/test_bridge_addon_lua.py` (bloc E, `lupa.lua51`, client simulé `tests/fixtures/bridge/wow_stub.lua`)
1. `_VERSION == "Lua 5.1"` ; le client simulé n'expose pas `bit` (le codec n'en dépend pas).
2. `ADDON_LOADED` : `ForeverBridgeDB` créée (`schema = 1`, jeton de session, `next_id = 1`), bande cachée, autotest
   des drapeaux réussi (vide : ne joue pas ; valide : joue).
3. **Codec Lua = codec Python** : `ForeverBridge_Codec.Encode` rend les trois séquences de cellules ci-dessus, et
   1 000 octets aléatoires (graine fixe) donnent les mêmes cellules qu'`encode_cells`.
4. Sans message : 400 pas de `Tick()` → bande jamais montrée.
5. `Send("Quel talent au niveau 20 ?")` → bande montrée ; ses cellules, lues dans les textures simulées, se décodent
   par `decode_band` en un `Record` dont le contexte porte `level`, `class`, `race`, `zone`, `talents`, `gear`.
6. `ack/01.wav` levé → bande cachée au pas suivant.
7. Sans accusé : après 3 × 30 s simulées, bande cachée, `ForeverBridgeDB.outbox` rempli (numéro, texte, contexte),
   statut affiché contenant `/reload`.
8. `sig/01.wav` levé et emplacement simulé contenant la réponse → réponse affichée, ligne de provenance affichée,
   un seul emplacement chargé, message plus en attente.
9. 64 emplacements chargés → statut contenant `/reload` ; au `PLAYER_LOGIN` suivant, `Inbox.lua` simulé appliqué.
10. `sig/02.wav` déjà valide avant l'envoi du message 2 → signaux marqués non fiables, emplacement chargé à 5 s.
11. API en erreur ou valeur secrète (talents, équipement simulés en erreur) → contexte sans ces clés, aucune erreur
    Lua.
12. `Status.lua` simulé lu à la connexion → ligne d'état affichée ; état remplacé par celui de l'emplacement chargé.
13. Fonctions interdites définies dans le client simulé comme pièges (`CastSpellByName`, `UseAction`,
    `SendChatMessage`, `RunMacroText`, `CreateMacro`, `ReloadUI`) : aucun appel sur tous les scénarios ; aucun
    `RegisterEvent` hors `pcall` ; aucun abonnement à `COMBAT_LOG_EVENT*`.

### `tests/unit/test_addon_rules.py` (étendu, bloc E)
- `check_addon.check_addon(addon/ForeverBridge) == []` ; ForeverLogger toujours `[]`.
- Nouveaux cas négatifs dans `tests/fixtures/addon/bad/` (avec leur ligne) : `create_macro.lua` (« fonction interdite
  CreateMacro »), `reload_ui.lua` (« fonction interdite ReloadUI »), `keyboard.lua` (« EnableKeyboard »), et
  `ForeverLogger/draw.lua` (« dessin réservé à ForeverBridge », `SetColorTexture` hors de l'addon du pont).
- La SavedVariable contrôlée est lue dans le `.toc` (`ForeverBridgeDB` pour le pont, alias local refusé).
- `ForeverBridge.toc` : `## Interface: 16001`, `## SavedVariables: ForeverBridgeDB`, fichiers listés présents.

### Autres
- `tests/unit/test_network_boundary.py` : l'ensemble des modules qui importent `subprocess` gagne
  `bridge/agent.py` ; nouvelle assertion : `agent.py` ne contient ni `"git"` ni `"gh"` et ne lance que l'exécutable
  `claude` ; `forever/bridge/` n'importe aucun module réseau.
- `tests/unit/test_hooks*.py` (fichier existant du hook de démarrage) : `FOREVER_BRIDGE=1` → ni archivage ni
  lancement, ligne d'état rendue.
- `tests/unit/test_bridge_license.py` : chaque fichier repris (liste fermée : `forever/bridge/codec.py`,
  `capture.py`, `record.py`, `slots.py`, `install.py`, `addon/ForeverBridge/Codec.lua`, `ForeverBridge.lua`) contient
  `Copyright (c) 2026 chelinho139` et `Permission is hereby granted, free of charge` ; `docs/ADDON.md` et
  `docs/VISION.md` citent `chelinho139/wow-ai`.
- Registre : **aucune entrée** (aucune mécanique de jeu) ; les comptes de `test_registry.py` ne bougent pas.

## Hors périmètre
- P06b : boutons, validation et refus en jeu des attentes, liens d'export cliquables, **liens Maj+clic et leur
  infobulle**, **écart avec le profil**, **conversation « addons »**, autorisation de l'outil `Skill`.
- Repris de wow-ai et écartés : plusieurs conversations et agents, Allow, macros, carte, présence, activité,
  restauration, `/r`, capte-clavier.
- Toute action de jeu, entrée simulée, message de chat automatique, lecture de la mémoire, capture hors de la bande,
  conseil en combat ; outil MCP qui écrit ou approuve.
- Capture sous macOS ou Linux (Wine) ; plein écran exclusif.
- Faire tourner wow-ai ou NeverQuestAlone.

## Risques
- **Fragilité à chaque build** : indexation des fichiers, cache des sons, police, échelle ; la checklist §8 gagne
  `forever bridge selftest --live` et l'autotest des drapeaux (`/fv diag`).
- **Effacement des SavedVariables** observé sur la bêta (wow-ai) : le secours `/reload` perd la boîte d'envoi ; le
  pont garde l'historique côté bureau (journal) ; pas de restauration en P06a.
- **`--strict-mcp-config` et `--plugin-dir`** : interaction inconnue, fixée par la sonde 0.4 ; la sécurité ne dépend
  que de `--tools ""`, de la liste d'autorisations et de `dontAsk`.
- **`lupa` sans `lua51`** dans la roue d'une plateforme de la CI : contrôle à l'étape 0.2 ; repli accepté par
  l'utilisateur (contrôles statiques) avec arrêt et accord avant de le prendre.
- **Latence** : démarrage de `claude` et du serveur MCP, dizaines de secondes ; la fenêtre affiche « en cours, N s ».
- **Capture noire** (plein écran exclusif, HDR non testé) : procédure en fenêtré sans bordure ; `selftest --live` le
  détecte.
- **Zone grise** (pixels et lecture d'écran, rapport §3.5) : assumée par la décision 194, périmètre strict, rien
  d'autre ; à réévaluer si Blizzard s'exprime.
- **Mise à l'échelle Windows** : processus « DPI aware » ; à défaut, rectangle faux et bande non lue (selftest).
- **Date** : la sonde en jeu A doit avoir lieu avant le 2026-10-14 pour laisser une semaine au reste ; si le
  transport échoue en jeu, le secours `/reload` reste livrable seul.

## Angles morts attendus
Aucune mécanique de jeu n'est ajoutée ni modifiée : la tranche n'influence aucun résultat chiffré. La qualité des
réponses en jeu dépend des outils existants (angles morts déjà listés par T04 à FA1 : classes sans moteur, modèle d'XP
de Forever absent, etc.).

## Questions ouvertes à ajouter (`docs/OPEN_QUESTIONS.md`)
- Sur ce client, un `.wav` vide « ne jouera pas » et un `.wav` valide « jouera » (autotest), et un drapeau levé reste
  valide jusqu'à la fermeture du client ? (mesuré par wow-ai, à confirmer par `/fv diag`).
- La bande est-elle lue sans erreur à toutes les échelles d'interface et résolutions de l'utilisateur ?

## Critères de fin
1. Protocole testé hors jeu dans les deux sens : codec (Python et Lua 5.1), bande, sonde, emplacements, drapeaux,
   boîte d'envoi `/reload`, reprise de session, erreurs (tests ci-dessus verts).
2. `test_addon_rules.py` étendu à ForeverBridge (dessin seulement dans le pont, bande seulement quand un message
   attend par les tests `lupa`, aucune fonction d'action).
3. Conversation « jeu » sans autre outil que ceux de forever (test de l'argv).
4. Journal du pont écrit (tests) ; état des données affiché (tests `lupa`).
5. Crédits et notices MIT en place (test).
6. Procédure en jeu écrite dans `docs/ADDON.md` §7, étape 9 : 9.1 client en fenêtré sans bordure ; 9.2
   `uv run forever bridge install`, puis fermer complètement et relancer le jeu ; 9.3 `/fv test` et
   `uv run forever bridge selftest --live` → « vecteur reconnu » ; 9.4 `uv run forever bridge start`, `/fv` : ligne
   d'état visible ; 9.5 question « Which talent should I take next? » ou en français → réponse courte avec sa ligne
   de provenance, journal relu ; 9.6 question de suite → même session (journal) ; 9.7 `forever bridge stop`, question,
   « tapez /reload », `/reload`, `forever bridge start` → réponse ; 9.8 `/fv diag` (autotest des drapeaux, réserve) ;
   9.9 ForeverLogger toujours actif. **À jouer avant le 2026-10-21**, non bloquant pour la fusion (comme FA1).
7. `uv run tasks.py verify` vert ; CI verte sous Ubuntu et Windows.

## Validation
Plan à valider par l'utilisateur. Exécution dans une nouvelle session (`/tranche P06a`), branche `p06a`, un cycle
rouge → vert par bloc.
