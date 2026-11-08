"""SIM2 bloc 16 : l'analyse suit les mises à jour toute seule. La veille (étape « simulateurs ») relance
`forever sims analyse` en tâche détachée quand des analyses manquent pour la version courante (données, commit et
correctifs de wowsims) ; jamais deux à la fois (verrou tenu par le calcul en cours, processus vivant) ; rien quand
tout est fait. Lanceur et vérification du processus fabriqués."""

import json

from forever.sims.analysis import LOCK_NAME, analysis_path, relaunch_if_needed

PRESETS = [("mage/dps/Fire", "Human"), ("warrior/dps/Fury", "Orc")]


def test_missing_analyses_launch_a_detached_run(make_deps):
    deps = make_deps()
    launched = []
    note = relaunch_if_needed(deps, presets=PRESETS, spawn=lambda args, log: launched.append((args, log)),
                              alive=lambda pid: False)  # fmt: skip
    assert len(launched) == 1 and launched[0][0][-2:] == ["sims", "analyse"]
    assert "2" in note and "arrière-plan" in note


def test_nothing_when_all_done_or_already_running(make_deps):
    deps = make_deps()
    for key, race in PRESETS:
        path = analysis_path(deps, key, race)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    calls = []
    assert relaunch_if_needed(deps, presets=PRESETS, spawn=lambda *a: calls.append(a), alive=lambda pid: True) is None
    analysis_path(deps, *PRESETS[0]).unlink()
    lock = deps.cache_dir / "analysis" / LOCK_NAME
    lock.write_text(json.dumps({"pid": 4242}), encoding="utf-8")
    note = relaunch_if_needed(deps, presets=PRESETS, spawn=lambda *a: calls.append(a), alive=lambda pid: pid == 4242)
    assert calls == [] and "en cours" in note
