# data: 1.60.1.70124 r5 → r6

Révision écrite à la main, sans candidate : aucune table du client ne change, `forever install` ne s'applique pas.
Changements notés dans `revisions.json` (`manual_changes`), comme les valeurs écrites à la main de la révision 4.

| Fichier | Chemin | Avant | Après | Source |
| --- | --- | --- | --- | --- |
| pet_rules.json | rules.tame.level_margin.value | 2 | 0 | notes officielles (ci-dessous) |
| pet_rules.json | rules.tame.level_margin.certainty | suppose | probable | texte officiel sans mesure (`docs/DATA_SOURCES.md`) |
| pet_rules.json | rules.tame.level_margin.origin | addon | manuel | règle écrite à la main d'après le texte officiel |
| pet_rules.json | rules.tame.level_margin.date, source, note, text, unit | relevé de joueurs (2026-09-22) | note officielle (version lue du 2026-10-01) | — |
| pet_rules.json, sources.json | source (en-tête du fichier) | relevés de joueurs, au plus suppose | relevés de joueurs et une note officielle, au plus probable | décision 162 |
| origins.json | règle `/rules/tame.level_margin` | — | `manuel`, `probable`, registre L13 | — |
| pet_rules.json | rules.tame.level_margin.registry | L1 | L13 | découpe de L1 (choix de l'utilisateur) |
| sources.json | revision, revised_at | 5, 2026-10-01 | 6, 2026-10-02 | — |

## Source primaire

Notes de développement de la bêta de Forever, sujet officiel ouvert le 24 septembre 2026 par un Community Manager
et révisé le 1er octobre (version 2 du premier message) : <https://us.forums.blizzard.com/en/wow/t/2360696>. Le texte
a été lu le 2026-10-02 par `forever notes` (lancé à la main, accord réseau de l'utilisateur), puis par la lecture
du premier message (JSON Discourse du même hôte, `robots.txt` respecté). La section Hunter > Pets dit que Tame Beast
ne fonctionne plus sur une bête de niveau supérieur à celui du Chasseur. Aucun texte du forum n'est recopié
(CC BY-NC-SA 3.0).

L'historique des révisions du message (`/posts/<id>/revisions/2.json`) est refusé (HTTP 403). On ne sait donc pas si
ce point date du 24 septembre ou du 1er octobre. Dans les deux cas, il est postérieur aux relevés de joueurs de Forever
Bestiary 0.5.0 (18 au 22 septembre 2026).

## Ce qui ne change pas

- Le client ne porte toujours pas la marge : `SpellTargetRestrictions` de Tame Beast a `MaxTargetLevel` nul (accès 6
  de CH0). La règle reste au serveur ; seule une mesure en jeu (bête d'un niveau au-dessus du Chasseur refusée) la
  ferait passer à `certain`.
- Le guide (`forever pets tame`, `forever_lookup(kind="pets")`) lit la valeur des données : `tameable_now` et
  `tameable_at` suivent la nouvelle marge sans changement de code.
- Les autres règles de `pet_rules.json` restent des relevés de joueurs (`suppose`) ; la certitude du fichier
  (`sources.json`) reste `suppose`.
- Registre : L1 découpée (choix de l'utilisateur du 2026-10-02). L1 garde les bêtes apprivoisables (Forever
  Bestiary, `suppose`) ; la nouvelle entrée L13 porte la marge (`probable`).

## Points de la même note examinés sans changement de données

- **Furious Howl** (bonus de puissance d'attaque réduit de 40 %) : points de base des rangs 24604, 24605, 24603 et 24597
  identiques dans 70009 et 70124 (`SpellEffect`, aura 99). Aucune table antérieure à la note n'est en cache (69893 :
  trois tables seulement) : **non vérifiable**, pas un écart. Un correctif du serveur (`DBCache.bin`) reste possible.
- **Sonic Blast** pour les chauves-souris : les sorts 1264478 à 1264488 (« Sonic Blast », rangs 1 à 5) existent dans
  `Spell` et `SpellEffect` de 70124, mais aucune ligne `SkillLineAbility` ne les rattache à une ligne de familier
  (« Pet - Bat » 653 et 3015, « Pet - Generic » 270). `pets.json` donne à la chauve-souris Bite et Dive seulement :
  **non reflété** dans les tables lues par `forever decode` (un octroi par une autre voie reste possible), à revoir à l'installation du client 1.60.1.70170 (installé sur le
  poste le 2026-10-02, non décodé).
- **Hot Streak** 20 s : déjà lu dans le client (T06b), concordance.
- **Ignite** sans double comptage des bonus en pourcentage : déjà appliqué en T05, avec la même source.
- **Arcane Missiles**, ligne de vue vérifiée une seule fois au début de la canalisation : le moteur ne modélise pas
  la ligne de vue (note au registre B6).
