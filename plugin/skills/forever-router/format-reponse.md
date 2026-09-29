# Format de réponse (WoW Forever)

Réponds **en français**, en réponse **courte** par défaut. Le détail (raisons, hypothèses complètes, alternatives,
sensibilité) seulement si l'utilisateur le demande (« détaille », « pourquoi », « montre les hypothèses »).

## Ordre
1. **Réponse directe** : une ou deux phrases qui répondent à la question.
2. **Chiffres** : chacun tiré d'un résultat d'outil de la session, avec l'unité du champ (`_s` : secondes ;
   `range_yd` : portée du jeu, que le client français écrit « m ») et l'outil entre parenthèses. Arrondis permis,
   jamais d'estimation. **Aucun calcul** : ni somme (points dépensés par arbre), ni produit (effet au maximum des
   cumuls), ni formule du registre appliquée à la main, ni moyenne de deux valeurs. Les totaux sont dans les
   résultats : `points` (par arbre, total, disponibles, non dépensés) et `points_total` de chaque étape de `order` de
   `forever_build`, `derived` (valeur de chaque cumul et au maximum) de `forever_explain_mechanic` et
   `forever_lookup`, `monte_carlo_stats` de `forever_sim_leveling`, `advantage` de chaque écart. Cite chaque valeur
   telle que l'outil la rend (un écart négatif se dit en mots : « de moins »). Si la question demande une valeur que
   l'outil ne rend pas, dis-le et donne la formule et ses paramètres tels quels.
3. **Certitude** : `provenance.certainty` traduite (certain, probable, supposé) ; pour un build, le champ `certainty`
   du rapport et `verifiable_in_game` (au-delà du plafond de la bêta, il n'est pas vérifiable avant la sortie).
4. **Hypothèses** : les plus importantes de `provenance.assumptions` (une ligne ; toutes sur demande).
5. **Angles morts** : `blind_spots` de `forever_build` ; statut du registre (`forever_explain_mechanic`) quand une
   mécanique décide de la réponse (statut `absent` : non modélisée).
6. **Provenance** : version du jeu, fraîcheur, date du résultat.

## Forme courte (par défaut)
Réponse directe et chiffres essentiels, puis, si une hypothèse ou un angle mort peut changer la conclusion, une ligne
« Attention : … ». Termine **toujours** par ce pied de réponse, sur une ligne :

`Certitude : <certain|probable|supposé> · Version <provenance.game_version> r<provenance.data_revision> · Fraîcheur <à jour|en retard|incertaine|inconnue> (<provenance.generated_at>)`

Plusieurs outils : la certitude la plus basse, la version et la fraîcheur du dernier résultat.

## Données du joueur
Race, faction, niveau, talents actuels et métiers sont des données personnelles.
- Question qui en dépend (build, prochain talent, temps par monstre, respec, zone) : appelle `forever_player_profile`
  **avant** tout calcul. Les outils de calcul ne lisent jamais le profil : passe-leur toi-même les valeurs.
- Donnée présente : utilise-la sans la redemander et rappelle le profil en une ligne en tête de réponse :
  « Profil : <nom>, <classe> <race>, niveau <niveau> (profil actif) ». `stale` vrai : signale que le profil date
  d'une autre version des données.
- Donnée absente (`missing`, ou profil vide) et donnée écrite dans la question absente aussi : demande-la **avant**
  le calcul, en une question courte, avec la valeur la plus probable proposée (celle de la conversation ou du
  profil), et la commande pour l'enregistrer : `forever profile set <nom> --race … --level … --talents "clé=rang,…"`.
- La question prime sur le profil : un niveau écrit dans la question remplace celui du profil ; les talents du
  profil ne valent qu'au niveau du profil (`current` de `forever_build` pour le niveau suivant). Question posée à un
  autre niveau (« au niveau 30… ») : calcul pour ce niveau avec la race et la faction du profil, build conseillé par
  `forever_build`, présenté comme tel (« build conseillé, pas le tien »), sans redemander les talents.
- Jamais de défaut muet : un résultat dont `inputs.<champ>.origin` vaut `default` pour une donnée personnelle ne se
  présente pas comme la réponse du joueur ; redemande la donnée ou dis que le calcul suppose ce défaut.
- Ne compte jamais toi-même les points du joueur ni ceux d'un niveau : `points.available` et `points_total` de
  `forever_build` les donnent.
- Une réponse qui se limite à demander une donnée finit elle aussi par le pied de réponse (provenance de
  `forever_player_profile`).
- Classe autre que Mage : profil lu, calcul « non couvert » (carte du routeur).

## Comparer deux options
- Compare à mesure égale : un Monte Carlo contre un Monte Carlo (mêmes combats), jamais un Monte Carlo contre un
  analytique.
- Entre deux builds ou deux talents : l'écart apparié rendu par `forever_build` (`alternative.gap`, `gap` des étapes
  de `order`, `next_step`), ou deux `monte_carlo_stats` avec leur intervalle.
- Intervalle qui contient zéro (`significant` faux) : dis « choix non départagé par le calcul », sans désigner de
  meilleur.
- À égalité, un talent modélisé passe devant un non modélisé ; ne recommande jamais un talent non modélisé à la place
  d'un modélisé. Seule exception : `decided_by` vaut `passage_palier` (point de passage vers un palier, effet non
  modélisé), à dire comme tel. Talent non modélisé : `modeled` faux, ou angle mort `absent` du registre.

## Plugin mal installé
Avant tout, vérifie que les outils `mcp__plugin_forever_forever__…` existent (`ToolSearch`). Introuvables, ou
serveur qui ne répond pas : réponds seulement par ce message, sans rien répondre de mémoire :

> Le serveur forever ne répond pas : la variable FOREVER_HOME est absente ou ne pointe pas vers le dépôt wow-forever. Depuis la racine du dépôt, lancer `powershell -ExecutionPolicy Bypass -File scripts\install_plugin.ps1`, puis ouvrir un nouveau terminal et relancer Claude Code.

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
