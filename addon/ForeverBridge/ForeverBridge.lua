-- ForeverBridge : pont de conversation de forever-core (P06a, décisions 194 et 212).
-- Blocs A et A2 : fenêtre dédiée (/fv, raccourci, Échap), bande de test (/fv test, une case par pixel par défaut) lue
-- par « forever bridge selftest --live », consultation d'un emplacement de sonde (/fv poll) et autotest des fichiers
-- de contrôle (/fv diag, seule commande qui écrit dans la discussion générale).
-- Seul addon de forever-core qui dessine (décision 194) : la bande n'apparaît que sur demande. Aucune fonction
-- d'action, aucun rechargement de l'interface, aucun abonnement au journal de combat, aucune ouverture automatique.
-- P06b (décision 235) : liens insérés par Maj+clic (accroches hooksecurefunc, jamais de fonction de Blizzard
-- remplacée), messages trop longs montrés en carrousel de parties, zone de collage de l'export SimulationCraft,
-- cartes « À valider » dont les actions demandent un second clic de confirmation.
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
local Message = ForeverBridge_Message

local DEFAULT_CELL = 1 -- côté d'une case de la bande, en pixels physiques (repli de 2 à 4 par /fv test N)
local MAX_CELL = 4
local TEST_DURATION = 120 -- la bande de test se retire seule au bout de deux minutes
local CTL = "Interface\\AddOns\\ForeverBridge\\ctl\\"
local PROBE_ADDON = "ForeverBridge_Probe"
local PROBE2_ADDON = "ForeverBridge_Probe2"
local PREFIX = "|cff33ff99ForeverBridge|r : "
local WINDOW_W, WINDOW_H = 520, 360
local MIN_W, MIN_H = 360, 240
local MAX_LETTERS = 1000 -- question tapée, en caractères (zone de saisie), séquences des liens comprises
local SLOT_PREFIX = "ForeverBridge_S"
local GIVE_UP_POLLS = 3 -- relevés sans accusé avant la boîte d'envoi /reload
local LOW_RESERVE = 10 -- emplacements restants à partir desquels /reload est proposé
local IDLE_POLL = 600 -- relevé au repos, fenêtre ouverte (secondes)
local UPDATE_POLL = 30 -- relevé pendant un passage de forever update, fenêtre ouverte
local UPDATE_POLLS = 20 -- relevés rapprochés au plus par passage
local HISTORY_KEPT = 50
local ARCHIVE_KEPT = 5 -- conversations archivées par « Nouvelle conversation »
-- Calendrier des relevés après un envoi (P06b, forever/bridge/polls.py) : 2, puis de 4 en 4 jusqu'à 60, puis de
-- 10 en 10 jusqu'au plafond (190, au-delà du délai de la conversation du pont).
local SCHEDULE = { 2 }
for t = 4, 60, 4 do
	SCHEDULE[#SCHEDULE + 1] = t
end
for t = 70, 190, 10 do
	SCHEDULE[#SCHEDULE + 1] = t
end
local CAROUSEL = 0.5 -- durée d'affichage d'une partie d'un message trop long
local CONFIRM = 5 -- délai du second clic qui confirme une action d'une carte
local CARDS_W = 360
local EXPLAIN_QUESTION = "Explique cette mise à jour en attente, simplement."
local EXPORT_TOO_LONG = "export trop long : utilisez /simc nobags"
local SEND_W, BAR_H, INPUT_H = 90, 22, 54
local MIN_ALPHA = 0.3 -- fond réglable par /fv fond, de 30 à 100 (opaque par défaut)

BINDING_HEADER_FOREVERBRIDGE = "ForeverBridge"
BINDING_NAME_FOREVERBRIDGE_TOGGLE = "Ouvrir ou fermer la fenêtre"

FB.SCHEDULE = SCHEDULE -- lu par les tests (forever/bridge/polls.py)

local driver = CreateFrame("Frame", "ForeverBridgeDriver", UIParent)
local band
local textures = {}
local run = { nextSlot = 1, unacked = {}, links = {}, unread = 0, cards = {}, carousel = 0 }
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

	local status = f:CreateFontString("ForeverBridgeStatusLine", "OVERLAY", "GameFontHighlightSmall")
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

	local pasteButton = CreateFrame("Button", "ForeverBridgePasteButton", f, "UIPanelButtonTemplate")
	pasteButton:SetSize(96, 20)
	pasteButton:SetPoint("TOPRIGHT", f, "TOPRIGHT", -32, -8)
	pasteButton:SetText("Coller /simc")
	pasteButton:SetScript("OnClick", function()
		FB.OpenPaste()
	end)
	local cardsButton = CreateFrame("Button", "ForeverBridgeCardsButton", f, "UIPanelButtonTemplate")
	cardsButton:SetSize(110, 20)
	cardsButton:SetPoint("RIGHT", pasteButton, "LEFT", -6, 0)
	cardsButton:SetScript("OnClick", function()
		FB.ToggleCards()
	end)
	ui.cardsButton = cardsButton

	local history = CreateFrame("ScrollingMessageFrame", "ForeverBridgeHistory", f)
	history:SetPoint("TOPLEFT", f, "TOPLEFT", 14, -52)
	history:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -14, 16 + INPUT_H + 8 + BAR_H + 8)
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
	history:SetScript("OnHyperlinkClick", function(_, link)
		local n = type(link) == "string" and link:match("^foreverbridge:copy:(%d+)$")
		if n and run.links[tonumber(n)] then
			FB.ShowCopy(run.links[tonumber(n)])
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

	-- Zone de saisie avec « Envoyer » accolé (disposition de wow-ai) : Entrée envoie, Maj+Entrée passe à la ligne.
	local inputBg = CreateFrame("Frame", nil, f, "BackdropTemplate")
	inputBg:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", 14, 16)
	inputBg:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -14 - SEND_W - 6, 16)
	inputBg:SetHeight(INPUT_H)
	if inputBg.SetBackdrop then
		inputBg:SetBackdrop(BACKDROP)
		inputBg:SetBackdropColor(0, 0, 0, 1)
		inputBg:SetBackdropBorderColor(0.5, 0.5, 0.5, 1)
	end
	local scroll = CreateFrame("ScrollFrame", "ForeverBridgeInputScroll", inputBg, "UIPanelScrollFrameTemplate")
	scroll:SetPoint("TOPLEFT", inputBg, "TOPLEFT", 8, -6)
	scroll:SetPoint("BOTTOMRIGHT", inputBg, "BOTTOMRIGHT", -24, 6)
	local input = CreateFrame("EditBox", "ForeverBridgeInput", scroll)
	input:SetMultiLine(true)
	input:SetAutoFocus(false)
	input:SetFontObject(ChatFontNormal)
	input:SetMaxLetters(MAX_LETTERS)
	input:SetSize(400, INPUT_H - 12)
	input:SetScript("OnEnterPressed", function(self)
		if IsShiftKeyDown() then
			self:Insert("\n")
		else
			FB.SendFromInput()
		end
	end)
	input:SetScript("OnEscapePressed", function(self)
		self:ClearFocus()
	end)
	scroll:SetScrollChild(input)
	scroll:HookScript("OnSizeChanged", function(_, width)
		input:SetWidth(width)
	end)
	inputBg:EnableMouse(true)
	inputBg:SetScript("OnMouseDown", function()
		input:SetFocus()
	end)
	ui.input = input

	local send = CreateFrame("Button", "ForeverBridgeSendButton", f, "UIPanelButtonTemplate")
	send:SetSize(SEND_W, 30)
	send:SetPoint("LEFT", inputBg, "RIGHT", 6, 0)
	send:SetText("Envoyer")
	send:SetScript("OnClick", function()
		FB.SendFromInput()
	end)

	local new = CreateFrame("Button", "ForeverBridgeNewButton", f, "UIPanelButtonTemplate")
	new:SetSize(160, BAR_H)
	new:SetPoint("BOTTOMLEFT", inputBg, "TOPLEFT", 0, 8)
	new:SetText("Nouvelle conversation")
	new:SetScript("OnClick", function()
		FB.NewConversation()
	end)
	ui.newButton = new
	ui.buttons = {}
	FB.RefreshButtons()
	FB.RenderHistory()
	FB.UpdateStatus()
	FB.RefreshCards()
	return f
end

-- Zone copiable (lien Talents Forever) : texte sélectionné, Ctrl+C, Échap ferme.
function FB.ShowCopy(text)
	local box = ui.copyBox
	if not box then
		local frame = CreateFrame("Frame", "ForeverBridgeCopy", UIParent, "BackdropTemplate")
		frame:SetSize(420, 60)
		frame:SetFrameStrata("DIALOG")
		frame:SetMovable(true)
		frame:SetClampedToScreen(true)
		frame:EnableMouse(true)
		frame:RegisterForDrag("LeftButton")
		frame:SetScript("OnDragStart", function(self)
			self:StartMoving()
		end)
		frame:SetScript("OnDragStop", function(self)
			self:StopMovingOrSizing()
		end)
		if frame.SetBackdrop then
			frame:SetBackdrop(BACKDROP)
			frame:SetBackdropColor(0.05, 0.05, 0.07, 1)
		end
		tinsert(UISpecialFrames, "ForeverBridgeCopy")
		local label = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
		label:SetPoint("TOPLEFT", frame, "TOPLEFT", 12, -8)
		label:SetText("Ctrl+C pour copier, Échap pour fermer")
		box = CreateFrame("EditBox", "ForeverBridgeCopyBox", frame)
		box:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 12, 10)
		box:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -12, 10)
		box:SetHeight(20)
		box:SetAutoFocus(false)
		box:SetFontObject(ChatFontNormal)
		box:SetScript("OnEscapePressed", function()
			frame:Hide()
		end)
		ui.copyFrame, ui.copyBox = frame, box
	end
	box:SetText(text)
	-- à côté de la fenêtre, à droite (gardé à l'écran) ; déplaçable ensuite
	ui.copyFrame:ClearAllPoints()
	ui.copyFrame:SetPoint("TOPLEFT", ui.frame or UIParent, ui.frame and "TOPRIGHT" or "CENTER", 8, 0)
	ui.copyFrame:Show()
	box:SetFocus()
	box:HighlightText()
end

-- Ligne ajoutée à l'historique de la fenêtre, jamais à la discussion générale.
function FB.Print(text, r, g, b)
	BuildWindow()
	ui.history:AddMessage(text, r, g, b)
	ui.count = (ui.count or 0) + 1
end

-- Ouverture à la demande du joueur seulement (commande ou raccourci), jamais automatique.
function FB.Open()
	local f = BuildWindow()
	if not f:IsShown() then
		run.openedAt = GetTime()
	end
	f:Show()
	FB.RefreshButtons()
	FB.UpdateStatus()
end

function FB.Toggle()
	local f = BuildWindow()
	if f:IsShown() then
		f:Hide()
	else
		FB.Open()
	end
end

-- Texte venu du joueur ou du pont : « | » doublé, les séquences d'interface restent du texte.
local function Escape(text)
	return (tostring(text):gsub("|", "||"))
end

-- Texte écrit par le pont : déjà neutralisé une fois (lua_string) ; ramené au texte brut avant d'être neutralisé ici,
-- pour qu'un « | » s'affiche une seule fois, sans jamais ouvrir de séquence d'interface.
local function Plain(text)
	return (tostring(text or ""):gsub("||", "|"))
end

local function PlayerClass()
	local ok, class = pcall(UnitClassBase, "player")
	if ok and type(class) == "string" then
		return class
	end
	return nil
end

local function HasPlayerTarget()
	local ok1, exists = pcall(UnitExists, "target")
	local ok2, isPlayer = pcall(UnitIsPlayer, "target")
	return ok1 and ok2 and exists == true and isPlayer == true
end

-- Barre de boutons : seulement ceux que le pont a écrits (Status.lua, puis emplacements au bloc E), pour la classe
-- du personnage ; aucun bouton tant que le pont n'a rien écrit.
function FB.RefreshButtons()
	if not ui.buttons then
		return
	end
	for _, button in pairs(ui.buttons) do
		button:Hide()
	end
	local state = type(ForeverBridgeStatus) == "table" and ForeverBridgeStatus or {}
	local entries = run.buttons or (type(state.buttons) == "table" and state.buttons) or {}
	local class = PlayerClass()
	local previous = ui.newButton
	for _, entry in ipairs(entries) do
		local allowed = type(entry) == "table" and type(entry.key) == "string"
		if allowed and type(entry.classes) == "table" then
			allowed = false
			for _, token in ipairs(entry.classes) do
				if token == class then
					allowed = true
				end
			end
		end
		if allowed then
			local button = ui.buttons[entry.key]
			if not button then
				button = CreateFrame("Button", "ForeverBridgeButton_" .. entry.key, ui.frame, "UIPanelButtonTemplate")
				button:SetSize(100, BAR_H)
				ui.buttons[entry.key] = button
			end
			button:SetText(tostring(entry.label or entry.key))
			button:ClearAllPoints()
			button:SetPoint("LEFT", previous, "RIGHT", 6, 0)
			button:SetScript("OnClick", function()
				FB.ClickButton(entry)
			end)
			button:Show()
			previous = button
		end
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
-- Historique, mise en forme des réponses
---------------------------------------------------------------------------

local function History()
	local db = ForeverBridgeDB
	if type(db) ~= "table" then
		return {}
	end
	if type(db.history) ~= "table" then
		db.history = {}
	end
	return db.history
end

local function Remember(entry)
	local history = History()
	history[#history + 1] = entry
	while #history > HISTORY_KEPT do
		table.remove(history, 1)
	end
end

-- Une ligne de réponse : « | » neutralisé d'abord, puis « ## titre », « - élément », « **en évidence** ».
function FB.FormatLine(line)
	local s = Escape(line)
	if s:match("^## ") then
		s = "|cffffd100" .. s:sub(4) .. "|r"
	elseif s:match("^%- ") then
		s = "  • " .. s:sub(3)
	end
	return (s:gsub("%*%*(.-)%*%*", "|cffffffff%1|r"))
end

-- `shown` : texte déjà prêt à l'affichage (liens de la question gardés en liens, Message.Links), sinon neutralisé.
local function PrintUser(text, shown)
	FB.Print("|cff4fa3ffVous|r : " .. (shown or Escape(text)))
end

local function PrintReply(entry)
	if entry.status == "error" then
		FB.Print("|cffff6060Forever|r : " .. Escape(Plain(entry.text or "erreur")))
		return
	end
	FB.Print("|cffffd100Forever|r :")
	for line in (Plain(entry.text) .. "\n"):gmatch("(.-)\n") do
		FB.Print(FB.FormatLine(line), 0.85, 0.85, 0.85)
	end
	if type(entry.provenance) == "string" and entry.provenance ~= "" then
		FB.Print("|cff888888" .. Escape(Plain(entry.provenance)) .. "|r")
	end
	if type(entry.link) == "string" and entry.link ~= "" then
		run.links[#run.links + 1] = entry.link
		FB.Print("|Hforeverbridge:copy:" .. #run.links .. "|h|cff66ccff[Talents Forever]|r|h  (cliquer pour copier le lien)")
	end
end

-- Historique gardé dans ForeverBridgeDB, rendu à la construction de la fenêtre.
function FB.RenderHistory()
	for _, entry in ipairs(History()) do
		if entry.role == "user" then
			PrintUser(entry.text or "", type(entry.shown) == "string" and entry.shown or nil)
		elseif entry.role == "assistant" then
			PrintReply(entry)
		end
	end
end

---------------------------------------------------------------------------
-- Envoi : bande jusqu'à l'accusé, puis consultation de la réserve
---------------------------------------------------------------------------

local function Waiting()
	local db = ForeverBridgeDB
	if type(db.waiting) ~= "table" then
		db.waiting = {}
	end
	return db.waiting
end

local function Outbox()
	local db = ForeverBridgeDB
	if type(db.outbox) ~= "table" then
		db.outbox = {}
	end
	return db.outbox
end

-- Messages qui justifient de consulter la réserve ; la boîte d'envoi ne compte qu'après un /reload (le pont la lit
-- alors), pas juste après l'abandon d'un message sans accusé.
local function AnyWaiting()
	return next(Waiting()) ~= nil or #run.unacked > 0 or (run.afterReload and #Outbox() > 0) or false
end

-- Parties pas encore reçues par le pont, dans l'ordre.
local function Missing(message)
	local missing = {}
	for i = 1, #message.parts do
		if not message.got[i] then
			missing[#missing + 1] = i
		end
	end
	return missing
end

-- Bande du plus récent message sans accusé (ou rien) ; message en parties : celle du carrousel, parmi les manquantes.
local function ShowCurrent()
	local current = run.unacked[#run.unacked]
	if not current then
		FB.HideBand()
		return
	end
	local db = ForeverBridgeDB
	local missing = Missing(current)
	if #missing == 0 then
		FB.HideBand()
		return
	end
	if current.cursor > #missing then
		current.cursor = 1
	end
	local index = missing[current.cursor]
	current.shown[index] = true
	FB.ShowBand(current.id, current.parts[index], tonumber(db.cell) or DEFAULT_CELL)
end

-- Partie suivante du carrousel.
local function TurnCarousel()
	local current = run.unacked[#run.unacked]
	if not current or #current.parts < 2 then
		return
	end
	local missing = Missing(current)
	if #missing > 1 then
		current.cursor = current.cursor % #missing + 1
		ShowCurrent()
	end
end

local function StartSchedule()
	run.scheduleStart = GetTime()
	run.pollIndex = 1
end

-- Envoi d'un message : `opts.flags` (drapeaux en plus), `opts.extra` (contexte en plus : liens), `opts.label` (texte
-- montré dans l'historique à la place du texte envoyé), `opts.tooLong` (message si la charge dépasse la limite).
function FB.Send(text, buttonKey, opts)
	opts = opts or {}
	local db = ForeverBridgeDB
	if type(db) ~= "table" then
		return false
	end
	local id = tonumber(db.next_id) or 1
	local flags = {}
	if run.newConversation then
		flags[#flags + 1] = "n"
	end
	if buttonKey then
		flags[#flags + 1] = "b=" .. buttonKey
	end
	for _, flag in ipairs(opts.flags or {}) do
		flags[#flags + 1] = flag
	end
	local payload, contextText = Message.Build(db.session, id, flags, run.nextSlot, text, opts.extra)
	FB.Open()
	if not payload then
		FB.Print("envoi impossible : " .. tostring(opts.tooLong or contextText))
		return false
	end
	local parts = Message.Fragments(payload, db.session, id)
	run.testLeft = nil
	run.newConversation = nil
	run.afterReload = nil
	db.next_id = id + 1
	run.unacked[#run.unacked + 1] = {
		id = id,
		text = text,
		payload = payload,
		parts = parts,
		got = {},
		shown = {},
		cursor = 1,
		flags = table.concat(flags, ","),
		slot = run.nextSlot,
		context = contextText,
		polls = 0,
	}
	run.carousel = 0
	ShowCurrent()
	StartSchedule()
	local label = opts.label or text
	PrintUser(label, opts.shown)
	Remember({ role = "user", text = label, shown = opts.shown, id = id })
	FB.UpdateStatus()
	return true
end

function FB.SendFromInput()
	local input = ui.input
	if not input then
		return
	end
	local text = (input:GetText() or ""):gsub("^%s+", ""):gsub("%s+$", "")
	if text == "" then
		return
	end
	local question, links, shown = Message.Links(text)
	if FB.Send(question, nil, { extra = { links = links }, shown = links and shown or nil }) then
		input:SetText("")
	end
end

-- Lien inséré par Maj+clic (accroche de ChatEdit_InsertLink et de ChatFrameUtil.InsertLink) : dans notre saisie
-- seulement si elle a le focus ; un même clic vu par les deux accroches n'insère qu'une fois.
function FB.InsertLink(link)
	local input = ui.input
	if type(link) ~= "string" or not input or not input:HasFocus() then
		return
	end
	local now = GetTime()
	if run.lastLink == link and run.lastLinkAt == now then
		return
	end
	run.lastLink, run.lastLinkAt = link, now
	input:Insert(link)
end

local function HookLinks()
	if type(hooksecurefunc) ~= "function" then
		return
	end
	if type(ChatEdit_InsertLink) == "function" then
		pcall(hooksecurefunc, "ChatEdit_InsertLink", FB.InsertLink)
	end
	if type(ChatFrameUtil) == "table" and type(ChatFrameUtil.InsertLink) == "function" then
		pcall(hooksecurefunc, ChatFrameUtil, "InsertLink", FB.InsertLink)
	end
end

---------------------------------------------------------------------------
-- Zone de collage de l'export SimulationCraft (texte de /simc, Ctrl+V)
---------------------------------------------------------------------------

function FB.OpenPaste()
	local frame = ui.pasteFrame
	if not frame then
		frame = CreateFrame("Frame", "ForeverBridgePaste", UIParent, "BackdropTemplate")
		frame:SetSize(460, 320)
		frame:SetFrameStrata("DIALOG")
		frame:SetMovable(true)
		frame:SetClampedToScreen(true)
		frame:EnableMouse(true)
		if frame.SetBackdrop then
			frame:SetBackdrop(BACKDROP)
			frame:SetBackdropColor(0.05, 0.05, 0.07, 1)
		end
		tinsert(UISpecialFrames, "ForeverBridgePaste")
		-- barre de titre : on y glisse la fenêtre (la zone de texte prend la souris partout ailleurs, sonde G)
		local title = CreateFrame("Frame", "ForeverBridgePasteTitle", frame)
		title:SetPoint("TOPLEFT", frame, "TOPLEFT", 4, -4)
		title:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -4, -4)
		title:SetHeight(22)
		title:EnableMouse(true)
		title:RegisterForDrag("LeftButton")
		title:SetScript("OnDragStart", function()
			frame:StartMoving()
		end)
		title:SetScript("OnDragStop", function()
			frame:StopMovingOrSizing()
			local db = ForeverBridgeDB
			if type(db) == "table" then
				local point, _, relPoint, x, y = frame:GetPoint(1)
				db.paste = { point = point, relPoint = relPoint, x = x, y = y }
			end
		end)
		local label = title:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
		label:SetPoint("TOPLEFT", frame, "TOPLEFT", 12, -10)
		label:SetPoint("RIGHT", frame, "RIGHT", -12, 0)
		label:SetJustifyH("LEFT")
		label:SetText("Export SimulationCraft (glisser ce titre pour déplacer) : /simc, Ctrl+C, puis Ctrl+V ici.")
		local scroll = CreateFrame("ScrollFrame", "ForeverBridgePasteScroll", frame, "UIPanelScrollFrameTemplate")
		scroll:SetPoint("TOPLEFT", frame, "TOPLEFT", 12, -30)
		scroll:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -30, 44)
		local box = CreateFrame("EditBox", "ForeverBridgePasteBox", scroll)
		box:SetMultiLine(true)
		box:SetAutoFocus(false)
		box:SetFontObject(ChatFontNormal)
		box:SetMaxLetters(0)
		box:SetSize(410, 240)
		box:SetScript("OnEscapePressed", function()
			frame:Hide()
		end)
		scroll:SetScrollChild(box)
		local send = CreateFrame("Button", "ForeverBridgePasteSend", frame, "UIPanelButtonTemplate")
		send:SetSize(140, 24)
		send:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -12, 12)
		send:SetText("Envoyer l'export")
		send:SetScript("OnClick", function()
			FB.SendPaste()
		end)
		local cancel = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
		cancel:SetSize(90, 24)
		cancel:SetPoint("RIGHT", send, "LEFT", -8, 0)
		cancel:SetText("Fermer")
		cancel:SetScript("OnClick", function()
			frame:Hide()
		end)
		ui.pasteFrame, ui.pasteBox = frame, box
	end
	frame:ClearAllPoints()
	local saved = type(ForeverBridgeDB) == "table" and ForeverBridgeDB.paste
	if type(saved) == "table" and type(saved.point) == "string" then
		frame:SetPoint(saved.point, UIParent, saved.relPoint or saved.point, tonumber(saved.x) or 0, tonumber(saved.y) or 0)
	else
		frame:SetPoint("CENTER", UIParent, "CENTER", 0, 0)
	end
	frame:Show()
	ui.pasteBox:SetFocus()
end

-- Envoi de l'export collé : drapeau k=simc, sans question ; refusé au-delà de la taille d'un message.
function FB.SendPaste()
	local box = ui.pasteBox
	if not box then
		return
	end
	local text = (box:GetText() or ""):gsub("^%s+", ""):gsub("%s+$", "")
	if text == "" then
		FB.Open()
		FB.Print("export vide : collez le texte de /simc (Ctrl+V), puis Envoyer l'export.")
		return
	end
	if #text > Message.MAX_MESSAGE then
		FB.Open()
		FB.Print(EXPORT_TOO_LONG)
		return
	end
	local lines = select(2, text:gsub("\n", "")) + 1
	local label = "export SimulationCraft (" .. lines .. " lignes)"
	if FB.Send(text, nil, { flags = { "k=simc" }, label = label, tooLong = EXPORT_TOO_LONG }) then
		box:SetText("")
		ui.pasteFrame:Hide()
	end
end

---------------------------------------------------------------------------
-- Cartes « À valider » (écrites par le pont : attentes, propositions de profil, carte de test)
---------------------------------------------------------------------------

function FB.RefreshCards()
	local button = ui.cardsButton
	if not button then
		return
	end
	local count = #run.cards
	button:SetText("À valider (" .. count .. ")")
	if count > 0 then
		button:Show()
	else
		button:Hide()
		if ui.cardsFrame then
			ui.cardsFrame:Hide()
		end
	end
	if ui.cardsFrame and ui.cardsFrame:IsShown() then
		FB.RenderCards()
	end
end

function FB.ToggleCards()
	BuildWindow()
	local frame = ui.cardsFrame
	if frame and frame:IsShown() then
		frame:Hide()
		return
	end
	FB.RenderCards()
end

local function CardText(card)
	local lines = { "|cffffd100" .. Escape(Plain(card.title or card.id or "")) .. "|r" }
	for _, line in ipairs(type(card.lines) == "table" and card.lines or {}) do
		lines[#lines + 1] = Escape(Plain(line))
	end
	return table.concat(lines, "\n")
end

local function CardPlain(card)
	local lines = { Plain(card.title or card.id or "") }
	for _, line in ipairs(type(card.lines) == "table" and card.lines or {}) do
		lines[#lines + 1] = Plain(line)
	end
	return table.concat(lines, "\n")
end

function FB.RenderCards()
	BuildWindow()
	local frame = ui.cardsFrame
	if not frame then
		frame = CreateFrame("Frame", "ForeverBridgeCards", UIParent, "BackdropTemplate")
		frame:SetFrameStrata("DIALOG")
		frame:SetClampedToScreen(true)
		frame:EnableMouse(true)
		if frame.SetBackdrop then
			frame:SetBackdrop(BACKDROP)
			frame:SetBackdropColor(0.05, 0.05, 0.07, 1)
		end
		tinsert(UISpecialFrames, "ForeverBridgeCards")
		ui.cardsFrame, ui.cardTexts, ui.cardButtons = frame, {}, {}
	end
	for _, widget in pairs(ui.cardButtons) do
		widget:Hide()
	end
	for _, text in pairs(ui.cardTexts) do
		text:Hide()
	end
	local y = -10
	for i, card in ipairs(run.cards) do
		local text = ui.cardTexts[i]
		if not text then
			text = frame:CreateFontString("ForeverBridgeCard" .. i .. "Text", "OVERLAY", "GameFontHighlightSmall")
			text:SetJustifyH("LEFT")
			ui.cardTexts[i] = text
		end
		text:ClearAllPoints()
		text:SetPoint("TOPLEFT", frame, "TOPLEFT", 12, y)
		text:SetWidth(CARDS_W - 24)
		text:SetText(CardText(card))
		text:Show()
		local count = 1 + (type(card.lines) == "table" and #card.lines or 0)
		y = y - count * 14 - 4
		local previous
		for _, entry in ipairs(type(card.buttons) == "table" and card.buttons or {}) do
			if type(entry) == "table" and type(entry.key) == "string" then
				local name = "ForeverBridgeCard" .. i .. "_" .. entry.key
				local widget = ui.cardButtons[name]
				if not widget then
					widget = CreateFrame("Button", name, frame, "UIPanelButtonTemplate")
					widget:SetSize(96, BAR_H)
					ui.cardButtons[name] = widget
				end
				widget:ClearAllPoints()
				if previous then
					widget:SetPoint("LEFT", previous, "RIGHT", 6, 0)
				else
					widget:SetPoint("TOPLEFT", frame, "TOPLEFT", 12, y)
				end
				widget:SetText(tostring(entry.label or entry.key))
				widget:SetScript("OnClick", function()
					FB.ClickCard(card, entry, widget)
				end)
				widget:Show()
				previous = widget
			end
		end
		y = y - BAR_H - 12
	end
	frame:SetSize(CARDS_W, -y + 4)
	frame:ClearAllPoints()
	frame:SetPoint("TOPLEFT", ui.frame, "TOPRIGHT", 8, 0)
	frame:Show()
end

-- Clic sur un bouton de carte : une action demande un second clic dans le délai (« Confirmer »), puis part en
-- a=<action> sans texte ; « Expliquer » pose la question fixe avec le texte de la carte (b=explain).
function FB.ClickCard(card, entry, widget)
	if entry.explain then
		FB.Send(EXPLAIN_QUESTION .. "\n" .. CardPlain(card), "explain", { label = "Expliquer : " .. Plain(card.title or "") })
		return
	end
	if type(entry.action) ~= "string" or entry.action == "" then
		return
	end
	local pending = run.confirm
	if entry.confirm and not (pending and pending.widget == widget and GetTime() - pending.at < CONFIRM) then
		if pending and pending.widget ~= widget then
			pending.widget:SetText(pending.label)
		end
		run.confirm = { widget = widget, label = tostring(entry.label or entry.key), at = GetTime() }
		widget:SetText("Confirmer")
		return
	end
	run.confirm = nil
	widget:SetText(tostring(entry.label or entry.key))
	FB.Send("", nil, { flags = { "a=" .. entry.action }, label = tostring(entry.label or entry.key) .. " : "
		.. Plain(card.title or card.id or "") })
end

local function TickConfirm()
	local pending = run.confirm
	if pending and GetTime() - pending.at >= CONFIRM then
		pending.widget:SetText(pending.label)
		run.confirm = nil
	end
end

-- Nouvelle conversation : la fenêtre est vidée, l'historique part dans l'archive (cinq dernières conversations).
function FB.NewConversation()
	run.newConversation = true
	local db = ForeverBridgeDB
	if type(db) == "table" and type(db.history) == "table" and #db.history > 0 then
		if type(db.archive) ~= "table" then
			db.archive = {}
		end
		table.insert(db.archive, 1, db.history)
		while #db.archive > ARCHIVE_KEPT do
			table.remove(db.archive)
		end
		db.history = {}
	end
	run.links = {}
	if ui.history then
		ui.history:Clear()
	end
	FB.Print("|cff888888— Nouvelle conversation : le prochain message repart de zéro —|r")
end

-- Message sans accusé après trois relevés : boîte d'envoi, lue par le pont au prochain /reload.
local function GiveUp(message)
	local outbox = Outbox()
	outbox[#outbox + 1] = {
		id = message.id,
		text = message.text,
		flags = message.flags,
		slot = message.slot,
		context = message.context,
	}
	FB.Print("|cffff6060Non reçu|r : pont injoignable, message n° " .. message.id .. " gardé pour le prochain /reload "
		.. "(lancez uv run forever bridge start, puis tapez /reload).")
end

local function RemoveFromOutbox(id)
	local outbox = Outbox()
	for i = #outbox, 1, -1 do
		if type(outbox[i]) == "table" and outbox[i].id == id then
			table.remove(outbox, i)
		end
	end
end

local function Remaining()
	if not run.slots then
		return nil
	end
	return run.slots - (run.nextSlot - 1)
end

-- Ligne d'état et voyant : données, pont vu, réponse en cours, réserve.
function FB.UpdateStatus()
	if not ui.status then
		return
	end
	local parts = {}
	local status = type(run.status) == "table" and run.status or nil
	parts[#parts + 1] = status and type(status.line) == "string" and Escape(Plain(status.line)) or "état des données inconnu"
	local seen = tonumber(run.bridgeSeen)
	local icon = "Offline"
	if seen and seen > 0 then
		local minutes = math.max(0, math.floor((time() - seen) / 60))
		parts[#parts + 1] = minutes == 0 and "pont vu à l'instant" or ("pont vu il y a " .. minutes .. " min")
		icon = minutes < 12 and "Online" or (minutes < 22 and "Away" or "Offline")
	else
		parts[#parts + 1] = "pont pas encore vu"
	end
	if #run.unacked > 0 then
		local current = run.unacked[#run.unacked]
		local sending = "envoi du message n° " .. current.id
		if #current.parts > 1 then
			local got = 0
			for _ in pairs(current.got) do
				got = got + 1
			end
			sending = sending .. " (" .. #current.parts .. " parties, " .. got .. " reçue(s) par le pont)"
		end
		parts[#parts + 1] = sending
	elseif next(Waiting()) ~= nil and run.scheduleStart then
		local seconds = math.floor(GetTime() - run.scheduleStart)
		local dots = string.rep(".", math.floor(GetTime() * 2) % 3 + 1)
		parts[#parts + 1] = "réponse en cours" .. dots .. " " .. seconds .. " s"
	end
	if run.exhausted then
		parts[#parts + 1] = "réserve vide : tapez /reload"
	else
		local remaining = Remaining()
		if remaining and remaining <= LOW_RESERVE then
			parts[#parts + 1] = "réserve : " .. remaining .. " emplacements restants, tapez /reload quand vous voulez"
		end
	end
	if run.unread > 0 and ui.frame and ui.frame:IsShown() then
		run.unread = 0
	end
	ui.status:SetText(table.concat(parts, " · "))
	if ui.dot then
		ui.dot:SetTexture("Interface\\FriendsFrame\\StatusIcon-" .. icon)
	end
end

-- Contenu d'un emplacement ou d'Inbox.lua : état, boutons, accusés et réponses de cette session.
function FB.ApplySlot(slot)
	if type(slot) ~= "table" then
		return
	end
	local db = ForeverBridgeDB
	-- un fichier d'attente (jamais publié par le pont : now = 0) n'apporte ni état ni boutons
	local published = tonumber(slot.now) and tonumber(slot.now) > 0
	if published then
		run.bridgeSeen = tonumber(slot.now)
		if type(slot.status) == "table" then
			run.status = slot.status
			FB.CheckUpdate(slot.status)
			run.slots = tonumber(slot.status.slots) or run.slots
		end
		if type(slot.buttons) == "table" then
			run.buttons = slot.buttons
			FB.RefreshButtons()
		end
	end
	if published and type(slot.cards) == "table" then
		run.cards = slot.cards
		FB.RefreshCards()
	end
	local waiting = Waiting()
	for _, reply in ipairs(type(slot.replies) == "table" and slot.replies or {}) do
		if type(reply) == "table" and reply.session == db.session and type(reply.id) == "number"
			and reply.status == "parts" then
			-- parties reçues par le pont : le carrousel ne montre plus que les manquantes ; ce n'est pas un accusé
			for _, message in ipairs(run.unacked) do
				if message.id == reply.id and type(reply.got) == "table" then
					local before = 0
					for _ in pairs(message.got) do
						before = before + 1
					end
					local got = {}
					local count = 0
					for _, index in ipairs(reply.got) do
						if type(index) == "number" and not got[index] then
							got[index] = true
							count = count + 1
						end
					end
					if count > before then
						message.got = got
						message.cursor = 1
						message.progressed = true
					end
				end
			end
		elseif type(reply) == "table" and reply.session == db.session and type(reply.id) == "number" then
			for i = #run.unacked, 1, -1 do
				if run.unacked[i].id == reply.id then
					table.remove(run.unacked, i)
					waiting[reply.id] = true
				end
			end
			for _, entry in ipairs(Outbox()) do
				if type(entry) == "table" and entry.id == reply.id then
					waiting[reply.id] = true
				end
			end
			if waiting[reply.id] and (reply.status == "done" or reply.status == "error") then
				waiting[reply.id] = nil
				RemoveFromOutbox(reply.id)
				local entry = {
					role = "assistant",
					id = reply.id,
					status = reply.status,
					text = reply.text,
					provenance = reply.provenance,
					link = reply.link,
				}
				PrintReply(entry)
				Remember(entry)
				if not (ui.frame and ui.frame:IsShown()) then
					run.unread = run.unread + 1
				end
			end
		end
	end
	ShowCurrent()
	if not AnyWaiting() then
		run.scheduleStart = nil
	end
	FB.UpdateStatus()
end

-- Charge l'emplacement suivant de la réserve (une fois par session d'interface) et applique son contenu.
function FB.PollSlot()
	if run.exhausted then
		return
	end
	local index = run.nextSlot
	run.nextSlot = index + 1
	run.lastPoll = GetTime()
	ForeverBridgeSlot = nil
	local loaded, reason = LoadOnDemand(string.format("%s%03d", SLOT_PREFIX, index))
	if not loaded and (reason == "MISSING" or (run.slots and index > run.slots)) then
		run.exhausted = true
		run.scheduleStart = nil
		for _, message in ipairs(run.unacked) do
			GiveUp(message)
		end
		run.unacked = {}
		FB.HideBand()
		if next(Waiting()) ~= nil then
			FB.Print("|cffffd100Plus d'emplacement libre|r : réserve vide, la réponse arrivera au prochain /reload "
				.. "(tapez /reload quand vous voulez).")
		end
		FB.UpdateStatus()
		return
	end
	if loaded then
		FB.ApplySlot(ForeverBridgeSlot)
	end
	local current = run.unacked[#run.unacked]
	if current then
		-- un relevé qui apporte une partie nouvelle ne compte pas pour l'abandon, ni un relevé fait avant que le
		-- carrousel ait montré chaque partie au moins une fois (message long)
		local shownAll = true
		for i = 1, #current.parts do
			shownAll = shownAll and (current.shown[i] or current.got[i]) and true
		end
		if current.progressed then
			current.progressed = nil
			current.polls = 0
		elseif not shownAll then
			current.polls = 0
		else
			current.polls = current.polls + 1
		end
		if current.polls >= GIVE_UP_POLLS then
			table.remove(run.unacked)
			GiveUp(current)
			ShowCurrent()
			if not AnyWaiting() then
				run.scheduleStart = nil
			end
		end
	end
	FB.UpdateStatus()
end

-- Relevés au calendrier après un envoi ; au repos, un relevé toutes les dix minutes fenêtre ouverte.
local function TickPolls()
	local now = GetTime()
	if run.scheduleStart then
		local elapsed = now - run.scheduleStart
		while run.scheduleStart and SCHEDULE[run.pollIndex] and elapsed >= SCHEDULE[run.pollIndex] - 1e-6 do
			run.pollIndex = run.pollIndex + 1
			FB.PollSlot()
		end
		if run.scheduleStart and not SCHEDULE[run.pollIndex] then
			run.scheduleStart = nil
			if next(Waiting()) ~= nil then
				FB.Print("Réponse toujours en cours : tapez /reload plus tard pour la récupérer.")
			end
			FB.UpdateStatus()
		end
	elseif ui.frame and ui.frame:IsShown() and not run.exhausted then
		local since = math.max(run.lastPoll or 0, run.openedAt or now)
		local update = type(run.status) == "table" and type(run.status.update) == "table" and run.status.update or {}
		if update.running and (run.updatePolls or 0) < UPDATE_POLLS then
			-- passage de forever update en cours : relevés rapprochés pour montrer sa fin
			if now - since >= UPDATE_POLL then
				run.updatePolls = (run.updatePolls or 0) + 1
				FB.PollSlot()
			end
		elseif now - since >= IDLE_POLL then
			FB.PollSlot()
		end
	end
end

-- Fin d'un passage de forever update : une ligne dans l'historique, une seule fois par passage terminé ; un passage
-- déjà fini à la connexion n'est pas annoncé (aucun passage vu en cours, aucun passage déjà noté).
function FB.CheckUpdate(status)
	local update = type(status) == "table" and type(status.update) == "table" and status.update or nil
	if not update then
		return
	end
	local db = ForeverBridgeDB
	if update.running then
		run.sawRunning = true
		return
	end
	run.updatePolls = 0
	local last = type(update.last) == "table" and update.last or nil
	local finished = last and last.finished_at
	if type(finished) ~= "string" or type(db) ~= "table" or db.update_seen == finished then
		return
	end
	local announce = run.sawRunning or db.update_seen ~= nil
	db.update_seen = finished
	run.sawRunning = nil
	if announce then
		FB.Print("Mise à jour terminée : " .. tostring(tonumber(last.written) or 0) .. " écrit(s), "
			.. tostring(tonumber(last.approvable) or 0) .. " à valider")
	end
end

function FB.ClickButton(entry)
	if entry.target and not HasPlayerTarget() then
		FB.Print(tostring(entry.label or "PvP") .. " : prenez un joueur en cible, puis cliquez à nouveau.")
		return
	end
	if type(entry.action) == "string" and entry.action ~= "" then
		-- bouton d'action (Mettre à jour) : a=<action> sans texte, traité par le pont sans conversation
		FB.Send("", nil, { flags = { "a=" .. entry.action }, label = tostring(entry.label or entry.key) })
		return
	end
	local class = PlayerClass()
	local question = type(entry.questions) == "table" and class and entry.questions[class] or entry.question
	if type(question) == "string" and question ~= "" then
		FB.Send(question, entry.key)
	end
end

---------------------------------------------------------------------------
-- Bande de test (/fv test [taille de case])
---------------------------------------------------------------------------

function FB.StopTest()
	run.testLeft = nil
	ShowCurrent()
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
	TickPolls()
	TickConfirm()
	run.carousel = (run.carousel or 0) + elapsed
	if run.carousel >= CAROUSEL - 1e-6 then
		run.carousel = 0
		TurnCarousel()
	end
	run.statusClock = (run.statusClock or 0) + elapsed
	if run.statusClock >= 0.5 then
		run.statusClock = 0
		if run.scheduleStart then
			FB.UpdateStatus()
		end
	end
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

-- Connexion et /reload : état et boutons de Status.lua, réponses arrivées dans Inbox.lua (chemin de secours).
function handlers.PLAYER_ENTERING_WORLD()
	if type(ForeverBridgeDB) ~= "table" then
		return
	end
	if type(ForeverBridgeStatus) == "table" then
		if type(ForeverBridgeStatus.status) == "table" and next(ForeverBridgeStatus.status) ~= nil then
			run.status = ForeverBridgeStatus.status
			FB.CheckUpdate(ForeverBridgeStatus.status)
			run.slots = tonumber(ForeverBridgeStatus.status.slots) or run.slots
		end
		if tonumber(ForeverBridgeStatus.now) and tonumber(ForeverBridgeStatus.now) > 0 then
			run.bridgeSeen = tonumber(ForeverBridgeStatus.now)
			if type(ForeverBridgeStatus.cards) == "table" then
				run.cards = ForeverBridgeStatus.cards
				FB.RefreshCards()
			end
		end
	end
	FB.ApplySlot(ForeverBridgeSlot)
	-- secours /reload : la boîte d'envoi vient d'être écrite, le pont la lit ; consultation relancée
	if (next(Waiting()) ~= nil or #Outbox() > 0) and not run.scheduleStart then
		run.afterReload = true
		StartSchedule()
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
HookLinks()

local HELP = {
	"/fv : ouvrir ou fermer cette fenêtre (raccourci : Options > Raccourcis > AddOns > ForeverBridge ; Échap ferme).",
	"/fv test [1-4] : bande de test, lue par uv run forever bridge selftest --live (une case par pixel par défaut).",
	"/fv poll : chargement d'un emplacement de sonde sans /reload (sonde en jeu B).",
	"/fv fond N : opacité du fond de la fenêtre, de 30 à 100 (opaque).",
	"Maj+clic sur un objet, un sort ou une quête pendant la saisie : le lien et son infobulle partent avec la question.",
	"Coller /simc : colle l'export de l'addon SimulationCraft (/simc, Ctrl+C, Ctrl+V), envoyé au pont sans question.",
	"/fv case N : taille de case de la bande des messages, 1 (défaut) à 4 pixels, si le pont ne la lit pas.",
	"/fv diag : autotest des fichiers de contrôle, écrit dans la discussion générale.",
}

-- Taille de case de la bande des messages, gardée dans ForeverBridgeDB.cell.
function FB.SetCell(value)
	local cell = tonumber(value)
	if not (cell and cell == math.floor(cell) and cell >= 1 and cell <= MAX_CELL) then
		FB.Print("case : /fv case suivi de 1, 2, 3 ou 4.")
		return
	end
	if type(ForeverBridgeDB) == "table" then
		ForeverBridgeDB.cell = cell
	end
	FB.Print("case de la bande des messages : " .. cell .. " pixel(s).")
end

-- Aide dans la fenêtre ; jamais deux fois de suite (rien d'autre écrit depuis la dernière).
local function Help()
	ui.helped = true
	if type(ForeverBridgeDB) == "table" then
		ForeverBridgeDB.help_shown = true -- aide montrée une fois, puis seulement par /fv aide
	end
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
		local db = ForeverBridgeDB
		if ui.frame:IsShown() and not ui.helped and not (type(db) == "table" and db.help_shown) then
			Help()
		end
	elseif command == "test" then
		FB.Test(rest)
	elseif command == "poll" then
		FB.Poll()
	elseif command == "fond" then
		FB.Open()
		FB.SetBackground(rest)
	elseif command == "case" then
		FB.Open()
		FB.SetCell(rest)
	elseif command == "diag" then
		FB.Diag()
	else
		Help()
	end
end
