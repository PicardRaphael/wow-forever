# Valeurs écrites à la main

Généré par `uv run forever origins inventory` sur la version 1.60.1.70245 (ne pas éditer à la main : le test
`tests/unit/test_origins_inventory.py` compare ce fichier au rendu de la commande). Chaque ligne est un chemin
de `forever/data/1.60.1.70245/` dont l'origine déclarée dans `origins.json` est `manuel` : ni décodé du client,
ni mesuré, ni lu dans un addon. Les valeurs elles-mêmes ne sont pas recopiées ici.

148 chemins, 616 valeurs ; 83 `probable`, 65 `suppose`

## Abaissements de certitude prévus

Aucun.

## Inventaire

| Fichier | Chemin | Valeurs | Certitude | Registre | Raison | Source |
| --- | --- | --- | --- | --- | --- | --- |
| character_scaling.json | `/level_cap` | 1 | probable | — | niveau maximal écrit à la main, recopié du fichier des règles de lecture (D2) | decode_rules.json levels.level_cap |
| decode_rules.json | `/community_positions` | 4 | probable | — | positions hors grille absentes du client | calculateurs communautaires de la bêta (PV1, D3) |
| decode_rules.json | `/levels/level_cap` | 1 | probable | I5 | aucune table du client ne le porte (D2) | niveau maximal annoncé de Forever |
| leveling.json | `/combat_rules/armor_dr` | 1 | suppose | — | jamais lue par le moteur (audit, section 1.4) | règle Classic (texte) |
| leveling.json | `/combat_rules/coef_direct` | 1 | suppose | — | jamais lue par le moteur (audit, section 1.4) | règle Classic (texte) |
| leveling.json | `/combat_rules/crit_mult_spell` | 1 | suppose | — | règle du serveur, absente des tables ; probable seulement si les journaux la recoupent (bloc B) | écrite à la main (règle Classic) |
| leveling.json | `/combat_rules/dot_can_crit` | 1 | suppose | — | règle du serveur, absente des tables ; probable seulement si les journaux la recoupent (bloc B) | écrite à la main (règle Classic) |
| leveling.json | `/combat_rules/five_second_rule` | 1 | suppose | — | jamais lue par le moteur (audit, section 1.4) | règle Classic (texte) |
| leveling.json | `/combat_rules/gcd` | 1 | suppose | — | règle du serveur ; mesures B1 dans les journaux | règle Classic (PC) |
| leveling.json | `/combat_rules/haste_rating_per_pct` | 1 | suppose | — | jamais lue par le moteur (audit, section 1.4) | règle Classic (texte) |
| leveling.json | `/combat_rules/level_resist` | 1 | suppose | — | jamais lue par le moteur (audit, section 1.4) | règle Classic (texte) |
| leveling.json | `/combat_rules/min_miss` | 1 | suppose | — | règle du serveur, absente du client | règle Classic (PC) |
| leveling.json | `/combat_rules/pushback_s` | 1 | suppose | — | règle du serveur, absente du client | règle Classic (PC) |
| leveling.json | `/combat_rules/spell_miss_by_level_diff` | 7 | suppose | — | règle du serveur, absente du client | règle Classic (PC) |
| leveling.json | `/mob_model` | 22 | suppose | — | combat et PV des monstres du mode seed : règles du serveur | sim_leveling.py du seed (EST) |
| leveling.json | `/mob_xp` | 16 | suppose | — | texte jamais lu ; doublon de mechanics.json leveling.mob_xp | règle Classic (texte) |
| leveling.json | `/player_model` | 8 | suppose | — | texte jamais lu ; doublon des entrées character de mechanics.json | règles Classic (texte) |
| leveling.json | `/xp_to_next` | 59 | suppose | — | mode seed seulement : le mode forever lit character_scaling.json (LevelExperience) | courbe Classic (FC dans le seed) |
| mechanics.json | `/values/build.scenarios` | 15 | suppose | H3 | rencontres inventées pour comparer les builds, affinées en DJ1 et T09 | scénarios provisoires (T05, décision 82) |
| mechanics.json | `/values/character.armor` | 4 | suppose | G2 | statistiques de base absentes du client (fichiers du serveur) | fm.py du seed (EST) |
| mechanics.json | `/values/character.base_mana` | 2 | suppose | B9 | mode seed seulement : le mode forever lit character_scaling.json | règle Classic (PC) |
| mechanics.json | `/values/character.crit_base` | 1 | suppose | A5 | absente du client (chancetospellcritbase vide) | Warcraft Tavern, règle Classic (PC) |
| mechanics.json | `/values/character.hp` | 3 | suppose | G2 | PV de base absents du client (octbasehpbyclass vide) | fm.py du seed (EST) |
| mechanics.json | `/values/character.int_per_crit` | 4 | suppose | A5 | mode seed seulement : le mode forever lit character_scaling.json | fm.py du seed (EST, interpolation) |
| mechanics.json | `/values/character.intellect` | 4 | suppose | G2 | statistiques de base absentes du client (fichiers du serveur) | fm.py du seed (EST) |
| mechanics.json | `/values/character.mana_from_intellect` | 2 | suppose | B9 | absente du client | règle Classic (PC) |
| mechanics.json | `/values/character.spell_power` | 2 | suppose | G2 | puissance des sorts d'équipement estimée, hors du client | fm.py du seed (EST) |
| mechanics.json | `/values/character.spirit` | 4 | suppose | G2 | statistiques de base absentes du client (fichiers du serveur) | fm.py du seed (EST) |
| mechanics.json | `/values/character.spirit_regen` | 3 | suppose | G2 | absente du client (regenmpperspt vide) | règle Classic (PC) |
| mechanics.json | `/values/coefficient.cast_bounds_s` | 2 | suppose | G4 | mode seed seulement : le mode forever lit les coefficients du client (spell_scaling.json) | règle Classic (fm.py du seed, PC) |
| mechanics.json | `/values/coefficient.cast_divisor` | 1 | suppose | G4 | mode seed seulement : le mode forever lit les coefficients du client (spell_scaling.json) | règle Classic (fm.py du seed, PC) |
| mechanics.json | `/values/coefficient.channel_cap_s` | 1 | suppose | G4 | mode seed seulement : le mode forever lit les coefficients du client (spell_scaling.json) | règle Classic (fm.py du seed, PC) |
| mechanics.json | `/values/coefficient.fixed` | 10 | suppose | G4 | mode seed seulement : le mode forever lit les coefficients du client (spell_scaling.json) | règle Classic (fm.py du seed, PC) |
| mechanics.json | `/values/coefficient.low_level` | 2 | suppose | G4 | pénalité des sorts de bas niveau : absente du client (question E2) | règle Classic (PC) |
| mechanics.json | `/values/coefficient.low_level_default` | 3 | probable | G4 | pénalité des sorts de bas niveau : absente du client, existence portée par un texte officiel sans mesure ; formule à mesurer (question E2) | règle Classic (PC), décision 72 ; existence confirmée par la note officielle du 01/10 (https://us.forums.blizzard.com/en/wow/t/2360696/4, révision 4) |
| mechanics.json | `/values/coefficient.slow_factor` | 1 | suppose | G4 | mode seed seulement : le mode forever lit les coefficients du client (spell_scaling.json) | règle Classic (fm.py du seed, PC) |
| mechanics.json | `/values/crit.winters_chill_per_stack` | 1 | probable | D4 | mode seed seulement : le mode forever lit spell_scaling.json auras.winters_chill | relevé du client 1.60.1.70009 recopié à la main (references/mechanics.md) |
| mechanics.json | `/values/damage.bonus_stacking` | 3 | probable | A20 | règle du serveur, test en jeu E6 | vidéo communautaire (décision 73) |
| mechanics.json | `/values/hit.miss_per_level_below` | 3 | suppose | A3 | règle du serveur, absente du client | règle Classic (PC) |
| mechanics.json | `/values/leveling.analytic` | 3 | suppose | I6 | hypothèses du modèle analytique | sim_leveling.py du seed (EST) |
| mechanics.json | `/values/leveling.armor_reduction` | 2 | suppose | I6 | mode seed seulement : le mode forever lit character_scaling.json armor_constant | règle Classic (PC) |
| mechanics.json | `/values/leveling.defaults` | 3 | suppose | I6 | hypothèses par défaut du simulateur (monstre, course entre deux monstres) | sim_leveling.py du seed (EST) |
| mechanics.json | `/values/leveling.dot_tick_s` | 1 | suppose | A17 | mode seed : le mode forever lit period_ms du client | sim_leveling.py du seed (EST) |
| mechanics.json | `/values/leveling.frost_nova_retreat_yd` | 1 | suppose | I1 | estimation du simulateur du seed | sim_leveling.py du seed (EST) |
| mechanics.json | `/values/leveling.frostbite_freeze_s` | 1 | suppose | C5 | estimation du simulateur du seed | sim_leveling.py du seed (EST) |
| mechanics.json | `/values/leveling.ignite` | 4 | probable | A18 | mode seed seulement : le mode forever lit spell_scaling.json auras.ignite | tables du client 1.60.1.70009 relues à la main (T04c) |
| mechanics.json | `/values/leveling.ignite_rule` | 3 | suppose | A18 | règle du serveur (Ignite roulant), absente du client | T04c, décision 2 |
| mechanics.json | `/values/leveling.mob_hit_damage` | 2 | suppose | I6 | combat des monstres : règle du serveur, absente du client | sim_leveling.py du seed (EST) |
| mechanics.json | `/values/leveling.mob_xp` | 2 | suppose | I6 | XP par monstre : GameTable xp en recoupement (bloc A), modulation au serveur | règle Classic (PC) |
| mechanics.json | `/values/leveling.projectile_speed` | 2 | suppose | C1 | vitesse des projectiles non publiée | sim_leveling.py du seed (EST) |
| mechanics.json | `/values/leveling.rest_hp_regen_fraction` | 1 | suppose | I6 | régénération au repos : formule du serveur (courbes de GlobalCurve décodées au bloc A, non utilisées) | sim_leveling.py du seed (EST) |
| mechanics.json | `/values/mana.regen_stacking` | 3 | suppose | B7 | règle du serveur, absente du client | règle Classic (décision 66) |
| mechanics.json | `/values/mana.talent_rank_cost` | 2 | suppose | B11 | mode seed seulement : coût non publié | estimation du seed (EST) |
| mechanics.json | `/values/pvp.profile` | 41 | suppose | I5 | modèle de scénarios du seed, sans simulation de duel | pvp.py du seed (EST) |
| mechanics.json | `/values/pvp.weights` | 8 | suppose | I5 | modèle de scénarios du seed, sans simulation de duel | pvp.py du seed (EST) |
| mechanics.json | `/values/respec.beta_observed_resets` | 1 | probable | I5 | relevé communautaire, pas de mesure du projet | observations de la bêta (respec.json) |
| mechanics.json | `/values/respec.gold_per_hour` | 6 | suppose | I5 | rythme de gain d'or du joueur estimé | respec.py du seed (EST) |
| mechanics.json | `/values/respec.trip_minutes` | 1 | suppose | I5 | trajet chez le maître de classe estimé | respec.py du seed (EST) |
| mechanics.json | `/values/spell.default_range_yd` | 1 | suppose | C2 | portée par défaut d'un sort sans portée publiée | repli de fm.py du seed |
| mechanics.json | `/values/talents.first_level` | 1 | probable | G3 | mode seed seulement : le mode forever lit character_scaling.json (NumTalentsAtLevel) | fm.py du seed (points_available) |
| mechanics.json | `/values/talents.points_per_tier` | 1 | probable | G3 | mode seed seulement : le mode forever lit character_scaling.json (TraitCond) | fm.py du seed (check_build) |
| overrides.json | `/Arcane~1Arcane Blast` | 6 | probable | — | corrections de rangs relevées sur un site, jamais lues par le moteur | foreverchanges.pro (build 1.60.1.70009) |
| overrides.json | `/Fire~1Blast Wave` | 4 | probable | — | corrections de rangs relevées sur un site, jamais lues par le moteur | foreverchanges.pro (build 1.60.1.70009) |
| overrides.json | `/Fire~1Pyroblast` | 4 | probable | — | corrections de rangs relevées sur un site, jamais lues par le moteur | foreverchanges.pro (build 1.60.1.70009) |
| overrides.json | `/Frost~1Ice Barrier` | 2 | probable | — | corrections de rangs relevées sur un site, jamais lues par le moteur | foreverchanges.pro (build 1.60.1.70009) |
| overrides.json | `/Frost~1Ice Lance` | 3 | probable | — | corrections de rangs relevées sur un site, jamais lues par le moteur | foreverchanges.pro (build 1.60.1.70009) |
| pet_rules.json | `/official_fixes` | 3 | probable | L3 | correctif du serveur absent du client, porté par un texte officiel sans mesure (révision 3) | notes de développement officielles de la bêta, mise à jour du 1er octobre 2026 (https://us.forums.blizzard.com/en/wow/t/2360696/4, révision 4) |
| pet_rules.json | `/rules/tame.level_margin` | 5 | probable | L13 | règle du serveur absente du client, portée par un texte officiel sans mesure (révision 6) | notes de développement officielles de la bêta du 24 septembre 2026, révisées le 1er octobre (https://us.forums.blizzard.com/en/wow/t/2360696) |
| pet_rules.json | `/rules/training.points_gain` | 3 | suppose | L3 | aucune source propre à Forever (CH0) | règle de Classic (niveau du familier) ; gain des points d'entraînement inconnu |
| pet_rules.json | `/rules/training.rank_level_applies_to` | 4 | suppose | L3 | aucune source propre à Forever (CH0) | règle de Classic (niveau du familier) ; gain des points d'entraînement inconnu |
| pvp_rules.json | `/categories` | 9 | suppose | K1 | règles du serveur des rendements décroissants, absentes du client | règles de Classic (vmangos, forum de 2019) |
| pvp_rules.json | `/diminishing_returns` | 6 | suppose | K1 | règles du serveur des rendements décroissants, absentes du client | règles de Classic (vmangos, forum de 2019) |
| pvp_rules.json | `/sheets` | 1 | suppose | K1 | règles du serveur des rendements décroissants, absentes du client | règles de Classic (vmangos, forum de 2019) |
| respec.json | `/beta_observed` | 4 | probable | — | barème observé sur la bêta, pas mesuré par le projet | observations de la bêta (relevé communautaire) |
| respec.json | `/classic_decay` | 1 | suppose | — | règle du serveur, absente du client | barème Classic (PC) |
| respec.json | `/classic_schedule_gold` | 11 | suppose | — | règle du serveur, absente du client | barème Classic (PC) |
| respec.json | `/dual_spec` | 1 | suppose | — | règle du serveur, absente du client | barème Classic (PC) |
| respec.json | `/legacy_reset` | 1 | suppose | — | règle du serveur, absente du client | barème Classic (PC) |
| spell_scaling.json | `/level_cap` | 1 | probable | — | niveau maximal écrit à la main, recopié du fichier des règles de lecture (D2) | decode_rules.json levels.level_cap |
| spells.json | `/spells/arcane_blast/mana_pct_base` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/arcane_blast/range` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/arcane_blast/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/arcane_blast/talent` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/arcane_explosion/aoe` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/arcane_explosion/radius` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/arcane_explosion/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/arcane_missiles/channel` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/arcane_missiles/range` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/arcane_missiles/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/blast_wave/aoe` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/blast_wave/daze` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/blast_wave/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/blast_wave/talent` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/blizzard/aoe` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/blizzard/channel` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/blizzard/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/cone_of_cold/aoe` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/cone_of_cold/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/cone_of_cold/slow` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/cone_of_cold/slow_dur` | 5 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/fire_blast/range` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/fire_blast/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/fireball/projectile_speed` | 1 | suppose | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | estimation du seed (EST) |
| spells.json | `/spells/fireball/range` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/fireball/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/flamestrike/aoe` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/flamestrike/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frost_nova/aoe` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frost_nova/breaks_on_damage` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frost_nova/freeze` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frost_nova/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frostbolt/binary` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frostbolt/projectile_speed` | 1 | suppose | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | estimation du seed (EST) |
| spells.json | `/spells/frostbolt/range` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frostbolt/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frostbolt/slow` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frostbolt/slow_dur` | 11 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frostfire_bolt/projectile_speed` | 1 | suppose | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | estimation du seed (EST) |
| spells.json | `/spells/frostfire_bolt/range` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frostfire_bolt/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frostfire_bolt/slow` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/frostfire_bolt/slow_dur` | 3 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/ice_lance/frozen_mult` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/ice_lance/projectile_speed` | 1 | suppose | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | estimation du seed (EST) |
| spells.json | `/spells/ice_lance/range` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/ice_lance/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/ice_lance/talent` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/pyroblast/projectile_speed` | 1 | suppose | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | estimation du seed (EST) |
| spells.json | `/spells/pyroblast/range` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/pyroblast/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/pyroblast/talent` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/scorch/range` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/spells/scorch/school` | 1 | probable | — | champ hors rang recopié du seed, jamais relu dans le client ; classes.json en porte plusieurs (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/arcane_intellect` | 10 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/blink` | 3 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/conjure_food` | 21 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/conjure_water` | 21 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/counterspell` | 4 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/evocation` | 4 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/fire_ward` | 16 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/frost_armor` | 12 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/frost_ward` | 16 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/ice_armor` | 14 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/ice_barrier` | 13 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/mage_armor` | 10 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/mana_gems` | 12 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/mana_shield` | 19 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
| spells.json | `/utility/polymorph` | 13 | probable | C2 | utilitaire recopié du seed ; classes.json porte des valeurs décodées (D2, bloc B) | copie du seed (wowforevertalents.com, build 1.60.1.70009) |
