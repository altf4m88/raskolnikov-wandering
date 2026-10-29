"""Warp an old city plan onto this map's extent.

usage: python3 -I georef_plan.py PLAN.jpg data/plan_gcp.json data/map.json OUT.jpg [WIDTH]

PLAN is the 3840 px wide Wikimedia Commons rendition of Musnitsky's 1868 plan (Commons serves
only standard thumbnail sizes to scripts; the original is 16281 px):
https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Plan_of_Saint-Petersburg_by_Musnitsky%2C_1868.jpg/3840px-Plan_of_Saint-Petersburg_by_Musnitsky%2C_1868.jpg

1. data/plan_gcp.json lists about twenty points picked by hand: street crossings and bridges
   that exist both on the plan and today, with their OSM lat/lon and their plan pixel. A
   polynomial through them gives a first warp.
2. That first warp is refined against OpenStreetMap: on a grid of patches, the plan's streets
   (near-white) and water (blue-grey) are cross-correlated with today's street centre lines and
   water areas, and each patch's best shift becomes a tie point. Patches that don't match
   cleanly are dropped, as are tie points that disagree with their neighbours.
3. A final polynomial through the tie points is chosen by leave-one-out error, the honest
   figure: how far off a patch lands when it did not help fit the warp. Then the plan is
   resampled north-up onto the extent.
"""
import sys, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PLAN, GCP, MAP, OUT = sys.argv[1:5]
WIDTH = int(sys.argv[5]) if len(sys.argv) > 5 else 2000
Image.MAX_IMAGE_PIXELS = 400_000_000

M = json.load(open(MAP))
LAT0, LON0 = M['origin']; KX, KY = M['k']
x0, y0, x1, y1 = M['ext']
pts = [p for p in json.load(open(GCP))['points'] if p.get('px') and not p.get('skip')]
XY = np.array([((p['ll'][1] - LON0) * KX, (p['ll'][0] - LAT0) * KY) for p in pts])
UV = np.array([p['px'] for p in pts], float)

# ---------- polynomial fits, local metres -> plan pixels ----------
C, S = np.array([(x0 + x1) / 2, (y0 + y1) / 2]), max(x1 - x0, y1 - y0) / 2
def terms(xy, order):
    x, y = ((np.atleast_2d(xy) - C) / S).T
    t = [np.ones_like(x)]
    for n in range(1, order + 1):
        t += [x ** (n - k) * y ** k for k in range(n + 1)]
    return np.stack(t, 1)
def fit(xy, uv, order):
    return np.linalg.lstsq(terms(xy, order), uv, rcond=None)[0]
def apply(coef, xy):
    order = {3: 1, 6: 2, 10: 3}[len(coef)]
    return terms(xy, order) @ coef
def loo(xy, uv, order):
    return np.array([np.linalg.norm(apply(fit(np.delete(xy, i, 0), np.delete(uv, i, 0), order), xy[i])[0] - uv[i]) for i in range(len(xy))])

coef = fit(XY, UV, 2)
J = np.linalg.lstsq(terms(XY, 1), UV, rcond=None)[0][1:3] / S
MPP = 1 / math.sqrt(abs(np.linalg.det(J)))  # metres per plan pixel
print(f'{len(pts)} hand-picked points; the plan is {MPP:.2f} m per pixel')

# ---------- the part of the plan that lands on the map ----------
src = Image.open(PLAN).convert('RGB')
corners = apply(coef, np.array([[x, y] for x in np.linspace(x0, x1, 9) for y in np.linspace(y0, y1, 9)]))
pad = 120
cu0, cv0 = max(0, int(corners[:, 0].min()) - pad), max(0, int(corners[:, 1].min()) - pad)
cu1, cv1 = min(src.width, int(corners[:, 0].max()) + pad), min(src.height, int(corners[:, 1].max()) + pad)
A = np.asarray(src.crop((cu0, cv0, cu1, cv1)))

def warp(coef, width):
    h = round(width * (y1 - y0) / (x1 - x0))
    gx = x0 + (np.arange(width) + 0.5) / width * (x1 - x0)
    gy = y1 - (np.arange(h) + 0.5) / h * (y1 - y0)
    GX, GY = np.meshgrid(gx, gy)
    uv = apply(coef, np.stack([GX.ravel(), GY.ravel()], 1))
    u, v = uv[:, 0].reshape(h, width) - cu0, uv[:, 1].reshape(h, width) - cv0
    inside = (u >= 0) & (v >= 0) & (u <= A.shape[1] - 1) & (v <= A.shape[0] - 1)
    u, v = np.clip(u, 0, A.shape[1] - 1.001), np.clip(v, 0, A.shape[0] - 1.001)
    iu, iv = u.astype(int), v.astype(int)
    fu, fv = (u - iu)[..., None].astype(np.float32), (v - iv)[..., None].astype(np.float32)
    f = np.float32
    out = (A[iv, iu].astype(f) * (1 - fu) * (1 - fv) + A[iv, iu + 1].astype(f) * fu * (1 - fv)
           + A[iv + 1, iu].astype(f) * (1 - fu) * fv + A[iv + 1, iu + 1].astype(f) * fu * fv)
    out[~inside] = (236, 223, 184)  # off the plan: the page's paper colour
    return out.round().astype(np.uint8)

# ---------- today's streets and water, rasterised at the working resolution ----------
RW = 2000
RH = round(RW * (y1 - y0) / (x1 - x0)); RM = (x1 - x0) / RW
topx = lambda x, y: ((x - x0) / RM, (y1 - y) / RM)
st = Image.new('L', (RW, RH)); ds = ImageDraw.Draw(st)
for s in M['s']:
    ds.line([topx(*p) for p in s['c']], fill=255, width=max(3, round(12 / RM)))
wa = Image.new('L', (RW, RH)); dw = ImageDraw.Draw(wa)
for poly in M['water']:
    dw.polygon([topx(*p) for p in poly[0]], fill=255)
    for hole in poly[1:]:
        dw.polygon([topx(*p) for p in hole], fill=0)
OSM_S = np.asarray(st.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
OSM_W = np.asarray(wa, np.float32) / 255

def plan_masks(img):
    i = img.astype(np.int16)
    street = ((i.min(2) > 172) & (i[..., 0] - i[..., 2] < 45)).astype(np.float32)
    water = ((i[..., 2] - i[..., 0] > 8) & (i[..., 1] - i[..., 0] > 8)).astype(np.float32)
    return np.asarray(Image.fromarray((street * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255, water

def ncc(big, tmpl, s):
    """normalised cross-correlation of tmpl (n x n) over big ((n+2s) x (n+2s)), for shifts -s..s"""
    n = tmpl.shape[0]
    t = tmpl - tmpl.mean(); tn = math.sqrt((t * t).sum())
    if tn < 1e-6: return None
    F = np.fft.rfft2(big); T = np.fft.rfft2(t, big.shape)
    corr = np.fft.irfft2(F * np.conj(T), big.shape)[:2 * s + 1, :2 * s + 1]
    c1 = np.cumsum(np.cumsum(np.pad(big, ((1, 0), (1, 0))), 0), 1)
    c2 = np.cumsum(np.cumsum(np.pad(big * big, ((1, 0), (1, 0))), 0), 1)
    box = lambda c: c[n:n + 2 * s + 1, n:n + 2 * s + 1] - c[:2 * s + 1, n:n + 2 * s + 1] - c[n:n + 2 * s + 1, :2 * s + 1] + c[:2 * s + 1, :2 * s + 1]
    var = box(c2) - box(c1) ** 2 / (n * n)
    return corr / (tn * np.sqrt(np.maximum(var, 1e-6)))

def tie_points(coef, step=300, half=300, search=70):
    img = warp(coef, RW)
    PS, PW = plan_masks(img)
    h, s = round(half / RM), round(search / RM)
    out = []
    for cx in np.arange(x0 + half + search, x1 - half - search + 1, step):
        for cy in np.arange(y0 + half + search, y1 - half - search + 1, step):
            j, i = (round(v) for v in topx(cx, cy))
            o_s, o_w = OSM_S[i - h:i + h, j - h:j + h], OSM_W[i - h:i + h, j - h:j + h]
            if o_s.mean() < 0.06: continue  # too few streets to lock onto
            big = lambda P: P[i - h - s:i + h + s, j - h - s:j + h + s]
            sc = ncc(big(PS), o_s, s)
            if sc is None: continue
            if 0.04 < o_w.mean() < 0.9:
                sw = ncc(big(PW), o_w, s)
                if sw is not None: sc = (sc + sw) / 2
            k = np.unravel_index(np.argmax(sc), sc.shape)
            if sc[k] < 0.22 or min(k) == 0 or max(k) == 2 * s: continue  # weak, or pinned to the search edge
            dy_px, dx_px = k[0] - s, k[1] - s
            d = np.array([dx_px * RM, -dy_px * RM])  # the plan shows this patch d metres away from OSM
            out.append((cx, cy, apply(coef, np.array([cx, cy]) + d)[0], sc[k]))
    return out

for rnd in range(3):
    T = tie_points(coef)
    TX = np.array([[t[0], t[1]] for t in T]); TU = np.array([t[2] for t in T])
    keep = np.ones(len(T), bool)
    for _ in range(4):  # drop tie points that disagree with the rest
        r = np.linalg.norm(apply(fit(TX[keep], TU[keep], 2), TX) - TU, axis=1)
        med = np.median(r[keep]); keep = r < max(3.0, 3.5 * med * 1.4826)
    order = min((2, 3), key=lambda o: math.sqrt((loo(TX[keep], TU[keep], o) ** 2).mean()))
    coef = fit(TX[keep], TU[keep], order)
    print(f'round {rnd + 1}: {len(T)} patches matched, {keep.sum()} kept, order {order}')

res = np.linalg.norm(apply(coef, TX[keep]) - TU[keep], axis=1) * MPP
lo = loo(TX[keep], TU[keep], order) * MPP
hand = np.linalg.norm(apply(coef, XY) - UV, axis=1) * MPP
print(f'tie points: RMS {math.sqrt((res ** 2).mean()):.1f} m, leave-one-out RMS {math.sqrt((lo ** 2).mean()):.1f} m, '
      f'90th percentile {np.percentile(lo, 90):.1f} m')
# the seed points were picked by eye on a 4.6 m/px scan; they only start the fit, and some are tens of metres out
print(f'hand-picked seed points against the final warp: median {np.median(hand):.1f} m, worst:')
for p, r in sorted(zip(pts, hand), key=lambda z: -z[1])[:6]:
    print(f'  {p["id"]:<16} {r:5.1f} m  {p["name"]}')

Image.fromarray(warp(coef, WIDTH)).save(OUT, quality=84, optimize=True, progressive=True)
print(f'wrote {OUT}: {WIDTH} x {round(WIDTH * (y1 - y0) / (x1 - x0))}, {(x1 - x0) / WIDTH:.2f} m per pixel')
