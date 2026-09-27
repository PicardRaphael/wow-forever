# Extraits des tables du client 1.60.1.70009

- Source : `https://wago.tools/db2/<Table>/csv?build=1.60.1.70009` (enUS) et `&locale=frFR` pour `SpellName`, collecte du 2026-09-27 par `uv run forever fetch` (empreintes dans `<cache>/wago/1.60.1.70009/fetch.json`).
- Filtre : `uv run python scripts/extract_wago_fixtures.py --version 1.60.1.70009` (fermeture transitive décrite dans le script) : arbre de talents du Mage (TraitTree 1112, 54 nœuds), sorts des talents, rangs des 15 sorts suivis, sorts déclenchés et cités par les infobulles.
- Leurres gardés volontairement : un nœud d'un autre arbre (103884), des sorts homonymes hors des lignes du Mage (PNJ), les doublons de Fire Blast à `AcquireMethod` 3.
- Lignes réécrites par le module `csv` (mêmes colonnes, fins de ligne LF) ; ne pas éditer à la main, relancer le script.
