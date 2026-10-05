# Dispositions dérivées de WoWDBDefs (T08c, bloc B)

- `layouts-1.60.1.70170.json` : pour chaque table présente dans `tests/fixtures/hotfix/DBCache.bin` et lue par le
  projet, le bloc de disposition qui nomme le build 1.60.1.70170 dans les définitions de WoWDBDefs
  (<https://github.com/wowdev/WoWDBDefs>, commit `1d356b44c798e89802928457b2854003098e28ab`, relevé du 2026-10-05
  par `uv run forever fetch --version 1.60.1.70170 --dbd`, accord de l'utilisateur au moment de l'accès) : nom,
  type, taille, signe, tableau, annotations et table référencée de chaque champ, dans l'ordre des octets.
- **Structure seulement, aucun texte du dépôt** : le fichier `LICENSE` du dépôt est introuvable à ce commit (réponse
  404), la licence n'est donc pas établie ; seules ces dispositions dérivées sont gardées (plan T08c, bloc B, étape 2).
- Écrit par `uv run python scripts/extract_dbd_layouts.py` depuis le cache (`<cache>/dbd/<commit>/`) ; ne pas éditer
  à la main.
