"""Build the curated grid model + game data from raw extracts and the source registry.
Inputs: data/raw/* (IESO reports, Gridwatch snapshot, OSM), data/substations.geojson, data/topology_osm.json, data/plants_osm.geojson.
Outputs: data/grid_model.json, data/day_profiles.json, data/generators.json, data/history.json, data/planned.geojson, data/registry.json, data/sources.json, SOURCES.md.
Every number carries `src` (ids in tools/sources.py) and `est` (true = ESTIMATE). Usage: python3 tools/build_model.py"""
import json, os, sys, math, csv, re, collections, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(__file__)); from sources import S, ACC
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = lambda *p: os.path.join(ROOT, "data", *p)
J = lambda p: json.load(open(p)); W = lambda p, o: json.dump(o, open(D(p), "w"), indent=1, ensure_ascii=False)
used = collections.Counter()
def src(*ids):
    for i in ids: assert i in S, i; used[i] += 1
    return list(ids)
def hav(a, b):
    r = math.pi/180; dl = (b[1]-a[1])*r; dn = (b[0]-a[0])*r
    h = math.sin(dl/2)**2 + math.cos(a[1]*r)*math.cos(b[1]*r)*math.sin(dn/2)**2; return 12742*math.asin(math.sqrt(h))
SUBS = {f["properties"]["name"]: f for f in J(D("substations.geojson"))["features"] if f["properties"]["name"]}
UNNAMED = {tuple(f["geometry"]["coordinates"]): f for f in J(D("substations.geojson"))["features"] if not f["properties"]["name"]}
TOPO = J(D("topology_osm.json"))["corridors"]
def corr(a, b, kv):
    for c in TOPO:
        if c["kv"] == kv and {c["a"], c["b"]} == {a, b}: return c
    return None
# ---------------- buses ----------------
# (id, label, osm substation name | (lon,lat), kind, zone)
BUS = [
 ("BRUCE", "Bruce (A+B switchyards)", "Bruce B Switchyard", "station", "Bruce"),
 ("LONGWOOD", "Longwood TS", "Longwood TS", "station", "Southwest"),
 ("MILTON", "Milton SS", "Milton SS", "station", "Toronto"),
 ("TRAFALGAR", "Trafalgar TS", "Trafalgar TS", "station", "Toronto"),
 ("CLAIREVILLE", "Claireville TS", "Claireville TS", "station", "Toronto"),
 ("RICHVIEW", "Richview TS", "Richview Transformer Station", "station", "Toronto"),
 ("CHERRYWOOD", "Cherrywood TS", "Cherrywood TS", "station", "Toronto"),
 ("PICKERING", "Pickering SS (A/B)", "Pickering SS A", "station", "Toronto"),
 ("CLARINGTON", "Clarington TS", "Clarington TS", "station", "Toronto"),
 ("BOWMANVILLE", "Bowmanville SS (Darlington)", "Bowmanville SS", "station", "Toronto"),
 ("ESSA", "Essa TS", "Essa TS", "station", "Essa"),
 ("NANTICOKE", "Nanticoke TS", "Nanticoke TS", "station", "Southwest"),
 ("MIDDLEPORT", "Middleport TS", "Middleport TS", "station", "Southwest"),
 ("BURLINGTON", "Burlington TS", "Burlington Transformer Station", "station", "Southwest"),
 ("BECK", "Beck 2 TS (Niagara)", (-79.048115, 43.14241), "station", "Niagara"),
 ("PRESTON", "Preston TS (Cambridge)", "Preston TS", "station", "Southwest"),
 ("DETWEILER", "Detweiler TS (Kitchener)", "Detweiler TS", "station", "Southwest"),
 ("SCHEIFELE", "Scheifele TS (Waterloo)", "Howard Scheifele Transformer Station", "station", "Southwest"),
 ("ORANGEVILLE", "Orangeville TS", "Orangeville TS", "station", "Southwest"),
 ("BUCHANAN", "Buchanan TS (London)", "E. V. Buchanan Transformer Station", "station", "Southwest"),
 ("LAMBTON", "Lambton TS (Sarnia/St. Clair)", "Lambton Substation", "station", "West"),
 ("CHATHAM", "Chatham SS", "Chatham Switching Station", "station", "West"),
 ("LAKESHORE", "Lakeshore TS", "Lakeshore Transmission Station", "station", "West"),
 ("KEITH", "Keith TS (Windsor)", "W. Clark Keith transformer Substation", "station", "West"),
 ("REST", "Rest of Ontario (equivalent; slack)", (-79.4, 45.3), "equivalent", None),
 ("MI", "Michigan (MISO) equivalent", "Saint Clair Power Plant Substation", "external", None),
 ("NY", "New York (NYISO) equivalent", "Robert Moses Substation", "external", None),
]
buses = []
for bid, label, ref, kind, zone in BUS:
    if isinstance(ref, tuple):
        f = UNNAMED.get(ref); pos = list(ref); s = src("osm") if f else []
        b = {"id": bid, "name": label, "lon": pos[0], "lat": pos[1], "kind": kind, "zone": zone, "pos_src": s, "pos_est": True,
             "osm": f["properties"]["source_url"] if f else None, "note": "unnamed OSM 345/230 kV substation next to Sir Adam Beck GS; name ESTIMATE" if f else "schematic position (not a real place)"}
    else:
        f = SUBS[ref]; lon, lat = f["geometry"]["coordinates"]
        b = {"id": bid, "name": label, "lon": lon, "lat": lat, "kind": kind, "zone": zone, "pos_src": src("osm"), "pos_est": False, "osm": f["properties"]["source_url"], "osm_name": ref, "kvs": f["properties"]["kvs"]}
    buses.append(b)
BP = {b["id"]: (b["lon"], b["lat"]) for b in buses}
# ---------------- branches ----------------
OHM_KM = {500: 0.28, 345: 0.32, 230: 0.40}       # ESTIMATE positive-sequence reactance per circuit-km (generic)
LIM_CKT = {500: 2000, 345: 1000, 230: 450}       # ESTIMATE MW per circuit (generic thermal order of magnitude, not Hydro One ratings)
# (id, a, b, kv, circuits, osm chain [(nameA,nameB,kv)...] or None, srcs, note, circuits_est)
BR = [
 ("BRU-MIL", "BRUCE", "MILTON", 500, 4, [("Bruce B Switchyard", "Milton SS")], ["b2m_lp", "b2m_news"], "Four 500 kV circuits Bruce-Milton (two owned by B2M LP); new double circuit in service 2012", False),
 ("BRU-LON", "BRUCE", "LONGWOOD", 500, 2, [("Bruce A Switchyard", "K2 Substation"), ("K2 Substation", "Evergreen SS"), ("Evergreen SS", "Longwood TS")], ["osm"], "OSM ways named 'Bruce to Longwood'; wind connections tap at K2 and Evergreen SS", True),
 ("LON-NAN", "LONGWOOD", "NANTICOKE", 500, 2, [("Longwood TS", "Nanticoke TS")], ["osm"], "", True),
 ("NAN-MID", "NANTICOKE", "MIDDLEPORT", 500, 2, [("Middleport TS", "Nanticoke TS")], ["osm"], "OSM refs include N580M/N581M", True),
 ("MID-MIL", "MIDDLEPORT", "MILTON", 500, 2, [("Middleport TS", "Milton SS")], ["osm"], "OSM refs M585M/V586M", True),
 ("MIL-CLA", "MILTON", "CLAIREVILLE", 500, 2, [("Claireville TS", "Milton SS")], ["osm", "apo_interfaces"], "Part of FETT ('four 500 kV circuits into Claireville')", True),
 ("MIL-TRA", "MILTON", "TRAFALGAR", 500, 2, [("Milton SS", "Trafalgar TS")], ["osm"], "OSM refs M572T/M573T", True),
 ("CLA-CHE", "CLAIREVILLE", "CHERRYWOOD", 500, 2, [("Cherrywood TS", "Claireville TS")], ["osm"], "OSM refs C550V/C551V", True),
 ("CLA-ESS", "CLAIREVILLE", "ESSA", 500, 2, [("Claireville TS", "Essa TS")], ["osm", "apo_interfaces"], "Part of FETT", True),
 ("CHE-BOW", "CHERRYWOOD", "BOWMANVILLE", 500, 2, [("Bowmanville SS", "Cherrywood TS")], ["osm"], "OSM refs B542C/B543C", True),
 ("CHE-CLR", "CHERRYWOOD", "CLARINGTON", 500, 2, [("Cherrywood TS", "Clarington TS")], ["osm"], "OSM refs B540C/B541C", True),
 ("CLR-BOW", "CLARINGTON", "BOWMANVILLE", 500, 2, [("Bowmanville SS", "Clarington TS")], ["osm"], "", True),
 ("TRA-RIC", "TRAFALGAR", "RICHVIEW", 230, 4, None, ["apo_interfaces"], "'four 230 kV circuits out of Trafalgar TS to Richview TS and Hurontario SS'; the FETT-limiting path; reconductoring expected Q4 2026", False),
 ("CHE-PIC", "CHERRYWOOD", "PICKERING", 230, 4, [("Cherrywood TS", "Pickering SS A")], ["osm"], "OSM refs P6C/P7C (A) and P30C/P31C (B)", False),
 ("CHE-RIC", "CHERRYWOOD", "RICHVIEW", 230, 2, [("Cherrywood TS", "Richview Transformer Station")], ["osm"], "OSM refs C4R/C5R", False),
 ("BEC-MID", "BECK", "MIDDLEPORT", 230, 3, None, ["apo_interfaces", "osm"], "QFW: 'three 230 kV circuits into Middleport TS'; via Allanburg TS (OSM Q-circuits)", False),
 ("BEC-BUR", "BECK", "BURLINGTON", 230, 2, [("Allanburg TS", "Burlington Transformer Station")], ["apo_interfaces", "osm"], "QFW remainder of 'four 230 kV circuits out of Beck 2'; OSM refs Q23BM/Q25BM (via Allanburg)", True),
 ("BUR-MID", "BURLINGTON", "MIDDLEPORT", 230, 2, [("Burlington Transformer Station", "Middleport Junction")], ["osm"], "", True),
 ("BUR-TRA", "BURLINGTON", "TRAFALGAR", 230, 2, None, ["osm"], "OSM refs T36B/T37B (Trafalgar-Burlington via Palermo)", True),
 ("MID-PRE", "MIDDLEPORT", "PRESTON", 230, 2, [("Middleport Junction", "Preston TS")], ["osm", "kwcg_scope24"], "M20D/M21D (KWCG 2024: Galt JCT-Cambridge JCT section overload need by 2026)", False),
 ("PRE-DET", "PRESTON", "DETWEILER", 230, 2, [("Detweiler TS", "Preston TS")], ["osm", "kwcg_scope24"], "M20D/M21D continue to Detweiler (KWCG 'MxD sub-system')", False),
 ("DET-SCH", "DETWEILER", "SCHEIFELE", 230, 2, None, ["kwcg_irrp26"], "Waterloo supply (KWCG 'DxV sub-system'); route not traced in OSM extract", True),
 ("SCH-ORA", "SCHEIFELE", "ORANGEVILLE", 230, 2, [("Howard Scheifele Transformer Station", "Orangeville TS")], ["osm"], "", True),
 ("ORA-ESS", "ORANGEVILLE", "ESSA", 230, 2, None, ["apo_interfaces"], "'two 230 kV circuits out of Orangeville TS to Essa TS' (FETT)", False),
 ("BRU-ORA", "BRUCE", "ORANGEVILLE", 230, 2, [("Bruce A Switchyard", "Hanover TS"), ("Hanover TS", "Orangeville TS")], ["osm"], "OSM refs B4V/B5V via Hanover TS", False),
 ("DET-BUC", "DETWEILER", "BUCHANAN", 230, 2, [("Detweiler TS", "E. V. Buchanan Transformer Station")], ["osm"], "", True),
 ("BUC-LON", "BUCHANAN", "LONGWOOD", 230, 2, [("E. V. Buchanan Transformer Station", "Longwood TS")], ["osm"], "", True),
 ("LON-LAM", "LONGWOOD", "LAMBTON", 230, 2, [("Lambton Substation", "Longwood TS")], ["osm"], "", True),
 ("LAM-CHA", "LAMBTON", "CHATHAM", 230, 2, [("Chatham Switching Station", "Lambton Substation")], ["osm"], "", True),
 ("LON-CHA", "LONGWOOD", "CHATHAM", 230, 2, [("Cowal Junction Station", "Longwood TS"), ("Chatham Switching Station", "Cowal Junction Station")], ["osm"], "via Cowal Junction", True),
 ("CHA-LAK", "CHATHAM", "LAKESHORE", 230, 2, [("Chatham Switching Station", "Lakeshore Transmission Station")], ["osm", "ho_cxl", "oeb_cxl_isd"], "Chatham x Lakeshore double-circuit 230 kV, in service 2024-12-17", False),
 ("LAK-KEI", "LAKESHORE", "KEITH", 230, 2, [("Lakeshore Transmission Station", "South Middle Road Transformer Station"), ("South Middle Road Transformer Station", "W. Clark Keith transformer Substation")], ["osm"], "", True),
 ("ESS-REST", "ESSA", "REST", 500, 2, None, ["apo_interfaces"], "Equivalent for the Flow North/Flow South interface (Essa-Hanmer); length schematic", True),
 ("BOW-REST", "BOWMANVILLE", "REST", 500, 4, None, ["apo_interfaces"], "Equivalent for TEC ('four 500 kV circuits out of Bowmanville SS'); length schematic", False),
 # interties
 ("L4D", "LAMBTON", "MI", 345, 1, None, ["nyiso_op09", "apo_interfaces"], "Lambton-St. Clair 345 kV, phase-angle regulated", False),
 ("L51D", "LAMBTON", "MI", 230, 1, None, ["nyiso_op09"], "Lambton-St. Clair 230 kV, phase-angle regulated", False),
 ("B3N", "LAMBTON", "MI", 230, 1, None, ["nyiso_op09"], "Scott TS (Sarnia)-Bunce Creek 230 kV, PAR; drawn from Lambton bus (ESTIMATE)", False),
 ("J5D", "KEITH", "MI", 230, 1, None, ["nyiso_op09"], "Keith-Waterman 230 kV, phase-angle regulated", False),
 ("PA301", "BECK", "NY", 345, 1, None, ["nyiso_ties"], "Beck 2-Niagara (Moses) 345 kV with 1000 MVA regulating transformer", False),
 ("PA302", "BECK", "NY", 345, 1, None, ["nyiso_ties"], "Beck 2-Niagara (Moses) 345 kV with 1000 MVA regulating transformer", False),
 ("BP76", "BECK", "NY", 230, 1, None, ["nyiso_ties"], "Beck-Packard 230 kV with 400 MVA transformer", False),
]
TIE = {"L4D", "L51D", "B3N", "J5D", "PA301", "PA302", "BP76"}
branches = []
for bid, a, b, kv, nc, chain, ss, note, nc_est in BR:
    L = None; refs = []; ways = []
    if chain:
        parts = [corr(x, y, kv) for x, y in chain]
        if all(parts): L = round(sum(p["length_km"] for p in parts), 1); refs = sorted({r for p in parts for r in p["refs"]}); ways = [w for p in parts for w in p["osm_ways"]]
    len_est = L is None
    if L is None: L = round(hav(BP[a], BP[b]) * 1.15, 1)
    if bid in TIE: L = max(L, 3.0)
    zb = kv * kv / 100.0; x = OHM_KM[kv] * L / nc / zb
    lim = LIM_CKT[kv] * nc
    if bid == "PA301" or bid == "PA302": lim = 1000
    if bid == "BP76": lim = 400
    lim_src = src("nyiso_ties") if bid in ("PA301", "PA302", "BP76") else []
    branches.append({"id": bid, "a": a, "b": b, "kv": kv, "circuits": nc, "circuits_est": nc_est, "length_km": L, "length_est": len_est,
        "x_pu": round(x, 6), "x_est": True, "limit_mw": lim, "limit_est": not lim_src, "limit_src": lim_src or None,
        "limit_note": "transformer MVA rating (sourced) used as MW limit" if lim_src else f"ESTIMATE: generic {LIM_CKT[kv]} MW per {kv} kV circuit x {nc}",
        "osm_refs": refs, "osm_ways": ways[:400], "src": src(*ss), "note": note, "tie": bid in TIE})
# interfaces with sourced Total Transfer Capability (2027, summer, all elements in service)
interfaces = [
 {"id": "FETT", "name": "Flow East Towards Toronto", "branches": [["MIL-CLA", 1], ["CLA-ESS", -1], ["TRA-RIC", 1], ["ORA-ESS", 1]], "ttc_mw": 5900, "src": src("apo_interfaces"), "est_membership": True, "note": "Membership simplified to model branches (ESTIMATE)"},
 {"id": "QFW", "name": "Queenston Flow West", "branches": [["BEC-MID", 1], ["BEC-BUR", 1]], "ttc_mw": 2025, "src": src("apo_interfaces"), "est_membership": True},
 {"id": "ON-MI", "name": "Ontario to Michigan", "branches": [["L4D", 1], ["L51D", 1], ["B3N", 1], ["J5D", 1]], "ttc_mw": 1500, "ttc_rev_mw": 1650, "src": src("apo_interfaces")},
 {"id": "ON-NY", "name": "Ontario to New York at Niagara", "branches": [["PA301", 1], ["PA302", 1], ["BP76", 1]], "ttc_mw": 2150, "ttc_rev_mw": 1835, "src": src("apo_interfaces")},
 {"id": "FN", "name": "Flow North (proxy: Essa to Rest)", "branches": [["ESS-REST", 1]], "ttc_mw": 1960, "ttc_rev_mw": 2150, "src": src("apo_interfaces"), "est_membership": True, "note": "FS TTC used for reverse direction"},
]
# ---------------- generators (IESO units) ----------------
def ieso_units(path):
    t = ET.parse(path).getroot()
    for x in t.iter(): x.tag = x.tag.split("}")[1]
    out = {}
    for g in t.iter("Generator"):
        n = g.findtext("GeneratorName"); f = g.findtext("FuelType")
        def series(tag):
            s = [None] * 24
            for c in g.iter(tag):
                h = int(c.findtext("Hour")); v = c.findtext("EnergyMW"); s[h-1] = float(v) if v not in (None, "") else None
            return s
        out[n] = {"fuel": f, "out": series("Output"), "cap": series("Capability"), "avail": series("AvailCapacity")}
    return out
U = ieso_units(D("raw", "ieso_PUB_GenOutputCapability_20261116.xml"))
MAP = [  # (regex on IESO name, bus, sited) ; sited=True when the plant's own switchyard is the bus
 (r"^BRUCE[AB]-", "BRUCE", True), (r"^DARLINGTON", "BOWMANVILLE", True), (r"^PICKERING", "PICKERING", True),
 (r"^BECK|^DECEW", "BECK", True), (r"^THOROLD", "BECK", False), (r"^WEST LINCOLN", "BECK", False),
 (r"^GREENFIELD|^STCLAIRCGS|^TASARNIA|^DOWCHEMICAL|^CEDAR POINT|^JERICHO|^SHANNON", "LAMBTON", False),
 (r"^BRIGHTON BEACH|^EAST WINDSOR|^TAWINDSOR|^WESTWINDSOR|^WINDSOR AIRPORT", "KEITH", False),
 (r"^COMBER|^BELLE RIVER|^ROMNEY|^GOSFIELD|^PAROCHES", "LAKESHORE", False),
 (r"^PORTALMA|^NORTH KENT|^ERIEAU|^DILLON|^RAILBED|^TILBURY|^LANDON", "CHATHAM", False),
 (r"^HALTONHILLS|^HYDROGEN READY", "TRAFALGAR", False), (r"^SITHE GOREWAY|^GOREWAY BESS|^VAUGHAN", "CLAIREVILLE", False),
 (r"^PORTLANDS|^GTAA", "RICHVIEW", False), (r"^WHITBY", "CHERRYWOOD", False), (r"^YORKCGS|^YORK BESS", "ESSA", False),
 (r"^NANTICOKE SOLAR|^HAGERSVILLE|^ONEIDA|^GRANDWF|^GRANDSF|^SUMMERHAVEN|^SANDUSK", "NANTICOKE", False),
 (r"^K2WIND|^ARMOW|^UNDERWOOD|^RIPLEY|^KINGSBRIDGE", "BRUCE", False), (r"^GOSHEN|^ZURICH|^PORT BURWELL|^SPENCE|^BORNISH|^ADELAIDE", "LONGWOOD", False),
 (r"^AMARANTH|^GRAND VALLEY|^SOUTHGATE", "ORANGEVILLE", False), (r"^ARLEN", "PRESTON", False),
]
gens = []
for n, u in U.items():
    bus = "REST"; sited = False
    for rx, b, s in MAP:
        if re.search(rx, n): bus, sited = b, s; break
    caps = [c for c in u["cap"] if c is not None] or [c for c in u["avail"] if c is not None] or [0]
    outs = [o if o is not None else 0 for o in u["out"]]
    gens.append({"id": n, "fuel": u["fuel"], "bus": bus, "bus_est": not sited, "max_cap_mw": max(caps), "cap_h": u["cap"], "out_h": outs,
                 "src": src("ieso_gen"), "note": "cap = IESO hourly capability on 2026-11-16 (availability that day, not nameplate)" + ("" if sited else "; bus assignment ESTIMATE")})
# station groups (for the map + future explorer tree)
STATION = [
 ("Bruce NGS", r"^BRUCE[AB]-", "NUCLEAR", ["wiki_bruce", "bp_about"]), ("Darlington NGS", r"^DARLINGTON", "NUCLEAR", ["wiki_darl"]), ("Pickering NGS", r"^PICKERING", "NUCLEAR", ["wiki_pick"]),
 ("Sir Adam Beck (I, II, PGS)", r"^BECK", "HYDRO", ["wiki_beck"]), ("DeCew Falls", r"^DECEW", "HYDRO", ["wiki_on_gs"]),
 ("Greenfield Energy Centre", r"^GREENFIELD ENERGY", "GAS", ["wiki_on_gs"]), ("St. Clair Energy Centre", r"^STCLAIRCGS", "GAS", ["wiki_on_gs"]), ("TransAlta Sarnia", r"^TASARNIA", "GAS", ["wiki_on_gs"]),
 ("Brighton Beach", r"^BRIGHTON BEACH", "GAS", ["wiki_on_gs"]), ("Halton Hills GS", r"^HALTONHILLS", "GAS", ["wiki_on_gs"]), ("Goreway Station", r"^SITHE GOREWAY", "GAS", ["wiki_on_gs"]),
 ("Portlands Energy Centre", r"^PORTLANDS", "GAS", ["wiki_on_gs"]), ("Thorold Cogen", r"^THOROLD", "GAS", ["wiki_on_gs"]), ("York Energy Centre", r"^YORKCGS", "GAS", ["wiki_on_gs"]),
 ("East Windsor Cogen", r"^EAST WINDSOR", "GAS", ["wiki_on_gs"]), ("Lennox GS", r"^LENNOX", "GAS", ["wiki_on_gs"]), ("Napanee GS", r"^NAPANEE-G", "GAS", ["wiki_on_gs"]),
 ("Oneida Energy Storage", r"^ONEIDA", "OTHER", ["wiki_on_gs"]), ("Hagersville BESS", r"^HAGERSVILLE", "OTHER", []), ("Nanticoke Solar", r"^NANTICOKE SOLAR", "SOLAR", []),
]
stations = []
for name, rx, fuel, ss in STATION:
    us = [g for g in gens if re.search(rx, g["id"])]
    if not us: continue
    stations.append({"id": "st:" + name, "name": name, "fuel": fuel, "units": [g["id"] for g in us], "bus": us[0]["bus"], "cap_mw_20261116": round(sum(g["max_cap_mw"] for g in us)), "src": src("ieso_gen", *ss)})
# OSM plant positions (name match) for map pins
PL = J(D("plants_osm.geojson"))["features"] if os.path.exists(D("plants_osm.geojson")) else []
def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())
for st in stations:
    key = norm(re.sub(r"\(.*\)|NGS|GS|Station|Energy Centre|Cogen", "", st["name"]))
    cands = [f for f in PL if key and key in norm(f["properties"]["name"])]
    if cands:
        f = max(cands, key=lambda f: len(f["properties"]["tags"])); st.update(lon=f["geometry"]["coordinates"][0], lat=f["geometry"]["coordinates"][1], pos_src=src("osm"), pos_est=False, osm=f["properties"]["source_url"], osm_name=f["properties"]["name"])
    else:
        st.update(lon=BP[st["bus"]][0], lat=BP[st["bus"]][1], pos_src=[], pos_est=True)
# ---------------- day profiles ----------------
def demand(path, day):
    rows = [r for r in csv.reader(open(path)) if r and r[0] == day]; return [float(r[3]) for r in sorted(rows, key=lambda r: int(r[1]))]
def zonal(path, day):
    rd = [r for r in csv.reader(open(path)) if r and not r[0].startswith("\\")]; hdr = rd[0]
    rows = [dict(zip(hdr, r)) for r in rd[1:] if r[0] == day]; rows.sort(key=lambda r: int(r["Hour"]))
    return {z: [float(r[z]) for r in rows] for z in ["Ontario Demand", "Northwest", "Northeast", "Ottawa", "East", "Toronto", "Essa", "Bruce", "Southwest", "Niagara", "West"]}
def intertie(path):
    t = ET.parse(path).getroot()
    for x in t.iter(): x.tag = x.tag.split("}")[1]
    out = {}
    for z in t.iter("IntertieZone"):
        n = z.findtext("IntertieZoneName"); h = collections.defaultdict(list)
        for a in z.iter("Actual"): h[int(a.findtext("Hour"))].append(float(a.findtext("Flow") or 0))
        sch = {int(s.findtext("Hour")): float(s.findtext("Export") or 0) - float(s.findtext("Import") or 0) for s in z.iter("Schedule")}
        out[n] = {"actual_flow_h": [round(sum(h[i]) / len(h[i]), 1) if h[i] else None for i in range(1, 25)], "sched_net_export_h": [sch.get(i) for i in range(1, 25)]}
    return out
DAY = "2026-11-16"
d26 = demand(D("raw", "ieso_PUB_Demand.csv"), DAY); z26 = zonal(D("raw", "ieso_PUB_DemandZonal_2026.csv"), DAY)
rows25 = [r for r in csv.reader(open(D("raw", "ieso_PUB_Demand_2025.csv"))) if r and re.match(r"\d{4}-", r[0])]
pk = max(rows25, key=lambda r: float(r[3])); pkday = pk[0]
d25 = demand(D("raw", "ieso_PUB_Demand_2025.csv"), pkday); z25 = zonal(D("raw", "ieso_PUB_DemandZonal_2025.csv"), pkday)
lo = min(rows25, key=lambda r: float(r[3])); loday = lo[0]
dlo = demand(D("raw", "ieso_PUB_Demand_2025.csv"), loday); zlo = zonal(D("raw", "ieso_PUB_DemandZonal_2025.csv"), loday)
IT = intertie(D("raw", "ieso_PUB_IntertieScheduleFlow_20261116.xml"))
fuel_h = collections.defaultdict(lambda: [0.0] * 24)
for g in gens:
    for i, v in enumerate(g["out_h"]): fuel_h[g["fuel"]][i] += v
GW = J(D("raw", "gridwatch_homeview_20261118.json"))
U18 = ieso_units(D("raw", "ieso_PUB_GenOutputCapability_20261118_partial.xml"))
ieso18 = collections.Counter()
for n, u in U18.items(): ieso18[u["fuel"]] += u["out"][0] or 0
num = lambda s: float(str(s).replace(",", "") or 0)
xcheck = {"snapshot": GW["timeOfReading"], "gridwatch_mw": {k: num(GW[k.lower() + "Output"]) for k in ["Nuclear", "Hydro", "Gas", "Wind", "Solar", "Biofuel"]},
          "ieso_hour1_20261118_mw": {k.title(): ieso18[k] for k in ["NUCLEAR", "HYDRO", "GAS", "WIND", "SOLAR", "BIOFUEL"]},
          "gridwatch_demand_mw": num(GW["ontarioDemand"]), "ieso_demand_mw": demand(D("raw", "ieso_PUB_Demand.csv"), "2026-11-18")[:1] or None,
          "gridwatch_net_export_mw": {k: num(v["net"]) for k, v in GW["intertieLineData"].items() if num(v["net"])},
          "src": src("gridwatch", "ieso_gen", "ieso_demand")}
profiles = {"default": DAY, "days": [
  {"id": DAY, "label": f"{DAY} (IESO actuals: demand, unit output, intertie flow)", "ontario_demand_h": d26, "zonal_h": z26, "dispatch": "ieso_actual",
   "intertie_h": {k: IT[k] for k in ("MICHIGAN", "NEW-YORK")}, "other_net_export_h": [round(sum((IT[k]["sched_net_export_h"][i] or 0) for k in IT if k not in ("MICHIGAN", "NEW-YORK")), 1) for i in range(24)],
   "fuel_output_h": {k: [round(v) for v in vs] for k, vs in fuel_h.items()}, "src": src("ieso_demand", "ieso_zonal", "ieso_gen", "ieso_intertie"),
   "flow_sign_note": "IESO actual intertie Flow: positive taken as Ontario export (matches the export schedules that day); ESTIMATE interpretation"},
  {"id": pkday, "label": f"{pkday} (2025 peak Ontario Demand hour {pk[1]}: {pk[3]} MW; dispatch ESTIMATE: 2026-11-16 unit pattern + auto-balance)", "ontario_demand_h": d25, "zonal_h": z25, "dispatch": "auto",
   "src": src("ieso_demand25", "ieso_zonal25")},
  {"id": loday, "label": f"{loday} (2025 minimum Ontario Demand hour {lo[1]}: {lo[3]} MW; dispatch ESTIMATE)", "ontario_demand_h": dlo, "zonal_h": zlo, "dispatch": "auto", "src": src("ieso_demand25", "ieso_zonal25")},
 ], "gridwatch_crosscheck": xcheck}
# bus load weights within IESO zones (ESTIMATE)
LOADW = {"Toronto": {"RICHVIEW": .28, "CLAIREVILLE": .22, "TRAFALGAR": .16, "CHERRYWOOD": .20, "PICKERING": .04, "CLARINGTON": .05, "MILTON": .05},
         "Southwest": {"DETWEILER": .13, "PRESTON": .10, "SCHEIFELE": .08, "BUCHANAN": .20, "BURLINGTON": .22, "MIDDLEPORT": .10, "NANTICOKE": .07, "ORANGEVILLE": .05, "LONGWOOD": .05},
         "West": {"LAMBTON": .25, "CHATHAM": .20, "LAKESHORE": .25, "KEITH": .30}, "Niagara": {"BECK": 1.0}, "Bruce": {"BRUCE": 1.0}, "Essa": {"ESSA": 1.0},
         "Northwest": {"REST": 1.0}, "Northeast": {"REST": 1.0}, "Ottawa": {"REST": 1.0}, "East": {"REST": 1.0}}
model = {"version": "0.1.0", "generated": ACC, "base_mva": 100, "slack": "REST", "buses": buses, "branches": branches, "interfaces": interfaces, "load_weights": LOADW, "load_weights_est": True,
  "load_weights_note": "IESO zonal demand (sourced) split to model buses by ESTIMATE weights", "notes": [
  "DC power flow on a reduced equivalent of the SW Ontario/GTA bulk system. Reactances, most circuit counts and all thermal limits except Niagara tie transformer ratings are ESTIMATE.",
  "REST is an equivalent for the rest of Ontario (north, east, Ottawa) and absorbs the balance (slack). Quebec/Manitoba/Minnesota/St. Lawrence interchange is lumped at REST.",
  "Phase-angle regulators on the Michigan ties are not modelled (free-flowing DC split)."],
  "est_params": {"ohm_per_km": OHM_KM, "mw_per_circuit": LIM_CKT}, "src": src("osm", "apo_interfaces")}
W("grid_model.json", model); W("generators.json", {"date": DAY, "units": gens, "stations": stations, "src": src("ieso_gen")}); W("day_profiles.json", profiles)
# ---------------- history (dated events; extend by appending) ----------------
def P(name): f = SUBS.get(name); return f["geometry"]["coordinates"] if f else None
H = [
 # (date, type, title, detail, refs, est, where[lon,lat]|bus, entity)
 ("1922", "plant_build", "Queenston-Chippawa (Sir Adam Beck I) in service", "Hydro at Niagara", ["wiki_beck"], False, "BECK", "st:Sir Adam Beck (I, II, PGS)"),
 ("1954", "plant_build", "Sir Adam Beck II in service", "", ["wiki_beck"], False, "BECK", "st:Sir Adam Beck (I, II, PGS)"),
 ("1962", "plant_build", "Lakeview GS (coal, Mississauga) in service", "", ["wiki_lakeview"], False, (-79.57, 43.57), "hist:lakeview"),
 ("1969", "plant_build", "Lambton GS (coal) in service", "", ["wiki_lambton"], False, (-82.45, 42.79), "hist:lambton"),
 ("1971", "plant_build", "Pickering A first unit in service", "", ["wiki_pick"], False, "PICKERING", "st:Pickering NGS"),
 ("1972", "plant_build", "Nanticoke GS (coal) first units", "Largest coal station in North America at the time", ["wiki_nanticoke"], False, (-80.05, 42.80), "hist:nanticoke"),
 ("1977", "plant_build", "Bruce A first unit in service", "", ["wiki_bruce"], False, "BRUCE", "st:Bruce NGS"),
 ("1983", "plant_build", "Pickering B units enter service (1983-86)", "", ["wiki_pick"], False, "PICKERING", "st:Pickering NGS"),
 ("1984", "plant_build", "Bruce B units enter service (1984-87)", "", ["wiki_bruce"], False, "BRUCE", "st:Bruce NGS"),
 ("1990", "plant_build", "Darlington units enter service (1990-93)", "", ["wiki_darl"], False, "BOWMANVILLE", "st:Darlington NGS"),
 ("2003-08-14", "event", "Northeast blackout", "Most of Ontario lost supply", ["wiki_blackout"], False, "REST", None),
 ("2005", "retirement", "Lakeview GS closes (coal, 2,400 MW)", "First step of the coal phase-out", ["on_end_coal", "on_coal_bg"], False, (-79.57, 43.57), "hist:lakeview"),
 ("2009", "policy", "Green Energy Act / FIT programme", "Wind and solar build-out in SW Ontario follows", ["wiki_gea"], False, "LONGWOOD", None),
 ("2010", "retirement", "Two units each at Nanticoke and Lambton shut", "", ["on_coal_bg"], False, (-80.05, 42.80), "hist:nanticoke"),
 ("2012-05", "line_build", "Bruce-Milton 500 kV double circuit in service", "176-180 km; final connection ceremony 2012-06-19", ["ho_2012", "b2m_news", "b2m_lp"], False, "BRUCE", "br:BRU-MIL"),
 ("2012-09-11", "retirement", "Atikokan GS burns last coal", "", ["opg_atikokan", "on_end_coal"], False, (-91.62, 48.84), "hist:atikokan"),
 ("2012-10", "refurb", "Bruce A units 1 and 2 return after restart", "Month ESTIMATE", ["wiki_bruce"], True, "BRUCE", "st:Bruce NGS"),
 ("2013-10", "retirement", "Lambton GS closes (coal, 1,980 MW)", "Month per Sierra Club", ["on_end_coal", "sierra_coal"], False, (-82.45, 42.79), "hist:lambton"),
 ("2013-12", "retirement", "Nanticoke GS closes (coal, 3,940 MW)", "", ["on_end_coal", "sierra_coal"], False, (-80.05, 42.80), "hist:nanticoke"),
 ("2014-04-08", "retirement", "Thunder Bay GS burns last coal; Ontario coal-free", "Later converted to advanced biomass", ["opg_atikokan", "sierra_coal", "on_end_coal", "wiki_tbay"], False, (-89.22, 48.36), "hist:tbay"),
 ("2014-07", "conversion", "Atikokan GS returns on 100% biomass", "OPG release 2014-09-10; ontario.ca timeline says 2015 (conflict; ESTIMATE)", ["opg_atikokan", "on_end_coal"], True, (-91.62, 48.84), "hist:atikokan"),
 ("2016-10", "refurb", "Darlington refurbishment begins (Unit 2)", "", ["wiki_darl"], True, "BOWMANVILLE", "st:Darlington NGS"),
 ("2020-01", "refurb", "Bruce Unit 6 Major Component Replacement begins", "", ["wiki_bruce"], True, "BRUCE", "st:Bruce NGS"),
 ("2024", "retirement", "Pickering units 1 and 4 shut down", "", ["wiki_pick"], True, "PICKERING", "st:Pickering NGS"),
 ("2024-12-17", "line_build", "Chatham-Lakeshore 230 kV double circuit in service", "One year ahead of schedule", ["oeb_cxl_isd", "ho_cxl"], False, "CHATHAM", "br:CHA-LAK"),
 ("2026-11-16", "snapshot", "Pickering B units 5-8 at 0 MW in IESO report", "Shown as unavailable on that day (IESO), not as retired", ["ieso_gen"], False, "PICKERING", "st:Pickering NGS"),
]
def where(w): return list(BP[w]) if isinstance(w, str) else list(w)
history = {"note": "Dated grid events. date is ISO (YYYY, YYYY-MM or YYYY-MM-DD). est=true -> ESTIMATE date. Add events by appending; schema is stable.",
  "schema": {"id": "str", "date": "ISO partial", "year": "int", "type": "plant_build|line_build|retirement|conversion|refurb|policy|event|snapshot", "title": "str", "detail": "str", "src": "[source ids]", "est": "bool", "lon": "float", "lat": "float", "entity": "registry id or null"},
  "events": []}
for i, (dt, ty, ti, de, rf, es, w, ent) in enumerate(H):
    lon, lat = where(w)
    history["events"].append({"id": f"ev{i:03d}", "date": dt, "year": int(dt[:4]), "type": ty, "title": ti, "detail": de, "src": src(*rf), "est": es, "lon": lon, "lat": lat, "pos_est": not isinstance(w, str) or w == "REST", "entity": ent})
W("history.json", history)
# ---------------- planned projects ----------------
PLN = {"Wellington TS (Puslinch)": (-80.22, 43.45), "Bruce C site": (-81.60, 44.32), "Hanmer TS (Sudbury)": (-80.95, 46.65), "Kleinburg TS": P("Kleinburg TS"), "Parkway TS": P("Parkway TS"),
       "Lauzon TS": P("Lauzon Transformer Station"), "St. Thomas TS": (-81.19, 42.78), "Meadowvale TS": P("Meadowvale TS"), "Hurontario SS": P("Hurontario SS"), "Oakville TS": P("Oakville TS #2"),
       "Milton TS": P("Milton SS"), "Halton #2 TS (Milton)": (-79.87, 43.50), "Lakeview MTS (Cooksville)": (-79.60, 43.58), "Caledon": (-79.80, 43.85), "Heritage Heights (NW Brampton)": (-79.82, 43.72), "Goreway #2 (NE Brampton)": (-79.68, 43.78), "Gateway MTS (Mississauga)": (-79.65, 43.69),
       "GBE MTS #2 (Cambridge)": (-80.33, 43.39), "Snider/11 TS/Office MTS (Waterloo Region)": (-80.52, 43.45), "Kitchener MTS #8": (-80.47, 43.42)}
PLPOS_EST = {k for k, v in PLN.items() if k in ("Wellington TS (Puslinch)", "Bruce C site", "Hanmer TS (Sudbury)", "St. Thomas TS", "Halton #2 TS (Milton)", "Lakeview MTS (Cooksville)", "Caledon", "Heritage Heights (NW Brampton)", "Goreway #2 (NE Brampton)", "Gateway MTS (Mississauga)", "GBE MTS #2 (Cambridge)", "Snider/11 TS/Office MTS (Waterloo Region)", "Kitchener MTS #8")}
def pos(k): return list(BP[k]) if k in BP else list(PLN[k])
PJ = [  # (id, name, kind, kv, [endpoints], isd, status, refs, detail, est_isd)
 ("p_lxl1", "Longwood-Lakeshore 500 kV Line 1", "line", 500, ["LONGWOOD", "LAKESHORE"], "2030", "planning/LTC filed", ["ho_lxl", "ho_lxl_esr", "oeb_swo_biannual"], "~120 km single circuit; construction 2027", False),
 ("p_lxl2", "Longwood-Lakeshore 500 kV Line 2", "line", 500, ["LONGWOOD", "LAKESHORE"], "2045+", "deferred", ["oeb_swo_biannual", "ho_lxl"], "Deferred beyond 2045 per IESO South and Central Bulk Plan draft", True),
 ("p_stl", "St. Thomas TS-Lakeshore TS 500 kV", "line", 500, ["St. Thomas TS", "LAKESHORE"], "2045+", "draft recommendation", ["oeb_swo_biannual"], "IESO draft (Apr 2026 webinar) per Hydro One OEB report", True),
 ("p_lxc", "Lambton-Chatham 230 kV", "line", 230, ["LAMBTON", "CHATHAM"], "ESTIMATE 2028", "development", ["oeb_swo_biannual"], "Project #1 of OIC 875/2022 directive", True),
 ("p_wlx", "Windsor (Lauzon)-Lakeshore 230 kV", "line", 230, ["Lauzon TS", "LAKESHORE"], "ESTIMATE 2030", "development", ["oeb_swo_biannual"], "Project #4 of OIC 875/2022 directive", True),
 ("p_brc_essa", "Bruce C-Essa 500 kV double circuit", "line", 500, ["Bruce C site", "ESSA"], "TBD", "IESO recommendation", ["sac_memo25"], "To enable Bruce C", True),
 ("p_brc_lon", "Bruce C-Longwood 500 kV double circuit", "line", 500, ["Bruce C site", "LONGWOOD"], "TBD", "IESO recommendation", ["sac_memo25"], "", True),
 ("p_bow_par", "Bowmanville-Parkway 500 kV double circuit", "line", 500, ["BOWMANVILLE", "Parkway TS"], "TBD", "IESO recommendation", ["sac_memo25"], "Enables Darlington SMRs", True),
 ("p_essa_kl", "Essa-Kleinburg 500 kV", "line", 500, ["ESSA", "Kleinburg TS"], "TBD", "IESO recommendation", ["sac_memo25"], "", True),
 ("p_han_essa", "Hanmer-Essa 500 kV (Sudbury-Barrie)", "line", 500, ["Hanmer TS (Sudbury)", "ESSA"], "TBD", "IEP implementation", ["sac_memo25", "on_ieP"], "Second line development work also recommended", True),
 ("p_ess_ora", "Essa-Orangeville 230 kV advanced reconductoring", "upgrade", 230, ["ESSA", "ORANGEVILLE"], "TBD", "IEP implementation", ["sac_memo25"], "", True),
 ("p_mdv_hur", "Meadowvale-Hurontario 230 kV double circuit", "line", 230, ["Meadowvale TS", "Hurontario SS"], "TBD", "IESO recommendation", ["sac_memo25"], "", True),
 ("p_oak_tra", "Oakville-Trafalgar 230 kV double circuit", "line", 230, ["Oakville TS", "TRAFALGAR"], "TBD", "IESO recommendation", ["sac_memo25", "gtaw_26"], "Also in GTA West draft (Cooksville/West Toronto growth)", True),
 ("p_mil_hur", "Milton TS-Hurontario SS 230 kV double circuit", "line", 230, ["Milton TS", "Hurontario SS"], "TBD", "GTA West draft", ["gtaw_26"], "New Milton bulk supply point", True),
 ("p_tra_ric", "Richview-Trafalgar 230 kV reconductoring", "upgrade", 230, ["TRAFALGAR", "RICHVIEW"], "Q4 2026", "under construction", ["apo_interfaces"], "Raises FETT capability", False),
 ("p_wellington", "Wellington TS 500/230 kV + 230 kV to Preston", "station", 500, ["Wellington TS (Puslinch)", "PRESTON"], "2031 or earlier", "IRRP recommendation", ["kwcg_irrp26"], "New autotransformer station in Puslinch with double-circuit 230 kV lines to Preston TS", False),
 ("p_gbe2", "GrandBridge Energy MTS #2 (115 kV, up to 75 MW)", "station", 115, ["GBE MTS #2 (Cambridge)"], "2028", "IRRP recommendation", ["kwcg_irrp26"], "", False),
 ("p_kw_uprate", "Uprate B5C/B6C, D7F/D9F, F11C/F12C (115 kV)", "upgrade", 115, ["DETWEILER"], "2028", "IRRP recommendation", ["kwcg_irrp26"], "Position schematic", False),
 ("p_kw_230st", "New 230 kV stations: 11 TS, Office MTS, Snider TS", "station", 230, ["Snider/11 TS/Office MTS (Waterloo Region)"], "2030+", "IRRP recommendation", ["kwcg_irrp26"], "Enova Power", False),
 ("p_kit8", "Kitchener MTS #8 new 230 kV DESN", "station", 230, ["Kitchener MTS #8"], "2030+", "IRRP recommendation", ["kwcg_irrp26"], "", False),
 ("p_dxv", "Uprate DxV + Detweiler TS station work", "upgrade", 230, ["DETWEILER", "SCHEIFELE"], "2031", "IRRP recommendation", ["kwcg_irrp26"], "", False),
 ("p_d11k", "Uprate D11K/D12K (115 kV)", "upgrade", 115, ["DETWEILER"], "2033", "IRRP recommendation", ["kwcg_irrp26", "kwcg_scope24"], "", False),
 ("p_halton2", "Halton #2 TS (230/27.6 kV, Milton)", "station", 230, ["Halton #2 TS (Milton)"], "2031", "GTA West draft", ["gtaw_26"], "", False),
 ("p_goreway2", "Goreway #2 MTS (NE Brampton)", "station", 230, ["Goreway #2 (NE Brampton)"], "2032", "GTA West draft", ["gtaw_26"], "", False),
 ("p_caledon", "Caledon #1 and #2 TS", "station", 230, ["Caledon"], "2032", "GTA West draft", ["gtaw_26"], "Supplied from Kleinburg TS", False),
 ("p_heritage", "Heritage Heights MTS (NW Brampton)", "station", 230, ["Heritage Heights (NW Brampton)"], "2033", "GTA West draft", ["gtaw_26"], "", False),
 ("p_lakeview", "Lakeview MTS (Cooksville)", "station", 230, ["Lakeview MTS (Cooksville)"], "2033", "GTA West draft", ["gtaw_26"], "", False),
 ("p_gateway", "Gateway MTS (Mississauga)", "station", 230, ["Gateway MTS (Mississauga)"], "2034", "GTA West draft", ["gtaw_26"], "", False),
 ("p_nwgta", "NWGTA corridor 230 kV double circuits (Kleinburg/Milton to Brampton)", "line", 230, ["Kleinburg TS", "Heritage Heights (NW Brampton)", "Milton TS"], "2032-2033", "GTA West draft", ["gtaw_26"], "Corridor protected for 500 and 230 kV; route schematic", True),
 ("p_dnnp", "Darlington New Nuclear (BWRX-300 SMRs)", "plant", None, ["BOWMANVILLE"], "after 2030 (revised schedule pending)", "construction", ["opg_smr", "opg_q3_26"], "Unit 1 no longer expected Oct 2030; four units planned", True),
 ("p_brucec", "Bruce C (up to 4,800 MW option)", "plant", None, ["Bruce C site"], "TBD (no build decision)", "impact assessment", ["bp_c", "iaac_brucec"], "", True),
]
pf = []
for pid, name, kind, kv, ends, isd, status, rf, de, est in PJ:
    pts = [pos(e) for e in ends]; pe = any(e in PLPOS_EST for e in ends)
    geom = {"type": "LineString", "coordinates": pts} if kind in ("line", "upgrade") and len(pts) > 1 else {"type": "Point", "coordinates": pts[0]}
    pf.append({"type": "Feature", "geometry": geom, "properties": {"id": pid, "name": name, "kind": kind, "kv": kv, "isd": isd, "isd_est": est, "status": status, "detail": de, "src": src(*rf),
        "route_est": True, "pos_est": pe, "note": "Schematic straight line between endpoints (route not drawn)" if geom["type"] == "LineString" else ("Position ESTIMATE" if pe else "At existing station")}})
W("planned.geojson", {"type": "FeatureCollection", "note": "Planned/recommended projects from public plans. Geometry is schematic.", "features": pf})
# ---------------- registry (uniform entity index for the future Explorer tree) ----------------
FUELN = {"NUCLEAR": "Nuclear", "HYDRO": "Hydro", "GAS": "Gas", "WIND": "Wind", "SOLAR": "Solar", "BIOFUEL": "Biofuel", "OTHER": "Storage/Other"}
reg = []
for st in stations: reg.append({"id": st["id"], "path": ["Generation", FUELN[st["fuel"]], st["name"]], "type": "station", "lon": st["lon"], "lat": st["lat"], "src": st["src"]})
for g in gens: reg.append({"id": "gen:" + g["id"], "path": ["Generation", FUELN.get(g["fuel"], g["fuel"]), "Units (IESO)", g["id"]], "type": "unit", "lon": BP[g["bus"]][0], "lat": BP[g["bus"]][1], "pos_est": True, "src": g["src"]})
for b in branches: reg.append({"id": "br:" + b["id"], "path": ["Interties" if b["tie"] else "Transmission", f"{b['kv']} kV", b["id"]], "type": "branch", "lon": (BP[b["a"]][0] + BP[b["b"]][0]) / 2, "lat": (BP[b["a"]][1] + BP[b["b"]][1]) / 2, "src": b["src"]})
for b in buses: reg.append({"id": "bus:" + b["id"], "path": ["Stations", "Model buses", b["name"]], "type": "bus", "lon": b["lon"], "lat": b["lat"], "src": b["pos_src"]})
for f in pf: p = f["properties"]; c = f["geometry"]["coordinates"]; c = c[0] if f["geometry"]["type"] == "LineString" else c; reg.append({"id": "plan:" + p["id"], "path": ["Planned", p["kind"], p["name"]], "type": "planned", "lon": c[0], "lat": c[1], "src": p["src"]})
for e in history["events"]: reg.append({"id": "hist:" + e["id"], "path": ["History", str(e["year"]), e["title"]], "type": "event", "lon": e["lon"], "lat": e["lat"], "src": e["src"]})
W("registry.json", {"note": "Flat entity index; path[] is the tree location. OSM lines/substations are indexed by their osm id in the GeoJSON files (path Transmission/<kV>/<ref> and Stations/<kV>/<name>).", "entities": reg})
# ---------------- sources + SOURCES.md ----------------
for k in ("osm", "overpass", "esri", "awsterrain", "gridwatch_home", "ieso_powerdata", "apo", "ro", "ieso_rp", "on_pog", "on_ieP", "ho_projects", "kwcg_irrp21", "gtaw_news", "gtaw_irrp_app"): used[k] += 0
W("sources.json", {"accessed": ACC, "sources": {k: {"title": t, "url": u, "uses": used.get(k, 0)} for k, (t, u) in S.items()}})
L = ["# SOURCES", "", f"All sources accessed {ACC} unless noted. Every number in `data/*.json` cites source ids from this list in a `src` field; values marked `est: true` / `*_est: true` are **ESTIMATE** and shown as ESTIMATE in the UI.", "",
     "## What is ESTIMATE in v0.1.0", "",
     "- Branch reactances (generic ohm/km), all thermal limits except the Niagara tie transformer ratings (PA301/PA302 1000 MVA, BP76 400 MVA, NYISO), most circuit counts not stated in a source.",
     "- Topology: OSM corridor lengths are derived automatically (`data/topology_osm.json`); some model branches have no traced OSM path and use straight-line distance x 1.15.",
     "- Generator-to-bus assignment for all units except Bruce, Darlington, Pickering, Beck/DeCew (sited at their own switchyards).",
     "- Bus load weights inside each IESO zone (zonal totals are IESO actuals).",
     "- REST (rest of Ontario) equivalent and its links; Michigan PARs not modelled.",
     "- Planned project routes (schematic straight lines), several positions and in-service dates (flagged per project).",
     "- History dates flagged `est` (month-level dates and one source conflict: Atikokan biomass 2014 vs 2015).",
     "- Interpretation of the sign of IESO actual intertie flow (positive = export).", "",
     "## Interface capabilities used (IESO 2025 APO, Table 1, 2027 summer, all elements in service)", "",
     "FETT 5,900 MW · QFW 2,025 MW · FN 1,960 / FS 2,150 MW · ON->MI 1,500 / MI->ON 1,650 MW · ON->NY (Niagara) 2,150 / NY->ON 1,835 MW. Source: apo_interfaces.", "",
     "## Gridwatch cross-check", "", f"Snapshot {xcheck['snapshot']}: Gridwatch fuel MW {json.dumps(xcheck['gridwatch_mw'])}; IESO hour 1 2026-11-18 {json.dumps({k: round(v) for k, v in xcheck['ieso_hour1_20261118_mw'].items()})}.", "",
     "## Source list", "", "| id | title | URL | uses |", "|---|---|---|---|"]
for k, (t, u) in S.items(): L.append(f"| {k} | {t} | {u} | {used.get(k, 0)} |")
L += ["", "## Raw extracts", "", "`data/raw/` holds the unmodified downloads (Overpass JSON with the query text, IESO XML/CSV, Gridwatch JSON). Rebuild: `python3 tools/fetch_osm.py && python3 tools/build_osm.py && python3 tools/build_model.py`.", ""]
open(os.path.join(ROOT, "SOURCES.md"), "w").write("\n".join(L))
print("buses", len(buses), "branches", len(branches), "gens", len(gens), "stations", len(stations), "events", len(history["events"]), "planned", len(pf), "registry", len(reg), "sources", len(S), "cited", sum(1 for k in S if used.get(k)))
print("2025 peak", pkday, pk[1], pk[3], "| min", loday, lo[1], lo[3])
print("xcheck", json.dumps(xcheck)[:600])
for st in stations: print(" ", st["name"], st["cap_mw_20261116"], st["bus"], st.get("osm_name"), st["pos_est"])
