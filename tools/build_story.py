"""Verify quotes against the Garnett text and compute street-following routes.

usage: python3 build_story.py data/story.json build/chapters.json build/graph.pkl data/map.json out.json
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

# ---------- routing ----------
adj, gnodes = G['adj'], G['nodes']
pts = {n: P(*ll) for n, ll in gnodes.items()}
CELL = 50.0
grid = {}
for n, (x, y) in pts.items():
    grid.setdefault((int(x // CELL), int(y // CELL)), []).append(n)


def nearest(x, y):
    cx, cy = int(x // CELL), int(y // CELL)
    best, bd = None, 1e18
    for r in range(0, 8):
        for i in range(cx - r, cx + r + 1):
            for j in range(cy - r, cy + r + 1):
                if max(abs(i - cx), abs(j - cy)) != r:
                    continue
                for n in grid.get((i, j), ()):
                    d = (pts[n][0] - x) ** 2 + (pts[n][1] - y) ** 2
                    if d < bd:
                        bd, best = d, n
        if best is not None and math.sqrt(bd) < r * CELL:
            break
    return best, math.sqrt(bd)


def dijkstra(a, b):
    dist = {a: 0.0}
    prev = {}
    h = [(0.0, a)]
    bx, by = pts[b]
    while h:
        d, u = heapq.heappop(h)
        if u == b:
            break
        if d > dist.get(u, 1e18):
            continue
        for v, w, _ in adj.get(u, ()):
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(h, (nd, v))
    if b not in dist:
        return None
    path = [b]
    while path[-1] != a:
        path.append(prev[path[-1]])
    return path[::-1]


def rdp(p, eps):
    if len(p) < 3:
        return p
    (x1, y1), (x2, y2) = p[0], p[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(p) - 1):
        d = abs(dy * p[i][0] - dx * p[i][1] + x2 * y1 - y2 * x1) / L
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return rdp(p[:idx + 1], eps)[:-1] + rdp(p[idx:], eps)
    return [p[0], p[-1]]


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
    full = []
    total = 0.0
    for a, b in zip(seq, seq[1:]):
        la, lb = ll_of(a), ll_of(b)
        na, da = nearest(*P(*la))
        nb, db = nearest(*P(*lb))
        if da > 60 or db > 60:
            print('WARN far snap', e['id'], a, round(da), b, round(db))
        path = dijkstra(na, nb)
        if path is None:
            print('NO PATH', e['id'], a, b)
            continue
        seg = [pts[n] for n in path]
        if isinstance(a, str) or not full:
            seg = [P(*la)] + seg
        seg = seg + [P(*lb)]
        for u, v in zip(seg, seg[1:]):
            total += math.dist(u, v)
        full += seg if not full else seg[1:]
    simp = rdp(full, 1.2)
    e['route'] = [[round(x, 1), round(y, 1)] for x, y in simp]
    e['len'] = round(total)

# special measurements quoted in the text
pace = story['meta']['pace_m']
for e in story['events']:
    if e.get('measure') == 'paces730':
        a = nearest(*P(*ll_of(e['from'])))[0]
        b = nearest(*P(*ll_of(e['loc'])))[0]
        sp = dijkstra(a, b)
        short = sum(math.dist(pts[u], pts[v]) for u, v in zip(sp, sp[1:]))
        e['measure'] = {'label': '730 paces', 'paces': 730, 'text_m': round(730 * pace), 'route_m': e['len'], 'short_m': round(short)}
    elif e.get('measure') == 'verst025':
        def shortest(la, lb):
            sp = dijkstra(nearest(*P(*la))[0], nearest(*P(*lb))[0])
            return round(sum(math.dist(pts[u], pts[v]) for u, v in zip(sp, sp[1:])))
        g = locs['garret']['ll']
        e['measure'] = {'label': 'a quarter of a verst', 'text_m': round(0.25 * story['meta']['verst_m']), 'route_m': e['len'],
                        'short_m': shortest(g, locs['police']['ll']), 'rival_m': shortest(g, [59.9296, 30.3268])}

for e in story['events']:
    print(f"{e['id']} d{e['day']:>2} {e['t']} {e['loc']:<12} len={e['len']:>5} pts={len(e['route'] or [])} ref={e.get('qref')}")
json.dump(story, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print('wrote', OUT)
