# Fixtures du pont de conversation (P06a)

- `claude_stream_status.jsonl`, `claude_stream_resume.jsonl` : flux `stream-json` réels de `claude` 2.1.294, relevés le
  2026-10-08 par la sonde 0.4 de `tasks/P06a-plan.md` (question « Quelle est la version des données ? », puis reprise
  par `--resume` : « Et la fraîcheur, en un mot ? »), avec la ligne de commande retenue. Identifiants (session, messages,
  outils), chemins et signatures remplacés ; le reste tel quel.
- `claude_stream_denied.jsonl` (refus d'un outil hors liste) et `claude_stream_build.jsonl` (résultat de
  `forever_build` avec son lien Talents Forever, contenu du résultat en liste de blocs `text`) : écrits à la main le
  2026-10-09 d'après la forme des flux réels ci-dessus (bloc C) ; le lien est fictif.
