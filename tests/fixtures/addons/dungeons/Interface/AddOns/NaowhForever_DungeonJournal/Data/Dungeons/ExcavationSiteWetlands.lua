-- ExcavationSiteWetlands.lua: fixture synthétique.
local ns = _G.NaowhForever

ns.Journal.AddDungeon("ExcavationSiteWetlands", {
    name = "Excavation Site: Wetlands",
    zone = "Wetlands", territory = "Contested",
    new = true,
    entrance = { map = 1437, x = 40.0, y = 30.0 },
    wings = {
        { bosses = {
            { npc = 900001, name = "Highland Horror", encounters = { 3644 }, loot = { 280001 }, chance = { 12 } },
            { npc = 900002, name = "Saltspine", encounters = { 3480 }, loot = { 280002 }, chance = { 20 } },
        } },
    },
})
