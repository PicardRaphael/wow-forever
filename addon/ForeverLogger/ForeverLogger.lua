-- ForeverLogger : active le journal de combat avancé à chaque connexion et note le contexte du personnage
-- (niveau, talents, bonus des sorts, gains d'expérience) dans la SavedVariable ForeverLoggerDB, lue hors du jeu
-- par forever (forever/pipeline/addon_sv.py) et jointe aux journaux de combat par GUID et par heure.
-- CH0 : hors combat, instantané du familier du Chasseur et des statistiques du Chasseur au même instant, et relevé
-- de la fenêtre Beast Training (capacités offertes, rang, coût en points d'entraînement, niveau requis).
--
-- Règles (docs/ADDON.md) :
-- * ForeverLoggerDB est initialisée dans ADDON_LOADED, jamais d'alias local au niveau du fichier ;
-- * pcall autour de chaque RegisterEvent et de chaque API incertaine ; une valeur secrète donne un champ absent ;
-- * aucune fonction d'action, aucun message de discussion automatique ;
-- * aucun abonnement au journal de combat : l'analyse se fait hors du jeu, sur WoWCombatLog-*.txt.

local ADDON_NAME = ...
local SCHEMA = 1
local MAX_ENTRIES = 5000 -- entrées gardées par liste (instantanés, gains d'expérience)
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
  }))
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
end

function handlers.PLAYER_ENTERING_WORLD()
  enableCombatLog()
end

function handlers.PLAYER_LEVEL_UP(level)
  snapshot("niveau", level) -- UnitLevel peut encore renvoyer l'ancien niveau
end

function handlers.TRAIT_CONFIG_UPDATED()
  snapshot("talents")
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
end

function handlers.CRAFT_SHOW()
  readTraining()
end

function handlers.CRAFT_UPDATE()
  readTraining()
end

function handlers.CHAT_MSG_COMBAT_XP_GAIN(text)
  local entry = character()
  if entry then
    push(entry.xp, stamp({ level = safe(UnitLevel, "player"), text = text }))
  end
end

frame:SetScript("OnEvent", function(_, event, ...)
  local handler = handlers[event]
  if handler and (event == "ADDON_LOADED" or ForeverLoggerDB ~= nil) then
    pcall(handler, ...)
  end
end)

-- Un événement inconnu du client lève une erreur : chaque abonnement est protégé.
for event in pairs(handlers) do
  pcall(frame.RegisterEvent, frame, event)
end
