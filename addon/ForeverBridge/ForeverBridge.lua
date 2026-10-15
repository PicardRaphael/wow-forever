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
local WINDOW_W, WINDOW_H = 520, 360 -- ancienne fenêtre (/fv classique)
local MIN_W, MIN_H = 360, 240
-- CJ1, bloc 6a (décision 280) : nouvelle fenêtre, barre latérale à gauche
local NEW_W, NEW_H = 640, 440
local NEW_MIN_W, NEW_MIN_H = 520, 380
local NAV_W = 150 -- largeur de la barre latérale, marges comprises
local MENU_STEP = 26 -- hauteur d'une ligne du menu « Plus »
local MAX_LETTERS = 1000 -- question tapée, en caractères (zone de saisie), séquences des liens comprises
local SLOT_PREFIX = "ForeverBridge_S"
local GIVE_UP_POLLS = 3 -- relevés sans accusé avant la boîte d'envoi /reload
local LOW_RESERVE = 10 -- emplacements restants à partir desquels /reload est proposé
local IDLE_POLL = 600 -- relevé au repos, fenêtre ouverte (secondes)
-- Relevés pendant une mise à jour, fenêtre ouverte (décision 240) : rapprochés (UPDATE_POLL) pour les premiers,
-- puis espacés (UPDATE_POLL_SLOW) jusqu'au plafond (une heure de passage), puis le relevé au repos.
local UPDATE_POLL = 30
local UPDATE_POLLS = 20
local UPDATE_POLL_SLOW = 60
local UPDATE_POLLS_MAX = 70
local UPDATE_CLICK_WAIT = 180 -- après « Mettre à jour », délai pour voir le passage commencer
local PANEL_BUTTON_MIN = 64 -- largeur minimale d'un bouton de carte
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
-- Conversation « addons » (délai de 600 au pont) : le même calendrier, puis de 30 en 30 jusqu'à 610.
local SCHEDULE_ADDONS = {}
for i, t in ipairs(SCHEDULE) do
	SCHEDULE_ADDONS[i] = t
end
for t = 220, 610, 30 do
	SCHEDULE_ADDONS[#SCHEDULE_ADDONS + 1] = t
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
local run = { nextSlot = 1, unacked = {}, links = {}, unread = 0, cards = {}, carousel = 0, conv = "game" }
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

-- Ancienne fenêtre gardée derrière /fv classique (décision 280), lue une fois à la construction de la fenêtre.
local function Classic()
	return type(ForeverBridgeDB) == "table" and ForeverBridgeDB.classic == true
end

-- Tailles par défaut et minimales de la disposition choisie.
local function Sizes()
	if ui.classic then
		return WINDOW_W, WINDOW_H, MIN_W, MIN_H
	end
	return NEW_W, NEW_H, NEW_MIN_W, NEW_MIN_H
end

-- Marge gauche du contenu : après la barre latérale, sauf dans l'ancienne fenêtre.
local function ContentLeft()
	return ui.classic and 14 or NAV_W
end

-- Largeur du contenu (historique, rangée des réponses, écrans), calculée sur la fenêtre.
function FB.ContentWidth()
	local f = ui.frame
	return f and math.max(0, f:GetWidth() - ContentLeft() - 14) or 0
end

local function RestoreGeometry(f)
	local state = WindowState() or {}
	local defaultW, defaultH, minW, minH = Sizes()
	local width = tonumber(state.width) or defaultW
	local height = tonumber(state.height) or defaultH
	f:SetSize(math.max(width, minW), math.max(height, minH))
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
	ui.classic = Classic()
	local _, _, minW, minH = Sizes()
	local f = CreateFrame("Frame", "ForeverBridgeWindow", UIParent, "BackdropTemplate")
	ui.frame = f
	f:SetFrameStrata("DIALOG")
	f:SetMovable(true)
	f:SetResizable(true)
	f:SetClampedToScreen(true)
	if not (f.SetResizeBounds and pcall(f.SetResizeBounds, f, minW, minH)) and f.SetMinResize then
		pcall(f.SetMinResize, f, minW, minH)
	end
	-- largeur changée : rangée des réponses, menu et écrans replacés (jamais de chevauchement)
	f:SetScript("OnSizeChanged", function()
		FB.LayoutAnswers()
		if FB.LayoutScreens then
			FB.LayoutScreens()
		end
	end)
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

	-- Onglets « Jeu » et « Addons » (P06b) : Addons seulement quand le pont publie une conversation configurée.
	local tabGame = CreateFrame("Button", "ForeverBridgeTabGame", f, "UIPanelButtonTemplate")
	tabGame:SetSize(60, 20)
	tabGame:SetPoint("LEFT", title, "RIGHT", 12, 0)
	tabGame:SetText("Jeu")
	tabGame:SetScript("OnClick", function()
		FB.SwitchConversation("game")
	end)
	local tabAddons = CreateFrame("Button", "ForeverBridgeTabAddons", f, "UIPanelButtonTemplate")
	tabAddons:SetSize(150, 20)
	tabAddons:SetPoint("LEFT", tabGame, "RIGHT", 4, 0)
	tabAddons:SetScript("OnClick", function()
		FB.SwitchConversation("addons")
	end)
	ui.tabGame, ui.tabAddons = tabGame, tabAddons

	-- Nouvelle fenêtre : menu « Plus » (décision 280) ; les actions secondaires y gardent leur nom et leur rôle.
	local holder = f
	if not ui.classic then
		local more = CreateFrame("Frame", "ForeverBridgeMore", f, "BackdropTemplate")
		more:SetFrameStrata("DIALOG")
		more:SetFrameLevel(50)
		if more.SetBackdrop then
			more:SetBackdrop(BACKDROP)
			more:SetBackdropColor(0.08, 0.08, 0.1, 1)
		end
		more:EnableMouse(true)
		more:Hide()
		ui.more = more
		holder = more
	end

	local pasteButton = CreateFrame("Button", "ForeverBridgePasteButton", holder, "UIPanelButtonTemplate")
	pasteButton:SetSize(96, 20)
	if ui.classic then
		pasteButton:SetPoint("TOPRIGHT", f, "TOPRIGHT", -32, -8)
	end
	pasteButton:SetText("Coller /simc")
	pasteButton:SetScript("OnClick", function()
		FB.HideMore()
		FB.TogglePaste()
	end)
	local cardsButton = CreateFrame("Button", "ForeverBridgeCardsButton", holder, "UIPanelButtonTemplate")
	cardsButton:SetSize(110, 20)
	if ui.classic then
		cardsButton:SetPoint("RIGHT", pasteButton, "LEFT", -6, 0)
	end
	cardsButton:SetScript("OnClick", function()
		FB.HideMore()
		FB.ToggleCards()
	end)
	ui.cardsButton = cardsButton

	local history = CreateFrame("ScrollingMessageFrame", "ForeverBridgeHistory", f)
	history:SetPoint("TOPLEFT", f, "TOPLEFT", ContentLeft(), -52)
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
	inputBg:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", ContentLeft(), 16)
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

	local new = CreateFrame("Button", "ForeverBridgeNewButton", holder, "UIPanelButtonTemplate")
	new:SetSize(160, BAR_H)
	new:SetText("Nouvelle conversation")
	new:SetScript("OnClick", function()
		FB.HideMore()
		FB.NewConversation()
	end)
	ui.newButton = new
	ui.chatWidgets = { history, inputBg, send }
	if ui.classic then
		new:SetPoint("BOTTOMLEFT", inputBg, "TOPLEFT", 0, 8)
		ui.chatWidgets[#ui.chatWidgets + 1] = new
	else
		-- barre d'actions courte : « Envoyer » à droite de la saisie, « Plus » au-dessus (au plus trois actions)
		local moreButton = CreateFrame("Button", "ForeverBridgeMoreButton", f, "UIPanelButtonTemplate")
		moreButton:SetSize(80, BAR_H)
		moreButton:SetPoint("BOTTOMLEFT", inputBg, "TOPLEFT", 0, 8)
		moreButton:SetText("Plus...")
		moreButton:SetScript("OnClick", function()
			FB.ToggleMore()
		end)
		ui.moreButton = moreButton
		ui.more:SetPoint("BOTTOMLEFT", moreButton, "TOPLEFT", 0, 4)
		ui.chatWidgets[#ui.chatWidgets + 1] = moreButton
	end
	ui.buttons = {}
	FB.RefreshButtons()
	FB.RenderHistory()
	FB.UpdateStatus()
	FB.RefreshCards()
	FB.RefreshTabs()
	if not ui.classic and FB.BuildScreens then
		FB.BuildScreens(f)
	end
	return f
end

-- Menu « Plus » : une action par ligne, largeur de la plus longue (libellés mesurés), fermé après chaque action.
local function MenuWidth(label)
	local letters = #(tostring(label or ""):gsub("[\128-\191]", ""))
	return letters * 7 + 24
end

function FB.LayoutMore()
	local more = ui.more
	if not more then
		return
	end
	local items = { ui.newButton, _G.ForeverBridgePasteButton, ui.cardsButton }
	for _, key in ipairs(ui.buttonOrder or {}) do
		items[#items + 1] = ui.buttons[key]
	end
	local width, row = 160, 0
	for _, item in ipairs(items) do
		if item and item:IsShown() then
			width = math.max(width, MenuWidth(item:GetText()))
		end
	end
	for _, item in ipairs(items) do
		if item and item:IsShown() then
			item:ClearAllPoints()
			item:SetPoint("TOPLEFT", more, "TOPLEFT", 6, -6 - row * MENU_STEP)
			item:SetSize(width, BAR_H)
			row = row + 1
		end
	end
	more:SetSize(width + 12, row * MENU_STEP + 8)
end

function FB.ToggleMore()
	if not ui.more then
		return
	end
	if ui.more:IsShown() then
		ui.more:Hide()
	else
		FB.LayoutMore()
		ui.more:Show()
	end
end

function FB.HideMore()
	if ui.more then
		ui.more:Hide()
	end
end

-- Écran « Chat » montré ou caché (les autres écrans viennent de Screens.lua).
function FB.ShowChat(shown)
	for _, widget in ipairs(ui.chatWidgets or {}) do
		widget:SetShown(shown)
	end
	if ui.answers then
		ui.answers:SetShown(shown and run.answering ~= nil)
	end
	if not shown then
		FB.HideMore()
	end
end

-- Onglets visibles selon l'état publié par le pont ; l'onglet courant est grisé.
function FB.RefreshTabs()
	if not ui.tabAddons then
		return
	end
	local addons = type(run.status) == "table" and type(run.status.addons) == "table" and run.status.addons or nil
	if addons and addons.configured then
		local label = tostring(addons.name or "?"):gsub("||", "|"):gsub("|", "||")
		ui.tabAddons:SetText("Addons (" .. label .. ")")
		ui.tabGame:Show()
		ui.tabAddons:Show()
	else
		ui.tabGame:Hide()
		ui.tabAddons:Hide()
		if run.conv == "addons" then
			FB.SwitchConversation("game")
		end
	end
	if ui.tabGame.Enable then
		if run.conv == "addons" then
			ui.tabGame:Enable()
			ui.tabAddons:Disable()
		else
			ui.tabGame:Disable()
			ui.tabAddons:Enable()
		end
	end
end

-- Changement de conversation : la fenêtre montre l'historique de la conversation choisie.
function FB.SwitchConversation(name)
	run.conv = name == "addons" and "addons" or "game"
	run.links = {}
	if ui.history then
		ui.history:Clear()
		FB.RenderHistory()
	end
	FB.RefreshTabs()
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
	ui.buttonOrder = {}
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
				local parent = ui.more or ui.frame
				button = CreateFrame("Button", "ForeverBridgeButton_" .. entry.key, parent, "UIPanelButtonTemplate")
				button:SetSize(100, BAR_H)
				ui.buttons[entry.key] = button
			end
			button:SetText(tostring(entry.label or entry.key))
			if not ui.more then
				button:ClearAllPoints()
				button:SetPoint("LEFT", previous, "RIGHT", 6, 0)
			end
			button:SetScript("OnClick", function()
				FB.HideMore()
				FB.ClickButton(entry)
			end)
			button:Show()
			previous = button
			ui.buttonOrder[#ui.buttonOrder + 1] = entry.key
		end
	end
	FB.LayoutMore()
end

-- Entrée publiée par le pont pour un bouton (écrans de la nouvelle fenêtre), ou nil.
function FB.ButtonEntry(key)
	local state = type(ForeverBridgeStatus) == "table" and ForeverBridgeStatus or {}
	local entries = run.buttons or (type(state.buttons) == "table" and state.buttons) or {}
	for _, entry in ipairs(entries) do
		if type(entry) == "table" and entry.key == key then
			return entry
		end
	end
	return nil
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

-- Historique d'une conversation : « game » (db.history) ou « addons » (db.history_addons, P06b).
local function HistoryKey(conv)
	return (conv or run.conv) == "addons" and "history_addons" or "history"
end

local function History(conv)
	local db = ForeverBridgeDB
	if type(db) ~= "table" then
		return {}
	end
	local key = HistoryKey(conv)
	if type(db[key]) ~= "table" then
		db[key] = {}
	end
	return db[key]
end

local function Remember(entry, conv)
	local history = History(conv)
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

-- EX1 : liens typés d'une réponse (`{kind, label, text}`), chacun cliquable : le clic ouvre la boîte de copie du
-- panneau avec sa propre chaîne. Rend vrai si au moins un lien a été imprimé.
function FB.PrintLinks(links)
	if type(links) ~= "table" then
		return false
	end
	local printed = false
	for _, item in ipairs(links) do
		if type(item) == "table" and type(item.text) == "string" and item.text ~= "" then
			run.links[#run.links + 1] = item.text
			local label = Escape(Plain(type(item.label) == "string" and item.label or "Export"))
			FB.Print("|Hforeverbridge:copy:" .. #run.links .. "|h|cff66ccff[" .. label .. "]|r|h  (cliquer pour copier)")
			printed = true
		end
	end
	return printed
end

-- EX1 : liens d'export reçus pendant la session (sans doublon), réimprimés par /fb exports.
local function KeepExports(links)
	if type(links) ~= "table" then
		return
	end
	run.exports = run.exports or {}
	for _, item in ipairs(links) do
		if type(item) == "table" and type(item.text) == "string" and item.text ~= "" then
			local seen = false
			for _, old in ipairs(run.exports) do
				if old.text == item.text then
					seen = true
				end
			end
			if not seen then
				run.exports[#run.exports + 1] = { kind = item.kind, label = item.label, text = item.text }
			end
		end
	end
end

-- Copie simple des liens d'un emplacement (la table de l'emplacement est remplacée au relevé suivant).
local function CopyLinks(links)
	if type(links) ~= "table" then
		return nil
	end
	local out = {}
	for _, item in ipairs(links) do
		if type(item) == "table" and type(item.text) == "string" then
			out[#out + 1] = { kind = item.kind, label = item.label, text = item.text }
		end
	end
	return #out > 0 and out or nil
end

-- Liens d'export de la session (écran Exports de la nouvelle fenêtre).
function FB.SessionExports()
	return run.exports or {}
end

function FB.Exports()
	FB.Open()
	if not run.exports or #run.exports == 0 then
		FB.Print("Exports : aucun export dans cette session (bouton Exports, ou une question sur un build).")
		return
	end
	FB.Print("|cffffd100Exports de la session|r :")
	FB.PrintLinks(run.exports)
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
	if not FB.PrintLinks(entry.links) and type(entry.link) == "string" and entry.link ~= "" then
		run.links[#run.links + 1] = entry.link
		FB.Print("|Hforeverbridge:copy:" .. #run.links .. "|h|cff66ccff[Talents Forever]|r|h  (cliquer pour copier le lien)")
	end
end

-- CJ1 (bloc 2, décision 276) : question en cours sous la dernière réponse, une rangée de boutons ; un clic envoie
-- a=<action> sans texte (question à choix, « Valider et livrer ») et la rangée disparaît.
local ANSWER_H = 22
local ANSWER_PAD = 24 -- marge du texte d'un bouton (largeur mesurée sur le libellé)

local function CopyChoices(choices)
	if type(choices) ~= "table" or type(choices.buttons) ~= "table" then
		return nil
	end
	local out = { prompt = type(choices.prompt) == "string" and choices.prompt or "", buttons = {} }
	for _, b in ipairs(choices.buttons) do
		if type(b) == "table" and type(b.label) == "string" and type(b.action) == "string" and b.action ~= "" then
			out.buttons[#out.buttons + 1] = { label = b.label, action = b.action }
		end
	end
	return #out.buttons > 0 and out or nil
end

function FB.HideAnswers()
	if ui.answers then
		ui.answers:Hide()
	end
	run.answering = nil
end

function FB.ShowAnswers(entry)
	if not (ui.frame and ui.history) or type(entry) ~= "table" or entry.answered or not entry.choices then
		FB.HideAnswers()
		return
	end
	if not ui.answers then
		local bar = CreateFrame("Frame", "ForeverBridgeAnswers", ui.frame)
		bar:SetHeight(ANSWER_H)
		bar:SetPoint("BOTTOMLEFT", ui.history, "BOTTOMLEFT", 0, 0)
		ui.answers = bar
		ui.answerButtons = {}
	end
	if entry.choices.prompt ~= "" then
		FB.Print("|cffffd100Question|r : " .. Escape(Plain(entry.choices.prompt)))
	end
	for i, choice in ipairs(entry.choices.buttons) do
		local button = ui.answerButtons[i]
		if not button then
			button = CreateFrame("Button", "ForeverBridgeAnswer" .. i, ui.answers, "UIPanelButtonTemplate")
			ui.answerButtons[i] = button
		end
		button:SetText(Plain(choice.label))
		button:SetScript("OnClick", function()
			FB.Answer(i)
		end)
		button:Show()
	end
	for i = #entry.choices.buttons + 1, #ui.answerButtons do
		ui.answerButtons[i]:Hide()
	end
	run.answering = entry
	FB.LayoutAnswers()
	ui.answers:Show()
end

-- Rangée des réponses sur la largeur du contenu : largeur de chaque bouton mesurée sur son libellé (caractères),
-- passage à la ligne quand le bouton suivant ne tient plus, jamais de chevauchement (CJ1, bloc 6a).
function FB.LayoutAnswers()
	local bar = ui.answers
	if not bar then
		return
	end
	local width = FB.ContentWidth()
	bar:SetWidth(width)
	local x, row = 0, 0
	for _, button in ipairs(ui.answerButtons) do
		if button:IsShown() then
			local letters = #(tostring(button:GetText() or ""):gsub("[\128-\191]", ""))
			local w = math.min(math.max(60, letters * 7 + ANSWER_PAD), width)
			if x > 0 and x + w > width then
				row, x = row + 1, 0
			end
			button:SetSize(w, ANSWER_H)
			button:ClearAllPoints()
			button:SetPoint("TOPLEFT", bar, "TOPLEFT", x, -row * (ANSWER_H + 4))
			x = x + w + 6
		end
	end
	bar:SetHeight((row + 1) * (ANSWER_H + 4))
end

function FB.Answer(index)
	local entry = run.answering
	local choice = entry and entry.choices and entry.choices.buttons[index]
	if not choice then
		return
	end
	entry.answered = true
	FB.HideAnswers()
	FB.Send("", nil, { flags = { "a=" .. choice.action }, label = Plain(choice.label) })
end

-- Historique gardé dans ForeverBridgeDB, rendu à la construction de la fenêtre.
function FB.RenderHistory()
	local last
	for _, entry in ipairs(History()) do
		if entry.role == "user" then
			PrintUser(entry.text or "", type(entry.shown) == "string" and entry.shown or nil)
		elseif entry.role == "assistant" then
			PrintReply(entry)
			last = entry
		end
	end
	if last then
		FB.ShowAnswers(last)
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

-- Calendrier des relevés ; la conversation « addons » attend plus longtemps.
local function StartSchedule(conv)
	if conv == nil then
		for _, waitingConv in pairs(Waiting()) do
			if waitingConv == "addons" then
				conv = "addons"
			end
		end
	end
	run.schedule = conv == "addons" and SCHEDULE_ADDONS or SCHEDULE
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
	local conv = run.conv
	if conv == "addons" then
		flags[#flags + 1] = "c=addons"
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
		conv = conv,
	}
	run.carousel = 0
	ShowCurrent()
	StartSchedule(conv)
	local label = opts.label or text
	PrintUser(label, opts.shown)
	Remember({ role = "user", text = label, shown = opts.shown, id = id }, conv)
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
-- Panneau d'action unique, collé à droite de la fenêtre (sonde en jeu H, décision 238) : copie d'un lien (Talents
-- Forever), zone de collage de l'export SimulationCraft (/simc, Ctrl+V) et cartes « À valider », l'un sous l'autre ;
-- le panneau défile (molette, barre du modèle UIPanelScrollFrameTemplate). Échap le ferme.
---------------------------------------------------------------------------

local PANEL_STEP = 40 -- défilement d'un cran de molette
local PASTE_H = 140 -- hauteur de la zone de collage (elle défile seule au-delà)

local function SectionLabel(parent, name, text)
	local label = parent:CreateFontString(name, "OVERLAY", "GameFontHighlightSmall")
	label:SetJustifyH("LEFT")
	label:SetWidth(CARDS_W - 52)
	label:SetText(text)
	return label
end

local function BuildPanel()
	if ui.panel then
		return ui.panel
	end
	BuildWindow()
	local panel = CreateFrame("Frame", "ForeverBridgePanel", UIParent, "BackdropTemplate")
	panel:SetFrameStrata("DIALOG")
	panel:SetClampedToScreen(true)
	panel:EnableMouse(true)
	panel:SetWidth(CARDS_W)
	if panel.SetBackdrop then
		panel:SetBackdrop(BACKDROP)
		panel:SetBackdropColor(0.05, 0.05, 0.07, 1)
	end
	tinsert(UISpecialFrames, "ForeverBridgePanel")
	-- fermé (Échap, boutons) : la copie et le collage se referment avec lui, les cartes restent
	panel:SetScript("OnHide", function()
		ui.copyText, ui.pasteOpen = nil, false
	end)
	-- croix de fermeture en haut à droite (décision 240), au-dessus de la barre de défilement
	local cross = CreateFrame("Button", "ForeverBridgePanelClose", panel, "UIPanelCloseButton")
	cross:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -4, -4)
	cross:SetScript("OnClick", function()
		panel:Hide()
	end)
	local scroll = CreateFrame("ScrollFrame", "ForeverBridgePanelScroll", panel, "UIPanelScrollFrameTemplate")
	scroll:SetPoint("TOPLEFT", panel, "TOPLEFT", 10, -30)
	scroll:SetPoint("BOTTOMRIGHT", panel, "BOTTOMRIGHT", -30, 10)
	scroll:EnableMouseWheel(true)
	scroll:SetScript("OnMouseWheel", function(self, delta)
		local top = self:GetVerticalScrollRange() or 0
		local y = (self:GetVerticalScroll() or 0) - delta * PANEL_STEP
		self:SetVerticalScroll(math.max(0, math.min(top, y)))
	end)
	local content = CreateFrame("Frame", "ForeverBridgePanelContent", scroll)
	content:SetWidth(CARDS_W - 40)
	scroll:SetScrollChild(content)

	-- copie d'un lien : texte sélectionné, Ctrl+C
	local copyLabel = SectionLabel(content, nil, "Lien : Ctrl+C pour copier, Échap pour fermer")
	local copyBox = CreateFrame("EditBox", "ForeverBridgeCopyBox", content)
	copyBox:SetSize(CARDS_W - 52, 20)
	copyBox:SetAutoFocus(false)
	copyBox:SetFontObject(ChatFontNormal)
	copyBox:SetScript("OnEscapePressed", function()
		panel:Hide()
	end)

	-- collage de l'export : zone de texte qui défile seule, puis Envoyer l'export
	local pasteLabel = SectionLabel(content, nil, "Export SimulationCraft : /simc, Ctrl+C, puis Ctrl+V ici.")
	local pasteScroll = CreateFrame("ScrollFrame", "ForeverBridgePasteScroll", content, "UIPanelScrollFrameTemplate")
	pasteScroll:SetSize(CARDS_W - 70, PASTE_H)
	local pasteBox = CreateFrame("EditBox", "ForeverBridgePasteBox", pasteScroll)
	pasteBox:SetMultiLine(true)
	pasteBox:SetAutoFocus(false)
	pasteBox:SetFontObject(ChatFontNormal)
	pasteBox:SetMaxLetters(0)
	pasteBox:SetSize(CARDS_W - 70, PASTE_H)
	pasteBox:SetScript("OnEscapePressed", function()
		panel:Hide()
	end)
	pasteScroll:SetScrollChild(pasteBox)
	local send = CreateFrame("Button", "ForeverBridgePasteSend", content, "UIPanelButtonTemplate")
	send:SetSize(140, BAR_H)
	send:SetText("Envoyer l'export")
	send:SetScript("OnClick", function()
		FB.SendPaste()
	end)
	local cancel = CreateFrame("Button", "ForeverBridgePasteClose", content, "UIPanelButtonTemplate")
	cancel:SetSize(90, BAR_H)
	cancel:SetPoint("LEFT", send, "RIGHT", 8, 0)
	cancel:SetText("Fermer")
	cancel:SetScript("OnClick", function()
		ui.pasteOpen = false
		FB.LayoutPanel()
	end)

	local cardsLabel = SectionLabel(content, nil, "À valider")
	ui.panel, ui.panelScroll, ui.panelContent = panel, scroll, content
	ui.copyParts = { copyLabel, copyBox }
	ui.copyLabel, ui.copyBox = copyLabel, copyBox
	ui.pasteParts = { pasteLabel, pasteScroll, send, cancel }
	ui.pasteLabel, ui.pasteScroll, ui.pasteBox, ui.pasteSend = pasteLabel, pasteScroll, pasteBox, send
	ui.cardsLabel, ui.cardTexts, ui.cardButtons = cardsLabel, {}, {}
	return panel
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
	-- détail technique de l'attente (jamais affiché), transmis par « Expliquer »
	if type(card.detail) == "string" and card.detail ~= "" then
		lines[#lines + 1] = Plain(card.detail)
	end
	return table.concat(lines, "\n")
end

-- Cartes montrées : celles du pont moins les cartes masquées par « Masquer » dont l'empreinte n'a pas changé.
local function VisibleCards()
	local db = ForeverBridgeDB
	local hidden = type(db) == "table" and type(db.hidden) == "table" and db.hidden or {}
	local shown = {}
	for _, card in ipairs(run.cards) do
		if not (type(card) == "table" and card.id ~= nil and card.stamp ~= nil and hidden[card.id] == card.stamp) then
			shown[#shown + 1] = card
		end
	end
	return shown
end

-- Largeur d'un bouton de carte d'après son libellé (caractères, pas octets).
local function ButtonWidth(label)
	local letters = #(label:gsub("[\128-\191]", ""))
	return math.max(PANEL_BUTTON_MIN, letters * 7 + 24)
end

-- Cartes placées à partir de y (négatif, haut du contenu) ; rend le y sous la dernière carte. Les boutons d'une
-- carte passent à la ligne quand ils dépassent la largeur du panneau.
local function LayoutCards(content, y)
	for _, widget in pairs(ui.cardButtons) do
		widget:Hide()
	end
	for _, text in pairs(ui.cardTexts) do
		text:Hide()
	end
	local cards = VisibleCards()
	if #cards == 0 then
		ui.cardsLabel:Hide()
		return y
	end
	ui.cardsLabel:ClearAllPoints()
	ui.cardsLabel:SetPoint("TOPLEFT", content, "TOPLEFT", 4, y)
	ui.cardsLabel:SetText("À valider (" .. #cards .. ")")
	ui.cardsLabel:Show()
	y = y - 18
	local maxX = CARDS_W - 52
	for i, card in ipairs(cards) do
		local text = ui.cardTexts[i]
		if not text then
			text = content:CreateFontString("ForeverBridgeCard" .. i .. "Text", "OVERLAY", "GameFontHighlightSmall")
			text:SetJustifyH("LEFT")
			ui.cardTexts[i] = text
		end
		text:ClearAllPoints()
		text:SetPoint("TOPLEFT", content, "TOPLEFT", 4, y)
		text:SetWidth(CARDS_W - 52)
		text:SetText(CardText(card))
		text:Show()
		local count = 1 + (type(card.lines) == "table" and #card.lines or 0)
		y = y - count * 14 - 4
		local x = 0
		for _, entry in ipairs(type(card.buttons) == "table" and card.buttons or {}) do
			if type(entry) == "table" and type(entry.key) == "string" then
				local name = "ForeverBridgeCard" .. i .. "_" .. entry.key
				local widget = ui.cardButtons[name]
				if not widget then
					widget = CreateFrame("Button", name, content, "UIPanelButtonTemplate")
					ui.cardButtons[name] = widget
				end
				local label = tostring(entry.label or entry.key)
				local width = ButtonWidth(label)
				if x > 0 and x + width > maxX then
					x = 0
					y = y - BAR_H - 4
				end
				widget:SetSize(width, BAR_H)
				widget:ClearAllPoints()
				widget:SetPoint("TOPLEFT", content, "TOPLEFT", 4 + x, y)
				widget:SetText(label)
				widget:SetScript("OnClick", function()
					FB.ClickCard(card, entry, widget)
				end)
				widget:Show()
				x = x + width + 6
			end
		end
		y = y - BAR_H - 12
	end
	return y
end

-- Sections ouvertes l'une sous l'autre (copie, collage, cartes) ; le panneau se cache quand aucune ne reste.
function FB.LayoutPanel()
	local panel = BuildPanel()
	local content = ui.panelContent
	local y = -4
	for _, part in ipairs(ui.copyParts) do
		part:SetShown(ui.copyText ~= nil)
	end
	if ui.copyText then
		ui.copyLabel:ClearAllPoints()
		ui.copyLabel:SetPoint("TOPLEFT", content, "TOPLEFT", 4, y)
		ui.copyBox:ClearAllPoints()
		ui.copyBox:SetPoint("TOPLEFT", content, "TOPLEFT", 4, y - 16)
		y = y - 16 - 20 - 12
	end
	for _, part in ipairs(ui.pasteParts) do
		part:SetShown(ui.pasteOpen)
	end
	if ui.pasteOpen then
		ui.pasteLabel:ClearAllPoints()
		ui.pasteLabel:SetPoint("TOPLEFT", content, "TOPLEFT", 4, y)
		ui.pasteScroll:ClearAllPoints()
		ui.pasteScroll:SetPoint("TOPLEFT", content, "TOPLEFT", 4, y - 16)
		ui.pasteSend:ClearAllPoints()
		ui.pasteSend:SetPoint("TOPLEFT", content, "TOPLEFT", 4, y - 16 - PASTE_H - 6)
		y = y - 16 - PASTE_H - 6 - BAR_H - 12
	end
	y = LayoutCards(content, y)
	content:SetHeight(-y + 4)
	if not ui.copyText and not ui.pasteOpen and #VisibleCards() == 0 then
		panel:Hide()
		return
	end
	-- même hauteur que la fenêtre, collé à sa droite : il suit la fenêtre quand on la déplace
	panel:SetHeight(math.max(MIN_H, ui.frame:GetHeight() or 0))
	panel:ClearAllPoints()
	panel:SetPoint("TOPLEFT", ui.frame, "TOPRIGHT", 8, 0)
	panel:Show()
end

local function PanelShown()
	return ui.panel ~= nil and ui.panel:IsShown()
end

-- Copie d'un lien (Talents Forever) : en tête du panneau, texte sélectionné.
function FB.ShowCopy(text)
	BuildPanel()
	ui.copyText = tostring(text or "")
	ui.copyBox:SetText(ui.copyText)
	FB.LayoutPanel()
	ui.panelScroll:SetVerticalScroll(0)
	ui.copyBox:SetFocus()
	ui.copyBox:HighlightText()
end

function FB.OpenPaste()
	BuildPanel()
	ui.pasteOpen = true
	FB.LayoutPanel()
	ui.pasteBox:SetFocus()
end

-- Bouton « Coller /simc » : ferme le panneau s'il montre déjà la zone de collage, sinon l'y ouvre.
function FB.TogglePaste()
	if PanelShown() and ui.pasteOpen then
		ui.panel:Hide()
		return
	end
	FB.OpenPaste()
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
		ui.pasteOpen = false
		FB.LayoutPanel()
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
	local count = #VisibleCards()
	button:SetText("À valider (" .. count .. ")")
	button:SetShown(count > 0)
	if FB.OnCardsCount then -- entrée « Mises à jour (n) » de la barre latérale : le même compte
		FB.OnCardsCount(count)
	end
	FB.LayoutMore()
	if PanelShown() then
		FB.LayoutPanel()
	end
	FB.UpdateStatus()
end

-- « Masquer » (décision 240) : la carte quitte le panneau et les compteurs, rien n'est envoyé au pont ; elle revient
-- quand le pont la publie avec une autre empreinte (attente changée).
function FB.HideCard(card)
	local db = ForeverBridgeDB
	if type(db) ~= "table" or type(card) ~= "table" or card.id == nil or card.stamp == nil then
		return
	end
	if type(db.hidden) ~= "table" then
		db.hidden = {}
	end
	db.hidden[card.id] = card.stamp
	if run.confirm then
		run.confirm.widget:SetText(run.confirm.label)
		run.confirm = nil
	end
	FB.RefreshCards()
end

-- Masquages des cartes que le pont ne publie plus : retirés.
local function PruneHidden()
	local db = ForeverBridgeDB
	if type(db) ~= "table" or type(db.hidden) ~= "table" then
		return
	end
	local present = {}
	for _, card in ipairs(run.cards) do
		if type(card) == "table" and card.id ~= nil then
			present[card.id] = true
		end
	end
	for id in pairs(db.hidden) do
		if not present[id] then
			db.hidden[id] = nil
		end
	end
end

function FB.ToggleCards()
	if PanelShown() then
		ui.panel:Hide()
		return
	end
	FB.RenderCards()
end

function FB.RenderCards()
	FB.LayoutPanel()
end

-- Clic sur un bouton de carte : une action demande un second clic dans le délai (« Confirmer »), puis part en
-- a=<action> sans texte ; « Expliquer » pose la question fixe avec le texte de la carte (b=explain).
function FB.ClickCard(card, entry, widget)
	if entry.explain then
		FB.Send(EXPLAIN_QUESTION .. "\n" .. CardPlain(card), "explain", { label = "Expliquer : " .. Plain(card.title or "") })
		return
	end
	if entry.hide then
		FB.HideCard(card)
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
	local key = HistoryKey()
	if type(db) == "table" and type(db[key]) == "table" and #db[key] > 0 then
		if type(db.archive) ~= "table" then
			db.archive = {}
		end
		table.insert(db.archive, 1, db[key])
		while #db.archive > ARCHIVE_KEPT do
			table.remove(db.archive)
		end
		db[key] = {}
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
		conv = message.conv,
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

local function UpdateInfo()
	return type(run.status) == "table" and type(run.status.update) == "table" and run.status.update or {}
end

-- Mise à jour en cours : passage vu en cours par le pont, ou « Mettre à jour » cliqué il y a peu (le passage n'est
-- pas encore visible dans un emplacement relevé).
local function Updating()
	if UpdateInfo().running then
		return true
	end
	if run.updateClicked and time() - run.updateClicked > UPDATE_CLICK_WAIT then
		run.updateClicked = nil
	end
	return run.updateClicked ~= nil
end

local function Elapsed(seconds)
	seconds = math.max(0, math.floor(seconds))
	if seconds < 60 then
		return seconds .. " s"
	end
	return math.floor(seconds / 60) .. " min " .. (seconds % 60) .. " s"
end

-- Avancement (décision 240) : animation, étape en mots simples, temps écoulé depuis le début du passage.
local function ProgressText()
	local update = UpdateInfo()
	local running = update.running
	local started = running and tonumber(update.started) or run.updateClicked or time()
	local stage = running and type(update.stage) == "string" and update.stage or (running and "travail en cours"
		or "lancement")
	local dots = string.rep(".", math.floor(GetTime() * 2) % 3 + 1)
	return "Mise à jour en cours" .. dots .. " " .. Escape(Plain(stage)) .. " · " .. Elapsed(time() - started)
end

-- Ligne des données : tête et fin publiées par le pont, avancement et compteurs des cartes montrées placés ici (les
-- cartes masquées n'y comptent pas) ; pont plus ancien : sa ligne entière.
local function DataLine(status)
	if not status then
		return "état des données inconnu"
	end
	if type(status.line_head) ~= "string" then
		return type(status.line) == "string" and Escape(Plain(status.line)) or "état des données inconnu"
	end
	local parts = { Escape(Plain(status.line_head)) }
	if Updating() then
		parts[#parts + 1] = ProgressText()
	end
	local approvable, waiting = 0, 0
	for _, card in ipairs(VisibleCards()) do
		if card.count == "approvable" then
			approvable = approvable + 1
		elseif card.count == "waiting" then
			waiting = waiting + 1
		end
	end
	if approvable > 0 then
		parts[#parts + 1] = approvable .. " à valider"
	end
	if waiting > 0 then
		parts[#parts + 1] = waiting .. " en attente"
	end
	if type(status.line_tail) == "string" and status.line_tail ~= "" then
		parts[#parts + 1] = Escape(Plain(status.line_tail))
	end
	return table.concat(parts, " · ")
end

-- Ligne d'état et voyant : données, pont vu, réponse en cours, réserve.
function FB.UpdateStatus()
	if not ui.status then
		return
	end
	local parts = {}
	local status = type(run.status) == "table" and run.status or nil
	parts[#parts + 1] = DataLine(status)
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
-- RX1 : feuille de route livrée par le pont (guide RestedXP), importée hors combat par l'API publique de RestedXP
-- (RXPGuides.ImportGuide), une seule fois par guide ; aucun code reçu n'est exécuté, jamais de chaîne chiffrée.
local pendingGuide

local function ImportGuideNow(guide)
	local db = ForeverBridgeDB
	if type(db.guides) ~= "table" then
		db.guides = {}
	end
	local api = type(RXPGuides) == "table" and RXPGuides.ImportGuide
	local status, detail
	if type(api) ~= "function" then
		status = "absent"
	else
		local ok, result = pcall(api, guide.text)
		if ok and result then
			status = "livré"
			local rxp = RXP
			local frame = type(rxp) == "table" and rxp.RXPFrame
			if type(rxp) == "table" and type(rxp.ScheduleTask) == "function" and type(frame) == "table"
				and frame.GenerateMenuTable then
				pcall(rxp.ScheduleTask, rxp, frame.GenerateMenuTable)
			end
		else
			status = "erreur"
			detail = tostring(result)
		end
	end
	db.guides[guide.sha] = status
	local name = Escape(tostring(guide.name or ""))
	if status == "livré" then
		FB.Print("Feuille de route livrée dans RestedXP : " .. name .. " (menu des guides de RestedXP).")
	elseif status == "absent" then
		FB.Print("RestedXP absent : feuille de route " .. name .. " non livrée (forever route deliver --addon, jeu fermé).")
	else
		FB.Print("RestedXP a refusé la feuille de route " .. name .. " : " .. Escape(detail or "?"))
	end
end

-- RX1 : « voir À valider » n'a de sens que si une carte est visible (cartes masquées comprises) ; sinon la ligne qui
-- le dit est retirée de la réponse.
local PENDING_MENTION = "voir À valider"

local function WithoutPendingMention(text)
	if type(text) ~= "string" or not text:find(PENDING_MENTION, 1, true) or #VisibleCards() > 0 then
		return text
	end
	local kept = {}
	for line in (text .. "\n"):gmatch("(.-)\n") do
		if not line:find(PENDING_MENTION, 1, true) then
			kept[#kept + 1] = line
		end
	end
	return (table.concat(kept, "\n"):gsub("%s+$", ""))
end

function FB.DeliverGuide(guide)
	local db = ForeverBridgeDB
	if type(db) ~= "table" or type(guide) ~= "table" or type(guide.text) ~= "string" or type(guide.sha) ~= "string" then
		return
	end
	if type(db.guides) == "table" and db.guides[guide.sha] then
		return
	end
	local ok, combat = pcall(InCombatLockdown)
	if ok and combat then
		pendingGuide = guide -- importée à la sortie du combat (PLAYER_REGEN_ENABLED)
		return
	end
	pendingGuide = nil
	ImportGuideNow(guide)
end

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
			if FB.UpdateBroker then
				FB.UpdateBroker()
			end
			FB.RefreshTabs()
			run.slots = tonumber(slot.status.slots) or run.slots
		end
		if type(slot.buttons) == "table" then
			run.buttons = slot.buttons
			FB.RefreshButtons()
		end
	end
	if published and type(slot.guide) == "table" then
		FB.DeliverGuide(slot.guide)
	end
	if published and type(slot.cards) == "table" then
		run.cards = slot.cards
		PruneHidden()
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
					waiting[reply.id] = run.unacked[i].conv or "game"
					table.remove(run.unacked, i)
				end
			end
			for _, entry in ipairs(Outbox()) do
				if type(entry) == "table" and entry.id == reply.id and not waiting[reply.id] then
					waiting[reply.id] = entry.conv or "game"
				end
			end
			if waiting[reply.id] and (reply.status == "done" or reply.status == "error") then
				local conv = waiting[reply.id] == "addons" and "addons" or "game"
				waiting[reply.id] = nil
				RemoveFromOutbox(reply.id)
				local entry = {
					role = "assistant",
					id = reply.id,
					status = reply.status,
					text = WithoutPendingMention(reply.text),
					provenance = reply.provenance,
					link = reply.link,
					links = CopyLinks(reply.links),
					choices = CopyChoices(reply.choices),
				}
				KeepExports(entry.links)
				if conv == run.conv then
					PrintReply(entry)
					FB.ShowAnswers(entry)
				end
				Remember(entry, conv)
				if not (ui.frame and ui.frame:IsShown()) or conv ~= run.conv then
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
		local schedule = run.schedule or SCHEDULE
		while run.scheduleStart and schedule[run.pollIndex] and elapsed >= schedule[run.pollIndex] - 1e-6 do
			run.pollIndex = run.pollIndex + 1
			FB.PollSlot()
		end
		if run.scheduleStart and not schedule[run.pollIndex] then
			run.scheduleStart = nil
			if next(Waiting()) ~= nil then
				FB.Print("Réponse toujours en cours : tapez /reload plus tard pour la récupérer.")
			end
			FB.UpdateStatus()
		end
	elseif ui.frame and ui.frame:IsShown() and not run.exhausted then
		local since = math.max(run.lastPoll or 0, run.openedAt or now)
		local polls = run.updatePolls or 0
		if Updating() and polls < UPDATE_POLLS_MAX then
			-- mise à jour en cours : relevés rapprochés pour suivre son étape et montrer sa fin
			if now - since >= (polls < UPDATE_POLLS and UPDATE_POLL or UPDATE_POLL_SLOW) then
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
	if not run.updateClicked then
		run.updatePolls = 0
	end
	local last = type(update.last) == "table" and update.last or nil
	local finished = last and last.finished_at
	if type(finished) ~= "string" or type(db) ~= "table" or db.update_seen == finished then
		return
	end
	local announce = run.sawRunning or run.updateClicked or db.update_seen ~= nil
	db.update_seen = finished
	run.sawRunning, run.updateClicked, run.updatePolls = nil, nil, 0
	if announce then
		-- phrase de fin rédigée par le pont (décision 240) ; pont plus ancien : écritures et cartes à valider
		if type(last.text) == "string" and last.text ~= "" then
			FB.Print(Escape(Plain(last.text)))
		else
			FB.Print("Mise à jour terminée : " .. tostring(tonumber(last.written) or 0) .. " écrit(s), "
				.. tostring(tonumber(last.approvable) or 0) .. " à valider")
		end
	end
	FB.UpdateStatus()
end

-- « Mettre à jour » cliqué : l'avancement s'affiche tout de suite ; le dernier passage déjà fini n'est pas annoncé
-- comme la fin de celui-ci.
local function StartUpdateProgress()
	local db = ForeverBridgeDB
	local last = type(UpdateInfo().last) == "table" and UpdateInfo().last or nil
	if type(db) == "table" and last and type(last.finished_at) == "string" then
		db.update_seen = last.finished_at
	end
	run.updateClicked = time()
	run.updatePolls = 0
	FB.UpdateStatus()
end

function FB.ClickButton(entry)
	if entry.target and not HasPlayerTarget() then
		FB.Print(tostring(entry.label or "PvP") .. " : prenez un joueur en cible, puis cliquez à nouveau.")
		return
	end
	if type(entry.action) == "string" and entry.action ~= "" then
		-- bouton d'action (Mettre à jour) : a=<action> sans texte, traité par le pont sans conversation
		if FB.Send("", nil, { flags = { "a=" .. entry.action }, label = tostring(entry.label or entry.key) })
			and entry.action == "update" then
			StartUpdateProgress()
		end
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
		if run.scheduleStart or Updating() then
			FB.UpdateStatus()
		end
	end
	if run.roleAt and GetTime() >= run.roleAt then
		run.roleAt = nil
		FB.SwitchProfile()
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
-- Rôle du personnage et bascule de profil EllesmereUI (EX1, décision 267)
---------------------------------------------------------------------------

-- Rôles tenus par chaque classe (table des spécialisations de docs/SPEC.md) et libellés du nom de profil
-- « <personnage> - <rôle> » écrit par forever export ellesmere.
local ROLE_LABELS = { dps = "DPS", heal = "Soins", tank = "Tank" }
local ROLE_ORDER = { "dps", "heal", "tank" }
local CLASS_ROLES = {
	WARRIOR = { dps = true, tank = true }, PALADIN = { heal = true, tank = true, dps = true },
	HUNTER = { dps = true }, ROGUE = { dps = true }, PRIEST = { heal = true, dps = true },
	SHAMAN = { dps = true, heal = true }, MAGE = { dps = true }, WARLOCK = { dps = true },
	DRUID = { dps = true, tank = true, heal = true },
}
local CLASS_LABELS = {
	WARRIOR = "Warrior", PALADIN = "Paladin", HUNTER = "Hunter", ROGUE = "Rogue", PRIEST = "Priest",
	SHAMAN = "Shaman", MAGE = "Mage", WARLOCK = "Warlock", DRUID = "Druid",
}
local SWITCH_DELAY = 5 -- attente après la connexion : la bascule propre d'EllesmereUI passe d'abord

local function CharName()
	local ok, name = pcall(UnitName, "player")
	return ok and type(name) == "string" and name or nil
end

local function CharKey()
	local name = CharName()
	local ok, realm = pcall(GetRealmName)
	if not name or not ok or type(realm) ~= "string" then
		return nil
	end
	return name .. " - " .. realm
end

local function PlayerClass()
	local ok, token = pcall(UnitClassBase, "player")
	return ok and type(token) == "string" and token or nil
end

function FB.Role()
	local db, key = ForeverBridgeDB, CharKey()
	if type(db) ~= "table" or type(db.roles) ~= "table" or not key then
		return nil
	end
	return db.roles[key]
end

local function AllowedRoles(token)
	local allowed = {}
	for _, role in ipairs(ROLE_ORDER) do
		if not CLASS_ROLES[token] or CLASS_ROLES[token][role] then
			allowed[#allowed + 1] = role
		end
	end
	return allowed
end

-- Vrai si la bascule automatique d'EllesmereUI vaut pour ce personnage : sa spécialisation (gardée par EllesmereUI,
-- lecture seule de EllesmereUIDB) est affectée à un profil existant. Jamais d'écriture dans EllesmereUIDB.
local function EllesmereAuto()
	if type(EllesmereUI) ~= "table" or type(EllesmereUI.GetSpecProfile) ~= "function" then
		return false
	end
	local key, spec = CharKey(), nil
	if key and type(EllesmereUIDB) == "table" then
		local ok, last = pcall(function()
			local byChar = EllesmereUIDB.lastSpecByChar
			return type(byChar) == "table" and byChar[key] or nil
		end)
		spec = ok and last or nil
	end
	local info = C_SpecializationInfo
	if not spec and type(info) == "table" and type(info.GetSpecialization) == "function" then
		local ok, index = pcall(info.GetSpecialization)
		if ok and type(index) == "number" and index > 0 then
			local okInfo, id = pcall(info.GetSpecializationInfo, index)
			spec = okInfo and id or nil
		end
	end
	if not spec then
		return false
	end
	local ok, assigned = pcall(EllesmereUI.GetSpecProfile, spec)
	if not ok or type(assigned) ~= "string" then
		return false
	end
	local okList, _, profiles = pcall(EllesmereUI.GetProfileList)
	return okList and type(profiles) == "table" and profiles[assigned] ~= nil
end

-- Bascule vers le profil « <personnage> - <rôle> » : hors combat (sinon à la sortie du combat), seulement si le profil
-- existe et n'est pas déjà actif, jamais si la bascule automatique d'EllesmereUI vaut pour ce personnage (EUI2).
function FB.SwitchProfile()
	run.rolePending = nil
	if type(ForeverBridgeDB) ~= "table" or ForeverBridgeDB.eui ~= true then
		return -- CJ1 (décision 274) : EllesmereUI éteint par défaut, jamais de bascule sans /fb eui on
	end
	local role, name = FB.Role(), CharName()
	if not role or not ROLE_LABELS[role] or not name then
		return
	end
	if type(EllesmereUI) ~= "table" or type(EllesmereUI.SwitchProfile) ~= "function" then
		return
	end
	if EllesmereAuto() then
		if not run.autoNoted then
			run.autoNoted = true
			FB.Print("EllesmereUI : bascule automatique active pour ce personnage (spécialisation affectée à un profil) : "
				.. "ForeverBridge ne bascule pas.")
		end
		return
	end
	if InCombatLockdown() then
		run.rolePending = true
		return
	end
	local profile = name .. " - " .. ROLE_LABELS[role]
	local okList, order = pcall(EllesmereUI.GetProfileList)
	local found = false
	if okList and type(order) == "table" then
		for _, each in ipairs(order) do
			if each == profile then
				found = true
			end
		end
	end
	if not found then
		if run.missingNoted ~= profile then
			run.missingNoted = profile
			FB.Print("EllesmereUI : profil « " .. profile .. " » absent : importer d'abord la chaîne !EUI_ (bouton "
				.. "Exports) sous ce nom.")
		end
		return
	end
	local okActive, active = pcall(EllesmereUI.GetActiveProfileName)
	if okActive and active == profile then
		return
	end
	if pcall(EllesmereUI.SwitchProfile, profile) then
		FB.Print("EllesmereUI : profil « " .. profile .. " » activé.")
	end
end

-- /fb role [dps|heal|tank] : rôle du personnage, gardé dans ForeverBridgeDB.roles, envoyé dans le contexte.
function FB.SetRole(value)
	FB.Open()
	local key, token = CharKey(), PlayerClass()
	local allowed = AllowedRoles(token)
	value = string.lower(value or "")
	if value == "" then
		FB.Print("Rôle de ce personnage : " .. (FB.Role() or "aucun") .. " (/fb role " .. table.concat(allowed, ", ") .. ")")
		return
	end
	if value == "clear" then
		local db = ForeverBridgeDB
		if type(db) == "table" and type(db.roles) == "table" and key then
			db.roles[key] = nil
		end
		FB.Print("Rôle de ce personnage effacé.")
		return
	end
	if not ROLE_LABELS[value] then
		FB.Print("rôle : /fb role suivi de " .. table.concat(allowed, ", ") .. ", ou clear.")
		return
	end
	if CLASS_ROLES[token] and not CLASS_ROLES[token][value] then
		FB.Print("Rôle « " .. value .. " » non tenu par la classe " .. (CLASS_LABELS[token] or tostring(token))
			.. " (rôles : " .. table.concat(allowed, ", ") .. ").")
		return
	end
	local db = ForeverBridgeDB
	if type(db) ~= "table" or not key then
		return
	end
	if type(db.roles) ~= "table" then
		db.roles = {}
	end
	db.roles[key] = value
	FB.Print("Rôle de " .. key .. " : " .. value .. ".")
	FB.SwitchProfile()
end

-- CJ1 (décision 274) : /fb eui on|off : propositions et bascule de profil EllesmereUI, éteintes par défaut.
function FB.SetEui(value)
	FB.Open()
	local db = ForeverBridgeDB
	if type(db) ~= "table" then
		return
	end
	value = string.lower(value or "")
	if value == "on" then
		db.eui = true
		FB.Print("EllesmereUI : profils et bascule par rôle rallumés (/fb eui off pour les éteindre).")
		FB.SwitchProfile()
	elseif value == "off" then
		db.eui = nil
		FB.Print("EllesmereUI : éteint ; ForeverBridge ne propose ni ne bascule aucun profil.")
	else
		FB.Print("EllesmereUI : " .. (db.eui == true and "rallumé" or "éteint (défaut)") .. " ; /fb eui on ou off.")
	end
end

-- Noms des profils d'EllesmereUI (API publique, lecture seule), ou nil si EllesmereUI est absent.
local function EllesmereProfiles()
	if type(EllesmereUI) ~= "table" or type(EllesmereUI.GetProfileList) ~= "function" then
		return nil
	end
	local ok, order, profiles = pcall(EllesmereUI.GetProfileList)
	if not ok or type(order) ~= "table" then
		return nil
	end
	-- ordre d'EllesmereUI d'abord, puis les profils absents de l'ordre (table des profils), triés
	local names, seen, rest = {}, {}, {}
	for _, each in ipairs(order) do
		if type(each) == "string" and not seen[each] then
			seen[each] = true
			names[#names + 1] = each
		end
	end
	if type(profiles) == "table" then
		for each in pairs(profiles) do
			if type(each) == "string" and not seen[each] then
				rest[#rest + 1] = each
			end
		end
	end
	table.sort(rest)
	for _, each in ipairs(rest) do
		names[#names + 1] = each
	end
	return names
end

-- /fb base [profil] : profil de base EllesmereUI de ce personnage (décision 269), gardé dans ForeverBridgeDB.bases,
-- envoyé dans le contexte ; le pont le garde au profil forever et le bouton Exports part de lui.
function FB.SetBase(value)
	FB.Open()
	local key = CharKey()
	local db = ForeverBridgeDB
	local names = EllesmereProfiles()
	local list = names and table.concat(names, ", ") or "EllesmereUI absent"
	value = value or ""
	if value == "" then
		local current = type(db) == "table" and type(db.bases) == "table" and key and db.bases[key] or nil
		FB.Print("Profil de base EllesmereUI de ce personnage : " .. (current or "aucun (le profil actif)") .. ".")
		FB.Print("Profils : " .. list .. " (/fb base <profil>).")
		return
	end
	if names then
		local found = false
		for _, each in ipairs(names) do
			if each == value then
				found = true
			end
		end
		if not found then
			FB.Print("Profil EllesmereUI « " .. value .. " » absent ; profils : " .. list .. ".")
			return
		end
	end
	if type(db) ~= "table" or not key then
		return
	end
	if type(db.bases) ~= "table" then
		db.bases = {}
	end
	db.bases[key] = value
	FB.Print("Profil de base EllesmereUI de " .. key .. " : " .. value .. " (bouton Exports).")
end

---------------------------------------------------------------------------
-- Objet LibDataBroker « Forever » (EX1, bloc G) : affiché par le bloc Broker des DataBars d'EllesmereUI
---------------------------------------------------------------------------

-- Créé seulement si LibDataBroker est déjà chargé par un autre addon (EllesmereUI) : rien d'embarqué ici. Le texte
-- reprend l'état publié par le pont ; XP par heure et prochain objectif seulement s'ils sont envoyés, jamais inventés.
local function BrokerText()
	local status = run.status
	if type(status) ~= "table" then
		return "pont pas encore vu"
	end
	local parts = {}
	if type(status.line) == "string" and status.line ~= "" then
		parts[#parts + 1] = Plain(status.line)
	end
	if status.xp_per_hour ~= nil then
		parts[#parts + 1] = "XP/h " .. Plain(tostring(status.xp_per_hour))
	end
	if type(status.next_objective) == "string" and status.next_objective ~= "" then
		parts[#parts + 1] = Plain(status.next_objective)
	end
	return #parts > 0 and table.concat(parts, " · ") or "pont pas encore vu"
end

function FB.UpdateBroker()
	if not run.broker then
		if type(LibStub) ~= "table" and type(LibStub) ~= "function" then
			return
		end
		local ok, ldb = pcall(LibStub, "LibDataBroker-1.1", true)
		if not ok or type(ldb) ~= "table" or type(ldb.NewDataObject) ~= "function" then
			return
		end
		local created, obj = pcall(ldb.NewDataObject, ldb, "Forever", {
			type = "data source",
			label = "Forever",
			text = "",
			OnClick = function()
				FB.Toggle()
			end,
			OnTooltipShow = function(tooltip)
				if type(tooltip) == "table" and type(tooltip.AddLine) == "function" then
					tooltip:AddLine("Forever")
					tooltip:AddLine(BrokerText())
				end
			end,
		})
		if not created or type(obj) ~= "table" then
			return
		end
		run.broker = obj
	end
	run.broker.text = BrokerText()
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
	if type(db.hidden) ~= "table" then
		db.hidden = {} -- cartes masquées : identifiant → empreinte (décision 240)
	end
end

-- Sortie du combat : feuille de route reçue pendant le combat, importée maintenant (RX1).
function handlers.PLAYER_REGEN_ENABLED()
	if pendingGuide then
		FB.DeliverGuide(pendingGuide)
	end
	if run.rolePending then
		FB.SwitchProfile()
	end
end

-- Connexion et /reload : état et boutons de Status.lua, réponses arrivées dans Inbox.lua (chemin de secours).
function handlers.PLAYER_ENTERING_WORLD()
	if type(ForeverBridgeDB) ~= "table" then
		return
	end
	if FB.Role() then
		run.roleAt = GetTime() + SWITCH_DELAY -- EX1 : bascule de profil après celle d'EllesmereUI
	end
	if type(ForeverBridgeStatus) == "table" then
		if type(ForeverBridgeStatus.status) == "table" and next(ForeverBridgeStatus.status) ~= nil then
			run.status = ForeverBridgeStatus.status
			FB.CheckUpdate(ForeverBridgeStatus.status)
			FB.RefreshTabs()
			run.slots = tonumber(ForeverBridgeStatus.status.slots) or run.slots
		end
		if tonumber(ForeverBridgeStatus.now) and tonumber(ForeverBridgeStatus.now) > 0 then
			run.bridgeSeen = tonumber(ForeverBridgeStatus.now)
			if type(ForeverBridgeStatus.cards) == "table" then
				run.cards = ForeverBridgeStatus.cards
				PruneHidden()
				FB.RefreshCards()
			end
		end
	end
	FB.ApplySlot(ForeverBridgeSlot)
	FB.UpdateBroker()
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
	"/fb exports : réafficher les liens d'export de la session (Talents Forever, Naowh), à copier depuis le panneau.",
	"/fb role dps|heal|tank|clear : rôle de ce personnage (profil EllesmereUI seulement après /fb eui on).",
	"/fb eui on|off : propositions et bascule de profil EllesmereUI, éteintes par défaut (ton interface reste la tienne).",
	"/fb base <profil> : profil EllesmereUI de base de ce personnage, d'où part le bouton Exports (sans nom : la liste).",
	"/fv classique : ancienne fenêtre ou nouvelle fenêtre (barre latérale), au /reload suivant.",
}

-- Ancienne fenêtre (décision 280) : réglage gardé, pris en compte au /reload suivant que le joueur tape.
function FB.ToggleClassic()
	if type(ForeverBridgeDB) ~= "table" then
		return
	end
	ForeverBridgeDB.classic = not (ForeverBridgeDB.classic == true)
	local which = ForeverBridgeDB.classic and "l'ancienne fenêtre" or "la nouvelle fenêtre (barre latérale)"
	FB.Print("Fenêtre : " .. which .. " au prochain /reload (tapez /reload).")
end

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
FB.Help = Help

SLASH_FOREVERBRIDGE1 = "/fv"
SLASH_FOREVERBRIDGE2 = "/forever"
SLASH_FOREVERBRIDGE3 = "/fb"
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
	elseif command == "exports" then
		FB.Exports()
	elseif command == "role" then
		FB.SetRole(rest)
	elseif command == "eui" then
		FB.SetEui(rest)
	elseif command == "base" then
		FB.SetBase(rest)
	elseif command == "classique" then
		FB.Open()
		FB.ToggleClassic()
	else
		Help()
	end
end
