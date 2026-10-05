# Extraits des tables du client 1.60.1.70170 (T08c, blocs B et C)

- Source : `https://wago.tools/db2/<Table>/csv?build=1.60.1.70170` (enUS, et frFR pour les tables localisées de
  `decode_rules.json`) ; collectes du cache de `forever fetch` faites pour l'installation de 1.60.1.70170 (empreintes
  dans `<cache>/wago/1.60.1.70170/fetch.json`) ; aucun accès réseau pour cette fixture.
- Filtre : `uv run python scripts/extract_class_fixtures.py --version 1.60.1.70170 --dbcache
  tests/fixtures/hotfix/DBCache.bin`, même portée que la fixture de 1.60.1.70124 (arbres des 9 classes en entier, dont
  l'arbre 1117 du Guerrier, sorts suivis et sorts nommés, races, objets, tables du personnage, familiers,
  GameTables), plus les lignes des enregistrements visés par les entrées de la fixture `DBCache.bin` (tous statuts),
  et leurs sorts : la ligne du build se compare à celle du correctif.
- Lignes réécrites par le module `csv` (mêmes colonnes, fins de ligne LF) ; ne pas éditer à la main, relancer le
  script.
