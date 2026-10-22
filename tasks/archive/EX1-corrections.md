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

## 3. `tests/unit/test_bridge_exports.py` (bloc C) : la réponse du bouton Exports ne peut pas porter les macros ni le profil EllesmereUI

**Test** : `test_exports_reply_gives_the_current_build_and_the_last_links`.

**Preuve (plan)** : `tasks/EX1-plan.md`, « Pont et panneau » : le bouton Exports donne le build Naowh, **les macros de
la classe au niveau** et **le profil EllesmereUI du rôle choisi** (blocs D et F, verts depuis). L'assertion
`links[1:] == last` impose que la réponse ne porte que le build actuel suivi des liens du dernier build : aucun lien
`naowh_macros` ni `ellesmere` ne peut y entrer sans faire échouer le test. Le test a été écrit au bloc C, avant les
formats des blocs D et F ; ce n'est pas une prémisse fausse sur les données, mais une forme trop étroite.

**Diff proposé** (le lien du build actuel reste le premier, les liens du dernier build restent tous présents, dans
leur ordre) :

```diff
-    assert links[1:] == last
+    assert [link for link in links[1:] if link["kind"] in ("talents_forever", "naowh_build")] == last
```

**Code appliqué après accord** (`forever/bridge/exports.py`, `exports_reply`) : après le build actuel, le lien
`[Naowh : macros]` (`macros_export` de la classe au niveau) et, si le contexte porte un rôle (`/fb role`) et qu'un
profil de base EllesmereUI existe, le lien `[EllesmereUI : <rôle>]` (`ellesmere_export`) ; sinon une ligne qui dit ce
qui manque (« aucun rôle choisi : /fb role », « aucun profil de base EllesmereUI »).
