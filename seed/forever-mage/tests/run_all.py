"""Tests de l'agent Mage. Lancer : python tests/run_all.py   (aucune dépendance)."""
import os, sys, traceback, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import fm, sim_leveling as sl, optimize as op, pvp, respec

T = []
def test(f): T.append(f); return f

# ---------------------------------------------------------------- données
@test
def donnees_completes():
    D = fm.data()
    trees = {tr["name"]: len(tr["talents"]) for tr in D.talents_raw["trees"]}
    assert trees == {"Arcane": 18, "Fire": 17, "Frost": 19}, trees
    assert len(D.spells) >= 15

@test
def valeurs_client_70009():
    assert fm.spell("frostbolt")["ranks"][1] == [8, 34, 38, 0, 0, 1.8, 35, 0]
    assert fm.spell("fireball")["ranks"][2] == [12, 48, 66, 6, 6, 2.5, 65, 0]
    assert fm.data().T["iceLance"]["ranks"] == [[26, 30, 300]]
    assert [r[0] for r in fm.data().T["improvedFrostbolt"]["ranks"]] == [0.1, 0.2, 0.3, 0.4, 0.5]
    assert fm.data().T["shatter"]["ranks"][0][0] == 17 and fm.data().T["shatter"]["ranks"][-1][0] == 50

@test
def prerequis():
    D = fm.data()
    need = {"fingersOfFrost": "iceLance", "arcanePower": "presenceOfMind", "hotStreak": "pyroblast", "combustion": "criticalMass", "iceBarrier": "coldSnap"}
    for k, pk in need.items():
        pr = D.T[k]["prereq"]; assert D.by_pos[(D.T[k]["tree"], pr["tier"], pr["col"])] == pk, k

@test
def legalite():
    assert fm.check_build({"improvedFrostbolt": 5, "iceLance": 1}, 20)                    # palier 3 sans 10 points
    ok = {"improvedFrostbolt": 5, "elementalPrecision": 2, "frostbite": 3, "iceLance": 1}
    assert not fm.check_build(ok, 20)
    assert fm.check_build(ok, 19)                                                        # 11 points au niveau 19
    assert fm.check_build({"improvedFrostbolt": 6}, 20)

# ---------------------------------------------------------------- mécaniques (couverture : rien d'oublié)
L = 60; CH = fm.character(60, "Orc", {"sp": 500, "spell_crit": 0.10})
def E(key, pts=None, **kw):
    return fm.expected_cast(key, L, pts or {}, kw.pop("ch", CH), kw.pop("diff", 0), **kw)

@test
def couverture_mecaniques():
    base_fb = E("frostbolt"); base_fi = E("fireball")
    checks = {
        "toucher/écart de niveau": E("frostbolt", diff=3)["hit"] < base_fb["hit"],
        "plafond de toucher": E("frostbolt", {"elementalPrecision": 5})["hit"] == 0.99,
        "Elemental Precision": E("frostbolt", {"elementalPrecision": 2})["hit"] > base_fb["hit"],
        "Arcane Focus": E("arcane_missiles", {"arcaneFocus": 2})["hit"] > E("arcane_missiles")["hit"],
        "critique Int/niveau": fm.character(30)["crit"] > 0.002,
        "critique d'équipement": fm.character(60, "Orc", {"crit_gear": 0.03})["crit"] > fm.character(60)["crit"],
        "critique épée Humain": fm.character(60, "Human", {"sword": True})["crit"] > fm.character(60, "Human")["crit"],
        "Arcane Instability": E("frostbolt", {"arcaneInstability": 3})["crit"] > base_fb["crit"],
        "Critical Mass": E("fireball", {"criticalMass": 3})["crit"] > base_fi["crit"],
        "Arcane Impact": E("arcane_missiles", {"arcaneImpact": 3})["crit"] > E("arcane_missiles")["crit"],
        "Incineration": E("fire_blast", {"incineration": 3})["crit"] > E("fire_blast")["crit"],
        "Shatter (gelé)": E("frostbolt", {"shatter": 3}, frozen=True)["crit"] > base_fb["crit"],
        "Winter's Chill": E("frostbolt", wc_stacks=5)["crit"] > base_fb["crit"],
        "multiplicateur de critique": base_fb["crit_mult"] == 1.5,
        "Ice Shards": E("frostbolt", {"iceShards": 5})["crit_mult"] == 2.0,
        "Arcane Mind": E("arcane_missiles", {"arcaneMind": 5})["crit_mult"] == 2.0,
        "DoT qui critiquent": base_fi["dot"] > fm.spell("fireball")["ranks"][-1][3],
        "Ignite": E("fireball", {"ignite": 5})["ignite"] > 0,
        "Piercing Ice": E("frostbolt", {"piercingIce": 3})["dmg"] > base_fb["dmg"],
        "Fire Power": E("fireball", {"firePower": 5})["dmg"] > base_fi["dmg"],
        "coefficients": fm.coefficient("frostbolt", fm.spell("frostbolt")["ranks"][-1]) == 3.0 / 3.5 * 0.95,
        "pénalité < 20": fm.coefficient("frostbolt", fm.spell("frostbolt")["ranks"][1]) < 1.8 / 3.5 * 0.95,
        "Improved Frostbolt": E("frostbolt", {"improvedFrostbolt": 5})["cast"] == 2.5,
        "Improved Fireball": E("fireball", {"improvedFireball": 5})["cast"] == 3.0,
        "hâte": E("frostbolt", ch=fm.character(60, "Orc", {"sp": 500, "spell_crit": 0.1, "haste": 0.1}))["cast"] < base_fb["cast"],
        "temps de recharge global": E("fire_blast")["cast"] == 1.5,
        "Frost Channeling": E("frostbolt", {"frostChanneling": 3})["mana"] < base_fb["mana"],
        "Master of Elements": E("fireball", {"masterOfElements": 3})["mana"] < base_fi["mana"],
        "Arcane Concentration": E("frostbolt", {"arcaneConcentration": 5})["mana"] < base_fb["mana"],
        "sorts en % du mana de base": abs(E("arcane_blast", {"arcaneBlast": 1})["mana"] - 0.15 * CH["base_mana"]) < 1e-6,
    }
    missing = [m for m in fm.mechanics_used() if m not in checks]
    failed = [m for m, ok in checks.items() if not ok]
    assert not missing, f"mécanique sans test : {missing}"
    assert not failed, f"mécanique inopérante : {failed}"

# ---------------------------------------------------------------- simulateurs
@test
def analytique_proche_du_monte_carlo():
    cases = [(12, "frost", {"improvedFrostbolt": 3}), (16, "frost", {"improvedFrostbolt": 5, "elementalPrecision": 2}),
             (24, "frost", {"improvedFrostbolt": 5, "elementalPrecision": 3, "frostbite": 3, "iceLance": 1, "frostChanneling": 3}),
             (16, "fire", {"improvedFireball": 5, "elementalPrecision": 2})]
    for lvl, rot, pts in cases:
        m = sl.mc(lvl, pts, "Orc", rot, 600)["total"]; a = sl.kill_analytic(lvl, pts, "Orc", rot)["total"]
        assert abs(a / m - 1) < 0.15, (lvl, rot, round(m, 1), round(a, 1))

@test
def calibrage_cible_blizzard():
    """Blizzard vise 10 à 15 s par monstre en solo : le modèle de monstre doit rester dans une marge large (8-20 s)."""
    for lvl, pts in [(12, {"improvedFrostbolt": 3}), (20, {"improvedFrostbolt": 5, "elementalPrecision": 3, "frostbite": 2, "iceLance": 1})]:
        c = sl.mc(lvl, pts, "Orc", "frost", 600)["combat"]; assert 8 <= c <= 20, (lvl, c)

@test
def monte_carlo_reproductible():
    a = sl.mc(16, {"improvedFrostbolt": 5}, n=200, seed=1)["total"]; b = sl.mc(16, {"improvedFrostbolt": 5}, n=200, seed=1)["total"]
    assert a == b

@test
def optimiseur_legal():
    r = op.leveling("Orc", 10, 14, beam=2, depth=2, mc_n=40)
    pts = {}
    for lvl, k, t, rot in r["steps"]:
        if k: pts[k] = pts.get(k, 0) + 1
        assert not fm.check_build(pts, lvl), (lvl, pts)

@test
def pvp_et_respec():
    s = pvp.score({"improvedFrostbolt": 5, "frostbite": 3, "elementalPrecision": 2, "iceLance": 1}, 20)
    assert s["score"] > 0 and s["statut"] == "EST"
    a = respec.advise_leveling(20, {"improvedFireball": 5}, {"improvedFrostbolt": 5}, 5)
    assert a["verdict"] in ("réinitialiser", "garder")

if __name__ == "__main__":
    bad = 0
    for f in T:
        try:
            f(); print(f"OK    {f.__name__}")
        except Exception as e:
            bad += 1; print(f"ÉCHEC {f.__name__} : {e}"); traceback.print_exc(limit=1)
    print(f"{len(T) - bad}/{len(T)} tests passent"); sys.exit(1 if bad else 0)
