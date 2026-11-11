"""Guides RestedXP de Forever en français, générés et tenus à jour (FR1).

RestedXP traduit lui-même ses guides ; ce module ne comble que le trou (guides anglais sans version française) et
s'efface dès que RestedXP le comble : un guide qu'il livre en français est toujours recopié tel quel. Le texte de
RestedXP (licence CC BY-NC-SA 4.0) n'entre jamais dans le dépôt : mémoire de traduction et sauvegardes vivent hors du
dépôt (`~/.forever/rxp_fr/`, `<cache>/backups/rxp_fr/`). Aucune formule de combat, aucun chiffre de jeu ici.

- `tokens` : découpage d'une ligne de guide et gabarit à jetons ;
- `names` : noms officiels français (glossaire de RestedXP, tables frFR du client, Questie frFR) ;
- `source` : fichiers de RestedXP, guides alignés et glossaire ;
- `memory`, `translator`, `patterns` : mémoire de traduction, phrases types, traducteur injecté ;
- `build`, `validate`, `install`, `run` : assemblage, validateur bloquant, écriture et annulation, orchestration."""
