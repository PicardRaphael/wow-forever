"""Liens internes de `README.md` et `docs/DEVELOPMENT.md` : chaque cible relative existe et reste dans le dépôt.

Ce sont les deux portes d'entrée du projet : un lien cassé y envoie le lecteur nulle part. Les ancres (`#…`) ne
sont pas vérifiées, seulement le fichier visé."""

import re

import pytest
from conftest import REPO_ROOT

DOCS = ("README.md", "docs/DEVELOPMENT.md")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
EXTERNAL = ("http://", "https://", "mailto:", "#")


def internal_links(name):
    """Couples (cible écrite, chemin résolu) des liens relatifs du fichier, résolus depuis son propre dossier."""
    path = REPO_ROOT / name
    text = path.read_text(encoding="utf-8")
    links = []
    for target in LINK.findall(text):
        if target.startswith(EXTERNAL):
            continue
        links.append((target, (path.parent / target.split("#", 1)[0]).resolve()))
    return links


@pytest.mark.parametrize("name", DOCS)
def test_internal_links_exist(name):
    links = internal_links(name)
    assert links, f"{name} : aucun lien interne trouvé"
    missing = sorted({t for t, p in links if not p.exists()})
    assert missing == [], f"{name} : cibles absentes {missing}"


@pytest.mark.parametrize("name", DOCS)
def test_internal_links_stay_in_repo(name):
    outside = sorted({t for t, p in internal_links(name) if not p.is_relative_to(REPO_ROOT)})
    assert outside == [], f"{name} : cibles hors du dépôt {outside}"
