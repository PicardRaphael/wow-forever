if GetLocale() ~= "frFR" then return end
--Guide de test (inventé pour les tests de forever)
RXPGuides.RegisterGuide([[
#forever
#version 1
#name 1-5 Île d’Essai
#group Guide Test Forever (A) << Alliance
#subgroup Guide Speedrun 1-20 << Alliance
#next 5-10 Île d’Essai
#defaultfor Testrace

step
    .goto 9001,40.10,20.20
    >>|Tinterface/worldmap/chatbubble_64grey.blp:20|tParlez à |cRXP_FRIENDLY_Brin Chênevaux::900001|r
    .accept 90001 >>Acceptez la quête Un nouveau départ
    .target Brin Oakvale::900001
step
    >>Tuez les |cRXP_ENEMY_Glade Boars|r. Dépouillez-les pour leurs |cRXP_LOOT_Boar Tusks|r
    .complete 90001,1
    .mob Sanglier des clairières
]])
