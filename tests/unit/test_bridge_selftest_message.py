"""`forever bridge selftest --live --message` (P06a, bloc B, sonde C) : lit un message quelconque de la bande, à
n'importe quelle taille de case, et l'affiche (numéro, drapeaux, emplacement, clés du contexte, texte)."""

from test_bridge_selftest import Clock, ScreenApi, run_live

from forever.bridge.capture import WindowsCapture
from forever.bridge.codec import encode_cells, render_band
from forever.bridge.record import Record, build_payload
from forever.bridge.selftest import selftest_message


def run_message(api, **kwargs):
    clock = Clock()
    return selftest_message(WindowsCapture({"WowB.exe"}, api), clock=clock, sleep=clock.sleep, **kwargs)


RECORD = Record(
    "abcd1234", 5, frozenset({"b=talents"}), {"level": "19", "class": "MAGE", "zone": "Westfall"}, "Quel talent ?",
    slot=3,
)  # fmt: skip


def test_message_is_read_and_described():
    api = ScreenApi(render_band(encode_cells(5, build_payload(RECORD)), 1))
    report = run_message(api)
    assert report.ok and report.record == RECORD
    text = "\n".join(report.lines)
    assert "message n° 5" in text and "emplacement annoncé : 3" in text
    assert "b=talents" in text and "level, class, zone" in text and "« Quel talent ? »" in text
    assert "case de 1 pixel" in text
    assert report.to_json()["record"]["context_keys"] == ["level", "class", "zone"]


def test_selftest_vector_is_not_a_message():
    from test_bridge_selftest import selftest_cells

    report = run_message(ScreenApi(render_band(selftest_cells(), 1)))
    assert not report.ok
    assert any("bande de test" in line for line in report.lines)


def test_unreadable_payload_is_reported():
    report = run_message(ScreenApi(render_band(encode_cells(9, b"pas un message"), 1)))
    assert not report.ok
    assert any("message illisible" in line for line in report.lines)


def test_live_selftest_still_reads_the_vector():
    from test_bridge_selftest import selftest_cells

    report, _ = run_live(ScreenApi(render_band(selftest_cells(), 1)))
    assert report.ok


def test_a_part_of_a_long_message_is_described():
    """P06b, bloc A : un message trop long part en parties ; l'autotest décrit la partie lue et renvoie au journal du
    pont pour le message complet."""
    from forever.bridge.fragments import split_payload

    record = Record("abcd1234", 6, frozenset(), {"level": "19"}, "é" * 2500, slot=3)
    parts = split_payload(build_payload(record), session="abcd1234", message_id=6)
    report = run_message(ScreenApi(render_band(encode_cells(6, parts[1]), 1)))
    assert report.ok and report.record is None
    text = "\n".join(report.lines)
    assert "partie 2/3 du message n° 6" in text and "forever bridge contexts last" in text
    assert report.to_json()["part"] == {"message_id": 6, "index": 2, "total": 3, "session": "abcd1234"}
