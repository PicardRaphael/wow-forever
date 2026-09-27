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
| 12 | SDK MCP v2 (`mcp>=2,<3`, `MCPServer` et `mcp.Client`) ; une erreur métier est renvoyée comme `CallToolResult(is_error=True)` avec erreur et provenance structurées | API actuelle ; le modèle voit le code d'erreur, l'action et la provenance | SDK v1 (`FastMCP`), exception brute (message générique) |
| 13 | Réseau limité à `forever status` / `forever_status` via `forever/pipeline/builds.py` (cache 6 h, délai 2 s) ; les autres outils relisent le cache et signalent son âge ; client HTTP injecté et simulé en test | Réponses rapides et hors ligne, un seul point réseau à auditer | Chaque outil interroge wago |
| 14 | pytest-socket : `allow_hosts(["127.0.0.1"])` sur les modules MCP, `--allow-unix-socket`, CI Ubuntu + Windows | La boucle asyncio de Windows ouvre une paire de sockets locale ; tout autre hôte reste bloqué | Désactiver pytest-socket pour ces tests |
| 15 | CLI : texte français par défaut + `--json`, pas de `--line` ; pas de statusline (la fraîcheur passe par SessionStart et le bloc provenance) | Une seule forme lisible et une forme machine ; la provenance suffit à signaler la fraîcheur | Statusline permanente |
| 16 | Aucune dépendance d'exécution ajoutée (argparse, urllib, hashlib, TypedDict, validateur de schéma maison) ; backend de construction `uv_build` | Surface minimale ; `uv_build` nécessaire aux points d'entrée | jsonschema, httpx, click |
| 17 | Données 70009 copiées octet pour octet depuis le seed (format positionnel des rangs conservé) ; sources et certitudes dans `sources.json` ; `overrides.json` dans le dossier de version | Traçabilité avec le seed, portage de `fm.py` en T02, immuabilité par version | Réécrire les fichiers, fichier mutable à la racine |
| 18 | Certitudes : FC→`certain`, FS→`probable`, PC et EST→`suppose` | Définitions de SPEC.md | Échelle à quatre niveaux |
| 19 | La certitude porte sur la valeur pour la `game_version` annoncée ; en T01, `stale` ajoute une hypothèse sans baisser la certitude | La baisse ciblée exige le diff de T03 | Tout passer à `suppose` si `stale` |
| 20 | Empreintes invalides : consultations refusées (`data_integrity`, code 3, commande de correction indiquée) ; `status` le signale sans échouer | Ne jamais répondre sur des données altérées ; garder un diagnostic | Avertissement seul |
| 21 | « Manifeste signé » = empreintes sha256 + historique git, sans signature cryptographique en T01 | Suffisant pour détecter une altération ; pas de gestion de clés | Signature GPG ou sigstore |
| 22 | Manifeste présent mais illisible, mal formé ou incohérent : `data_integrity` (code 3), distinct de `manifest_missing` ; provenance avec l'empreinte réelle des fichiers et l'écart au manifeste | Jamais de trace Python ; la provenance ne doit pas annoncer une empreinte que les fichiers n'ont pas | Traiter un manifeste corrompu comme absent ; afficher l'empreinte du manifeste |
| 23 | Cache de fraîcheur daté dans le futur : ignoré, avec une hypothèse | Une horloge qui recule rendrait le cache « récent » indéfiniment | Faire confiance au cache |
| 24 | Erreurs d'usage argparse (code 2) : même format que les autres erreurs (provenance, `--json` si présent sur la ligne) ; seule exclusion : `--help` | Contrat de sortie uniforme pour les consommateurs (hook SessionStart) | Exclure les erreurs d'usage du contrat |
