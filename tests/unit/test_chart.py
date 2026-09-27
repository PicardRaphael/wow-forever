"""Graphique de leveling (`forever/chart.py`) : PNG déterministe à graine fixe (deux générations identiques octet
pour octet dans le même test : les polices diffèrent entre Ubuntu et Windows, aucune empreinte n'est codée), niveau
illégal omis et cité, certitude des PV par niveau."""

from forever.chart import leveling_chart

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PTS = {"improvedFrostbolt": 3}


def test_two_generations_are_identical(game_data, tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    ra = leveling_chart(game_data, range(12, 16), PTS, n=20, seed=5, out=a)
    rb = leveling_chart(game_data, range(12, 16), PTS, n=20, seed=5, out=b)
    assert a.read_bytes() == b.read_bytes() and a.read_bytes().startswith(PNG_SIGNATURE)
    assert ra["levels"] == rb["levels"]


def test_points_and_omitted_levels(game_data, tmp_path):
    result = leveling_chart(game_data, range(10, 17), PTS, n=20, seed=5, out=tmp_path / "c.png")
    assert [p["level"] for p in result["levels"]] == [12, 13, 14, 15, 16]
    assert [o["level"] for o in result["omitted"]] == [10, 11]
    assert all("points" in o["reason"] or "talent" in o["reason"] for o in result["omitted"])
    by_level = {p["level"]: p for p in result["levels"]}
    assert by_level[12]["mob_hp_certainty"] == "certain" and by_level[16]["mob_hp_certainty"] == "probable"
    assert set(by_level[12]) >= {"mc_total", "mc_combat", "analytic_total", "xp_h", "mob_hp"}


def test_seed_mode_is_accepted(game_data, tmp_path):
    options = {"mob_source": "seed", "spell_level": "rank"}
    result = leveling_chart(game_data, range(20, 22), {}, n=10, seed=1, out=tmp_path / "d.png", options=options)
    assert {p["mob_hp_certainty"] for p in result["levels"]} == {"suppose"}
