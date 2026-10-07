# FA1 — Builds suivis en jeu avec Talents Forever : plan

Demande de l'utilisateur du 2026-10-07, section FA1 de `docs/ROADMAP.md` (décisions 171, 172, 188, 196, 202),
précisée par la commande `/tranche FA1` du même jour (comparaison d'équipement retirée ; six points : export,
numérotation, va-et-vient, builds populaires, recoupement, plugin). Plan écrit sans code ; exécution dans une nouvelle
session, sur la branche `fa1`, un cycle rouge → vert par bloc. **Aucun accès réseau** : tout se lit dans l'addon
installé (`<FOREVER_WOW_DIR>/Interface/AddOns/TalentsForeverBook`).

## Constat du plan (lecture locale du 2026-10-07)

Addon installé : Talents Forever **0.37.1** (`.toc`), `Data.lua` en-tête `build = "1.60.1.70170"`,
`generated = "2026-10-04"`, `codeVersion = "6"` ; builds populaires `asOf` 2026-10-04. Données installées de forever :
**1.60.1.70245** (refonte du Guerrier portée par les correctifs du serveur, T08c à T08e). Le code de l'addon a été lu
pour décrire le format ci-dessous **en nos mots** ; l'implémentation se fera depuis ce plan, jamais depuis
`Core.lua` (aucune licence, décisions 172 et 196).

### Format du code v6 (observé)

- Forme : `<classe>/<niveau>/<arbre 1>-<arbre 2>-<arbre 3>[-<Legacy 1>-<Legacy 2>-<Legacy 3>][-<ordre>]-6`.
  `<classe>` : nom anglais de la classe en minuscules (`mage`) ; `-6` : génération du code (`codeVersion`).
- **Les nœuds n'apparaissent pas dans le code.** Un arbre est une suite de chiffres : le chiffre de rang *j* est le
  rang du *j*-ième talent de la liste `talents` de cet arbre **dans l'ordre de `Data.lua`** ; zéros finaux retirés ;
  segment vide = arbre sans point (`mage/60/--0555323331321331251-6`). Les arbres sont dans l'ordre de `Data.lua`.
  Dans 0.37.1, chaque liste est triée par (rangée, colonne) pour les 9 classes : contrôle, pas hypothèse.
- **Niveau** : l'addon écrit `max(niveau du plan, points + 9 − rang de Talented)`, au plus 60 ; il relit un niveau
  borné à [8, 60].
- **Legacy** : trois segments, seulement quand un perk est pris. Jamais émis par forever (Legacy hors périmètre) ;
  relus tels quels pour le va-et-vient.
- **Ordre** (facultatif) : un symbole par suite de points consécutifs sur le même talent, pris dans l'alphabet de 58
  signes `A`–`Z`, `a`–`z`, `0`, `5`, `6`, `7`, `8`, `9`, indexé par la position du talent **à plat à travers les trois
  arbres** (1er talent du 1er arbre = `A`). Le symbole est suivi d'un chiffre `1`–`4` **seulement** si la suite est
  plus courte que les points qui restent à placer sur ce talent ; sinon le symbole seul prend tout le reste. À la
  relecture, un chiffre `1`–`4` qui suit un symbole est un compte ; `0`, `5`–`9` sont toujours des symboles.
  **Piège du Mage** (54 talents) : Winter's Chill (53e) s'écrit `0` et Ice Barrier (54e) `5`.
- Ordre absent : l'addon place les points arbre par arbre, dans l'ordre des listes.
- Lien : `https://talentsforever.com/<code>`. Le suffixe `?a` est le marqueur de visite propre à l'addon : forever ne
  l'ajoute pas. Import en jeu : `/tf import <code ou lien>` (ou coller dans la fenêtre de partage).
- Générations 1 à 5 (relues par l'addon par noms de talents, `orderV1`…`orderV5`, `renames`) : hors périmètre ;
  forever ne lit et n'écrit que `-6`.

### Builds populaires (bloc `popular` de `Data.lua`, agrégats)

Par classe : `builds` (builds relevés), `window` (fenêtre), `asOf`, `full`, `spec` (part de chaque spécialisation en
%), `top` (5 builds : `code`, `lead` = spécialisation, `pts` par arbre, `rank`, `score`, `shared`, `saved`,
`opened`, `variants`). Les **45 codes** sont des `-6` au niveau 60, **sans ordre ni Legacy**.

### Correspondance des nœuds (installé 0.37.1 face à 1.60.1.70245)

Appariement par **arbre au même indice**, **sort** et **position (rangée, colonne)** :

| Classe | Appariés | Sans correspondance | Export |
| --- | --- | --- | --- |
| Mage | 54/54 | — | possible |
| Guerrier | 52/52 (4 nœuds numérotés autrement : Lingering Rage, Furious Precision, Gore Drinker, Iron Will, DON13) | — | possible |
| Chasseur | 50/51 | forever seul : Improved Serpent Sting (nœud 105003, Marksmanship 4/4) | **bloqué** |
| Démoniste | 50/52 | rangée inconnue chez nous (CLS1) : Improved Life Tap, Amplify Curse | **bloqué** |
| Paladin, Voleur, Prêtre, Chaman, Druide | tous | — | possible |

Autres écarts du recoupement : noms d'arbres (Prêtre « Shadow Magic »/« Shadow », Chaman « Elemental
Combat »/« Elemental » : cosmétiques, arbres appariés par indice), prérequis d'Intimidation du Chasseur (absent chez
nous, présent chez Talents Forever : pièce pour DON5).

### Valeurs relevées pour les tests (brouillon hors dépôt, à refaire par le script de fixture)

- Va-et-vient : les 45 codes ; ex. `mage/60/-0055103013013304-00550003310003002-6` → points par arbre 0/29/22,
  `mage/60/--0555323331321331251-6` → 0/0/51.
- Légalité sur le client (70245) : **44 légaux**, 1 non vérifiable (Démoniste n° 4, points sur Improved Life Tap ou
  Amplify Curse, sans correspondance).
- Nos builds (70245, préréglage `rapide`, graine 12345, `forever build … --json`) :

| Cas | Points | Code attendu |
| --- | --- | --- |
| `leveling-20` | improvedFrostbolt 5, elementalPrecision 3, frostbite 2, iceLance 1 (ordre : 5 + 3 + 2 + 1) | `mage/20/--0530002001-klps-6` |
| `leveling-30` | improvedFrostbolt 5, elementalPrecision 3, frostbite 3, piercingIce 3, frostChanneling 2, iceLance 1, shatter 3, fingersOfFrost 1 | `mage/30/--05300033210003001-klp2sr1prq1w2q1wqz-6` |
| `dungeon-20` | arcaneFocus 5, arcaneConcentration 5, arcaneBlast 1 (aucun ordre : non calculé hors leveling) | `mage/20/0500050001---6` |

- Plus proche build populaire de la même spécialisation (critère du choix 3) : `leveling-20` → n° 3 Frost
  (0 point absent, écart total 40) ; `leveling-30` → n° 3 Frost (0, 30) ; `dungeon-20` → n° 4 Arcane (0, 40).

## À valider (questions décisives, défaut recommandé en premier)

1. **Où vit la table de correspondance ?** *Défaut* : construite **à l'exécution** depuis l'addon installé (jamais
   stockée dans `forever/data/` : ce serait recopier ses données) ; la provenance porte la version de l'addon, l'en-tête
   de `Data.lua` et son empreinte ; addon absent → bloc d'export `absent` avec une note, jamais une erreur. Les tests
   lisent une fixture dérivée (nos clés dans l'ordre de ses listes, écarts) et un `Data.lua` synthétique écrit dans
   `tmp_path`. *Autre* : fichier `talents_forever.json` versionné par version du jeu (export sans l'addon, mais une
   attente de `forever update` à chaque mise à jour de l'addon).
2. **Ordre des contextes sans ordre calculé** (donjon, raid, PvP : l'optimiseur ne rend un ordre qu'en leveling).
   *Défaut* : code sans segment d'ordre, avec la note « ordre non calculé pour ce contexte : Talents Forever place les
   points arbre par arbre ». *Autre* : un ordre légal construit palier par palier, signalé non calculé.
3. **« Au plus proche »**. *Défaut* : builds populaires de la même spécialisation (arbre le plus chargé de notre build ;
   à défaut, tous, avec une note) ; classement par **points de notre build absents du sien** (Σ max(0, nous − lui)),
   puis écart total (Σ |nous − lui|), puis rang populaire ; rendu : rang, spécialisation, code, lien, points absents,
   points à ajouter, écart total, différences par talent. Tous ses builds sont au niveau 60 : à bas niveau, les points
   absents disent si notre build est une étape de sa route.
4. **Export secondaire vers Naowh Forever (`!NFB1!`)** : *défaut* hors périmètre (repris en EX1) ; *autre* : dans FA1.
5. **Test en jeu** : *défaut* procédure dans `docs/ADDON.md` (§ 7), faite par l'utilisateur avant le 21 octobre, non
   bloquante pour la fusion (« Bloqué sur moi » du résumé) ; s'il colle un code **avec ordre** relevé en jeu
   (`/tf`, partage), il entre en fixture comme témoin indépendant de notre encodeur. *Autre* : fusion après le test.

## Choix proposés (sans question, à confirmer à la validation)

- **Appariement strict** : arbre au même indice + sort + rangée + colonne, une seule correspondance ; tout le reste
  est « sans correspondance » avec sa raison (`seulement_forever`, `seulement_talents_forever`, `position_inconnue`,
  `ambigu`). **Un talent sans correspondance bloque l'export de sa classe** (ROADMAP) ; le décodage d'un code de cette
  classe reste possible, et un build qui met des points sur un talent sans correspondance est « non vérifiable ».
- **Contrôles de l'addon à la lecture** : `codeVersion` = `"6"` (sinon export `format_non_pris_en_charge`) ; listes
  triées par (rangée, colonne) ; 3 arbres ; au plus 58 talents par classe. Un contrôle raté bloque l'export avec sa
  raison, jamais une exception dans `forever build`.
- **Niveau du code** = niveau du build. Avec `talented_bonus` > 0, la provenance signale que l'addon lit le rang de
  Talented en jeu (même rang attendu).
- **Ordre** : pas de l'ordre de `build_report` dont `talent` est non nul ; contrôle : la somme des pas de chaque talent
  = son rang (sinon export bloqué, raison `ordre_incoherent`).
- **Certitude** : export `probable` (format réimplémenté, recoupé par va-et-vient, pas encore relu en jeu ; `certain`
  après le test en jeu) ; builds populaires `suppose` (choix de joueurs, décision 127).
- **`forever addons status`** : rien dans le dépôt ne dépend plus de l'addon (table à l'exécution) → `depends` de
  `TalentsForeverBook` vidé (plus d'attente `addon_data` à chaque mise à jour de l'addon) ; la relecture
  (`_talents_recheck`) rend, en plus des comptes du recoupement, l'état de l'export par classe (possible ou bloqué,
  talents en cause) et `codeVersion` pris en charge ou non ; `action` pointe vers `forever talents tf crosscheck`.
- **`build_report` inchangé** : l'addon n'est pas une entrée du moteur. Le bloc `export` est ajouté au rapport par
  `attach_export(deps, report)`, appelé par la CLI (`forever build`) et par l'outil MCP `forever_build` ; le rejeu des
  builds (`scripts/replay_builds.py`, chaîne de `forever update` dans le clone sans addon) et `engine_inputs.py` ne
  voient rien de nouveau.
- **Positions de liste brutes** : la disposition se lit dans les listes `talents` de chaque arbre de `Data.lua`, dans
  leur ordre, jamais par `read_trees` (qui ré-indexe par nœud et perd la position, seule base de l'index plat).
- **Spécialisation appariée par indice d'arbre** : le `lead` d'un build populaire (noms de l'addon : « Shadow »,
  « Elemental ») donne l'indice de son arbre, apparié au nôtre ; jamais par nom.
- **Modules** : le format est une règle d'échange, pas une formule de combat : il ne va pas dans `forever/engine/`.
  Codec pur dans `forever/tf_code.py` ; lecture de l'addon, table, export, builds populaires et comparaison dans
  `forever/talents_forever.py` ; `forever/pipeline/talents_forever.py` garde la lecture brute et le recoupement.

## Contexte du code (lecture du plan)

- `forever/pipeline/talents_forever.py` : `read_head_and_doc`, `read_trees` (nœuds de l'addon), `our_trees`,
  `compare`, `crosscheck` (comptes) ; appelé par `scripts/compare_talents_forever.py` et `forever/addons.py`
  (`_talents_recheck`, `content_version`).
- `forever/build.py` : `BuildReport` ; `order` rempli seulement en leveling (`optimize_leveling`), vide sinon.
- `forever/engine/talents.py::check_class_build` et `forever/lookup.py::check_talents` : légalité sur le client (G3).
- `forever/data/<version>/classes.json` : par classe, arbres (ordre des onglets du client), talents avec `key`,
  `node_id`, `spell_id`, `tier`, `col`, `max`, `prereqs`.
- `Deps.wow_dir` : dossier du client (addons lus sur disque).
- `plugin/skills/forever-builds`, `forever-mage`, `forever-leveling` ; `plugin/evals/` (66 cas, 44 positifs, 22
  négatifs, `POSITIVE_COUNTS` par catégorie dans `tests/unit/test_plugin_evals.py`).

## Blocs et étapes

### Étape 0 — Fixtures (avant tout autre travail)

- `scripts/extract_talents_forever_fixture.py` (lecture locale, écriture `write_bytes`, LF) écrit dans
  `tests/fixtures/talents_forever/` :
  - `popular.json` : en-tête de l'addon (version `.toc`, `build`, `generated`, `codeVersion`), par classe `builds`,
    `window`, `asOf`, `full`, `spec`, et pour chaque build `code`, `lead`, `pts`, `rank` (agrégats, décision 172) ;
  - `layout.json` : par classe, arbres de l'addon dans son ordre (indice de notre arbre apparié), et pour chaque
    position de liste notre `key`, ou pour une position sans correspondance son sort, sa rangée, sa colonne et ses
    rangs (écart du recoupement) ; nos talents sans correspondance avec leur raison ;
  - `mage_builds.json` : les trois cas `leveling-20`, `leveling-30`, `dungeon-20` (points et ordre de
    `forever build … --preset rapide --sensitivity off --json`, version, graine), et les codes attendus.
- `tests/fixtures/talents_forever/README.md` : source, date, commande, ce qui n'est pas recopié.
- Aide de test `tests/talents_forever_data.py` : écrit dans `tmp_path` un `Data.lua` synthétique (en-tête, arbres
  reconstruits depuis `classes.json` + `layout.json`, bloc `popular` depuis `popular.json`), pour passer par le vrai
  lecteur sans copie de l'addon.

### Bloc 0 — Feuille de route et décisions

ROADMAP FA1 (format v6 décrit, données installées 70245, choix validés), `docs/DECISIONS.md` (décision 209 : choix
1 à 5 validés), `docs/DATA_SOURCES.md` et `tasks/inventaire-addons.md` (v5 → v6).

### Bloc A — Codec v6 (pur)

`forever/tf_code.py` : lecture et écriture d'un code sur une disposition abstraite (rangs maximaux par arbre), sans
aucune donnée de l'addon. Tests : `tests/unit/test_tf_code.py`.

### Bloc B — Table de correspondance et recoupement

`forever/talents_forever.py::load_layout` (lecture de l'addon installé, contrôles, appariement), `crosscheck_report`
(écarts classés : nœud numéroté autrement, sans correspondance, position inconnue, prérequis, nom d'arbre), CLI
`forever talents tf crosscheck [--out <md>]` ; rapport `docs/research/talents-forever-FA1.md` (en-tête : addon 0.37.1,
`Data.lua` 70170 + correctifs des 1er et 2 octobre, face à 1.60.1.70245 installée). Relecture de `forever addons
status` (choix ci-dessus). Tests : `tests/unit/test_talents_forever_layout.py`, `tests/unit/test_addons_status.py`.

### Bloc C — Export dans `forever build` et `forever_build`

`export_build`, `attach_export` (bloc `export` ajouté par la CLI texte et JSON et par le MCP, `build_report`
inchangé) ; décodage `forever talents tf decode
<code|lien> [--level]` (classe, niveau, points en nos clés, ordre, légalité). Tests :
`tests/unit/test_talents_forever_export.py`, `tests/unit/test_build_cli.py`, tests MCP.

### Bloc D — Builds populaires et comparaison

`popular_builds` (lecture du bloc `popular`, légalité par `check_talents`), `closest_popular` (choix 3), CLI
`forever talents tf popular [--class <classe>]`, MCP `forever_lookup(kind="tf_popular", name=<classe>)` ; bloc
`closest_popular` dans l'export du Mage. Tests : `tests/unit/test_talents_forever_popular.py`.

### Bloc E — Plugin, évaluation, documentation

Skills `forever-builds` (builds populaires de Talents Forever avant le chercheur web pour les 8 autres classes ;
lien du build calculé), `forever-mage` et `forever-leveling` (lien et `/tf import <code>` relayés tels quels depuis
`export.talents_forever` ; **aucun code réel dans un `SKILL.md`**, des rangs de talents sont des chiffres de jeu) ;
routeur si besoin. Quatre cas d'évaluation (ci-dessous). `docs/ADDON.md` § 7 (procédure en jeu), `docs/ARCHITECTURE.md`
(modules, outil), `docs/USAGE.md` (commandes), ROADMAP « Réalisé », `docs/OPEN_QUESTIONS.md`. Tests :
`tests/unit/test_plugin_evals.py` (comptes), test du skill sans chiffre (existant).

## Fichiers

| Fichier | Changement |
| --- | --- |
| `forever/tf_code.py` | nouveau : codec v6 pur |
| `forever/talents_forever.py` | nouveau : disposition de l'addon, correspondance, export, builds populaires, plus proche |
| `forever/pipeline/talents_forever.py` | lecture du bloc `popular` ; recoupement enrichi (classes d'écarts) |
| `forever/build.py` | inchangé (le bloc `export` est ajouté hors de `build_report`) |
| `forever/cli.py` | `forever talents tf decode|popular|crosscheck` ; ligne « Talents Forever » de `forever build` |
| `forever/mcp_server.py` | `forever_build` porte `export` ; `forever_lookup(kind="tf_popular")` |
| `forever/addons.py` | `TalentsForeverBook` : `depends` vidé, relecture enrichie, `action` |
| `scripts/extract_talents_forever_fixture.py` | nouveau : fixtures (lecture locale) |
| `scripts/compare_talents_forever.py` | renvoie vers la CLI ou garde son rôle (rapport T08c) |
| `tests/fixtures/talents_forever/` | `popular.json`, `layout.json`, `mage_builds.json`, `README.md` |
| `tests/talents_forever_data.py` | aide : `Data.lua` synthétique dans `tmp_path` |
| `tests/unit/test_tf_code.py`, `test_talents_forever_layout.py`, `test_talents_forever_export.py`, `test_talents_forever_popular.py` | nouveaux |
| `tests/unit/test_build_cli.py`, `test_addons_status.py`, `test_plugin_evals.py`, tests MCP | mis à jour |
| `plugin/skills/forever-builds|forever-mage|forever-leveling/SKILL.md` | lien Talents Forever, builds populaires |
| `plugin/evals/` | 4 cas |
| `docs/…` | ROADMAP, DECISIONS (209), DATA_SOURCES, ADDON, ARCHITECTURE, USAGE, OPEN_QUESTIONS, rapport de recherche |
| `tasks/inventaire-addons.md` | format v6, usage FA1 fait |

## Interfaces

```
# forever/tf_code.py
CODE_VERSION = "6"; SYMBOLS: str (58 signes)
@dataclass(frozen=True) class TfPlan:
    class_slug: str; level: int; ranks: tuple[tuple[int, ...], ...]   # par arbre, par position de liste
    order: tuple[tuple[int, int], ...] | None                        # (arbre, position), un pas par point
    legacy: tuple[str, ...] | None                                    # segments bruts, relus pour le va-et-vient
def encode(plan: TfPlan) -> str
def decode(code: str, max_ranks: Sequence[Sequence[int]]) -> TfPlan   # lien ou code ; ValueError en français
def link(code: str) -> str                                            # https://talentsforever.com/<code>

# forever/talents_forever.py
@dataclass(frozen=True) class TfLayout:   # une classe
    file: str; slug: str; trees: tuple[tuple[str | None, ...], ...]   # notre clé par position, None sans correspondance
    max_ranks: tuple[tuple[int, ...], ...]; unmatched: tuple[dict, ...]; exportable: bool
@dataclass(frozen=True) class TfAddon:
    version: str; head: dict; fingerprint: str; layouts: dict[str, TfLayout]; checks: list[str]
def load_addon(deps: Deps) -> TfAddon | None                          # None : addon absent
def export_build(addon: TfAddon | None, class_name: str, level: int, talents: Mapping[str, int],
                 order: Sequence[str] | None, talented_bonus: int = 0) -> dict   # bloc export.talents_forever
def decode_code(addon: TfAddon, deps: Deps, code: str) -> dict        # nos clés, ordre, légalité
def popular_builds(addon: TfAddon, deps: Deps, class_name: str | None) -> dict
def closest_popular(popular: dict, class_name: str, talents: Mapping[str, int]) -> dict | None
```

Bloc `export.talents_forever` de `forever build` : `status` (`ok`, `absent`, `bloque`, `format_non_pris_en_charge`,
`ordre_incoherent`), `reason`, `code`, `link`, `import` (`/tf import <code>`), `level`, `order_included`,
`order_note`, `closest_popular`, `certainty`, `provenance` (`format` v6, version de l'addon, `build`, `generated`,
`codeVersion`, empreinte de `Data.lua`, `talented_note`).

## Tests attendus

Bloc A (`test_tf_code.py`, rapides) :
- Va-et-vient exact des 45 codes de `popular.json` : `encode(decode(c)) == c` ; somme des chiffres de chaque arbre =
  `pts` (ex. `mage/60/-0055103013013304-00550003310003002-6` → 0/29/22 ; `mage/60/--0555323331321331251-6` → 0/0/51).
- Ordre : Givre seul, improvedFrostbolt ×2, elementalPrecision ×1, improvedFrostbolt ×3, elementalPrecision ×2 →
  segment `k2l1kl` ; relu : mêmes rangs et même ordre.
- Symboles `0` et `5` : wintersChill 5 en une suite puis iceBarrier 1 → `05` relu comme deux symboles ; wintersChill
  ×2, iceBarrier ×1, wintersChill ×3 → `0250` (`2` compte, `5` symbole, dernier `0` sans compte).
- Segment vide et zéros finaux ; code sans ordre → `order` None ; lien `https://talentsforever.com/` + code, sans `?a`
  ; lien collé avec `?a` ou `#…` relu.
- Refus : génération `-5`, classe inconnue, forme invalide, plus de 58 talents (message en français).

Bloc B (`test_talents_forever_layout.py`, `Data.lua` synthétique) :
- Mage : 54 appariés, `exportable` ; Guerrier : 52 appariés malgré 4 nœuds numérotés autrement (DON13) ;
  Chasseur : bloqué, `improvedSerpentSting` `seulement_forever` ; Démoniste : bloqué, `improvedLifeTap` et
  `amplifyCurse` `position_inconnue`.
- Arbres appariés par indice : écarts de nom du Prêtre et du Chaman classés cosmétiques, sans blocage.
- Contrôles : `codeVersion` `"7"` → `format_non_pris_en_charge` ; liste non triée → blocage nommé ; addon absent →
  `load_addon` None.
- Recoupement de la version installée (fixture) : écarts listés (nœuds numérotés autrement 4, sans correspondance 3,
  prérequis 1, noms d'arbres 2) ; rendu du rapport déterministe.
- `forever addons status` : addon changé → relecture avec l'état de l'export par classe, sans proposition `addon_data`.

Bloc C (`test_talents_forever_export.py`, `test_build_cli.py`, tests MCP) :
- Les trois cas de `mage_builds.json` : `export_build` rend exactement `mage/20/--0530002001-klps-6`,
  `mage/30/--05300033210003001-klp2sr1prq1w2q1wqz-6`, `mage/20/0500050001---6` ; relus, mêmes points et même ordre
  (donjon : sans ordre, `order_note`).
- Talent du Mage sans correspondance (disposition modifiée) → `bloque`, talent nommé, pas de code ; addon absent →
  `absent` avec note ; ordre dont un talent a plus de pas que de rangs → `ordre_incoherent`.
- `talented_bonus` 1 : niveau du code = niveau du build, `talented_note` présente.
- Provenance : format `v6`, version 0.37.1, `build`, `generated`, `codeVersion`, empreinte ; certitude `probable`.
- `slow` : `build_report` leveling 20 (préréglage `rapide`) avec un `Data.lua` synthétique → `export.talents_forever`
  relu = `talents` et `order` du rapport, niveau `mage/20/` ; même contrôle par l'outil MCP `forever_build` (import de
  `mcp` dans le module) ; ligne « Talents Forever » de la sortie texte de la CLI.
- `forever talents tf decode` : code du cas `leveling-30` → nos clés, ordre, « légal ».

Bloc D (`test_talents_forever_popular.py`) :
- 9 classes, 5 builds chacune ; Mage : parts Fire 44, Frost 34, Arcane 22, `asOf` 2026-10-04, `builds` 41203 ;
  certitude `suppose` ; provenance (version de l'addon, `asOf`, fenêtre).
- Légalité sur le client : 44 légaux, Démoniste n° 4 « non vérifiable » (talents sans correspondance nommés).
- Plus proche, déterministe : `leveling-20` → n° 3 Frost, 0 point absent, écart total 40 ; `leveling-30` → n° 3 Frost,
  0, 30 ; `dungeon-20` → n° 4 Arcane, 0, 40 ; différences par talent triées.
- MCP `forever_lookup(kind="tf_popular", name="Rogue")` : 5 builds, liens, `suppose`.

Bloc E :
- `test_plugin_evals.py` : 66 → **70** cas, positifs 44 → **47**, négatifs 22 → **23**, `POSITIVE_COUNTS` mis à jour
  (catégories des trois cas positifs), comptes négatifs (`== 22` → 23).
- Cas : `build-lien-talents-forever` (« Donne-moi mon build de leveling niveau 20 avec le lien Talents Forever » :
  `forever_build` leveling, regex `talentsforever\.com/mage/\d+/`, certitude, provenance, skill) ;
  `builds-populaires-voleur` (`forever_lookup` `tf_popular`, regex « suppos », date `2026-\d\d-\d\d`) ;
  `build-proche-populaire` (« Mon build de donjon niveau 20 ressemble-t-il à un build populaire ? » : `forever_build`
  dungeon, regex « point ») ; négatif voisin `neg-retail-loadout-talents` (chaîne d'import de talents de retail).
- Skills : aucun chiffre de jeu (contrôle existant).

Registre : **aucune mécanique de combat ajoutée ni modifiée** (format d'échange, lecture de l'addon) ;
`test_registry.py` inchangé. La légalité (G3) est appelée telle quelle.

## Hors périmètre

Legacy dans l'export (relu seulement pour le va-et-vient) ; générations de code 1 à 5 ; format de chaîne de Blizzard
de l'addon ; suffixe `?a` ; export vers Naowh Forever (`!NFB1!`, EX1, choix 4) ; écriture de `TalentsForeverBookDB` ;
toute copie du code ou de `Data.lua` dans le dépôt (seuls les agrégats de la fixture) ; talent suivant affiché en jeu ;
comparaison d'équipement (décision 202) ; lien cliquable en jeu (P06b) ; ordre construit hors leveling (choix 2) ;
réseau.

## Risques

- **Format mal compris** (ordre surtout, aucun code populaire n'en porte) : va-et-vient sur nos builds, cas
  synthétiques des comptes partiels et des symboles `0`/`5`, et test en jeu (choix 5) ; certitude `probable` tant
  que le test en jeu n'est pas fait.
- **Mise à jour de l'addon** (quasi quotidienne pour les builds populaires ; `codeVersion` 7 un jour) : table refaite
  à l'exécution, contrôles qui bloquent proprement ; tests sur fixture, jamais sur le dossier réel.
- **Valeurs attendues liées au moteur** : les tests rapides partent des points et de l'ordre figés de
  `mage_builds.json` ; le test `slow` vérifie une propriété (relu = rapport), pas un code littéral.
- **Données de l'addon dans le dépôt** : fixture limitée aux agrégats ; le `Data.lua` des tests est reconstruit depuis
  `classes.json` ; relecture du diff avant commit.
- **Fins de ligne** : fixtures écrites en `write_bytes` (LF) ; `git diff --stat` contrôlé.
- **Tests MCP sous Windows** : importer `mcp` dans le module (piège T06b).
- **Comptes** : bloc `export` ajouté par la CLI et le MCP (tests de clés de leur sortie) ; évaluations (70/47/23).

## Angles morts attendus (à chiffrer en fin de tranche)

- Ordre absent hors leveling (donjon, raid, PvP) : l'addon place les points arbre par arbre ; effet : ordre de prise
  non optimisé dans ces contextes, sans effet sur le build final.
- Talented (Legacy) : niveau du code juste, mais le pas de chaque point dépend du rang lu en jeu par l'addon.
- Builds populaires tous au niveau 60 : comparaison à bas niveau par inclusion seulement (points absents).

## Questions ouvertes à ajouter

- **CLS1** (mise à jour) : Talents Forever place Improved Life Tap en rangée 1 et Amplify Curse en rangée 3 (indice,
  `suppose`) ; relevé en jeu toujours nécessaire.
- **DON5** (mise à jour) : Talents Forever donne un prérequis à Intimidation que notre décodage n'a pas.
- **CLS3** (nouvelle) : Improved Serpent Sting (nœud 105003, Marksmanship rangée 4, colonne 4) est-il dans l'arbre en
  jeu ? Absent de Talents Forever. Test : arbre du Chasseur en jeu. Priorité : basse (bloque l'export du Chasseur, qui
  n'a pas de build calculé).

## Critères de fin

- Va-et-vient exact des 45 codes de la fixture ; nos trois builds du Mage rendent les codes attendus et se relisent
  sur les mêmes points et le même ordre.
- `forever build` (CLI) et `forever_build` (MCP) rendent code, lien, import et plus proche build populaire, avec
  provenance et certitude ; addon absent ou classe bloquée signalés, jamais devinés.
- Builds populaires lus sur fixture, sans réseau, avec part, date et légalité ; comparaison déterministe, `suppose`.
- Recoupement de 1.60.1.70245 rendu (`docs/research/talents-forever-FA1.md`) : chaque écart listé.
- Procédure de test en jeu dans `docs/ADDON.md` ; quatre cas d'évaluation ajoutés.
- `uv run tasks.py verify` vert ; CI verte sous Ubuntu et Windows.

## Validation

En attente des réponses aux questions 1 à 5 (« À valider ») et des choix proposés.
