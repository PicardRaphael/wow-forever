"""CJ1, bloc 2 (décision 272, demande de l'utilisateur du 2026-10-14) : retrait sûr des routes livrées par forever dans
RestedXP. RestedXP range chaque guide importé dans sa sauvegarde de compte (`RXPDB`, clés `<groupe>|<sous-groupe>|<nom>`
suivies d'un compteur) ; `forever route rxp-clean` liste d'abord (essai à blanc), puis, sur `--apply` et jeu fermé
seulement, retire les seules entrées du groupe « Forever Routes » après une copie datée du fichier ; tout le reste
du fichier est relu à l'identique.

Valeurs : sauvegarde fabriquée ici (structure seulement, aucun guide de RestedXP)."""

from pathlib import Path

import pytest

from forever.errors import InvalidArgumentError
from forever.pipeline.lua_table import parse_lua_value_at
from forever.rxp_clean import ROUTES_GROUP, clean_rxp_routes, forever_keys

SV = """
RXPDB = {
["profileKeys"] = {
["Bob - Forever"] = "global",
},
["profiles"] = {
["global"] = {
["guides"] = {
["Forever Routes||Forever · Bob · 1-10|1"] = {
["groupOrContent"] = "abc",
["key"] = "Forever Routes||Forever · Bob · 1-10",
},
["Some Group|x|Other Guide|2"] = {
["groupOrContent"] = "def",
},
["Forever Routes||Forever · Jen · 5-10|3"] = {
["groupOrContent"] = "g}h{i",
["nested"] = {
1, -- [1]
"}", -- [2]
},
},
},
},
},
}
RXPData = {
["release"] = 1,
}
"""


def _wow(tmp_path: Path) -> Path:
    sv = tmp_path / "wow" / "WTF" / "Account" / "ACC" / "SavedVariables"
    sv.mkdir(parents=True)
    (sv / "RXPGuides.lua").write_text(SV, encoding="utf-8")
    return tmp_path / "wow"


def _db(text: str) -> object:
    start = text.index("RXPDB = ") + len("RXPDB = ")
    return parse_lua_value_at(text, start)[0]


def test_forever_keys_are_found_only_in_our_group():
    keys = forever_keys(SV)
    assert keys == ["Forever Routes||Forever · Bob · 1-10|1", "Forever Routes||Forever · Jen · 5-10|3"]
    assert all(k.startswith(ROUTES_GROUP + "|") for k in keys)


def test_dry_run_lists_without_writing(tmp_path):
    wow = _wow(tmp_path)
    out = clean_rxp_routes(wow, apply=False, backup_dir=tmp_path / "bak", game_running=lambda: False)
    assert out["status"] == "à blanc" and len(out["files"][0]["keys"]) == 2
    path = wow / "WTF" / "Account" / "ACC" / "SavedVariables" / "RXPGuides.lua"
    assert path.read_text(encoding="utf-8") == SV and not (tmp_path / "bak").exists()


def test_apply_refused_while_the_game_runs(tmp_path):
    wow = _wow(tmp_path)
    with pytest.raises(InvalidArgumentError):
        clean_rxp_routes(wow, apply=True, backup_dir=tmp_path / "bak", game_running=lambda: True)
    with pytest.raises(InvalidArgumentError):
        clean_rxp_routes(wow, apply=True, backup_dir=tmp_path / "bak", game_running=lambda: None)  # état inconnu


def test_apply_removes_only_our_routes_after_a_backup(tmp_path):
    wow = _wow(tmp_path)
    out = clean_rxp_routes(wow, apply=True, backup_dir=tmp_path / "bak", game_running=lambda: False)
    assert out["status"] == "retirées"
    path = wow / "WTF" / "Account" / "ACC" / "SavedVariables" / "RXPGuides.lua"
    after = path.read_text(encoding="utf-8")
    backups = list((tmp_path / "bak").rglob("RXPGuides.lua"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == SV
    assert forever_keys(after) == []
    before_db, after_db = _db(SV), _db(after)
    guides_before = before_db["profiles"]["global"]["guides"]  # type: ignore[index]
    expected = {k: v for k, v in guides_before.items() if not k.startswith(ROUTES_GROUP + "|")}
    assert after_db["profiles"]["global"]["guides"] == expected  # type: ignore[index]
    assert after_db["profileKeys"] == before_db["profileKeys"]  # type: ignore[index]
    assert after.split("RXPData = ", 1)[1] == SV.split("RXPData = ", 1)[1]  # le reste du fichier intact


def test_no_saved_variables(tmp_path):
    out = clean_rxp_routes(tmp_path / "vide", apply=False, backup_dir=tmp_path / "bak", game_running=lambda: False)
    assert out["files"] == [] and "aucune" in out["message"]
