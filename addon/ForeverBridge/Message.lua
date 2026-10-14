-- ForeverBridge : message porté par la bande (P06a, bloc B, décision 212 ; P06b, décision 235). Champs séparés par
-- l'octet 31 : version du protocole, jeton de session, numéro, drapeaux, prochain emplacement, contexte en lignes
-- « clé=valeur », texte ; lu par forever/bridge/record.py. Contexte du personnage lu sous pcall, une valeur secrète
-- laissant la clé absente.
-- Équipement complet (P06b) : « emplacement=chaîne d'objet=nom », la chaîne étant le corps du lien sans « item: » ni
-- les champs vides ou nuls de fin (enchantement, gemmes, suffixe aléatoire et identifiant unique gardés). Liens cités
-- (clé links) : par lien (octet 29), corps, nom et lignes de l'infobulle (octet 28).
-- Trop long pour une bande : noms d'objets coupés, puis retirés, puis sous-zone ; ensuite le message part en
-- plusieurs parties (Message.Fragments, lues par forever/bridge/fragments.py). Équipement, talents, liens et question
-- ne sont jamais retirés.

ForeverBridge_Message = {}
local M = ForeverBridge_Message
local Codec = ForeverBridge_Codec

M.PROTOCOL = "1"
M.FRAGMENT_TAG = "F"
M.FIELD_SEP = string.char(31)
M.RECORD_SEP = string.char(30)
M.LINK_SEP = string.char(29)
M.LINE_SEP = string.char(28)
M.MAX_MESSAGE = 32768 -- octets d'un message complet, toutes parties comprises
M.ITEM_NAME_CHARS = 20 -- longueur des noms d'objets au premier allègement
M.MAX_LINKS = 8
M.TOOLTIP_LINES = 30
M.TOOLTIP_CHARS = 120
M.LINK_KINDS = { item = true, spell = true, quest = true, talent = true }
M.KEYS = { "name", "realm", "level", "class", "race", "faction", "zone", "subzone", "map", "talents", "gear",
	"target", "target_level", "target_race", "client", "links", "rested", "resting", "xp_auras", "xp_items",
	"professions", "role", "eui_base" }
-- T04f (0.2.0) : auras du joueur relevées (au plus MAX_AURAS, parmi les AURA_SCAN premières), filtrées par la liste
-- que le pont écrit dans Status.lua (ForeverBridgeStatus.xp, identifiants lus dans les données, jamais écrits ici).
M.MAX_AURAS = 16
M.AURA_SCAN = 40
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

-- Séparateurs du protocole et des liens, sauts de ligne : remplacés par une espace.
local function clean(text)
	text = tostring(text)
	text = text:gsub("[%z\28-\31\r\n]", " ")
	return text
end

-- Champs vides ou nuls de fin d'un corps de lien retirés (« 12345::::::::19::::: » → « 12345::::::::19 »).
local function trimFields(rest)
	local previous
	repeat
		previous = rest
		rest = rest:gsub(":0*$", "")
	until rest == previous
	return rest
end
M.TrimFields = trimFields

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

-- Équipement : liste de { slot, chain, name } lue dans les liens d'objets (chaîne complète du lien).
local function Gear()
	local pieces = {}
	for slot = 1, GEAR_SLOTS do
		local link = safe(GetInventoryItemLink, "player", slot)
		if type(link) == "string" then
			local body = link:match("|Hitem:([^|]+)")
			if body and body:match("^%d+") then
				local name = clean(link:match("|h%[(.-)%]|h") or ""):gsub("[;=]", " ")
				pieces[#pieces + 1] = { slot = slot, chain = trimFields(body), name = name }
			end
		end
	end
	return pieces
end

function M.GearText(pieces, mode)
	local parts = {}
	for _, piece in ipairs(pieces) do
		if mode == "ids" then
			parts[#parts + 1] = piece.slot .. "=" .. piece.chain
		else
			local name = mode == "cut" and cutChars(piece.name, M.ITEM_NAME_CHARS) or piece.name
			parts[#parts + 1] = piece.slot .. "=" .. piece.chain .. "=" .. name
		end
	end
	return table.concat(parts, ";")
end

-- Texte d'une ligne d'infobulle sans séquences d'interface (couleurs, textures, liens), coupé.
local function plainLine(text)
	local s = tostring(text)
	s = s:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", ""):gsub("|T.-|t", ""):gsub("|A.-|a", ""):gsub("|n", " ")
	s = s:gsub("|H.-|h(.-)|h", "%1")
	s = s:gsub("%c", " "):gsub("^%s+", ""):gsub("%s+$", "")
	return cutChars(s, M.TOOLTIP_CHARS)
end

-- Lignes de l'infobulle d'un lien (C_TooltipInfo.GetHyperlink), sous pcall ; aucune ligne si l'API manque, lève une
-- erreur ou rend une valeur secrète.
local function Tooltip(link)
	if type(C_TooltipInfo) ~= "table" or type(C_TooltipInfo.GetHyperlink) ~= "function" then
		return {}
	end
	local ok, data = pcall(C_TooltipInfo.GetHyperlink, link)
	if not ok or isSecret(data) or type(data) ~= "table" or type(data.lines) ~= "table" then
		return {}
	end
	local out = {}
	for _, line in ipairs(data.lines) do
		if #out >= M.TOOLTIP_LINES then
			break
		end
		if type(line) == "table" then
			local left, right = line.leftText, line.rightText
			local text = (type(left) == "string" and not isSecret(left)) and left or ""
			if type(right) == "string" and not isSecret(right) and right ~= "" then
				text = text .. "  " .. right
			end
			text = plainLine(text)
			if text ~= "" then
				out[#out + 1] = text
			end
		end
	end
	return out
end

-- Formes d'un lien dans une zone de saisie : couleur « |cffRRGGBB » (Classic), couleur nommée « |cnIQ2: » (Forever,
-- sonde en jeu G), ou lien sans couleur.
local LINK_FORMS = {
	"^|c%x%x%x%x%x%x%x%x|H([^|]+)|h(.-)|h|r",
	"^|cn[^:|]*:|H([^|]+)|h(.-)|h|r",
	"^|H([^|]+)|h(.-)|h",
}

-- Liens d'une question : texte où chaque lien devient « [Nom] », valeur de la clé links (nil sans lien), et texte à
-- montrer dans l'historique (liens gardés tels quels, tout autre « | » neutralisé). Objets, sorts, quêtes et
-- talents ; au plus MAX_LINKS liens envoyés, les suivants seulement nommés.
function M.Links(text)
	text = tostring(text)
	local links, count = {}, 0
	local out, shown = {}, {}
	local i, n = 1, #text
	while i <= n do
		local bar = text:find("|", i, true)
		if not bar then
			out[#out + 1] = text:sub(i)
			shown[#shown + 1] = text:sub(i)
			break
		end
		out[#out + 1] = text:sub(i, bar - 1)
		shown[#shown + 1] = text:sub(i, bar - 1)
		local last, body, display
		for _, form in ipairs(LINK_FORMS) do
			local first
			first, last, body, display = text:find(form, bar)
			if first then
				break
			end
		end
		if body then
			local full = text:sub(bar, last)
			local name = display:match("^%[(.*)%]$") or display
			local kind = body:match("^(%a+):")
			if kind and M.LINK_KINDS[kind] then
				count = count + 1
				if count <= M.MAX_LINKS then
					local fields = { kind .. ":" .. trimFields(body:sub(#kind + 2)), clean(name) }
					for _, line in ipairs(Tooltip(full)) do
						fields[#fields + 1] = line
					end
					links[#links + 1] = table.concat(fields, M.LINE_SEP)
				end
				shown[#shown + 1] = full
			else
				shown[#shown + 1] = "[" .. name:gsub("|", "||") .. "]"
			end
			out[#out + 1] = "[" .. name .. "]"
			i = last + 1
		else
			out[#out + 1] = "|"
			shown[#shown + 1] = "||"
			i = bar + 1
		end
	end
	return table.concat(out), (#links > 0) and table.concat(links, M.LINK_SEP) or nil, table.concat(shown)
end

-- Contexte du personnage : table clé → texte, et l'équipement en morceaux pour l'allègement.
-- Liste de surveillance des bonus d'XP écrite par le pont (auras, objets, arbres Legacy) ; nil sans elle.
local function xpWatch()
	local status = ForeverBridgeStatus
	if type(status) ~= "table" or type(status.xp) ~= "table" then
		return nil
	end
	return status.xp
end

-- Auras utiles du joueur « sort:cumuls:secondes restantes » (vide : sans fin), séparées par des virgules ; filtrées
-- par la liste du pont quand il l'a écrite ; nil si l'API manque, échoue ou ne rend rien.
function M.XpAuras(watch)
	if type(C_UnitAuras) ~= "table" or type(C_UnitAuras.GetAuraDataByIndex) ~= "function" then
		return nil
	end
	local wanted = nil
	if watch and type(watch.auras) == "table" then
		wanted = {}
		for _, id in ipairs(watch.auras) do
			wanted[id] = true
		end
	end
	local now = safe(GetTime)
	local out = {}
	for index = 1, M.AURA_SCAN do
		local ok, aura = pcall(C_UnitAuras.GetAuraDataByIndex, "player", index, "HELPFUL")
		if not ok then
			return nil
		end
		if type(aura) ~= "table" or isSecret(aura) then
			break
		end
		local id = aura.spellId
		if type(id) == "number" and not isSecret(id) and (wanted == nil or wanted[id]) then
			local stacks = aura.applications
			if type(stacks) ~= "number" or isSecret(stacks) or stacks < 1 then
				stacks = 1
			end
			local remaining = ""
			local expires = aura.expirationTime
			if type(expires) == "number" and not isSecret(expires) and expires > 0 and type(now) == "number" then
				remaining = tostring(math.floor(expires - now + 0.5))
			end
			out[#out + 1] = id .. ":" .. stacks .. ":" .. remaining
			if #out >= M.MAX_AURAS then
				break
			end
		end
	end
	if #out == 0 then
		return nil
	end
	return table.concat(out, ",")
end

-- Objets de la liste du pont portés « objet:nombre » ; nil sans liste ou si l'API échoue.
function M.XpItems(watch)
	if not watch or type(watch.items) ~= "table" or type(C_Item) ~= "table" then
		return nil
	end
	local out = {}
	for _, id in ipairs(watch.items) do
		local count = safe(C_Item.GetItemCount, id, true) -- banque comprise : un sac rangé reste possédé
		if type(count) == "number" then
			out[#out + 1] = id .. ":" .. count
		end
	end
	if #out == 0 then
		return nil
	end
	return table.concat(out, ",")
end

-- RX1 (0.3.0) : métiers « nom:rang:rang maximal » séparés par des virgules (lignes de compétence que le joueur peut
-- désapprendre : métiers principaux et secondaires) ; nil si l'API manque, échoue ou ne rend rien.
function M.Professions()
	if type(GetNumSkillLines) ~= "function" or type(GetSkillLineInfo) ~= "function" then
		return nil
	end
	local ok, count = pcall(GetNumSkillLines)
	if not ok or type(count) ~= "number" or isSecret(count) then
		return nil
	end
	local out = {}
	for index = 1, count do
		local fine, name, header, _, rank, _, _, maxRank, abandonable = pcall(GetSkillLineInfo, index)
		if not fine then
			return nil
		end
		if type(name) == "string" and not isSecret(name) and not header and abandonable == true
			and type(rank) == "number" and type(maxRank) == "number" then
			out[#out + 1] = name:gsub("[,:]", " ") .. ":" .. rank .. ":" .. maxRank
		end
	end
	if #out == 0 then
		return nil
	end
	return table.concat(out, ",")
end

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
		local level = safe(UnitLevel, "target")
		if type(level) == "number" then
			put("target_level", level > 0 and level or "??") -- -1 : niveau caché (crâne)
		end
		put("target_race", second(UnitRace, "target"))
	end
	local version, build = safe(GetBuildInfo), second(GetBuildInfo)
	if version then
		put("client", build and (version .. "." .. build) or version)
	end
	-- T04f : repos, zone de repos, auras d'XP et objets surveillés (bouton Leveling).
	put("rested", safe(GetXPExhaustion))
	if type(IsResting) == "function" then
		local ok, resting = pcall(IsResting)
		if ok and not isSecret(resting) then
			put("resting", resting and "1" or "0")
		end
	end
	local watch = xpWatch()
	put("xp_auras", M.XpAuras(watch))
	put("xp_items", M.XpItems(watch))
	put("professions", M.Professions())
	put("role", M.Role())
	put("eui_base", M.Base())
	return ctx, pieces
end

-- EX1 : rôle choisi par le joueur (/fb role), gardé par personnage dans ForeverBridgeDB.roles.
function M.Role()
	local db = ForeverBridgeDB
	if type(db) ~= "table" or type(db.roles) ~= "table" then
		return nil
	end
	local okName, name = pcall(UnitName, "player")
	local okRealm, realm = pcall(GetRealmName)
	if not (okName and okRealm) or type(name) ~= "string" or type(realm) ~= "string" then
		return nil
	end
	local role = db.roles[name .. " - " .. realm]
	return type(role) == "string" and role or nil
end

-- EX1 (décision 269) : profil de base EllesmereUI choisi par le joueur (/fb base), gardé par personnage dans
-- ForeverBridgeDB.bases.
function M.Base()
	local db = ForeverBridgeDB
	if type(db) ~= "table" or type(db.bases) ~= "table" then
		return nil
	end
	local okName, name = pcall(UnitName, "player")
	local okRealm, realm = pcall(GetRealmName)
	if not (okName and okRealm) or type(name) ~= "string" or type(realm) ~= "string" then
		return nil
	end
	local base = db.bases[name .. " - " .. realm]
	return type(base) == "string" and base or nil
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

-- Charge de la bande ; `flags` est une liste de drapeaux (« n », « h », « b=clé », « a=action », « k=simc »).
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

-- Infobulles retirées des liens (corps et nom gardés) : dernier recours avant le refus d'un message trop long.
local function linksWithoutTooltips(value)
	local out = {}
	for link in (value .. M.LINK_SEP):gmatch("(.-)" .. M.LINK_SEP) do
		local body, name = link:match("^([^\28]*)\28?([^\28]*)")
		out[#out + 1] = (body or "") .. M.LINE_SEP .. (name or "")
	end
	return table.concat(out, M.LINK_SEP)
end

-- Message complet, allégé si besoin : charge et texte du contexte envoyé (boîte d'envoi), ou nil et la raison s'il
-- dépasse MAX_MESSAGE même allégé. `extra` complète le contexte (clé links). Au-delà d'une bande, la charge part en
-- parties (M.Fragments).
function M.Build(session, id, flags, slot, text, extra)
	local ctx, pieces = M.Context()
	for key, value in pairs(extra or {}) do
		ctx[key] = value
	end
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
	}
	local payload = M.Payload(session, id, flags, slot, ctx, text)
	for _, step in ipairs(steps) do
		if #payload <= Codec.MAX_PAYLOAD then
			break
		end
		step()
		payload = M.Payload(session, id, flags, slot, ctx, text)
	end
	if #payload > M.MAX_MESSAGE and ctx.links then
		ctx.links = linksWithoutTooltips(ctx.links)
		payload = M.Payload(session, id, flags, slot, ctx, text)
	end
	if #payload > M.MAX_MESSAGE then
		return nil, "message trop long (" .. #payload .. " octets, " .. M.MAX_MESSAGE .. " au plus)"
	end
	return payload, M.ContextText(ctx)
end

-- Parties d'une charge trop longue pour une bande : « F », session, numéro, rang, total, puis un morceau brut de la
-- charge ; la taille des morceaux suit l'en-tête le plus long. Une seule partie (la charge) si elle tient.
function M.Fragments(payload, session, id)
	local max = Codec.MAX_PAYLOAD
	if #payload <= max then
		return { payload }
	end
	local function header(i, n)
		return table.concat({ M.FRAGMENT_TAG, clean(session), tostring(id), tostring(i), tostring(n), "" }, M.FIELD_SEP)
	end
	local digits, chunk, total = 1, nil, nil
	while true do
		local widest = math.floor(10 ^ digits) - 1
		chunk = max - #header(widest, widest)
		total = math.ceil(#payload / chunk)
		if total <= widest then
			break
		end
		digits = digits + 1
	end
	local parts = {}
	for i = 1, total do
		parts[i] = header(i, total) .. payload:sub((i - 1) * chunk + 1, i * chunk)
	end
	return parts
end
