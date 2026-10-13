local J = _G.NaowhForever.Journal

J.QuestData = {
    { name = "Ragefire Chasm", map = 389, levels = { 13, 18 }, quests = {
        { 5761, "Slaying the Beast", 9, "H", true, "Orgrimmar, The Drag - Neeru Fireblade (49.5, 50.6)", 1454, 49.5, 50.6 },
        { 5725, "The Power to Destroy...", 9, "H", true, "Undercity, Royal Quarter - Varimathras (56.2, 92.2)", 1458, 56.2, 92.2 },
        { 5723, "Testing an Enemy's Strength", 9, "H", true, "Thunder Bluff, Elder Rise - Rahauro (70.1, 29.5)", 1456, 70.1, 29.5 },
        { 5722, "Searching for the Lost Satchel", 9, "H", true, "Thunder Bluff, Elder Rise - Rahauro; the satchel is on Maur Grimtotem inside RFC (70.1, 29.5)", 1456, 70.1, 29.5, steps = { 5724 } },
        { 5728, "Hidden Enemies", 9, "H", "pre", "Orgrimmar, Valley of Wisdom - Thrall Prerequisite: Complete 3 quests, starting with Hidden Enemies from Thrall (31.7, 37.8)", 1454, 31.7, 37.8 },
    } },
    { name = "The Hall of Thanes", map = 3065, levels = { 13, 18 }, quests = {
        { 96403, "Important Heirlooms", 14, "A", true, "Ironforge, Old Ironforge - Thom Filch (32.6, 44.6)", 1455, 32.6, 44.6 },
        { 96394, "The Restless Dead", 15, "A", true, "Ironforge, Old Ironforge - Afadra Dunwall (33.2, 47.8)", 1455, 33.2, 47.8 },
        { 96393, "Old Ironforge Incursion", 15, "A", true, "Dun Morogh, Gol'Golar Quarry - Earthseer Farsen Prerequisite to pick up Underground Map from Dark Iron Map (64.8, 58.4)", 1426, 64.8, 58.4 },
        { 98423, "The Treaty of Understanding", 16, "A", false, "The Hall of Thanes, Located in the Reliquary of Kings in a Vault" },
        { 96395, "An Ancient Grudge", 14, "H", true, "The Hall of Thanes, Anvilmar's Rest - Ghostly Attendant" },
    } },
}
