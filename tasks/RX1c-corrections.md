# RX1c — Demandes de correction de tests verrouillés

Regroupées pour une seule validation avant la fusion (règle « regroupement des demandes de correction »).

## 1. `tests/unit/test_ellesmere_base_choice.py` (profil de base par personnage) : deux erreurs du test

**Tests** : `test_unknown_base_in_the_profile_is_refused_with_the_list`,
`test_exports_button_with_an_unknown_base_lists_the_profiles`.

**Constat** :
- `InvalidArgumentError` (`forever/errors.py`, `ForeverError.__init__`) porte l'action à faire dans `action`, pas
  dans `hint` : `AttributeError: 'InvalidArgumentError' object has no attribute 'hint'`. Le refus attendu est bien levé,
  avec « Inconnu » dans le message et « Autre » dans l'action.
- `read_profile(deps, "Jen")` lève `InvalidArgumentError` quand le personnage est absent du profil (`_known`) : c'est
  justement le cas attendu (profil de base inconnu : rien écrit). La prémisse « rend `character is None` » est fausse.

**Diff proposé** (aucune attente changée) :

```diff
-    assert "Inconnu" in err.value.message and "Autre" in err.value.hint
+    assert "Inconnu" in err.value.message and "Autre" in err.value.action
@@
-    assert read_profile(deps, WHO)["character"] is None or read_profile(deps, WHO)["character"].get(
-        "ellesmere_base"
-    ) in (None, "")
+    assert WHO not in read_profile(deps)["characters"]
```
