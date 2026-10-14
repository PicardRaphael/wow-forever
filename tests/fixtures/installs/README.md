# Installations du client (LN1)

- `build_info_15.txt` : en-tête réel de `.build.info` (15 colonnes) et sa ligne, relevés le 2026-10-14 sur le PC de
  jeu (`C:\Program Files (x86)\World of Warcraft\.build.info`) ; clés de build, de CDN et serveurs **retirées**
  (colonnes vides), seules `Branch`, `Active`, `CDN Path`, `Version` et `Product` gardées.
- `flavor_info.txt` : copie de `_classic_beta_\.flavor.info` (même date).

Les autres racines des tests sont construites dans `tmp_path` ; les produits non bêta y sont **manifestement fictifs**
(`wow_fictif_finale`, `wow_fictif_inconnu`) ou publics (`wow`), jamais le produit supposé de la version finale.
