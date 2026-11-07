# EC1a — Fiche de personnage par l'API Blizzard

Demande de l'utilisateur du 2026-11-07 : suivre son équipement par l'API Blizzard, depuis ses deux ordinateurs ;
accord donné pour le réseau, le commit et le push.

- Qui maintient déjà ça mieux que nous ? Blizzard (l'API) ; aucun addon installé ne publie l'équipement hors du jeu.
  On lit l'API telle quelle, par un adaptateur mince (`forever/pipeline/blizzard_api.py`).
- Que se passe-t-il au prochain patch ? Rien : l'API rend des identifiants d'objets et des textes affichés ; aucun
  chiffre de jeu recopié. Espace non documenté (`profile-forever-<région>`) : s'il change, la commande échoue en le
  disant (404 expliqué) et la sonde quotidienne le signale.

Fait : `forever api character <Nom-Surnom> [--region] [--locale] [--save] [--json]` ; écriture dans le profil sous la
source `api` (niveau, classe, équipement) ; décision 304 ; DATA_SOURCES (mode d'emploi d'un autre ordinateur) ;
LEG2 en partie répondue. Tests : `tests/unit/test_blizzard_character.py` (réseau simulé, réponses inventées).
Essai en jeu : se déconnecter (ou `/reload`), puis `uv run forever api character Rose-Krypto --save` : l'équipement
porté doit apparaître.
