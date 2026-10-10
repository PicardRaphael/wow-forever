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
- `links_constructed.txt` (P06b, bloc A) : valeur de la clé de contexte `links` **construite à la main** d'après le
  format de `forever/bridge/items.py` (un lien d'objet avec suffixe aléatoire, un lien de sort ; corps, nom et lignes
  d'infobulle séparés par 0x1C, liens par 0x1D) ; lignes d'infobulle synthétiques. Remplacée ou complétée par les
  relevés de la sonde en jeu G (`forever bridge contexts export`).
- `reply_seconds.json` (P06b, bloc A) : les neuf durées de réponse (`reply.seconds`) du journal du pont du 2026-10-09,
  relevées le 2026-10-10 pour chiffrer le calendrier des relevés (`forever/bridge/polls.py`).
- `contexts/mage19_sonde_g.txt`, `mage19_sonde_g_liens.txt`, `mage19_sonde_g_simc.txt` (P06b, sonde en jeu G du
  2026-10-10) : contextes **réels** relevés par `forever bridge contexts export` (question, question avec deux liens
  Maj+clic et leur infobulle, envoi de l'export `/simc`), **anonymisés** : `name` et `realm` remplacés
  (`Personnage`, `Royaume`), GUID des artisans des objets fabriqués remplacés par `Player-0000-0000000N` ; le reste tel
  quel (chaînes d'objet complètes, avec le champ de l'artisan).
- `claude_stream_addons.jsonl`, `claude_stream_addons_denied.jsonl` (P06b, sonde 0.2 du 2026-10-10, accord de
  l'utilisateur) : flux `stream-json` réels de `claude` 2.1.296 dans une **copie** de RaphCompletionist placée dans le
  cache, avec la ligne de la conversation « addons » (`--tools Read,Glob,Grep,Edit,Write`, `--restricted`, règles
  `Read(./**)`, `Edit(./**)`, `Write(./**)`, `Glob(./**)`, `Grep(./**)`, `dontAsk`) : travail dans le dossier
  (lecture, Glob, Grep, écriture d'un fichier), puis quatre opérations hors du dossier (écriture, lecture, Grep,
  Glob) **toutes refusées** (`permission_denials`). Une troisième conversation a vérifié qu'aucun shell n'est exposé.
  Identifiants remplacés, chemin de l'utilisateur remplacé (`C:\Users\joueur`), signatures retirées.
- `claude_stream_persistent.jsonl` (P06b, sonde 0.3 du 2026-10-10, dans l'accord des 48 conversations de mesure) :
  flux réel de `claude` 2.1.296 lancé une fois avec `--input-format stream-json` (ligne de la conversation « jeu »),
  deux messages écrits sur son entrée (« Quelle est la version des données ? Une ligne. », puis « Et la fraîcheur, en
  un mot ? ») : un événement `result` par message, même session ; premier résultat à 13,9 s (dont environ 6 s de hook
  de démarrage du plugin), second 1,4 s après son envoi ; `total_cost_usd` cumulé sur le processus. Identifiants
  remplacés.
