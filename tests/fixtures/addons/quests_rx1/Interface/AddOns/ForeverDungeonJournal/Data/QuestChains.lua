-- Fixture RX1 : structure de QuestChains.lua de ForeverDungeonJournal (1.6), valeurs et noms inventés.
local ADDON_NAME, FDJ = ...
FDJ = FDJ or _G.ForeverDungeonJournal_NS
local FIXTURE_LOCATION = FDJ.Constants.FIXTURE_LOCATION

FDJ.QUEST_PREREQ_CHAINS = {
    -- Fixture : deux prérequis requis.
    [990052] = {
        { id = 990050, name = "Fixture Rumors" },
        { id = 990051, name = "Fixture Lead" },
    },
}

FDJ.QUEST_PREREQ_DETAILS = {
    [990050] = { level = 31, requires = 24, objective = "Meet the agent.", pickup = "Fixture Giver, Fixture Camp", turnin = "Fixture Agent", description = "Required before." },
    [990051] = { level = 32, requires = 25, objective = "Find him.", pickup = FIXTURE_LOCATION, turnin = FIXTURE_LOCATION, description = "Second.", map = { mapID = 1002, x = 0.530, y = 0.533, label = "Fixture — Inn", detail = "Start here" } },
}
