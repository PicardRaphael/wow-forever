local ADDON_NAME, FDJ = ...
FDJ = FDJ or _G.ForeverDungeonJournal_NS
local ALBA_FAIRMOON_LOCATION = FDJ.Constants.ALBA_FAIRMOON_LOCATION

FDJ.DB = {
    ["Hall of Thanes"] = {
        level = "13-20",
        location = "Beneath Ironforge",
        quests = {{
            id = 96395,
            name = "An Ancient Grudge",
            level = 15,
            requires = 10,
            faction = "Both",
            liveXPFallback = 1000,
        }},
        bosses = {
            { name = "Faldrim Anvilmar", npcID = 900010, loot = { {280010, "Choker", "Neck", 3} } },
        },
    },
}
local DB = FDJ.DB

DB["Ragefire Chasm"] = {
    level = "13-18",
    quests = {{
        id = 5723,
        name = "Testing an Enemy's Strength",
        level = 15,
        requires = 9,
        faction = "Horde",
        liveXPFallback = 1200,
    }, {
        id = 5728,
        name = "Hidden Enemies",
        level = 16,
        requires = 12,
        faction = "Horde",
        liveXPFallback = 1400,
    }},
    bosses = {
        { name = "Taragaman the Hungerer", npcID = 11520 },
    },
}

FDJ.DB["Excavation Site: Wetlands"] = {
    level = "26-33", -- plage propre à l'addon
    quests = {{
        id = 96500,
        name = "Deep Dig",
        level = 27,
        requires = 22,
        faction = "Both",
    }},
    bosses = {
        { name = "Saltspine", npcID = 900002 },
        { name = "Relic Guardian" },
    },
}

FDJ.ORDER = { "Hall of Thanes", "Ragefire Chasm", "Excavation Site: Wetlands" }
