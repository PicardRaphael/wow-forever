local ns = _G.NaowhForever
local J = ns.Journal

J.QuestChains = {
    [5728] = { 5726, 5727, 5728 },
}

J.QuestPrereqs = {
    [5728] = { 5727 },
    [96500] = { 96498, { 96499, 96497 } },
}

J.QuestMinLevel = {
    [5723] = 9,
    [96500] = 22,
}
