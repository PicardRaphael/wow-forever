"""Outils de test communs : dépendances injectées, faux client HTTP, copie des données."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from forever.config import Deps

LOCAL_HOSTS = ["127.0.0.1"]  # boucle asyncio de Windows : paire de sockets locale (tests MCP)


_MCP_IMPORT = re.compile(r"^\s*(from mcp[ .]|import mcp\b)", re.MULTILINE)
_MCP_MODULES: dict[str, bool] = {}


def _uses_mcp(module: Any) -> bool:
    """Le module de test importe le SDK `mcp` (en tête de fichier ou dans un test), client ou serveur MCP."""
    path = getattr(module, "__file__", None)
    if not isinstance(path, str):
        return False
    if path not in _MCP_MODULES:
        _MCP_MODULES[path] = bool(_MCP_IMPORT.search(Path(path).read_text(encoding="utf-8")))
    return _MCP_MODULES[path]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """T06b : tout test d'un module qui importe `mcp` reçoit `allow_hosts(LOCAL_HOSTS)` (socket local seulement) ;
    plus de marqueur à écrire test par test."""
    for item in items:
        module = getattr(item, "module", None)
        if module is not None and _uses_mcp(module):
            item.add_marker(pytest.mark.allow_hosts(LOCAL_HOSTS))


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
DATA_DIR = REPO_ROOT / "forever" / "data"
REGISTRY_PATH = REPO_ROOT / "docs" / "MECHANICS_REGISTRY.yaml"
SEED_DATA = REPO_ROOT / "seed" / "forever-mage" / "data"
# Version des données du seed (lecture seule, figée à la version portée en T02) : le seed ne suit pas les
# versions du jeu, la parité se joue toujours sur la sienne.
SEED_VERSION = max(d.name for d in SEED_DATA.iterdir() if d.is_dir() and d.name[0].isdigit())

# Version installée du dépôt (dossier forever/data/<version>/ le plus récent). Passée à 1.60.1.70124 en T08a :
# les 22 tables du client sont identiques à celles de 1.60.1.70009, aucune valeur de jeu ne change.
LOCAL_VERSION = "1.60.1.70124"
# Version précédente, gardée dans le dépôt : sert aux comparaisons entre versions installées.
PREVIOUS_VERSION = "1.60.1.70009"
PRODUCT = "wow_classic_beta"
PREFIX = "1.60."
NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


class FakeHttp:
    """Client HTTP simulé : renvoie `body` ou lève `exc`, et garde la trace des appels.

    `routes` (URL -> corps ou exception) prend le pas sur `body` pour les URL qu'il contient."""

    def __init__(
        self,
        body: bytes | None = None,
        exc: Exception | None = None,
        routes: Mapping[str, bytes | Exception] | None = None,
    ) -> None:
        self.body = body
        self.exc = exc
        self.routes = dict(routes or {})
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def __call__(self, url: str, headers: Mapping[str, str], timeout: float) -> bytes:
        self.calls.append((url, dict(headers), timeout))
        if url in self.routes:
            answer = self.routes[url]
            if isinstance(answer, Exception):
                raise answer
            return answer
        if self.exc is not None:
            raise self.exc
        assert self.body is not None, f"URL non simulée : {url}"
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
        wow_dir: Path | None = None,
    ) -> Deps:
        return Deps(
            data_dir=data_dir,
            registry_path=registry_path,
            cache_dir=cache_dir or tmp_path / "cache",
            http_get=http or FakeHttp.failing(),
            now=lambda: now,
            offline=offline,
            wow_dir=wow_dir,
            profile_path=tmp_path / "profil" / "profile.json",  # jamais ~/.forever dans les tests (T06b)
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


@pytest.fixture(scope="session")
def seed_game_data() -> Any:
    """Données typées du mode seed (copies figées `_seed_talents.json` et `_seed_spells.json`, T06b), pour la parité."""
    from forever.gamedata import build_game_data
    from forever.store import load_version

    return build_game_data(load_version(isolated_deps(REPO_ROOT / ".cache-tests-inutilise")), rules="seed")


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


# --- Pipeline de données (T03) -------------------------------------------------------------------

# Extraits des tables du client (voir son README.md) : relevés sur 1.60.1.70009, identiques en 1.60.1.70124.
WAGO_70009 = FIXTURES / "wago" / PREVIOUS_VERSION


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def isolated_deps(tmp: Path, data_dir: Path = DATA_DIR) -> Deps:
    """Deps isolées pour les fixtures de session : cache dans `tmp`, réseau en échec, horloge fixe."""
    return Deps(
        data_dir=data_dir,
        registry_path=REGISTRY_PATH,
        cache_dir=tmp / "cache",
        http_get=FakeHttp.failing(),
        now=lambda: NOW,
        profile_path=tmp / "profil" / "profile.json",
    )


@pytest.fixture(scope="session")
def decode_rules() -> Any:
    return read_json(DATA_DIR / LOCAL_VERSION / "decode_rules.json")


@pytest.fixture(scope="session")
def client_tables(decode_rules: Any) -> Any:
    """Tables typées des fixtures wago 1.60.1.70009."""
    from forever.pipeline.decode import load_tables

    return load_tables(WAGO_70009, decode_rules)


@pytest.fixture(scope="session")
def candidate(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """Version candidate décodée des fixtures, à **leur** version (1.60.1.70009 : ce sont des extraits de ce
    client), dossier temporaire partagé par la session. Les tests de la révision (T06b) l'installent dans un dépôt
    ramené à cette version ; ceux de la nouvelle version (T08a) la relabellisent."""
    from forever.pipeline.decode import decode_version

    tmp = tmp_path_factory.mktemp("candidate")
    return decode_version(isolated_deps(tmp), PREVIOUS_VERSION, csv_dir=WAGO_70009, out=tmp / "candidate")


def change_key(c: Mapping[str, Any]) -> tuple[str, str, str, str, str, str]:
    """Identité d'un changement de `forever diff`, comparable entre le diff et confirmed_changes.json."""
    return (
        c["kind"],
        c["key"],
        c["change"],
        str(c["field"]),
        json.dumps(c["old"], sort_keys=True),
        json.dumps(c["new"], sort_keys=True),
    )


def format_changes(changes: list[Mapping[str, Any]]) -> str:
    """Table lisible (une ligne par écart) pour les messages d'échec."""
    return "\n".join(
        f"  {c['kind']:<6} {c['key']:<22} {c['change']:<8} {c['field']!s:<18} "
        f"référence={json.dumps(c['old'], ensure_ascii=False)} client={json.dumps(c['new'], ensure_ascii=False)}"
        for c in changes
    )


COMBATLOG = FIXTURES / "combatlog"  # journaux de combat (voir son README.md)
REAL_LOG = COMBATLOG / "WoWCombatLog-092726_145346.anon.txt"
SYNTHETIC_LOGS = COMBATLOG / "synthetic"
MINE_GUID = "Player-0000-00000000"  # joueur « à moi » de la fixture anonymisée (Mage)


def seed_view(root: Path) -> Any:
    """Référence d'origine (copies figées du seed `_seed_talents.json`, `_seed_spells.json`) vue comme une version,
    pour comparer le décodage du client à la référence de T03 une fois le dépôt en révision 2 (T06b)."""
    from forever.store import VersionData

    view = root / "seed-view" / PREVIOUS_VERSION
    view.mkdir(parents=True, exist_ok=True)
    for name in ("talents", "spells"):
        shutil.copyfile(DATA_DIR / LOCAL_VERSION / f"_seed_{name}.json", view / f"{name}.json")
    return VersionData(PREVIOUS_VERSION, "0" * 12, view, {})


def client_vs_reference(candidate: Any, kind: str) -> tuple[list[Any], list[Any], list[Any]]:
    """(écarts, observations, changements confirmés) entre la référence d'origine (copies du seed) et la candidate,
    pour `kind`.

    Observation : valeur relevée dans le client là où la référence a null (décision 2 du plan T03) ; installées en
    révision 2, elles figurent aussi dans confirmed_changes.json (`old` null), exclues ici des changements confirmés."""
    from forever.pipeline.diff import compare_data
    from forever.store import load_version

    client = load_version(isolated_deps(candidate.root.parent, candidate.root))
    changes = [c for c in compare_data(seed_view(candidate.root.parent), client) if c["kind"] == kind]
    observations = [c for c in changes if c["change"] == "modified" and c["old"] is None]
    gaps = [c for c in changes if c not in observations]
    confirmed = [
        c
        for c in read_json(DATA_DIR / LOCAL_VERSION / "confirmed_changes.json")["changes"]
        if c["kind"] == kind and c["old"] is not None
    ]
    return gaps, observations, confirmed
