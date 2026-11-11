"""FR1 : mémoire de traduction hors dépôt (gabarit anglais -> gabarit français, origine, date) ; une phrase déjà
traduite ne repasse pas au traducteur ; une entrée `manuel` n'est jamais écrasée ; seule la phrase nouvelle part au
traducteur après un changement de la source.

Valeurs : phrases inventées pour le test."""

import json
from pathlib import Path

from forever.rxp_fr.memory import Memory, normalize
from forever.rxp_fr.translator import resolve


class Recorder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def translate(self, items):
        self.calls.append(list(items))
        return {p: "FR " + p for p in items}


def test_manual_entries_are_never_overwritten(tmp_path: Path):
    mem = Memory()
    assert mem.put("Wait here", "Attendez ici", "manuel", date="2026-11-11")
    assert not mem.put("Wait here", "Patientez", "restedxp", date="2026-11-11")
    assert not mem.put("Wait here", "Patientez", "traduit", date="2026-11-11")
    assert mem.get("Wait here").fr == "Attendez ici"


def test_restedxp_beats_an_earlier_session_translation():
    mem = Memory()
    mem.put("Talk to {1}", "Causez avec {1}", "traduit", date="d")
    assert mem.put("Talk to {1}", "Parlez à {1}", "restedxp", date="d")
    assert not mem.put("Talk to {1}", "Causez à {1}", "traduit", date="d")
    assert mem.get("Talk to {1}").fr == "Parlez à {1}"


def test_a_translation_must_keep_every_slot_once():
    mem = Memory()
    assert not mem.put("Kill {1} and {2}", "Tuez {1}", "traduit", date="d")
    assert not mem.put("Kill {1}", "Tuez {1} {1}", "traduit", date="d")
    assert mem.put("Kill {1} and {2}", "Tuez {2} et {1}", "traduit", date="d")


def test_the_memory_is_saved_and_read_back(tmp_path: Path):
    path = tmp_path / "rxp_fr" / "memoire.json"
    mem = Memory()
    mem.put("Wait  here ", "Attendez ici", "manuel", date="2026-11-11")
    mem.save(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["schema_version"] == 1
    again = Memory.load(path)
    assert again.get("Wait here").origin == "manuel"
    assert normalize(" a   b ") == "a b"


def test_only_new_phrases_reach_the_translator():
    mem = Memory()
    mem.put("Old phrase", "Vieille phrase", "traduit", date="d")
    rec = Recorder()
    out = resolve(["Old phrase", "New phrase", "New phrase"], mem, rec, date="d")
    assert rec.calls == [["New phrase"]]
    assert out["New phrase"] == ("FR New phrase", "traduit")
    assert out["Old phrase"] == ("Vieille phrase", "traduit")
    rec2 = Recorder()
    resolve(["Old phrase", "New phrase"], mem, rec2, date="d")
    assert rec2.calls == []


def test_without_translator_a_new_phrase_stays_english():
    out = resolve(["Brand new"], Memory(), None, date="d")
    assert out["Brand new"] == (None, "anglais")
