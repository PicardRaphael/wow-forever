local L = GetLocale() if L and RXP.enabledLocale[L] then return end
RXPGuides.RegisterGuide([[
#forever
#version 1
#name 1-3 Paired Vale
#group Test Forever Guide (A) << Alliance
#subgroup Speedrun Guide 1-20 << Alliance
#next 10-12 Test Marsh

step
    >>Talk to |cRXP_FRIENDLY_Ondra Fenwick|r
    .accept 90003 >>Accept Marsh Errand
    .target Ondra Fenwick
step
    >>Travel to Test Marsh
    .turnin 90002 >>Turn in Tusks for Brin
]])
