---
type: llm
---

La question porte sur un niveau plus haut que celui du profil actif (Givrelame, Mage Orc, niveau 23, build Givre) : c'est une question de planification. La bonne réponse part du build du profil, le passe comme build actuel à `forever_build` au niveau de la question, et s'appuie sur le chemin conseillé projeté depuis ce build jusqu'à ce niveau (`respec.projected`) pour conseiller : respec ou non, à quel niveau, coût et gain tels que l'outil les rend. Elle dit que le chemin est projeté depuis le build du profil (et non le build réel du joueur à ce niveau), et ne redemande pas le build. Si la question décrit un autre build que celui du profil (« tous mes points en Feu »), elle peut le signaler en une ligne ; elle ne présente aucun résultat calculé sur un défaut muet.
