---
description: "talent, bouton Talents de la fenêtre du jeu (contexte réel de la sonde F), prochain point au niveau suivant"
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
Talents actuels (clés de forever, pour `current` de forever_build) : elementalPrecision:5 (Elemental Precision 5/5), improvedFrostbolt:5 (Improved Frostbolt 5/5)
Équipement (noms du client ; objets pas encore reliés aux données, table d'objets prévue en T10a) : Canvas Shoulderpads, Deckhand's Shirt, Green Woolen Vest, Novice Arcanist's Sash, Barbaric Loincloth, Mystic's Slippers, Featherbead Bracers, Brewer's Gloves, Depleted Ritual Band, Bounty Hunter's Ring, Reinforced Linen Cape, Staff of Orgrimmar, Greater Magic Wand

Consigne du bouton « talents » : appelle exactement, dans cet ordre :
- forever_build {"context": "leveling", "level": 20, "race": "Orc", "current": {"elementalPrecision": 5, "improvedFrostbolt": 5}, "sensitivity": false}
Puis :
- Prochain point, en premier : le talent du premier pas de `respec.projected.steps` et son niveau (un pas à un niveau inférieur ou égal à 19 est un point à placer dès maintenant).
- Égalité : si `next_step.decided_by` vaut `non_departage` ou `modelise`, dis que le choix est à égalité statistique (non départagé par le calcul) et nomme `next_step.runner_up` et les autres candidats dont l'écart (`next_step.candidates[].gap.significant`) n'est pas significatif.
- Lien Talents Forever : celui de `respec.projected.export` (build actuel plus ce point), tel quel.
- Build, en complément, après le prochain point : si `respec.versus_optimal.same` est vrai, dis que ton build actuel est la recommandation (départage final au Monte Carlo) et que tu le gardes ; si `respec.versus_optimal.tie` est vrai, dis que ton build actuel et le build optimal (`choices.leveling.rotation`) sont à égalité statistique et que tu gardes ton build (aucun gain mesurable) ; si `stability.stable` est faux, ajoute que le build optimal lui-même est instable (il change avec la graine). Si `respec.versus_optimal.current_better` est vrai, dis que ton build actuel est meilleur que le build retenu par l'optimiseur (écart mesuré, `respec.versus_optimal`) et que tu le gardes. Sinon, donne l'écart (`respec.versus_optimal`) et le conseil de respec (`respec.verdict`).

Question posée par le bouton « talents » de la fenêtre :
Quel est mon prochain talent, avec le lien Talents Forever ?
