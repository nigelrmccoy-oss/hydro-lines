# HYDRO-LINES v0.1.0: Ontario power grid game (SW Ontario + GTA slice)

Interactive 3D globe (CesiumJS, vendored, **no API keys**; Esri World Imagery + AWS Terrain Tiles) with the real transmission network from OpenStreetMap and a small DC power-flow game engine driven by IESO public data. Same no-build pattern as `swo-pipelines`: vanilla ES modules, vendored libs. **Unofficial**, public data only, nothing beyond what public maps and reports show.

## Run
```bash
python3 tools/serve.py 8790          # http://127.0.0.1:8790/  (localhost only)
tools/run_tests.sh                   # engine + headless smoke (flock'd, 15-min cap, logs in logs/)
```

## What's in v0.1.0
- **Layers** (toggle buttons): OSM lines 500 / 345 / 230 / 115 kV (3,100 ways incl. Michigan/NY side, circuit refs such as B560V, M20D, D11K where mapped), stations (428 OSM substations), generation (20 grouped stations from 188 IESO units), **model flows** (real OSM geometry recoloured by loading; dashed = schematic), **Planned** (31 projects from IESO/Hydro One/OEB/OPG/Bruce Power), **History** (26 dated events with year slider; coal phase-out, Bruce-Milton 2012, Chatham-Lakeshore 2024).
- **Game**: pick a day (2026-11-16 IESO actuals; 2025 peak and minimum demand days), hour slider/play, load multiplier, Michigan/New York export sliders, per-station dispatch sliders, auto-balance (gas/hydro/storage), trip/restore any corridor from its popup. DC flow on a 27-bus / 41-branch equivalent; overloads highlighted red; FETT/QFW/ON-MI/ON-NY interface flows vs IESO APO capabilities; simple score.
- **Popups** are Name / Type / Value tables with source links; deep links `#view=kw&open=br:CHA-LAK&hour=7&day=2026-11-16&layers=...&year=2013`; `#tour` runs a scripted click-through.
- **Data**: `data/raw/` unmodified downloads; processed `data/*.geojson|json`; `data/registry.json` (flat entity index with tree paths, ready for the Explorer panel); `SOURCES.md` (every source URL and what is ESTIMATE).
- UI is a **placeholder shell**; the designed interface is being mocked up in `design/` (not part of this build).

## Rebuild data
```bash
python3 tools/fetch_osm.py          # Overpass (IPv4 forced; polite, single queries)
python3 tools/build_osm.py          # lines/substations/plants GeoJSON + derived corridor topology
python3 tools/build_model.py        # grid model, generators, day profiles, history, planned, registry, SOURCES.md
python3 tools/check_links.py        # one polite GET per source URL -> logs/links.txt
```

## Limits (v0.1.0)
Reactances and most thermal limits are generic ESTIMATES (not Hydro One ratings); generator-to-bus mapping is ESTIMATE except Bruce, Darlington, Pickering and Beck; REST (rest of Ontario) is a slack equivalent; Michigan phase-angle regulators are not modelled; planned routes are straight schematic lines.
