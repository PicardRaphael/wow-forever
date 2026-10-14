-- Sauvegarde EllesmereUI synthétique (EX1, bloc F) : forme de WTF/Account/<compte>/SavedVariables/EllesmereUI.lua
-- relevée dans EllesmereUI 9.5.4 ; valeurs inventées, sauf les identifiants de sorts du Mage repris de classes.json
-- (1.60.1.70374 : Fire Blast rang 1 2136, Frost Nova rang 1 122) et de Paladin (Judgement rang 1 20271).
EllesmereUIDB = {
	["activeProfile"] = "Base",
	["profileOrder"] = { "Base", "Autre" },
	["ppUIScale"] = 0.71,
	["specProfiles"] = {},
	["lastSpecByChar"] = {
		["Jen - Forever"] = 9001,
		["Bob - Forever"] = 9002,
	},
	["profiles"] = {
		["Base"] = {
			["fonts"] = { ["global"] = "Expressway", ["size"] = 12 },
			["customColors"] = { ["accent"] = { ["r"] = 0.2, ["g"] = 0.6, ["b"] = 1 } },
			["unlockLayout"] = { ["anchors"] = { ["player"] = { ["x"] = -240, ["y"] = -180, ["point"] = "CENTER" } } },
			["addons"] = {
				["EllesmereUIUnitFrames"] = { ["width"] = 220, ["showName"] = true, ["text"] = "a:b}c{d" },
				["EllesmereUIAuraBuffReminders"] = {
					["display"] = { ["scale"] = 1 },
					["forever"] = { ["camp"] = false, ["customIDs"] = { 9999 }, ["whereToShow"] = {} },
				},
			},
		},
		["Autre"] = {
			["fonts"] = { ["global"] = "Friz" },
			["addons"] = {},
		},
	},
	["spellAssignments"] = {
		["profiles"] = {
			["Base"] = {
				["specProfiles"] = {
					["9001"] = {
						["_migrations"] = { ["v6"] = true },
						["_barFilterModelV6"] = true,
						["barSpells"] = {
							["cooldowns"] = { ["assignedSpells"] = { 2136, 122 } },
							["utility"] = { ["assignedSpells"] = {} },
							["buffs"] = { ["assignedSpells"] = { 7777 } },
							["__ghost_cd"] = { ["assignedSpells"] = { 2136 } },
						},
					},
					["9002"] = {
						["barSpells"] = {
							["cooldowns"] = { ["assignedSpells"] = { 20271 } },
						},
					},
				},
			},
		},
	},
}
