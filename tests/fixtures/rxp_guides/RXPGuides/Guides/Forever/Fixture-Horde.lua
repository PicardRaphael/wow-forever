local faction = UnitFactionGroup("player")
if faction == "Alliance" then return end

RXPGuides.RegisterGuide([[
#forever
<< Horde
#name 1-3 Fixture Vale
#version 1
#group Fixture Guide (H)
#defaultfor Orc/Troll
#next 3-5 Fixture Hills << !Hunter
#next 3-5 Fixture Hunter Hills << Hunter

step
    .goto Fixture Vale,40,41
    .accept 101 >>Accept Fixture Secret Text
step << Mage
    .accept 107
step << Tauren
    .accept 105
step
    .accept 102
    .complete 101,1 --Fixture objective one
step
    .complete 101,2
    .turnin 101,1
step << skip
    .accept 106
step
    .dungeon FIX
    .accept 111
step
    .xp <9,1
    .accept 999
]])

RXPGuides.RegisterGuide([[
#forever
<< Horde
#name 3-5 Fixture Hills
#group Fixture Guide (H)
#next Fixture Guide (H)\5-12 Fixture Paid Lands

step
    #xprate >1.99
    .accept 110
step
    .xp 3
step
    .isOnQuest 102
    .complete 102,1
    .turnin 102
    .accept 103 << Orc
    .accept 104 << Troll
]])

RXPGuides.RegisterGuide("Rml4dHVyZSBlbmNyeXB0ZWQgcGF5bG9hZA==")
