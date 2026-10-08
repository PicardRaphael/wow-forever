"""Retour bureau → jeu (P06a) : fichiers sons servant de drapeaux et réserve d'emplacements chargés à la demande.

Un fichier son vide « ne jouera pas », un WAV valide « jouera » (`PlaySoundFile`, mesuré par wow-ai, contrôlé en jeu
par l'autotest `/fv diag`) : le pont lève un drapeau en écrivant `SILENT_WAV` dans un fichier vide préinstallé.

Contient du code adapté de wow-ai (https://github.com/chelinho139/wow-ai, commit 3756eb5a : `bridge/protocol.js`,
`bridge/bridge.js`), sous la licence suivante :

MIT License

Copyright (c) 2026 chelinho139

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

from __future__ import annotations

import struct


def _silent_wav(rate: int = 8000, samples: int = 80) -> bytes:
    fmt = struct.pack("<HHIIHH", 1, 1, rate, rate, 1, 8)  # PCM, mono, octets par seconde, bloc, bits
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", samples)
    return b"RIFF" + struct.pack("<I", len(body) + samples) + body + bytes([128]) * samples


# WAV PCM valide et silencieux : 8 bits, mono, 8 000 Hz, 80 échantillons à 128 (10 ms), 124 octets.
SILENT_WAV: bytes = _silent_wav()
