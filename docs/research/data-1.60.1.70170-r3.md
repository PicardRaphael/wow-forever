# data: 1.60.1.70170 r2 → r3

Révision écrite à la main, sans candidate : aucune table du client ne change, `forever install` ne s'applique pas.
Changements notés dans `revisions.json` (`manual_changes`), comme pour la révision 6 de 1.60.1.70124.

| Fichier | Chemin | Avant | Après | Source |
| --- | --- | --- | --- | --- |
| mechanics.json | values.coefficient.low_level_default.certainty | suppose | probable | note officielle (ci-dessous) : existence de la pénalité des rangs bas |
| mechanics.json | values.coefficient.low_level_default.source | règle Classic supposée jusqu'au test E2 | existence confirmée par la note, formule toujours supposée (E2) | idem |
| origins.json | règle `/values/coefficient.low_level_default` | `manuel`, `suppose` | `manuel`, `probable`, source et raison citant la note | idem |
| pet_rules.json | official_fixes | — | correctif des rangs enseignés par les bêtes (2026-10-01, `probable`, registre L3) | note officielle, Hunter > Pets |
| pet_rules.json | source (en-tête) | … une règle tirée d'une note officielle | … et un correctif officiel daté, signalé par le guide | révision 3 |
| origins.json | règle `/official_fixes` | — | `manuel`, `probable`, registre L3 | note officielle |
| sources.json | files.pet_rules.json, files.mechanics.json (source, notes) | — | mention de la révision 3 | — |
| sources.json | revision, revised_at | 2, 2026-10-02 | 3, 2026-10-02 | — |

## Source primaire

Notes de développement de la bêta de Forever, mise à jour du 1er octobre 2026 : message n° 4 du sujet officiel
<https://us.forums.blizzard.com/en/wow/t/2360696/4>, créé le 2026-10-01 à 22:56 UTC par un Community Manager,
**révision 4** du 2026-10-02 à 02:55 UTC. Lu le 2026-10-02 par `uv run forever notes --post 2360696/4` (lecture
ciblée lancée à la main, accord réseau de l'utilisateur). Le lien `/2360696/3` mène à ce message : les n° 2 et 3 sont
vides. Aucun texte du forum n'est recopié (CC BY-NC-SA 3.0). Recoupement complet :
`docs/research/notes-blizzard-2026-10-01.md`.

- Section « User Interface » : l'infobulle de la fiche du personnage dit qu'un sort lancé à un rang très inférieur
  au niveau profite moins de la puissance des sorts et déclenche moins les effets de classe et de talents. La
  **pénalité existe** ; sa **formule** n'est pas donnée.
- Section Hunter > Pets : des bêtes apprivoisables enseignaient des rangs de capacités trop élevés pour leur niveau,
  toutes corrigées. La base de Forever Bestiary installée (0.5.0) date du 2026-09-25 : elle est antérieure.

## Ce qui ne change pas

- `coefficient.low_level` (formule Classic, seuil et pente) reste `suppose` : seule l'existence passe à `probable`.
  La provenance d'un calcul affiche le minimum des deux. L'option `low_level_penalty` et sa plage de sensibilité ne
  changent pas.
- La chance de déclenchement réduite des rangs bas n'entre pas dans les données. Aucune valeur n'est connue, et le
  moteur prend toujours le rang le plus haut. Elle est au registre en B20 (`absent`, `probable`).
- Aucune valeur de `pets.json` ne change. Le guide d'apprivoisement (`forever pets tame`,
  `forever_lookup(kind="pets")`) lit `official_fixes` et signale chaque correctif postérieur à la date de la base de
  Forever Bestiary : une ligne « Attention » dans le guide, une hypothèse dans la provenance de toute consultation des
  familiers. `forever pets rules` le liste.
- Winter's Chill et Fire Vulnerability sans jet de résistance : aucune donnée à changer. Le moteur concorde déjà
  (registre D4), et Fire Vulnerability n'entre pas dans les rotations (I8).
