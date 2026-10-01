# Protocole de mesure des familiers du Chasseur (CH0, pour CH1)

CH0 décode du client les familles, capacités, rangs et niveaux requis (`forever/data/1.60.1.70124/pets.json`), et
rassemble dans `pet_rules.json` les règles relevées par des joueurs (registre L1 à L12, `suppose`). Ce document dit
quoi relever en jeu et dans mes journaux pour confirmer ou réfuter ce qui reste supposé ou probable : coût en points
d'entraînement (L4, colonne sans nom du client), régime (L7), héritage des statistiques du Chasseur (L10), vitesse
d'attaque (L11), niveau requis d'un rang (L3, à qui il s'applique). Aucun chiffre de jeu ici : les valeurs attendues
sont celles des données, les seuils celles du registre (`tolerance.n_min`).

## Ce que ForeverLogger relève (0.3.0)

Hors combat seulement (instantané reporté à la sortie du combat), dans `ForeverLoggerDB` (`addon/README.md`) :

1. **Instantané du familier** (`pet_snapshots`) à l'appel du familier (`UNIT_PET`), à l'ouverture de la fenêtre du
   familier (`PET_UI_UPDATE`) et à la connexion : famille, nom, niveau, PV maximaux, armure, vitesse d'attaque,
   puissance d'attaque, loyauté, bonheur, points d'entraînement (totaux et dépensés), régime ; et **au même
   instant** le Chasseur : Endurance, armure, puissance d'attaque en mêlée et à distance, critique en mêlée et à
   distance. Les retours multiples d'une API sont gardés par position ; une valeur secrète donne un trou.
2. **Fenêtre Beast Training** (`training`, événements `CRAFT_SHOW` et `CRAFT_UPDATE`) : ligne affichée, famille et
   niveau du familier, puis chaque capacité offerte avec son rang, son état, son coût en points d'entraînement et
   son niveau requis.

Lecture hors ligne : `uv run forever pets measure --addon-sv <WTF>/SavedVariables/ForeverLogger.lua` (rien n'est
écrit dans les données).

## Mesures

### Coût en points d'entraînement et niveau requis (L4, L3)
- Ouvrir Beast Training avec un familier de chaque famille possédée, à plusieurs niveaux du familier.
- `forever pets measure` compare chaque ligne au coût de la famille dans `pets.json` (`training_costs`) et au
  niveau du rang ; `concorde` sur toutes les lignes d'au moins deux familles : preuve proposée pour passer L4 à
  `certain` (accord demandé, jamais écrit seul). Une ligne en `ecart` est notée avec ses deux valeurs.
- Les capacités dont la colonne du client vaut zéro (Dash chez le Crocilisk, capacités nouvelles) : relever si elles
  apparaissent dans la fenêtre et à quel coût ; c'est la question ouverte sur le sens du zéro.
- Niveau requis : comparer, pour un même rang, le niveau du familier et celui du Chasseur au moment où le rang
  devient disponible ; dit si la règle de Classic (niveau du familier) vaut sur Forever.

### Régime (L7)
- Un instantané par famille possédée suffit : `forever pets measure` compare la liste du client (`GetPetFoodTypes`)
  au masque décodé. Toutes les familles relevées en `concorde` : preuve proposée pour L7.

### Héritage des statistiques (L10)
- **Paires d'instantanés** du même familier au même niveau, en changeant **une seule** statistique du Chasseur :
  équiper ou retirer une pièce d'Endurance (PV du familier), une pièce d'armure (armure du familier), une arme ou un
  effet de puissance d'attaque (puissance d'attaque du familier). Rouvrir la fenêtre du familier après chaque
  changement (nouvel instantané).
- `forever pets measure` forme le rapport « écart du familier / écart du Chasseur » pour chaque paire, avec `n` ;
  comparer à `pet_rules.json` (`inheritance.*`). Au moins `tolerance.n_min` paires concordantes : preuve proposée
  pour L10.
- Le bloc avancé du journal de combat donne aussi, pour un familier qui frappe, ses PV maximaux, sa puissance
  d'attaque et son armure : recoupement possible, à la même heure qu'un instantané.

### Vitesse d'attaque (L11)
- Dans le journal (`SWING_DAMAGE` d'une unité `Pet-…`), intervalle entre deux coups blancs consécutifs du familier
  sur la même cible, hors effets de hâte connus ; `forever pets measure` donne en plus la vitesse affichée par
  famille (instantanés).
- Comparer à la vitesse de base de `pet_rules.json` et à l'effet du passif de la bête (Faster Attack, Slower Attack,
  `pets.json`).

## Ce qu'il faut écarter

- Les instantanés pris en combat (l'addon les reporte, mais un instantané repris après un combat long peut porter
  des effets temporaires) : ne garder que ceux dont les buffs sont connus.
- Les combats contre un joueur et les auras de hâte (familier ou Chasseur) pour la vitesse d'attaque.
- Les sessions dont la version du client diffère de la version installée (`client_builds.split_by_version`,
  décision 135).
- Toute paire où deux statistiques du Chasseur ont changé à la fois.

## Forme de la preuve proposée au registre

Pour chaque entrée (L3, L4, L7, L10, L11) : fichier relevé, date, version du client, nombre de lignes ou de paires,
valeur observée et valeur des données, statut. Proposée dans le résumé de la tranche ; écrite au registre
(`valide-jeu` ou `valide-journal`) seulement après accord.
