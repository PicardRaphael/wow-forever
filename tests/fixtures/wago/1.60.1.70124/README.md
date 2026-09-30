# Extraits des tables du client 1.60.1.70124 (9 classes, PV1)

- Source : `https://wago.tools/db2/<Table>/csv?build=1.60.1.70124` (enUS), `&locale=frFR` pour `SpellName` et `ChrRaces` ; collectes du 2026-09-30 par `uv run forever fetch` (empreintes dans `<cache>/wago/1.60.1.70124/fetch.json`) ; les 16 tables ajoutées en PV1 (plus `ChrRaces` en frFR) sur accord de l'utilisateur (D3).
- Filtre : `uv run python scripts/extract_class_fixtures.py` (fermeture transitive décrite dans le script) : arbres de talents des 9 classes en entier (470 nœuds) et un nœud leurre d'un autre arbre, sorts des talents et rangs des sorts suivis du Mage ; les blocs suivants y ajoutent sorts nommés, raciaux et objets.
- Tables petites recopiées en entier (`FULL_TABLES` du script) ; les autres réduites aux sorts ou objets retenus.
- Lignes réécrites par le module `csv` (mêmes colonnes, fins de ligne LF) ; ne pas éditer à la main, relancer le script.
