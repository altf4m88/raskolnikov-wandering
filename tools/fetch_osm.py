"""Download the OpenStreetMap tiles and water relations the map is built from.

usage: python3 fetch_osm.py CACHE_DIR
Writes CACHE_DIR/osm_raw/*.osm (bbox tiles) and CACHE_DIR/osm_rel/*.osm (full water relations).
Uses the OSM editing API (overpass was unreachable when this was built), so it is deliberately
slow and polite: about 60 small requests with pauses. Re-running skips files already present.
"""
import sys, os, time, urllib.request, urllib.error

CACHE = sys.argv[1]
RAW = os.path.join(CACHE, 'osm_raw')
REL = os.path.join(CACHE, 'osm_rel')
os.makedirs(RAW, exist_ok=True)
os.makedirs(REL, exist_ok=True)
UA = {'User-Agent': 'raskolnikov-wandering/1.0 (literary map; low volume)'}


def get(url, path):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                data = r.read()
            open(path, 'wb').write(data)
            print(os.path.basename(path), len(data), flush=True)
            time.sleep(3)
            return True
        except urllib.error.HTTPError as ex:
            if ex.code == 400:
                return False  # too many nodes: caller splits the tile
            print(os.path.basename(path), 'HTTP', ex.code, flush=True)
            time.sleep(8 * (attempt + 1))  # 509 = bandwidth limit, back off
        except Exception as ex:
            print(os.path.basename(path), 'ERR', ex, flush=True)
            time.sleep(8 * (attempt + 1))
    raise SystemExit('giving up on ' + url)


def tile(name, w, s, e, n, depth=0):
    path = os.path.join(RAW, name + '.osm')
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return
    url = f"https://api.openstreetmap.org/api/0.6/map?bbox={w:.5f},{s:.5f},{e:.5f},{n:.5f}"
    if not get(url, path):
        mx, my = (w + e) / 2, (s + n) / 2
        for i, b in enumerate([(w, s, mx, my), (mx, s, e, my), (w, my, mx, n), (mx, my, e, n)]):
            tile(f"{name}_{i}", *b, depth + 1)


def grid(prefix, w, s, e, n, dx, dy):
    i, x = 0, w
    while x < e - 1e-9:
        j, y = 0, s
        while y < n - 1e-9:
            tile(f"{prefix}_{i}_{j}", x, y, min(x + dx, e), min(y + dy, n))
            y += dy; j += 1
        x += dx; i += 1


grid('core', 30.293, 59.918, 30.338, 59.938, 0.0075, 0.005)   # Haymarket district
grid('adm', 30.283, 59.930, 30.318, 59.942, 0.0075, 0.006)    # Admiralty side, Nikolaevsky Bridge
grid('vas', 30.268, 59.937, 30.300, 59.947, 0.008, 0.005)     # Vasilievsky Island, the Lines
grid('vasm', 30.268, 59.930, 30.283, 59.937, 0.0075, 0.0035)
grid('vasw', 30.255, 59.930, 30.268, 59.947, 0.0065, 0.0057)
grid('pet', 30.280, 59.947, 30.322, 59.962, 0.008, 0.005)     # Petersburg Side
grid('pete', 30.322, 59.947, 30.338, 59.962, 0.008, 0.005)
grid('petr', 30.255, 59.946, 30.280, 59.960, 0.0085, 0.007)   # Petrovsky Island
grid('kol', 30.255, 59.917, 30.293, 59.930, 0.0076, 0.0065)   # Kolomna
grid('pal', 30.318, 59.938, 30.338, 59.947, 0.0067, 0.0045)   # Winter Palace

# full water relations, so rivers and canals close properly
for rid in (2599821, 1114249, 72500, 1201708, 1201709, 3298068, 3298111, 1576202, 1576203, 3298067,
            1576258, 3862609, 1312627, 1312677, 2893409, 1576116, 1576084, 10573022, 10573023):
    path = os.path.join(REL, f'r{rid}.osm')
    if not (os.path.exists(path) and os.path.getsize(path) > 1000):
        get(f'https://api.openstreetmap.org/api/0.6/relation/{rid}/full', path)
print('done')
