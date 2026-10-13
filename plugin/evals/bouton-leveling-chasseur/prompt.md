---
description: "leveling, bouton Leveling de la fenêtre du jeu pour une classe non calculée (contexte réel de Chasseur relevé le 2026-10-13)"
tags: [positif, leveling]
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

Consigne du bouton « leveling » : appelle exactement, dans cet ordre :
- forever_lookup {"kind": "zones", "level": 15, "faction": "horde", "limit": 5}
- forever_lookup {"kind": "tf_popular", "name": "Hunter", "current": "deadlyAspects=5,focusedFire=1"}
- forever_sim_leveling {"kind": "objectives", "level": 15, "class_name": "Hunter", "faction": "horde", "race": "Orc"}
Puis :
- Zones et quêtes : les trois premières zones du résultat de zones, dans l'ordre rendu, avec leur nombre de quêtes utiles ; prochain donjon : le premier donjon rendu (`dungeons`).
- Build populaire de ta classe : `closest` s'il est rendu (le plus proche de tes talents), sinon le build le plus joué ; son lien et sa commande `/tf import` tels quels, sa date (`asOf`).
- Objectifs (résultat de forever_sim_leveling, kind objectives) : rends `advice` tel quel, puis le meilleur objectif (`best` : nom, XP, minutes, XP par heure) et, s'il y a un donjon, son premier passage avec ses quêtes et ses passages suivants ; dis d'où vient le temps par monstre (`kill_time.source` : engine calculé, measured mesuré sur tes relevés, estimated estimé) et que les temps de trajet et de quête sont des hypothèses.
- Dis clairement ce qui est calculé et ce qui ne l'est pas encore : zones, quêtes, donjon et XP par heure viennent des données et de tes relevés ; le build est un choix de joueurs ; le prochain talent n'est pas encore calculé pour ta classe.

Question posée par le bouton « leveling » de la fenêtre :
Quel est mon prochain objectif de leveling ?
