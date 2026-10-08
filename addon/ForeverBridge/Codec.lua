-- Codec de la bande de ForeverBridge (P06a) : Lua 5.1 pur, sans API du jeu ni bibliothèque bit, exécuté hors du jeu
-- par les tests (tests/unit/test_bridge_addon_lua.py) et comparé au codec Python du pont (forever/bridge/codec.py).
--
-- Message : [C7 1A] [numéro fort, faible] [longueur forte, faible] [charge] [Fletcher-16 s1, s2], somme sur
-- numéro..charge. Les octets sont découpés en cellules de trois bits, poids fort d'abord ; chaque cellule est un carré
-- dont les canaux R, G et B sont tout allumés ou tout éteints (bit 2 = R, bit 1 = G, bit 0 = B) : huit couleurs pures,
-- qui résistent au gamma et au contraste.
--
-- Contient du code adapté de wow-ai (https://github.com/chelinho139/wow-ai, commit 3756eb5a : addon/WoWAI/Codec.lua),
-- sous la licence suivante :
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

ForeverBridge_Codec = {}
local C = ForeverBridge_Codec

C.MAGIC1, C.MAGIC2 = 0xC7, 0x1A
C.BITS = 3
C.CELLS_PER_ROW = 200
C.MAX_ROWS = 24
C.MAX_PAYLOAD = 1792 -- 24 rangées de 200 cellules, moins l'en-tête et la somme
C.SELFTEST_ID = 4242 -- numéro de la bande de test (/fv test)

function C.Fletcher16(bytes, from, to)
	local s1, s2 = 0, 0
	for i = from, to do
		s1 = (s1 + bytes[i]) % 255
		s2 = (s2 + s1) % 255
	end
	return s1, s2
end

-- Cellules (valeurs 0 à 7) du message ; nil et la raison si la charge dépasse la bande.
function C.Encode(id, payload)
	local len = #payload
	if len > C.MAX_PAYLOAD then
		return nil, "message trop long pour la bande"
	end
	local bytes = {
		C.MAGIC1, C.MAGIC2,
		math.floor(id / 256) % 256, id % 256,
		math.floor(len / 256) % 256, len % 256,
	}
	for i = 1, len do
		bytes[#bytes + 1] = payload:byte(i)
	end
	local s1, s2 = C.Fletcher16(bytes, 3, 6 + len)
	bytes[#bytes + 1] = s1
	bytes[#bytes + 1] = s2

	local BITS = C.BITS
	local base = 2 ^ BITS
	local cells = {}
	local acc, nbits = 0, 0
	for i = 1, #bytes do
		acc = acc * 256 + bytes[i]
		nbits = nbits + 8
		while nbits >= BITS do
			local shift = nbits - BITS
			cells[#cells + 1] = math.floor(acc / 2 ^ shift) % base
			nbits = shift
			acc = acc % 2 ^ nbits
		end
	end
	if nbits > 0 then
		cells[#cells + 1] = (acc * 2 ^ (BITS - nbits)) % base
	end
	return cells
end

-- Couleur d'une cellule : chaque canal tout allumé (1) ou tout éteint (0).
function C.CellColor(v)
	local r = math.floor(v / 4) % 2
	local g = math.floor(v / 2) % 2
	local b = v % 2
	return r, g, b
end

-- Charge de la bande de test : l'octet i vaut i modulo 256, sur toute la charge (toutes les rangées, toutes les couleurs).
function C.SelftestPayload()
	local parts = {}
	for i = 0, C.MAX_PAYLOAD - 1 do
		parts[#parts + 1] = string.char(i % 256)
	end
	return table.concat(parts)
end
