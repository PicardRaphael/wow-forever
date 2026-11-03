"""Règle de lecture dépassée (demande du 2026-11-03) : une règle de `decode_rules.json` qui ne correspond plus à un
talent ou à un sort ne bloque plus toute l'installation. Le talent est gardé avec le texte du client, marqué « à
relire » (certitude `suppose`), exclu des calculs qui dépendent de la valeur manquante, et la candidate le dit (notes
de la carte « Mis à jour ») ; tout le reste se décode normalement. Une vraie casse d'intégrité bloque toujours.

Et la surveillance de GitHub ne décode plus une version publiée plus ancienne que la version installée (le 3 novembre,
elle décodait 1.60.1.70532 de la bêta avec les règles de 1.60.1.70707) ; le produit de la version finale décodée sur
le client adopté passe dans `sources.json` à l'installation.

CSV du client : `tests/fixtures/wago/1.60.1.70170` ; règles mutées sur une copie des données. Aucun chiffre du jeu."""

import json

import pytest
from conftest import FIXTURES, LOCAL_VERSION, REPO_ROOT, FakeHttp, isolated_deps, read_json

from forever.cli import main
from forever.errors import DataSchemaError
from forever.manifest import write_manifest
from forever.pipeline.decode import decode_version

WAGO = FIXTURES / "wago" / "1.60.1.70170"
VERSION = "1.60.1.70170"
WATCH = REPO_ROOT / ".github" / "workflows" / "build-watch.yml"


def mutate(data_dir, change):
    path = data_dir / LOCAL_VERSION / "decode_rules.json"
    rules = json.loads(path.read_text(encoding="utf-8"))
    change(rules)
    path.write_text(json.dumps(rules, ensure_ascii=False, indent=1), encoding="utf-8")
    write_manifest(data_dir)


def outdated(rules):
    rules["target_auras"]["winters_chill"]["trigger_aura"] = 9999  # aura déclenchée absente du sort du talent
    rules["rank_variables"]["impact"] = [99]  # variable hors de l'infobulle


def decode(tmp_path, data_dir, name):
    return decode_version(isolated_deps(tmp_path, data_dir), VERSION, csv_dir=WAGO, out=tmp_path / name).root / VERSION


def talents(vdir):
    return {t["key"]: t for tree in read_json(vdir / "talents.json")["trees"] for t in tree["talents"]}


@pytest.fixture
def both(tmp_path, data_copy):
    sound = decode(tmp_path, data_copy, "saine")
    mutate(data_copy, outdated)
    return sound, decode(tmp_path, data_copy, "depassee")


def test_an_outdated_rule_no_longer_blocks_the_decode(both):
    _, vdir = both
    impact = talents(vdir)["impact"]
    assert impact["certainty"] == "suppose" and "rank_variables" in impact["review"]
    assert impact["desc"] and impact["ranks"] == []  # texte du client gardé, valeurs non lues


def test_every_other_talent_is_decoded_as_before(both):
    sound, vdir = both
    before, after = talents(sound), talents(vdir)
    assert set(before) == set(after)
    changed = sorted(k for k in before if before[k] != after[k])
    assert changed == ["impact", "wintersChill"]


def test_the_talent_of_an_outdated_aura_rule_is_marked(both):
    _, vdir = both
    chill = talents(vdir)["wintersChill"]
    assert chill["certainty"] == "suppose" and "déclenché" in chill["review"]
    auras = read_json(vdir / "spell_scaling.json")["auras"]
    assert "winters_chill" not in auras and "fire_vulnerability" in auras


def test_the_candidate_says_what_to_review(both):
    _, vdir = both
    sources = read_json(vdir / "sources.json")
    review = sources["to_review"]
    assert {r["talent"] for r in review} == {"impact", "wintersChill"}
    assert sources["files"]["talents.json"]["certainty"] == "suppose"


def test_the_engine_leaves_out_a_talent_to_review(both):
    from forever.gamedata import build_game_data
    from forever.store import VersionData

    _, vdir = both
    gd = build_game_data(VersionData(vdir.name, "candidate", vdir, read_json(vdir / "sources.json")))
    assert "impact" not in gd.talents and "wintersChill" not in gd.talents
    assert "ignite" in gd.talents


def test_a_real_integrity_break_still_blocks(tmp_path, data_copy):
    mutate(data_copy, lambda rules: rules["skill_lines"].update({k: 999999 for k in rules["skill_lines"]}))
    with pytest.raises(DataSchemaError):
        decode(tmp_path, data_copy, "cassee")


# --- Surveillance de GitHub et produit --------------------------------------------------------------------------------


def builds_http(*versions):
    payload = {"wow_classic_beta": [{"version": v, "created_at": "2026-10-21T00:00:00Z"} for v in versions]}
    return FakeHttp(body=json.dumps(payload).encode("utf-8"))


@pytest.mark.parametrize(("published", "newer"), [("1.60.1.70009", False), ("1.60.1.99999", True)])
def test_only_a_newer_published_version_is_new(make_deps, capsys, published, newer):
    assert main(["builds", "--json"], make_deps(http=builds_http(published))) == 0
    assert json.loads(capsys.readouterr().out)["newer"] is newer


def test_the_watch_decodes_only_a_newer_version():
    text = WATCH.read_text(encoding="utf-8")
    assert "['newer']" in text and '[ "$latest" = "$installed" ]' not in text


def test_the_product_of_the_candidate_is_kept_at_install(tmp_path):
    from forever.pipeline.install import carry_product

    cand = tmp_path / "cand"
    cand.mkdir()
    (cand / "sources.json").write_text(json.dumps({"product": "wow_fictif_finale", "version_prefix": "1.60."}))
    sources = {"product": "wow_classic_beta", "version_prefix": "1.60."}
    carry_product(sources, cand)
    assert sources["product"] == "wow_fictif_finale"
    (cand / "sources.json").write_text(json.dumps({}))
    carry_product(sources, cand)  # candidate sans produit (client d'un autre build) : rien ne change
    assert sources["product"] == "wow_fictif_finale"


def test_the_install_keeps_a_talent_to_review_without_refusing(data_copy):
    """L'installation ne refuse plus un talent à relire (ses valeurs non lues ne sont pas des écarts) : il est gardé,
    marqué `suppose` avec la raison, et la révision le dit (règle « review »)."""
    from forever.pipeline.install import _Merge

    repo = read_json(data_copy / LOCAL_VERSION / "talents.json")
    cand = json.loads(json.dumps(repo))
    target = cand["trees"][0]["talents"][0]
    target.update(ranks=[], certainty="suppose", review="rank_variables dépassée")
    merge = _Merge(LOCAL_VERSION, [], "2026-11-03")
    doc = merge.talents(repo, cand)
    out = next(t for tree in doc["trees"] for t in tree["talents"] if t["key"] == target["key"])
    assert out["certainty"] == "suppose" and out["review"] == "rank_variables dépassée"
    assert out["ranks"] == repo["trees"][0]["talents"][0]["ranks"]  # anciennes valeurs gardées, hors des calculs
    assert merge.refused == []
    assert [c["path"] for c in merge.changes if c["rule"] == "review"] == [target["key"]]


def test_the_candidate_with_a_talent_to_review_passes_verify(both, tmp_path, data_copy):
    from forever.pipeline.decode import review_note
    from forever.pipeline.verify import verify_version

    _, vdir = both
    result = verify_version(isolated_deps(tmp_path, data_copy), str(vdir.parent))
    assert result["ok"], result.get("errors")
    line = review_note(read_json(vdir / "sources.json")["to_review"][0])
    assert line.startswith("à relire : talent ") and "exclu des calculs" in line
