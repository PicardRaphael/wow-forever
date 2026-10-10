-- Faute : fonction de Blizzard remplacée au lieu d'être accrochée.
local previous = ChatEdit_InsertLink
ChatEdit_InsertLink = function(link)
  return previous(link)
end
