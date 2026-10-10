"""Messages en plusieurs parties (P06b, bloc A, décision 235). Une charge plus longue qu'une bande (`MAX_PAYLOAD`) est
découpée en parties ; la charge d'une partie s'écrit `F␟<session>␟<numéro>␟<i>␟<n>␟<octets>` (␟ = 0x1F, `F` à la
place de la version du protocole), les octets étant un morceau brut de la charge complète (une coupe peut tomber au
milieu d'un caractère UTF-8). L'addon montre les parties en carrousel ; le pont les réassemble dans n'importe quel
ordre, doublons ignorés, puis lit la charge complète comme un message ordinaire (`record.parse_payload`). Le même
découpage existe en Lua (`addon/ForeverBridge/Message.lua`, `Message.Fragments`)."""

from __future__ import annotations

from dataclasses import dataclass

FRAGMENT_TAG = "F"
MAX_MESSAGE = 32768  # octets d'un message complet (19 parties) ; au-delà, l'addon refuse l'envoi


@dataclass(frozen=True)
class Fragment:
    session: str
    message_id: int
    index: int  # de 1 à total
    total: int
    chunk: bytes


_SEP = b"\x1f"
_TAG = FRAGMENT_TAG.encode()
_KEPT = 16  # messages en cours de réassemblage gardés (les plus récents)


def _header(session: str, message_id: int, index: int, total: int) -> bytes:
    return _SEP.join([_TAG, session.encode("utf-8"), str(message_id).encode(), str(index).encode(),
                      str(total).encode(), b""])  # fmt: skip


def split_payload(payload: bytes, *, session: str, message_id: int) -> list[bytes]:
    """Charges des parties du message ; `[payload]` s'il tient dans une bande ; ValueError au-delà de MAX_MESSAGE.
    La taille des morceaux suit l'en-tête le plus long (numéros écrits avec autant de chiffres que le total)."""
    from forever.bridge.codec import MAX_PAYLOAD

    if len(payload) > MAX_MESSAGE:
        raise ValueError(f"message de {len(payload)} octets : {MAX_MESSAGE} au plus")
    if len(payload) <= MAX_PAYLOAD:
        return [payload]
    digits = 1
    while True:
        widest = 10**digits - 1
        chunk = MAX_PAYLOAD - len(_header(session, message_id, widest, widest))
        total = -(-len(payload) // chunk)
        if total <= widest:
            break
        digits += 1
    return [_header(session, message_id, i + 1, total) + payload[i * chunk : (i + 1) * chunk] for i in range(total)]


def parse_fragment(payload: bytes) -> Fragment | None:
    """Partie lue dans la charge d'une bande ; None si ce n'est pas une partie ; RecordError si elle est mal formée."""
    from forever.bridge.record import RecordError

    if not payload.startswith(_TAG + _SEP):
        return None
    fields = payload.split(_SEP, 5)
    if len(fields) != 6:
        raise RecordError(f"partie illisible : {len(fields)} champ(s), 6 attendus")
    _, session, number, index, total, chunk = fields
    if not (number.isdigit() and index.isdigit() and total.isdigit()):
        raise RecordError("partie illisible : numéro, rang ou total invalide")
    i, n = int(index), int(total)
    if not 1 <= i <= n:
        raise RecordError(f"partie illisible : rang {i} hors de 1…{n}")
    try:
        name = session.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RecordError("partie illisible : session en UTF-8 invalide") from exc
    return Fragment(name, int(number), i, n, chunk)


class FragmentBuffer:
    """Parties reçues par message (session, numéro) ; la charge complète est rendue une seule fois."""

    def __init__(self) -> None:
        self._parts: dict[tuple[str, int], dict[int, bytes]] = {}
        self._totals: dict[tuple[str, int], int] = {}
        self._done: dict[tuple[str, int], None] = {}

    def add(self, fragment: Fragment) -> bytes | None:
        """Ajoute la partie ; charge complète quand toutes les parties sont là (une seule fois), None sinon ;
        RecordError si le nombre de parties change d'une partie à l'autre."""
        from forever.bridge.record import RecordError

        key = (fragment.session, fragment.message_id)
        if key in self._done:
            return None
        total = self._totals.setdefault(key, fragment.total)
        if total != fragment.total:
            raise RecordError(f"partie illisible : {fragment.total} parties annoncées, {total} auparavant")
        parts = self._parts.setdefault(key, {})
        parts.setdefault(fragment.index, fragment.chunk)
        while len(self._parts) > _KEPT:
            oldest = next(iter(self._parts))
            del self._parts[oldest]
            self._totals.pop(oldest, None)
        if len(parts) < total:
            return None
        del self._parts[key]
        del self._totals[key]
        self._done[key] = None
        while len(self._done) > _KEPT * 8:
            del self._done[next(iter(self._done))]
        return b"".join(parts[i] for i in range(1, total + 1))

    def received(self, session: str, message_id: int) -> list[int]:
        """Numéros des parties reçues, triés."""
        return sorted(self._parts.get((session, message_id), {}))
