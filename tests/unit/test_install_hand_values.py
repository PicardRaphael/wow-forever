"""Valeurs écrites à la main d'une tranche (`mechanics.json`, jamais décodé : hérité tel quel par `forever decode`) :
installées par une révision numérotée et reportées à chaque nouvelle version, comme les règles de lecture et d'origine
(décision 263 ; demande de l'utilisateur du 2026-10-19 pour `route.start_zones` et `route.filters`).

- révision de la version courante : `mechanics.json` du dépôt modifié depuis le manifeste et porté par la candidate est
  installé (changement `rules` par clé), manifeste réécrit ;
- nouvelle version : une candidate décodée **avant** l'ajout des valeurs (version finale du 4 novembre décodée par la
  veille, par exemple) reçoit les valeurs et les règles d'origine du dépôt ; les règles des correctifs du serveur de
  la candidate sont gardées ; le journal de la révision 1 nomme les clés reportées.

Valeurs : `route.start_zones` et `route.filters` lues dans la version courante du dépôt (`forever/data/`), installées
sur une copie ramenée à la version des extraits ; candidate décodée des fixtures 1.60.1.70124."""

import json
import shutil

from conftest import CLASS_FIXTURE_VERSION as LOCAL_VERSION  # version des extraits, pas la version installée
from conftest import DATA_DIR, WAGO_70124, isolated_deps, read_json

from forever.manifest import load_manifest, write_manifest
from forever.pipeline.decode import decode_version
from forever.pipeline.install import apply_install, plan_install, render_install_report
from forever.store import ensure_integrity

MECHANICS, ORIGINS = "mechanics.json", "origins.json"
KEYS = ("route.filters", "route.start_zones")
NEWER = "1.60.1.70150"  # version fictive plus récente que la copie : la « version finale » des tests
SERVER_RULE = {
    "file": "spells.json",
    "paths": ["/spells/frostbolt/ranks"],
    "origin": "correctif_serveur",
    "source": "correctif du serveur de test",
    "certainty": "certain",
    "reason": "règle propre à la candidate",
}


def current_dir():
    return DATA_DIR / load_manifest(DATA_DIR)["game_version"]


def hand_values():
    """Les deux valeurs et leurs règles d'origine, lues dans la version courante du dépôt."""
    values = read_json(current_dir() / MECHANICS)["values"]
    rules = [r for r in read_json(current_dir() / ORIGINS)["rules"] if any(f"/values/{k}" in r["paths"] for k in KEYS)]
    return {k: values[k] for k in KEYS}, rules


def write(path, doc, indent):
    path.write_bytes((json.dumps(doc, ensure_ascii=False, indent=indent) + "\n").encode("utf-8"))


def add_hand_values(data):
    values, rules = hand_values()
    mech = read_json(data / LOCAL_VERSION / MECHANICS)
    mech["values"].update(values)
    write(data / LOCAL_VERSION / MECHANICS, mech, 1)
    origins = read_json(data / LOCAL_VERSION / ORIGINS)
    origins["rules"] += rules
    write(data / LOCAL_VERSION / ORIGINS, origins, 2)


def decode(data, tmp_path, name="cand"):
    return decode_version(
        isolated_deps(tmp_path, data_dir=data), LOCAL_VERSION, csv_dir=WAGO_70124, out=tmp_path / name
    )


def relabel(cand, tmp_path, server_rule=False):
    """Candidate relabellisée en version plus récente (aucun accès réseau), avec au besoin une règle de correctif."""
    copy = tmp_path / "cand-new"
    shutil.copytree(cand.root, copy)
    (copy / LOCAL_VERSION).rename(copy / NEWER)
    sources = read_json(copy / NEWER / "sources.json")
    sources["game_version"] = NEWER
    write(copy / NEWER / "sources.json", sources, 2)
    if server_rule:
        origins = read_json(copy / NEWER / ORIGINS)
        origins["rules"].append(SERVER_RULE)
        write(copy / NEWER / ORIGINS, origins, 2)
    write_manifest(copy)
    return str(copy)


def rules_changes(doc, file=None):
    return [c for c in doc["changes"] if c["rule"] == "rules" and (file is None or c["file"] == file)]


def test_the_repository_has_both_values_and_their_origins():
    values, rules = hand_values()
    assert set(values) == set(KEYS) and all("value" in v for v in values.values())
    assert {p for r in rules for p in r["paths"]} >= {f"/values/{k}" for k in KEYS}


def test_revision_installs_the_hand_values(data_at_class_fixture_version, tmp_path, make_deps):
    data = data_at_class_fixture_version
    add_hand_values(data)  # écrites dans le dépôt, manifeste non réécrit (règles d'une tranche)
    cand = decode(data, tmp_path)
    plan = plan_install(make_deps(data_dir=data), str(cand.root))
    assert not plan["refused"]
    assert {c["path"] for c in rules_changes(plan, MECHANICS)} == {f"values.{k}" for k in KEYS}
    assert rules_changes(plan, ORIGINS)
    report = render_install_report(plan)
    assert all(f"values.{k}" in report for k in KEYS)
    revision = apply_install(make_deps(data_dir=data), str(cand.root), motif="test")
    ensure_integrity(data)  # manifeste réécrit par l'installation
    assert {c["path"] for c in rules_changes(revision, MECHANICS)} == {f"values.{k}" for k in KEYS}
    values, _ = hand_values()
    installed = read_json(data / LOCAL_VERSION / MECHANICS)["values"]
    assert {k: installed[k] for k in KEYS} == values


def test_a_new_version_decoded_before_the_values_still_gets_them(data_at_class_fixture_version, tmp_path, make_deps):
    data = data_at_class_fixture_version
    stale = relabel(decode(data, tmp_path), tmp_path, server_rule=True)  # décodée avant l'ajout des valeurs
    assert not set(KEYS) & set(read_json(tmp_path / "cand-new" / NEWER / MECHANICS)["values"])
    add_hand_values(data)
    write_manifest(data)  # valeurs installées dans la version courante
    revision = apply_install(make_deps(data_dir=data), stale, motif="nouvelle version", new_version=True)
    ensure_integrity(data)
    vdir = data / NEWER
    values, rules = hand_values()
    mech = read_json(vdir / MECHANICS)
    assert {k: mech["values"][k] for k in KEYS} == values
    assert mech["inherited_from"] == LOCAL_VERSION
    installed_rules = read_json(vdir / ORIGINS)["rules"]
    assert all(r in installed_rules for r in rules)
    assert SERVER_RULE in installed_rules  # règles des correctifs de la candidate gardées
    first = read_json(vdir / "revisions.json")["revisions"][0]
    assert {c["path"] for c in rules_changes(first, MECHANICS)} == {f"values.{k}" for k in KEYS}
    assert rules_changes(first, ORIGINS)
    assert rules_changes(revision, MECHANICS)


def test_a_new_version_decoded_after_the_values_inherits_them(data_at_class_fixture_version, tmp_path, make_deps):
    data = data_at_class_fixture_version
    add_hand_values(data)
    write_manifest(data)
    cand = relabel(decode(data, tmp_path), tmp_path)
    revision = apply_install(make_deps(data_dir=data), cand, motif="nouvelle version", new_version=True)
    assert rules_changes(revision) == []  # rien à reporter : la candidate les a héritées
    values, _ = hand_values()
    mech = read_json(data / NEWER / MECHANICS)["values"]
    assert {k: mech[k] for k in KEYS} == values
