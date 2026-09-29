---
type: llm
---

La réponse recommande un talent pour le niveau 22 à partir du build actuel donné dans la question, en s'appuyant sur le résultat de l'outil (prochain talent, Monte Carlo). Elle ne recommande jamais un talent dont l'effet est non modélisé à la place d'un talent modélisé, sauf si l'outil le présente comme un point de passage vers un palier. Toute comparaison entre deux talents est un Monte Carlo contre un Monte Carlo avec son intervalle, jamais un Monte Carlo contre un résultat analytique. Si l'intervalle de l'écart contient zéro, la réponse dit que le choix est non départagé par le calcul (ou une formule équivalente) au lieu de désigner un meilleur talent.
