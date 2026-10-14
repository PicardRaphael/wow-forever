# Idée du chat à intégrer : comparer nos routes aux parcours de RestedXP

Fichier d'entrée écrit depuis la conversation claude.ai de Raphaël, à sa demande, pour ne pas l'oublier. RX1 étant
terminée, ce travail devient une petite suite de RX1 (« RX1 suite » ou tranche courte), à placer **après LN1** dans le
calendrier, avant la sortie du 4 novembre si possible (il améliore les routes du premier jour). À intégrer par une session
Claude Code (décision numérotée, ROADMAP), puis à archiver dans `tasks/archive/`.

## Demande de Raphaël

À côté de la comparaison avec Factoruide (`forever route compare`), comparer nos routes aux parcours **gratuits** de
RestedXP pour Forever installés dans RXPGuides, sur le même personnage et la même tranche de niveaux.

1. Vérifier d'abord jusqu'où vont les parcours **en clair** dans l'addon (niveau 21 ou 22 selon la faction d'après nos
   relevés précédents, ou plus, avec les donjons jusqu'au 30 s'ils sont en clair).
2. Pour chaque comparaison : calculer notre route ; faire passer la leur dans notre simulateur ; comparer les durées
   estimées et les choix (ordre des zones, quêtes gardées ou sautées, donjons, trajets) ; expliquer pourquoi la nôtre est
   plus ou moins rapide ; en tirer des réglages pour notre optimiseur.
3. Partie payante : la comparaison se fait sur les **mesures réelles** de Raphaël. Quand il suivra un guide payant en
   jouant, ForeverLogger relève sa vitesse niveau par niveau, et `forever route` compare nos routes à cette montée réelle.

## Règles

- C'est une **mesure**, pas une source : seuls les chiffres de la comparaison et les leçons entrent dans le dépôt ; jamais
  une étape recopiée dans nos routes.
- Jamais aucun guide **payant** ni **chiffré**, même acheté (ni lu, ni déchiffré, ni rejoué).
- À consigner dans `DECISIONS.md` comme une **exception encadrée** à l'exclusion de RXPGuides (qui reste exclu comme
  source de données ; on n'en lit que les parcours gratuits en clair, pour mesurer).
