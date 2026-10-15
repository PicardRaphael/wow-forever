# Idée du chat à intégrer (2026-10-15, nuit) : se renseigner sur les réputations de Forever avant l'assistant

Fichier d'entrée écrit depuis la conversation claude.ai de Raphaël. À intégrer au bloc 6b (assistant selon le type de
route) et au bloc 4e (route de réputation) de CJ1, puis à archiver dans `tasks/archive/`.

Constat en jeu (2026-10-15) : l'assistant « Réputation » montre toujours « Du niveau … au niveau … » et le champ libre
« Faction ou métier visé » (attendu : corrigé au bloc 6b). Raphaël ne se souvient plus de la façon dont Forever organise
les réputations et demande qu'on **se renseigne** avant de concevoir l'écran.

À faire avant de coder l'écran et la route :
- **Étude des réputations de Forever** (décision 264, lecture seule) : liste des factions du client (tables Faction et
  FactionGroup ou équivalent), leur camp, leur regroupement (villes de chaque camp, factions neutres, factions de zone
  comme Timbermaw Hold ou l'Argent Dawn, factions propres à Forever s'il y en a), comment on les monte (quêtes, monstres,
  objets à rendre, donjons), leurs plafonds, et ce que Forever a changé (notes officielles, Forever Guide, Naowh, Forever
  Companion, Questie) ; résultat écrit dans `docs/research/reputations-forever.md`.
- **Écran Réputation** : liste des factions lue en jeu dans le panneau de réputation du personnage (avec son palier
  actuel), groupées comme dans le jeu (camp, neutres, zones), éventuellement filtrées par zone ; puis le palier visé ;
  jamais de niveaux ni de champ libre.
