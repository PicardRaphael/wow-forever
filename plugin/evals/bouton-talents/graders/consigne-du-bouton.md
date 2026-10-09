---
type: llm
---

La réponse suit la consigne du bouton : elle appelle forever_build au niveau suivant avec le build actuel du contexte, donne d'abord le talent à prendre au prochain niveau tiré du chemin projeté (respec.projected), signale l'égalité statistique quand next_step n'est pas départagé par le calcul en nommant les autres candidats, et ne donne le conseil de respec qu'en complément. Elle ne dit jamais qu'elle ne sait pas quel sera le prochain point, ni « je ne reconnais pas » un talent du contexte. Elle ne redemande pas le build.
