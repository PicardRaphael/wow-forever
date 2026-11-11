# FR1 — Guides RestedXP de Forever en français, générés et tenus à jour

Demande de l'utilisateur du 2026-11-11. Plan seul : aucun code, aucune branche. Exécution dans une nouvelle session,
sur la branche `fr1`, après validation des questions de la section 9.

## 1. Constat (mesuré le 2026-11-11, RXPGuides v4.11.35-7, lecture seule)

- Client en frFR : RestedXP désactive les guides anglais (`enabledLocale["frFR"] = true`, chaque fichier anglais
  sort dès sa première ligne) et charge `lang/Guides-frFR/GuideList-forever.xml`.
- 22 fichiers Forever (13 parcours, 9 `dungeon/`) : 21 ont autant de guides en anglais qu'en français. Seul
  `RestedXP-Skyborne.lua` est incomplet : 200 guides en anglais, 2 en français (Zéphras 1-9 et 9-13). Les 198 autres
  disparaissent en français.
- Ce que RestedXP traduit, mesuré sur 54 517 lignes alignées des 21 fichiers complets :
  - texte libre après `>>`, lignes `+`, `.vendor`, `.trainer` : toujours ;
  - noms de quête après l'identifiant (`.accept`, `.turnin`) : toujours ;
  - **arguments en nom** : `.zone`, `.subzone`, `.cast`, `.fly` toujours ; `.train` presque toujours (nom du sort
    entre crochets) ; `.target`, `.mob`, `.use`, `.goto` (texte après `>>`) partiellement ;
  - en-tête : `#name`, `#displayname` et `#next` traduits ;
  - jamais : `.waypoint`, `.unitscan`, `.pin`, `#hardcore`, `#season`, `#softcore`, identifiants, coordonnées,
    filtres `<<` ;
  - les icônes `|T…|t` sont souvent retirées devant un nom de sort traduit.
- **Écart avec la consigne « commandes intactes »** : RestedXP traduit les arguments en nom (`.zone`, `.cast`,
  `.target`…), parce que le client frFR compare ces noms au texte du jeu en français. Les laisser en anglais
  casserait le ciblage et les validations d'étape. Le plan suit RestedXP : commande, identifiants et coordonnées
  intacts, noms traduits quand le nom officiel est connu (question Q2).
- Les guides sont rangés par `groupe||nom` (`GuideLoader.lua:159`) et `#next` désigne un nom exact. Les deux guides
  Zéphras français pointent déjà vers des noms traduits (« 13-15 Marche de l’Ouest », apostrophe typographique,
  etc.) : nos `#name` générés doivent leur être identiques au caractère près.
- Noms officiels disponibles hors réseau :
  - quêtes : 1 582 des 1 864 quêtes du fichier Skyborne dans `Questie/Localization/lookups/Classic/lookupQuests/frFR.lua` ;
    les 282 restantes (identifiants 79xxx et 9xxxx, propres à Forever) seulement dans `Cache/WDB/frFR/questcache.wdb`
    (quêtes vues en jeu) ;
  - sorts : `SpellName` frFR (cache wago, version du client) ; zones : `UiMap` frFR ; races, familles : déjà là ;
  - PNJ (2 817 noms colorés distincts) et objets (740 + 844 noms entre crochets) : Questie frFR (`lookupNpcs`,
    `lookupItems`, par identifiant, à rapprocher du nom anglais de la base Questie enUS), `creaturecache.wdb` frFR ;
    `ItemSparse` et `AreaTable` frFR ne sont pas encore téléchargés (question Q3) ;
  - les 21 fichiers déjà traduits par RestedXP : glossaire anglais → français relevé ligne à ligne (noms de PNJ,
    de zones, tournures), prioritaire sur le reste.
- Fichier source : ASCII, fins de ligne CRLF. Dossier `RXPGuides/lang/` accessible en écriture.
- La veille relève déjà l'empreinte de chaque addon (`forever/addons.py`, `fingerprint`) à l'étape `addons` de
  `forever update`.

## 2. Décision 288

**Qui le maintient déjà mieux que nous ?** RestedXP, qui traduit lui-même ses guides (21 fichiers sur 22). Leur
traduction prime toujours : un guide qu'ils livrent en français n'est jamais régénéré. Nous ne comblons que le trou
(198 guides) et nous effaçons dès qu'ils le comblent. Aucune autre traduction française de ces guides n'existe à
notre connaissance (à revérifier sur Internet en début d'exécution : CurseForge, Discord RestedXP, GitHub).

**Que se passe-t-il au prochain patch ?** Une mise à jour de RestedXP remplace notre fichier par le leur (2 guides).
La veille le voit (empreinte de `Guides/forever/` ou de `lang/Guides-frFR/forever/` changée, marqueur FR1 absent),
régénère depuis la nouvelle source anglaise et ne traduit que les phrases nouvelles (mémoire de traduction) ; elle
prévient par la carte « Mis à jour ». Un nouveau patch du jeu ne casse rien : les noms officiels sont relus dans les
données de la version installée. Rien ne devient un test rouge : un changement donne un rapport (phrases nouvelles,
noms restés en anglais).

## 3. Périmètre

- Dedans : tout guide Forever en clair dont le fichier anglais a plus de guides que le fichier français (aujourd'hui
  `RestedXP-Skyborne.lua`, 198 guides), parcours et `dungeon/`.
- Dehors : guides payants ou chiffrés (tri « en clair / refusé » de `forever/rxp_guides.py`, jamais décodés) ;
  autres saisons (Classic, SoD…) ; EllesmereUI (jamais touché) ; tout autre addon.
- Usage personnel. Le texte de RestedXP (licence CC BY-NC-SA 4.0) n'entre jamais dans le dépôt (décisions 268 et
  277) : ni guides, ni mémoire de traduction, ni extraits dans les tests. En tête du fichier généré : attribution à
  RestedXP, licence, mention « traduction automatique personnelle, non officielle ».

## 4. Conception

Nouveau module `forever/rxp_fr/` (aucune formule de combat, aucun chiffre de jeu) :

1. **Lecture** (`source.py`) : réutilise le découpage des blocs de `rxp_guides.py`. Pour chaque fichier Forever :
   guides anglais, guides français existants (par `#name` anglais reconstitué par position dans le fichier), tri en
   clair / refusé.
2. **Découpage d'une ligne** (`tokens.py`) : sépare ce qui ne se traduit jamais (commande, identifiants,
   coordonnées, filtres `<<`, `|c…` / `|r`, `|T…|t`, `|H…|h`, `%s`, nombres) de ce qui se traduit (texte libre, noms).
   Le texte à traduire devient un **gabarit** : noms connus remplacés par des jetons (`{npc:1}`, `{quest:176}`,
   `{spell:6673}`, `{zone:1411}`, `{item:…}`), pour qu'une même phrase serve à toutes les étapes.
3. **Noms officiels** (`names.py`), ordre de priorité, chaque nom avec sa source :
   1. glossaire tiré des 21 fichiers déjà traduits par RestedXP ;
   2. tables frFR du client (version installée, cache wago) : `SpellName`, `UiMap`, `ChrRaces`, `CreatureFamily`,
      et `ItemSparse`, `AreaTable` si Q3 est acceptée ;
   3. `questcache.wdb` et `creaturecache.wdb` frFR du client (extension des lecteurs existants aux chaînes) ;
   4. Questie frFR (`lookupQuests`, `lookupNpcs`, `lookupItems`, `lookupObjects`), certitude `suppose` comme ailleurs.
   Sans nom officiel : le nom **reste en anglais** (accord de l'utilisateur du 2026-11-11 : « tu peux laisser du
   franglais ») et figure au rapport. Un nom n'est jamais traduit librement.
4. **Phrases types** (`patterns.py`) : tournures de RestedXP relevées dans les paires alignées (« Parlez à »,
   « Acceptez », « Rendez », « Apprenez », « Vendez », « Tuez », « Allez jusqu'à »…), appliquées par motif sur le
   gabarit. Liste de motifs dans le code, sans texte de guide.
5. **Mémoire de traduction** (`memory.py`) : gabarit anglais normalisé → gabarit français, avec origine
   (`restedxp`, `motif`, `traduit`, `manuel`), date et empreinte. Hors dépôt, dans un dossier durable
   (`~/.forever/rxp_fr/memoire.json`, à côté du profil, pas le cache purgeable), sauvegardé par `forever backup`.
   Une entrée `manuel` n'est jamais écrasée.
6. **Traducteur des phrases libres** (`translator.py`) : interface injectée. Phrases traduites depuis la VO
   anglaise. Lot initial : sous-agents de la session d'exécution (un lot de guides par agent, en worktree), qui
   écrivent dans la mémoire. Mises à jour : selon Q1. Sans traducteur, la phrase reste en anglais et figure au
   rapport. Aucun réseau dans les tests (traducteur factice).
7. **Assemblage** (`build.py`) : première ligne `if GetLocale() ~= "frFR" then return end`, puis marqueur FR1
   (version du générateur, empreinte de la source anglaise, version de RXPGuides, attribution). Les guides que
   RestedXP a traduits sont recopiés tels quels, dans l'ordre du fichier anglais ; les autres sont générés. Encodage
   UTF-8 sans BOM, fins de ligne CRLF comme la source. `#name` et `#next` traduits par la même table de noms de
   guide, alignée sur les `#next` déjà présents chez RestedXP.
8. **Validateur** (`validate.py`), bloquant : pour chaque guide, même suite de commandes, d'identifiants, de
   coordonnées et de filtres `<<` que la source ; codes couleur équilibrés ; aucun `]]` introduit ; chaque `#next`
   résolu par un `#name` du fichier ou des autres fichiers frFR ; chargement sous lupa avec un faux
   `RXPGuides.RegisterGuide` : 200 guides rendus. Un échec n'écrit rien.
9. **Écriture** (`install.py`) : sauvegarde du fichier de RestedXP avant la première écriture
   (`~/.cache/forever/backups/rxp_fr/`), écriture atomique, `forever rxp traduire --annuler` remet la sauvegarde.
   N'écrit que sous `RXPGuides/lang/Guides-frFR/forever/`.

Commande `forever rxp traduire` (CLI) : `--simulation` (rapport sans écrire), `--json`, `--annuler`,
`--manquants` (noms et phrases restés en anglais), `--sans-traducteur`. Sortie : guides générés, recopiés, refusés ;
phrases venues de la mémoire, des motifs, traduites, restées en anglais ; noms par source ; bloc `provenance`
(version du jeu, empreinte des données, date, certitude `probable` pour le texte, `certain` pour les noms du client,
`suppose` pour Questie). Outil MCP : action `rxp_fr` de `forever_route` en lecture seule (rapport), si utile.

Veille : sous-étape de `addons` dans `forever update` : si l'empreinte de `Guides/forever/` ou de
`lang/Guides-frFR/forever/` a changé, ou si le marqueur FR1 manque, régénère (sans écrire si `--dry-run`) et
l'annonce par la carte « Mis à jour » ; `forever update undo <id>` remet le fichier précédent.

## 5. Tests d'abord (fixtures synthétiques, aucun texte de RestedXP)

`tests/fixtures/rxp_fr/` : mini-addon factice (un fichier anglais de 3 guides écrits pour le test, sa traduction
partielle d'1 guide, petites tables de noms frFR inventées pour le test et marquées comme telles).

- `test_rxp_fr_tokens.py` : commandes, identifiants, coordonnées, filtres, codes `|c|r|T|t|H|h` intacts ; gabarit
  et jetons ; reconstitution exacte.
- `test_rxp_fr_names.py` : ordre de priorité des sources ; nom absent → anglais et rapport ; jamais inventé.
- `test_rxp_fr_memory.py` : une phrase déjà traduite ne repasse pas au traducteur ; `manuel` jamais écrasé ;
  seule la phrase nouvelle est envoyée après un changement de la source.
- `test_rxp_fr_build.py` : garde-fou en première ligne, marqueur, guides de RestedXP recopiés, CRLF ; `#next`
  résolus ; validateur qui refuse une commande changée, un `]]`, un code couleur déséquilibré ; rien d'écrit sur
  échec.
- `test_rxp_fr_lua.py` : le fichier généré se charge sous lupa et enregistre le bon nombre de guides.
- `test_rxp_fr_cli.py` : `forever rxp traduire --simulation --json` (bloc `provenance`), `--annuler`.
- `test_update_rxp_fr.py` : la veille régénère sur empreinte changée ou marqueur absent, ne fait rien sinon.
- Test `slow` local seulement (hors CI, lit l'addon installé s'il existe, sinon sauté) : validateur sur le vrai
  fichier, et taux de reproduction des 21 fichiers de RestedXP par nos motifs et noms (mesure de qualité, sans seuil
  bloquant).

## 6. Étapes (petits commits `FR1: …`)

1. Tests de découpage, noms, mémoire, assemblage, validateur, CLI, veille : constater l'échec, committer.
2. Découpage et validateur.
3. Noms : glossaire tiré des paires, lecteurs frFR (tables wago, caches WDB, Questie).
4. Motifs et mémoire ; rapport des manquants.
5. Assemblage, écriture, sauvegarde, annulation ; commande CLI.
6. Lot initial : un sous-agent par lot d'environ 25 guides (8 lots), en worktree depuis `fr1`, qui traduit depuis
   l'anglais les phrases restantes et écrit sa part de mémoire (hors dépôt) ; fusion des mémoires, puis génération
   et validation.
7. Accroche dans la veille, carte « Mis à jour », annulation.
8. Docs : `docs/USAGE.md`, `docs/DECISIONS.md` (nouvelle décision), `CLAUDE.md` (liste des accès réseau si Q1 =
   oui), `docs/ROADMAP.md`. Registre des mécaniques : non concerné (aucune mécanique de jeu).
9. `uv run tasks.py quick`, push, CI verte Ubuntu et Windows, fusion fast-forward, suppression de la branche.

## 7. Procédure d'essai en jeu (client frFR)

1. `uv run forever rxp traduire` puis `/reload` (ou relancer le jeu).
2. Ouvrir la liste des guides RestedXP : la section Forever montre les guides 22-60 et les guides de donjon, noms en
   français.
3. Charger un guide 22-60 (par exemple celui de votre zone actuelle) : étapes en français, noms de quêtes et de PNJ
   comme en jeu, flèche et coordonnées correctes, une étape `.accept` se coche à l'acceptation.
4. Charger un guide de donjon : affichage en français, aucune erreur Lua (`/console scriptErrors 1`).
5. Finir le guide 9-13 Zéphras : le guide suivant proposé se charge (chaîne `#next` intacte).
6. Me dire les phrases restées en anglais ou mal traduites : elles passent en `manuel` dans la mémoire.

## 8. Risques

- Nom officiel faux ou absent pour un contenu propre à Forever : reste en anglais, listé ; se corrige seul quand la
  quête est vue en jeu (cache WDB) ou que le client l'apporte.
- Ciblage `.target` / `.mob` en anglais quand le nom manque : l'étape s'affiche mais la macro de ciblage ne trouve
  pas le PNJ (franglais accepté).
- Taille du fichier (environ 150 000 lignes) : même taille que l'anglais, déjà chargé par RestedXP.
- RestedXP change sa syntaxe : le validateur refuse, rien n'est écrit, le rapport le dit.

## 9. Questions pour l'utilisateur (bloquantes)

- **Q1 — Traduction automatique des phrases nouvelles lors des mises à jour.** Recommandé : `forever rxp traduire`
  et la veille lancent `claude -p` (comme le pont de P06a) pour les seules phrases absentes de la mémoire, sans
  outil, avec le glossaire et les noms officiels imposés ; nouvel accès réseau (API d'Anthropic), nouvelle décision
  numérotée et ajout à la liste de `CLAUDE.md`. Sinon : phrases nouvelles laissées en anglais jusqu'à une session
  Claude lancée à la main.
- **Q2 — Arguments en nom traduits comme RestedXP** (`.zone`, `.subzone`, `.cast`, `.fly`, `.train`, `.target`,
  `.mob`, `#name`, `#next`) quand le nom officiel français est connu, plutôt que gardés en anglais comme le dit la
  consigne « commandes intactes ». Recommandé : oui (sinon validations d'étape et ciblage cassés en frFR).
- **Q3 — Télécharger aussi `ItemSparse` et `AreaTable` en frFR** dans le cache wago par `forever update` (accès
  réseau déjà permis, décision 179 ; seule la liste des tables change). Recommandé : oui (noms d'objets et de
  sous-zones officiels du client Forever, au lieu de Questie Classic).
- **Q4 — Mémoire de traduction hors dépôt** dans `~/.forever/rxp_fr/` (durable, sauvegardée par `forever backup`),
  jamais dans le dépôt (décisions 268 et 277). Recommandé : oui.
