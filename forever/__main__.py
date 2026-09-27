"""`python -m forever` : même point d'entrée que la commande `forever`."""

import sys

from forever.cli import main

sys.exit(main())
