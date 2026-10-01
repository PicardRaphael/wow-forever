"""Client HTTP de production (bibliothèque standard) : seul appel à `urlopen` du paquet.

N'importe pas `forever.config`, qui l'injecte dans `Deps.http_get` (pas d'import circulaire)."""

from __future__ import annotations

import http.client
import urllib.request
from collections.abc import Mapping


def urllib_get(url: str, headers: Mapping[str, str], timeout: float) -> bytes:
    """(url, en-têtes, délai en secondes) -> corps de la réponse ; lève OSError en cas d'échec."""
    request = urllib.request.Request(url, headers=dict(headers))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body: bytes = response.read()
            return body
    except http.client.HTTPException as exc:  # réponse tronquée ou mal formée : même traitement qu'une panne
        raise OSError(str(exc)) from exc


def urllib_post(url: str, headers: Mapping[str, str], data: bytes, timeout: float) -> bytes:
    """POST (jeton de l'API Blizzard, T08b) : (url, en-têtes, corps, délai) -> corps de la réponse ; OSError sinon."""
    request = urllib.request.Request(url, data=data, headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body: bytes = response.read()
            return body
    except http.client.HTTPException as exc:
        raise OSError(str(exc)) from exc
