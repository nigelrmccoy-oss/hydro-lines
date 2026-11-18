"""One polite GET per source URL (1 s apart); writes logs/links.txt. Usage: python3 tools/check_links.py"""
import sys, os, time, socket, urllib.request
sys.path.insert(0, os.path.dirname(__file__)); from sources import S
_g = socket.getaddrinfo; socket.getaddrinfo = lambda h, p, f=0, *a, **k: _g(h, p, socket.AF_INET, *a, **k)
out = []
for k, (t, u) in S.items():
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (hydro-lines link check)", "Range": "bytes=0-2000"}), timeout=30); c = r.status
    except urllib.error.HTTPError as e: c = e.code
    except Exception as e: c = "ERR " + type(e).__name__
    out.append(f"{c}\t{k}\t{u}"); time.sleep(1)
os.makedirs("logs", exist_ok=True); open("logs/links.txt", "w").write("\n".join(out) + "\n")
print("\n".join(l for l in out if not l.startswith(("200", "206"))))
