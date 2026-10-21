# Simulateur de la communauté pour Forever : état au 2026-10-21

Étude en lecture seule du 2026-10-21 : pages GitHub, `api.github.com` et `raw.githubusercontent.com` en anonyme,
sites publics. Rien n'a été cloné, téléchargé, compilé ni exécuté. Elle met à jour
[l'étude du 2026-10-09](wowsims-forever.md) (décision 224) et la correction de
[l'étude du moteur générique](moteur-generique.md) (décision 252) ; ce qui y est dit et reste vrai n'est pas répété.

Tout ce qui vient de ces dépôts est une **source communautaire**, au mieux `suppose`, datée au commit lu. Aucune
valeur de jeu n'est recopiée ici : seuls les formats, les dates et les noms de fichiers. **[lu]** : vu dans la source
citée ; **[déduit]** : interprétation.

## Résumé

- **ElliotWood/Forever n'existe plus** : le dépôt, son API et ses fichiers bruts répondent 404 le 2026-10-21 [lu] ;
  le journal des correctifs de MythicSim date la disparition d'**environ le 19 octobre 2026** [lu]. Le binaire
  `wowsimcli-windows.exe` hebdomadaire de l'étude du 9 octobre a disparu avec lui.
- **Le simulateur de référence est désormais `wowsims/forever`**, le dépôt officiel de l'équipe WoWSims (MIT, créé le
  2026-09-19, site <https://wowsims.com/forever/>) : c'est lui qu'ElliotWood reprenait, et MythicSim le suit
  directement depuis le 20 octobre.
- **Aucun binaire à jour** : `wowsims/forever` n'a aucune publication (le flux `release.yml` n'a jamais tourné),
  MythicSim (Go et Rust), gunba, ryanfitz7 et laurencestokes non plus. Seul `Bearly-Tanky/foreversim` publie un
  `ForeverSim-windows-amd64.exe` (v1.1.0 du 2026-10-15), tiré d'ElliotWood `859556a`, abandonné depuis et antérieur à
  70450. « Lancer en local » veut donc dire **compiler** (Go 1.25, `protoc`, `protoc-gen-go`).
- **Données à jour** : sorts du client à **1.60.1.70450** depuis le 2026-10-17 ; correctif du serveur (hotfix push)
  112753 appliqué au Mage le 20 octobre ; objets resynchronisés plusieurs fois par jour (dernier : 2026-10-21
  01:39 UTC). Refonte du Mage : **données** prises environ 3 heures après la sortie du build 70425 ; **modélisation**
  (rotations, talents déplacés, résultats de référence) en 4 jours environ, du 16 au 20 octobre.
- **Le simulateur est en avance sur nous** : il applique les correctifs du serveur de 70450 (`DBCache.bin` publié par
  raidbots), que nous n'avons pas (décision 285). Exemple : le talent Piercing Ice est retiré chez lui, encore présent
  dans nos `talents.json` et `classes.json` de 70450.
- **Limites inchangées** : joueur fixé au niveau 60 (`const CharacterLevel = 60`) ; ni leveling, ni temps par monstre
  de bas niveau, ni PvP. Spécialisations de dégâts en « Alpha », soigneurs en « GearPlanner » seulement, Druide ours et
  Guerrier Protection « Unlaunched ».

## 1. État du dépôt

### Dépôts et ce qu'ils sont devenus

| Dépôt | Au 2026-10-09 (étude précédente) | Au 2026-10-21 |
| --- | --- | --- |
| [ElliotWood/Forever](https://github.com/ElliotWood/Forever) | référence, `0dbbe2d`, build 70291, `wowsimcli` hebdomadaire | **404** (dépôt, API, fichiers bruts) ; absent de la liste des dépôts de l'utilisateur ElliotWood [lu] ; « returned 404 from about 19 October 2026 » (`docs/mythicsim-patches.md` de MythicSim, audit du 20 octobre) [lu] |
| [wowsims/forever](https://github.com/wowsims/forever) | cité comme moteur en amont | **référence** : MIT (« Copyright (c) 2022 wowsims team »), créé le 2026-09-19, dernier envoi 2026-10-21 06:07 UTC, 56 tickets ouverts, 10 forks [lu] |
| [sage3648/mythicsim-forever-engine-go](https://github.com/sage3648/mythicsim-forever-engine-go) | fork d'ElliotWood, branches `mythicsim/*` | GitHub le rattache désormais à `wowsims/classic` [lu, champ `parent`] ; suit `wowsims/forever` « by behaviour rather than merged » (histoires divergentes depuis le 25 septembre) [lu] ; dernier envoi 2026-10-21 04:59 UTC ; **gelé** selon le README du Rust (« The Go fork no longer accepts patches ») [lu] |
| [sage3648/mythicsim-forever-engine](https://github.com/sage3648/mythicsim-forever-engine) (Rust) | expérimental, build 70235 | moteur de production des Quick Sims de MythicSim ; dernier commit `9eef0de` (2026-10-21 03:33 UTC) ; référence Go épinglée `62b7445d1` [lu] |
| [gunba/wow-forever-sim](https://github.com/gunba/wow-forever-sim) | fork, benchmark de niveau 60 | n'est plus marqué comme fork ; actif (2026-10-21 05:29 UTC) ; aucune publication [lu] |

**[déduit]** La disparition d'ElliotWood/Forever casse aussi une source citée dans nos données :
`forever/data/1.60.1.70450/meta.json` (`sources.confirmed_ranks`), `talents.json` et `_seed_talents.json` pointent vers
`raw.githubusercontent.com/ElliotWood/Forever/master/assets/confirmed_talents.json`, aujourd'hui 404. Aucun code ne
télécharge cette adresse (recherche dans `forever/`, `plugin/`, `scripts/`) : c'est une citation morte, pas une panne.

### Dernier commit et publications de `wowsims/forever`

- **Dernier commit sur `master`** : `64662bc` (2026-10-21 01:44 UTC), fusion de la PR #618 « [DB] Update items to
  1.60.1.70450 with hotfixes as of 2026-10-21 » (`e029f32`, robot) [lu].
- **Publications : aucune.** La page des publications dit « There aren't any releases here » ; `releases` de l'API est
  vide ; `release.yml` et `scheduled_release.yml` ont **0 exécution** [lu]. Les 30 étiquettes `v0.0.111` à `v0.0.140`
  viennent de l'historique de wowsims/classic : `v0.0.140` pointe sur `f02667f` du 2026-09-18, avant la création du
  dépôt [lu]. Aucune n'est une publication de Forever.
- `scheduled_release.yml` prévoit une publication **quotidienne** (10:00 UTC) des binaires `wowsimcli-windows.exe.zip`,
  `wowsimcli-amd64-linux.zip`, `wowsimcli-arm64-darwin.zip` et `wowsimforever-*` [lu] ; ce flux-là n'a jamais tourné
  (0 exécution), alors que le flux horaire `check_hotfixes.yml` tourne (PR #600, #604, #618 du robot) [lu].
- **Ce qui est publié en continu** : le site <https://wowsims.com/forever/>, reconstruit à chaque envoi sur `master`
  (flux « Build and Deploy », exécution du 2026-10-21 06:14 UTC) [lu].

### Build du jeu des données

Les données du simulateur sont tenues **par groupe** : les 9 classes, `racials`, `shared`, et les objets
(`docs/spell_data/partial-updates.md`) [lu]. Chaque groupe garde le build et le correctif du serveur avec lesquels il a
été extrait, dans `assets/db_inputs/spell_store_inputs.json` (JSON compressé en gzip, champs `Builds` et `Hotfixes`)
[lu]. Le fichier de l'étude précédente (`assets/db_inputs/forever_client_build.txt`) n'existe pas dans ce dépôt [lu].

| Date (UTC) | Commit | Changement de build [lu] |
| --- | --- | --- |
| 2026-09-22 | `f2c7f0d` | « [DB] Update to 1.60.1.69913 » |
| 2026-09-24 | `f0ee569` | 1.60.1.69977 |
| 2026-09-24 | `2d0572d` | 1.60.1.70009 |
| 2026-10-01 | `76d8cab` | 1.60.1.70124 |
| 2026-10-02 | `bf4f6aa` | 1.60.1.70170 |
| 2026-10-06 | `0e374d8` | 1.60.1.70235 |
| 2026-10-08 | `b1bfb5a`, `4dd050c` | 1.60.1.70291, classe par classe (« Update warlock, racials, shared and items… ») |
| 2026-10-14 | `fb6e865` | objets à 1.60.1.70374 (sorts de classe pris classe par classe) |
| 2026-10-16 01:30 | `2e10ccf` | « Take the items, shared rows and racials from 1.60.1.70425 » |
| 2026-10-16 03:43 | `cf82c75` | « [Mage] Take the mage from 1.60.1.70425 » (MR-Valdez) |
| 2026-10-16 05:00 | `bbf7eed` | objets, lignes partagées et raciaux au correctif 112835 |
| 2026-10-16 22:52 | `9cd3a8a` | objets à 1.60.1.70450 |
| 2026-10-16 23:58 | `446a46e` | « [Spells] Regenerate spelldata from 1.60.1.70450 » (`spells_auto_gen.go`, résultats du Paladin Vindicte) |
| 2026-10-20 05:25 | PR #594 (`12f3f1d`) | « [Mage] mage hotfix and talent shift and spelldata » : `proto/mage.proto` réordonné, sorts du Mage, résultats Arcane, Feu et Givre-feu |
| 2026-10-21 01:39 | `e029f32` | objets à 1.60.1.70450, correctifs du 2026-10-21 |

**Build 70425** : build de `wow_classic_beta` du 16 octobre 00:50 UTC selon MythicSim (patch 142) [lu]. Nous ne l'avons
jamais installé (nos versions passent de 70374 à 70450) [lu, `forever/data/`].

### Cadence après un patch (refonte du Mage, 15-20 octobre)

1. Note de Blizzard du 15 octobre (`docs/research/notes-blizzard-2026-10-15.md`) ; build 70425 le 16 octobre
   00:50 UTC.
2. Mage du simulateur pris de 70425 à 03:43 UTC, **environ 3 heures après** ; objets, raciaux et Chaman dans la même
   nuit [lu].
3. Build 70450 : objets et sorts regénérés dans les 24 heures (16 octobre 22:52 et 23:58 UTC) [lu].
4. Rotations et tests du Mage : PR #538 (FoF, rangs des sorts, 18 octobre), #558 (rotation Arcane, 18 octobre), #567
   (19 octobre), #576 (tests, 19 octobre), puis #594 (correctif 112753, déplacement de talents, 20 octobre) [lu].
5. Même période chez nous : rejeu de 70450 et décision 285 le 20 octobre ; refonte du Mage pas encore modélisée.

**Mécanique de mise à jour [lu]** :
- `check_hotfixes.yml` tourne **toutes les heures** (`17 * * * *`) : il lit la liste des `DBCache.bin` vérifiés de
  raidbots (<https://www.raidbots.com/api/dbcache/verified>), garde la plus récente de `classic_beta` dont le build est
  celui du CDN de Blizzard, et lance `update_items.yml`.
- `update_items.yml` régénère **les objets seulement** (`make db CLASSES=none SHARED=0`), sans installation du jeu,
  par le CDN ; la PR est fusionnée seule si les correctifs sont appliqués et les tests verts.
- `update_db.yml` (toutes les tables) est **manuel** (cron commenté), PR sans fusion automatique.
- Les **sorts de classe** sont repris à la main, classe par classe, par le mainteneur de la classe.

**[déduit]** Objets : quelques heures. Sorts et talents d'une classe : de quelques heures à quelques jours, selon le
mainteneur. Rotations et préréglages : quelques jours.

### Licence

MIT, « Copyright (c) 2022 wowsims team », sans clause ajoutée [lu, `LICENSE`]. Le README demande en plus, sans
l'imposer, un lien visible vers le projet d'origine dans tout logiciel qui le réutilise [lu].

## 2. Couverture

### Classes et spécialisations

`sim/register_all.go` enregistre **18 spécialisations** pour les 9 classes [lu]. Leur état publié vient du champ
`launch.status` de `ui/sim/player/specs/<classe>.ts`, ce que le site affiche [lu, 2026-10-21] :

| Classe | Spécialisation | État publié |
| --- | --- | --- |
| Druid (Druide) | Balance, Feral Cat | Alpha |
| Druid | Feral Bear | **Unlaunched** |
| Druid | Restoration | GearPlanner (planificateur d'équipement, pas de simulation) |
| Hunter (Chasseur) | une seule simulation (pas de spécialisation séparée) | Alpha |
| Mage | une seule simulation DPS (Arcane, Feu, Givre-feu, Givre par talents et APL) | Alpha |
| Paladin | Protection, Retribution | Alpha |
| Paladin | Holy | GearPlanner |
| Priest (Prêtre) | DPS | Alpha |
| Priest | Healer | GearPlanner |
| Rogue (Voleur) | une seule simulation | Alpha |
| Shaman (Chaman) | Elemental, Enhancement | Alpha |
| Shaman | Restoration | GearPlanner |
| Warlock (Démoniste) | une seule simulation | Alpha |
| Warrior (Guerrier) | DPS | Alpha |
| Warrior | Protection | **Unlaunched** |

- **Rotations** : chaque spécialisation Alpha a ses APL et préréglages (`ui/specs/<classe>/…/apls/*.apl.json`,
  `presets.ts`) [lu pour le Mage]. **Aucune n'est « Launched »** : tout reste Alpha.
- Les tickets de suivi `[Spec]` (#1 à #24, ouverts le 19 et le 20 septembre) ne sont **pas fiables** pour l'état : le
  #19 (Mage) dit encore « core abilities, APL » à faire alors que 56 commits `[Mage]` sont arrivés du 15 au 21 octobre
  [lu]. Ils ne servent qu'à voir ce qui reste prévu (ensembles de tier, échelle des statistiques).
- **Soigneurs** : simulés seulement chez MythicSim, en Rust, depuis le 2026-10-21 (Holy Paladin, Restoration Shaman,
  Restoration Druid, Holy Priest), sans équivalent en Go [lu, README et commit `ee4e963`].

### Niveaux

- **Joueur fixé au niveau 60** : `const CharacterLevel = 60` (`sim/core/constants.go`, `master` du 2026-10-21) [lu].
  Rien ne change par rapport à l'étude du 9 octobre : ni leveling, ni personnage de niveau inférieur, ni temps pour tuer
  un monstre de bas niveau.
- La bêta était plafonnée au niveau 30 (`meta.json`, `game_state.beta_level_cap`) : **[déduit]** aucun chiffre de
  niveau 60 de ces simulateurs n'a été mesuré en jeu, ce que le Sim Lab dit lui-même (« level-60 numbers are the
  engine's projection ») [lu].

### Contextes

- **Raid et donjon de niveau 60** : rencontre à un ou plusieurs boss (MythicSim : 2 à 5 cibles), durée et variation,
  phases d'exécution ; les phases d'exécution inutilisées à 25, 45 et 90 % ont été retirées le 2026-10-20 (`39c264c`)
  [lu].
- **Tanks** : menace et mitigation (Protection Paladin en Alpha ; menace du Guerrier portée par MythicSim, patchs 181 à
  185) [lu].
- **Solo, leveling, PvP** : absents.

### Poids, comparaison d'objets, lots

- **Poids des statistiques (EP)** : par le serveur local `wowsimforever` (`sim/web/main.go`) : `/statWeights`,
  `/statWeightsAsync`, `/statWeightRequests`, `/statWeightCompute` (`StatWeightsRequest`, protobuf binaire) [lu] ; et
  dans le navigateur (WASM) sur le site. **Pas par `wowsimcli`** [lu]. Statistiques pondérées du Mage : intelligence,
  esprit, puissance des sorts par école, pénétration, toucher, critique, hâte, mana, MP5, toucher par école en
  pseudo-statistique (`ui/specs/mage/dps/spec.ts`) [lu].
- **Comparaison d'objets** : deux simulations appariées par `wowsimcli`, ou `/bulkSimAsync` (lots d'objets et
  d'enchantements, étapes Low à Finalist, erreur appariée contre la référence) [lu, skill `wowsims-bulk-sim`].
- **Optimiseur d'équipement** : `/reforgeOptimizeAsync` (programme linéaire HiGHS sur les EP) [lu].
- **« Bulk sim » de builds de talents** : **absent** chez `wowsims/forever` (le lot porte sur les objets et les
  enchantements) [lu]. MythicSim a un « Build Lab », privé, qui tourne en Go [lu, README du Rust].

## 3. Interface

- **`wowsimcli`** (`cmd/wowsimcli/cmd/`) : `sim --infile <RaidSimRequest en protojson> [--outfile r.json]
  [--verbose]`, plus `version` et `decode-link` [lu]. Lecture en `DiscardUnknown` (un champ inconnu est ignoré sans
  erreur) ; `simOptions` obligatoire ; sortie `RaidSimResult` en protojson, champs vides compris [lu]. Rien n'a changé
  depuis l'étude du 9 octobre, sauf l'origine du dépôt.
- **Talents** : `talentsString` positionnel, un chiffre par talent dans l'ordre des champs de `proto/<classe>.proto`,
  arbres séparés par `-` [lu, `mage_test.go`]. **L'ordre change avec le jeu** : la PR #594 a retiré `piercing_ice` et
  renuméroté le Givre (`elemental_precision = 39`… `ice_barrier = 54`) [lu] ; MythicSim refuse depuis les chaînes trop
  longues d'avant le correctif (patch 189) [lu].
- **Binaires** : **aucun à jour** (section 1 ; le `ForeverSim-windows-amd64.exe` de `Bearly-Tanky/foreversim`,
  v1.1.0 du 2026-10-15, MIT, 8 commits, vient d'ElliotWood `859556a` et n'est plus suivi). Construction : `go build --tags=with_db` dans `cmd/wowsimcli` (cible `release`
  ou `wowsimforever-windows.exe` du `makefile`) après `make proto` (`protoc` et `protoc-gen-go`) [lu]. Prérequis :
  Go 1.25, `protoc`, `protoc-gen-go` ; Node 22 seulement pour l'interface ; sous Windows, la documentation conseille
  WSL ou Docker, ou Go, NVM et `make` en natif (`docs/installation.md`) [lu].
- **Serveur local** `wowsimforever` : `-host localhost:3333`, `-launch`, `-wasm`, `-nvc` (sans vérification de la
  dernière publication GitHub) ; corps en protobuf binaire, CORS ouvert [lu].
- **Temps de calcul** : aucun chiffre nouveau. Repère de l'étude précédente : 0,66 à 2,63 s pour 10 000 itérations en
  Go (Apple M2 Max, 2026-10-04) ; le Rust annonce 1,3 à 2 fois plus vite [lu, README du 2026-10-21]. Sous Windows, chez
  l'utilisateur : à mesurer.

## 4. MythicSim et les autres outils

### MythicSim

- **Site** <https://mythicsim.com/wow-forever> : Quick Sim et Best Gear (export par l'addon MythicSim 0.3.0 ou plus,
  `/msim`, JSON collé), classement des spécialisations, bijoux, races, builds de la communauté, guide de rotation,
  journal d'audit ; plafond 60 ; **aucune API publique** ; mise à jour du moteur le 21 octobre [lu].
- **Build affiché** : la page et `data/manifest.json` du Rust disent **1.60.1.70425** [lu] ; or la référence Go
  épinglée (`62b7445d1`, 2026-10-21) contient le correctif 112753 (`DBCache.bin` de la bêta, en-tête 70450) [lu,
  patch 187]. **Écart non résolu** : le manifeste n'a peut-être pas été régénéré.
- **Apport par rapport à `wowsims/forever`** : soigneurs (Rust seulement), menace du Guerrier, correctifs signalés sur
  leur Discord ; **pas plus à jour** sur les données : il porte les changements de `wowsims/forever` avec quelques heures
  de retard (patchs 187 et 188 repris de la PR #594).
- **Ce qui reste en Go chez eux** : poids des statistiques, Best Gear, classements, Build Lab ; le code du worker et de
  l'API reste privé [lu].

### Autres outils (tous `suppose`, aucun n'est un calcul vérifiable par nous)

| Outil | Ce qu'il donne | Moteur et date | Limite |
| --- | --- | --- | --- |
| [WoW Forever Sim Lab](https://wowforever-sims.pages.dev/) (@plankton_dao) | 24 spécialisations de dégâts, 213 scénarios, **poids des statistiques publiés** en clair, 10 000 itérations | Go de MythicSim, commit `0d17668`, build 70425, simulé le 2026-10-18 [lu] | niveau 60 projeté ; avant le correctif 112753 |
| [kami-labs BiS](https://kami-labs.fr/en/bis-list-wow-forever/) | listes BiS par spécialisation | « WoW Forever simulator weights (wowsims) », sans commit, calculé le 2026-10-16 [lu] | BiS du niveau 30 avec des poids de niveau 60 **[déduit]** |
| [ForeverBiS](https://www.curseforge.com/wow/addons/foreverbis) (CurseForge, 2.3.1 du 2026-10-16) | BiS des 28 spécialisations | poids publics de ForeverDB, « provisional comparisons, not simulations » [lu] | aucun simulateur |
| [The Forever Era](https://theforeverera.com/en/bis/) | BiS, poids « indicatifs » | aucune simulation, base Classic 1.12 [lu, résultat de recherche] | |
| Discord officiel de WoW Forever (environ 32 900 membres) ; Discord de MythicSim et de WoWSims | discussions | — | pas une source citable ; aucun tableur de théorie publique trouvé ; pas de sous-forum Reddit dédié trouvé |

Les addons déjà installés chez l'utilisateur (Naowh Forever, AtlasLoot Forever, Forever Companion) restent la source
des BiS en attendant le calcul (décision 250).

## 5. Détecter des données périmées

### Ce que le simulateur expose

- **Build et correctif par groupe** : `assets/db_inputs/spell_store_inputs.json` (gzip) porte `Builds` et `Hotfixes`
  pour chaque classe, `racials` et `shared`, et une **copie des lignes des tables du client** dont le magasin des sorts
  est construit [lu, `docs/spell_data/regenerating.md`]. C'est la pièce clé : des lignes brutes, comparables à nos CSV
  de wago.tools, sans lire de Go.
- **Magasin des sorts** : `sim/core/spelldata/spells_auto_gen.go` (4,8 Mo), une ligne par identifiant de sort : `ID`,
  `Name`, `Rank`, `School`, `Attr` (17 mots d'attributs), temps, `Powers`, et `Effects[]` (`Index`, `Type`, `Aura`,
  `BasePoints`, `SPCoef`, cible…) [lu]. Ni build ni date dans le fichier [lu].
- **Sorts par classe** : `sim/<classe>/spell_data_auto_gen.go` liste, par nom, les identifiants de sorts
  (`Ranked(id1, id2…)`, `Talent(spellID, maxRank)`) et, en commentaire, ce qui n'a pas été généré (« Magic Attunement:
  missing rank 1 of 2 ») [lu].
- **Talents** : `proto/<classe>.proto`, champs dans l'ordre des arbres [lu].
- **Contrôle chez eux** : `make spelldata-check` (`gen_spelldata -check`) signale les groupes dont le build diffère de
  la base ; un correctif plus récent bloque la régénération [lu].
- **Résultats de référence** : `sim/<classe>/*.results` changent quand une mécanique change [lu].

### Exemple réel : le simulateur est en avance

- Chez eux : la PR #594 (2026-10-20, correctif 112753) retire `piercing_ice` de `proto/mage.proto` et ajoute Frigid
  Power (`1326891` dans `db.json` de MythicSim) [lu].
- Chez nous : `forever/data/1.60.1.70450/talents.json` et `classes.json` portent encore `piercingIce` [lu, recherche
  locale], parce que 70450 est installé **sans correctifs du serveur** (décision 285).
- La source de ce correctif est publique : la liste raidbots des `DBCache.bin` vérifiés (section 1). **[déduit]** La
  phrase de la décision 285 « aucun `DBCache.bin` du build » vaut pour le cache local de l'utilisateur, pas pour le
  monde : un `DBCache.bin` de 70450 existe chez raidbots. Le récupérer serait un nouvel accès réseau (accord de
  l'utilisateur).

### Méthode proposée (outil manuel, jamais dans les tests ni dans `verify`)

Commande proposée : `forever sim drift --sim-commit <sha>`, lancée à la main, sur une copie téléchargée et épinglée
(accord réseau), rapport écrit dans `docs/research/` :

1. **Builds** : décompresser `spell_store_inputs.json` au commit épinglé ; lire `Builds` et `Hotfixes` par groupe ;
   comparer à notre version installée (`sources.json` : `game_version`) et à notre correctif (aucun pour 70450). Sortie :
   « Mage : simulateur 70450 + correctif 112753 ; nous 70450 sans correctif ».
2. **Lignes du client** : pour chaque table présente des deux côtés (`Spell`, `SpellEffect`, `SpellMisc`,
   `SpellLevels`, `SpellPower`…, noms à lire dans la copie), joindre par identifiant de ligne et comparer champ par
   champ : ajoutée, retirée, changée. Même build des deux côtés : écart = correctif du serveur. Builds différents :
   écart = retard de l'un des deux.
3. **Talents** : par classe, ensemble des identifiants de sorts de `Talent(…)` de `sim/<classe>/spell_data_auto_gen.go`
   et noms de `proto/<classe>.proto` contre nos `talents.json` et `classes.json` (par identifiant de sort, comme
   `forever talents tf crosscheck`). Talent absent d'un côté = alerte (cas Piercing Ice).
4. **Valeurs utilisées par notre moteur** : pour nos sorts du Mage (`spells.json`), comparer `BasePoints` et `SPCoef`
   des effets de dégâts à nos champs décodés (`bonus_coefficient` vient du même `EffectBonusCoefficient`). Un accord ne
   prouve pas le jeu (même source) ; un désaccord désigne un correctif ou une erreur de lecture.
5. **Retard du simulateur** : pour une version que nous installons, un groupe resté sur un build antérieur dans
   `Builds`, ou un `.results` inchangé alors que nos valeurs de la classe changent, marque ses résultats « simulateur pas
   à jour pour cette classe » dans la provenance, et `forever status` l'affiche.

## 6. Risques

- **Disparition d'un fork** : c'est arrivé à ElliotWood/Forever en moins de deux semaines. Parade : ne dépendre que de
  `wowsims/forever` (organisation, plusieurs mainteneurs), épingler un commit, garder une copie locale du code source
  construit et de son empreinte.
- **Maintenance** : équipe, pas un seul mainteneur. Auteurs actifs vus du 15 au 21 octobre : 1337LutZ, kayla-glick,
  hillerstorm, MR-Valdez, dodoels, plus le robot des objets [lu]. Mais **une classe = souvent un mainteneur** (Mage :
  MR-Valdez et 1337LutZ ; Chaman : kayla-glick ; Druide : dodoels) [lu, commits] ; le README dit que « chaque communauté
  tient sa partie » [lu]. Une classe peut donc prendre du retard seule.
- **Formats instables** : protos modifiés sans migration (« Nothing migrates an input file ») ; lecture en
  `DiscardUnknown`, donc un champ perdu passe **sans erreur** ; ordre des talents renuméroté à chaque déplacement
  (PR #594). Parade : chaînes de talents générées par identifiant de sort depuis le proto du commit épinglé ; tests de
  contrat sur des demandes en fixtures ; refus si l'empreinte du proto change.
- **Pas de binaire** : il faut une chaîne Go et `protoc` sur la machine (nouvelles dépendances, accord de
  l'utilisateur), ou Docker.
- **Statut Alpha partout** ; soigneurs et deux tanks non simulés en amont.
- **Lancement du 4 novembre** : tous les flux visent le produit `wow_classic_beta` [lu] ; le produit de la version
  publiée n'est pas connu. **[déduit]** Les deux chaînes (la leur, la nôtre) devront changer de produit le même jour.
- **Licence** : MIT, sans risque juridique ; mettre le lien vers wowsims demandé par le README dans la provenance et
  l'aide.
- **Circularité** : ils lisent le même client que nous ; un accord n'est pas une preuve en jeu (déjà noté le 9 octobre).

## Verdict : réutiliser, recouper, écarter

| Usage | Verdict | Comment |
| --- | --- | --- |
| DPS de raid et de donjon de niveau 60, 9 classes | **Réutiliser** | `wowsimcli` de `wowsims/forever`, compilé en local à un commit épinglé ; `suppose`, commit et builds par groupe dans la provenance |
| Poids des statistiques au niveau 60 | **Réutiliser** | simulations appariées par `wowsimcli`, ou serveur local `/statWeights` ; poids du Mage **recoupés** avec notre moteur |
| « Est-ce une amélioration ? » au niveau 60 | **Réutiliser** | deux simulations appariées (ou `/bulkSimAsync`) |
| Lots de builds de talents | **Écarter l'amont** | absent chez `wowsims/forever`, privé chez MythicSim ; lots de `wowsimcli` à écrire chez nous si besoin |
| Moteur du Mage | **Recouper** | contrôle croisé au niveau 60 (registre J4) ; le simulateur fait foi en raid, notre moteur reste pour les niveaux bas |
| Leveling, temps par monstre, niveau inférieur à 60, mana entre les combats | **Écarter** | joueur fixé à 60 ; notre moteur (Mage), sinon builds populaires (décision 243) |
| Soigneurs (4 spécialisations), Druide ours, Guerrier Protection | **Écarter pour l'instant** | GearPlanner ou Unlaunched en amont ; soigneurs de MythicSim en Rust à revoir |
| PvP | **Écarter** | non simulé |
| MythicSim (site) | **Recouper à la main** | aucune API ; utile pour un contrôle ponctuel et pour les soigneurs |
| Sim Lab, kami-labs, ForeverBiS, Forever Era | **Recouper** | repères `suppose`, datés ; jamais dans `forever/data/` |
| Détection des données périmées | **Réutiliser** | `spell_store_inputs.json` (builds, correctifs, lignes du client) et la liste raidbots des `DBCache.bin` vérifiés, outil manuel de la section 5 |

**Clauses devenues fausses dans les décisions** (à amender par la décision suivante, rien n'est modifié ici) :
- **224** : « le moteur `wowsimcli` d'ElliotWood/Forever » → `wowsims/forever` ; « binaire Windows publié » et
  « téléchargement du binaire » → aucun binaire à jour, compilation locale (Go 1.25, `protoc`) ; « données au même build que
  les nôtres » → le simulateur a les correctifs du serveur de 70450, pas nous ; « 9 classes au niveau 60 » → 18
  spécialisations enregistrées : 12 simulées (Alpha), 4 soigneurs en planificateur seulement, 2 tanks non publiés.
- **250** : « au niveau 60 par SIM1 (wowsims, `suppose`, 9 classes) » reste vrai pour les spécialisations de dégâts ;
  pas pour les soigneurs, le Druide ours et le Guerrier Protection.
- **252** : « ElliotWood/Forever, MIT, données au build 1.60.1.70291, `wowsimcli-windows.exe` publié chaque semaine » →
  `wowsims/forever`, 70450 avec correctif 112753 pour le Mage, aucun binaire à jour ; « `sage3648/mythicsim-forever-engine-go`
  en est un fork » → il suit désormais `wowsims/forever` directement, et il est gelé au profit du moteur Rust.
- **Données** : la source `confirmed_ranks` de `meta.json` de 70450 (ElliotWood) est une adresse morte.

## Sources

Toutes lues le 2026-10-21.

- [wowsims/forever](https://github.com/wowsims/forever), `master` à `64662bc` (2026-10-21 01:44 UTC) : `README.md`,
  `LICENSE`, `AGENTS.md`, `makefile`, `docs/commands.md`, `docs/installation.md`, `docs/spell_data/README.md`,
  `store.md`, `regenerating.md`, `partial-updates.md`, `.github/workflows/` (`release.yml`, `scheduled_release.yml`,
  `update_db.yml`, `update_items.yml`, `check_hotfixes.yml`), `.github/skills/wowsims-bulk-sim/SKILL.md`,
  `wowsims-reforge-optimizer/SKILL.md`, `cmd/wowsimcli/cmd/basic_sim.go`, `root.go`, `sim/register_all.go`,
  `sim/core/constants.go`, `sim/core/spelldata/spells_auto_gen.go`, `sim/mage/spell_data_auto_gen.go`, `sim/web/main.go`,
  `proto/mage.proto`, `ui/sim/player/specs/*.ts`, `ui/specs/mage/dps/spec.ts`, `ui/app/landing/landing_classes.ts` ;
  commits `446a46e`, `983ea6f`, `da381e4`, `12f3f1d`, `cf82c75`, `2e10ccf`, `bbf7eed`, `e029f32`, `39c264c`, PR #594 ;
  recherches de commits (« 70450 », « 70425 », « 70374 », « 70291 », « [DB] Update to », « [Mage] ») ; tickets
  `[Spec]` #1 à #24 ; API `releases`, `tags`, `actions/workflows/*/runs`, `contributors`.
- [ElliotWood/Forever](https://github.com/ElliotWood/Forever) : 404 (page, API, fichiers bruts) ;
  [dépôts de l'utilisateur ElliotWood](https://api.github.com/users/ElliotWood/repos).
- [sage3648/mythicsim-forever-engine-go](https://github.com/sage3648/mythicsim-forever-engine-go) : métadonnées,
  branches, commit `62b7445d1c812b257110e51a5b1e8db93b987972` (2026-10-21), `docs/mythicsim-patches.md` à ce commit
  (patchs 142, 185 à 189, audit du 20 octobre).
- [sage3648/mythicsim-forever-engine](https://github.com/sage3648/mythicsim-forever-engine) : `README.md`,
  `data/manifest.json`, commits jusqu'à `9eef0de` (2026-10-21).
- [gunba/wow-forever-sim](https://github.com/gunba/wow-forever-sim) : métadonnées et publications (aucune).
- [Bearly-Tanky/foreversim](https://github.com/Bearly-Tanky/foreversim) : README, métadonnées, publications v1.0.0 à
  v1.1.0 (2026-10-14 et 2026-10-15) ; publications de `ryanfitz7/Forever` et `laurencestokes/foreversim` (aucune).
- [MythicSim, WoW Forever](https://mythicsim.com/wow-forever), [Sim](https://mythicsim.com/wow-forever/sim),
  [Tier list](https://mythicsim.com/wow-forever/tier-list).
- [WoW Forever Sim Lab](https://wowforever-sims.pages.dev/) ; [kami-labs](https://kami-labs.fr/en/bis-list-wow-forever/) ;
  [ForeverBiS sur CurseForge](https://www.curseforge.com/wow/addons/foreverbis) ;
  [The Forever Era](https://theforeverera.com/en/bis/) (résultat de recherche) ;
  [Discord officiel de WoW Forever](https://discord.com/servers/world-of-warcraft-forever-pvp-1171140498367467711)
  (résultat de recherche).
- [raidbots, DBCache vérifiés](https://www.raidbots.com/api/dbcache/verified) : adresse lue dans `check_hotfixes.yml`,
  non consultée.
- Projet : `docs/research/wowsims-forever.md`, `docs/research/moteur-generique.md`,
  `docs/research/notes-blizzard-2026-10-15.md`, `docs/DECISIONS.md` (224, 250, 252, 285, 288),
  `forever/data/1.60.1.70450/` (`meta.json`, `sources.json`, `talents.json`, `classes.json`), `forever/pipeline/decode.py`.
