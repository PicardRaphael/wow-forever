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
	function r:SetBackdropColor() end
	function r:SetBackdropBorderColor() end
	function r:SetNormalTexture(t) self.normal = t end
	function r:SetHighlightTexture(t) self.highlight = t end
	function r:SetPushedTexture(t) self.pushed = t end
	function r:SetText(text) self.text = text end
	function r:GetText() return self.text end
	function r:SetFontObject(o) self.font = o end
	function r:SetJustifyH(j) self.justify = j end
	function r:SetJustifyV(j) self.justifyV = j end
	function r:SetTextColor() end
	function r:SetWordWrap(v) self.wrap = v end
	function r:SetVertexColor(...) self.vertex = { ... } end
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
	table.insert(Stub.frames, f)
	if name then _G[name] = f end
	return f
end

function GetPhysicalScreenSize() return Stub.screen[1], Stub.screen[2] end
function GetTime() return Stub.time end
function time() return Stub.epoch + math.floor(Stub.time) end
function InCombatLockdown() return Stub.combat end
function issecretvalue() return false end

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
function C_AddOns.LoadAddOn(name)
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
