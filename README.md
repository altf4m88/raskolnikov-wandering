# raskolnikov-wandering

**Raskolnikov's Petersburg**: a 3D, scene-by-scene map of Raskolnikov's walks in Dostoevsky's *Crime and Punishment* (1866), laid over the real street plan of St Petersburg.

Open `index.html` in a browser. It is a single file. It needs a network connection for three.js (jsDelivr) and Google Fonts.

## What it shows

- **53 scenes over about 14 days, plus the Epilogue.** Each scene has its Part and chapter, an approximate clock time, a place, a summary, and one quotation from Constance Garnett's 1914 translation. Every quotation is machine-checked word for word against the Project Gutenberg text.
- **Routes along real streets.** Walks between scenes are routed over an OpenStreetMap street graph. Solid lines mean the text gives or forces the streets; dashed lines are routes I inferred.
- **A sky for each scene.** Lighting is computed for 59.93° N on the scene's date, in local mean time. "Early July" in the novel is Old Style, which is the second half of July by our calendar.
- **Svidrigailov's last night** as an optional second track.
- **A confidence chip on every place:** *textual* (named in the novel), *traditional* (an initial such as "K—— Bridge" that local tradition has resolved), or *conjectural* (my own guess, with the reasoning given).
- **Measurements that test the text,** for example the famous "seven hundred and thirty" paces from the garret to the pawnbroker's.

Controls: drag to pan, right-drag or two fingers to rotate, scroll or pinch to zoom. ←/→ step through scenes, space plays. Links like `index.html#e13` or `#day-9` open a given scene or day.

## What is not certain

This map takes a position on several open questions, and you should know where.

- **Most addresses are traditions, not facts.** Dostoevsky hides places behind initials. Only the garret (Grazhdanskaya 19 / Stolyarny 5) and the pawnbroker's (Srednyaya Podyacheskaya 15 / Canal 104) have strong traditions, and both are still argued over. The police office has two rival traditions: Canal 67 (used here) and Sadovaya 28. Kozel's house, the tavern, Porfiry's "grey house", Potchinkov's and Svidrigailov's watch-tower have no agreed site. Their pins are guesses and are marked as such.
- **The chronology is a reconstruction.** The novel never numbers its days. The count here follows the text's own cues: "the last four days" of fever, then "two or three days" of fog in Part VI. Katerina Ivanovna's funeral, Porfiry's third visit and Svidrigailov's last night fall on a single day. Other reconstructions come out a day shorter or longer.
- **The "fever band" under the timeline is interpretation,** not data.
- **The base map is today's city.** Building footprints are present-day OSM, capped at six storeys. Bridges that did not exist in 1865 (Palace, Trinity, Birzhevoy, Betancourt) are removed, and the router avoids them. Nothing else is back-dated.
- **The 730 paces do not fit.** The text sends him "towards K. bridge". That route is about 1.1 km, and even the shortest street route today is about 0.7 km. At an ordinary 0.71 m pace, 730 paces is about 520 m.

### Garnett against the Russian

These were found by checking the place names against the Russian text:

| Garnett | Russian | Meaning |
|---|---|---|
| "S. Place" | в С—м переулке | S—— *Lane* (Stolyarny) |
| "walking along Vassilyevsky Prospect" | через В—й проспект | the V—— Prospect (Voznesensky) |
| "near the bridge to Vassilyevsky Ostrov" | на набережную Малой Невы, на Васильевском острове, подле моста | *on* the island, by the bridge |
| "That's in Voskresensky" | на Вознесенском | Voznesensky Prospekt |
| "Third Street in Vassilyevsky Island" | в Третьей линии, на Малом проспекте | the Third *Line*, at Maly Prospekt |
| "I am done for!" | Уездили клячу! | "They've driven the nag to death!", which echoes the mare dream |

## How it is built

```
tools/fetch_osm.py    OSM API tiles + full water relations  -> cache/osm_raw, cache/osm_rel
tools/text.py         Gutenberg #2554 split into 41 chapters -> cache/chapters.json
tools/build_map.py    land/water/parks/bridges/buildings + walking graph -> data/map.json
tools/build_story.py  checks quotes, routes every walk, measures them -> data/story.built.json
tools/bundle.py       packs everything into src/app.html -> index.html
```

Run `tools/build.sh` for the whole pipeline. The first run downloads about 120 MB of OSM data into `./cache`. Use `tools/build.sh --bundle` to re-pack after editing only `src/app.html`.

The scenes, places and quotations live in `data/story.json`. If you change a quotation that does not occur verbatim in Garnett, `build_story.py` reports it.

## Sources and licences

- F. M. Dostoevsky, *Crime and Punishment*, trans. Constance Garnett (1914). Public domain, [Project Gutenberg #2554](https://www.gutenberg.org/ebooks/2554). Russian text consulted at [ilibrary.ru](https://ilibrary.ru/text/69/p.1/index.html).
- Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). `data/map.json` and the geometry embedded in `index.html` are derived from OSM and are available under the [Open Database License](https://opendatacommons.org/licenses/odbl/).
- Address traditions come from popular guides ([peterburg2.ru](https://peterburg2.ru/articles/marshrut-po-peterburgu-adresa-geroev-romana-prestuplenie-i-nakazanie-231759.html), [Vokrug Sveta](https://www.vokrugsveta.ru/articles/mesto-prestupleniya-i-nakazaniya-izmenit-nelzya-gde-snimali-novyi-serial-po-romanu-fedora-dostoevskogo-id5955567/), KudaGo), not from a critical edition. Treat them accordingly.
- Rendering: [three.js](https://threejs.org/) r147.
