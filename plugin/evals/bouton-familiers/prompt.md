---
description: "familiers, bouton Familiers de la fenêtre du jeu (contexte de Chasseur construit : aucun relevé en jeu)"
tags: [positif, familiers]
max_turns: 20
timeout_seconds: 900
allowed_tools: [Skill, ToolSearch, Read, Glob, Grep]
---

Contexte du personnage (envoyé par le jeu) :
name=Jen
realm=Classic Beta PvE 2
level=19
class=HUNTER
race=Orc
faction=Horde
zone=The Barrens
map=1413
client=1.60.1.70291

Consigne du bouton « pets » : appelle exactement, dans cet ordre :
- forever_lookup {"kind": "pets", "zone": "The Barrens", "level": 19}
Puis :
- Donne le rang le plus haut atteignable et la bête qui l'enseigne la plus proche (zone, coordonnées et date tels que rendus).

Question posée par le bouton « pets » de la fenêtre :
Où apprivoiser le prochain rang utile près de moi ?
