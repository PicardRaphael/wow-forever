// Pont Python -> moteur analytique de raid (engine.js). Entrée JSON sur stdin :
// {spec:'frost'|'fire'|'arcane', ctx:{...}, params:{id:valeur}, flags:{...}, variant:{...}}
const D = require('./legacy-data.js'), E = require('./engine.js');
let raw = ''; process.stdin.on('data', c => raw += c).on('end', () => {
  const input = JSON.parse(raw), many = Array.isArray(input), qs = many ? input : [input];
  const res = qs.map(q => {
  const PM = {}; D.P.forEach(r => PM[r[0]] = r[1]);
  Object.assign(PM, q.params || {});
  const p = id => { if (!(id in PM)) throw new Error('paramètre manquant ' + id); return PM[id]; };
  const c = q.ctx;
  const t = { T: c.T, d: 3, crit: c.crit, H: c.H, R: () => c.R, dm: () => c.dm || 1, sp: () => c.sp, healPow: 0, healMult: 1,
              haste: c.haste || 1, costMult: 1, baseMana: c.baseMana, pool: c.pool, regen: c.regen || 5, manaExtra: 0, flags: q.flags || {} };
  const out = E.MODELS[q.spec](t, p, q.variant || {});
  return { dps: out.dps, mps: out.mps, parts: out.parts, info: out.info };
  });
  process.stdout.write(JSON.stringify(many ? res : res[0]));
});
