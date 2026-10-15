-- Client simulé de WoW Forever pour les tests de ForeverBridge sous lupa.lua51 (P06a).
-- Écrit pour ce dépôt, sans rien reprendre d'un autre projet : seules les API que nos addons appellent.
-- Les fonctions d'action et ReloadUI sont des pièges qui enregistrent tout appel (Stub.forbidden).
-- Pilotage depuis Python : Stub.Fire(event, ...), Stub.Advance(secondes, pas), Stub.Slash(ligne),
-- Stub.files[chemin] = "valid" | "empty" (absent : nil), Stub.addons[nom] = source Lua d'un addon à la demande.
-- Sons comme sur Forever (sonde en jeu A du 2026-10-09) : un fichier présent au lancement (au premier ADDON_LOADED)
-- « jouera », vide ou non ; un fichier ajouté ensuite n'est jamais vu.

bit = nil -- absent de Lua 5.1 nu ; le jeu le fournit, nos addons n'en dépendent pas

Stub = {
	time = 0,
	epoch = 1791547200,
	screen = { 1920, 1080 },
	combat = false,
	printed = {},
	played = {},
	stopped = {},
	forbidden = {},
	registered = {},
	unknown_events = {},
	files = {},
	launched = nil,
	addons = {},
	loaded = {},
	sound_error = false,
	frames = {},
	next_handle = 0,
}

local function newRegion(kind, name, parent)
	local r = {
		kind = kind,
		name = name,
		parent = parent,
		shown = true,
		points = {},
		width = 0,
		height = 0,
		scale = 1,
		ignoreParentScale = false,
		scripts = {},
		events = {},
		textures = {},
		color = nil,
	}
	function r:Show() self.shown = true end
	function r:Hide() self.shown = false end
	function r:SetShown(v) self.shown = v and true or false end
	function r:IsShown() return self.shown end
	function r:IsVisible()
		local f = self
		while f do
			if not f.shown then return false end
			f = f.parent
		end
		return true
	end
	function r:SetSize(w, h) self.width, self.height = w, h end
	function r:SetWidth(w) self.width = w end
	function r:SetHeight(h) self.height = h end
	function r:GetWidth() return self.width end
	function r:GetHeight() return self.height end
	function r:ClearAllPoints() self.points = {} end
	function r:SetPoint(point, rel, relPoint, x, y)
		if type(rel) == "number" then rel, relPoint, x, y = nil, nil, rel, relPoint end
		table.insert(self.points, { point = point, rel = rel or self.parent, relPoint = relPoint or point, x = x or 0, y = y or 0 })
	end
	function r:SetAllPoints(rel) self.points = { { point = "ALL", rel = rel or self.parent, x = 0, y = 0 } } end
	function r:SetScale(s) self.scale = s end
	function r:GetScale() return self.scale end
	function r:SetIgnoreParentScale(v) self.ignoreParentScale = v and true or false end
	function r:GetEffectiveScale()
		if self.ignoreParentScale or not self.parent then return self.scale end
		return self.parent:GetEffectiveScale() * self.scale
	end
	function r:SetFrameStrata(s) self.strata = s end
	function r:GetFrameStrata() return self.strata end
	function r:SetFrameLevel(l) self.level = l end
	function r:SetAlpha(a) self.alpha = a end
	function r:SetColorTexture(cr, cg, cb, ca) self.color = { cr, cg, cb, ca or 1 } end
	function r:SetTexture(t) self.texture = t end
	function r:SetScript(what, fn) self.scripts[what] = fn end
	function r:HookScript(what, fn)
		local before = self.scripts[what]
		self.scripts[what] = function(...)
			if before then before(...) end
			fn(...)
		end
	end
	function r:GetPoint(i)
		local p = self.points[i or 1]
		if not p then return nil end
		return p.point, p.rel, p.relPoint, p.x, p.y
	end
	function r:GetSize() return self.width, self.height end
	function r:SetMovable(v) self.movable = v and true or false end
	function r:SetResizable(v) self.resizable = v and true or false end
	function r:SetClampedToScreen(v) self.clamped = v and true or false end
	function r:SetResizeBounds(w, h) self.minWidth, self.minHeight = w, h end
	function r:EnableMouse(v) self.mouse = v and true or false end
	function r:EnableMouseWheel(v) self.wheel = v and true or false end
	function r:RegisterForDrag(...) self.drag = { ... } end
	function r:StartMoving() self.moving = true end
	function r:StartSizing() self.sizing = true end
	function r:StopMovingOrSizing() self.moving, self.sizing = false, false end
	function r:SetBackdrop(b) self.backdrop = b end
	function r:SetBackdropColor(cr, cg, cb, ca) self.backdropColor = { cr, cg, cb, ca or 1 } end
	function r:SetBackdropBorderColor() end
	function r:SetNormalTexture(t) self.normal = t end
	function r:SetHighlightTexture(t) self.highlight = t end
	function r:SetPushedTexture(t) self.pushed = t end
	function r:SetText(text) self.text = text end
	function r:GetText() return self.text end
	function r:SetFontObject(o) self.font = o end
	function r:SetFont(path, size, flags) self.fontPath, self.fontSize = path, size; return true end
	function r:SetFontString(fs) self.fontString = fs end
	function r:SetJustifyH(j) self.justify = j end
	function r:SetJustifyV(j) self.justifyV = j end
	function r:SetTextColor() end
	function r:SetWordWrap(v) self.wrap = v end
	function r:SetVertexColor(...) self.vertex = { ... } end
	-- EditBox
	function r:SetMultiLine(v) self.multiLine = v end
	function r:SetAutoFocus(v) self.autoFocus = v end
	function r:SetMaxLetters(n) self.maxLetters = n end
	function r:SetTextInsets() end
	function r:Insert(s) self.text = (self.text or "") .. s end
	function r:SetFocus() self.focus = true end
	function r:ClearFocus() self.focus = false end
	function r:HasFocus() return self.focus and true or false end
	function r:HighlightText() self.highlighted = true end
	function r:SetScrollChild(c) self.child = c end
	function r:GetScrollChild() return self.child end
	function r:SetVerticalScroll(y) self.vscroll = y end
	function r:GetVerticalScroll() return self.vscroll or 0 end
	function r:GetVerticalScrollRange()
		return math.max(0, (self.child and self.child.height or 0) - self.height)
	end
	function r:Enable() self.enabled = true end
	function r:Disable() self.enabled = false end
	-- ScrollingMessageFrame
	function r:AddMessage(text) self.messages = self.messages or {}; table.insert(self.messages, text) end
	function r:Clear() self.messages = {} end
	function r:SetMaxLines(n) self.maxLines = n end
	function r:SetFading(v) self.fading = v end
	function r:SetInsertMode(m) self.insertMode = m end
	function r:SetHyperlinksEnabled(v) self.hyperlinks = v end
	function r:ScrollUp() end
	function r:ScrollDown() end
	function r:ScrollToBottom() end
	function r:SetSpacing() end
	function r:GetScript(what) return self.scripts[what] end
	function r:RegisterEvent(event)
		if Stub.unknown_events[event] then error("Attempt to register unknown event \"" .. event .. "\"") end
		self.events[event] = true
		Stub.registered[event] = true
	end
	function r:UnregisterEvent(event) self.events[event] = nil end
	function r:CreateTexture(tname, layer)
		local t = newRegion("Texture", tname, self)
		t.layer = layer
		if tname then _G[tname] = t end
		table.insert(self.textures, t)
		return t
	end
	function r:CreateFontString(fname, layer)
		local fs = newRegion("FontString", fname, self)
		fs.layer = layer
		if fname then _G[fname] = fs end
		return fs
	end
	return r
end

Stub.newRegion = newRegion
UIParent = newRegion("Frame", "UIParent", nil)
UIParent.width, UIParent.height = 1024, 768
WorldFrame = UIParent

function CreateFrame(kind, name, parent, template)
	local f = newRegion(kind, name, parent or UIParent)
	f.template = template
	if kind == "ScrollingMessageFrame" then f.messages = {} end -- historique vide lisible avant la première ligne
	table.insert(Stub.frames, f)
	if name then _G[name] = f end
	return f
end

function GetPhysicalScreenSize() return Stub.screen[1], Stub.screen[2] end
function GetTime() return Stub.time end
function time() return Stub.epoch + math.floor(Stub.time) end
function InCombatLockdown() return Stub.combat end
-- Valeur secrète simulée : une API listée dans Stub.secret la rend ; une API de Stub.failing lève une erreur.
Stub.SECRET = setmetatable({}, { __tostring = function() return "<secret>" end })
Stub.secret = {}
Stub.failing = {}
Stub.shift = false
function issecretvalue(v) return rawequal(v, Stub.SECRET) end
function IsShiftKeyDown() return Stub.shift end

-- Personnage simulé (valeurs synthétiques, aucune règle de jeu).
Stub.player = {
	name = "Jen", realm = "Forever", level = 19, class = "MAGE", race = "Human", faction = "Alliance",
	zone = "Westfall", subzone = "Sentinel Hill", map = 1436, config = 7, trees = { 1 },
	nodes = { [1] = { 101, 102, 140, 150 } }, ranks = { [101] = 2, [102] = 3, [140] = 1, [150] = 0 },
	gear = {
		[1] = "|cffffffff|Hitem:12345::::::::19:::::|h[Hat of Testing]|h|r",
		[5] = "|cff1eff00|Hitem:23456::::::::19:::::|h[Robe of Testing]|h|r",
	},
	target = nil, -- jeton de classe d'un joueur en cible
	target_level = nil, -- niveau de la cible (-1 : crâne, niveau caché)
	target_race = nil, -- race de la cible (nom de fichier)
	version = "1.60.1", build = "70291",
}

local function api(name, fn)
	return function(...)
		if Stub.failing[name] then error("panne simulée de " .. name) end
		if Stub.secret[name] then return Stub.SECRET end
		return fn(...)
	end
end

UnitName = api("UnitName", function(unit) if unit == "player" then return Stub.player.name end end)
GetRealmName = api("GetRealmName", function() return Stub.player.realm end)
UnitLevel = api("UnitLevel", function(unit)
	if unit == "player" then return Stub.player.level end
	if unit == "target" then return Stub.player.target_level end
end)
UnitClassBase = api("UnitClassBase", function(unit)
	if unit == "player" then return Stub.player.class end
	if unit == "target" then return Stub.player.target end
end)
UnitClass = api("UnitClass", function(unit)
	local token = UnitClassBase(unit)
	if token then return token:sub(1, 1) .. token:sub(2):lower(), token end
end)
UnitRace = api("UnitRace", function(unit)
	if unit == "player" then return Stub.player.race, Stub.player.race end
	if unit == "target" and Stub.player.target_race then return Stub.player.target_race, Stub.player.target_race end
end)
UnitFactionGroup = api("UnitFactionGroup", function(unit) return Stub.player.faction, Stub.player.faction end)
GetRealZoneText = api("GetRealZoneText", function() return Stub.player.zone end)
GetSubZoneText = api("GetSubZoneText", function() return Stub.player.subzone end)
UnitExists = api("UnitExists", function(unit) return unit == "player" or (unit == "target" and Stub.player.target ~= nil) end)
UnitIsPlayer = api("UnitIsPlayer", function(unit) return unit == "player" or (unit == "target" and Stub.player.target ~= nil) end)
GetBuildInfo = api("GetBuildInfo", function() return Stub.player.version, Stub.player.build, "Oct 1 2026", 16001 end)
GetInventoryItemLink = api("GetInventoryItemLink", function(unit, slot) return Stub.player.gear[slot] end)
C_Map = {
	GetBestMapForUnit = api("C_Map.GetBestMapForUnit", function() return Stub.player.map end),
	-- CJ1 : position du joueur (fraction de la carte), nil si Stub.player.pos est absent
	GetPlayerMapPosition = api("C_Map.GetPlayerMapPosition", function(_, _)
		local pos = Stub.player.pos
		if not pos then return nil end
		return { x = pos.x, y = pos.y, GetXY = function(self) return self.x, self.y end }
	end),
}
C_ClassTalents = { GetActiveConfigID = api("C_ClassTalents.GetActiveConfigID", function() return Stub.player.config end) }
C_Traits = {
	GetConfigInfo = api("C_Traits.GetConfigInfo", function(config) return { treeIDs = Stub.player.trees } end),
	GetTreeNodes = api("C_Traits.GetTreeNodes", function(tree) return Stub.player.nodes[tree] end),
	GetNodeInfo = api("C_Traits.GetNodeInfo", function(config, node)
		return { ID = node, ranksPurchased = Stub.player.ranks[node] or 0 }
	end),
}

-- Infobulles (P06b) : Stub.tooltips[corps du lien] = { lignes } ; C_TooltipInfo.GetHyperlink rend { lines = {
-- { leftText = … } } } d'après le corps lu entre |H et |h (ou le texte donné tel quel).
Stub.tooltips = {}
C_TooltipInfo = {
	GetHyperlink = api("C_TooltipInfo.GetHyperlink", function(link)
		local body = tostring(link):match("|H(.-)|h") or tostring(link)
		local lines = Stub.tooltips[body]
		if not lines then return nil end
		local data = { lines = {} }
		for i, text in ipairs(lines) do data.lines[i] = { leftText = text } end
		return data
	end),
}

-- Insertion de liens par Maj+clic (P06b) : fonctions de Blizzard simulées, sans effet propre ; avec
-- Stub.chained_insert, ChatFrameUtil.InsertLink appelle aussi ChatEdit_InsertLink (un clic, deux accroches).
Stub.inserted = {}
function ChatEdit_InsertLink(link)
	table.insert(Stub.inserted, link)
	return false
end
ChatFrameUtil = {}
function ChatFrameUtil.InsertLink(link)
	if Stub.chained_insert then return ChatEdit_InsertLink(link) end
	table.insert(Stub.inserted, link)
	return false
end

-- hooksecurefunc([table,] nom, fonction) : la fonction d'origine, puis l'accroche, avec les mêmes arguments.
function hooksecurefunc(a, b, c)
	local tbl, name, hook = a, b, c
	if type(a) == "string" then tbl, name, hook = _G, a, b end
	local original = tbl[name]
	if type(original) ~= "function" then error("hooksecurefunc : " .. tostring(name) .. " absente") end
	tbl[name] = function(...)
		local r1, r2, r3 = original(...)
		hook(...)
		return r1, r2, r3
	end
end

function PlaySoundFile(path, channel)
	if Stub.sound_error then error("PlaySoundFile simulé en erreur") end
	table.insert(Stub.played, path)
	if Stub.launched and Stub.launched[path] then
		Stub.next_handle = Stub.next_handle + 1
		return true, Stub.next_handle
	end
	return false, nil
end

function StopSound(handle) table.insert(Stub.stopped, handle) end

DEFAULT_CHAT_FRAME = { AddMessage = function(self, msg) table.insert(Stub.printed, msg) end }
function print(...)
	local parts = {}
	for i = 1, select("#", ...) do parts[#parts + 1] = tostring((select(i, ...))) end
	table.insert(Stub.printed, table.concat(parts, " "))
end

SlashCmdList = {}
UISpecialFrames = {}
tinsert = table.insert
GameFontNormal, GameFontNormalLarge, GameFontHighlight, GameFontHighlightSmall, GameFontDisableSmall, ChatFontNormal =
	{}, {}, {}, {}, {}, {}

C_AddOns = {}
function C_AddOns.IsAddOnLoaded(name) return Stub.loaded[name] and true or false end
Stub.loadlog = {} -- { nom, instant } de chaque appel à LoadAddOn
function C_AddOns.LoadAddOn(name)
	table.insert(Stub.loadlog, { name, Stub.time })
	if Stub.loaded[name] then return true, nil end
	local source = Stub.addons[name]
	if not source then return false, "MISSING" end
	local chunk = assert(loadstring(source, name))
	chunk(name, {})
	Stub.loaded[name] = true
	return true, nil
end

-- Pièges : aucune action de jeu, aucun rechargement de l'interface par nos addons.
local function trap(fname)
	return function() table.insert(Stub.forbidden, fname) end
end
for _, fname in ipairs({ "CastSpellByName", "CastSpellByID", "UseAction", "SendChatMessage", "RunMacroText",
	"RunMacro", "CreateMacro", "ReloadUI" }) do
	_G[fname] = trap(fname)
end
C_UI = { Reload = trap("C_UI.Reload") }

function Stub.Fire(event, ...)
	if not Stub.launched then
		Stub.launched = {}
		for path in pairs(Stub.files) do Stub.launched[path] = true end
	end
	for _, f in ipairs(Stub.frames) do
		local handler = f.scripts.OnEvent
		if f.events[event] and handler then handler(f, event, ...) end
	end
end

-- Avance l'horloge ; OnUpdate n'est appelé que sur les cadres visibles, comme dans le jeu.
function Stub.Advance(seconds, step)
	step = step or 0.1
	local done = 0
	while done < seconds - 1e-9 do
		local dt = math.min(step, seconds - done)
		Stub.time = Stub.time + dt
		done = done + dt
		for _, f in ipairs(Stub.frames) do
			local handler = f.scripts.OnUpdate
			if handler and f:IsVisible() then handler(f, dt) end
		end
	end
end

-- Ligne tapée dans le chat (« /fv test »).
function Stub.Slash(line)
	local command, rest = line:match("^(/%S+)%s*(.-)$")
	for key, handler in pairs(SlashCmdList) do
		local i = 1
		while _G["SLASH_" .. key .. i] do
			if _G["SLASH_" .. key .. i] == command then
				handler(rest)
				return true
			end
			i = i + 1
		end
	end
	return false
end

-- Textures visibles d'un cadre : { x, y, largeur, hauteur, r, g, b } en unités d'interface du cadre.
function Stub.ShownTextures(frame)
	local out = {}
	for _, t in ipairs(frame.textures) do
		if t.shown and t.color then
			local p = t.points[1]
			table.insert(out, { p and p.x or 0, p and p.y or 0, t.width, t.height, t.color[1], t.color[2], t.color[3] })
		end
	end
	return out
end

-- ForeverLogger (T04d, bloc A) : unités simulées (cible, plaques de nom, groupe), expérience et repos du personnage,
-- instance, groupe, journal des quêtes. Valeurs synthétiques posées par les tests, aucune règle de jeu.
-- Stub.units[unité] = { name, level, classification, dead, guid, creature_type } ; une unité absente garde le
-- comportement précédent (cible joueur de ForeverBridge).
Stub.units = {}
Stub.player.guid = "Player-0000-00000001"
Stub.player.xp = 0
Stub.player.xp_max = 1000
Stub.player.rested = nil -- GetXPExhaustion : nil sans repos
Stub.player.resting = false
Stub.player.rest_state = 2 -- GetRestState : identifiant d'état (valeur synthétique)
Stub.player.trivial_range = 5
Stub.instance = { inside = false, type = "none", name = nil, id = nil }
Stub.group = { size = 0, raid = false }
Stub.quests = {} -- [questID] = { title, level, index } : quêtes présentes dans le journal
Stub.cvars = {}
Stub.logging = false

local baseUnitName, baseUnitLevel, baseUnitExists = UnitName, UnitLevel, UnitExists
UnitName = api("UnitName", function(unit)
	local u = Stub.units[unit]
	if u then return u.name end
	return baseUnitName(unit)
end)
UnitLevel = api("UnitLevel", function(unit)
	local u = Stub.units[unit]
	if u then return u.level end
	return baseUnitLevel(unit)
end)
UnitExists = api("UnitExists", function(unit)
	if Stub.units[unit] then return true end
	return baseUnitExists(unit)
end)
UnitGUID = api("UnitGUID", function(unit)
	if unit == "player" then return Stub.player.guid end
	local u = Stub.units[unit]
	if u then return u.guid end
end)
UnitIsDead = api("UnitIsDead", function(unit) local u = Stub.units[unit]; return u ~= nil and u.dead == true end)
UnitClassification = api("UnitClassification", function(unit) local u = Stub.units[unit]; return u and u.classification end)
UnitCreatureType = api("UnitCreatureType", function(unit) local u = Stub.units[unit]; return u and u.creature_type end)
UnitXP = api("UnitXP", function(unit) if unit == "player" then return Stub.player.xp end end)
UnitXPMax = api("UnitXPMax", function(unit) if unit == "player" then return Stub.player.xp_max end end)
GetXPExhaustion = api("GetXPExhaustion", function() return Stub.player.rested end)
IsResting = api("IsResting", function() return Stub.player.resting end)
GetRestState = api("GetRestState", function() return Stub.player.rest_state, "State" .. Stub.player.rest_state, 1 end)
UnitQuestTrivialLevelRange = api("UnitQuestTrivialLevelRange", function() return Stub.player.trivial_range end)
IsInInstance = api("IsInInstance", function() return Stub.instance.inside, Stub.instance.type end)
GetInstanceInfo = api("GetInstanceInfo", function()
	return Stub.instance.name, Stub.instance.type, 1, "Normal", 5, 0, false, Stub.instance.id
end)
GetNumGroupMembers = api("GetNumGroupMembers", function() return Stub.group.size end)
IsInRaid = api("IsInRaid", function() return Stub.group.raid end)
GetServerTime = api("GetServerTime", function() return Stub.epoch + math.floor(Stub.time) end)
date = function(fmt) return os.date(fmt, Stub.epoch + math.floor(Stub.time)) end
SetCVar = function(name, value) Stub.cvars[name] = value end
LoggingCombat = function(value)
	if value ~= nil then Stub.logging = value end
	return Stub.logging
end
C_QuestLog = {
	GetTitleForQuestID = api("C_QuestLog.GetTitleForQuestID", function(id) local q = Stub.quests[id]; return q and q.title end),
	GetLogIndexForQuestID = api("C_QuestLog.GetLogIndexForQuestID", function(id) local q = Stub.quests[id]; return q and q.index end),
	GetInfo = api("C_QuestLog.GetInfo", function(index)
		for id, q in pairs(Stub.quests) do
			if q.index == index then return { questID = id, title = q.title, level = q.level } end
		end
	end),
}

-- T04f, bloc D : auras du joueur (C_UnitAuras), objets portés (C_Item.GetItemCount), configuration d'un arbre de
-- traits du compte (C_Traits.GetConfigIDByTreeID). Valeurs synthétiques posées par les tests, aucune règle de jeu.
-- Stub.player.auras = { { spellId, applications, expirationTime, duration } } (expirationTime 0 : sans fin) ;
-- Stub.player.items[objet] = nombre ; Stub.player.tree_configs[arbre] = configuration.
Stub.player.auras = {}
Stub.player.items = {}
Stub.player.tree_configs = {}
C_UnitAuras = {
	GetAuraDataByIndex = api("C_UnitAuras.GetAuraDataByIndex", function(unit, index, filter)
		if unit ~= "player" or filter ~= "HELPFUL" then return nil end
		return Stub.player.auras[index]
	end),
}
C_Item = C_Item or {}
C_Item.GetItemCount = api("C_Item.GetItemCount", function(item) return Stub.player.items[item] or 0 end)
C_Traits.GetConfigIDByTreeID = api("C_Traits.GetConfigIDByTreeID", function(tree) return Stub.player.tree_configs[tree] end)

-- DJ1, bloc D : fenêtre de butin (GetNumLootItems, GetLootSlotLink, GetLootSlotInfo, GetLootSourceInfo).
-- Stub.loot = { { link, name, quantity, sources = { guid, quantité, guid, quantité… } } } ; valeurs synthétiques.
Stub.loot = {}
GetNumLootItems = api("GetNumLootItems", function() return #Stub.loot end)
GetLootSlotLink = api("GetLootSlotLink", function(slot) local l = Stub.loot[slot]; return l and l.link end)
GetLootSlotInfo = api("GetLootSlotInfo", function(slot)
	local l = Stub.loot[slot]
	if l then return nil, l.name, l.quantity end
end)
GetLootSourceInfo = api("GetLootSourceInfo", function(slot)
	local l = Stub.loot[slot]
	if l and l.sources then return unpack(l.sources) end
end)
