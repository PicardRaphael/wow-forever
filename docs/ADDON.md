# Addons de forever-core sur WoW: Forever

Source de rédaction : `docs/research/addon-forever.md` (rapport du 2026-09-27, sources en fin de fichier). Légende reprise du rapport : **[Certain]** source primaire ou mesure publiée sur le client Forever, **[Probable]** sources concordantes ou comportement Retail non remesuré, **[Supposé]** inférence ou source unique, **[À vérifier]** non établi. Code : `addon/` ; installation et contenu de la SavedVariable : `addon/README.md`.

## 1. Objectif et non-objectifs
- **Objectif** : afficher dans le jeu des données **précalculées par `forever`**, et rapporter hors du jeu le contexte du personnage ; analyser les journaux de combat **après** le combat, hors du jeu.
- **Non-objectifs** : aucune automatisation, aucun conseil de rotation en combat, aucun calcul sur des valeurs de combat dans l'addon, aucun canal temps réel.

## 2. Règles
### Politique de Blizzard
- [Certain] Addons gratuits ; code ni caché ni obfusqué ; pas de publicité ni de dons ; pas d'usage excessif du chat ; Blizzard peut désactiver des fonctionnalités.
- [Certain] Interdiction des logiciels qui modifient le client ou contrôlent le jeu.

### Lignes rouges
- **Pas d'automatisation** : aucune fonction d'action (`CastSpell*`, `UseAction`, `RunMacro`, `RunMacroText`), aucun `SendChatMessage` automatique, aucune macro générée.
- **Pas de lecture d'écran ni de pixels**, pas de lecture de la mémoire, pas d'injection.
- **Pas d'entrées simulées** (touches, clics).
- Zone grise, à éviter : fenêtre externe qui conseille en direct pendant un combat ; messages de chat comme canal de données ; ponts pixels + lecture d'écran (voir la section 9).

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
| à éviter | Journal de discussion (écrit à la sortie, ignore les `print` d'addon) ; pixels et lecture d'écran | — | Non |

## 6. Contrat de données
- **ForeverLoggerDB** (retour, schéma 1) : par GUID, instantanés `{reason, time, localtime, level, talents, spell_bonus, spell_crit}` à la connexion, au gain de niveau et au changement de talents ; gains d'expérience `{time, localtime, level, text}`. Détail : `addon/README.md`. Lecture : `forever/pipeline/addon_sv.py` ; jointure avec un journal par GUID et heure locale (`forever logs measure <journal> --addon-sv <fichier>`).
- **Fichier généré pour ForeverAssist** (aller, V1) : variable `ForeverAssistData` avec `schema`, `build`, `generated_at`, puis les données ; schéma versionné et validé par pytest, `Generated.sample.lua` versionné, `Generated.lua` ignoré par git.

## 7. Installation et procédure de test en jeu
1. `uv run python scripts/install_addon.py --dry-run`, puis sans `--dry-run` (terminal administrateur si l'écriture dans `Program Files (x86)` est refusée).
2. En jeu : `/reload` ; le message « journal de combat activé » s'affiche à l'entrée dans le monde si le journal était arrêté.
3. Jouer, puis `/reload` (ou se déconnecter) pour écrire `ForeverLoggerDB`.
4. Hors du jeu : `uv run forever logs scan`, puis `uv run forever logs measure <journal> --addon-sv <SavedVariables>/ForeverLogger.lua`.

### Protocole de collecte (mesures pour le registre)
- **B1** (recharge globale) : sur un mannequin ou des monstres faciles, 50 sorts instantanés enchaînés sans pause → intervalles minimaux ; `tolerance.n_min` de B1 dans le registre.
- **A3** (raté des sorts selon l'écart de niveau) : leveling ordinaire au Frostbolt, ForeverLogger installé (niveau du lanceur) ; il faut plusieurs centaines de lancers par écart de niveau pour distinguer des taux voisins ; noter les talents de toucher (instantané de l'addon).
- **H1** (niveau d'un boss) : un boss de donjon → niveau lu dans le bloc avancé du journal.
- **Monstres** : tout journal de leveling enrichit la table (`uv run forever monsters build --logs <dossier> --questie <addon Questie>`) ; `uv run forever measures refresh` relance toutes les mesures et n'écrit qu'après accord.
- **A18** (Ignite) : leveling ou mannequin au Fireball avec Ignite pris, ForeverLogger installé (rangs de talents) ; relever des paires de critiques de feu à moins de 4 s l'une de l'autre et des critiques isolés ; pour chacun, montants et instants des tics de 412538 jusqu'à la fin de l'aura ; `forever measures refresh` relève les épisodes et les compare à la règle des données et à la variante (écart affiché, jamais écrit au registre).
- **B7** : régénération de mana en incantation avec Arcane Meditation et Mage Armor à la fois (cumul Classic supposé) ; bonus d'armure de Frost et Ice Armor non modélisé.
- **B11** : coût d'Arcane Blast à chaque cumul (1 + 1,75 n supposé additif) et effet de Clearcasting sur le cumul.
- **I7** : couleur des quêtes au niveau du personnage (vertes les plus basses), à comparer à `leveling.quest_band`.
- **G4, pénalité des sorts de bas niveau (E2, T04e)** : une dizaine de Frostbolt **rang 1** sur un monstre gris, sans talent de dégâts, personnage de niveau 8 ou plus : base 20-22 ; + 0,407 × puissance des sorts sans pénalité, + 0,163 × avec. À 14 de puissance des sorts : 25,6-27,8 contre 22,2-24,4 (sans recouvrement). La puissance des sorts se lit dans le bloc avancé de `SPELL_CAST_SUCCESS`.
- **Ice Lance (E4, T04e)** : sur cible **non gelée**, deux séries à au moins 30 de puissance des sorts d'écart : + 4,3 par coup attendu avec 0,1429, rien avec 0. Un seul coup au-dessus du maximum de base (× talents) réfute 0.
- **Pyroblast r1 (E3, T04e)** : tic = 11 + 0,15 × puissance des sorts (× talents) ; à 20 de puissance des sorts, 14 au lieu de 11 ; un tic toutes les 3 s (4 tics).
- **Cumul des bonus (E6, T04e)**, journaux ordinaires : Arcane Missiles sous Arcane Power avec 4 cumuls d'Arcane Blast, contre Arcane Power seul : rapport 1,40 (multiplicatif) contre 1,31 (additif). Talent Arcane Power requis.
- **Bornes de dégâts (E7, T04e)** : arrondi au demi supérieur ou troncature ? Choisir un rang dont les bornes diffèrent entre les deux règles (points × (1 ∓ variance / 2) de `spell_scaling.json` à partie décimale ≥ 0,5 ; au niveau 60 : Ice Lance r6, maximum 161 arrondi ou 160 tronqué ; Arcane Explosion r6, minimum 239 ou 238). Au moins 50 coups non critiques à puissance des sorts connue S (bloc avancé de `SPELL_CAST_SUCCESS`), talents de dégâts notés (instantané de l'addon) : relever le minimum et le maximum observés ; bornes attendues (min + coefficient × S) × talents et (max + coefficient × S) × talents sous chaque règle ; un coup hors des bornes d'une règle la réfute.
- **Improved Cone of Cold (T04e)** : Cone of Cold avec le talent à **1/3** (× 1,12 selon la courbe du client, × 1,15 selon la décision du 2026-09-28), coups non critiques à puissance des sorts connue, comparés aux mêmes coups sans le talent.
- **Blizzard (T04e)** : tics de Blizzard (sans variance) à deux niveaux de puissance des sorts : écart par tic de 0,042 × Δ (sort déclenché) ou 0,03 × Δ (effet factice du parent).

## 8. Checklist à chaque build
Régénérer la référence d'API Forever ; relancer une sonde (`/dump` des API clés : `C_Traits`, `issecretvalue`, `GetSpellBonusDamage`) ; `uv run python scripts/check_addon.py` ; vérifier le numéro d'interface et le suffixe du `.toc` ; vérifier l'en-tête du journal (`COMBAT_LOG_VERSION`, bloc avancé à 19 champs).

## 9. Feuille de route ForeverAssist
Addon d'**affichage** (voir `docs/ROADMAP.md`, lignes FA1, P06, V2 et V3).
- **V1 — données précalculées** (après T05) : `forever export-addon` génère `Data/Generated.lua` ; l'addon propose **le talent suivant à chaque gain de niveau** (ordre de talents de l'optimiseur T05) et **compare l'équipement dans l'infobulle des objets** (valeur des statistiques au niveau du personnage, calculée par le moteur), affiche la table des monstres de la zone ; hors combat, sous `pcall` et `issecretvalue`, panneau `/fa`, avertissement si la build diffère.
- **V2 — contexte retour** (proposée avec T07) : l'addon écrit hors combat niveau, talents, équipement, zone, quêtes dans `ForeverAssistCharDB` ; `forever ingest-sv` relit après un `/reload`, recalcule et régénère `Generated.lua`.
- **V3 — compagnon de bureau** (proposée après T08) : analyse de `WoWCombatLog-*.txt` après le combat (`forever logs measure`), résumé du dernier combat exposé au MCP. Aucune consigne « lance tel sort maintenant ».
- **Pont de conversation** (P06, après T06) : évaluer un pont existant (wow-claude / wow-ai, rapport section 3.5) dont la session Claude Code est pointée sur ce dépôt. [Supposé] Aucune action de jeu, mais même technique que les bots à pixels (lecture d'écran) : zone grise. Sécurité : liste d'autorisations stricte, jamais de mode sans permission. Fragile à chaque build. Décision écrite dans `docs/DECISIONS.md` avant tout usage.
