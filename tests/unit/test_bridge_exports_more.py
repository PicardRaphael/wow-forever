"""Bouton « Exports » (EX1, suite) : liens `[Naowh : macros]` et `[EllesmereUI : <rôle>]` après le build actuel ;
sans rôle choisi ou sans profil de base, une ligne dit ce qui manque.

Valeurs : contexte réel `tests/fixtures/bridge/contexts/mage19.txt` (niveau, classe, royaume), sauvegarde synthétique
`tests/fixtures/exports/ellesmere_base.lua` copiée dans `tmp_path`."""

import shutil

import pytest
from conftest import FIXTURES

from forever.bridge.exports import exports_reply
from forever.exports.ellesmere import PREFIX, ROLE_LABELS, read_ellesmere
from forever.exports.naowh import MACRO_PREFIX, read_naowh_macros

CONTEXT = dict(
    line.split("=", 1)
    for line in (FIXTURES / "bridge" / "contexts" / "mage19.txt").read_text(encoding="utf-8").split("\n")
    if "=" in line
)


@pytest.fixture
def wow(tmp_path):
    root = tmp_path / "wow"
    sv = root / "WTF" / "Account" / "COMPTE" / "SavedVariables"
    sv.mkdir(parents=True)
    shutil.copy(FIXTURES / "exports" / "ellesmere_base.lua", sv / "EllesmereUI.lua")
    return root


def by_kind(links, kind):
    return [link for link in links if link["kind"] == kind]


def test_macros_and_ellesmere_links_follow_the_current_build(wow, make_deps):
    text, links = exports_reply(make_deps(wow_dir=wow), {**CONTEXT, "role": "dps"}, [])
    assert links[0]["kind"] == "naowh_build"
    (macros,) = by_kind(links, "naowh_macros")
    assert macros["text"].startswith(MACRO_PREFIX) and read_naowh_macros(macros["text"])
    (eui,) = by_kind(links, "ellesmere")
    assert eui["text"].startswith(PREFIX) and read_ellesmere(eui["text"])["client"] == "forever"
    assert eui["label"] == f"EllesmereUI : {ROLE_LABELS['dps']}"
    assert f"{CONTEXT['name']} - {ROLE_LABELS['dps']}" in text


def test_without_role_the_reply_says_so(wow, make_deps):
    text, links = exports_reply(make_deps(wow_dir=wow), CONTEXT, [])
    assert by_kind(links, "naowh_macros") and not by_kind(links, "ellesmere")
    assert "/fb role" in text


def test_without_base_profile_the_reply_says_so(make_deps, tmp_path):
    text, links = exports_reply(make_deps(wow_dir=tmp_path / "vide"), {**CONTEXT, "role": "dps"}, [])
    assert not by_kind(links, "ellesmere") and "profil de base" in text
