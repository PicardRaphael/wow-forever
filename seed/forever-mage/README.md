# forever-mage — agent Mage WoW Forever pour Claude Code

## Installation
Copier le dossier `forever-mage` dans `~/.claude/skills/` (tous les projets) ou dans `.claude/skills/` d'un projet. Prérequis : Python 3.10+, Node 18+ (pour le moteur de raid). Aucune bibliothèque externe.

## Premier lancement
```
python scripts/update_data.py check          # le build des données est-il à jour ?
python tests/run_all.py                      # 10 tests, dont la couverture des 30 mécaniques
python scripts/import_character.py --name moi --level 16 --race Orc --int 52 --spirit 48 --sp 9 --spell-crit 0.031 --talents improvedFrostbolt=5,elementalPrecision=1
```
Ensuite, pose tes questions à Claude normalement : le skill se déclenche sur tout ce qui touche au Mage de Forever.

## Exemples
```
python scripts/sim_leveling.py --level 16 --talents improvedFrostbolt=5,elementalPrecision=2 --rotation frost
python scripts/optimize.py leveling --from 10 --to 40 --race Orc
python scripts/optimize.py raid --spec fire --sp 650 --crit 0.18
python scripts/optimize.py pvp --weights burst=0.4,control=0.3,survival=0.2,sustain=0.1
python scripts/respec.py --level 60 --current ... --target ... --hours 20 --n 1
```
Les données vivent dans `data/<build>/` avec leur provenance ; `data/overrides.json` garde les corrections lues dans le client.
Licences : arbres de talents issus de projets MIT (wowsims Forever) ; lien requis vers wowsims/classic.
