---
description: "profil vide : la donnée personnelle manquante est demandée avant tout calcul (règle « Données du joueur »)"
tags: [positif, profil]
max_turns: 20
timeout_seconds: 900
allowed_tools: [Skill, ToolSearch, Read, Glob, Grep]
env:
  EVAL_FOREVER_PROFILE: profil-vide-inexistant.json
---

Combien de temps pour tuer un monstre au niveau 18 en Givre ?
