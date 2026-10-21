# 1.60.1.70450 : installation sans correctifs du serveur, défauts trouvés, tests rendus indépendants (2026-10-20)

Installée le 2026-10-20 avec l'accord de l'utilisateur (décision 285, 63 écarts du Mage tranchés « client » après le
rejeu `docs/research/rejeu-70450.md`), depuis les tables du client **sans correctifs du serveur** (pas de session de
jeu possible : ce qui en dépend reste `suppose`). La suite locale comptait alors 229 tests rouges (104 échecs,
125 erreurs). Méthode de la décision 215 : aucun test corrigé valeur par valeur ; d'abord trier les vrais défauts,
puis rattacher chaque famille à la version d'où viennent ses valeurs.

## Révisions installées

| Révision | Contenu | Rapport |
| --- | --- | --- |
| r1 | tables du client de 70450, 63 écarts du Mage confirmés « client » | `docs/research/data-1.60.1.70450-r1.md` |
| r2 | règle du serveur de Heating Up (`hot_streak.server_rules`, `manuel probable`) | `docs/research/data-1.60.1.70450-r2.md` |
| r3 | gabarit `{i}` d'Arcane Wrath (talent ajouté) et de Wake of Fire renommé | `docs/research/data-1.60.1.70450-r3.md` |
| r4 | gabarits alignés sur les textes du client changés depuis 70374 (8 talents du Mage) | `docs/research/data-1.60.1.70450-r4.md` |
| r5 | gabarits numérotés sur les valeurs retenues par rang (Winter's Chill), durées en secondes | `docs/research/data-1.60.1.70450-r5.md` |

## Vrais défauts trouvés par la suite (corrigés dans le code, tests d'abord)

| Défaut | Effet | Correction |
| --- | --- | --- |
| `forever decode` recopiait du `spells.json` hérité un sort nouveau absent du client | une candidate sans Frost Blast ni Arcane Wrath (fixtures de 70009) les gardait : 21 installations refusées | `decode_spells` retire un sort de `new_spells` absent du client |
| un talent ajouté par la fusion gardait l'infobulle brute du client | `forever lookup talent "Arcane Wrath"` affichait `$s1` | `tooltip.placeholder_template`, `desc_template` de chaque talent décodé, repris par la fusion |
| le dépôt gardait l'ancien gabarit quand le client changeait son texte | Arcane Blast décrit avec « dégâts des autres sorts », Winter's Chill avec le critique, Fire Power sans effets de Feu… | le gabarit suit le texte du client changé depuis la plus récente version installée antérieure ; un renommage passé (Hot Streak) ne le remet plus |
| gabarit numéroté sur toutes les variables de l'infobulle | Winter's Chill affichait « {2} » | `decode.rank_template` : numéros sur `ranks`, constantes non retenues en clair |
| `$d` sans unité | « lasts 15 from time of initial application » | unité du client (`duration_unit` du résolveur : sec, min dès une minute), `$D` compris |
| tables par cumul à l'ancien sens (et `explain B15`, `D4` sans l'effet de 70450) | `lookup`/`explain` : Arcane Blast « dégâts des autres sorts », Winter's Chill « critique » nul | `engine/derived` selon le marqueur `model` et la sorte de l'aura |
| B19 : estimation nulle d'Improved Fire Blast | angle mort « critique de Wake of Fire » chiffré à 0 | l'estimation rend None (plus de critique dans 70450) |
| `_client_mechanics` : aura de critique sans remise à zéro du bonus de Cone of Cold | sans effet en production (constantes de base à zéro), visible avec des constantes déjà chargées | remise à zéro explicite |

## Tests rattachés à une version figée

`PRE_70450_VERSION = "1.60.1.70374"` (`tests/conftest.py`) : dernière version avant la refonte (Mage ; arbres du
Prêtre, du Chaman, du Démoniste). Fixtures de session `data_at_pre_70450_version`, `game_data_at_pre_70450_version`
et `make_deps_at_pre_70450_version`. Garde : `test_revision_constants.py::test_frozen_versions_are_installed_and_older`.

| Famille | Cause | Correction |
| --- | --- | --- |
| Talents Forever (`test_tf_code`, `test_export_naowh_build`, `test_talents_forever_*`, `test_bridge_bench`, `test_hunter_p06b`, `test_in_game_survey`, `test_class_witnesses`, `test_parked_nodes`, `test_review_fa1`, `test_addons_status`, `test_tf_code_v7`) | `tests/fixtures/talents_forever/layout.json` est relevé sur les arbres de 70374 ; 70450 remplace Improved Fade et Shadow Affinity (Prêtre, Dark Inspiration), Call of Thunder (Chaman, Elemental Mastery), Malediction (Démoniste, Grim Reach), sorts différents (décision 218 non applicable) | addon fabriqué, Deps (`make_deps` redéfini par module, bancs P06b) et versions attendues sur `PRE_70450_VERSION` |
| Décodage des fixtures (`test_decode_spells`, `test_decode_class_spells`, `test_client_coefficients`, `test_client_decisions`, `test_diff`) | fixtures de 70009 et 70124 comparées à la version installée | référence lue dans `PRE_70450_VERSION` |
| `test_decode_spells::test_installed_observations_are_recorded` | les entrées de 70450 à `old` null (sort ajouté, rang de talent ajouté) ne sont pas des observations | filtre : sort modifié là où le dépôt avait null |
| Moteur, ancien sens (`test_engine_arcane_blast`, `test_engine_character`, `test_engine_mechanics`, `test_engine_talents`, `test_engine_values`, `test_gamedata`, `test_rotations_t05`, `test_totals`, `test_video_examples`, `test_review_t04b`, `test_review_t04c`, `test_encounter`, `test_optimize_leveling::test_build_choices`, `test_blind_spots::test_estimates_are_positive_bounds_from_the_data`) | aura d'Arcane Blast consommée, Winter's Chill au critique, épée de l'Humain, Ice Lance ×4, paliers du Mage de 70374, vidéos et contrôles du seed | `game_data_at_pre_70450_version`, test par test |
| Mes tests de 70450 écrits sur données sans marqueurs (`test_engine_70450_*`) | ils supposaient l'ancien sens dans la version installée | `PRE_70450_VERSION` ; Ruthless et Savage comparés à une base sans critique racial |
| `test_observation_jen`, `test_community_builds::test_legality_is_recomputed` | relevé et builds d’avant 70450 | `PRE_70450_VERSION` |
| `test_lookup_talent::test_rank_gives_the_value_and_the_description_of_that_rank`, `::test_cli_text` | texte d’Improved Frostbolt changé par le client (Frost Blast ajouté, révision 4) | `PRE_70450_VERSION` |

## Restent des angles morts
- RJ1 : l'analytique est optimiste sur les nouveaux Arcanes face au Monte Carlo (temps par monstre −20,8 % à L24,
  −12,6 % à L30, −8 % en leveling 30 du rejeu ; DPS +3,5 % sur un boss au niveau 40). Les tests « analytique ≈ Monte
  Carlo » tournent sur la version installée (Givre, Feu, Arcanes à L30), les cas hors tolérance (Arcanes à L24 et
  sur un boss) en `xfail` strict ; l'ancien sens reste vérifié sur 70374. Registre (notes) et `docs/OPEN_QUESTIONS.md`.
- Aucun relevé de la disposition de Talents Forever génération 7 dans les fixtures : les tests de l'addon tournent
  sur les arbres de 70374 ; l'export des 9 classes sur 70450 a été vérifié à la main (bloc D).
- Presence of Mind : gabarit `{0}` sans valeur retenue (`ranks` vide), antérieur à 70450.
- Limites de la fusion des gabarits (relecture du 2026-10-20) : un talent ajouté dont le gabarit ne peut être ramené
  aux valeurs retenues (`rank_template` rend None) garde l'infobulle brute ; un texte changé dans ce cas garde
  l'ancien gabarit sans le signaler ; une révision réaligne les gabarits des talents changés depuis la version
  précédente (une correction à la main serait réécrite). B19 déduit l'absence de critique du nombre de variables
  d'Improved Fire Blast.

## Révision 6 : correctifs du serveur lus chez Raidbots (2026-10-21, décision 290)
- `forever hotfixes --raidbots` épingle le `DBCache.bin` vérifié le plus récent de 70450 (créé le 2026-10-21 à 06:25,
  sha256 68e09c5c315e…) ; `forever decode --hotfixes --dbcache raidbots` l'applique ; certitude `probable`.
- 31 écarts confirmés (nature `correctif_serveur`) : Piercing Ice retiré (seul talent retiré ; Improved Fire Nova du
  Chaman est un renommage en Trial by Fire, même nœud, même sort) ; Elemental Precision à 3 rangs ; quatre talents du
  Givre changent de colonne ; Winter's Chill, Missile Barrage, Frost Warding, Ice Barrier changent d'infobulle ; valeurs
  de Frost Blast.
- Défauts corrigés : variables de statistique du personnage (`$SPFR`) dans une infobulle ; talent retiré confirmé
  accepté par la fusion ; champ `hotfix` d'un sort traité comme provenance ; moteur sans panne sur un talent absent des
  données (`talent_value`) ; Missile Barrage au marqueur `listed_spells` ; `lookup` dit « probablement retiré » ; builds
  populaires qui placent Piercing Ice écartés avec leur raison.
- Talents Forever 0.38.9 (build 70425) n'a pas le correctif : export du Mage bloqué par la table de recoupement jusqu'à
  la mise à jour de l'addon (dit comme tel).
- Tests rattachés à `PRE_70450_VERSION` (contextes et valeurs relevés avant le correctif) : `test_engine_talents::
  test_prerequisite_must_be_maxed`, `test_damage_modifiers::test_improved_cone_of_cold`, `test_community_builds::
  test_references_are_legal_builds_of_the_optimizer`, `test_departage`, `test_bridge_context::
  test_real_talents_of_the_probe_are_recognized`, `test_leveling_from_current`, exports (`test_bridge_exports`,
  `test_cj1_eui_gear`, `test_bridge_exports_more`) et `test_plugin_evals::test_button_cases_are_the_messages_of_the_bridge`.
  `test_client_decisions::test_confirmed_changes_have_a_nature` admet la nature `correctif_serveur`.
- **Écart connu** : après le correctif, le chemin recommandé et la projection de la respec départagent autrement une
  quasi-égalité au niveau 16 (Ice Shards contre Elemental Precision) ; à reprendre avec l'inversion de fixture (c).
- **Angles morts** : 7 % de puissance des sorts par cumul de Winter's Chill sur Cone of Cold ; Frigid Power d'Ice
  Barrier (HF2).
