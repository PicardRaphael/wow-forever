"""Horodatages UTC au format `AAAA-MM-JJTHH:MM:SSZ`."""

from __future__ import annotations

from datetime import UTC, datetime


def format_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(text: str) -> datetime:
    """Accepte `AAAA-MM-JJ HH:MM:SS` ou ISO 8601 (Z ou décalage) ; une date sans fuseau est lue en UTC."""
    dt = datetime.fromisoformat(text.strip())
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def format_age(hours: float) -> str:
    """Âge lisible en français (ex. « 9 h »)."""
    if hours < 1:
        return "moins d'une heure"
    if hours < 48:
        return f"{int(hours)} h"
    return f"{int(hours // 24)} j"
