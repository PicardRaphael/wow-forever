if GetLocale() ~= "frFR" then return end
RXPGuides.RegisterGuide([[
#forever
#version 1
#name 1-3 Val Jumelé
#group Guide Test Forever (A) << Alliance
#subgroup Guide Speedrun 1-20 << Alliance
#next 10-12 Marais d’Essai

step
    >>Parlez à |cRXP_FRIENDLY_Ondra Lande-Fen|r
    .accept 90003 >>Acceptez la quête Course au marais
    .target Ondra Lande-Fen
step
    >>Allez jusqu'au Marais d’Essai
    .turnin 90002 >>Rendez la quête Des défenses pour Brin
]])
