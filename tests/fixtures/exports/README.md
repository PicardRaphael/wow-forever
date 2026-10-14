# Exports d'EX1 (fixtures)

- `naowh_keys.json` : noms de format de Naowh Forever 1.1.12 (clés de spécialisation, de statistiques, emplacements
  d'une liste BiS), relevés en local le 2026-10-14 ; noms d'un addon, pas des valeurs du jeu.
- `ellesmere_base.lua` : sauvegarde EllesmereUI **synthétique** (forme relevée dans EllesmereUI 9.5.4) : deux profils,
  sorts du gestionnaire de recharges par clé de spécialisation (clés 9001 et 9002 inventées), clé gardée par
  personnage (`lastSpecByChar`), rappels de buffs ; identifiants de sorts repris de `classes.json` (1.60.1.70374) et
  cités en tête du fichier, le reste inventé. Jamais copiée depuis la sauvegarde réelle du joueur.
- `roles.json` : rôles tenus par chaque classe, repris de `docs/SPEC.md` (section « Classes, spécialisations et
  rôles »).
