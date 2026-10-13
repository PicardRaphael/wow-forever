-- Extrait structurel de FojjiCore_DungeonJournal 3.3.5 (Data/Guides.lua) pour les tests de T04f : clé, niveau,
-- objet, zones, positions, titres et camps gardés ; textes remplacés par « text ».
local Addon = FojjiCoreNS
if not (Addon and Addon.IsForever) then return end
local FDJ = Addon.DJ

FDJ.Guides = {
    {
        key = "sleepingbag",
        name = "Cozy Sleeping Bag",
        level = 14,
        summary = "text",
        reward = "Cozy Sleeping Bag",
        rewards = { 211527 },
        extras = { 2459, 3388 },
        steps = {
            { zone = "Westfall", x = 37.0, y = 50.0, title = "...and that note you found", side = "Alliance",
                text = "text" },
            { zone = "The Barrens", x = 46.0, y = 74.0, title = "The burned tower", side = "Horde",
                text = "text" },
            { zone = "Stonetalon Mountains", x = 40.6, y = 52.4, title = "Stepping Stones", text = "text" },
            { zone = "Stonetalon Mountains", x = 39.6, y = 49.8, title = "Scramble", text = "text" },
            { zone = "Loch Modan", x = 49.4, y = 12.9, title = "Wet Job", text = "text" },
            { zone = "Hillsbrad Foothills", x = 87.3, y = 49.6, title = "Eagle's Fist", text = "text" },
        },
    },
}
