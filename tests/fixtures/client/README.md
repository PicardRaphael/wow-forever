# Fichiers du client (fixtures de T04d)

- `questcache_sample.wdb` : extrait de `Cache/WDB/enUS/questcache.wdb` du client 1.60.1.70338 (relevé le 2026-10-13,
  203 quêtes vues), par `uv run python scripts/extract_quest_fixtures.py questcache` : en-tête (signature `WQST`,
  build 70338, locale enUS) et 12 enregistrements recopiés octet pour octet (479, 421, 5725, 825, 786, 823, 784,
  851, 863, 6365, 97249, 96638), puis le couple de fin (0, 0). Aucune donnée personnelle (le cache ne garde que le
  texte des quêtes du client). Ne pas éditer à la main.
- `QuestXP.csv` : table `QuestXP` de 1.60.1.70338 (wago.tools, cache de `forever fetch`), recopiée octet pour octet
  par `uv run python scripts/extract_quest_fixtures.py questxp`.
