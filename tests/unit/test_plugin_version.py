"""Version du plugin (T06b, bloc F, décision D8) : `plugin.json` porte une version semver, relevée à chaque
changement de `plugin/` ; l'empreinte des fichiers (`fingerprint.json`) garde la version à jour ; le script
d'installation valide le plugin en mode strict."""

import importlib.util
import json
import re

from conftest import REPO_ROOT

PLUGIN = REPO_ROOT / "plugin"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def fingerprint_module():
    spec = importlib.util.spec_from_file_location("plugin_fingerprint", REPO_ROOT / "scripts" / "plugin_fingerprint.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_plugin_json_has_a_semver_version():
    version = read_json(PLUGIN / ".claude-plugin" / "plugin.json")["version"]
    assert SEMVER.match(version), version
    # 0.1.0 : T06 ; 0.2.0 puis 0.2.1 : T06b (0.2.0 installé en cours de tranche) ; 0.3.0 : décisions 116 et 117 ;
    # 0.4.0 : planification, personnages prévus, rapport sourcé du sous-agent de recherche (décisions 118 à 121) ;
    # 0.4.1 : corrections après le passage d'évaluation 0.4.0 ; 0.4.2 : question contraire au profil (décision 122) ;
    # 0.4.3 : proposition d'analyser la nouvelle version quand la fraîcheur est en retard (T08a, décision 134) ;
    # 0.5.0 : skills forever-pvp et forever-builds, routeur (PV1) ; 0.6.0 : skill forever-familiers (CH0) ;
    # 0.7.0 : noms tels que dans le client du joueur (game_locale), T08c ; 0.8.0 : Talents Forever (lien du build
    # calculé, builds populaires), FA1 ; 0.8.1 : cas d'évaluation comparé au code rendu par l'outil (relevés du
    # 2026-10-08, décision 210) ; 0.8.2 : serveur MCP et hooks lancés par `python -m forever` avec `--no-sync`,
    # jamais par forever.exe (verrou de uv sync, demande de l'utilisateur du 2026-10-09) ; 0.8.3 : prochain point au
    # niveau suivant quand tous les points sont placés, un cas d'évaluation par bouton du pont (sonde en jeu F) ;
    # 0.8.4 : cas des boutons Talents et Leveling régénérés (égalité avec le build retenu, build actuel gardé, décision 217).
    # 0.8.5 : cas des boutons régénérés (build actuel retenu par le départage final au Monte Carlo, décision 219).
    # 0.8.6 : cas des boutons régénérés (chemin depuis le build actuel, respec contre le chemin libre, décision 220).
    # 0.8.7 : tranches de classe dans l'ordre de la décision 232 (CM1, CH1, DE1, PA1, GU1, VO1, PR1, DR1).
    assert version == "0.8.7"


def test_fingerprint_is_up_to_date():
    mod = fingerprint_module()
    stored = read_json(PLUGIN / ".claude-plugin" / "fingerprint.json")
    version = read_json(PLUGIN / ".claude-plugin" / "plugin.json")["version"]
    assert stored["version"] == version
    assert stored["sha256"] == mod.compute(PLUGIN), (
        "plugin/ a changé : relever la version de plugin.json puis lancer uv run python scripts/plugin_fingerprint.py"
    )


def test_fingerprint_ignores_results_and_itself(tmp_path):
    mod = fingerprint_module()
    files = mod.files(PLUGIN)
    assert files
    assert not any(p.parts[:2] == ("evals", "results") for p in files)
    assert (PLUGIN / ".claude-plugin" / "fingerprint.json").relative_to(PLUGIN) not in files
    assert (PLUGIN / ".claude-plugin" / "plugin.json").relative_to(PLUGIN) in files


def test_fingerprint_changes_with_a_file_and_ignores_line_endings(tmp_path):
    mod = fingerprint_module()
    root = tmp_path / "plugin"
    (root / "skills").mkdir(parents=True)
    (root / "skills" / "a.md").write_bytes(b"un\ndeux\n")
    first = mod.compute(root)
    (root / "skills" / "a.md").write_bytes(b"un\r\ndeux\r\n")
    assert mod.compute(root) == first
    (root / "skills" / "a.md").write_bytes(b"un\ntrois\n")
    assert mod.compute(root) != first


def test_install_script_validates_strictly():
    text = (REPO_ROOT / "scripts" / "install_plugin.ps1").read_text(encoding="utf-8")
    assert "claude plugin validate --strict" in text


def test_fingerprint_order_does_not_depend_on_the_system():
    """CI T06b : sous Windows, trier des `Path` ignore la casse (format-reponse.md avant SKILL.md), pas sous Linux ;
    l'empreinte trie les chemins en texte POSIX, même ordre partout."""
    files = fingerprint_module().files(PLUGIN)
    assert [p.as_posix() for p in files] == sorted(p.as_posix() for p in files)
