"""Poids par défaut de Naowh Forever (plan « Sources d'abord », reste de l'étape b ; décisions 272 et 288) :
`NaowhForever_BiS/StatWeights/Data/Defaults.lua` (une fonction `Spec(classe, clé, nom, gabarit, propres)` par
spécialisation, gabarits de rôle fusionnés puis poids propres ; date `StatWeightDefaultsUpdated`, poids du niveau 60
écrits à la main) lus sans exécuter de Lua, en clés de Forever Guide. Choix des poids hors Mage : l'échelle de Forever
Companion de la spécialisation (onglet de talents, rôle du libellé), sinon les poids de Naowh de la spécialisation,
sinon la première échelle de la classe (comme avant) ; un Druide Restauration n'a plus l'échelle « Balance ».

Addons fabriqués dans `tmp_path` (structures de Naowh Forever et de Forever Companion) ; poids inventés."""

from forever.gear import _weights_for, companion_spec_weights, naowh_weights
from forever.pipeline.gear_sources import read_naowh_weights

DEFAULTS = """-- Données fabriquées (structure de Naowh Forever).
local ns = _G.NaowhForever

local NONE = {}
local CASTER = { spell = 1, sta = 0.05 }
local HEALER = { heal = 1, sta = 0.05 }

local function Spec(class, key, name, role, own)
    local weights = {}
    for stat, worth in pairs(role) do weights[stat] = worth end
    for stat, worth in pairs(own or NONE) do weights[stat] = worth end
    return { class = class, key = key, name = name, weights = weights }
end

ns.StatWeightDefaultsUpdated = "5 Oct 2026"

ns.StatWeightDefaults = {
    Spec("DRUID", "balance-druid", "Balance", CASTER, { arcane = 0.6, int = 0.3,
        shit = 13, haste = 9 }),
    Spec("HUNTER", "survival-hunter", "Survival", CASTER, { sta = 0.2, mp5 = 0.4, threat = 2 }),
    Spec("DRUID", "restoration-druid", "Restoration", HEALER, { spi = 0.4 }),
}
"""

COMPANION = """ForeverCompanionData = ForeverCompanionData or {}
ForeverCompanionData.weights = {
  DRUID={
    {id=1,label="Balance DPS",tab=1,icon="x",w={Intellect=1,SpellPower=2}},
    {id=2,label="Feral DPS",tab=2,icon="x",w={Agility=2}},
    {id=3,label="Healer",tab=3,icon="x",w={Healing=3,Spirit=1}},
    {id=4,label="Feral Tank",tab=2,icon="x",w={Stamina=3}},
  },
  HUNTER={
    {id=5,label="DPS",tab=1,icon="x",w={Agility=1}},
  },
}
"""


def addons(tmp_path):
    root = tmp_path / "AddOns"
    naowh = root / "NaowhForever_BiS" / "StatWeights" / "Data"
    naowh.mkdir(parents=True)
    (naowh / "Defaults.lua").write_text(DEFAULTS, encoding="utf-8")
    comp = root / "ForeverCompanion" / "Data"
    comp.mkdir(parents=True)
    (comp / "Weights.lua").write_text(COMPANION, encoding="utf-8")
    return root


def test_defaults_are_read_with_their_role_template_and_date(tmp_path):
    data = read_naowh_weights(addons(tmp_path))
    assert data.updated == "2026-10-05"
    balance = data.specs["balance-druid"]
    assert balance.class_token == "DRUID" and balance.name == "Balance"
    assert balance.weights == {"spell": 1.0, "sta": 0.05, "arcane": 0.6, "int": 0.3, "shit": 13.0, "haste": 9.0}
    assert data.specs["survival-hunter"].weights["sta"] == 0.2  # le poids propre l'emporte sur le gabarit


def test_naowh_weights_in_guide_keys(tmp_path):
    w = naowh_weights(addons(tmp_path), "balance-druid")
    assert w == {"sp": 1.0, "sta": 0.05, "arc": 0.6, "int": 0.3, "shit": 13.0}  # hâte : pas de clé chez Guide
    assert naowh_weights(addons(tmp_path), "survival-hunter") == {"sp": 1.0, "sta": 0.2, "mp5": 0.4}
    assert naowh_weights(addons(tmp_path), "fury-warrior") == {}
    assert naowh_weights(tmp_path / "vide", "balance-druid") == {}


def test_companion_scale_of_the_spec(tmp_path):
    trees = ["Balance", "Feral Combat", "Restoration"]
    weights, label = companion_spec_weights(addons(tmp_path), "DRUID", "restoration-druid", trees)
    assert label == "Healer" and weights == {"hp": 3.0, "spi": 1.0}
    assert companion_spec_weights(addons(tmp_path), "DRUID", "feral-tank-druid", trees)[1] == "Feral Tank"
    assert companion_spec_weights(addons(tmp_path), "DRUID", "feral-dps-druid", trees)[1] == "Feral DPS"
    hunter = ["Beast Mastery", "Marksmanship", "Survival"]
    assert companion_spec_weights(addons(tmp_path), "HUNTER", "survival-hunter", hunter) is None  # onglet absent


def test_weights_choice_for_other_classes(tmp_path, make_deps):
    root = addons(tmp_path)
    deps = make_deps(wow_dir=tmp_path)
    w, source = _weights_for(deps, root, "DRUID", level=60, race="Tauren", spec="restoration-druid")
    assert w == {"hp": 3.0, "spi": 1.0} and source.startswith("Forever Companion") and "Healer" in source
    w, source = _weights_for(deps, root, "HUNTER", level=60, race="Orc", spec="survival-hunter")
    assert w == {"sp": 1.0, "sta": 0.2, "mp5": 0.4} and "Naowh" in source and "2026-10-05" in source
    assert "niveau 60" in source
    w, source = _weights_for(deps, root, "DRUID", level=60, race="Tauren", spec="")
    assert w == {"int": 1.0, "sp": 2.0} and source == "Forever Companion (échelle de la classe, suppose)"


def test_naowh_weights_freshness_is_reported(tmp_path, make_deps):
    from forever.sources import _dated_addons

    addons(tmp_path)
    deps = make_deps(wow_dir=tmp_path.parent / tmp_path.name)
    (tmp_path / "Interface").mkdir()
    (tmp_path / "AddOns").rename(tmp_path / "Interface" / "AddOns")
    rows = {r["source"]: r for r in _dated_addons(deps, "2026-10-16")}
    naowh = rows["naowh_weights"]
    assert naowh["domain"] == "poids" and naowh["status"] == "en retard" and "2026-10-05" in naowh["detail"][0]
