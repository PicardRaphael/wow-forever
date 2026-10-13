-- Extrait structurel de NaowhForever_Discovery 1.1.11 (Data/SleepingBag.lua) pour les tests de T04f : forme, objets,
-- cartes, positions et quêtes gardées ; conseils remplacés par « tip ».
local ns = _G.NaowhForever

local POCKET_LITTER = { object = "Pocket Litter", map = 1442, x = 40.8, y = 52.6, place = "an abandoned camp",
    done = 79192, tip = "tip" }
local MOUND_OF_DIRT = { object = "Mound of Dirt", map = 1442, x = 39.6, y = 49.9, place = "a ledge",
    done = 79980, tip = "tip" }
local CARVED_FIGURINE = { object = "Carved Figurine", map = 1432, x = 49.5, y = 12.8, place = "the Stonewrought Dam",
    done = 79974, tip = "tip" }
local MESSENGER_BAG = { object = "Messenger Bag", map = 1417, x = 22.5, y = 24.2, place = "inside Thoradin's Wall",
    done = 79975, tip = "tip " .. "(suite)" }
local SATCHEL = { object = "Hastily Rolled-Up Satchel", map = 1417, x = 22.5, y = 24.2, place = "under the bag",
    done = 79976, tip = "tip" }

ns.SleepingBag = {
    level = 14,
    item = 211527,
    steps = {
        A = {
            { object = "Burned-Out Remains", map = 1436, x = 37.5, y = 50.7, place = "Alexston Farmstead",
              tip = "tip", started = 79008 },
            { object = "Burned-Out Remains", map = 1413, x = 46.4, y = 73.9,
              place = "the burnt tower south of Camp Taurajo", tip = "tip",
              done = 79008 },
            POCKET_LITTER, MOUND_OF_DIRT, CARVED_FIGURINE, MESSENGER_BAG, SATCHEL,
        },
        H = {
            { object = "Burned-Out Remains", map = 1413, x = 46.4, y = 73.9,
              place = "the burnt tower south of Camp Taurajo", tip = "tip",
              started = 79007 },
            { object = "Burned-Out Remains", map = 1436, x = 37.5, y = 50.7, place = "Alexston Farmstead",
              tip = "tip", done = 79007 },
            POCKET_LITTER, MOUND_OF_DIRT, CARVED_FIGURINE, MESSENGER_BAG, SATCHEL,
        },
    },
    optional = { object = "Firepit", map = 1442, x = 40.6, y = 52.4, place = "the abandoned camp", done = 80001,
        quest = "Rekindle", tip = "tip" },
}
