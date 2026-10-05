# Extrait de `Logs/Hotfix.log` (T08b, bloc E)

- Lignes réelles : journal du client 1.60.1.70124 du poste de l'utilisateur, démarrage du 2026-10-01 (lecture locale,
  aucune valeur de jeu : table, enregistrement, résultat, identifiant de poussée) ; une ligne par sorte retenue.
- Lignes synthétiques (poussée `900001`, datées du 30/9) : même forme, enregistrements choisis dans les fixtures
  `tests/fixtures/wago/1.60.1.70124/` pour relier un correctif à une entité (`CurvePoint` 241055 → courbe du talent
  Winter's Chill, `SpellMisc` 314147 → Frostbolt rang 1, `Item` 4381 → bijou PvP), plus un `INVALID` et un `DELETE`.
- Le journal n'a pas d'année : l'année vient de la date du fichier (réécrit à chaque démarrage du client).

<!-- dbcache:début (écrit par scripts/extract_dbcache_fixture.py) -->

## Fixture `DBCache.bin` (T08c, bloc A)

- Extraite du `Cache/ADB/enUS/DBCache.bin` du poste de
  l'utilisateur (build 70170, 7300286 octets, sha256 `2f2a6ba10c8272c1…`), lecture
  locale par `scripts/extract_dbcache_fixture.py` ; en-tête recopié ; entrées réelles choisies : toutes celles
  des poussées 112323, 112347, 112349, la première entrée des poussées 112340, 112350 (tables
  hors du projet), deux réponses `DBReply` (Spell 15147), les réponses d'objets de l'objet
  720 (poussée 0x01000000 + identifiant) ; aucune entrée `TactKey`.
- Entrées **synthétiques** (signalées) : `SpellLevels` 999901, absent des tables, `DELETE` en poussée
  100002 placée avant un `VALID` en poussée 100001 (données recopiées d'une entrée réelle) : la poussée la plus
  haute l'emporte, quel que soit l'ordre du fichier.
- `hotfixes-70170.json` : entrées du journal du cache (`forever hotfixes`, lignes de `Hotfix.log` du
  démarrage du client 70170 du 2026-10-02) des mêmes poussées, gardées pour ce build.
- Comptes lus par les tests (ne pas éditer : relancer le script) :

```json
{
 "format": 9,
 "build": 70170,
 "entries": 280,
 "size": 18774,
 "sha256": "c71fbbe45bc8ee9ee30af32b518ad2d37a4040e6fd9729aca9f536d84e26d636",
 "by_status": {
  "DELETE": 64,
  "INVALID": 17,
  "NOTPUBLIC": 1,
  "VALID": 198
 },
 "pushes": {
  "-1": 2,
  "100001": 1,
  "100002": 1,
  "112323": 1,
  "112340": 1,
  "112347": 259,
  "112349": 8,
  "112350": 1,
  "16777936": 6
 },
 "synthetic": [
  {
   "table": "SpellLevels",
   "rec_id": 999901,
   "push_id": 100002,
   "status": "DELETE"
  },
  {
   "table": "SpellLevels",
   "rec_id": 999901,
   "push_id": 100001,
   "status": "VALID"
  }
 ],
 "journal_lines": 192
}
```

<!-- dbcache:fin -->
