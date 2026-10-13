-- RagefireChasm.lua: fixture synthétique.
local ns = _G.NaowhForever

ns.Journal.AddDungeon("RagefireChasm", {
    name = "Ragefire Chasm",
    zone = "Orgrimmar", territory = "Horde",
    entrance = { map = 1454, x = 52.0, y = 49.0 },
    wings = {
        { bosses = {
            { npc = 11520, name = "Taragaman the Hungerer", model = 1, encounters = { 2733 }, loot = { 14149, 14148 }, chance = { 32, 0 } },
            { npc = 11518, name = "Jergosh the Invoker", model = 2, encounters = { 2734 }, loot = { 14150 }, chance = { 25 } },
            { npc = nil, name = "Trash", trash = true, loot = { 14151 } },
        } },
    },
})
