local ADDON_NAME, FDJ = ...

local entrances = {
    ["Hall of Thanes"] = { mapID = 1426, x = 0.5, y = 0.4, label = "Ironforge", markerType = "dungeon" },
}

for name, e in pairs(entrances) do
    if FDJ.DB[name] then FDJ.DB[name].entrance = e end
end
