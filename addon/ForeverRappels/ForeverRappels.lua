-- ForeverRappels (forever-core, RA1) : rappels d'aura en jeu.
-- Une icône déplaçable apparaît quand une règle tombe : en combat, aura attendue absente ou aura interdite
-- présente ; hors combat, familier absent ou mort (ou aspect de voyage, éteint par défaut). Elle prévient
-- seulement : aucune fonction d'action, aucun bouton sécurisé, rien de cliquable (décision 307). Réglages dans
-- EllesmereUI par son API publique de plugin (EllesmereUI.RegisterPlugin), sinon par /rappels.
-- Aucun identifiant de sort ici : les groupes de sorts viennent de RappelsData.lua, généré depuis les données du
-- client à l'installation.
-- Lecture des auras à trois états : présente, absente, inconnue (panne, valeur secrète, ou nil en combat tant que
-- la lecture « exacte » n'est pas choisie : le client de Forever peut masquer les auras en combat). Une aura
-- inconnue garde son dernier état connu, mis à jour par les sorts du joueur vus lancés.

local ADDON = (...) or "ForeverRappels"

local PET_ICON = "Interface\\Icons\\Ability_Hunter_BeastCall"
local TEST_ICON = "Interface\\Icons\\INV_Misc_QuestionMark"
local DEFAULT_SIZE = 48
local DEFAULT_Y = 140

-- Règles par classe (jeton de UnitClassBase). expected : il en faut une présente ; forbidden : aucune présente.
local RULES = {
	HUNTER = {
		{
			key = "combat_faucon",
			when = "combat",
			expected = { "aspect_faucon" },
			forbidden = { "aspect_guepard", "aspect_meute" },
			on = true,
		},
		{ key = "hors_combat_familier", when = "out", pet = true, on = true, label = "Hors combat : familier absent ou mort" },
		{ key = "hors_combat_guepard", when = "out", expected = { "aspect_guepard", "aspect_meute" }, on = false },
	},
}

-- Familles exclusives : une seule aura de la famille à la fois (une lue présente efface les autres inconnues).
local FAMILY = { aspect_faucon = "aspect", aspect_guepard = "aspect", aspect_meute = "aspect", aspect_bete = "aspect" }

local M = { known = {}, combat = false, testing = false, wasShown = false, plugin = false, errorSaid = false }

local function say(text)
	print("|cff33d94dForeverRappels|r : " .. text)
end

local function isSecret(v)
	return issecretvalue ~= nil and issecretvalue(v) and true or false
end

local function groups()
	return (ForeverRappelsData and ForeverRappelsData.groups) or {}
end

local function hasData()
	return next(groups()) ~= nil
end

local function inCombat()
	if M.combat then return true end
	local ok, locked = pcall(InCombatLockdown)
	return ok and locked == true
end

local function playerClass()
	local ok, token = pcall(UnitClassBase, "player")
	if ok and type(token) == "string" and not isSecret(token) then return token end
	return nil
end

local function groupName(key)
	local g = groups()[key]
	return (g and g.name) or key
end

local function ruleLabel(rule)
	if rule.label then return rule.label end
	local prefix = rule.when == "combat" and "En combat : " or "Hors combat : "
	return prefix .. groupName(rule.expected[1])
end

local function ruleOn(rule)
	local saved = ForeverRappelsDB and ForeverRappelsDB.regles and ForeverRappelsDB.regles[rule.key]
	if saved == nil then return rule.on end
	return saved == true
end

-- État d'un groupe : "present", "absent" ou "unknown".
local function readGroup(key)
	local g = groups()[key]
	if not g then return "unknown" end
	local unknown = false
	for _, id in ipairs(g.spells or {}) do
		local ok, aura = pcall(C_UnitAuras.GetPlayerAuraBySpellID, id)
		if not ok or isSecret(aura) then
			unknown = true
		elseif aura ~= nil then
			return "present"
		end
	end
	if unknown then return "unknown" end
	if inCombat() and ForeverRappelsDB.lecture_combat ~= "exacte" then return "unknown" end
	return "absent"
end

local function refreshStates()
	local read = {}
	for key in pairs(groups()) do
		read[key] = readGroup(key)
		if read[key] ~= "unknown" then M.known[key] = read[key] end
	end
	for key, state in pairs(read) do
		local family = FAMILY[key]
		if state == "present" and family then
			for other, f in pairs(FAMILY) do
				if f == family and other ~= key and read[other] == "unknown" then M.known[other] = "absent" end
			end
		end
	end
end

local function spellGroup(id)
	if id == nil or isSecret(id) then return nil end
	for key, g in pairs(groups()) do
		for _, s in ipairs(g.spells or {}) do
			if s == id then return key end
		end
	end
	return nil
end

local function onCast(id)
	local key = spellGroup(id)
	if not key then return end
	local family = FAMILY[key]
	if family then
		for other, f in pairs(FAMILY) do
			if f == family and other ~= key and groups()[other] then M.known[other] = "absent" end
		end
	end
	M.known[key] = "present"
end

local function petMissing()
	local ok, exists = pcall(UnitExists, "pet")
	if not ok or isSecret(exists) then return false end
	if not exists then return true end
	local okDead, dead = pcall(UnitIsDead, "pet")
	return okDead and not isSecret(dead) and dead == true
end

local function anyKnown(list, state)
	for _, key in ipairs(list or {}) do
		if M.known[key] == state then return true end
	end
	return false
end

local function allKnown(list, state)
	if not list or #list == 0 then return false end
	for _, key in ipairs(list) do
		if M.known[key] ~= state then return false end
	end
	return true
end

local function ruleFires(rule)
	if rule.pet then return petMissing() end
	if anyKnown(rule.forbidden, "present") then return true end
	return allKnown(rule.expected, "absent")
end

local function iconFor(rule)
	if rule.pet then return PET_ICON end
	local g = rule.expected and groups()[rule.expected[1]]
	local id = g and g.spells and g.spells[1]
	if id then
		local ok, texture = pcall(C_Spell.GetSpellTexture, id)
		if ok and texture and not isSecret(texture) then return texture end
	end
	return TEST_ICON
end

local function firedRule()
	local rules = RULES[playerClass() or ""]
	if not rules or not hasData() then return nil end
	local combat = inCombat()
	for _, rule in ipairs(rules) do
		if ruleOn(rule) and (rule.when == "combat") == combat and ruleFires(rule) then return rule end
	end
	return nil
end

local function evaluate()
	local frame, db = M.frame, ForeverRappelsDB
	if not frame or not db then return end
	local rule = firedRule()
	if rule then
		M.texture:SetTexture(iconFor(rule))
		frame:Show()
		if not M.wasShown and db.son and rule.when == "combat" then
			pcall(PlaySound, SOUNDKIT and SOUNDKIT.RAID_WARNING, "Master")
		end
		M.wasShown = true
		return
	end
	M.wasShown = false
	if M.testing or not db.locked then
		M.texture:SetTexture(TEST_ICON)
		frame:Show()
	else
		frame:Hide()
	end
end

local function applyPosition()
	local pos = ForeverRappelsDB.pos
	M.frame:ClearAllPoints()
	if pos and pos.point then
		M.frame:SetPoint(pos.point, UIParent, pos.relPoint or pos.point, pos.x or 0, pos.y or 0)
	else
		M.frame:SetPoint("CENTER", UIParent, "CENTER", 0, DEFAULT_Y)
	end
end

local function applySize()
	local size = ForeverRappelsDB.taille or DEFAULT_SIZE
	M.frame:SetSize(size, size)
end

local function applyLock()
	M.frame:EnableMouse(not ForeverRappelsDB.locked)
	evaluate()
end

local function setLocked(locked)
	ForeverRappelsDB.locked = locked and true or false
	applyLock()
end

local function createFrame()
	local frame = CreateFrame("Frame", "ForeverRappelsIcon", UIParent)
	frame:SetFrameStrata("HIGH")
	frame:SetMovable(true)
	frame:SetClampedToScreen(true)
	frame:RegisterForDrag("LeftButton")
	frame:SetScript("OnDragStart", function(self)
		if not ForeverRappelsDB.locked then self:StartMoving() end
	end)
	frame:SetScript("OnDragStop", function(self)
		self:StopMovingOrSizing()
		local point, _, relPoint, x, y = self:GetPoint(1)
		ForeverRappelsDB.pos = { point = point, relPoint = relPoint, x = x, y = y }
	end)
	local texture = frame:CreateTexture("ForeverRappelsIconTexture", "ARTWORK")
	texture:SetAllPoints(frame)
	frame:Hide()
	M.frame, M.texture = frame, texture
	applySize()
	applyPosition()
	applyLock()
end

local function dataStatus()
	if not hasData() then
		return "données absentes : réinstaller l'addon (uv run python scripts/install_addon.py --addon ForeverRappels)"
	end
	return "données " .. tostring(ForeverRappelsData.game_version or "?")
end

local function help()
	say(dataStatus())
	say("/rappels verrou | deverrou (déplacer l'icône) | test | regles | lecture exacte|prudente")
end

local function listRules()
	local rules = RULES[playerClass() or ""]
	if not rules then
		say("aucune règle pour cette classe")
		return
	end
	for _, rule in ipairs(rules) do
		say((ruleOn(rule) and "[actif] " or "[éteint] ") .. ruleLabel(rule))
	end
end

local function slash(msg)
	local cmd, arg = (msg or ""):match("^%s*(%S*)%s*(.-)%s*$")
	cmd = (cmd or ""):lower()
	if cmd == "" then
		if M.plugin then
			local ok = pcall(EllesmereUI.OpenPlugin, ADDON)
			if ok then return end
		end
		help()
	elseif cmd == "verrou" then
		setLocked(true)
	elseif cmd == "deverrou" then
		setLocked(false)
		say("icône déverrouillée : la faire glisser, puis /rappels verrou")
	elseif cmd == "test" then
		M.testing = not M.testing
		evaluate()
	elseif cmd == "regles" then
		listRules()
	elseif cmd == "lecture" and (arg == "exacte" or arg == "prudente") then
		ForeverRappelsDB.lecture_combat = arg
		say("lecture des auras en combat : " .. arg)
	else
		help()
	end
end

-- Page dans EllesmereUI (API publique de plugin, PLUGINS_API.md d'EllesmereUI) ; rien n'est modifié chez lui.
local function buildPage(pageName, parent, yOffset)
	local W = EllesmereUI.Widgets
	local y = yOffset or 0
	local _, h
	_, h = W:SectionHeader(parent, "RÈGLES", y)
	y = y - h
	local rules = RULES[playerClass() or ""] or {}
	for _, rule in ipairs(rules) do
		_, h = W:Toggle(parent, ruleLabel(rule), y, function()
			return ruleOn(rule)
		end, function(value)
			ForeverRappelsDB.regles[rule.key] = value and true or false
			evaluate()
		end)
		y = y - h
	end
	_, h = W:SectionHeader(parent, "AFFICHAGE", y)
	y = y - h
	_, h = W:Toggle(parent, "Verrouiller l'icône", y, function()
		return ForeverRappelsDB.locked
	end, setLocked)
	y = y - h
	_, h = W:Toggle(parent, "Son à l'apparition", y, function()
		return ForeverRappelsDB.son
	end, function(value)
		ForeverRappelsDB.son = value and true or false
	end)
	y = y - h
	_, h = W:Slider(parent, "Taille de l'icône", y, 24, 128, 2, function()
		return ForeverRappelsDB.taille
	end, function(value)
		ForeverRappelsDB.taille = value
		applySize()
	end)
	y = y - h
	_, h = W:Button(parent, "Tester l'icône", y, function()
		M.testing = not M.testing
		evaluate()
	end)
	y = y - h
	return math.abs(y)
end

local function registerPlugin()
	if not (EllesmereUI and EllesmereUI.RegisterPlugin) then return end
	local ok, accepted = pcall(EllesmereUI.RegisterPlugin, ADDON, {
		label = "Rappels",
		modules = {
			{
				key = "Rappels",
				title = "Rappels d'aura",
				description = "Icône qui rappelle l'aura qui manque, en combat et hors combat.",
				pages = { "Réglages" },
				buildPage = buildPage,
			},
		},
	})
	M.plugin = ok and accepted == true
	if not M.plugin then say("page EllesmereUI non créée (API de plugin refusée ou changée) : /rappels reste disponible") end
end

local function init()
	ForeverRappelsDB = ForeverRappelsDB or {}
	local db = ForeverRappelsDB
	if db.locked == nil then db.locked = true end
	if db.son == nil then db.son = true end
	if db.taille == nil then db.taille = DEFAULT_SIZE end
	if db.regles == nil then db.regles = {} end
	if db.lecture_combat == nil then db.lecture_combat = "prudente" end
	createFrame()
	SLASH_FOREVERRAPPELS1 = "/rappels"
	SlashCmdList.FOREVERRAPPELS = slash
	registerPlugin()
end

local handlers = {
	ADDON_LOADED = function(name)
		if name == ADDON then init() end
	end,
	PLAYER_LOGIN = function() refreshStates() end,
	PLAYER_ENTERING_WORLD = function() refreshStates() end,
	PLAYER_REGEN_DISABLED = function()
		M.combat = true
		refreshStates()
	end,
	PLAYER_REGEN_ENABLED = function()
		M.combat = false
		refreshStates()
	end,
	UNIT_AURA = function(unit)
		if unit == "player" then refreshStates() end
	end,
	UNIT_PET = function() end,
	UNIT_SPELLCAST_SUCCEEDED = function(unit, _, spellID)
		if unit == "player" then onCast(spellID) end
	end,
}

local events = CreateFrame("Frame", "ForeverRappelsEvents", UIParent)
for event in pairs(handlers) do
	pcall(events.RegisterEvent, events, event)
end
events:SetScript("OnEvent", function(_, event, ...)
	local ok = pcall(handlers[event], ...)
	if ok and event ~= "ADDON_LOADED" then pcall(evaluate) end
	if not ok and not M.errorSaid then
		M.errorSaid = true
		say("erreur interne sur " .. event .. " (signalée une fois)")
	end
end)
