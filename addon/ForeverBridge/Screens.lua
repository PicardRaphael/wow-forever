-- ForeverBridge : écrans de la nouvelle fenêtre (CJ1, bloc 6a, décision 280 ; maquettes acceptées le 2026-10-15).
-- Barre latérale à gauche, un écran à la fois ; chaque écran est un raccourci vers une question ou une action du
-- chat (même chemin que la saisie : FB.Send, FB.ClickButton), jamais une copie de l'interface d'un autre addon.
-- Thème : couleur d'accent et police d'EllesmereUI lues par ses fonctions publiques, sans rien y écrire ; sinon
-- un accent propre. Rien de protégé, rien en combat ; l'ancienne fenêtre reste derrière /fv classique.

local FB = ForeverBridge

local NAV_W = 150 -- même largeur que dans ForeverBridge.lua
local NAV_ROW = 26 -- hauteur d'une entrée de la barre latérale
local TOP = -52 -- haut du contenu, sous l'en-tête
local ROW = 30 -- pas vertical des lignes d'un écran
local ROUTE_SPAN = 5 -- écart proposé par défaut entre les deux niveaux de l'assistant (réglage d'interface)
local DEFAULT_ACCENT = { 0.2, 0.75, 0.55 }
local SELECTED_ALPHA = 0.35
local LABEL_SIZE = 12

local NAV = {
	{ key = "chat", label = "Chat" },
	{ key = "route", label = "Feuille de route" },
	{ key = "talents", label = "Talents" },
	{ key = "gear", label = "Équipement" },
	{ key = "exports", label = "Exports" },
	{ key = "updates", label = "Mises à jour" },
	{ key = "help", label = "Aide" },
}
local SCREENS = { "chat", "route", "talents", "gear", "exports" }

local ROUTE_TYPES = {
	{ key = "leveling", label = "Leveling" },
	{ key = "reputation", label = "Réputation" },
	{ key = "profession", label = "Métier" },
	{ key = "gear", label = "Équipement" },
}
-- Bloc 6b (décision 281) : types de route que Forever calcule ; un autre type le dit, sans formulaire ni question.
local COMPUTED = { leveling = true, gear = true }
local NOT_COMPUTED = {
	reputation = "La route de réputation n'est pas encore calculée par Forever (bloc 4e, avant le 4 novembre) : "
		.. "rien n'est envoyé.",
	profession = "La route de métier n'est pas encore calculée par Forever : rien n'est envoyé.",
}

local S = { screens = {}, nav = {}, exportRows = {} }
local REP_ROWS = 5 -- lignes de la liste des factions montrées à la fois (réglage d'interface)
local REP_ROW_H = 20

local function Player()
	local okName, name = pcall(UnitName, "player")
	local okLevel, level = pcall(UnitLevel, "player")
	if not okName or issecretvalue(name) or type(name) ~= "string" then
		name = "?"
	end
	if not okLevel or issecretvalue(level) or type(level) ~= "number" or level < 1 then
		level = 1
	end
	return name, level
end

-- Accent et police d'EllesmereUI (fonctions publiques, appel protégé), sinon l'accent propre et la police du jeu.
local function Theme()
	local r, g, b = DEFAULT_ACCENT[1], DEFAULT_ACCENT[2], DEFAULT_ACCENT[3]
	local font
	local eui = _G.EllesmereUI
	if type(eui) == "table" then
		if type(eui.ResolveActiveAccent) == "function" then
			local ok, ar, ag, ab = pcall(eui.ResolveActiveAccent)
			if ok and type(ar) == "number" and type(ag) == "number" and type(ab) == "number" then
				r, g, b = ar, ag, ab
			end
		end
		if type(eui.GetFontPath) == "function" then
			local ok, path = pcall(eui.GetFontPath, nil)
			if ok and type(path) == "string" and path ~= "" then
				font = path
			end
		end
	end
	return r, g, b, font
end

local function Button(name, parent, label, width)
	local button = CreateFrame("Button", name, parent, "UIPanelButtonTemplate")
	button:SetSize(width or 120, 22)
	button:SetText(label)
	return button
end

local function Text(name, parent, template)
	local fs = parent:CreateFontString(name, "OVERLAY", template or "GameFontHighlight")
	fs:SetJustifyH("LEFT")
	return fs
end

local function Place(widget, parent, x, y)
	widget:ClearAllPoints()
	widget:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
end

-- Sélecteur « < valeur > » ; `get` et `set` lisent et écrivent la valeur, bornée par l'appelant.
local function Stepper(prefix, parent, x, y, get, set)
	local down = Button(prefix .. "Down", parent, "<", 26)
	local value = Text(prefix .. "Value", parent)
	local up = Button(prefix .. "Up", parent, ">", 26)
	Place(down, parent, x, y)
	Place(value, parent, x + 34, y - 4)
	value:SetWidth(34)
	Place(up, parent, x + 72, y)
	local function refresh()
		value:SetText(tostring(get()))
	end
	down:SetScript("OnClick", function()
		set(get() - 1)
		refresh()
	end)
	up:SetScript("OnClick", function()
		set(get() + 1)
		refresh()
	end)
	return refresh
end

local function SendQuestion(text, key, flags)
	if FB.Send(text, key, { flags = flags }) then
		FB.ShowScreen("chat")
	end
end

local function ClickKey(key)
	local entry = FB.ButtonEntry(key)
	if not entry then
		FB.Print("Bouton « " .. key .. " » pas encore publié par le pont (lancez le pont, puis réessayez).")
		return
	end
	FB.ClickButton(entry)
	FB.ShowScreen("chat")
end

---------------------------------------------------------------------------
-- Feuille de route : type, niveaux, options ; même demande que le chat
---------------------------------------------------------------------------

---------------------------------------------------------------------------
-- Réputation (bloc 6b, décision 281) : factions du panneau du personnage, groupées comme dans le jeu, filtrables
-- par groupe, puis le palier visé ; ni niveaux ni champ libre. Libellés des paliers : ceux du client.
---------------------------------------------------------------------------

local function StandingLabel(reaction)
	local label = type(reaction) == "number" and _G["FACTION_STANDING_LABEL" .. reaction]
	return type(label) == "string" and label or tostring(reaction or "?")
end

-- Dernier palier connu du client (libellés FACTION_STANDING_LABEL<n> présents), jamais un nombre écrit ici.
local function TopStanding()
	local top = 1
	while type(_G["FACTION_STANDING_LABEL" .. (top + 1)]) == "string" do
		top = top + 1
	end
	return top
end

function S.BuildReputation(screen, state)
	local group = Button("ForeverBridgeRepGroup", screen, "", 220)
	Place(group, screen, 0, -3 * ROW)
	group:SetScript("OnClick", function()
		state.repGroup = ((state.repGroup or 0) + 1) % (#(state.repGroups or {}) + 1)
		state.repPage = 0
		S.RefreshReputation(true)
	end)
	local page = Button("ForeverBridgeRepNext", screen, "Suite >", 80)
	Place(page, screen, 226, -3 * ROW)
	page:SetScript("OnClick", function()
		state.repPage = (state.repPage or 0) + 1
		S.RefreshReputation(true)
	end)
	S.repRows = {}
	for i = 1, REP_ROWS do
		local row = Button("ForeverBridgeRepRow" .. i, screen, "", 340)
		row:SetHeight(REP_ROW_H)
		Place(row, screen, 0, -4 * ROW - (i - 1) * REP_ROW_H)
		row:SetScript("OnClick", function(self)
			local chosen = self.faction
			if chosen then
				state.repChosen = chosen
				state.repTarget = math.min((chosen.reaction or 0) + 1, TopStanding())
				S.RefreshReputation(true)
			end
		end)
		S.repRows[i] = row
	end
	local y = -4 * ROW - REP_ROWS * REP_ROW_H - 6
	local chosen = Text("ForeverBridgeRepChosen", screen)
	Place(chosen, screen, 0, y)
	chosen:SetWidth(340)
	local targetLabel = Text("ForeverBridgeRepTargetLabel", screen)
	Place(targetLabel, screen, 0, y - 26)
	targetLabel:SetText("Palier visé")
	local down = Button("ForeverBridgeRepTargetDown", screen, "<", 26)
	local value = Text("ForeverBridgeRepTargetValue", screen)
	local up = Button("ForeverBridgeRepTargetUp", screen, ">", 26)
	Place(down, screen, 90, y - 22)
	Place(value, screen, 124, y - 26)
	value:SetWidth(110)
	Place(up, screen, 240, y - 22)
	down:SetScript("OnClick", function()
		if state.repChosen then
			state.repTarget = math.max((state.repChosen.reaction or 0) + 1, (state.repTarget or 1) - 1)
			S.RefreshReputation(true)
		end
	end)
	up:SetScript("OnClick", function()
		if state.repChosen then
			state.repTarget = math.min(TopStanding(), (state.repTarget or 1) + 1)
			S.RefreshReputation(true)
		end
	end)
	S.repWidgets = { group, page, chosen, targetLabel, down, value, up }
	S.repState = state
end

function S.RefreshReputation(shown)
	if not S.repWidgets then
		return
	end
	local state = S.repState
	for _, widget in ipairs(S.repWidgets) do
		widget:SetShown(shown)
	end
	for _, row in ipairs(S.repRows) do
		row:SetShown(false)
	end
	if not shown then
		return
	end
	local Message = ForeverBridge_Message
	local all = type(Message) == "table" and type(Message.Reputations) == "function" and Message.Reputations() or nil
	local chosen, value = _G.ForeverBridgeRepChosen, _G.ForeverBridgeRepTargetValue
	if not all then
		chosen:SetText("Aucune réputation lue en jeu (panneau de réputation indisponible).")
		for _, name in ipairs({ "ForeverBridgeRepGroup", "ForeverBridgeRepNext", "ForeverBridgeRepTargetLabel",
			"ForeverBridgeRepTargetDown", "ForeverBridgeRepTargetValue", "ForeverBridgeRepTargetUp" }) do
			_G[name]:SetShown(false)
		end
		return
	end
	-- groupes : en-têtes du panneau, dans leur ordre ; filtre 0 = tous
	state.repGroups = {}
	for _, row in ipairs(all) do
		if row.header then
			state.repGroups[#state.repGroups + 1] = row.name
		end
	end
	local wanted = state.repGroups[state.repGroup or 0]
	local rows, current = {}, nil
	for _, row in ipairs(all) do
		if row.header then
			current = row.name
		end
		if not wanted or current == wanted then
			rows[#rows + 1] = row
		end
	end
	_G.ForeverBridgeRepGroup:SetText("Groupe : " .. (wanted and wanted:gsub("|", "||") or "tous"))
	local pages = math.max(1, math.ceil(#rows / REP_ROWS))
	state.repPage = (state.repPage or 0) % pages
	_G.ForeverBridgeRepNext:SetShown(pages > 1)
	for i, widget in ipairs(S.repRows) do
		local row = rows[state.repPage * REP_ROWS + i]
		widget.faction = nil
		if row then
			local name = row.name:gsub("|", "||")
			if row.header then
				widget:SetText(name)
				widget:Disable()
			else
				widget:SetText("  " .. name .. " — " .. StandingLabel(row.reaction))
				widget:Enable()
				widget.faction = row
			end
			widget:SetShown(true)
		end
	end
	if state.repChosen then
		chosen:SetText("Faction choisie : " .. state.repChosen.name:gsub("|", "||") .. " · palier actuel : "
			.. StandingLabel(state.repChosen.reaction))
		value:SetText(StandingLabel(state.repTarget))
	else
		chosen:SetText("Choisissez une faction dans la liste, puis le palier visé.")
		value:SetText("—")
	end
end

local function BuildRoute(screen)
	local state = { kind = "leveling", dungeons = true, class = true }
	S.route = state
	local title = Text("ForeverBridgeRouteTitle", screen, "GameFontNormalLarge")
	Place(title, screen, 0, 0)
	title:SetText("Feuille de route")
	local who = Text("ForeverBridgeRouteWho", screen)
	Place(who, screen, 0, -ROW + 4)
	S.routeWho = who

	S.routeTypes = {}
	for i, kind in ipairs(ROUTE_TYPES) do
		local b = Button("ForeverBridgeRouteType_" .. kind.key, screen, kind.label, 100)
		Place(b, screen, (i - 1) * 106, -2 * ROW)
		b:SetScript("OnClick", function()
			state.kind = kind.key
			FB.RefreshRoute()
		end)
		S.routeTypes[kind.key] = b
	end

	local from = Text("ForeverBridgeRouteFromLabel", screen)
	Place(from, screen, 0, -3 * ROW - 4)
	from:SetText("Du niveau")
	S.routeFrom = Stepper("ForeverBridgeRouteFrom", screen, 80, -3 * ROW, function()
		return state.from
	end, function(v)
		state.from = math.max(1, v)
		if state.to <= state.from then
			state.to = state.from + 1
		end
	end)
	local to = Text("ForeverBridgeRouteToLabel", screen)
	Place(to, screen, 200, -3 * ROW - 4)
	to:SetText("au niveau")
	S.routeTo = Stepper("ForeverBridgeRouteTo", screen, 280, -3 * ROW, function()
		return state.to
	end, function(v)
		state.to = math.max(state.from + 1, v)
	end)

	local dungeons = Button("ForeverBridgeRouteDungeons", screen, "", 260)
	Place(dungeons, screen, 0, -4 * ROW)
	dungeons:SetScript("OnClick", function()
		state.dungeons = not state.dungeons
		FB.RefreshRoute()
	end)
	local class = Button("ForeverBridgeRouteClass", screen, "", 220)
	Place(class, screen, 266, -4 * ROW)
	class:SetScript("OnClick", function()
		state.class = not state.class
		FB.RefreshRoute()
	end)
	S.routeDungeons, S.routeClass = dungeons, class

	local unavailable = Text("ForeverBridgeRouteUnavailable", screen)
	Place(unavailable, screen, 0, -3 * ROW - 4)
	unavailable:SetWidth(340)
	S.routeUnavailable, S.routeScreen = unavailable, screen
	S.BuildReputation(screen, state)

	local compute = Button("ForeverBridgeRouteCompute", screen, "Calculer", 120)
	Place(compute, screen, 0, -6 * ROW - 6)
	compute:SetScript("OnClick", function()
		FB.ComputeRoute()
	end)
	local note = Text("ForeverBridgeRouteNote", screen, "GameFontHighlightSmall")
	Place(note, screen, 0, -7 * ROW - 6)
	note:SetText("L'aperçu et « Valider et livrer » arrivent dans le chat.")
	S.routeForm = { from, to, compute, note }
end

-- Sélecteur montré ou caché avec ses trois éléments (« < », valeur, « > »).
local function ShowStepper(prefix, shown)
	for _, suffix in ipairs({ "Down", "Value", "Up" }) do
		local widget = _G[prefix .. suffix]
		if widget then
			widget:SetShown(shown)
		end
	end
end

function FB.RefreshRoute()
	local state = S.route
	if not state then
		return
	end
	local name, level = Player()
	S.routeWho:SetText("Personnage : " .. (tostring(name):gsub("|", "||")) .. " · niveau " .. level)
	if not state.from then
		state.from, state.to = level, level + ROUTE_SPAN
	end
	for key, b in pairs(S.routeTypes) do
		-- type choisi : bouton grisé (comme les onglets Jeu et Addons), son nom reste lisible
		if key == state.kind then
			b:Disable()
		else
			b:Enable()
		end
	end
	S.routeDungeons:SetText("Donjons avec leurs quêtes : " .. (state.dungeons and "oui" or "non"))
	S.routeClass:SetText("Quêtes de classe : " .. (state.class and "oui" or "non"))
	local leveling = state.kind == "leveling"
	S.routeDungeons:SetShown(leveling)
	S.routeClass:SetShown(leveling)
	local computed = COMPUTED[state.kind] == true
	for _, widget in ipairs(S.routeForm) do
		widget:SetShown(computed)
	end
	ShowStepper("ForeverBridgeRouteFrom", computed)
	ShowStepper("ForeverBridgeRouteTo", computed)
	S.routeUnavailable:SetText(NOT_COMPUTED[state.kind] or "")
	S.routeUnavailable:SetShown(not computed)
	local reputation = state.kind == "reputation"
	-- réputation : le message vient sous la liste des factions et le palier visé
	Place(S.routeUnavailable, S.routeScreen, 0, reputation and (-4 * ROW - REP_ROWS * REP_ROW_H - 64)
		or (-3 * ROW - 4))
	S.RefreshReputation(reputation)
	S.routeFrom()
	S.routeTo()
end

function FB.ComputeRoute()
	local state = S.route
	local a, b = state.from, state.to
	if state.kind == "leveling" then
		local flags = { "lv=" .. a .. "-" .. b }
		if not state.dungeons then
			flags[#flags + 1] = "dj=none"
		end
		if not state.class then
			flags[#flags + 1] = "cq=no"
		end
		local question = "Prépare ma feuille de route de leveling du niveau " .. a .. " au niveau " .. b
			.. " et montre-moi l'aperçu ; je l'ajuste avec les boutons sous ta réponse."
		SendQuestion(question, "route", flags)
		return
	end
	if state.kind == "gear" then
		-- bloc 6b : même action que « En faire une route » de l'écran Équipement (traitée par le pont, bloc 4d)
		local label = "Route d'équipement du niveau " .. a .. " au niveau " .. b
		if FB.Send("", nil, { flags = { "a=gear_route:" .. a .. "-" .. b }, label = label }) then
			FB.ShowScreen("chat")
		end
	end
	-- type pas encore calculé : l'écran le dit (FB.RefreshRoute), rien n'est envoyé
end

---------------------------------------------------------------------------
-- Talents, Équipement, Exports
---------------------------------------------------------------------------

local function BuildTalents(screen)
	local title = Text("ForeverBridgeTalentsTitle", screen, "GameFontNormalLarge")
	Place(title, screen, 0, 0)
	title:SetText("Talents")
	local nextTalent = Button("ForeverBridgeTalentsNext", screen, "Mon prochain talent", 180)
	Place(nextTalent, screen, 0, -ROW)
	nextTalent:SetScript("OnClick", function()
		ClickKey("talents")
	end)
	local links = Button("ForeverBridgeTalentsLinks", screen, "Liens à copier", 140)
	Place(links, screen, 186, -ROW)
	links:SetScript("OnClick", function()
		FB.ShowScreen("exports")
	end)
	local note = Text("ForeverBridgeTalentsNote", screen, "GameFontHighlightSmall")
	Place(note, screen, 0, -2 * ROW - 4)
	note:SetText("Liens [Talents Forever] et [Naowh : build] : copier, puis coller dans l'addon.")
end

local function BuildGear(screen)
	local state = {}
	S.gear = state
	local title = Text("ForeverBridgeGearTitle", screen, "GameFontNormalLarge")
	Place(title, screen, 0, 0)
	title:SetText("Équipement")
	local label = Text("ForeverBridgeGearLevelLabel", screen)
	Place(label, screen, 0, -ROW - 4)
	label:SetText("Équipement pour le niveau")
	S.gearLevel = Stepper("ForeverBridgeGearLevel", screen, 180, -ROW, function()
		return state.level
	end, function(v)
		local before = state.level
		state.level = math.max(1, v)
		-- sans tranche choisie (haut = départ), ou haut dépassé : le haut de la tranche suit le départ
		if state.to == before or (state.to or 0) < state.level then
			state.to = state.level
			if S.gearTo then
				S.gearTo()
			end
		end
	end)
	-- bloc 4c : tranche de niveaux, une ligne par palier où l'objet visé change
	local toLabel = Text("ForeverBridgeGearToLabel", screen)
	Place(toLabel, screen, 290, -ROW - 4)
	toLabel:SetText("jusqu'au")
	S.gearTo = Stepper("ForeverBridgeGearTo", screen, 350, -ROW, function()
		return state.to
	end, function(v)
		state.to = math.max(state.level, v)
	end)
	local list = Button("ForeverBridgeGearList", screen, "Mon équipement à ce niveau", 210)
	Place(list, screen, 0, -2 * ROW)
	list:SetScript("OnClick", function()
		-- essai CJ-6 : action traitée par le pont sans le modèle (seule la sortie de l'outil, au niveau choisi)
		local label, levels = "Mon équipement au niveau " .. state.level, tostring(state.level)
		if state.to > state.level then
			label = "Mon équipement du niveau " .. state.level .. " au niveau " .. state.to
			levels = state.level .. "-" .. state.to
		end
		if FB.Send("", nil, { flags = { "a=gear_level:" .. levels }, label = label }) then
			FB.ShowScreen("chat")
		end
	end)
	local route = Button("ForeverBridgeGearRoute", screen, "En faire une route", 160)
	Place(route, screen, 216, -2 * ROW)
	route:SetScript("OnClick", function()
		-- bloc 4c : action traitée par le pont sans le modèle (objets obtenables au niveau choisi, jamais la route BiS) ;
		-- bloc 4d : une tranche choisie donne la route de ses objets
		local label, levels = "Route d'équipement au niveau " .. state.level, tostring(state.level)
		if state.to > state.level then
			label = "Route d'équipement du niveau " .. state.level .. " au niveau " .. state.to
			levels = state.level .. "-" .. state.to
		end
		if FB.Send("", nil, { flags = { "a=gear_route:" .. levels }, label = label }) then
			FB.ShowScreen("chat")
		end
	end)
	local bis = Button("ForeverBridgeGearBis", screen, "Ma liste BiS", 120)
	Place(bis, screen, 0, -3 * ROW)
	bis:SetScript("OnClick", function()
		SendQuestion("Donne ma liste BiS, avec les liens à copier.")
	end)
	local weights = Button("ForeverBridgeGearWeights", screen, "Liens à copier", 140)
	Place(weights, screen, 126, -3 * ROW)
	weights:SetScript("OnClick", function()
		FB.ShowScreen("exports")
	end)
	local note = Text("ForeverBridgeGearNote", screen, "GameFontHighlightSmall")
	Place(note, screen, 0, -4 * ROW - 4)
	note:SetText("Est-ce une amélioration ? Maj+clic sur un objet pendant la saisie, dans le chat.")
end

function FB.RefreshGear()
	if S.gear and not S.gear.level then
		local _, level = Player()
		S.gear.level, S.gear.to = level, level
	end
	if S.gearLevel then
		S.gearLevel()
		S.gearTo()
	end
end

local function BuildExports(screen)
	local title = Text("ForeverBridgeExportsTitle", screen, "GameFontNormalLarge")
	Place(title, screen, 0, 0)
	title:SetText("Exports")
	local ask = Button("ForeverBridgeExportsAsk", screen, "Demander les exports", 170)
	Place(ask, screen, 0, -ROW)
	ask:SetScript("OnClick", function()
		ClickKey("exports")
	end)
	local empty = Text("ForeverBridgeExportsEmpty", screen)
	Place(empty, screen, 0, -2 * ROW - 4)
	empty:SetText("Aucun export dans cette session : « Demander les exports », ou une question sur un build.")
	S.exportsEmpty = empty
	local eui = Text("ForeverBridgeExportsEui", screen, "GameFontHighlightSmall")
	S.exportsEui = eui
end

function FB.RefreshExports()
	local screen = S.screens.exports
	if not screen then
		return
	end
	local links = FB.SessionExports()
	S.exportsEmpty:SetShown(#links == 0)
	for i, item in ipairs(links) do
		local row = S.exportRows[i]
		if not row then
			row = {
				label = Text("ForeverBridgeExport" .. i .. "Label", screen),
				copy = Button("ForeverBridgeExport" .. i .. "Copy", screen, "Copier", 80),
			}
			S.exportRows[i] = row
		end
		local y = -(i + 1) * ROW
		Place(row.copy, screen, 0, y)
		Place(row.label, screen, 88, y - 4)
		row.label:SetText((tostring(item.label or item.kind or "Export"):gsub("|", "||")))
		row.copy:SetScript("OnClick", function()
			FB.ShowCopy(item.text)
		end)
		row.label:Show()
		row.copy:Show()
	end
	for i = #links + 1, #S.exportRows do
		S.exportRows[i].label:Hide()
		S.exportRows[i].copy:Hide()
	end
	local on = type(ForeverBridgeDB) == "table" and ForeverBridgeDB.eui == true
	S.exportsEui:SetText(on and "" or "EllesmereUI : éteint (/fb eui on pour ses liens de profil).")
	Place(S.exportsEui, screen, 0, -(math.max(#links, 1) + 2) * ROW)
end

---------------------------------------------------------------------------
-- Barre latérale, écrans, accueil, thème
---------------------------------------------------------------------------

function FB.ShowScreen(key)
	if not S.nav.chat then
		return
	end
	S.current = key
	for _, name in ipairs(SCREENS) do
		S.screens[name]:SetShown(name == key)
	end
	FB.ShowChat(key == "chat")
	local entry = S.nav[key]
	if entry then
		S.selected:ClearAllPoints()
		S.selected:SetPoint("TOPLEFT", entry, "TOPLEFT", -4, 0)
		S.selected:SetSize(4, NAV_ROW - 4)
		for navKey, button in pairs(S.nav) do
			S.labels[navKey]:SetTextColor(1, 1, 1, navKey == key and 1 or 0.7)
			-- deux repères pour l'entrée choisie : la barre d'accent et une étiquette plus vive
			if button.LockHighlight then
				if navKey == key then
					button:LockHighlight()
				else
					button:UnlockHighlight()
				end
			end
		end
	end
	if key == "route" then
		FB.RefreshRoute()
	elseif key == "gear" then
		FB.RefreshGear()
	elseif key == "exports" then
		FB.RefreshExports()
	end
end

local function NavClick(key)
	if key == "updates" then
		if (S.cards or 0) == 0 then
			FB.ShowScreen("chat")
			FB.Print("Mises à jour : aucune mise à jour en attente.")
		else
			FB.ToggleCards()
		end
	elseif key == "help" then
		S.welcome:Show()
		FB.Help()
	else
		FB.ShowScreen(key)
	end
end

function FB.OnCardsCount(count)
	S.cards = count
	local entry = S.nav.updates
	if entry then
		entry:SetText(count > 0 and ("Mises à jour (" .. count .. ")") or "Mises à jour")
	end
end

local function BuildWelcome(f)
	local welcome = CreateFrame("Frame", "ForeverBridgeWelcome", f, "BackdropTemplate")
	welcome:SetFrameLevel(60)
	welcome:SetSize(380, 130)
	welcome:SetPoint("CENTER", f, "CENTER", NAV_W / 2, 0)
	if welcome.SetBackdrop then
		welcome:SetBackdrop({
			bgFile = "Interface\\Buttons\\WHITE8X8",
			edgeFile = "Interface\\Buttons\\WHITE8X8",
			edgeSize = 1,
		})
		welcome:SetBackdropColor(0.08, 0.08, 0.1, 1)
		welcome:SetBackdropBorderColor(0.5, 0.5, 0.5, 1)
	end
	local text = Text("ForeverBridgeWelcomeText", welcome)
	text:SetPoint("TOPLEFT", welcome, "TOPLEFT", 12, -12)
	text:SetWidth(356)
	text:SetText("Bienvenue. Posez votre question en bas, ou choisissez un écran à gauche.\n"
		.. "Maj+clic sur un objet, un sort ou une quête : il part avec votre question.\n"
		.. "Les liens [ … ] se copient d'un clic ; collez-les dans l'addon indiqué.")
	local ok = Button("ForeverBridgeWelcomeOk", welcome, "Compris", 100)
	ok:SetPoint("BOTTOMRIGHT", welcome, "BOTTOMRIGHT", -10, 10)
	ok:SetScript("OnClick", function()
		welcome:Hide()
		if type(ForeverBridgeDB) == "table" then
			ForeverBridgeDB.welcomed = true
		end
	end)
	S.welcome = welcome
	welcome:SetShown(not (type(ForeverBridgeDB) == "table" and ForeverBridgeDB.welcomed))
end

function FB.BuildScreens(f)
	local nav = CreateFrame("Frame", "ForeverBridgeNav", f, "BackdropTemplate")
	nav:SetPoint("TOPLEFT", f, "TOPLEFT", 10, TOP)
	nav:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", 10, 12)
	nav:SetWidth(NAV_W - 20)
	if nav.SetBackdrop then
		nav:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8X8" })
		nav:SetBackdropColor(1, 1, 1, 0.04) -- fond à part : la navigation se distingue du contenu
	end
	local r, g, b, font = Theme()
	S.selected = nav:CreateTexture("ForeverBridgeNavSelected", "OVERLAY")
	S.selected:SetColorTexture(r, g, b, SELECTED_ALPHA * 2)
	S.labels = {}
	for i, item in ipairs(NAV) do
		local button = CreateFrame("Button", "ForeverBridgeNav_" .. item.key, nav)
		button:SetSize(NAV_W - 32, NAV_ROW - 4)
		local gap = item.key == "help" and NAV_ROW or 0 -- l'aide à part, sous les écrans
		button:SetPoint("TOPLEFT", nav, "TOPLEFT", 8, -6 - (i - 1) * NAV_ROW - gap)
		local label = button:CreateFontString("ForeverBridgeNav_" .. item.key .. "Label", "OVERLAY", "GameFontHighlight")
		label:SetPoint("LEFT", button, "LEFT", 6, 0)
		label:SetJustifyH("LEFT")
		if font then
			pcall(label.SetFont, label, font, LABEL_SIZE)
		end
		if button.SetFontString then
			button:SetFontString(label)
		end
		button:SetText(item.label)
		button:SetHighlightTexture("Interface\\Buttons\\WHITE8X8")
		local highlight = button.GetHighlightTexture and button:GetHighlightTexture()
		if highlight then
			highlight:SetVertexColor(r, g, b, SELECTED_ALPHA)
		end
		button:SetScript("OnClick", function()
			NavClick(item.key)
		end)
		S.nav[item.key] = button
		S.labels[item.key] = label
	end
	for _, key in ipairs(SCREENS) do
		local screen = CreateFrame("Frame", "ForeverBridgeScreen_" .. key, f)
		screen:SetPoint("TOPLEFT", f, "TOPLEFT", NAV_W, TOP)
		screen:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -14, 16)
		screen:Hide()
		S.screens[key] = screen
	end
	BuildRoute(S.screens.route)
	BuildTalents(S.screens.talents)
	BuildGear(S.screens.gear)
	BuildExports(S.screens.exports)
	BuildWelcome(f)
	FB.ShowScreen("chat")
	FB.RefreshCards()
end

function FB.LayoutScreens()
	FB.HideMore()
end
