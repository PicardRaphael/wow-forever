"""Décision 300 (demande du 2026-11-03) : mes personnages de la bêta, c'est fini. Ils restent archivés, et ne sont plus
jamais recopiés, importés, proposés ni utilisés pour un conseil. Une fois la version finale adoptée, `forever profile
import` ne prend que les relevés de la version finale : produit adopté, version du client connue, royaume hors bêta,
relevé postérieur à l'adoption. Tout relevé de la bêta est ignoré sans question, prix des royaumes compris (les
SavedVariables de la bêta ont suivi le dossier du compte dans celui de la version finale).

SavedVariables fabriquées dans `tmp_path` (ForeverLogger écrit à la main, Auctionator de `tests/fixtures/addon/`)."""

import json
import shutil
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from conftest import FIXTURES
from test_installs import FINAL, FINAL_V, make_root

from forever.installs import discover
from forever.pipeline.client_builds import ClientBuild, adopt_product, record_build
from forever.profile import load_profile
from forever.profile_import import apply_import, plan_import

ADOPTED = datetime(2026, 9, 28, tzinfo=UTC)  # avant les prix du « Royaume » de la fixture (29 septembre)
BEFORE = datetime(2026, 9, 20, 12, tzinfo=UTC)
AFTER = datetime(2026, 10, 1, 12, tzinfo=UTC)
CHARACTERS = [  # (GUID, nom, royaume, instant du relevé)
    ("Player-1-0000000A", "Jen", "Classic Beta PvE", BEFORE),  # bêta : royaume et date
    ("Player-1-0000000B", "Krypto", "Royaume", BEFORE),  # avant l'adoption : client inconnu
    ("Player-1-0000000C", "Bob", "Classic Beta PvP", AFTER),  # royaume de la bêta
    ("Player-1-0000000D", "Neuf", "Royaume", AFTER),  # version finale
]


def logger_db(path):
    rows = []
    for guid, name, realm, when in CHARACTERS:
        rows.append(
            f'["{guid}"] = {{ ["name"] = "{name}", ["realm"] = "{realm}", ["class"] = "MAGE", ["race"] = "Gnome", '
            f'["snapshots"] = {{ {{ ["reason"] = "connexion", ["time"] = {int(when.timestamp())}, ["level"] = 5 }} }} }},'
        )
    path.write_text('ForeverLoggerDB = {\n["schema"] = 1,\n["characters"] = {\n' + "\n".join(rows) + "\n},\n}\n",
                    encoding="utf-8")  # fmt: skip


@pytest.fixture
def mixed(make_deps, tmp_path):
    root = make_root(tmp_path / "jeu", [(FINAL, FINAL_V)], {"_fictif_": (FINAL, "WowF.exe")})
    wow = root / "_fictif_"
    sv = wow / "WTF" / "Account" / "COMPTE" / "SavedVariables"
    sv.mkdir(parents=True)
    logger_db(sv / "ForeverLogger.lua")
    prices = (FIXTURES / "addon" / "Auctionator.lua").read_bytes()
    (sv / "Auctionator.lua").write_bytes(prices.replace(b'["AutreRoyaume"]', b'["Classic Beta PvE"]'))
    deps = replace(make_deps(now=datetime(2026, 10, 2, tzinfo=UTC)), wow_dir=wow)
    record_build(deps.cache_dir, ClientBuild(FINAL_V, ADOPTED, FINAL))
    adopt_product(deps.cache_dir, next(i for i in discover([root]) if i.product == FINAL), ADOPTED)
    return deps, sv


def test_only_the_characters_of_the_final_version_are_imported(mixed):
    deps, sv = mixed
    plan = plan_import(deps, sv_dir=sv, logs_dir=None)
    names = {c.get("character") for c in plan["changes"]} - {None}
    assert names == {"Neuf"}
    proposed = [*plan["skipped"], *plan["conflicts"]]
    assert not [p for p in proposed if (p.get("name") or p.get("character")) in {"Jen", "Krypto", "Bob"}]
    apply_import(deps, plan)
    assert list(load_profile(deps.profile_path)["characters"]) == ["Neuf"]


def test_prices_of_the_beta_realms_are_ignored(mixed):
    deps, sv = mixed
    plan = plan_import(deps, sv_dir=sv, logs_dir=None)
    realms = {c.get("realm") for c in plan["changes"] if c.get("realm")}
    assert realms == {"Royaume"}


def test_the_beta_is_ignored_without_question(mixed):
    deps, sv = mixed
    plan = plan_import(deps, sv_dir=sv, logs_dir=None)
    assert any("bêta ignoré" in n for n in plan["notes"])  # une ligne d'information, aucune proposition
    assert json.dumps(plan["changes"], ensure_ascii=False).count("Classic Beta") == 0


def test_without_adoption_nothing_changes(make_deps, tmp_path):
    """Avant l'adoption (bêta seule), l'import reste celui de PV1 : rien n'est filtré."""
    root = make_root(tmp_path / "jeu", [(FINAL, FINAL_V)], {"_fictif_": (FINAL, "WowF.exe")})
    sv = root / "_fictif_" / "WTF" / "Account" / "COMPTE" / "SavedVariables"
    sv.mkdir(parents=True)
    logger_db(sv / "ForeverLogger.lua")
    deps = replace(make_deps(), wow_dir=root / "_fictif_")
    plan = plan_import(deps, sv_dir=sv, logs_dir=None)
    assert {c.get("character") for c in plan["changes"]} >= {"Jen", "Neuf"}
    shutil.rmtree(root)
