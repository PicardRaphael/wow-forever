# Décisions (à compléter au fil du projet)

| # | Décision | Raison | Alternative écartée |
| --- | --- | --- | --- |
| 1 | Un cœur Python unique (CLI + MCP) et un plugin mince | Testable, portable vers Claude.ai, ChatGPT et un site, économe en tokens | Logique dans les skills |
| 2 | Aucune donnée de jeu dans les skills ni la mémoire | Péremption silencieuse, coût en tokens | Skills « encyclopédie » |
| 3 | Données versionnées par version du jeu + manifeste signé | Fraîcheur vérifiable, diffs | Données « latest » écrasées |
| 4 | Registre de mécaniques lié aux tests | Exhaustivité contrôlée par la CI | Liste informelle |
| 5 | Monte Carlo pour décider, analytique pour explorer | Précision et vitesse | Un seul modèle |
| 6 | Parité avec wowsims Forever plutôt qu'une réécriture | Moteur existant, règles Forever déjà portées | Porter wowsims en Python |
| 7 | Veille par GitHub Actions (Routines en option) | Routines encore en aperçu de recherche | Routines seules |
| 8 | Tranches verticales, tests d'abord | Retour de bout en bout rapide, moins de dérive | Phases horizontales |
| 9 | Sous-agents limités à quatre, sorties courtes | Coût et cohérence | Un sous-agent par classe |
| 10 | Serveur MCP distant seulement après le plugin | Priorité à l'usage quotidien dans Claude Code | Tout en même temps |
| 11 | CLAUDE.md court (~35 lignes), règles ciblées par dossier, procédures en skills, garanties en hooks | Pratiques de Boris Cherny et de la doc officielle : un fichier gonflé fait ignorer les consignes ; seuls les hooks garantissent | Un CLAUDE.md exhaustif et emphatique |
