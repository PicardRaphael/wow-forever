"""Contrôle des origines déclarées (`forever/data/<version>/origins.json`, T08b, bloc H) : enveloppe de
`forever.origins.main`. Échec si une valeur n'a pas d'origine, si une règle `manuel` n'a pas de raison ou dépasse
`probable`, si un motif couvre une valeur `manuel`, si une certitude déclarée dépasse celle de son origine (hors
abaissement prévu), ou si une règle ne couvre plus rien."""

import sys

from forever.origins import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
