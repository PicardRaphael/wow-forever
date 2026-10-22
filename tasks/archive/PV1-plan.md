# PV1 — Profil automatique, puis PvP : savoir des 9 classes : plan

Tranche longue, sur la version du jeu installée la plus récente (**1.60.1.70124**, révision 1 à ce jour). Demande de
l'utilisateur du 2026-09-30, en sept points et dans cet ordre : import du profil, données du client des 9 classes,
rendements décroissants, fiches par affrontement, légalité des builds de toutes les classes, plugin, rappel des
limites. Section PV1 de `docs/ROADMAP.md` ; décisions 31, 99, 105, 106, 114, 115, 119, 120, 122, 125, 130, 131, 135.

PV1 ne calcule **aucun dégât** hors Mage : il lit, classe et croise des données fixes du client. Aucune valeur de
jeu n'apparaît dans ce plan : les tests lisent leurs valeurs attendues dans `forever/data/` ou `tests/fixtures/`.

## Questions décisives (réponse attendue avant l'exécution)

- **D1 — Questie et Auctionator dans l'import minimal.** Tu les demandes en PV1 ; la ROADMAP et la décision 125 les
  plaçaient en T07. Le profil n'a aujourd'hui ni champ de quêtes ni champ de prix. **Proposition** :
  - quêtes faites, **par personnage** : champ `quests_completed` (identifiants et date de rendu), lu dans le carnet
    de Questie (`QuestieConfig.char[…].journey`, événements `Quest` de sous-type `Complete`, joints par GUID) ;
    quêtes abandonnées ignorées ;
  - prix, **par royaume** et non par personnage : nouvelle section `realms.<royaume>.prices` du profil, avec pour
    chaque objet le dernier minimum vu, son jour et sa quantité, lus dans `AUCTIONATOR_PRICE_DATABASE` par un
    **décodeur CBOR maison** (aucune dépendance ajoutée, code de l'addon jamais lu, décision 123) ; aucun historique ;
    `AUCTIONATOR_POSTING_HISTORY` (tes ventes) jamais lu ;
  - T07 garde équipement, métiers, réputations, historique et vault ; la ROADMAP est corrigée en fin de tranche.
- **D2 — Ordre des sources à date égale, et classe venue du journal.** La règle « la plus récente l'emporte, à date
  égale la plus directe » (décision 125) demande un ordre. **Proposition**, de la plus directe à la moins directe :
  saisie explicite du joueur (`forever profile set`) > ForeverLogger > sauvegarde d'un autre addon (Questie,
  Auctionator) > journal de combat > API Blizzard (EC1). Le journal **ne porte pas la classe** (aucun
  `COMBATANT_INFO` dans les journaux de Forever, vérifié sur le journal du 2026-09-30) : la classe d'un joueur « à moi »
  vient de ForeverLogger par jointure de GUID ; à défaut, elle est **déduite des sorts de classe qu'il lance**
  (lignes de compétence des 9 classes), certitude `probable`, et seulement si aucune autre classe n'est vue pour ce
  GUID ; sinon la classe reste inconnue et le personnage n'est pas créé (listé dans la sortie).
- **D3 — Accès réseau.** Deux accès, chacun demandé **au moment de l'exécution**, rien d'autre :
  1. `forever fetch --version 1.60.1.70124` des tables **listées au bloc B** (et seulement elles ; les tables déjà en
     cache ne sont pas retéléchargées). Les noms n'ont **pas pu être vérifiés sur wago.tools** pendant le plan (pas de
     réseau sans accord) : une table absente (erreur 404) n'entraîne aucun autre appel ; elle est signalée, et le
     repli prévu (colonne « Repli » du bloc B) n'utilise que des tables déjà listées.
  2. Une recherche du sous-agent `forever-web-researcher` pour la **source des règles de rendements décroissants de
     Classic** (catégories, fenêtre, paliers, immunité) et d'éventuelles annonces de Forever sur les contrôles en PvP.
     Aucune source locale n'existe (le seed n'en a pas, `pvp-model.md` nomme seulement le manque). Chaque adresse
     retenue est citée dans `sources.json`. **Proposition** : accepter cette recherche ; ou tu me donnes la source.
- **D4 — Périmètre face à la ROADMAP.** Ta liste nomme un skill ; la ROADMAP et la décision 115 en nomment deux, et
  elle prévoit aussi le profil PvP du Mage avec rendements décroissants et bijou. **Proposition** :
  - `forever-builds` **fait ici**, court : c'est le foyer naturel du point 5 (builds de la communauté vérifiés pour
    les classes pas encore calculées) ; `forever-pvp` porte le savoir et les fiches ;
  - profil PvP du Mage (rendements décroissants, bijou) **reporté à PV2** : il change les builds `pvp-bg` et
    `pvp-world` de T05 sur des règles encore supposées ; en PV2, les rendements seront mesurés dans tes journaux.
- **D5 — Remplacer `racials.json`, c'est supprimer une donnée et peut changer le Mage.** `CLAUDE.md` demande ton
  accord avant de supprimer une donnée. Le moteur du Mage lit aujourd'hui trois raciaux passifs (esprit, mana,
  critique à l'épée) dans ce relevé communautaire. **Proposition** : les raciaux décodés du client l'emportent
  (décision 106) ; `racials.json` est retiré à la révision 2, une copie figée `_seed_racials.json` garde le mode
  `rules=seed` identique (parité inchangée) ; si une valeur décodée diffère du relevé et qu'un build de T05 change au
  rejeu, je m'arrête avant le commit et te montre l'écart.

## Contexte relevé pendant le plan (lecture locale seulement)

| Fait | Où |
| --- | --- |
| Profil vide ; ForeverLogger connaît 3 personnages : Chasseur Tauren, Mage Orc, Chasseur Elfe de la nuit | `~/.forever/profile.json`, `ForeverLogger.lua` |
| Talents de ForeverLogger : `{ID de TraitNode : rang}` ; `talents.json` n'a **aucun identifiant de nœud** | `addon/ForeverLogger/ForeverLogger.lua`, `talents.json` |
| Le journal ne porte ni classe ni `COMBATANT_INFO` ; le champ `level` du bloc avancé n'est pas vérifié pour un joueur | journal du 2026-09-30, `combatlog.py` (`Advanced`) |
| `SkillLineXTraitTree` lie **un** arbre de traits par classe (9 lignes) ; ses nœuds couvrent les trois arbres de la classe | cache `1.60.1.70124/enUS` |
| Même grille d'onglets pour les 9 classes ; trois nœuds hors grille : Paladin (PosX 5030), Prêtre (9280), Chasseur (102800, zéro en trop déjà géré) | `TraitNode.csv` |
| `decode_rules.json` est **mono-classe** (`class: "Mage"`, `skill_lines`, `talent_geometry`) | `forever/data/1.60.1.70124/` |
| Colonnes déjà présentes mais non lues : `SpellMisc.RangeIndex`, `SchoolMask`, `PvPDurationIndex` ; `SpellEffect.EffectMechanic`, `PvpMultiplier`, `ImplicitTarget_*` ; `SkillLineAbility.ClassMask`, `RaceMasks_*` | CSV du cache |
| `ChrClasses` et `SkillLine` sont déjà en cache (hors des 22 tables décodées) | cache |
| Moteur du Mage : `_racials()` lit `spirit_pct`, `mana_pct`, `sword_spec.crit` ; `profile.py` et `leveling.py` lisent la liste des races | `forever/gamedata.py`, `profile.py`, `leveling.py` |
| Rendements décroissants absents du client (règle du serveur en Classic) ; aucune source locale | seed, `docs/research/` |
| Registre : 108 entrées, 37 testées ou mieux ; `ENGINE_CATEGORIES = "ABCDEFGH"` ; préfixes A à J utilisés | `docs/MECHANICS_REGISTRY.yaml`, `forever/registry.py` |
| Plugin 0.4.3, 3 skills, 58 cas d'évaluation (38 positifs, 20 voisins) | `plugin/`, `tests/unit/test_plugin_structure.py` |
| `tests/golden/` n'existe pas | `find tests -iname '*golden*'` |

## Choix d'architecture (sans question)

- **Espace par classe (décision 31)** : `GameData` garde son moteur Mage tel quel et gagne `classes: Mapping[str,
  ClassKnowledge]` (clé : nom anglais du client). `ClassKnowledge` : arbres, talents (clé, nœud, palier, colonne,
  rangs, prérequis, description du client), sorts (rangs, niveau, recharge, recharge globale, durée, durée PvP,
  portée, école, coût, temps d'incantation, classement PvP), sorts de familier. Les tranches de classe y brancheront
  leurs moteurs sans changer ce schéma.
- **Fichiers de données** (1.60.1.70124, révision 2, installée par `forever install`) :
  - décodés (`DECODED_FILES`) : `classes.json` (9 classes, Mage compris), `races.json` (races jouables, classes
    permises, raciaux), `pvp_items.json` (bijoux PvP) ;
  - non décodés (`INHERITED_FILES`) : `pvp_rules.json` (règles de rendements décroissants, table mécanique →
    catégorie, types d'aura et d'effet qui classent un sort, seuils ; certitude `suppose` ou `probable` par entrée,
    source citée) ; `_seed_racials.json` (copie figée, D5) ;
  - retiré (D5) : `racials.json`. `talents.json` et `spells.json` du Mage **ne changent pas** : un test vérifie que la
    partie Mage de `classes.json` leur est identique.
- **Profil, schéma 2** : chaque champ devient `{value, source, at, client_build}` ; `read_profile` rend toujours les
  valeurs à plat (compatibilité de `forever_player_profile` et du profil de test des évaluations) et ajoute
  `fields` (source et date par champ) et `conflicts`. Un profil de schéma 1 est migré **à la lecture** (source
  `joueur`, date `updated_at`) et réécrit seulement par une commande qui écrit.
- **Aucun outil de calcul ne lit le profil** (décision 99) : les fiches prennent classe, niveau, race et talents en
  arguments ; le skill dit de lire le profil puis de les passer.
- **Registre** : nouvelle catégorie `pvp`, lettre **K**, ajoutée à `ENGINE_CATEGORIES` (la fonction de rendements
  décroissants vit dans `forever/engine/` et doit y être citée).

## Blocs et étapes

Un cycle rouge → vert par bloc (commits « PV1: tests (bloc X) » puis « PV1: bloc X vert ») ; `tasks/.rouge` et
`tasks/.tests-verrouilles` réécrits à chaque bloc. Branche `pv1`. Si le contexte se remplit, arrêt après un bloc
vert committé.

### Bloc A — Import automatique minimal du profil (sans réseau)

1. `forever/profile.py` : schéma 2, migration à la lecture, règle de fusion (`merge_field` : plus récente, puis ordre
   de D2 ; écart gardé dans `conflicts`, jamais effacé) ; `set_character` écrit la source `joueur`.
2. `forever/profile_import.py` (nouveau) : collecte → plan de changements → écriture après accord.
   - ForeverLogger (`addon_sv.read_logger_db`) : classe, race, niveau, talents du **dernier instantané** de chaque
     GUID ; talents gardés en `{nœud : rang}` (`talent_nodes`) et traduits en clés dès que l'arbre de la classe est
     décodé (bloc B) ; `validated: false` jusque-là.
   - Journaux (`combatlog.scan_logs`, `read_log`) : unités `Player-…` au drapeau « à moi », nom, royaume, GUID ;
     classe selon D2 ; date = dernier événement vu.
   - Questie : quêtes faites (D1), par GUID. Auctionator : prix par royaume (D1), `forever/pipeline/cbor.py`.
   - **Version du client** de chaque instantané et de chaque session : `client_builds.version_at` (T08a) ; inconnue →
     `null` et une note, jamais la version installée par défaut.
   - Personnage prévu retrouvé (même nom, même royaume si connu, même classe si connue) : `planned: false` ;
     classe en désaccord : signalé, rien changé.
   - Faction jamais importée (décision 99).
3. CLI : `forever profile import [--wtf <dossier>] [--logs <dossier>] [--dry-run] [--yes] [--json]` : liste des
   changements (champ, ancienne valeur, nouvelle, source, date, version du client) avant écriture ; « aucun
   changement » quand rien ne bouge. Sources absentes : signalées, pas une erreur. Dossiers par défaut sous
   `FOREVER_WOW_DIR`.
4. Fixtures : `tests/fixtures/addon/ForeverLoggerDB.lua` étendu d'un **Chasseur fictif** (nom inventé, GUID de la
   fixture de journal pour l'un des deux) ; `tests/fixtures/addon/Questie_journey.lua` et
   `tests/fixtures/addon/Auctionator.lua` synthétiques (chaîne CBOR écrite par un script de fixture, valeurs
   inventées, signalées comme telles dans `README.md`).
5. Essai réel après le vert (hors tests, sur ton poste) : `forever profile import --dry-run` sur tes trois
   personnages ; résultat résumé sans nom de tiers.

Tests (`tests/unit/test_profile_import.py`, `tests/unit/test_cbor.py`) :
- `test_import_creates_two_characters_of_different_classes` : classe, race, niveau, talents, source et date par champ.
- `test_second_import_writes_nothing` ; `test_older_value_never_replaces_newer` ;
  `test_equal_dates_follow_source_order` ; `test_disagreement_is_reported_not_erased`.
- `test_planned_character_found_in_log_becomes_created` ; `test_planned_class_conflict_is_reported`.
- `test_faction_is_never_imported` ; `test_client_build_attached_per_snapshot_and_session` ;
  `test_unknown_build_is_null_not_installed_version`.
- `test_class_from_logger_else_from_class_spells_probable` ; `test_mixed_class_spells_leave_class_unknown`.
- `test_questie_completed_quests_per_character` ; `test_auctionator_prices_per_realm` ;
  `test_posting_history_is_never_read`.
- `test_changes_listed_before_writing_and_consent_required` ; `test_profile_import_cli_dry_run`.
- `test_schema_1_profile_is_migrated_on_read` ; `test_cbor_decodes_maps_arrays_ints_strings` ;
  `test_cbor_rejects_truncated_input`.
- Modifié dans le commit « tests » : `tests/unit/test_profile.py` (schéma 2 au lieu de 1).

### Bloc B — Données du client des 9 classes (réseau après accord, D3)

1. **Arrêt pour accord** avant `forever fetch`. Tables nouvelles, enUS sauf mention :

   | Table | Usage | Repli si absente |
   | --- | --- | --- |
   | `SpellRange` | portée (min, max) par `RangeIndex` | portée non résolue, listée |
   | `SpellCategories` | type de dissipation de l'aura, mécanique, catégorie de recharge globale | `EffectMechanic` seul |
   | `SpellCategory` | recharges partagées par catégorie | recharge partagée signalée inconnue |
   | `SpellMechanic` | noms des mécaniques du client | identifiants seuls |
   | `SpellDispelType` | noms des types de dissipation | identifiants seuls |
   | `SpellInterrupts` | drapeaux de rupture des auras (dégâts, mouvement…) | ruptures non résolues |
   | `SpellClassOptions` | famille de classe d'un sort (sorts hors lignes de compétence) | lignes de compétence seules |
   | `SpellAuraRestrictions` | conditions d'emploi (camouflage…) | condition non résolue |
   | `SpellShapeshift` | posture ou forme exigée | condition non résolue |
   | `ChrRaces` (enUS et frFR) | races, faction, jouable | aucun : arrêt, raciaux non décodés |
   | `CharBaseInfo` | combinaisons race et classe permises | `SkillRaceClassInfo` |
   | `SkillRaceClassInfo` | lignes de compétence raciales par race et classe | `SkillLineAbility.RaceMasks_*` |
   | `Item` | type d'emplacement (bijou) | aucun : bijoux non décodés |
   | `ItemSparse` | nom et niveau des bijoux (lecture ciblée) | `Item` seul, noms absents |
   | `ItemEffect` | sort d'utilisation, recharge, catégorie de recharge | aucun : bijoux non décodés |
   | `ItemXItemEffect` | lien objet → effet | `ItemEffect.ParentItemID` s'il existe |

   Soit 17 téléchargements au plus. Un test (`test_fetch_list_is_the_approved_one`) fige cette liste dans
   `decode_rules.json` : toute table ajoutée plus tard fait échouer le test.
2. `decode_rules.json` par classe : section `classes.<Classe>` (lignes de compétence dans l'ordre des onglets, lignes
   des familiers pour le Démoniste et le Chasseur, arbre de traits de `SkillLineXTraitTree`) ; géométrie commune ;
   règle des nœuds hors grille : zéro en trop corrigé (règle existante), **tout autre écart listé non résolu**, jamais
   arrondi ; arbre d'un onglet = ligne de compétence majoritaire des sorts de ses talents, désaccord listé.
3. `forever/pipeline/decode.py` : `decode_classes`, `decode_races`, `decode_pvp_items` ; `node_id` pour chaque
   talent ; sorts suivis par leurs déclencheurs (pièges, sorts à effet déclenché) sur un niveau ; durée PvP lue quand
   `PvPDurationIndex` est non nul ; colonnes ajoutées à `forever/pipeline/tables.py`.
4. **Classement** de chaque sort, par les champs du client et la table de `pvp_rules.json` : contrôle (mécanique,
   type d'aura, durée pleine, durée PvP, ruptures, catégorie de rendement décroissant du bloc C), défensif ou
   immunité, rupture de contrôle, interruption (et durée de verrouillage), dissipation (types), mobilité, burst
   (recharge offensive : types d'aura et seuil de recharge dans les données). Certitude : champ du client
   `certain` (`FC-70124`), classement par la table `probable`, catégorie de rendement `suppose`. Un sort sans
   classement possible va dans `unresolved` (raison), jamais deviné.
5. Raciaux (décision 106) : sorts des lignes raciales, par race et par classe permise, avec effet, recharge et
   durée ; les combinaisons nouvelles de Forever viennent de `CharBaseInfo`, sans comparaison à une liste de Classic.
   `_racials()` du moteur relit `races.json` (mêmes trois grandeurs) ; le mode seed lit `_seed_racials.json`.
6. Bijoux PvP : bijoux dont le sort d'utilisation rompt un contrôle (effet de dissipation par mécanique, ou immunité
   de mécanique), avec recharge et catégorie de recharge ; recharge partagée avec un racial : **non décidée par le
   client**, signalée (registre K4, question ouverte).
7. `forever/gamedata.py` : `GameData.classes` ; `forever/profile.py` : races et talents validés pour les 9 classes
   (`validated: true` quand le build est légal, bloc E).
8. Installation : `forever decode` → `forever verify` → `forever diff` (rapport :
   `docs/research/data-1.60.1.70124-r2.md`) → `forever install` (révision 2) → `forever manifest --update`. Le retrait
   de `racials.json` apparaît dans le diff, justifié dans le rapport (D5).
9. Contrôles de non-régression : parité du seed (`tests/parity/`) verte sans valeur attendue changée ;
   `scripts/replay_builds.py` identique au rejeu de T08a ; sinon arrêt (D5).
10. Fixtures : `scripts/extract_wago_fixtures.py` étendu (nouvelle version de fixture `tests/fixtures/wago/1.60.1.70124/`,
    fermeture transitive décrite dans le script) : pour chaque classe quelques sorts de contrôle, un défensif, une
    interruption, une dissipation, les trois nœuds hors grille, les raciaux de deux races dont une combinaison
    nouvelle, un bijou PvP ; leurres gardés (sort homonyme de PNJ, objet non bijou).

Tests (`tests/unit/test_decode_classes.py`, `test_decode_races.py`, `test_decode_pvp_items.py`) :
- `test_nine_classes_have_three_named_trees` ; `test_every_talent_has_a_node_id` ;
  `test_mage_part_matches_talents_and_spells_json`.
- `test_extra_zero_node_is_placed` ; `test_off_grid_nodes_are_listed_unresolved` (Paladin, Prêtre).
- `test_class_spells_have_ranks_cooldown_duration_school_range` ; `test_pvp_duration_read_when_present` ;
  `test_trigger_spell_is_followed_once` ; `test_pet_spells_belong_to_their_class`.
- `test_every_spell_is_classified_or_unresolved` ; `test_classification_certainty_per_field` ;
  `test_unresolved_spells_listed_in_report`.
- `test_races_and_allowed_classes_from_client` ; `test_racials_have_effect_cooldown_duration` ;
  `test_engine_racials_read_from_races_json` ; `test_seed_mode_reads_frozen_racials`.
- `test_pvp_trinkets_have_use_spell_and_cooldown` ; `test_non_trinket_decoy_is_ignored`.
- `test_game_data_exposes_nine_classes` (`tests/unit/test_gamedata.py`).
- `test_fetch_list_is_the_approved_one` (`tests/unit/test_fetch.py`).
- Comptes mis à jour dans le commit « tests » : `test_data_import.py` (ensemble exact : `classes.json`,
  `races.json`, `pvp_items.json`, `pvp_rules.json`, `_seed_racials.json` ajoutés, `racials.json` retiré),
  `test_manifest.py`, `test_decode_version.py` ; `DECODED_FILES`, `INHERITED_FILES`, `sources.json`.

### Bloc C — Rendements décroissants (règles de Classic, `suppose`)

1. Source : recherche du sous-agent après accord (D3), adresses dans `sources.json`.
2. `pvp_rules.json` : catégories, fenêtre de remise à zéro, paliers de durée, immunité après le dernier palier,
   table mécanique du client → catégorie ; chaque entrée `suppose` avec la source ; aucun chiffre ailleurs.
3. `forever/engine/diminishing.py` (fonction pure, « Registre : K1 ») : `effective_durations(rules, applications)`
   où chaque application porte l'instant, la catégorie et la durée de base (durée PvP du client si présente, sinon
   durée pleine ; « Registre : K3 ») ; rend durée effective, palier, immunité.
4. Protocole de mesure pour PV2 : `docs/research/pvp-dr-protocole.md` (ce qu'il faut relever dans tes journaux de
   champs de bataille : pose et retrait d'aura sur un joueur, même catégorie, écart entre applications, ruptures à
   écarter, `n` minimal pris dans `tolerance.n_min` du registre).
5. Registre : K1 (rendements décroissants), K2 (classement des sorts depuis le client), K3 (durée des contrôles en
   PvP), K4 (recharge partagée bijou PvP et racial, `absent`) ; G1 (raciaux) : source `races.json`, note mise à jour.

Tests (`tests/unit/test_diminishing.py`) — valeurs lues dans `pvp_rules.json`, jamais écrites dans le test :
- `test_first_application_has_full_duration` ; `test_successive_applications_follow_the_data_steps` ;
  `test_window_resets_after_the_data_window` ; `test_categories_are_independent` ;
  `test_immune_after_the_last_step` ; `test_pvp_duration_is_the_base_when_present` ;
  `test_rules_are_suppose_with_a_source` ; `test_unmapped_mechanic_has_no_category`.
- Chaque test vérifié rouge quand la règle est ignorée (piège « avant de verrouiller »).
- `test_registry.py` dans le commit « tests » : total 112, 40 testées ou mieux (K1, K2, K3 `teste`, K4 `absent`),
  sortie de `main` ; `ENGINE_CATEGORIES` avec K.

### Bloc D — Fiches par affrontement

1. `forever/pvp.py` (service, aucun calcul de combat) :
   - `class_sheet(gd, cls, level=None, talents=None)` : contrôles (catégorie, durée pleine et PvP, portée, recharge,
     ruptures, condition d'emploi), défensifs et immunités (recharge, durée), interruptions et verrouillage,
     dissipations, mobilité, burst (recharges offensives), raciaux possibles pour la classe, bijou PvP ;
   - `matchup(gd, mine, opponent)` où `mine` = classe, niveau, race, talents passés en arguments : menaces adverses
     (burst, contrôles, défensifs et leurs recharges), mes réponses (ruptures de contrôle, bijou, raciaux, mes
     interruptions contre ses sorts à incantation, mes dissipations contre ses auras selon leur type), ses réponses à
     mes contrôles, fenêtres à surveiller (recharges longues adverses), et `missing` : ce qui manque (talents
     adverses inconnus → sorts de talent marqués « si talent », catégorie non résolue, portée absente…).
   - Chaque valeur porte son chemin dans les données (`from`), sa certitude et la provenance ; **aucune valeur
     inventée** : absente → `null` et une ligne dans `missing`.
2. CLI : `forever pvp class <classe> [--level N] [--json]`, `forever pvp matchup <ma classe> <classe adverse>
   [--level N] [--race R] [--talents k=r,…] [--opponent-level N] [--json]`.
3. MCP : `forever_lookup(kind="pvp", class=…, opponent=…, level=…, race=…, talents=…, page=…, detail=false)` —
   compact et paginé ; `UnsupportedKindError` liste `pvp`.

Tests (`tests/unit/test_pvp_sheets.py`, `test_pvp_cli.py`, `test_lookup_pvp.py`) :
- `test_matchup_is_deterministic` pour deux paires fixées : Mage contre Démoniste, Voleur contre Paladin.
- `test_every_value_traces_to_the_data` (chaque nombre retrouvé à son chemin `from`).
- `test_missing_values_are_flagged_not_invented` ; `test_talent_spells_marked_conditional_without_talents`.
- `test_provenance_and_certainty_per_field` ; `test_sheet_never_reads_the_profile`.
- `test_rogue_controls_listed_with_category` ; `test_paladin_defensive_cooldowns_listed` ;
  `test_warlock_pet_abilities_in_the_sheet`.
- `test_pvp_class_cli` ; `test_pvp_matchup_cli_json` ; `test_lookup_pvp_kind` (module qui importe `mcp`) ;
  `test_unsupported_kind_lists_pvp`.

### Bloc E — Légalité des builds de toutes les classes

1. `forever/engine/talents.py` : `check_class_build(knowledge, rules, points, level)` (points par palier,
   prérequis, rangs maximaux, points disponibles au niveau ; règles lues dans les données, « Registre : G3 ») ;
   `check_build` du Mage inchangé et égal au nouveau contrôle sur le Mage.
2. Consultation : `forever_lookup(kind="talent", class=…, name=…)` pour les 9 classes (défaut : Mage) ;
   contrôle : `forever_lookup(kind="build_check", class=…, level=…, talents=…)` et CLI
   `forever talents check --class <classe> --level N k=r …` : légal ou liste des erreurs, description des talents du
   client.
3. Profil : talents traduits et validés pour les 9 classes (`validated: true` si légal, erreurs listées sinon).

Tests (`tests/unit/test_class_build_legality.py`, `test_lookup_talent.py` étendu) :
- `test_rejects_tier_overflow_other_class` ; `test_rejects_missing_prerequisite` ;
  `test_rejects_more_points_than_the_level_allows` ; `test_accepts_a_legal_community_build` (fixture
  `tests/fixtures/community/`) ; `test_mage_check_is_unchanged`.
- `test_lookup_talent_of_another_class` ; `test_build_check_kind` ; `test_talents_check_cli`.
- `test_profile_import_validates_hunter_talents`.

### Bloc F — Plugin

1. `plugin/skills/forever-pvp/SKILL.md` (moins de 200 lignes, aucun chiffre) : savoir des classes et fiches ; lire
   le profil pour « mon Mage », passer classe, niveau, race et talents à `forever_lookup(kind="pvp")` ; citer
   certitude et `missing` ; rappel des limites (bloc G).
2. `plugin/skills/forever-builds/SKILL.md` (D4) : builds calculés (Mage, `forever_build`) ou de la communauté
   vérifiés (`forever-web-researcher` puis `build_check`).
3. `forever-router/SKILL.md` :
   - carte des domaines : lignes PvP (savoir, fiches) et builds de toutes les classes ; lignes « PvP : classes
     adverses… » et « Profil rempli automatiquement » retirées de la table des domaines non couverts ;
   - consigne **« donnée manquante »** (décision 131) : proposer un addon qui la comblerait, recherche par
     `forever-web-researcher` (CurseForge, Wago, liste de foreverchanges.pro), rien téléchargé ni installé ;
   - consigne **« pas encore construit »** (décision 130) : objets, réputations, PvP de champ de bataille : source
     citée si elle existe, sinon la tranche ;
   - classe pas encore calculée : la légalité et les effets **sont** désormais vérifiés par `build_check` ;
   - proposition de `forever profile import` quand le profil est vide ou daté.
4. `docs/ARCHITECTURE.md` : section « Outils et skills prévus » (PvP et builds passés de prévu à fait, formes
   définitives), mémoire joueur (schéma 2, fusion), comptes d'évaluation.
5. Évaluations : `pvp-controles-voleur` (« quels sont les contrôles d'un Voleur ? »), `pvp-mage-contre-demoniste`
   (« comment jouer contre un Démoniste avec mon Mage ? », profil de test), `pvp-defensif-paladin` (« quel temps de
   recharge défensif a un Paladin ? »), voisin `neg-retail-pvp-voleur` ; outil attendu `forever_lookup`, juges
   certitude, provenance, chiffres, `missing` cité ; `generale-classe-non-calculee` : juge mis à jour (légalité
   vérifiée). 62 cas, 41 positifs, 21 voisins.
6. Plugin 0.5.0, empreinte (`scripts/plugin_fingerprint.py`), `validate --strict`.

Tests : `test_plugin_structure.py` (`SKILLS` avec `forever-pvp` et `forever-builds`, lignes du routeur, aucune
valeur de jeu), `test_plugin_evals.py` (comptes), `test_plugin_version.py` ;
`test_router_missing_data_and_not_built_instructions` ; `test_router_uncovered_table_drops_pv1_rows`.

### Bloc G — Rappel des limites

1. `forever-pvp/SKILL.md`, `docs/ADDON.md` et la sortie texte de `forever pvp` : aucun suivi en direct des recharges
   adverses dans un addon sur Forever (journal de combat refusé aux addons, valeurs de combat secrètes,
   `docs/research/addon-forever.md`) ; seules des fiches fixes, affichées en jeu par FA1p.
2. Aucune ligne d'addon ajoutée ; `scripts/check_addon.py` inchangé.

Tests : `test_pvp_skill_states_no_live_cooldown_tracking` ; `test_pvp_cli_prints_the_limit`.

## Fin de tranche

- `docs/ROADMAP.md` (PV1 fait, date ; T07 sans Questie ni Auctionator), `docs/DECISIONS.md` (réponses D1 à D5),
  `docs/USAGE.md` (commandes), `docs/DATA_SOURCES.md` (tables ajoutées), `docs/OPEN_QUESTIONS.md`.
- `/verifier`, relecture (`relecteur`), audit (`auditeur-mecaniques`), CI verte Ubuntu et Windows, fusion en
  avance rapide, branche supprimée.

## Hors périmètre

Dégâts et soins des autres classes ; simulation de duel ; résistances des joueurs ; profil PvP du Mage avec
rendements décroissants et bijou (PV2 si D4 accepté) ; mesures sur journaux (PV2) ; analyse de mes combats (AN1) ;
équipement, métiers, réputations, historique du profil (T07) ; toute détection d'événement de combat dans un addon ;
affichage des fiches en jeu (FA1p).

## Risques

- Noms de tables non vérifiés hors réseau (D3) ; une table absente ne déclenche aucun autre appel.
- Nœuds hors grille (Paladin, Prêtre) : un placement deviné fausserait paliers et légalité ; listés non résolus.
- Catégories de rendements décroissants absentes du client : table `suppose` ; un contrôle Forever sans équivalent
  Classic reste non résolu.
- Sorts de familier (Démoniste, Chasseur) hors des lignes de classe : sans règle, les fiches omettraient des
  contrôles majeurs ; test dédié.
- Raciaux décodés différents du relevé communautaire : peut changer le Mage (D5, arrêt).
- Migration du profil de schéma 1 : le profil de test des évaluations (`tests/fixtures/plugin_eval/profile-rempli.json`)
  doit rester lisible.
- `ItemSparse` volumineux : lecture ciblée des bijoux, fixture réduite.
- Tranche longue : contexte ; arrêt propre après un bloc vert.

## Angles morts attendus (à chiffrer en fin de tranche)

Talents qui modifient la durée ou la recharge d'un contrôle (appliqués seulement si les talents sont donnés) ;
résistance et toucher des contrôles ; postures et formes ; ressources (rage, énergie, points de combo) ; recharges
partagées non décrites par le client ; champ `level` du journal pour un joueur (non utilisé).
