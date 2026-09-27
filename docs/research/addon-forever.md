# Addon « en direct » pour forever-core sur WoW: Forever — état des lieux, règles, canaux et architecture recommandée

> Rapport de recherche du 27/09/2026 (claude.ai), recopié pour Claude Code. À utiliser pour rédiger `docs/ADDON.md`. Sources principales en fin de fichier.
> Légende : **[Certain]** source primaire ou mesure publiée sur le client Forever ; **[Probable]** sources concordantes ou comportement Retail non remesuré ; **[Supposé]** inférence ou source unique.

**Recommandation : il n'existe pas de canal temps réel légitime entre l'addon et Claude Code.** Forever fait tourner l'API Retail (Midnight 12.1.5), avec les « valeurs secrètes » et le refus d'abonnement au journal de combat. Construire un addon d'affichage alimenté par un fichier Lua que `forever` régénère et que le jeu relit à chaque `/reload`, un canal retour par SavedVariables, puis plus tard seulement une fenêtre de bureau qui lit `WoWCombatLog.txt` pour l'analyse après le combat. Pas de conseils de rotation en direct.

## TL;DR

- **Forever n'est pas du Classic côté addons.** Blizzard : Forever partage l'architecture d'interface de Mainline, avec la grande majorité des API de 12.1.5 ; les restrictions de Midnight (valeurs secrètes) y sont actives. Interface `16001`, suffixe de TOC `_Camelot`, `WOW_PROJECT_ID` égal à celui de Retail. Partir des sources Retail et de la branche `forever` de wow-ui-source.
- **Seul aller-retour fiable : des fichiers, rythmés par `/reload`.** Aller : fichier Lua écrit par forever-core dans le dossier de l'addon (modèle TSM AppData ou WeakAuras Companion). Retour : SavedVariables. `ReloadUI()` est protégé, donc le rafraîchissement reste manuel. Journal de discussion inutilisable (écrit à la déconnexion, ignore les `print` d'addon). Journal de combat écrit par paquets (retard de quelques secondes à plusieurs minutes).
- **Recommandé : V1 affichage de données précalculées ; V2 export de contexte par SavedVariables ; V3 compagnon de bureau pour l'analyse des journaux.** À éviter absolument : encodage de pixels, lecture d'écran ou de mémoire, entrées simulées (bannissement).

## 1. Créer un addon aujourd'hui, et ce qui s'applique à Forever

### 1.1 Forever = famille Mainline

- [Certain] Déclaration Blizzard (Discord WoW UI, relayée par Wowhead et Icy Veins, 17/09/2026) : Forever partage l'architecture d'interface de Mainline et la grande majorité des API de 12.1.5 ; « Camelot » (à renommer avant le lancement) et « Standard » sont deux types de jeu de la même famille ; les changements de « désarmement » des addons de Midnight, dont les valeurs secrètes, sont actifs dans Forever.
- [Certain] Le client cherche `<Addon>_Camelot.toc` avant le TOC sans suffixe. `_Mainline.toc` charge aussi sur Forever, mais également sur Midnight.
- [Certain] `WOW_PROJECT_ID == WOW_PROJECT_MAINLINE` sur Forever ; détection fiable seulement au chargement (fichier listé uniquement dans le `_Camelot.toc`, ou numéro d'interface).
- Divergence : l'en-tête du journal de combat indique `PROJECT_ID 18`, la constante Lua vaut 1 — deux identifiants différents [Supposé] ; vérifier avec `/dump WOW_PROJECT_ID`.
- [Certain] Fonctions globales anciennes disparues (`GetItemInfo`, `GetSpellInfo`, `GetTalentInfo`…), remplacées par `C_Item`, `C_Spell`, `C_Traits`.

### 1.2 Structure (valable pour Forever)

```
## Interface: 16001
## Title: ForeverAssist
## Notes: Affichage des données forever-core
## Version: @project-version@
## SavedVariables: ForeverAssistDB
## SavedVariablesPerCharacter: ForeverAssistCharDB
Data\Generated.lua
Core.lua
UI.lua
```
- Un seul TOC `_Camelot` (secours sans suffixe facultatif) ; plusieurs valeurs d'interface séparées par des virgules acceptées.
- Lua 5.1 bridé ; XML facultatif (pointer vers `Blizzard_SharedXML/UI.xsd`).
- Cycle de vie : `ADDON_LOADED`, puis `PLAYER_LOGIN`, puis `PLAYER_ENTERING_WORLD`. **[Certain, build 70009]** Sans `## LoadSavedVariablesFirst: 1`, le client remplace la variable globale à `ADDON_LOADED` : un alias `local db = ForeverAssistDB` au niveau du fichier pointe vers l'ancienne table. Règle : initialiser dans `ADDON_LOADED`, jamais d'alias au niveau du fichier.
- Sur Forever, `RegisterEvent` avec un événement inconnu lève une erreur et interrompt le fichier : encapsuler dans `pcall`.
- Commandes slash, frames (`CreateFrame`, `BackdropTemplate`), panneau `Settings` : comme Retail.
- Bibliothèques (LibStub, Ace3, LibDataBroker…) : fonctionnent sur la base Retail [Probable] ; AceDB a dû être patché ailleurs (un royaume par ruleset sur Forever). En V1, pas d'Ace3.

### 1.3 Outils de développement

| Besoin | Outil | Statut Forever |
|---|---|---|
| Référence d'API pour l'agent | `imperial64/forever-addon-dev` (plugin Claude Code : skills build, api, restrictions, regenerate ; linter `tools/lint_addon.py` ; addon sonde ForeverProbe) | [Certain] Généré depuis la doc du client, régénéré pour 70009 |
| API, source de l'UI, validation TOC/XML | `hated-wow-mcp` (`claude mcp add wow -- npx -y hated-wow-mcp`, flavor `mainline`) | [Probable] |
| Autocomplétion | Extension VS Code `ketho.wow-api` + LuaLS | [Probable] Annotations Retail |
| Lint | `luacheck` (`read_globals` générés depuis la référence imperial64) | [Certain] |
| Tests hors jeu | `busted` sous Lua 5.1 + bouchons de l'API | [Certain] |
| Débogage | BugGrabber/BugSack, `/dump`, `/fstack`, `/etrace`, `/api` | [Probable] ; le client cesse de rapporter après 100 erreurs Lua par session |
| Empaquetage | Packager BigWigs ≥ v2.6.0 (support Forever, `_Camelot.toc`) | [Certain] ; CurseForge et Wago acceptent Forever, WoWInterface non |

Ordre de confiance des sources : mesures publiées sur le client (imperial64), branche `forever` de wow-ui-source, warcraft.wiki.gg (pages 12.x), Townlong Yak ; articles de presse à ignorer.

## 2. Limites et règles

### 2.1 Bac à sable

- [Certain] Pas de réseau, pas de fichiers arbitraires, pas de mémoire ; seuls les SavedVariables sont écrits (au `/reload`, à la déconnexion, à la sortie). L'addon ne peut rien ajouter au journal de combat.
- [Certain] Fonctions protégées et taint : actions de jeu réservées au code sécurisé déclenché par une vraie touche ; pas de modification des frames sécurisées en combat ; `UseAction`, `ReloadUI`, `SetBinding`, `SetOverrideBindingClick` parmi les plus restreintes.
- [Certain, 70009] Snippets sécurisés : fonctionnent hors combat ; en combat `Execute` refusé.

### 2.2 Restrictions de Midnight appliquées à Forever

- [Certain] Les informations de combat sont des valeurs secrètes : affichables mais pas « connues » par les addons.
- [Certain, mesuré sur Forever] **Abonnement au journal de combat refusé** (`COMBAT_LOG_EVENT` et `COMBAT_LOG_EVENT_UNFILTERED`, ADDON_ACTION_FORBIDDEN, même hors combat) ; `UnitPower` secret en permanence ; `UnitHealth` secret même hors combat ; barres d'incantation fonctionnelles ; état de menace lisible, pas sa valeur.
- [Certain] Le client **écrit toujours `WoWCombatLog.txt`** (format 22, projet 18, client 1.60.1) : c'est la voie ForeverLogger, seule voie pour mesurer les PV des monstres.
- [Probable] Compteur de dégâts et Cooldown Manager natifs sur Forever ; « Assisted Highlight » de Retail non confirmé sur Forever.
- **Conséquence** : en combat, l'addon peut afficher mais pas calculer. Un moteur de décision de rotation est impossible dans l'addon et contraire à l'intention de Blizzard s'il est fait à l'extérieur en direct.

### 2.3 Politique officielle

- [Certain] Addons gratuits ; code ni caché ni obfusqué ; pas de publicité ni de dons sollicités ; pas d'usage excessif du chat ; Blizzard peut désactiver des fonctionnalités.
- [Certain] Interdiction des logiciels qui modifient le client ou contrôlent le jeu.

### 2.4 Lignes rouges

| Autorisé | Zone grise (à éviter) | Interdit |
|---|---|---|
| Afficher des données précalculées | Fenêtre externe qui conseille en direct pendant un combat | Envoyer des touches ou des clics depuis un programme |
| Analyser un journal après le combat | Messages de chat automatiques comme canal de données | Lire la mémoire, injecter du code, modifier le client |
| Import/export par fichiers ou chaînes copiées | Superposition injectée dans le rendu ; pont pixels + lecture d'écran limité au transport de texte (voir 3.5) | Encodage de pixels et lecture d'écran combinés à des entrées simulées (architecture des bots) |
| Assistant LLM hors jeu | | Addon payant ou obfusqué |

[Probable] La lecture des fichiers journaux par un programme tiers est tolérée de fait (Warcraft Logs) ; aucune déclaration explicite de Blizzard.

## 3. Relier l'addon à un programme externe

### 3.1 Addon → programme

| Méthode | Latence | Verdict |
|---|---|---|
| SavedVariables (`WTF\Account\<COMPTE>\SavedVariables\…`) | Prochain `/reload` ou déconnexion | **Recommandé** (bug 69913 corrigé en 70009) |
| Journal de combat | Par paquets : secondes à minutes | Pour la mesure et l'analyse après combat ; `LoggingCombat` limité à 5 appels par 10 s |
| Journal de discussion | À la sortie ; n'enregistre pas les `print` d'addon | **À éviter** |
| Chaîne d'export copiable | Quelques secondes, action humaine | Appoint |
| Pixels et lecture d'écran pour transporter du texte (ponts wow-claude, wow-ai, wow-agent-bridge, voir 3.5) | Quasi temps réel | **Zone grise** : ni automatisation, ni injection, ni lecture mémoire, mais même technique que les bots à pixels ; à utiliser en connaissance de cause |
| Lecture mémoire, injection, entrées simulées | — | **Interdit** |

### 3.2 Programme → addon

- [Certain] Un programme écrit un `.lua` que le TOC exécute au chargement (TSM AppHelper, WeakAuras Companion) ; relu au prochain `/reload` ; `ReloadUI()` protégé = rafraîchissement manuel.
- Le fichier doit exister et figurer dans le TOC avant le lancement ; rester sous quelques centaines de Ko.
- Chaîne d'import collée dans une EditBox : sans `/reload`, décodage d'un format simple ; jamais `loadstring` sur une chaîne arbitraire.

### 3.3 Superpositions externes

- Overwolf : statut pour WoW non vérifié [Supposé].
- Recommandation : fenêtre de bureau séparée, jeu en fenêtré plein écran, réservée à l'analyse du dernier combat.

### 3.4 Projets existants

- `imperial64/forever-addon-dev` : son « Claude Code bridge » a été réduit à un fichier `ExternalData.lua` écrit par un script — même conclusion : fichier + `/reload`.
- Parseurs de journaux (tzcnt/forever-data pour Forever) : le travail sérieux se fait hors jeu.
- Bots à pixels : risque de bannissement documenté ; addons « ChatGPT » en jeu : techniquement impossibles sans canal interdit.


### 3.5 Ponts existants pour parler à Claude Code depuis le jeu (ajout du 27/09/2026)

- **wow-claude / wow-ai** (chelinho139 et forks : lixni, Zyra-V21, cheloc, coreyone, Nercari ; portage macOS realworldbuilder) : discuter avec ses sessions Claude Code locales depuis WoW: Forever, sans `/reload` par message ; plusieurs conversations en parallèle ; progression en direct ; réponses reprises dans le chat. L'addon transmet le contexte du personnage (niveau, zone, coordonnées, argent, talents, métiers, journal de quêtes) au prompt système de Claude. Fonctionnement : l'addon n'utilise que des API documentées ; le programme compagnon **lit une zone de l'écran** et **écrit des fichiers ordinaires** (« slots » installés à l'avance, relus par le client). Bouton « Allow & retry » quand Claude veut une commande hors de la liste autorisée.
- **wow-agent-bridge** (VIXAL-OS, portage de 0xInuarashi/wow-forever-codex) : les questions sortent du jeu sous forme de **bande de pixels**, les réponses reviennent par la **largeur des glyphes de police** ; ni DLL, ni lecture mémoire, ni entrée simulée.
- **agent-board** (btsouth) : superposition hors du jeu pour le direct, et repli natif par fichier `Data.lua` + SavedVariables au `/reload`.
- **wow-agent** (Oighty) : application de bureau toujours au premier plan ; état du jeu lu dans les SavedVariables (`/agent sync`), conversation sans aucun rechargement.

**Évaluation pour forever-core** [Supposé] :
- Ces ponts ne font aucune action de jeu : le risque vis-à-vis des règles est plus faible que celui d'un bot, mais la technique (lecture d'écran, bande de pixels) est la même ; zone grise, pas de validation explicite de Blizzard.
- Sécurité : une question tapée en jeu fait agir une session Claude Code capable d'exécuter des commandes sur le PC ; garder une liste d'autorisations stricte, jamais de mode sans permission.
- Fragilité : dépend du client (polices, fichiers relus, sons) ; peut casser à chaque build.
- Intérêt majeur : faire pointer la session du pont sur le dépôt `wow-forever` donne à Claude, en jeu, les outils et les données de forever-core (via le serveur MCP du plugin, T06).
- **Décision recommandée** : ne pas réécrire de pont ; construire ForeverAssist pour les suggestions sans conversation (données précalculées, voir V1/V2), et évaluer l'un de ces ponts pour la conversation une fois le plugin et le serveur MCP livrés.

## 4. Architecture

| Option | En jeu | Latence | Conformité |
|---|---|---|---|
| **(a) Addon + fichier de données régénéré** | Infobulles et panneaux précalculés | Un `/reload` | **Vert** |
| **(b) Boucle SavedVariables → forever → fichier → addon** | (a) + réponses au contexte | Deux `/reload` | Vert si fichiers et `/reload` manuels |
| (c) Addon + fenêtre de bureau | (a) + analyse du dernier combat à côté | Secondes à minutes | Vert après combat ; gris en direct |
| (d) Tout hors jeu (MCP), addon minimal | Presque rien | Immédiate hors jeu | Vert |
| Pixels, écran, entrées simulées | « Vrai direct » | Temps réel | **Rouge** |

**Décision** : (a), étendue en (b) lente, avec (c) en option pour l'analyse après combat.

### Plan par étapes

- **V1 — ForeverAssist, affichage seul** : `forever export-addon` génère `Data/Generated.lua` (`ForeverAssistData` : `schema`, `build`, `generated_at`, monstres `npcID` → PV mesurés, niveau, source ; sorts du Mage `spellID` → rang, coût, dégâts moyens, efficacité par point de mana). Affichage hors combat : lignes d'infobulle via `TooltipDataProcessor` et `npcID` extrait du GUID quand il n'est pas secret (protégé par `issecretvalue` et `pcall`), panneau `/fa`, avertissement si la build du client diffère.
- **V2 — contexte retour** : l'addon écrit hors combat niveau, talents (`C_Traits`), équipement (`C_Item`), zone, quêtes dans `ForeverAssistCharDB` ; `forever ingest-sv` lit après un `/reload`, recalcule, régénère `Generated.lua`.
- **V3 — compagnon de bureau** : watcher Python sur `Logs\WoWCombatLog-*.txt`, découpe des combats, résumé du dernier combat, exposé au MCP. Aucune consigne « lance tel sort maintenant ».

## 5. Intégration au dépôt

```
addon/
  ForeverAssist/ (ForeverAssist_Camelot.toc, Core.lua, UI.lua, Tooltip.lua,
                  Data/Generated.lua [généré, ignoré par git], Data/Generated.sample.lua)
  ForeverLogger/
  .luacheckrc
  spec/ (stubs/wow.lua, contract_spec.lua)
forever/ … export de l'addon + lecteur de SavedVariables
docs/ADDON.md
scripts/install_addon.py
```
- Installation Windows : jonction NTFS (`mklink /J`) plutôt que lien symbolique (pas de droits admin) ; le script détecte `_classic_beta_` (et le futur dossier de production), vérifie dossier = nom du TOC, refuse si WoW tourne.
- Export atomique (`.tmp` puis renommage) pour qu'un `/reload` ne lise jamais un fichier à moitié écrit.
- SavedVariables lus en Python sans exécuter de Lua ; tests sur des captures réelles.

### Tests et CI

1. luacheck (`std = "lua51"`, globals déclarés).
2. Linter Forever d'imperial64 (appels absents, abonnements refusés, lectures secrètes, alias de SavedVariables).
3. busted sous Lua 5.1 avec bouchons.
4. Tests de contrat : pytest génère `Generated.sample.lua` et valide son schéma ; busted le charge et vérifie la version du schéma et les champs.
5. CI : luacheck + lint + busted + pytest ; empaquetage BigWigs sur tag si besoin.
6. Numéro d'interface en source unique (`16001`) ; prévoir `_Camelot` et le futur suffixe (Blizzard parle de renommer avant le lancement).

### Plan de `docs/ADDON.md`

1. Objectif et non-objectifs (affichage et analyse ; jamais d'automatisation ni de conseil en combat).
2. Règles (politique Blizzard, lignes rouges).
3. Plateforme (Mainline 12.1.5, 16001, `_Camelot`, valeurs secrètes mesurées, build de référence).
4. API utiles (`C_Spell`, `C_Item`, `C_Traits`, `TooltipDataProcessor`, `Settings`, `issecretvalue`, `InCombatLockdown`, `LoggingCombat`).
5. Canaux (SavedVariables, `Generated.lua`, chaînes d'export et d'import, journal de combat) et latences.
6. Contrat de données (schéma versionné).
7. Procédure de test en jeu.
8. Checklist à chaque build (régénérer la référence, sonde, lint, `/dump` des API clés).

### Faire travailler Claude Code

- Installer le plugin `forever-addon-dev` et le MCP `hated-wow-mcp` ; règle : toute API vérifiée dans la référence Forever avant usage.
- Garde-fous CLAUDE.md : interdits `CastSpell*`, `UseAction`, `RunMacroText`, `SendChatMessage` automatique, `COMBAT_LOG_EVENT*`, arithmétique sur des valeurs de combat ; obligatoires `pcall` autour de `RegisterEvent` et des lectures douteuses, pas d'alias SavedVariables au niveau du fichier.
- Boucle de test : code, lint et tests verts ; export ; `/reload` puis `/fa selftest` (résultats dans les SavedVariables) ; second `/reload` ; `forever ingest-sv --selftest` rend le résultat lisible à Claude.
- Place dans la feuille de route : V1 après la stabilisation des données Mage et des PV mesurés ; V2 après le 21 octobre avec revérification au 4 novembre ; V3 quand le parseur de journaux est validé.

## Caveats

- Bêta mouvante (69893, 69913, 69977, 70009) : suffixe TOC, interface et liste des valeurs secrètes peuvent changer ; revalider au lancement.
- Mesures Forever souvent issues de dépôts récents peu étoilés, retenues parce qu'elles publient leurs captures et se recoupent.
- Latences du journal de combat non mesurées précisément : à mesurer soi-même.
- Statut d'Overwolf non vérifié ; aucune règle explicite sur une fenêtre externe qui lit le journal en direct.

## Sources principales

- https://www.wowhead.com/news/wow-forever-will-have-addon-changes-from-midnight-382921
- https://news.blizzard.com/en-us/article/24246290/combat-philosophy-and-addon-disarmament-in-midnight
- https://us.forums.blizzard.com/en/wow/t/prohibitions-on-third-party-software/2142972
- https://github.com/imperial64/forever-addon-dev
- https://github.com/imperial64/forever-addon-dev/pull/7
- https://github.com/imperial64/forever-addon-dev/pull/4
- https://github.com/imperial64/forever-addon-dev/pull/2
- https://github.com/RdyGaming/hated-wow-mcp
- https://github.com/eylgg/sink
- https://wowforeverbuilds.com/news/what-the-wow-forever-beta-breaks-for-addons-secret-health-values-dead-secure-sni
- https://github.com/Ludovicus-Maior/WoW-Pro-Guides/pull/3460
- https://github.com/Ludovicus-Maior/WoW-Pro-Guides/pull/3468
- https://github.com/Cidan/BetterBags/pull/1092
- https://github.com/tzcnt/forever-data
- https://github.com/nobewayo/ForeverSVFix
- https://github.com/ClassicWoWCommunity/forever-bugs/issues/34
- https://github.com/Questie/QuestieDB/issues/23
- https://warcraft.wiki.gg/wiki/TOC_format
- https://warcraft.wiki.gg/wiki/API_LoggingCombat
- https://support.tradeskillmaster.com/en_US/addon/how-do-i-fix-an-error-about-appdatalua-being-empty
- https://github.com/WeakAuras/WeakAuras-Companion/blob/main/i18n/en.json
- https://www.curseforge.com/wow/addons/forever-meter
- https://github.com/lixni/wow-claude
- https://github.com/cheloc/wow-ai
- https://github.com/Nercari/wow-ai
- https://github.com/realworldbuilder/wow-claude-mac
- https://github.com/VIXAL-OS/wow-agent-bridge
- https://github.com/btsouth/agent-board
- https://github.com/Oighty/wow-agent
