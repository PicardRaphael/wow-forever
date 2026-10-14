-- Fixture RX1 : structure de Books.lua de Naowh Discovery (1.1.12), valeurs et noms inventés.
local ns = _G.NaowhForever

ns.LibraryGoals = {
    { quest = 990020, name = "Fixture Reader", books = 10,
      rewards = { { 990900, "Fixture Pendant" } } },
    { quest = 990021, name = "Fixture Scholar", books = 25, level = 30, reported = true,
      rewards = { { 990901, "Fixture Bow" } } },
}

ns.LibraryTurnIns = {
    librarian = { { 1001, 10.0, 20.0, "Fixture Librarian" } },
}

ns.LibraryBooks = {
    { quest = 990022, item = 990910, tier = 20, side = "H", turnIn = "librarian",
      name = "Fixture Almanac, Vol. 1",
      spots = { { 1001, 12.5, 34.5, "Fixture Hut", "On a shelf." } } },
    { quest = 990023, item = 990911, tier = 20, side = "B", turnIn = "librarian", unplaced = true,
      name = "Fixture Digest",
      spots = {} },
    { quest = 990024, item = 990912, tier = 60, side = "A", turnIn = "trainer",
      name = "Fixture Primer",
      spots = { { 1002, 55.0, 66.0, "Fixture Tower", "On the floor." } } },
}
