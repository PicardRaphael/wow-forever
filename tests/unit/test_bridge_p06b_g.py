"""Suites de l'essai en jeu du panneau « À valider » et du bouton « Mettre à jour » (décision 240), côté pont :

- une seule carte pour plusieurs attentes de la même branche (écriture bloquée `data/<version>-r<N>`) ou de la même
  cause ; deux attentes approuvables ne sont jamais fusionnées (chacune garde sa décision) ;
- textes des cartes et des réponses aux actions en mots de joueur (ni commande, ni branche, ni CI, ni passage) ; le
  détail technique reste dans `detail`, que « Expliquer » transmet ;
- avancement d'une mise à jour : étape en mots simples, heure de début (secondes depuis l'époque, lue par l'addon), et
  phrase de fin rédigée par le pont (« Mise à jour terminée en 4 min : rien de nouveau ») ;
- chaque carte publiée porte une empreinte (`stamp`) et un bouton « Masquer » ; l'empreinte change quand l'attente
  change (la carte masquée revient alors).

Attentes synthétiques, aucun chiffre du jeu."""

import json
import os
import re
from datetime import UTC, datetime

import pytest

from forever.bridge.actions import ActionHandler
from forever.bridge.cards import CardSource, card_lines, update_cards
from forever.bridge.status import pass_outcome, status_line, status_payload, update_stage
from forever.update import record_pending, update_dir

VERSION = "1.60.1.70338"
NOW = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)
CI_URL = "https://github.com/PicardRaphael/wow-forever/actions/runs/38117641238"
# termes internes interdits dans un texte montré au joueur (en plus de `jargon.internal_jargon`)
DENIED = re.compile(
    r"forever update|--auto|`|FOREVER_|\bverify\b|\bCI\b|\bmain\b|\bbranche\b|\bclone\b|\bpassage\b"
    r"|session nécessaire|sortie gardée|\bdata/"
)
PC_FIX = "Une mise à jour attend une correction sur ton PC : ouvre une session Claude"


def blocked(ident, *, created="2026-10-10T16:30:00Z", by="ci", revision=2, url=CI_URL):
    return {
        "id": ident, "kind": "install_revision", "action": "bloqué", "blocked_by": by, "version": VERSION,
        "revision": revision, "state": "en_attente", "created_at": created,
        "reasons": [f"CI failure sur data/{VERSION}-r{revision} ({url}) : rien fusionné, branche gardée à distance"],
        "commands": ["session nécessaire : lire la sortie gardée, corriger sur main, puis `forever update`"],
    }  # fmt: skip


def waiting(ident, kind="measures", **extra):
    return {"id": ident, "kind": kind, "action": "attente", "version": VERSION, "revision": None,
            "state": "en_attente", "created_at": "2026-10-10T08:00:00Z", "reasons": ["raison"], "commands": [],
            **extra}  # fmt: skip


def jargon(text):
    from forever.bridge.jargon import internal_jargon

    return internal_jargon(text) + DENIED.findall(text)


# --- 2. une carte par branche ou par cause -------------------------------------------------------------------


def test_two_blocked_entries_of_the_same_branch_make_one_card():
    first = blocked(f"{VERSION}-r2-78a3d340380a", created="2026-10-10T16:30:00Z",
                    url="https://github.com/PicardRaphael/wow-forever/actions/runs/38066561567")  # fmt: skip
    second = blocked(f"measures-{VERSION}-0db779cfd25d", created="2026-10-11T06:30:00Z")
    cards = update_cards([first, second])
    assert len(cards) == 1
    (card,) = cards
    assert card["id"] == second["id"]  # la plus récente porte la carte
    assert card["count"] == "waiting"


def test_blocked_entries_of_two_branches_stay_apart():
    cards = update_cards([blocked("a", revision=2), blocked("b", revision=3)])
    assert [c["id"] for c in cards] == ["a", "b"]


def test_same_cause_makes_one_card_but_approvable_entries_never_merge():
    same = [waiting("x", kind="column_names", action="bloqué"), waiting("y", kind="column_names", action="bloqué")]
    assert len(update_cards(same)) == 1
    two = update_cards([waiting("m1"), waiting("m2")])
    assert [c["id"] for c in two] == ["m1", "m2"]
    assert all(c["count"] == "approvable" for c in two)


def put(cache_dir, doc):
    folder = update_dir(cache_dir) / "pending"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{doc['id']}.json").write_text(json.dumps(doc), encoding="utf-8")


def test_status_counts_one_wait_per_card(make_deps):
    deps = make_deps()
    put(deps.cache_dir, blocked(f"{VERSION}-r2-78a3d340380a", created="2026-10-10T16:30:00Z"))
    put(deps.cache_dir, blocked(f"measures-{VERSION}-0db779cfd25d", created="2026-10-11T06:30:00Z"))
    payload = status_payload(deps)
    assert (payload["approvable"], payload["waiting"]) == (0, 1)
    assert "1 en attente" in payload["line"]


# --- 3. mots de joueur -----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entry",
    [
        blocked("b-ci"),
        blocked("b-verify", by="verify"),
        blocked("b-sync", by="uv_sync"),
        waiting("net", kind="network"),
        waiting("hot", kind="hotfixes_unread", until="2026-10-11T05:07:29Z"),
        waiting("col", kind="column_names"),
        waiting("dbd", kind="network_dbd"),
        waiting("add", kind="addon_data", addon="GearQuestForever"),
        waiting("rev", kind="install_revision", revision=2, summary={"pvp": {"sentence": "fiches PvP : Warrior"}}),
        waiting("appr", state="approuvée"),
        {
            "id": "pass-error-x",
            "kind": "pass_error",
            "action": "bloqué",
            "state": "en_attente",
            "version": None,
            "reasons": ["passage arrêté au bout de 120 min, à l'étape journaux"],
            "commands": ["forever update status"],
        },
    ],
    ids=lambda e: str(e["id"]),
)
def test_card_texts_have_no_internal_jargon(entry):
    (card,) = update_cards([entry])
    shown = "\n".join([card["title"], *card["lines"]])
    assert jargon(shown) == [], shown


def test_blocked_card_tells_the_player_what_to_do():
    (card,) = update_cards([blocked("b-ci")])
    assert card["lines"][0] == "La validation sur GitHub a échoué : rien n'a été installé."
    assert card["lines"][-1] == PC_FIX
    assert CI_URL in card["detail"]  # détail technique gardé pour « Expliquer »


def test_pass_error_card_tells_the_player_what_to_do():
    entry = {"id": "pass-error-x", "kind": "pass_error", "action": "bloqué", "state": "en_attente", "version": None,
             "reasons": ["passage arrêté au bout de 120 min, à l'étape journaux"], "commands": ["forever update status"]}  # fmt: skip
    (card,) = update_cards([entry])
    assert card["title"] == "La dernière mise à jour s'est arrêtée"
    assert card["lines"][-1] == PC_FIX


def test_simple_lines_in_player_words():
    assert card_lines(waiting("net", kind="network")) == ["En attente du réseau : la mise à jour reprendra seule."]
    hot = card_lines(waiting("hot", kind="hotfixes_unread", until="2026-10-11T05:07:29Z"))
    assert hot == ["Correctifs du serveur à lire jusqu'au 11/10/2026."]
    (approved,) = update_cards([waiting("appr", state="approuvée")])
    assert approved["lines"][-1] == "Validée : sera installée à la prochaine mise à jour."


class FakeSpawn:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def __call__(self, argv, log):
        if self.fail:
            raise OSError("introuvable")
        self.calls.append(list(argv))


def handler(cache, **kwargs):
    spawn = kwargs.pop("spawn", FakeSpawn())
    return ActionHandler(cache_dir=cache, now=lambda: NOW, spawn=spawn, **kwargs), spawn


def lock(cache, **fields):
    path = update_dir(cache) / "lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"pid": os.getpid(), "started_at": "2026-10-11T08:57:00Z", **fields}
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_update_reply_in_player_words(tmp_path):
    actions, spawn = handler(tmp_path)
    result, text = actions.handle("update", None)
    assert result == "lancée" and text == "Mise à jour lancée."
    assert len(spawn.calls) == 1


def test_replies_have_no_internal_jargon(tmp_path):
    texts = []
    actions, _ = handler(tmp_path, offline=True)
    texts.append(actions.handle("update", None)[1])
    actions, _ = handler(tmp_path, spawn=FakeSpawn(fail=True))
    texts.append(actions.handle("update", None)[1])
    record_pending(tmp_path, waiting(f"measures-{VERSION}-a"))
    record_pending(tmp_path, blocked(f"{VERSION}-r2-b"))
    actions, _ = handler(tmp_path)
    texts += [
        actions.handle("approve", f"measures-{VERSION}-a")[1],
        actions.handle("reject", f"measures-{VERSION}-a")[1],
        actions.handle("approve", f"{VERSION}-r2-b")[1],
        actions.handle("approve", "inconnue")[1],
    ]
    lock(tmp_path, step="journaux", detail="journaux : CI attendue sur data/x-r2 (abc, jusqu'à 60 min)")
    texts.append(actions.handle("update", None)[1])
    for text in texts:
        assert jargon(text) == [], text
    assert texts[-1] == "Une mise à jour est déjà en cours (attente de la validation sur GitHub) : attends sa fin."
    assert texts[2] == "Validé : Mesures de tes combats (1.60.1.70338) ; mise à jour lancée."


# --- 4. avancement d'une mise à jour ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("step", "detail", "stage"),
    [
        ("verrou", None, "préparation"),
        ("clone", "clone : reprise de data/x-r2 (abc), CI attendue", "attente de la validation sur GitHub"),
        ("jeu", "jeu : en cours", "recherche d'une nouvelle version du jeu"),
        ("nouvelle_version", None, "téléchargement de la nouvelle version"),
        ("correctifs", None, "lecture des correctifs du serveur"),
        ("journaux", "journaux : en cours", "mesures de tes combats"),
        ("journaux", "rejeu : 12 cas comparés en 40 s", "recalcul des builds"),
        ("journaux", "journaux : tasks.py verify --data dans le clone (moteurs : aucun)", "vérification des données"),
        ("journaux", "journaux : uv sync dans le clone", "préparation de la vérification"),
        ("journaux", "journaux : verify vert ; commit et poussée de data/x-r2", "envoi sur GitHub"),
        (
            "journaux",
            "journaux : CI attendue sur data/x-r2 (abc, jusqu'à 60 min)",
            "attente de la validation sur GitHub",
        ),
        (
            "journaux",
            "journaux : CI verte ; fusion de data/x-r2 dans main en avance rapide",
            "installation des données",
        ),
        ("addons", None, "lecture des addons"),
        ("fin", None, "finalisation"),
        (None, None, "travail en cours"),
    ],
)
def test_stage_in_player_words(step, detail, stage):
    assert update_stage(step, detail) == stage


def last(written=(), steps=(("journaux", "rien"),), verdicts=(), minutes=4):
    return {
        "started_at": "2026-10-11T08:00:00Z",
        "finished_at": f"2026-10-11T08:{minutes:02d}:10Z",
        "written": list(written),
        "steps": [{"name": n, "status": s} for n, s in steps],
        "verdicts": [{"id": i, "action": a} for i, a in verdicts],
    }


@pytest.mark.parametrize(
    ("doc", "pending", "text"),
    [
        (last(), [], "Mise à jour terminée en 4 min : rien de nouveau"),
        (last(written=[{"version": VERSION, "revision": 2}]), [], "Mise à jour terminée en 4 min : données installées"),
        (last(steps=[("journaux", "arrêt")]), [], "Mise à jour terminée en 4 min : en erreur, voir À valider"),
        (last(verdicts=[("m", "bloqué")]), [], "Mise à jour terminée en 4 min : en erreur, voir À valider"),
        (
            last(verdicts=[("m", "attente")]),
            [],
            "Mise à jour terminée en 4 min : une validation t'attend dans À valider",
        ),
        (last(), [{"kind": "pass_error"}], "Mise à jour terminée en 4 min : en erreur, voir À valider"),
        (last(minutes=0), [], "Mise à jour terminée en 10 s : rien de nouveau"),
    ],
)
def test_pass_outcome(doc, pending, text):
    assert pass_outcome(doc, pending) == text


def test_running_pass_carries_its_start_and_stage(make_deps):
    deps = make_deps()  # horloge des tests : 2026-09-27T12:00:00Z
    lock(deps.cache_dir, started_at="2026-09-27T11:50:00Z", step="journaux", step_at="2026-09-27T11:52:00Z",
         detail="journaux : CI attendue sur data/x-r2 (abc, jusqu'à 60 min)", detail_at="2026-09-27T11:51:00Z")  # fmt: skip
    update = status_payload(deps)["update"]
    assert update["started"] == int(datetime(2026, 9, 27, 11, 50, tzinfo=UTC).timestamp())
    assert update["stage"] == "attente de la validation sur GitHub"
    line = status_line({"version": VERSION, "freshness": "fresh", "running": True, "update": update})
    assert "mise à jour en cours (attente de la validation sur GitHub, 9 min)" in line
    assert jargon(line) == []


def test_finished_pass_carries_its_sentence(make_deps):
    deps = make_deps()
    path = update_dir(deps.cache_dir) / "last.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(last(written=[{"version": VERSION, "revision": 2}])), encoding="utf-8")
    done = status_payload(deps)["update"]["last"]
    assert done["text"] == "Mise à jour terminée en 4 min : données installées"
    assert done["finished_at"] == "2026-10-11T08:04:10Z"


def test_line_head_and_tail_leave_progress_and_counts_to_the_addon(make_deps):
    deps = make_deps()
    put(deps.cache_dir, waiting(f"measures-{VERSION}-a"))
    payload = status_payload(deps)
    assert "à valider" in payload["line"]
    assert "à valider" not in payload["line_head"] and "en cours" not in payload["line_head"]
    assert payload["line_head"].startswith("Données ")


# --- 6. empreinte et bouton Masquer ----------------------------------------------------------------------------


def test_published_cards_carry_a_stamp_and_a_hide_button(tmp_path):
    record_pending(tmp_path, waiting(f"measures-{VERSION}-a"))
    (card,) = CardSource(tmp_path).current()
    assert re.fullmatch(r"[0-9a-f]{12}", card["stamp"])
    assert card["buttons"][-1] == {"key": "hide", "label": "Masquer", "hide": True}
    assert CardSource(tmp_path).current()[0]["stamp"] == card["stamp"]  # même attente : même empreinte


def test_stamp_changes_when_the_entry_changes(tmp_path):
    record_pending(tmp_path, waiting(f"measures-{VERSION}-a"))
    before = CardSource(tmp_path).current()[0]["stamp"]
    path = update_dir(tmp_path) / "pending" / f"measures-{VERSION}-a.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**doc, "state": "approuvée"}), encoding="utf-8")
    assert CardSource(tmp_path).current()[0]["stamp"] != before
