# EX1 — Exports vers les addons d'interface : plan

Tranche de la ROADMAP (section « EX1 — Exports vers les addons d'interface : profils EllesmereUI et macros »),
fondée sur les décisions 195, 196, 243, 247, 251, 255 et 264. Plan écrit le 2026-10-14. **Exécution avancée à la
demande de l'utilisateur** : avant la fin de la bêta (21 octobre), pour que les imports puissent être essayés en jeu
s'il en a envie (tests en jeu facultatifs, décision 247) ; cela amende l'ordre de la décision 251 (EX1 après LN1) :
nouvelle décision 267 au bloc 0. LN1 garde sa borne (au plus tard le 24 octobre) : si EX1 n'est pas finie le 21 au
soir, les blocs restants passent après LN1. Branche `ex1`, un cycle rouge → vert par bloc. Aucun accès réseau dans le
code ni les tests ; aucune dépendance Python nouvelle.

## Demande de l'utilisateur (2026-10-14)

1. Talents vers Naowh Forever : format `!NFB1!` du module Training, réimplémenté d'après l'observation sans recopier
   le code de Naowh, tests de va-et-vient ; le chat donne pour chaque build le lien Talents Forever **et** le code
   Naowh.
2. Profils EllesmereUI par classe et par rôle (`!EUI_`) et macros utiles par classe, selon la ROADMAP.
3. BiS `!NBIS1!` et poids `NFSW1:` (T10a) préparés côté format, remplis seulement quand T10a sera faite.
4. Un bouton ou une commande dans le chat pour copier chaque export dans le panneau d'action, comme le lien Talents
   Forever.

## Étude de l'existant (décision 264 ; 2026-10-14, lecture seule)

Recherche web (GitHub, PyPI, CurseForge, Wago, sites Forever) et lecture locale des addons installés. Rien
téléchargé ni installé.

| Trouvaille | Licence | Fraîcheur | Réutilisable | Verdict |
| --- | --- | --- | --- | --- |
| rossnichols/LibSerialize (spécification « Encoding format » du README) | MIT | MINOR 7 embarquée chez Naowh | description octet par octet des types | **Réutiliser comme spécification** : sérialiseur et lecteur Python écrits d'après elle |
| SafeteeWoW/LibDeflate (`EncodeForPrint`, `CompressDeflate`) | zlib | 1.0.2, même copie chez Naowh et EllesmereUI | alphabet 6 bits `a-zA-Z0-9()`, poids faible d'abord, sans remplissage ; deflate brut RFC 1951 | **Réutiliser** : `zlib` de la bibliothèque standard (`wbits=-15`) + encodeur 6 bits écrit d'après la doc |
| weakauras-codec (Rust, codeberg Velithris) | MIT (option GPL désactivée) | v0.1.2, 24/09/2026 | sous-crates LibSerialize et 6 bits | **Recouper** : lecture d'algorithme seulement |
| node-weakauras-parser | distribution GPLv2 | v3.2.11 | codec complet | **Écarter** (GPL, module natif Node) |
| python-weakauras-tool (geexmmo) | aucune | ancien | Lua de WeakAuras appelé par lupa | **Écarter** le code ; l'idée d'un oracle lupa est reprise (bloc A) |
| softcreatr/weakauras-decoder (PHP), LetsTimeIt/mdt-compression (TS) | non vérifiée ; GPL-3.0 | abandonné ; AceSerializer | — | **Écarter** |
| Naowh Forever (github.com/naowh-gaming/NaowhForever ; installé 1.1.12) | tous droits réservés | 1.1.12, 14/10/2026 | formats `!NFB1!`, `!NFM1!`, `!NBIS1!`, `NFSW1:` décrits ci-dessous | **Format oui, code non** (décision 196) |
| EllesmereUI (EllesmereGaming ; installé 9.5.4) | propriétaire | 9.5.4 | format `!EUI_`, API `SwitchProfile`, `ImportProfileSilent` | **Format oui, code non** |
| talentsforever.com | données CC BY 4.0 | active | partage par URL ; aucun export Naowh | **Écarter** pour EX1 (FA1 couvre Talents Forever) |
| Calculateurs Forever (seemeta, mobalytics, zockify, icy-veins) | non vérifiée | 2026 | partage par URL | **Écarter** |
| ForeverForge Macros, Forever Macro Creator (CurseForge), kami-labs.fr (240 macros), rankedboost | tous droits réservés ou non vérifiée | octobre 2026 | macros écrites à la main, aucune chaîne d'export | **Recouper les idées** (`/cast` sans rang), rien recopié |
| LibAddonProfiles (Wago) | — | introuvable | contrat cité par EllesmereUI | **Écarté** : on s'en tient aux fonctions lues dans EllesmereUI 9.5.4 |

Aucun générateur tiers de `!NFB1!`, `!NFM1!` ou `!EUI_` n'existe. Le travail propre est un codec d'environ 300 lignes
(LibSerialize, 6 bits, deflate de la bibliothèque standard) et un sérialiseur EllesmereUI d'environ 100 lignes.

## Constats (addons installés, 2026-10-14 ; aucun code recopié, chemins `fichier:ligne` pour la relecture)

Changements depuis `tasks/inventaire-addons.md` (Naowh 0.5.25-beta, EllesmereUI 9.3.8) à reporter dans l'inventaire
au bloc 0 : Naowh ne vise plus que l'interface 16001, fichiers réorganisés, **plus de `/nftraining` ni `/nfbis`**
(seulement `/nf` → Profiles → Import, qui aiguille par préfixe, et le bouton Import de chaque fenêtre) ; EllesmereUI
importe dans un **profil nommé** (copie du profil actif recouverte), plus dans le profil actif.

- **Chaîne commune Naowh** : préfixe + `EncodeForPrint(CompressDeflate(LibSerialize:Serialize(t)))`, options par
  défaut, niveau de compression non fixé (celui de LibDeflate, qui dépend de la taille). Lecture : 6 bits, contrôle
  de taille avant décompression, deflate, désérialisation ; seuls nombres finis, chaînes, booléens et tables
  (`NaowhForever/Shared/Decode.lua:261-275`) ; limites 100 000 caractères, 1 Mio, profondeur 8, 20 000 valeurs.
  Toute sortie deflate valide passe : **les octets ne seront pas identiques à ceux de Naowh**, le va-et-vient se juge
  sur la table décodée.
- **`!NFB1!`** (`NaowhForever_Training/Builds.lua:10, 17, 124-187`) : `{v=1, class=<identifiant numérique de
  classe>, name, spec=<nom de l'arbre dominant, texte libre>, points={TraitNodeID, un par point, dans l'ordre de
  prise}, skip=<facultatif>}` ; au plus 51 points, au moins un ; `CheckBuild` refuse un nœud hors de l'arbre, un rang
  au-delà du maximum, un prérequis pas à plein rang, un palier sans 5 × (palier − 1) points dans le même arbre
  **au moment de la prise** ; nom et spécialisation tronqués à 40 caractères ; import confirmé par une fenêtre ;
  apprentissage par `C_Traits` hors combat. **Nos données ont déjà tout** : `classes.json` porte l'`id` de la classe
  et le `node_id` (TraitNodeID) de chacun des 997 talents ; le nœud de Ice Block relevé chez Naowh
  (`Data/TrainingBuilds.lua:355`) est celui de notre `classes.json`. Aucun build livré par Naowh ; la sauvegarde de
  l'utilisateur n'a qu'un build vide : **pas de chaîne réelle** (question NFB1 ouverte).
- **`!NFM1!`** (`NaowhForever_Macros/Sharing.lua:8, 42-137`, `Constants.lua:5-10`) : `{v=1, macros={{name, body}…}}`,
  pas d'icône ; nom de 1 à 16 octets, corps d'au plus 255 octets ; **une macro invalide rejette toute la chaîne** ;
  alerte sur `/run`, `/script`, `/dump`, sur les commandes d'addons et les commandes inconnues ; macros de personnage,
  hors combat, nom déjà pris ignoré.
- **`!NBIS1!`** (`NaowhForever_BiS/BiS/Sharing.lua:11, 27-29, 100-106`) : export en `v=4`, `{v, name, spec,
  slots={[emplacement]=objet}, extra={[emplacement]={objets…}}}` ; emplacements d'inventaire 1 à 18 sans le 4 ;
  28 clés de spécialisation (`arcane-mage`, `feral-tank-druid`…). **`NFSW1:`** (`StatWeights/Sharing.lua:6-93`) :
  texte clair `NFSW1:<clé>:<stat>=<poids>,…`, poids en chiffres et point seulement (jamais de notation `e`), moins de
  1 000, 27 clés de statistiques (`StatWeights.lua:11-27`), poids par point, ou par 1 % pour les statistiques en
  pourcentage ; l'import remet d'abord la spécialisation à zéro.
- **API Naowh** : seule `NaowhForever_API:ImportProfile` (`NFPROFILE1:`) est publique, et elle importe **sans
  confirmation** et remplace un profil : **écartée** (le joueur colle lui-même chaque chaîne, décision 196).
- **`!EUI_`** (`EllesmereUI/EllesmereUI_Profiles.lua:243-355, 1892, 2808-2860, 3215-3503`) : sérialiseur maison
  (chaîne `s<longueur>:<octets>`, nombre `n<texte>;`, `T`, `F`, `N`, table `{` partie tableau puis paires `K<clé><valeur>`
  `}` ; ordre des clés non fixé chez eux) ; enveloppe `{version=3, type="full", data, meta, client="forever"}` ;
  version autre que 3 refusée ; import dans un profil nommé puis activé (sauf si la spécialisation courante est
  affectée à un autre profil), rechargement demandé. `data.cdmSpells[<clé de spécialisation>].barSpells.<barre>.
  assignedSpells` = liste de sorts ; sur Forever la clé de la classe est renommée à l'export (`:1926-1937`) : **on
  reprend la clé présente dans le profil de base**, sans table de spécialisations à nous. Rappels de buffs :
  `data.addons.EllesmereUIAuraBuffReminders.forever.customIDs` (liste ordonnée de sorts).
  API : `SwitchProfile(nom)` (`:3845`, sans garde de combat, sans effet si le nom est inconnu),
  `GetActiveProfileName()`, `GetProfileList()`, `ImportProfileSilent{…}` (refusée en combat). **Aucune fonction
  publique d'affectation spécialisation → profil**, et EllesmereUI rebascule lui-même au `PLAYER_ENTERING_WORLD` si la
  spécialisation est affectée.
- **Bloc Broker** (`EllesmereUIDataBars/Blocks/LDB.lua:30-212`) : lit tout objet LibDataBroker nommé (`text`, `label`,
  `icon`, `OnClick`, `OnTooltipShow` sous `pcall`). LibStub et LibDataBroker-1.1 sont chargés par EllesmereUI.
- **Bibliothèques** : LibSerialize MINOR 7, MIT (en-tête) ; LibDeflate 1.0.2, zlib (`LICENSE.txt`). Lupa du dépôt :
  2.8, **Lua 5.5**.

## Contexte du code (2026-10-14)

- FA1 : `forever/tf_code.py` (codec v6), `forever/talents_forever.py` (`export_build` l.488, `attach_export` l.575,
  `popular_builds` l.761, `closest_popular` l.817) ; build calculé : `BuildReport.talents` et `.order` (clés,
  leveling seulement) ; builds populaires : `talents{clé: rang}` sans ordre ; builds de la communauté : contrôlés par
  `forever_lookup(kind="build_check")`, rien de stocké. Table nœud ↔ clé : `forever/bridge/context.py:45-61`.
- Pont : une réponse n'a **qu'un champ `link`** (`forever/bridge/loop.py:630`, `slots.py:102`) ; l'addon l'imprime
  `[Talents Forever]` cliquable (`ForeverBridge.lua:623-639`) qui ouvre la boîte de copie du panneau unique
  (`FB.ShowCopy` l.1090, `BuildPanel` l.836). Boutons : `forever/bridge/buttons.py` (`DONE_SLICES`, `BUTTONS`) ;
  actions fermées : `forever/bridge/actions.py:19-34`.
- Sorts par classe et rang au niveau : `classes.json` → `spells.<clé>.ranks[{spell_id, rank, level…}]` ;
  `_rank_index` (`forever/pvp.py:48`, privée). Aucune donnée « buff de classe » ni « rôle » ; le profil n'a pas de
  rôle.
- Aucun codec LibSerialize, 6 bits ou LibDeflate dans le dépôt ; deflate brut déjà utilisé en lecture
  (`forever/pipeline/travel_sources.py:139`). Sérialiseur de tables Lua en texte : `forever/bridge/slots.py:65-100`.
- Règles d'addon : `scripts/check_addon.py` n'interdit pas encore `CreateMacro` (interdit par `docs/ADDON.md:16`) :
  ajout au bloc D.

## À valider (cinq questions ; défaut proposé en premier)

1. **Oracle Lua des tests.** *Défaut* : copier dans `tests/fixtures/third_party/` `LibSerialize.lua` (MIT) et le
   dossier `LibDeflate` (zlib), avec leur licence, tels que livrés par Naowh 1.1.12 (provenance et empreinte dans un
   `README.md`), pour que chaque chaîne produite par Python soit relue par les vraies bibliothèques sous lupa, et
   l'inverse ; jamais livrées avec un addon. *Autre* : vecteurs écrits à la main seulement (pas de copie, mais aucune
   preuve d'interopérabilité avant un essai en jeu).
2. **Ordre des points d'un build sans ordre** (builds populaires de Talents Forever, builds de la communauté, build
   calculé hors leveling). Naowh exige un ordre légal à chaque prise. *Défaut* : ordre légal généré par une fonction
   pure (palier croissant, prérequis d'abord, arbre dominant d'abord), signalé « ordre généré, pas un ordre de
   leveling » dans la réponse. *Autre* : pas de code Naowh pour un build sans ordre.
3. **Profil de base EllesmereUI.** *Défaut* : lu en local dans la sauvegarde `EllesmereUI.lua` (profil nommé par
   `--base`, sinon le profil actif), jamais écrit ; une chaîne `!EUI_` collée dans le panneau est acceptée aussi.
   *Autre* : chaîne collée seulement (ce que dit la ROADMAP mot pour mot).
4. **Rôle d'un personnage.** EllesmereUI n'a qu'une spécialisation par classe sur Forever. *Défaut* : rôle choisi par
   le joueur (`/fb role dps|heal|tank`, gardé par personnage dans `ForeverBridgeDB`, rôles permis par la table des
   spécialisations de `docs/SPEC.md`), et bascule hors combat, après la bascule propre d'EllesmereUI ; le rôle de
   recherche de groupe (`UnitGroupRolesAssigned`) n'est **pas** suivi. *Autre* : suivre aussi le rôle de groupe.
5. **Macros utiles.** *Défaut* : catalogue court par classe, écrit à la main dans `forever/exports/macros.yaml`
   (clés de sorts seulement, aucun chiffre), quatre motifs : soin ou buff `[@mouseover,help,nodead][]`, contrôle
   `[@focus,harm,nodead][]`, interruption `/stopcasting` + sort, attaque de mêlée `/startattack` + sort ;
   `#showtooltip` ; `/cast` **sans rang** (le jeu prend le meilleur rang appris, `suppose`, question MAC1) ; une macro
   seulement si tous ses sorts sont appris au niveau du personnage ; utilité `suppose`. *Autre* : me donner la liste
   des macros voulues par classe.

## Conception

### Codec commun (`forever/exports/codec.py`, fonctions pures)

- `serialize(value) -> bytes` / `deserialize(data) -> object` : sous-ensemble de LibSerialize version 1 (nil,
  booléens, entiers, flottants, chaînes, tables tableau, dictionnaire et mixtes) ; **clés triées** (sortie
  déterministe, comme l'option `stable`) ; les références de chaînes et de tables de LibSerialize sont **lues** mais
  jamais écrites ; types refusés : `TypeError` en français.
- `encode_for_print(data) -> str` / `decode_for_print(text) -> bytes` ; `deflate(data) -> bytes` (zlib, `wbits=-15`,
  niveau fixé) / `inflate(data, max_bytes)` borné (1 Mio, comme Naowh).
- `pack(prefix, table) -> str` / `unpack(prefix, text) -> object` : chaîne complète, motif « un seul jeton après le
  préfixe », limites de Naowh (caractères, octets, profondeur, valeurs) appliquées à la lecture.

### Formats (`forever/exports/naowh.py`, `forever/exports/ellesmere.py`)

- `naowh_build(class_id, name, spec, points) -> str`, `read_naowh_build(text) -> NaowhBuild` ;
  `naowh_macros(macros) -> str`, `read_naowh_macros(text)` ; `naowh_bis(name, spec, slots, extra) -> str`,
  `read_naowh_bis` ; `naowh_weights(spec_key, weights) -> str`, `read_naowh_weights`. Bornes de Naowh contrôlées à
  l'écriture (nom ≤ 16 octets, corps ≤ 255, 51 points, 40 caractères) : une entrée hors bornes lève une erreur
  nommée, jamais une chaîne que Naowh rejetterait.
- Tables de format de Naowh (clés de spécialisation, clés de statistiques, emplacements) dans
  `forever/exports/naowh_keys.py` : ce sont des **noms de format d'un addon**, pas des chiffres de jeu ; contrôlées par
  un test contre la liste relevée au plan (`tests/fixtures/exports/naowh_keys.json`).
- `ellesmere_serialize(value) -> bytes` / `ellesmere_deserialize` ; `ellesmere_profile(base, *, name, cdm_spells,
  buff_ids) -> str` et `read_ellesmere(text) -> dict` (enveloppe contrôlée : `version=3`, `type="full"`,
  `client="forever"`).

### Construction depuis nos données

- **Points d'un build** (`forever/exports/talents.py`) : `naowh_points(gd, class_name, talents, order) ->
  tuple[int, …]` (clé → `node_id`, répété par rang, dans l'ordre) ; `legal_order(gd, class_name, talents) ->
  list[str]` (question 2) ; contrôle de légalité **par prise** (paliers, prérequis, rangs) réutilisant les règles déjà
  tenues pour `build_check` ; `naowh_export(deps, class_name, level, talents, order, name) -> dict` avec `status`
  (`ok`, `bloque`, `ordre_genere`), `code`, `points`, `order_source` (`leveling` ou `genere`), `certainty`
  (`probable` tant que NFB1 n'est pas vérifiée), `provenance`.
- **Macros** (`forever/exports/macros.py`) : `class_macros(deps, class_name, level) -> list[Macro]` depuis
  `macros.yaml` et `classes.json` (noms anglais, client enUS) ; `macro_violations(body) -> list[str]` (refuse `/run`,
  `/script`, `/dump`, toute commande hors `/cast`, `/use`, `/stopcasting`, `/startattack`, `#showtooltip`).
- **Profil EllesmereUI** (`forever/exports/ellesmere.py`) : `read_base_profile(wow_dir, name=None)` (lecture de la
  sauvegarde, jamais d'écriture) ; sorts du gestionnaire de recharges = sorts de la classe appris au niveau dont la
  recharge (`cooldown_s` de `classes.json`) dépasse celle d'un sort ordinaire, regroupés par rôle par le catalogue
  (`forever/exports/roles.yaml` : clés de sorts par rôle, sans chiffre) ; rappels de buffs = sorts du catalogue
  marqués buff pour la classe et le rôle. Le reste du profil de base est **recopié tel quel** (choix du joueur).
  Profil nommé `<personnage> - <rôle>`.

### CLI et MCP

- `forever export naowh-build --class <c> --level <n> (--talents <clé=rang,…> [--order …] | --code <Talents Forever>
  | --popular <rang>)` ; `forever export naowh-macros --class <c> --level <n>` ; `forever export ellesmere
  <personnage> --role <rôle> [--base <profil>]` ; `forever export read <chaîne>` (décode n'importe laquelle des
  chaînes, pour le recoupement et la question NFB1) ; `forever export bis|weights` : refus clair « rempli par T10a ».
  Sortie `_emit` avec provenance.
- MCP : **pas de nouvel outil** (le jeu exact des outils reste celui de `tests/integration/test_mcp.py`) :
  `forever_build` ajoute `naowh` à côté de `export` (Talents Forever) ; `forever_lookup` gagne
  `kind="export"` (sous-types `naowh_build`, `naowh_macros`, `ellesmere`, `read`).
- Builds populaires (`popular_builds`) et `build_check` : champ `naowh` dans chaque build rendu.

### Pont et panneau (point 4)

- Réponse du pont : `links` devient une **liste typée** `[{kind, label, text}]` (`talents_forever`, `naowh_build`,
  `naowh_macros`, `ellesmere`), `link` gardé tel quel pour la compatibilité d'un addon pas encore rechargé ; le
  bouton Talents rend les deux liens du build (Talents Forever et Naowh).
- Addon `ForeverBridge` 0.4.0 : chaque lien imprimé `[Talents Forever]`, `[Naowh : build]`, `[Naowh : macros]`,
  `[EllesmereUI : <rôle>]`, cliquable, ouvre la boîte de copie du panneau d'action (même mécanique que FA1) ; commande
  `/fb exports` qui réaffiche les derniers liens d'export de la session ; `/fb role <rôle>` (question 4).
- Bouton **« Exports »** (`requires: EX1`) : réponse **rédigée par le pont sans le modèle** (comme le résumé d'une
  attente, décision 235) : pour le personnage du contexte, build Naowh du build du bouton Talents, macros de la classe
  au niveau, profil EllesmereUI du rôle choisi s'il y a un profil de base ; chaque ligne dit ce qui manque (« aucun
  profil de base EllesmereUI », « Naowh Forever absent : texte des macros à coller à la main »).
- Bascule EllesmereUI : à la connexion (après `PLAYER_ENTERING_WORLD` et un délai pour laisser passer la bascule
  d'EllesmereUI), au `/fb role` et au `PLAYER_REGEN_ENABLED` si un changement attendait la fin du combat ; appel
  `EllesmereUI.SwitchProfile` sous `pcall`, seulement si `GetProfileList()` contient le nom ; rien sinon (message une
  fois). Aucune écriture de `EllesmereUIDB`.
- **Objet LibDataBroker** « Forever » (ROADMAP EX1, point 3) : créé seulement si `LibStub("LibDataBroker-1.1", true)`
  existe (chargé par EllesmereUI ; **rien d'embarqué**, aucune dépendance) ; texte = état du pont (fraîcheur des
  données, XP par heure et prochain objectif quand le pont les envoie dans `ForeverBridgeSlot`, sinon absent, jamais
  inventé) ; clic = ouvre le panneau.

## Blocs (ordre d'utilité ; dates indicatives)

### Bloc 0 — Décisions et documents (2026-10-15)
Décision 267 (EX1 avant LN1, choix du plan) ; ROADMAP (place d'EX1, critères précisés) ; inventaire des addons mis à
jour (Naowh 1.1.12, EllesmereUI 9.5.4, sans code recopié) ; questions NFB1 précisée, MAC1, EUI1, EUI2 ; fixtures
(question 1) avec `README.md` de provenance.

### Bloc A — Codec commun (2026-10-15)
`forever/exports/codec.py` ; tests Python purs et oracle lupa.

### Bloc B — Builds vers Naowh (2026-10-16)
Points, ordre légal, `naowh_export`, CLI, `forever_build`, builds populaires et `build_check`.

### Bloc C — Pont : liens typés, bouton Exports, `/fb exports` (2026-10-17)
Le chat donne Talents Forever et Naowh pour chaque build ; panneau de copie ; ForeverBridge 0.4.0.

### Bloc D — Macros `!NFM1!` (2026-10-18)
Catalogue, génération par classe et niveau, contrôle des commandes ; `CreateMacro` ajouté aux interdits de
`check_addon.py`.

### Bloc E — Formats de T10a préparés (2026-10-18)
`!NBIS1!` et `NFSW1:` : écriture, lecture, bornes ; aucune donnée remplie ; bouton Équipement inchangé (caché).

### Bloc F — Profils EllesmereUI et bascule par rôle (2026-10-19 et 20)
Sérialiseur, profil de base, `cdmSpells` et rappels, bascule dans ForeverBridge, `/fb role`.

### Bloc G — Objet LibDataBroker (2026-10-21 ; peut glisser après LN1)

## Tests attendus (aucun chiffre de jeu écrit dans un test : valeurs lues dans `tests/fixtures/` ou `forever/data/`)

### Bloc A (`tests/unit/test_export_codec.py`, `tests/unit/test_export_codec_lua.py`)
- `encode_for_print` puis `decode_for_print` rend les octets d'origine pour des longueurs 0 à 7 (tous les restes
  modulo 3) ; alphabet limité à `a-zA-Z0-9()`.
- `serialize` est déterministe (deux dictionnaires égaux insérés dans un ordre différent → mêmes octets) ; chaque type
  du sous-ensemble fait l'aller-retour Python ; un type non pris (`set`, objet) lève `TypeError`.
- `unpack` refuse un préfixe faux, un deuxième jeton, une chaîne au-delà des limites, une décompression au-delà de
  1 Mio (bombe synthétique).
- **Oracle lupa** (fixtures de la question 1) : une table produite par Python, relue par `LibDeflate:DecodeForPrint`,
  `DecompressDeflate` et `LibSerialize:Deserialize`, est égale à l'originale ; une table sérialisée et encodée par les
  bibliothèques Lua est relue à l'identique par `unpack` (tables avec références de chaînes répétées, flottants,
  négatifs, grands entiers).

### Bloc B (`tests/unit/test_export_naowh_build.py`)
- Pour le build de Mage de `tests/fixtures/talents_forever/mage_builds.json` : `points` = `node_id` de
  `classes.json` répété par rang, dans l'ordre de la fixture ; longueur = somme des rangs ; `class` = `id` de la classe.
- `read_naowh_build(naowh_build(…))` rend la même table (va-et-vient) ; la chaîne relue par l'oracle Lua aussi.
- `legal_order` : chaque prise est légale (palier, prérequis, rang) pour chaque build de
  `tests/fixtures/talents_forever/popular.json` ; un build illégal rend `status="bloque"` avec le talent nommé.
- Le contrôle par prise refuse un ordre où un talent de palier 2 précède le cinquième point de l'arbre.
- Un build de plus de 51 points ou un nom de plus de 40 caractères est refusé ou tronqué comme chez Naowh.
- `forever export naowh-build --json` porte `provenance` (contrat CLI, `test_contract.py`) ; `forever_build` rend
  `naowh` à côté de `export`.

### Bloc C (`tests/unit/test_bridge_exports.py`, `tests/unit/test_bridge_exports_lua.py`)
- Le bouton Talents produit deux liens typés ; le slot les écrit dans `links` et garde `link`.
- Lua (client simulé) : deux liens imprimés, chacun ouvre la boîte de copie avec **sa** chaîne ; `/fb exports`
  réimprime les liens de la session ; un addon sans `links` (ancien slot) imprime toujours `[Talents Forever]`.
- Le bouton Exports n'apparaît qu'avec `EX1` dans `DONE_SLICES` et sa réponse ne passe pas par le modèle (agent
  bouchonné jamais appelé).

### Bloc D (`tests/unit/test_export_macros.py`, `tests/unit/test_addon_rules.py`)
- Pour chaque classe de `classes.json`, chaque macro générée n'a que des commandes permises (aucune `/run`,
  `/script`, `/dump`), nom ≤ 16 octets, corps ≤ 255 ; aucune macro avec un sort non appris au niveau donné
  (niveaux lus dans `classes.json`) ; va-et-vient `!NFM1!` Python et oracle Lua.
- `check_addon.py` refuse `CreateMacro` (fixture de faute dans `tests/fixtures/addon/bad`).

### Bloc E (`tests/unit/test_export_t10a_formats.py`)
- `!NBIS1!` en `v=4`, emplacement 4 ou 19 refusé, va-et-vient Python et Lua ; `NFSW1:` sans notation `e`, poids
  ≥ 1 000 refusé, clé inconnue refusée, va-et-vient texte ; clés de spécialisation et de statistiques égales à
  `tests/fixtures/exports/naowh_keys.json` ; `forever export bis` répond « rempli par T10a ».

### Bloc F (`tests/unit/test_export_ellesmere.py`, `tests/unit/test_bridge_role_lua.py`)
- Va-et-vient du sérialiseur EllesmereUI sur une table synthétique (types, chaînes avec `:` et `}`), déterministe.
- Sur un profil de base de fixture (`tests/fixtures/exports/ellesmere_base.lua`, synthétique) : le profil rendu garde
  tout le reste à l'identique, ne change que `cdmSpells` (clé de spécialisation du profil de base) et `customIDs` ;
  sorts tous appris au niveau ; enveloppe `version=3`, `type="full"`, `client="forever"` ; nom `<personnage> - <rôle>`.
- Rôle refusé s'il n'est pas tenu par la classe (table de `docs/SPEC.md`, reprise en fixture).
- Lua : `SwitchProfile` appelé hors combat avec le bon nom ; en combat, différé au `PLAYER_REGEN_ENABLED` ; nom absent
  de `GetProfileList` → aucun appel ; EllesmereUI absent → aucune erreur ; aucune écriture de `EllesmereUIDB`.

### Bloc G (`tests/unit/test_bridge_ldb_lua.py`)
- Avec un LibStub et un LibDataBroker bouchonnés : objet créé, texte tiré du slot, champ absent quand le slot ne le
  porte pas ; sans LibStub : rien, aucune erreur.

## Registre (`docs/MECHANICS_REGISTRY.yaml`)
Aucune mécanique de jeu modifiée. Une entrée seulement si les règles de légalité d'un build (paliers, prérequis) sont
déplacées ou complétées pour l'ordre par prise : alors l'entrée existante des paliers de talents est mise à jour
(tests ajoutés), comptes de `test_registry.py` écrits dès le commit « tests » du bloc B.

## Questions ouvertes (à ajouter à `docs/OPEN_QUESTIONS.md`)
- **NFB1** (existante, précisée) : relire un build exporté par Naowh 1.1.12 ; aussi : un code `!NFB1!` produit par
  forever s'importe-t-il et Naowh l'apprend-il ?
- **MAC1** : sur Forever, `/cast <sort>` sans rang lance-t-il le meilleur rang appris ? Test facultatif : une macro
  importée, lancée à deux niveaux.
- **EUI1** : un profil `!EUI_` produit par forever s'importe-t-il, et sa clé `cdmSpells` est-elle reprise ?
- **EUI2** : la bascule par `SwitchProfile` tient-elle face à la bascule d'EllesmereUI au `PLAYER_ENTERING_WORLD`
  quand la spécialisation de la classe est affectée à un profil ?

Procédures de test en jeu (facultatives, décision 247) dans `docs/ADDON.md`, et listées pour `docs/LANCEMENT.md`
(LN1) comme tests restés en attente.

## Hors périmètre
- Disposition et apparence des profils EllesmereUI ; profils `fullaccount` ; affectation spécialisation → profil.
- `NFPROFILE1:` et `NaowhForever_API:ImportProfile` (import sans confirmation du joueur) ; champ `skip` de `!NFB1!`.
- Contenu des listes BiS et des poids (T10a) ; macros avec `/run`, `/script` ou commande d'addon ; création ou
  lancement d'une macro par notre addon ; écriture d'une sauvegarde d'addon tiers.
- Abandon de Talents Forever (décision de l'utilisateur, plus tard).

## Risques
- **Interopérabilité non prouvée en jeu** avant un essai : l'oracle lupa prouve la compatibilité avec les
  bibliothèques, pas l'acceptation par Naowh ou EllesmereUI (bornes, champs) ; certitude `probable` jusqu'à NFB1 et
  EUI1.
- **Lua 5.5 sous lupa** : LibSerialize et LibDeflate visent Lua 5.1 ; si un détail (entiers, `math.pow`) diffère, un
  petit bouchon de compatibilité dans le test, sans toucher aux bibliothèques ; sinon repli sur la question 1 *Autre*.
- **Formats mouvants** : Naowh publie plusieurs versions par semaine ; la version relevée (1.1.12, 9.5.4) est écrite
  dans la provenance de chaque export, et `forever addons status` signale un changement.
- **Bascule EllesmereUI** : sans fonction publique d'affectation, la bascule d'EllesmereUI peut reprendre la main
  (EUI2) ; mitigation : délai après la sienne et conseil au joueur de ne pas affecter la spécialisation.
- **Calendrier** : six jours avant la fin de la bêta, RX1 et LN1 autour ; les blocs F et G peuvent glisser après LN1
  sans gêner A à E.

## Angles morts (prévus)
- « Macros utiles » et « sorts d'un rôle » sont des choix de catalogue, `suppose` : effet sur la qualité de l'aide,
  pas sur un chiffre calculé.
- L'ordre généré n'est pas un ordre de leveling optimisé : pour une autre classe que le Mage, il peut retarder un
  talent utile (sens : XP par heure un peu plus basse que l'ordre d'un guide), à signaler dans la réponse.

## Étapes d'exécution
1. Validation du plan et réponses aux cinq questions ; décision 267 committée sur `main` avec le bloc 0.
2. `git switch -c ex1` depuis `origin/main` ; un cycle rouge → vert par bloc (`EX1: tests (bloc X)`, `EX1: bloc X
   vert`) ; `uv run tasks.py quick` pendant le travail.
3. Fin : `/verifier`, `uv run ruff check . --no-cache`, push, CI verte sous Ubuntu et Windows, fusion en
   fast-forward, plugin et skill `forever-builds` mis à jour (Naowh à côté de Talents Forever), pont relancé
   (mémoire « relancer le pont après une fusion »).

## Critères de fin
Va-et-vient exact des chaînes `!NFB1!`, `!NFM1!`, `!NBIS1!`, `NFSW1:` et `!EUI_` sur fixtures (Python et oracle
Lua) ; le chat donne pour chaque build le lien Talents Forever et le code Naowh, chacun copiable depuis le panneau ;
bouton Exports et `/fb exports` ; aucune macro avec `/run`, `/script` ou `/dump` ; bascule par rôle testée sur
bouchons ; procédures facultatives dans `docs/ADDON.md` ; `test_addon_rules.py` vert ; `uv run tasks.py verify` vert.
