local Addon = FojjiCoreNS
if not (Addon and Addon.DJ) then return end
local FDJ = Addon.DJ

FDJ.Dungeons = {
  { key = "ragefire", name = "Ragefire Chasm", zone = "Orgrimmar",
    instance = 389, range = { 13, 18 },
    bosses = {
      { n = "Taragaman the Hungerer", npc = 11520, lv = 17, loot = {14149,14148}, odds = {30.5,22.25} },
    },
    quests = {5723,5728},
  },
  { key = "excavation", name = "Excavation Site: Wetlands", zone = "Wetlands",
    instance = 2998, range = { 26, 31 },
    bosses = {
      { n = "Saltspine", npc = 900002, lv = 27, loot = {280002} },
    },
    quests = {96500},
  },
}

FDJ.Access = {
  excavation = {
    { item = 280100, name = "Dig Permit", need = "required", have = {96498} },
  },
}
