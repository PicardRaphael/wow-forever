# EX1 — Demandes de correction de tests verrouillés

Regroupées pour une seule validation avant la fusion (règle « regroupement des demandes de correction »).

## 1. `tests/unit/test_export_codec_lua.py` (bloc A) : deux valeurs rendues par LibDeflate

**Tests** : `test_lua_compression_levels_read_by_python`, `test_python_deflate_read_by_lua`.

**Preuve (fixture)** : `tests/fixtures/third_party/LibDeflate/LibDeflate.lua`, documentation de `CompressDeflate`
(l. 2030-2031 : « @return [string] The compressed data. @return [integer] The number of bits padded at the end of
output. ») et de `DecompressDeflate` (l. 2731-2735 : données décompressées, puis nombre d'octets non traités). Sous
`lupa` (`unpack_returned_tuples=True`), l'appel rend donc un tuple `(données, nombre)` : le test compare un tuple à
des octets (`assert (b'…', 0) == b'…'`) ou passe un tuple à `inflate` (`TypeError: a bytes-like object is required,
not 'tuple'`). Le code testé n'est pas en cause : les 81 autres tests du bloc, dont les relectures complètes par
`DecodeForPrint`, `DecompressDeflate` et `Deserialize`, passent.

**Diff proposé** (parenthèses Lua : une seule valeur rendue) :

```diff
-        packed = lua.eval(b"function(s, l) return LD:CompressDeflate(s, { level = l }) end")(data, level)
+        packed = lua.eval(b"function(s, l) return (LD:CompressDeflate(s, { level = l })) end")(data, level)
@@
-    assert lua.eval(b"function(s) return LD:DecompressDeflate(s) end")(deflate(data)) == data
+    assert lua.eval(b"function(s) return (LD:DecompressDeflate(s)) end")(deflate(data)) == data
```

## 2. `tests/unit/test_export_t10a_formats.py` (bloc E) : « e » cherché dans le nom d'une statistique

**Test** : `test_weights_round_trip_and_text`.

**Preuve (fixture)** : `tests/fixtures/exports/naowh_keys.json`, `stat_keys` contient `spell` (et `haste`, `def`,
`threat`…) ; la ligne produite est `NFSW1:frost-mage:sta=0.000125,int=0.5,spell=1,scrit=12.25,mp5=0`. L'assertion
`"e" not in` porte sur tout le corps, noms de statistiques compris, alors que la règle (jamais de notation `e`)
porte sur les **poids** ; le test voisin `test_weights_never_use_exponent_notation` retire déjà `spell` avant de
chercher. Les poids de la ligne sont corrects.

**Diff proposé** :

```diff
-    assert "e" not in text.split(":", 2)[2]
+    assert all("e" not in part.split("=", 1)[1] for part in text.split(":", 2)[2].split(","))
```
