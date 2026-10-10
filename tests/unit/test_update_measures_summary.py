"""Résumé des attentes de mesure et `forever update status` (demande de l'utilisateur du 2026-10-10, décision 227).

Une attente `measures` porte son résumé : PNJ ajoutés, changés et écartés (avec la raison), niveaux dont les PV
changent, et cas des builds qui changeraient après rejeu (« avant » : données installées, « après » : copie où la
mesure est écrite, `preview` rendu par la mesure). Le rejeu n'est fait qu'une fois par attente (même identifiant, même
base). `forever update status` ne montre que les attentes ouvertes, l'historique complet avec `--all`.

Valeurs des PNJ synthétiques (aucun chiffre du jeu) ; rejeu simulé."""

import json
import shutil

from conftest import LOCAL_VERSION
from test_update_chain import LOG, logs, step  # noqa: F401  (fixture importée)

from forever.cli import main
from forever.manifest import write_manifest
from forever.update import (
    UpdateOptions,
    list_pending,
    measure_summary,
    record_pending,
    reject,
    replay_label,
    run_update,
)

JOURNALS = UpdateOptions(dry_run=True, only=frozenset({"journaux"}))
CHANGED_CASE = "leveling-20"
DETAILS = {
    "added": [{"npc_id": 900001, "name": "Synthetic Boar", "levels": {"7": 111}}],
    "changed": [{"npc_id": 900002, "name": "Synthetic Wolf", "levels": {"8": {"before": 120, "after": 125}}}],
    "removed": [],
    "excluded": [{"npc_id": 900003, "name": "Synthetic Giant", "reason": "PV hors norme (synthétique)", "new": True}],
}
HP_LEVELS = {"7": {"before": 100, "after": 111}}


class PreviewMeasure:
    """Mesure simulée : une entrée des moteurs change (`monsters.json`) et l'aperçu est une copie des données où
    `monsters.json` diffère."""

    def __init__(self, root):
        self.root = root
        self.calls = 0

    def __call__(self, deps, data_dir, files):
        self.calls += 1
        preview = self.root / f"apercu-{self.calls}"
        shutil.copytree(data_dir, preview)
        path = preview / LOCAL_VERSION / "monsters.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc.setdefault("npcs", {})["900001"] = {"name": "Synthetic Boar", "levels": {"7": {"max_hp": 111}}}
        path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        write_manifest(preview)
        return {
            "changed": [{"file": "monsters.json", "pointer": "/npcs"}],
            "details": DETAILS,
            "hp_by_level": HP_LEVELS,
            "preview": preview,
        }


class SplitReplay:
    """Rejeu simulé : le cas `CHANGED_CASE` du build du Mage diffère après ; les autres sont identiques."""

    def __init__(self, base):
        self.base = base
        self.calls = []

    def __call__(self, engine, case, data_dir):
        self.calls.append((engine, case))
        after = data_dir != self.base
        return {"talents": "B" if after and engine == "mage_build" and case == CHANGED_CASE else "A"}


def test_measure_pending_carries_its_summary(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    replay = SplitReplay(deps.data_dir)
    report = run_update(deps, JOURNALS, replay=replay, measure=PreviewMeasure(tmp_path))
    assert step(report, "journaux")["status"] == "attente"
    (entry,) = report["pending"]
    summary = entry["summary"]["measures"]
    assert summary["npcs"]["added"][0]["name"] == "Synthetic Boar"
    assert summary["npcs"]["changed"][0]["levels"] == {"8": {"before": 120, "after": 125}}
    assert summary["npcs"]["excluded"][0]["reason"] == "PV hors norme (synthétique)"
    assert summary["hp_by_level"] == HP_LEVELS
    builds = summary["builds"]
    assert builds["replayed"] is True and builds["base"] == replay_label(deps.data_dir)
    assert builds["changed"] == [{"engine": "mage_build", "case": CHANGED_CASE}]
    assert builds["unchanged"] > 0
    assert "1 ajouté" in summary["sentence"] and "1 cas" in summary["sentence"]


def test_replay_is_done_once_per_pending(logs, tmp_path):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])
    first = run_update(deps, JOURNALS, replay=SplitReplay(deps.data_dir), measure=PreviewMeasure(tmp_path))
    record_pending(deps.cache_dir, first["pending"][0])
    replay = SplitReplay(deps.data_dir)
    again = run_update(deps, JOURNALS, replay=replay, measure=PreviewMeasure(tmp_path / "bis"))
    assert replay.calls == []
    assert again["pending"][0]["summary"]["measures"]["builds"] == first["pending"][0]["summary"]["measures"]["builds"]


def test_measure_without_preview_says_why_builds_are_not_replayed(logs):  # noqa: F811
    deps = logs([(LOCAL_VERSION, 1)])

    def measure(deps, data_dir, files):
        return {"changed": [{"file": "monsters.json", "pointer": "/npcs"}]}

    replay = SplitReplay(deps.data_dir)
    report = run_update(deps, JOURNALS, replay=replay, measure=measure)
    builds = report["pending"][0]["summary"]["measures"]["builds"]
    assert builds["replayed"] is False and builds["reason"]
    assert replay.calls == []


# --- forever update status ---------------------------------------------------------------------------------------


def entry(pending_id, summary=None, kind="measures"):
    return {
        "id": pending_id,
        "kind": kind,
        "action": "attente",
        "version": LOCAL_VERSION,
        "revision": None,
        "clauses": {},
        "reasons": ["synthétique"],
        "created_at": "2026-10-10T06:00:00Z",
        "summary": summary or {},
    }


def summary_doc():
    builds = {
        "replayed": True,
        "base": "update-x-y",
        "changed": [{"engine": "mage_build", "case": CHANGED_CASE}],
        "unchanged": 15,
        "not_replayed": [{"engine": "mage_leveling", "case": "sim-leveling-20", "reason": "sans rejeu automatique"}],
    }
    return measure_summary(DETAILS, HP_LEVELS, builds)


def test_status_shows_open_entries_by_default_and_all_with_the_flag(make_deps, capsys):
    deps = make_deps()
    record_pending(deps.cache_dir, entry("measures-open", summary_doc()))
    record_pending(deps.cache_dir, entry("measures-old"))
    reject(deps.cache_dir, "measures-old", "synthétique")
    assert {e["id"] for e in list_pending(deps.cache_dir)} == {"measures-open", "measures-old"}

    assert main(["update", "status"], deps) == 0
    out = capsys.readouterr().out
    assert "measures-open" in out and "measures-old" not in out
    assert "--all" in out  # l'historique est annoncé

    assert main(["update", "status", "--all"], deps) == 0
    out = capsys.readouterr().out
    assert "measures-open" in out and "measures-old" in out

    assert main(["update", "status", "--json"], deps) == 0
    assert [e["id"] for e in json.loads(capsys.readouterr().out)["pending"]] == ["measures-open"]


def test_status_renders_the_measure_summary(make_deps, capsys):
    deps = make_deps()
    record_pending(deps.cache_dir, entry("measures-open", summary_doc()))
    assert main(["update", "status"], deps) == 0
    out = capsys.readouterr().out
    assert "PNJ ajoutés : Synthetic Boar (900001) niv. 7 : 111 PV" in out
    assert "PNJ changés : Synthetic Wolf (900002) niv. 8 : 120 → 125 PV" in out
    assert "PNJ écartés : Synthetic Giant (900003) : PV hors norme (synthétique) (nouveau)" in out
    assert "PV par niveau : niv. 7 : 100 → 111" in out
    assert f"builds qui changeraient après rejeu : mage_build {CHANGED_CASE} (15 inchangé(s))" in out
    assert "non rejoué(s) : mage_leveling sim-leveling-20 (sans rejeu automatique)" in out
