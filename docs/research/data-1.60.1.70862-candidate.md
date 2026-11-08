# data: 1.60.1.70790 → /home/runner/.cache/forever/candidates/1.60.1.70862

10 changement(s) : 4 talent(s), 1 sort(s), 5 fichier(s), 0 valeur(s) de spell_scaling.json, 0 valeur(s) de character_scaling.json.

## Talents

| Talent | Changement | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| wakeOfFire | retiré | — | — | — |
| hotStreak | retiré | — | — | — |
| improvedFireBlast | ajouté | — | — | — |
| heatingUp | ajouté | — | — | — |

## Sorts

| Sort | Changement | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| frost_blast | retiré | — | — | — |

## Fichiers

| Fichier | Changement | Champ | Avant | Après |
| --- | --- | --- | --- | --- |
| _seed_spells.json | retiré | — | — | — |
| _seed_talents.json | retiré | — | — | — |
| _source_gunba_mage_tree.json | retiré | — | — | — |
| confirmed_changes.json | retiré | — | — | — |
| revisions.json | retiré | — | — | — |

## Vérification

/home/runner/.cache/forever/candidates/1.60.1.70862 : ok
- avertissement : 18 fichier(s) hérité(s) d'une version antérieure, à revérifier

## Hypothèses

- fraîcheur jamais vérifiée (lancer `forever status`)
- 1.60.1.70862 : version candidate non installée (/home/runner/.cache/forever/candidates/1.60.1.70862)
- 1.60.1.70862 : fichiers hérités d'une version antérieure (_seed_racials.json, character_scaling.json, classes.json, decode_rules.json, leveling.json, mechanics.json, meta.json, monsters.json, origins.json, overrides.json, pet_rules.json, pets.json, pvp_items.json, pvp_rules.json, quest_rewards.json, races.json, respec.json, xp_bonuses.json)
- comparaison 1.60.1.70790 (données af004b0824d8) -> /home/runner/.cache/forever/candidates/1.60.1.70862 (données cb681f8cf517)

Provenance · version 1.60.1.70862 r11 · données cb681f8cf517 · générée 2026-11-08T13:22:44Z · fraîcheur unknown · certitude suppose · registre 76/148 · hypothèses : fraîcheur jamais vérifiée (lancer `forever status`) ; 1.60.1.70862 : version candidate non installée (/home/runner/.cache/forever/candidates/1.60.1.70862) ; 1.60.1.70862 : fichiers hérités d'une version antérieure (_seed_racials.json, character_scaling.json, classes.json, decode_rules.json, leveling.json, mechanics.json, meta.json, monsters.json, origins.json, overrides.json, pet_rules.json, pets.json, pvp_items.json, pvp_rules.json, quest_rewards.json, races.json, respec.json, xp_bonuses.json) ; comparaison 1.60.1.70790 (données af004b0824d8) -> /home/runner/.cache/forever/candidates/1.60.1.70862 (données cb681f8cf517)

---

Rapport produit par le workflow build-watch. **Rien n'est installé** :
`forever/data/` n'a pas changé. L'installation reste validée à la main
(`forever install --new-version <candidate>`, tranche T08a).
