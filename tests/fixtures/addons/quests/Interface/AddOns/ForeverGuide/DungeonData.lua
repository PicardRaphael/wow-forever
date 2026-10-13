local _, ns = ...

ns.DUNGEONS = {
  {key="rfc",slug="ragefire-chasm",en="Ragefire Chasm",ru="Огненная пропасть",min=13,max=18,loc="Оргриммар",loce="Orgrimmar",q={5723,5728,5724,5761,5725,5722},map=1454,x=52.6,y=49},
  {key="thanes",slug="hall-of-thanes",en="Hall of Thanes",ru="Hall of Thanes · Чертог танов",min=13,max=18,loc="Под Стальгорном, Дун Морог",loce="Beneath Ironforge, Dun Morogh",new=true,q={96395,96403,96393,96394,98423,96391},map=1455,x=31.8,y=46.4},
}
ns.DQ = {
  [5723]={n="Testing an Enemy's Strength",r="Испытание силы врага",lv=15,rl=9,fa="H",s={11833},f={11833},z=2437,o="Найдите в Оргриммаре Огненную пропасть, убейте 8 троггов и 8 шаманов Огненной пропасти и возвращайтесь к Рахауро в Громовой Утес.",oe="Search Orgrimmar for Ragefire Chasm, then kill 8 Ragefire Troggs and 8 Ragefire Shaman before returning to Rahauro in Thunder Bluff.",rw={m=700,rep={81}}},
  [5728]={n="Hidden Enemies",r="Тайные враги",lv=16,rl=9,fa="H",s={4949},f={4949},ps={5727},z=2437,o="Убейте Баззалана и Жергоша Призывателя Духов и вернитесь в Оргриммар к Траллу.",oe="Kill Bazzalan and Jergosh the Invoker before returning to Thrall in Orgrimmar.",rw={m=800,rep={76}},nx=5729},
  [5724]={n="Returning the Lost Satchel",r="Возвращение потерянной сумки",lv=16,rl=9,fa="H",s={11834},f={11833},ps={5722},z=2437,o="Отнесите сумку Маура Зловещего Тотема Рахауро в Громовой Утес.",oe="Take the Grimtotem Satchel to Rahauro in Thunder Bluff.",rw={c={{15452,1},{15453,1},{270003,1}},rep={81},fv=true}},
  [5722]={n="Searching for the Lost Satchel",r="В поисках потерянного ранца",lv=16,rl=9,fa="H",s={11833},f={11834},z=2437,o="Обыщите Огненную пропасть в поисках тела Маура Зловещего Тотема и найдите все необычные предметы.",oe="Search Ragefire Chasm for Maur Grimtotem's corpse and search it for any items of interest.",nx=5724},
  [5761]={n="Slaying the Beast",r="Убить тварь",lv=16,rl=9,fa="H",s={3216},f={3216},z=2437,o="Спуститесь в Огненную пропасть, убейте Тарагамана Ненасытного и принесите его сердце Нииру Огненному Клинку в Оргриммаре.",oe="Enter Ragefire Chasm and slay Taragaman the Hungerer, then bring his heart back to Neeru Fireblade in Orgrimmar.",rw={m=800}},
  [5725]={n="The Power to Destroy...",r="Силы разрушения...",lv=16,rl=9,fa="H",s={2425},f={2425},z=2437,o="Принесите книги \"Заклинания Тьмы\" и \"Заклятия Пустоты\" Вариматрасу в Подгород.",oe="Bring the books Spells of Shadow and Incantations from the Nether to Varimathras in Undercity.",rw={c={{15449,1},{15450,1},{15451,1}},rep={68},fv=true}},
  [96395]={n="An Ancient Grudge",lv=15,rl=10,g="Ghostly Attendant",inside=true,new=true,rw={c={{279899,1},{279900,1}},fv=true}},
  [96403]={n="Important Heirlooms",lv=15,rl=10,g="Thom Filch",gz=1455,e="Thom Filch",new=true,rw={c={{279898,1},{280096,1}},rep={369},fv=true},gxy={1455,32.6,44.6},exy={1455,32.6,44.6}},
}
ns.DNPC = {
  [2425]={n="Varimathras",r="Вариматрас",sp={{1458,56.2,92.2,nil}},fr="H"},
  [3216]={n="Neeru Fireblade",r="Нииру Огненный Клинок",sp={{1454,49.5,50.6,nil}},fr="H"},
  [4949]={n="Thrall",r="Тралл",sp={{1454,31.7,37.8,nil}},fr="H"},
  [11833]={n="Rahauro",r="Рахауро",sp={{1456,70.1,29.5,nil}},fr="H"},
  [11834]={n="Maur Grimtotem",r="Маур Зловещий Тотем",sp={{1454,52.6,49,2437}},fr="AH"},
}
