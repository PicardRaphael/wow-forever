-- Network.lua: fixture (valeurs inventées).
local ns = _G.NaowhForever

ns.JourneyNetwork = {
    flights = {
        [1] = { "Fixture Field", 0, 100.0, 100.0, 0.0, "A" },
    },
    hops = {
        { 1, 1, 10 },
    },
    ships = {
        { "Boat", "AH", { 0, 0.0, 0.0, 9001, "West Dock", 30, 1000 }, { 1, 0.0, 0.0, 9002, "East Dock", 40, 2000 } },
        { "Zeppelin", "H", { 0, 500.0, 0.0, 9001, "West Tower", 20, 3000 }, { 1, 500.0, 0.0, 9002, "East Tower", 20, 3000 } },
    },
    links = {
        { "Tram", "AH", 50, { 0, 2000.0, 0.0, "Fixture Hall" }, { 0, 4000.0, 0.0, "Fixture Vault" } },
    },
}
