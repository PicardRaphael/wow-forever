"""CJ1, bloc 1c (registre I15, I18) : temps par monstre « au camp » pour les routes. La cadence des gains de
ForeverLogger compte aussi les trajets entre les quêtes (pauses jusqu'à `pause_s`), que la route ajoute déjà à part :
pour une route, seuls les intervalles courts (jusqu'à `camp_pause_s`) comptent ; les autres usages gardent la cadence
complète.

Constat du 2026-10-14 : le Mage de niveau 1 à 5 avait 47 s par monstre (30 intervalles, trajets compris).

Valeurs : gains fabriqués ici ; paramètres lus dans les données de la version du dépôt. Aucun chiffre de jeu ici."""

from types import SimpleNamespace

from conftest import DATA_DIR, LOCAL_VERSION, read_json

from forever.kill_time import kill_params, kill_time, measure_kill_times
from forever.pipeline.addon_sv import XpGain

VALUES = read_json(DATA_DIR / LOCAL_VERSION / "mechanics.json")["values"]
PARAMS = kill_params(VALUES)


def _gains(level, gaps):
    t, out = 1000, []
    for g in gaps:
        t += g
        out.append(XpGain(time=t, localtime=None, level=level, text="", kind="monster"))
    return out


def test_camp_pause_comes_from_mechanics():
    assert PARAMS.camp_pause_s == VALUES["measures.kill_time"]["value"]["camp_pause_s"]
    assert 0 < PARAMS.camp_pause_s < PARAMS.pause_s


def test_camp_band_keeps_only_short_intervals():
    short, long = PARAMS.camp_pause_s / 2, (PARAMS.camp_pause_s + PARAMS.pause_s) / 2
    gaps = [0, *([short] * PARAMS.min_samples), *([long] * PARAMS.min_samples * 2)]
    character = SimpleNamespace(class_="Mage", xp=_gains(1, gaps))
    out = measure_kill_times(PARAMS, logs=[], loggers=[SimpleNamespace(characters={"g": character})])
    bands = {b["method"]: b for b in out["bands"]}
    assert bands["camp"]["median_s"] == short and bands["camp"]["samples"] == PARAMS.min_samples
    assert bands["cadence"]["median_s"] == long  # cadence complète : trajets compris


def test_route_scope_prefers_the_camp_band():
    short, long = PARAMS.camp_pause_s / 2, (PARAMS.camp_pause_s + PARAMS.pause_s) / 2
    gaps = [0, *([short] * PARAMS.min_samples), *([long] * PARAMS.min_samples * 2)]
    character = SimpleNamespace(class_="Mage", xp=_gains(1, gaps))
    measures = measure_kill_times(PARAMS, logs=[], loggers=[SimpleNamespace(characters={"g": character})])
    camp = kill_time(PARAMS, class_name="mage", level=1, measures=measures, camp=True)
    total = kill_time(PARAMS, class_name="mage", level=1, measures=measures)
    assert camp.seconds == short and camp.scope == "camp" and "camp" in camp.method
    assert total.seconds == long and total.scope == "total"
