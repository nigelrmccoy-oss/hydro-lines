"""Fetch raw OSM extracts (Overpass API) for the SW Ontario slice -> data/raw/*.json. Public data, (c) OpenStreetMap contributors, ODbL.
Usage: python3 tools/fetch_osm.py"""
import json, os, sys, time, socket, urllib.request, urllib.parse
_gai = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, f=0, *a, **k: _gai(h, p, socket.AF_INET, *a, **k)  # IPv6 route to Overpass hangs on this host
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BBOX = (42.0, -83.2, 44.6, -78.6)   # S,W,N,E  (E edge stretched past -79.0 to include Darlington)
EPS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
B = "%s,%s,%s,%s" % BBOX
ONB = '41.6,-95.2,56.9,-74.3'  # Ontario bounding box (includes some US/QC; filtered by name/IESO match later)
Q = {
  "lines": f'[out:json][timeout:300];way["power"="line"]["voltage"~"(^|;)(500000|345000|230000|115000)(;|$)"]({B});out tags geom;',
  "cables": f'[out:json][timeout:300];way["power"="cable"]["voltage"~"(500000|345000|230000|115000)"]({B});out tags geom;',
  "substations": f'[out:json][timeout:240];(nwr["power"="substation"]["voltage"~"(500000|345000|230000|115000)"]({B}););out tags center;',
  "plants": f'[out:json][timeout:300];nwr["power"="plant"]({ONB});out tags center;',
  "generators_big": f'[out:json][timeout:300];nwr["power"="generator"]["generator:output:electricity"~"^[0-9.]+ ?MW"]({ONB});out tags center;',
}
def run(q):
    for ep in EPS:
        for t in range(2):
            try:
                req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": "hydro-lines/0.1 (personal, unofficial)"})
                with urllib.request.urlopen(req, timeout=300) as r: return json.load(r), ep
            except Exception as e: print("  ", ep, "fail", e, file=sys.stderr); time.sleep(10)
    raise SystemExit("all Overpass endpoints failed")
only = sys.argv[1:]
for k, q in Q.items():
    if only and k not in only: continue
    d, ep = run(q); d["_query"] = q; d["_endpoint"] = ep; d["_fetched"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    json.dump(d, open(os.path.join(ROOT, "data/raw", f"osm_{k}.json"), "w"))
    print(k, len(d.get("elements", [])), ep); time.sleep(5)
