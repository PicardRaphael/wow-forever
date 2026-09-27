"""Horodatages UTC au format `AAAA-MM-JJTHH:MM:SSZ`."""

from __future__ import annotations

from datetime import datetime


def format_utc(dt: datetime) -> str:
    raise NotImplementedError


def parse_utc(text: str) -> datetime:
    """Accepte `AAAA-MM-JJ HH:MM:SS` ou ISO 8601 (Z ou décalage) ; une date sans fuseau est lue en UTC."""
    raise NotImplementedError


def format_age(hours: float) -> str:
    """Âge lisible en français (ex. « 9 h »)."""
    raise NotImplementedError
