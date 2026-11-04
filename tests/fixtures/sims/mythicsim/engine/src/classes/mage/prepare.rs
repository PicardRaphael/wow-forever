const FOREVER_ARCANE: &[ForeverTalent] = &[
    talent("wand_specialization", "Wand Specialization", 2),
    talent("improved_channeling", "Improved Channeling", 5),
    talent("arcane_resilience", "Arcane Resilience", 3),
    talent("arcane_subtlety", "Arcane Subtlety", 2),
    talent("magic_absorption", "Magic Absorption", 2),
    talent("arcane_concentration", "Arcane Concentration", 5),
    talent("missile_barrage", "Missile Barrage", 2),
    talent("arcane_geometry", "Arcane Geometry", 2),
    talent("arcane_impact", "Arcane Impact", 3),
    talent("arcane_blast", "Arcane Blast", 1),
    talent("arcane_shielding", "Arcane Shielding", 2),
    talent("improved_counterspell", "Improved Counterspell", 2),
    talent("arcane_meditation", "Arcane Meditation", 3),
    talent("arcane_wrath", "Arcane Wrath", 1),
    talent("presence_of_mind", "Presence of Mind", 1),
    talent("arcane_mind", "Arcane Mind", 5),
    talent("arcane_instability", "Arcane Instability", 3),
    talent("arcane_power", "Arcane Power", 1),
];

/// Improved Fire Blast (TraitNode 105797) moves from the first row's first column (5020, 2130)
/// to the third row's fourth (6820, 3330), after Pyroblast. Improved Fireball (11069) is called
/// Accelerant from this build on. Incineration has 5 ranks (TraitNodeEntry 130525, was 3) and
/// Critical Mass 3 (130513, was 5).
const FOREVER_FIRE: &[ForeverTalent] = &[
    talent("incineration", "Incineration", 5),
    talent("improved_fireball", "Accelerant", 5),
    talent("ignite", "Ignite", 5),
    talent("flame_throwing", "Flame Throwing", 2),
    talent("impact", "Impact", 3),
    talent("burning_soul", "Burning Soul", 3),
    talent("improved_flamestrike", "Improved Flamestrike", 3),
    talent("pyroblast", "Pyroblast", 1),
    talent("improved_fire_blast", "Improved Fire Blast", 2),
    talent("improved_scorch", "Improved Scorch", 3),
    talent("improved_fire_ward", "Improved Fire Ward", 2),
    talent("heating_up", "Heating Up", 1),
    talent("master_of_elements", "Master of Elements", 3),
    talent("critical_mass", "Critical Mass", 3),
    talent("blast_wave", "Blast Wave", 1),
    talent("fire_power", "Fire Power", 3),
    talent("combustion", "Combustion", 1),
];

/// Unchanged from the Go reference's order. Elemental Precision is called Precision.
const FOREVER_FROST: &[ForeverTalent] = &[
    talent("frost_warding", "Frost Warding", 2),
    talent("improved_frostbolt", "Improved Frostbolt", 5),
    talent("elemental_precision", "Precision", 3),
    talent("ice_shards", "Ice Shards", 5),
    talent("frostbite", "Frostbite", 3),
    talent("improved_frost_nova", "Improved Frost Nova", 2),
    talent("permafrost", "Permafrost", 3),
    talent("frost_channeling", "Frost Channeling", 3),
    talent("improved_blizzard", "Improved Blizzard", 3),
    talent("ice_lance", "Ice Lance", 1),
    talent("arctic_reach", "Arctic Reach", 2),
    talent("ice_block", "Ice Block", 1),
    talent("shatter", "Shatter", 3),
    talent("improved_cone_of_cold", "Improved Cone of Cold", 3),
    talent("cold_snap", "Cold Snap", 1),
    talent("fingers_of_frost", "Fingers of Frost", 2),
    talent("winters_chill", "Winter's Chill", 5),
    talent("ice_barrier", "Ice Barrier", 1),
];

const FOREVER_TREES: [&[ForeverTalent]; 3] = [FOREVER_ARCANE, FOREVER_FIRE, FOREVER_FROST];
