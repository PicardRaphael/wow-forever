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


def test_added_talent_takes_the_repository_template():
    """Talent ajouté : `desc` au gabarit du dépôt (`{i}`, `desc_template` de la candidate), jamais le gabarit brut
    du client (`$s1`), gardé dans `source.client_desc` ; `desc_template` n'est pas recopié."""
    repo = doc(talent("blast"))
    cand = doc(talent("blast"), talent("wrath", tier=4, desc="causing $s1 damage", desc_template="causing {0} damage"))
    m = _Merge(VERSION, [confirmed("talent", "wrath", "added", None, None, "wrath")], "2026-10-20")
    wrath = m.talents(repo, cand)["trees"][0]["talents"][1]
    assert wrath["desc"] == "causing {0} damage" and "desc_template" not in wrath
    assert wrath["source"]["client_desc"] == "causing $s1 damage"


def test_raw_repository_description_is_replaced_by_the_template():
    """Gabarit brut déjà installé (Arcane Wrath de 1.60.1.70450 r1) : remplacé par le gabarit de la candidate, sans
    confirmation (même texte, variables numérotées) ; un gabarit `{i}` du dépôt est toujours gardé."""
    repo = doc(talent("wrath", desc="causing $s1 damage"), talent("blast", col=2, desc="deals {0} damage"))
    cand = doc(
        talent("wrath", desc="causing $s1 damage", desc_template="causing {0} damage"),
        talent("blast", col=2, desc="deals $s1 damage", desc_template="deals {0} damage now"),
    )
    m = _Merge(VERSION, [], "2026-10-20")
    wrath, blast = m.talents(repo, cand)["trees"][0]["talents"]
    assert not m.refused
    assert wrath["desc"] == "causing {0} damage" and blast["desc"] == "deals {0} damage"
    assert any(c["path"] == "wrath.desc" and c["rule"] == "metadata" for c in m.changes)


def test_renamed_talent_takes_the_template_of_the_client_description():
    """Renommage confirmé dont la décision cite l'infobulle brute du client (Wake of Fire devenu Improved Fire Blast,
    décision 285) : le dépôt prend le gabarit `{i}` de cette infobulle, jamais le texte brut."""
    raw = "cooldown reduced by ${$s1/-1000} sec"
    repo = doc(talent("wake", desc="old {0}"))
    cand = doc(talent("improved", name="Improved", desc=raw, desc_template="cooldown reduced by {0} sec"))
    rename = {**confirmed("talent", "wake", "renamed", "key", "wake", "improved"), "desc": raw}
    m = _Merge(VERSION, [rename], "2026-10-20")
    out = m.talents(repo, cand)["trees"][0]["talents"][0]
    assert not m.refused and out["key"] == "wake" and out["desc"] == "cooldown reduced by {0} sec"
