-- Faute : abonnement au journal de combat.
local frame = CreateFrame("Frame")
pcall(frame.RegisterEvent, frame, "COMBAT_LOG_EVENT_UNFILTERED")
