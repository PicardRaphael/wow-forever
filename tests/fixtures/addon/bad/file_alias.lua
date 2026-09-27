-- Faute : alias local de la SavedVariable au niveau du fichier (pointe vers une table perdue).
local db = ForeverLoggerDB
local frame = CreateFrame("Frame")
frame:SetScript("OnEvent", function(_, event, name)
  if event == "ADDON_LOADED" then
    ForeverLoggerDB = ForeverLoggerDB or {}
  end
end)
pcall(frame.RegisterEvent, frame, "ADDON_LOADED")
