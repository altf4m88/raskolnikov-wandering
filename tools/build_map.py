"""Build map geometry (local metres around the Haymarket) and a walking graph from OSM tiles.

usage: python3 build_map.py CACHE_DIR OUT_JSON
Reads CACHE_DIR/osm_raw and CACHE_DIR/osm_rel; writes OUT_JSON and CACHE_DIR/build/graph.pkl.
"""
import sys, os, glob, json, math, random, pickle
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(__file__))
from osmload import load
from shapely.geometry import Polygon, MultiPolygon, LineString, box, Point
from shapely.ops import unary_union, linemerge, polygonize
from shapely.validation import make_valid

S = sys.argv[1]
OUT = sys.argv[2]
LAT0, LON0 = 59.9268, 30.3195
KX = math.cos(math.radians(LAT0)) * 111320.0
KY = 110574.0 + 1.0 * (111694.0 - 110574.0) * (LAT0 / 90.0)  # ~111.3 km per degree at 60N


def P(lat, lon):
    return ((lon - LON0) * KX, (lat - LAT0) * KY)


# map extent (lon/lat) -> metres
W, E_, SO, N_ = 30.255, 30.338, 59.917, 59.962
x0, y0 = P(SO, W)
x1, y1 = P(N_, E_)
EXT = box(x0, y0, x1, y1)
print('extent m', round(x0), round(y0), round(x1), round(y1))

os.makedirs(os.path.join(S, 'build'), exist_ok=True)
nodes, ways, rels = load(os.path.join(S, 'osm_raw'), os.path.join(S, 'build/osm_all.pkl'))
# relation fulls for water
rn, rw, rr = {}, {}, {}
for f in glob.glob(os.path.join(S, 'osm_rel/*.osm')):
    for ev, el in ET.iterparse(f):
        if el.tag == 'node':
            rn[int(el.get('id'))] = (float(el.get('lat')), float(el.get('lon')))
        elif el.tag == 'way':
            rw[int(el.get('id'))] = {'n': [int(n.get('ref')) for n in el.findall('nd')], 't': {t.get('k'): t.get('v') for t in el.findall('tag')}}
        elif el.tag == 'relation':
            rr[int(el.get('id'))] = {'m': [(m.get('type'), int(m.get('ref')), m.get('role')) for m in el.findall('member')], 't': {t.get('k'): t.get('v') for t in el.findall('tag')}}
nodes.update(rn)
for k, v in rw.items():
    ways.setdefault(k, v)
for k, v in rr.items():
    rels[k] = v  # full versions win


def coords(nids):
    out = []
    for n in nids:
        if n in nodes:
            la, lo = nodes[n]
            out.append(P(la, lo))
    return out


def mp_polygon(rel):
    """Assemble a multipolygon by polygonizing its member linework (robust to touching rings)."""
    def faces(role_ok):
        lines = []
        for t, r, role in rel['m']:
            if t == 'way' and r in ways and role_ok(role):
                c = coords(ways[r]['n'])
                if len(c) >= 2:
                    lines.append(LineString(c))
        if not lines:
            return None
        polys = list(polygonize(unary_union(lines)))
        return unary_union([make_valid(p) for p in polys]) if polys else None
    outs = faces(lambda role: role in ('outer', ''))
    if outs is None or outs.is_empty:
        return None
    ins = faces(lambda role: role == 'inner')
    if ins is not None and not ins.is_empty:
        outs = outs.difference(ins)
    return outs


def way_polygon(w):
    if len(w['n']) < 4 or w['n'][0] != w['n'][-1]:
        return None
    c = coords(w['n'])
    if len(c) < 4:
        return None
    return make_valid(Polygon(c))


# ---------------- water ----------------
water = []
for rid, r in rels.items():
    t = r['t']
    if t.get('type') == 'multipolygon' and (t.get('natural') == 'water' or t.get('waterway') == 'riverbank' or t.get('water')):
        g = mp_polygon(r)
        if g is not None and not g.is_empty:
            water.append(g)
for wid, w in ways.items():
    t = w['t']
    if t.get('natural') == 'water' or t.get('waterway') == 'riverbank':
        g = way_polygon(w)
        if g is not None:
            water.append(g)
WATER = unary_union([g.buffer(0) for g in water]).intersection(EXT.buffer(5))
WATER = WATER.buffer(0.6).buffer(-0.6).simplify(1.2)
LAND = EXT.difference(WATER).buffer(0)
print('water area km2', round(WATER.area / 1e6, 3), 'land', round(LAND.area / 1e6, 3))

# ---------------- parks ----------------
parks = []
for rid, r in rels.items():
    t = r['t']
    if t.get('type') == 'multipolygon' and (t.get('leisure') in ('park', 'garden') or t.get('landuse') in ('grass',)):
        g = mp_polygon(r)
        if g is not None:
            parks.append(g)
for wid, w in ways.items():
    t = w['t']
    if t.get('leisure') in ('park', 'garden') or t.get('landuse') in ('grass',) or t.get('natural') == 'wood':
        g = way_polygon(w)
        if g is not None:
            parks.append(g)
PARKS = unary_union([p.buffer(0) for p in parks]).intersection(LAND).simplify(1.5)
PARKS = PARKS.buffer(-0.5).buffer(0.5)

# ---------------- buildings ----------------
blds = []


def bheight(t, area):
    lv = t.get('building:levels')
    try:
        lv = float(lv.split(';')[0])
    except Exception:
        lv = None
    if lv is None:
        lv = 4 if area > 300 else 3
    lv = max(1, min(lv, 6))
    return lv


for wid, w in ways.items():
    t = w['t']
    if 'building' not in t or t.get('building') in ('no', 'roof', 'construction', 'ruins'):
        continue
    if t.get('location') == 'underground' or t.get('layer', '0').startswith('-'):
        continue
    g = way_polygon(w)
    if g is None:
        continue
    blds.append((g, t))
for rid, r in rels.items():
    t = r['t']
    if t.get('type') == 'multipolygon' and 'building' in t and t.get('building') not in ('no', 'roof'):
        g = mp_polygon(r)
        if g is not None:
            blds.append((g, t))

out_b = []
for g, t in blds:
    g = g.intersection(EXT)
    if g.is_empty or g.area < 25:
        continue
    g = g.simplify(0.9, preserve_topology=True)
    polys = [g] if g.geom_type == 'Polygon' else [p for p in getattr(g, 'geoms', []) if p.geom_type == 'Polygon']
    for p in polys:
        if p.area < 25:
            continue
        lv = bheight(t, p.area)
        ext = [[round(x), round(y)] for x, y in list(p.exterior.coords)[:-1]]
        holes = []
        for h in p.interiors:
            hc = [[round(x), round(y)] for x, y in list(h.coords)[:-1]]
            if len(hc) >= 3 and Polygon(hc).area > 30:
                holes.append(hc)
        if len(ext) < 3:
            continue
        kind = 0
        b = t.get('building')
        if b in ('church', 'cathedral', 'chapel') or t.get('amenity') == 'place_of_worship':
            kind = 1
        out_b.append({'o': ext, 'h': holes, 'l': lv, 'k': kind})
print('buildings', len(out_b))

# ---------------- bridges (only those standing in 1865) ----------------
BAD_BR = ('Дворцовый', 'Бетанкура', 'Биржевой', 'Троицкий', 'Сампсониевский', 'Литейный')
brs = []
for rid, r in rels.items():
    t = r['t']
    if t.get('man_made') == 'bridge' and t.get('type') == 'multipolygon' and not any(b in t.get('name', '') for b in BAD_BR):
        g = mp_polygon(r)
        if g is not None:
            brs.append(g)
for wid, w in ways.items():
    t = w['t']
    if t.get('man_made') == 'bridge' and not any(b in t.get('name', '') for b in BAD_BR):
        g = way_polygon(w)
        if g is not None:
            brs.append(g)
BRIDGES = unary_union([b.buffer(0) for b in brs]).intersection(EXT).simplify(0.8)
print('bridges', len(getattr(BRIDGES, 'geoms', [BRIDGES])))

# ---------------- streets ----------------
DRAW = {'primary': 3, 'secondary': 3, 'tertiary': 2, 'residential': 1, 'unclassified': 1, 'living_street': 1, 'pedestrian': 1, 'primary_link': 2, 'secondary_link': 2, 'tertiary_link': 1}
streets = []
for wid, w in ways.items():
    t = w['t']
    hw = t.get('highway')
    if hw in DRAW and t.get('area') != 'yes':
        c = coords(w['n'])
        if len(c) < 2:
            continue
        ls = LineString(c).intersection(EXT)
        if ls.is_empty:
            continue
        parts = [ls] if ls.geom_type == 'LineString' else [p for p in getattr(ls, 'geoms', []) if p.geom_type == 'LineString']
        for p in parts:
            p = p.simplify(1.5)
            streets.append({'c': [[round(x), round(y)] for x, y in p.coords], 'r': DRAW[hw], 'n': t.get('name', '')})
print('street segs', len(streets))

# ---------------- routing graph ----------------
WALK = {'primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'living_street', 'pedestrian', 'primary_link', 'secondary_link', 'tertiary_link', 'service', 'footway', 'path', 'steps', 'track', 'cycleway'}
BAD_BRIDGES = ('Дворцовый', 'Бетанкура', 'Биржевой', 'Троицкий')
adj = {}
for wid, w in ways.items():
    t = w['t']
    if t.get('highway') not in WALK or t.get('area') == 'yes' or t.get('indoor') == 'yes' or t.get('access') == 'private':
        continue
    nm = t.get('name', '')
    if any(b in nm for b in BAD_BRIDGES):
        continue
    pen = 1.0
    if t.get('highway') in ('service', 'track'):
        if t.get('service') in ('parking_aisle', 'driveway', 'drive-through'):
            continue
        pen = 2.2
    if t.get('highway') in ('footway', 'path', 'cycleway', 'steps'):
        pen = 1.05 if t.get('footway') in ('sidewalk', 'crossing') else 1.8
    if t.get('tunnel') == 'building_passage' or t.get('covered') == 'yes':
        pen = 3.0
    ns = [n for n in w['n'] if n in nodes]
    for a, b in zip(ns, ns[1:]):
        pa, pb = P(*nodes[a]), P(*nodes[b])
        d = math.dist(pa, pb)
        adj.setdefault(a, []).append((b, d * pen, d))
        adj.setdefault(b, []).append((a, d * pen, d))
print('graph nodes', len(adj))
pickle.dump({'adj': adj, 'nodes': {n: nodes[n] for n in adj}}, open(os.path.join(S, 'build/graph.pkl'), 'wb'))


def q(g, tol=0):
    polys = [g] if g.geom_type == 'Polygon' else [p for p in getattr(g, 'geoms', []) if p.geom_type == 'Polygon']
    out = []
    for p in polys:
        if p.area < 40:
            continue
        out.append([[[round(x), round(y)] for x, y in list(p.exterior.coords)[:-1]]] + [[[round(x), round(y)] for x, y in list(h.coords)[:-1]] for h in p.interiors if Polygon(h).area > 40])
    return out


data = {
    'origin': [LAT0, LON0], 'k': [KX, KY],
    'ext': [round(x0), round(y0), round(x1), round(y1)],
    'land': q(LAND), 'water': q(WATER), 'parks': q(PARKS),
    'b': out_b, 's': streets, 'br': q(BRIDGES),
}
json.dump(data, open(OUT, 'w'), separators=(',', ':'))
print('wrote', OUT, os.path.getsize(OUT) // 1024, 'KB')
