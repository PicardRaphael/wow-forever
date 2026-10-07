"""Origine `correctif_serveur` des arbres de talents touchés par un correctif du serveur (T08e, DON17).

Un correctif qui ajoute, retire ou déplace un nœud, change une arête ou l'entrée d'un nœud touche la liste des talents
de son arbre (composition, rangées, colonnes, prérequis) et son contrôle (`tree_checks`) : ces éléments prennent
l'origine `correctif_serveur`, pour qu'une perte de correctif qui ne toucherait que les arbres soit vue (décision 207).

Cas réel réduit : la seule suppression du nœud 105929 et de son entrée (poussée 112347, fixture `DBCache.bin` de
T08c) ; sans DON17, elle ne laissait aucune trace (enregistrements non attribués, aucune valeur perdue). Fixtures :
`tests/fixtures/hotfix/`, `tests/fixtures/dbd/`, `tests/fixtures/wago/1.60.1.70170/`."""

import pytest
from conftest import DATA_DIR, FIXTURES, isolated_deps, read_json

from forever.engine_inputs import hotfix_losses
from forever.origins import ORIGINS_NAME, OriginResolver, check_version
from forever.pipeline.dbd import layouts_from_json
from forever.pipeline.decode import decode_version
from forever.pipeline.hotfix_overlay import SERVER_ORIGIN, hotfix_source

HOTFIX = FIXTURES / "hotfix"
LAYOUTS_DOC = read_json(FIXTURES / "dbd" / "layouts-1.60.1.70170.json")
WAGO = FIXTURES / "wago" / "1.60.1.70170"
VERSION = "1.60.1.70170"  # build des fixtures DBCache.bin, dispositions et tables
RULES = read_json(DATA_DIR / VERSION / "decode_rules.json")
DELETED = (("TraitNode", 105929), ("TraitNodeXTraitNodeEntry", 128126))  # sources.json de 70245 r3 : non attribués


def source(only=None):
    found = hotfix_source(
        HOTFIX / "DBCache.bin",
        layouts_from_json(LAYOUTS_DOC),
        {"repo": LAYOUTS_DOC["repo"], "commit": LAYOUTS_DOC["commit"], "files": {}},
        read_json(HOTFIX / "hotfixes-70170.json")["entries"],
        VERSION,
        RULES,
        "2026-10-05T10:00:00Z",
    )
    if only is None:
        return found
    kept = {k: e for k, e in found.resolved.applicable.items() if k in only}
    assert set(kept) == set(only)
    return found._replace(resolved=found.resolved._replace(applicable=kept))


@pytest.fixture(scope="module")
def decoded(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("don17")

    def run(name, hotfixes):
        return decode_version(isolated_deps(tmp), VERSION, csv_dir=WAGO, out=tmp / name, hotfixes=hotfixes).root

    return {
        "suppression": run("suppression", source(DELETED)) / VERSION,
        "tout": run("tout", source()) / VERSION,
        "sans": run("sans", None) / VERSION,
    }


def fury_index(vdir, key):
    trees = read_json(vdir / "classes.json")["classes"]["Warrior"]["trees"]
    [index] = [i for i, tree in enumerate(trees) if any(t["key"] == key for t in tree["talents"])]
    return index


def server_paths(vdir):
    rules = read_json(vdir / ORIGINS_NAME)["rules"]
    return {p for r in rules if r["origin"] == SERVER_ORIGIN and r["file"] == "classes.json" for p in r["paths"]}


def test_a_deleted_node_marks_the_talents_of_its_tree(decoded):
    vdir = decoded["suppression"]
    tree = fury_index(decoded["sans"], "precision")  # arbre du talent retiré, lu sans le correctif
    talents = read_json(vdir / "classes.json")["classes"]["Warrior"]["trees"]
    assert "precision" not in {t["key"] for t in talents[tree]["talents"]}
    resolver = OriginResolver.load(vdir)
    assert resolver.origin("classes.json", f"/classes/Warrior/trees/{tree}/talents/0/name") == SERVER_ORIGIN
    assert resolver.origin("classes.json", f"/classes/Warrior/tree_checks/{tree}/tree") == SERVER_ORIGIN
    other = next(i for i in range(len(talents)) if i != tree)
    assert resolver.origin("classes.json", f"/classes/Warrior/trees/{other}/talents/0/name") == "client"
    assert resolver.origin("classes.json", "/classes/Mage/trees/0/talents/0/name") == "client"
    assert read_json(vdir / "sources.json")["hotfixes"]["unattributed"] == []
    issues = {(i.kind, i.file, i.path) for i in check_version(vdir.parent, VERSION).issues}
    baseline = {(i.kind, i.file, i.path) for i in check_version(decoded["sans"].parent, VERSION).issues}
    assert issues == baseline


def test_a_tree_only_loss_is_seen(decoded):
    tree = fury_index(decoded["sans"], "precision")
    losses = hotfix_losses(decoded["suppression"], decoded["sans"])
    assert losses
    assert all(c.pointer.startswith(f"/classes/Warrior/trees/{tree}/talents/") for c in losses)
    assert all(c.origin_before == SERVER_ORIGIN and c.origin_after == "client" for c in losses)


def test_the_full_redesign_marks_the_reshaped_trees_without_dead_rules(decoded):
    vdir = decoded["tout"]
    paths = server_paths(vdir)
    fury = fury_index(vdir, "goreDrinker")
    assert f"/classes/Warrior/trees/{fury}/talents" in paths
    assert not any(p.startswith(f"/classes/Warrior/trees/{fury}/talents/") for p in paths)  # inclus dans la liste
    assert any(p.startswith("/classes/Warrior/spells/") for p in paths)
    issues = {(i.kind, i.file, i.path) for i in check_version(vdir.parent, VERSION).issues}
    baseline = {(i.kind, i.file, i.path) for i in check_version(decoded["sans"].parent, VERSION).issues}
    assert issues == baseline
