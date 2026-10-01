# Forever Bestiary (fixtures synthétiques, CH0)

- `ForeverBestiary/` : addon synthétique à la structure de Forever Bestiary 0.5.0 (`.toc`, `Data/Data.lua`,
  `Data/Community.lua`, `Data/Guide.lua`, un fichier de code). Bêtes, noms et valeurs inventés ; identifiants de
  PNJ repris de la fixture Questie (`tests/fixtures/questie/11.38.0`) pour le recoupement, plus deux identifiants
  inventés (990001 hors du continent, 990002 au-dessus du niveau) et une découverte de la carte (990003). Une
  famille inventée (`chimera-test`) absente du client ; le Crocilisk porte une armure qui diffère du client ;
  Bite rang 3 un niveau qui diffère du client. Aucune table de l'addon réel n'est recopiée (décision 133).
- `changed/ForeverBestiary/` : même version du `.toc`, une plage de niveau changée (statut `changé`).
- `ForeverBestiary.lua` : sauvegarde `ForeverBestiaryDB` (schéma 2) synthétique ; les champs de tiers (`peers`,
  `feed[].who`, `rp`, `petGuids`, `self*`, clés de `likes` et de `votes`) portent des valeurs inventées que le
  lecteur doit supprimer ; `PersoInvente` est un personnage inventé du joueur.
- Fins de ligne LF ; écrites une fois en CH0 (pas de script de régénération : ne modifier qu'avec la même structure).
