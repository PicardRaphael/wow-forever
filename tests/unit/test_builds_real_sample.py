"""Parseur sur un échantillon réel de https://wago.tools/api/builds (capturé le 2026-09-27, réduit)."""

import json
from datetime import UTC, datetime

from conftest import FIXTURES, LOCAL_VERSION, PREFIX, PRODUCT

from forever.pipeline.builds import latest_build, parse_builds

SAMPLE = FIXTURES / "wago" / "builds_real_sample.json"


def test_real_sample_is_parsed():
    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    builds = parse_builds(payload, PRODUCT, PREFIX)
    assert len(builds) == 5
    assert all(b.version.startswith(PREFIX) for b in builds)
    assert latest_build(builds).version == LOCAL_VERSION
    assert latest_build(builds).created_at == datetime(2026, 9, 24, 22, 2, 3, tzinfo=UTC)
