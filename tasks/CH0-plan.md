# CH0 — Savoir des familiers du Chasseur : plan

Tranche de savoir, **sans moteur** (décision 154), sur la version du jeu installée la plus récente (**1.60.1.70124**,
révision 4 à ce jour). Demande de l'utilisateur du 2026-10-01 ; section CH0 de `docs/ROADMAP.md` ; décisions 49, 99,
124, 127, 131, 133, 148, 154, 155, 156.

But : qu'un joueur de Chasseur puisse demander, en français et sans rien deviner, comment fonctionne le système de
familiers de Forever, ce qu'une famille sait faire et à quels rangs, et où apprivoiser la bête qui enseigne tel rang
près de sa zone et à son niveau ; chaque champ avec sa source et sa certitude, le client d'abord, Forever Bestiary
ensuite. Aucune valeur de jeu n'apparaît dans ce plan : les clés sont nommées, les tests lisent leurs valeurs
attendues dans `tests/fixtures/` ou `forever/data/`.

Trois réponses attendues, chacune devenue un cas du jeu d'évaluation (bloc E) :

1. « Où apprendre Bite rang 3 près des Tarides à mon niveau ? » → guide d'apprivoisement (bloc D).
2. « Quelles capacités a un loup et à quels rangs ? » → fiche de famille (blocs A et D).
3. « Comment fonctionne l'entraînement des familiers sur Forever ? » → fiche des règles du système (blocs C et D).

## Questions décisives (réponse attendue avant l'exécution)

- **D1 — Tables du client à télécharger (accord demandé avant chaque accès, au moment de l'exécution).**
  Ce que le cache de 1.60.1.70124 porte déjà et qui suffit, **sans aucun accès** : `SkillLine` (lignes `Pet - <famille>`,
  `Beast Training`, `Pet - Generic`), `SkillLineAbility` (capacités de chaque ligne, chaîne des rangs par
  `SupercedesSpell`, colonne sans nom `Field_5_5_4_67090_014_1`), `SpellName` (enUS et frFR : noms français des
  capacités), `Spell` (textes des effets), `SpellLevels` (niveau requis de chaque rang), `SpellPower` (coût en focus),
  `SpellCooldowns`, `SpellEffect` (bonus de famille portés par l'aura passive de chaque ligne ; passifs de vitesse
  d'attaque ; aura « Hunter Pet Scaling »), et `classes.json` (Tame Beast, Beast Lore, Beast Training, Feed Pet,
  Revive Pet et Call Pet y sont déjà, avec leur niveau, depuis PV1).
  Accès proposés, par `forever fetch --version 1.60.1.70124` (adresse actuelle de wago.tools ; une table déjà en cache
  n'est pas retéléchargée ; réponse vide = « absente du build », notée, **jamais remplacée** par une autre table) :
  - **Nécessaires**
    1. `CreatureFamily` (enUS, puis frFR) : lien famille ↔ ligne de compétence, masque de régime (`PetFoodMask`),
       noms français des familles (« loup » → famille du client). Sans elle : régime tiré de l'addon seulement
       (`suppose`), noms français des familles absents (l'agent passe le nom anglais).
    2. `UiMap` (enUS, puis frFR) : noms des cartes dont les positions de l'addon et de la sauvegarde portent
       l'identifiant (`uiMapID`), noms français des zones (« Les Tarides » → « The Barrens » : Questie n'a pas de
       table française), continent de chaque zone (`ParentUiMapID`) pour les zones voisines (D2). Sans elle : zones
       demandées en anglais seulement, positions de la carte communautaire non rattachées à une zone.
  - **Facultatives** (chacune seulement si tu l'acceptes ; leur absence ne bloque aucun critère de fin)
    3. `ItemPetFood` (enUS, frFR) : noms des régimes du masque de `CreatureFamily`. Sans elle : bits du masque
       nommés par recoupement avec l'addon (`probable`).
    4. `Creature` (enUS, frFR) : famille et noms (anglais et français) de chaque PNJ ; recoupe la famille des bêtes
       de l'addon par le client et nomme en français les bêtes que la carte communautaire ne nomme pas.
    5. `CreatureDifficulty` : drapeaux des PNJ, dont un bit d'apprivoisement probable (sens à établir sur des bêtes
       connues, question ouverte si le bit ne se dégage pas).
    6. `SpellTargetRestrictions` : une borne de niveau de cible sur Tame Beast, si la colonne existe ; sinon la marge
       d'apprivoisement reste un relevé de joueurs (`suppose`) avec sa question ouverte.
  Aucun autre accès ; ni wowhead, ni beastmaster.io, ni foreverchanges.pro (sources de l'addon, déjà citées par lui).
  **Proposition** : 1 et 2, plus 4 (le recoupement de famille par le client est le seul moyen de signaler une bête mal
  classée par l'addon) ; 3, 5 et 6 si tu veux pousser le régime et l'apprivoisement au plus près du client.
- **D2 — « Près des Tarides à mon niveau » : zone, niveau, personnage.** Le profil n'a pas de champ de zone
  (`forever/profile.py`), ForeverLogger ne relève pas la zone, et le profil d'évaluation n'a aucun Chasseur
  (personnage actif : un Mage).
  - **Zone** : tirée de la question (nom français ou anglais, résolu par `UiMap` frFR et enUS, puis par les noms de
    zones de Questie) ; absente de la question, l'agent la demande. Pas de champ de zone ajouté au profil.
  - **Niveau** : celui du personnage actif s'il est Chasseur ; sinon, si le profil a un seul Chasseur, celui-là,
    annoncé en une ligne ; sinon l'agent demande le personnage ou le niveau (règle « Données du joueur » de
    `format-reponse.md`). Le guide refuse un niveau absent, jamais de valeur par défaut muette.
  - **Zones voisines de son niveau** : zones du même continent que la zone demandée (`UiMap`, continent trouvé en
    remontant `ParentUiMapID` jusqu'à une carte de type continent, comme `Core/Maps.lua` de l'addon, et non en un
    seul saut) dont la plage de niveau
    des PNJ normaux (Questie, `zones_for_level`) recoupe la bande de niveau du joueur (`level_band`). Sans `UiMap` :
    toutes les zones dont la plage recoupe la bande, signalé.
  - **Évaluation** : un profil d'évaluation à part, `tests/fixtures/plugin_eval/profile-chasseur.json` (Chasseur
    Horde actif, niveau écrit dans la fixture), passé par `env: EVAL_FOREVER_PROFILE` au seul cas « Bite rang 3 » ;
    `profile-rempli.json` reste inchangé (les cas existants ne bougent pas). Seuls les cas étiquetés « profil »
    exigent un profil absent (`test_empty_profile_cases`) : un profil existant passé par `env` à un autre cas ne
    casse aucun test.
  - **Proposition** : tout ce qui précède.
- **D3 — Protocole de mesure : ForeverLogger relève-t-il le familier ?** La ROADMAP veut « les statistiques du
  Chasseur au même instant par ForeverLogger », mais ForeverLogger ne relève aujourd'hui ni l'Endurance, ni l'armure,
  ni la puissance d'attaque du Chasseur, ni rien du familier (`addon/ForeverLogger/ForeverLogger.lua`). Le bloc avancé
  du journal donne, pour une unité source, ses PV maximaux, sa puissance d'attaque et son armure (familier compris
  quand il frappe), pas l'Endurance du Chasseur.
  - (a) **Étendre ForeverLogger** dans CH0 : instantané **hors combat** sur `UNIT_PET` et `PET_UI_UPDATE` (familier :
    famille, niveau, PV maximaux, armure, vitesse d'attaque, puissance d'attaque, loyauté, points d'entraînement
    totaux et dépensés, régime) et, au même instant, le Chasseur (Endurance, armure, puissance d'attaque à distance et
    en mêlée, critique) ; et à l'ouverture de la fenêtre Beast Training, la liste des capacités offertes avec leur
    rang, leur coût en points d'entraînement et leur niveau requis. Chaque API sous `pcall`, valeur secrète = champ
    absent, aucune fonction d'action, aucun abonnement au journal de combat (`docs/ADDON.md`). Effet : le coût en
    points d'entraînement et le régime deviennent **observables en jeu** (preuve proposée au registre, jamais écrite
    sans accord), et l'héritage se mesure par paires d'instantanés (équipement du Chasseur changé, familier inchangé).
  - (b) Protocole écrit seulement, sur le journal seul ; l'extension de ForeverLogger passe en CH1.
  - **Proposition : (a)**, bloc F. Tu relèveras en jeu (je ne le peux pas) ; la lecture du relevé est testée sur
    fixture.
- **D4 — Ce que les sorties montrent de Forever Bestiary, et ce qui entre dans le dépôt.** L'addon n'a pas de licence
  (décision 133 : lecture locale libre, seuls des agrégats dans le dépôt).
  - **Dans les sorties** (CLI, MCP, à l'exécution, rien d'écrit) : bêtes, niveaux, zones, coordonnées (base de
    l'addon, carte communautaire, mes observations), rangs enseignés et leur marque de l'addon, vitesse d'attaque,
    chacun avec sa source, sa date et le **nombre** de joueurs qui l'ont vu ; jamais une empreinte de joueur (`rp`), un
    nom (`peers`, `feed[].who`), un GUID (`petGuids`) ni les clés `self*`, **supprimés à la lecture**.
  - **Dans le dépôt** : `pet_rules.json` (règles du système non portées par le client, chacune en une phrase avec sa
    source : section du guide de l'addon, auteurs cités par l'addon, dates des relevés ; `suppose`, décision 127) ;
    rapport de recoupement généré `docs/research/familiers-recoupement.md` (écarts nommés, avec les deux valeurs et
    leur source, comme les rapports de données ; aucune table de l'addon recopiée) ; fixtures **synthétiques** (bêtes
    et noms inventés, structure réelle). La base des bêtes reste lue dans l'addon installé, comme Questie.
  - **Proposition** : tout ce qui précède.
- **D5 — Évaluation et installation des données.**
  - Quatre cas : les trois questions ci-dessus (étiquette nouvelle `familiers`) et **un voisin négatif** (familier
    exotique en retail, étiquette `wow-autre`), comme PV1 (trois cas et un voisin) ; contrôlés sans modèle en CI ;
    passage avec le modèle des quatre cas à la main en fin de tranche, sur ton accord (coût d'un passage).
  - `pets.json` (décodé) entre par une **révision 5** de 1.60.1.70124 : `forever decode`, puis
    `forever install --dry-run` (liste des fichiers et des valeurs ajoutés), **arrêt pour ton accord**, puis
    installation et commit. `pet_rules.json`, fichier hérité nouveau, n'est pas écrit par `forever install` (comme
    `pvp_rules.json` en PV1) : il entre à la main dans `forever/data/1.60.1.70124/` (écriture en octets, fins de ligne
    LF, manifeste régénéré), dans le même commit de données, après le même accord. Si un build plus récent est publié d'ici là, je te demande s'il faut l'installer
    d'abord (T08a) ; le savoir des familiers ne l'attend pas.
  - **Proposition** : tout ce qui précède.

## Contexte relevé pendant le plan (lecture locale seulement)

| Fait | Où |
| --- | --- |
| Le cache de 1.60.1.70124 porte toutes les tables des capacités : lignes `Pet - <famille>` du Chasseur (chacune avec « Hunter Pet Scaling » et « Tamed Pet Passive (DND) »), `Beast Training` (capacités enseignées), `Pet - Generic` (Growl, résistances, Great Stamina, Natural Armor, Cower, passifs Faster Attack et Slower Attack) | `~/.cache/forever/wago/1.60.1.70124/enUS/SkillLine.csv`, `SkillLineAbility.csv` |
| Lignes de démons du Démoniste dans la même catégorie : distinguées par « Warlock Pet Scaling » ; la règle de sélection va dans `decode_rules.json`, pas dans le code | même table |
| Écarts visibles avant tout recoupement : deux lignes « Pet - Bat », une ligne « Pet - Core Hound » absente de l'addon, une ligne « Pet - Fox » (famille de Forever), orthographe « Crocilisk » du client contre « crocolisk » de l'addon | `SkillLine.csv`, `Data/Data.lua` de l'addon |
| Colonne sans nom `SkillLineAbility.Field_5_5_4_67090_014_1` : non nulle **seulement** sur les lignes de familier, croissante avec le rang dans une chaîne : coût en points d'entraînement **probable** ; l'autre colonne sans nom est nulle partout | `SkillLineAbility.csv` |
| Bonus de famille : aura passive de chaque ligne, trois effets (dégâts infligés, armure, PV, par type d'aura) ; valeurs dans `SpellEffect` | `SpellEffect.csv` |
| « Hunter Pet Scaling » : une aura de mise à l'échelle dont les effets nomment des grandeurs (PV, puissance d'attaque, résistances par école, critique…) avec des points de base presque tous nuls : valeurs calculées par le serveur ; l'héritage reste un relevé de joueurs (`suppose`) | `SpellEffect.csv` |
| Tame Beast, Beast Lore, Beast Training, Feed Pet, Revive Pet, Call Pet déjà décodés (niveau, recharge) | `forever/data/1.60.1.70124/classes.json` |
| Noms français des sorts présents (frFR de `SpellName`) ; aucune table française des zones ni des familles en cache | `~/.cache/forever/wago/1.60.1.70124/frFR/` |
| Forever Bestiary 0.5.0 : `Data/Data.lua` (`ns.Data` : familles, capacités et rangs, `ns.Data.beasts` : PNJ, famille, plage de niveau, rang du PNJ, vitesse `s`, zones `z`, coordonnées `c`, rangs enseignés `t`), `Data/Community.lua` (`ns.Data.community` : date, nombre de joueurs, observations par PNJ avec positions par `uiMapID` et empreintes `rp`), `Data/Guide.lua` (sections avec leur source ; textes assemblés par concaténation `..`, donc pas un littéral Lua) ; données figées sur le client 1.60.1.69913 | `Interface/AddOns/ForeverBestiary/`, `tasks/inventaire-addons.md` |
| Troisième élément de `t` : `p` affiché « beta » (relevé par des joueurs de la bêta), `b` affiché « ? », `c` sans marque (Classic, sens probable) ; `cf` : `classic`, `beta`, `datos` (« vu seulement dans les données du jeu »), `community` | `UI/Beasts.lua`, `Core/Index.lua` de l'addon |
| `lua_table.py` lit des affectations globales et un littéral seul ; les fichiers de l'addon commencent par `local _, ns = ...` puis affectent des champs (`ns.Data = {…}`) : il faut lire un littéral à partir d'une position | `forever/pipeline/lua_table.py` |
| Sauvegarde `ForeverBestiaryDB` (schéma 2) : `obs` (par PNJ : positions par `uiMapID` avec heure et niveau, noms par langue dont frFR, plage de niveau, empreintes `rp`, nombre de rapporteurs), `feed` (avec `who` : nom d'un joueur), `pets` et `history` (mes familiers, par nom de personnage), `petGuids`, `self*`, `peers` (joueurs tiers), `zoneByName`, `zoneIds`, `opts` | `WTF/Account/<COMPTE>/SavedVariables/ForeverBestiary.lua` |
| `forever addons status` : `DATA_ADDONS` sans Forever Bestiary ; le test vérifie un sous-ensemble des addons suivis (aucun compte épinglé) | `forever/addons.py`, `tests/unit/test_addons_status.py` |
| Questie : PNJ (niveaux, zone), noms des zones en anglais seulement, `zones_for_level` (plage des PNJ normaux par zone) | `forever/pipeline/questie.py` |
| Profil : aucun champ de zone ; profil d'évaluation sans Chasseur | `forever/profile.py`, `tests/fixtures/plugin_eval/profile-rempli.json` |
| ForeverLogger : instantanés de niveau, talents, bonus et critique des sorts ; rien du familier ni des statistiques physiques du Chasseur | `addon/ForeverLogger/ForeverLogger.lua` |
| Routeur : CH0 absent de `UNCOVERED_TRANCHES` (jamais ajoutée) ; la ligne « Paladin, Démoniste, …, Chasseur » renvoie à CH1 sans distinguer le familier | `tests/unit/test_plugin_structure.py`, `plugin/skills/forever-router/SKILL.md` |
| Évaluation : 62 cas (41 positifs, 21 négatifs), `POSITIVE_COUNTS` par étiquette, aucun chiffre de jeu dans les questions (`GAME_NUMBER`) | `tests/unit/test_plugin_evals.py` |
| Registre : 113 entrées, couverture 41/113, `teste 40` ; catégories du moteur `A` à `H` seulement (une catégorie `L` n'exige pas d'implémentation dans le moteur) | `forever/registry.py`, `tests/unit/test_registry.py` |
| `docs/SPEC.md` (« Domaines et sources ») et `docs/ARCHITECTURE.md` (« Outils et skills prévus ») ne citent pas CH0 | — |
| Le guide de l'addon cite un bug de la bêta signalé par des joueurs (familiers d'une zone qui perdent leurs capacités) : rien à modéliser (aucun calcul ici), affiché comme signalement de joueurs ; s'il apparaît dans les « Known Issues » officielles (`forever notes`, lancé à la main), il est listé comme bug reconnu | `Data/Guide.lua` |

## Choix d'architecture (sans question)

- **Deux sources séparées net.**
  - **Client → `forever/data/1.60.1.70124/pets.json`**, fichier décodé (`DECODED_FILES`, `sources.json`,
    `origins.json` origine `client`, manifeste) : familles du Chasseur (lignes de compétence, noms anglais et
    français, bonus de dégâts, d'armure et de PV par l'aura passive, régime si `CreatureFamily`), capacités (familiales,
    enseignées par Beast Training, générales, passifs de vitesse d'attaque) et leurs rangs (sort, niveau requis, coût
    en points d'entraînement `probable`, coût en focus, recharge, texte de l'effet résolu par `forever/pipeline/tooltip.py`,
    variable non résolue gardée telle quelle et signalée), effets de « Hunter Pet Scaling » (type d'aura, valeur
    annexe, points de base, `probable`, rien d'interprété), cartes et zones si `UiMap` ; renvoi vers `classes.json`
    pour les sorts du Chasseur (aucune recopie).
  - **Forever Bestiary → lu à l'exécution**, jamais copié : `forever/pipeline/bestiary.py` (modèle de `questie.py`),
    lit `Data/Data.lua`, `Data/Community.lua` et la sauvegarde ; version et empreinte de l'addon (méthode de
    `forever/addons.py`), date de la base, date de la carte communautaire et date de chaque observation dans la
    provenance. Addon absent : les fiches de famille et de capacité restent rendues par le client ; le guide le dit
    et ne rend aucune bête.
- **Règles du système hors du client → `pet_rules.json`** (fichier hérité, `INHERITED_FILES`, origine `addon` ou
  `manuel` avec raison) : marge d'apprivoisement, mode d'apprentissage, gain des points d'entraînement (inconnu :
  `null`, statut `absent`), effet de la loyauté, héritage des statistiques, vitesse d'attaque de base, focus et
  bonheur, à qui s'applique le niveau requis d'un rang (familier ou Chasseur, règle de Classic) ; chacune avec
  `source`, `date`, `certainty` (au plus `suppose` pour un relevé de joueurs, décision 127) et l'identifiant du
  registre. Une règle établie dans le client pendant le bloc A (colonne de `SpellTargetRestrictions`, régime de
  `CreatureFamily`) quitte ce fichier pour `pets.json`.
- **Aucun calcul de combat** : le guide est un filtre et un tri de données (`forever/pets.py`, fonctions pures),
  comme `zones_for_level` ; rien dans `forever/engine/`.
- **Anonymisation à la lecture** : `bestiary.py` supprime `rp`, `peers`, `feed[].who`, `petGuids`, `selfIds`,
  `selfForms`, `selfLooseDone` dès le décodage ; seuls restent des comptes (`nrp`, nombre de joueurs de la carte).
  Mes familiers (`pets`, `history`) sont rendus à moi seulement (CLI, MCP), jamais écrits dans le dépôt ; aucun nom
  de personnage dans les fixtures (noms inventés).
- **Recoupement, jamais tranché** : `forever pets crosscheck` compare client ↔ addon (familles présentes, nom,
  bonus, capacités de chaque famille, niveaux requis des rangs) et addon ↔ Questie (niveaux et zone de chaque PNJ ;
  famille par `Creature` si D1-4) ; chaque écart nommé avec ses deux valeurs et leurs sources ; la valeur rendue par
  les fiches reste celle du client, l'écart figure dans `assumptions` de la provenance.
- **Une seule entrée MCP** : `forever_lookup(kind="pets", …)` (principe de `docs/ARCHITECTURE.md` : un domaine de
  consultation, pas un outil). CLI `forever pets …`, branchée sur les mêmes fonctions.
- **Noms français** : capacités par `SpellName` frFR, familles par `CreatureFamily` frFR, zones par `UiMap` frFR,
  bêtes par `Creature` frFR (D1-4) sinon par les noms frFR de la carte communautaire (source communautaire datée) ;
  résolution insensible à la casse et aux accents ; plusieurs candidats : erreur qui les liste (comme
  `forever_explain_mechanic`).

## Interfaces

### `pets.json` (clés ; valeurs dans les fixtures et les données)

```
build, source, notes
families.<clé> : name{en, fr}, skill_lines[], passive_spell, bonus{damage_pct, armor_pct, health_pct},
                 diet[] | null, abilities[], certainty{<champ>: certain|probable}
abilities.<clé> : name{en, fr}, kind (family|trained|general|attack_speed), skill_lines[], families[],
                  ranks[{rank, spell_id, level, training_cost, focus_cost, cooldown_s, description}],
                  certainty{training_cost: probable, …}
pet_scaling : spell_id, effects[{aura, misc, base_points}], certainty: probable
maps.<uiMapID> : name{en, fr}, parent, kind          (si UiMap)
hunter_spells : clés de classes.json (renvoi, aucune valeur recopiée)
```

### `pet_rules.json`

```
rules.<clé> : text (français), value | null, unit, source, date, certainty, registry
clés : tame.level_margin, learning.method, training.rank_level_applies_to, training.points_gain,
       loyalty.limits_training, inheritance.{health_per_stamina, armor_pct, attack_power_pct, crit},
       attack_speed.base_s, focus.regen_per_s, happiness.decay, reported_bugs[]
```

### CLI (texte et `--json`, code 0, provenance)

- `forever pets rules` : système de familiers, une règle par ligne (texte, valeur, source, date, certitude, registre).
- `forever pets family <famille>` : noms, bonus, régime, capacités avec leurs rangs (niveau, coût, focus, recharge).
- `forever pets ability <capacité> [--rank N]` : rangs, familles, bêtes qui enseignent chaque rang (nombre, puis
  liste avec `--detail`).
- `forever pets beast <nom|id>` : famille (addon, client si D1-4), niveaux (addon et Questie), zones, coordonnées,
  rangs enseignés et leur marque, vitesse d'attaque, observations datées.
- `forever pets tame (--ability <capacité> [--rank N] | --family <famille> | --beast <nom>) --zone <zone> --level <N>`
  : guide d'apprivoisement (bloc D).
- `forever pets crosscheck [--markdown <chemin>]` : écarts client ↔ addon ↔ Questie.
- `forever pets mine` : mes observations et mes familiers (`ForeverBestiaryDB`), sans aucune donnée de tiers.

### MCP

`forever_lookup(kind="pets", name=None, rank=None, zone=None, level=None, detail=False)` :
`name` absent → règles ; famille → fiche de famille ; capacité → fiche de capacité ; capacité, famille ou bête avec
`zone` et `level` → guide ; bête → fiche de bête. `UnsupportedKindError` et la docstring listent `pets`.

### Guide d'apprivoisement (`forever/pets.py`)

Entrée : cible (capacité et rang, famille ou bête), zone, niveau ; règles de `pet_rules.json`.
Sortie : `level`, `zone` (nom anglais et français), `target`, `highest_rank` (rang le plus haut dont le niveau requis
est atteint au niveau donné, selon `training.rank_level_applies_to`), `zones[]` (zone demandée d'abord, puis zones
voisines selon D2, chacune avec sa plage de niveau Questie), `beasts[]` par zone (nom, PNJ, famille, plage de niveau,
`tameable_now` et, sinon, le niveau où elle le devient selon `tame.level_margin`, rang enseigné et marque de l'addon,
coordonnées avec leur source et leur date, nombre de rapporteurs, écarts du recoupement), `certainty` par champ,
`provenance` (version du jeu, empreinte des données, version et empreinte de l'addon, date de sa base, date de la
carte communautaire, date de ma sauvegarde, hypothèses).

## Blocs et étapes

Un cycle rouge → vert par bloc (commit « CH0: tests (bloc X) », puis « CH0: bloc X vert ») ; `tasks/.rouge` et
`tasks/.tests-verrouilles` réécrits à chaque bloc. Ordre par dépendance. Contexte plein : arrêt après un bloc vert
committé.

### Bloc A — Système de familiers décodé du client

1. Accès réseau de D1 retenus, chacun après accord ; tables ajoutées à `decode_rules.json` (`pet_tables`,
   `localized_pet_tables`), règle de sélection des lignes du Chasseur (`pet_skill_lines` : catégorie, préfixe,
   présence de « Hunter Pet Scaling » ; lignes `Beast Training` et `Pet - Generic` par leur nom), alias des clés de
   famille (`pet_family_aliases`), sens des types d'aura des bonus et des passifs (`pet_auras`, `probable`).
2. Fixtures : extraits du cache dans `tests/fixtures/wago/1.60.1.70124/` (deux familles du Chasseur, une ligne de
   démon, `Beast Training`, `Pet - Generic`, les sorts de leurs rangs dans chaque table, frFR de `SpellName`, et les
   lignes correspondantes des tables téléchargées).
3. `forever decode` produit `pets.json` ; `verify` de la candidate contrôle sa forme (chaque famille a au moins une
   capacité, chaque rang a un niveau, chaîne des rangs sans trou ni cycle, aucune ligne de démon) ; comptes des
   fichiers mis à jour dès le commit « tests » (`test_data_import.py`, `test_manifest.py`, `test_decode_version.py`,
   `origins.json`).
4. `GameData.pets()` (lecture seule) ; `forever lookup` inchangé pour les autres domaines.

### Bloc B — Lecteur de Forever Bestiary et de sa sauvegarde

1. `lua_table.py` : lecture d'un littéral à partir d'une position (`parse_lua_value_at`), pour `ns.Data = {…}`,
   `ns.Data.beasts = {…}`, `ns.Data.community = {…}` ; `Guide.lua` n'est pas lu par le code (concaténations) : ses
   règles entrent dans `pet_rules.json` à la main, avec leur source.
2. `forever/pipeline/bestiary.py` : `read_bestiary(addon_dir)` (version, empreinte, date et build de la base,
   familles, capacités, bêtes, carte communautaire) et `read_bestiary_saved(sv)` (mes observations, mes familiers),
   anonymisation à la lecture (choix d'architecture), marques `t` et `cf` traduites avec leur sens et sa certitude.
3. `DATA_ADDONS` : entrée `ForeverBestiary` (`reader` = le nouveau module, `depends` = `pets.json` en recoupement et
   `pet_rules.json`, `action` = « forever pets crosscheck, puis relire Guide.lua et comparer pet_rules.json »).
4. Fixtures synthétiques : `tests/fixtures/addons/ForeverBestiary/` (`.toc`, `Data/Data.lua`, `Data/Community.lua`,
   `Data/Guide.lua`, bêtes et noms inventés, deux zones d'un même continent et une d'un autre) et un second état à
   version identique, contenu changé ; `tests/fixtures/savedvariables/ForeverBestiary.lua` (avec `peers`, `who`,
   `rp`, `petGuids` et `self*` inventés, pour prouver qu'ils disparaissent).
5. `docs/DATA_SOURCES.md` (lecteur, provenance, ce que l'addon apporte) et `tasks/inventaire-addons.md` (empreinte de
   référence remplacée par le relevé de `forever addons status --save`).

### Bloc C — Règles du système, registre et recoupement

1. `pet_rules.json` (clés de l'interface) dans `forever/data/1.60.1.70124/`, `INHERITED_FILES`, `sources.json`,
   `origins.json` (origine `addon`, nom et version ; `manuel` avec raison pour la règle de Classic du niveau requis).
2. Registre : catégorie `familiers`, entrées **L1 à L12** (liste ci-dessous) ; questions ouvertes dans
   `docs/OPEN_QUESTIONS.md` : marge d'apprivoisement (si absente du client), gain des points d'entraînement, sens de
   la colonne de coût, sens du bit d'apprivoisement (si D1-5), marques `t` de l'addon, effets de « Hunter Pet
   Scaling », deux lignes « Pet - Bat » et « Pet - Core Hound » (apprivoisable ?), bug signalé par des joueurs.
3. `forever pets crosscheck` et rapport généré `docs/research/familiers-recoupement.md` (écarts listés ; régénéré en
   fin de tranche sur l'addon installé).
4. **Révision 5** (D5) : `forever decode`, `forever install --dry-run`, **arrêt pour ton accord**, installation de
   `pets.json`, ajout à la main de `pet_rules.json` (D5), commit des données et rapport
   `docs/research/data-1.60.1.70124-r5.md`.

| Id | Description | Statut visé | Certitude (règle) |
| --- | --- | --- | --- |
| L1 | Apprivoisement : bêtes apprivoisables et marge de niveau au-dessus du Chasseur | teste | suppose (certain si le client la porte, D1-6) |
| L2 | Apprentissage d'une capacité : bête apprivoisée qui la connaît, combat, puis Beast Training ; capacités générales chez l'entraîneur | teste | suppose |
| L3 | Capacités de chaque famille, chaîne des rangs et niveau requis | teste | certain |
| L4 | Coût d'un rang en points d'entraînement | teste | probable (colonne sans nom ; certain après relevé de D3) |
| L5 | Gain de points d'entraînement | absent | suppose |
| L6 | Loyauté : limite de l'entraînement | teste | suppose |
| L7 | Régime par famille | teste | certain par `CreatureFamily` (D1-1), sinon suppose |
| L8 | Beast Lore : niveau d'apprentissage et ce qu'il montre | teste | certain (niveau) ; suppose (effet décrit) |
| L9 | Bonus de famille : dégâts, armure, PV | teste | certain |
| L10 | Héritage des statistiques du Chasseur (PV, armure, puissance d'attaque, critique) | teste | suppose (décision 127) |
| L11 | Vitesse d'attaque : base et passifs Faster Attack et Slower Attack | teste | suppose (base) ; effet des passifs lu dans le client |
| L12 | Focus et bonheur du familier : coût des capacités, régénération, baisse du bonheur | teste | suppose (régénération, bonheur) |

Comptes écrits en phase rouge : `total` 125, couverture **52/125**, sortie de `main` `teste 51` (et
`valide-journal` inchangé) ; à reprendre dans la même phase rouge si la liste change sur ton accord.

### Bloc D — Guide d'apprivoisement, CLI et MCP

1. `forever/pets.py` : résolution des noms (français, anglais, clé), fiches (règles, famille, capacité, bête),
   guide (interface), zones voisines (D2), certitude par champ, provenance.
2. `forever pets …` (CLI) et `forever_lookup(kind="pets")` (MCP), docstring, `UnsupportedKindError`.
3. Sans réseau ; sans addon installé : fiches du client seules, guide refusé avec un message qui le dit.

### Bloc E — Plugin : skill, routeur, évaluation

1. Nouveau skill `plugin/skills/forever-familiers/SKILL.md` (moins de 200 lignes, sans chiffre de jeu ;
   déclencheurs : familier, chasseur, apprivoiser, capacité, rang, entraînement, Beast Training, loyauté, régime,
   famille ; pas pour retail ni Classic hors Forever ; renvoi à `format-reponse.md` ; règle D2 pour la zone et le
   personnage ; ce qu'il ne fait pas : choix du meilleur familier, dégâts du familier → CH1).
2. Routeur : description (« familiers du Chasseur »), lignes de la carte des domaines couverts
   (`forever_lookup(kind="pets", …)` → `forever-familiers`, trois lignes : règles, famille ou capacité, guide) ; dans
   les domaines non couverts, la ligne des classes précise « Chasseur : dégâts, rotations, leveling, choix du
   familier par contexte » → CH1.
3. `tests/unit/test_plugin_structure.py` : `SKILLS` + `forever-familiers` ; mots déclencheurs ; le routeur cite
   `kind="pets"` et `forever-familiers` ; `UNCOVERED_TRANCHES` : CH1 gardée (moteur et choix du familier), CH0
   absente et vérifiée comme couverte (un test nouveau : CH0 n'est dans aucune ligne « non couvert ») ; commentaire de
   la liste mis à jour ; `test_domain_skills_use_the_response_format` paramétré avec le nouveau skill.
4. Évaluation (D5) : `familiers-bite-rang-tarides`, `familiers-capacites-loup`, `familiers-entrainement`,
   `neg-retail-familier-exotique` ; correcteurs `skill`, `outil` (`forever_lookup`, `"kind": "pets"`), `chiffres`,
   `certitude`, `provenance`, plus un juge par cas (guide : zone demandée et zones voisines, niveau du profil,
   bêtes avec coordonnées et source, date de la carte communautaire, rang le plus haut atteignable, ce qui est
   supposé ; loup : capacités et rangs recopiés de l'outil, niveau et coût de chaque rang, coût `probable` dit tel ;
   entraînement : étapes, points d'entraînement, loyauté, marge d'apprivoisement, Beast Lore, chacun avec sa
   certitude, relevés de joueurs annoncés comme tels, gain des points inconnu) ; profil `profile-chasseur.json`
   (D2) ; questions passées à `GAME_NUMBER` avant le verrouillage.
5. Version du plugin 0.5.0 → **0.6.0**, `fingerprint.json` (`scripts/plugin_fingerprint.py`), description et mots-clés
   de `plugin.json` ; `docs/ARCHITECTURE.md` (section « Plugin Claude Code » : skills, évaluation à 66 cas).

### Bloc F — Protocole de mesure et relevé du familier (selon D3)

1. `docs/research/familiers-protocole.md`, sur le modèle de `pvp-dr-protocole.md`, sans chiffre : coups blancs du
   familier (`SWING_DAMAGE` d'une unité `Pet-…` à moi) et intervalle entre deux coups, hors effets de hâte connus ;
   PV maximaux, armure et puissance d'attaque du familier lus dans le bloc avancé ; statistiques du Chasseur au même
   instant par ForeverLogger ; paires d'instantanés pour l'héritage ; ce qu'il faut écarter (combat contre un joueur,
   auras de hâte, version du client différente, décision 135) ; seuil (`tolerance.n_min`) et forme de la preuve
   proposée au registre, jamais écrite sans accord.
2. Si D3 = (a) : ForeverLogger, instantané du familier et du Chasseur hors combat, relevé de la fenêtre Beast
   Training ; `docs/ADDON.md` (procédure de test en jeu) ; `scripts/check_addon.py` et `test_addon_rules.py` passent.
3. Lecture des instantanés (`forever/pipeline/addon_sv.py`) et `forever pets measure` (hors ligne) : coût et niveau
   requis observés comparés à `pets.json`, régime observé comparé à `CreatureFamily` ou à l'addon, rapports PV du
   familier sur Endurance du Chasseur, et vitesse d'attaque observée par passif, avec `n` ; rien n'est écrit dans les
   données.

### Bloc G — Documentation et fin de tranche

`docs/SPEC.md` (« Domaines et sources » : ligne « Familiers du Chasseur (savoir) », tranches CH0, CH1),
`docs/ARCHITECTURE.md` (« Outils et skills prévus » : ligne `pets` → `forever-familiers`, CH0 ; `forever_lookup` ;
plugin), `docs/ROADMAP.md` (CH0 « Réalisé »), `docs/DECISIONS.md` (réponses D1 à D5), `docs/OPEN_QUESTIONS.md`,
`docs/DATA_SOURCES.md` (données manquantes : gain des points d'entraînement, héritage mesuré), `docs/USAGE.md`
(`forever pets`) ; `forever pets crosscheck --markdown` régénéré ; `/verifier` ; push de la branche `ch0`, CI verte
sous Ubuntu et Windows, fusion en avance rapide.

## Fichiers

| Fichier | Bloc | Nature |
| --- | --- | --- |
| `forever/data/1.60.1.70124/decode_rules.json` | A | tables, sélection des lignes, alias, sens des auras |
| `forever/pipeline/decode.py`, `verify.py`, `fetch.py` (si une table l'exige) | A | décodage de `pets.json`, contrôle de forme |
| `forever/data/1.60.1.70124/pets.json`, `pet_rules.json`, `sources.json`, `origins.json`, `revisions.json`, `meta.json`, manifeste | A, C | données (révision 5, après accord) |
| `forever/gamedata.py` | A | `pets()`, `pet_rules()` |
| `forever/pipeline/lua_table.py` | B | lecture d'un littéral à une position |
| `forever/pipeline/bestiary.py` | B | nouveau (lecture locale) |
| `forever/addons.py` | B | entrée `ForeverBestiary` |
| `forever/pets.py` | C, D | nouveau : fiches, guide, recoupement (fonctions pures) |
| `forever/cli.py`, `forever/mcp_server.py`, `forever/lookup.py` | D | `forever pets …`, `kind="pets"` |
| `addon/ForeverLogger/ForeverLogger.lua`, `forever/pipeline/addon_sv.py` | F | selon D3 |
| `plugin/skills/forever-familiers/SKILL.md`, `plugin/skills/forever-router/SKILL.md`, `plugin/.claude-plugin/plugin.json`, `fingerprint.json` | E | skill, routeur, version |
| `plugin/evals/familiers-*`, `plugin/evals/neg-retail-familier-exotique` | E | quatre cas |
| `tests/fixtures/wago/1.60.1.70124/`, `tests/fixtures/addons/ForeverBestiary/` (deux états), `tests/fixtures/savedvariables/ForeverBestiary.lua`, `tests/fixtures/plugin_eval/profile-chasseur.json`, relevé ForeverLogger de fixture | A, B, E, F | extraits et fixtures synthétiques |
| `docs/MECHANICS_REGISTRY.yaml`, `docs/OPEN_QUESTIONS.md`, `docs/DECISIONS.md`, `docs/DATA_SOURCES.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/USAGE.md`, `docs/ADDON.md` | tous | documentation |
| `docs/research/familiers-recoupement.md`, `docs/research/familiers-protocole.md`, `docs/research/data-1.60.1.70124-r5.md` | C, F, G | rapport généré, protocole, rapport de données |
| `tasks/inventaire-addons.md` | B | empreinte de référence remplacée |

## Tests attendus

Valeurs attendues lues dans les fixtures (ligne et colonne nommées dans le test) ou dans `forever/data/`, jamais
écrites dans le test. Aucun réseau (`FakeHttp.failing()`), aucun fichier du client lu par un test.

| Bloc | Test | Attendu |
| --- | --- | --- |
| A | `test_decode_pets.py` | familles = lignes du Chasseur de la fixture, ligne de démon exclue ; clé par alias ; chaîne des rangs dans l'ordre de `SupercedesSpell` ; niveau = `SpellLevels` du sort du rang ; coût = colonne de coût, certitude `probable` ; focus = `SpellPower` ; bonus = points de base de l'aura passive par type d'aura ; noms français = frFR ; régime = bits du masque de `CreatureFamily` (si accès accordé, sinon `null` et note) ; effets de « Hunter Pet Scaling » listés `probable` ; sortie déterministe |
| A | `test_verify_pets.py` | famille sans capacité, rang sans niveau, chaîne avec cycle : chacun refusé avec un message qui le nomme (copie des données, manifeste régénéré) |
| A | comptes (`test_data_import.py`, `test_manifest.py`, `test_decode_version.py`, `test_origins.py`) | `pets.json` et `pet_rules.json` comptés ; toute feuille couverte par une règle d'origine |
| B | `test_lua_table.py` (extension) | littéral lu à une position, fin rendue ; texte qui suit ignoré |
| B | `test_bestiary.py` | version, empreinte, date et build de la base lus dans la fixture ; familles, capacités, bêtes ; carte communautaire datée ; marques `t` et `cf` traduites ; addon absent : erreur lisible ; **aucun nom de `peers`, aucune valeur de `who`, aucune empreinte `rp`, aucun GUID de la fixture dans la sortie** (recherche de chaque chaîne de la fixture dans le JSON rendu) ; mes observations et mes familiers lus |
| B | `test_addons_status.py` (extension) | `ForeverBestiary` suivi ; `changé` quand un fichier de données change à version identique ; `reader` pointe vers le module |
| C | `test_pet_rules.py` | chaque règle a texte, source, date, certitude et identifiant du registre existant ; relevé de joueurs au plus `suppose` ; `training.points_gain` vaut `null` ; certitude d'une règle jamais supérieure à celle de son origine |
| C | `test_pets_crosscheck.py` | sur les fixtures : famille absente de l'addon, famille absente du client, niveau requis différent, bonus différent, plage de niveau d'un PNJ différente de Questie : chacun listé avec ses deux valeurs et leurs sources ; rien d'écart sur deux sources concordantes ; Markdown déterministe |
| C | `test_registry.py` | `total` 125, couverture 52/125, sortie de `main` `teste 51` |
| D | `test_pets_guide.py` | « capacité, rang, zone, niveau » : bêtes de la zone qui enseignent le rang, apprivoisables au niveau selon `tame.level_margin` de la fixture, puis zones voisines du même continent dont la plage recoupe la bande, zone d'un autre continent exclue ; bête trop haute rendue avec le niveau où elle devient apprivoisable ; `highest_rank` selon les niveaux de la fixture ; zone française résolue par `UiMap` frFR ; zone inconnue : erreur qui liste des candidats ; niveau absent refusé ; provenance avec version et empreinte de l'addon, date de la carte communautaire, certitude par champ ; aucune chaîne de tiers dans la sortie |
| D | `test_pets_lookup.py` | `forever_lookup(kind="pets")` : règles, famille (nom français et anglais), capacité, bête, guide ; deux candidats : erreur qui les liste ; `kind` inconnu : la liste contient `pets` ; sans addon : fiches du client rendues, guide refusé |
| D | `test_cli_pets.py` | chaque sous-commande rend code 0, texte et `--json`, provenance ; aucun réseau |
| E | `test_plugin_structure.py` | `forever-familiers` dans `SKILLS` ; mots déclencheurs ; routeur : `kind="pets"`, `forever-familiers`, CH1 citée pour le choix du familier, CH0 dans aucune ligne « non couvert » |
| E | `test_plugin_evals.py` | 66 cas, 44 positifs, 22 négatifs ; `POSITIVE_COUNTS["familiers"]` = 3 ; les trois cas attendent `forever_lookup` avec `"kind": "pets"` et un juge ; le cas du guide porte `EVAL_FOREVER_PROFILE` vers `profile-chasseur.json`, dont le personnage actif est Chasseur ; le voisin négatif interdit les skills forever ; aucune question avec un chiffre de jeu |
| E | `test_plugin_version.py` | version relevée, empreinte à jour |
| F | `test_addon_rules.py` (selon D3) | ForeverLogger : nouveaux événements sous `pcall`, aucune fonction d'action, aucun `COMBAT_LOG_EVENT` |
| F | `test_pet_measure.py` (selon D3) | instantanés de fixture : coût et niveau requis observés comparés à `pets.json`, écart signalé ; rapport PV du familier / Endurance par paire ; `n` compté ; rien écrit dans les données |
| F | `test_network_boundary.py` | inchangé (aucun module réseau hors de `forever/pipeline/`) |

## Hors périmètre

- Choix du meilleur familier par contexte (leveling, donjon, raid, PvP), dégâts du familier et sa part dans les
  dégâts du Chasseur, moteur du Chasseur (CH1) ; partie raid (CH1r).
- Toute écriture dans `ForeverBestiaryDB` ou dans les fichiers de l'addon ; tout partage en jeu.
- Lecture de `Core/PvP.lua` (votes du meilleur familier contre chaque classe) : avis de joueurs pour CH1.
- Familiers exotiques ou talents de familier : aucun vu dans la bêta selon l'addon ; signalé, rien de modélisé.
- Démons du Démoniste (lignes `Pet - <démon>`) : DE1.
- Chemin de leveling vers une bête (route, temps de trajet) : hors de la SPEC (« routes de leveling détaillées »).

## Risques

- **Colonne de coût sans nom** : lue comme coût en points d'entraînement, `probable` jusqu'au relevé de D3 ; si
  elle se révèle autre chose, le coût devient absent, sans valeur de remplacement.
- **Addon figé sur 1.60.1.69913** : écarts attendus avec le client ; listés, jamais tranchés ; les fiches suivent le
  client.
- **Noms de zones** : `UiMap`, AreaTable de Questie et zones de l'addon peuvent nommer une zone différemment ; table
  des écarts dans le rapport de recoupement, résolution par le nom anglais exact d'abord.
- **Données de tiers** : un champ de la sauvegarde ajouté par une version future de l'addon pourrait porter un nom ;
  le lecteur ne garde que les champs connus (liste blanche), pas l'inverse.
- **Textes d'effet** : variables d'infobulle non résolues pour certains sorts de familier ; gardées telles quelles et
  signalées, jamais devinées.
- **Tests verrouillés faux** : demandes regroupées dans `tasks/CH0-corrections.md`, présentées avant la fusion.
- **Le relevé en jeu (D3) dépend de toi** : sans relevé, L4 reste `probable` et L10, L11 `suppose` ; la tranche se
  termine quand même.

## Angles morts attendus (à chiffrer en fin de tranche)

- Gain des points d'entraînement et vitesse de la loyauté : inconnus (relevés qualitatifs seulement) ; effet :
  impossible de dire quand un rang devient enseignable, le guide dit seulement à quel niveau.
- Héritage des statistiques et vitesse d'attaque de base : relevés de joueurs ; effet sur CH1 (dégâts du familier),
  pas sur le savoir de CH0.
- Bêtes nouvelles de Forever absentes de Questie : niveaux et zones de l'addon seuls (`suppose`).
- Bêtes que l'addon ne connaît pas : invisibles au guide tant que la carte communautaire ne les a pas vues.

## Critères de fin

- Chaque famille, capacité et rang consultable par la CLI et le MCP, avec source et certitude par champ ; noms
  français et anglais.
- Recoupement client ↔ Forever Bestiary ↔ Questie documenté (`docs/research/familiers-recoupement.md`, écarts
  listés).
- Guide d'apprivoisement rendu pour une zone et un niveau sur fixture, sans réseau, avec provenance (version et
  empreinte de l'addon, date de la carte communautaire) ; aucun nom ni empreinte de joueur tiers dans une sortie
  (test).
- Forever Bestiary suivi par `forever addons status` (version et empreinte).
- Les trois questions de la demande et le voisin négatif dans le jeu d'évaluation, contrôlés sans modèle ; skill
  `forever-familiers` et routeur à jour ; `docs/SPEC.md` et `docs/ARCHITECTURE.md` citent CH0.
- Protocole de mesure écrit ; selon D3, relevé du familier dans ForeverLogger et sa lecture testée.
- Révision 5 de 1.60.1.70124 installée après accord ; registre L1 à L12, questions ouvertes, décisions et
  documentation à jour ; `uv run tasks.py verify` vert ; CI verte sous Ubuntu et Windows ; fusion en avance rapide
  dans `main`.

## Validation

Plan à valider par l'utilisateur (D1 à D5) avant l'exécution, dans une nouvelle session, sur la branche `ch0`.
