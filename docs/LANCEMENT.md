# Lancement de WoW Forever : pas-à-pas du 4 novembre

Écrit par LN1 (décision 271). Une section par PC, dans l'ordre ; pour chaque étape : la commande, ce qu'il faut voir,
que faire sinon. Toutes les commandes se lancent dans PowerShell, **depuis la racine du dépôt**, sauf mention
contraire. Rien ici n'est deviné sur la version finale : son produit se lit sur le disque (`forever wow list`) et son
numéro d'interface en jeu.

Règle pour la suite (ROADMAP) : chaque tranche qui laisse un test en jeu en attente l'ajoute à la section « Tests en
jeu restés en attente ».

## PC de jeu

PC `RAPHAEL-GAMING`, jeu dans `C:\Program Files (x86)\World of Warcraft`, sauvegardes sur `F:` (« SAUVEGARDE »).

1. **Sauvegarde, jeu fermé** : `uv run forever backup --reason "avant le lancement"`.
   - À voir : `Sauvegarde faite : F:\WoW Forever\sauvegardes\<date>`.
   - Sinon : poser `FOREVER_BACKUP_DIR` si la racine ne convient pas (le diagnostic de l'étape 9 la contrôle).
2. **Installer la version finale par Battle.net** (hors forever). Noter le dossier choisi par Battle.net.
3. **Voir les installations** : `uv run forever wow list`.
   - À voir : la bêta (`bêta`) et une ligne `inconnu` avec le produit de la version finale, son dossier, sa version
     et son exécutable, suivie de « si c'est la version finale, forever wow adopt <dossier> ».
   - Sinon (aucune ligne nouvelle) : section « Le jeu change de dossier » ; produit illisible : forcer le dossier par
     `FOREVER_WOW_FORCE` (même section).
4. **Adopter la version finale, une fois** : `uv run forever wow adopt "<dossier de la ligne inconnu>"`, puis
   répondre `o` (ou `--yes`).
   - À voir : `Adopté comme version finale : <produit> (<dossier>)`, une sauvegarde faite juste avant, et la commande
     d'archivage des personnages de la bêta (étape 13). `uv run forever wow list` montre ensuite
     `Choix : <dossier> (version finale adoptée)`.
   - Sinon : un refus dit pourquoi (produit de la bêta, produit public connu, produit illisible).
5. **Variables d'environnement** : `powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1`.
   - À voir : la question « FOREVER_WOW_DIR vaut … ; forever choisit … (version finale adoptée). Remplacer ? »,
     répondre `o` ; puis `FOREVER_WOW_DIR = <dossier>`. Ouvrir ensuite un **nouveau** terminal.
   - Diagnostic sans rien changer : `... install_plugin.ps1 -Print`.
6. **Addons, jeu fermé** : `uv run python scripts/install_addon.py` (ForeverLogger), puis
   `uv run forever bridge install` (ForeverBridge, sa réserve et ses sondes).
   - À voir : les copies dans `<dossier>\Interface\AddOns` ; le diagnostic de l'étape 9 les compare au dépôt
     (`addons.logger`, `addons.bridge`).
7. **Numéro d'interface de la version finale** : lancer le jeu, se connecter, taper
   `/dump select(4, GetBuildInfo())`.
   - Si la valeur est celle de `forever.toc.INTERFACES` : rien à faire. Sinon : l'ajouter à `INTERFACES`
     (`forever/toc.py`), committer (`LN1: interface de la version finale`), quitter le jeu, refaire l'étape 6.
     Si les addons n'apparaissent pas dans la liste des addons du jeu : le client exige peut-être un `.toc` suffixé
     (question LNC1) ; le noter et le signaler.
   - ForeverLogger 0.7.0 note aussi la valeur à chaque connexion ; le diagnostic la compare aux `.toc`.
8. **Tâches planifiées et pont**, jeu fermé : `uv run forever bridge autostart install` (sans `--wow-dir` : la
   surveillance suit le choix), puis
   `powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1`.
   - Pont : `uv run forever bridge stop`, attendre que la surveillance soit arrêtée
     (`uv run forever bridge autostart status`), puis `schtasks /Run /TN "WoW Forever - pont"` (le pont ne recharge
     jamais seul son code).
   - Une tâche plus ancienne qui forçait le dossier de la bêta est signalée « à recréer » par le diagnostic.
9. **Diagnostic** : `uv run forever doctor`.
   - À voir : `Bilan : … 0 bloquant(s)` (seul `antivirus` reste `[?]`). Sinon : appliquer la correction donnée sous
     chaque `[x]` et `[!]`, puis relancer.
10. **Première connexion** : se connecter avec un personnage, jouer quelques minutes, quitter.
    - À voir ensuite : `uv run forever doctor` → `combatlog` `[ok]` (journal avancé récent, activé par
      ForeverLogger).
11. **Données de la version finale** : `uv run forever update`.
    - À voir : la cible est le build du client final, le produit demandé à wago.tools est celui de la version finale
      (`uv run forever builds` le montre) ; la nouvelle version s'installe (`forever install --new-version` si une
      attente le demande).
    - Sinon : `uv run forever update status` ; une version pas encore publiée sur wago.tools attend.
12. **Données héritées de la bêta** : `uv run forever measures inherited` liste les PV encore issus de la bêta.
13. **Profil** : `uv run forever profile archive --product <produit de la bêta>` (affiché à l'étape 4), puis
    `uv run forever profile import`.
    - À voir : les personnages de la bêta dans `uv run forever profile list --archived` ; les nouveaux personnages
      importés (produit de la version finale).
14. **Mesures** : après quelques sessions de jeu, `uv run forever measures refresh`.
    - À voir : les journaux de la bêta « retenus » (autre produit), ceux de la version finale mesurés ; les PV
      remesurés sortent de `forever measures inherited`.
15. Tests en jeu restés en attente : section du même nom, facultatifs, en jouant normalement.

## Portable

Portable Lenovo Legion (nom Windows à compléter). Mêmes étapes que le PC de jeu, dans le même ordre ; les différences
sont dites à chaque étape.

1. **Sauvegarde, jeu fermé** : `uv run forever backup --reason "avant le lancement"` ; la racine est choisie sur le
   portable (disque fixe hors système, sinon OneDrive connecté, sinon Documents avec un avertissement de
   diagnostic) ; poser `FOREVER_BACKUP_DIR` si besoin.
2. **Installer la version finale par Battle.net** si le jeu y est joué ; sinon, seules les étapes 5, 8, 9, 11 et 13
   s'appliquent (pas d'addons ni de journaux sur ce PC).
3. `uv run forever wow list` : même lecture qu'au PC de jeu ; la racine peut différer (autre disque) : section « Le
   jeu change de dossier ».
4. `uv run forever wow adopt "<dossier>"` : l'adoption est propre à chaque PC (journal des versions du cache local).
5. `powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1`, accepter le nouveau `FOREVER_WOW_DIR`,
   nouveau terminal.
6. Addons, jeu fermé : `uv run python scripts/install_addon.py`, puis `uv run forever bridge install`.
7. Interface : `/dump select(4, GetBuildInfo())` ; la valeur ajoutée au PC de jeu arrive par `git pull` (refaire
   l'étape 6 après le `git pull`).
8. Tâches : `uv run forever bridge autostart install`, puis
   `powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1` ; pont relancé comme au PC de jeu.
9. `uv run forever doctor` : 0 bloquant.
10. Première connexion si le jeu est joué sur le portable.
11. `uv run forever update` : si le PC de jeu l'a déjà fait, la version finale arrive par `git pull` (rien à
    télécharger).
12. `uv run forever measures inherited`.
13. Profil : le profil est propre à chaque PC ; `uv run forever profile archive --product <produit de la bêta>`, puis
    `uv run forever profile import`.
14. `uv run forever measures refresh` si des journaux de la version finale y sont écrits.

## Le jeu change de dossier

Nouveau disque, `Program Files` ↔ `Program Files (x86)`, dossier choisi dans Battle.net :

1. `uv run forever wow list` : les racines cherchées sont listées (`--json`, champ `roots`) : `Program Files (x86)`,
   `Program Files`, `\World of Warcraft` et `\Games\World of Warcraft` de chaque disque fixe, plus les parents de
   `FOREVER_WOW_DIR` et `FOREVER_WOW_FORCE`.
2. Racine ailleurs : la déclarer, `[Environment]::SetEnvironmentVariable("FOREVER_WOW_ROOTS", "D:\Jeux\World of Warcraft", "User")`
   (plusieurs racines séparées par `;`), nouveau terminal, puis `uv run forever wow list`.
3. Produit illisible (ni `.flavor.info`, ni ligne unique dans `.build.info`) : forcer le dossier,
   `[Environment]::SetEnvironmentVariable("FOREVER_WOW_FORCE", "<dossier>", "User")` (l'emporte sur l'adoption).
4. Puis, dans l'ordre : étape 5 (`install_plugin.ps1`), étape 6 (addons), étape 8 (tâches), étape 9 (`forever doctor`).
   La surveillance du pont suit seule le nouveau choix (jeu fermé, événement `autostart_wow_changed` du journal du
   pont) ; une tâche qui force l'ancien dossier est à recréer.
5. SavedVariables restées dans l'ancien dossier, même produit : `uv run forever backup restore --only wtf`, jeu fermé.

## Antivirus

`forever doctor` ne peut pas lire les exclusions de Defender sans droits d'administrateur (contrôle `antivirus`
toujours `[?]`). Si Defender bloque ou ralentit le pont, la mise à jour ou le jeu, poser les exclusions à la main,
dans un PowerShell **administrateur** : le dossier du dépôt, le dossier du cache (`%USERPROFILE%\.cache\forever` ou
`FOREVER_CACHE_DIR`), l'interpréteur de uv (`%APPDATA%\uv\python`) et le dossier du jeu ; par exemple
`Add-MpPreference -ExclusionPath "C:\Users\<moi>\Documents\wow-forever"`. forever ne pose jamais d'exclusion.

## Remise à zéro du PC

Leçon du 12 octobre (décision 256) : tout C: effacé. Ordre :

1. Installer uv (`winget install --id astral-sh.uv`), Git for Windows, puis cloner le dépôt.
2. `uv sync` à la racine du dépôt.
3. GitHub CLI : `winget install --id GitHub.cli`, puis `gh auth login`.
4. Claude Code : l'installer, lancer `claude`, puis `/login`.
5. `powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1`, nouveau terminal.
6. Tâches : `uv run forever bridge autostart install`, puis
   `powershell -ExecutionPolicy Bypass -File scripts\install_update_task.ps1`.
7. Restauration, jeu fermé : `uv run forever backup list`, puis `uv run forever backup restore` (la plus récente ;
   l'état courant est sauvegardé d'abord). Les sauvegardes sont sur F: (jamais sur C: par défaut).
8. Addons : `uv run python scripts/install_addon.py` et `uv run forever bridge install`.
9. `uv run forever doctor` jusqu'à 0 bloquant.

## Tests en jeu restés en attente

Tous facultatifs (décisions 247 et 260), à faire en jouant normalement ; le détail de chacun est dans
`docs/OPEN_QUESTIONS.md` (identifiant entre parenthèses) ou `docs/ADDON.md`.

- Lancement : `.toc` sans suffixe lus par la version finale et numéro d'interface (LNC1) ; version finale à côté de
  la bêta ou à sa place (LNC2) ; produit de la version finale (DON4).
- Monstres et journaux : MON7, LOG6.
- Pont en jeu : BR2, BR4, BR5, BR6, BR7, BR9 ; sondes et procédure 21 (sonde I) de `docs/ADDON.md`.
- Feuilles de route RestedXP : RXP1, RXP2.
- Profil et exports : PRO1, NFB1.
- Legacy et API Blizzard : LEG1, LEG2 (`forever api probe` après le lancement).
- Familiers du Chasseur : PET1.
