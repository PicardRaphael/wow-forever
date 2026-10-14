-- Fixture RX1 : structure de QuestChains.lua du Dungeon Journal de Naowh (1.1.12), valeurs et noms inventés.
local J = _G.NaowhForever.Journal

J.QuestChains = {
    [990043] = { 990040, 990041, 990042, 990043 },
    [990046] = { { 990044, 990045 }, 990046 },
}

J.QuestPrereqs = {
    [990043] = { 990040, 990041, 990042 },
    [990046] = { { 990044, 990045 } },
}

J.QuestMinLevel = {
    [990040] = 10,
    [990043] = 14,
}

J.QuestWhere = {
    [990043] = "Fixture Vale, Fixture Camp - Fixture Shaman (37.1, 49.4)",
}

J.QuestChainNames = {
    [990040] = "Fixture Call",
    [990041] = "Fixture Call",
    [990042] = "Fixture Call",
    [990043] = "Fixture Call",
    [990046] = "Fixture Blade",
}

J.QuestChainStarts = {
    [990040] = { 1001, 35.2, 8, "Fixture Shaman" },
}
