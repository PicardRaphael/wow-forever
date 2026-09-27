"""Interface en ligne de commande : `forever status | lookup | manifest | mcp`."""

from __future__ import annotations

import sys

from forever.config import Deps


def main(argv: list[str] | None = None, deps: Deps | None = None) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
