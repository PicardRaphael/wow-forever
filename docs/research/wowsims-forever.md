# Simulateurs wowsims Forever et MythicSim : étude (SIM1)

Étude en lecture seule du 2026-10-09, documentation seulement (décision 224). Dépôts lus sur GitHub en anonyme, avec l'accord de l'utilisateur du même jour : pages, `raw.githubusercontent.com` et une vingtaine de requêtes à `api.github.com`. Rien n'a été cloné, téléchargé, compilé ni exécuté, aucun compte n'a servi, et rien n'a été lu sur mythicsim.com. La page CurseForge de l'addon MythicSim a été lue. L'addon SimulationCraft a été lu sur disque dans `Interface/AddOns`, sans être modifié.

Tout ce qui vient de ces dépôts est une **source communautaire** : au mieux `suppose` (hiérarchie de `docs/DATA_SOURCES.md`), daté au commit lu. Une valeur citée ici sert à orienter un test et n'entre jamais dans `forever/data/`. **[lu]** : vu dans le fichier cité ; **[déduit]** : interprétation.

## Résumé

- **Moteurs utilisables** :
  - **ElliotWood/Forever** (Go, MIT) est le moteur communautaire de référence. Ses données sont au build **1.60.1.70291**, le même que les nôtres, et il publie chaque semaine un `wowsimcli` compilé pour Windows.
  - **MythicSim** fait tourner une variante de ce moteur : les branches `mythicsim/*` du fork Go, au build 1.60.1.70235. Il prépare un moteur Rust qui reproduit le Go à l'identique sur plus de 24 000 demandes.
- **Limite décisive : le joueur est toujours de niveau 60.**
  - Aucun de ces moteurs n'accepte un personnage plus bas. Une cible de bas niveau reçoit les tables d'attaque d'un boss.
  - Ils ne servent donc **ni au leveling, ni au temps par monstre, ni à MAG19 au niveau 20**. Ils servent au raid et au donjon de niveau 60, aux poids des statistiques et aux comparaisons d'objets à 60.
- **Format de la demande** : `RaidSimRequest` en JSON (protojson), passé à `wowsimcli sim --infile`. Notre pont peut construire cette demande lui-même. Il n'a pas besoin du JSON de `/msim`, dont le schéma n'est pas public et que MythicSim convertit dans un service privé.
  - Il faut deux ajouts : le **lien d'objet complet** (enchantement, suffixe aléatoire) dans le contexte envoyé par l'addon, et une **table de correspondance des talents** vers l'ordre de leurs arbres.
- **Règles de Forever** : sur toucher et critique uniques, expertise et critiques des DoT, ils lisent les mêmes tables et les mêmes attributs du client que nous. Ils comblent deux trous de nos données : la conversion des notations en pourcentage, et l'expertise. Ils contredisent ou font douter sur deux points :
  - le **tiers des soins en dégâts**, notre F7 : abandonné chez ElliotWood, au profit des statistiques des objets du client ;
  - le **moment du tirage du critique d'un DoT** : au tic chez eux, figé à la pose selon leur propre document.
- **MON7** (PV par famille de monstres) : hors de leur périmètre. Leur cible est un boss de raid fixe, sans famille.
- **Proposition** : tranche **SIM1** du 21 octobre au 4 novembre, après DJ1 et avant T10a.
  - Contenu : adaptateur local de `wowsimcli`, boutons « Simuler » et « Est-ce une amélioration ? » au niveau 60, contrôle croisé de notre moteur du Mage en raid.
  - Ce qui demande le jeu passe dans P06b avant le 21 octobre : lien d'objet complet dans le contexte, Maj+clic.
  - Télécharger le binaire et ajouter la dépendance restent soumis à l'accord de l'utilisateur au moment du plan.

## 1. Dépôts et lancement en local

### Vue d'ensemble

| Dépôt | Commit lu (date) | Langage, licence | Build visé | État |
| --- | --- | --- | --- | --- |
| [wowsims/classic](https://github.com/wowsims/classic) | `7779ebb` (2026-07-24) | Go, MIT | aucun (Classic, restes de Season of Discovery) | amont peu actif |
| [ElliotWood/Forever](https://github.com/ElliotWood/Forever) | `0dbbe2d` (2026-10-09) | Go, MIT, fork de wowsims/classic | **1.60.1.70291** (`assets/db_inputs/forever_client_build.txt`) | très actif, publication hebdomadaire |
| [sage3648/mythicsim-forever-engine-go](https://github.com/sage3648/mythicsim-forever-engine-go), branche `master` | `51da185` (2026-10-01) | Go, MIT, fork d'ElliotWood | 1.60.1.69977 | ancienne structure Classic, pas le moteur de production |
| même dépôt, branches `mythicsim/*` | `6683724` (2026-10-08) ; référence du Rust `2d93e42` | Go, MIT | **1.60.1.70235** | moteur de MythicSim ; la branche `data/master/forever-client` passe à 70291 le 2026-10-09 |
| [sage3648/mythicsim-forever-engine](https://github.com/sage3648/mythicsim-forever-engine) | `e346c5e` (2026-10-08) | **Rust**, MIT | 1.60.1.70235 (`data/manifest.json`) | expérimental ; la production tourne encore en Go |
| [gunba/wow-forever-sim](https://github.com/gunba/wow-forever-sim) (pour mémoire) | `9c05fc8` (2026-10-09) | Go, MIT | 1.60.1.69913 (fichier peut-être non tenu) | benchmark reproductible de niveau 60 |

**[lu]** La phrase « construit sur 1.60.1.70235 » du fork Go n'est vraie que pour ses branches `mythicsim/*`. Son README demande de partir de la branche `mythicsim/*` la plus récente. Au commit de référence, les fichiers des règles (`forever_rules.go`, `base_stats_auto_gen.go`, `maps.go`) sont identiques octet pour octet à ceux d'ElliotWood. **[déduit]** MythicSim suit donc ElliotWood avec un léger retard de build.

**[lu]** ElliotWood n'a plus la structure de wowsims/classic : son module Go s'appelle `github.com/wowsims/forever`. Ses données viennent :
- du client local, lu par CASC ou par le CDN, avec `DBCache.bin` ;
- de wago.tools et du gear planner de Wowhead ;
- de constantes posées à la main dans `sim/<classe>`.

Son document `docs/DATA_SOURCES.md` signale que les statistiques des objets sont masquées dans le client : elles viennent alors de Wowhead.

### Lancer `wowsimcli`

| | ElliotWood/Forever (recommandé) | MythicSim Go (`mythicsim/*`) | MythicSim Rust |
| --- | --- | --- | --- |
| Prérequis pour compiler | Go 1.25 (`go.mod`), `protoc` et `protoc-gen-go`, `buf` ; Node 22 seulement pour l'interface ; `make` à installer sous Windows | comme ElliotWood | Rust stable (`rust-toolchain.toml`), Python 3 pour `tools/route.py` |
| Binaire Windows déjà compilé | **oui** : `wowsimcli-windows.exe.zip` (6,39 Mo, v0.0.2 du 2026-10-05 ; publication le lundi, `scheduled_release.yml`) ; la v0.0.2 précède le passage des données à 70291 **[déduit]** | aucune publication | aucune publication (paquets `bundle-<sha>` internes) |
| Commande | `wowsimcli sim --infile demande.json [--outfile r.json] [--verbose]` (`cmd/wowsimcli/cmd/basic_sim.go`) ; aussi `version`, `decode-link` ; plus de `bulk` | même CLI | `forever-engine sim --infile|--request …`, `prepare`, `check`, `bench`, `version` |
| Entrée | `RaidSimRequest` en protojson : `raid.parties[].players[]` (race, classe, `equipment.items[{id, enchant, randomSuffix, gems}]`, consommables, `talentsString`, rotation APL, `oneof` de spécialisation), `encounter` (durée, variation, cibles `{level, mobType…}`, `useHealth`), `simOptions` (`iterations`, `randomSeed`), obligatoire | même message | même JSON, lu strictement (champ inconnu = erreur) |
| Sortie | `RaidSimResult` en protojson : `raidMetrics…dps` (moyenne, écart type, min, max, histogramme), métriques par joueur et par sort, `iterationsDone` | même | « le même JSON que le Go » |
| Poids, meilleur équipement | seulement par le serveur HTTP `wowsimforever` (`/statWeights`, `/bulkSimAsync`, `/reforgeOptimizeAsync`, corps en protobuf binaire), pas par la CLI | id. | par lots de demandes (`route.py --batch`) |
| Exemple de demande | aucun dans le dépôt | — | 2 728 `*.request.json` dans `tests/` et `fixtures/` |

**[lu]** Les messages évoluent sans migration. La documentation d'ElliotWood dit : « Nothing migrates an input file: export the settings from the UI again after a proto change ». Le Go lit le JSON en ignorant les champs inconnus (`DiscardUnknown`). Une demande construite pour une autre version perd donc des champs **sans erreur**.

**Temps d'une simulation** (seul chiffre publié, `benchmarks/2026-10-04-production-builds.json` du dépôt Rust, Apple M2 Max, un seul fil d'exécution) : de 0,66 à 2,63 s pour 10 000 itérations en Go, médiane 1,9 s, et environ 1,5 fois plus vite en Rust. Sous Windows, sur la machine de l'utilisateur : **à mesurer en SIM1**. Le classement de MythicSim et l'arène d'ElliotWood tournent à 5 000 itérations par build.

**[lu]** Le README du fork Go confirme l'architecture de MythicSim : site, API interne, worker qui lance `wowsimcli` comme processus séparé. Le code du worker et de l'API (`worker/forever/talents.go`, `request.go`, `export.go`) n'est pas public.

## 2. Couverture

- **Classes et spécialisations** (`sim/register_all.go` d'ElliotWood, 20 enregistrements) : les 9 classes. Druide Équilibre, Farouche félin et ours, Restauration ; Chasseur ; Mage ; Paladin Sacré, Protection, Vindicte ; Prêtre DPS et soigneur ; Voleur ; Chaman Élémentaire, Amélioration, Restauration ; Démoniste ; Guerrier DPS et Protection. Le moteur Rust annonce 29 builds de production sur les 9 classes, dont Arcane, Feu, Givre et Givre-feu pour le Mage. L'addon MythicSim déclare les spécialisations de soin non simulables.
- **Ce qu'ils simulent** :
  - dégâts par seconde sur une rencontre de raid ou de donjon de niveau 60 (une ou plusieurs copies du boss, durée et variation, phase d'exécution) ;
  - poids des statistiques et meilleur équipement par lots de simulations (serveur HTTP ou lots) ;
  - menace et mitigation des tanks, soins (selon la spécialisation).
- **Ce qu'ils ne simulent pas [lu, absence de champ ou constante]** :
  - **le leveling** ;
  - **un joueur sous le niveau 60** : `const CharacterLevel = 60` imposé au joueur (`sim/core/constants.go`, `character.go`) ; même constante en Rust ;
  - **le temps pour tuer un monstre de bas niveau** : `Target.level` est accepté, mais `UnitLevelFloat64` (`sim/core/utils.go`) ne connaît que les niveaux 58, 60, 61 et 62, et donne à tout autre niveau les tables d'un boss de niveau 63 ;
  - **la mana entre les combats** : seuls le temps avant panne de mana et la mana en fin de combat sont mesurés, sans repos ni boisson.

## 3. Règles de Forever face à notre registre

Leur document des règles : `docs/forever_rules.md` d'ElliotWood, « Forever rule changes modelled in this fork ».
- **Structure** : une ligne par règle, sur 173 lignes dont 64 lignes de tableau. Trois colonnes : règle, source, endroit du code. Sections par classe, une section Racials et une section Encounters.
- **Sources** : infobulles, arbres, panneau du personnage, guide des raciaux, valeurs *demo* tirées des infobulles de la BlizzCon 2026, souvent au rang 1, et un journal de bêta foreverlogs.gg du 2026-09-25.
- **Date** : aucune en tête.
- **Retard sur le code [lu]** : le document parle encore d'un `SimOptions.ruleset` et de `sim/core/ruleset.go`. Or ElliotWood n'a plus d'enum `Ruleset` : ce moteur ne connaît que Forever. Le `master` du fork Go garde, lui, un enum `RulesetClassic`/`RulesetForever`.

| Règle | Leur modèle (ElliotWood `0dbbe2d`, repris par MythicSim et le Rust) | Nos données et notre registre (1.60.1.70291) | Verdict |
| --- | --- | --- | --- |
| Toucher et critique uniques | `UnifyGearHitAndCrit` (`sim/core/forever_rules.go`) : toucher et critique des objets, en mêlée comme en sorts, additionnés puis versés dans toutes les réserves ; le toucher de mêlée et le toucher des sorts égaux d'un même objet sont dédoublonnés à l'import. Conversion lue dans le client (`CombatRatings.txt`, `base_stats_auto_gen.go`), **constante à tous les niveaux**. Source : panneau du personnage. | A4 (`teste`, `certain` sur la forme) et A5 (`probable`) : un seul toucher et un seul critique d'équipement, en fractions (`engine/hit.py`, `engine/character.py`). **Conversion notation → % absente** : `leveling.json` laisse la critique et le toucher à `null` ; `audit-mises-a-jour.md` note la même table constante, jugée « probablement inerte ». | **Confirmé** sur la forme. Leur lecture du client comble notre trou de conversion : question PER8. |
| Expertise | Statistique `ExpertiseRating` convertie en pourcentage (même table du client) ; réduit esquive et parade sans arrondi au quart de point (`spell_result.go`, `spell_outcome.go`). Leur document n'en parle pas. Sources : bonus de tier 1 et flacon d'Hyjal (commentaire de `proto/common.proto`). | A7 et A8 `absent` ; seul le talent Weapon Expertise du Voleur dans `classes.json`. | **Non couvert chez nous.** Rien ne contredit leur modèle. À reprendre dans GU1 et VO1. |
| Soins qui donnent de la puissance des sorts | Le `master` du fork Go applique un tiers du bonus de soins en dégâts (`ForeverHealingToSpellDamage`, source : Hide of the Wild). **ElliotWood l'a retiré** : la statistique 45 du client (« Spell Power ») vaut pour les dégâts et les soins, la 41 pour les soins seuls (`tools/database/dbc/maps.go`, exemple Atiesh). | F7 « Bonus de soins : un tiers en dégâts », `absent`, certitude `certain`, sans source ni test ; seulement `healOnly / 3` dans `seed/grimoire-engine/engine.js`. | **Contredit en partie** : la certitude de F7 n'a pas de source et le moteur le plus à jour a abandonné ce ratio. Question PER9. |
| Critiques des DoT | Sort par sort, d'après l'attribut du client `ATTR_EX_8_PERIODIC_CAN_CRIT` (225 sorts dans leur build) ; critique tirée **au tic**, avec la chance du moment, et toucher tiré une seule fois. Multiplicateur de critique des sorts distinct du physique. Ignite ne critique jamais. Leur document dit « snapshot crit chance », leur code tire au tic. | A17 `teste`, `probable` ; `leveling.json` `dot_can_crit` vaut vrai pour tous les DoT (`suppose`). MAG6 a relevé le même bit `Attributes_8` (Fireball, Pyroblast, Frostfire Bolt oui ; Flamestrike, Ignite non) sans l'appliquer. | **Confirmé** pour la règle par sort. Ce n'est pas une preuve indépendante : ils lisent le même attribut. Le tirage au tic reste à mesurer (MAG5, MAG6). |
| Raciaux propres à Forever | `sim/core/racials.go` : raciaux d'arme à +1 % de critique, résistances retirées, Big Game Hunter, Shatter Curse, Expansive Mind, Eureka!, Elune's Light, Touch of the Grave, raciaux Skyborne. Valeurs *demo* ou guide des raciaux, numéros de sort du client. **ElliotWood et le `master` du fork Go divergent** (Eureka!, Blood Fury, Berserking). | G1 `teste`, `certain` : `races.json` décodé du client pour les 10 races ; seuls les passifs Humain et Gnome entrent dans le moteur du Mage, les raciaux actifs ne sont pas modélisés. | **Confirmé** : mêmes sorts du client. Leurs valeurs *demo* sont moins sûres que nos décodages ; à recouper dans les tranches de classe. |
| Paliers de talents | 7 rangées, 5 points par rangée, prérequis au rang maximal, 51 points au niveau 60 (`ui/features/talents/model/can_set_points.ts`) ; aucune marque de talent « doré ». | G3 `teste`, `certain` : premier point au niveau 10, 5 points par palier (`character_scaling.json`, `NumTalentsAtLevel` et `TraitCond`), Voleur encore `null` ; 7 paliers dans `classes.json`. Les 11e, 16e, 21e et 31e points sont les premiers points des paliers 3, 4, 5 et 7, mais le 26e (palier 6) manque à la liste : elle désigne donc des talents particuliers, pas la règle des paliers. | **Règle des 5 points cohérente** ; **talents particuliers à 11, 16, 21 et 31 points non identifiés** : aucun drapeau de nœud chez eux ni dans `classes.json` (le « 4e talent doré à 16 points » de `theorycraft-plan-app.md` n'a pas de source lue). Piste : un drapeau ou un type de nœud dans `TraitNode` du client (angle mort de G3). |
| Format des arbres | `talentsString` : un chiffre par talent dans l'ordre de leur fichier d'arbre, arbres séparés par `-`. L'interface d'ElliotWood **ignore les talents importés de l'addon** (« No exporter targets these trees yet »). | `classes.json` : nœuds `C_Traits` et sorts du client ; notre addon envoie `nœud:rang`. | Correspondance à construire par sort (comme `forever talents tf crosscheck` en FA1). |
| PV par famille de monstres (MON7) | Hors de leur périmètre : `Target` a `mobType` (bonus de tueur de bêtes et autres) mais aucun multiplicateur de PV ; la cible type est un boss de niveau 63. | MON7 ouverte ; ours et Sunscale Lashtail écartés de la courbe comme hors norme (décision 223). | **Pas de réponse chez eux.** Le test de MON7 reste celui des journaux et de `CreatureDifficulty`. |

Autres points du Mage dans leur document :
- Improved Scorch et Winter's Chill sont personnels.
- Ignite paie exactement 40 % du critique et cumule le reste dû sans redémarrer, ce qui touche notre MAG10.
- Heating Up, l'ancien Hot Streak, réduit l'incantation de Pyroblast par cumul, d'après la ligne du client.
- Rien sur Arcane Blast, la hâte ni la régénération de mana.

## 4. Exports de personnage

### L'addon MythicSim (« Forever Sim Exporter »)

D'après CurseForge, 0.3.0 est la dernière version, mise à jour le 21 septembre 2026, licence MIT. Commandes : `/msim`, `/msim export`, `/msim probe`. L'addon lit les objets équipés (enchantements, suffixes aléatoires), les talents des 9 classes, la race, la classe, le niveau et les métiers.

Son schéma n'est pas publié, et le dépôt de l'addon est introuvable sur GitHub. La page dit seulement : « same character format as the WoWSims Exporter addon, with a few extra fields ».

Base publique, [wowsims/exporter](https://github.com/wowsims/exporter) `ad9e903` [lu] :
- `version`, `unit`, `name`, `realm`, `race`, `class`, `level`, `talents` (rangs par position, `GetTalentRank`), `professions`, `spec`, `gear.items[{id, enchant, random_suffix}]` ;
- les gemmes à partir de TBC seulement.

Champs ajoutés par MythicSim, selon `docs/application-contract-inventory.md` du dépôt Rust : listes de sorts des talents (`client_spell_ids`) et objets candidats des sacs. **La conversion vers `RaidSimRequest` se fait dans leur worker privé.**

**Notre pont peut-il produire ce format ?**
- Il n'en a pas besoin : le moteur prend un `RaidSimRequest`, que le pont construira directement en Python.
- Il le pourrait pour la base WowSimsExporter. Il manque aujourd'hui deux choses au contexte envoyé (`addon/ForeverBridge/Message.lua`) :
  1. **le lien d'objet complet** : seul l'identifiant (`|Hitem:(%d+)`) est capté, pas l'enchantement (champ 2) ni le suffixe aléatoire (champ 7) ;
  2. **un équipement jamais retiré** : quand le message dépasse la bande (1 792 octets), l'allègement retire l'équipement avant les talents. Une demande « Simuler » doit porter l'équipement entier, quitte à alléger la question ou à envoyer un message dédié.
- Les talents se traduisent déjà de `nœud:rang` en clés forever (`forever/bridge/context.py`). Reste à les traduire de nos clés vers leur ordre positionnel, par sort.

### SimulationCraft (`Interface/AddOns/Simulationcraft`, lu sur disque)

- **Version et compatibilité** : version 12.1.0-alpha-06, TOC `120100, 120105, 16001` : **chargé par Forever**. Dernier commit annoncé « Experimental Forever support » (2026-10-08). Détection de Forever par `Enum.TraitConfigType.CamelotCombat` ou `C_SpecializationInfo.GetCombatConfigIDForSpecGroup`.
- **Contenu de l'export sous Forever** (texte de `/simc`, `core.lua` et `forever/stats.lua`) :
  - en-tête : nom, version du client, classe, `level=`, `race=`, `region=`, `server=`, `role=`, `professions=`, `spec=unknown` ;
  - `talents=` : chaîne d'import native du client (`C_Traits.GenerateImportString` de la configuration de combat), donc **un autre format** que les chaînes `b=` que nous savons décoder ; à décoder par les nœuds de `classes.json` ;
  - une ligne par objet équipé : `id`, `enchant_id`, `gem_id`, `bonus_id`, **mais pas le suffixe aléatoire** (`OFFSET_SUFFIX_ID` commenté) ; option : objets des sacs, objets liés par Maj+clic (`/simc [lien]`) ;
  - en commentaires, la **fiche réelle** lue par les API du jeu :
    - PV, puissances, caractéristiques totales, de base et bonus, statistiques additionnées des objets ;
    - puissance d'attaque, puissance des sorts par école, bonus de soins, pénétration ;
    - régénérations en combat et hors combat ;
    - critique par type et par école, toucher (notation et modificateur), hâte, expertise ;
    - toutes les notations non nulles, défense, résistances, dégâts d'arme ;
    - familier ;
    - compétences d'arme et métiers (`skills=`) ;
    - buffs actifs (`buffs=`).
- **Lecture sur disque** : impossible. `SimulationCraftDB` ne garde que les options (aucun fichier de sauvegarde trouvé dans `WTF`), et l'export ne s'obtient qu'en copiant le texte de la fenêtre.
- **Ce qu'il apporte** :
  - SimulationCraft lui-même ne simule pas Forever, et aucun importeur `/simc` n'existe chez wowsims ni chez MythicSim ;
  - l'export sert de **source pour notre profil**, en collage manuel : fiche lue au client (`certain` hors combat), à comparer à notre fiche estimée (`mechanics.json`, `character.spell_power` `suppose`) ;
  - c'est la meilleure source pour PER1, PER7 et la base de toucher et de critique ;
  - à terme, ForeverLogger peut lire lui-même ces mêmes API hors combat (LOG4), sans dépendre de cet addon.

## 5. Usage en jeu : « Simuler » et « Est-ce une amélioration ? »

### Ce qu'il faut

1. **Moteur local épinglé** : `wowsimcli` d'ElliotWood, binaire Windows de la publication hebdomadaire, ou compilation Go. C'est un téléchargement et une dépendance externe : **accord de l'utilisateur au plan de SIM1**. On garde dans la provenance la version, le commit, le build de jeu du moteur et l'empreinte du binaire. Si le build du moteur diffère de nos données installées, c'est signalé, et le résultat reste `suppose` dans tous les cas.
2. **Adaptateur `forever/sim/wowsims/`** (forme au plan) :
   - il construit le `RaidSimRequest` à partir du profil et du contexte en jeu : classe, race, talents traduits, objets `{id, enchant, randomSuffix}`, préréglage de rencontre, de buffs et de consommables, déclarés comme hypothèses ;
   - il lance le binaire en sous-processus, sans réseau, avec un délai maximal, et lit le `RaidSimResult` ;
   - il ne calcule aucune formule de combat : le résultat est une **source externe** citée, jamais une valeur de `forever/engine/`.
3. **Poids des statistiques** : simulations appariées (même `randomSeed`), une avec un point en plus par statistique utile, avec écart type. La CLI ne fait qu'une simulation à la fois ; le serveur HTTP en protobuf n'est pas nécessaire.
4. **« Est-ce une amélioration ? »** : l'objet passé par Maj+clic (lien complet, reçu de P06b) remplace l'objet de son emplacement. Deux simulations appariées ; réponse « gain de X ± Y DPS, significatif ou non », avec les limites. Les cas à deux emplacements (bagues, bijoux, armes) se comparent aux deux.
5. **Boutons du pont** : le pont lance lui-même la commande fixée, comme « Mettre à jour » (décision 197), et non la conversation. La conversation « jeu » ne fait que mettre en forme une réponse courte : DPS, poids, limites, provenance. Le bouton n'apparaît **que pour un personnage de niveau 60**, sinon le pont répond que le moteur ne simule que le niveau 60.
6. **Contexte d'équipement complet dans l'addon** : lien entier, équipement jamais retiré. C'est un changement de Lua à tester en jeu, donc **dans P06b, avant le 21 octobre**.

### Temps de réponse attendu

- Moteur : ordre de la seconde pour une simulation de quelques milliers d'itérations (benchmark publié, autre machine) ; quelques secondes en parallèle pour les poids (environ dix simulations) ; deux simulations pour une comparaison.
- Pont : réponse revenue en jeu en 10 à 40 s (`docs/ADDON.md`), sous le délai maximal de 180 s (`forever/bridge/agent.py`).
- **Total attendu : de 15 s à une minute environ, à mesurer en SIM1** (critère de fin).

### Dans quelle tranche

- **P06b**, avant le 21 octobre : seulement ce qui demande le jeu, c'est-à-dire le lien d'objet complet dans le contexte et le Maj+clic, déjà prévu.
- **SIM1** : le reste, adaptateur et boutons.
- **T10a** : n'en dépend pas. Ses poids restent ceux de notre moteur du Mage ; SIM1 en est le contrôle indépendant au niveau 60.

## 6. Autres usages et leurs risques

### Contrôle indépendant de notre moteur du Mage

Même personnage, même rencontre de raid de niveau 60 et même durée, résultats comparés : DPS absolu, classement des builds, poids.
- **Possible au niveau 60 seulement.** MAG19 (écart entre l'analytique et le Monte Carlo du Feu au niveau 20) **ne peut pas** se trancher par MythicSim : le test prévu dans `OPEN_QUESTIONS.md` est corrigé. En revanche, la même comparaison analytique / Monte Carlo / wowsims au niveau 60 en raid isole ce que fait Ignite (règle d'ElliotWood : 40 % exactement, reste cumulé).
- Notre `forever_build` ne prend ni équipement, ni toucher, ni hâte en entrée, seulement `sp` et `crit`. Il faudra soit un personnage nu avec des statistiques ajoutées côté wowsims (champ à vérifier au plan), soit ouvrir `hit_gear` et `haste` en entrée.
- **Risques** :
  - circularité, car ils lisent les mêmes tables du client que nous : un accord ne prouve pas le jeu, et leur README le dit (« It does not prove the live game ») ;
  - valeurs *demo* de la BlizzCon ;
  - divergences entre leurs propres forks ;
  - parité tenue en ordre de classement plutôt qu'en valeur absolue tant que la bêta bouge (`theorycraft-plan-app.md`).
- C'est l'entrée J4 du registre (« Parité avec wowsims Forever », `absent`), que SIM1 reprend à T09.

### Moteur de dégâts de fin de jeu pour les huit autres classes

- **En complément**, pas à la place. Il donne dès SIM1 un DPS de raid de niveau 60 et des poids pour les 9 classes, étiquetés `suppose` (source externe, son commit et son build).
- Les tranches de classe gardent ce que wowsims ne fait pas : leveling, donjon à bas niveau, PvP, certitude des valeurs, mesures dans les journaux.
- T09 garde le Monte Carlo et le rejeu de raid de AN2 ; savoir s'il porte encore `seed/grimoire-engine/` ou s'appuie sur wowsims se décide au plan de T09.
- **Risques** :
  - le format évolue sans migration (épingler la version, tests de contrat sur des demandes en fixtures) ;
  - les statistiques des objets viennent de Wowhead quand le client les masque ;
  - les spécialisations de soin sont peu ou pas simulées ;
  - le binaire change chaque semaine (veille à prévoir dans `forever status`).

### Poids des statistiques pour T10a

- Le contrôle indépendant des poids du Mage au niveau 60 est le seul usage sans risque de remplacement.
- T10a reste sur notre moteur (`NFSW1:`), qui couvre aussi le leveling.
- Pour les autres classes, des poids wowsims peuvent alimenter Naowh Forever avant leur tranche, avec la mention de la source.

### Ce que notre moteur garde

Le leveling, le temps par monstre et l'XP par heure, la mana et le repos, les mesures réelles des journaux, la certitude par valeur et la provenance du client.

## 7. Tranche SIM1

Proposée le 2026-10-09 (décision 224), placée dans la fenêtre sans jeu du 21 octobre au 4 novembre, **après DJ1 et avant T10a** : T04d, T04f, DJ1, **SIM1**, T10a, EX1. Elle ne dépend pas de DJ1. Elle passe après lui pour ne pas retarder le butin des donjons, utile dès le lancement, alors que SIM1 ne sert qu'aux personnages de niveau 60.

- **Dépend de** : P06a (fait), P06b (lien d'objet complet et Maj+clic), T05.
- **Condition** : accord de l'utilisateur sur la dépendance et l'accès réseau (téléchargement du binaire ou chaîne Go), donné au plan.
- **Fait** :
  1. moteur `wowsimcli` d'ElliotWood installé et épinglé, sa version dans `forever status` ;
  2. adaptateur : demande construite depuis le profil, l'export SimulationCraft collé ou le contexte en jeu ; correspondance des talents de `classes.json` vers leurs arbres, par sort ; préréglages de rencontre, de buffs et de consommables déclarés ;
  3. commande et outil MCP (par exemple `forever sim raid`, `forever sim weights`, `forever sim compare`), provenance avec la source externe ;
  4. boutons « Simuler » et « Est-ce une amélioration ? » du pont, au niveau 60 seulement ;
  5. contrôle croisé du moteur du Mage au niveau 60 (registre J4), écarts listés ;
  6. lecteur de l'export SimulationCraft collé (chaîne `talents=` du client, objets, fiche).
- **Hors périmètre** :
  - leveling et niveaux inférieurs à 60 ;
  - remplacement de notre moteur ou de T09 ;
  - poids de T10a remplacés ;
  - serveur HTTP de wowsims ;
  - toute lecture de mythicsim.com.
- **Critères de fin** (précisés au plan) :
  - demande construite et résultat lu sur des fixtures, sans réseau ni binaire dans les tests ;
  - tests de contrat sur une demande de référence par spécialisation ;
  - refus clair sous le niveau 60 ;
  - temps de réponse mesuré en bout de chaîne ;
  - `uv run tasks.py verify` vert.

## Suites décidées le 2026-10-09 (décision 225)

- **F7** passe de `certain` à `suppose`, avec renvoi à PER9 : une règle sans source ni test ne peut pas être certaine.
- **SIM1** : place confirmée, du 21 octobre au 4 novembre, après DJ1 et avant T10a. L'accord sur la dépendance et le binaire `wowsimcli` viendra au plan.
- **PER8** : le décodage de la conversion des notations en pourcentage, depuis la table `CombatRatings` du client, se fait en SIM1. C'est la première tranche qui en a besoin, pour le contrôle croisé du Mage avec un équipement réel, et un prérequis de T10a. Les paires notation et bonus de l'export SimulationCraft en donnent la preuve en jeu.
- **P06b** :
  - lit l'export SimulationCraft collé dans la fenêtre du chat (talents, objets, fiche du personnage) et propose la mise à jour du profil en signalant les écarts ;
  - garde le lien d'objet complet et l'équipement jamais retiré du message.
  - Contrainte à régler au plan : le texte dépasse la zone de saisie et probablement un message de la bande. Il faudra une zone de collage multiligne et un envoi en plusieurs messages.

### Entrées du registre encore `certain` sans source ni test (listées, non modifiées)

Relevé du registre au 2026-10-09 : 16 entrées en plus de F7, toutes au statut `absent`. Aucune entrée `certain` n'a des sources sans tests, ni des tests sans sources.

| Id | Catégorie | Description | Nature |
| --- | --- | --- | --- |
| A1 | attaque | Table d'attaque des coups blancs (ordre, tirage unique) | règle de jeu |
| A2 | attaque | Deux jets pour les sorts (raté puis résistance) | règle de jeu |
| A6 | attaque | Éraflures (taux et pénalité selon la compétence d'arme) | règle de jeu |
| A9 | attaque | Esquive, parade, blocage selon la position | règle de jeu |
| A10 | attaque | Pénalité de raté en double arme | règle de jeu |
| A11 | attaque | Écrasements (monstres) | règle de jeu |
| A15 | attaque | Pénétration des sorts | règle de jeu |
| B8 | ressources | MP5 | règle de jeu |
| C4 | physique | Vitesse de déplacement du joueur | règle de jeu |
| F5 | equipement | Bijoux uniques | règle de jeu |
| H8 | rencontre | Taille de raid (10, 20, 40) | règle de jeu |
| F8 | equipement | Liste des effets non modélisés | outil du projet |
| I3 | optimisation | Poids de stats avec erreur standard | outil du projet |
| I4 | optimisation | Simulation de l'ensemble réel | outil du projet |
| J3 | meta | Erreur statistique cible | outil du projet |
| J6 | meta | Hypothèses datées avec date de péremption | outil du projet |

Pour les cinq outils du projet, la certitude ne décrit pas une règle du jeu. Pour les onze règles de jeu, elle reste à étayer ou à baisser, au cas par cas, quand leur tranche les modélise. Les tables d'attaque A1, A6, A9, A10 et A11 sont celles que wowsims Forever code (`spell_outcome.go` d'ElliotWood) : source communautaire, au mieux `suppose`.

## Questions ouvertes ajoutées ou modifiées

- **PER8** (ajoutée) : conversion des notations en pourcentage.
- **PER9** (ajoutée) : tiers des soins en dégâts, F7.
- **MAG19** : le test par MythicSim n'est pas possible au niveau 20.
- **MON7** : pas de réponse dans les simulateurs.
- **MAG6** : les simulateurs lisent le même bit du client.

## Sources

- [ElliotWood/Forever](https://github.com/ElliotWood/Forever) `0dbbe2d4e7cd3f7c0c06d55d748420b2c41944fe` : `docs/forever_rules.md`, `docs/DATA_SOURCES.md`, `docs/commands.md`, `docs/installation.md`, `cmd/wowsimcli/`, `sim/core/forever_rules.go`, `base_stats_auto_gen.go`, `racials.go`, `utils.go`, `target.go`, `spell_outcome.go`, `proto/api.proto`, `proto/common.proto`, `tools/database/dbc/maps.go`, `ui/features/talents/model/can_set_points.ts`, `ui/features/import-export/importers/addon.ts`, publications v0.0.1 et v0.0.2.
- [sage3648/mythicsim-forever-engine-go](https://github.com/sage3648/mythicsim-forever-engine-go) `51da1856fc932401bd880e3691cba14b33039dc1` (`master`), `66837240ec3c27a25620e7eb6ee03c8c1da6f6ce` (`mythicsim/imbue-stacking-thistle`), référence `2d93e423e0303e93dbb16e190d435503248b68f9` : README, `docs/forever_rules.md`, `docs/mythicsim-upstream-refresh-2026-09-23.md`, `sim/core/ruleset.go`.
- [sage3648/mythicsim-forever-engine](https://github.com/sage3648/mythicsim-forever-engine) `e346c5e6700ac5c5c3fc76f104ffcb71ad6dba04` : README, `docs/validation-summary.md`, `docs/routing.md`, `docs/release.md`, `docs/application-contract-inventory.md`, `benchmarks/2026-10-04-production-builds.json`, `src/prepare/`.
- [wowsims/classic](https://github.com/wowsims/classic) `7779ebbf79dc7f1341e6ab939b28a3402c9a730a` ; [wowsims/exporter](https://github.com/wowsims/exporter) `ad9e903e3997b99f66a2122a4a91b555d40c4ece` ; [gunba/wow-forever-sim](https://github.com/gunba/wow-forever-sim) `9c05fc890b2c78e95c15605895134ebeb689b857`.
- [MythicSim - Forever Sim Exporter](https://www.curseforge.com/wow/addons/mythicsim-forever-sim-exporter), page lue le 2026-10-09.
- SimulationCraft 12.1.0-alpha-06, `Interface/AddOns/Simulationcraft/` (`Simulationcraft.toc`, `core.lua`, `forever/stats.lua`), lu sur disque.
- Projet : `docs/MECHANICS_REGISTRY.yaml` (A4, A5, A7, A8, A17, F7, G1, G3, H11, J4), `forever/data/1.60.1.70291/` (`leveling.json`, `character_scaling.json`, `classes.json`, `races.json`, `monsters.json`), `docs/OPEN_QUESTIONS.md`, `addon/ForeverBridge/Message.lua`, `forever/bridge/`.
