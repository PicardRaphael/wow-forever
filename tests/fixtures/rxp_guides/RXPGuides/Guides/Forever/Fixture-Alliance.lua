local faction = UnitFactionGroup("player")
if faction == "Horde" then return end

RXPGuides.RegisterGuide([[
#forever
<< Alliance
#name 1-4 Fixture Meadow
#group Fixture Guide (A)
#defaultfor Human
#next 4-6 Fixture Coast;4-7 Fixture Coast

step
    .accept 102
]])

RXPGuides.RegisterGuide([[
#forever
<< Alliance
#name 4-7 Fixture Coast
#group Fixture Guide (A)

step
    .accept 110
]])
