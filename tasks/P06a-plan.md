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

1. *(Remplacé le 2026-10-09 : 200 emplacements, voir « Amendement du 2026-10-09 ».)* **Réserve de 64 emplacements** (`ForeverBridge_S01` … `ForeverBridge_S64`), réglable à l'installation
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
4. *(Taille de case reconnue de 1 à 4 pixels depuis le 2026-10-09, voir l'amendement.)* **Sonde** : cinq premières cellules de la rangée 0 (20 × 4 px, les 15 premiers bits du marqueur `C7 1A` : cellules
   `6, 1, 6, 1, 5`) toutes les 250 ms ; bande entière (200 × 24 cellules au plus, 800 × 96 px) lue seulement si la
   sonde reconnaît le marqueur ; la somme de contrôle écarte un faux marqueur. Fenêtre absente : recherche toutes les
   3 s, aucune capture.
5. *(Remplacé le 2026-10-09 : une case par pixel, bande montrée jusqu'à l'accusé seulement.)* **Bande** : 200 cellules par rangée, 24 rangées au plus, soit 1 792 octets de charge (1 800 − 8 d'en-tête et de
   somme). Montrée tant que le message n'a pas d'accusé de réception, 30 s au plus, trois fois au plus ; ensuite
   boîte d'envoi pour `/reload` et bande retirée.
6. **Message** (charge de la bande) : champs séparés par `0x1F` : version du protocole `1`, jeton de session de
   l'addon, numéro du message, drapeaux (`n` nouvelle conversation, `h` bonjour sans question), contexte, texte.
   Contexte en lignes `clé=valeur` : `name`, `realm`, `level`, `class` (jeton anglais), `race` (jeton anglais),
   `faction`, `zone`, `subzone`, `map` (uiMapID), `talents` (`nœud:rang` séparés par des virgules, rangs achetés
   seulement), `gear` (`emplacement:objet:nom` séparés par `;`), `client` (version du client). Question limitée à
   255 caractères (zone de saisie). Contexte envoyé à chaque message (pas seulement quand il change : plus simple, il
   tient dans la bande). **Dépassement** (contexte + question au-delà de 1 792 octets) : l'addon allège le contexte
   dans cet ordre, en s'arrêtant dès que le message tient : noms d'objets coupés à 20 caractères, puis noms d'objets
   retirés (numéros gardés), puis `subzone`, puis `gear` ; la question n'est jamais coupée.
7. *(Remplacé le 2026-10-09 : aucun son ; consultation de la réserve à intervalles.)* **Signaux** : `sig/NN.wav` (réponse prête), `ack/NN.wav` (message reçu), `NN = ((id − 1) mod 64) + 1` ; avant
   d'envoyer le message `id`, l'addon vérifie que `sig/NN` et `ack/NN` ne jouent pas déjà (sinon signaux « non
   fiables » pour ce message : relevé de la réserve à horaire fixe, comme wow-ai : 5, 10, 16, 24, 34, 46, 60 s puis
   toutes les 30 s) ; le pont vide les drapeaux des 8 numéros suivants à chaque message reçu et tous les drapeaux à
   son démarrage quand le jeu est fermé.
8. *(Remplacé le 2026-10-09 : écriture à partir de l'emplacement annoncé.)* **Retour** : à chaque publication, le pont écrit le même `Inbox.lua` dans les 64 emplacements (écriture atomique),
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
13. *(Mise en forme restreinte depuis le 2026-10-09, voir l'amendement.)* **Consignes fixes** (prompt système ajouté, en français) : réponse de 600 caractères au plus, texte brut sans
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
   `dontAsk` suffisent à refuser tout autre outil) ; si `--plugin-dir` sur le plugin `forever`, déjà installé au
   niveau de l'utilisateur, crée un second serveur MCP du même nom ; le temps de démarrage avec et sans
   `--strict-mcp-config` et `--setting-sources project` (les serveurs MCP de l'utilisateur, context7, Serena…, se
   chargeraient sinon à chaque message) ; la forme des événements `system`, `assistant`, `user`
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
| `tests/fixtures/bridge/` | flux `claude`, SavedVariables avec boîte d'envoi, client simulé Lua (`wow_stub.lua`, **écrit de zéro** pour nos seules API, sans recopier celui de wow-ai), bandes BMP | non |
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

### `tests/unit/test_bridge_slots.py` (bloc B ; remplacé le 2026-10-09, voir l'amendement)
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

### `tests/unit/test_bridge_install.py` (bloc B ; remplacé le 2026-10-09, voir l'amendement)
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
- Entrée standard en octets UTF-8 explicites : une question accentuée (« Quel talent prendre à Westfall ? ») arrive
  intacte au faux `Popen`.

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

### `tests/unit/test_bridge_addon_lua.py` (bloc E, `lupa.lua51`, client simulé `tests/fixtures/bridge/wow_stub.lua` ; cas 6, 8, 10 remplacés le 2026-10-09)
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
11. Contexte trop gros (question de 255 caractères, 51 nœuds, 19 pièces aux noms de 60 caractères) : message envoyé
    quand même, sous 1 792 octets, question entière, clés allégées dans l'ordre du choix 6.
12. API en erreur ou valeur secrète (talents, équipement simulés en erreur) → contexte sans ces clés, aucune erreur
    Lua.
13. `Status.lua` simulé lu à la connexion → ligne d'état affichée ; état remplacé par celui de l'emplacement chargé.
14. Fonctions interdites définies dans le client simulé comme pièges (`CastSpellByName`, `UseAction`,
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

## Exécution : sonde 0.4 de `claude` (2026-10-08, accord de l'utilisateur)
Validation du plan avec une modification : l'outil `Skill` est autorisé dans la conversation « jeu » (choix 10
remplacé). Relevés sur `claude` 2.1.294 (question « Quelle est la version des données ? » puis reprise) :
1. Ligne du choix 9 telle quelle, lancée dans le dépôt : **le hook `Stop` du projet** (`.claude/hooks/test_on_stop.py`,
   tests rapides) se déclenche et **remplace la réponse finale** par un commentaire sur les tests ; 134 outils exposés
   (connecteurs claude.ai : Gmail, Drive, Jira…, refusés par `dontAsk` mais visibles) ; coût d'environ 0,8 $.
2. `--strict-mcp-config` seul retire aussi le serveur du plugin (aucun outil forever : le routeur répond « plugin mal
   installé »). `--restricted` seul ignore les réglages (hooks du projet, plugins de l'utilisateur) mais garde les
   connecteurs claude.ai.
3. **Ligne retenue** : `--tools Skill`, `--restricted`, `--strict-mcp-config`, `--mcp-config` avec le seul serveur
   `forever` (`uv run --no-sync --quiet --project <dépôt> forever mcp`), `--plugin-dir <dépôt>/plugin` (skills et
   hooks du plugin), `--allowedTools` = `Skill` et les six outils au préfixe **`mcp__forever__`**, `dontAsk`,
   `--permission-prompts none` ; **dossier de travail dédié hors du dépôt** (`<cache>/bridge/conversation/` : ni
   `CLAUDE.md` du dépôt, ni skills de développement, ni hooks du projet). Relevé : 7 outils exactement, un seul serveur
   MCP, skills du plugin présents (`Skill` → `forever:forever-router` ou `forever:forever-mage` selon la question),
   reprise par `--resume` sur la même session, 6 à 15 s par message, quelques centimes.
4. Événements : `system/hook_started`, `system/hook_response`, `system/init` (`tools`, `mcp_servers`, `skills`,
   `session_id`), `assistant` (`thinking`, `tool_use`, `text`), `user` (`tool_result` en texte JSON), `rate_limit_event`,
   `result` (`result`, `session_id`, `is_error`, `permission_denials`, `num_turns`). Fixtures
   `tests/fixtures/bridge/claude_stream_status.jsonl` et `claude_stream_resume.jsonl` (identifiants et chemins
   remplacés).

## Exécution : bloc A (2026-10-08)
- Séquences de cellules et sommes du plan recalculées par le `Codec.lua` de wow-ai sous `lupa.lua51` : conformes.
- Ajouts pour que la sonde en jeu A tranche tout en une session (jalon de l'utilisateur) : addon de sonde
  `ForeverBridge_Probe` (chargé à la demande, `Probe.lua` réécrit en cours de jeu), fichiers de contrôle `flip` (vide
  puis rempli) et `late` (absent puis créé) en `.wav` et `.ogg` (`.ogg` copié d'un addon installé, aucun encodeur),
  `forever bridge selftest --touch`, `/fv diag` étendu ; bande de test pleine (1 792 octets, 24 rangées) affichée deux
  minutes ; `selftest --live --wait --save` détaillé (fenêtre, zone client, premier plan, sonde, cellules fausses).
- Tests Lua du bloc E avancés au bloc A (codec Lua = codec Python, `/fv test` au pixel près à trois résolutions,
  `/fv diag`, pièges) ; capture réelle par l'API de Windows vérifiée sur une fenêtre Tk (vecteur reconnu).
- `install_bridge(wow_dir, slots=0)` : la réserve d'emplacements arrive au bloc B.
- Procédure : `docs/ADDON.md` §7, étape 9.

## Exécution : sonde en jeu A (2026-10-09, relevés de l'utilisateur, captures prises)
1. **Bande lue** : « vecteur reconnu (1792 octets, 24 rangées, 4800 cellules) » ; écran 2 560 × 1 440, échelle de la
   bande 0,5333, échelle de l'interface 0,7111. La capture enregistrée (`tests/fixtures/bridge/band_live.bmp`) ne porte
   que les huit couleurs pures et chaque pixel est égal au centre de sa case : le rendu est au pixel près.
2. **Sons** : `PlaySoundFile` « joue » aussi les fichiers vides (`empty`, `flip`, en `.wav` comme en `.ogg`) ; seul un
   fichier absent au lancement ne joue pas. Autotests `.wav` et `.ogg` en échec : le drapeau vide ou valide de wow-ai
   ne marche pas sur Forever.
3. Après `selftest --touch`, jeu lancé : `late.wav` et `late.ogg` ne jouent pas (un fichier ajouté pendant que le jeu
   tourne n'est pas vu) ; `flip` joue, mais il jouait déjà vide : rien n'est prouvé.
4. `ForeverBridge_Probe` chargé après la modification affiche « modifié à 08:13:00 » : un addon chargé à la demande
   lit bien un fichier modifié pendant que le jeu tourne (chargement après `/reload`).
5. Après redémarrage complet : `late` joue (un fichier présent au lancement est vu) ; la sonde garde « modifié à
   08:13:00 ».

Conclusion : le chemin des réponses par la réserve marche ; seul le signal « réponse prête » manque. Reste à vérifier
en jeu (sonde B) : le **premier** chargement d'un emplacement modifié après le lancement, **sans `/reload`** (le cas
exact de la consultation), et la bande d'une case par pixel.

## Amendement du 2026-10-09 (sonde en jeu A et demandes de l'utilisateur)

Demandes de l'utilisateur du 2026-10-09 : retour par consultation de la réserve comme wow-ai quand son canal son est
inutilisable (lecture de son `docs/ARCHITECTURE.md`, accord réseau du 2026-10-09), 200 emplacements, fenêtre dédiée
reprise de wow-ai, boutons dès P06a, bande d'une case par pixel retirée dès l'accusé, rien dans la discussion
générale. Décision 212 amendée le même jour. Les choix 1, 5, 7, 8 et 13 et les tests marqués plus haut sont remplacés
par ce qui suit ; le reste du plan tient.

### Ce que fait wow-ai sans son (lu le 2026-10-09, `docs/ARCHITECTURE.md` au commit 3756eb5a)
- 200 emplacements `WoWAI_S001`…`S200`, même contenu écrit dans les 200 à chaque publication ; le jeu charge un
  emplacement neuf à 5, 10, 16, 24, 34, 46, 60, 80, 100, 130, 160, 200, 240, 300 s après un envoi, puis toutes les
  60 s ; au repos, un emplacement toutes les 10 min pour le voyant du pont (fenêtres « vu » de 12 et 22 min).
- Les sons ne servent qu'aux raccourcis (« prêt », « reçu », progression, présence) ; un client qui dit « jouera »
  pour un fichier vide fait passer l'addon en consultation seule pour la session : **c'est notre cas sur Forever**.

### R1. Retour par consultation de la réserve (remplace les choix 7 et 8)
- **Après un envoi**, l'addon charge l'emplacement suivant (`C_AddOns.LoadAddOn`) à **3 s**, puis **toutes les 4 s
  jusqu'à 30 s**, puis **toutes les 10 s**, **plafond à 190 s** (délai de la conversation : 180 s ; le pont publie
  alors une erreur). Au plus 24 consultations par message ; une réponse de 6 à 15 s en coûte 3 ou 4.
- **Marqueur « pas encore prêt »** : dès qu'il lit la bande, le pont publie une entrée `{ session, id, status =
  "working", since }` ; puis `done` (texte, provenance, lien) ou `error` (raison). L'addon vide la globale
  `ForeverBridgeSlot` avant chaque chargement et ignore une entrée d'une autre session.
- **Accusé de réception** = premier relevé qui porte le message (`working`, `done` ou `error`) : la bande est retirée
  aussitôt. **Trois relevés sans accusé** (3, 7, 11 s) : bande retirée, message mis dans la boîte d'envoi, erreur
  expliquée (« pont injoignable : lancez `uv run forever bridge start`, puis tapez /reload »), plus aucune
  consultation pour ce message.
- **Un seul message en vol** : un envoi suivant attend l'accusé du précédent (file locale, montrée « en attente »).
- **Emplacement annoncé** : chaque message porte le numéro du prochain emplacement que le jeu chargera (`slot`) ; le
  pont écrit à chaque publication dans les emplacements `slot` à 200 et dans `ForeverBridge/Inbox.lua` ; numéro
  inconnu (démarrage du pont, boîte d'envoi) : toute la réserve. Le compteur de l'addon repart à 1 à chaque `/reload`
  (non sauvegardé), comme la réserve.
- **Publication** : au démarrage du pont, à chaque changement d'état d'un message, et toutes les 10 min (état des
  données, `now`), toujours atomique fichier par fichier.
- **Au repos** : un relevé toutes les 10 min, **fenêtre ouverte seulement**, et un à l'ouverture de la fenêtre si le
  dernier date de plus de 2 min ; « pont vu il y a N min » vient du champ `now` du dernier relevé (même horloge).
- **Réserve** : **200 emplacements** `ForeverBridge_S001`…`S200` (`--slots` de 8 à 200). À **10 restants**, la ligne
  d'état propose `/reload` (jamais automatique) ; **réserve vide** pendant une attente : « réponse au prochain
  /reload », lue dans `ForeverBridge/Inbox.lua` au `/reload` (chemin de secours) ; un emplacement qui ne se charge
  pas (`MISSING`, `DISABLED`…) est sauté et compté.
- **Aucun son dans le chemin de P06a** : ni `sig/` ni `ack/` ; `ctl/` et `/fv diag` restent comme diagnostic. Contenu
  d'un emplacement : `ForeverBridgeSlot = { v = 1, now, status = {…}, buttons = {…}, replies = { … dix dernières … } }`.

### R2. Bande (remplace le choix 5 ; choix 4 précisé)
- **Une case par pixel physique** par défaut : bande de test de 200 × 24 pixels, message de 200 × N. Repli `/fv test
  N` (N de 1 à 4) pour la bande de test, réglage `/fv case N` gardé dans `ForeverBridgeDB.cell` pour les messages.
  Capture : 8 couleurs exactes et pixels égaux au centre de leur case (sonde A), d'où le pari d'une case par pixel.
- Le pont reconnaît la taille de case sur la sonde (20 × 4 pixels inchangée : marqueur cherché pour une case de 1, 2,
  3 puis 4 pixels), puis ne lit que le rectangle de la bande à cette taille (`band_rect(client, cell_px)`, 200 × 24 à
  une case par pixel) ; la somme de contrôle écarte une fausse détection.
- **Coin haut gauche** de la zone client (seul coin prouvé, à l'abri de la barre de titre de la fenêtre).
- **Montrée de l'envoi à l'accusé** (R1), jamais plus ; `/fv test` reste deux minutes (diagnostic demandé).

### R3. Fenêtre dédiée (bloc E ; squelette avancé au bloc A2)
- **Reprise de wow-ai** (`BuildUI`, cadre `BackdropTemplate`, glisser, poignée de redimensionnement, ligne d'état,
  saisie avec « Envoyer » accolé, zone copiable), adaptée : une seule conversation (ni liste de conversations, ni
  agents, ni Allow, ni macros, ni barre réduite), notice MIT déjà en tête de `ForeverBridge.lua`. Historique dans un
  `ScrollingMessageFrame` de Blizzard (défilement à la molette, retour à la ligne au redimensionnement, liens
  cliquables) plutôt que les bulles de wow-ai : plus court, plus sûr.
- Déplaçable, redimensionnable (bornes 360 × 240), **position et taille dans `ForeverBridgeDB.window`** ; ouverte et
  fermée par `/fv` (et `/forever`) et par un **raccourci configurable** (`Bindings.xml`, Options > Raccourcis >
  AddOns > ForeverBridge) ; **Échap ferme** (`UISpecialFrames`) ; strate `DIALOG`, cadres et polices de Blizzard
  (style sobre, compatible EllesmereUI qui habille les cadres standard) ; rien de protégé.
- **Historique** : questions (« Vous », bleu) et réponses (« Forever », or) distinguées, une ligne vide entre deux
  messages, 50 derniers messages gardés dans `ForeverBridgeDB.history`.
- **Mise en forme restreinte** (remplace « texte brut » du choix 13) : la réponse peut contenir des lignes `## titre`,
  `- élément` et des passages `**en évidence**`, rien d'autre ; le pont normalise toute autre syntaxe (`#`, `###`,
  `* `, `__…__`, accents graves, tableaux) avant publication ; l'addon rend les titres en or, les éléments avec une
  puce, la mise en évidence en blanc vif. 600 caractères au plus, hors mise en forme.
- **Lien Talents Forever** : ligne `[Talents Forever]` cliquable (lien `|Hforeverbridge:copy:N|h`, géré par le
  `OnHyperlinkClick` de l'historique, jamais `SetItemRef`) qui ouvre la zone copiable, texte présélectionné (Ctrl+C).
- **Saisie** : Entrée envoie, **Maj+Entrée passe à la ligne** (`IsShiftKeyDown`), Échap ôte le focus ; 255
  caractères ; bouton « Envoyer » ; bouton **« Nouvelle conversation »** (drapeau `n` sur le message suivant, trait
  de séparation dans l'historique).
- **Indicateur d'état toujours visible** : voyant (vert : pont vu depuis moins de 12 min ; jaune : 12 à 22 min ;
  rouge : jamais vu ou injoignable), « réponse en cours » animé (points qui tournent, secondes écoulées), erreur
  expliquée (pont injoignable, délai dépassé, réserve vide, bande refusée), réserve restante ; **ligne d'état des
  données** (version, fraîcheur, attentes de `forever update`).
- **Rien dans la discussion générale** : aide, bande de test, réponses et erreurs vont dans la fenêtre ; seul `/fv
  diag`, demandé par le joueur, écrit ses lignes dans la discussion (diagnostic seulement, comme le demande
  l'utilisateur). Test : aucune ligne écrite dans `DEFAULT_CHAT_FRAME` sur tous les scénarios hors `/fv diag`.
- **Aucune ouverture automatique** : une réponse qui arrive fenêtre fermée allume un compteur sur le voyant et ne
  l'ouvre pas, en combat comme hors combat.

### R4. Boutons dès P06a (déplacés de P06b)
- Barre au-dessus de la saisie ; chaque bouton envoie sa **question fixe** par le même chemin que le chat (même
  bande, même conversation, réponse dans l'historique). Liste écrite par le pont dans chaque publication et dans
  `Status.lua` (`buttons`) : **l'addon n'affiche que ce que le pont envoie** (aucun bouton avant le premier état lu).
- Table `forever/bridge/buttons.py` ; tranches faites **fixées au plan** : T04b, T04c, T05, FA1, CH0, PV1 (ROADMAP du
  2026-10-09). Filtre de classe **validé par l'utilisateur le 2026-10-09** : un bouton n'apparaît que pour les classes
  que sa tranche sert.

  | Bouton | Question envoyée | Tranches | Classes |
  | --- | --- | --- | --- |
  | Talents | Mage : « Quel est mon prochain talent, avec le lien Talents Forever ? » ; autres classes : « Quel build populaire de Talents Forever est le plus proche de mes talents actuels ? Donne son lien Talents Forever. » | FA1, T05 | toutes |
  | Leveling | « Quel est mon prochain objectif de leveling ? » | T04b, T04c | Mage |
  | Familiers | « Où apprivoiser le prochain rang utile près de moi ? » | CH0 | Chasseur |
  | PvP | « Fiche de la classe de ma cible » | PV1 | toutes (cible joueur requise) |

- **Talents hors Mage** (demande de l'utilisateur du 2026-10-09) : build populaire le plus proche, avec son lien
  Talents Forever, **en disant clairement qu'il n'est pas encore calculé par le moteur**. Garanti sans dépendre du
  modèle : le message porte le bouton d'origine (drapeau `b=talents`) et, pour une classe autre que le Mage, le pont
  ajoute à la réponse la ligne fixe « Build populaire de Talents Forever (choix de joueurs), pas encore calculé par
  le moteur de forever. » (certitude `suppose`, celle de `tf_popular`). Outil : `forever_lookup(kind="tf_popular",
  name=<classe>, current=<talents du contexte>)` gagne au bloc C un champ `closest` calculé par `closest_popular`
  (`forever/talents_forever.py`, déjà utilisé pour le Mage) ; conversion des nœuds du contexte (`nœud:rang` de
  `C_Traits`) en talents de la classe à vérifier au bloc C ; à défaut, build le plus populaire de la spécialisation
  la plus chargée, avec une note. Tests : `test_bridge_buttons.py` (Talents visible pour les neuf classes, question
  du Mage et des autres), `test_bridge_loop.py` (ligne fixe ajoutée hors Mage, absente pour le Mage),
  `test_mcp_*` (`closest` rendu avec `current`).

- Absents en P06a : « Mettre à jour », Valider, Refuser (P06b) ; Équipement (T10a) ; Analyse du dernier combat (AN1,
  AN2). Le contexte gagne `target` (jeton de classe de la cible si c'est un joueur, sous `pcall` et `issecretvalue`).

### R5. Piste des polices (wow-forever-codex, lue le 2026-10-09 : README et `docs/`, commit 85953db)
- Principe : un fichier de police par emplacement, présent au lancement ; le pont réécrit le fichier que le jeu lira
  ensuite ; l'addon l'affecte par `SetFont`, mesure des largeurs de glyphes (`GetStringWidth`) et en tire 512 octets
  (somme de contrôle). Mesuré par eux sur Forever 1.60.1.69913 : un nom de police jamais chargé lit le fichier
  modifié ; un nom déjà chargé garde l'ancien contenu jusqu'au redémarrage complet (même après `/reload`) ; un fichier
  créé en cours de jeu n'est pas vu ; banque de 65 535 noms par liens physiques (NTFS).
- **Utilisable sur Forever** d'après leurs mesures (non revérifié ici) : chaque vérification « est-ce prêt ? » brûle
  un nom de police au lieu d'un emplacement d'addon, donc une consultation par seconde deviendrait possible sans
  toucher la réserve. **Pas pour P06a** : le dépôt n'a **aucune licence** (rien ne peut être repris, réécriture
  complète), il faut écrire des polices TrueType valides sans dépendance (ou en ajouter une, accord requis), mesurer
  sous toutes les échelles d'interface, et le compteur de noms doit survivre aux redémarrages. Piste notée pour P06b
  (question ouverte BR4).

### Blocs revus
- **Bloc A2 (avant la sonde B)** : taille de case reconnue par le pont (1 à 4), `/fv test N` (1 par défaut), squelette
  de la fenêtre (cadre, titre, voyant, ligne d'état, historique, fermeture, Échap, glisser, redimensionner, position
  gardée, `Bindings.xml`), aide et messages de `/fv test` dans la fenêtre, `ForeverBridge_Probe2` et `/fv poll`
  (premier chargement sans `/reload`), test de non-régression sur `band_live.bmp`, client simulé fidèle à Forever.
- **Bloc B** : `record.py` (champ `slot`), `slots.py` (200 emplacements, `publish` à partir de l'emplacement annoncé,
  sans drapeaux), `install.py` (réserve, `Inbox.lua` d'attente), `buttons.py`, `format.py` (mise en forme
  restreinte).
- **Bloc C** : inchangé (consignes : mise en forme restreinte).
- **Bloc D** : publication des états `working`, `done`, `error` ; rafraîchissement toutes les 10 min ; boîte d'envoi.
- **Bloc E** : consultation (R1), fenêtre complète (R3), boutons (R4), contexte (`target`).

### Interfaces modifiées
```python
# forever/bridge/codec.py
CELL_PX = 4                      # plus grande case lue (rectangle de la sonde : 20 × 4)
CELL_SIZES = (1, 2, 3, 4)        # tailles reconnues, dans cet ordre
def render_band(cells, cell_px: int = CELL_PX) -> Image: ...
def detect_cell_px(image: Image) -> int | None: ...    # marqueur reconnu à cette taille, sinon None
def marker_present(probe: Image) -> bool: ...           # à n'importe quelle taille de CELL_SIZES
def decode_band(image: Image, cell_px: int | None = None) -> Decoded | BandError | None: ...
def cell_values(image: Image, rows: int, cell_px: int = CELL_PX) -> list[int]: ...
def cell_mismatches(image: Image, expected, cell_px: int | None = None) -> list[...]: ...
# forever/bridge/capture.py
def band_rect(client: Rect, cell_px: int = CELL_PX) -> Rect | None: ...
# forever/bridge/slots.py
SLOTS = 200
def slot_name(index: int) -> str: ...            # 1 -> "ForeverBridge_S001"
def publish(addons_dir: Path, inbox: str, slots: int = SLOTS, first: int = 1) -> int: ...
# forever/bridge/buttons.py
DONE_SLICES: frozenset[str]
@dataclass(frozen=True)
class Button: key: str; label: str; question: str; requires: tuple[str, ...]; classes: tuple[str, ...] | None
def visible_buttons(done: AbstractSet[str] = DONE_SLICES) -> list[Button]: ...
# forever/bridge/format.py
def normalize_reply(text: str) -> str: ...      # garde ## , - , **…** ; convertit ou retire le reste
```
Côté Lua : `FB.Toggle()`, `FB.Poll(why)`, `FB.Schedule()`, `FB.Render()`, `FB.Format(text)`; `ForeverBridgeDB = {
schema = 1, session, next_id, history, outbox, window = { point, relPoint, x, y, width, height }, cell }`.

### Tests remplacés ou ajoutés
- `test_bridge_codec.py` : détection de la taille (une bande dessinée à 1, 2, 3 et 4 pixels se relit, `detect_cell_px`
  rend la taille, une image noire rend `None`) ; aller-retour à une case par pixel ; `band_live.bmp` se relit en
  vecteur de test, taille 4 détectée (non-régression de la sonde A).
- `test_bridge_capture.py` : `band_rect(Rect(100, 50, 1920, 1080), 1) == Rect(100, 50, 200, 24)`.
- `test_bridge_selftest.py` : bande vivante à une case par pixel reconnue, ligne « case de 1 pixel ».
- `test_bridge_slots.py` (remplace la section du plan) : `slot_name(1) == "ForeverBridge_S001"`, `slot_name(200) ==
  "ForeverBridge_S200"` ; `publish(…, slots=200, first=37)` écrit `S037` à `S200` et `ForeverBridge/Inbox.lua` (165
  fichiers), sans `.tmp` restant ; `first` absent : 201 fichiers ; plus de `raise_signal`, `lower_ahead`, `lower_all`.
- `test_bridge_install.py` (bloc B) : `install_bridge(tmp, slots=8)` crée `ForeverBridge_S001` à `S008` (`.toc` avec
  `## LoadOnDemand: 1`, `## Dependencies: ForeverBridge`, `Inbox.lua` d'attente `ForeverBridgeSlot = { v = 1, now =
  0, replies = {} }`) et aucun `sig/` ni `ack/` ; `slots=7` ou `201` → erreur nommée ; par défaut 200.
- `test_bridge_record.py` : champ `slot` lu et écrit ; absent → `None`.
- `test_bridge_buttons.py` : les quatre boutons visibles avec `DONE_SLICES` ; un bouton dont une tranche manque
  (Équipement T10a, Analyse AN1) absent ; « Mettre à jour » absent ; classes du tableau.
- `test_bridge_format.py` : `# T` et `### T` → `## T` ; `* x` → `- x` ; `__x__` → `**x**` ; accents graves retirés ;
  tableau → lignes ; texte déjà conforme inchangé.
- `test_bridge_addon_lua.py`, cas remplacés : (6) premier relevé à 3 s portant `working` → bande cachée, « en cours »
  affiché ; (8) relevé portant `done` → réponse affichée, une seule réponse, plus de consultation ; (10) calendrier
  exact des chargements (3, 7, 11, 15, 19, 23, 27, 30, 40 … 190 s) et rien après 190 s ; ajoutés : trois relevés sans
  accusé → bande cachée, boîte d'envoi, erreur ; 10 emplacements restants → `/reload` proposé ; réserve vide →
  « réponse au prochain /reload », puis `Inbox.lua` appliqué au chargement suivant ; entrée d'une autre session
  ignorée ; aucune ligne dans la discussion générale hors `/fv diag` ; fenêtre (`/fv` bascule, `UISpecialFrames`,
  position et taille restaurées, `BINDING_NAME_FOREVERBRIDGE_TOGGLE` défini, Entrée envoie, Maj+Entrée insère un
  saut de ligne, « Nouvelle conversation » pose `n`) ; boutons : seuls ceux du pont et de la classe, un clic envoie la
  question fixe ; réponse arrivée fenêtre fermée (en combat ou non) : fenêtre non ouverte ; rendu de `##`, `-`,
  `**` ; lien copiable ; bande d'un pixel par case (`/fv test`) et de deux (`/fv test 2`).
- Client simulé (accord de l'utilisateur du 2026-10-09, sonde A) : un fichier son présent au lancement « joue », vide
  ou non ; un fichier ajouté ensuite n'est jamais vu ; `test_fv_diag_reports_each_control_file` et
  `test_fv_diag_sees_files_changed_while_the_game_runs` corrigés en conséquence.

### Procédures en jeu
- **Sonde B** (avant le bloc B) : `docs/ADDON.md` §7, étape 10.
- **Procédure du chat** (fin de tranche) : `docs/ADDON.md` §7, étape 11 (remplace le critère de fin 6).

### Exécution : bloc A2 (2026-10-09)
- Tests dans `tests/unit/test_bridge_cells.py` (taille de case, `band_live.bmp`, bande vivante à 1 et 2 pixels :
  ce dernier point était prévu dans `test_bridge_selftest.py`), `test_bridge_window_lua.py` (fenêtre, `/fv test N`,
  `/fv poll`, rien dans la discussion générale) et `test_bridge_install_a2.py` (`ForeverBridge_Probe2`,
  `Bindings.xml`).
- Sonde du premier chargement sans `/reload` : `ForeverBridge_Probe2`, chargé seulement par `/fv poll`, réécrit par
  `selftest --touch` après le lancement (`docs/ADDON.md` §7, étape 10).
- `/fv diag` est la seule commande qui écrit dans la discussion générale (lecture de « les diagnostics seulement sur
  /fv diag ») ; le basculer dans la fenêtre tient en une ligne (`ChatSay` → `FB.Print`) et une assertion.
- Corrections de tests accordées par l'utilisateur le 2026-10-09 : client simulé fidèle à Forever pour les sons (deux
  tests du diagnostic) ; harnais `Game` qui convertissait `saved` sans récursion (`table_from(saved,
  recursive=True)`), une table imbriquée arrivant sinon en `userdata`.

### Exécution : sonde en jeu B (2026-10-09, relevés de l'utilisateur)
- `/fv poll` : « modifié à 09:01:46 » : **BR1 résolue** (premier chargement sans `/reload` relu ; consignée dans
  `docs/RESOLVED_QUESTIONS.md`). Bande d'une case par pixel lue (« case de 1 pixel », 2 560 × 1 440), capture en
  non-régression (`band_live_1px.bmp`). Fenêtre : tout marche sauf le raccourci, pas encore essayé.
- Corrigé le même jour : aide affichée deux fois (jamais répétée désormais), fond trop transparent (opaque par défaut,
  `/fv fond N` de 30 à 100, gardé dans `ForeverBridgeDB.window.alpha`), `/fv diag` sans rien de visible (même code
  qu'à la sonde A ; la fenêtre couvrait sans doute la discussion : confirmation dans la fenêtre et erreur Lua montrée).

### Bloc B revu (2026-10-09, demande de l'utilisateur : la saisie et la barre de boutons dans P06a)
Le bloc B porte le message **des deux côtés**, pour qu'une question tapée en jeu soit lue par le pont dès sa fin
(sonde C) :
- Python : `record.py` (champs `1`, session, numéro, drapeaux `n`, `h`, `b=<bouton>`, `slot`, contexte, texte),
  `slots.py` (200 emplacements, `publish` à partir de `first`, `lua_string`, `inbox_lua`, `status_lua`),
  `install.py` (réserve `ForeverBridge_S001`…, `Inbox.lua` d'attente écrit seulement s'il manque ; `--slots`),
  `buttons.py`, `format.py`, `forever bridge selftest --live --message` (décode n'importe quel message de la bande et
  l'affiche : numéro, drapeaux, emplacement, clés du contexte, texte ; rien n'est gardé).
- Lua : `Message.lua` (contexte du personnage sous `pcall` et `issecretvalue`, charge, allègement dans l'ordre du
  choix 6), **zone de saisie** (Entrée envoie, Maj+Entrée passe à la ligne, Échap ôte le focus, 255 caractères),
  boutons « Envoyer » et « Nouvelle conversation », **barre de boutons** d'après `ForeverBridgeStatus.buttons`
  (`Status.lua`, écrit par le pont au bloc D ; fichier d'attente sans bouton d'ici là), envoi par la bande avec le
  numéro du prochain emplacement. **Provisoire jusqu'au bloc E** : sans consultation de la réserve, la bande est
  retirée au bout de 30 s ou par l'envoi suivant, et la fenêtre dit « réponse au bloc E ».
- Bloc E : consultation (R1), accusé, réponses mises en forme, lien copiable, voyant et état des données.

### Exécution : bloc B (2026-10-09)
- Tests : `test_bridge_record.py`, `test_bridge_slots_b.py`, `test_bridge_install_slots.py`, `test_bridge_buttons.py`,
  `test_bridge_format.py`, `test_bridge_selftest_message.py`, `test_bridge_send_lua.py` ; retours de la sonde B dans
  `test_bridge_window_fixes_lua.py`.
- Allègement : les talents sont retirés en dernier recours, après l'équipement (la question n'est jamais coupée) ;
  ajout au choix 6, sans effet sur un message type.
- Défaut trouvé par les tests : la ligne d'état de la fenêtre portait le nom global `ForeverBridgeStatus`, celui de
  l'état écrit par le pont (renommée `ForeverBridgeStatusLine`).
- Correction de test accordée par l'utilisateur le 2026-10-09 : message type avec une question de 255 caractères sans
  accent (comme le plan) ; tests ajoutés à sa demande : question réaliste en français, accents compris, qui tient
  avec le contexte complet (pont et addon).
- Sonde en jeu C : `docs/ADDON.md` §7, étape 12 (avant l'étape 11).
- `/fv case N` livré (R2). À faire au bloc E : `run.nextSlot` mis à 1 à la connexion et augmenté à chaque
  `LoadAddOn` d'un emplacement ; d'ici là, `FB.Send` annonce toujours l'emplacement 1.

### Exécution : sonde en jeu C et blocs C à F (2026-10-09)
- Sonde C (relevés de l'utilisateur) : message lu (576 octets, case d'un pixel, emplacement 1, contexte attendu, texte
  exact) ; BR3 résolue (démarrage pas plus long) ; `/fv diag` visible.
- Corrections de tests accordées le 2026-10-09 : `test_band_is_provisional_until_block_e` remplacé par
  `test_band_is_removed_at_the_acknowledgement` ; `test_subprocess_only_in_gitops_and_the_detached_launch` gagne
  `bridge/agent.py`, avec les assertions demandées (aucun shell, un seul exécutable, options de restriction). Deux
  commits de lint seulement sur des tests (annotation `ClassVar`, variable inutilisée, ordre des imports).
- Bloc C : `agent.py` (ligne de la sonde 0.4, liste d'arguments, question sur l'entrée standard, objet de tâche Windows
  pour arrêter l'arbre au-delà du délai, reprise refusée relancée en nouvelle session), `prompt.py`, hook muet sous
  `FOREVER_BRIDGE` ; `claude` 2.1.295 accepte toutes les options (aide relue hors réseau). Fixtures écrites à la main :
  refus d'outil, `forever_build` avec lien.
- Bloc D : `loop.py` (conversation sur un fil à part, un message à la fois ; publication à partir de l'emplacement du
  message le plus récent, toute la réserve et `Status.lua` toutes les 10 min ; boîte d'envoi relue au changement de la
  sauvegarde, emplacements depuis 1 pour elle), `journal.py`, `state.py` (un seul `state.json` au lieu de
  `sessions.json`), `status.py`, `forever bridge start | run | stop | status | ask` (`ask` : la conversation sans le
  jeu, étape 0 de la sonde E).
- Bloc E : calendrier R1, accusé, rendu des réponses (texte du pont ramené au brut puis neutralisé une seule fois),
  zone copiable, boîte d'envoi, réserve, consultation relancée après `/reload`, historique gardé, état publié avec la
  taille de la réserve. Plusieurs envois rapprochés : chaque message sans accusé garde sa bande à tour de rôle.
- Bloc F : `docs/ARCHITECTURE.md`, `docs/USAGE.md` (« Chat en jeu »), `addon/README.md`, `docs/ADDON.md` (§5, §6,
  §9, §10 Crédits), `docs/VISION.md` (Crédits), `CLAUDE.md` (le pont lance `claude`), `test_bridge_license.py`.
- **Reporté après la fusion** (première suite de P06a, décision de l'utilisateur du 2026-10-09 : fusion après les corrections de la sonde E) : `forever_lookup(kind="tf_popular", current=…)` et son champ
  `closest` pour le bouton Talents hors Mage (R4) ; d'ici là, l'agent choisit parmi les builds populaires et le pont
  ajoute la mention fixe.
- Sonde E : `docs/ADDON.md` §7, étape 11.

### Exécution : sonde en jeu E et ses retours (2026-10-09)
- Sonde E (relevés de l'utilisateur) : le chat marche de bout en bout (question, réponse mise en forme, boutons
  Talents, Leveling, PvP, voyant vert, lien copiable). Défauts corrigés le même jour (décision 213) :
  1. talents du jeu (`105778:5,105779:5`) reliés aux clés de forever par `classes.json` (Elemental Precision 5/5 et
     Improved Frostbolt 5/5 : 5 rangs chacun sur Forever) et donnés à la conversation (`forever/bridge/context.py`),
     testé sur le contexte réel (`tests/fixtures/bridge/context_sonde_e.txt`) ;
  2. égalités : `forever build` affichait un build que sa propre comparaison départageait en faveur de l'alternative
     (écart non significatif) ; la CLI partait du préréglage complet, le MCP du rapide. Même défaut (rapide),
     `alternative.tie` et lien de l'alternative, consigne « présenter les deux options » ;
  3. zone copiable déplaçable, ouverte à droite de la fenêtre ; 4. cible : niveau (`??` si caché) et race en plus de
     la classe ; 5. « Nouvelle conversation » vide la fenêtre, l'historique part dans `ForeverBridgeDB.archive` (cinq
     conversations) ; 6. ligne d'état « Données 1.60.1.70245 · client 1.60.1.70291 : mise à jour en attente · 3 mises à
     jour à valider sur le PC » ; 7. durées et coût dans le journal, modèle réglable (Sonnet par défaut).
- Mesures (journal de la sonde E, modèle par défaut de Claude Code) : 14 à 31 s de la lecture de la bande à la
  réponse. Comparaison du 2026-10-09 (contexte réel, six questions, ligne du pont) : Sonnet 10 à 20 s, 0,03 à 0,10 $
  par réponse ; Haiku 11 à 30 s, 0,002 à 0,01 $. Décomposition (Sonnet) : démarrage de `claude` et du serveur MCP
  2,2 s (6 s à froid), outils 0,3 à 12 s (`forever_build` 5 à 6 s, `forever_lookup` des builds populaires 6,5 s),
  modèle 7 à 9 s ; lecture de la bande et écriture de la réserve négligeables (0,1 s pour 200 emplacements) ; attente
  du relevé suivant : au plus 4 s avant 30 s, au plus 10 s ensuite.
- Recommandation : **Sonnet** (défaut). Haiku n'est pas plus rapide ici, et sa réponse au bouton Talents était
  confuse (lien refusé) ; il suffit pour PvP et les questions simples, pas pour Talents. Aucun chiffre hors outils
  relevé chez l'un ou l'autre (Purge, Earth Shock et War Stomp de Haiku viennent bien de la fiche du Chaman).
- Accélérations proposées, non faites : relevés toutes les 4 s jusqu'à 60 s (au lieu de 10 s après 30 s : jusqu'à
  6 s gagnées, environ 4 emplacements de plus par réponse longue) ; réflexion du modèle coupée
  (`MAX_THINKING_TOKENS=0`, à mesurer) ; boutons qui nomment l'outil à appeler (moins d'appels, pas de `Skill`) ;
  conversation `claude` gardée ouverte (`--input-format stream-json`, environ 2 s par message, P06b).
- Sonde F (rejouer les corrections, fenêtre fermée après un envoi, secours) : `docs/ADDON.md` §7, étape 13.

### Questions ouvertes ajoutées (`docs/OPEN_QUESTIONS.md`, section « Pont en jeu »)
BR1 premier chargement d'un emplacement sans `/reload` ; BR2 bande d'une case par pixel à toutes les échelles ; BR3
effet de 200 addons chargés à la demande sur le démarrage et la liste des addons ; BR4 canal par polices.

## Validation
Plan à valider par l'utilisateur. Exécution dans une nouvelle session (`/tranche P06a`), branche `p06a`, un cycle
rouge → vert par bloc.
