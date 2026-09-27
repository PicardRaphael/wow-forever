---
paths:
  - "forever/engine/**"
---
# Moteur de mécaniques
- Fonctions pures : pas d'entrée-sortie, pas d'horloge, pas d'aléatoire non injecté (le générateur est un paramètre).
- Aucune constante de jeu en dur : les valeurs (recharge globale, multiplicateurs, plafonds) viennent des données de la version, passées en paramètre.
- Unités : secondes, points de dégâts, fractions (0,05 et non 5) ; arrondir seulement à l'affichage.
- Chaque fonction qui implémente une mécanique cite l'identifiant du registre dans sa docstring (ex. « Registre : A3 ») et a au moins un test.
