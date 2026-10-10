# Exports de l'addon SimulationCraft (P06b)

- `constructed_mage.txt` : **construit à la main** le 2026-10-10 d'après le format lu dans le code de l'addon
  (`Interface/AddOns/Simulationcraft`, 12.1.5-alpha-01 : `core.lua`, `forever/stats.lua`) ; personnage du contexte
  réel `tests/fixtures/bridge/contexts/mage19.txt` (Jen, Mage Orc 19), objets de son équipement ; valeurs de la
  fiche **synthétiques** (aucune règle de jeu), chaîne `talents=` fictive ; somme de contrôle recalculée (adler32 du
  texte qui précède sa ligne).
- Exports réels : ajoutés après la sonde en jeu G (collage de `/simc` dans la fenêtre du chat, gardé anonymisé dans
  le journal du pont, puis `forever bridge contexts export`), décision 235.
- `mage19_sonde_g.txt` : premier export **réel** (sonde en jeu G du 2026-10-10, `/simc` collé dans la fenêtre du chat),
  tel que le pont l'a gardé dans son journal : anonymisé par le pont (en-tête, `mage=`, `server=`), somme de contrôle
  d'origine juste puis recalculée (décision 235). Région vide et chaîne `talents=` du client gardées telles quelles.
