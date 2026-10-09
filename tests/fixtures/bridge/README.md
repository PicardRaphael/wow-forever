# Fixtures du pont de conversation (P06a)

- `claude_stream_status.jsonl`, `claude_stream_resume.jsonl` : flux `stream-json` réels de `claude` 2.1.294, relevés le
  2026-10-08 par la sonde 0.4 de `tasks/P06a-plan.md` (question « Quelle est la version des données ? », puis reprise
  par `--resume` : « Et la fraîcheur, en un mot ? »), avec la ligne de commande retenue. Identifiants (session, messages,
  outils), chemins et signatures remplacés ; le reste tel quel.
- `claude_stream_denied.jsonl` (refus d'un outil hors liste) et `claude_stream_build.jsonl` (résultat de
  `forever_build` avec son lien Talents Forever, contenu du résultat en liste de blocs `text`) : écrits à la main le
  2026-10-09 d'après la forme des flux réels ci-dessus (bloc C) ; le lien est fictif.
- `context_sonde_e.txt` : contexte réel envoyé par le jeu à la sonde en jeu E du 2026-10-09 (Mage Orc niveau 19,
  talents `105778:5,105779:5`), relu dans la transcription de la conversation « jeu ».
- `contexts/` (sonde en jeu F du 2026-10-09, banc d'essai des boutons) : contextes réels relus dans les transcriptions
  des conversations « jeu » (`~/.claude/projects/…-cache-forever-bridge-conversation/`), tels que le jeu les a envoyés :
  `mage19.txt` (bouton Talents, 10:13:58Z), `mage19_cible_chaman21_tauren.txt` (bouton PvP, 09:23:26Z),
  `mage19_cible_chaman21_skyborne.txt` (bouton PvP, 10:15:31Z ; le client envoie le nom de fichier de la race,
  « Skyborne », commun à deux races). Aucun contexte de Chasseur n'a été relevé : `chasseur19_construit.txt` est
  construit à la main (contexte du Mage, classe changée, sans talents ni équipement) pour le seul bouton Familiers.
