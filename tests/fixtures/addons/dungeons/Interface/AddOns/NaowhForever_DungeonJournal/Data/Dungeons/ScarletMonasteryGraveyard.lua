-- ScarletMonasteryGraveyard.lua: fixture synthétique.
local ns = _G.NaowhForever

ns.Journal.AddDungeon("ScarletMonasteryGraveyard", {
    name = "Scarlet Monastery - Graveyard",
    zone = "Tirisfal Glades", territory = "Contested",
    wings = {
        { bosses = {
            { npc = 3983, name = "Boss ScarletMonasteryGraveyard", encounters = { 444 }, loot = { 7710 }, chance = { 5 } },
        } },
    },
})
