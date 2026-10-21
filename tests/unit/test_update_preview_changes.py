"""Aperçu du rejeu de la veille (plan « Sources d'abord », étape c) : les écarts refusés par les règles de fusion sont
acceptés dans une copie seulement, pour rejouer les builds et montrer les recommandations qui changent avant tout
accord. Depuis 70450 (talent Arcane Wrath et sort Frost Blast ajoutés, Piercing Ice retiré), un talent ou un sort
ajouté et un talent retiré entrent dans l'aperçu au lieu d'empêcher le rejeu ; un sort retiré ou un autre fichier
l'empêchent toujours (la fusion ne sait pas l'appliquer). Écarts fabriqués."""

from forever.update import preview_changes


def refused(file, path, before, after):
    return {"file": file, "path": path, "before": before, "after": after}


def test_modified_added_and_removed_enter_the_preview():
    out = preview_changes([
        refused("talents.json", "frostbite.col", 4, 2),
        refused("talents.json", "arcaneWrath", None, {"key": "arcaneWrath"}),
        refused("spells.json", "frost_blast", None, "frost_blast"),
        refused("talents.json", "piercingIce", {"key": "piercingIce"}, None),
    ])
    assert [(c["kind"], c["key"], c["change"], c["field"]) for c in out] == [
        ("talent", "frostbite", "modified", "col"),
        ("talent", "arcaneWrath", "added", None),
        ("spell", "frost_blast", "added", None),
        ("talent", "piercingIce", "removed", None),
    ]
    assert out[1]["new"] == "arcaneWrath" and out[3]["old"] == "piercingIce" and out[3]["new"] is None


def test_what_the_merge_cannot_apply_stops_the_preview():
    assert preview_changes([refused("spells.json", "scorch", {"x": 1}, None)]) is None
    assert preview_changes([refused("classes.json", "Mage.x", 1, 2)]) is None
