# data: 1.60.1.70009 r2 → 1.60.1.70124 (candidate, **non installée**)

Analyse du 2026-09-30. Version candidate écrite dans `<cache>/candidates/1.60.1.70124` (données `66be48468707`),
comparée à la version du dépôt `1.60.1.70009` révision 2 (données `5ec8369f724b`). **Rien n'a été installé** :
`forever/data/` n'a pas changé, la version courante reste 1.60.1.70009 r2.

Cumul de **deux publications** : 1.60.1.70058 (2026-09-29T16:41:04Z) puis 1.60.1.70124 (2026-09-30T01:57:04Z).
70058 n'a été ni téléchargée ni décodée : un changement apparu en 70058 puis annulé en 70124 serait invisible ici.

## Chaîne exécutée

| Étape | Commande | Résultat |
| --- | --- | --- |
| Versions publiées | `forever builds --limit 15 --json` | dernière 1.60.1.70124, locale 1.60.1.70009, 7 versions `1.60.x` |
| Téléchargement | `forever fetch --version 1.60.1.70124` | 20 tables (19 enUS + `SpellName` frFR) |
| Téléchargement de référence | `forever fetch --version 1.60.1.70009` | mêmes 20 tables (le cache était vide) |
| Rattachement de classe | `forever fetch --tables SkillLine,ChrClasses` sur les deux versions | 2 tables × 2 versions |
| Décodage | `forever decode --version 1.60.1.70124` | 54 talents, 15 sorts, 99 rangs |
| Vérification | `forever verify <candidate>` | **ok**, 1 avertissement (8 fichiers hérités) |
| Comparaison | `forever diff 1.60.1.70009 <candidate>` | **0 talent, 0 sort**, 5 fichiers |
| Rapport machine | `forever report 1.60.1.70009 <candidate>` | repris ci-dessous |

## Résultat : aucun changement dans les tables du client

Les **22 tables** téléchargées sont **identiques octet pour octet** entre 1.60.1.70009 et 1.60.1.70124
(comparaison des empreintes SHA-256 des CSV du cache) :

| Table | Lignes | Table | Lignes |
| --- | --- | --- | --- |
| `Spell` | 36 735 | `SpellCooldowns` | 4 436 |
| `SpellName` (enUS et frFR) | 31 716 | `SpellPower` | 3 429 |
| `SpellEffect` | 42 365 | `SpellCastTimes` | 72 |
| `SpellMisc` | 31 698 | `SpellDuration` | 133 |
| `SpellLevels` | 12 825 | `SkillLineAbility` | 7 826 |
| `SpellAuraOptions` | 12 881 | `SkillLine` | 154 |
| `CurvePoint` | 38 293 | `SkillLineXTraitTree` | 9 |
| `TraitNode` | 558 | `TraitNodeEntry` | 655 |
| `TraitNodeXTraitNodeEntry` | 561 | `TraitDefinition` | 654 |
| `TraitDefinitionEffectPoints` | 637 | `TraitEdge` | 96 |
| `ChrClasses` | 9 | | |

### Contrôle de validité

Le doute légitime est que wago.tools serve la même donnée quelle que soit la version demandée. Contrôle fait sur une
version antérieure : les trois tables de 1.60.1.69893 **diffèrent** de celles de 1.60.1.70009.

| Table | 69893 | 70009 |
| --- | --- | --- |
| `TraitDefinitionEffectPoints` | 14 890 o, `64105c2e36b1` | 14 818 o, `dd2af33a2530` |
| `TraitNodeEntry` | 13 174 o, `2072534b68d4` | 13 154 o, `4f13a6dc76af` |
| `SpellName` | 833 945 o, `ede393ee7dd2` | 832 295 o, `b9a0d125fd47` |

Le service sert donc bien des données par version : l'identité 70009 ↔ 70124 est réelle, pas un artefact.

## 1. Mage

**Aucun changement.** Ni talent, ni sort, ni rang, ni coût en mana, ni temps d'incantation, ni recharge, ni durée,
ni école, ni option d'aura. `forever diff` compte `0 talent, 0 spell` sur les 54 talents et les 15 sorts décodés
(99 rangs).

**Builds de T05 : aucun risque de changement.** Les builds de T05 sont calculés depuis `talents.json`,
`spells.json` et `spell_scaling.json`, tous décodés des tables `Trait*`, `Spell*` et `SkillLineAbility` ci-dessus.
Ces tables étant identiques, l'optimiseur reçoit exactement les mêmes entrées et rend exactement les mêmes builds.
Aucun rejeu n'est nécessaire ; il n'y a aucun changement à passer en revue un par un.

L'observation rendue par `forever decode` (7 talents portant un autre sort que la référence : `arcaneGeometry`,
`arcaneBlast`, `missileBarrage`, `flameThrowing`, `hotStreak`, `iceLance`, `fingersOfFrost`) est **identique à celle
de 70009** : c'est l'écart connu entre le client et la référence du seed, pas une nouveauté de 70124.

## 2. Autres classes

**Aucun changement non plus.** Le constat n'est pas limité au Mage : les tables comparées sont **globales**, pas
filtrées sur une classe.

- `ChrClasses` : 9 lignes, les 9 classes jouables (Warrior, Paladin, Hunter, Rogue, Priest, Shaman, Mage, Warlock, Druid).
- `SkillLineXTraitTree` : 9 lignes, un arbre de talents par classe.
- `SkillLineAbility` : 7 826 lignes, toutes les lignes de compétence de toutes les classes.
- `Spell` / `SpellName` : 36 735 et 31 716 lignes, tous les sorts du client.

Ces quatre tables étant identiques entre les deux versions, **aucune classe n'a vu un sort, un talent, un coût ou
une recharge changer** dans les tables téléchargées. Certitude `certain` pour ce périmètre.

Ce constat ne dépend pas du décodeur, qui ne couvre que le Mage jusqu'à PV1 : il est établi sur les CSV bruts.

## 3. Le reste

### Correctifs serveur (hotfixes)

Les tables téléchargées sont celles **livrées** avec le client. Les correctifs poussés par le serveur les
surchargent à l'exécution et n'y apparaissent pas (décision 128). Relevé de `Logs/Hotfix.log` (106 307 lignes, **un seul `---- Startup ----`**, à
08:58:29 le 2026-09-30 : le fichier est recréé à chaque lancement du client et ne couvre donc que la dernière
session ; ses trois blocs de validation, à 08:58:43, 08:58:59 et 09:07:41, appartiennent à cette seule session) :

| Table surchargée | Enregistrements distincts | Lesquels |
| --- | --- | --- |
| `Item` | 4 386 | non identifiés (table non téléchargée, base d'objets en T10) |
| `SpellMisc` | 2 | RecID 856075 et 866852 |
| `Spell` | 1 | RecID 1309410 |
| `SpellName` | 1 | RecID 1309410 |
| `SpellEffect`, `SpellPower`, `SpellCooldowns`, `SkillLineAbility`, `Trait*` | 0 | — |

Le sort corrigé, RecID **1309410**, est `Night Watchman's Torch` (`SpellName.csv`) : un sort porté par un objet de
quête, aucune classe jouable. Les deux lignes `SpellMisc` renvoient aux sorts 1309410 et 1321139, même icône
(135432), même catégorie (572).

**Aucun correctif serveur ne touche un sort, un talent ou une recharge de classe.** Aucune table de talent
(`Trait*`) ni de coût (`SpellPower`, `SpellCooldowns`) n'est surchargée.

### Angles morts

| Angle mort | Effet possible |
| --- | --- |
| Tables non téléchargées : `Item`, `ItemSparse`, `Creature`, `Quest`, `Map`, `JournalEncounter`… | Un changement d'objet, de monstre, de quête ou de carte en 70124 est invisible ici. Les 4 386 objets surchargés par hotfix indiquent que **quelque chose a bougé côté objets**. |
| 1.60.1.70058 non décodée | Un changement introduit en 70058 puis annulé en 70124 ne laisserait aucune trace. |
| `DBCache.bin` | Non lu (hors périmètre, T08). |
| Correctifs serveur des sessions antérieures | `Logs/Hotfix.log` est recréé à chaque lancement du client : les correctifs reçus pendant la première session du 2026-09-30 et pendant tous les jours sous 70009 sont **perdus**. |
| Contenu non décodé : `leveling.json`, `mechanics.json`, `monsters.json`, `racials.json`, `respec.json`, `overrides.json` | Hérités de 70009 dans la candidate, à revérifier à l'installation (avertissement de `forever verify`). |

## Rapport machine (`forever report`)

> # data: 1.60.1.70009 → `<cache>/candidates/1.60.1.70124`
>
> 5 changement(s) : 0 talent(s), 0 sort(s), 5 fichier(s).
>
> | Fichier | Changement |
> | --- | --- |
> | `_seed_spells.json` | retiré |
> | `_seed_talents.json` | retiré |
> | `_source_gunba_mage_tree.json` | retiré |
> | `confirmed_changes.json` | retiré |
> | `revisions.json` | retiré |
>
> Vérification : ok — avertissement : 8 fichier(s) hérité(s) d'une version antérieure, à revérifier.

**Ces 5 lignes ne sont pas des changements du jeu** : ce sont des fichiers que `forever decode` n'écrit pas dans une
candidate (copies figées du seed, changements confirmés, journal des révisions). `forever install` sait les reporter
d'une révision à l'autre, mais pas encore d'une **version** à l'autre : c'est le manque que la tranche T08a comble
(`tasks/T08a-plan.md`).

## Provenance

```
Provenance · version 1.60.1.70124 r2 · données 66be48468707 · générée 2026-09-30T07:37:13Z
· fraîcheur stale · certitude suppose · registre 37/108
· hypothèses : version plus récente publiée : 1.60.1.70124 (données locales antérieures)
; 1.60.1.70124 : version candidate non installée
; 1.60.1.70124 : fichiers hérités d'une version antérieure (decode_rules.json, leveling.json,
  mechanics.json, meta.json, monsters.json, overrides.json, racials.json, respec.json)
; comparaison 1.60.1.70009 (données 5ec8369f724b) -> candidate 1.60.1.70124 (données 66be48468707)
```

La certitude `suppose` et la fraîcheur `stale` de ce bloc portent sur la **candidate non installée**, pas sur le
constat d'absence de changement, qui est `certain` pour les 22 tables comparées.

---

# Inventaire des journaux de combat de ce PC (2026-09-30)

Lecture seule, sur disque, sans réseau. **Rien n'a été ingéré** : ni `forever/data/`, ni `tests/fixtures/`, ni une
mesure. L'ingestion reste l'import de profil de PV1 et `forever measures refresh`.

Noms de compte, de royaume et de personnages **anonymisés** (même règle que `tasks/inventaire-addons.md`).

## Recherche

`Get-ChildItem -Recurse -Filter WoWCombatLog*.txt` sur `C:\Program Files`, `C:\Program Files (x86)` et
`C:\Users\rapha`. **8 journaux réels**, tous dans `<FOREVER_WOW_DIR>\Logs`. Les autres résultats sont des
temporaires de pytest (`AppData\Local\Temp\pytest-of-*`) et la fixture du dépôt
(`tests/fixtures/combatlog/WoWCombatLog-092726_145346.anon.txt`) : hors inventaire.
Il n'existe qu'une installation du client (`C:\Program Files\World of Warcraft\_classic_beta_`).

## Version du jeu par journal

La ligne d'entête du journal donne `COMBAT_LOG_VERSION … BUILD_VERSION 1.60.1` : **tronquée, sans numéro de build**.
`forever logs scan` rend donc `build: "1.60.1"` pour les huit journaux, ce qui ne distingue pas 70009 de 70124.
L'attribution se fait par l'**instant de mise à jour du client**, et non par le journal.

### Instant de la mise à jour

| Preuve | Valeur |
| --- | --- |
| `<WOW>\.build.info`, champ `Version` | `1.60.1.70124` |
| `.build.info`, date de modification | 2026-09-30 **07:46:26** (+0200) |
| `_classic_beta_\WowB.exe`, date de modification | 2026-09-30 **07:46:25** (+0200) |
| `Logs\Client.log` | vide (0 o) : inutilisable |

### Borne basse : les sessions antérieures

| Preuve | Valeur |
| --- | --- |
| `Errors\2026-09-25_13.45.24_Error_21332.txt` | `World of Warcraft: Beta Build (build 70009)` |
| `Errors\2026-09-24_14.58.34_…` | `build 69977` |
| Publication de 1.60.1.70058 (`forever builds`) | 2026-09-29T16:41:04Z = **18:41 local** |
| Fin de la dernière session du 2026-09-29 | **17:43:24 local** |

Entre le 2026-09-25 13:45 (dernier rapport d'erreur, build 70009) et le 2026-09-29 17:43 (fin de la dernière
session), **aucune version n'a été publiée** : 70058 ne paraît qu'à 18:41 ce jour-là. Les sessions du 28 et du 29
sont donc **nécessairement** sous 70009, et les deux sessions du 30 (démarrées à 07:49:51 et 08:59:23, après la
réécriture du binaire à 07:46:25) sous **70124**. Certitude `certain` dans les deux cas.

### Table

| # | Journal | Début → fin | Événements | Version du jeu | Certitude |
| --- | --- | --- | --- | --- | --- |
| 1 | `WoWCombatLog-092826_074711.txt` | 2026-09-28 07:48:33 → 17:17:32 | 121 232 | **1.60.1.70009** | certain |
| 2 | `WoWCombatLog-092926_073012.txt` | 2026-09-29 07:30:12 → 13:29:15 | 45 563 | **1.60.1.70009** | certain |
| 3 | `WoWCombatLog-092926_133000.txt` | 2026-09-29 13:30:00 → 14:22:10 | 8 138 | **1.60.1.70009** | certain |
| 4 | `WoWCombatLog-092926_142301.txt` | 2026-09-29 14:23:01 → 15:35:30 | 12 326 | **1.60.1.70009** | certain |
| 5 | `WoWCombatLog-092926_153751.txt` | 2026-09-29 15:37:51 → 15:59:50 | 4 931 | **1.60.1.70009** | certain |
| 6 | `WoWCombatLog-092926_160122.txt` | 2026-09-29 16:01:22 → 17:43:24 | 13 815 | **1.60.1.70009** | certain |
| 7 | `WoWCombatLog-093026_074951.txt` | 2026-09-30 07:49:51 → 08:58:07 | 7 184 | **1.60.1.70124** | certain |
| 8 | `WoWCombatLog-093026_085923.txt` | 2026-09-30 08:59:23 → 09:34:13 | 4 076 | **1.60.1.70124** | certain |

Total : 217 265 événements, dont **206 005 sous 70009** (journaux 1 à 6) et **11 260 sous 70124** (journaux 7 et 8).

Aucun journal ne chevauche la mise à jour : le journal 6 se termine le 29 à 17:43 et le journal 7 commence le 30 à
07:49, la mise à jour ayant lieu à 07:46. L'attribution est donc possible **par fichier** ici ; elle devra rester
**par session** dans le code, car rien ne garantit qu'un journal ne chevauchera pas une future mise à jour.

## Personnages « à moi »

Classe et race lues dans `ForeverLoggerDB` (`WTF\Account\<compte>\SavedVariables\ForeverLogger.lua`), source directe
et non déduite. Les noms marqués « à moi » par `forever logs scan` concordent avec les trois personnages de
ForeverLogger.

| Personnage | Race | Classe | Royaume | Niveau atteint | Instantanés | Période | Journaux |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | Tauren | **Chasseur** | PvE (Horde) | 4 | 5 | 09-28 07:47 → 09-28 08:31 | 1 |
| B | Orc | **Mage** | PvE (Horde) | 19 | 14 | 09-28 08:32 → 09-30 09:06 | 1, 8 |
| C | Elfe de la nuit | **Chasseur** | PvP (Alliance) | 13 | 31 | 09-29 07:30 → 09-30 08:28 | 2 à 8 |

Le Chasseur que tu évoques correspond à **deux** personnages, A et C, sur deux royaumes et deux factions.

### Conséquence pour l'ingestion

- Le Mage B a des instantanés ForeverLogger **sous 70124** (le dernier, du 09-30 09:06). L'import de profil de PV1
  doit donc porter la version du jeu de chaque instantané, au même titre que les mesures.
- Les journaux 7 et 8 (11 260 événements) ne doivent pas alimenter une mesure attribuée à 70009.

### Lacune constatée dans le code (à combler en T08a)

`forever measures refresh` écrit `monsters.json` dans **le dossier de la version installée**
(`forever/pipeline/refresh.py`, `version_dir = data_dir / new["game_version"]`) et n'enregistre nulle part le build
du client qui a produit le journal mesuré. Rien n'empêche aujourd'hui qu'une mesure faite sous 70124 soit écrite
dans les données de 70009. La règle « ne jamais attribuer à 70009 une mesure faite sous 70124 » n'a donc **aucun
garde-fou** : c'est le bloc C du plan `tasks/T08a-plan.md`.
