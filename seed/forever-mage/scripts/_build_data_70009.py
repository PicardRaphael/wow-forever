"""Générateur ponctuel des données du build 1.60.1.70009 (trace de provenance).
À relancer seulement pour reconstruire ce build ; les builds suivants passent par update_data.py."""
import json, os
S=os.path.join(os.path.dirname(__file__),'..','data','1.60.1.70009')
tree=json.load(open(f'{S}/_source_gunba_mage_tree.json'))
OVR={("Fire","Pyroblast"):[[95,125,44,12]],("Fire","Blast Wave"):[[148,178,50,6]],("Arcane","Arcane Blast"):[[50,58,10,175,4,8]],
     ("Frost","Ice Lance"):[[26,30,300]],("Frost","Ice Barrier"):[[431,1]]}
out={"build":"1.60.1.70009","class":"Mage","trees":[],"notes":[
 "Rangs complets : arbre wowsims Forever (gunba/wow-forever-sim, MIT), recoupé avec les rangs confirmés du client 1.60.1.69893 (ElliotWood/Forever).",
 "Corrigé au build 70009 (lecture client, ForeverChanges / WoW Forever Talents) : Pyroblast r1, Blast Wave r1, Arcane Blast r1, Ice Lance r1, Ice Barrier r1, durée de Hot Streak 20 s.",
 "Paliers : le palier n exige 5×(n-1) points dépensés dans le même arbre. Points disponibles = niveau - 9 (bonus Legacy 'Talented' non inclus)."]}
for tr in tree:
    T={"name":tr["name"],"talents":[]}
    for x in tr["talents"]:
        ranks=OVR.get((tr["name"],x["name"]),x["ranks"])
        e={"key":x["fieldName"],"name":x["name"],"tree":tr["name"],"tier":x["location"]["rowIdx"]+1,"col":x["location"]["colIdx"]+1,
           "max":x["maxPoints"],"ranks":ranks,"desc":x["description"],"spellIds":x.get("spellIds",[]),
           "prereq":({"tier":x["prereqLocation"]["rowIdx"]+1,"col":x["prereqLocation"]["colIdx"]+1} if x.get("prereqLocation") else None),
           "wowsims_not_simulated":bool(x.get("notSimulated")),
           "certainty":"FC-70009" if (tr["name"],x["name"]) in OVR else "FC-69893"}
        if x["name"]=="Hot Streak": e["duration_s"]=20
        T["talents"].append(e)
    out["trees"].append(T)
json.dump(out,open(f'{S}/talents.json','w'),ensure_ascii=False,indent=1)
# rangs : [niveau, min, max, dot_total, dot_duree, incantation_s, mana, recharge_s]
SP={
 "frostbolt":{"school":"frost","range":30,"slow":0.40,"slow_dur":[5,6,6,7,7,8,8,9,9,9,9],"binary":True,"projectile_speed":28,
   "ranks":[[4,20,22,0,0,1.5,25,0],[8,34,38,0,0,1.8,35,0],[14,47,52,0,0,2.2,50,0],[20,61,68,0,0,2.6,65,0],[26,96,106,0,0,3.0,100,0],
            [32,135,147,0,0,3.0,130,0],[38,181,197,0,0,3.0,160,0],[44,243,263,0,0,3.0,195,0],[50,305,331,0,0,3.0,225,0],[56,382,413,0,0,3.0,260,0],[60,457,493,0,0,3.0,290,0]]},
 "fireball":{"school":"fire","range":35,"projectile_speed":24,
   "ranks":[[1,16,25,2,4,1.5,30,0],[6,32,47,3,6,2.0,45,0],[12,48,66,6,6,2.5,65,0],[18,66,91,12,8,3.0,95,0],[24,97,131,16,8,3.5,140,0],[30,137,183,24,8,3.5,185,0],
            [36,170,223,24,8,3.5,220,0],[42,212,276,32,8,3.5,260,0],[48,270,349,40,8,3.5,305,0],[54,337,432,48,8,3.5,350,0],[60,397,505,56,8,3.5,395,0],[60,425,541,60,8,3.5,410,0]]},
 "fire_blast":{"school":"fire","range":20,"ranks":[[6,27,35,0,0,0,40,8],[14,56,70,0,0,0,75,8],[22,96,118,0,0,0,115,8],[30,156,188,0,0,0,165,8],[38,225,269,0,0,0,220,8],[46,315,373,0,0,0,280,8],[54,415,491,0,0,0,340,8]]},
 "scorch":{"school":"fire","range":30,"ranks":[[22,38,46,0,0,1.5,50,0],[28,53,65,0,0,1.5,65,0],[34,66,80,0,0,1.5,80,0],[40,89,107,0,0,1.5,100,0],[46,111,132,0,0,1.5,115,0],[52,142,170,0,0,1.5,135,0],[58,166,196,0,0,1.5,150,0]]},
 "pyroblast":{"school":"fire","range":35,"talent":"pyroblast","projectile_speed":24,
   "ranks":[[20,95,125,44,12,6.0,None,0],[24,125,164,56,12,6.0,150,0],[30,178,229,76,12,6.0,195,0],[36,228,291,100,12,6.0,240,0],[42,289,366,124,12,6.0,285,0],[48,365,459,152,12,6.0,335,0],[54,446,557,184,12,6.0,385,0],[60,520,646,212,12,6.0,440,0]]},
 "frostfire_bolt":{"school":"frostfire","range":35,"slow":0.40,"slow_dur":[9,9,9],"projectile_speed":28,
   "ranks":[[40,102,119,27,9,3.0,205,0],[50,181,211,39,9,3.0,285,0],[60,270,314,57,9,3.0,370,0]]},
 "ice_lance":{"school":"frost","range":30,"talent":"iceLance","frozen_mult":4.0,"projectile_speed":38,
   "ranks":[[20,26,30,0,0,0,None,0],[28,34,41,0,0,0,55,0],[34,44,52,0,0,0,70,0],[42,76,90,0,0,0,105,0],[48,95,112,0,0,0,120,0],[56,136,161,0,0,0,160,0]]},
 "arcane_blast":{"school":"arcane","range":30,"talent":"arcaneBlast","mana_pct_base":0.15,
   "ranks":[[20,50,58,0,0,2.5,None,0],[30,131,152,0,0,2.5,None,0],[40,168,196,0,0,2.5,None,0],[50,269,313,0,0,2.5,None,0],[60,364,424,0,0,2.5,None,0]]},
 "arcane_missiles":{"school":"arcane","range":30,"channel":True,
   "ranks":[[8,75,75,0,0,3.0,85,0],[16,132,132,0,0,4.0,140,0],[24,230,230,0,0,5.0,235,0],[32,340,340,0,0,5.0,320,0],[40,490,490,0,0,5.0,410,0],[48,665,665,0,0,5.0,500,0],[56,875,875,0,0,5.0,595,0],[56,1045,1045,0,0,5.0,655,0]]},
 "frost_nova":{"school":"frost","aoe":True,"freeze":8,"breaks_on_damage":"chance",
   "ranks":[[10,21,24,0,0,0,55,25],[26,34,39,0,0,0,85,25],[40,52,59,0,0,0,115,25],[54,71,80,0,0,0,145,25]]},
 "cone_of_cold":{"school":"frost","aoe":True,"slow":0.40,"slow_dur":[6,6,6,6,6],
   "ranks":[[26,96,106,0,0,0,210,10],[34,142,156,0,0,0,290,10],[42,200,220,0,0,0,380,10],[50,261,286,0,0,0,465,10],[58,328,358,0,0,0,555,10]]},
 "arcane_explosion":{"school":"arcane","aoe":True,"radius":10,
   "ranks":[[14,32,36,0,0,0,75,0],[22,55,61,0,0,0,120,0],[30,95,102,0,0,0,185,0],[38,134,145,0,0,0,250,0],[46,181,196,0,0,0,315,0],[54,239,258,0,0,0,390,0]]},
 "blizzard":{"school":"frost","aoe":True,"channel":True,
   "ranks":[[20,200,200,0,0,8.0,320,0],[28,344,344,0,0,8.0,520,0],[36,504,504,0,0,8.0,720,0],[44,712,712,0,0,8.0,935,0],[52,928,928,0,0,8.0,1160,0],[60,1168,1168,0,0,8.0,1400,0]]},
 "flamestrike":{"school":"fire","aoe":True,
   "ranks":[[16,55,71,44,8,3.0,195,0],[24,100,126,84,8,3.0,330,0],[32,158,198,132,8,3.0,490,0],[40,226,279,188,8,3.0,650,0],[48,298,367,256,8,3.0,815,0],[56,381,466,332,8,3.0,990,0]]},
 "blast_wave":{"school":"fire","aoe":True,"talent":"blastWave","daze":0.5,
   "ranks":[[36,148,178,0,0,0,None,45],[36,199,239,0,0,0,270,45],[44,276,327,0,0,0,355,45],[52,365,433,0,0,0,450,45],[60,453,533,0,0,0,545,45]]},
}
UTIL={
 "blink":{"level":20,"mana_pct_base":0.35,"cooldown":15,"note":"Libère des étourdissements et immobilisations (infobulle 70009). Lançable sous étourdissement : NON en Classic, à vérifier en jeu."},
 "evocation":{"level":20,"cooldown":480,"duration":8,"regen_mult":15.0},
 "counterspell":{"level":24,"mana":100,"cooldown":30,"lockout":10},
 "polymorph":{"ranks":[[8,20,60],[20,30,90],[40,40,120],[60,50,150]],"cast":1.5},
 "frost_armor":{"ranks":[[1,30,60],[10,110,110],[20,200,170]],"attacker_slow":0.30,"attacker_swing_slow":0.25,"dur":5},
 "ice_armor":{"ranks":[[30,290,240],[40,380,320],[50,470,410],[60,560,500]],"attacker_slow":0.30,"attacker_swing_slow":0.25},
 "mage_armor":{"ranks":[[34,5,270],[46,10,380],[58,15,490]],"regen_while_casting":0.50},
 "mana_shield":{"ranks":[[20,120,40],[28,210,60],[36,300,80],[44,390,100],[52,480,120],[60,570,140]],"mana_per_dmg":2},
 "ice_barrier":{"ranks":[[20,431,None],[46,561,360],[52,693,420],[58,819,480]],"cooldown":30,"no_pushback":True},
 "frost_ward":{"ranks":[[22,162,85],[32,284,135],[42,463,195],[52,668,255],[60,913,320]],"cooldown":30},
 "fire_ward":{"ranks":[[20,162,85],[30,285,135],[40,463,195],[50,668,255],[60,913,320]],"cooldown":30},
 "mana_gems":{"agate":[28,375,425],"jade":[38,550,650],"citrine":[48,775,925],"ruby":[58,1000,1200]},
 "arcane_intellect":{"ranks":[[1,2],[14,7],[28,15],[42,22],[56,31]]},
 "conjure_water":{"spell_levels":[4,10,20,30,40,50,60],"restore":[[151,18],[436,21],[835,24],[1344,27],[1992,30],[2934,30],[4200,30]],"certainty":"PC (valeurs Classic, non exposées par la source Forever)"},
 "conjure_food":{"spell_levels":[6,12,22,32,42,52,60],"restore":[[61,18],[243,21],[552,24],[874,27],[1392,30],[2148,30],[3180,30]],"certainty":"EST"},
}
json.dump({"build":"1.60.1.70009","source":"Client Forever 1.60.1.70009 via wowforevertalents.com/abilities/mage (lu le 26/09/2026)",
  "rank_format":["level","min","max","dot_total","dot_duration","cast_s","mana","cooldown_s"],
  "note":"mana None = coût non publié pour le rang issu d'un talent (à relever en jeu). Vitesses de projectile : EST.",
  "spells":SP,"utility":UTIL},open(f'{S}/spells.json','w'),ensure_ascii=False,indent=1)
print('talents:',sum(len(t["talents"]) for t in out["trees"]),'| sorts:',len(SP),'| rangs:',sum(len(v["ranks"]) for v in SP.values()))
