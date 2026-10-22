# Tests indépendants de la révision installée et des mesures des journaux (demande de l'utilisateur du 2026-10-02)

But : la prochaine mesure des journaux (`forever measures refresh`) ou la prochaine révision des données ne doit plus
toucher aucun test verrouillé. Même démarche que T08a pour la version : les valeurs de l'état installé sont lues dans
les données installées au lieu d'être écrites dans les tests. Accord donné par l'utilisateur avec la demande.

## I1 — révision installée (`tests/conftest.py`, nouvelles constantes)
- `LOCAL_REVISION`, `LOCAL_REVISED_AT` et `LOCAL_COLLECTED_AT` sont lues dans `forever/data/manifest.json` (version
  installée).
- Nouveau test de garde : `tests/unit/test_revision_constants.py`. Les trois constantes doivent concorder avec
  `sources.json` et avec la dernière entrée de `revisions.json`.
- Tests qui les utilisent :
  - `test_install.py::test_repository_is_revision_two` et `::test_status_shows_the_revision` ;
  - `test_manifest.py::test_manifest_content` (le manifeste recalculé doit égaler le manifeste installé) ;
  - `test_provenance.py::test_make_provenance`.
- `test_origins_r4.py::test_beta_cap_is_an_installation_fact` : la révision où le plafond a été posé est lue dans
  `revisions.json` (dernière révision qui pose le plafond sans le reporter).

## I2 — PV des monstres dans le moteur (`tests/unit/test_engine_monsters.py`)
- Les quatre tests lisent `monsters.json` installé : droite, plage, rapports mesurés et niveaux mesurés.
- Ils vérifient toujours la règle du moteur :
  - un niveau mesuré rend sa mesure et sa certitude ;
  - un niveau de la plage sans mesure prend la droite, `probable` ;
  - au-delà de la plage, `suppose` ;
  - arrondi au demi supérieur.
- Les rapports eux-mêmes restent vérifiés sur fixtures par `test_monsters_correction.py`, inchangé.
- `test_mob_hp_seed_model` et `test_mob_hp_unknown_source_or_level` sont inchangés.

## I3 — écarts des builds communautaires (`tests/unit/test_community_builds.py`, `scripts/build_community_fixture.py`)
- Le script écrit à côté de la fixture une copie de `monsters.json` installé (`tests/fixtures/community/monsters.json`)
  et son empreinte (`monsters_sha256`).
- `test_gaps_are_computed_by_the_engine` recalcule les écarts sur une copie du dépôt qui porte ces PV-là. Une mesure
  des journaux ne le touche plus.
- Un changement de version (talents, sorts) demande toujours de régénérer la fixture.
- Nouveau test : `test_frozen_monsters_are_the_ones_of_the_comparison` (empreinte et version de la copie).
