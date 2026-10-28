"""Download Garnett's translation (Project Gutenberg #2554) and split it into chapters.

usage: python3 text.py CACHE_DIR
Writes CACHE_DIR/chapters.json: [{"part": "I".."VI" | "E", "ch": "I".., "text": "..."}]
"""
import sys, os, re, json, urllib.request

CACHE = sys.argv[1]
os.makedirs(CACHE, exist_ok=True)
src = os.path.join(CACHE, 'pg2554.txt')
if not os.path.exists(src):
    req = urllib.request.Request('https://www.gutenberg.org/cache/epub/2554/pg2554.txt', headers={'User-Agent': 'raskolnikov-wandering/1.0'})
    open(src, 'wb').write(urllib.request.urlopen(req, timeout=120).read())

T = open(src, encoding='utf-8').read().replace('\r\n', '\n')
T = T[T.index('CRIME AND PUNISHMENT\n\n\n\n\nPART I'):T.index('*** END')]  # skip the preface and contents
chapters, part, cur = [], None, None
for ln in T.split('\n'):
    s = ln.strip()
    if re.fullmatch(r'PART [IVX]+', s):
        part = s.split()[1]; continue
    if s == 'EPILOGUE':
        part = 'E'; continue
    if re.fullmatch(r'CHAPTER [IVX]+', s) or (part == 'E' and s in ('I', 'II')):
        cur = {'part': part, 'ch': s.split()[-1], 'text': []}; chapters.append(cur); continue
    if cur is not None:
        cur['text'].append(ln)
for c in chapters:
    c['text'] = re.sub(r'\s+', ' ', '\n'.join(c['text'])).strip()
assert len(chapters) == 41, len(chapters)
json.dump(chapters, open(os.path.join(CACHE, 'chapters.json'), 'w'))
print('chapters', len(chapters))
