-- Données fabriquées pour les tests (structure de GearQuest Forever 1.2.2 : choix rangés en texte, `<classe>PicksPacked`).
local GQ = _G.GearQuest
GQ.Data.warlockItemFacts = {
    [900101]={name="Fixture Cowl",quality=3,ilvl=25,reqLevel=20,sourceType="quest_reward",instructions="Fixture quest.",zone="Fixture Vale"},
}
GQ.Data.warlockPicksPacked = {
    slots = {"Head","SecondaryHand"},
    specs = {"affliction","destruction"},
    extras = {
        {suffix="of Fixture",suffixChance=4,suffixId=1,suffixRange="+1-3 Intellect"},
    },
    rows = {
        ["Alliance"] = "900101 1 18 22 1 2 3.5 0\n900102 2 18 22 2 1 2.25 1\n",
        ["Horde"] = "900103 1 20 25 1 1 1.5 0\n",
    },
    specMask = {
        ["Alliance"] = "\n900101 12\n",
    },
    suffixRows = "900102 18 1\n",
}
