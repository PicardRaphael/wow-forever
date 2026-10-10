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


def split_payload(payload: bytes, *, session: str, message_id: int) -> list[bytes]:
    """Charges des parties du message ; `[payload]` s'il tient dans une bande ; ValueError au-delà de MAX_MESSAGE."""
    raise NotImplementedError


def parse_fragment(payload: bytes) -> Fragment | None:
    """Partie lue dans la charge d'une bande ; None si ce n'est pas une partie ; RecordError si elle est mal formée."""
    raise NotImplementedError


class FragmentBuffer:
    """Parties reçues par message (session, numéro) ; la charge complète est rendue une seule fois."""

    def add(self, fragment: Fragment) -> bytes | None:
        """Ajoute la partie ; charge complète quand toutes les parties sont là (une seule fois), None sinon ;
        RecordError si le nombre de parties change d'une partie à l'autre."""
        raise NotImplementedError

    def received(self, session: str, message_id: int) -> list[int]:
        """Numéros des parties reçues, triés."""
        raise NotImplementedError
