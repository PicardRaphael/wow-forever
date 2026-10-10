"""`python -m forever` : même point d'entrée que la commande `forever`."""

import sys

from forever.cli import main

if __name__ == "__main__":  # garde : un processus de calcul réimporte le module principal (Windows, décision 230)
    sys.exit(main())
