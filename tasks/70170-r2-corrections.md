# 1.60.1.70170 révision 2 : demandes de correction de tests (regroupées avant le commit)

Cause commune : la révision 2 (accord de l'utilisateur du 2026-10-02) écrit la mesure du premier journal de 70170
(`WoWCombatLog-100226_080035`) dans `monsters.json`. Elle ajoute 30 PNJ mesurés et recalcule la correction Questie
sur 13 niveaux (1 à 22 au lieu de 1 à 17 ; pente 0,0238 au lieu de 0,0248). Les quatre PNJ hors norme sont écartés de
la courbe. Le diff exact est dans l'arbre de travail (`git diff -- tests`).

## R1 — `tests/unit/test_engine_monsters.py` (T04b, valeurs de la correction installée)
- `SLOPE, INTERCEPT` : valeurs de la révision 2 ; plage `(1, 17)` → `(1, 22)`.
- `test_questie_ratio` : le niveau 16 est désormais mesuré ; la droite se contrôle au niveau 8 (dans la plage, sans
  mesure à ce niveau). Le niveau 30 reste au-delà (`suppose`).
- `test_corrected_questie_hp` : même raison, niveau 16 → 8 (356 × rapport du niveau 8 = 361, `probable`).
- `test_mob_hp_measured_first` : le niveau 20 est désormais mesuré (629, `certain`) ; le niveau hors plage contrôlé
  devient le 23 (`suppose`, Questie corrigé). Le niveau 16 garde son assertion (mesuré, `probable`, entre 385 et 473).

## R2 — révision des données 1 → 2
- `test_install.py::test_repository_is_revision_two`, `test_install.py::test_status_shows_the_revision`,
  `test_manifest.py::test_manifest_content`, `test_provenance.py::test_make_provenance`.

## R3 — fixture `tests/fixtures/community/mage_builds.json` (régénérée par `scripts/build_community_fixture.py`)
- Écarts analytiques recalculés pour les builds communautaires des niveaux touchés par les PV des monstres :
  - leveling 30 : C4, C10, A2, A3, A4, A7, A8, A9, A25, A30, A31, A34 ;
  - leveling 40 : C8 ;
  - donjon 20 et 60 : C11, C13, A29.
  Les variations sont de 0,1 point de pourcentage au plus, et aucune nature d'écart ne change.
- **Référence du donjon au niveau 30** (préréglage rapide de la fixture) : elle passe d'un build Arcanes à 0/0/21 Givre.
  C12 passe ainsi de « concorde » à « mécanique non modélisée » (+10,2 %).
  Contrôle en préréglage complet (`build_report(..., "dungeon", 30, preset="complet")`) : 0/0/21 Givre, identique en
  révisions 1 et 2 (stable 5/5 en révision 2, 4/5 en révision 1). Le préréglage rapide rejoint la réponse complète.
- Le tableau « Comparaison avec nos builds » de `docs/research/community-builds-mage.md` est régénéré par le même
  script.
- `tests/unit/test_community_builds.py::test_gaps_are_computed_by_the_engine` passe sans modification.

## Tests ajoutés (écrits avant le code, échec constaté)
- `tests/unit/test_monsters_curve_exclude.py` : PNJ hors norme mesurés mais écartés de `hp_by_level` et de la
  correction, raison obligatoire, liste reprise de `monsters.json` installé.
