/** Hydro-Lines grid engine (pure ES module, no DOM): hourly load, unit dispatch, intertie schedules, DC power flow, limits and interfaces.
 *  Works in the browser and in Node (tests/engine.mjs). All parameters come from data/grid_model.json; see SOURCES.md for what is ESTIMATE. */
export function createEngine(model, gens, profiles) {
  const B = model.buses, idx = Object.fromEntries(B.map((b, i) => [b.id, i])), slack = idx[model.slack];
  const units = gens.units, days = Object.fromEntries(profiles.days.map(d => [d.id, d]));
  const state = { day: profiles.default, hour: 18, loadMult: 1, mw: {}, avail: {}, export: { MICHIGAN: 0, 'NEW-YORK': 0 }, out: new Set() };
  function setDay(id, hour = state.hour) {
    state.day = id; state.hour = hour; const d = days[id], h = hour - 1;
    const ref = days[profiles.default];
    for (const u of units) { state.avail[u.id] ??= true; state.mw[u.id] = Math.min(u.out_h[h] || 0, cap(u)); }
    const it = (d.intertie_h || ref.intertie_h);
    for (const k of ['MICHIGAN', 'NEW-YORK']) { const a = it[k].actual_flow_h[h]; state.export[k] = d.intertie_h ? Math.round(a ?? it[k].sched_net_export_h[h] ?? 0) : 0; }
    if (d.dispatch === 'auto') autoBalance();
    return state;
  }
  const cap = u => state.avail[u.id] === false ? 0 : (u.cap_h[state.hour - 1] ?? u.max_cap_mw ?? 0);
  function loads() {
    const d = days[state.day], h = state.hour - 1, L = new Array(B.length).fill(0);
    for (const [zone, w] of Object.entries(model.load_weights)) { const z = d.zonal_h[zone]; if (!z) continue; for (const [bus, f] of Object.entries(w)) L[idx[bus]] += z[h] * f * state.loadMult; }
    return L;
  }
  function otherExport() { const d = days[state.day]; return d.other_net_export_h ? d.other_net_export_h[state.hour - 1] : 0; }
  /** Net injections (MW) and the balance the slack (REST) must supply on top of its own scheduled units/load. */
  function injections() {
    const P = new Array(B.length).fill(0), L = loads();
    for (const u of units) P[idx[u.bus]] += Math.min(state.mw[u.id] || 0, cap(u));
    for (let i = 0; i < B.length; i++) P[i] -= L[i];
    P[idx.MI] -= state.export.MICHIGAN; P[idx.NY] -= state.export['NEW-YORK']; P[slack] -= otherExport();
    const imbalance = P.reduce((a, b) => a + b, 0); // >0 surplus, <0 deficit; slack absorbs it
    return { P, L, imbalance };
  }
  function components(active) {
    const adj = B.map(() => []); for (const br of active) { adj[idx[br.a]].push(idx[br.b]); adj[idx[br.b]].push(idx[br.a]); }
    const comp = new Array(B.length).fill(-1); let c = 0;
    for (let s = 0; s < B.length; s++) { if (comp[s] >= 0) continue; const st = [s]; comp[s] = c; while (st.length) { const n = st.pop(); for (const m of adj[n]) if (comp[m] < 0) { comp[m] = c; st.push(m); } } c++; }
    return comp;
  }
  function solve() {
    const active = model.branches.filter(b => !state.out.has(b.id));
    const { P, L, imbalance } = injections(); const comp = components(active), sc = comp[slack];
    let shed = 0, spill = 0; const island = B.map((_, i) => comp[i] !== sc);
    const Pp = P.slice(); for (let i = 0; i < B.length; i++) if (island[i]) { if (P[i] < 0) shed += -P[i]; else spill += P[i]; Pp[i] = 0; }
    const n = B.length, keep = [...Array(n).keys()].filter(i => i !== slack && !island[i]), pos = Object.fromEntries(keep.map((k, j) => [k, j]));
    const m = keep.length, A = Array.from({ length: m }, () => new Float64Array(m + 1));
    for (const br of active) { const a = idx[br.a], b = idx[br.b]; if (island[a]) continue; const y = 1 / br.x_pu;
      if (a !== slack) A[pos[a]][pos[a]] += y; if (b !== slack) A[pos[b]][pos[b]] += y; if (a !== slack && b !== slack) { A[pos[a]][pos[b]] -= y; A[pos[b]][pos[a]] -= y; } }
    keep.forEach((k, j) => A[j][m] = Pp[k] / model.base_mva);
    for (let c = 0; c < m; c++) { let p = c; for (let r = c + 1; r < m; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r; [A[c], A[p]] = [A[p], A[c]];
      const d = A[c][c] || 1e-12; for (let r = 0; r < m; r++) { if (r === c) continue; const f = A[r][c] / d; if (f) for (let k = c; k <= m; k++) A[r][k] -= f * A[c][k]; } }
    const th = new Float64Array(n); keep.forEach((k, j) => th[k] = A[j][m] / (A[j][j] || 1e-12));
    const flows = {}, loading = {};
    for (const br of model.branches) { const on = !state.out.has(br.id) && !island[idx[br.a]]; const f = on ? (th[idx[br.a]] - th[idx[br.b]]) / br.x_pu * model.base_mva : 0; flows[br.id] = f; loading[br.id] = Math.abs(f) / br.limit_mw; }
    const ifs = model.interfaces.map(I => { const f = I.branches.reduce((s, [id, sg]) => s + sg * (flows[id] || 0), 0); const lim = f >= 0 ? I.ttc_mw : (I.ttc_rev_mw ?? I.ttc_mw); return { id: I.id, name: I.name, flow: f, ttc: lim, loading: Math.abs(f) / lim }; });
    const over = model.branches.filter(b => loading[b.id] > 1).map(b => b.id);
    const gen = units.reduce((s, u) => s + Math.min(state.mw[u.id] || 0, cap(u)), 0), load = L.reduce((a, b) => a + b, 0);
    return { flows, loading, interfaces: ifs, overloads: over, island: B.filter((_, i) => island[i]).map(b => b.id), shed, spill, imbalance, slackMW: -imbalance, gen, load,
      exportMI: state.export.MICHIGAN, exportNY: state.export['NEW-YORK'], otherExport: otherExport(), score: score(over, ifs, imbalance, shed) };
  }
  function score(over, ifs, imb, shed) { // 100 = no overloads, balanced; each overload/interface breach and MW of slack/shed costs points
    return Math.max(0, Math.round(100 - 15 * over.length - 10 * ifs.filter(i => i.loading > 1).length - Math.abs(imb) / 100 - shed / 20));
  }
  /** Move dispatchable gas/hydro/storage units (pro rata to headroom or output) until the imbalance is ~0. */
  function autoBalance() {
    const disp = units.filter(u => ['GAS', 'HYDRO', 'OTHER'].includes(u.fuel) && cap(u) > 0);
    for (let it = 0; it < 4; it++) {
      const imb = injections().imbalance; if (Math.abs(imb) < 1) break;
      const room = disp.map(u => imb < 0 ? cap(u) - (state.mw[u.id] || 0) : (state.mw[u.id] || 0)), tot = room.reduce((a, b) => a + b, 0); if (tot <= 0) break;
      const f = Math.min(1, Math.abs(imb) / tot); disp.forEach((u, i) => state.mw[u.id] = Math.max(0, Math.min(cap(u), (state.mw[u.id] || 0) + (imb < 0 ? 1 : -1) * f * room[i])));
    }
    return injections().imbalance;
  }
  const setUnit = (id, mw) => { state.mw[id] = Math.max(0, mw); };
  const setStation = (st, frac) => { for (const id of st.units) { const u = units.find(x => x.id === id); state.mw[id] = cap(u) * frac; } };
  const toggleBranch = id => { state.out.has(id) ? state.out.delete(id) : state.out.add(id); };
  return { state, setDay, solve, autoBalance, setUnit, setStation, toggleBranch, cap, loads, days, units, model };
}
