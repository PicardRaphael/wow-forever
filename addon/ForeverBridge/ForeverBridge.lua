-- ForeverBridge : pont de conversation de forever-core (P06a, décisions 194 et 212).
-- Blocs A et A2 : fenêtre dédiée (/fv, raccourci, Échap), bande de test (/fv test, une case par pixel par défaut) lue
-- par « forever bridge selftest --live », consultation d'un emplacement de sonde (/fv poll) et autotest des fichiers
-- de contrôle (/fv diag, seule commande qui écrit dans la discussion générale).
-- Seul addon de forever-core qui dessine (décision 194) : la bande n'apparaît que sur demande. Aucune fonction
-- d'action, aucun rechargement de l'interface, aucun abonnement au journal de combat, aucune ouverture automatique.
--
-- Contient du code adapté de wow-ai (https://github.com/chelinho139/wow-ai, commit 3756eb5a : dessin de la bande,
-- autotest des signaux et fenêtre, addon/WoWAI/WoWAI.lua), sous la licence suivante :
--
-- MIT License
--
-- Copyright (c) 2026 chelinho139
--
-- Permission is hereby granted, free of charge, to any person obtaining a copy
-- of this software and associated documentation files (the "Software"), to deal
-- in the Software without restriction, including without limitation the rights
-- to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
-- copies of the Software, and to permit persons to whom the Software is
-- furnished to do so, subject to the following conditions:
--
-- The above copyright notice and this permission notice shall be included in all
-- copies or substantial portions of the Software.
--
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
-- IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
-- FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
-- AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
-- LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
-- OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
-- SOFTWARE.

local ADDON = ... or "ForeverBridge"

ForeverBridge = {}
local FB = ForeverBridge
local Codec = ForeverBridge_Codec

local DEFAULT_CELL = 1 -- côté d'une case de la bande, en pixels physiques (repli de 2 à 4 par /fv test N)
local MAX_CELL = 4
local TEST_DURATION = 120 -- la bande de test se retire seule au bout de deux minutes
local CTL = "Interface\\AddOns\\ForeverBridge\\ctl\\"
local PROBE_ADDON = "ForeverBridge_Probe"
local PROBE2_ADDON = "ForeverBridge_Probe2"
local PREFIX = "|cff33ff99ForeverBridge|r : "
local WINDOW_W, WINDOW_H = 520, 360
local MIN_W, MIN_H = 360, 240
local MIN_ALPHA = 0.3 -- fond réglable par /fv fond, de 30 à 100 (opaque par défaut)

BINDING_HEADER_FOREVERBRIDGE = "ForeverBridge"
BINDING_NAME_FOREVERBRIDGE_TOGGLE = "Ouvrir ou fermer la fenêtre"

local driver = CreateFrame("Frame", "ForeverBridgeDriver", UIParent)
local band
local textures = {}
local run = {}
local ui = {}

-- Diagnostic demandé par le joueur (/fv diag) : seule écriture dans la discussion générale.
local function ChatSay(text)
	DEFAULT_CHAT_FRAME:AddMessage(PREFIX .. text)
end

local function PhysicalSize()
	if type(GetPhysicalScreenSize) == "function" then
		local width, height = GetPhysicalScreenSize()
		if width and height and height > 0 then
			return width, height
		end
	end
	return 1920, 1080
end

---------------------------------------------------------------------------
-- Fenêtre dédiée (cadre adapté de wow-ai : glisser, poignée, Échap)
---------------------------------------------------------------------------

local BACKDROP = {
	bgFile = "Interface\\ChatFrame\\ChatFrameBackground",
	edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
	tile = true,
	tileSize = 16,
	edgeSize = 12,
	insets = { left = 3, right = 3, top = 3, bottom = 3 },
}

local function WindowState()
	local db = ForeverBridgeDB
	if type(db) ~= "table" then
		return nil
	end
	if type(db.window) ~= "table" then
		db.window = {}
	end
	return db.window
end

function FB.SaveGeometry()
	local f, state = ui.frame, WindowState()
	if not f or not state then
		return
	end
	local point, _, relPoint, x, y = f:GetPoint(1)
	state.point, state.relPoint, state.x, state.y = point, relPoint, x, y
	state.width, state.height = f:GetWidth(), f:GetHeight()
end

local function RestoreGeometry(f)
	local state = WindowState() or {}
	local width = tonumber(state.width) or WINDOW_W
	local height = tonumber(state.height) or WINDOW_H
	f:SetSize(math.max(width, MIN_W), math.max(height, MIN_H))
	f:ClearAllPoints()
	if type(state.point) == "string" then
		f:SetPoint(state.point, UIParent, state.relPoint or state.point, tonumber(state.x) or 0, tonumber(state.y) or 0)
	else
		f:SetPoint("CENTER", UIParent, "CENTER", 0, 0)
	end
end

-- Opacité du fond : celle gardée dans ForeverBridgeDB.window, opaque à défaut.
function FB.ApplyBackground()
	local f = ui.frame
	if not (f and f.SetBackdropColor) then
		return
	end
	local alpha = tonumber((WindowState() or {}).alpha) or 1
	alpha = math.min(1, math.max(MIN_ALPHA, alpha))
	f:SetBackdropColor(0.05, 0.05, 0.07, alpha)
end

local function BuildWindow()
	if ui.frame then
		return ui.frame
	end
	local f = CreateFrame("Frame", "ForeverBridgeWindow", UIParent, "BackdropTemplate")
	ui.frame = f
	f:SetFrameStrata("DIALOG")
	f:SetMovable(true)
	f:SetResizable(true)
	f:SetClampedToScreen(true)
	if not (f.SetResizeBounds and pcall(f.SetResizeBounds, f, MIN_W, MIN_H)) and f.SetMinResize then
		pcall(f.SetMinResize, f, MIN_W, MIN_H)
	end
	f:EnableMouse(true)
	f:RegisterForDrag("LeftButton")
	f:SetScript("OnDragStart", function(self)
		self:StartMoving()
	end)
	f:SetScript("OnDragStop", function(self)
		self:StopMovingOrSizing()
		FB.SaveGeometry()
	end)
	if f.SetBackdrop then
		f:SetBackdrop(BACKDROP)
		f:SetBackdropBorderColor(0.6, 0.6, 0.6, 1)
	end
	RestoreGeometry(f)
	FB.ApplyBackground()
	f:Hide()
	tinsert(UISpecialFrames, "ForeverBridgeWindow")

	local dot = f:CreateTexture(nil, "OVERLAY")
	dot:SetSize(14, 14)
	dot:SetPoint("TOPLEFT", f, "TOPLEFT", 14, -14)
	dot:SetTexture("Interface\\FriendsFrame\\StatusIcon-Offline")
	ui.dot = dot

	local title = f:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
	title:SetPoint("LEFT", dot, "RIGHT", 6, 0)
	title:SetText("ForeverBridge")

	local status = f:CreateFontString("ForeverBridgeStatus", "OVERLAY", "GameFontHighlightSmall")
	status:SetPoint("TOPLEFT", f, "TOPLEFT", 14, -34)
	status:SetPoint("RIGHT", f, "RIGHT", -34, 0)
	status:SetJustifyH("LEFT")
	status:SetText("Pont : pas encore vu · état des données inconnu")
	ui.status = status

	local close = CreateFrame("Button", nil, f, "UIPanelCloseButton")
	close:SetPoint("TOPRIGHT", f, "TOPRIGHT", -4, -4)
	close:SetScript("OnClick", function()
		f:Hide()
	end)

	local history = CreateFrame("ScrollingMessageFrame", "ForeverBridgeHistory", f)
	history:SetPoint("TOPLEFT", f, "TOPLEFT", 14, -52)
	history:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -14, 22)
	history:SetFontObject(ChatFontNormal)
	history:SetJustifyH("LEFT")
	history:SetFading(false)
	history:SetMaxLines(500)
	history:SetHyperlinksEnabled(true)
	history:EnableMouseWheel(true)
	history:SetScript("OnMouseWheel", function(self, delta)
		if delta > 0 then
			self:ScrollUp()
		else
			self:ScrollDown()
		end
	end)
	ui.history = history

	local grip = CreateFrame("Button", nil, f)
	grip:SetSize(16, 16)
	grip:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -5, 5)
	grip:SetNormalTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Up")
	grip:SetHighlightTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Highlight")
	grip:SetPushedTexture("Interface\\ChatFrame\\UI-ChatIM-SizeGrabber-Down")
	grip:SetScript("OnMouseDown", function()
		f:StartSizing("BOTTOMRIGHT")
	end)
	grip:SetScript("OnMouseUp", function()
		f:StopMovingOrSizing()
		FB.SaveGeometry()
	end)
	return f
end

-- Ligne ajoutée à l'historique de la fenêtre, jamais à la discussion générale.
function FB.Print(text)
	BuildWindow()
	ui.history:AddMessage(text)
	ui.count = (ui.count or 0) + 1
end

-- Ouverture à la demande du joueur seulement (commande ou raccourci), jamais automatique.
function FB.Open()
	BuildWindow():Show()
end

function FB.Toggle()
	local f = BuildWindow()
	if f:IsShown() then
		f:Hide()
	else
		f:Show()
	end
end

---------------------------------------------------------------------------
-- Bande de pixels
---------------------------------------------------------------------------

-- Cadre de la bande : coin haut gauche, au-dessus de tout, une unité d'interface pour un pixel physique.
local function EnsureBand()
	if band then
		return band
	end
	band = CreateFrame("Frame", "ForeverBridgeBand", UIParent)
	band:SetFrameStrata("TOOLTIP")
	band:SetFrameLevel(10000)
	if band.SetIgnoreParentScale then
		band:SetIgnoreParentScale(true)
		run.ignoresParentScale = true
	end
	band:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 0, 0)
	band:Hide()
	return band
end

function FB.HideBand()
	if band then
		band:Hide()
	end
end

-- Dessine le message (numéro, charge) avec des cases de `cell` pixels ; faux et la raison si la charge dépasse la
-- bande.
function FB.ShowBand(id, payload, cell)
	cell = cell or DEFAULT_CELL
	local cells, why = Codec.Encode(id % 65536, payload)
	if not cells then
		return false, why
	end
	local b = EnsureBand()
	-- échelle recalculée à chaque affichage (la résolution a pu changer) ; sans SetIgnoreParentScale, celle de
	-- l'interface est compensée
	local _, height = PhysicalSize()
	local scale = 768 / height
	if not run.ignoresParentScale then
		scale = scale / UIParent:GetEffectiveScale()
	end
	b:SetScale(scale)
	local perRow = Codec.CELLS_PER_ROW
	local rows = math.ceil(#cells / perRow)
	b:SetSize(perRow * cell, rows * cell)
	local total = rows * perRow
	for i = 1, total do
		local t = textures[i]
		if not t then
			t = b:CreateTexture(nil, "OVERLAY")
			textures[i] = t
		end
		local col = (i - 1) % perRow
		local row = math.floor((i - 1) / perRow)
		t:SetSize(cell, cell)
		t:ClearAllPoints()
		t:SetPoint("TOPLEFT", b, "TOPLEFT", col * cell, -row * cell)
		local r, g, bl = Codec.CellColor(cells[i] or 0)
		t:SetColorTexture(r, g, bl, 1)
		t:Show()
	end
	for i = total + 1, #textures do
		textures[i]:Hide()
	end
	b:Show()
	return true
end

---------------------------------------------------------------------------
-- Bande de test (/fv test [taille de case])
---------------------------------------------------------------------------

function FB.StopTest()
	run.testLeft = nil
	FB.HideBand()
end

function FB.Test(size)
	local cell = tonumber(size)
	if size and size ~= "" and not (cell and cell == math.floor(cell) and cell >= 1 and cell <= MAX_CELL) then
		FB.Open()
		FB.Print("taille de case invalide : /fv test suivi de 1, 2, 3 ou 4.")
		return
	end
	if run.testLeft and not cell then
		FB.StopTest()
		FB.Print("bande de test retirée.")
		return
	end
	cell = cell or DEFAULT_CELL
	local ok, why = FB.ShowBand(Codec.SELFTEST_ID, Codec.SelftestPayload(), cell)
	FB.Open()
	if not ok then
		FB.Print("bande de test impossible : " .. tostring(why))
		return
	end
	run.testLeft = TEST_DURATION
	FB.Print("bande de test affichée en haut à gauche, case de " .. cell .. " pixel(s) (retirée dans deux minutes, "
		.. "ou par /fv test). Dans un terminal : uv run forever bridge selftest --live, puis revenir au jeu.")
end

-- Minuterie : le cadre pilote reste visible (OnUpdate ne tourne que sur un cadre visible).
function FB.Tick(elapsed)
	if run.testLeft then
		run.testLeft = run.testLeft - elapsed
		if run.testLeft <= 0 then
			FB.StopTest()
		end
	end
end

---------------------------------------------------------------------------
-- Consultation d'un emplacement de sonde (/fv poll)
---------------------------------------------------------------------------

local function LoadOnDemand(name)
	if not (C_AddOns and type(C_AddOns.LoadAddOn) == "function") then
		return false, "C_AddOns.LoadAddOn absente"
	end
	local ok, loaded, reason = pcall(C_AddOns.LoadAddOn, name)
	if not ok then
		return false, "erreur"
	end
	return loaded, reason
end

function FB.Poll()
	FB.Open()
	if run.probe2Loaded then
		FB.Print(PROBE2_ADDON .. " : déjà chargé dans cette session (valeur « " .. tostring(ForeverBridge_Probe2Value)
			.. " ») ; un nouvel essai demande /reload")
		return
	end
	local loaded, reason = LoadOnDemand(PROBE2_ADDON)
	if loaded then
		run.probe2Loaded = true
		FB.Print(PROBE2_ADDON .. " : chargé, valeur « " .. tostring(ForeverBridge_Probe2Value) .. " »")
	else
		FB.Print(PROBE2_ADDON .. " : non chargé (" .. tostring(reason) .. ")")
	end
end

---------------------------------------------------------------------------
-- Autotest des fichiers de contrôle (/fv diag)
---------------------------------------------------------------------------

-- Le son jouerait-il ? vrai, faux, ou nil et la raison ; un son valide est arrêté aussitôt.
local function Plays(path)
	if type(PlaySoundFile) ~= "function" then
		return nil, "PlaySoundFile absente"
	end
	local ok, willPlay, handle = pcall(PlaySoundFile, path, "Master")
	if not ok then
		return nil, "PlaySoundFile en erreur"
	end
	if willPlay and handle and type(StopSound) == "function" then
		pcall(StopSound, handle)
	end
	return willPlay and true or false
end

local CONTROLS = {
	{ "empty", "vide : ne doit pas jouer" },
	{ "valid", "son valide : doit jouer" },
	{ "flip", "vide au lancement, rempli par selftest --touch : joue alors si le client voit le fichier modifié" },
	{ "late", "absent au lancement, créé par selftest --touch : joue alors si le client voit le fichier ajouté" },
}

local function DiagSounds(ext)
	local results = {}
	for _, control in ipairs(CONTROLS) do
		local name = control[1]
		local plays, why = Plays(CTL .. name .. "." .. ext)
		results[name] = plays
		local state = why or (plays and "joue" or "ne joue pas")
		ChatSay("ctl/" .. name .. "." .. ext .. " : " .. state .. " (" .. control[2] .. ")")
	end
	local passed = results.empty == false and results.valid == true
	ChatSay("autotest ." .. ext .. " : " .. (passed and "réussi" or "échoué"))
	return passed
end

local function DiagProbe()
	local loaded, reason = LoadOnDemand(PROBE_ADDON)
	if loaded then
		ChatSay(PROBE_ADDON .. " : chargé, valeur « " .. tostring(ForeverBridge_ProbeValue) .. " »")
	else
		ChatSay(PROBE_ADDON .. " : non chargé (" .. tostring(reason) .. ")")
	end
end

local function RunDiag()
	local width, height = PhysicalSize()
	local uiScale = UIParent.GetEffectiveScale and UIParent:GetEffectiveScale() or 1
	ChatSay(string.format("écran %d × %d, échelle de la bande %.4f, échelle de l'interface %.4f", width, height,
		768 / height, uiScale))
	local wav = DiagSounds("wav")
	local ogg = DiagSounds("ogg")
	if not (wav or ogg) then
		ChatSay("canal son inutilisable sur ce client : les réponses passent par la consultation de la réserve "
			.. "(aucun son dans le chemin du pont)")
	end
	DiagProbe()
end

-- Diagnostic dans la discussion générale ; la fenêtre confirme son passage (elle peut couvrir la discussion) et une
-- erreur Lua y est montrée au lieu d'un silence.
function FB.Diag()
	local ok, err = pcall(RunDiag)
	if ok then
		FB.Print("/fv diag : résultats écrits dans la discussion générale (onglet principal), sous cette fenêtre si "
			.. "elle la couvre.")
	else
		local text = "/fv diag en erreur : " .. tostring(err)
		ChatSay(text)
		FB.Open()
		FB.Print(text)
	end
end

function FB.SetBackground(value)
	local percent = tonumber(value)
	if not (percent and percent >= MIN_ALPHA * 100 and percent <= 100) then
		FB.Print("fond : /fv fond suivi d'un nombre de 30 (transparent) à 100 (opaque).")
		return
	end
	local state = WindowState()
	if state then
		state.alpha = percent / 100
	end
	FB.ApplyBackground()
	FB.Print("fond : " .. percent .. " sur 100.")
end

---------------------------------------------------------------------------
-- Événements et commandes
---------------------------------------------------------------------------

local handlers = {}

function handlers.ADDON_LOADED(name)
	if name ~= ADDON then
		return
	end
	if type(ForeverBridgeDB) ~= "table" then
		ForeverBridgeDB = {}
	end
	local db = ForeverBridgeDB
	db.schema = 1
	if type(db.session) ~= "string" or db.session == "" then
		db.session = string.format("%08x%04x", time() % 4294967296, math.random(0, 65535))
	end
	if type(db.next_id) ~= "number" then
		db.next_id = 1
	end
	if type(db.window) ~= "table" then
		db.window = {}
	end
end

driver:SetScript("OnEvent", function(_, event, ...)
	local handler = handlers[event]
	if handler then
		handler(...)
	end
end)
driver:SetScript("OnUpdate", function(_, elapsed)
	FB.Tick(elapsed)
end)
for event in pairs(handlers) do
	pcall(driver.RegisterEvent, driver, event)
end

local HELP = {
	"/fv : ouvrir ou fermer cette fenêtre (raccourci : Options > Raccourcis > AddOns > ForeverBridge ; Échap ferme).",
	"/fv test [1-4] : bande de test, lue par uv run forever bridge selftest --live (une case par pixel par défaut).",
	"/fv poll : chargement d'un emplacement de sonde sans /reload (sonde en jeu B).",
	"/fv fond N : opacité du fond de la fenêtre, de 30 à 100 (opaque).",
	"/fv diag : autotest des fichiers de contrôle, écrit dans la discussion générale.",
}

-- Aide dans la fenêtre ; jamais deux fois de suite (rien d'autre écrit depuis la dernière).
local function Help()
	ui.helped = true
	FB.Open()
	if ui.helpAt and ui.helpAt == ui.count then
		return
	end
	for _, line in ipairs(HELP) do
		FB.Print(line)
	end
	ui.helpAt = ui.count
end

SLASH_FOREVERBRIDGE1 = "/fv"
SLASH_FOREVERBRIDGE2 = "/forever"
SlashCmdList.FOREVERBRIDGE = function(message)
	local command, rest = (message or ""):match("^%s*(%S*)%s*(.-)%s*$")
	command = string.lower(command or "")
	if command == "" then
		FB.Toggle()
		if ui.frame:IsShown() and not ui.helped then
			Help()
		end
	elseif command == "test" then
		FB.Test(rest)
	elseif command == "poll" then
		FB.Poll()
	elseif command == "fond" then
		FB.Open()
		FB.SetBackground(rest)
	elseif command == "diag" then
		FB.Diag()
	else
		Help()
	end
end
