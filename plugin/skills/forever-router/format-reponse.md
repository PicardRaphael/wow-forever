# Format de réponse (WoW Forever)

Réponds **en français**, en réponse **courte** par défaut. Le détail (raisons, hypothèses complètes, alternatives,
sensibilité) seulement si l'utilisateur le demande (« détaille », « pourquoi », « montre les hypothèses »).

## Ordre
1. **Réponse directe** : une ou deux phrases qui répondent à la question.
2. **Chiffres** : chacun tiré d'un résultat d'outil de la session, avec l'unité du champ (`_s` : secondes ;
   `range_yd` : portée du jeu, que le client français écrit « m ») et l'outil entre parenthèses. Arrondis permis,
   jamais d'estimation. **Aucun calcul** : ni somme (points dépensés par arbre), ni produit (effet au maximum des
   cumuls), ni formule du registre appliquée à la main, ni moyenne de deux valeurs. Cite chaque valeur telle que
   l'outil la rend (un écart négatif se dit en mots : « de moins »). Si la question demande une valeur que l'outil ne
   rend pas, dis-le et donne la formule et ses paramètres tels quels.
3. **Certitude** : `provenance.certainty` traduite (certain, probable, supposé) ; pour un build, le champ `certainty`
   du rapport et `verifiable_in_game` (au-delà du plafond de la bêta, il n'est pas vérifiable avant la sortie).
4. **Hypothèses** : les plus importantes de `provenance.assumptions` (une ligne ; toutes sur demande).
5. **Angles morts** : `blind_spots` de `forever_build` ; statut du registre (`forever_explain_mechanic`) quand une
   mécanique décide de la réponse (statut `absent` : non modélisée).
6. **Provenance** : version du jeu, fraîcheur, date du résultat.

## Forme courte (par défaut)
Réponse directe et chiffres essentiels, puis, si une hypothèse ou un angle mort peut changer la conclusion, une ligne
« Attention : … ». Termine **toujours** par ce pied de réponse, sur une ligne :

`Certitude : <certain|probable|supposé> · Version <provenance.game_version> · Fraîcheur <à jour|en retard|incertaine|inconnue> (<provenance.generated_at>)`

Plusieurs outils : la certitude la plus basse, la version et la fraîcheur du dernier résultat.

## Règle « je ne sais pas »
Dis « je ne sais pas » (ou « le projet ne couvre pas encore … ») quand :
- le domaine n'est pas couvert (carte du routeur) ;
- la mécanique qui décide est au statut `absent` dans le registre ;
- l'outil est en erreur ou absent ;
- aucun outil ne donne le chiffre demandé.

Cite alors ce qui manque et comment le savoir : l'entrée du registre (`forever_explain_mechanic`), la tranche de
`docs/ROADMAP.md`, un test en jeu du protocole de `docs/ADDON.md`, ou une question de `docs/OPEN_QUESTIONS.md`.
N'estime rien de mémoire et ne donne pas de valeur de WoW Classic ou retail à la place.

## Sources extérieures
Un chiffre rapporté par le sous-agent `forever-web-researcher` s'écrit comme l'affirmation de sa source, avec son
type (officielle Blizzard, communautaire, simulateur), sa date et son adresse ; jamais comme un fait du projet.
