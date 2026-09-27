/* ===== Moteur de calcul — fonctions pures, testées en Node ===== */
const ENGINE = (function () {
  const clamp01 = x => Math.max(0, Math.min(1, x));
  const dmg = (avg, k, sp) => avg + k * sp;

  // Part du combat couverte par un effet (durée dur, recharge cd, utilisé dès le pull)
  function uptime(T, dur, cd) {
    if (!(T > 0) || !(dur > 0)) return 0;
    if (!(cd > 0)) return Math.min(1, dur / T);
    let s = 0;
    for (let t0 = 0; t0 < T - 1e-9; t0 += cd) s += Math.min(dur, T - t0);
    return Math.min(1, s / T);
  }
  function uses(T, cd) { return cd > 0 ? Math.floor((T - 1e-9) / cd) + 1 : 1; }

  // Hot Streak : nombre moyen d'incantations pour atteindre 3 cumuls, les cumuls expirant
  // après m incantations sans critique. Chaîne de Markov (états 0,1,2).
  function hotStreakEvents(p, m) {
    if (!(p > 0)) return Infinity;
    if (p >= 1) return 3;
    m = Math.max(1, Math.floor(m));
    const r = 1 - p, q = Math.pow(r, m), A = 1 - q;
    let B = 0;
    for (let j = 1; j <= m; j++) B += j * Math.pow(r, j - 1) * p;
    const den = 1 - q * (1 + A);
    if (den <= 1e-12) return Infinity;
    return (1 / p + (1 + A) * (B + q * m)) / den;
  }

  const HIT_PARAM = { frost: 'frost.hitT', fire: 'fire.hitT', arcane: 'arc.hitT', shadow: 'sh.hitT', affli: 'aff.hitT', demo: 'demo.hitT', destro: 'des.hitT' };
  const REGEN_PARAM = { frost: 'frost.regen', fire: 'fire.regen', arcane: 'arc.regen', shadow: 'sh.regen', holyp: 'hp.regen', disc: 'hp.regen', holypal: 'hpal.regen' };

  function flagsFor(S, spec, D) {
    const out = {};
    (D.FLAGS[spec.id] || []).forEach(([k, , def]) => {
      const v = S.flags && S.flags[spec.id] ? S.flags[spec.id][k] : undefined;
      out[k] = v === undefined ? def : !!v;
    });
    return out;
  }

  // ---------- Totaux de fiche (équipement + buffs + consommables + raciaux + talents)
  function totals(S, spec, p, D) {
    const cls = spec.cls;
    const g = Object.assign({ int: 0, spi: 0, sta: 0, sp: 0, school: 0, heal: 0, crit: 0, hit: 0, mp5: 0, mana: 0, hp: 0, armor: 0, dodge: 0, parry: 0, block: 0 }, S.gear || {});
    const T = Math.max(10, +S.T || 120);
    const d = Math.max(0, Math.min(3, S.d === undefined ? 3 : +S.d));
    const acc = { int: 0, spi: 0, sta: 0, stats: 0, pct: [], sp: 0, heal: 0, crit: 0, hit: 0, mp5: 0, armor: 0, hp: 0, mana: 0, school: {}, dmgMult: 1, healMult: 1, spUp: 0, healUp: 0, manaExtra: 0, intBuff: 0, spiBuff: 0, coe: 0 };
    const apply = fx => {
      for (const k in fx) {
        const v = fx[k];
        switch (k) {
          case 'int': case 'spi': case 'sta': case 'stats': case 'sp': case 'heal': case 'crit': case 'hit': case 'mp5': case 'armor': case 'hp': case 'mana':
            acc[k] += p(v); break;
          case 'pct': acc.pct.push(p(v)); break;
          case 'school': for (const s in v) acc.school[s] = (acc.school[s] || 0) + p(v[s]); break;
          case 'dmgPct': acc.dmgMult *= 1 + p(v); break;
          case 'dmgUp': acc.dmgMult *= 1 + p(v[0]) * uptime(T, p(v[1]), p(v[2])); break;
          case 'healUp': acc.healMult *= 1 + p(v[0]) * uptime(T, p(v[1]), p(v[2])); break;
          case 'coe': acc.coe = p(v); break;
          case 'intBuff': acc.intBuff = Math.max(acc.intBuff, p(v)); break;
          case 'spiBuff': acc.spiBuff = Math.max(acc.spiBuff, p(v)); break;
          case 'manaUse': acc.manaExtra += p(v[0]) * uses(T, p(v[1])); break;
        }
      }
    };
    const sel = S.sel || {};
    D.BUFFS.forEach(b => { if (sel.buffs && sel.buffs[b.id]) apply(b.fx); });
    const wbActive = S.ctx === 'monde' || !!S.forceWB;
    if (wbActive) D.WORLD.forEach(b => { if (sel.wb && sel.wb[b.id]) apply(b.fx); });
    D.CONS.forEach(c => { if (sel.cons && sel.cons[c.id]) apply(c.fx); });
    acc.int += acc.intBuff; acc.spi += acc.spiBuff;

    const pot = sel.potion || 'none';
    if (pot === 'spellblast') acc.spUp += p('c.spellblast') * uptime(T, p('c.spellblast.dur'), p('k.potCd'));
    if (pot === 'mender') acc.healUp += p('c.mender') * uptime(T, p('c.mender.dur'), p('k.potCd'));
    if (pot === 'manapot') acc.manaExtra += p('c.manapot') * uses(T, p('k.potCd'));

    const race = D.RACES[S.race] || { fx: [] };
    let spMult = 1, haste = 1, critUp = 0, manaMult = 1, racialMult = 1, costMult = 1;
    if (race.fx.includes('bloodfury')) spMult *= 1 + p('r.bloodfury') * uptime(T, p('r.bloodfury.dur'), p('r.bloodfury.cd'));
    if (race.fx.includes('berserk')) haste *= 1 + p('r.berserk') * uptime(T, p('r.berserk.dur'), p('r.berserk.cd'));
    if (race.fx.includes('wind')) haste *= 1 + p('r.wind');
    if (race.fx.includes('elune')) critUp += p('r.elune') * uptime(T, p('r.elune.dur'), p('r.elune.cd'));
    if (race.fx.includes('expmind')) manaMult *= 1 + p('r.expmind');
    if (race.fx.includes('eureka')) {
      const frac = Math.min(1, 3 * uses(T, p('r.eureka.cd')) * 2.5 / T);
      racialMult *= 1 + p('r.eureka') * frac;
      costMult *= 1 - (spec.role === 'heal' ? 0.15 : 0.5) * frac; // soigneurs : −15 % de mana, DPS : −50 %
    }

    let intTal = 0;
    if (spec.id === 'arcane') intTal += p('arc.mindInt');
    if (spec.id === 'disc') intTal += p('disc.ms');
    const statMult = acc.pct.reduce((m, x) => m * (1 + x), 1);
    const intT = (g.int + acc.int + acc.stats) * statMult * (1 + intTal);
    const spiT = (g.spi + acc.spi + acc.stats) * statMult;
    const staT = (g.sta + acc.sta + acc.stats) * statMult;
    const critPct = p('k.bc.' + cls) + intT / p('k.ipc.' + cls) + g.crit + acc.crit + critUp;
    const hitPct = g.hit + acc.hit + (HIT_PARAM[spec.id] ? p(HIT_PARAM[spec.id]) : 0);

    const flags = flagsFor(S, spec, D);
    const healOnly = g.heal + acc.heal;
    const spGen = g.sp + acc.sp + acc.spUp;
    const dk = spec.id === 'demo' ? p('demo.dk') : 0;
    const sp = s => (spGen + (s === spec.school ? g.school : 0) + (acc.school[s] || 0) + healOnly / 3 + dk) * spMult;
    const sgOn = spec.id === 'holyp' && flags.sg;
    const healPow = spGen + healOnly + acc.healUp + (sgOn ? p('hp.sg') * spiT : 0);

    const coeSchools = S.coeSchools || D.COE_SCHOOLS_DEFAULT;
    const coeOn = s => acc.coe > 0 && coeSchools.includes(s);
    const dm = s => acc.dmgMult * racialMult * (coeOn(s) ? 1 + acc.coe : 1);
    const R = s => coeOn(s) ? 0 : p('k.resPerLvl') * d;
    const H0 = [p('k.h0_0'), p('k.h0_1'), p('k.h0_2'), p('k.h0_3')][d];
    const H = Math.min(p('k.hitcap'), H0 + hitPct / 100);

    const flagsEarly = flagsFor(S, spec, D);
    if (cls === 'mage' && flagsEarly.gem) acc.manaExtra += p('mage.gem') * uses(T, p('mage.gemCd'));
    const bm = p('k.bm.' + cls);
    const pool = g.mana > 0
      ? (g.mana + p('k.manaPerInt') * (intT - g.int) + acc.mana) * manaMult
      : (bm + 20 + p('k.manaPerInt') * Math.max(0, intT - 20) + acc.mana) * manaMult;
    const a = p('k.sr.' + cls + '.a'), dv = p('k.sr.' + cls + '.d');
    const combat = REGEN_PARAM[spec.id] ? p(REGEN_PARAM[spec.id]) : 0;
    const mp5 = g.mp5 + acc.mp5;
    const regen = mp5 / 5 + ((a + spiT / dv) / 2) * combat;

    return {
      spec, cls, T, d, intT, spiT, staT, critPct, crit: clamp01(critPct / 100), hitPct, H, R, dm, sp, spGen, healOnly,
      healPow, healMult: acc.healMult * racialMult, haste, costMult, baseMana: bm, pool, regen, manaExtra: acc.manaExtra, mp5,
      armor: g.armor + acc.armor, hp: g.hp + acc.hp + Math.max(0, staT - g.sta) * 10, flags, coe: acc.coe, wbActive, dmgMult: acc.dmgMult * racialMult
    };
  }

  // ---------- Modèles de rotation (DPS moyen sur un cycle)
  const MODELS = {
    frost(t, p) {
      const sp = t.sp('frost'), H = t.H, hf = H * (1 - t.R('frost'));
      const mult = (1 + p('frost.piercing')) * t.dm('frost');
      const b = p('k.critBase') * (1 + p('frost.shards'));
      const wc = t.flags.wc ? p('frost.wc') : 0;
      const cFB = clamp01(t.crit + wc), cIL = clamp01(t.crit + wc + p('frost.shatter'));
      const castFB = p('frost.fbCast') / t.haste, gcd = p('k.gcd') / t.haste;
      const dFB = dmg(p('frost.fbAvg'), p('frost.fbK'), sp) * mult * hf * (1 + cFB * b);
      const pIL = t.flags.fof ? p('frost.fof') * H : 0;
      const dIL = dmg(p('frost.ilAvg'), p('frost.ilK'), sp) * p('frost.ilFrozen') * mult * hf * (1 + cIL * b);
      const time = castFB + pIL * gcd;
      return {
        dps: (dFB + pIL * dIL) / time,
        mps: (p('frost.fbMana') + pIL * p('frost.ilMana')) * t.costMult / time,
        parts: [['Éclair de givre', dFB / time], ['Javelot de glace (Fingers of Frost)', pIL * dIL / time]],
        info: { dFB, dIL, pIL, cFB, cIL, fbDps: dFB / castFB }
      };
    },

    fire(t, p, v) {
      const sp = t.sp('fire'), H = t.H, hf = H * (1 - t.R('fire'));
      const mult = (1 + p('fire.power')) * (1 + p('fire.scorchStack')) * t.dm('fire');
      const b = p('k.critBase'), ig = p('fire.ignite'), dc = p('k.dotCrit') > 0;
      const cFB = clamp01(t.crit + p('fire.critT') / 100), cBl = clamp01(cFB + p('fire.incin') / 100);
      const castFB = p('fire.fbCast') / t.haste, gcd = p('k.gcd') / t.haste;
      const direct = (avg, k, c) => { const nc = dmg(avg, k, sp) * mult; return hf * nc * (1 + c * b) + hf * c * (1 + b) * nc * ig; };
      const dot = (base, k, c) => dmg(base, k, sp) * mult * hf * (dc ? 1 + c * b : 1);
      const dFB = direct(p('fire.fbAvg'), p('fire.fbK'), cFB) + dot(p('fire.fbDot'), 0, cFB);
      const dBl = direct(p('fire.blAvg'), p('fire.blK'), cBl);
      const dSc = direct(p('fire.scAvg'), p('fire.scK'), cBl);
      const dPy = direct(p('fire.pyAvg'), p('fire.pyKd'), cFB) + dot(p('fire.pyDot'), p('fire.pyKdot'), cFB);
      const blCd = p('fire.blCd');
      const blastOn = v && v.blast !== undefined ? v.blast : t.flags.blast;
      const rBl = blastOn && blCd > gcd ? castFB / (blCd - gcd) : 0; // Traits de feu par Boule de feu
      const pEv = (cFB * H + rBl * cBl * H) / (1 + rBl);
      const tEv = (castFB + rBl * gcd) / (1 + rBl);
      const E0 = t.flags.hs ? hotStreakEvents(pEv, Math.floor(p('fire.hsWin') / tEv)) : Infinity;
      const n = isFinite(E0) ? E0 : 1, nPy = isFinite(E0) ? 1 : 0;
      const nFB = n / (1 + rBl), nBl = n * rBl / (1 + rBl);
      const baseTime = n * tEv + nPy * p('fire.hsCast') / t.haste;
      const every = p('fire.scEvery');
      const share = every > gcd ? gcd / every : 0;
      const time = baseTime / (1 - share);
      const nSc = share > 0 ? time / every : 0;
      const total = nFB * dFB + nBl * dBl + nPy * dPy + nSc * dSc;
      const mana = nFB * p('fire.fbMana') + nBl * p('fire.blMana') + nPy * p('fire.pyMana') + nSc * p('fire.scMana');
      return {
        dps: total / time, mps: mana * t.costMult / time,
        parts: [['Boule de feu (+ Ignite)', nFB * dFB / time], ['Trait de feu', nBl * dBl / time], ['Explosion pyrotechnique (Hot Streak)', nPy * dPy / time], ['Brûlure (entretien)', nSc * dSc / time]],
        info: { dFB, fbDps: dFB / castFB, E0, pyroEvery: nPy ? time : Infinity, cFB, blast: !!blastOn }
      };
    },

    arcane(t, p, v) {
      const sp = t.sp('arcane'), H = t.H, hf = H * (1 - t.R('arcane'));
      const upAP = t.flags.ap ? uptime(t.T, p('arc.apDur'), p('arc.apCd')) : 0;
      const mult = (1 + p('arc.inst')) * (1 + p('arc.ap') * upAP) * t.dm('arcane');
      const b = p('k.critBase') * (1 + p('arc.mind'));
      const c = clamp01(t.crit + p('arc.inst') + p('arc.impact') / 100);
      const n = Math.max(1, Math.round(v && v.stacks ? v.stacks : p('arc.stacks')));
      const dAB = dmg(p('arc.abAvg'), p('arc.abK'), sp) * mult * hf * (1 + c * b);
      const dAM = dmg(p('arc.amTotal'), p('arc.amK'), sp) * mult * (1 + n * p('arc.abStackDmg')) * hf * (1 + c * b);
      const pMB = 1 - Math.pow(1 - p('arc.mb') * H, n);
      const tAM = p('arc.amDur') * (pMB * 0.5 + (1 - pMB));
      const time = (n * p('arc.abCast') + tAM) / t.haste;
      const abBase = p('arc.abCost') * t.baseMana;
      const seq = abBase * (n + p('arc.abStackCost') * n * (n - 1) / 2);
      const mana = (seq + p('arc.amMana') * (1 - pMB)) * (1 + p('arc.ap') * upAP) * (1 - p('arc.cc') * H) * t.costMult;
      return {
        dps: (n * dAB + dAM) / time, mps: mana / time,
        parts: [['Déflagration des Arcanes', n * dAB / time], ['Projectiles des arcanes', dAM / time]],
        info: { pMB, upAP, seqCost: seq, stacks: n }
      };
    },

    shadow(t, p) {
      const sp = t.sp('shadow'), H = t.H, hf = H * (1 - t.R('shadow'));
      const mult = (1 + p('sh.sf')) * (1 + p('sh.weave')) * t.dm('shadow');
      const b = p('k.critBase') * (1 + p('sh.sfBonus')), c = clamp01(t.crit), dc = p('k.dotCrit') > 0 ? 1 : 0;
      const gcd = p('k.gcd') / t.haste;
      const dSWP = dmg(p('sh.swpTotal'), p('sh.swpK'), sp) * mult * hf * (1 + c * b * dc);
      const dMB = dmg(p('sh.mbAvg'), p('sh.mbK'), sp) * mult * hf * (1 + c * b);
      const dMF = dmg(p('sh.mfTotal'), p('sh.mfK'), sp) * mult * hf * (1 + c * b * dc);
      const dSWD = dmg(p('sh.swdAvg'), p('sh.swdK'), sp) * mult * hf * (1 + c * b);
      const L = p('sh.swpDur');
      const nMB = t.flags.mb ? L / p('sh.mbCd') : 0;
      const nSWD = t.flags.swd ? L / p('sh.swdCd') : 0;
      const rem = Math.max(0, L - gcd * (1 + nSWD) - nMB * gcd);
      const nMF = rem / (p('sh.mfDur') / t.haste);
      const total = dSWP + nMB * dMB + nSWD * dSWD + nMF * dMF;
      const mana = (p('sh.swpMana') + nMB * p('sh.mbMana') + nSWD * p('sh.swdMana') + nMF * p('sh.mfMana')) * (1 - p('sh.sfCost')) * t.costMult;
      return {
        dps: total / L, mps: mana / L,
        parts: [['Mot de l’ombre : Douleur', dSWP / L], ['Attaque mentale', nMB * dMB / L], ['Mot de l’ombre : Mort', nSWD * dSWD / L], ['Fouet mental', nMF * dMF / L]],
        info: { dMF, mfDps: dMF / p('sh.mfDur') }
      };
    },

    affli(t, p) {
      const sp = t.sp('shadow'), H = t.H, hf = H * (1 - t.R('shadow')), dc = p('k.dotCrit') > 0 ? 1 : 0;
      const dm = t.dm('shadow'), sm = 1 + p('aff.sm'), mal = 1 + p('aff.mal');
      const c = clamp01(t.crit + p('aff.malev') / 100);
      const bDot = p('k.critBase') * (1 + p('aff.pand')), bSB = p('k.critBase');
      const gcd = p('k.gcd') / t.haste, sbCast = p('wl.sbCast') / t.haste;
      const dCorr = dmg(p('aff.corrTotal'), p('aff.corrK'), sp) * (1 + p('aff.impCorr')) * mal * sm * dm * hf * (1 + c * bDot * dc);
      const dAg = dmg(p('aff.agTotal'), p('aff.agK'), sp) * mal * sm * dm * hf * (1 + c * bDot * dc);
      const dSB = dmg(p('wl.sbAvg'), p('wl.sbK'), sp) * sm * dm * hf * (1 + c * bSB);
      const L = p('aff.corrDur');
      const nAg = t.flags.agony ? L / p('aff.agDur') : 0;
      const procs = t.flags.nf ? 6 * p('aff.nf') * H : 0;
      const rem = Math.max(0, L - gcd * (1 + nAg));
      const nSB = (rem + procs * (sbCast - gcd)) / sbCast;
      const total = dCorr + nAg * dAg + nSB * dSB;
      const mana = (p('aff.corrMana') + nAg * p('aff.agMana') + nSB * p('wl.sbMana')) * t.costMult;
      return {
        dps: total / L, mps: mana / L, lifeTap: true,
        parts: [['Corruption', dCorr / L], ['Fléau d’agonie', nAg * dAg / L], ['Trait de l’ombre (+ Nightfall)', nSB * dSB / L]],
        info: { dCorr, procs }
      };
    },

    demo(t, p) {
      const sp = t.sp('shadow'), H = t.H, hf = H * (1 - t.R('shadow')), dc = p('k.dotCrit') > 0 ? 1 : 0;
      const mult = (1 + p('demo.sac')) * (1 + p('demo.md')) * (1 + p('demo.sl')) * t.dm('shadow');
      const c = clamp01(t.crit), b = p('k.critBase');
      const gcd = p('k.gcd') / t.haste, sbCast = p('wl.sbCast') / t.haste;
      const dCorr = dmg(p('aff.corrTotal'), p('aff.corrK'), sp) * (1 + p('aff.impCorr')) * mult * hf * (1 + c * b * dc);
      const dSB = dmg(p('wl.sbAvg'), p('wl.sbK'), sp) * mult * hf * (1 + c * b);
      const L = p('aff.corrDur');
      const nSB = Math.max(0, L - gcd) / sbCast;
      const total = dCorr + nSB * dSB;
      const mana = (p('aff.corrMana') + nSB * p('wl.sbMana')) * t.costMult;
      return {
        dps: total / L, mps: mana / L, lifeTap: true, pet: p('demo.pet'),
        parts: [['Corruption', dCorr / L], ['Trait de l’ombre', nSB * dSB / L], ['Démon (saisi)', p('demo.pet')]],
        info: { dSB }
      };
    },

    destro(t, p) {
      const sp = t.sp('fire'), H = t.H, hf = H * (1 - t.R('fire')), dc = p('k.dotCrit') > 0 ? 1 : 0;
      const dm = t.dm('fire'), af = 1 + p('des.af');
      const b = p('k.critBase') * (1 + p('des.ruin')), c = clamp01(t.crit);
      const immCast = p('des.immCast') / t.haste, incCast = p('des.incCast') / t.haste;
      const dImm = dmg(p('des.immD'), p('des.immKd'), sp) * af * dm * hf * (1 + c * b) + dmg(p('des.immDot'), p('des.immKdot'), sp) * af * dm * hf * (1 + c * b * dc);
      const dInc = dmg(p('des.incAvg'), p('des.incK'), sp) * af * (1 + p('des.incImm')) * dm * hf * (1 + c * b);
      const L = p('des.immDur');
      const nInc = Math.max(0, L - immCast) / incCast;
      const total = dImm + nInc * dInc;
      const mana = (p('des.immMana') + nInc * p('des.incMana')) * t.costMult;
      const spS = t.sp('shadow'), hfS = H * (1 - t.R('shadow'));
      const dSB = dmg(p('wl.sbAvg'), p('wl.sbK'), spS) * (1 + p('des.sm')) * af * t.dm('shadow') * hfS * (1 + c * b);
      return {
        dps: total / L, mps: mana / L, lifeTap: true,
        parts: [['Immolation', dImm / L], ['Incinérer', nInc * dInc / L]],
        info: { incDps: dInc / incCast, sbDps: dSB / (p('wl.sbCast') / t.haste) }
      };
    }
  };

  // ---------- Soins
  function heal(id, t, p) {
    const c = t.crit, bH = p('k.healCrit'), hp = t.healPow, hm = t.healMult;
    const rows = [];
    const add = (name, avg, k, cast, mana, o) => {
      const base = (avg + k * hp) * hm;
      let h = base * (1 + c * bH);
      if (o.da) h += c * o.da * base * (1 + bH);
      const ct = cast / t.haste;
      const m = mana * t.costMult * (1 - (o.illum ? c * o.illum : 0));
      const spend = m / ct;
      const oom = spend > t.regen ? (t.pool + t.manaExtra) / (spend - t.regen) : Infinity;
      const casts = Math.min(t.T / ct, (t.pool + t.manaExtra + t.regen * t.T) / m);
      rows.push({ name, heal: h, cast: ct, mana: m, hps: h / ct, hpm: h / m, oom, total: casts * h, sustained: casts * h / t.T });
    };
    if (id === 'holyp' || id === 'disc') add('Soins supérieurs', p('hp.ghAvg'), p('hp.ghK'), p('hp.ghCast'), p('hp.ghMana'), { da: id === 'disc' ? p('disc.da') : 0 });
    if (id === 'holypal') {
      add('Lumière sacrée', p('hpal.hlAvg'), p('hpal.hlK'), p('hpal.hlCast'), p('hpal.hlMana'), { illum: p('hpal.illum') });
      add('Éclair lumineux', p('hpal.folAvg'), p('hpal.folK'), p('hpal.folCast'), p('hpal.folMana'), { illum: p('hpal.illum') });
    }
    return rows;
  }

  // ---------- Tank
  function tank(t, p, S) {
    const g = S.gear || {};
    const armor = t.armor, K = p('k.armorK');
    const dr = Math.min(0.75, armor / (armor + K));
    const hp = t.hp;
    const speed = p('prot.speed');
    const sealDps = p('prot.seal') / speed;
    return {
      dr, hp, armor, ehp: hp / (1 - dr), avoid: 5 + (+g.dodge || 0) + (+g.parry || 0),
      block: (+g.block || 0) + p('prot.hsBlock'), sealDps, tps: sealDps * p('prot.rf'), absorbPs: p('prot.seal') * p('prot.absorb') / speed
    };
  }

  // ---------- Soutenabilité mana (Connexion, Évocation, baguette en repli)
  function sustain(t, rot, p, v) {
    const S = rot.mps, r = t.regen, T = t.T;
    if (rot.lifeTap) {
      const L = p('wl.lt') / (p('k.gcd') / t.haste);
      const avail = (t.pool + t.manaExtra) / T;
      const factor = S <= 0 ? 1 : Math.min(1, (avail + r + L) / (S + L));
      return { factor, active: 1, oom: Infinity, spend: S, regen: r, tap: 1 - factor, evoc: 0 };
    }
    const nEv = v && v.evoc ? uses(T, p('mage.evocCd')) : 0;
    const active = Math.max(0, 1 - nEv * p('mage.evocDur') / T);
    const extra = t.manaExtra + nEv * p('mage.evoc') * t.pool;
    const need = S * active * T;
    const factor = need <= 0 ? 1 : Math.min(1, (t.pool + extra + r * T) / need);
    const oom = S > r ? (t.pool + t.manaExtra) / (S - r) : Infinity;
    return { factor, active, oom, spend: S, regen: r, tap: 0, evoc: nEv };
  }

  function variantsFor(spec, t, p) {
    let vs = [{}];
    if (spec.id === 'arcane') { vs = []; const mx = Math.max(1, Math.round(p('arc.stacks'))); for (let n = 1; n <= mx; n++) vs.push({ stacks: n }); }
    if (spec.id === 'fire') vs = t.flags.blast ? [{ blast: true }, { blast: false }] : [{ blast: false }];
    if (spec.cls === 'mage' && t.flags.evoc) vs = vs.concat(vs.map(x => Object.assign({}, x, { evoc: true })));
    return vs;
  }

  function evaluate(S, specId, p, D) {
    const spec = D.SPECS.find(s => s.id === specId);
    const t = totals(S, spec, p, D);
    if (spec.role === 'dps') {
      let best = null;
      const wand = spec.cls === 'warlock' ? 0 : p('k.wand');
      for (const v of variantsFor(spec, t, p)) {
        const rot = MODELS[spec.id](t, p, v);
        const su = sustain(t, rot, p, v);
        const pet = rot.pet || 0;
        const dpsEff = su.active * (rot.dps * su.factor + (1 - su.factor) * wand) + pet;
        if (!best || dpsEff > best.dpsEff + 1e-9) best = { spec, t, rot, su, v, dps: rot.dps + pet, dpsEff };
      }
      return best;
    }
    if (spec.role === 'heal') {
      const rows = heal(spec.id, t, p);
      return { spec, t, heal: rows, metric: rows[0] ? rows[0].sustained : 0 };
    }
    const tk = tank(t, p, S);
    return { spec, t, tank: tk, metric: tk.ehp };
  }

  function metricOf(ev) { return ev.spec.role === 'dps' ? ev.dpsEff : ev.metric; }

  // Poids de stats par différences finies (métrique : DPS effectif, soins soutenus ou EHP)
  function weights(S, specId, p, D) {
    const base = evaluate(S, specId, p, D);
    const m0 = metricOf(base);
    const deltas = base.spec.role === 'tank'
      ? [['armor', 100], ['hp', 100]]
      : base.spec.role === 'heal'
        ? [['heal', 10], ['crit', 1], ['int', 10], ['spi', 10], ['mp5', 5]]
        : [['sp', 10], ['school', 10], ['crit', 1], ['hit', 1], ['int', 10], ['spi', 10], ['mp5', 5]];
    const out = {};
    deltas.forEach(([k, dlt]) => {
      const S2 = Object.assign({}, S, { gear: Object.assign({}, S.gear) });
      S2.gear[k] = (+S2.gear[k] || 0) + dlt;
      out[k] = (metricOf(evaluate(S2, specId, p, D)) - m0) / dlt;
    });
    return { base, m0, w: out };
  }

  return { clamp01, uptime, uses, hotStreakEvents, totals, MODELS, heal, tank, sustain, evaluate, metricOf, weights };
})();
if (typeof module !== 'undefined') module.exports = ENGINE;
