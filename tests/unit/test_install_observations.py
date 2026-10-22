"""Écarts aux règles de fusion tranchés par la veille (décision 296, 2026-10-22) : une observation faite sur une version
plus ancienne que la nouvelle version du client est remplacée par les données de cette version, et la carte
« Mis à jour » le dit (« talent X retiré par la version Y ; ton observation datait de X ») ; une observation faite sur
la même version garde la priorité, l'écart est signalé et le reste s'installe.

Écarts, talents et sorts fabriqués (clés et valeurs inventées), plus la chaîne de `test_update_chain.py` ; aucun
chiffre du jeu écrit ici."""

import json
import shutil

from test_update_chain import BASE, DRY, TARGET, Replay, montage, only_verdict  # noqa: F401  (fixture importée)

from forever.manifest import write_manifest
from forever.pipeline.install import plan_install
from forever.pipeline.observations import keep_observations, resolve
from forever.update import run_update

OLD, NEW = "1.60.1.10000", "1.60.1.10001"


def refused(file, path, before, after):
    return {"file": file, "path": path, "before": before, "after": after, "source": "client", "certainty": "certain",
            "rule": "refused"}  # fmt: skip


def candidate(tmp_path, version, *, hotfix=False):
    vdir = tmp_path / "cand" / version
    vdir.mkdir(parents=True)
    talent = {"key": "fakeTalent", "name": "Fake Talent", "tier": 1, "col": 2, "ranks": [[1], [2]]}
    if hotfix:
        talent["hotfix"] = {"pushes": [1]}
    doc = {"trees": [{"name": "Arbre", "talents": [talent]}]}
    (vdir / "talents.json").write_text(json.dumps(doc), encoding="utf-8")
    (vdir / "spells.json").write_text(json.dumps({"rank_format": ["mana"], "spells": {}}), encoding="utf-8")
    return vdir


# --- observation plus ancienne : remplacée, dite --------------------------------------------------------------------


def test_an_older_observation_gives_way_to_the_new_version_and_is_said(tmp_path):
    cand = candidate(tmp_path, NEW)
    out = resolve(
        [refused("talents.json", "goneTalent", "goneTalent", None), refused("talents.json", "fakeTalent.col", 3, 2)],
        version_from=OLD, version_to=NEW, candidate_vdir=cand, names={"goneTalent": "Gone Talent"},
    )  # fmt: skip
    assert out.unresolved == [] and out.kept == []
    assert [(e["kind"], e["key"], e["change"], e["field"]) for e in out.accepted] == [
        ("talent", "goneTalent", "removed", None),
        ("talent", "fakeTalent", "modified", "col"),
    ]
    assert all("décision 296" in e["decision"] for e in out.accepted)
    assert out.notes[0] == f"talent Gone Talent retiré par la version {NEW} ; ton observation datait de {OLD}"
    assert out.notes[1] == f"talent Fake Talent : col 3 → 2 par la version {NEW} ; ton observation datait de {OLD}"


def test_a_new_client_version_installs_over_an_older_observation(montage):  # noqa: F811
    """Chaîne complète : la nouvelle version change un coût en mana que la version installée tenait ; plus de
    blocage, la valeur du client s'installe et la note de la carte le dit."""
    deps, _ = montage(change=("SpellPower", "116", "ManaCost"))
    report = run_update(deps, DRY, replay=Replay())
    verdict = only_verdict(report)
    assert verdict["action"] == "écrire", verdict["reasons"]
    assert verdict["clauses"]["install"] is True and report["pending"] == []
    assert any(f"par la version {TARGET} ; ton observation datait de {BASE}" in n for n in verdict["notes"])


# --- même version : l'observation garde la priorité, l'écart est signalé, le reste s'installe ----------------------


def test_a_same_version_observation_keeps_priority_and_is_flagged(tmp_path):
    cand = candidate(tmp_path, NEW)
    out = resolve([refused("talents.json", "fakeTalent.col", 3, 2)], version_from=NEW, version_to=NEW,
                  candidate_vdir=cand, names={})  # fmt: skip
    assert out.accepted == [] and out.unresolved == []
    assert [k["path"] for k in out.kept] == ["fakeTalent.col"]
    assert out.notes == [
        f"écart signalé : talent Fake Talent, col : ton observation de {NEW} (3) garde la priorité sur le client (2)"
    ]


def test_a_server_hotfix_of_the_same_version_is_not_an_observation(tmp_path):
    cand = candidate(tmp_path, NEW, hotfix=True)
    out = resolve([refused("talents.json", "fakeTalent.col", 3, 2)], version_from=NEW, version_to=NEW,
                  candidate_vdir=cand, names={})  # fmt: skip
    assert out.kept == [] and [e["nature"] for e in out.accepted] == ["correctif_serveur"]
    assert "correctif du serveur" in out.notes[0]


def test_the_kept_observation_lets_the_rest_install(make_deps, data_copy, tmp_path):
    """Révision de la même version : la candidate change un coût en mana (écart refusé) ; la copie corrigée garde la
    valeur observée, et la fusion ne refuse plus rien."""
    from conftest import LOCAL_VERSION

    deps = make_deps(data_dir=data_copy)
    cand_root = tmp_path / "candidate"
    shutil.copytree(data_copy / LOCAL_VERSION, cand_root / LOCAL_VERSION)  # candidate : une seule version
    spells_path = cand_root / LOCAL_VERSION / "spells.json"
    spells = json.loads(spells_path.read_text(encoding="utf-8"))
    key = next(k for k, s in spells["spells"].items() if s.get("ranks") and isinstance(s["ranks"][0][0], int))
    spells["spells"][key]["ranks"][0][0] += 1
    spells_path.write_text(json.dumps(spells, ensure_ascii=False), encoding="utf-8")
    write_manifest(cand_root)
    plan = plan_install(deps, str(cand_root))
    assert plan["refused"], "écart fabriqué attendu"
    out = resolve(plan["refused"], version_from=LOCAL_VERSION, version_to=LOCAL_VERSION,
                  candidate_vdir=cand_root / LOCAL_VERSION, names={})  # fmt: skip
    assert out.kept and not out.unresolved
    patched = keep_observations(cand_root, LOCAL_VERSION, data_copy / LOCAL_VERSION, out.kept, tmp_path / "gardée")
    assert plan_install(deps, str(patched))["refused"] == []
