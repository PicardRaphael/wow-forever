# Plan LN2 — Données de la version finale (`wowf`) acceptées (2026-11-05, en attente de validation)

Constat du 2026-11-05 :
- La veille a décodé 1.60.1.70755, la première version lue sur la version finale adoptée sur le poste (`forever wow list` :
  `_forever_ · version finale · wowf · 1.60.1.70790 (choisie)`).
- Son `sources.json` porte donc `"product": "wowf"`, ce qui est juste : c'est le produit observé, pas deviné.
- La CI de la branche `data/1.60.1.70755-r1` (run 41807890072) échoue sur 7 tests, tous pour cette seule raison :
  - `test_no_final_product_name` : le garde-fou de LN1 (décision 271) interdit `wowf` partout, données comprises ;
  - `test_choice_everywhere` (2 tests) et `test_ln1_review` (1 test) : `installs.beta_product` prend le produit de la
    version de données **la plus récente**. Avec `wowf`, plus aucune installation n'a le rôle bêta : sans adoption,
    le choix tombe sur le dossier de repli ;
  - `test_update_network` (3 tests) : le montage cherche les versions du produit de la donnée la plus récente
    (`wowf`), alors que le faux wago.tools sert la bêta, d'où « aucune version à installer ».
- Rien n'a été fusionné. Le client du joueur est déjà en 1.60.1.70790.

## 1. Les deux questions (décision 288)
- **Qui maintient déjà ça mieux que nous ?** Le client lui-même (`.build.info`, `.flavor.info`) et wago.tools, qui
  publient le produit. Nous ne faisons que le recopier ; rien à construire.
- **Que se passe-t-il au prochain patch ?** Toute version suivante porte `wowf` : sans LN2, la veille reste bloquée
  à chaque version. Avec LN2, plus rien ne dépend du nom du produit : les rôles viennent des données et de l'adoption.

## 2. Ce qui change
### a) Décision 271 révisée (décision 302)
- Le code, les skills et les tests ne nomment toujours pas la version finale : la règle de LN1 tient.
- Exception : un produit **observé** et écrit par la veille dans `forever/data/<version>/` (`sources.json`,
  `manifest.json`, `meta.json`) est une donnée, pas une supposition. Le garde-fou ne lit plus `forever/data/`.
- L'adoption sur le poste (`forever wow adopt`) reste nécessaire pour qu'une installation soit lue comme version
  finale ; une donnée `wowf` ne vaut pas adoption.

### b) Rôles des installations (`forever/installs.py`)
- `beta_product` devient `data_products` : l'ensemble des produits de **toutes** les versions de données
  installées, et non plus celui de la plus récente.
- Rôle : produit adopté → finale ; produit présent dans les données et non adopté → bêta ; produit public connu →
  autre ; sinon inconnu. Plusieurs installations bêta : la plus récente est choisie.
- `forever wow list` et `forever doctor` (appel de `cli.py`) suivent le nouveau nom.

### c) Produit interrogé par la veille
- `_local_product` / `wago_product` : inchangés pour le poste (produit adopté s'il est l'installation lue).
- Les tests de `test_update_network` utilisent un montage qui fixe la bêta : le produit et le préfixe du montage
  sont lus dans les données de la fixture, pas dans la version la plus récente du dépôt. Les tests ne dépendent plus
  des données réelles installées.

### d) Tests (d'abord, rouges, committés)
- Garde-fou : un `wowf` dans `forever/data/<version>/sources.json` est accepté ; dans `forever/`, `scripts/`,
  `addon/`, `plugin/` ou `tests/` hors données, toujours refusé.
- Rôles : données de deux produits (bêta puis `wowf`), rien d'adopté → la bêta est lue ; `wowf` adopté → finale.
- `test_update_network` et `test_choice_everywhere` : indépendants du produit de la dernière version des données.
- Contre-épreuve : la suite complète passe sur la branche `data/1.60.1.70755-r1` rebasée sur LN2 (job `e2e`
  compris).

### e) Documents
- `docs/DECISIONS.md` : décision 302. `docs/ARCHITECTURE.md` (rôles des installations).

## 3. Après la fusion
- La branche `data/1.60.1.70755-r1` est remplacée : la veille repart de `main` et installe 1.60.1.70790 (ou la
  plus récente publiée), avec les correctifs du serveur lus dans `DBCache.bin` (`Cache/ADB/frFR`, écrit le
  2026-11-05 à la fermeture du jeu).
- Rapport des valeurs qui changent, comme toujours (décision 288).

## 4. Essai (décision 273)
- `forever wow list` : `_forever_` reste « version finale (choisie) ».
- `forever update status` : 1.60.1.70790 installée, plus d'attente bloquée.
- En jeu : `/fv` répond, avec les données de la nouvelle version dans la provenance.

## 5. Durée et dépendances
- Environ une heure ; aucune dépendance, aucun accès réseau nouveau.
