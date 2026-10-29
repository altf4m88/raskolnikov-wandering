"""Download Dostoevsky's Russian text (ilibrary.ru, 41 pages) and split it into chapters.

usage: python3 text_ru.py CACHE_DIR
Writes CACHE_DIR/ru_chapters.json in the same shape as chapters.json:
[{"part": "I".."VI" | "E", "ch": "I".., "text": "..."}]
"""
import sys, os, re, json, html, time, urllib.request

CACHE = sys.argv[1]
RAW = os.path.join(CACHE, 'ru_raw')
os.makedirs(RAW, exist_ok=True)

# ilibrary.ru serves one chapter per page, in the novel's order
ORDER = [(p, c) for p, n in (('I', 7), ('II', 7), ('III', 6), ('IV', 6), ('V', 5), ('VI', 8), ('E', 2))
         for c in ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII')[:n]]
assert len(ORDER) == 41

chapters = []
for i, (part, ch) in enumerate(ORDER, start=1):
    path = os.path.join(RAW, f'p{i}.html')
    if not os.path.exists(path):
        req = urllib.request.Request(f'https://ilibrary.ru/text/69/p.{i}/index.html', headers={'User-Agent': 'raskolnikov-wandering/1.0'})
        open(path, 'wb').write(urllib.request.urlopen(req, timeout=60).read())
        time.sleep(0.5)
    page = open(path, 'rb').read().decode('cp1251')
    # the chapter is a run of <z> paragraphs inside div#text; &#151; style references become em dashes
    region = page[page.index('<div id="text"'):page.index('<div id="tbd"')]
    paras = re.findall(r'(?s)<z>(.*?)</z>', region)
    text = html.unescape(' '.join(re.sub(r'<[^>]+>', ' ', z) for z in paras)).replace('\xad', '')
    chapters.append({'part': part, 'ch': ch, 'text': re.sub(r'\s+', ' ', text).strip()})

json.dump(chapters, open(os.path.join(CACHE, 'ru_chapters.json'), 'w'), ensure_ascii=False)
print('ru chapters', len(chapters), 'first words:', chapters[0]['text'][:60])
