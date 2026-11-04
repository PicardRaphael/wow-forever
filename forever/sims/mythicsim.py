"""Adaptateur mince de MythicSim au niveau 60 (MS1, décision 301), second simulateur à côté de wowsims/forever : aucun
calcul de jeu ici. Le binaire épinglé par `forever sims update` (`forever-engine`, empreinte vérifiée) reçoit le même
`RaidSimRequest` que wowsims (`sim --request … --outfile … --gate`, règles de Forever), en local, sans réseau.

- Rotation, options de la spé et buffs viennent du fork Go épinglé par MythicSim lui-même (`ui/specs/<classe>/<spé>/`,
  lu comme le dépôt de wowsims) : son proto refuse les rotations du wowsims actuel. Équipement, talents (convertis par
  `forever.sims.talents`), race et rencontre sont ceux du cas.
- Un refus du moteur (code 5 de la préparation, code 3 de la porte) est rendu tel quel, avec son code et sa raison
  (`mythicsim_refused`) ; jamais remplacé par wowsims.
- `identity.client_build` du résultat est la version du contrat du moteur, jamais présentée comme la version simulée.
Certitude `suppose` (simulateur tiers) ; provenance : commit, empreinte du binaire, révision du fork Go."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from forever.errors import ForeverError
from forever.pipeline import gitops
from forever.pipeline.mythicsim_build import mythicsim_dir, pinned
from forever.sims import wowsims
from forever.sims.wowsims import Preset

TIMEOUT_S = 600.0
EXIT_REFUSED, EXIT_REJECTED, EXIT_NOT_PREPARED = 3, 4, 5  # codes de sortie de `forever-engine sim` (src/main.rs)
BLANK = "Blank"  # rotation vide des préréglages du fork, jamais choisie
request_for = wowsims.request_for  # même RaidSimRequest


class MythicsimError(ForeverError):
    """MythicSim non compilé, binaire changé, combat en échec ou refus du moteur (`mythicsim_refused`)."""

    def __init__(self, message: str, action: str = "lancer `uv run forever sims update`", *,
                 code: str = "mythicsim_failed") -> None:  # fmt: skip
        super().__init__(code, message, action)


def _binary(cache_dir: Path) -> tuple[Path, dict[str, Any]]:
    pin = pinned(cache_dir)
    if pin is None:
        raise MythicsimError("MythicSim n'est pas encore compilé : lancer `uv run forever sims update`.")
    binary = mythicsim_dir(cache_dir) / str(pin["binary"])
    if not binary.is_file():
        raise MythicsimError(f"binaire épinglé de MythicSim introuvable : {binary}.")
    if hashlib.sha256(binary.read_bytes()).hexdigest() != pin["sha256"]:
        raise MythicsimError(
            f"empreinte du binaire de MythicSim différente de l'épinglage ({binary.name}) : il a changé."
        )
    return binary, pin


def source_note(pin: Mapping[str, Any]) -> str:
    """Hypothèse de provenance d'un résultat de MythicSim."""
    return (f"calcul de MythicSim (moteur Rust), commit {str(pin['commit'])[:12]} du {pin.get('committed_at')}, binaire "
            f"compilé tel quel (empreinte {str(pin['sha256'])[:12]}), règles de Forever, niveau 60 ; rotation, options "
            f"et buffs de son fork Go épinglé ({str(pin.get('go_revision'))[:12]}) ; la version du client de son "
            "contrat n'est pas la version simulée ; simulateur tiers, certitude suppose")  # fmt: skip


def _rotations(go: Path, rel: str) -> dict[str, Path]:
    spec = go / "ui" / "specs" / rel
    path = spec / "presets.ts"
    if not path.is_file():
        return {}
    text = wowsims._strip_comments(path.read_text(encoding="utf-8"))
    files = {name: spec / file for name, file in wowsims._IMPORT.findall(text)}
    out: dict[str, Path] = {}
    for _, label, src in wowsims._APL.findall(text):
        if label != BLANK and src in files and files[src].is_file():
            out[label] = files[src]
    return out


def _lead_tree(talents: str, tree_names: Sequence[str]) -> str | None:
    points = [sum(int(c) for c in seg if c.isdigit()) for seg in talents.split("-")]
    if not points or max(points) == 0 or len(tree_names) < len(points):
        return None
    return tree_names[points.index(max(points))]


def preset_for(
    cache_dir: Path,
    case: Preset,
    *,
    talents: str,
    tree_names: Sequence[str] | None,
    rotation: str | None = None,
) -> Preset:
    """Préréglage de MythicSim pour un cas : options, buffs et rotation du fork Go de la même spé ; équipement du cas ;
    `talents` : chaîne de MythicSim. Rotation : `rotation` (nom du fork), sinon la seule de la spé, sinon celle qui
    porte le nom de l'arbre le plus pris (`tree_names`, noms du client)."""
    go = mythicsim_dir(cache_dir) / "go"
    rel = case.key.rsplit("/", 1)[0]
    base = next((p for p in wowsims.read_presets(go) if p.key.startswith(rel + "/")), None)
    rotations = _rotations(go, rel)
    if base is None or not rotations:
        raise MythicsimError(f"spé {rel} absente du fork Go épinglé de MythicSim.", "choisir engine=wowsims")
    label = rotation
    if label is None:
        label = next(iter(rotations)) if len(rotations) == 1 else _lead_tree(talents, tree_names or [])
    if label not in rotations:
        raise MythicsimError(
            f"rotation « {label} » absente du fork de MythicSim pour {rel} (rotations : {', '.join(rotations)}).",
            "donner rotation=<nom>",
        )
    apl = json.loads(rotations[label].read_text(encoding="utf-8"))
    return dataclasses.replace(base, key=case.key, talents=talents, equipment=case.equipment, rotation=apl,
                               race=None, encounter=None, distance=case.distance)  # fmt: skip


def _refusal(out: Any) -> str:
    try:
        doc = json.loads(out.stdout or "{}")
    except ValueError:
        return (out.stdout or out.stderr or "sans message").strip()[-500:]
    refusal = doc.get("refusal")
    if isinstance(refusal, dict):
        return f"code {refusal.get('code')} : {refusal.get('reason')}"
    reasons = doc.get("reasons") or [r.get("reason") for r in doc.get("refusals") or [] if isinstance(r, dict)]
    return "porte : " + "; ".join(str(r) for r in reasons)


def run_sim(cache_dir: Path, request: dict[str, Any], *, runner: gitops.Runner | None = None) -> dict[str, Any]:
    """Un combat simulé par le binaire épinglé : dégâts par seconde (moyenne, écart type), combats faits, source."""
    binary, pin = _binary(cache_dir)
    runs = mythicsim_dir(cache_dir) / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    name = uuid.uuid4().hex[:12]
    infile, outfile = runs / f"{name}.in.json", runs / f"{name}.out.json"
    infile.write_text(json.dumps(request), encoding="utf-8")
    try:
        out = gitops._run(
            runner or gitops.subprocess_runner,
            [str(binary), "sim", "--request", str(infile), "--outfile", str(outfile), "--gate"],
            runs,
            timeout=TIMEOUT_S,
            check=False,
        )
        if out.returncode in (EXIT_NOT_PREPARED, EXIT_REFUSED):
            raise MythicsimError(f"MythicSim refuse le cas ({_refusal(out)}).",
                                 "lire la raison du moteur ; autre build, équipement ou engine=wowsims",
                                 code="mythicsim_refused")  # fmt: skip
        if out.returncode != 0:
            detail = (out.stderr or out.stdout or "sans message").strip().splitlines()
            raise MythicsimError(f"combat simulé par MythicSim en échec ({out.returncode}) : "
                                 f"{detail[-1] if detail else 'sans message'}",
                                 "vérifier la requête ; relancer `forever sims update`")  # fmt: skip
        doc = json.loads(outfile.read_text(encoding="utf-8"))
    except (gitops.GitOpsError, OSError, ValueError) as exc:
        raise MythicsimError(f"combat simulé par MythicSim en échec : {exc}",
                             "vérifier la requête ; relancer `forever sims update`") from exc  # fmt: skip
    finally:
        infile.unlink(missing_ok=True)
        outfile.unlink(missing_ok=True)
    result = doc.get("result") or {}
    identity = doc.get("identity") or {}
    dps = result["raidMetrics"]["parties"][0]["players"][0]["dps"]
    return {
        "dps": float(dps.get("avg", 0.0)),
        "stdev": float(dps.get("stdev", 0.0)),
        "iterations": int(result.get("iterationsDone", 0)),
        "source": {
            "simulator": "MythicSim",
            "commit": pin["commit"],
            "committed_at": pin.get("committed_at"),
            "sha256": pin["sha256"],
            "go_reference_revision": identity.get("go_reference_revision"),
            "contract_client_build": identity.get("client_build"),
            "certainty": "suppose",
        },
    }


VEILLE_NAME = "veille.json"


def replay_reference(
    cache_dir: Path,
    cases: Sequence[tuple[Preset, str]],
    convert: Callable[[Preset], tuple[str, Sequence[str]]],
    encounter: dict[str, Any] | None,
    *,
    iterations: int = wowsims.DEFAULT_ITERATIONS,
    seed: int = wowsims.DEFAULT_SEED,
    runner: gitops.Runner | None = None,
) -> dict[str, Any]:
    """Cas de référence de la veille rejoués par MythicSim (préréglages de wowsims et race de chacun, même graine) :
    `convert` rend la chaîne de MythicSim et les noms des arbres ; un cas non convertible ou refusé est mis de côté.
    Écarts au passage précédent au-delà de `wowsims.GAP_THRESHOLD`, écrits dans `veille.json`."""
    root = mythicsim_dir(cache_dir)
    pin = pinned(cache_dir) or {}
    path = root / VEILLE_NAME
    previous = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    done: dict[str, float] = {}
    skipped: list[str] = []
    for preset, race in cases:
        try:
            code, trees = convert(preset)
            ms = preset_for(cache_dir, preset, talents=code, tree_names=trees)
            out = run_sim(cache_dir, request_for(ms, race=race, encounter=encounter, iterations=iterations,
                                                 seed=seed), runner=runner)  # fmt: skip
        except ForeverError:
            skipped.append(preset.key)
            continue
        done[preset.key] = out["dps"]
    old = previous.get("cases") or {}
    gaps = [
        {"case": k, "before": old[k], "after": v, "relative": (v - old[k]) / old[k]}
        for k, v in sorted(done.items())
        if k in old and old[k] and abs(v - old[k]) / old[k] > wowsims.GAP_THRESHOLD
    ]
    report = {"commit": pin.get("commit"), "previous_commit": previous.get("commit"), "cases": done, "gaps": gaps,
              "skipped": skipped, "threshold": wowsims.GAP_THRESHOLD, "seed": seed}  # fmt: skip
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report
