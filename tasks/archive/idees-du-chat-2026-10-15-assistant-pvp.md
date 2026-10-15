# Idées du chat à intégrer (2026-10-15, soir) : assistant de route selon le type, et PvP actionnable

Fichier d'entrée écrit depuis la conversation claude.ai de Raphaël, après son essai en jeu de la nouvelle fenêtre
(bloc 6a). À intégrer au plan de CJ1 (blocs 4e et 6b), puis à archiver dans `tasks/archive/`.

## 1. L'assistant de feuille de route doit s'adapter au type de route

Constat : en choisissant « Réputation » (ou « Métier »), l'écran garde « Du niveau … au niveau … » et un champ libre
« Faction ou métier visé ». Ce n'est pas ainsi qu'on pense une réputation ou un métier.

- **Leveling** : niveaux de départ et d'arrivée (comme aujourd'hui), donjons et quêtes de classe cochés.
- **Réputation** : choix de la **faction dans une liste** (factions de mon camp, avec mon palier actuel lu en jeu,
  par exemple « Darnassus : Amical 1200/6000 »), puis le **palier visé** (Honoré, Révéré, Exalté) ; pas de niveaux
  ni de champ libre. La réponse donne la route (quêtes, objets à rendre, monstres à tuer avec leur nombre, plafond).
- **Métier** : choix du **métier dans la liste de mes métiers** (avec mon rang actuel lu en jeu), puis le **rang
  visé** (par exemple 75 → 150) ; la réponse s'appuie sur SkillUp Forever (plan, recettes, liste de courses, trajet).
- **Équipement** : liste BiS visée ou niveau visé, comme l'écran Équipement.
- Tant qu'un type n'est pas calculé (réputation avant le bloc 4e), le bouton le dit clairement au lieu de proposer
  un formulaire inutile.

## 2. PvP : dire quoi faire, pas seulement décrire

Constat : la « fiche de la classe de ma cible » (un Guerrier) liste les menaces, mes réponses, ses réponses, sa
fenêtre et ce qui manque ; c'est jugé « pas mal mais incompréhensible ».

- La réponse commence par **« Comment jouer contre lui »** : trois à cinq consignes concrètes, dans l'ordre du combat,
  adaptées à ma classe et à mes sorts (par exemple pour un Mage contre un Guerrier : garder la distance, Frost Nova
  puis s'éloigner, garder Blink pour sa charge, ne pas tenter de contrôle pendant Death Wish, etc.).
- Puis seulement le détail (menaces, réponses, fenêtres), en langage de joueur : pas de jargon (« rendement
  décroissant » remplacé ou expliqué en une phrase), chaque sort nommé avec ce qu'il fait.
- Toujours en langage clair, et avec la certitude affichée.
