local ADDON_NAME, FDJ = ...
local ALBA_FAIRMOON_LOCATION = FDJ.Constants.ALBA_FAIRMOON_LOCATION

FDJ.QUEST_PREREQ_CHAINS = {
    [96395] = { { id = 96391, name = "Underground Map" }, { id = 96392, name = "Ghostly Lead" } },
}

FDJ.QUEST_PREREQ_DETAILS = {
    [96391] = { level = 12, requires = 8, pickup = ALBA_FAIRMOON_LOCATION, turnin = ALBA_FAIRMOON_LOCATION },
}
