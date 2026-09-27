"""Commandes decode, diff, verify, report : texte et JSON, codes de sortie, jamais de réseau."""

import json
import shutil

import pytest
from conftest import LOCAL_VERSION, WAGO_70009, FakeHttp, read_json

from forever.cli import main
from forever.manifest import write_manifest

NEXT = "1.60.1.70010"


def run(capsys, argv, deps):
    code = main(argv, deps)
    out, err = capsys.readouterr()
    return code, out, err


def make_next(data_copy):
    shutil.copytree(data_copy / LOCAL_VERSION, data_copy / NEXT)
    path = data_copy / NEXT / "talents.json"
    doc = read_json(path)
    next(t for tree in doc["trees"] for t in tree["talents"] if t["key"] == "improvedFrostbolt")["ranks"][0] = [0.15]
    path.write_bytes(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
    path = data_copy / NEXT / "spells.json"
    doc = read_json(path)
    doc["spells"]["arcane_barrage"] = dict(doc["spells"]["arcane_blast"])
    path.write_bytes(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
    write_manifest(data_copy)


def test_decode_text_and_json(capsys, make_deps, tmp_path):
    http = FakeHttp.failing()
    deps = make_deps(http=http)
    argv = ["decode", "--version", LOCAL_VERSION, "--csv-dir", str(WAGO_70009), "--out", str(tmp_path / "c")]
    code, out, _ = run(capsys, argv, deps)
    assert code == 0 and "54 talents" in out and out.rstrip().splitlines()[-1].startswith("Provenance")
    code, out, _ = run(capsys, [*argv, "--force", "--json"], deps)
    payload = json.loads(out)
    assert code == 0 and payload["talents"] == 54 and payload["root"] == str(tmp_path / "c")
    assert http.calls == []


def test_decode_errors(capsys, make_deps, tmp_path):
    deps = make_deps()
    code, out, _ = run(capsys, ["decode", "--version", LOCAL_VERSION, "--json"], deps)
    assert code == 4 and json.loads(out)["error"]["code"] == "csv_missing"
    argv = ["decode", "--version", LOCAL_VERSION, "--csv-dir", str(WAGO_70009), "--out", str(tmp_path / "c")]
    assert run(capsys, argv, deps)[0] == 0
    code, out, _ = run(capsys, [*argv, "--json"], deps)
    assert code == 2 and json.loads(out)["error"]["code"] == "candidate_exists"


def test_diff_text_lines(capsys, make_deps, data_copy):
    make_next(data_copy)
    code, out, _ = run(capsys, ["diff", LOCAL_VERSION, NEXT], make_deps(data_dir=data_copy))
    assert code == 0
    assert "~ improvedFrostbolt : ranks[1] [0.1] -> [0.15]" in out
    assert "+ sort ajouté : arcane_barrage" in out
    assert "2 changement(s)" in out


def test_diff_json_and_unknown(capsys, make_deps, data_copy):
    make_next(data_copy)
    deps = make_deps(data_dir=data_copy)
    code, out, _ = run(capsys, ["diff", LOCAL_VERSION, NEXT, "--json"], deps)
    assert code == 0 and len(json.loads(out)["changes"]) == 2
    code, out, _ = run(capsys, ["diff", LOCAL_VERSION, "1.60.1.99999", "--json"], deps)
    assert code == 4 and json.loads(out)["error"]["code"] == "unknown_version"


def test_verify_codes(capsys, make_deps, data_copy, candidate):
    assert run(capsys, ["verify"], make_deps())[0] == 0
    code, out, _ = run(capsys, ["verify", str(candidate.root), "--json"], make_deps())
    assert code == 0 and json.loads(out)["ok"] is True
    path = data_copy / LOCAL_VERSION / "talents.json"
    doc = read_json(path)
    doc["trees"][0]["talents"][0]["ranks"].pop()
    path.write_bytes(json.dumps(doc).encode("utf-8"))
    write_manifest(data_copy)
    code, out, _ = run(capsys, ["verify"], make_deps(data_dir=data_copy))
    assert code == 3 and "ÉCHEC" in out


def test_report_text_json_and_out(capsys, make_deps, data_copy, tmp_path):
    make_next(data_copy)
    deps = make_deps(data_dir=data_copy)
    code, out, _ = run(capsys, ["report", LOCAL_VERSION, NEXT], deps)
    assert code == 0 and out.startswith(f"# data: {LOCAL_VERSION} → {NEXT}")
    assert out.rstrip().splitlines()[-1].startswith("Provenance")
    target = tmp_path / "rapport.md"
    code, out, _ = run(capsys, ["report", LOCAL_VERSION, NEXT, "--out", str(target)], deps)
    assert code == 0 and target.read_text(encoding="utf-8").startswith("# data:")
    code, out, _ = run(capsys, ["report", LOCAL_VERSION, NEXT, "--json"], deps)
    assert code == 0 and json.loads(out)["report"].startswith("# data:")
    assert run(capsys, ["report", LOCAL_VERSION, "1.60.1.99999"], deps)[0] == 4


@pytest.mark.parametrize(
    "argv",
    [
        ["decode", "--version", LOCAL_VERSION, "--csv-dir", str(WAGO_70009)],
        ["diff", LOCAL_VERSION, LOCAL_VERSION],
        ["verify"],
        ["report", LOCAL_VERSION, LOCAL_VERSION],
    ],
)
def test_offline_commands_never_call_the_network(capsys, make_deps, argv):
    http = FakeHttp.failing()
    assert run(capsys, argv, make_deps(http=http))[0] == 0
    assert http.calls == []
