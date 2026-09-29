# Résultat d'évaluation synthétique (T06)

`aggregate.json` reprend la forme du résultat de `claude plugin eval --json` (Claude Code 2.1.284, relevée au bloc A :
`cases[].name`, `cases[].arms.with[].graders[].name/passed`, `tracePath`), avec cinq cas inventés : deux positifs de la
catégorie talent (l'un réussi, l'autre avec un chiffre inventé), un hors périmètre, deux questions voisines (l'une
qui déclenche le plugin à tort). Les traces pointent vers `../transcripts/`.

`aggregate_hook.json` et `trace_with_hook.jsonl` : un cas dont la trace porte le message du hook Stop (« Stop says:
[forever:chiffres] … », forme relevée au bloc A) alors que la dernière réponse ne contient aucun chiffre : le rapport
reprend le message du hook, qui a vu le transcript de la session, plutôt qu'un nouveau calcul sur la trace.
