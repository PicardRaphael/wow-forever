---
description: "pvp, bouton PvP de la fenêtre du jeu (contexte réel de la sonde F, cible Chaman)"
tags: [positif, pvp]
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
target=SHAMAN
target_level=21
target_race=Tauren
client=1.60.1.70291
Talents actuels (clés de forever, pour `current` de forever_build) : elementalPrecision:5 (Elemental Precision 5/5), improvedFrostbolt:5 (Improved Frostbolt 5/5)
Cible (joueur) : Shaman, niveau 21, race Tauren
Équipement (noms du client ; objets pas encore reliés aux données, table d'objets prévue en T10a) : Canvas Shoulderpads, Deckhand's Shirt, Green Woolen Vest, Novice Arcanist's Sash, Barbaric Loincloth, Mystic's Slippers, Featherbead Bracers, Brewer's Gloves, Depleted Ritual Band, Bounty Hunter's Ring, Reinforced Linen Cape, Staff of Orgrimmar, Greater Magic Wand

Consigne du bouton « pvp » : appelle exactement, dans cet ordre :
- forever_lookup {"kind": "pvp", "name": "Mage", "level": 19, "race": "Orc", "talents": "elementalPrecision=5,improvedFrostbolt=5", "opponent": "Shaman", "opponent_level": 21}
Puis :
- Fiche de Shaman face à ton personnage : menaces (`threats`), tes réponses (`answers`), leurs réponses (`their_answers`), fenêtres (`windows`) ; cite ce qui manque (`missing`).

Question posée par le bouton « pvp » de la fenêtre :
Fiche de la classe de ma cible
