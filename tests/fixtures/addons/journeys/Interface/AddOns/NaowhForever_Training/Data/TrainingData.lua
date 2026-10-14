-- TrainingData.lua: fixture (valeurs inventées).
local ns = _G.NaowhForever

ns.TrainingData = {
    [1] = {
        { 1, 900001, 10 },
        { 6, 900002, 100 },
    },
    [8] = {
        { 1, 900101, 10 },
        { 2, 900102, 100 },
        { 4, 900103, 200 },
        { 4, 900104, 0, quest = true },
        { 6, 900105, 300, needs = 900102 },
    },
}
