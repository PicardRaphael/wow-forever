---
description: "talents, bouton Talents de la fenêtre du jeu pour un Chasseur (contexte réel relevé le 2026-10-13, talents placés)"
tags: [positif, talent]
max_turns: 20
timeout_seconds: 900
allowed_tools: [Skill, ToolSearch, Read, Glob, Grep]
---

Contexte du personnage (envoyé par le jeu) :
name=Mydream
realm=Classic Beta PvE 2
level=15
class=HUNTER
race=Orc
faction=Horde
zone=The Barrens
subzone=The Merchant Coast
map=1413
talents=104960:5,104975:1
gear=4=127::::::::15:1485::75=Trapper's Shirt;5=5957:15:::::::15:1485::::::::Player-0000-00000001=Handstitched Leather Vest;6=14113::::::::15:1485:::1:12718=Aboriginal Sash of the Eagle;7=1507::::::::15:1485::1::1:28:5244=Warped Leather Pants;8=4942::::::::15:1485::11=Tiger Hide Boots;9=15453::::::::15:1485::11=Savannah Bracers;10=15300:15:::::::15:1485::1::1:28:5244=Grizzly Gloves;11=281268::::::::15:1485::11=Depleted Ritual Band;15=14365::::::::15:1485::1::1:28:5244=Mystic's Cape;16=2632::::::::15:1485::1:1:12721:1:28:5244=Curved Dagger of the Monkey;18=3036::::::::15:1485=Heavy Shortbow
client=1.60.1.70338
Talents actuels (clés de forever, pour `current` de forever_build) : deadlyAspects:5 (Deadly Aspects 5/5), focusedFire:1 (Focused Fire 1/2)
Équipement (noms du client ; objets pas encore reliés aux données de forever, comparaison d'objets à venir) : Trapper's Shirt, Handstitched Leather Vest (enchantement 15), Aboriginal Sash of the Eagle, Warped Leather Pants, Tiger Hide Boots, Savannah Bracers, Grizzly Gloves (enchantement 15), Depleted Ritual Band, Mystic's Cape, Curved Dagger of the Monkey, Heavy Shortbow

Consigne du bouton « talents » : appelle exactement, dans cet ordre :
- forever_lookup {"kind": "tf_popular", "name": "Hunter", "current": "deadlyAspects=5,focusedFire=1"}
- forever_lookup {"kind": "build_check", "name": "Hunter", "level": 15, "talents": "deadlyAspects=5,focusedFire=1"}
- forever_lookup {"kind": "class_guide", "name": "Hunter", "level": 15}
Puis :
- Donne `closest` tel quel (spécialisation, lien, commande `/tf import`, points absents `missing_points`, écarts `differences`), avec sa date (`asOf`) et sa certitude ; n'en choisis pas un autre.
- Guide de Forever Companion (`class_guide`), pour la spécialisation du build retenu ci-dessus : son build `pick` (nom ; légal à son niveau ou non) et les builds écartés avec leur raison (`set_aside`), puis la rotation telle quelle (`rotation.single`, puis `rotation.aoe`), en disant qu'elle vient de Forever Companion, qu'elle est écrite pour le niveau 30 et qu'aucun ordre de prise n'est calculé pour ta classe ; si `freshness.status` n'est pas « à jour », dis « calcul en cours de mise à jour » avec sa raison. Forever Companion absent : ne dis rien de plus.

Question posée par le bouton « talents » de la fenêtre :
Quel build populaire de Talents Forever est le plus proche de mes talents actuels ? Donne son lien Talents Forever.
