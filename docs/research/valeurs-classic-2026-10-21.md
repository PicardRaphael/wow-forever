# Valeurs héritées de la Classic (recensement du 2026-10-21, décision 294)

Liste produite par `uv run forever origins classic` sur 1.60.1.70450 r8. Chaque réponse qui s'appuie sur ces fichiers le
dit dans sa provenance (build, leveling, poids du Mage, zones, fiches PvP). Remplacement par des valeurs de Forever
après la sortie, avec les mesures de l'utilisateur.

| Fichier | Chemin | Origine | Certitude | Source |
| --- | --- | --- | --- | --- |
| leveling.json | `/combat_rules/armor_dr` | manuel | suppose | règle Classic (texte) jamais lue par le moteur (audit, section 1.4) |
| leveling.json | `/combat_rules/coef_direct` | manuel | suppose | règle Classic (texte) jamais lue par le moteur (audit, section 1.4) |
| leveling.json | `/combat_rules/crit_mult_spell` | manuel | suppose | écrite à la main (règle Classic) règle du serveur, absente des tables ; probable seulement si les journaux la recoupent (bloc B) |
| leveling.json | `/combat_rules/dot_can_crit` | manuel | suppose | écrite à la main (règle Classic) règle du serveur, absente des tables ; probable seulement si les journaux la recoupent (bloc B) |
| leveling.json | `/combat_rules/five_second_rule` | manuel | suppose | règle Classic (texte) jamais lue par le moteur (audit, section 1.4) |
| leveling.json | `/combat_rules/gcd` | manuel | suppose | règle Classic (PC) règle du serveur ; mesures B1 dans les journaux |
| leveling.json | `/combat_rules/haste_rating_per_pct` | manuel | suppose | règle Classic (texte) jamais lue par le moteur (audit, section 1.4) |
| leveling.json | `/combat_rules/level_resist` | manuel | suppose | règle Classic (texte) jamais lue par le moteur (audit, section 1.4) |
| leveling.json | `/combat_rules/min_miss` | manuel | suppose | règle Classic (PC) règle du serveur, absente du client |
| leveling.json | `/combat_rules/pushback_s` | manuel | suppose | règle Classic (PC) règle du serveur, absente du client |
| leveling.json | `/combat_rules/spell_miss_by_level_diff` | manuel | suppose | règle Classic (PC) règle du serveur, absente du client |
| leveling.json | `/mob_xp` | manuel | suppose | règle Classic (texte) texte jamais lu ; doublon de mechanics.json leveling.mob_xp |
| leveling.json | `/player_model` | manuel | suppose | règles Classic (texte) texte jamais lu ; doublon des entrées character de mechanics.json |
| leveling.json | `/xp_to_next` | manuel | suppose | courbe Classic (FC dans le seed) mode seed seulement : le mode forever lit character_scaling.json (LevelExperience) |
| mechanics.json | `/values/build.scenarios` | manuel | suppose | scénario provisoire T05 (décision 82), affiné en DJ1 (donjons) et T09 (raid) : boss de donjon niveau + 2 pendant 60 s, paquet de 4 monstres normaux niveau + 1 (PV du monstre normal du niveau, au plus 40 s), boss de raid niveau + 3 pendant 180 s (durée du seed pve_raid.py) ; tank présent (aucun coup reçu, aucun recul) ; boss insensibles au gel (règle Classic supposée, voir OPEN_QUESTIONS) ; hp boss : PV sans limite (durée fixe), mob : PV du monstre normal ; valeurs inventées pour comparer les builds, pas des chiffres de jeu |
| mechanics.json | `/values/character.base_mana` | manuel | suppose | règle Classic (PC) mode seed seulement : le mode forever lit character_scaling.json |
| mechanics.json | `/values/character.crit_base` | manuel | suppose | Warcraft Tavern, règle Classic (PC) absente du client (chancetospellcritbase vide) |
| mechanics.json | `/values/character.int_per_crit` | manuel | suppose | mode seed seulement (T08b, révision 4 : le mode forever lit character_scaling.json (PlayerExpectedStat.SpellCritPerIntellect)) ; Int pour 1 % de critique : 59,5 au niveau 60 (Mage Classic) ; interpolation linéaire depuis 6 au niveau 1 (EST, fm.py) |
| mechanics.json | `/values/character.mana_from_intellect` | manuel | suppose | règle Classic (PC) absente du client |
| mechanics.json | `/values/character.spirit_regen` | manuel | suppose | règle Classic (PC) absente du client (regenmpperspt vide) |
| mechanics.json | `/values/coefficient.cast_bounds_s` | manuel | suppose | règle Classic (fm.py du seed, PC) mode seed seulement : le mode forever lit les coefficients du client (spell_scaling.json) |
| mechanics.json | `/values/coefficient.cast_divisor` | manuel | suppose | règle Classic (fm.py du seed, PC) mode seed seulement : le mode forever lit les coefficients du client (spell_scaling.json) |
| mechanics.json | `/values/coefficient.channel_cap_s` | manuel | suppose | règle Classic (fm.py du seed, PC) mode seed seulement : le mode forever lit les coefficients du client (spell_scaling.json) |
| mechanics.json | `/values/coefficient.fixed` | manuel | suppose | règle Classic (fm.py du seed, PC) mode seed seulement : le mode forever lit les coefficients du client (spell_scaling.json) |
| mechanics.json | `/values/coefficient.low_level` | manuel | suppose | règle Classic (PC) pénalité des sorts de bas niveau : absente du client (question E2) |
| mechanics.json | `/values/coefficient.low_level_default` | manuel | probable | règle Classic (PC), décision 72 ; existence confirmée par la note officielle du 01/10 (https://us.forums.blizzard.com/en/wow/t/2360696/4, révision 4) pénalité des sorts de bas niveau : absente du client, existence portée par un texte officiel sans mesure ; formule à mesurer (question E2) |
| mechanics.json | `/values/coefficient.slow_factor` | manuel | suppose | règle Classic (fm.py du seed, PC) mode seed seulement : le mode forever lit les coefficients du client (spell_scaling.json) |
| mechanics.json | `/values/hit.miss_per_level_below` | manuel | suppose | règle Classic (PC) règle du serveur, absente du client |
| mechanics.json | `/values/leveling.armor_reduction` | manuel | suppose | règle Classic (PC) mode seed seulement : le mode forever lit character_scaling.json armor_constant |
| mechanics.json | `/values/leveling.mob_xp` | manuel | suppose | règle Classic (PC) XP par monstre : GameTable xp en recoupement (bloc A), modulation au serveur |
| mechanics.json | `/values/leveling.quest_band` | addon | suppose | Questie 11.38.0 (QuestieLib.lua) et règle Classic couleurs de quête lues dans l'addon |
| mechanics.json | `/values/mana.regen_stacking` | manuel | suppose | règle Classic (décision 66) règle du serveur, absente du client |
| mechanics.json | `/values/respec.beta_observed_resets` | manuel | probable | respec.json beta_observed (1 po puis 5 po observés sur la bêta) : les deux premiers paliers du barème sont observés (probable), les suivants suivent la règle Classic (suppose) |
| mechanics.json | `/values/xp.elite_factor` | manuel | suppose | règle de Classic (vMangos, émulateur de Classic 1.12), T04d bloc C règle du serveur absente du client ; facteur de Classic, non vérifié pour Forever (LVL8) |
| mechanics.json | `/values/xp.group` | manuel | suppose | règle de Classic (vMangos, émulateur de Classic 1.12), T04d bloc C règle du serveur absente du client ; multiplicateurs de groupe de Classic, non vérifiés pour Forever (LVL4) |
| mechanics.json | `/values/xp.group_level_basis` | manuel | probable | note officielle du 08/10 (https://us.forums.blizzard.com/en/wow/t/2360696/5, révision 1) : l'XP d'un monstre tué en groupe est ajustée sur le niveau de chaque joueur (règle de Classic Era, individual), plus sur le plus haut niveau du groupe (highest_member, avant ce build) ; aucune XP pour le groupe si un membre est d'un niveau très supérieur au monstre (seuil non donné, question LVL4) ; lue par le modèle d'XP (forever/engine/xp.py, T04d, avec xp.group) |
| mechanics.json | `/values/xp.legacy_rested` | manuel | suppose | description du perk Legacy Well Rested du client (repos accumulé plus vite, plafond relevé) : gain et plafond multipliés par (1 + valeur du rang), valeurs par rang lues dans les courbes (xp_bonuses.json) ; sens des codes d'aura 386 et 656 probable, application au gain et au plafond de Classic supposée (LVL10) |
| mechanics.json | `/values/xp.lower_mob_base` | manuel | probable | relevés du joueur (ForeverLogger 0.3.0, gains d'XP du 2026-09-27 au 2026-10-13, décision 127 : ses observations priment ; accord de l'utilisateur du 2026-10-13) : pour un monstre plus bas que le joueur et non gris, XP = XP de base au niveau du monstre (PerKill du client) × (1 - écart / écart nul) ; 87 gains sur 92 conformes à l'arrondi près (niveau 2 contre 1 : 40 ; 10 contre 5 : 20 ; 16 contre 15 : 107), les 5 autres ne suivent ni cette règle ni celle de Classic (niveau du monstre pris au niveau fixe de Questie, à revérifier) ; aucun gain relevé sur un monstre gris ; probable tant que le niveau des monstres vient de Questie et non de la cible relevée par ForeverLogger 0.4.0 |
| mechanics.json | `/values/xp.mob_level_difference` | manuel | suppose | règle de Classic (vMangos, émulateur de Classic 1.12), T04d bloc C règle du serveur absente du client ; écart de niveau de Classic, non vérifié pour Forever |
| mechanics.json | `/values/xp.quest_level_difference` | manuel | suppose | règle de Classic (vMangos, émulateur de Classic 1.12), T04d bloc C règle du serveur absente du client ; réduction de Classic, non vérifiée pour Forever (LVL7) |
| mechanics.json | `/values/xp.rested` | manuel | suppose | règle de Classic (vMangos, émulateur de Classic 1.12), T04d bloc C règle du serveur ; multiplicateur et période relus dans le client en mode forever, gain et plafond de Classic (LVL10) |
| pet_rules.json | `/rules/training.points_gain` | manuel | suppose | règle de Classic (niveau du familier) ; gain des points d'entraînement inconnu aucune source propre à Forever (CH0) |
| pet_rules.json | `/rules/training.rank_level_applies_to` | manuel | suppose | règle de Classic (niveau du familier) ; gain des points d'entraînement inconnu aucune source propre à Forever (CH0) |
| pvp_rules.json | `/categories` | manuel | suppose | règles de Classic (vmangos, forum de 2019) règles du serveur des rendements décroissants, absentes du client |
| pvp_rules.json | `/diminishing_returns` | manuel | suppose | règles de Classic (vmangos, forum de 2019) règles du serveur des rendements décroissants, absentes du client |
| pvp_rules.json | `/sheets` | manuel | suppose | règles de Classic (vmangos, forum de 2019) règles du serveur des rendements décroissants, absentes du client |
| respec.json | `/classic_decay` | manuel | suppose | barème Classic (PC) règle du serveur, absente du client |
| respec.json | `/classic_schedule_gold` | manuel | suppose | barème Classic (PC) règle du serveur, absente du client |
| respec.json | `/dual_spec` | manuel | suppose | barème Classic (PC) règle du serveur, absente du client |
| respec.json | `/legacy_reset` | manuel | suppose | barème Classic (PC) règle du serveur, absente du client |
