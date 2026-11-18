"""Raw Overpass extracts (data/raw/osm_*.json) -> processed GeoJSON in data/ + OSM-derived corridor topology (data/topology_osm.json).
Every feature carries source_url (the OSM element). (c) OpenStreetMap contributors, ODbL. Usage: python3 tools/build_osm.py"""
import json, os, math, collections, heapq
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = lambda f: json.load(open(os.path.join(ROOT, "data/raw", f)))
W = lambda f, o: json.dump(o, open(os.path.join(ROOT, "data", f), "w"), separators=(",", ":"))
KEEP = {"power","voltage","ref","name","operator","circuits","cables","wires","frequency","line","location","layer","operator:wikidata","wikidata","wikipedia","start_date","substation","plant:source","plant:method","plant:output:electricity","generator:source","generator:output:electricity","operator:short","description","note","source"}
def tags(t): return {k: v for k, v in t.items() if k in KEEP or k.startswith("plant:") or k.startswith("generator:")}
def hav(a, b):
    r = math.pi / 180; dl = (b[1]-a[1])*r; dn = (b[0]-a[0])*r
    h = math.sin(dl/2)**2 + math.cos(a[1]*r)*math.cos(b[1]*r)*math.sin(dn/2)**2; return 12742*math.asin(math.sqrt(h))
def kvs(v):
    out = []
    for p in str(v or "").replace("/", ";").split(";"):
        try: x = int(float(p)) // 1000
        except: continue
        if x >= 100: out.append(x)
    return sorted(set(out), reverse=True)
def country(lon, lat, op):
    if op and any(k in op for k in ("ITC","DTE","National Grid","NYSEG","Penelec","Pennsylvania","Niagara Mohawk","New York Power","Consumers")): return "US"
    return "CA" if op and "Hydro One" in op else None
def url(e): return f"https://www.openstreetmap.org/{e['type']}/{e['id']}"
# ---------- lines + cables ----------
feats = []
for f in ("osm_lines.json", "osm_cables.json"):
    for e in R(f)["elements"]:
        g = e.get("geometry");
        if not g or len(g) < 2: continue
        t = e["tags"]; ks = kvs(t.get("voltage")); 
        if not ks: continue
        coords = [[round(p["lon"], 6), round(p["lat"], 6)] for p in g]
        L = sum(hav(coords[i], coords[i+1]) for i in range(len(coords)-1))
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"osm": f"{e['type']}/{e['id']}", "kv": ks[0], "kvs": ks, "ref": t.get("ref"), "name": t.get("name"), "operator": t.get("operator"),
                "circuits": t.get("circuits"), "power": t.get("power"), "country": country(*coords[0], t.get("operator")), "length_km": round(L, 3), "tags": tags(t), "source_url": url(e)}})
W("lines.geojson", {"type": "FeatureCollection", "source": "OpenStreetMap via Overpass API (power=line/cable, 115-500 kV)", "source_url": "https://www.openstreetmap.org/copyright", "license": "ODbL 1.0", "fetched": R("osm_lines.json").get("_fetched"), "features": feats})
# ---------- substations ----------
subs = []
for e in R("osm_substations.json")["elements"]:
    t = e["tags"]; c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
    if c.get("lat") is None: continue
    subs.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(c["lon"], 6), round(c["lat"], 6)]},
        "properties": {"osm": f"{e['type']}/{e['id']}", "name": t.get("name"), "kv": (kvs(t.get("voltage")) or [0])[0], "kvs": kvs(t.get("voltage")), "operator": t.get("operator"), "substation": t.get("substation"),
            "country": country(c["lon"], c["lat"], t.get("operator")), "tags": tags(t), "source_url": url(e)}})
W("substations.geojson", {"type": "FeatureCollection", "source": "OpenStreetMap via Overpass API (power=substation, 115-500 kV)", "source_url": "https://www.openstreetmap.org/copyright", "license": "ODbL 1.0", "features": subs})
# ---------- plants / big generators (optional) ----------
for raw, out in (("osm_plants.json", "plants_osm.geojson"), ("osm_generators_big.json", "generators_osm.geojson")):
    p = os.path.join(ROOT, "data/raw", raw)
    if not os.path.exists(p): print("missing", raw); continue
    fs = []; seen = set()
    for e in R(raw)["elements"]:
        k = (e["type"], e["id"]); 
        if k in seen: continue
        seen.add(k); t = e["tags"]; c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        if c.get("lat") is None: continue
        fs.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(c["lon"], 6), round(c["lat"], 6)]},
            "properties": {"osm": f"{e['type']}/{e['id']}", "name": t.get("name"), "source": t.get("plant:source") or t.get("generator:source"), "output": t.get("plant:output:electricity") or t.get("generator:output:electricity"),
                "operator": t.get("operator"), "tags": tags(t), "source_url": url(e)}})
    W(out, {"type": "FeatureCollection", "source": f"OpenStreetMap via Overpass API ({raw})", "source_url": "https://www.openstreetmap.org/copyright", "license": "ODbL 1.0", "features": fs}); print(out, len(fs))
# ---------- corridor topology: station-to-station paths along lines of one voltage ----------
SNAP = {500: 1.2, 345: 1.0, 230: 0.8, 115: 0.5}
named = [s for s in subs if s["properties"]["name"]]
def near_sub(pt, kv):
    best = None
    for s in named:
        if kv not in s["properties"]["kvs"] and not (kv == 230 and 345 in s["properties"]["kvs"]): 
            if s["properties"]["kvs"]: continue
        d = hav(pt, s["geometry"]["coordinates"])
        if d <= SNAP[kv] and (best is None or d < best[0]): best = (d, s)
    return best[1]["properties"]["name"] if best else None
corr = []
for kv in (500, 345, 230):
    ways = [f for f in feats if kv in f["properties"]["kvs"]]
    key = lambda c: (round(c[0], 4), round(c[1], 4))  # ~10 m node merge
    adj = collections.defaultdict(list); subof = {}
    for i, f in enumerate(ways):
        cs = f["geometry"]["coordinates"]; a, b = key(cs[0]), key(cs[-1])
        adj[a].append((b, i)); adj[b].append((a, i))
        for n, c in ((a, cs[0]), (b, cs[-1])):
            if n not in subof: subof[n] = near_sub(c, kv)
    starts = collections.defaultdict(list)
    for n, s in subof.items():
        if s: starts[s].append(n)
    found = {}
    for s, ns in starts.items():
        pq = [(0.0, n, ()) for n in ns]; best = {}
        while pq:
            d, n, path = heapq.heappop(pq)
            if n in best: continue
            best[n] = d; t = subof.get(n)
            if t and t != s and path:
                k = tuple(sorted((s, t)))
                if k not in found or d < found[k][0]: found[k] = (d, path)
                continue
            if t and t != s: continue
            for m, wi in adj[n]:
                if m not in best and wi not in path: heapq.heappush(pq, (d + ways[wi]["properties"]["length_km"], m, path + (wi,)))
    for (a, b), (d, path) in found.items():
        refs = sorted({r for wi in path for r in str(ways[wi]["properties"]["ref"] or "").split(";") if r})
        circ = max([int(c) for wi in path for c in [ways[wi]["properties"]["circuits"] or "0"] if str(c).isdigit()] or [0])
        corr.append({"a": a, "b": b, "kv": kv, "length_km": round(d, 1), "refs": refs, "circuits_osm": circ or None, "osm_ways": [ways[wi]["properties"]["osm"] for wi in path]})
json.dump({"note": "Derived automatically from OSM line geometry: endpoints snapped to named substations within " + str(SNAP) + " km. Tees and mid-span taps are not followed. Topology ESTIMATE; not a Hydro One single-line diagram.",
    "source_url": "https://www.openstreetmap.org/copyright", "corridors": corr}, open(os.path.join(ROOT, "data/topology_osm.json"), "w"), indent=0)
print("lines", len(feats), "subs", len(subs), "corridors", len(corr))
for c in sorted(corr, key=lambda c: (-c["kv"], c["a"])):
    if c["kv"] >= 345: print(c["kv"], c["a"], "--", c["b"], c["length_km"], c["refs"][:6])
