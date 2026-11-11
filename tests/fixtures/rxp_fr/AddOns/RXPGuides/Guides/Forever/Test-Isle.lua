local L = GetLocale() if L and RXP.enabledLocale[L] then return end
--Test leveling guide (invented for forever tests)
RXPGuides.RegisterGuide([[
#forever
#version 1
#name 1-5 Testing Isle
#group RestedXP Forever Guide (A) << Alliance
#subgroup Speedrun Guide 1-20 << Alliance
#next 5-10 Testing Isle
#defaultfor Testrace

step
    .goto 9001,40.10,20.20
    >>|Tinterface/worldmap/chatbubble_64grey.blp:20|tTalk to |cRXP_FRIENDLY_Brin Oakvale::900001|r
    .accept 90001 >>Accept A Fresh Start
    .target Brin Oakvale::900001
step
    >>Kill |cRXP_ENEMY_Glade Boars|r. Loot them for their |cRXP_LOOT_Boar Tusks|r
    .complete 90001,1
    .mob Glade Boar
]])

RXPGuides.RegisterGuide([[
#forever
#version 1
#name 5-10 Testing Isle
#group RestedXP Forever Guide (A) << Alliance
#subgroup Speedrun Guide 1-20 << Alliance
#next 10-12 Test Marsh

step
    .goto 9001,41.50,22.70
    >>Talk to |cRXP_FRIENDLY_Brin Oakvale|r
    .turnin 90001 >>Turn in A Fresh Start
    .accept 90002 >>Accept Tusks for Brin
    .target Brin Oakvale
step << Mage
    .train 9133 >>Train |T135846:0|t[Frost Spark]
    *|cRXP_WARN_Wait for the boat at the dock|r
    +|cRXP_WARN_Keep 5 silver for the boat|r << Alliance
    .zone Test Marsh >>Travel to Test Marsh
]])

RXPGuides.RegisterGuide([[
#forever
#version 1
#name 10-12 Test Marsh
#group RestedXP Forever Guide (A) << Alliance
#subgroup Speedrun Guide 1-20 << Alliance

step
    #completewith next
    .goto 9002,10.00,10.00
    >>|cRXP_WARN_Be careful as |cRXP_ENEMY_Marsh Lurkers|r hit hard|r
    .mob Marsh Lurker,Bog Crawler::900010
step
    .goto 9002,12.00,14.00
    >>Talk to |cRXP_FRIENDLY_Ondra Fenwick|r
    .turnin 90002 >>Turn in Tusks for Brin
    .xp 12
]])
