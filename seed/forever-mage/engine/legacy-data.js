/* ===== Données WoW Forever — passes 1 à 4 (23/09/2026, build 1.60.1.69977) =====
   Tags : FC = confirmé Forever (client/tooltip) · FS = source sim · PC = proxy Classic · EST = estimation */
const DATA = (function () {
  const TAGS = {
    FC: { label: 'confirmé Forever', cls: 'fc' },
    FS: { label: 'source sim', cls: 'fs' },
    PC: { label: 'proxy Classic', cls: 'pc' },
    EST: { label: 'estimation', cls: 'est' }
  };

  // [id, valeur, tag, libellé, groupe]
  const P = [
    // --- Constantes de combat
    ['k.h0_0', 0.96, 'PC', 'Toucher de base, cible même niveau', 'Constantes'],
    ['k.h0_1', 0.95, 'PC', 'Toucher de base, cible +1', 'Constantes'],
    ['k.h0_2', 0.94, 'PC', 'Toucher de base, cible +2', 'Constantes'],
    ['k.h0_3', 0.83, 'PC', 'Toucher de base, cible +3 (boss)', 'Constantes'],
    ['k.hitcap', 0.99, 'PC', 'Plafond de toucher', 'Constantes'],
    ['k.resPerLvl', 0.0125, 'PC', 'Résistance moyenne par niveau d’écart', 'Constantes'],
    ['k.critBase', 0.5, 'FS', 'Bonus de critique des sorts (base)', 'Constantes'],
    ['k.healCrit', 0.5, 'PC', 'Bonus de critique des soins', 'Constantes'],
    ['k.dotCrit', 1, 'FS', 'Les DoT peuvent critiquer (1 = oui, 0 = non)', 'Constantes'],
    ['k.gcd', 1.5, 'PC', 'Temps de recharge global (s)', 'Constantes'],
    ['k.manaPerInt', 15, 'FS', 'Mana par point d’Intelligence', 'Constantes'],
    ['k.armorK', 7285, 'PC', 'Constante d’armure contre un boss niveau 63', 'Constantes'],
    ['k.potCd', 120, 'FC', 'Recharge partagée des potions (s)', 'Constantes'],
    ['k.ipc.mage', 59.5, 'PC', 'Mage : Intelligence pour 1 % de crit', 'Constantes'],
    ['k.ipc.priest', 59.5, 'PC', 'Prêtre : Intelligence pour 1 % de crit', 'Constantes'],
    ['k.ipc.warlock', 60.6, 'PC', 'Démoniste : Intelligence pour 1 % de crit', 'Constantes'],
    ['k.ipc.paladin', 29.5, 'PC', 'Paladin : Intelligence pour 1 % de crit (conflit : 54–60 selon warcrafttavern)', 'Constantes'],
    ['k.bc.mage', 0.2, 'PC', 'Mage : crit de base (%)', 'Constantes'],
    ['k.bc.priest', 0.8, 'PC', 'Prêtre : crit de base (%)', 'Constantes'],
    ['k.bc.warlock', 1.7, 'PC', 'Démoniste : crit de base (%)', 'Constantes'],
    ['k.bc.paladin', 0, 'PC', 'Paladin : crit de base (%)', 'Constantes'],
    ['k.bm.mage', 1213, 'EST', 'Mage : mana de base niveau 60', 'Constantes'],
    ['k.bm.priest', 1436, 'EST', 'Prêtre : mana de base niveau 60', 'Constantes'],
    ['k.bm.warlock', 1373, 'EST', 'Démoniste : mana de base niveau 60', 'Constantes'],
    ['k.bm.paladin', 1512, 'EST', 'Paladin : mana de base niveau 60', 'Constantes'],
    ['k.wand', 59.6, 'FC', 'DPS de baguette pendant les phases sans mana (Brilliant Wand)', 'Constantes'],
    ['mage.evoc', 0.60, 'PC', 'Évocation : part du mana max rendue', 'Mage (commun)'],
    ['mage.evocCd', 480, 'PC', 'Évocation : recharge (s)', 'Mage (commun)'],
    ['mage.evocDur', 8, 'PC', 'Évocation : canalisation (s)', 'Mage (commun)'],
    ['mage.gem', 1100, 'PC', 'Gemme de mana (Mana Ruby) : mana moyen', 'Mage (commun)'],
    ['mage.gemCd', 120, 'PC', 'Gemme de mana : recharge (s)', 'Mage (commun)'],
    ['k.sr.mage.a', 12.5, 'FS', 'Mage : regen par tick, constante', 'Constantes'],
    ['k.sr.mage.d', 4, 'FS', 'Mage : regen par tick, diviseur d’Esprit', 'Constantes'],
    ['k.sr.priest.a', 13, 'PC', 'Prêtre : regen par tick, constante', 'Constantes'],
    ['k.sr.priest.d', 4, 'PC', 'Prêtre : regen par tick, diviseur d’Esprit', 'Constantes'],
    ['k.sr.warlock.a', 8, 'PC', 'Démoniste : regen par tick, constante', 'Constantes'],
    ['k.sr.warlock.d', 4, 'PC', 'Démoniste : regen par tick, diviseur d’Esprit', 'Constantes'],
    ['k.sr.paladin.a', 15, 'PC', 'Paladin : regen par tick, constante', 'Constantes'],
    ['k.sr.paladin.d', 5, 'PC', 'Paladin : regen par tick, diviseur d’Esprit', 'Constantes'],

    // --- Buffs de raid (wowsims/forever #36, build 69913)
    ['b.ai.int', 31, 'FS', 'Intelligence des Arcanes : Intelligence', 'Buffs'],
    ['b.ds.spi', 40, 'FS', 'Esprit divin : Esprit', 'Buffs'],
    ['b.fort.sta', 70, 'FS', 'Robustesse : Endurance', 'Buffs'],
    ['b.gotw.stats', 16, 'FS', 'Don du fauve : toutes les stats', 'Buffs'],
    ['b.gotw.armor', 385, 'FS', 'Don du fauve : armure', 'Buffs'],
    ['b.kings.pct', 0.10, 'FS', 'Bénédiction des rois : stats (%)', 'Buffs'],
    ['b.wisdom.mp5', 40, 'FS', 'Bénédiction de sagesse : mp5', 'Buffs'],
    ['b.spring.mp5', 25, 'FS', 'Totem Fontaine de mana : mp5', 'Buffs'],
    ['b.moonkin.crit', 3, 'FS', 'Aura de sélénien : crit des sorts (%)', 'Buffs'],
    ['b.pi.pct', 0.20, 'FS', 'Infusion de puissance : dégâts et soins', 'Buffs'],
    ['b.pi.dur', 15, 'FS', 'Infusion de puissance : durée (s)', 'Buffs'],
    ['b.pi.cd', 180, 'PC', 'Infusion de puissance : recharge (s)', 'Buffs'],
    ['b.coe.pct', 0.10, 'FS', 'Malédiction des éléments : dégâts subis', 'Buffs'],
    ['b.devotion.armor', 735, 'FS', 'Aura de dévotion : armure', 'Buffs'],

    // --- Buffs de monde (valeurs Classic ; monde ouvert seulement, PROBABLE)
    ['w.rally.crit', 10, 'PC', 'Cri de ralliement du tueur de dragon : crit (%)', 'Buffs de monde'],
    ['w.song.stats', 15, 'PC', 'Sérénade de Chantefleur : toutes les stats', 'Buffs de monde'],
    ['w.song.crit', 5, 'PC', 'Sérénade de Chantefleur : crit (%)', 'Buffs de monde'],
    ['w.warchief.mp5', 10, 'PC', 'Bénédiction du chef de guerre : mp5', 'Buffs de monde'],
    ['w.zand.pct', 0.15, 'PC', 'Esprit de Zandalar : stats (%)', 'Buffs de monde'],
    ['w.slip.crit', 3, 'PC', 'Slip’kik’s Savvy : crit des sorts (%)', 'Buffs de monde'],
    ['w.sayge.pct', 0.10, 'PC', 'Sombre fortune de Sayge : dégâts (%)', 'Buffs de monde'],

    // --- Consommables
    ['c.flask_sp', 150, 'PC', 'Flask of Supreme Power : puissance des sorts', 'Consommables'],
    ['c.flask_wis', 2000, 'PC', 'Flask of Distilled Wisdom : mana max', 'Consommables'],
    ['c.flask_titans', 400, 'PC', 'Flask of the Titans : points de vie', 'Consommables'],
    ['c.owl.int', 25, 'FC', 'Elixir of the Owl : Intelligence', 'Consommables'],
    ['c.owl.crit', 2, 'FC', 'Elixir of the Owl : crit (%)', 'Consommables'],
    ['c.sages.spi', 25, 'FC', 'Elixir of Sages : Esprit', 'Consommables'],
    ['c.sages.crit', 2, 'FC', 'Elixir of Sages : crit (%)', 'Consommables'],
    ['c.cleric', 40, 'FC', 'Greater Cleric’s Elixir : soins', 'Consommables'],
    ['c.arcane_l', 15, 'FC', 'Lesser Arcane Elixir : puissance des sorts', 'Consommables'],
    ['c.gae', 35, 'PC', 'Greater Arcane Elixir : puissance des sorts', 'Consommables'],
    ['c.mageblood_g', 20, 'FC', 'Greater Mageblood Elixir : mp5', 'Consommables'],
    ['c.mageblood', 12, 'PC', 'Mageblood (Classic) : mp5', 'Consommables'],
    ['c.wicked', 10, 'FC', 'Elixir of Wicked Regeneration : mp5', 'Consommables'],
    ['c.spirit_g', 18, 'FC', 'Elixir of Greater Spirit : Esprit', 'Consommables'],
    ['c.cunning', 25, 'FC', 'Elixir of Cunning : Intelligence', 'Consommables'],
    ['c.int_g', 25, 'PC', 'Elixir of Greater Intellect : Intelligence', 'Consommables'],
    ['c.shadowp', 40, 'PC', 'Elixir of Shadow Power : dégâts Ombre', 'Consommables'],
    ['c.firep', 40, 'PC', 'Elixir of Greater Firepower : dégâts Feu', 'Consommables'],
    ['c.frostp', 15, 'PC', 'Elixir of Frost Power : dégâts Givre', 'Consommables'],
    ['c.phalanx.hp', 400, 'FC', 'Elixir of the Phalanx : points de vie', 'Consommables'],
    ['c.phalanx.armor', 500, 'FC', 'Elixir of the Phalanx : armure', 'Consommables'],
    ['c.defsup', 450, 'PC', 'Elixir of Superior Defense : armure', 'Consommables'],
    ['c.spellblast', 40, 'FC', 'Major Spellblasting Potion : puissance des sorts', 'Consommables'],
    ['c.spellblast.dur', 30, 'FC', 'Major Spellblasting Potion : durée (s)', 'Consommables'],
    ['c.manapot', 1800, 'PC', 'Major Mana Potion : mana moyen (1 350–2 250)', 'Consommables'],
    ['c.mender', 75, 'FC', 'Major Mender’s Potion : soins', 'Consommables'],
    ['c.mender.dur', 30, 'FC', 'Major Mender’s Potion : durée (s)', 'Consommables'],
    ['c.rune', 1200, 'PC', 'Demonic Rune : mana moyen (900–1 500)', 'Consommables'],
    ['c.rune.cd', 120, 'PC', 'Demonic Rune : recharge (s)', 'Consommables'],
    ['c.bwo.sp', 36, 'FC', 'Brilliant Wizard Oil : dégâts et soins', 'Consommables'],
    ['c.bwo.crit', 1, 'FC', 'Brilliant Wizard Oil : crit (%)', 'Consommables'],
    ['c.wo.sp', 30, 'FC', 'Wizard Oil : dégâts et soins', 'Consommables'],
    ['c.bmo.mp5', 12, 'PC', 'Brilliant Mana Oil : mp5', 'Consommables'],
    ['c.bmo.heal', 25, 'PC', 'Brilliant Mana Oil : soins', 'Consommables'],
    ['c.bat', 20, 'FC', 'Bat Hachee : Intelligence', 'Consommables'],
    ['c.smoothie', 20, 'FC', 'Wicked Smoothie : Esprit', 'Consommables'],
    ['c.runn', 10, 'PC', 'Runn Tum Tuber Surprise : Intelligence', 'Consommables'],
    ['c.nightfin', 8, 'PC', 'Nightfin Soup : mp5', 'Consommables'],
    ['c.sagefish', 6, 'PC', 'Sagefish Delight : mp5', 'Consommables'],
    ['c.egg', 6, 'PC', 'Herb Baked Egg : Esprit', 'Consommables'],
    ['c.scrollint', 16, 'PC', 'Scroll of Intellect IV : Intelligence', 'Consommables'],
    ['c.scrollspi', 15, 'PC', 'Scroll of Spirit IV : Esprit', 'Consommables'],

    // --- Raciaux (talentsforever, build 69876)
    ['r.bloodfury', 0.10, 'FC', 'Blood Fury (Orc) : puissance des sorts (+10 %)', 'Raciaux'],
    ['r.bloodfury.dur', 15, 'FC', 'Blood Fury : durée (s)', 'Raciaux'],
    ['r.bloodfury.cd', 120, 'FC', 'Blood Fury : recharge (s)', 'Raciaux'],
    ['r.berserk', 0.10, 'FC', 'Berserking (Troll) : hâte (+10 %)', 'Raciaux'],
    ['r.berserk.dur', 10, 'FC', 'Berserking : durée (s)', 'Raciaux'],
    ['r.berserk.cd', 180, 'FC', 'Berserking : recharge (s)', 'Raciaux'],
    ['r.eureka', 0.10, 'FC', 'Eureka! (Gnome) : dégâts ou soins sur 3 sorts (+10 %)', 'Raciaux'],
    ['r.eureka.cd', 120, 'FC', 'Eureka! : recharge (s)', 'Raciaux'],
    ['r.expmind', 0.05, 'FC', 'Expansive Mind (Gnome) : mana max (+5 %)', 'Raciaux'],
    ['r.elune', 10, 'FC', 'Elune’s Light (Elfe de la nuit) : crit (%)', 'Raciaux'],
    ['r.elune.dur', 15, 'FC', 'Elune’s Light : durée (s)', 'Raciaux'],
    ['r.elune.cd', 180, 'FC', 'Elune’s Light : recharge (s)', 'Raciaux'],
    ['r.wind', 0.01, 'FC', 'Wind Blessed (Skyborne) : hâte (+1 %)', 'Raciaux'],

    // --- Mage Givre
    ['frost.fbAvg', 475, 'FC', 'Éclair de givre R11 : dégâts moyens (457–493)', 'Mage Givre'],
    ['frost.fbK', 0.814, 'FC', 'Éclair de givre : coefficient', 'Mage Givre'],
    ['frost.fbCast', 2.5, 'PC', 'Éclair de givre : incantation (3,0 − Improved Frostbolt 0,5)', 'Mage Givre'],
    ['frost.fbMana', 290, 'FC', 'Éclair de givre : mana', 'Mage Givre'],
    ['frost.piercing', 0.06, 'PC', 'Piercing Ice : dégâts Givre', 'Mage Givre'],
    ['frost.shards', 1.0, 'FC', 'Ice Shards : bonus de critique (+100 %)', 'Mage Givre'],
    ['frost.wc', 0.10, 'FS', 'Winter’s Chill : +2 % crit × 5 (personnel)', 'Mage Givre'],
    ['frost.fof', 0.15, 'FC', 'Fingers of Frost : chance par Éclair (rang 1)', 'Mage Givre'],
    ['frost.shatter', 0.50, 'FC', 'Shatter : crit contre cible gelée (rang 3)', 'Mage Givre'],
    ['frost.ilAvg', 145, 'FC', 'Javelot de glace R6 : dégâts moyens (133–157)', 'Mage Givre'],
    ['frost.ilK', 0.143, 'EST', 'Javelot de glace : coefficient (absent du client)', 'Mage Givre'],
    ['frost.ilFrozen', 4, 'FC', 'Javelot de glace : multiplicateur sur cible gelée (+300 %)', 'Mage Givre'],
    ['frost.ilMana', 75, 'EST', 'Javelot de glace : mana', 'Mage Givre'],
    ['frost.hitT', 5, 'FC', 'Elemental Precision : toucher (%)', 'Mage Givre'],
    ['frost.regen', 0.5, 'FC', 'Arcane Meditation : regen en combat', 'Mage Givre'],

    // --- Mage Feu
    ['fire.fbAvg', 483, 'FC', 'Boule de feu R12 : dégâts moyens (425–541)', 'Mage Feu'],
    ['fire.fbDot', 60, 'FC', 'Boule de feu : DoT (60 sur 8 s)', 'Mage Feu'],
    ['fire.fbK', 1.0, 'FC', 'Boule de feu : coefficient', 'Mage Feu'],
    ['fire.fbCast', 3.0, 'FC', 'Boule de feu : incantation (3,5 − Improved Fireball 0,5)', 'Mage Feu'],
    ['fire.fbMana', 410, 'FC', 'Boule de feu : mana', 'Mage Feu'],
    ['fire.power', 0.10, 'PC', 'Fire Power : dégâts Feu', 'Mage Feu'],
    ['fire.scorchStack', 0.15, 'FC', 'Improved Scorch : +3 % × 5 (personnel)', 'Mage Feu'],
    ['fire.critT', 6, 'PC', 'Critical Mass : crit Feu (%)', 'Mage Feu'],
    ['fire.ignite', 0.40, 'FC', 'Ignite : part du critique en DoT', 'Mage Feu'],
    ['fire.pyAvg', 583, 'FC', 'Explosion pyrotechnique R8 : dégâts directs (520–646)', 'Mage Feu'],
    ['fire.pyDot', 212, 'FC', 'Explosion pyrotechnique : DoT (212 sur 12 s)', 'Mage Feu'],
    ['fire.pyKd', 1.0, 'EST', 'Explosion pyrotechnique : coefficient direct (total 1,6)', 'Mage Feu'],
    ['fire.pyKdot', 0.6, 'EST', 'Explosion pyrotechnique : coefficient DoT (total 1,6)', 'Mage Feu'],
    ['fire.pyMana', 440, 'FC', 'Explosion pyrotechnique : mana', 'Mage Feu'],
    ['fire.hsWin', 15, 'FC', 'Hot Streak : durée des cumuls (s)', 'Mage Feu'],
    ['fire.hsCast', 1.5, 'FC', 'Pyro à 3 cumuls : incantation (s)', 'Mage Feu'],
    ['fire.blAvg', 438, 'FC', 'Trait de feu R7 : dégâts moyens (402–474)', 'Mage Feu'],
    ['fire.blK', 0.429, 'FC', 'Trait de feu : coefficient', 'Mage Feu'],
    ['fire.blCd', 6, 'PC', 'Trait de feu : recharge (8 − Wake of Fire 2)', 'Mage Feu'],
    ['fire.blMana', 340, 'FC', 'Trait de feu : mana', 'Mage Feu'],
    ['fire.incin', 6, 'FC', 'Incineration : crit Trait de feu et Brûlure (%)', 'Mage Feu'],
    ['fire.scAvg', 178, 'FC', 'Brûlure R7 : dégâts moyens (163–193)', 'Mage Feu'],
    ['fire.scK', 0.429, 'FC', 'Brûlure : coefficient', 'Mage Feu'],
    ['fire.scMana', 150, 'FC', 'Brûlure : mana', 'Mage Feu'],
    ['fire.scEvery', 30, 'PC', 'Entretien de Fire Vulnerability : une Brûlure toutes les (s)', 'Mage Feu'],
    ['fire.hitT', 5, 'FC', 'Elemental Precision : toucher (%)', 'Mage Feu'],
    ['fire.regen', 0.5, 'FC', 'Arcane Meditation : regen en combat', 'Mage Feu'],

    // --- Mage Arcanes
    ['arc.abAvg', 394, 'FS', 'Déflagration des Arcanes R5 : dégâts moyens (364–424)', 'Mage Arcanes'],
    ['arc.abK', 0.714, 'EST', 'Déflagration : coefficient (règle 2,5/3,5)', 'Mage Arcanes'],
    ['arc.abCast', 2.5, 'FC', 'Déflagration : incantation (R1 ; R5 à vérifier)', 'Mage Arcanes'],
    ['arc.abCost', 0.15, 'FS', 'Déflagration : coût (fraction du mana de base)', 'Mage Arcanes'],
    ['arc.abStackCost', 1.75, 'FS', 'Déflagration : +175 % de coût par cumul', 'Mage Arcanes'],
    ['arc.abStackDmg', 0.10, 'FS', 'Déflagration : +10 % aux autres sorts par cumul', 'Mage Arcanes'],
    ['arc.stacks', 4, 'FS', 'Déflagration : cumuls maximum (le modèle choisit 1 à max)', 'Mage Arcanes'],
    ['arc.amTotal', 1045, 'FC', 'Projectiles des arcanes R8 : dégâts totaux (209 × 5)', 'Mage Arcanes'],
    ['arc.amK', 1.43, 'FC', 'Projectiles : coefficient', 'Mage Arcanes'],
    ['arc.amDur', 5, 'FC', 'Projectiles : canalisation (s)', 'Mage Arcanes'],
    ['arc.amMana', 655, 'FC', 'Projectiles : mana', 'Mage Arcanes'],
    ['arc.mb', 0.40, 'FC', 'Missile Barrage : chance par Déflagration', 'Mage Arcanes'],
    ['arc.cc', 0.10, 'FC', 'Arcane Concentration : chance de Clearcasting', 'Mage Arcanes'],
    ['arc.inst', 0.03, 'FC', 'Arcane Instability : dégâts et crit', 'Mage Arcanes'],
    ['arc.impact', 6, 'FC', 'Arcane Impact : crit Arcane (%)', 'Mage Arcanes'],
    ['arc.mind', 1.0, 'FC', 'Arcane Mind : bonus de critique Arcane (+100 %)', 'Mage Arcanes'],
    ['arc.mindInt', 0.10, 'FC', 'Arcane Mind : Intelligence (+10 %)', 'Mage Arcanes'],
    ['arc.ap', 0.30, 'FC', 'Arcane Power : dégâts et coût (+30 %)', 'Mage Arcanes'],
    ['arc.apDur', 15, 'FC', 'Arcane Power : durée (s)', 'Mage Arcanes'],
    ['arc.apCd', 180, 'FC', 'Arcane Power : recharge (s)', 'Mage Arcanes'],
    ['arc.hitT', 5, 'FC', 'Arcane Focus : toucher (%)', 'Mage Arcanes'],
    ['arc.regen', 0.5, 'FC', 'Arcane Meditation : regen en combat', 'Mage Arcanes'],

    // --- Prêtre Ombre
    ['sh.swpTotal', 762, 'FC', 'Mot de l’ombre : Douleur R8 : dégâts sur 18 s', 'Prêtre Ombre'],
    ['sh.swpK', 1.2, 'FC', 'Mot de l’ombre : Douleur : coefficient', 'Prêtre Ombre'],
    ['sh.swpDur', 18, 'FC', 'Mot de l’ombre : Douleur : durée (s)', 'Prêtre Ombre'],
    ['sh.swpMana', 470, 'FC', 'Mot de l’ombre : Douleur : mana', 'Prêtre Ombre'],
    ['sh.mbAvg', 485, 'FC', 'Attaque mentale R9 : dégâts moyens (472–498)', 'Prêtre Ombre'],
    ['sh.mbK', 0.429, 'FC', 'Attaque mentale : coefficient', 'Prêtre Ombre'],
    ['sh.mbCd', 8, 'PC', 'Attaque mentale : recharge (s)', 'Prêtre Ombre'],
    ['sh.mbMana', 350, 'FC', 'Attaque mentale : mana', 'Prêtre Ombre'],
    ['sh.mfTotal', 390, 'FC', 'Fouet mental R6 : dégâts sur 3 s', 'Prêtre Ombre'],
    ['sh.mfK', 0.501, 'FC', 'Fouet mental : coefficient', 'Prêtre Ombre'],
    ['sh.mfDur', 3, 'FC', 'Fouet mental : canalisation (s)', 'Prêtre Ombre'],
    ['sh.mfMana', 205, 'FC', 'Fouet mental : mana', 'Prêtre Ombre'],
    ['sh.swdAvg', 448, 'FC', 'Mot de l’ombre : Mort R4 : dégâts moyens (434–462)', 'Prêtre Ombre'],
    ['sh.swdK', 0.429, 'FC', 'Mot de l’ombre : Mort : coefficient', 'Prêtre Ombre'],
    ['sh.swdCd', 12, 'PC', 'Mot de l’ombre : Mort : recharge (s)', 'Prêtre Ombre'],
    ['sh.swdMana', 340, 'FC', 'Mot de l’ombre : Mort : mana', 'Prêtre Ombre'],
    ['sh.sf', 0.10, 'FC', 'Forme d’ombre : dégâts Ombre', 'Prêtre Ombre'],
    ['sh.sfBonus', 1.0, 'FC', 'Forme d’ombre : bonus de critique (+100 %)', 'Prêtre Ombre'],
    ['sh.sfCost', 0.5, 'FC', 'Forme d’ombre : réduction de coût', 'Prêtre Ombre'],
    ['sh.weave', 0.10, 'FC', 'Shadow Weaving : +2 % × 5 (personnel)', 'Prêtre Ombre'],
    ['sh.hitT', 0, 'EST', 'Toucher apporté par les talents (%)', 'Prêtre Ombre'],
    ['sh.regen', 0.5, 'PC', 'Meditation (Discipline) : regen en combat', 'Prêtre Ombre'],

    // --- Démoniste (commun + Affliction)
    ['wl.sbAvg', 268, 'FC', 'Trait de l’ombre R10 : dégâts moyens (253–283)', 'Démoniste'],
    ['wl.sbK', 0.857, 'FC', 'Trait de l’ombre : coefficient', 'Démoniste'],
    ['wl.sbCast', 2.5, 'PC', 'Trait de l’ombre : incantation (3,0 − Bane 0,5)', 'Démoniste'],
    ['wl.sbMana', 380, 'FC', 'Trait de l’ombre : mana', 'Démoniste'],
    ['wl.lt', 424, 'PC', 'Connexion (Life Tap) : mana par incantation', 'Démoniste'],
    ['aff.corrTotal', 438, 'FC', 'Corruption R7 : dégâts sur 18 s', 'Démoniste Affliction'],
    ['aff.corrK', 1.2, 'FC', 'Corruption : coefficient', 'Démoniste Affliction'],
    ['aff.corrDur', 18, 'FC', 'Corruption : durée (s)', 'Démoniste Affliction'],
    ['aff.corrMana', 340, 'FC', 'Corruption : mana', 'Démoniste Affliction'],
    ['aff.impCorr', 0.10, 'FC', 'Improved Corruption : dégâts (+2 % × 5)', 'Démoniste Affliction'],
    ['aff.agTotal', 1044, 'PC', 'Fléau d’agonie : dégâts sur 24 s (valeur Classic)', 'Démoniste Affliction'],
    ['aff.agK', 1.2, 'PC', 'Fléau d’agonie : coefficient', 'Démoniste Affliction'],
    ['aff.agDur', 24, 'PC', 'Fléau d’agonie : durée (s)', 'Démoniste Affliction'],
    ['aff.agMana', 265, 'PC', 'Fléau d’agonie : mana', 'Démoniste Affliction'],
    ['aff.mal', 0.05, 'FC', 'Malediction : dégâts périodiques', 'Démoniste Affliction'],
    ['aff.sm', 0.05, 'FC', 'Shadow Mastery : dégâts Ombre', 'Démoniste Affliction'],
    ['aff.pand', 0.99, 'FC', 'Pandemic : bonus de crit des DoT (+33 % × 3)', 'Démoniste Affliction'],
    ['aff.malev', 5, 'FC', 'Malevolence : crit Ombre (%)', 'Démoniste Affliction'],
    ['aff.nf', 0.04, 'FC', 'Nightfall : chance par tick de Corruption', 'Démoniste Affliction'],
    ['aff.hitT', 5, 'FC', 'Suppression : toucher (%)', 'Démoniste Affliction'],

    // --- Démonologie
    ['demo.sac', 0.15, 'FC', 'Demonic Sacrifice (Diablotin) : dégâts Ombre', 'Démoniste Démonologie'],
    ['demo.md', 0.10, 'FC', 'Master Demonologist : dégâts Feu et Ombre', 'Démoniste Démonologie'],
    ['demo.sl', 0.03, 'FC', 'Soul Link : dégâts', 'Démoniste Démonologie'],
    ['demo.dk', 19.8, 'EST', 'Demonic Knowledge : puissance des sorts (33 % du niveau)', 'Démoniste Démonologie'],
    ['demo.pet', 0, 'EST', 'DPS du démon (inconnu, à saisir)', 'Démoniste Démonologie'],
    ['demo.hitT', 0, 'EST', 'Toucher apporté par les talents (%)', 'Démoniste Démonologie'],

    // --- Destruction
    ['des.incAvg', 217, 'FC', 'Incinérer R3 : dégâts moyens (201–233)', 'Démoniste Destruction'],
    ['des.incK', 0.714, 'FC', 'Incinérer : coefficient', 'Démoniste Destruction'],
    ['des.incCast', 2.0, 'PC', 'Incinérer : incantation (2,5 − Bane 0,5)', 'Démoniste Destruction'],
    ['des.incMana', 325, 'FC', 'Incinérer : mana', 'Démoniste Destruction'],
    ['des.incImm', 0.25, 'FC', 'Incinérer : bonus sous Immolation', 'Démoniste Destruction'],
    ['des.immD', 158, 'FC', 'Immolation R8 : dégâts directs', 'Démoniste Destruction'],
    ['des.immDot', 275, 'FC', 'Immolation : DoT (275 sur 15 s)', 'Démoniste Destruction'],
    ['des.immKd', 0.2, 'PC', 'Immolation : coefficient direct (total 0,85)', 'Démoniste Destruction'],
    ['des.immKdot', 0.65, 'PC', 'Immolation : coefficient DoT (total 0,85)', 'Démoniste Destruction'],
    ['des.immDur', 15, 'FC', 'Immolation : durée (s)', 'Démoniste Destruction'],
    ['des.immCast', 1.5, 'PC', 'Immolation : incantation (2,0 − Bane 0,5)', 'Démoniste Destruction'],
    ['des.immMana', 380, 'FC', 'Immolation : mana', 'Démoniste Destruction'],
    ['des.af', 0.09, 'FC', 'Agonizing Flames : dégâts Destruction (+3 % × 3)', 'Démoniste Destruction'],
    ['des.ruin', 1.0, 'FC', 'Ruin : bonus de critique (+20 % × 5)', 'Démoniste Destruction'],
    ['des.sm', 0.05, 'FC', 'Shadow Mastery (Trait de l’ombre)', 'Démoniste Destruction'],
    ['des.hitT', 0, 'EST', 'Toucher apporté par les talents (%)', 'Démoniste Destruction'],

    // --- Soigneurs
    ['hp.ghAvg', 1960, 'FC', 'Soins supérieurs R5 : soins moyens (1 853–2 067)', 'Prêtre soins'],
    ['hp.ghK', 0.857, 'FC', 'Soins supérieurs : coefficient', 'Prêtre soins'],
    ['hp.ghCast', 2.5, 'PC', 'Soins supérieurs : incantation (3,0 − Divine Fury 0,5)', 'Prêtre soins'],
    ['hp.ghMana', 710, 'FC', 'Soins supérieurs : mana', 'Prêtre soins'],
    ['hp.sg', 0.25, 'FC', 'Spiritual Guidance : Esprit converti en soins (Sacré)', 'Prêtre soins'],
    ['hp.regen', 0.5, 'FC', 'Meditation : regen en combat', 'Prêtre soins'],
    ['disc.da', 0.15, 'FC', 'Divine Aegis : absorption sur soin critique', 'Prêtre soins'],
    ['disc.ms', 0.15, 'FC', 'Mental Strength : Intelligence (Discipline)', 'Prêtre soins'],
    ['hpal.hlAvg', 1580, 'FC', 'Lumière sacrée R9 : soins moyens (1 495–1 665)', 'Paladin soins'],
    ['hpal.hlK', 0.714, 'FC', 'Lumière sacrée : coefficient', 'Paladin soins'],
    ['hpal.hlCast', 2.5, 'FC', 'Lumière sacrée : incantation (s)', 'Paladin soins'],
    ['hpal.hlMana', 660, 'FC', 'Lumière sacrée : mana', 'Paladin soins'],
    ['hpal.folAvg', 303, 'FC', 'Éclair lumineux R6 : soins moyens (286–320)', 'Paladin soins'],
    ['hpal.folK', 0.429, 'FC', 'Éclair lumineux : coefficient', 'Paladin soins'],
    ['hpal.folCast', 1.5, 'FC', 'Éclair lumineux : incantation (s)', 'Paladin soins'],
    ['hpal.folMana', 140, 'FC', 'Éclair lumineux : mana', 'Paladin soins'],
    ['hpal.illum', 0.5, 'FC', 'Illumination : fraction du coût rendue sur crit', 'Paladin soins'],
    ['hpal.regen', 0.3, 'FC', 'Reverence : regen en combat', 'Paladin soins'],

    // --- Paladin tank
    ['prot.seal', 37, 'FC', 'Seal of Fury R7 : dégâts Sacré par coup', 'Paladin tank'],
    ['prot.absorb', 0.5, 'FC', 'Seal of Fury : absorption avec bouclier (fraction)', 'Paladin tank'],
    ['prot.rf', 1.6, 'PC', 'Righteous Fury : multiplicateur de menace Sacré', 'Paladin tank'],
    ['prot.speed', 2.0, 'EST', 'Vitesse de l’arme (s)', 'Paladin tank'],
    ['prot.hsBlock', 20, 'FC', 'Holy Shield : blocage (%)', 'Paladin tank'],
    ['prot.hsDmg', 110, 'FC', 'Holy Shield : dégâts par blocage', 'Paladin tank']
  ];

  const CLASSES = {
    mage: { name: 'Mage', color: '#3FC7EB', races: ['gnome', 'human', 'orc', 'undead', 'troll', 'skyborne'] },
    warlock: { name: 'Démoniste', color: '#8788EE', races: ['orc', 'undead', 'gnome', 'human', 'troll'] },
    priest: { name: 'Prêtre', color: '#D9D2C3', colorLight: '#8C8472', races: ['human', 'dwarf', 'nightelf', 'gnome', 'undead', 'troll'] },
    paladin: { name: 'Paladin', color: '#F48CBA', races: ['human', 'dwarf', 'undead'] }
  };

  const RACES = {
    gnome: { name: 'Gnome', fx: ['eureka', 'expmind'] },
    human: { name: 'Humain', fx: [] },
    orc: { name: 'Orc', fx: ['bloodfury'] },
    undead: { name: 'Mort-vivant', fx: [] },
    troll: { name: 'Troll', fx: ['berserk'] },
    dwarf: { name: 'Nain', fx: [] },
    nightelf: { name: 'Elfe de la nuit', fx: ['elune'] },
    skyborne: { name: 'Skyborne', fx: ['wind'] }
  };

  const SPECS = [
    { id: 'arcane', cls: 'mage', name: 'Arcanes', role: 'dps', school: 'arcane', dash: [6, 3], sim: 546, simOld: 551, talents: '— (preset non publié)' },
    { id: 'fire', cls: 'mage', name: 'Feu', role: 'dps', school: 'fire', dash: [], sim: 613, simOld: 723, talents: '19/32/0' },
    { id: 'frost', cls: 'mage', name: 'Givre', role: 'dps', school: 'frost', dash: [2, 3], sim: 558, simOld: 527, talents: '18/0/31' },
    { id: 'affli', cls: 'warlock', name: 'Affliction', role: 'dps', school: 'shadow', dash: [], sim: 439, simOld: 559, talents: '36/0/15' },
    { id: 'demo', cls: 'warlock', name: 'Démonologie', role: 'dps', school: 'shadow', dash: [6, 3], sim: 475, simOld: 625, talents: '5/31/15' },
    { id: 'destro', cls: 'warlock', name: 'Destruction', role: 'dps', school: 'fire', dash: [2, 3], sim: 431, simOld: 627, talents: '13/11/27' },
    { id: 'shadow', cls: 'priest', name: 'Ombre', role: 'dps', school: 'shadow', dash: [], sim: 423, simOld: 519, talents: '20/0/31' },
    { id: 'holyp', cls: 'priest', name: 'Sacré', role: 'heal', school: 'holy', dash: [6, 3], talents: '18/33/0 (communautaire)' },
    { id: 'disc', cls: 'priest', name: 'Discipline', role: 'heal', school: 'holy', dash: [2, 3], talents: '—' },
    { id: 'prot', cls: 'paladin', name: 'Protection', role: 'tank', school: 'holy', dash: [], talents: '—' },
    { id: 'holypal', cls: 'paladin', name: 'Sacré', role: 'heal', school: 'holy', dash: [6, 3], talents: '—' }
  ];

  // Flags de rotation (interrupteurs du modèle)
  const FLAGS = {
    frost: [['wc', 'Winter’s Chill actif', true], ['fof', 'Fingers of Frost → Javelot de glace', true], ['evoc', 'Évocation si rentable', true], ['gem', 'Gemme de mana', true]],
    fire: [['hs', 'Hot Streak → Explosion pyrotechnique', true], ['blast', 'Trait de feu si rentable en mana', true], ['evoc', 'Évocation si rentable', true], ['gem', 'Gemme de mana', true]],
    arcane: [['ap', 'Arcane Power sur recharge', true], ['evoc', 'Évocation si rentable', true], ['gem', 'Gemme de mana', true]],
    shadow: [['mb', 'Attaque mentale sur recharge', true], ['swd', 'Mot de l’ombre : Mort sur recharge (contrecoup de 10 % des PV)', false]],
    affli: [['agony', 'Fléau d’agonie entretenu', true], ['nf', 'Nightfall (Trait instantané)', true]],
    demo: [],
    destro: [],
    holyp: [['sg', 'Spiritual Guidance', true]],
    disc: [],
    holypal: [],
    prot: []
  };

  // Buffs de raid : fx → id de paramètre
  const BUFFS = [
    { id: 'ai', name: 'Intelligence des Arcanes', fx: { intBuff: 'b.ai.int' } },
    { id: 'ds', name: 'Esprit divin', fx: { spiBuff: 'b.ds.spi' } },
    { id: 'fort', name: 'Mot de pouvoir : Robustesse', fx: { sta: 'b.fort.sta' } },
    { id: 'gotw', name: 'Don du fauve', fx: { stats: 'b.gotw.stats', armor: 'b.gotw.armor' } },
    { id: 'kings', name: 'Bénédiction des rois', fx: { pct: 'b.kings.pct' } },
    { id: 'wisdom', name: 'Bénédiction de sagesse', fx: { mp5: 'b.wisdom.mp5' } },
    { id: 'spring', name: 'Totem Fontaine de mana', fx: { mp5: 'b.spring.mp5' } },
    { id: 'moonkin', name: 'Aura de sélénien', fx: { crit: 'b.moonkin.crit' } },
    { id: 'pi', name: 'Infusion de puissance (sur toi)', fx: { dmgUp: ['b.pi.pct', 'b.pi.dur', 'b.pi.cd'], healUp: ['b.pi.pct', 'b.pi.dur', 'b.pi.cd'] } },
    { id: 'coe', name: 'Malédiction des éléments (sur la cible)', fx: { coe: 'b.coe.pct' } },
    { id: 'devotion', name: 'Aura de dévotion', fx: { armor: 'b.devotion.armor' } }
  ];
  const COE_SCHOOLS_DEFAULT = ['fire', 'frost'];

  const WORLD = [
    { id: 'rally', name: 'Cri de ralliement du tueur de dragon', fx: { crit: 'w.rally.crit' } },
    { id: 'song', name: 'Sérénade de Chantefleur', fx: { stats: 'w.song.stats', crit: 'w.song.crit' } },
    { id: 'warchief', name: 'Bénédiction du chef de guerre', fx: { mp5: 'w.warchief.mp5' } },
    { id: 'zand', name: 'Esprit de Zandalar', fx: { pct: 'w.zand.pct' } },
    { id: 'slip', name: 'Slip’kik’s Savvy', fx: { crit: 'w.slip.crit' } },
    { id: 'sayge', name: 'Sombre fortune de Sayge (dégâts)', fx: { dmgPct: 'w.sayge.pct' } }
  ];

  // Consommables (grp = pas de cumul dans le groupe, règle Classic « même effet »)
  const CONS = [
    { id: 'flask_sp', name: 'Flask of Supreme Power', grp: 'flask', fx: { sp: 'c.flask_sp' } },
    { id: 'flask_wis', name: 'Flask of Distilled Wisdom', grp: 'flask', fx: { mana: 'c.flask_wis' } },
    { id: 'flask_titans', name: 'Flask of the Titans', grp: 'flask', fx: { hp: 'c.flask_titans' } },
    { id: 'owl', name: 'Elixir of the Owl', grp: 'elixInt', fx: { int: 'c.owl.int', crit: 'c.owl.crit' } },
    { id: 'int_g', name: 'Elixir of Greater Intellect', grp: 'elixInt', fx: { int: 'c.int_g' } },
    { id: 'cunning', name: 'Elixir of Cunning', grp: 'elixInt', fx: { int: 'c.cunning' } },
    { id: 'gae', name: 'Greater Arcane Elixir', grp: 'elixSp', fx: { sp: 'c.gae' } },
    { id: 'arcane_l', name: 'Lesser Arcane Elixir', grp: 'elixSp', fx: { sp: 'c.arcane_l' } },
    { id: 'shadowp', name: 'Elixir of Shadow Power', grp: 'elixShadow', fx: { school: { shadow: 'c.shadowp' } } },
    { id: 'firep', name: 'Elixir of Greater Firepower', grp: 'elixFire', fx: { school: { fire: 'c.firep' } } },
    { id: 'frostp', name: 'Elixir of Frost Power', grp: 'elixFrost', fx: { school: { frost: 'c.frostp' } } },
    { id: 'sages', name: 'Elixir of Sages', grp: 'elixSpi', fx: { spi: 'c.sages.spi', crit: 'c.sages.crit' } },
    { id: 'spirit_g', name: 'Elixir of Greater Spirit', grp: 'elixSpi', fx: { spi: 'c.spirit_g' } },
    { id: 'cleric', name: 'Greater Cleric’s Elixir', grp: 'elixHeal', fx: { heal: 'c.cleric' } },
    { id: 'mageblood_g', name: 'Greater Mageblood Elixir', grp: 'elixMp5', fx: { mp5: 'c.mageblood_g' } },
    { id: 'mageblood', name: 'Mageblood (Classic)', grp: 'elixMp5', fx: { mp5: 'c.mageblood' } },
    { id: 'wicked', name: 'Elixir of Wicked Regeneration', grp: 'elixMp5', fx: { mp5: 'c.wicked' } },
    { id: 'phalanx', name: 'Elixir of the Phalanx', grp: 'elixTank', fx: { hp: 'c.phalanx.hp', armor: 'c.phalanx.armor' } },
    { id: 'defsup', name: 'Elixir of Superior Defense', grp: 'elixTank', fx: { armor: 'c.defsup' } },
    { id: 'bwo', name: 'Brilliant Wizard Oil', grp: 'oil', fx: { sp: 'c.bwo.sp', crit: 'c.bwo.crit' } },
    { id: 'wo', name: 'Wizard Oil', grp: 'oil', fx: { sp: 'c.wo.sp' } },
    { id: 'bmo', name: 'Brilliant Mana Oil', grp: 'oil', fx: { mp5: 'c.bmo.mp5', heal: 'c.bmo.heal' } },
    { id: 'bat', name: 'Bat Hachee', grp: 'food', fx: { int: 'c.bat' } },
    { id: 'smoothie', name: 'Wicked Smoothie', grp: 'food', fx: { spi: 'c.smoothie' } },
    { id: 'runn', name: 'Runn Tum Tuber Surprise', grp: 'food', fx: { int: 'c.runn' } },
    { id: 'nightfin', name: 'Nightfin Soup', grp: 'food', fx: { mp5: 'c.nightfin' } },
    { id: 'sagefish', name: 'Sagefish Delight', grp: 'food', fx: { mp5: 'c.sagefish' } },
    { id: 'egg', name: 'Herb Baked Egg', grp: 'food', fx: { spi: 'c.egg' } },
    { id: 'scrollint', name: 'Scroll of Intellect IV', grp: 'scrollInt', fx: { intBuff: 'c.scrollint' } },
    { id: 'scrollspi', name: 'Scroll of Spirit IV', grp: 'scrollSpi', fx: { spiBuff: 'c.scrollspi' } },
    { id: 'rune', name: 'Demonic Rune (sur recharge)', grp: 'rune', fx: { manaUse: ['c.rune', 'c.rune.cd'] } }
  ];
  const CONS_GROUPS = {
    flask: 'Flacon', elixInt: 'Élixir d’Intelligence', elixSp: 'Élixir de puissance des sorts', elixShadow: 'Élixir d’Ombre', elixFire: 'Élixir de Feu',
    elixFrost: 'Élixir de Givre', elixSpi: 'Élixir d’Esprit', elixHeal: 'Élixir de soins', elixMp5: 'Élixir de mp5', elixTank: 'Élixir de tank',
    oil: 'Huile d’arme', food: 'Nourriture (Well Fed)', scrollInt: 'Parchemin d’Intelligence', scrollSpi: 'Parchemin d’Esprit', rune: 'Rune'
  };
  const POTIONS = [
    { id: 'none', name: 'Aucune' },
    { id: 'spellblast', name: 'Major Spellblasting (+40 PdS, 30 s)', tag: 'FC' },
    { id: 'manapot', name: 'Major Mana (≈1 800 mana)', tag: 'PC' },
    { id: 'mender', name: 'Major Mender’s (+75 soins, 30 s)', tag: 'FC' }
  ];

  // Presets « sets pro » (buffs + consommables)
  const PRO_SETS = {
    raid_caster: { name: 'Raid, lanceur de sorts', ctx: 'raid', buffs: ['ai', 'ds', 'fort', 'gotw', 'kings', 'wisdom', 'spring', 'moonkin', 'coe'], cons: ['flask_sp', 'owl', 'gae', 'shadowp', 'firep', 'frostp', 'bwo', 'bat', 'rune'], potion: 'spellblast' },
    raid_heal: { name: 'Raid, soigneur', ctx: 'raid', buffs: ['ai', 'ds', 'fort', 'gotw', 'kings', 'wisdom', 'spring', 'moonkin'], cons: ['flask_wis', 'cleric', 'mageblood_g', 'sages', 'bmo', 'smoothie', 'rune'], potion: 'manapot' },
    raid_tank: { name: 'Raid, tank', ctx: 'raid', buffs: ['ai', 'ds', 'fort', 'gotw', 'kings', 'devotion'], cons: ['flask_titans', 'phalanx', 'owl'], potion: 'none' },
    dungeon: { name: 'Donjon (budget)', ctx: 'donjon', buffs: ['ai', 'ds', 'fort', 'gotw', 'kings'], cons: ['arcane_l', 'wo', 'bat'], potion: 'manapot' },
    world_pvp: { name: 'Monde ouvert / PvP sauvage', ctx: 'monde', buffs: ['ai', 'fort', 'gotw'], cons: ['owl', 'bwo', 'bat'], wb: ['rally', 'song', 'warchief', 'zand', 'slip', 'sayge'], potion: 'none' },
    leveling: { name: 'Leveling', ctx: 'monde', buffs: [], cons: ['smoothie'], potion: 'none' }
  };

  // Presets de stats d’équipement (fiche sans buffs de raid) — estimations passe 3
  const STAGES = {
    dps: {
      fresh: { name: '60 frais', gear: { int: 170, spi: 110, sp: 150, school: 0, heal: 0, crit: 2, hit: 2, mp5: 0, sta: 150 } },
      preraid: { name: 'Pré-raid', gear: { int: 225, spi: 125, sp: 260, school: 30, heal: 0, crit: 4, hit: 5, mp5: 0, sta: 190 } },
      t1: { name: 'Raid T1 (hyp.)', gear: { int: 270, spi: 140, sp: 360, school: 40, heal: 0, crit: 6, hit: 8, mp5: 0, sta: 220 } },
      bis: { name: 'BiS P1 (hyp.)', gear: { int: 320, spi: 150, sp: 460, school: 50, heal: 0, crit: 8, hit: 10, mp5: 0, sta: 250 } }
    },
    heal: {
      fresh: { name: '60 frais', gear: { int: 180, spi: 170, sp: 0, school: 0, heal: 350, crit: 2, hit: 0, mp5: 10, sta: 150 } },
      preraid: { name: 'Pré-raid', gear: { int: 230, spi: 200, sp: 0, school: 0, heal: 525, crit: 3, hit: 0, mp5: 20, sta: 180 } },
      t1: { name: 'Raid T1 (hyp.)', gear: { int: 270, spi: 230, sp: 0, school: 0, heal: 700, crit: 5, hit: 0, mp5: 30, sta: 210 } },
      bis: { name: 'BiS P1 (hyp.)', gear: { int: 310, spi: 250, sp: 0, school: 0, heal: 850, crit: 6, hit: 0, mp5: 40, sta: 240 } }
    },
    tank: {
      fresh: { name: '60 frais', gear: { hp: 6000, armor: 6500, dodge: 5, parry: 5, block: 10, int: 100, spi: 80, sp: 0, school: 0, heal: 0, crit: 0, hit: 2, mp5: 0, sta: 250 } },
      preraid: { name: 'Pré-raid', gear: { hp: 7500, armor: 8000, dodge: 7, parry: 6, block: 15, int: 120, spi: 90, sp: 0, school: 0, heal: 0, crit: 0, hit: 4, mp5: 0, sta: 320 } },
      t1: { name: 'Raid T1 (hyp.)', gear: { hp: 8500, armor: 9500, dodge: 9, parry: 8, block: 18, int: 140, spi: 90, sp: 0, school: 0, heal: 0, crit: 0, hit: 6, mp5: 0, sta: 380 } },
      bis: { name: 'BiS P1 (hyp.)', gear: { hp: 9500, armor: 11000, dodge: 10, parry: 10, block: 20, int: 160, spi: 90, sp: 0, school: 0, heal: 0, crit: 0, hit: 8, mp5: 0, sta: 430 } }
    }
  };

  // Scores passe 1 (1–10)
  const CRITERIA = [
    ['lvlSpeed', 'Leveling : vitesse'], ['lvlSafety', 'Leveling : sécurité'], ['farm', 'Farm solo'],
    ['pveRole', 'PvE : rôle'], ['pveAoe', 'PvE : zone'], ['pveUtil', 'PvE : utilité'], ['pveDemand', 'PvE : demande'],
    ['pvpDuel', 'PvP : duel'], ['pvpBg', 'PvP : champ de bataille'], ['pvpWorld', 'PvP : sauvage'],
    ['scaling', 'Scaling'], ['mana', 'Tenue de mana'], ['ease', 'Facilité']
  ];
  const SCORES = {
    arcane: [6, 6, 6, 8, 7, 8, 7, 7, 6, 7, 8, 4, 5],
    fire: [7, 6, 5, 8, 7, 8, 8, 7, 7, 7, 8, 6, 6],
    frost: [9, 8, 7, 6, 8, 8, 7, 9, 8, 9, 6, 8, 7],
    affli: [9, 9, 8, 7, 6, 8, 7, 9, 8, 9, 7, 9, 6],
    demo: [8, 10, 7, 6, 5, 8, 6, 8, 7, 8, 6, 8, 7],
    destro: [7, 6, 5, 7, 6, 8, 7, 7, 7, 7, 7, 5, 7],
    shadow: [6, 8, 5, 5, 3, 6, 5, 8, 7, 8, 6, 7, 7],
    holyp: [3, 7, 2, 8, 9, 8, 9, 4, 7, 4, 8, 7, 7],
    disc: [4, 8, 3, 8, 6, 9, 8, 6, 8, 5, 7, 8, 6],
    prot: [6, 8, 5, 7, 8, 7, 8, 5, 5, 5, 7, 9, 7],
    holypal: [4, 7, 3, 8, 6, 8, 8, 5, 7, 5, 8, 9, 7]
  };
  const PROFILES = {
    equilibre: { name: 'Équilibré', w: { lvlSpeed: 10, lvlSafety: 5, farm: 5, pveRole: 15, pveAoe: 5, pveUtil: 7, pveDemand: 8, pvpDuel: 5, pvpBg: 8, pvpWorld: 7, scaling: 15, mana: 5, ease: 5 } },
    raid: { name: 'Raid', w: { lvlSpeed: 0, lvlSafety: 0, farm: 0, pveRole: 30, pveAoe: 5, pveUtil: 15, pveDemand: 20, pvpDuel: 0, pvpBg: 0, pvpWorld: 0, scaling: 20, mana: 10, ease: 0 } },
    donjon: { name: 'Donjon', w: { lvlSpeed: 0, lvlSafety: 5, farm: 0, pveRole: 25, pveAoe: 25, pveUtil: 15, pveDemand: 20, pvpDuel: 0, pvpBg: 0, pvpWorld: 0, scaling: 0, mana: 10, ease: 0 } },
    pvp: { name: 'PvP', w: { lvlSpeed: 0, lvlSafety: 0, farm: 0, pveRole: 0, pveAoe: 0, pveUtil: 0, pveDemand: 0, pvpDuel: 30, pvpBg: 30, pvpWorld: 30, scaling: 0, mana: 0, ease: 10 } },
    leveling: { name: 'Leveling', w: { lvlSpeed: 40, lvlSafety: 25, farm: 20, pveRole: 0, pveAoe: 0, pveUtil: 0, pveDemand: 0, pvpDuel: 0, pvpBg: 0, pvpWorld: 0, scaling: 0, mana: 15, ease: 0 } }
  };

  const LEVEL_CURVES = {
    levels: [10, 20, 30, 40, 50, 60],
    arcane: [40, 55, 62, 72, 76, 80], fire: [42, 55, 65, 74, 78, 82], frost: [50, 66, 76, 84, 87, 90],
    affli: [52, 68, 78, 88, 90, 92], demo: [52, 64, 76, 84, 86, 88], destro: [45, 55, 65, 76, 80, 83],
    shadow: [38, 48, 62, 78, 82, 85], holyp: [30, 36, 44, 50, 54, 58], disc: [32, 40, 50, 56, 60, 63],
    prot: [45, 58, 66, 74, 77, 80], holypal: [40, 48, 55, 60, 63, 66]
  };
  const SP_LEVELING = {
    levels: [10, 20, 30, 40, 50, 60],
    casual: [5, 40, 65, 95, 130, 170], optimized: [15, 127, 170, 215, 260, 330],
    intCasual: [25, 65, 90, 115, 140, 170], intOpt: [35, 101, 130, 160, 190, 240]
  };
  const SPIKES = {
    arcane: [[20, 'Déflagration des Arcanes (talent), Transfert, Évocation'], [25, 'Missile Barrage'], [40, 'Arcane Power']],
    fire: [[25, 'Hot Streak'], [40, 'Combustion (4 critiques)']],
    frost: [[20, 'Javelot de glace (talent), Blizzard, Transfert'], [30, 'Fingers of Frost'], [40, 'Capstone Givre (Barrière de glace)']],
    affli: [[10, 'Marcheur du Vide et Explorer Imp'], [25, 'Pandemic, Malevolence : les DoT critiquent fort'], [40, 'Wrack']],
    demo: [[30, 'Demonic Knowledge, Chasseur corrompu'], [40, 'Demonic Pact']],
    destro: [[30, 'Bane of Havoc, Fire and Brimstone'], [35, 'Shadow and Flame'], [40, 'Incinérer (capstone)']],
    shadow: [[30, 'Étreinte vampirique'], [32, 'Mot de l’ombre : Mort (sort de base)'], [40, 'Forme d’ombre']],
    holyp: [[30, 'Esprit divin (sort de base), Binding Heal'], [35, 'Spiritual Guidance'], [40, 'Prayer of Mending']],
    disc: [[20, 'Inner Focus, Meditation'], [30, 'Penance'], [40, 'Infusion de puissance']],
    prot: [[6, 'Holy Strike'], [20, 'Consécration (base), Improved Seal of Fury'], [30, 'Templar’s Bulwark'], [40, 'Holy Shield, Hammer of the Righteous']],
    holypal: [[20, 'Reverence, Voice of Truth'], [30, 'Horion sacré'], [40, 'Light’s Vigil']]
  };

  const VERDICTS = [
    ['Leveling solo', 'Démoniste Affliction (alt. Mage Givre)', 'DoT instantanés, démon qui tank, Connexion et drains', 'moyenne à haute'],
    ['DPS PvE', 'Mage Feu (alt. Arcanes)', 'Meilleure sim du périmètre, Hot Streak et Combustion', 'moyenne'],
    ['Soins PvE', 'Prêtre Sacré ≈ Paladin Sacré', 'Soins de groupe d’un côté, mono-cible et mana de l’autre', 'faible à moyenne'],
    ['Tank PvE', 'Paladin Protection', 'Taunt, mana autonome, Templar’s Bulwark ; pas d’interrupt', 'moyenne'],
    ['PvP duel et sauvage', 'Mage Givre ≈ Démoniste Affliction', 'Contrôle et burst contre Peur et DoT qui critiquent', 'moyenne'],
    ['PvP champ de bataille', 'Prêtre Discipline', 'Penance, Divine Aegis, Infusion de puissance, dissipations', 'moyenne'],
    ['À éviter', 'Prêtre Ombre en raid ; soigneurs en leveling solo', '423 DPS simulés, pas de zone, synergie perdue', 'moyenne']
  ];

  const DUAL = {
    status: 'Non annoncée par Blizzard. Le client contient des chaînes « spé primaire/secondaire » verrouillées. Respec en bêta : 1 po puis 5 po.',
    combos: [
      ['Prêtre', 'Ombre ↔ Sacré ou Discipline', 'Meilleur recouvrement : Int et Esprit servent aux deux ; le soin donne 1/3 en dégâts'],
      ['Paladin', 'Protection ↔ Sacré', 'Peu de recouvrement (armure/blocage contre soins) ; valeur maximale en donjon'],
      ['Démoniste', 'Affliction ↔ Destruction ou Démonologie', 'Recouvrement total (puissance des sorts) ; Affliction pour le leveling et le PvP'],
      ['Mage', 'Givre ↔ Feu ou Arcanes', 'Recouvrement total ; Givre pour le leveling et le PvP, Feu en raid (+9,9 % en sim)']
    ]
  };

  const RACIALS_PVP = [
    ['Mort-vivant', 'Will of the Forsaken', 'Retire Charme, Peur et Sommeil, sans immunité', '2 min'],
    ['Humain', 'Will to Survive', 'Retire les étourdissements', '3 min'],
    ['Gnome', 'Escape Artist', 'Retire les ralentissements, 3 s d’immunité', '2 min'],
    ['Nain', 'Stoneform', 'Immunité saignements, poisons et maladies ; −10 % dégâts physiques 8 s', '3 min'],
    ['Orc', 'Shatter Curse', 'Immunité aux Malédictions et Banes ; −15 % dégâts magiques 8 s', '3 min'],
    ['Orc', 'Blood Fury', '+10 % PA et puissance des sorts, 15 s', '2 min'],
    ['Troll', 'Berserking', '+10 % de hâte, 10 s', '3 min'],
    ['Tauren', 'War Stomp', 'Étourdit 2 s, jusqu’à 5 cibles', '2 min'],
    ['Gnome', 'Eureka!', '3 sorts à −50 % de mana et +10 % de dégâts', '2 min'],
    ['Elfe de la nuit', 'Elune’s Light', '+10 % de crit, 15 s', '3 min'],
    ['Humain', 'Perception', 'Détection de la furtivité, 20 s', '3 min'],
    ['Elfe de la nuit', 'Shadowmeld', 'Utilisable en combat (recharge alors portée à 2 min)', '—']
  ];

  const PVP_RULES = [
    'Pas de PvP coté ni d’arènes (Q&A du 17/09).',
    '14 rangs d’Honneur par saison, 24 750 Rank Points au total pour le rang 14 ; réserve d’Honneur plafonnée à 15 000.',
    'Insignia débloquée au rang 2 (valeurs Classic : spécifique à la classe, recharge 5 min).',
    'Battle Standard au rang 7 : +15 % de PV max au groupe, champs de bataille seulement, recharge 10 min.',
    'Champs de bataille : Goulet des Chanteguerres, Bassin Arathi, Vallée d’Alterac et Darkspear Islands (15 contre 15, dès le niveau 30).',
    'Rendements décroissants : aucune donnée Forever ; proxy Classic 100 %, 50 %, 25 %, puis immunité (remise à zéro après 15–18 s).'
  ];

  const ITEMS = [
    { id: 'leafre', name: 'Leafre’s Ring of Precise Spell Power', slot: 'finger', st: { sp: 100 }, tag: 'FC', note: 'épique ilvl 66, anomalie de budget (+186 %)' },
    { id: 'malroot', name: 'Malignant Root', slot: 'finger', st: { sta: 7, ap: 8, sp: 4 }, tag: 'FC', note: 'rare ilvl 32, Wetlands' },
    { id: 'ladimore', name: 'Ladimore Heirloom Ring', slot: 'finger', st: { int: 6, sp: 5 }, tag: 'FC', note: 'quête Mor’Ladim' },
    { id: 'hotw', name: 'Hide of the Wild', slot: 'back', st: { int: 10, sta: 8, heal: 42 }, tag: 'FC', note: 'niv. 57, +14 dégâts (1/3)' },
    { id: 'radiant', name: 'Radiant Staff', slot: '2h', st: { int: 19, sta: 19, sp: 56 }, tag: 'FC', note: 'Enchantement 220, niv. 45' },
    { id: 'dreamstaff', name: 'Dreamstaff', slot: '2h', st: { spi: 19, sta: 19, heal: 105 }, tag: 'FC', note: 'Enchantement 220, niv. 45' },
    { id: 'glimmer', name: 'Glimmering Staff', slot: '2h', st: { int: 11, sta: 11, sp: 34 }, tag: 'FC', note: 'Enchantement 140, niv. 25' },
    { id: 'soulstaff', name: 'Soulstaff', slot: '2h', st: { spi: 11, sta: 11, sp: 34 }, tag: 'FC', note: 'Enchantement 140, niv. 25' },
    { id: 'westfall', name: 'Staff of Westfall', slot: '2h', st: { int: 5, spi: 6, heal: 48 }, tag: 'FC', note: 'aperçu du panel' },
    { id: 'orbmystic', name: 'Orb of Mystic Insight', slot: 'offhand', st: { int: 6, sp: 7 }, tag: 'FC', note: 'niv. 25' },
    { id: 'truesilver', name: 'Truesilver Conduit', slot: 'offhand', st: { int: 8, sta: 8, sp: 10 }, tag: 'FC', note: 'niv. 45' },
    { id: 'orbsouls', name: 'Orb of Souls', slot: 'offhand', st: { spi: 6, heal: 13 }, tag: 'FC', note: 'niv. 25' },
    { id: 'twisting', name: 'Twisting Essence Jar', slot: 'offhand', st: { spi: 8, sta: 8, heal: 19 }, tag: 'FC', note: 'niv. 45' },
    { id: 'bwand', name: 'Brilliant Wand', slot: 'ranged', st: { int: 7, sp: 9 }, tag: 'FC', note: 'niv. 55, 59,6 DPS' },
    { id: 'lionheart', name: 'Lionheart Helm', slot: 'head', st: { str: 18, hit: 2, crit: 2 }, tag: 'FC', note: 'plaques, niv. 56' }
  ];
  const ENCHANTS = [
    { id: 'e_brsp', name: 'Bracelets : Greater Spellpower', slot: 'wrist', st: { sp: 16 }, tag: 'FC' },
    { id: 'e_brint', name: 'Bracelets : Superior Intellect', slot: 'wrist', st: { int: 9 }, tag: 'FC' },
    { id: 'e_brheal', name: 'Bracelets : Lesser Healing Power', slot: 'wrist', st: { heal: 16 }, tag: 'FC' },
    { id: 'e_brdef', name: 'Bracelets : Superior Deflection', slot: 'wrist', st: { def: 9 }, tag: 'FC' },
    { id: 'e_necksp', name: 'Cou : Spell Power', slot: 'neck', st: { sp: 6 }, tag: 'FC' },
    { id: 'e_neckheal', name: 'Cou : Healing Power', slot: 'neck', st: { heal: 11 }, tag: 'FC' },
    { id: 'e_neckdef', name: 'Cou : Deflection', slot: 'neck', st: { def: 5 }, tag: 'FC' },
    { id: 'e_2hsp', name: 'Arme 2M : Mighty Spell Power', slot: '2h', st: { sp: 55 }, tag: 'FC' },
    { id: 'e_2hheal', name: 'Arme 2M : Mighty Healing Power', slot: '2h', st: { heal: 100 }, tag: 'FC' },
    { id: 'e_glarc', name: 'Gants : Arcane Power', slot: 'hands', st: { arcane: 20 }, tag: 'FC' }
  ];
  const SLOTS = { head: 'Tête', neck: 'Cou', shoulder: 'Épaules', back: 'Dos', chest: 'Torse', wrist: 'Poignets', hands: 'Mains', waist: 'Taille', legs: 'Jambes', feet: 'Pieds', finger: 'Doigt', trinket: 'Bijou', '2h': 'Arme 2M', mainhand: 'Main droite', offhand: 'Main gauche', ranged: 'Baguette' };
  const SLOT_MOD = { head: 1, chest: 1, legs: 1, '2h': 1, shoulder: 0.77, hands: 0.77, waist: 0.77, feet: 0.77, wrist: 0.56, neck: 0.56, back: 0.56, finger: 0.56, offhand: 0.56, trinket: 0.7, mainhand: 0.56, ranged: 0.56 };
  const STAT_COST = { int: 1, spi: 1, sta: 1, str: 1, agi: 1, sp: 0.86, heal: 0.46, school: 0.7, crit: 14, hit: 10, mp5: 2.5, ap: 0.5, def: 1.2 };
  const STAT_NAMES = { int: 'Intelligence', spi: 'Esprit', sta: 'Endurance', str: 'Force', agi: 'Agilité', sp: 'Puissance des sorts', heal: 'Soins', school: 'Dégâts d’école', arcane: 'Dégâts Arcane', fire: 'Dégâts Feu', frost: 'Dégâts Givre', shadow: 'Dégâts Ombre', crit: 'Crit %', hit: 'Toucher %', mp5: 'mp5', ap: 'PA', def: 'Défense', armor: 'Armure', hp: 'PV', dodge: 'Esquive %', parry: 'Parade %', block: 'Blocage %' };

  const SOURCES = [
    ['Blizzard, annonce WoW Forever', 'https://news.blizzard.com/en-us/article/24302093/carve-a-new-path-with-world-of-warcraft-forever'],
    ['Blizzard, récap du Deep Dive', 'https://news.blizzard.com/en-us/article/24303313/world-of-warcraft-forever-deep-dive-panel-recap'],
    ['talentsforever.com (talents, raciaux, diff de builds)', 'https://talentsforever.com/'],
    ['wowforevertalents.com (datamine client vs Classic Era)', 'https://wowforevertalents.com/'],
    ['foreverchanges.pro (sorts, objets, métiers)', 'https://foreverchanges.pro/'],
    ['foreverdiff.com (diff de tooltips)', 'https://foreverdiff.com/'],
    ['Wowhead Forever', 'https://www.wowhead.com/forever'],
    ['wago.tools (tables DB2)', 'https://wago.tools'],
    ['MythicSim, tier list DPS', 'https://mythicsim.com/wow-forever/tier-list'],
    ['ElliotWood/Forever (sims, APL Mage)', 'https://github.com/ElliotWood/Forever'],
    ['wowsims/forever (buffs, débuffs, consommables)', 'https://github.com/wowsims/forever'],
    ['gunba/wow-forever-sim', 'https://github.com/gunba/wow-forever-sim'],
    ['wow.gg, recettes d’Alchimie', 'https://wow.gg/guides/wow-forever-new-recipes-alchemy'],
    ['wow.gg, recettes de Cuisine', 'https://wow.gg/guides/wow-forever-new-recipes-cooking'],
    ['Blizzard Watch, enchantements', 'https://blizzardwatch.com/2026/09/21/every-new-enchant-world-warcraft-forever/'],
    ['Output Lag, hit/crit unifiés', 'https://outputlag.com/news/world-of-warcraft-forever-unifies-hit-and-crit-stats-and-gives-healing-gear-bonus-damage/'],
    ['Icy Veins, rangs PvP', 'https://www.icy-veins.com/wow-forever/pvp-rank-system'],
    ['classicwow.gg, composition de raid', 'https://classicwow.gg/forever/guides/raid-comp'],
    ['Warcraft Tavern, stats', 'https://www.warcrafttavern.com/forever/guides/stats/'],
    ['LFCarry, double spé', 'https://lfcarry.com/guides/wow-forever-dual-spec'],
    ['Forum Blizzard, Beta Client Update 22/09', 'https://us.forums.blizzard.com/en/wow/t/beta-client-update-september-22/2358655'],
    ['PatchBot (alerte de build)', 'https://patchbot.io/games/world-of-warcraft-forever'],
    ['Zockify, raids (buffs de monde)', 'https://www.zockify.com/forever/raids/']
  ];
  const MONITOR = [
    'wago.tools — tables DB2 brutes, détection de build',
    'foreverdiff.com — diff tooltip Forever contre Classic Era',
    'foreverchanges.pro — objets, recettes, bandeau de build',
    'talentsforever.com/data.json — talents et raciaux en JSON',
    'github.com/wowsims/forever — buffs, débuffs, consommables datamined',
    'github.com/ElliotWood/Forever — sims et APL, valeurs vérifiées client',
    'wowhead.com/forever — tooltips et news',
    'us.forums.blizzard.com (WoW Forever) — posts bleus, notes de build',
    'patchbot.io — alerte de nouveau build',
    'wow.gg — nouvelles recettes',
    'icy-veins.com/wow-forever — PvP et systèmes'
  ];

  const META = { build: '1.60.1.69977', date: '2026-09-23', release: '4 novembre 2026', beta: '17/09 → 21/10, niveau max 20 puis 30' };

  return { TAGS, P, CLASSES, RACES, SPECS, FLAGS, BUFFS, COE_SCHOOLS_DEFAULT, WORLD, CONS, CONS_GROUPS, POTIONS, PRO_SETS, STAGES, CRITERIA, SCORES, PROFILES, LEVEL_CURVES, SP_LEVELING, SPIKES, VERDICTS, DUAL, RACIALS_PVP, PVP_RULES, ITEMS, ENCHANTS, SLOTS, SLOT_MOD, STAT_COST, STAT_NAMES, SOURCES, MONITOR, META };
})();
if (typeof module !== 'undefined') module.exports = DATA;
