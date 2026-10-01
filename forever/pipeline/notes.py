"""Veille des notes officielles du forum de Blizzard (T08b, bloc F ; décision 148).

**Lancée à la main seulement** (`forever notes`, à la demande de l'utilisateur ou proposée par `forever watch` quand
le build du client change ; workflow en `workflow_dispatch` seul) : les conditions des API de Blizzard (§ 2.16)
interdisent les requêtes automatisées vers ses sites hors des API autorisées.

Un passage : `robots.txt` relu (arrêt si une adresse suivie devient interdite), une requête par catégorie suivie
(JSON de Discourse), puis une par sujet officiel nouveau ou révisé. Officiel : sujet ouvert par un compte de Blizzard
(administrateur, modérateur ou groupe de l'équipe) ; un message de joueur n'est jamais lu. Révisé : `updated_at` ou
`version` du premier message plus récents que l'état connu (les notes sont corrigées en place). Une fois par jour au
plus. L'état vit dans le cache ou, en CI, dans le corps des issues (marqueur caché). Le sujet « Known Issues » est
repéré : ses éléments sont des bugs reconnus, jamais modélisés (CLAUDE.md). Aucun texte du forum (CC BY-NC-SA 3.0)
n'est recopié : la sortie nomme l'adresse, les dates, le nombre d'éléments et les entités du projet reconnues."""

from __future__ import annotations

import fnmatch
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path
from typing import Any

from forever.config import FETCH_TIMEOUT, USER_AGENT, Deps
from forever.errors import FetchFailedError, OfflineError
from forever.timefmt import format_utc

HOST = "https://us.forums.blizzard.com"
ROBOTS_URL = f"{HOST}/robots.txt"
# Catégories suivies (relevé de l'audit du 2026-10-01) : discussion de la bêta, discussion générale de Forever.
CATEGORIES = {349: "wow-forever-beta-discussion", 347: None}
OFFICIAL_GROUPS = frozenset({"community-manager", "blizzard", "blizzard-employee", "developer"})
KNOWN_ISSUES = re.compile(r"known issues", re.IGNORECASE)
# Mots-clés reliés aux entrées du registre (aucun chiffre) ; les noms des sorts et talents viennent des données.
KEYWORDS: Mapping[str, str] = {
    "ignite": "A18",
    "winter's chill": "D4",
    "diminishing returns": "K1",
    "level cap": "I5",
    "experience": "I6",
    "rested": "D7",
    "talent point": "G3",
    "spell power": "G4",
    "critical strike": "A5",
    "base mana": "B9",
    "respec": "I5",
    "global cooldown": "B1",
}
STATE_MARKER = re.compile(r"<!-- forever-notes-state: (\{.*?\}) -->")
MIN_INTERVAL = timedelta(hours=24)


def category_url(category_id: int) -> str:
    slug = CATEGORIES.get(category_id)
    return f"{HOST}/en/wow/c/{slug}/{category_id}.json" if slug else f"{HOST}/en/wow/c/{category_id}.json"


def topic_url(topic_id: int) -> str:
    return f"{HOST}/en/wow/t/{topic_id}.json"


def page_url(topic_id: int) -> str:
    return f"{HOST}/en/wow/t/{topic_id}"


def disallowed(robots: str, path: str) -> bool:
    """`path` interdit pour `User-agent: *` (règles `Disallow`, motifs `*` et `$` des moteurs de recherche)."""
    applies, rules = False, []
    for raw in robots.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        field, value = (x.strip() for x in line.split(":", 1))
        if field.lower() == "user-agent":
            applies = value == "*"
        elif field.lower() == "disallow" and applies and value:
            rules.append(value)
    for rule in rules:
        pattern = rule if rule.endswith("$") else rule + "*"
        if fnmatch.fnmatchcase(path, pattern.rstrip("$")):
            return True
    return False


def _get(deps: Deps, url: str, robots: str | None) -> bytes:
    if robots is not None and disallowed(robots, url.removeprefix(HOST)):
        raise FetchFailedError(f"{url} interdit par robots.txt : lecture arrêtée.")
    try:
        return deps.http_get(url, {"User-Agent": USER_AGENT, "Accept": "application/json"}, FETCH_TIMEOUT)
    except OSError as exc:
        raise FetchFailedError(f"Lecture impossible de {url} ({exc}).") from exc


def _json(body: bytes, url: str) -> Any:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise FetchFailedError(f"Réponse illisible de {url} ({exc}).") from exc


def _official(user: Mapping[str, Any] | None) -> bool:
    if not user:
        return False
    groups = {str(user.get("primary_group_name") or ""), str(user.get("flair_name") or "")}
    return bool(user.get("admin") or user.get("moderator") or groups & OFFICIAL_GROUPS)


def _names(data_dir: Path) -> list[tuple[str, str]]:
    """(nom anglais, sorte) des sorts, talents et classes des données de la version la plus récente."""
    from forever.manifest import version_dirs

    versions = version_dirs(data_dir)
    if not versions:
        return []
    vdir = data_dir / versions[-1]
    out: dict[str, str] = {}

    def read(name: str) -> Any:
        try:
            return json.loads((vdir / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    for name in (read("decode_rules.json").get("spells") or {}).values():
        out.setdefault(str(name), "sort")
    for tree in read("talents.json").get("trees", []):
        for t in tree.get("talents", []):
            if t.get("name"):
                out.setdefault(str(t["name"]), "talent")
    for cls, entry in (read("classes.json").get("classes") or {}).items():
        out.setdefault(str(cls), "classe")
        for spell in (entry.get("spells") or {}).values():
            if spell.get("name"):
                out.setdefault(str(spell["name"]), "sort de classe")
    return sorted(out.items(), key=lambda kv: (-len(kv[0]), kv[0]))


def _text(cooked: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", cooked))


def recognise(text: str, names: Sequence[tuple[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Entités des données et mots-clés du registre nommés dans un texte (mot entier, casse ignorée)."""
    lower = text.lower()
    entities = [
        {"name": n, "kind": k} for n, k in names if re.search(rf"(?<![\w']){re.escape(n.lower())}(?![\w'])", lower)
    ]
    keywords = [
        {"keyword": kw, "registry": reg}
        for kw, reg in sorted(KEYWORDS.items())
        if re.search(rf"(?<![\w']){re.escape(kw)}(?![\w'])", lower)
    ]
    return entities, keywords


def _state_path(cache_dir: Path) -> Path:
    return cache_dir / "notes" / "state.json"


def _load_state(cache_dir: Path) -> dict[str, Any]:
    try:
        doc = json.loads(_state_path(cache_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def read_notes(deps: Deps, state: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Notes officielles nouvelles ou révisées depuis `state` (défaut : état du cache). Une fois par jour au plus."""
    if deps.offline:
        raise OfflineError("la lecture des notes officielles")
    cached = _load_state(deps.cache_dir)
    last = cached.get("last_run")
    now = deps.now()
    if isinstance(last, str):
        try:
            if now - datetime.fromisoformat(last) < MIN_INTERVAL:
                return {"skipped": True, "last_run": last, "notes": [], "checked_at": format_utc(now)}
        except ValueError:
            pass
    known: Mapping[str, Any] = state if state is not None else cached.get("topics", {})
    robots = _get(deps, ROBOTS_URL, None).decode("utf-8", errors="replace")
    names = _names(deps.data_dir)
    notes: list[dict[str, Any]] = []
    seen: dict[str, Any] = dict(known)
    for category in CATEGORIES:
        url = category_url(category)
        doc = _json(_get(deps, url, robots), url)
        users = {u.get("id"): u for u in doc.get("users", [])}
        for topic in doc.get("topic_list", {}).get("topics", []):
            op = next((p for p in topic.get("posters", []) if "Original Poster" in str(p.get("description"))), None)
            if not _official(users.get(op.get("user_id")) if op else None):
                continue  # message de joueur : jamais lu
            tid = int(topic["id"])
            turl = topic_url(tid)
            tdoc = _json(_get(deps, turl, robots), turl)
            posts = tdoc.get("post_stream", {}).get("posts", [])
            first = posts[0] if posts else {}
            if not first.get("staff") and not _official(first):
                continue
            updated, version = str(first.get("updated_at") or ""), int(first.get("version") or 1)
            before = known.get(str(tid))
            seen[str(tid)] = {"updated_at": updated, "version": version}
            if before and before.get("updated_at") == updated and int(before.get("version") or 1) == version:
                continue
            if before and (str(before.get("updated_at") or "") > updated or int(before.get("version") or 1) > version):
                continue
            text = _text(str(first.get("cooked") or ""))
            entities, keywords = recognise(f"{topic.get('title', '')} {text}", names)
            known_issues = bool(KNOWN_ISSUES.search(str(topic.get("title", ""))))
            notes.append(
                {
                    "topic_id": tid,
                    "title": str(topic.get("title", "")),
                    "url": page_url(tid),
                    "category": category,
                    "created_at": str(topic.get("created_at", "")),
                    "updated_at": updated,
                    "version": version,
                    "author": str(first.get("user_title") or first.get("username") or ""),
                    "change": "révisé" if before else "nouveau",
                    "known_issues": known_issues,
                    "items": len(re.findall(r"<li\b", str(first.get("cooked") or ""))) if known_issues else 0,
                    "entities": entities,
                    "keywords": keywords,
                }
            )
    path = _state_path(deps.cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc_state = {"last_run": format_utc(now), "topics": seen}
    path.write_bytes((json.dumps(doc_state, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    for note in notes:
        note["issue_body"] = issue_body(note)
    return {"skipped": False, "notes": notes, "checked_at": format_utc(now)}


def issue_body(note: Mapping[str, Any]) -> str:
    """Corps d'issue déterministe (marqueur d'état caché en dernière ligne) ; aucun texte du forum recopié."""
    lines = [
        f"Note officielle {note['change']} : [{note['title']}]({note['url']})",
        "",
        (
            f"- auteur : {note['author']} ; créée le {note['created_at'][:10]} ; révisée le {note['updated_at'][:10]}"
            f" (version {note['version']})"
        ),
    ]
    if note.get("known_issues"):
        lines.append(
            f"- **problèmes connus** : {note['items']} élément(s), bugs reconnus par Blizzard : à ne jamais modéliser"
        )
    if note.get("entities"):
        lines.append("- entités nommées : " + ", ".join(f"{e['name']} ({e['kind']})" for e in note["entities"]))
    if note.get("keywords"):
        lines.append("- registre : " + ", ".join(f"{k['registry']} ({k['keyword']})" for k in note["keywords"]))
    lines += [
        "",
        (
            "À vérifier : chaque valeur citée est relue dans le client ou mesurée avant tout changement ; une note seule"
            " ne change jamais une donnée (docs/DATA_SOURCES.md)."
        ),
        "",
        "<!-- forever-notes-state: "
        + json.dumps(
            {"topic_id": note["topic_id"], "updated_at": note["updated_at"], "version": note["version"]},
            sort_keys=True,
        )
        + " -->",
    ]
    return "\n".join(lines) + "\n"


def state_from_issues(issues: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """État lu dans le corps des issues (`gh issue list --json number,body`) : sujet -> dernière version vue."""
    state: dict[str, Any] = {}
    for issue in issues:
        for m in STATE_MARKER.finditer(str(issue.get("body") or "")):
            try:
                data = json.loads(m.group(1))
            except ValueError:
                continue
            key = str(data.get("topic_id"))
            entry = {"updated_at": str(data.get("updated_at")), "version": int(data.get("version") or 1)}
            if key not in state or (entry["updated_at"], entry["version"]) > (
                state[key]["updated_at"],
                state[key]["version"],
            ):
                state[key] = entry
    return state
