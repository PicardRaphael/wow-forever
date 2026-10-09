"""Installation pour la sonde en jeu B (P06a, bloc A2) : emplacement de sonde `ForeverBridge_Probe2` jamais chargé
avant `/fv poll` (premier chargement sans `/reload` d'un fichier modifié après le lancement), raccourci clavier
(`Bindings.xml`) copié avec l'addon."""

from test_bridge_install import NOW, check_addon, fake_wow

from forever.bridge.install import install_bridge, touch_probe


def probe2(wow):
    return wow / "Interface" / "AddOns" / "ForeverBridge_Probe2"


def test_install_adds_the_second_probe_and_the_bindings(tmp_path):
    wow = fake_wow(tmp_path)
    install_bridge(wow)
    toc = (probe2(wow) / "ForeverBridge_Probe2.toc").read_text(encoding="utf-8").splitlines()
    for line in ("## Interface: 16001", "## LoadOnDemand: 1", "## Dependencies: ForeverBridge", "Probe2.lua"):
        assert line in toc, line
    assert (probe2(wow) / "Probe2.lua").read_text(encoding="utf-8") == 'ForeverBridge_Probe2Value = "installation"\n'
    assert check_addon.check_addon(probe2(wow)) == []
    bindings = wow / "Interface" / "AddOns" / "ForeverBridge" / "Bindings.xml"
    assert "FOREVERBRIDGE_TOGGLE" in bindings.read_text(encoding="utf-8")


def test_touch_rewrites_the_second_probe(tmp_path):
    wow = fake_wow(tmp_path)
    install_bridge(wow)
    actions = touch_probe(wow, NOW)
    text = (probe2(wow) / "Probe2.lua").read_text(encoding="utf-8")
    assert text == 'ForeverBridge_Probe2Value = "modifié à 14:05:09"\n'
    assert any("Probe2.lua" in a for a in actions)
    install_bridge(wow)
    assert (probe2(wow) / "Probe2.lua").read_text(encoding="utf-8") == 'ForeverBridge_Probe2Value = "installation"\n'
