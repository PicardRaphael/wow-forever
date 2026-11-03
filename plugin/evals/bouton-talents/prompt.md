---
description: "talent, bouton Talents de la fenêtre du jeu (contexte réel de la sonde F), build populaire de Talents Forever le plus proche, comme les autres classes (RB1)"
tags: [positif, talent]
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
Talents actuels (clés de forever, pour `current` de tf_popular) : elementalPrecision:5 (Elemental Precision 5/5), improvedFrostbolt:5 (Improved Frostbolt 5/5)
Équipement (noms du client ; objets pas encore reliés aux données de forever, comparaison d'objets à venir) : Canvas Shoulderpads, Deckhand's Shirt, Green Woolen Vest, Novice Arcanist's Sash, Barbaric Loincloth, Mystic's Slippers, Featherbead Bracers, Brewer's Gloves, Depleted Ritual Band, Bounty Hunter's Ring, Reinforced Linen Cape, Staff of Orgrimmar, Greater Magic Wand

Consigne du bouton « talents » : appelle exactement, dans cet ordre :
- forever_lookup {"kind": "tf_popular", "name": "Mage", "current": "elementalPrecision=5,improvedFrostbolt=5"}
- forever_lookup {"kind": "build_check", "name": "Mage", "level": 19, "talents": "elementalPrecision=5,improvedFrostbolt=5"}
- forever_lookup {"kind": "class_guide", "name": "Mage", "level": 19}
Puis :
- Donne `closest` tel quel (spécialisation, lien, commande `/tf import`, points absents `missing_points`, écarts `differences`), avec sa date (`asOf`) et sa certitude ; n'en choisis pas un autre.
- Guide de Forever Companion (`class_guide`), pour la spécialisation du build retenu ci-dessus : son build `pick` (nom ; légal à son niveau ou non) et les builds écartés avec leur raison (`set_aside`), puis la rotation telle quelle (`rotation.single`, puis `rotation.aoe`), en disant qu'elle vient de Forever Companion, qu'elle est écrite pour le niveau 30 et qu'aucun ordre de prise n'est calculé ; si `freshness.status` n'est pas « à jour », dis « calcul en cours de mise à jour » avec sa raison. Forever Companion absent : ne dis rien de plus.

Question posée par le bouton « talents » de la fenêtre :
Quel build populaire de Talents Forever est le plus proche de mes talents actuels ? Donne son lien Talents Forever.
