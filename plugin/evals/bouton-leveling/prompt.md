---
description: "leveling, bouton Leveling de la fenêtre du jeu (contexte réel de la sonde F)"
tags: [positif, leveling]
max_turns: 20
timeout_seconds: 900
allowed_tools: [Skill, ToolSearch, Read, Glob, Grep]
---

Contexte du personnage (envoyé par le jeu) :
name=Jen
realm=Classic Beta PvE 2
level=19
class=MAGE
race=Orc
faction=Horde
zone=The Barrens
map=1413
talents=105778:5,105779:5
gear=3:1769:Canvas Shoulderpads;4:5107:Deckhand's Shirt;5:2582:Green Woolen Vest;6:253885:Novice Arcanist's Sash;7:3309:Barbaric Loincloth;8:14364:Mystic's Slippers;9:15452:Featherbead Bracers;10:10637:Brewer's Gloves;11:281268:Depleted Ritual Band;12:5351:Bounty Hunter's Ring;15:2580:Reinforced Linen Cape;16:15444:Staff of Orgrimmar;18:11288:Greater Magic Wand
client=1.60.1.70291
Talents actuels (clés de forever, pour `current` de forever_build) : elementalPrecision:5 (Elemental Precision 5/5), improvedFrostbolt:5 (Improved Frostbolt 5/5)
Équipement (noms du client ; objets pas encore reliés aux données de forever, comparaison d'objets à venir) : Canvas Shoulderpads, Deckhand's Shirt, Green Woolen Vest, Novice Arcanist's Sash, Barbaric Loincloth, Mystic's Slippers, Featherbead Bracers, Brewer's Gloves, Depleted Ritual Band, Bounty Hunter's Ring, Reinforced Linen Cape, Staff of Orgrimmar, Greater Magic Wand

Consigne du bouton « leveling » : appelle exactement, dans cet ordre :
- forever_lookup {"kind": "zones", "level": 19, "faction": "horde", "limit": 5}
- forever_build {"context": "leveling", "level": 20, "race": "Orc", "current": {"elementalPrecision": 5, "improvedFrostbolt": 5}, "sensitivity": false}
- forever_sim_leveling {"kind": "objectives", "level": 19, "class_name": "Mage", "faction": "horde", "race": "Orc"}
Puis :
- Zones et quêtes : les trois premières zones du résultat de zones, dans l'ordre rendu, avec leur nombre de quêtes utiles ; prochain donjon : le premier donjon rendu (`dungeons`).
- Prochain talent calculé, lu comme pour le bouton Talents (`respec.projected.steps`, chemin depuis ton niveau et ton build actuels) ; si `respec.versus_optimal.same` ou `respec.versus_optimal.tie` est vrai, tu gardes ton build (le build d'une respec, `respec.versus_optimal.optimal_rotation`, n'apporte aucun gain mesurable ; instable si `stability.stable` est faux).
- Objectifs (résultat de forever_sim_leveling, kind objectives) : rends `advice` tel quel, puis le meilleur objectif (`best` : nom, XP, minutes, XP par heure) et, s'il y a un donjon, son premier passage avec ses quêtes et ses passages suivants ; dis d'où vient le temps par monstre (`kill_time.source` : engine calculé, measured mesuré sur tes relevés, estimated estimé) et que les temps de trajet et de quête sont des hypothèses.

Question posée par le bouton « leveling » de la fenêtre :
Quel est mon prochain objectif de leveling ?
