"""Documentation du lancement (LN1, bloc G, décision 271) : `docs/LANCEMENT.md` donne le pas-à-pas du 4 novembre pour
chaque PC, dans l'ordre, avec les cas du jeu qui change de dossier, de l'antivirus et de la remise à zéro du PC ;
`docs/USAGE.md` décrit les nouvelles commandes et variables. Aucun produit ni numéro d'interface de la version finale
n'y est deviné (`test_no_final_product_name.py` couvre le code)."""

from conftest import REPO_ROOT

LANCEMENT = REPO_ROOT / "docs" / "LANCEMENT.md"
USAGE = REPO_ROOT / "docs" / "USAGE.md"
STEPS = [
    "forever backup",
    "forever wow list",
    "forever wow adopt",
    "install_plugin.ps1",
    "install_addon.py",
    "forever bridge install",
    "select(4, GetBuildInfo())",
    "forever bridge autostart install",
    "install_update_task.ps1",
    "forever doctor",
    "forever update",
    "forever profile archive",
    "forever profile import",
    "forever measures refresh",
]


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start : end if end != -1 else len(text)]


def test_one_section_per_pc_with_every_step_in_order():
    text = LANCEMENT.read_text(encoding="utf-8")
    for heading in ("## PC de jeu", "## Portable"):
        body = section(text, heading)
        positions = [body.find(step) for step in STEPS]
        assert all(p >= 0 for p in positions), (heading, [s for s, p in zip(STEPS, positions, strict=True) if p < 0])
        assert positions == sorted(positions), heading


def test_special_cases():
    text = LANCEMENT.read_text(encoding="utf-8")
    for heading in ("## Le jeu change de dossier", "## Antivirus", "## Remise à zéro du PC", "## Tests en jeu"):
        assert heading in text, heading
    assert "FOREVER_WOW_ROOTS" in section(text, "## Le jeu change de dossier")
    assert "FOREVER_WOW_FORCE" in text
    reset = section(text, "## Remise à zéro du PC")
    order = [
        "uv",
        "uv sync",
        "gh auth login",
        "/login",
        "install_plugin.ps1",
        "forever backup restore",
        "forever doctor",
    ]
    positions = [reset.find(step) for step in order]
    assert all(p >= 0 for p in positions) and positions == sorted(positions), positions


def test_usage_describes_the_new_commands_and_variables():
    text = USAGE.read_text(encoding="utf-8")
    for needle in (
        "forever doctor",
        "forever backup",
        "forever wow list",
        "forever wow adopt",
        "forever profile archive",
        "forever measures inherited",
        "FOREVER_WOW_FORCE",
        "FOREVER_WOW_ROOTS",
        "FOREVER_BACKUP_DIR",
        "FOREVER_CACHE_DIR",
        "autostart_wow_changed",
        "autostart_env_error",
        "autostart_skip",
        "docs/LANCEMENT.md",
    ):
        assert needle in text, needle
