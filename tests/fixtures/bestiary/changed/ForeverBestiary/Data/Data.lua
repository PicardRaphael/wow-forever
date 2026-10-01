-- Forever Bestiary : base synthétique pour les tests, second état (taille différente) (structure de Data/Data.lua 0.5.0, bêtes et noms inventés).
local _, ns = ...
ns.Data = {
  date = "2026-09-25",
  clientBuild = "1.60.1.69913",
  familyOrder = {"bat", "chimera-test", "crocolisk", "wolf"},
  families = {
    bat = {
      en = "Bat",
      es = "Murcielago de prueba",
      icon = "Ability_Hunter_Pet_Bat",
      dmg = 7,
      armor = 0,
      hp = 0,
      diet = {"Fungus", "Fruit"},
      abil = {
        {n="Dive", from=2},
        {n="Bite"},
      },
    },
    ["chimera-test"] = {
      en = "Chimera Test",
      es = "Quimera de prueba",
      dmg = 3,
      armor = 3,
      hp = 3,
      diet = {"Meat"},
      renamed = "Old Chimera",
      abil = {
        {n="Bite"},
      },
    },
    crocolisk = {
      en = "Crocolisk",
      es = "Crocolisco de prueba",
      dmg = 0,
      armor = 99,
      hp = -5,
      diet = {"Meat", "Fish"},
      abil = {
        {n="Bite"},
        {n="Dash"},
      },
    },
    wolf = {
      en = "Wolf",
      es = "Lobo de prueba",
      dmg = 0,
      armor = 5,
      hp = 0,
      diet = {"Meat"},
      fastest = {s=1.2, n="Loup Rapide d'essai", l=20},
      abil = {
        {n="Furious Howl"},
        {n="Bite"},
        {n="Dash"},
      },
    },
  },
  abilities = {
    Bite = {
      kind = "common",
      focus = 35,
      cd = 10,
      fams = {"bat", "chimera-test", "crocolisk", "wolf"},
      ranks = {
        {r=1, l=1, en="Bite rank one (fixture).", es="Mordisco uno."},
        {r=2, l=8, en="Bite rank two (fixture).", es="Mordisco dos."},
        {r=3, l=17, en="Bite rank three (fixture).", es="Mordisco tres."},
      },
      taught = {[1]=3, [2]=1, [3]=2},
    },
    Dash = {
      kind = "common",
      focus = 20,
      fams = {"crocolisk", "wolf"},
      ranks = {
        {r=1, l=30, en="Dash rank one (fixture)."},
      },
    },
    ["Slower Attack"] = {
      kind = "passive",
      fams = {},
      ranks = {
        {r=2, l=nil, en="Slower (fixture).", spd=2.5, pct=-20},
      },
    },
    Growl = {kind="general", fams={}, ranks={}},
  },
  zonesES = {
    Durotar = "Durotar de prueba",
    ["The Barrens"] = "Los Baldios de prueba",
    ["Elwynn Forest"] = "Bosque de prueba",
  },
}
ns.Data.beasts = {
  {
    id = 3425,
    en = "Prowler of the Test",
    es = "Merodeador de prueba",
    f = "wolf",
    l1 = 15,
    l2 = 16,
    r = "n",
    s = 2,
    t = {
      {"Bite", 3, "c"},
      {"Dash", 1, "p"},
    },
    z = {
      {z="The Barrens"},
    },
    c = {
      ["The Barrens"] = {
        {40.5, 60.2},
        {41.1, 61.7},
      },
    },
    cf = "beta",
    src = "bm+fc",
  },
  {
    id = 3244,
    en = "Strider of the Test",
    f = "wolf",
    l1 = 9,
    l2 = 10,
    r = "n",
    s = 2,
    t = {
      {"Bite", 2, "b"},
    },
    z = {
      {z="The Barrens"},
    },
    cf = "classic",
    src = "bm",
  },
  {
    id = 3099,
    en = "Boar of the Test",
    f = "crocolisk",
    l1 = 6,
    l2 = 7,
    r = "n",
    s = 2,
    t = {
      {"Bite", 3, "p"},
    },
    z = {
      {z="Durotar"},
    },
    c = {
      Durotar = {
        {50.1, 50.2},
      },
    },
    cf = "datos",
    src = "fc",
  },
  {
    id = 990001,
    en = "Faraway Beast of the Test",
    f = "wolf",
    l1 = 10,
    l2 = 12,
    r = "n",
    s = 2,
    t = {
      {"Bite", 3, "c"},
    },
    z = {
      {z="Elwynn Forest"},
    },
    cf = "classic",
    src = "bm",
  },
  {
    id = 990002,
    en = "High Beast of the Test",
    f = "wolf",
    l1 = 25,
    l2 = 26,
    r = "r",
    s = 1.6,
    t = {
      {"Bite", 3, "c"},
    },
    z = {
      {z="The Barrens"},
    },
    colEN = {"Other Name of the Test"},
    cf = "classic",
    src = "bm",
  },
}
