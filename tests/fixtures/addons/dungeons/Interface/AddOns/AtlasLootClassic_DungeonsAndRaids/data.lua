local data = AtlasLoot.ItemDB:Add(addonname, 1, AtlasLoot.CLASSIC_VERSION_NUM)

data["Ragefire"] = {
	name = C_Map.GetAreaInfo(2437) .. LTNX,
	MapID = 2437,
	InstanceID = 389,
	ContentType = DUNGEON_CONTENT,
	LoadDifficulty = NORMAL_DIFF,
	LevelRange = GetForVersion({ 10, 13, 18 }, { 8, 13, 16 }),
	items = {
		{ -- Taragaman
			name = AL["Taragaman the Hungerer"],
			npcID = 11520,
			Level = 16,
			[NORMAL_DIFF] = {
				{ 1, 14149 },
				{ 2, 14148 },
			},
		},
	},
}

data["TheRuinsOfLordaeron"] = {
	name = AL["Ruins of Lordaeron"] .. LTNX,
	ContentType = DUNGEON_CONTENT,
	LevelRange = { 10, 13, 18 },
	items = {
		{
			name = AL["Witherfang"],
			[NORMAL_DIFF] = {
				{ 1, 280500 },
			},
		},
	},
}
