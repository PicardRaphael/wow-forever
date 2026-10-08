-- ForeverBridge : pont de conversation de forever-core (P06a, décisions 194 et 212).
-- Bloc A : bande de test (/fv test) lue par « forever bridge selftest --live », et autotest des fichiers de contrôle
-- (/fv diag) : sons vides ou valides, fichier modifié ou ajouté pendant que le jeu tourne, addon chargé à la demande.
-- Seul addon de forever-core qui dessine (décision 194) : la bande n'apparaît que sur demande. Aucune fonction
-- d'action, aucun rechargement de l'interface, aucun abonnement au journal de combat.
--
-- Contient du code adapté de wow-ai (https://github.com/chelinho139/wow-ai, commit 3756eb5a : dessin de la bande et
-- autotest des signaux, addon/WoWAI/WoWAI.lua), sous la licence suivante :
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

local CELL = 4 -- côté d'une cellule, en pixels physiques
local TEST_DURATION = 120 -- la bande de test se retire seule au bout de deux minutes
local CTL = "Interface\\AddOns\\ForeverBridge\\ctl\\"
local PROBE_ADDON = "ForeverBridge_Probe"
local PREFIX = "|cff33ff99ForeverBridge|r : "

local driver = CreateFrame("Frame", "ForeverBridgeDriver", UIParent)
local band
local textures = {}
local run = {}

local function Say(text)
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
	band:SetSize(Codec.CELLS_PER_ROW * CELL, Codec.MAX_ROWS * CELL)
	band:Hide()
	return band
end

function FB.HideBand()
	if band then
		band:Hide()
	end
end

-- Dessine le message (numéro, charge) ; faux et la raison si la charge dépasse la bande.
function FB.ShowBand(id, payload)
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
	local total = math.ceil(#cells / perRow) * perRow
	for i = 1, total do
		local t = textures[i]
		if not t then
			t = b:CreateTexture(nil, "OVERLAY")
			t:SetSize(CELL, CELL)
			local col = (i - 1) % perRow
			local row = math.floor((i - 1) / perRow)
			t:SetPoint("TOPLEFT", b, "TOPLEFT", col * CELL, -row * CELL)
			textures[i] = t
		end
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
-- Bande de test (/fv test)
---------------------------------------------------------------------------

function FB.StopTest()
	run.testLeft = nil
	FB.HideBand()
end

function FB.ToggleTest()
	if run.testLeft then
		FB.StopTest()
		Say("bande de test retirée.")
		return
	end
	local ok, why = FB.ShowBand(Codec.SELFTEST_ID, Codec.SelftestPayload())
	if not ok then
		Say("bande de test impossible : " .. tostring(why))
		return
	end
	run.testLeft = TEST_DURATION
	Say("bande de test affichée en haut à gauche (retirée dans deux minutes, ou par /fv test). "
		.. "Dans un terminal : uv run forever bridge selftest --live, puis revenir au jeu.")
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
		Say("ctl/" .. name .. "." .. ext .. " : " .. state .. " (" .. control[2] .. ")")
	end
	local passed = results.empty == false and results.valid == true
	Say("autotest ." .. ext .. " : " .. (passed and "réussi" or "échoué"))
end

local function DiagProbe()
	local loaded, reason = false, "C_AddOns.LoadAddOn absente"
	if C_AddOns and type(C_AddOns.LoadAddOn) == "function" then
		local ok, result, why = pcall(C_AddOns.LoadAddOn, PROBE_ADDON)
		if ok then
			loaded, reason = result, why
		else
			loaded, reason = false, "erreur"
		end
	end
	if loaded then
		Say(PROBE_ADDON .. " : chargé, valeur « " .. tostring(ForeverBridge_ProbeValue) .. " »")
	else
		Say(PROBE_ADDON .. " : non chargé (" .. tostring(reason) .. ")")
	end
end

function FB.Diag()
	local width, height = PhysicalSize()
	local uiScale = UIParent.GetEffectiveScale and UIParent:GetEffectiveScale() or 1
	Say(string.format("écran %d × %d, échelle de la bande %.4f, échelle de l'interface %.4f", width, height,
		768 / height, uiScale))
	DiagSounds("wav")
	DiagSounds("ogg")
	DiagProbe()
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

local HELP = "/fv test : bande de test (lue par forever bridge selftest --live) ; /fv diag : autotest des fichiers "
	.. "de contrôle et de l'addon chargé à la demande."

SLASH_FOREVERBRIDGE1 = "/fv"
SLASH_FOREVERBRIDGE2 = "/forever"
SlashCmdList.FOREVERBRIDGE = function(message)
	local command = string.lower((message or ""):match("^%s*(%S*)") or "")
	if command == "test" then
		FB.ToggleTest()
	elseif command == "diag" then
		FB.Diag()
	else
		Say(HELP)
	end
end
