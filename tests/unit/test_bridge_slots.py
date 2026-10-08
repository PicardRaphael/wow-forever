"""Drapeaux et emplacements du pont (P06a). Bloc A : le WAV silencieux des drapeaux (porté de wow-ai)."""

from forever.bridge.slots import SILENT_WAV


def test_silent_wav():
    assert len(SILENT_WAV) == 124
    assert SILENT_WAV[:4] == b"RIFF" and SILENT_WAV[8:12] == b"WAVE"
    assert int.from_bytes(SILENT_WAV[4:8], "little") == 116
    assert SILENT_WAV[12:16] == b"fmt " and int.from_bytes(SILENT_WAV[16:20], "little") == 16
    # PCM, mono, 8 000 Hz, 8 000 octets par seconde, bloc d'un octet, 8 bits
    assert SILENT_WAV[20:36] == bytes.fromhex("0100 0100 401f0000 401f0000 0100 0800")
    assert SILENT_WAV[36:40] == b"data" and int.from_bytes(SILENT_WAV[40:44], "little") == 80
    assert SILENT_WAV[44:] == bytes([128]) * 80
