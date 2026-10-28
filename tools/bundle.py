"""Pack map geometry + story into the page template.

usage: python3 bundle.py data/map.json data/story.built.json src/app.html OUT_DIR
writes OUT_DIR/index.html (full document), OUT_DIR/artifact.html (body fragment)
and OUT_DIR/csp.txt (a Content-Security-Policy that pins the inline app script by hash).
"""
import sys, json, os, re, hashlib, base64

mp = json.load(open(sys.argv[1]))
st = json.load(open(sys.argv[2]))
tpl = open(sys.argv[3], encoding='utf-8').read()
out_dir = sys.argv[4]


def ring(r):
    """delta-encode a ring of integer points: x0,y0,dx1,dy1,..."""
    out, px, py = [], 0, 0
    for x, y in r:
        x, y = int(round(x)), int(round(y))
        out += [x - px, y - py]
        px, py = x, y
    return out


def polys(ps):
    return [[ring(r) for r in p] for p in ps]


packed = {
    'origin': mp['origin'], 'k': mp['k'], 'ext': mp['ext'],
    'land': polys(mp['land']), 'water': polys(mp['water']), 'parks': polys(mp['parks']),
    'br': polys(mp['br']),
    'b': [[b['l'], b['k'], ring(b['o'])] + [ring(h) for h in b['h']] for b in mp['b']],
    's': [[s['r'], ring(s['c'])] for s in mp['s']],
}
for e in st['events']:
    if e.get('route'):
        e['route'] = ring(e['route'])
data = json.dumps({'map': packed, 'story': st}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
body = tpl.replace('__DATA__', data)
os.makedirs(out_dir, exist_ok=True)
open(os.path.join(out_dir, 'artifact.html'), 'w', encoding='utf-8').write(body)
head, rest = body.split('<!--/head-->', 1)
full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + head + '</head>\n<body>\n' + rest + '\n</body>\n</html>\n')
open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8').write(full)

# The page has exactly one executable inline script (the JSON data block is not executed).
inline = [m.group(2) for m in re.finditer(r'<script(\s[^>]*)?>(.*?)</script>', full, re.S)
          if not re.search(r'\bsrc=|application/json', m.group(1) or '')]
assert len(inline) == 1, f'expected one inline script, found {len(inline)}'
sha = base64.b64encode(hashlib.sha256(inline[0].encode('utf-8')).digest()).decode()
csp = '; '.join([
    "default-src 'none'",
    f"script-src 'sha256-{sha}' https://cdn.jsdelivr.net",
    "style-src 'unsafe-inline' https://fonts.googleapis.com",
    "font-src https://fonts.gstatic.com",
    "img-src 'self' data: blob:",
    "connect-src 'self'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'self'",
])
open(os.path.join(out_dir, 'csp.txt'), 'w').write(csp)
print('bundle', round(len(body.encode()) / 1024), 'KB')
