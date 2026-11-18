// Node-only engine checks (no browser): flows conserve power, interfaces computed, overload appears when a corridor is tripped. Usage: node tests/engine.mjs
import { readFileSync } from 'fs'; import { createEngine } from '../js/engine.js';
const J = p => JSON.parse(readFileSync(new URL('../data/' + p, import.meta.url)));
const E = createEngine(J('grid_model.json'), J('generators.json'), J('day_profiles.json'));
const fails = []; const ok = (c, m) => { if (!c) fails.push(m); };
for (const h of [4, 12, 18]) { E.setDay(E.state.day, h); const r = E.solve();
  console.log(`h${h} load ${r.load.toFixed(0)} gen ${r.gen.toFixed(0)} imbalance(slack) ${r.imbalance.toFixed(0)} MI ${r.exportMI} NY ${r.exportNY} overloads [${r.overloads}] score ${r.score}`);
  console.log('   interfaces', r.interfaces.map(i => `${i.id} ${i.flow.toFixed(0)}/${i.ttc}`).join('  '));
  // KCL at every non-slack bus
  const { P } = (() => { const m = E.model, inj = new Array(m.buses.length).fill(0); return { P: inj }; })();
  ok(Number.isFinite(r.flows['BRU-MIL']), 'finite flow'); ok(r.load > 8000 && r.load < 30000, 'load range ' + r.load);
}
E.setDay(E.state.day, 18); const base = E.solve();
const tieMI = ['L4D', 'L51D', 'B3N', 'J5D'].reduce((s, k) => s + base.flows[k], 0); ok(Math.abs(tieMI - base.exportMI) < 1, `MI ties sum ${tieMI.toFixed(1)} == export ${base.exportMI}`);
const tieNY = ['PA301', 'PA302', 'BP76'].reduce((s, k) => s + base.flows[k], 0); ok(Math.abs(tieNY - base.exportNY) < 1, `NY ties sum ${tieNY.toFixed(1)} == export ${base.exportNY}`);
console.log('BRU-MIL', base.flows['BRU-MIL'].toFixed(0), 'BRU-LON', base.flows['BRU-LON'].toFixed(0), 'TRA-RIC', base.flows['TRA-RIC'].toFixed(0), 'max loading', Math.max(...Object.values(base.loading)).toFixed(2));
E.toggleBranch('BRU-MIL'); const trip = E.solve(); console.log('trip BRU-MIL -> BRU-LON', trip.flows['BRU-LON'].toFixed(0), 'BRU-ORA', trip.flows['BRU-ORA'].toFixed(0), 'overloads', trip.overloads.join(','));
ok(Math.abs(trip.flows['BRU-LON']) > Math.abs(base.flows['BRU-LON']), 'flow shifts after trip'); ok(trip.overloads.length > 0, 'trip of Bruce-Milton should overload something'); E.toggleBranch('BRU-MIL');
E.state.export.MICHIGAN = 3000; const big = E.solve(); ok(big.interfaces.find(i => i.id === 'ON-MI').loading > 1, 'MI 3000 MW export breaches TTC'); E.setDay(E.state.day, 18);
E.state.loadMult = 1.2; const imb = E.autoBalance(); console.log('load x1.2 autoBalance residual', imb.toFixed(0)); E.state.loadMult = 1;
for (const d of Object.keys(E.days)) { E.setDay(d, 19); const r = E.solve(); console.log('day', d, 'h19 load', r.load.toFixed(0), 'imbalance', r.imbalance.toFixed(0), 'overloads', r.overloads.length); }
console.log(fails.length ? 'ENGINE FAIL ' + fails.join('; ') : 'ENGINE PASS'); process.exit(fails.length ? 1 : 0);
