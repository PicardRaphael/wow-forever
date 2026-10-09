# Vision — forever-core, le cerveau qui pilote les addons de Forever

Adoptée le 2026-10-07 (décision 193). Ce document dit **où va le projet** ; `docs/SPEC.md` dit ce qu'il fait,
`docs/ROADMAP.md` dans quel ordre, `docs/ARCHITECTURE.md` comment. Aucun chiffre de jeu ici.

## En une phrase

forever-core calcule, décide et prépare ; les meilleurs addons de Forever, déjà installés par le joueur, affichent
et font jouer. Le projet **pilote** ces addons au lieu de refaire leur interface.

## Pourquoi ce virage

Les tranches faites ont construit ce qui manque aux addons de la communauté : des données lues dans le client et
suivies version par version, un moteur de combat testé, un registre des mécaniques, une certitude et une
provenance sur chaque chiffre. Ce que les addons font déjà très bien, nous le refaisions en partie (ForeverAssist
V1 à V3, comparaison d'équipement en infobulle, fiches en jeu) :

| Besoin en jeu | Déjà fait par | Ce que forever-core apporte |
| --- | --- | --- |
| Suivre un build de talents niveau par niveau | Talents Forever | le build **calculé** pour le personnage et le contexte, en lien cliquable |
| Listes BiS, macros, rappels, journal des donjons | Naowh Forever, Forever Companion | la liste **calculée** pour le personnage, et l'endroit où looter chaque objet |
| Interface (barres, cadres, profils) | EllesmereUI | le profil qui convient au personnage et à son rôle |
| Quêtes, zones, donjons | Questie, Forever Guide, Zone Level: Forever, ForeverDungeonJournal | l'objectif suivant, chiffré (XP par heure, bonus d'XP actifs) |
| Conversation avec l'agent | rien d'utilisable tel quel | un pont recodé dans le projet, avec des boutons en jeu |

## La boucle

Chaque domaine du jeu passe par les cinq mêmes étapes. Une étape absente d'un domaine est un angle mort, pas
une raison de deviner.

### 1. Observer
Tout ce qui se lit sur le disque du joueur, sans réseau et sans lecture de la mémoire du jeu :
- journaux de combat (`WoWCombatLog-*.txt`, T04a) ;
- relevés de **ForeverLogger**, notre addon (niveau, talents, familier, observations hors combat : PV1, CH0, DJ1) ;
- sauvegardes des addons (Questie, Auctionator, Forever Bestiary, Talents Forever, puis Naowh Forever et Forever
  Companion) ;
- correctifs du serveur (`DBCache.bin`, `Hotfix.log` : T08b, T08c) et version du client (`.build.info` : T08a) ;
- notes officielles de Blizzard (signal seulement, lancé à la main : décision 148).

### 2. Comprendre
Le moteur (`forever/engine/`, fonctions pures) et le registre des mécaniques (`docs/MECHANICS_REGISTRY.yaml`)
transforment ces observations en règles du jeu, avec leur certitude (`certain`, `probable`, `suppose`). Une règle
incertaine est marquée `suppose` avec sa question dans `docs/OPEN_QUESTIONS.md` ; un bug reconnu par Blizzard
n'est jamais modélisé.

### 3. Décider
Pour chacun des personnages du joueur (profil multi-sources, décision 125) :
- **talents** : build par contexte (T05 pour le Mage, tranches de classe pour les autres) ;
- **objets à viser et où les looter** : plan d'équipement (T10), donjons et butin (DJ1) ;
- **route de quêtes et de donjons** : zone, donjon et objectif suivant selon le niveau (fait en partie :
  `forever lookup zones`), chiffrés par le modèle d'XP de Forever (T04d) ; pas de guide pas à pas, que Questie et
  Forever Guide font en jeu ;
- **bonus d'XP** : bonus actifs et à prendre (repos, campement, nourriture, Legacy : T04f) ;
- **familier** du Chasseur (CH0 fait, CH1) ; **métiers** (MT1) ; **PvP** (PV1 fait, PV2, AN1).

### 4. Agir en jeu
forever-core ne joue jamais à la place du joueur : il **prépare** ce que le joueur ouvre ou importe lui-même.
- **Lien Talents Forever** du build calculé (FA1) ;
- **liste BiS** et poids des statistiques dans **Naowh Forever** (T10a pour le Mage, puis T10), par ses points d'import ;
- **profils EllesmereUI** par personnage et par rôle (tranche EX1) ;
- **macros** par classe, en texte à importer (EX1, décision 195) ;
- **chat et boutons en jeu** : poser une question à l'agent sans quitter le jeu, et lancer en un clic ce qu'il
  sait faire (P06a pour le chat, P06b pour les boutons).

Règle commune (décision 196) : un export vers un addon se fait dans la tranche qui calcule la donnée, et
seulement si l'addon a un point d'import ; sinon, notre addon affiche la donnée. Le code des addons de la
communauté n'est jamais modifié.

### 5. Apprendre
- **Mesure continue** : chaque journal et chaque relevé améliore le modèle (`forever measures refresh`, preuves du
  registre, protocoles de `docs/research/`) ; l'analyse de mes combats (AN1, AN2) compare le réel au modèle.
- **Mise à jour automatique des données** : `forever update` suit le jeu, les correctifs du serveur, les journaux
  et les addons, et ne s'arrête que si un résultat change pour le joueur (T08d, affiné par T08e).

## Trois paris, par ordre de valeur

1. **Chat et boutons en jeu** (P06a, puis P06b) : la valeur du projet devient visible là où le joueur joue. Un bouton
   n'apparaît que si la tranche qui le calcule est faite.
2. **Exports vers les addons** (FA1, T10, EX1) : chaque décision de forever-core arrive dans l'addon que le joueur
   utilise déjà, sans nouvelle interface à apprendre.
3. **Boucle de mesure** : chaque session de jeu rend le modèle plus juste, et chaque chiffre affiché dit d'où il
   vient.

L'ordre des tranches qui sert ces paris est appliqué à `docs/ROADMAP.md` depuis le 2026-10-07 (décision 202 ;
raisons dans `tasks/ordre-propose-2026-10-07.md`).

## Ce qu'on refuse

- **Refaire ce que font déjà les addons** : pas d'interface concurrente de Talents Forever, Naowh Forever,
  EllesmereUI, Questie ou Forever Guide. Notre addon n'affiche que ce qu'aucun addon installé ne sait recevoir.
- **Multiplier les chantiers** : une tranche à la fois, dans l'ordre de `docs/ROADMAP.md` ; un pari ne démarre pas
  un chantier parallèle.
- **Promettre des chiffres non mesurés** : un chiffre sans source dans `forever/data/` n'existe pas ; un chiffre
  `suppose` est affiché comme tel, en jeu comme dans le terminal.
- **Agir à la place du joueur** : aucune fonction d'action, aucune entrée simulée, aucune lecture de la mémoire du
  jeu, aucun message de chat envoyé automatiquement (`docs/ADDON.md`).

## Ce qui ne change pas

Les invariants de `CLAUDE.md` restent : chiffres de jeu dans `forever/data/` seulement, formules dans
`forever/engine/`, bloc `provenance` sur chaque résultat, registre à jour, tests sans réseau, règles de l'addon.
Deux lignes rouges de l'addon sont levées **partiellement**, à la demande du joueur et dans un périmètre strict :
la bande de pixels du pont (décision 194) et le texte des macros exportées (décision 195).

## Crédits

Le pont de P06a reprend la technique de **wow-ai** (https://github.com/chelinho139/wow-ai, chelinho139/wow-ai, commit
3756eb5a du 2026-09-27, **licence MIT** vérifiée le 2026-10-08) et une partie de son code : codec de la bande, dessin
à l'échelle physique, capture de la zone client, format des messages, réserve d'emplacements chargés à la demande et
leur installation, cadre de la fenêtre. Chaque fichier repris porte la notice MIT complète en tête (liste fermée,
contrôlée par `tests/unit/test_bridge_license.py`) : `forever/bridge/codec.py`, `capture.py`, `record.py`,
`slots.py`, `install.py`, `addon/ForeverBridge/Codec.lua`, `ForeverBridge.lua`. Mesures du client citées sans reprise
de code : wow-forever-codex (0xinuarashi, dépôt sans licence, lu le 2026-10-09 : fichiers vus au lancement seulement,
canal par mesures de polices, piste de P06b).
