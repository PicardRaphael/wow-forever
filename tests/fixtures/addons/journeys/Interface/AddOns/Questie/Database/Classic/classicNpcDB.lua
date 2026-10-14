-- fixture (valeurs inventées), structure de classicNpcDB.lua
local QuestieDB = QuestieLoader:ImportModule("QuestieDB");

QuestieDB.npcKeys = {
    ['name'] = 1,
    ['minLevelHealth'] = 2,
    ['maxLevelHealth'] = 3,
    ['minLevel'] = 4,
    ['maxLevel'] = 5,
    ['rank'] = 6,
    ['spawns'] = 7,
    ['waypoints'] = 8,
    ['zoneID'] = 9,
    ['questStarts'] = 10,
    ['questEnds'] = 11,
    ['factionID'] = 12,
    ['friendlyToFaction'] = 13,
    ['subName'] = 14,
    ['npcFlags'] = 15,
}

QuestieDB.npcData = [[return {
[990001] = {'Fixture Arcanist',100,100,30,30,0,{[701]={{40,40},{41,41}}},nil,701,nil,nil,1,"H","Mage Trainer",48},
[990002] = {'Fixture Sage',100,100,30,30,0,{[702]={{60,60}}},nil,702,nil,nil,1,"A","Mage Trainer",48},
[990003] = {'Fixture Blade',100,100,30,30,0,{[701]={{50,50}}},nil,701,nil,nil,1,"AH","Warrior Trainer",48},
[990004] = {'Fixture Merchant',100,100,30,30,0,{[701]={{45,45}}},nil,701,nil,nil,1,"AH","General Goods",4},
}]]
