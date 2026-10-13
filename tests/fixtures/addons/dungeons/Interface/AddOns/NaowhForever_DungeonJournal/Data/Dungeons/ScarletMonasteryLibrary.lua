-- ScarletMonasteryLibrary.lua: fixture synthétique.
local ns = _G.NaowhForever

ns.Journal.AddDungeon("ScarletMonasteryLibrary", {
    name = "Scarlet Monastery - Library",
    zone = "Tirisfal Glades", territory = "Contested",
    wings = {
        { bosses = {
            { npc = 3974, name = "Boss ScarletMonasteryLibrary", encounters = { 446 }, loot = { 7710 }, chance = { 5 } },
        } },
    },
})
