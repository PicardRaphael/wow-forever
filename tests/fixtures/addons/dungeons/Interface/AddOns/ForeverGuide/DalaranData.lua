local _, ns = ...
ns.DQ[96986]={["n"]="Arcane Remnants",["lv"]=33,["rl"]=24,["fa"]="B",["new"]=true,["inside"]=true}
ns.DQ[96987]={["n"]="Lost Tomes",["lv"]=33,["rl"]=24,["fa"]="A",["new"]=true}
ns.DQ[544]={["n"]="Sewer Key",["lv"]=30,["rl"]=24,["fa"]="B",["nx"]=96986}
for _, d in ipairs(ns.DUNGEONS) do
    if d.key == "dalaran" then d.q = {96986,96987} end
end
