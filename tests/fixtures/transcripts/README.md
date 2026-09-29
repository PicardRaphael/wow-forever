# Transcripts de session (T06, hooks du plugin)

Lignes `user` et `assistant` seulement (`type`, `message.role`, `message.content`) ; chemins, identifiants et
contexte de session retirés ; noms du plugin de sonde remplacés par ceux du plugin `forever`.

| Fichier | Origine | Attendu du contrôle des chiffres |
|---|---|---|
| `session_sourced.jsonl` | réel : session `claude -p` du bloc A, `forever_lookup` Frostbolt rang 1 | aucun chiffre signalé |
| `eval_trace_sourced.jsonl` | réel : trace d'un passage de `claude plugin eval` (même question) | aucun chiffre signalé |
| `session_invented.jsonl` | réel : réponse d'une évaluation du bloc A, serveur MCP en échec (fin de la dernière phrase complétée à la main) | « 18 à 20 points de dégâts », « 5 secondes » |
| `session_no_forever.jsonl` | synthétique : session sans outil ni skill forever | aucun contrôle |
| `session_other_tool.jsonl` | synthétique : chiffre présent seulement dans un résultat `WebFetch` | « 18 à 20 dégâts » |
| `session_user_numbers.jsonl` | synthétique : chiffres de la question repris | aucun chiffre signalé |
| `session_rounding.jsonl` | synthétique : arrondis, fraction en %, secondes en minutes, point et virgule | « 15 % » |
| `session_sim_runner.jsonl` | synthétique : résultat du sous-agent `forever-sim-runner` | aucun chiffre signalé |

Régénération : `build_transcripts.py` du bloc A (hors dépôt), écriture en octets (LF).
