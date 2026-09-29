# Résultat d'évaluation synthétique (T06)

`aggregate.json` reprend la forme du résultat de `claude plugin eval --json` (Claude Code 2.1.284, relevée au bloc A :
`cases[].name`, `cases[].arms.with[].graders[].name/passed`, `tracePath`), avec cinq cas inventés : deux positifs de la
catégorie talent (l'un réussi, l'autre avec un chiffre inventé), un hors périmètre, deux questions voisines (l'une
qui déclenche le plugin à tort). Les traces pointent vers `../transcripts/`.
