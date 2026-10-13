ForeverLoggerDB = {
	["schema"] = 2,
	["characters"] = {
		["Player-0000-0000BEEF"] = {
			["name"] = "Traqueur",
			["realm"] = "Royaume",
			["class"] = "HUNTER",
			["race"] = "Orc",
			["snapshots"] = {
				{
					["reason"] = "connexion",
					["time"] = 1791547200,
					["localtime"] = "10/14/2026 20:00:00",
					["level"] = 15,
					["trivial_range"] = 5,
					["state"] = {
						["xp"] = 300,
						["max"] = 1000,
						["rested"] = 300,
						["rest_state"] = 1,
					},
					["resting"] = true,
				}, -- [1]
			},
			["xp"] = {
				{
					["time"] = 1791547260,
					["localtime"] = "10/14/2026 20:01:00",
					["level"] = 15,
					["text"] = "Dire Mottled Boar dies, you gain 23 experience.",
				}, -- [1]
				{
					["time"] = 1791547290,
					["localtime"] = "10/14/2026 20:01:30",
					["level"] = 15,
					["text"] = "Kolkar Drudge dies, you gain 40 experience. (+4 group bonus)",
				}, -- [2]
				{
					["time"] = 1791547320,
					["localtime"] = "10/14/2026 20:02:00",
					["level"] = 15,
					["text"] = "You gain 450 experience.",
				}, -- [3]
				{
					["time"] = 1791547350,
					["localtime"] = "10/14/2026 20:02:30",
					["level"] = 15,
					["text"] = "Sanglier marbré meurt, vous gagnez 23 points d'expérience.",
				}, -- [4]
				{
					["seq"] = 12,
					["time"] = 1791547380,
					["localtime"] = "10/14/2026 20:03:00",
					["level"] = 15,
					["text"] = "Ragefire Trogg dies, you gain 67 experience. (+33 exp Rested bonus)",
					["amount"] = 67,
					["kind"] = "monster",
					["monster"] = "Ragefire Trogg",
					["target"] = {
						["name"] = "Ragefire Trogg",
						["level"] = 13,
						["classification"] = "normal",
						["npc"] = 11318,
						["creature_type"] = "Humanoid",
						["source"] = "target",
					},
					["state"] = {
						["xp"] = 400,
						["max"] = 1000,
						["rested"] = 300,
						["rest_state"] = 1,
					},
					["resting"] = false,
					["instance"] = {
						["inside"] = true,
						["type"] = "party",
						["name"] = "Ragefire Chasm",
						["id"] = 389,
					},
					["group"] = {
						["size"] = 3,
						["raid"] = false,
						["levels"] = {
							14, -- [1]
							17, -- [2]
						},
					},
					["map"] = 213,
				}, -- [5]
				{
					["seq"] = 14,
					["time"] = 1791547440,
					["localtime"] = "10/14/2026 20:04:00",
					["level"] = 15,
					["text"] = "Durotar Tiger dies, you gain 30 experience.",
					["amount"] = 30,
					["kind"] = "monster",
					["monster"] = "Durotar Tiger",
					["seen_levels"] = {
						7, -- [1]
						8, -- [2]
					},
					["state"] = {
						["xp"] = 467,
						["max"] = 1000,
						["rest_state"] = 2,
					},
					["resting"] = false,
					["instance"] = {
						["inside"] = false,
						["type"] = "none",
					},
					["group"] = {
						["size"] = 0,
						["raid"] = false,
					},
					["map"] = 1411,
				}, -- [6]
			},
			["xp_states"] = {
				{
					["seq"] = 11,
					["reason"] = "connexion",
					["time"] = 1791547200,
					["localtime"] = "10/14/2026 20:00:00",
					["level"] = 15,
					["xp"] = 400,
					["max"] = 1000,
					["rested"] = 300,
					["rest_state"] = 1,
					["resting"] = false,
				}, -- [1]
				{
					["seq"] = 13,
					["reason"] = "xp",
					["time"] = 1791547380,
					["localtime"] = "10/14/2026 20:03:00",
					["level"] = 15,
					["xp"] = 467,
					["max"] = 1000,
					["rested"] = 267,
					["rest_state"] = 1,
					["resting"] = false,
				}, -- [2]
			},
			["quests"] = {
				{
					["event"] = "accepted",
					["seq"] = 20,
					["quest_id"] = 5761,
					["title"] = "Slaying the Beast",
					["quest_level"] = 16,
					["time"] = 1791547500,
					["localtime"] = "10/14/2026 20:05:00",
					["level"] = 15,
					["map"] = 1454,
				}, -- [1]
				{
					["event"] = "turned_in",
					["seq"] = 21,
					["quest_id"] = 5761,
					["title"] = "Slaying the Beast",
					["quest_level"] = 16,
					["xp_reward"] = 1450,
					["money_reward"] = 2500,
					["time"] = 1791548100,
					["localtime"] = "10/14/2026 20:15:00",
					["level"] = 15,
					["state"] = {
						["xp"] = 900,
						["max"] = 1000,
						["rested"] = 120,
						["rest_state"] = 1,
					},
					["resting"] = true,
					["map"] = 1454,
				}, -- [2]
			},
		},
	},
}
