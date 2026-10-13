-- AUTO GENERATED FILE! DO NOT EDIT!

---@type QuestieDB
local QuestieDB = QuestieLoader:ImportModule("QuestieDB");

QuestieDB.questKeys = {
    ['name'] = 1, -- string
    ['startedBy'] = 2, -- table
        --['creatureStart'] = 1, -- table {creature(int),...}
        --['objectStart'] = 2, -- table {object(int),...}
        --['itemStart'] = 3, -- table {item(int),...}
    ['finishedBy'] = 3, -- table
        --['creatureEnd'] = 1, -- table {creature(int),...}
        --['objectEnd'] = 2, -- table {object(int),...}
    ['requiredLevel'] = 4, -- int
    ['questLevel'] = 5, -- int
    ['requiredRaces'] = 6, -- bitmask
    ['requiredClasses'] = 7, -- bitmask
    ['objectivesText'] = 8, -- table: {string,...}, Description of the quest. Auto-complete if nil.
    ['triggerEnd'] = 9, -- table: {text, {[zoneID] = {coordPair,...},...}}
    ['objectives'] = 10, -- table
        --['creatureObjective'] = 1, -- table {{creature(int), text(string), iconFile},...}, If text is nil the default "<Name> slain x/y" is used
        --['objectObjective'] = 2, -- table {{object(int), text(string), iconFile},...}
        --['itemObjective'] = 3, -- table {{item(int), text(string), iconFile},...}
        --['reputationObjective'] = 4, -- table: {faction(int), value(int)}
        --['killCreditObjective'] = 5, -- table: {{{creature(int), ...}, baseCreatureID, baseCreatureText, iconFile}, ...}
        --['spellObjective'] = 6, -- table: {{spell(int), text(string), item(int)},...}
    ['sourceItemId'] = 11, -- int, item provided by quest starter
    ['preQuestGroup'] = 12, -- table: {quest(int)}
    ['preQuestSingle'] = 13, -- table: {quest(int)}
    ['childQuests'] = 14, -- table: {quest(int)}
    ['inGroupWith'] = 15, -- table: {quest(int)}
    ['exclusiveTo'] = 16, -- table: {quest(int)}
    ['zoneOrSort'] = 17, -- int, >0: AreaTable.dbc ID; <0: QuestSort.dbc ID
    ['requiredSkill'] = 18, -- table: {skill(int), value(int)}
    ['requiredMinRep'] = 19, -- table: {faction(int), value(int)}
    ['requiredMaxRep'] = 20, -- table: {faction(int), value(int)}
    ['requiredSourceItems'] = 21, -- table: {item(int), ...} Items that are not an objective but still needed for the quest.
    ['nextQuestInChain'] = 22, -- int: if this quest is active/finished, the current quest is not available anymore
    ['questFlags'] = 23, -- bitmask: see https://github.com/cmangos/issues/wiki/Quest_template#questflags
    ['specialFlags'] = 24, -- bitmask: 1 = Repeatable, 2 = Needs event, 4 = Monthly reset (req. 1). See https://github.com/cmangos/issues/wiki/Quest_template#specialflags
    ['parentQuest'] = 25, -- int, the ID of the parent quest that needs to be active for the current one to be available. See also 'childQuests' (field 14)
    ['reputationReward'] = 26, -- table: {{faction(int), value(int)},...}, a list of reputation rewarded upon quest completion
    ['breadcrumbForQuestId'] = 27, -- int: quest ID for the quest this optional breadcrumb quest leads to
    ['breadcrumbs'] = 28, -- table: {questID(int), ...} quest IDs of the breadcrumbs that lead to this quest
    ['extraObjectives'] = 29, -- table: {{spawnlist, iconFile, text, objectiveIndex (optional), {{dbReferenceType, id}, ...} (optional)},...}, a list of hidden special objectives for a quest. Similar to requiredSourceItems
    ['requiredSpell'] = 30, -- int: quest is only available if character has this spellID
    ['requiredSpecialization'] = 31, -- int: quest is only available if character meets the spec requirements. Use QuestieProfessions.specializationKeys for having a spec, or QuestieProfessions.professionKeys to indicate having the profession with no spec. See QuestieProfessions.lua for more info.
    ['requiredMaxLevel'] = 32, -- int: the maximum level at which the quest is still available
    ['availableUntilCompleted'] = 33, -- int: the current quest is available until this quest is turned in
    ['availableStartingWith'] = 34, -- int: the ID of the quest that needs to be in quest log OR turned in for the current one to be available.
    ['requiredRanks'] = 35, -- table: {{skill(int), value(int)}}. Table of professions and ranks to be checked with OR logic
    ['disabledByQuest'] = 36, -- int: quest that, if in player's quest log, makes current quest unavailable for the duration
}

QuestieDB.questData = [[return {
[7] = {"Kobold Camp Cleanup",{{197}},{{197}},1,2,77,nil,{"Kill 10 Kobold Vermin, then return to Marshal McBride."},nil,{{{6}}},nil,nil,{783},nil,nil,nil,9,nil,nil,nil,nil,nil,8,nil,nil,{{72,250}}},
[15] = {"Investigate Echo Ridge",{{197}},{{197}},1,3,77,nil,{"Kill 10 Kobold Workers, then report back to Marshal McBride."},nil,{{{257}}},nil,nil,{7},nil,nil,nil,9,nil,nil,nil,nil,21,8,nil,nil,{{72,250}}},
[783] = {"A Threat Within",{{823}},{{197}},1,1,77,nil,{"Speak with Marshal McBride."},nil,nil,nil,nil,nil,nil,nil,nil,9,nil,nil,nil,nil,7,8,nil,nil,{{72,75}}},
[790] = {"Sarkoth",{{3287}},{{3287}},1,5,178,nil,{"Kill Sarkoth and bring his claw back to Hana'zua."},nil,{nil,nil,{{4905}}},nil,nil,nil,nil,nil,nil,363,nil,nil,nil,nil,804,8,nil,nil,{{76,250},{530,250}}},
[804] = {"Sarkoth",{{3287}},{{3143}},1,5,178,nil,{"Bring the news of Hana'zua's plight to Gornek at the Den."},nil,nil,nil,nil,{790},nil,nil,nil,363,nil,nil,nil,nil,nil,nil,nil,nil,{{76,25},{530,25}}},
[825] = {"From The Wreckage....",{{3139}},{{3139}},3,8,178,nil,{"Gar'Thok of Razor Hill wants you to retrieve 3 Gnomish Tools from the wreckage off the coast."},nil,{nil,nil,{{4863}}},nil,nil,{784},nil,nil,nil,14,nil,nil,nil,nil,nil,8,nil,nil,{{76,250},{530,250}}},
[5722] = {"Searching for the Lost Satchel",{{11833}},{{11834}},9,16,178,nil,{"Search Ragefire Chasm for Maur Grimtotem's corpse and search it for any items of interest."},nil,nil,nil,nil,nil,nil,nil,nil,2437,nil,nil,nil,nil,5724,8},
[5723] = {"Testing an Enemy's Strength",{{11833}},{{11833}},9,15,178,nil,{"Search Orgrimmar for Ragefire Chasm, then kill 8 Ragefire Troggs and 8 Ragefire Shaman before returning to Rahauro in Thunder Bluff."},nil,{{{11318},{11319}}},nil,nil,nil,nil,nil,nil,2437,nil,nil,nil,nil,nil,8,nil,nil,{{81,500}}},
[5724] = {"Returning the Lost Satchel",{{11834}},{{11833}},9,16,178,nil,{"Take the Grimtotem Satchel to Rahauro in Thunder Bluff."},nil,nil,14381,nil,{5722},nil,nil,nil,2437,nil,nil,nil,nil,nil,nil,nil,nil,{{81,500}}},
[5725] = {"The Power to Destroy...",{{2425}},{{2425}},9,16,178,nil,{"Bring the books Spells of Shadow and Incantations from the Nether to Varimathras in Undercity."},nil,{nil,nil,{{14395},{14396}}},nil,nil,nil,nil,nil,nil,2437,nil,nil,nil,nil,nil,8,nil,nil,{{68,350}}},
[5728] = {"Hidden Enemies",{{4949}},{{4949}},9,16,178,nil,{"Kill Bazzalan and Jergosh the Invoker before returning to Thrall in Orgrimmar."},nil,{{{11519},{11518}}},nil,nil,{5727},nil,nil,nil,2437,nil,nil,nil,nil,5729,8,nil,nil,{{76,250}}},
[5761] = {"Slaying the Beast",{{3216}},{{3216}},9,16,178,nil,{"Enter Ragefire Chasm and slay Taragaman the Hungerer, then bring his heart back to Neeru Fireblade in Orgrimmar."},nil,{nil,nil,{{14540}}},nil,nil,nil,nil,nil,nil,2437,nil,nil,nil,nil,nil,8},
[7677] = {"White Stallion Exchange",{{384}},{{384}},60,1,77,nil,{"If you bring me your white stallion, I'll trade you for one from the new herd. The new horse will be just as fast as your old one, but have a different look to it. You can look at the swift steeds here to see what it will look like.","","MUST PAY 500 Gold too...."},nil,{nil,nil,{{12353}}},nil,nil,nil,nil,nil,nil,12,nil,nil,nil,nil,nil,nil,1},
}]]
