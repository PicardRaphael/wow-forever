-- ForeverBridge : message porté par la bande (P06a, bloc B, décision 212). Champs séparés par l'octet 31 : version du
-- protocole, jeton de session, numéro, drapeaux, prochain emplacement, contexte en lignes « clé=valeur », texte ; lu
-- par forever/bridge/record.py. Contexte du personnage lu sous pcall, une valeur secrète laissant la clé absente.
-- Trop long pour la bande : noms d'objets coupés, puis retirés, puis sous-zone, puis équipement, puis talents ; la
-- question n'est jamais coupée.

ForeverBridge_Message = {}
local M = ForeverBridge_Message
local Codec = ForeverBridge_Codec

M.PROTOCOL = "1"
M.FIELD_SEP = string.char(31)
M.RECORD_SEP = string.char(30)
M.ITEM_NAME_CHARS = 20 -- longueur des noms d'objets au premier allègement
M.KEYS = { "name", "realm", "level", "class", "race", "faction", "zone", "subzone", "map", "talents", "gear",
	"target", "client" }
local GEAR_SLOTS = 19

local function isSecret(value)
	local ok, secret = pcall(issecretvalue, value)
	return ok and secret == true
end

-- Appel protégé : nil si l'API manque, lève une erreur ou rend une valeur secrète.
local function safe(fn, ...)
	if type(fn) ~= "function" then
		return nil
	end
	local ok, value = pcall(fn, ...)
	if not ok or isSecret(value) then
		return nil
	end
	return value
end

local function second(fn, ...)
	if type(fn) ~= "function" then
		return nil
	end
	local ok, first, value = pcall(fn, ...)
	if not ok or isSecret(first) or isSecret(value) then
		return nil
	end
	return value
end

local function clean(text)
	text = tostring(text)
	text = text:gsub(M.FIELD_SEP, " "):gsub(M.RECORD_SEP, " "):gsub("[\r\n]", " ")
	return text
end

-- Rangs achetés, « nœud:rang » triés par nœud ; nil si l'API manque.
local function Talents()
	local configID = safe(C_ClassTalents and C_ClassTalents.GetActiveConfigID)
	if not configID or type(C_Traits) ~= "table" then
		return nil
	end
	local config = safe(C_Traits.GetConfigInfo, configID)
	if type(config) ~= "table" or type(config.treeIDs) ~= "table" then
		return nil
	end
	local ranks, order = {}, {}
	for _, treeID in ipairs(config.treeIDs) do
		local nodes = safe(C_Traits.GetTreeNodes, treeID)
		if type(nodes) == "table" then
			for _, nodeID in ipairs(nodes) do
				local node = safe(C_Traits.GetNodeInfo, configID, nodeID)
				if type(node) == "table" and type(node.ranksPurchased) == "number" and node.ranksPurchased > 0 then
					if not ranks[nodeID] then
						order[#order + 1] = nodeID
					end
					ranks[nodeID] = node.ranksPurchased
				end
			end
		end
	end
	table.sort(order)
	local parts = {}
	for _, nodeID in ipairs(order) do
		parts[#parts + 1] = nodeID .. ":" .. ranks[nodeID]
	end
	return table.concat(parts, ",")
end

-- Équipement : liste de { slot, id, name } lue dans les liens d'objets.
local function Gear()
	local pieces = {}
	for slot = 1, GEAR_SLOTS do
		local link = safe(GetInventoryItemLink, "player", slot)
		if type(link) == "string" then
			local id = link:match("|Hitem:(%d+)")
			if id then
				local name = (link:match("|h%[(.-)%]|h") or ""):gsub("[;:]", " ")
				pieces[#pieces + 1] = { slot = slot, id = id, name = name }
			end
		end
	end
	return pieces
end

-- Coupe un texte UTF-8 à `count` caractères.
local function cutChars(text, count)
	local out, n = {}, 0
	for char in text:gmatch("[%z\1-\127\194-\244][\128-\191]*") do
		n = n + 1
		if n > count then
			break
		end
		out[n] = char
	end
	return table.concat(out)
end

function M.GearText(pieces, mode)
	local parts = {}
	for _, piece in ipairs(pieces) do
		if mode == "ids" then
			parts[#parts + 1] = piece.slot .. ":" .. piece.id
		else
			local name = mode == "cut" and cutChars(piece.name, M.ITEM_NAME_CHARS) or piece.name
			parts[#parts + 1] = piece.slot .. ":" .. piece.id .. ":" .. name
		end
	end
	return table.concat(parts, ";")
end

-- Contexte du personnage : table clé → texte, et l'équipement en morceaux pour l'allègement.
function M.Context()
	local ctx = {}
	local function put(key, value)
		if value ~= nil and value ~= "" then
			ctx[key] = clean(value)
		end
	end
	put("name", safe(UnitName, "player"))
	put("realm", safe(GetRealmName))
	put("level", safe(UnitLevel, "player"))
	put("class", safe(UnitClassBase, "player"))
	put("race", second(UnitRace, "player"))
	put("faction", safe(UnitFactionGroup, "player"))
	put("zone", safe(GetRealZoneText))
	put("subzone", safe(GetSubZoneText))
	put("map", safe(C_Map and C_Map.GetBestMapForUnit, "player"))
	put("talents", Talents())
	local pieces = Gear()
	if #pieces > 0 then
		ctx.gear = M.GearText(pieces, "full")
	end
	if safe(UnitExists, "target") and safe(UnitIsPlayer, "target") then
		put("target", safe(UnitClassBase, "target"))
	end
	local version, build = safe(GetBuildInfo), second(GetBuildInfo)
	if version then
		put("client", build and (version .. "." .. build) or version)
	end
	return ctx, pieces
end

function M.ContextText(ctx)
	local lines = {}
	for _, key in ipairs(M.KEYS) do
		if ctx[key] then
			lines[#lines + 1] = key .. "=" .. ctx[key]
		end
	end
	return table.concat(lines, "\n")
end

-- Charge de la bande ; `flags` est une liste de drapeaux (« n », « h », « b=clé »).
function M.Payload(session, id, flags, slot, ctx, text)
	local sorted = {}
	for _, flag in ipairs(flags or {}) do
		sorted[#sorted + 1] = clean(flag):gsub(",", " ")
	end
	table.sort(sorted)
	return table.concat({
		M.PROTOCOL,
		clean(session),
		tostring(id),
		table.concat(sorted, ","),
		slot and tostring(slot) or "",
		M.ContextText(ctx),
		(tostring(text):gsub(M.FIELD_SEP, " "):gsub(M.RECORD_SEP, " ")),
	}, M.FIELD_SEP)
end

-- Message complet, allégé si besoin : charge, ou nil et la raison si même la question seule ne tient pas.
function M.Build(session, id, flags, slot, text)
	local ctx, pieces = M.Context()
	local steps = {
		function()
			if ctx.gear then
				ctx.gear = M.GearText(pieces, "cut")
			end
		end,
		function()
			if ctx.gear then
				ctx.gear = M.GearText(pieces, "ids")
			end
		end,
		function()
			ctx.subzone = nil
		end,
		function()
			ctx.gear = nil
		end,
		function()
			ctx.talents = nil
		end,
	}
	local payload = M.Payload(session, id, flags, slot, ctx, text)
	for _, step in ipairs(steps) do
		if #payload <= Codec.MAX_PAYLOAD then
			return payload
		end
		step()
		payload = M.Payload(session, id, flags, slot, ctx, text)
	end
	if #payload <= Codec.MAX_PAYLOAD then
		return payload
	end
	return nil, "message trop long pour la bande, même sans contexte"
end
