---
name: forever-familiers
description: "Familiers du Chasseur dans WoW Forever : système d'entraînement (Beast Training, points d'entraînement, loyauté, apprivoiser une bête), capacités de chaque famille et leurs rangs (niveau requis, coût), bonus de famille, régime, Beast Lore, et où apprivoiser la bête qui enseigne un rang près de ma zone et à mon niveau. Déclencher pour « où apprendre Morsure rang 3 près des Tarides », « capacités d'un loup », « comment marche l'entraînement des familiers », « que mange un sanglier ». Pas pour WoW retail (familiers exotiques, spécialisations de familier) ni WoW Classic hors Forever, ni la programmation."
---

# Familiers du Chasseur (WoW Forever)

Lis d'abord `../forever-router/format-reponse.md` : section « Plugin mal installé », forme de la réponse, règle
« je ne sais pas ». Aucun chiffre de mémoire : tout vient de `forever_lookup(kind="pets")`, recopié tel quel.

## Noms du client

Le joueur lit les noms dans son client : sa langue est `game_locale`, rendue par `forever_player_profile`. Cite
chaque sort, talent, capacité, objet et zone **tel qu'il apparaît dans son client** (en anglais pour `enUS`), suivi du
nom français entre parenthèses quand l'outil le rend (`name_fr`, `name.fr`) ; le reste de la réponse reste en
français. Sans `game_locale` connue, cite le nom anglais du client et le nom français entre parenthèses.

## Outil
- `forever_lookup(kind="pets")` sans `name` : règles du système (apprentissage, points d'entraînement, loyauté,
  marge d'apprivoisement, héritage des statistiques, vitesse d'attaque, focus, bonheur, Beast Lore), chacune avec
  sa source, sa date, sa certitude et son entrée du registre ; bugs signalés par des joueurs.
- `name` = famille, capacité ou bête (nom français ou anglais, casse et accents ignorés) : sa fiche. Capacité :
  `rank` pour un seul rang, `detail=true` pour les bêtes qui enseignent chaque rang. Plusieurs candidats : l'erreur
  les liste, choisis puis rappelle l'outil.
- `name` + `zone` (nom français ou anglais) + `level` : guide d'apprivoisement (bêtes de la zone demandée, puis des
  zones voisines du même continent à ce niveau ; coordonnées avec leur source et leur date ; apprivoisable
  maintenant ou niveau où elle le devient ; rang le plus haut atteignable).

## Zone, niveau, personnage (guide)
- Zone : celle de la question ; absente, demande-la (aucun champ de zone dans le profil).
- Niveau : question personnelle (« à mon niveau ») : `forever_player_profile` d'abord (section « Données du joueur »
  de `format-reponse.md`). Personnage actif Chasseur : son niveau ; sinon un seul Chasseur dans le profil : celui-là,
  annoncé en une ligne ; sinon demande le personnage ou le niveau. Jamais de niveau par défaut : l'outil le refuse.

## Réponse
- Guide : zone demandée d'abord, puis zones voisines (plage de niveau des PNJ telle que l'outil la rend) ; pour
  chaque bête : nom, niveau, apprivoisable ou à quel niveau, rang enseigné et sa marque de l'addon, deux ou trois
  coordonnées avec leur source (base de l'addon, carte communautaire, mes observations) et leur date, nombre de
  joueurs qui l'ont vue. Rang demandé au-dessus du rang atteignable : dis-le avec le niveau requis.
- Famille : capacités et rangs (niveau requis, coût en points d'entraînement, focus), bonus et régime.
- Système : les étapes d'apprentissage, puis chaque règle avec sa certitude ; le gain des points d'entraînement est
  inconnu (l'outil rend `null`) : dis « je ne sais pas ».

## Certitude
- Client (familles, capacités, rangs, niveau requis, focus) : certain. Coût en points d'entraînement, bonus de
  famille, régime : probable (colonne sans nom ou sens d'un type d'aura). Règles du système, bêtes, niveaux et
  coordonnées de Forever Bestiary : relevés de joueurs, supposé au mieux, avec leur date.
- Écarts entre le client et l'addon (orthographe, ligne en double, famille absente de l'un ou l'autre) : cite-les
  tels que la provenance les liste, le client fait foi ; une entrée du client jamais vue en jeu se dit telle.
- Addon absent : fiches du client seules, guide impossible ; dis-le.

## Hors de ce skill
- Choix du meilleur familier par contexte (leveling, donjon, raid, PvP), dégâts du familier, moteur du Chasseur :
  tranche CH1, « je ne sais pas » en attendant.
- Démons du Démoniste (DE1) ; familiers exotiques et talents de familier : aucun vu dans Forever selon les relevés.
