"""Outils de test communs : dépendances injectées, faux client HTTP, copie des données."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from forever.config import Deps

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
DATA_DIR = REPO_ROOT / "forever" / "data"
REGISTRY_PATH = REPO_ROOT / "docs" / "MECHANICS_REGISTRY.yaml"
SEED_DATA = REPO_ROOT / "seed" / "forever-mage" / "data"

# Version des données du dépôt (dossier forever/data/1.60.1.70009/, copié du seed).
LOCAL_VERSION = "1.60.1.70009"
PRODUCT = "wow_classic_beta"
PREFIX = "1.60."
NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


class FakeHttp:
    """Client HTTP simulé : renvoie `body` ou lève `exc`, et garde la trace des appels."""

    def __init__(self, body: bytes | None = None, exc: Exception | None = None) -> None:
        self.body = body
        self.exc = exc
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def __call__(self, url: str, headers: Mapping[str, str], timeout: float) -> bytes:
        self.calls.append((url, dict(headers), timeout))
        if self.exc is not None:
            raise self.exc
        assert self.body is not None
        return self.body

    @classmethod
    def fixture(cls, name: str) -> FakeHttp:
        return cls(body=(FIXTURES / "wago" / name).read_bytes())

    @classmethod
    def failing(cls) -> FakeHttp:
        return cls(exc=OSError("réseau simulé indisponible"))


MakeDeps = Callable[..., Deps]


@pytest.fixture
def make_deps(tmp_path: Path) -> MakeDeps:
    """Fabrique de Deps isolées : cache dans tmp_path, réseau simulé (en échec par défaut), horloge fixe."""

    def factory(
        *,
        http: FakeHttp | None = None,
        now: datetime = NOW,
        data_dir: Path = DATA_DIR,
        registry_path: Path = REGISTRY_PATH,
        cache_dir: Path | None = None,
        offline: bool = False,
    ) -> Deps:
        return Deps(
            data_dir=data_dir,
            registry_path=registry_path,
            cache_dir=cache_dir or tmp_path / "cache",
            http_get=http or FakeHttp.failing(),
            now=lambda: now,
            offline=offline,
        )

    return factory


@pytest.fixture(scope="session")
def game_data() -> Any:
    """Données typées du moteur pour la version du dépôt (après contrôle d'intégrité)."""
    from forever.gamedata import load_game_data

    deps = Deps(
        data_dir=DATA_DIR,
        registry_path=REGISTRY_PATH,
        cache_dir=REPO_ROOT / ".cache-tests-inutilise",
        http_get=FakeHttp.failing(),
        now=lambda: NOW,
    )
    return load_game_data(deps)


@pytest.fixture
def data_copy(tmp_path: Path) -> Path:
    """Copie modifiable de forever/data (manifeste compris)."""
    dst = tmp_path / "data"
    shutil.copytree(DATA_DIR, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def tamper(path: Path) -> None:
    """Change le premier chiffre d'un fichier : même taille, JSON toujours valide, empreinte différente."""
    raw = bytearray(path.read_bytes())
    i = next(i for i, b in enumerate(raw) if chr(b).isdigit())
    raw[i] = ord("7") if raw[i] != ord("7") else ord("8")
    path.write_bytes(bytes(raw))


def _mutated(mutate: Callable[[dict[str, Any]], object]) -> Callable[[bytes], bytes]:
    def apply(raw: bytes) -> bytes:
        manifest = json.loads(raw)
        mutate(manifest)
        return json.dumps(manifest).encode("utf-8")

    return apply


# Manifestes présents mais corrompus : illisibles, mal formés ou incohérents.
MANIFEST_CORRUPTIONS: dict[str, Callable[[bytes], bytes]] = {
    "tronque": lambda raw: raw[: len(raw) // 2],
    "vide": lambda raw: b"",
    "non-utf8": lambda raw: b"\xff\xfe" + raw,
    "pas-un-objet": lambda raw: b"[]\n",
    "versions-liste": _mutated(lambda m: m.update(versions=[])),
    "entree-texte": _mutated(lambda m: m["versions"].update({LOCAL_VERSION: "x"})),
    "files-liste": _mutated(lambda m: m["versions"][LOCAL_VERSION].update(files=["spells.json"])),
    "version-invalide": _mutated(lambda m: m["versions"].update(latest=m["versions"][LOCAL_VERSION])),
    "empreinte-non-texte": _mutated(lambda m: m["versions"][LOCAL_VERSION]["files"].update({"spells.json": 42})),
    "data-sha-incoherent": _mutated(lambda m: m["versions"][LOCAL_VERSION].update(data_sha="0" * 12)),
    "game-version-absente": _mutated(lambda m: m.update(game_version="1.60.1.99999")),
}


def corrupt_manifest(data_dir: Path, kind: str = "tronque") -> None:
    path = data_dir / "manifest.json"
    path.write_bytes(MANIFEST_CORRUPTIONS[kind](path.read_bytes()))
