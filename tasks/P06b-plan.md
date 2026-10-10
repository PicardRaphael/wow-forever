# P06b — Deuxième moitié du chat en jeu : plan

Tranche de `docs/ROADMAP.md` (section P06b), suite de P06a (`tasks/P06a-plan.md`, décisions 197, 202, 212, 213, 224,
225, 226, 227). Plan écrit le 2026-10-10 ; aucun code ici. **À finir avant la fin de la bêta, le 2026-10-21** : tout
ce qui demande le jeu se joue avant (sondes en jeu G et H).

## Demande de l'utilisateur (lancement de la tranche, 2026-10-10)
1. Bouton « Mettre à jour » : `forever update` lancé par le pont ; état des données toujours visible (version des
   données et du client, fraîcheur, attentes) ; une attente s'affiche en jeu avec son résumé (PNJ et builds touchés,
   changements de version, attente réseau ou correctifs à lire) et, **seulement pour les attentes approuvables**, deux
   boutons Valider et Refuser (approbation différée).
2. Liens par Maj+clic (objets, sorts, quêtes) insérés dans la zone de saisie, infobulle lue et envoyée ; lien d'objet
   complet (enchantement, suffixe aléatoire) ; l'équipement n'est jamais retiré du message.
3. Écart entre le jeu et le profil (décision 122) signalé, mise à jour du profil proposée, rien d'écrit sans accord.
4. Export de l'addon SimulationCraft collé dans une zone qui accepte un texte long, envoyé en plusieurs messages et
   réassemblé par le pont ; le pont lit talents, objets et fiche du personnage (puissance des sorts, critique, toucher,
   hâte, régénération, buffs) et propose la mise à jour du profil en signalant chaque écart.
5. Conversation « addons » limitée au dossier de RaphCompletionist, sans `git push` ni suppression.
6. Talents des autres classes : le build populaire le plus proche des talents actuels est **calculé par l'outil**,
   pas choisi par le modèle.
7. Réponses plus rapides : mesurer la réflexion coupée (`MAX_THINKING_TOKENS=0`), une session `claude` gardée ouverte
   entre les messages, un premier relevé de la réserve plus tôt ; garder ce qui accélère sans dégrader la qualité.
8. Banc d'essai : chaque nouvelle fonction testée sur les contextes réels relevés par le pont ; procédure de test en jeu
   dans `docs/ADDON.md`.

Hors de cette tranche, et confirmé par la demande : les boutons « Simuler » et « Est-ce une amélioration ? »,
appuyés sur une vraie simulation, restent dans SIM1.

## Réponses de l'utilisateur (2026-10-10)
1. **Conversation « addons », réversibilité** : avant chaque tour, le pont **copie le dossier** dans le cache.
   Après chaque tour, il **committe lui-même** dans un dépôt git local qu'il tient (historique et différences faciles
   à relire et à annuler). L'agent **n'a aucun shell** : seulement Read, Glob, Grep, Edit et Write, limités au
   dossier. `forever bridge addons restore` remet une copie en place. Demande jointe : vérifier si la source de
   RaphCompletionist est dans le projet ForeverCompletionist (dossier `completionist`), que l'utilisateur déplace dans
   ses Documents ; si oui, travailler dans ce projet puis déployer vers le dossier des addons, au lieu de modifier le
   dossier installé (constat plus bas).
2. **Profil, schéma 3** : le profil gagne l'équipement (`gear`, liens complets) et la fiche du personnage (`sheet`).
   Quand le profil n'existe pas, sa création est proposée depuis le jeu et n'est écrite qu'après le clic sur Valider.
3. **Résumé d'une attente rédigé par le pont** (texte fixe tiré des champs de l'attente : instantané, gratuit, sans
   erreur de modèle) ; la ligne de la ROADMAP qui confiait le résumé à la conversation « jeu » est corrigée. À côté, un
   bouton **« Expliquer »** envoie ce résumé à la conversation « jeu » pour une explication détaillée.
4. **Mesure des accélérations** : accord pour environ 48 conversations `claude` (6 questions × 4 variantes × 2
   passages, environ 2 à 5 $), à l'exécution.

## Constat du plan

### RaphCompletionist et ForeverCompletionist (lu sur disque le 2026-10-10)
- `…\_classic_beta_\Interface\AddOns\RaphCompletionist\` : `RaphCompletionist.toc` et `_Camelot.toc`
  (`## Interface: 16001`, version 0.2.1, `RequiredDeps: RXPGuides`, `SavedVariables: RaphCompletionistDB`),
  `Core.lua`, `Collector.lua`, `QuestieBridge.lua`, `ProfessionBridge.lua`, `Guides\` ; **aucun `.git`**.
- `ForeverCompletionist\` ne contient **aucun Lua** : c'est un outil d'inventaire en Python (`completionist/cli.py`,
  `inventory.py`, `model.py`, `source_importers/lua_data.py`, `tests/`, `baseline.json`, `LOCAL_INVENTORY.md`).
  RaphCompletionist y est **un addon inventorié parmi d'autres** (7 fichiers, 31 954 octets), pas un produit de ce
  projet. **La source de RaphCompletionist est donc le dossier installé lui-même.**
- Conséquence : par défaut, la conversation « addons » travaille dans le dossier installé. Le dossier source est
  réglable (`forever bridge addons config --source <dossier> [--deploy <dossier installé>]`). Si un projet source est
  créé plus tard dans les Documents, le pont y travaille et **déploie** après chaque tour : il copie les fichiers
  ajoutés ou modifiés vers le dossier installé, sans jamais en supprimer ; un fichier absent de la source est
  seulement signalé. Aucun chemin de ForeverCompletionist n'est écrit en dur (l'utilisateur le déplace).
- `RequiredDeps: RXPGuides` : RestedXP n'est plus installé (2026-10-07) et reste exclu comme source (décision 227).
  RaphCompletionist ne se charge donc probablement plus : c'est un bon premier sujet pour la conversation « addons ».
  La conversation ne lit jamais les dossiers des addons de la communauté (décision 196) ; si elle a besoin de l'API
  de RXP, le joueur colle l'extrait voulu dans le message.

### Export SimulationCraft (addon lu sur disque, `Interface/AddOns/Simulationcraft`)
- Version 12.1.5-alpha-01 (2026-10-09), TOC `120100, 120105, 16001`, licence **Unlicense**. Sur Forever, ce sont
  `core.lua` et `forever/stats.lua` qui écrivent l'export. Notre addon ne l'appelle jamais : le joueur copie le texte
  de `/simc` (cadre `SimcEditBox`, sans limite de longueur) et le colle dans notre zone.
- **Forme** :
  - en-tête `# <Nom> - <date> - <region>/<royaume>`, `# SimC Addon <version>`, `# WoW <version>.<build>, TOC <toc>` ;
  - `<classe>="<Nom>"`, `level=`, `race=`, `region=`, `server=`, `role=` (peut être vide) ;
  - `professions=` (sinon une **ligne vide**), `spec=` (`unknown` attendu sur Forever, valeur à ne pas figer) ;
  - `talents=<C_Traits.GenerateImportString>` : chaîne d'import opaque de Blizzard, ou le commentaire
    `# Unable to export talents…` si le client n'a pas encore les données ;
  - par objet, deux lignes : `# <Nom> (<ilvl>)` puis `<slot>=,id=…,enchant_id=…,gem_id=a/b,bonus_id=…` (une virgule
    juste après `=`) ;
  - bloc facultatif `### Gear from Bags` (lignes commentées) ;
  - `### Additional Character Info`, puis des lignes `# clé=a:v/b:v`, dans un ordre fixe : `character_stats`,
    `_base`, `_bonus`, `_gear`, `attack_power`, `spell_power` (holy, fire, nature, frost, shadow, arcane),
    `spell_stats`, `regen`, `crit`, `hit`, `haste`, `combat_modifiers`, `combat_ratings` (`nom:notation:bonus`),
    `defense`, `resistances`, `weapon_damage`, `pet_*`, `skills=`, `buffs=spellID:cumuls/…` ; un champ dont l'API
    manque est omis, d'où des lignes vides comme `# hit=` ;
  - en dernière ligne, `# Checksum: <hex>` : adler32 de tout le texte qui précède, `\n` final compris, après
    `||`→`|`, hexadécimal minuscule sans zéros de tête.
- **Manques de l'export**, que le contexte du jeu comble :
  - **aucun suffixe aléatoire** (offset 7 non lu) ;
  - **emplacement à distance (18) absent** (`slotNames` sans `RangedSlot`, à confirmer en jeu) ;
  - talents sous une forme opaque.
- Taille estimée : 4 à 7 k caractères sans les sacs, 10 à 15 k avec. En UTF-8 (nom du personnage, noms d'objets).
  Aucun `|` hors du mode `debug`.

### forever-core
- **Profil** (`forever/profile.py`, schéma 2) : champs sourcés `class`, `race`, `faction`, `level`, `talents`,
  `professions`, `talent_nodes`, `quests_completed` ; fusion `merge_field` (le plus récent l'emporte ; à date égale,
  `SOURCE_RANK`) ; écriture atomique `save_profile`, refusée sous le dépôt. `forever_player_profile` est en lecture
  seule. **Aucun profil sur ce poste** (`~/.forever/profile.json` absent, `FOREVER_PROFILE` non défini). La décision
  122 n'est appliquée que par les skills du plugin (`forever-router/format-reponse.md`) ; le pont ne compare rien.
- **`forever update`** :
  - attentes dans `<cache>/update/pending/<id>.json`, états `en_attente | approuvée | rejetée | périmée | faite` ;
  - **approuvables avec effet** : `install_version` et `install_revision` d'action `attente`, et `measures` ;
  - **non approuvables** : action `bloqué`, `network` et `hotfixes_unread` (qui se lèvent seules), `column_names`
    (session) ; `addon_data` et `network_dbd` sont acceptées par `approve` **sans effet** et sont traitées ici comme
    non approuvables ;
  - résumés existants : `summary_text`, `measure_summary_lines` (PNJ ajoutés, changés, retirés, écartés ; niveaux
    dont les PV changent ; builds), `reasons`, `commands` ;
  - `launch_pass` rend faux si le verrou est vivant ; `approve` sans `--wait` ne regarde pas le verrou (approbation
    consommée au passage suivant) ;
  - fin d'un passage : verrou disparu et nouveau `finished_at` dans `last.json`.
- **Pont** :
  - `status_line` compte comme « à valider sur le PC » des attentes qu'on ne peut pas valider ; la version du client
    n'y paraît que quand elle dépasse celle des données ;
  - `Button("update")` a une question vide, que `ClickButton` n'envoie pas ;
  - l'équipement part en `slot:id:nom` (sans lien complet) ;
  - l'allègement retire `gear`, puis `talents`, ce qui casse la décision 224 et le bouton Talents.
- **Builds populaires** : `closest_popular` (`forever/talents_forever.py:809`) existe mais ne sert qu'au build
  calculé du Mage ; `forever_lookup(kind="tf_popular")` n'a ni `current` ni `closest`.
- **Contextes réels** : le journal du pont ne garde que les **clés** du contexte (`context_keys`). Les valeurs ne
  sont que dans les transcriptions de la conversation « jeu », et toutes viennent de Jen, Mage Orc 19 de la Horde
  (103 messages ; les niveaux 21 sont des cibles). Elles sont déjà en fixtures (`tests/fixtures/bridge/contexts/`) ;
  `chasseur19_construit.txt` est construit à la main. Aucun contexte réel ne porte de lien complet, d'infobulle ni
  d'export SimulationCraft : **ces fonctions se testent d'abord sur des fixtures construites, marquées comme telles,
  puis sur les relevés des sondes G et H** (tests ajoutés après la sonde, hors du commit rouge, comme `band_live.bmp`
  en P06a).

### Calendrier des relevés, sur les durées réelles du journal (9 réponses du 2026-10-09 et du 2026-10-10)
Durées de réponse relevées : 23,4 · 14,8 · 31,0 · 15,5 · 14,3 · 29,6 · 18,5 · 19,2 · 9,5 s.

| Calendrier | Attente moyenne après la réponse prête | Pire attente | Relevés moyens (emplacements) |
| --- | --- | --- | --- |
| Actuel : 3, 7, 11, …, 27, 30, puis toutes les 10 s jusqu'à 190 | 2,58 s | 9,0 s | 5,7 |
| Proposé : 2, 4, puis toutes les 4 s jusqu'à 60, puis toutes les 10 s jusqu'à 190 | 1,36 s | 2,5 s | 6,2 |

Le calendrier proposé gagne en moyenne 1,2 s et jusqu'à 6,5 s, pour moins d'un emplacement de plus par réponse. Le
premier relevé à 2 s retire aussi la bande une seconde plus tôt.

## Choix proposés (à confirmer à la validation)

1. **Messages en plusieurs parties** (un seul mécanisme pour l'export SimulationCraft, les infobulles et l'équipement
   complet).
   - Un message dont la charge dépasse `MAX_PAYLOAD` (1 792 octets) est découpé en **parties**. La charge d'une
     partie s'écrit `F␟<session>␟<id>␟<i>␟<n>␟<octets>` (␟ = 0x1F, `F` à la place de la version `1` ; octets bruts
     de la charge complète du message). Le protocole `1` du message lui-même ne change pas.
   - L'addon montre les parties **en carrousel**, une toutes les 0,5 s (la sonde du pont tourne toutes les 0,25 s).
   - Chaque publication du pont porte les parties reçues (`{session, id, status = "parts", got = {…}}`) ; l'addon ne
     montre plus que celles qui manquent. Message complet : `working`, puis le traitement habituel.
   - Abandon après trois relevés sans aucune partie nouvelle : boîte d'envoi `/reload` (le message entier, sans
     limite de taille dans la sauvegarde).
   - Taille d'un message limitée à 32 768 octets (19 parties) ; au-delà, l'envoi est refusé avec « export trop long :
     utilisez /simc nobags ».
   - Ordre quelconque, doublons ignorés, partie d'une autre session ignorée.
2. **Allègement révisé** (décision 224) : noms d'objets coupés à 20 caractères, puis retirés, puis `subzone` ; ensuite
   **découpage en parties**. `gear`, `talents`, `links` et la question ne sont **jamais** retirés.
3. **Équipement complet** : `gear` devient `slot=<chaîne d'objet>[=nom]` (séparateur `;`). La chaîne d'objet est
   celle du lien (`item:…`) sans le préfixe `item:` et sans les champs vides ou nuls de fin. Elle garde l'objet,
   l'enchantement, les gemmes, le **suffixe aléatoire** et l'identifiant unique (qui porte le facteur du suffixe).
   Le pont lit encore l'ancienne forme `slot:id[:nom]` (contextes réels de P06a).
4. **Liens par Maj+clic** :
   - accroche par `hooksecurefunc` sur `ChatFrameUtil.InsertLink` et sur `ChatEdit_InsertLink` (ceux qui existent,
     sous `pcall`) : si notre zone de saisie a le focus, le lien y est inséré ;
   - objets, sorts, quêtes et talents (`|Hitem:`, `|Hspell:`, `|Hquest:`, `|Htalent:`) ;
   - la zone de saisie passe de 255 à 1 000 caractères, séquences des liens comprises ;
   - à l'envoi, chaque lien est remplacé par `[Nom]` dans la question, et la clé de contexte `links` porte, par lien
     (séparés par 0x1D), le corps du lien, son nom et les lignes de son infobulle (séparées par 0x1C) ;
   - l'infobulle est lue par `C_TooltipInfo.GetHyperlink`, sous `pcall` et `issecretvalue`, avec au plus 8 liens
     par message, 30 lignes et 120 caractères par ligne.
5. **Actions du jeu sans le modèle** : drapeau `a=<action>` intercepté par le pont **avant la file**. Le pont répond
   lui-même ; l'agent n'est jamais appelé.
   - Actions fermées : `update`, `approve:<id>`, `reject:<id>`, `explain:<id>`, `profile_apply:<id>`,
     `profile_dismiss:<id>`.
   - L'identifiant venu de la bande est **apparié exactement** à une entrée connue (attente approuvable de
     `list_pending`, proposition de profil du pont). Il n'est jamais passé tel quel à une commande.
   - Commandes fixées lancées par `spawn_detached` :
     - `[python, -u, -m, forever, update, --auto, --json]` (journal `run-<horodatage>.log`, par `launch_pass`) ;
     - `[python, -u, -m, forever, update, approve, <id>, --json]` ;
     - `[python, -u, -m, forever, update, reject, <id>, --reason, "refusé en jeu", --json]`.
   - Valider et Refuser demandent un **second clic** (« Confirmer », 5 s).
   - Un passage déjà en cours : « passage en cours (étape X) ; approbation prise au prochain passage ».
6. **Cartes « À valider »** : une seule forme dans `Inbox.lua` et `Status.lua`,
   `cards = { { id, kind = "update" | "profile", title, lines = {…}, buttons = {…} } }`. Elles sont rendues par
   l'addon dans un panneau « À valider (n) » de la fenêtre.
   - **Texte rédigé par le pont** (réponse 3), selon le type d'attente :
     - `install_*` : version, révision et phrase par moteur ;
     - `measures` : PNJ ajoutés, changés, retirés et nouvellement écartés (noms, 10 au plus par ligne), niveaux dont
       les PV changent, builds changés après rejeu ;
     - `network` : « attente réseau : se lève seule au prochain passage réussi » ;
     - `hotfixes_unread` : « correctifs du serveur à lire jusqu'au <date> » ;
     - `bloqué`, `column_names`, `addon_data` et `network_dbd` : « à traiter sur le PC : <commande> ».
   - Valider et Refuser seulement pour une attente approuvable à l'état `en_attente`. « Expliquer » sur toutes : il
     envoie le texte de la carte à la conversation « jeu » (question fixe « Explique cette mise à jour en attente,
     simplement »).
   - Les propositions de profil (choix 9) utilisent les mêmes cartes, avec « Mettre à jour le profil » et « Ignorer ».
7. **Bouton « Mettre à jour » et état des données** :
   - le bouton envoie `a=update` ;
   - pendant un passage, le statut porte `update = { running, step, started_at }`, et l'addon relève la réserve
     toutes les 30 s, fenêtre ouverte, 20 fois au plus ;
   - le pont surveille le verrou et `last.json` à chaque relevé de l'état du jeu (5 s) et republie dès qu'ils
     changent ;
   - à la fin d'un passage, une ligne fixe s'ajoute une fois à l'historique : « Mise à jour terminée : <n> écrit(s),
     <m> à valider ».
   - Ligne d'état : `Données <version> · client <version> · <fraîcheur> · <n> à valider · <m> en attente`. Le client
     est toujours affiché ; client plus récent : `client <version> : mise à jour en attente` à la place de la
     fraîcheur ; « à valider » ne compte que les attentes approuvables.
   - Le bouton « Mettre à jour » est visible dès P06b (tranches T08d, T08e et P06b faites).
8. **Écart entre le jeu et le profil** (décision 122), à chaque message.
   - Le pont compare le contexte relié (`Resolved`) au personnage du profil de même nom et royaume (à défaut, au
     personnage actif de même nom) : `class`, `race`, `faction`, `level`, `talents` et, au schéma 3, `gear`.
   - Le message au modèle gagne une ligne fixe : « Écart avec le profil : <liste>. Le jeu l'emporte pour cette
     réponse ». La réponse publiée gagne la mention « Écart avec ton profil : voir À valider ».
   - Une carte de proposition est créée ; personnage absent ou profil absent : carte « Créer le personnage <nom> au
     profil ».
   - « Ignorer » garde l'empreinte de l'écart : il n'est plus proposé tant qu'il ne change pas.
   - Écriture **par le pont seulement**, au clic : `merge_field`, source `jeu`.
9. **Profil, schéma 3** (réponse 2).
   - Nouveaux champs sourcés `gear` (`{slot: {item, enchant, gems, suffix, unique, link_level, bonus, name}}`) et
     `sheet` (puissance des sorts par école, soins, critique par type et par école, toucher : notation, bonus et
     modificateur, hâte, notations `nom: {notation, bonus}`, régénération en combat et hors combat, buffs actifs,
     date de lecture).
   - Nouvelles sources : `jeu` (contexte du pont, rang de ForeverLogger) et `simulationcraft` (export collé, rang
     juste après `jeu`).
   - Certitude `certain` pour une valeur lue au client, avec la note « lue avec les buffs actifs » pour `sheet`.
   - Lecture du schéma 2 acceptée, écriture en 3 ; `forever profile show` affiche les deux champs.
   - `forever_player_profile` reste en lecture seule.
10. **Export SimulationCraft** : bouton « Coller un export » qui ouvre une zone de collage multiligne (sans limite de
    lettres, Ctrl+V). Le bouton « Envoyer l'export » envoie le texte en parties avec le drapeau `k=simc`, sans
    question.
    - Le pont le lit **sans le modèle** (`forever/simc.py`, réutilisé par SIM1) : en-tête, objets, fiche, `skills`,
      `buffs`, somme de contrôle.
    - Somme fausse : « export incomplet ou modifié : recopiez /simc ».
    - Il compare au profil et au contexte du même message, publie la liste des écarts, puis une carte « Mettre à jour
      le profil ».
    - **Talents** : ceux du contexte (`C_Traits`, même instant) font foi. La chaîne `talents=` n'est décodée que si
      l'accord du choix 16 est donné, et sert alors de contrôle croisé (écart signalé, certitude `suppose` tant que
      le décodage n'a pas été vérifié sur un export réel).
    - **Suffixe aléatoire et emplacement 18** : pris du contexte ; l'absence de l'emplacement à distance dans
      l'export est signalée sans être un écart.
    - Les paires notation et bonus sont gardées dans `sheet`, preuve en jeu pour PER8 (SIM1).
11. **Talents des autres classes** (point 6) :
    - `forever_lookup(kind="tf_popular", name, current="clé=rang,…")` gagne `closest`, calculé par `closest_popular`
      sur les talents actuels ; même option `--current` pour la CLI (`forever tf popular`) ;
    - la consigne du bouton Talents (hors Mage) appelle `tf_popular` avec `current`, puis `build_check` ;
    - la lecture dit : « donne `closest` tel quel (spécialisation, lien, `/tf import`, points absents, écarts) ; n'en
      choisis pas un autre » ;
    - le pont publie le lien de `closest.link` (`links["closest"]`, plan `link="closest"`) ;
    - sans talent placé, `closest` vaut `None` et la consigne dit « aucun talent placé : build le plus joué de la
      classe (rang 1) ».
12. **Conversation « addons »** (réponse 1) :
    - deuxième ligne de `claude` dans `agent.py` : `--tools Read,Glob,Grep,Edit,Write`, et `--allowedTools` avec des
      règles limitées au dossier (`Read(<dossier>/**)`, `Edit(<dossier>/**)`, `Write(<dossier>/**)`, `Glob`,
      `Grep` ; syntaxe exacte fixée par la sonde 0.2) ;
    - `--restricted`, `--strict-mcp-config` avec une configuration MCP vide, `dontAsk`, dossier de travail égal au
      dossier source ;
    - délai de 600 s ; relevés de l'addon prolongés pour cette conversation (toutes les 30 s de 190 à 610 s) ;
    - session à part (`sessions.addons`), onglets « Jeu » et « Addons » dans la fenêtre (Addons visible seulement si
      configurée), historique séparé ;
    - consignes : Lua 5.1 de WoW, règles de `docs/ADDON.md` (`pcall`, SavedVariables, aucune fonction d'action), ne
      rien supprimer, finir par un résumé des fichiers changés et « tapez /reload pour essayer » ;
    - **le pont**, avant le tour, copie le dossier vers `<cache>/bridge/addons/backups/<horodatage>/` ; après le
      tour, il lance `git init` au premier usage, puis `git add -A` et `git commit` (identité locale
      `ForeverBridge <forever-bridge@localhost>`, message « Conversation addons : <question coupée à 60 caractères> »).
      Aucune autre commande git (ni `push`, ni `remote`, ni `fetch`) ;
    - réponse publiée suivie de la ligne fixe du commit (`<sha court> · <n> fichier(s)`) ;
    - `forever bridge addons restore [<horodatage>]` recopie une sauvegarde et **déplace** les fichiers créés depuis
      vers `<cache>/bridge/addons/set-aside/<horodatage>/` : rien n'est détruit ;
    - `forever bridge addons config` **refuse** un dossier d'addon de la communauté (inventaire de `forever/addons.py`
      : seuls `OWN_ADDONS` hors projet, ou un dossier hors de `Interface/AddOns`) et accepte RaphCompletionist.
13. **Contextes réels, désormais gardés** : l'événement `message` du journal porte le contexte complet (`context`, à
    côté de `context_keys`), et `k=simc` porte l'export. `forever bridge contexts export <dossier>` écrit chaque
    contexte distinct au format des fixtures (`clé=valeur`), pour le banc. Le journal est dans le cache de
    l'utilisateur, jamais dans le dépôt.
14. **Accélérations** (point 7), mesurées au bloc G avant d'être gardées (protocole plus bas) :
    - **A**, ligne actuelle ;
    - **B**, `MAX_THINKING_TOKENS=0` dans l'environnement de `claude` ;
    - **C**, session gardée ouverte : un processus `claude --input-format stream-json --output-format stream-json`
      par conversation « jeu », messages écrits en JSON sur son entrée, relancé à « Nouvelle conversation », après
      15 min sans message, en cas d'erreur ou de délai dépassé, arrêté avec le pont (objet de tâche) ;
    - **D**, B et C ensemble.
    - Le calendrier proposé des relevés (2, 4, puis toutes les 4 s jusqu'à 60) est adopté au bloc A sans mesure par
      l'API : le tableau ci-dessus le chiffre déjà sur les durées réelles.
15. **Décision 235** pour ces choix ; ROADMAP P06b mise à jour (résumé par le pont, bouton « Expliquer », profil au
    schéma 3, conversation « addons » dans le dossier installé, liens d'export : aucune tranche d'export faite, rien à
    ajouter).
16. **Accord réseau demandé à la validation** (hors des quatre dépôts de la décision 234) : lecture seule du Lua de
    Blizzard qui écrit la chaîne d'import des talents (`Blizzard_ClassTalentImportExport`, miroir
    `Gethe/wow-ui-source`), pour décoder `talents=`. Sans accord, la chaîne est gardée brute et ignorée : les talents
    du contexte suffisent.
17. **Accord API à la validation** : la sonde 0.2 (deux ou trois conversations « addons ») s'ajoute à l'accord des
    48 conversations de mesure.

## Étapes et blocs

Ordre fixé par la date : le transport en jeu d'abord, avec la sonde G avant le 2026-10-14.

### Étape 0 — Préalables (avant tout test)
1. ROADMAP P06b (choix 15) et **décision 235** ; `docs/OPEN_QUESTIONS.md` (questions plus bas).
2. **Sonde de `claude` pour la conversation « addons »** (accord du choix 17) : la ligne du choix 12, lancée sur une
   copie de RaphCompletionist placée dans le cache. Elle fixe la syntaxe des règles de chemin (absolu `//C:/…`,
   relatif au dossier de travail) et vérifie que :
   - une lecture et une écriture dans le dossier passent ;
   - **une écriture hors du dossier est refusée** (`permission_denials`) ;
   - `Bash` n'est pas exposé ;
   - Glob et Grep restent dans le dossier.
   Sa sortie, identifiants remplacés, devient `tests/fixtures/bridge/claude_stream_addons.jsonl` et
   `claude_stream_addons_denied.jsonl`.
3. **Sonde du format de `--input-format stream-json`** (dans les 48 conversations) : forme du message écrit sur
   l'entrée, plusieurs messages dans un même processus, un événement `result` par message. Fixture
   `claude_stream_persistent.jsonl`.
4. **Export SimulationCraft réel** (l'utilisateur, en jeu, dès maintenant : `/simc`, Ctrl+C, collé dans
   `<cache>/bridge/simc-jen.txt`, puis `/simc nobags` dans `simc-jen-nobags.txt`). Ces textes deviennent les
   fixtures `tests/fixtures/simc/jen_mage19.txt` et `jen_mage19_nobags.txt`, sans modification (la somme de contrôle
   doit tenir). Sans export réel au moment du bloc D, la fixture construite `constructed_mage.txt` (somme recalculée)
   sert seule et le test sur l'export réel est ajouté après la sonde G.

### Bloc A — Transport : parties, actions, cartes, liens, zone de collage, calendrier (puis sonde en jeu G)
- **Python** :
  - `forever/bridge/fragments.py` ;
  - `record.py` : drapeaux `a=`, `k=`, `c=`, clé `links` ;
  - `forever/bridge/items.py` : chaîne d'objet, liens, infobulles ;
  - `context.py` : `gear` à la nouvelle forme et à l'ancienne ;
  - `loop.py` : parties, actions interceptées, contexte au journal, publication des parties reçues ;
  - `slots.py` : `cards`.
- **Lua** :
  - `Message.lua` : `gear` complet, `links`, allègement révisé, découpage ;
  - `ForeverBridge.lua` : carrousel, accroche de Maj+clic, saisie à 1 000 caractères, zone de collage, panneau
    « À valider » avec ses cartes et le double clic, calendrier proposé ;
  - client simulé : `C_TooltipInfo`, `ChatFrameUtil.InsertLink`, `ChatEdit_InsertLink`, zone multiligne.
- **Sonde en jeu G** (`docs/ADDON.md` §7, étape 17, **avant le 2026-10-14**) :
  - Maj+clic d'un objet, d'un sort et d'une quête dans la saisie ;
  - question avec deux liens : réponse qui cite l'infobulle ;
  - équipement complet relu par `forever bridge selftest --live --message` (suffixe d'un objet « of the … » s'il y en
    a un) ;
  - collage du vrai `/simc` : parties reçues, puis « export reçu » (le lecteur arrive au bloc D, d'ici là le pont
    garde le texte) ;
  - carte factice (`forever bridge selftest --card`) : Valider, Confirmer, le pont journalise l'action sans rien
    lancer.
  - Les relevés (contexte avec liens complets et infobulles, export) entrent en fixtures et en tests de
    non-régression, ajoutés après la sonde, hors du commit rouge.

### Bloc B — Mettre à jour, cartes des attentes, ligne d'état
- `forever/bridge/actions.py` (actions fermées, appariement, commandes fixées), `forever/bridge/cards.py` (texte des
  cartes depuis les attentes, approuvable ou non), `status.py` (ligne d'état, attentes approuvables, passage en cours),
  `updater.py` (surveillance du verrou et de `last.json`), `buttons.py` (`DONE_SLICES` gagne T08d, T08e, P06b ;
  bouton `update` envoyé avec `action = "update"`), Lua (bouton d'action, relevés pendant un passage, ligne de fin).

### Bloc C — Profil au schéma 3, écart avec le profil
- `forever/profile.py` (schéma 3, sources `jeu` et `simulationcraft`, `apply_game_fields`), `forever/bridge/
  profile_gap.py` (comparaison, empreinte, cartes), `prompt.py` (ligne d'écart), `loop.py` (`profile_apply`,
  `profile_dismiss`), `forever profile show` (gear, sheet).

### Bloc D — Lecteur de l'export SimulationCraft
- `forever/simc.py` (lecture, somme de contrôle, objets, fiche, `skills`, `buffs` ; décodage de `talents=` si l'accord
  du choix 16 est donné), `loop.py` (`k=simc` sans modèle : écarts, carte).

### Bloc E — Build populaire le plus proche
- `forever/talents_forever.py` (`popular_builds(…, current)` → `closest`), `forever/mcp_server.py` (`current` de
  `forever_lookup`), `forever/cli.py` (`--current`), `plans.py`, `agent.py` (`links["closest"]`).

### Bloc F — Conversation « addons »
- `forever/bridge/addons.py` (configuration, sauvegarde, git local, restauration, déploiement), `agent.py` (deuxième
  ligne, délai), `prompt.py` (consignes « addons »), `state.py` (sessions par conversation), `loop.py` (`c=addons`),
  CLI `forever bridge addons {config,status,restore,log}`, Lua (onglets, historiques séparés, relevés jusqu'à 610 s).

### Bloc G — Mesure des accélérations
- `forever/bridge/speed.py` et `forever bridge bench --variants A,B,C,D --rounds 2` (accord du 2026-10-10).
- **Questions** : les 6 questions sont prises dans le banc sur contextes réels. Ce sont les boutons Talents, Leveling
  et PvP (cible Tauren), plus trois questions libres relevées dans le journal.
- **Mesures** par réponse : durée totale, `init_s`, `first_text_s`, temps des outils, coût.
- **Critères de qualité**, tous automatiques et écrits avant la mesure :
  1. les appels d'outils sont exactement ceux de la consigne du bouton (outil et arguments) ;
  2. le lien publié est identique à celui de la variante A ;
  3. la ligne de provenance est présente quand un outil a été appelé ;
  4. la réponse fait 600 caractères au plus après mise en forme ;
  5. aucun chiffre hors des résultats d'outil (contrôle du hook `check-numbers`) ;
  6. aucune erreur ni délai dépassé.
- **Règle de décision** (`keep`) : une variante est gardée si sa durée médiane baisse d'au moins 2 s **ou** d'au moins
  15 % par rapport à A, sans aucun échec de qualité sur les deux passages. Le rapport côte à côte des réponses
  (`tasks/P06b-vitesse.md`) est relu par l'utilisateur, qui peut écarter une variante gardée.
- La variante retenue devient le réglage par défaut (`forever bridge config --thinking off|on`,
  `--persistent on|off`) ; résultats consignés dans le plan et dans la décision 235.

### Bloc H — Documentation et procédure en jeu
- `docs/ADDON.md` :
  - §5 et §6 : parties, `links`, `gear` complet, `cards`, actions, conversation « addons » ;
  - §7, étapes 17 (sonde G) et 18 (sonde H, procédure complète) ;
  - §8 : checklist.
- `docs/USAGE.md` (Mettre à jour, À valider, coller un export, addons), `docs/ARCHITECTURE.md`, `addon/README.md`,
  `docs/DATA_SOURCES.md` (export SimulationCraft : source `certain` de la fiche).
- `CLAUDE.md` : le pont lance aussi `git` en local, sans réseau, dans le dossier de la conversation « addons ».
- **Sonde en jeu H** (étape 18, **avant le 2026-10-19**) :
  1. bouton « Mettre à jour » ;
  2. carte d'une vraie attente, « Expliquer », puis Valider ou Refuser ;
  3. écart avec le profil, puis Mettre à jour le profil (création au premier passage) ;
  4. collage `/simc` : écarts listés, puis profil mis à jour ;
  5. bouton Talents d'un second personnage d'une autre classe, si le joueur en a un : `closest` cité, lien publié ;
  6. onglet « Addons » : une petite demande sur RaphCompletionist, commit affiché, `/reload`, puis
     `forever bridge addons restore` ;
  7. durée ressentie avec la variante retenue.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `forever/bridge/fragments.py` | découpage d'une charge en parties, tampon de réassemblage par session et numéro |
| `forever/bridge/items.py` | chaîne d'objet (champs), liens du message, infobulles |
| `forever/bridge/actions.py` | actions fermées du jeu, appariement des identifiants, commandes fixées |
| `forever/bridge/cards.py` | cartes « À valider » des attentes (texte du pont, approuvable) |
| `forever/bridge/profile_gap.py` | écart contexte ↔ profil, cartes de proposition, empreinte ignorée |
| `forever/bridge/addons.py` | conversation « addons » : configuration, sauvegarde, git local, restauration, déploiement |
| `forever/bridge/speed.py` | variantes, critères de qualité, règle de décision, rapport |
| `forever/bridge/polls.py` | calendriers des relevés, attente après réponse, relevés consommés (miroir du Lua, testé) |
| `forever/simc.py` | lecteur de l'export SimulationCraft (réutilisé par SIM1) |
| `forever/bridge/record.py`, `context.py`, `loop.py`, `slots.py`, `status.py`, `updater.py`, `buttons.py`, `plans.py`, `prompt.py`, `agent.py`, `state.py` | extensions ci-dessus |
| `forever/profile.py` | schéma 3, sources `jeu` et `simulationcraft` |
| `forever/talents_forever.py`, `forever/mcp_server.py`, `forever/cli.py` | `closest`, `current`, sous-commandes `bridge addons`, `bridge contexts`, `bridge bench`, `bridge config --thinking/--persistent` |
| `addon/ForeverBridge/Message.lua`, `ForeverBridge.lua` | contexte complet, liens, parties, carrousel, collage, cartes, onglets, calendrier |
| `tests/fixtures/bridge/wow_stub.lua` | infobulles, insertion de liens, zone multiligne |
| `tests/fixtures/bridge/links_constructed.txt`, `contexts/mage19_liens_construit.txt` | liens et infobulles construits (format documenté), remplacés ou complétés par la sonde G |
| `tests/fixtures/simc/` | export construit (`constructed_mage.txt`), exports réels de l'étape 0.4 |
| `tests/fixtures/bridge/claude_stream_addons*.jsonl`, `claude_stream_persistent.jsonl` | sondes 0.2 et 0.3 |

## Interfaces

```python
# forever/bridge/fragments.py
FRAGMENT_TAG = "F"; MAX_MESSAGE = 32768
def split_payload(payload: bytes, *, session: str, message_id: int) -> list[bytes]: ...  # [payload] si elle tient
def parse_fragment(payload: bytes) -> Fragment | None: ...    # None : pas une partie ; RecordError si mal formée
# Fragment(session: str, message_id: int, index: int, total: int, chunk: bytes)
class FragmentBuffer:
    def add(self, fragment: Fragment) -> bytes | None: ...    # charge complète quand toutes les parties sont là
    def received(self, session: str, message_id: int) -> list[int]: ...

# forever/bridge/items.py
@dataclass(frozen=True)
class ItemString: item: int; enchant: int; gems: tuple[int, ...]; suffix: int; unique: int; link_level: int | None; bonus: tuple[int, ...]
def parse_item_string(text: str) -> ItemString: ...           # « 7909:1883:0:0:0:0:-12:1234567:19 » ou « item:… »
def parse_links(value: str) -> list[GameLink]: ...            # GameLink(kind, body, name, tooltip: tuple[str, ...])
def parse_gear(value: str) -> tuple[list[GearPiece], list[Defect]]: ...  # nouvelle et ancienne forme

# forever/bridge/actions.py
ACTIONS = ("update", "approve", "reject", "explain", "profile_apply", "profile_dismiss")
def parse_action(flag: str) -> tuple[str, str | None] | None: ...
def approvable(entry: Mapping[str, Any]) -> bool: ...
def update_argv(kind: str, pending_id: str | None = None) -> list[str]: ...
class ActionHandler:
    def handle(self, record: Record) -> dict[str, Any]: ...  # réponse publiée ; lance au plus une commande fixée

# forever/bridge/cards.py
def update_cards(entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]: ...
def card_lines(entry: Mapping[str, Any]) -> list[str]: ...

# forever/bridge/profile_gap.py
def profile_gaps(resolved: Resolved, profile: Mapping[str, Any] | None, gear: Sequence[GearPiece]) -> list[Gap]: ...
# Gap(field: str, profile: Any, game: Any)
def gap_card(name: str, realm: str | None, gaps: Sequence[Gap], *, create: bool) -> dict[str, Any]: ...
def gap_fingerprint(gaps: Sequence[Gap]) -> str: ...

# forever/simc.py
def parse_simc(text: str) -> SimcExport: ...
# SimcExport(name, class_token, level, race, region, server, client_version, talents_string, items: dict[str, SimcItem],
#            sheet: dict[str, dict[str, float]], ratings: dict[str, tuple[float, float]], skills, buffs,
#            checksum_ok: bool | None, warnings: list[str])
def simc_checksum(text_before: str) -> str: ...
def simc_gaps(export: SimcExport, profile: Mapping | None, context_gear: Sequence[GearPiece]) -> list[Gap]: ...

# forever/profile.py
SCHEMA_VERSION = 3
def apply_game_fields(path: Path, name: str, realm: str | None, fields: Mapping[str, Any], *, source: str,
                      at: str, client_build: str | None) -> dict[str, Any]: ...

# forever/bridge/addons.py
@dataclass(frozen=True)
class AddonsConfig: source: Path; deploy: Path | None
def check_folder(path: Path, addons_dir: Path) -> None: ...   # ForeverError si addon de la communauté
def snapshot(config: AddonsConfig, cache_dir: Path, stamp: str) -> Path: ...
def commit(config: AddonsConfig, message: str, *, run=subprocess.run) -> CommitInfo | None: ...
def deploy(config: AddonsConfig) -> DeployReport: ...          # copie seulement ; manquants signalés
def restore(config: AddonsConfig, cache_dir: Path, stamp: str | None, now: str) -> RestoreReport: ...

# forever/bridge/agent.py (ajouts)
ADDONS_TOOLS: tuple[str, ...] = ("Read", "Glob", "Grep", "Edit", "Write")
def addons_argv(*, claude: str, folder: Path, mcp_config: Path, system_prompt: str, session_id: str | None,
                model: str | None) -> list[str]: ...
class PersistentSession: ...                                   # variante C, si gardée

# forever/bridge/polls.py
CURRENT = (3, 7, …, 190); PROPOSED = (2, 4, 8, …, 60, 70, …, 190)
def poll_wait(schedule: Sequence[float], ready_s: float) -> float: ...
def polls_used(schedule: Sequence[float], ready_s: float) -> int: ...

# forever/bridge/speed.py
VARIANTS: dict[str, Variant]
def quality_failures(result: AgentResult, plan: Plan | None, baseline_link: str | None) -> list[str]: ...
def keep(baseline: Sequence[float], candidate: Sequence[float], failures: int) -> bool: ...
```

Côté Lua :
- `Message.Fragments(payload)`, `Message.Links(text)` ;
- `FB.InsertLink(link)` (accroche), `FB.OpenPaste()`, `FB.SendPaste()`, `FB.RenderCards()`, `FB.ClickCard(card,
  button)`, `FB.SwitchConversation(name)` ;
- `ForeverBridgeDB` gagne `history_addons`, `cards_seen`.

## Tests attendus

Tous sans réseau, sans jeu ni écran, écrits dans `tmp_path`. « Construit » marque une fixture écrite à la main
d'après le format documenté. Les valeurs qui dépendent des données (build le plus proche) sont relevées au moment
d'écrire le test (script hors du dépôt, `repr()`), jamais écrites de mémoire.

### `tests/unit/test_bridge_fragments.py` (bloc A)
- `split_payload(b"x" * 1792, session="abcd1234", message_id=7)` rend `[payload]` (une seule bande, aucune partie).
- `split_payload(b"x" * 5000, session="abcd1234", message_id=7)` : 3 parties, chacune de 1 792 octets au plus. En-tête
  `F␟abcd1234␟7␟1␟3␟` (17 octets) ; morceaux de 1 775, 1 775 et 1 450 octets.
- Réassemblage dans l'ordre, dans le désordre (3, 1, 2) et avec doublons : la même charge est rendue une seule fois.
  `received` vaut `[1, 3]` avant la deuxième partie ; une partie d'une autre session reste à part.
- 32 769 octets → `ValueError` ; `total` incohérent entre deux parties → `RecordError`.
- Charge commençant par `1␟` → `parse_fragment` rend `None` ; parties encodées puis décodées par `encode_cells` et
  `decode_band` → même charge.

### `tests/unit/test_bridge_items.py` (bloc A, fixture `links_constructed.txt`)
- `parse_item_string("item:7909:1883:0:0:0:0:-12:1234567:19")` → objet 7909, enchantement 1883, aucune gemme, suffixe
  −12, unique 1234567, niveau du lien 19. Même résultat sans `item:`. Les champs de fin vides ou nuls sont tolérés.
- `parse_gear("16=7909:1883:0:0:0:0:-12:1234567=Sword of the Bear;1=2:0")` : deux pièces, nom gardé. L'ancienne forme
  `16:7909:Sword` est encore lue. `16=abc` → défaut « objet mal formé ».
- `parse_links` sur deux liens (objet et sort) : genre, corps, nom, lignes d'infobulle (séparateurs 0x1D et 0x1C).
- Un message type (19 pièces complètes, 51 nœuds de talents, question de 255 caractères) tient en **deux parties au
  plus**, sans rien retirer d'autre que les noms.

### `tests/unit/test_bridge_loop_p06b.py` (blocs A à F)
- **Parties** : trois parties capturées dans le désordre → un seul `message`. Chaque publication intermédiaire porte
  `status = "parts"` et `got`. Une partie manquante ne déclenche aucun agent.
- **Contexte au journal** : l'événement `message` porte `context` (valeurs) et `context_keys` ; toujours aucune clé
  `pixels`, `image` ni `bgra`.
- **Actions** (faux `spawn`, faux agent qui lève s'il est appelé), avec des attentes écrites dans un cache simulé
  (fabriques `entry()` de `test_update_pending.py`) :
  - `a=update` → `spawn` reçoit `[python, "-u", "-m", "forever", "update", "--auto", "--json"]` et un journal
    `run-*.log` ; verrou vivant → aucune commande, réponse « passage en cours » ;
  - `a=approve:<id>` d'une `measures` en attente → argv exact `[…, "update", "approve", <id>, "--json"]`, une fois ;
  - `a=approve:network-1.60.1.70338` → refus « attente non approuvable », aucune commande ;
  - `a=approve:../x`, `a=approve:inconnu` et `a=reject:<id d'une attente faite>` → refus, aucune commande ;
  - `a=reject:<id>` → `[…, "reject", <id>, "--reason", "refusé en jeu", "--json"]` ;
  - `a=explain:<id>` → **un** appel de l'agent dont le message contient le texte de la carte ;
  - `a=autre` → refus.
  - L'agent n'est jamais appelé pour `update`, `approve`, `reject`, `profile_*`.
- **Fin de passage** : `last.json` réécrit avec un nouveau `finished_at` et verrou absent → publication aussitôt
  (sans attendre 10 min), `update.last` dans le statut.
- **`k=simc`** : export construit en trois parties → aucune conversation, réponse « export lu » avec les écarts,
  carte « Mettre à jour le profil ». Export dont un octet est changé → réponse « export incomplet ou modifié ».
- **Écart avec le profil** : profil simulé (Jen niveau 18, sans talent) et contexte réel `mage19.txt` :
  - le message à l'agent contient « Écart avec le profil » ;
  - la réponse publiée porte la mention, et une carte apparaît ;
  - `a=profile_apply:<id>` écrit le profil (niveau 19, talents du contexte, source `jeu`) ;
  - un nouveau message identique ne propose plus rien ;
  - `a=profile_dismiss:<id>`, puis même écart → aucune carte ; écart nouveau (niveau 20) → nouvelle carte ;
  - sans profil : carte « Créer le personnage Jen au profil », et rien n'est écrit avant le clic.
- **Conversation « addons »** (`c=addons`) : l'agent reçoit la ligne « addons », la session « addons » est distincte
  de celle de « jeu », la sauvegarde précède l'agent, et le commit le suit.

### `tests/unit/test_bridge_cards.py` (bloc B)
- `approvable` :
  - vrai pour `install_version` (action `attente`) et `measures`, à l'état `en_attente` ;
  - faux pour action `bloqué`, `network`, `hotfixes_unread`, `column_names`, `addon_data`, `network_dbd`, et pour les
    états `approuvée`, `rejetée`, `périmée`, `faite`.
- `card_lines` d'une `measures` (résumé de `test_update_measures_summary.py`) : ligne des PNJ (ajoutés, changés,
  retirés, nouvellement écartés, noms), ligne des niveaux de PV, ligne des builds changés.
- `card_lines` d'une attente `network` : « attente réseau : se lève seule au prochain passage réussi ».
- Une carte non approuvable n'a que le bouton « Expliquer ».

### `tests/unit/test_bridge_status.py` (étendu, bloc B)
- Données et client 1.60.1.70338, fraîcheur `fresh`, une `measures` en attente, une `network` et une
  `hotfixes_unread` → `Données 1.60.1.70338 · client 1.60.1.70338 · à jour · 1 à valider · 2 en attente`.
- Client 1.60.1.70338 et données 1.60.1.70291 → `… · client 1.60.1.70338 : mise à jour en attente · …`.
- Passage en cours → `update.running` vrai et `step` lu dans le verrou.

### `tests/unit/test_bridge_buttons.py` (étendu, bloc B)
- « Mettre à jour » visible avec `DONE_SLICES` ; entrée publiée avec `action = "update"` et sans question. Équipement
  et Dernier combat toujours absents.

### `tests/unit/test_profile_schema3.py` (bloc C)
- Un profil au schéma 2 se lit ; la première écriture le passe au schéma 3 sans rien perdre.
- `apply_game_fields(… source="jeu")` crée le personnage au besoin et écrit `level`, `talents`, `gear`, avec
  `certainty` `certain` et la version du client.
- `merge_field` à date égale : `joueur` > `jeu` > `simulationcraft` > `ForeverLogger` (rangs relus dans
  `SOURCE_RANK`).
- `forever profile show` affiche l'équipement et la fiche.

### `tests/unit/test_bridge_profile_gap.py` (bloc C, contextes réels)
- `mage19.txt` comparé à un profil identique → aucun écart.
- Niveau 18 au profil → `Gap("level", 18, 19)`.
- Talents absents du profil → un écart `talents` (liste des clés).
- `gap_fingerprint` est stable à l'ordre près.
- Personnage d'un autre royaume → carte de création.

### `tests/unit/test_simc.py` (bloc D)
- `simc_checksum("abc") == "24d0127"` ; `"Wikipedia"` → `"11e60398"` (valeurs publiées d'adler32) ;
  `'mage="Jen"\nlevel=19\n'` → `"4466060c"`.
- Export construit :
  - classe `mage`, niveau, race et serveur lus ; `role=` vide et `professions` absente acceptés ; `spec` non figée ;
  - objets par emplacement (`id`, `enchant_id`, `gem_id`, `bonus_id`) ;
  - `sheet["spell_power"]` porte les six écoles ; `ratings` (notation, bonus) ; `buffs` ;
  - `checksum_ok` vrai ;
  - texte en CRLF → même résultat ; un caractère changé → `checksum_ok` faux ; somme absente → `None` ;
  - `# hit=` vide → aucun champ et aucune erreur ;
  - talents illisibles (`# Unable to export talents…`) → `talents_string` `None` et un avertissement.
- `simc_gaps` : emplacement 18 dans le contexte et absent de l'export → avertissement « à distance absent de
  l'export », pas un écart ; même objet et même enchantement → aucun écart ; suffixe pris du contexte.
- Exports réels (`jen_mage19.txt`, `jen_mage19_nobags.txt`), **ajoutés après l'étape 0.4 ou la sonde G** :
  `checksum_ok` vrai, niveau 19 ou plus, objets du contexte du même jour retrouvés.

### `tests/unit/test_talents_forever_closest.py` (bloc E)
- `forever_lookup(kind="tf_popular", name="Hunter", current=<talents de chasseur19_construit>)` rend `closest`, de la
  même valeur que `closest_popular` appelé directement (comparaison dans le test, aucune valeur écrite de mémoire).
- Sans `current` : pas de `closest`.
- `forever tf popular --current …` rend le même bloc.
- Banc (`test_bridge_bench.py`, étendu) : pour `chasseur19_construit`, la consigne du bouton Talents appelle
  `tf_popular` avec `current` ; le lien publié est `closest.link`. Pour `mage19`, la consigne ne change pas.

### `tests/unit/test_bridge_addons.py` (bloc F)
- `addons_argv` :
  - contient `--tools Read,Glob,Grep,Edit,Write`, `--restricted`, `--strict-mcp-config`, `dontAsk`, `--allowedTools`
    avec les seules règles du dossier (forme de la sonde 0.2) ;
  - ne contient ni `Bash`, ni `WebFetch`, ni `WebSearch`, ni `mcp__`, ni `bypassPermissions`, ni
    `--dangerously-skip-permissions` ;
  - délai de 600 s.
- `check_folder` :
  - refuse `AddOns/Questie` et `AddOns/Simulationcraft` (addons de la communauté), ainsi que `AddOns` lui-même ;
  - accepte `AddOns/RaphCompletionist` et un dossier hors de `Interface/AddOns`.
- `snapshot` copie tout le dossier. `commit` (faux `run`) :
  - lance `git init` au premier usage, puis `add -A` et `commit -m` avec l'identité locale ;
  - argv sans `push`, `remote`, `fetch`, `pull`, `clone` ;
  - aucun commit quand rien n'a changé.
- `restore` recopie la sauvegarde, déplace un fichier créé depuis vers `set-aside/` et n'appelle jamais `unlink`
  (piège).
- `deploy` copie les fichiers changés vers le dossier installé et signale, sans le supprimer, un fichier absent de la
  source.
- `tests/unit/test_network_boundary.py` : l'ensemble des modules qui importent `subprocess` gagne
  `bridge/addons.py` ; ce module ne lance que `git`, avec des sous-commandes de la liste fermée `init`, `add`,
  `commit`, `status`, `diff`, `log`, `rev-parse`.

### `tests/unit/test_bridge_polls.py` et `test_bridge_speed.py` (blocs A et G)
- `poll_wait(CURRENT, 31.0) == 9.0` et `poll_wait(PROPOSED, 31.0) == 1.0`.
- Sur les 9 durées réelles (fixture `tests/fixtures/bridge/reply_seconds.json`, relevée dans le journal) : attente
  moyenne 2,58 s puis 1,36 s ; relevés moyens 5,7 puis 6,2 (`pytest.approx(abs=0.01)`).
- `PROPOSED` est égal au calendrier lu dans `ForeverBridge.lua` (test `lupa`).
- `keep` :
  - `keep([20.0, 18.0, 22.0], [15.0, 16.0, 17.0], 0)` vrai ;
  - le même avec `failures=1` faux ;
  - `keep([20.0, 18.0, 22.0], [19.5, 17.8, 21.6], 0)` faux.
- `quality_failures` :
  - un appel d'outil absent de la consigne → « appel hors consigne » ;
  - un lien différent de A → « lien changé » ;
  - 601 caractères → « réponse trop longue ».
- Variante B : l'environnement de `claude` porte `MAX_THINKING_TOKENS=0`, et A ne l'a pas.
- Variante C (faux processus qui lit l'entrée) : deux messages dans un même processus, chacun avec son `result` ;
  relance après « Nouvelle conversation » et après un délai dépassé.

### `tests/unit/test_bridge_p06b_lua.py` (`lupa.lua51`, client simulé ; blocs A, B, F)
1. Maj+clic avec la saisie active : `ChatFrameUtil.InsertLink(lien)` insère le lien dans notre saisie. Saisie sans
   focus : rien n'est inséré. Les deux accroches manquantes : aucune erreur Lua.
2. Envoi d'une question avec deux liens : la question porte `[Nom]` ; `links` porte les deux corps, leurs noms et
   les lignes d'infobulle simulées, coupées à 30 lignes et 120 caractères ; au-delà de 8 liens, seuls les 8 premiers.
3. `GetInventoryItemLink` simulé avec un suffixe → `gear` porte la chaîne complète (`…:-12:…`).
4. Contexte trop gros (19 pièces aux noms de 60 caractères, 51 nœuds, question de 255 caractères, 8 liens d'infobulle
   de 30 lignes) : le message part en parties, avec `gear`, `talents`, `links` et la question entiers ; les parties
   lues dans les textures simulées se réassemblent par `FragmentBuffer` en une charge que `parse_payload` lit.
5. Carrousel : les parties alternent toutes les 0,5 s simulées ; après une publication `got = {1, 3}`, seule la
   partie 2 est montrée ; message complet : bande retirée. Trois relevés sans partie nouvelle : boîte d'envoi avec le
   message entier.
6. Zone de collage : aucune limite de lettres ; un export de 15 000 caractères part en 9 parties. 32 769 octets →
   « export trop long : utilisez /simc nobags », rien d'envoyé.
7. Calendrier : chargements à 2, 4, 8, …, 60, 70, …, 190 s ; pendant un passage de `forever update`, toutes les 30 s,
   20 fois au plus.
8. Cartes :
   - rendues depuis l'emplacement ;
   - un clic sur Valider montre « Confirmer », un second clic dans les 5 s envoie `a=approve:<id>`, un second clic
     après 6 s n'envoie rien ;
   - carte sans bouton Valider pour une attente non approuvable ;
   - « Expliquer » envoie `a=explain:<id>`.
9. Bouton « Mettre à jour » → message `a=update` sans texte ; ligne « Mise à jour terminée » écrite une seule fois par
   `finished_at`.
10. Onglets : l'onglet « Addons » est absent sans configuration publiée et présent avec. Les historiques sont séparés.
    Un message de l'onglet porte `c=addons` ; ses relevés vont jusqu'à 610 s.
11. Pièges (fonctions d'action, `ReloadUI`, `SendChatMessage`…) jamais appelés. Aucun `RegisterEvent` hors `pcall`,
    aucun `COMBAT_LOG_EVENT*`, rien dans la discussion générale hors `/fv diag`.

### `tests/unit/test_addon_rules.py` (étendu)
- `check_addon(addon/ForeverBridge) == []` avec les accroches `hooksecurefunc`. Cas négatif : remplacer
  `ChatEdit_InsertLink` par une affectation (`ChatEdit_InsertLink = …`) → « fonction de Blizzard remplacée (utiliser
  hooksecurefunc) ».

### Registre
**Aucune entrée** : aucune mécanique de jeu n'est ajoutée ni modifiée. La fiche de l'export est rangée au profil, pas
dans le moteur. Les comptes de `test_registry.py` ne bougent pas.

## Hors périmètre
- Boutons « Simuler » et « Est-ce une amélioration ? », appuyés sur une simulation (SIM1).
- Bouton Équipement (T10a), « Analyse du dernier combat » (AN1, AN2).
- Chaînes d'import des addons (T10a, EX1 : aucune tranche d'export faite).
- Conversion des notations en pourcentage (PER8, SIM1) : P06b garde seulement les paires lues.
- Décodage de la chaîne `talents=` sans l'accord du choix 16.
- Lecture des dossiers d'addons de la communauté par la conversation « addons » ; tout shell pour l'agent ;
  `git push` ; toute suppression de fichier.
- Outil MCP qui écrit ou approuve ; écriture du profil par le modèle.
- Toute action de jeu, entrée simulée, message de chat automatique ; détection d'événement de combat.
- Canal par polices (BR4).

## Risques
- **Infobulles** : `C_TooltipInfo.GetHyperlink` peut rendre des valeurs secrètes ou vides pour certains liens (quête
  hors journal). Clé absente et rien d'envoyé dans ce cas ; la sonde G le dit.
- **Accroche de Maj+clic** : sur Forever, la fonction appelée par un Maj+clic peut différer (`ChatFrameUtil`,
  `ChatEdit_InsertLink`, ou un autre chemin pour les sacs). Les deux accroches sont posées sous `pcall` ; la sonde G
  dit laquelle sert. Repli : coller le lien par Ctrl+V dans la saisie.
- **Carrousel** : une capture faite pendant le changement de partie échoue à la somme de contrôle ; elle est rejetée,
  et le tour suivant la reprend. Le coût mesuré à la sonde G est le nombre de tours pour un export de 9 parties.
- **Collage d'un long texte** dans une zone de saisie de WoW : lenteur possible au-delà de 10 k caractères ;
  `/simc nobags` est conseillé dans la fenêtre.
- **Chaîne `talents=`** : format de Blizzard possiblement différent sur Forever (configuration `CamelotCombat`). Les
  talents du contexte font foi ; le décodage reste un contrôle.
- **Session gardée ouverte** : contexte qui grossit (coût, durée) et état du serveur MCP. Relance après 15 min ;
  gardée seulement si la mesure le justifie.
- **Règles de chemin de Claude Code** : la syntaxe (absolu `//`, relatif) se fixe par la sonde 0.2. Si une écriture
  hors du dossier passe, la conversation « addons » ne sort pas : arrêt et retour à l'utilisateur.
- **git dans un dossier d'addon installé** : `.git` est ignoré par le jeu. Un gestionnaire d'addons qui réinstallerait
  le dossier l'effacerait, mais RaphCompletionist n'est suivi par aucun gestionnaire.
- **Écart avec le profil à chaque montée de niveau** : une carte par niveau. L'empreinte limite à une carte par écart
  distinct ; « Ignorer » la fait taire jusqu'au prochain changement.
- **Date** : la sonde G doit avoir lieu avant le 2026-10-14 et la sonde H avant le 2026-10-19. Si le temps manque, les
  blocs F et G (addons, mesures) passent après la sonde H sans bloquer la fusion. Les procédures de `docs/ADDON.md`
  marquées « au lancement » sont rejouées par LN1.

## Angles morts attendus
Aucune mécanique de jeu n'est ajoutée ni modifiée. La qualité des réponses dépend des outils existants (angles morts
de T04 à FA1 : classes sans moteur, modèle d'XP de Forever absent, etc.). La fiche lue par SimulationCraft (`certain`)
pourra contredire notre fiche estimée (`character.spell_power`, `suppose`). P06b la garde au profil sans changer le
moteur ; l'écart est exploité par SIM1 et T10a.

## Questions ouvertes à ajouter (`docs/OPEN_QUESTIONS.md`, section « Pont en jeu »)
- **BR5** : quelle fonction appelle un Maj+clic sur Forever (sacs, livre des sorts, journal des quêtes) quand une zone
  de saisie d'addon a le focus ?
- **BR6** : l'export SimulationCraft omet-il vraiment l'emplacement à distance sur Forever, et la chaîne `talents=`
  suit-elle le format d'import de Blizzard ?
- **BR7** : combien de tours de carrousel faut-il pour un export de 9 parties à une case par pixel ?

## Critères de fin
1. Parties, actions, cartes, liens, équipement complet, zone de collage et calendrier testés hors jeu (tests
   ci-dessus verts).
2. Valider et Refuser :
   - ils lancent la commande fixée et rien d'autre, seulement pour une attente approuvable ;
   - un identifiant inconnu ou un type non approuvable ne lance rien ;
   - l'agent n'est jamais appelé pour une action (tests).
3. Écart avec le profil et export SimulationCraft : rien n'est écrit au profil sans le clic ; profil au schéma 3
   (tests).
4. Bouton Talents hors Mage : `closest` calculé par l'outil, lien publié par le pont (tests et banc).
5. Conversation « addons » limitée au dossier, sans shell : sauvegarde avant chaque tour, commit après, restauration
   sans suppression (tests, sonde 0.2).
6. Mesure des accélérations faite selon le protocole du bloc G ; résultat et variante retenue consignés (décision 235,
   `tasks/P06b-vitesse.md`).
7. Contextes complets journalisés et `forever bridge contexts export` ; banc étendu aux nouvelles fonctions, sur les
   contextes réels disponibles et sur les relevés des sondes G et H.
8. Procédures en jeu écrites (`docs/ADDON.md` §7, étapes 17 et 18), à jouer avant le 2026-10-19 ; non bloquantes pour
   la fusion si le jeu n'est pas disponible (comme P06a).
9. `test_addon_rules.py` vert ; `uv run tasks.py verify` vert ; CI verte sous Ubuntu et Windows.

## Validation
Plan à valider par l'utilisateur, avec les accords des choix 16 (lecture du Lua de Blizzard pour `talents=`) et 17
(sonde « addons » dans l'accord des conversations de mesure), et l'export `/simc` de l'étape 0.4. Exécution dans une
nouvelle session (`/tranche P06b`), branche `p06b`, un cycle rouge → vert par bloc.
