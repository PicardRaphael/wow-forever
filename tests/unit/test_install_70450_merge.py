"""1.60.1.70450, bloc A : la fusion d'une installation accepte, s'ils sont confirmés dans `confirmed_changes.json`
(écarts tranchés « client » par l'utilisateur, décision 285), les changements de la refonte du Mage que les règles
refusaient d'office :

- champ d'un talent (`tier`, `max`, `prereq` : Missile Barrage passe en ligne 1 sur 2 points) ;
- talent ajouté (Arcane Wrath) ; sort ajouté (Frost Blast) ;
- marqueur de modèle d'un talent (`model`) repris de la candidate (champ ajouté).

Sans entrée confirmée, ces changements restent refusés. Documents fabriqués ici ; aucun chiffre de jeu."""

from forever.pipeline.install import _Merge

VERSION = "1.60.1.99999"


def talent(key, tier=1, col=1, max_=1, ranks=((1,),), **extra):
    return {"key": key, "name": key, "tree": "Arcane", "tier": tier, "col": col, "max": max_, "prereq": None,
            "ranks": [list(r) for r in ranks], "tooltip_values": [list(r) for r in ranks], "certainty": "FC-1",
            "source": {}, **extra}  # fmt: skip


def doc(*talents):
    return {"trees": [{"name": "Arcane", "talents": list(talents)}]}


def confirmed(kind, key, change, field, old, new):
    return {"kind": kind, "key": key, "change": change, "field": field, "old": old, "new": new,
            "nature": "client", "decision": "décision de test"}  # fmt: skip


def test_talent_field_change_needs_a_confirmation():
    repo, cand = doc(talent("barrage", tier=4)), doc(talent("barrage", tier=1))
    m = _Merge(VERSION, [], "2026-10-20")
    m.talents(repo, cand)
    assert [r["path"] for r in m.refused] == ["barrage.tier"]
    m = _Merge(VERSION, [confirmed("talent", "barrage", "modified", "tier", 4, 1)], "2026-10-20")
    out = m.talents(repo, cand)
    assert not m.refused and out["trees"][0]["talents"][0]["tier"] == 1
    assert any(c["rule"] == "confirmed" and c["path"] == "barrage.tier" for c in m.changes)


def test_added_talent_needs_a_confirmation():
    repo, cand = doc(talent("blast")), doc(talent("blast"), talent("wrath", tier=4))
    m = _Merge(VERSION, [], "2026-10-20")
    m.talents(repo, cand)
    assert [r["path"] for r in m.refused] == ["wrath"]
    m = _Merge(VERSION, [confirmed("talent", "wrath", "added", None, None, "wrath")], "2026-10-20")
    out = m.talents(repo, cand)
    keys = [t["key"] for t in out["trees"][0]["talents"]]
    assert not m.refused and keys == ["blast", "wrath"]


def test_model_marker_comes_from_the_candidate():
    repo = doc(talent("blast"))
    cand = doc(talent("blast", model="intellect_spell_power"))
    m = _Merge(VERSION, [], "2026-10-20")
    out = m.talents(repo, cand)
    assert not m.refused and out["trees"][0]["talents"][0]["model"] == "intellect_spell_power"


def spells_doc(**spells):
    return {"rank_format": ["level", "min", "max"], "spells": dict(spells)}


def spell(ranks=((1, 2, 3),), **extra):
    return {"school": "frost", "ranks": [list(r) for r in ranks], "name": "x", "spell_ids": [1], **extra}


def test_added_spell_needs_a_confirmation():
    repo = spells_doc(frostbolt=spell())
    cand = spells_doc(frostbolt=spell(), frost_blast=spell(ranks=((24, 5, 6),)))
    m = _Merge(VERSION, [], "2026-10-20")
    m.spells(repo, cand)
    assert [r["path"] for r in m.refused] == ["frost_blast"]
    m = _Merge(VERSION, [confirmed("spell", "frost_blast", "added", None, None, "frost_blast")], "2026-10-20")
    out = m.spells(repo, cand)
    assert not m.refused and out["spells"]["frost_blast"]["ranks"] == [[24, 5, 6]]


def test_spell_field_change_needs_a_confirmation():
    repo = spells_doc(ice_lance=spell(frozen_mult=4.0))
    cand = spells_doc(ice_lance=spell(frozen_mult=3))
    m = _Merge(VERSION, [], "2026-10-20")
    m.spells(repo, cand)
    assert [r["path"] for r in m.refused] == ["ice_lance.frozen_mult"]
    m = _Merge(VERSION, [confirmed("spell", "ice_lance", "modified", "frozen_mult", 4.0, 3)], "2026-10-20")
    out = m.spells(repo, cand)
    assert not m.refused and out["spells"]["ice_lance"]["frozen_mult"] == 3
