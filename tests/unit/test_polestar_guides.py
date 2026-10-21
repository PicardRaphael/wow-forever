"""Guides de Polestar lus comme squelette des routes au-delà des parcours gratuits de RestedXP (plan « Sources
d'abord », étape d ; décision 289) : fichiers `.guide` du clone en cache (lecture seule, usage privé, GPL-3.0, rien
recopié dans le dépôt), traduits dans la structure des parcours de RestedXP pour le même rejeu et la même base adaptée :
en-tête (identifiant, titre, niveaux, camp, races, classes, suite), étapes (`accept`, `turnin`, `complete`, `kill` ou
`collect` liés à une quête, `level`), conditions `only` (classes OU, races OU, camps OU ; groupes ET ; `!` nie), contenu
de groupe (`group`) écarté comme les donjons de RestedXP ; seuls les guides de la catégorie Leveling servent.

Guides fabriqués ici (structure du format v1 de Polestar) ; quêtes et niveaux inventés."""

from forever.polestar import parse_polestar, read_polestar_guides
from forever.rxp_guides import Who, applies, guide_chain

GUIDE = """guide forever/horde/zone-a
title Zone A
faction Horde
levels 20-25
zone Zone A
next forever/horde/zone-b

step Camp
  accept 900001
  accept 900002 only Mage,Warlock
  kill 900 x8 quest 900001.1
  tip Un conseil.
  turnin 900001
  only Orc,Troll

step Donjon
  accept 900003 group 5
  level 22
  complete 900002
  turnin 900002
"""

NEXT = """guide forever/horde/zone-b
title Zone B
faction Horde
levels 25-30
zone Zone B

step Suite
  accept 900010
  turnin 900010
"""

CLASS_GUIDE = """guide forever/class/mage-chain
title Chaîne du Mage
category Class
class Mage
levels 20-30
zone Zone A

step Chaîne
  accept 900020
"""


def test_header_and_steps_become_a_replayable_guide():
    g = parse_polestar(GUIDE, "zone-a.guide")
    assert g.name == "20-25 Zone A" and g.levels == (20, 25)
    assert g.next == (("25-30 Zone B", None),) or g.next[0][0].startswith("forever/horde/zone-b")
    camp, donjon = g.steps
    assert [(a.kind, a.ref, a.filter) for a in camp.actions] == [
        ("accept", 900001, None),
        ("accept", 900002, "mage/warlock"),
        ("objective", 900001, None),
        ("turnin", 900001, None),
    ]
    assert camp.filter == "orc/troll"  # condition de l'étape
    assert [(a.kind, a.ref) for a in donjon.actions] == [("grind", 22), ("objective", 900002), ("turnin", 900002)]
    assert g.filter == "horde"


def test_conditions_and_and_or_and_negation():
    g = parse_polestar(GUIDE.replace("only Orc,Troll", "only Mage,!Gnome,Alliance"), "x.guide")
    expr = g.steps[0].filter
    assert applies(expr, Who("Mage", "Human", "Alliance")) and not applies(expr, Who("Mage", "Gnome", "Alliance"))
    assert not applies(expr, Who("Warrior", "Human", "Alliance"))


def test_library_follows_next_and_keeps_leveling_guides_only(tmp_path):
    root = tmp_path / "polestar" / "guides" / "forever" / "horde"
    root.mkdir(parents=True)
    (root / "zone-a.guide").write_text(GUIDE, encoding="utf-8")
    (root / "zone-b.guide").write_text(NEXT, encoding="utf-8")
    cls = tmp_path / "polestar" / "guides" / "forever" / "class"
    cls.mkdir()
    (cls / "mage.guide").write_text(CLASS_GUIDE, encoding="utf-8")
    library = read_polestar_guides(tmp_path / "polestar")
    assert sorted(g.name for g in library.guides) == ["20-25 Zone A", "25-30 Zone B"]
    chain = guide_chain(library, Who("Mage", "Orc", "Horde"), start="20-25 Zone A")
    assert [g.name for g in chain.guides] == ["20-25 Zone A", "25-30 Zone B"]


def test_steps_carry_no_raw_polestar_line():
    """La route est livrée dans RestedXP : une étape de Polestar ne garde aucune ligne brute (syntaxe de Polestar) ; le
    corps du guide livré est réécrit depuis ses actions (`forever.compare._adapted_lines`)."""
    g = parse_polestar(GUIDE, "zone-a.guide")
    assert all(step.raw == () for step in g.steps)


def test_polestar_clone_is_made_then_updated_read_only(tmp_path):
    """`forever route polestar` (décision 289) : premier appel, clone superficiel du dépôt public dans le cache ; ensuite,
    récupération du dernier commit et remise de la copie dessus ; jamais une écriture vers le dépôt distant. Lanceur de
    git simulé, aucun réseau."""
    from forever.pipeline.polestar_fetch import REPO, update_polestar

    calls = []

    def run(args, cwd=None):
        calls.append((list(args), cwd))
        if args[:2] == ["git", "clone"]:
            (tmp_path / "third_party" / "polestar" / ".git").mkdir(parents=True)

    clone = update_polestar(tmp_path, run=run)
    assert calls[0][0][:4] == ["git", "clone", "--depth", "1"] and REPO in calls[0][0]
    calls.clear()
    update_polestar(tmp_path, run=run)
    assert [c[0][:2] for c in calls] == [["git", "fetch"], ["git", "reset"]]
    assert all(c[1] == clone for c in calls) and not any("push" in c[0] for c in calls)


def test_a_git_failure_points_to_route_polestar(tmp_path, monkeypatch):
    """Un échec de git (réseau) se rapporte à `forever route polestar`, pas au passage de `forever update`."""
    import pytest

    from forever.pipeline import gitops, polestar_fetch

    def failing(args, cwd, timeout=None):
        return __import__("subprocess").CompletedProcess(args, 128, "", "fatal: unable to access")

    monkeypatch.setattr(gitops, "subprocess_runner", failing)
    with pytest.raises(gitops.GitOpsError) as err:
        polestar_fetch.update_polestar(tmp_path)
    assert "forever route polestar" in err.value.action and "forever update" not in err.value.action
