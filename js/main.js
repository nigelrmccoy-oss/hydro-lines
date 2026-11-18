/** Hydro-Lines v0.1.0 placeholder shell: Cesium globe (vendored, keyless) + OSM grid layers + engine overlay + history/planned layers.
 *  The designed UI (Explorer tree etc.) comes later; everything here reads the same data/registry.json-style records. */
import { makeTerrain } from './terrain.js';
import { createEngine } from './engine.js';
const C = window.Cesium, $ = id => document.getElementById(id);
const J = u => fetch(u).then(r => { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); });
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const banner = $('banner'), tip = $('mapTip'), fp = $('faceplate');
const imagery = new C.UrlTemplateImageryProvider({ url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', maximumLevel: 19, credit: 'Powered by Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community' });
const viewer = new C.Viewer('globe', { baseLayer: new C.ImageryLayer(imagery), terrainProvider: makeTerrain(), geocoder: false, baseLayerPicker: false, timeline: false, animation: false, homeButton: false, sceneModePicker: false, navigationHelpButton: false, infoBox: false, selectionIndicator: false, fullscreenButton: false });
viewer.scene.globe.depthTestAgainstTerrain = false; viewer.scene.globe.maximumScreenSpaceError = 1.5;
const VIEWS = { on: [-80.6, 40.2, 5.2e5, -50, 'SW Ontario'], kw: [-80.45, 43.2, 6.5e4, -45, 'Waterloo Region'], gta: [-79.55, 43.25, 9e4, -45, 'GTA'], bruce: [-81.6, 44.1, 6e4, -45, 'Bruce'], niagara: [-79.1, 42.95, 4e4, -45, 'Niagara'], sarnia: [-82.5, 42.55, 6e4, -45, 'Sarnia/Windsor'] };
const hs = new URLSearchParams(location.hash.slice(1));
function fly(k, dur = 2) { const v = VIEWS[k]; if (!v) return; viewer.camera.flyTo({ destination: C.Cartesian3.fromDegrees(v[0], v[1], v[2]), orientation: { heading: 0, pitch: C.Math.toRadians(v[3]) }, duration: dur }); hs.set('view', k); writeHash(); }
function writeHash() { try { history.replaceState(null, '', '#' + hs.toString()); } catch (e) { } }
$('views').innerHTML = Object.entries(VIEWS).map(([k, v]) => `<button data-fly="${k}">${v[4]}</button>`).join(''); $('views').onclick = e => e.target.dataset.fly && fly(e.target.dataset.fly);
fly(VIEWS[hs.get('view')] ? hs.get('view') : 'on', 0);

const [lines, subs, model, gens, prof, hist, planned, reg, srcs] = await Promise.all(['lines.geojson', 'substations.geojson', 'grid_model.json', 'generators.json', 'day_profiles.json', 'history.json', 'planned.geojson', 'registry.json', 'sources.json'].map(f => J('data/' + f)));
const SRC = srcs.sources, srcLinks = ids => (ids || []).map(i => SRC[i] ? `<a href="${esc(SRC[i].url)}" target="_blank" rel="noopener" title="${esc(SRC[i].title)}">[${esc(i)}]</a>` : `[${esc(i)}]`).join(' ');
const E = createEngine(model, gens, prof);
const KVC = { 500: '#ff3b3b', 345: '#ff9f1a', 230: '#ffd400', 115: '#3fd0ff' };
const layers = { kv500: true, kv345: true, kv230: true, kv115: true, subs: true, plants: true, flows: true, planned: false, history: false };
const groups = {}; const add = (g, o) => (groups[g] ||= []).push(o);
const byId = {}; // registry id -> record for popups / deep links

// ---------- OSM lines by kV (real geometry) ----------
const per = {}; const wayFeat = {};
for (const f of lines.features) { const p = f.properties, kv = p.kv >= 500 ? 500 : p.kv >= 345 ? 345 : p.kv >= 230 ? 230 : 115; wayFeat[p.osm] = f;
  (per[kv] ||= []).push(new C.GeometryInstance({ geometry: new C.GroundPolylineGeometry({ positions: C.Cartesian3.fromDegreesArray(f.geometry.coordinates.flat()), width: kv >= 500 ? 3 : kv >= 230 ? 2 : 1.5 }), id: { kind: 'osmline', p }, attributes: { color: C.ColorGeometryInstanceAttribute.fromColor(C.Color.fromCssColorString(KVC[kv]).withAlpha(0.8)) } }));
  byId['osm:' + p.osm] = { kind: 'osmline', p }; }
for (const [kv, inst] of Object.entries(per)) add('kv' + kv, viewer.scene.groundPrimitives.add(new C.GroundPolylinePrimitive({ geometryInstances: inst, appearance: new C.PolylineColorAppearance(), asynchronous: true })));
// ---------- substations ----------
const pts = viewer.scene.primitives.add(new C.PointPrimitiveCollection()), labs = viewer.scene.primitives.add(new C.LabelCollection());
for (const f of subs.features) { const p = f.properties, [lon, lat] = f.geometry.coordinates, kv = p.kv || 115; if (p.country === 'US' && kv < 345) continue;
  const o = pts.add({ position: C.Cartesian3.fromDegrees(lon, lat, 30), pixelSize: kv >= 500 ? 9 : kv >= 230 ? 6 : 4, color: C.Color.fromCssColorString(KVC[kv] || '#ccc'), outlineColor: C.Color.BLACK, outlineWidth: 1, disableDepthTestDistance: Infinity, id: { kind: 'sub', p } }); add('subs', o);
  if (p.name && kv >= 230) add('subs', labs.add({ position: C.Cartesian3.fromDegrees(lon, lat, 30), text: p.name, font: '11px system-ui', fillColor: C.Color.WHITE, outlineColor: C.Color.BLACK, outlineWidth: 3, style: C.LabelStyle.FILL_AND_OUTLINE, pixelOffset: new C.Cartesian2(8, -8), disableDepthTestDistance: Infinity, distanceDisplayCondition: new C.DistanceDisplayCondition(0, kv >= 500 ? 4e5 : 1.2e5) }));
  byId['osm:' + p.osm] = { kind: 'sub', p }; }
// ---------- generating stations (IESO units grouped) ----------
const FC = { NUCLEAR: '#b061ff', HYDRO: '#2e86ff', GAS: '#ff7a1a', WIND: '#7dff7a', SOLAR: '#ffe14d', OTHER: '#00e0c0', BIOFUEL: '#9b7b4b' };
for (const st of gens.stations) { const o = pts.add({ position: C.Cartesian3.fromDegrees(st.lon, st.lat, 40), pixelSize: 8 + Math.sqrt(st.cap_mw_20261116 || 1) / 5, color: C.Color.fromCssColorString(FC[st.fuel]), outlineColor: C.Color.WHITE, outlineWidth: 2, disableDepthTestDistance: Infinity, id: { kind: 'station', st } }); add('plants', o);
  add('plants', labs.add({ position: C.Cartesian3.fromDegrees(st.lon, st.lat, 40), text: st.name, font: 'bold 12px system-ui', fillColor: C.Color.fromCssColorString(FC[st.fuel]), outlineColor: C.Color.BLACK, outlineWidth: 3, style: C.LabelStyle.FILL_AND_OUTLINE, pixelOffset: new C.Cartesian2(10, 10), disableDepthTestDistance: Infinity, distanceDisplayCondition: new C.DistanceDisplayCondition(0, 6e5) }));
  byId[st.id] = { kind: 'station', st }; }
// ---------- engine branches: OSM ways recoloured by loading, schematic line when no traced path ----------
const BP = Object.fromEntries(model.buses.map(b => [b.id, b]));
const flowPolys = {};
for (const br of model.branches) {
  const segs = br.osm_ways.length ? br.osm_ways.map(w => wayFeat[w]?.geometry.coordinates).filter(Boolean) : [[[BP[br.a].lon, BP[br.a].lat], [BP[br.b].lon, BP[br.b].lat]]];
  flowPolys[br.id] = segs.map(cs => { const e = viewer.entities.add({ polyline: { positions: C.Cartesian3.fromDegreesArrayHeights(cs.flatMap(c => [c[0], c[1], 600])), width: br.kv >= 500 ? 6 : 4, material: br.osm_ways.length ? C.Color.WHITE : new C.PolylineDashMaterialProperty({ color: C.Color.WHITE }), arcType: C.ArcType.GEODESIC } }); e.hl = { kind: 'branch', br }; add('flows', e); return e; });
  byId['br:' + br.id] = { kind: 'branch', br };
}
for (const b of model.buses) byId['bus:' + b.id] = { kind: 'bus', b };
// ---------- planned + history ----------
for (const f of planned.features) { const p = f.properties, g = f.geometry; let e;
  if (g.type === 'LineString') e = viewer.entities.add({ polyline: { positions: C.Cartesian3.fromDegreesArrayHeights(g.coordinates.flatMap(c => [c[0], c[1], 900])), width: 3, material: new C.PolylineDashMaterialProperty({ color: C.Color.fromCssColorString('#ff4fd8'), dashLength: 24 }) } });
  else e = viewer.entities.add({ position: C.Cartesian3.fromDegrees(g.coordinates[0], g.coordinates[1], 900), point: { pixelSize: 10, color: C.Color.fromCssColorString('#ff4fd8'), outlineColor: C.Color.WHITE, outlineWidth: 2, disableDepthTestDistance: Infinity }, label: { text: p.name, font: '11px system-ui', fillColor: C.Color.fromCssColorString('#ffb3f0'), outlineColor: C.Color.BLACK, outlineWidth: 3, style: C.LabelStyle.FILL_AND_OUTLINE, pixelOffset: new C.Cartesian2(10, -10), disableDepthTestDistance: Infinity, distanceDisplayCondition: new C.DistanceDisplayCondition(0, 1.5e5) } });
  e.hl = { kind: 'planned', p }; add('planned', e); byId['plan:' + p.id] = { kind: 'planned', p }; }
const histEnts = hist.events.map(ev => { const e = viewer.entities.add({ position: C.Cartesian3.fromDegrees(ev.lon, ev.lat, 1200), point: { pixelSize: 11, color: C.Color.GOLD, outlineColor: C.Color.BLACK, outlineWidth: 2, disableDepthTestDistance: Infinity }, label: { text: `${ev.date} ${ev.title}`, font: '11px system-ui', fillColor: C.Color.GOLD, outlineColor: C.Color.BLACK, outlineWidth: 3, style: C.LabelStyle.FILL_AND_OUTLINE, pixelOffset: new C.Cartesian2(10, 12), disableDepthTestDistance: Infinity } }); e.hl = { kind: 'event', ev }; byId['hist:' + ev.id] = { kind: 'event', ev }; return e; });
function showYear(y) { $('yearv').textContent = y; hs.set('year', y); writeHash();
  histEnts.forEach((e, i) => { const ev = hist.events[i]; e.show = layers.history && ev.year <= y; e.point.color = ev.year === y ? C.Color.RED : ev.type === 'retirement' ? C.Color.GRAY : C.Color.GOLD; e.label.show = ev.year === y || (y - ev.year < 3); });
  $('hlist').innerHTML = hist.events.filter(ev => ev.year <= y).slice(-14).reverse().map(ev => `<div class="${ev.year === y ? 'now' : ''}" data-ev="${ev.id}">${esc(ev.date)} · ${esc(ev.title)}${ev.est ? ' <span class="est">ESTIMATE</span>' : ''}</div>`).join(''); }
$('year').oninput = e => showYear(+e.target.value); $('hlist').onclick = e => { const id = e.target.closest('[data-ev]')?.dataset.ev; if (id) openId('hist:' + id); };

// ---------- layer toggles ----------
const LBL = { kv500: '500 kV', kv345: '345 kV', kv230: '230 kV', kv115: '115 kV', subs: 'Stations', plants: 'Generation', flows: 'Flows (model)', planned: 'Planned', history: 'History' };
function apply() { for (const [k, on] of Object.entries(layers)) (groups[k] || []).forEach(o => o.show = on); $('hist').classList.toggle('hidden', !layers.history); showYear(+$('year').value);
  document.querySelectorAll('#layers button').forEach(b => b.classList.toggle('on', layers[b.dataset.l])); hs.set('layers', Object.keys(layers).filter(k => layers[k]).join(',')); writeHash(); }
$('layers').innerHTML = Object.entries(LBL).map(([k, v]) => `<button data-l="${k}">${v}</button>`).join(''); $('layers').onclick = e => { const k = e.target.dataset.l; if (k) { layers[k] = !layers[k]; apply(); } };
if (hs.get('layers')) { const on = new Set(hs.get('layers').split(',')); for (const k in layers) layers[k] = on.has(k); }
if (hs.get('year')) $('year').value = hs.get('year');
$('mapLegend').innerHTML = `<b>Lines (OSM)</b><br>${[500, 345, 230, 115].map(k => `<i style="background:${KVC[k]}"></i>${k} kV`).join('<br>')}<br><b>Flows</b> (model loading)<br><i style="background:#5f5"></i>&lt;70% <i style="background:#fd0"></i>70-100% <i style="background:#f33"></i>&gt;100%<br><i style="background:#fff;height:2px"></i>dashed = schematic route<br><b>Generation</b> ${Object.entries(FC).map(([k, c]) => `<i style="background:${c};width:8px"></i>${k.toLowerCase()}`).join(' ')}<br><i style="background:#ff4fd8"></i>Planned (schematic)<br><span class="est">ESTIMATE</span> = not from a source`;

// ---------- game controls ----------
$('day').innerHTML = prof.days.map(d => `<option value="${d.id}">${esc(d.label)}</option>`).join('');
const stOf = Object.fromEntries(gens.stations.flatMap(s => s.units.map(u => [u, s])));
function dispatchList() { const rows = gens.stations.filter(s => s.cap_mw_20261116 > 0).map(s => { const mw = s.units.reduce((a, u) => a + (E.state.mw[u] || 0), 0), cap = s.units.reduce((a, u) => a + E.cap(gens.units.find(x => x.id === u)), 0);
  return `<div><span style="color:${FC[s.fuel]}">${esc(s.name)}</span><input type="range" min="0" max="1" step="0.01" value="${cap ? mw / cap : 0}" data-st="${esc(s.id)}" /><b>${Math.round(mw)}</b></div>`; });
  const other = gens.units.filter(u => !stOf[u.id]).reduce((a, u) => a + (E.state.mw[u.id] || 0), 0);
  $('dlist').innerHTML = rows.join('') + `<div><span>Other units (${gens.units.filter(u => !stOf[u.id]).length})</span><span></span><b>${Math.round(other)}</b></div>`; }
$('dlist').oninput = e => { const id = e.target.dataset.st; if (!id) return; E.setStation(gens.stations.find(s => s.id === id), +e.target.value); update(false); };
function syncControls() { $('day').value = E.state.day; $('hour').value = E.state.hour; $('hourv').textContent = String(E.state.hour).padStart(2, '0') + 'h'; $('lm').value = E.state.loadMult; $('lmv').textContent = E.state.loadMult.toFixed(2);
  $('mi').value = E.state.export.MICHIGAN; $('miv').textContent = E.state.export.MICHIGAN; $('ny').value = E.state.export['NEW-YORK']; $('nyv').textContent = E.state.export['NEW-YORK']; }
const colorFor = l => l > 1 ? C.Color.fromCssColorString('#ff3333') : l > 0.7 ? C.Color.fromCssColorString('#ffdd00') : C.Color.fromCssColorString('#55ff55');
let R = null;
function update(list = true) {
  R = E.solve();
  for (const br of model.branches) { const l = R.loading[br.id], col = E.state.out.has(br.id) ? C.Color.GRAY.withAlpha(0.6) : colorFor(l).withAlpha(0.9);
    for (const e of flowPolys[br.id]) { e.polyline.material = br.osm_ways.length ? new C.ColorMaterialProperty(col) : new C.PolylineDashMaterialProperty({ color: col }); e.polyline.width = l > 1 ? 9 : br.kv >= 500 ? 6 : 4; } }
  const I = Object.fromEntries(R.interfaces.map(i => [i.id, i]));
  const k = (n, v, cls = '') => `<div class="${cls}"><span>${n}</span>${v}</div>`;
  $('kpis').innerHTML = k('Score', R.score, R.score < 70 ? 'bad' : '') + k('Load (model)', Math.round(R.load) + ' MW') + k('Generation', Math.round(R.gen) + ' MW') + k('REST/slack', `${Math.round(R.slackMW)} MW`, Math.abs(R.slackMW) > 1500 ? 'warn' : '') +
    k('MI', `${R.exportMI > 0 ? 'export' : 'import'} ${Math.abs(R.exportMI)} MW`, I['ON-MI'].loading > 1 ? 'bad' : '') + k('NY', `${R.exportNY > 0 ? 'export' : 'import'} ${Math.abs(R.exportNY)} MW`, I['ON-NY'].loading > 1 ? 'bad' : '') +
    ['FETT', 'QFW'].map(n => k(n, `${Math.round(I[n].flow)} / ${I[n].ttc} MW`, I[n].loading > 1 ? 'bad' : I[n].loading > 0.8 ? 'warn' : '')).join('') +
    k('Overloads', R.overloads.length ? R.overloads.join(', ') : 'none', R.overloads.length ? 'bad' : '') + (R.shed ? k('Islanded load', Math.round(R.shed) + ' MW', 'bad') : '') + k('', '<span class="est">limits & reactances ESTIMATE</span>');
  if (list) dispatchList(); syncControls(); hs.set('day', E.state.day); hs.set('hour', E.state.hour); writeHash();
  if (fp.dataset.open?.startsWith('br:')) openId(fp.dataset.open, false);
}
$('day').onchange = e => { E.setDay(e.target.value, E.state.hour); update(); };
$('hour').oninput = e => { E.setDay(E.state.day, +e.target.value); update(); };
$('lm').oninput = e => { E.state.loadMult = +e.target.value; update(false); };
$('mi').oninput = e => { E.state.export.MICHIGAN = +e.target.value; update(false); }; $('ny').oninput = e => { E.state.export['NEW-YORK'] = +e.target.value; update(false); };
$('bal').onclick = () => { E.autoBalance(); update(); }; $('reset').onclick = () => { E.state.loadMult = 1; E.state.out.clear(); E.setDay(E.state.day, E.state.hour); update(); };
let timer = null; $('play').onclick = () => { if (timer) { clearInterval(timer); timer = null; $('play').textContent = '▶'; return; } $('play').textContent = '❚❚'; timer = setInterval(() => { E.setDay(E.state.day, E.state.hour % 24 + 1); update(); }, 1500); };

// ---------- popups: registry-style Name / Type / Value table ----------
const row = (n, v, t = typeof v) => `<tr><td>${esc(n)}</td><td>${esc(t)}</td><td>${v}</td></tr>`;
const flag = b => b ? ' <span class="est">ESTIMATE</span>' : '';
function table(rec) {
  if (rec.kind === 'osmline' || rec.kind === 'sub') { const p = rec.p; return [`<h3>${esc(p.name || p.ref || (rec.kind === 'sub' ? 'Substation' : 'Line'))}</h3>`, '<table>', row('kV', esc(p.kvs.join(' / ')), 'kV'), row('operator', esc(p.operator || '—')),
    ...(p.length_km ? [row('length', p.length_km.toFixed(2) + ' km (segment)', 'km')] : []), ...Object.entries(p.tags).map(([k, v]) => row('osm:' + k, esc(v), 'tag')), row('source', `<a href="${esc(p.source_url)}" target="_blank">${esc(p.osm)}</a> ${srcLinks(['osm'])}`, 'url'), '</table>'].join(''); }
  if (rec.kind === 'branch') { const b = rec.br, f = R?.flows[b.id] ?? 0, l = R?.loading[b.id] ?? 0;
    return [`<h3>${esc(b.id)} · ${b.kv} kV ${b.tie ? 'intertie' : 'corridor'}</h3><button id="trip">${E.state.out.has(b.id) ? 'Restore' : 'Trip (outage)'}</button><table>`, row('from → to', `${esc(BP[b.a].name)} → ${esc(BP[b.b].name)}`, 'str'),
      row('flow (model)', `${Math.round(f)} MW (${Math.round(l * 100)}% of limit)`, 'MW'), row('limit', `${b.limit_mw} MW${flag(b.limit_est)} <small>${esc(b.limit_note)}</small>`, 'MW'), row('circuits', b.circuits + flag(b.circuits_est), 'int'),
      row('length', b.length_km + ' km' + flag(b.length_est), 'km'), row('reactance', b.x_pu + ' pu' + flag(true), 'pu'), row('OSM refs', esc(b.osm_refs.join(', ') || '—'), 'tag'), row('OSM ways', b.osm_ways.length, 'int'), row('note', esc(b.note), 'str'), row('sources', srcLinks(b.src), 'url'), '</table>'].join(''); }
  if (rec.kind === 'station') { const s = rec.st, us = s.units.map(id => gens.units.find(u => u.id === id));
    return [`<h3>${esc(s.name)}</h3><table>`, row('fuel', esc(s.fuel)), row('capability 2026-11-16', s.cap_mw_20261116 + ' MW', 'MW'), row('model bus', esc(BP[s.bus].name) + flag(us[0]?.bus_est), 'bus'), row('position', `${s.lon.toFixed(4)}, ${s.lat.toFixed(4)}${flag(s.pos_est)}${s.osm ? ` <a href="${esc(s.osm)}" target="_blank">${esc(s.osm_name)}</a>` : ''}`, 'lonlat'),
      ...us.map(u => row(u.id, `${Math.round(E.state.mw[u.id] || 0)} / ${Math.round(E.cap(u))} MW`, 'unit')), row('sources', srcLinks(s.src), 'url'), '</table>'].join(''); }
  if (rec.kind === 'planned') { const p = rec.p; return [`<h3>${esc(p.name)}</h3><table>`, row('kind', esc(p.kind)), row('voltage', p.kv ? p.kv + ' kV' : '—', 'kV'), row('in service', esc(p.isd) + flag(p.isd_est), 'date'), row('status', esc(p.status)), row('detail', esc(p.detail)), row('geometry', esc(p.note) + flag(p.route_est || p.pos_est)), row('sources', srcLinks(p.src), 'url'), '</table>'].join(''); }
  if (rec.kind === 'event') { const e = rec.ev; return [`<h3>${esc(e.title)}</h3><table>`, row('date', esc(e.date) + flag(e.est), 'date'), row('type', esc(e.type)), row('detail', esc(e.detail)), row('sources', srcLinks(e.src), 'url'), '</table>'].join(''); }
  if (rec.kind === 'bus') { const b = rec.b; return [`<h3>${esc(b.name)}</h3><table>`, row('kind', esc(b.kind)), row('IESO zone', esc(b.zone || '—')), row('position', `${b.lon}, ${b.lat}${flag(b.pos_est)}`, 'lonlat'), row('OSM', b.osm ? `<a href="${esc(b.osm)}" target="_blank">${esc(b.osm_name || 'element')}</a>` : '—', 'url'), row('note', esc(b.note || '')), '</table>'].join(''); }
  return '<h3>?</h3>';
}
function recId(rec) { return rec.kind === 'osmline' || rec.kind === 'sub' ? 'osm:' + rec.p.osm : rec.kind === 'branch' ? 'br:' + rec.br.id : rec.kind === 'station' ? rec.st.id : rec.kind === 'planned' ? 'plan:' + rec.p.id : rec.kind === 'event' ? 'hist:' + rec.ev.id : 'bus:' + rec.b.id; }
function openId(id, flyTo = true) { const rec = byId[id]; if (!rec) { fp.innerHTML = `<h3>Not found</h3><code>${esc(id)}</code>`; fp.classList.remove('hidden'); return; }
  fp.innerHTML = `<button style="float:right" id="fpx">✕</button>` + table(rec); fp.dataset.open = id; fp.classList.remove('hidden'); $('fpx').onclick = () => { fp.classList.add('hidden'); fp.dataset.open = ''; hs.delete('open'); writeHash(); };
  const t = $('trip'); if (t) t.onclick = () => { E.toggleBranch(rec.br.id); update(); };
  hs.set('open', id); writeHash();
  if (flyTo) { const r = reg.entities.find(x => x.id === id); const ll = r ? [r.lon, r.lat] : rec.p?.source_url && rec.kind === 'sub' ? rec.p && null : null;
    const pos = ll || (rec.kind === 'sub' ? rec.p && subs.features.find(f => f.properties.osm === rec.p.osm)?.geometry.coordinates : rec.kind === 'osmline' ? wayFeat[rec.p.osm].geometry.coordinates[0] : null);
    if (pos) viewer.camera.flyTo({ destination: C.Cartesian3.fromDegrees(pos[0], pos[1] - 0.25, 3.5e4), orientation: { heading: 0, pitch: C.Math.toRadians(-45) }, duration: 1.5 }); } }
function pickAt(pos) { const p = viewer.scene.pick(pos); if (!p) return null; const id = p.id; if (id?.hl) return id.hl; if (id?.kind) return id; return null; }
const hnd = new C.ScreenSpaceEventHandler(viewer.scene.canvas);
hnd.setInputAction(m => { const r = pickAt(m.position); if (r) openId(recId(r), false); }, C.ScreenSpaceEventType.LEFT_CLICK);
hnd.setInputAction(m => { const r = pickAt(m.endPosition); if (!r) { tip.style.display = 'none'; return; } tip.style.display = 'block'; tip.style.left = m.endPosition.x + 14 + 'px'; tip.style.top = m.endPosition.y + 14 + 'px';
  tip.textContent = r.kind === 'branch' ? `${r.br.id} ${r.br.kv} kV · ${Math.round(R.flows[r.br.id])} MW (${Math.round(R.loading[r.br.id] * 100)}%)` : r.kind === 'station' ? `${r.st.name} · ${r.st.fuel}` : r.kind === 'event' ? `${r.ev.date} ${r.ev.title}` : r.kind === 'planned' ? `Planned: ${r.p.name} (${r.p.isd})` : `${r.p.name || r.p.ref || ''} ${r.p.kvs.join('/')} kV`; }, C.ScreenSpaceEventType.MOUSE_MOVE);

// ---------- start ----------
E.setDay(prof.days.find(d => d.id === hs.get('day')) ? hs.get('day') : prof.default, Math.min(24, Math.max(1, +hs.get('hour') || 18)));
apply(); update();
if (hs.get('open')) openId(hs.get('open'), !hs.get('view'));
banner.innerHTML = `Imagery: Esri World Imagery · Terrain: <a href="https://registry.opendata.aws/terrain-tiles/" target="_blank">AWS Terrain Tiles</a> · Grid: © OpenStreetMap contributors (ODbL) · Demand/units/interties: IESO public reports (2026-11-16) · cross-check: Gridwatch · Plans: IESO, Hydro One, OEB · Unofficial; model values marked ESTIMATE · v0.1.0`;
window.HL = { viewer, E, model, gens, prof, hist, planned, reg, layers, groups, apply, update, openId, fly, byId, get R() { return R; }, version: '0.1.0' };

// ---------- #tour: scripted click-through for on-display QA ----------
if (hs.has('tour')) { const S = [() => fly('on'), () => fly('kw'), () => openId('br:MID-PRE'), () => { E.toggleBranch('BRU-MIL'); update(); fly('on'); }, () => { E.toggleBranch('BRU-MIL'); update(); layers.planned = true; apply(); fly('gta'); }, () => { layers.history = true; apply(); $('year').value = 2013; showYear(2013); fly('on'); }];
  let i = 0; const step = () => { try { S[i](); document.title = 'TOUR ' + i; } catch (e) { document.title = 'TOUR ERR ' + i; console.error(e); } if (++i < S.length) setTimeout(step, 15000); }; setTimeout(step, 3000); }
