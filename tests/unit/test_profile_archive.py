"""Profil au lancement (LN1, bloc F, décision 271) : schéma 4, personnages de la bêta archivés (gardés, plus jamais
actifs), nouveaux personnages de la version finale importés à côté d'un homonyme archivé, produit de chaque
personnage, tous les comptes de l'installation lus ; mesures encore héritées de la bêta listées.

Écart au plan, assumé au bloc : les personnages **actifs** restent indexés par leur nom (pont, MCP, exports les
lisent ainsi) ; seuls les archivés sont rangés sous `<nom>-<royaume>`, dans `archived_characters`."""

import json
import shutil
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from conftest import FIXTURES, LOCAL_VERSION, PRODUCT
from test_installs import FINAL, FINAL_V, make_root

from forever.cli import main
from forever.errors import InvalidArgumentError
from forever.manifest import write_manifest
from forever.pipeline.refresh import inherited_measures
from forever.profile import SCHEMA_VERSION, archive_characters, load_profile, read_profile, use
from forever.profile_import import apply_import, plan_import

ADDON = FIXTURES / "addon"
NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)
SCHEMA_3 = {
    "schema_version": 3,
    "active": "Moi",
    "characters": {
        "Moi": {
            "class": {
                "value": "Mage",
                "source": "joueur",
                "at": "2026-10-01T10:00:00Z",
                "client_build": None,
                "certainty": "certain",
            },
            "realm": "Royaume",
            "planned": False,
            "validated": False,
            "game_version": "1.60.1.70374",
            "updated_at": "2026-10-01T10:00:00Z",
        },
        "Prevu": {"realm": None, "planned": True, "updated_at": "2026-10-02T10:00:00Z"},
    },
    "realms": {},
}


@pytest.fixture
def deps(make_deps):
    deps = make_deps(now=NOW)
    deps.profile_path.parent.mkdir(parents=True)
    deps.profile_path.write_text(json.dumps(SCHEMA_3), encoding="utf-8")
    return deps


def test_schema_4_and_the_original_kept_at_the_first_write(deps):
    original = deps.profile_path.read_bytes()
    assert SCHEMA_VERSION == 4
    assert load_profile(deps.profile_path)["archived_characters"] == {}  # lecture : rien d'écrit
    assert deps.profile_path.read_bytes() == original
    use(deps, "Moi")
    assert json.loads(deps.profile_path.read_text(encoding="utf-8"))["schema_version"] == 4
    assert (deps.profile_path.parent / "profile.json.schema3.bak").read_bytes() == original


def test_beta_characters_are_archived(deps):
    archived = archive_characters(deps, PRODUCT, NOW)
    assert archived == ["Moi-Royaume", "Prevu"]
    doc = load_profile(deps.profile_path)
    assert doc["characters"] == {} and doc["active"] is None
    moi = doc["archived_characters"]["Moi-Royaume"]
    assert moi["archived"] == {"at": "2026-11-04T09:00:00Z", "product": PRODUCT, "game_version": "1.60.1.70374"}
    assert moi["class"]["value"] == "Mage"


def test_an_archived_character_is_never_made_active(deps):
    archive_characters(deps, PRODUCT, NOW)
    with pytest.raises(InvalidArgumentError, match="archivé"):
        use(deps, "Moi")


def test_only_the_given_product_is_archived(deps):
    doc = json.loads(deps.profile_path.read_text(encoding="utf-8"))
    doc["characters"]["Moi"]["product"] = FINAL
    deps.profile_path.write_text(json.dumps(doc), encoding="utf-8")
    assert archive_characters(deps, PRODUCT, NOW) == ["Prevu"]
    assert list(load_profile(deps.profile_path)["characters"]) == ["Moi"]


def test_the_view_lists_archived_characters(deps):
    archive_characters(deps, PRODUCT, NOW)
    view = read_profile(deps)
    assert view["characters"] == [] and view["archived"] == ["Moi-Royaume", "Prevu"]


def final_install(tmp_path, accounts=("COMPTE",)):
    root = make_root(tmp_path / "jeu", [(FINAL, FINAL_V)], {"_fictif_": (FINAL, "WowF.exe")})
    wow = root / "_fictif_"
    for account in accounts:
        sv = wow / "WTF" / "Account" / account / "SavedVariables"
        sv.mkdir(parents=True)
        shutil.copy(ADDON / "ForeverLoggerDB.lua", sv / "ForeverLogger.lua")
    return wow


def test_a_homonym_of_an_archived_character_is_imported_beside_it(deps, tmp_path):
    archive_characters(deps, PRODUCT, NOW)
    wow = final_install(tmp_path)
    deps = replace(deps, wow_dir=wow)
    plan = plan_import(deps, sv_dir=wow / "WTF" / "Account" / "COMPTE" / "SavedVariables", logs_dir=None)
    assert not [s for s in plan["skipped"] if s["name"] == "Moi"]
    apply_import(deps, plan)
    doc = load_profile(deps.profile_path)
    assert doc["characters"]["Moi"]["product"] == FINAL
    assert doc["archived_characters"]["Moi-Royaume"]["class"]["value"] == "Mage"
    assert doc["active"] == "Moi"


def test_cli_archive_and_list(deps, capsys):
    assert main(["profile", "archive", "--product", PRODUCT, "--yes", "--json"], deps) == 0
    assert json.loads(capsys.readouterr().out)["archived"] == ["Moi-Royaume", "Prevu"]
    assert main(["profile", "list", "--archived", "--json"], deps) == 0
    assert json.loads(capsys.readouterr().out)["archived"] == ["Moi-Royaume", "Prevu"]


def test_cli_archive_without_agreement_writes_nothing(deps):
    before = deps.profile_path.read_bytes()
    assert main(["profile", "archive", "--product", PRODUCT], deps) == 2
    assert deps.profile_path.read_bytes() == before


def test_import_reads_every_account_of_the_installation(deps, tmp_path, capsys):
    wow = final_install(tmp_path, accounts=("A", "B"))
    (wow / "WTF" / "Account" / "A" / "SavedVariables" / "ForeverLogger.lua").unlink()
    deps = replace(deps, wow_dir=wow)
    archive_characters(deps, PRODUCT, NOW)
    assert main(["profile", "import", "--dry-run", "--json"], deps) == 0
    data = json.loads(capsys.readouterr().out)
    assert any(c["character"] == "Moi" for c in data["changes"])


# --- Mesures héritées de la bêta ---------------------------------------------------------------------------------------


def test_measures_inherited_from_the_previous_version(data_copy):
    """Version de fixture qui hérite toutes ses mesures de la précédente (comme une version finale décodée depuis la
    bêta) ; une mesure reprise d'un journal de la nouvelle version sort de la liste."""
    versions = sorted(d.name for d in data_copy.iterdir() if d.is_dir() and d.name[0].isdigit())
    previous = versions[versions.index(LOCAL_VERSION) - 1]
    monsters = json.loads((data_copy / previous / "monsters.json").read_text(encoding="utf-8"))
    monsters["inherited_from"] = previous
    path = data_copy / LOCAL_VERSION / "monsters.json"
    path.write_text(json.dumps(monsters, ensure_ascii=False), encoding="utf-8")
    write_manifest(data_copy)
    total = sum(len(npc["levels"]) for npc in monsters["npcs"].values())
    found = inherited_measures(data_copy, LOCAL_VERSION)
    assert len(found) == total > 0
    assert {m["from"] for m in found} == {previous}
    npc_id, npc = next(iter(monsters["npcs"].items()))
    level = next(iter(npc["levels"]))
    npc["levels"][level] = {**npc["levels"][level], "source": "journal WoWCombatLog-110426_200000.txt (bloc avancé)"}
    path.write_text(json.dumps(monsters, ensure_ascii=False), encoding="utf-8")
    write_manifest(data_copy)
    after = inherited_measures(data_copy, LOCAL_VERSION)
    assert len(after) == total - 1
    assert not [m for m in after if (m["npc_id"], m["level"]) == (npc_id, level)]


def test_cli_measures_inherited(data_copy, make_deps, capsys):
    assert main(["measures", "inherited", "--json"], make_deps(data_dir=data_copy)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["version"] == LOCAL_VERSION and data["count"] == len(data["measures"])
    assert data["provenance"]["certainty"] == "certain"
