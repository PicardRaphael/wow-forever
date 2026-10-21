"""Correctifs du serveur lus dans la liste publique des caches vérifiés de Raidbots (décision 290) : quand
l'utilisateur ne peut pas se connecter, `forever hotfixes --raidbots` télécharge en lecture seule le `DBCache.bin`
vérifié le plus récent du build installé, l'épingle (empreinte, adresse, date de création) dans le cache, et
`forever decode --hotfixes --dbcache raidbots` l'applique ; la provenance nomme Raidbots et la certitude des valeurs
corrigées est au plus `probable` (copie tierce du cache du jeu).

Réseau simulé (FakeHttp) ; liste fabriquée ici sur le modèle de la réponse réelle du 2026-10-21 ; le `DBCache.bin`
est la fixture de `tests/fixtures/hotfix/` (build 70170)."""

import json

import pytest
from conftest import FIXTURES, FakeHttp, read_json

from forever.cli import main
from forever.errors import ForeverError
from forever.pipeline import raidbots

DBCACHE = (FIXTURES / "hotfix" / "DBCache.bin").read_bytes()
BUILD = 70170
URL = "https://storage.googleapis.com/raidbots-static/wow%2F70170%2FenUS%2FDBCache-new.bin"
OLD = "https://storage.googleapis.com/raidbots-static/wow%2F70170%2FenUS%2FDBCache-old.bin"


def listing(*entries):
    return json.dumps({"data": list(entries)}).encode()


def entry(url, build=BUILD, version="classic_beta", created="2026-10-21T06:25:13.118Z", verified=True):
    return {"version": version, "build": build, "verified": verified, "url": url, "entries": 118516,
            "pushIds": 4930, "created": created}  # fmt: skip


LISTING = listing(
    entry("https://x/retail.bin", build=70448, version="retail"),
    entry(OLD, created="2026-10-20T01:40:58.347Z"),
    entry(URL),
    entry("https://x/unverified.bin", created="2026-10-21T09:00:00Z", verified=False),
    entry("https://x/other-build.bin", build=70449, created="2026-10-21T10:00:00Z"),
)


def http(listing_body=LISTING):
    return FakeHttp(routes={raidbots.VERIFIED_URL: listing_body, URL: DBCACHE, OLD: b"ancien"})


def test_latest_verified_cache_of_the_build_and_product():
    chosen = raidbots.latest_verified(json.loads(LISTING), "wow_classic_beta", BUILD)
    assert chosen["url"] == URL  # vérifié, même build, même produit, le plus récent
    with pytest.raises(ForeverError):
        raidbots.latest_verified(json.loads(LISTING), "wow_classic_beta", 70000)  # aucun cache de ce build


def test_fetch_pins_the_file_with_its_source(make_deps):
    deps = make_deps(http=http())
    path = raidbots.fetch_dbcache(deps, BUILD, "wow_classic_beta")
    assert path.read_bytes() == DBCACHE and path.is_relative_to(deps.cache_dir)
    meta = raidbots.third_party_of(path)
    assert meta["source"] == "raidbots" and meta["url"] == URL and meta["created"] == "2026-10-21T06:25:13.118Z"
    assert len(meta["sha256"]) == 64 and meta["fetched_at"]
    calls = len(deps.http_get.calls)
    assert raidbots.fetch_dbcache(deps, BUILD, "wow_classic_beta") == path  # même cache : seule la liste est relue
    assert len(deps.http_get.calls) == calls + 1
    assert raidbots.cached_dbcache(deps.cache_dir, BUILD) == path  # dernier fichier épinglé, sans réseau


def test_offline_or_network_error_is_said(make_deps):
    with pytest.raises(ForeverError):
        raidbots.fetch_dbcache(make_deps(), BUILD, "wow_classic_beta")  # réseau en échec par défaut
    assert raidbots.cached_dbcache(make_deps().cache_dir, BUILD) is None


def test_hotfix_source_names_raidbots_and_caps_certainty(make_deps):
    from test_hotfix_overlay import source

    deps = make_deps(http=http())
    path = raidbots.fetch_dbcache(deps, BUILD, "wow_classic_beta")
    src = source(path=path)
    assert src.third_party["url"] == URL
    from forever.pipeline.hotfix_overlay import origin_rules_certainty

    assert origin_rules_certainty(src) == "probable"
    assert origin_rules_certainty(source()) == "certain"  # DBCache.bin du client de l'utilisateur


def test_cli_hotfixes_raidbots(make_deps, capsys):
    deps = make_deps(http=http())
    assert main(["hotfixes", "--raidbots", "--build", str(BUILD), "--json"], deps) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["raidbots"]["url"] == URL and out["raidbots"]["path"].endswith(".bin")


def test_raidbots_is_a_declared_network_command():
    text = (FIXTURES.parent.parent / "CLAUDE.md").read_text(encoding="utf-8")
    assert "forever hotfixes --raidbots" in text  # décision 290 : accès réseau déclaré
    assert read_json(FIXTURES / "hotfix" / "hotfixes-70170.json")  # fixture toujours là
