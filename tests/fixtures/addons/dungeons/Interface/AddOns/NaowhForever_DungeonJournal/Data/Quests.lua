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
    { name = "Alcaz Prison", map = nil, levels = { 35, 40 }, quests = {} },
}

J.QuestTurnIns = {
    [5723] = { 1454, 40.0, 50.0, "Rahauro, Orgrimmar" },
}
