"""Téléchargements robustes (décision 230, point 3) : chaque table qui expire ou échoue est retentée (trois essais,
attente croissante entre deux essais, délai de la requête allongé à chaque essai), chaque essai noté dans le journal ;
réseau et attente simulés (aucune pause réelle)."""

import pytest
from conftest import FIXTURES, PREVIOUS_VERSION, FakeHttp

from forever.config import FETCH_ATTEMPTS, FETCH_BACKOFF, FETCH_TIMEOUT
from forever.errors import FetchFailedError
from forever.pipeline.fetch import fetch_gametables, fetch_tables, gametable_url, table_path, table_url

FETCH = FIXTURES / "wago" / "fetch"
SPELLNAME = (FETCH / "SpellName_min.csv").read_bytes()
URL = table_url("SpellName", PREVIOUS_VERSION, None)
URL_FR = table_url("SpellName", PREVIOUS_VERSION, "frFR")
TIMEOUT = TimeoutError("The read operation timed out")


class SeqHttp(FakeHttp):
    """Réponses successives par URL (corps ou exception), puis la dernière répétée."""

    def __init__(self, seq):
        super().__init__()
        self.seq = {url: list(answers) for url, answers in seq.items()}

    def __call__(self, url, headers, timeout):
        self.calls.append((url, dict(headers), timeout))
        answers = self.seq[url]
        answer = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


class Sleeps(list):
    def __call__(self, seconds):
        self.append(seconds)


def test_three_attempts_with_growing_timeouts_and_waits():
    assert FETCH_ATTEMPTS == 3
    assert len(FETCH_BACKOFF) == FETCH_ATTEMPTS - 1 and list(FETCH_BACKOFF) == sorted(FETCH_BACKOFF)


def test_a_timeout_is_retried_and_the_table_is_written(make_deps):
    http = SeqHttp({URL: [TIMEOUT, SPELLNAME]})
    sleeps, lines = Sleeps(), []
    deps = make_deps(http=http)
    result = fetch_tables(deps, PREVIOUS_VERSION, ["SpellName"], sleep=sleeps, log=lines.append)
    assert table_path(deps.cache_dir, PREVIOUS_VERSION, "enUS", "SpellName").read_bytes() == SPELLNAME
    assert result[0]["sha256"] and not result[0]["from_cache"]
    assert [t for _, _, t in http.calls] == [FETCH_TIMEOUT, FETCH_TIMEOUT * 2]  # délai allongé au deuxième essai
    assert sleeps == [FETCH_BACKOFF[0]]
    assert any("enUS/SpellName" in line and "essai 1/3" in line and "timed out" in line for line in lines)
    assert any("enUS/SpellName" in line and "essai 2/3" in line for line in lines)


def test_three_failures_give_up_with_every_attempt_in_the_log(make_deps):
    http = SeqHttp({URL: [TIMEOUT]})
    sleeps, lines = Sleeps(), []
    with pytest.raises(FetchFailedError) as info:
        fetch_tables(make_deps(http=http), PREVIOUS_VERSION, ["SpellName"], sleep=sleeps, log=lines.append)
    assert "enUS/SpellName" in info.value.message and "timed out" in info.value.message
    assert [t for _, _, t in http.calls] == [FETCH_TIMEOUT, FETCH_TIMEOUT * 2, FETCH_TIMEOUT * 4]
    assert sleeps == list(FETCH_BACKOFF)
    for n in (1, 2, 3):
        assert any(f"essai {n}/3" in line for line in lines), lines


def test_a_non_csv_answer_is_retried_too(make_deps):
    http = SeqHttp({URL: [b"<html>erreur</html>", SPELLNAME]})
    fetch_tables(make_deps(http=http), PREVIOUS_VERSION, ["SpellName"], sleep=Sleeps())
    assert len(http.calls) == 2


def test_a_good_table_is_downloaded_once_without_waiting(make_deps):
    http = SeqHttp({URL: [SPELLNAME]})
    sleeps = Sleeps()
    fetch_tables(make_deps(http=http), PREVIOUS_VERSION, ["SpellName"], sleep=sleeps)
    assert len(http.calls) == 1 and sleeps == []


def test_retries_are_per_table(make_deps):
    """Une table en échec n'empêche pas les autres d'être téléchargées (toutes retentées chacune de leur côté)."""
    http = SeqHttp({URL: [TIMEOUT], URL_FR: [TIMEOUT, SPELLNAME]})
    deps = make_deps(http=http)
    with pytest.raises(FetchFailedError) as info:
        fetch_tables(deps, PREVIOUS_VERSION, ["SpellName"], locales=["enUS", "frFR"], sleep=Sleeps())
    assert "enUS/SpellName" in info.value.message and "frFR/SpellName" not in info.value.message
    assert table_path(deps.cache_dir, PREVIOUS_VERSION, "frFR", "SpellName").is_file()


def test_tests_never_sleep_for_real(make_deps):
    """Les Deps des tests portent une attente simulée : un échec retenté ne fait aucune pause réelle."""
    deps = make_deps(http=FakeHttp(routes={URL: TIMEOUT}))
    deps.sleep(1000.0)  # rendu immédiatement
    with pytest.raises(FetchFailedError):
        fetch_tables(deps, PREVIOUS_VERSION, ["SpellName"])


def test_gametables_are_retried(make_deps):
    url = gametable_url(1391660, PREVIOUS_VERSION)
    body = b"Level\tMage\n1\t1\n"
    http = SeqHttp({url: [TIMEOUT, body]})
    lines = []
    fetch_gametables(
        make_deps(http=http), PREVIOUS_VERSION, {"SpellScaling": 1391660}, sleep=Sleeps(), log=lines.append
    )
    assert len(http.calls) == 2 and any("essai 1/3" in line for line in lines)
