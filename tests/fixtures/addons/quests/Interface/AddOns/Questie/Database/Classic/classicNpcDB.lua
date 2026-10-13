-- AUTO GENERATED FILE! DO NOT EDIT!

---@type QuestieDB
local QuestieDB = QuestieLoader:ImportModule("QuestieDB");

QuestieDB.npcKeys = {
    ['name'] = 1, -- string
    ['minLevelHealth'] = 2, -- int
    ['maxLevelHealth'] = 3, -- int
    ['minLevel'] = 4, -- int
    ['maxLevel'] = 5, -- int
    ['rank'] = 6, -- int, see https://github.com/cmangos/issues/wiki/creature_template#rank
    ['spawns'] = 7, -- table {[zoneID(int)] = {coordPair(floatVector2D),...},...}
    ['waypoints'] = 8, -- table {[zoneID(int)] = {coordPair(floatVector2D),...},...}
    ['zoneID'] = 9, -- guess as to where this NPC is most common
    ['questStarts'] = 10, -- table {questID(int),...}
    ['questEnds'] = 11, -- table {questID(int),...}
    ['factionID'] = 12, -- int, see https://github.com/cmangos/issues/wiki/FactionTemplate.dbc
    ['friendlyToFaction'] = 13, -- string, Contains "A" and/or "H" depending on NPC being friendly towards those factions. nil if hostile to both.
    ['subName'] = 14, -- string, The title or function of the NPC, e.g. "Weapon Vendor"
    ['npcFlags'] = 15, -- int, Bitmask containing various flags about the NPCs function (Vendor, Trainer, Flight Master, etc.).
                       -- For flag values see https://github.com/cmangos/mangos-classic/blob/172c005b0a69e342e908f4589b24a6f18246c95e/src/game/Entities/Unit.h#L536
}

QuestieDB.npcData = [[return {
[197] = {'Marshal McBride',484,484,20,20,0,{[12]={{48.92,41.61}}},nil,12,{7,15,21,54,3100,3101,3102,3103,3104,3105},{7,15,21,783},12,"A",nil,3},
[384] = {'Katie Hunter',198,198,10,10,0,{[12]={{84.15,65.49}}},nil,12,{7677,7678},{7677,7678},12,"A","Horse Breeder",135},
[823] = {'Deputy Willem',417,417,18,18,0,{[12]={{48.17,42.94}}},nil,12,{6,18,783,3903,5261},{6,18},12,"A",nil,2},
[2425] = {'Varimathras',518000,518000,62,62,3,{[1497]={{56.25,92.2}}},nil,1497,{1048,5725,6145,6521},{550,1048,1978,5725,6144,6521,6522},68,"H",nil,3},
[3139] = {'Gar\'Thok',198,198,10,10,0,{[14]={{51.95,43.5}}},nil,14,{784,825,831,837},{784,825,830,837},29,"H",nil,3},
[3143] = {'Gornek',102,102,5,5,0,{[14]={{42.06,68.33}}},nil,14,{788,789,2383,3065,3082,3083,3084,3085,3086,3087,3088,3089,3090},{787,788,789,804,4641},29,"H",nil,3},
[3216] = {'Neeru Fireblade',1536,1536,37,37,0,{[1637]={{49.47,50.59}}},nil,1637,{809,3122,5730,5761},{829,832,3121,5729,5761},29,"H",nil,3},
[3287] = {'Hana\'zua',55,55,2,2,0,{[14]={{40.6,62.58}}},nil,14,{790,804},{790},126,"H",nil,2},
[4949] = {'Thrall',799500,799500,63,63,3,{[1637]={{31.73,37.82}}},nil,1637,{4002,4003,4974,5726,5727,5728,5729,6566,6567,7491,7784},{4001,4002,4004,4941,4974,5726,5727,5728,5730,6566,7490,7783,8485},125,"H","Warchief",3},
[11318] = {'Ragefire Trogg',819,984,13,15,1,{[2437]={{-1,-1}}},nil,2437,nil,nil,59,nil,nil,0},
[11319] = {'Ragefire Shaman',759,903,13,15,1,{[2437]={{-1,-1}}},nil,2437,nil,nil,59,nil,nil,0},
[11518] = {'Jergosh the Invoker',1382,1382,16,16,1,{[2437]={{-1,-1}}},nil,2437,nil,nil,554,nil,nil,0},
[11519] = {'Bazzalan',1513,1513,16,16,1,{[2437]={{-1,-1}}},nil,2437,nil,nil,554,nil,nil,0},
[11833] = {'Rahauro',484,484,20,20,0,{[1638]={{70.14,29.52}}},{[1638]={{{70.14,29.52},{70.39,29.43},{70.7,29.45},{71.0,29.68},{71.19,30.29},{71.21,30.72},{71.18,31.15},{71.04,31.51},{70.5,31.81},{71.04,31.51},{71.18,31.15},{71.21,30.72},{71.19,30.29},{71.0,29.68},{70.7,29.45},{70.39,29.43}}}},1638,{5722,5723},{5723,5724},104,"H","Magatha's Servant",3},
[11834] = {'Maur Grimtotem',300,300,14,14,0,{[2437]={{-1,-1}}},nil,2437,{5724},{5722},35,"AH",nil,2},
}]]
