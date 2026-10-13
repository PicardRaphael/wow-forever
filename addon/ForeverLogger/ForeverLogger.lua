-- ForeverLogger : active le journal de combat avancé à chaque connexion et note le contexte du personnage
-- (niveau, talents, bonus des sorts, gains d'expérience) dans la SavedVariable ForeverLoggerDB, lue hors du jeu
-- par forever (forever/pipeline/addon_sv.py) et jointe aux journaux de combat par GUID et par heure.
-- CH0 : hors combat, instantané du familier du Chasseur et des statistiques du Chasseur au même instant, et relevé
-- de la fenêtre Beast Training (capacités offertes, rang, coût en points d'entraînement, niveau requis).
-- T04d (0.4.0) : montant de chaque gain d'XP, monstre tué (niveau, classification, PNJ) quand la cible ou une plaque
-- de nom le montre, état de l'XP et du repos (xp_states), instance, groupe, carte ; quêtes acceptées et rendues
-- (ID, xpReward) ; erreurs des gestionnaires comptées dans ForeverLoggerDB.errors ; résumé par /flog.
-- T04f (0.5.0, schéma 3) : auras actives du joueur (sort, cumuls, temps restant) dans chaque état de l'XP et chaque
-- gain ; rangs des perks Legacy lus hors combat (arbres donnés par ForeverBridge depuis les données, jamais écrits
-- ici), gardés dans legacy.
-- DJ1 (0.6.0, schéma 4) : passages en instance (entrée, sortie, rencontres de ENCOUNTER_END) dans runs, butin
-- ramassé (objet, quantité, PNJ source par GetLootSourceInfo) dans loot.
--
-- Règles (docs/ADDON.md) :
-- * ForeverLoggerDB est initialisée dans ADDON_LOADED, jamais d'alias local au niveau du fichier ;
-- * pcall autour de chaque RegisterEvent et de chaque API incertaine ; une valeur secrète donne un champ absent ;
-- * aucune fonction d'action, aucun message de discussion automatique ;
-- * aucun abonnement au journal de combat : l'analyse se fait hors du jeu, sur WoWCombatLog-*.txt.

local ADDON_NAME = ...
local SCHEMA = 4
local MAX_AURAS = 16 -- auras gardées par relevé
local AURA_SCAN = 40 -- auras parcourues au plus
local MAX_ENTRIES = 5000 -- entrées gardées par liste (instantanés, gains d'expérience)
local MAX_NAMEPLATES = 40 -- jetons nameplate1… parcourus pour trouver le monstre tué
local MAX_SEEN = 200 -- noms de monstres vus gardés avant remise à zéro
local RECENT_WINDOW = 3 -- écart maximal (horloge GetTime) entre plaque retirée sur une unité morte et gain d'XP
local SCHOOLS = { holy = 2, fire = 3, nature = 4, frost = 5, shadow = 6, arcane = 7 } -- indices d'école de l'API

local frame = CreateFrame("Frame")

-- Valeur secrète (restrictions de Midnight appliquées à Forever) : traitée comme absente.
local function isSecret(value)
  local ok, secret = pcall(issecretvalue, value)
  return ok and secret == true
end

-- Appel protégé d'une API incertaine : nil en cas d'erreur, d'API absente ou de valeur secrète.
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

-- Deuxième valeur de retour d'une API (nom de fichier de la race…), protégée comme safe.
local function second(fn, ...)
  if type(fn) ~= "function" then
    return nil
  end
  local ok, _, value = pcall(fn, ...)
  if not ok or isSecret(value) then
    return nil
  end
  return value
end

-- Toutes les valeurs de retour d'une API, protégées comme safe : { [position] = valeur }, trous pour les valeurs
-- secrètes ou absentes ; nil si l'API manque ou lève une erreur.
local function pack(...)
  return { n = select("#", ...), ... }
end

local function returns(fn, ...)
  if type(fn) ~= "function" then
    return nil
  end
  local results = pack(pcall(fn, ...))
  if not results[1] then
    return nil
  end
  local out = {}
  for i = 2, results.n do
    local value = results[i]
    if value ~= nil and not isSecret(value) then
      out[i - 1] = value
    end
  end
  return out
end

local function push(list, entry)
  table.insert(list, entry)
  while #list > MAX_ENTRIES do
    table.remove(list, 1)
  end
end

-- Rangs de talents achetés (arbre de traits du moteur Mainline) : { [nodeID] = rang }.
local function readTalents()
  local configID = safe(C_ClassTalents and C_ClassTalents.GetActiveConfigID)
  if not configID or type(C_Traits) ~= "table" then
    return nil
  end
  local config = safe(C_Traits.GetConfigInfo, configID)
  if type(config) ~= "table" or type(config.treeIDs) ~= "table" then
    return nil
  end
  local ranks = {}
  for _, treeID in ipairs(config.treeIDs) do
    local nodes = safe(C_Traits.GetTreeNodes, treeID)
    if type(nodes) == "table" then
      for _, nodeID in ipairs(nodes) do
        local node = safe(C_Traits.GetNodeInfo, configID, nodeID)
        if type(node) == "table" and type(node.ranksPurchased) == "number" and node.ranksPurchased > 0 then
          ranks[nodeID] = node.ranksPurchased
        end
      end
    end
  end
  return ranks
end

local function readSchools(fn)
  local values = {}
  for name, index in pairs(SCHOOLS) do
    values[name] = safe(fn, index)
  end
  return values
end

local function character()
  local guid = safe(UnitGUID, "player")
  if not guid then
    return nil
  end
  local entry = ForeverLoggerDB.characters[guid]
  if not entry then
    entry = { snapshots = {}, xp = {} }
    ForeverLoggerDB.characters[guid] = entry
  end
  entry.name = safe(UnitName, "player")
  entry.realm = safe(GetRealmName)
  entry.class = safe(UnitClassBase, "player")
  entry.race = second(UnitRace, "player")
  return entry
end

local function stamp(entry)
  entry.time = safe(GetServerTime)
  entry.localtime = safe(date, "%m/%d/%Y %H:%M:%S") -- heure locale, comme les journaux de combat
  return entry
end

local function nextSeq()
  ForeverLoggerDB.seq = (ForeverLoggerDB.seq or 0) + 1
  return ForeverLoggerDB.seq
end

-- XP du personnage et réserve de repos (GetXPExhaustion : nil sans repos).
local function readState()
  return {
    xp = safe(UnitXP, "player"),
    max = safe(UnitXPMax, "player"),
    rested = safe(GetXPExhaustion),
    rest_state = safe(GetRestState),
  }
end

-- Auras utiles du joueur : { spell, stacks, remaining } (remaining absent : sans fin) ; nil si l'API manque ou échoue.
local function readAuras()
  if type(C_UnitAuras) ~= "table" or type(C_UnitAuras.GetAuraDataByIndex) ~= "function" then
    return nil
  end
  local now = safe(GetTime)
  local out = {}
  for index = 1, AURA_SCAN do
    local ok, aura = pcall(C_UnitAuras.GetAuraDataByIndex, "player", index, "HELPFUL")
    if not ok then
      return nil
    end
    if type(aura) ~= "table" or isSecret(aura) then
      break
    end
    local id = aura.spellId
    if type(id) == "number" and not isSecret(id) then
      local stacks = aura.applications
      if type(stacks) ~= "number" or isSecret(stacks) or stacks < 1 then
        stacks = 1
      end
      local remaining = nil
      local expires = aura.expirationTime
      if type(expires) == "number" and not isSecret(expires) and expires > 0 and type(now) == "number" then
        remaining = math.floor(expires - now + 0.5)
      end
      out[#out + 1] = { spell = id, stacks = stacks, remaining = remaining }
      if #out >= MAX_AURAS then
        break
      end
    end
  end
  return out
end

local function pushState(reason, level)
  local entry = character()
  if not entry then
    return
  end
  local state = readState()
  entry.xp_states = entry.xp_states or {}
  push(entry.xp_states, stamp({
    seq = nextSeq(),
    reason = reason,
    level = level or safe(UnitLevel, "player"),
    xp = state.xp,
    max = state.max,
    rested = state.rested,
    rest_state = state.rest_state,
    resting = safe(IsResting),
    auras = readAuras(),
  }))
end

-- Rangs des perks Legacy (compte) : { trees = { [arbre] = { [nœud] = rang } } }, hors combat seulement ; arbres lus
-- dans la liste écrite par ForeverBridge (ForeverBridgeStatus.xp.legacy_trees) ; rien si l'API échoue.
local pendingLegacy = false

local function readLegacy()
  local entry = character()
  local status = ForeverBridgeStatus
  if not entry or type(status) ~= "table" or type(status.xp) ~= "table" or type(status.xp.legacy_trees) ~= "table" then
    return
  end
  if safe(InCombatLockdown) then
    pendingLegacy = true
    return
  end
  pendingLegacy = false
  if type(C_Traits) ~= "table" then
    return
  end
  local trees = {}
  local found = false
  for _, tree in ipairs(status.xp.legacy_trees) do
    local config = safe(C_Traits.GetConfigIDByTreeID, tree)
    local nodes = config and safe(C_Traits.GetTreeNodes, tree)
    if type(nodes) == "table" then
      local ranks = {}
      for _, node in ipairs(nodes) do
        local info = safe(C_Traits.GetNodeInfo, config, node)
        if type(info) == "table" and type(info.ranksPurchased) == "number" then
          ranks[node] = info.ranksPurchased
        end
      end
      trees[tree] = ranks
      found = true
    end
  end
  if found then
    entry.legacy = stamp({ trees = trees })
  end
end

local function currentMap()
  return safe(C_Map and C_Map.GetBestMapForUnit, "player")
end

local function instanceInfo()
  local where = returns(IsInInstance)
  if not where then
    return nil
  end
  local info = { inside = where[1], type = where[2] }
  if where[1] then
    local details = returns(GetInstanceInfo)
    if details then
      info.name = details[1]
      info.id = details[8]
    end
  end
  return info
end

local function groupInfo()
  local group = { size = safe(GetNumGroupMembers), raid = safe(IsInRaid) }
  if type(group.size) == "number" and group.size > 0 then
    local levels = {}
    for i = 1, 4 do
      local level = safe(UnitLevel, "party" .. i)
      if type(level) == "number" then
        table.insert(levels, level)
      end
    end
    if #levels > 0 then
      group.levels = levels
    end
  end
  return group
end

-- DJ1 : identifiant du PNJ d'un GUID de créature (« Creature-0-serveur-instance-zone-PNJ-apparition »).
local function npcOf(guid)
  if type(guid) ~= "string" then
    return nil
  end
  local kind, npc = guid:match("^(%a+)%-%d+%-%d+%-%d+%-%d+%-(%d+)%-")
  if kind == "Creature" or kind == "Vehicle" then
    return tonumber(npc)
  end
  return nil
end

local RUN_TYPES = { party = true, raid = true } -- instances dont le passage est relevé

-- Passage ouvert (dernier passage sans heure de sortie) ou nil.
local function openRun(entry)
  local last = entry.runs and entry.runs[#entry.runs]
  if last and last.left == nil then
    return last
  end
  return nil
end

-- DJ1 : entrée ou sortie d'instance, vue à chaque changement de zone ; une instance illisible ne change rien.
local function updateRun()
  local entry = character()
  if not entry then
    return
  end
  local info = instanceInfo()
  if not info then
    return
  end
  entry.runs = entry.runs or {}
  local open = openRun(entry)
  local now = safe(GetServerTime)
  if info.inside and RUN_TYPES[info.type] and info.id then
    if open and open.id == info.id then
      return
    end
    if open then
      open.left = now
    end
    local details = returns(GetInstanceInfo)
    push(entry.runs, {
      seq = nextSeq(),
      instance = info.name,
      id = info.id,
      type = info.type,
      difficulty = details and details[3],
      level = safe(UnitLevel, "player"),
      group = safe(GetNumGroupMembers),
      entered = now,
      encounters = {},
    })
  elseif open then
    open.left = now
  end
end

local function snapshot(reason, level)
  local entry = character()
  if not entry then
    return
  end
  push(entry.snapshots, stamp({
    reason = reason,
    level = level or safe(UnitLevel, "player"),
    talents = readTalents(),
    spell_bonus = readSchools(GetSpellBonusDamage),
    spell_crit = readSchools(GetSpellCritChance),
    trivial_range = safe(UnitQuestTrivialLevelRange, "player"),
    state = readState(),
    resting = safe(IsResting),
  }))
end

-- Monstre tué : cible morte du même nom, sinon plaque de nom morte, sinon plaque retirée sur une unité morte juste
-- avant le gain, sinon niveaux vus pour ce nom (cible, plaques) depuis l'entrée dans la zone.
local seen, seenCount, recentDead = {}, 0, {}

local function npcFromGUID(guid)
  if type(guid) ~= "string" then
    return nil
  end
  local id = guid:match("^%a+%-%d+%-%d+%-%d+%-%d+%-(%d+)%-")
  return id and tonumber(id)
end

local function unitInfo(unit, source)
  return {
    name = safe(UnitName, unit),
    level = safe(UnitLevel, unit),
    classification = safe(UnitClassification, unit),
    npc = npcFromGUID(safe(UnitGUID, unit)),
    creature_type = safe(UnitCreatureType, unit),
    source = source,
  }
end

local function isDeadNamed(unit, name)
  return safe(UnitExists, unit) and safe(UnitName, unit) == name and safe(UnitIsDead, unit) == true
end

local function remember(unit)
  if not safe(UnitExists, unit) or safe(UnitIsPlayer, unit) then
    return
  end
  local name, level = safe(UnitName, unit), safe(UnitLevel, unit)
  if type(name) ~= "string" or type(level) ~= "number" then
    return
  end
  if not seen[name] then
    seenCount = seenCount + 1
    if seenCount > MAX_SEEN then
      seen, seenCount = {}, 1
    end
    seen[name] = {}
  end
  seen[name][level] = true
end

local function forgetSeen()
  seen, seenCount, recentDead = {}, 0, {}
end

local function findKilled(name)
  if isDeadNamed("target", name) then
    return unitInfo("target", "target")
  end
  for i = 1, MAX_NAMEPLATES do
    local unit = "nameplate" .. i
    if isDeadNamed(unit, name) then
      return unitInfo(unit, "nameplate")
    end
  end
  local recent, now = recentDead[name], safe(GetTime)
  if recent then
    recentDead[name] = nil
    if type(now) == "number" and type(recent.at) == "number" and now - recent.at <= RECENT_WINDOW then
      return recent.info
    end
  end
  return nil
end

local function seenLevels(name)
  local levels = {}
  for level in pairs(seen[name] or {}) do
    table.insert(levels, level)
  end
  table.sort(levels)
  return #levels > 0 and levels or nil
end

-- Résumé de la session pour /flog (vérification en jeu pendant une sonde).
local session = { gains = 0, last = nil, quest = nil }

local function questLevel(id)
  local index = safe(C_QuestLog and C_QuestLog.GetLogIndexForQuestID, id)
  if index then
    local info = safe(C_QuestLog.GetInfo, index)
    if type(info) == "table" and type(info.level) == "number" then
      return info.level
    end
    local row = returns(GetQuestLogTitle, index)
    return row and row[2]
  end
  local count = safe(GetNumQuestLogEntries)
  if type(count) == "number" then
    for i = 1, count do
      local row = returns(GetQuestLogTitle, i)
      if row and row[8] == id then
        return row[2]
      end
    end
  end
  return nil
end

local function questEvent(event, id, xpReward, moneyReward)
  local entry = character()
  if not entry or type(id) ~= "number" then
    return
  end
  entry.quests = entry.quests or {}
  local record = stamp({
    event = event,
    seq = nextSeq(),
    quest_id = id,
    title = safe(C_QuestLog and C_QuestLog.GetTitleForQuestID, id),
    quest_level = questLevel(id),
    xp_reward = xpReward,
    money_reward = moneyReward,
    level = safe(UnitLevel, "player"),
    state = readState(),
    resting = safe(IsResting),
    map = currentMap(),
    instance = instanceInfo(),
    group = groupInfo(),
  })
  push(entry.quests, record)
  if event == "turned_in" then
    session.quest = record
  end
end

-- CH0 : familier du Chasseur et statistiques du Chasseur au même instant, hors combat seulement.
local STAMINA = LE_UNIT_STAT_STAMINA or 3 -- indice de statistique de l'API (Endurance)
local pendingPet = false

local function petState()
  return {
    family = safe(UnitCreatureFamily, "pet"),
    name = safe(UnitName, "pet"),
    level = safe(UnitLevel, "pet"),
    health_max = safe(UnitHealthMax, "pet"),
    armor = returns(UnitArmor, "pet"),
    attack_speed = safe(UnitAttackSpeed, "pet"),
    attack_power = returns(UnitAttackPower, "pet"),
    loyalty = safe(GetPetLoyalty),
    happiness = returns(GetPetHappiness),
    training_points = returns(GetPetTrainingPoints),
    diet = returns(GetPetFoodTypes),
  }
end

local function hunterState()
  return {
    stamina = returns(UnitStat, "player", STAMINA),
    armor = returns(UnitArmor, "player"),
    attack_power = returns(UnitAttackPower, "player"),
    ranged_attack_power = returns(UnitRangedAttackPower, "player"),
    crit = safe(GetCritChance),
    ranged_crit = safe(GetRangedCritChance),
  }
end

local function snapshotPet(reason)
  if safe(InCombatLockdown) then
    pendingPet = true -- repris à la sortie du combat (PLAYER_REGEN_ENABLED)
    return
  end
  pendingPet = false
  if not safe(UnitExists, "pet") then
    return
  end
  local entry = character()
  if not entry then
    return
  end
  entry.pet_snapshots = entry.pet_snapshots or {}
  push(entry.pet_snapshots, stamp({
    reason = reason,
    level = safe(UnitLevel, "player"),
    pet = petState(),
    hunter = hunterState(),
  }))
end

-- Fenêtre Beast Training (fenêtre d'artisanat du client) : capacités offertes au familier, rang, coût, niveau requis.
local function readTraining()
  if safe(InCombatLockdown) then
    return
  end
  local entry = character()
  local count = safe(GetNumCrafts)
  if not entry or type(count) ~= "number" or count <= 0 then
    return
  end
  local rows = {}
  for index = 1, count do
    local info = returns(GetCraftInfo, index)
    if info then
      table.insert(rows, {
        name = info[1],
        rank = info[2],
        type = info[3],
        cost = info[6],
        level = info[7],
      })
    end
  end
  entry.training = entry.training or {}
  push(entry.training, stamp({
    skill_line = safe(GetCraftDisplaySkillLine),
    family = safe(UnitCreatureFamily, "pet"),
    pet_level = safe(UnitLevel, "pet"),
    entries = rows,
  }))
end

local function enableCombatLog()
  pcall(SetCVar, "advancedCombatLogging", 1)
  local logging = safe(LoggingCombat)
  if not logging then
    pcall(LoggingCombat, true)
    print("|cff69ccf0ForeverLogger|r : journal de combat activé")
  end
end

local handlers = {}

function handlers.ADDON_LOADED(name)
  if name ~= ADDON_NAME then
    return
  end
  -- Les SavedVariables sont chargées après l'exécution du fichier : on les initialise ici, jamais avant.
  ForeverLoggerDB = ForeverLoggerDB or {}
  ForeverLoggerDB.schema = SCHEMA
  ForeverLoggerDB.characters = ForeverLoggerDB.characters or {}
end

function handlers.PLAYER_LOGIN()
  snapshot("connexion")
  snapshotPet("connexion")
  pushState("connexion")
  readLegacy()
end

function handlers.PLAYER_ENTERING_WORLD()
  enableCombatLog()
  forgetSeen()
  updateRun()
end

function handlers.ZONE_CHANGED_NEW_AREA()
  forgetSeen()
  updateRun()
end

-- ENCOUNTER_END : (rencontre, nom, difficulté, taille du groupe, succès 1 ou 0).
function handlers.ENCOUNTER_END(id, name, _, _, success)
  local entry = character()
  local run = entry and openRun(entry)
  if not run then
    return
  end
  run.encounters = run.encounters or {}
  table.insert(run.encounters, { id = id, name = name, success = success == 1, time = safe(GetServerTime) })
end

-- LOOT_OPENED : objets de la fenêtre de butin, quantité, GUID et PNJ de la source (monnaie sans lien : ignorée).
function handlers.LOOT_OPENED()
  local entry = character()
  if not entry then
    return
  end
  local items = {}
  for slot = 1, safe(GetNumLootItems) or 0 do
    local link = safe(GetLootSlotLink, slot)
    local item = type(link) == "string" and tonumber(link:match("item:(%d+)")) or nil
    if item then
      local info = returns(GetLootSlotInfo, slot)
      local sources = returns(GetLootSourceInfo, slot)
      local guid = sources and sources[1]
      table.insert(items, {
        item = item,
        quantity = info and info[3],
        source = type(guid) == "string" and guid or nil,
        npc = npcOf(guid),
      })
    end
  end
  if #items == 0 then
    return
  end
  local info = instanceInfo()
  entry.loot = entry.loot or {}
  push(entry.loot, stamp({
    seq = nextSeq(),
    instance = info and info.inside and info.id or nil,
    items = items,
  }))
end

function handlers.PLAYER_LEVEL_UP(level)
  snapshot("niveau", level) -- UnitLevel peut encore renvoyer l'ancien niveau
  pushState("niveau", level)
end

function handlers.PLAYER_XP_UPDATE(unit)
  if unit == nil or unit == "player" then
    pushState("xp")
  end
end

function handlers.UPDATE_EXHAUSTION()
  pushState("repos")
end

function handlers.PLAYER_UPDATE_RESTING()
  pushState("repos")
end

function handlers.PLAYER_TARGET_CHANGED()
  remember("target")
end

function handlers.NAME_PLATE_UNIT_ADDED(unit)
  remember(unit)
end

function handlers.NAME_PLATE_UNIT_REMOVED(unit)
  if safe(UnitIsDead, unit) == true then
    local name = safe(UnitName, unit)
    if type(name) == "string" then
      recentDead[name] = { info = unitInfo(unit, "recent"), at = safe(GetTime) }
    end
  end
end

-- QUEST_ACCEPTED : (questID) sur le moteur Mainline, (index du journal, questID) sur Classic.
function handlers.QUEST_ACCEPTED(first, second)
  questEvent("accepted", second or first)
end

function handlers.QUEST_TURNED_IN(id, xpReward, moneyReward)
  questEvent("turned_in", id, xpReward, moneyReward)
end

function handlers.TRAIT_CONFIG_UPDATED()
  snapshot("talents")
  readLegacy()
end

function handlers.UNIT_PET(unit)
  if unit == "player" then
    snapshotPet("familier")
  end
end

function handlers.PET_UI_UPDATE()
  snapshotPet("fenetre")
end

function handlers.PLAYER_REGEN_ENABLED()
  if pendingPet then
    snapshotPet("apres-combat")
  end
  if pendingLegacy then
    readLegacy()
  end
end

function handlers.CRAFT_SHOW()
  readTraining()
end

function handlers.CRAFT_UPDATE()
  readTraining()
end

-- Montant lu dans le texte (anglais et français) ; le texte brut reste la référence (relu hors du jeu).
local function amountOf(text)
  local raw = text:match("gain ([%d,]+)") or text:match("gagnez ([%d,]+)")
  return raw and tonumber((raw:gsub(",", "")))
end

function handlers.CHAT_MSG_COMBAT_XP_GAIN(text)
  local entry = character()
  if not entry then
    return
  end
  if type(text) ~= "string" or isSecret(text) then
    text = nil
  end
  local monster = text and (text:match("^(.-) dies, ") or text:match("^(.-) meurt, "))
  local amount = text and amountOf(text)
  local gain = stamp({
    seq = nextSeq(),
    level = safe(UnitLevel, "player"),
    text = text,
    amount = amount,
    kind = monster and "monster" or (amount and "other" or "unknown"),
    monster = monster,
    state = readState(),
    resting = safe(IsResting),
    auras = readAuras(),
    instance = instanceInfo(),
    group = groupInfo(),
    map = currentMap(),
  })
  if monster then
    gain.target = findKilled(monster)
    if not gain.target then
      gain.seen_levels = seenLevels(monster)
    end
  end
  push(entry.xp, gain)
  session.gains = session.gains + 1
  session.last = gain
end

local function report()
  local lines = { "|cff69ccf0ForeverLogger|r : " .. session.gains .. " gain(s) d'XP relevé(s) pendant cette session" }
  local state = readState()
  table.insert(lines, "XP " .. tostring(state.xp) .. " / " .. tostring(state.max) .. ", repos : "
    .. (state.rested and tostring(state.rested) or "aucun") .. (safe(IsResting) and " (au repos)" or ""))
  local last = session.last
  if last then
    local line = "Dernier gain : +" .. tostring(last.amount) .. " XP (" .. (last.monster or "hors monstre") .. ")"
    if last.target then
      line = line .. ", niveau du monstre " .. tostring(last.target.level) .. " (" .. last.target.source .. ")"
    elseif last.seen_levels then
      line = line .. ", niveaux vus " .. table.concat(last.seen_levels, ", ")
    elseif last.monster then
      line = line .. ", niveau du monstre inconnu"
    end
    table.insert(lines, line)
  end
  local quest = session.quest
  if quest then
    table.insert(lines, "Dernière quête rendue : " .. quest.quest_id .. " " .. (quest.title or "") .. ", "
      .. tostring(quest.xp_reward) .. " XP")
  end
  local errors = 0
  for _, e in pairs(ForeverLoggerDB.errors or {}) do
    errors = errors + (e.count or 0)
  end
  if errors > 0 then
    table.insert(lines, "Erreurs relevées : " .. errors)
  end
  for _, line in ipairs(lines) do
    print(line)
  end
end

-- Erreur d'un gestionnaire : comptée par événement (dernier message gardé), jamais remontée au joueur.
local function recordError(event, err)
  pcall(function()
    ForeverLoggerDB.errors = ForeverLoggerDB.errors or {}
    local e = ForeverLoggerDB.errors[event] or { count = 0 }
    e.count = e.count + 1
    e.last = tostring(err):sub(1, 200)
    ForeverLoggerDB.errors[event] = e
  end)
end

frame:SetScript("OnEvent", function(_, event, ...)
  local handler = handlers[event]
  if handler and (event == "ADDON_LOADED" or ForeverLoggerDB ~= nil) then
    local ok, err = pcall(handler, ...)
    if not ok and ForeverLoggerDB ~= nil then
      recordError(event, err)
    end
  end
end)

SLASH_FOREVERLOGGER1 = "/flog"
SlashCmdList.FOREVERLOGGER = function()
  if ForeverLoggerDB ~= nil then
    pcall(report)
  end
end

-- Un événement inconnu du client lève une erreur : chaque abonnement est protégé.
for event in pairs(handlers) do
  pcall(frame.RegisterEvent, frame, event)
end
