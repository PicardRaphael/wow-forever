local ns = _G.NaowhForever
local J = ns.Journal

J.QuestData = {
    { name = "Ragefire Chasm", map = 389, levels = { 13, 18 }, quests = {
        { 5723, "Testing an Enemy's Strength", 15, "H", true, "Orgrimmar - Rahauro", 1454, 40.0, 50.0 },
        { 5728, "Hidden Enemies", 16, "H", "pre", "Orgrimmar - Thrall", 1454, 31.0, 37.0 },
    } },
    { name = "Excavation Site: Wetlands", map = 2998, levels = { 24, 29 }, quests = {
        { 96500, "Deep Dig", 27, "B", true, "Menethil - Foreman", 1437, 10.0, 60.0 },
    } },
    { name = "Scarlet Monastery - Graveyard", map = 189, levels = { 26, 36 }, quests = {
        { 90001, "Graveyard Errand", 30, "B", true, "Tirisfal - Gravedigger", 1420, 80.0, 30.0 },
    } },
    { name = "Scarlet Monastery - Library", map = 189, levels = { 29, 39 }, quests = {
        { 90002, "Library Errand", 33, "B", true, "Tirisfal - Archivist", 1420, 81.0, 31.0 },
    } },
    { name = "Scarlet Monastery", map = 189, levels = { 26, 45 }, quests = {
        { 90003, "Monastery Errand", 34, "B", true, "Tirisfal - Pilgrim", 1420, 82.0, 32.0 },
    } },
    { name = "Mystery Hollow", map = nil, levels = { 20, 25 }, quests = {
        { 90004, "Hollow Errand", 22, "B", true, "Wetlands - Hermit", 1437, 50.0, 50.0 },
    } },
    { name = "Alcaz Prison", map = nil, levels = { 35, 40 }, quests = {} },
}

J.QuestTurnIns = {
    [5723] = { 1454, 40.0, 50.0, "Rahauro, Orgrimmar" },
}
