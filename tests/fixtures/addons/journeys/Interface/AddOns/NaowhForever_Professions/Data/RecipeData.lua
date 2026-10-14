-- RecipeData.lua: fixture (valeurs inventées), structure du fichier de Naowh Forever Professions.
local ns = _G.NaowhForever

ns.RecipeData = {
    [9171] = {
        skillSpell = 9001,
        trainers = {
            { 990101, "Fixture Brewer", "H", 9001, 42.0, 42.0 },
            { 990102, "Fixture Distiller", "A", 9002, 70.0, 70.0 },
            { 990103, "Fixture Neutral", "-", 9002, 10.0, 10.0 },
        },
        ranks = {
            { cap = 150, skill = 50, spell = 9002, name = "Journeyman Fixturecraft", cost = 500 },
            { cap = 225, skill = 125, spell = 9003, name = "Expert Fixturecraft", cost = 5000 },
            { cap = 300, skill = 200, level = 4, spell = 9004, name = "Artisan Fixturecraft", cost = 45000 },
        },
        recipes = {
            { spell = 9101, item = 9201, skill = 1, source = "trainer", cost = 50 },
        },
    },
}
