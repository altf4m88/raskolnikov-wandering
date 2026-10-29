"""Verify quotes against Garnett and Dostoevsky, and compute street-following routes.

usage: python3 build_story.py data/story.json cache/chapters.json cache/build/graph.pkl data/map.json out.json [cache/ru_chapters.json]
The last argument is optional; without it the Russian quotes are not checked.
"""
import sys, json, math, re, heapq, pickle

story = json.load(open(sys.argv[1]))
chapters = json.load(open(sys.argv[2]))
G = pickle.load(open(sys.argv[3], 'rb'))
M = json.load(open(sys.argv[4]))
OUT = sys.argv[5]

LAT0, LON0 = M['origin']
KX, KY = M['k']


def P(lat, lon):
    return ((lon - LON0) * KX, (lat - LAT0) * KY)


# ---------- quotes ----------
def norm(s):
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    s = s.replace('—', '--').replace('_', '').replace('ï', 'i')
    return re.sub(r'\s+', ' ', s).strip()


ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8}
book = [(c['part'], c['ch'], norm(c['text'])) for c in chapters]
bad = 0
for e in story['events']:
    q = norm(e['q'])
    hits = [f"{p}.{ROMAN.get(c, c)}" for p, c, t in book if q in t]
    if not hits:
        bad += 1
        print('QUOTE NOT FOUND', e['id'], '|', e['q'][:90])
    else:
        e['qref'] = hits[0].replace('E.', 'Ep.')
print('quotes checked:', len(story['events']), 'missing:', bad)

# ---------- Russian quotes: each segment must occur verbatim in Dostoevsky's text ----------
if len(sys.argv) > 6:
    def norm_ru(s):
        s = s.replace('\u2014', '—').replace('\xa0', ' ')
        return re.sub(r'\s+', ' ', s).strip()
    ru_book = [(c['part'], c['ch'], norm_ru(c['text'])) for c in json.load(open(sys.argv[6]))]
    rbad = 0
    for e in story['events']:
        if 'ru' not in e:
            rbad += 1
            print('NO RUSSIAN', e['id'])
            continue
        segs = e['ru'] if isinstance(e['ru'], list) else [e['ru']]
        refs = []
        for seg in segs:
            hits = [f"{p}.{ROMAN.get(c, c)}" for p, c, t in ru_book if norm_ru(seg) in t]
            if not hits:
                rbad += 1
                print('RUSSIAN NOT FOUND', e['id'], '|', seg[:80])
            refs += hits[:1]
        if refs:
            e['ruref'] = refs[0].replace('E.', 'Ep.')
            if e.get('qref') and e['ruref'] != e['qref']:
                print('WARN chapter differs', e['id'], e['qref'], e['ruref'])
    print('russian quotes checked:', len(story['events']), 'missing:', rbad)

# ---------- routing ----------
adj, gnodes = G['adj'], G['nodes']
pts = {n: P(*ll) for n, ll in gnodes.items()}
CELL = 50.0

# Waypoints snap onto the nearest street *segment*, not the nearest graph node. Snapping to
# nodes made walks overshoot to the far end of long edges (a bridge is one 300 m edge) and then
# double back, which looked like Raskolnikov stepping backwards.
edges = {}
for u, lst in adj.items():
    for v, w, d in lst:
        k = (u, v) if u < v else (v, u)
        if k not in edges and d > 0:
            edges[k] = (w / d, d)
egrid = {}
for (u, v) in edges:
    (x1, y1), (x2, y2) = pts[u], pts[v]
    for cx in range(int(min(x1, x2) // CELL), int(max(x1, x2) // CELL) + 1):
        for cy in range(int(min(y1, y2) // CELL), int(max(y1, y2) // CELL) + 1):
            egrid.setdefault((cx, cy), []).append((u, v))


def snap(x, y):
    """nearest point on any street segment: (u, v, t along u->v, (px, py), distance)"""
    cx, cy = int(x // CELL), int(y // CELL)
    best = None
    for r in range(0, 10):
        for i in range(cx - r, cx + r + 1):
            for j in range(cy - r, cy + r + 1):
                if max(abs(i - cx), abs(j - cy)) != r:
                    continue
                for (u, v) in egrid.get((i, j), ()):
                    (x1, y1), (x2, y2) = pts[u], pts[v]
                    dx, dy = x2 - x1, y2 - y1
                    L2 = dx * dx + dy * dy or 1e-9
                    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
                    px, py = x1 + t * dx, y1 + t * dy
                    d = math.hypot(px - x, py - y)
                    if best is None or d < best[4]:
                        best = (u, v, t, (px, py), d)
        if best is not None and best[4] < r * CELL:
            break
    return best


def route(pa, pb, weighted=True):
    """shortest walk between two arbitrary points, entering and leaving the graph mid-edge"""
    ua, va, ta, qa, _ = snap(*pa)
    ub, vb, tb, qb, _ = snap(*pb)
    pen_a, La = edges[(ua, va) if ua < va else (va, ua)]
    pen_b, Lb = edges[(ub, vb) if ub < vb else (vb, ub)]
    if not weighted:
        pen_a = pen_b = 1.0
    dist, prev = {ua: ta * La * pen_a, va: (1 - ta) * La * pen_a}, {ua: None, va: None}
    h = [(dist[ua], ua), (dist[va], va)]
    heapq.heapify(h)
    done = set()
    while h and not (ub in done and vb in done):
        d, u = heapq.heappop(h)
        if u in done:
            continue
        done.add(u)
        for v, w, l in adj.get(u, ()):
            nd = d + (w if weighted else l)
            if nd < dist.get(v, 1e18):
                dist[v], prev[v] = nd, u
                heapq.heappush(h, (nd, v))
    options = []
    if ub in dist:
        options.append((dist[ub] + tb * Lb * pen_b, ub))
    if vb in dist:
        options.append((dist[vb] + (1 - tb) * Lb * pen_b, vb))
    if {ua, va} == {ub, vb}:  # both on the same street segment
        tb2 = tb if (ua, va) == (ub, vb) else 1 - tb
        options.append((abs(ta - tb2) * La * pen_a, None))
    cost, endn = min(options)
    if endn is None:
        return [qa, qb]
    chain = [endn]
    while prev[chain[-1]] is not None:
        chain.append(prev[chain[-1]])
    return [qa] + [pts[n] for n in chain[::-1]] + [qb]


def plen(p):
    return sum(math.dist(a, b) for a, b in zip(p, p[1:]))


def rdp(p, eps):
    if len(p) < 3:
        return p
    (x1, y1), (x2, y2) = p[0], p[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    dmax, idx = 0, 0
    for i in range(1, len(p) - 1):
        if L < 1e-6:  # closed path (a round trip): measure from the endpoint itself
            d = math.dist(p[i], p[0])
        else:
            d = abs(dy * p[i][0] - dx * p[i][1] + x2 * y1 - y2 * x1) / L
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return rdp(p[:idx + 1], eps)[:-1] + rdp(p[idx:], eps)
    return [p[0], p[-1]]


def dedupe(p):
    out = [p[0]]
    for q in p[1:]:
        if math.dist(q, out[-1]) > 0.3:
            out.append(q)
    return out


def cut_loops(p):
    """drop short out-and-back excursions: the path returns to a point it already visited"""
    total = plen(p)
    limit = min(80.0, 0.3 * total)  # only slop; deliberate detours through a waypoint are longer
    changed = True
    while changed:
        changed = False
        cum = [0.0]
        for a, b in zip(p, p[1:]):
            cum.append(cum[-1] + math.dist(a, b))
        cells = {}
        for i, q in enumerate(p):
            cells.setdefault((int(q[0] // 4), int(q[1] // 4)), []).append(i)
        for i, q in enumerate(p):
            cx, cy = int(q[0] // 4), int(q[1] // 4)
            far = None
            for a in (cx - 1, cx, cx + 1):
                for b in (cy - 1, cy, cy + 1):
                    for j in cells.get((a, b), ()):
                        if j > i + 1 and math.dist(q, p[j]) < 3.0 and 6 < cum[j] - cum[i] < limit:
                            far = j if far is None else max(far, j)
            if far is not None:
                p = p[:i + 1] + p[far + 1:]
                changed = True
                break
    return p


def turn(a, b, c):
    v1 = (b[0] - a[0], b[1] - a[1]); v2 = (c[0] - b[0], c[1] - b[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return 0.0, n1, n2
    cosv = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(cosv)), n1, n2


def cut_uturns(p, keep):
    """remove hairpin reversals with a short leg (sidewalk hops, snapping slop)"""
    changed = True
    while changed and len(p) > 2:
        changed = False
        for i in range(1, len(p) - 1):
            if i in keep:
                continue
            ang, n1, n2 = turn(p[i - 1], p[i], p[i + 1])
            if ang > 150 and min(n1, n2) < 40:
                p = p[:i] + p[i + 1:]
                keep = {k - 1 if k > i else k for k in keep}
                changed = True
                break
    return p


# open ground test for shortcuts: buildings and water block a straight line
from shapely.geometry import Polygon as _Poly, LineString as _Line
from shapely.strtree import STRtree
_obst = []
for bld in M['b']:
    if len(bld['o']) >= 3:
        _obst.append(_Poly(bld['o']).buffer(-0.5))
for poly in M['water']:
    if len(poly[0]) >= 3:
        _obst.append(_Poly(poly[0], [h for h in poly[1:] if len(h) >= 3]).buffer(-0.5))
_obst = [g for g in _obst if not g.is_empty and g.is_valid]
_tree = STRtree(_obst)


def clear(a, b):
    ln = _Line([a, b])
    return not any(_obst[i].intersects(ln) for i in _tree.query(ln))


def shortcuts(p, keep_ends=True):
    """replace a long detour by a straight walk when the two ends are close and nothing is in between"""
    changed = True
    while changed:
        changed = False
        cum = [0.0]
        for a, b in zip(p, p[1:]):
            cum.append(cum[-1] + math.dist(a, b))
        for i in range(1, len(p) - 2):
            for j in range(min(len(p) - 2, i + 80), i + 1, -1):
                d = math.dist(p[i], p[j])
                if d < 35 and cum[j] - cum[i] > 3 * d + 40 and clear(p[i], p[j]):
                    p = p[:i + 1] + p[j:]
                    changed = True
                    break
            if changed:
                break
    return p


def round_corners(p, rmax=9.0, steps=5):
    """replace each corner with a short quadratic curve so the walker turns instead of pivoting"""
    if len(p) < 3:
        return p
    out = [p[0]]
    for i in range(1, len(p) - 1):
        a, b, c = p[i - 1], p[i], p[i + 1]
        ang, n1, n2 = turn(a, b, c)
        if ang < 12:
            out.append(b)
            continue
        r = min(rmax, 0.4 * n1, 0.4 * n2)
        s0 = (b[0] - (b[0] - a[0]) / n1 * r, b[1] - (b[1] - a[1]) / n1 * r)
        s1 = (b[0] + (c[0] - b[0]) / n2 * r, b[1] + (c[1] - b[1]) / n2 * r)
        for k in range(steps + 1):
            t = k / steps
            out.append(((1 - t) ** 2 * s0[0] + 2 * (1 - t) * t * b[0] + t * t * s1[0],
                        (1 - t) ** 2 * s0[1] + 2 * (1 - t) * t * b[1] + t * t * s1[1]))
    out.append(p[-1])
    return dedupe(out)


locs = story['locations']


def ll_of(ref):
    if isinstance(ref, str):
        return locs[ref]['ll']
    return ref


for k, l in locs.items():
    x, y = P(*l['ll'])
    l['p'] = [round(x, 1), round(y, 1)]
for lm in story['landmarks']:
    x, y = P(*lm['ll'])
    lm['p'] = [round(x, 1), round(y, 1)]

last = {}
backsteps = 0
for e in story['events']:
    who = e['who']
    start = e.get('from', last.get(who))
    last[who] = e['loc']
    e['route'] = None
    e['len'] = 0
    if e['loc'] == 'siberia' or start is None:
        continue
    seq = [start] + list(e.get('via', [])) + [e['loc']]
    if start == e['loc'] and not e.get('via'):
        continue
    for ref in seq:
        d = snap(*P(*ll_of(ref)))[4]
        if d > 60:
            print('WARN far from any street', e['id'], ref, round(d))
    # the door of the start and end buildings, then street-only legs through the waypoints
    full = [P(*ll_of(seq[0]))]
    for a, b in zip(seq, seq[1:]):
        full += route(P(*ll_of(a)), P(*ll_of(b)))
    full.append(P(*ll_of(seq[-1])))
    full = dedupe(full)
    full = cut_loops(full)
    full = rdp(full, 2.0)
    roundtrip = start == e['loc']
    if not roundtrip:
        full = shortcuts(full)
    full = cut_uturns(full, keep=set() if not roundtrip else set(range(1, len(full) - 1)))
    full = round_corners(full)
    # count remaining reversals so a regression is visible in the build log
    for i in range(1, len(full) - 1):
        ang, n1, n2 = turn(full[i - 1], full[i], full[i + 1])
        if ang > 150 and min(n1, n2) < 40 and not roundtrip:
            backsteps += 1
    e['route'] = [[round(x, 1), round(y, 1)] for x, y in full]
    e['len'] = round(plen(full))
print('hairpin back-steps left:', backsteps)

# special measurements quoted in the text
pace = story['meta']['pace_m']
for e in story['events']:
    if e.get('measure') == 'paces730':
        short = plen(route(P(*ll_of(e['from'])), P(*ll_of(e['loc'])), weighted=False))
        e['measure'] = {'label': '730 paces', 'paces': 730, 'text_m': round(730 * pace), 'route_m': e['len'], 'short_m': round(short)}
    elif e.get('measure') == 'verst025':
        def shortest(la, lb):
            return round(plen(route(P(*la), P(*lb), weighted=False)))
        g = locs['garret']['ll']
        e['measure'] = {'label': 'a quarter of a verst', 'text_m': round(0.25 * story['meta']['verst_m']), 'route_m': e['len'],
                        'short_m': shortest(g, locs['police']['ll']), 'rival_m': shortest(g, [59.9296, 30.3268])}

for e in story['events']:
    print(f"{e['id']} d{e['day']:>2} {e['t']} {e['loc']:<12} len={e['len']:>5} pts={len(e['route'] or [])} ref={e.get('qref')}")
json.dump(story, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print('wrote', OUT)
