# Extrait de `Logs/Hotfix.log` (T08b, bloc E)

- Lignes réelles : journal du client 1.60.1.70124 du poste de l'utilisateur, démarrage du 2026-10-01 (lecture locale,
  aucune valeur de jeu : table, enregistrement, résultat, identifiant de poussée) ; une ligne par sorte retenue.
- Lignes synthétiques (poussée `900001`, datées du 30/9) : même forme, enregistrements choisis dans les fixtures
  `tests/fixtures/wago/1.60.1.70124/` pour relier un correctif à une entité (`CurvePoint` 241055 → courbe du talent
  Winter's Chill, `SpellMisc` 314147 → Frostbolt rang 1, `Item` 4381 → bijou PvP), plus un `INVALID` et un `DELETE`.
- Le journal n'a pas d'année : l'année vient de la date du fichier (réécrit à chaque démarrage du client).
