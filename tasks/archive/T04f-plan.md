# T04f — Bonus d'XP cumulés : plan

> Plan rédigé le 2026-10-13 (`/tranche T04f`), sans code. Exécution : `/tranche T04f` dans une nouvelle session, sur la
> branche `t04f` partie de `origin/main`, un cycle rouge → vert par bloc. Aucune sonde en jeu exigée (décision 247) :
> les relevés de ForeverLogger vérifieront le modèle quand l'utilisateur jouera. Garde-fou du calendrier (décision
> 251) : T04f, DJ1 et RX1 avant LN1, qui commence au plus tard le 24 octobre.

## Demande de l'utilisateur (2026-10-13)
Utile à toutes les classes, sans sonde obligatoire :
1. **Recenser** tous les bonus d'XP de Forever et leur cumul : XP de repos (accumulation, plafond, durée du bonus,
   question LVL3 sur la durée du Well-Rested), sac de couchage (chaîne de Naowh Discovery, effet lu dans le client),
   bonus Legacy, bonus de groupe ou de donjon, consommables, et tout autre effet du client qui modifie le gain d'XP
   (auras de pourcentage d'XP dans les tables des sorts).
2. **Sources** : d'abord le client (effets des sorts et des auras, avec leur valeur), puis les notes officielles, puis
   les addons installés lus en local (Naowh Forever Discovery et QoL, Legacy Forever, ForeverLogger pour les relevés) ;
   chaque règle avec sa source et sa certitude ; les mesures de ForeverLogger 0.4.0 servent à vérifier plus tard.
3. **Intégrer** ces bonus au simulateur de leveling et aux objectifs de T04d (XP par heure avec et sans repos, avec le
   sac de couchage), au bouton Leveling (« prends le sac de couchage : la chaîne commence ici »), et les préparer pour
   RX1 (étapes à placer dans une route, comme la chaîne du sac de couchage).

Préalable fait avant ce plan : **décision 261** (CM1 dès la sortie, avant PV2 et AN1 ; dépendance à AN1 réduite à
l'analyse étendue), écrite dans `docs/DECISIONS.md` et `docs/ROADMAP.md` (commit de ce plan).

## Réponses de l'utilisateur (2026-10-13)
1. **Cumul** : les pourcentages d'XP s'additionnent, puis le repos s'applique sur l'XP déjà majorée ; règle `suppose`
   (émulateur TrinityCore : total des modificateurs d'aura), variante multiplicative gardée dans les données,
   question ouverte **LVL12**.
2. **Réseau** : la table `PlayerCondition` est ajoutée aux tables de `forever update` et `forever fetch` (wago.tools,
   voie existante) et décodée, pour lire la condition 142418 du bonus de nourriture.
3. **Rangs Legacy** : lus hors combat par ForeverLogger (`C_Traits` sous `pcall`) et écrits au profil ; à défaut, champ
   du profil réglé à la main ; sinon rang 0, signalé dans la sortie.
4. **Contexte du pont** : ForeverBridge envoie aussi, à chaque message, le repos, l'état « en zone de repos » et les
   auras d'XP actives (cumuls, temps restant), pour que le bouton Leveling parle de l'état du moment.

## Constats (relevés le 2026-10-13, lecture seule du client 1.60.1.70338, des addons et du dépôt)

### Client : bonus d'XP lus dans les tables (`~/.cache/forever/wago/1.60.1.70338/enUS`)
Sens des codes d'aura (effet 6) déduit des descriptions des sorts, `probable` : **200** % d'XP des monstres tués ;
**291** % d'XP des quêtes ; **386** vitesse d'accumulation du repos ; **656** plafond du repos ; **447** % d'XP contre un
type de créature (valeur diverse = type) ; 348 % d'or des quêtes (hors sujet) ; 637 inconnu (valeur 0).

| Bonus | Client | Effet lu | Durée, cumul | Accès |
| --- | --- | --- | --- | --- |
| Cozy Sleeping Bag | objet 211527 → `ItemEffect` 181192 → sort 429961 « Unroll Bag » | sac posé 20 min ; repos d'au moins une minute dedans → aura 429960 « Well-Rested Tracking Aura » (déclenchement toutes les 60 s) → **Well-Rested 429959** : auras 200 et 291, **1 % par cumul** | Well-Rested **2 h** (`SpellDuration` 7 200 000 ms), **3 cumuls** (`SpellAuraOptions.CumulativeAura`) ; recharge de l'objet 1 h | chaîne de quêtes (plus bas) |
| Well Fed XP Boost | aura 1243969, permanente | aura 200 : **+5 % d'XP des monstres tués** (pas les quêtes) | texte conditionné par la condition de joueur 142418 ; les buffs Well Fed de « Nutritious Food / Drink » (15 min) affichent la ligne quand 1243969 est active | nourritures et boissons nutritives (Murloc Fin Soup, Spiced Wolf Meat, Smoothies, Teas…, paliers de niveau requis 1 à 45) |
| Well Rested (perk Legacy) | sort 1225478, trait 141618, nœud 110301 de l'arbre Legacy 1188 « Adventure » | auras 386 et 656 : repos accumulé plus vite et plafond relevé, **4 % par rang** (courbes de `TraitDefinitionEffectPoints` : 4, 8, 12, 16, 20) | 5 rangs | points Legacy |
| Gourmand (perk Legacy) | 1225499, arbre 1189 | durée des buffs de nourriture allongée (33, 67, 100 %) | 3 rangs | points Legacy ; agit sur la durée de Well Fed XP Boost |
| Field Guide (perk Legacy) | 1225479 | recharge des éléments de camp réduite | 3 rangs | agit sur la tente |
| Tente de camp | 1307230 « Camp Tent » (recharge partagée 1308027, 1 h) ; « Boosted Rest » 1229451 | **repos remonté à 5 % d'un niveau**, sans effet si le repos dépasse déjà ce seuil | une fois par heure | camp (feu Basic, Journeyman, Expert : 3, 5, 10 éléments, 15 min) |
| Autres éléments de camp | Camp Benefits 1229741 (1 h après 60 s assis) : Mana Well, Sharpening Wheel, Lute, First Aid Kit… | **aucun % d'XP** | — | — |
| Archmagister's (1292997, 1293736) | objet 273049 (sans nom) | aura 447 : +10 % contre les morts-vivants | 5 min | à classer (source inconnue) |
| Discoverer's Delight 436412, Winds of Wisdom 335924 (« CN Only »), Adventure Awaits 362859 (Season of Mastery), WoW Variety Show 430496 | — | +50 à +100 % | — | **aucune source joueur** dans le client : listés, marqués « non accessible » (`suppose`), jamais appliqués |

- **Correctifs du serveur** : aucun enregistrement de `DBCache.bin` (build 70338, 29 642 entrées) ne touche ces sorts,
  ni l'objet 211527. Les valeurs ci-dessus sont celles du client, sans correction.
- **Repos (table `Exhaustion`)** : déjà décodée (`character_scaling.json` `rested`) et modélisée en T04d
  (`xp.rested` : facteur et période lus dans le client ; gain, rapport dehors et plafond de Classic, `suppose`, LVL10).
- **LVL3 tranchée par le client** : Well-Rested dure 2 h (foreverchanges.pro avait raison, les guides à 1 h non) ;
  la valeur est de 1 % par cumul, 3 au plus.
- **Groupe et donjon** : déjà modélisés en T04d (I10, I11) ; T04f ne fait que les cumuler.

### Addons installés (lecture locale)
- **Naowh Forever 1.1.11**, `NaowhForever_Discovery/Data/SleepingBag.lua` (pas `SleepingBagData.lua`) : niveau 14,
  objet 211527, chaîne de 7 étapes par objets à cliquer (Westfall, The Barrens, Stonetalon ×2, Loch Modan, Arathi ×2,
  quêtes 79007 ou 79008, 79192, 79980, 79974, 79975, 79976) ; ordre des deux premières inversé pour la Horde ; étape
  facultative « Rekindle » (Stonetalon, quête 80001). Positions en uiMapID et pourcentage. **FojjiCore_DungeonJournal
  3.3.5** (`Data/Guides.lua`, clé `sleepingbag`) donne la même chaîne avec les noms de quêtes (recoupement).
- `NaowhForever_QoL/XP/*.lua` et `NaowhForever_AuraBuffs/Data/Campfire.lua` : affichage seulement, aucune valeur de
  bonus (la liste des sorts de camp concorde avec le client).
- **Legacy Forever 0.6.18** : défis seulement, aucun perk ni bonus d'XP ; les perks sont lus dans le client (tables
  `Trait*`), noms d'arbre recoupés avec TalentsForeverBook 0.38.1.
- **Campfire Tooltips, CampingInfo** : non installés.
- **ForeverLogger** : addon 0.4.0 installé, SavedVariables encore au schéma 1 (pas de `xp_states`) ; 2 760 gains
  d'XP, aucun avec bonus de repos ni Well-Rested (LVL10 inchangée).

### Code actuel (T04d)
- `forever/engine/xp.py` : `mob_kill_xp(gd, player_level, mob_level, *, elite, dungeon, party, rested_pool)` et
  `quest_xp` rendent `XpResult(xp, rested_used, terms)` ; le repos s'applique en dernier, sans état (le réservoir n'est
  pas décrémenté) ; `rested_gain(gd, level, hours, *, inn, pool)`. Règles lues par `forever/gamedata.py`
  (`XP_KEYS`, `XpRules` de `engine/model.py`). Aucun bonus en pourcentage.
- `forever/sim/objectives.py` : `objectives(..., rested=…)` accepte le repos mais **ne l'applique pas** (hypothèse
  « repos non appliqué au classement ») ; `forever sim objectives --rested` ; MCP
  `forever_sim_leveling(kind="objectives", rested=…)`.
- `forever/engine/monsters.py` `mob_xp` (niveau égal, sans bonus) alimente `leveling_analytic.py` et
  `leveling_mc.py` ; `tests/parity/test_sim_leveling_parity.py` compare `xp_h` au seed à 1e-12 en `rules="seed"` :
  **les bonus restent nuls par défaut**.
- Pont : `forever/bridge/buttons.py` (bouton Leveling), `forever/bridge/plans.py` (`_objectives_call` sans
  `rested`) ; contexte de ForeverBridge 0.1.0 (`addon/ForeverBridge/Message.lua` `M.Context()`) sans repos ni auras.
- `forever lookup` : branches `if kind ==` dans `forever/cli.py` et `forever/mcp_server.py`, sans registre central.
- `tests/golden/` n'existe pas ; les tests de parité jouent son rôle.
- Registre : D5 (camps et Legacy, `absent`), D7 (repos et Well Fed, `teste`, `suppose`), E3 (nourriture, `absent`),
  G5 (Legacy, `absent`).

## Décisions à écrire (étape 0, `docs/DECISIONS.md`)
- **262** : choix de ce plan (réponses 1 à 4) ; bonus sans source joueur listés mais jamais appliqués ; chaîne du sac
  lue dans les addons au moment du calcul, gardée dans le cache, jamais recopiée dans le dépôt (décision 133) ;
  identifiants des sorts et des objets jamais écrits en dur dans les addons (le pont les fournit depuis les données).

## Choix de conception
1. **Données du client** : nouveau fichier décodé `forever/data/1.60.1.70338/xp_bonuses.json`, installé en révision
   suivante de 1.60.1.70338 (`forever install --dry-run`, puis accord de l'utilisateur, décision 98). Contenu :
    - `auras` : chaque sort du client qui porte une aura 200, 291, 386, 656 ou 447, avec le nom, l'effet (code, sens,
      valeur de base, valeur diverse), la durée (`SpellDuration`), le cumul (`SpellAuraOptions`), le déclencheur
      (`EffectTriggerSpell` remonté jusqu'à l'objet par `ItemEffect` et `ItemXItemEffect`, ou jusqu'au trait Legacy
      par `TraitDefinition`), la valeur par rang (`TraitDefinitionEffectPoints` et `CurvePoint`) et l'accès
      (`item`, `legacy`, `food`, `camp`, `none`) ;
    - `food` : sorts « Nutritious Food / Drink », buffs Well Fed qui citent 1243969, objets et niveau requis ;
    - `camp` : tente (repos remonté, seuil, recharge), feux et nombre d'éléments, Camp Benefits (sans XP) ;
    - `conditions` : la condition 142418 décodée de `PlayerCondition` (champs utiles seulement, sens déclaré ;
      champ inconnu → « inconnu », jamais deviné) ;
    - une certitude par champ : `certain` pour une valeur lue, `probable` pour le sens d'un code d'aura déduit des
      descriptions.
   Les tables déjà téléchargées suffisent, sauf `PlayerCondition` (ajoutée à `decode_rules.json`, nouvelle clé
   `xp_bonus_tables`, facultative dans `forever update` comme `quest_tables`). Les correctifs du serveur s'y
   appliquent comme aux autres tables (`hotfix_related_tables`).
2. **Règles écrites** (`mechanics.json`, avec source, certitude et registre ; aucun chiffre dans le code) :
    - `xp.bonus_stacking` : `{"mode": "additive", "variants": ["additive", "multiplicative"], "rested_after": true}`,
      `suppose`, source TrinityCore (`Unit::GetTotalAuraModifier`, KillRewarder, `Player::GiveXP`), registre D10,
      question LVL12 ;
    - `xp.sleeping_bag` : temps assis pour un cumul (lu : période de 429960), cumuls à la pose (déduit : un par
      minute de repos dans le sac, au plus le cumul lu), `probable` ;
    - `xp.food_bonus` : buff Well Fed nutritif requis, condition 142418 lue, `probable` ou `suppose` selon la lecture ;
    - `xp.legacy_rested` : perk Well Rested appliqué au gain (`rested_gain` × (1 + vitesse)) et au plafond
      (× (1 + plafond)) ; `suppose` (sens du code d'aura) jusqu'à la mesure ;
    - `xp.camp_tent` : repos remonté au seuil lu, sans effet au-dessus, `probable`.
3. **Moteur, fonctions pures** (`forever/engine/xp.py`) :
    - `XpBonusState` (auras actives avec cumuls et temps restant, nourriture, rangs Legacy, tente disponible) ;
    - `xp_multiplier(gd, state, *, source)` → `(facteur, terms)` : somme (ou produit, variante) des pourcentages
      applicables à `kill` ou `quest`, chaque bonus un `Term` avec source et certitude ; un bonus « non accessible »
      n'entre jamais ;
    - `mob_kill_xp(..., bonuses=None)` et `quest_xp(..., bonuses=None)` : facteur appliqué après groupe et donjon,
      repos en dernier sur l'XP majorée (choix 1 de l'utilisateur) ; `bonuses=None` rend exactement la valeur de T04d ;
    - `rested_gain(..., legacy_rank=0)`, `rested_cap(gd, level, legacy_rank=0)`, `tent_rested(gd, level, pool)` ;
    - `session_xp(gd, *, xp_per_hour_base, hours, state, rested_pool, kill_share)` : déroulé d'une séance par pas de
      temps (durée restante de Well-Rested, réservoir de repos consommé, nourriture renouvelée ou non), qui rend l'XP
      par heure moyenne et la part de chaque bonus ; c'est elle qui chiffre « avec repos », « sans repos » et « avec le
      sac ».
4. **Simulateur et objectifs** :
    - `forever sim objectives` : options `--rested XP` (désormais appliqué), `--sleeping-bag [N]`, `--food`,
      `--legacy-rested-rank R`, `--hours H` ; chaque objectif rend `xp_h` (sans bonus), `xp_h_rested`,
      `xp_h_sleeping_bag`, `xp_h_all` (bonus actifs du personnage) et la liste des bonus pris en compte avec leur
      certitude et leur durée restante ; l'hypothèse « repos non appliqué » disparaît de la provenance ;
    - `forever sim leveling` et `forever_sim_leveling` : paramètre `bonus` (liste) et `rested`, défaut vide :
      sortie et parité inchangées sans bonus ; avec bonus, `xp_h` multiplié par le facteur de `session_xp` et la
      sortie liste les bonus ;
    - « quel bonus prendre maintenant » : écart d'XP par heure de chaque bonus absent mais accessible (sac, nourriture
      de son niveau, tente), calculé par l'outil et rangé, jamais par le modèle de langage.
5. **Chaîne du sac de couchage** (`forever/xp_bonuses.py`, lecteurs dans `forever/pipeline/naowh.py` et
   `forever/pipeline/fojji.py`) : étapes lues dans Naowh Discovery, recoupées avec FojjiCore (noms des quêtes) et la
   liste des quêtes de T04d (`<cache>/quests/`) ; gardées dans le cache, jamais dans le dépôt ; écart entre sources
   signalé ; niveau minimal de Naowh (`suppose`). Pour un personnage : faction, sac déjà possédé (contexte du pont),
   étape suivante (quêtes de la chaîne déjà faites, d'après Questie ou le relevé) et sa position.
6. **Étapes de route pour RX1** : type neutre `RouteStep(kind, quest_id, item_id, map, x, y, text, level, source,
   certainty)` (`kind` : `goto`, `accept`, `turnin`, `click`, `use_item`, `note`) défini dans `forever/route.py`.
   T04f fournit deux producteurs : la chaîne du sac (`sleeping_bag_steps(...)`) et les rappels de bonus
   (`bonus_reminders(...)` : reposer le sac à chaque heure de recharge, manger une nourriture nutritive de son niveau,
   monter une tente avant une longue séance). RX1 les place dans la route et les encode au format RestedXP.
7. **Pont** :
    - **ForeverBridge 0.2.0** : contexte enrichi (repos `GetXPExhaustion`, `IsResting`, auras actives du joueur :
      identifiant, cumuls, temps restant, sous `pcall`, valeur secrète traitée comme absente ; possession du sac par
      un identifiant fourni par le pont depuis `xp_bonuses.json`, jamais écrit en dur) ; place dans la bande de pixels
      contrôlée (nombre d'auras borné, filtrées côté Python) ;
    - **ForeverLogger 0.5.0** : auras d'XP actives (même lecture) dans chaque `xp_states` et chaque gain d'XP ; rangs
      Legacy hors combat (`C_Traits` sous `pcall`, configuration du compte ; échec → absent) ; lecture Python
      (`addon_sv.py`), rangs écrits au profil au clic (voie de PV1 et de la décision 254) ;
    - **Bouton Leveling** (`bridge/plans.py`, `buttons.py`) : appelle les objectifs avec l'état du moment (repos, auras,
      rangs Legacy), rend les bonus actifs et leur temps restant, puis le meilleur bonus à prendre ; sans sac et au
      niveau de la chaîne : « prends le sac de couchage : la chaîne commence ici » avec l'étape suivante (lieu, carte,
      position), phrase construite par l'outil.
8. **Consultation** : `forever lookup xp_bonuses [--name] [--access]` et `forever_lookup(kind="xp_bonuses")` :
   chaque bonus avec sa valeur, sa durée, son cumul, son accès, sa source et sa certitude ; la chaîne du sac quand
   l'addon est installé (sinon la source manquante est nommée, décision 243).
9. **Vérification passive** : `forever xp check` compare le facteur prédit aux gains relevés avec auras (schéma 2
   et suivants de ForeverLogger) : par règle (Well-Rested, nourriture, cumul, repos Legacy) « vérifié » ou « à
   vérifier », jamais bloquant (décision 247).

## Étapes et blocs (commits `T04f: tests (bloc X)` puis `T04f: bloc X vert`)

### Étape 0 — Préalables
Branche `t04f` depuis `origin/main` (la veille pousse sur main) ; décision 262 ; charger le skill `addon-forever`
avant le bloc D.

### Bloc A — Client : `xp_bonuses.json`
`PlayerCondition` ajoutée aux règles (`xp_bonus_tables`) et à `forever/pipeline/tables.py` ; décodeur
`forever/pipeline/xp_bonuses.py` (choix 1) branché dans `decode.py` (`DECODED_FILES`, bloc facultatif comme
`quest_tables`, note de source) ; `sources.json`, `origins.json` ; téléchargement réel de `PlayerCondition` hors
tests, candidate décodée, `forever install --dry-run`, **arrêt pour l'accord d'installation** (révision suivante de
1.60.1.70338) ; comptes des tests de données.

### Bloc B — Règles et moteur
`mechanics.json` (choix 2), `gamedata.py` (`XP_KEYS` étendues, `XpBonusRules`), `engine/xp.py` (choix 3) ; registre
D5, D7, D9, D10, E3 ; questions LVL3 (résolue), LVL12, LVL13.

### Bloc C — Simulateur, objectifs, consultation
`sim/objectives.py`, `leveling.py`, `sim/leveling_analytic.py`, `sim/leveling_mc.py` (paramètre de bonus), CLI et MCP
(choix 4 et 8), « quel bonus prendre ».

### Bloc D — Addons et contexte
ForeverBridge 0.2.0 et ForeverLogger 0.5.0 (choix 7), sous lupa ; `addon_sv.py`, `bridge/context.py`, profil (rangs
Legacy) ; `scripts/check_addon.py` et `test_addon_rules.py` (versions) ; `docs/ADDON.md` (relevé facultatif : une
séance avec et sans sac, avec et sans nourriture nutritive, LVL12).

### Bloc E — Chaîne du sac, étapes de route, bouton Leveling
Lecteurs Naowh Discovery et FojjiCore, `forever/xp_bonuses.py`, `forever/route.py` (choix 5 et 6), plan du bouton
Leveling ; skill `forever-leveling` et routeur sans chiffre, évaluations du plugin (bouton Leveling d'un Chasseur de
niveau 15 sans sac, d'un Mage reposé avec Well-Rested).

### Bloc F — Vérification passive
`forever xp check` étendu (choix 9) ; documentation (`docs/USAGE.md`, `docs/ARCHITECTURE.md`, `docs/DATA_SOURCES.md` :
Naowh Discovery `SleepingBag.lua`, FojjiCore, `PlayerCondition`).

## Fichiers
- **Nouveaux** : `forever/pipeline/xp_bonuses.py`, `forever/xp_bonuses.py`, `forever/route.py`,
  `forever/pipeline/fojji.py`, `forever/data/1.60.1.70338/xp_bonuses.json` (par `forever install`), fixtures, tests.
- **Modifiés** : `forever/pipeline/{decode,tables,naowh,addon_sv,hotfixes}.py`, `forever/update.py`,
  `forever/gamedata.py`, `forever/engine/{xp,model}.py`, `forever/sim/{objectives,leveling_analytic,leveling_mc}.py`,
  `forever/leveling.py`, `forever/xp_check.py`, `forever/cli.py`, `forever/mcp_server.py`, `forever/profile*.py`,
  `forever/bridge/{plans,buttons,context}.py`, `addon/ForeverBridge/*` (0.2.0), `addon/ForeverLogger/*` (0.5.0),
  `forever/data/1.60.1.70338/{decode_rules,mechanics,sources,origins}.json`, `plugin/skills/forever-leveling/`,
  `plugin/skills/forever-router/`, `plugin/evals/`, `docs/{MECHANICS_REGISTRY.yaml,OPEN_QUESTIONS.md,
  RESOLVED_QUESTIONS.md,DATA_SOURCES.md,DECISIONS.md,ROADMAP.md,USAGE.md,ARCHITECTURE.md,ADDON.md}`.

## Interfaces (signatures indicatives, forme définitive au bloc)
```
# forever/engine/xp.py  (registre : D5, D7, D9, D10, E3)
# XpBonusState(auras: tuple[ActiveAura(spell_id, stacks, remaining_s)], food: bool, legacy: Mapping[str, int],
#              tent_ready: bool)
# xp_multiplier(gd, state, *, source: Literal["kill", "quest"], mode=None) -> tuple[float, tuple[Term, ...]]
# mob_kill_xp(..., bonuses: XpBonusState | None = None) ; quest_xp(..., bonuses=None)
# rested_gain(..., legacy_rank=0) ; rested_cap(gd, level, legacy_rank=0) ; tent_rested(gd, level, pool) -> float
# session_xp(gd, *, base_xp_h, kill_share, hours, state, rested_pool, level) -> SessionXp(xp_h, by_bonus, terms)

# forever/xp_bonuses.py
# catalog(gd) -> list[XpBonus(id, name, effects, duration_s, stacks, access, source, certainty)]
# sleeping_bag_chain(deps, *, faction, done_quests, addons_dir) -> Chain(steps: [RouteStep], next_step, sources,
#                                                                       discrepancies)
# best_bonus(gd, state, *, level, faction, base_xp_h) -> list[BonusAdvice(bonus, xp_h_gain, how, certainty)]

# forever/route.py
# RouteStep(kind, quest_id, item_id, map, x, y, text, level, source, certainty)
# sleeping_bag_steps(chain) -> list[RouteStep] ; bonus_reminders(gd, state, *, hours) -> list[RouteStep]
```
CLI : `forever lookup xp_bonuses [--access item|legacy|food|camp|none]`,
`forever sim objectives ... [--rested XP] [--sleeping-bag [N]] [--food] [--legacy-rested-rank R] [--hours H]`,
`forever sim leveling ... [--bonus sleeping_bag,food] [--rested XP]`. MCP : `forever_lookup(kind="xp_bonuses")`,
`forever_sim_leveling(..., bonus=[...], hours=...)` ; aucun nouvel outil.

## Tests attendus (valeurs lues dans les fixtures ou les données, aucun chiffre de jeu écrit dans un test)
- **Fixtures** : `tests/fixtures/wago/xp_bonuses/` (lignes extraites du client 1.60.1.70338 par
  `scripts/extract_xp_bonus_fixtures.py` : `SpellName`, `Spell`, `SpellEffect`, `SpellMisc`, `SpellDuration`,
  `SpellAuraOptions`, `ItemSparse`, `ItemEffect`, `ItemXItemEffect`, `TraitDefinition`, `TraitNodeEntry`,
  `TraitDefinitionEffectPoints`, `CurvePoint`, `PlayerCondition` pour les sorts du tableau des constats) ;
  `tests/fixtures/addons/xp_bonuses/` (extraits structurels de `SleepingBag.lua` et de la clé `sleepingbag` de
  FojjiCore, sans texte recopié) ; `tests/fixtures/addon/ForeverLoggerDB_auras.lua` (schéma 3 : auras, rangs
  Legacy) ; contexte du pont avec auras.
- `test_xp_bonuses_decode.py` : Well-Rested 429959 = durée de son `DurationIndex` (7 200 000 ms dans la fixture),
  cumul 3, auras 200 et 291 à la valeur de base de la fixture (1), accès `item` remonté jusqu'à 211527 ; 1243969 :
  aura 200 seule non nulle (5), accès `food`, condition 142418 décodée ; 1225478 : valeurs par rang tirées des
  courbes (4 à 20), accès `legacy` ; 436412 → accès `none` ; tente : seuil lu (5 % d'un niveau) ; aucune aura d'XP de
  la fixture oubliée (ensemble exact).
- `test_engine_xp_bonuses.py` : facteur des monstres avec Well-Rested 3 cumuls et nourriture = 1 + somme des valeurs
  lues (addition), variante multiplicative = produit ; quêtes : nourriture sans effet ; `bonuses=None` → valeur de
  T04d à l'identique ; repos appliqué après le facteur (surplus pris au réservoir calculé sur l'XP majorée) ; bonus
  `none` jamais appliqué ; chaque `Term` porte source et certitude ; perk Legacy : gain et plafond × (1 + valeur du
  rang) ; tente : réservoir remonté au seuil, inchangé au-dessus.
- `test_session_xp.py` : séance plus longue que Well-Rested → bonus seulement sur sa durée restante ; repos épuisé →
  facteur retombé ; XP par heure avec bonus ≥ sans bonus ; somme des parts par bonus = gain total.
- `test_sim_objectives_bonuses.py` : sur les fixtures de T04d, chaque objectif rend `xp_h`, `xp_h_rested`,
  `xp_h_sleeping_bag`, `xp_h_all` ; `xp_h_sleeping_bag / xp_h` égal au facteur de `session_xp` ; l'hypothèse « repos
  non appliqué » a disparu ; « quel bonus prendre » rangé par gain.
- `test_sim_leveling_bonus.py` : sans bonus, sortie identique (parité seed intacte, `tests/parity/` inchangé) ; avec
  `bonus=["sleeping_bag"]`, `xp_h` multiplié par le facteur et bonus listés.
- `test_lookup_xp_bonuses.py` (CLI) et `tests/integration/test_mcp.py` (kind `xp_bonuses`, liste d'erreur des kinds) :
  provenance, certitude par bonus, source manquante nommée sans Naowh.
- `test_sleeping_bag_chain.py` : Horde → première étape The Barrens, Alliance → Westfall (ordre lu dans la fixture) ;
  quête 79007 faite → étape suivante ; écart FojjiCore / Naowh signalé ; rien écrit sous le dépôt (`tmp_path`).
- `test_route_steps.py` : `sleeping_bag_steps` rend une étape par point de la chaîne, avec carte et position ;
  `bonus_reminders` sur 3 h de séance rend un rappel de pose du sac par recharge.
- `test_addon_bridge_auras.py` et `test_addon_logger_auras.py` (lupa) : auras du bouchon relevées (identifiant,
  cumuls, temps restant) ; API qui lève une erreur ou valeur secrète → champ absent, pas d'erreur ; rangs Legacy lus
  sous `pcall` ; aucun identifiant de sort ou d'objet en dur dans le Lua (`check_addon.py`) ; versions 0.2.0 et 0.5.0
  dans `test_addon_rules.py`.
- `test_bridge_leveling_bonuses.py` : contexte avec Well-Rested 2 cumuls → la consigne transmet l'état aux objectifs
  et la réponse cite bonus et temps restant ; Chasseur de niveau 15 Horde sans sac → phrase « prends le sac de
  couchage : la chaîne commence ici » avec l'étape de The Barrens de la fixture.
- `test_xp_check.py` étendu : gain avec Well-Rested relevé → règle « vérifié » si le facteur concorde, « à vérifier »
  sans relevé, jamais d'échec.
- Comptes à mettre à jour dès le commit « tests » de chaque bloc : `test_data_import.py`, `test_manifest.py`,
  `test_decode_version.py` (nouveau fichier), `test_registry.py` (entrées D9, D10 ajoutées, statuts de D5, E3
  changés), `test_addon_rules.py` (versions).

## Registre (`docs/MECHANICS_REGISTRY.yaml`)
- **D5** (camps et Legacy) : `absent` → `teste` ; camps : aucun % d'XP, tente qui remonte le repos ; perk Well Rested ;
  `probable`.
- **D7** (repos, Well Fed) : sources client ajoutées (`xp_bonuses.json`), perk Legacy sur le gain et le plafond ;
  reste `suppose` (LVL10).
- **E3** (nourriture) : `absent` → `teste` pour le bonus d'XP de la nourriture nutritive (Gourmand : durée).
- **Nouvelles** : **D9** Cozy Sleeping Bag et Well-Rested (`certain` pour la durée, le cumul et la valeur lus,
  `probable` pour la pose) ; **D10** cumul des bonus d'XP (`suppose`, LVL12).

## Questions ouvertes (`docs/OPEN_QUESTIONS.md`)
- **LVL3** : durée tranchée par le client (2 h) → `docs/RESOLVED_QUESTIONS.md` ; la partie « cumul » passe dans LVL12.
- **LVL12** : les pourcentages d'XP s'additionnent-ils, et le repos s'applique-t-il sur l'XP majorée ? Test : gains
  d'un même monstre relevés par ForeverLogger 0.5.0 avec et sans sac, avec et sans nourriture nutritive.
- **LVL13** : que demande la condition 142418 du bonus de nourriture, et le bonus vaut-il pour toutes les nourritures
  nutritives ? (Décodage de `PlayerCondition`, puis relevé.)
- **LVL10** : inchangée (repos jamais vu dans les relevés).

## Hors périmètre
- Catalogue Legacy complet et conseil Legacy (LG1) ; suivi de la progression Legacy (LG2).
- Encodage RestedXP, route complète, déplacements (RX1) ; T04f ne livre que les étapes et les rappels.
- Consommables de raid (T11) ; métiers de cuisine (MT1).
- Bonus sans source joueur (Discoverer's Delight, Winds of Wisdom, Adventure Awaits, Variety Show) : listés, jamais
  appliqués ; Archmagister's (+10 % contre les morts-vivants) : listé, appliqué seulement quand l'aura est active
  dans le contexte.
- Changement du classement des builds de T05 (l'XP ne le change pas).

## Risques
- **Sens des codes d'aura** déduit des descriptions (`probable`) : une description trompeuse fausserait un bonus ; le
  relevé de ForeverLogger tranchera (LVL12).
- **Valeur de Well-Rested à 1 % par cumul** : faible ; si le serveur la change sans correctif du client, seul un relevé
  le montrera.
- **`C_Traits` des perks Legacy** : API du compte peut-être absente ou secrète en bêta ; repli sur le profil réglé à la
  main.
- **Bande de pixels du pont** : les auras allongent le contexte ; bornage et filtrage à contrôler sur l'autotest de la
  bande.
- **Réseau** : `PlayerCondition` seulement, par la voie existante ; aucun test réseau.
- **Installation des données** : révision de 1.60.1.70338 soumise à l'accord de l'utilisateur (arrêt au bloc A).
- **Calendrier** : six blocs ; si le contexte se remplit, s'arrêter après un bloc vert committé ; LN1 au plus tard le
  24 octobre.

## Critères de fin (T04f)
- Chaque bonus d'XP du client avec sa valeur, sa durée, son cumul, son accès, sa source et sa certitude
  (`forever lookup xp_bonuses`, `forever_lookup(kind="xp_bonuses")`).
- Durée du Well-Rested lue dans le client, LVL3 résolue.
- Règle de cumul (addition, repos ensuite) testée sur des valeurs lues dans les données, variante gardée, LVL12
  ouverte.
- `forever sim objectives` rend l'XP par heure sans repos, avec repos, avec le sac et avec les bonus actifs ;
  `forever sim leveling` modifié par un bonus actif sur fixture, inchangé sans bonus (parité intacte).
- Bouton Leveling : bonus actifs du moment, meilleur bonus à prendre, « prends le sac de couchage : la chaîne
  commence ici » ; ForeverBridge 0.2.0 et ForeverLogger 0.5.0 exécutés sans erreur sous lupa.
- Étapes de route (`RouteStep`) de la chaîne du sac et des rappels de bonus prêtes pour RX1.
- `forever xp check` dit par bonus ce qui est vérifié et ce qui reste à vérifier, sans jamais bloquer.
- Registre D5, D7, D9, D10, E3 à jour ; questions ouvertes à jour ; `uv run tasks.py verify` vert ; CI verte sous
  Ubuntu et Windows.
