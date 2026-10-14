"""CJ1, bloc 2 : la sauvegarde réelle de RestedXP porte des guides compressés (octets qui ne sont pas de l'UTF-8) ;
`forever route rxp-clean` la lit et la réécrit octet pour octet, hors des seules entrées « Forever Routes ».

Valeurs : sauvegarde fabriquée ici (structure seulement)."""

from forever.rxp_clean import clean_rxp_routes

RAW = (
    b'RXPDB = {\n["profiles"] = {\n["global"] = {\n["guides"] = {\n'
    b'["Forever Routes||Forever \xc2\xb7 Bob \xc2\xb7 1-10|1"] = {\n["groupOrContent"] = "\xe5\x01\xff",\n},\n'
    b'["Other|x|Guide|1"] = {\n["groupOrContent"] = "\xe5\x02\xfe",\n},\n},\n},\n},\n}\n'
)


def test_non_utf8_bytes_are_kept_and_names_shown(tmp_path):
    sv = tmp_path / "wow" / "WTF" / "Account" / "A" / "SavedVariables"
    sv.mkdir(parents=True)
    (sv / "RXPGuides.lua").write_bytes(RAW)
    dry = clean_rxp_routes(tmp_path / "wow", apply=False, backup_dir=tmp_path / "bak", game_running=lambda: False)
    assert dry["files"][0]["keys"] == ["Forever Routes||Forever · Bob · 1-10|1"]
    clean_rxp_routes(tmp_path / "wow", apply=True, backup_dir=tmp_path / "bak", game_running=lambda: False)
    after = (sv / "RXPGuides.lua").read_bytes()
    assert b"Forever Routes" not in after and b'["Other|x|Guide|1"] = {\n["groupOrContent"] = "\xe5\x02\xfe",' in after
    assert next((tmp_path / "bak").rglob("RXPGuides.lua")).read_bytes() == RAW
