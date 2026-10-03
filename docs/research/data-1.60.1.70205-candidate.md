# data: 1.60.1.70170 → /home/runner/.cache/forever/candidates/1.60.1.70205

7 changement(s) : 2 talent(s), 0 sort(s), 5 fichier(s), 0 valeur(s) de spell_scaling.json, 0 valeur(s) de character_scaling.json.

## Talents

| Talent | Changement | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| hotStreak | retiré | — | — | — |
| heatingUp | ajouté | — | — | — |

## Fichiers

| Fichier | Changement | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| _seed_spells.json | retiré | — | — | — |
| _seed_talents.json | retiré | — | — | — |
| _source_gunba_mage_tree.json | retiré | — | — | — |
| confirmed_changes.json | retiré | — | — | — |
| revisions.json | retiré | — | — | — |

## Vérification

/home/runner/.cache/forever/candidates/1.60.1.70205 : ok
- avertissement : 16 fichier(s) hérité(s) d'une version antérieure, à revérifier

## Hypothèses

- fraîcheur jamais vérifiée (lancer `forever status`)
- 1.60.1.70205 : version candidate non installée (/home/runner/.cache/forever/candidates/1.60.1.70205)
- 1.60.1.70205 : fichiers hérités d'une version antérieure (_seed_racials.json, character_scaling.json, classes.json, decode_rules.json, leveling.json, mechanics.json, meta.json, monsters.json, origins.json, overrides.json, pet_rules.json, pets.json, pvp_items.json, pvp_rules.json, races.json, respec.json)
- comparaison 1.60.1.70170 (données e7a5c1156df9) -> /home/runner/.cache/forever/candidates/1.60.1.70205 (données 248befaa19b8)

Provenance · version 1.60.1.70205 r3 · données 248befaa19b8 · générée 2026-10-03T11:38:33Z · fraîcheur unknown · certitude suppose · registre 53/129 · hypothèses : fraîcheur jamais vérifiée (lancer `forever status`) ; 1.60.1.70205 : version candidate non installée (/home/runner/.cache/forever/candidates/1.60.1.70205) ; 1.60.1.70205 : fichiers hérités d'une version antérieure (_seed_racials.json, character_scaling.json, classes.json, decode_rules.json, leveling.json, mechanics.json, meta.json, monsters.json, origins.json, overrides.json, pet_rules.json, pets.json, pvp_items.json, pvp_rules.json, races.json, respec.json) ; comparaison 1.60.1.70170 (données e7a5c1156df9) -> /home/runner/.cache/forever/candidates/1.60.1.70205 (données 248befaa19b8)

---

Rapport produit par le workflow build-watch. **Rien n'est installé** :
`forever/data/` n'a pas changé. L'installation reste validée à la main
(`forever install --new-version <candidate>`, tranche T08a).
