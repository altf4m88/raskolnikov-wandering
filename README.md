# raskolnikov-wandering

**Raskolnikov Wandering**: a 3D, scene-by-scene map of Raskolnikov's walks in Dostoevsky's *Crime and Punishment* (1866), laid over the real street plan of St Petersburg.

Designed and developed by **@altf4m8** ([Instagram](https://instagram.com/altf4m8) · [GitHub](https://github.com/altf4m88)).

Open `index.html` in a browser. It is a single file. It needs a network connection for three.js (jsDelivr) and Google Fonts.

## What it shows

- **53 scenes over about 14 days, plus the Epilogue.** Each scene has its Part and chapter, an approximate clock time, a place, a summary, and one quotation from Constance Garnett's 1914 translation. Every quotation is machine-checked word for word against the Project Gutenberg text.
- **Routes along real streets.** Walks between scenes are routed over an OpenStreetMap street graph. Waypoints snap onto the nearest street segment, and the build removes out-and-back hops and rounds the corners. Solid lines mean the text gives or forces the streets; dashed lines are routes I inferred.
- **A sky for each scene.** Lighting is computed for 59.93° N on the scene's date, in local mean time. "Early July" in the novel is Old Style, which is the second half of July by our calendar.
- **Svidrigailov's last night** as an optional second track.
- **A confidence chip on every place:** *textual* (named in the novel), *traditional* (an initial such as "K—— Bridge" that local tradition has resolved), or *conjectural* (my own guess, with the reasoning given).
- **Measurements that test the text,** for example the famous "seven hundred and thirty" paces from the garret to the pawnbroker's.
- **Places & distances:** every place in order of appearance, with each scene set there, and how far he walks. That is about 48.5 km over the fourteen days, 18.0 km of it on streets the text gives, with a per-day chart and table. Every figure is a floor: walks run pin to pin along today's streets, and the novel's hours of aimless wandering can't be measured.

On a first visit a short introduction plays (skip it any time, or press Esc); **About this map → Replay the introduction** brings it back. Controls: drag to pan, right-drag or two fingers to rotate, scroll or pinch to zoom. ←/→ step through scenes, space plays. At 1× each scene stays on screen about as long as it takes to read its card (roughly 190 words a minute), and the walk is stretched to match; ½× and 2× are on the speed button. Links like `index.html#e13` or `#day-9` open a given scene or day.

## What is not certain

This map takes a position on several open questions, and you should know where.

- **Most addresses are traditions, not facts.** Dostoevsky hides places behind initials. Only the garret (Grazhdanskaya 19 / Stolyarny 5) and the pawnbroker's (Srednyaya Podyacheskaya 15 / Canal 104) have strong traditions, and both are still argued over. The police office has two rival traditions: Canal 67 (used here) and Sadovaya 28. Kozel's house, the tavern, Porfiry's "grey house", Potchinkov's and Svidrigailov's watch-tower have no agreed site. Their pins are guesses and are marked as such.
- **The chronology is a reconstruction.** The novel never numbers its days. The count here follows the text's own cues: "the last four days" of fever, then "two or three days" of fog in Part VI. Katerina Ivanovna's funeral, Porfiry's third visit and Svidrigailov's last night fall on a single day. Other reconstructions come out a day shorter or longer.
- **The "fever band" under the timeline is interpretation,** not data.
- **The base map is today's city.** Building footprints are present-day OSM, capped at six storeys. Bridges that did not exist in 1865 (Palace, Trinity, Birzhevoy, Betancourt) are removed, and the router avoids them. Nothing else is back-dated.
- **The 730 paces do not fit.** The text sends him "towards K. bridge". That route is about 1.1 km, and even the shortest street route today is about 0.7 km. At an ordinary 0.71 m pace, 730 paces is about 520 m.

### Checked against a printed edition

The Wordsworth Classics edition (Garnett translation, introduction by Keith Carabine) prints a hand-drawn map, "The St Petersburg of *Crime and Punishment*", with eight numbered sites. The scene card for each place it marks says whether that edition agrees.

| Book | This map |
|---|---|
| 1 Raskolnikov's room, 2 pawnbroker's, 4 St Isaac's, 6 Nikolaevsky Bridge, Konnogvardeisky Boulevard | agree |
| 8 Svidrigailov's suicide | agrees on the street (Bolshoy Prospekt, Petersburg Side); both guess the exact spot |
| 3 Sonia's room | **differs.** The book puts it east of Kokushkin Bridge; this map keeps Canal 73, west of it. Part V puts her house two doors from a "—sky" bridge, which fits Voznesensky but not Sennoy or Demidov to the east. |
| "Obukhovsky Prospect" | **adopted.** It was the 1865 name of the X. Prospect off the Hay Market. This map had said "Zabalkansky", a name given only in 1878. |
| 7 University | **added** as a landmark |

The book itself gets the islands wrong. It says Petrovsky Island "contains the fortress of St Peter and St Paul" and labels the Petersburg Side as Petrovsky Island. The fortress is on Zayachy (Hare) Island, and Petrovsky Island is the separate island where Raskolnikov dreams of the mare. Its Winter Palace (5) is drawn away from the Neva. The map is a sketch, so it can settle which street or bank a place is on, not which house.

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
tools/bundle.py       packs everything into src/app.html -> index.html (+ csp.txt for the container)
```

Run `tools/build.sh` for the whole pipeline. The first run downloads about 120 MB of OSM data into `./cache`. Use `tools/build.sh --bundle` to re-pack after editing only `src/app.html`.

The scenes, places and quotations live in `data/story.json`. If you change a quotation that does not occur verbatim in Garnett, `build_story.py` reports it.

## Deploy to Cloud Run

The repo builds into a small container: unprivileged nginx serving the page and a health check. The `Dockerfile` re-packs the page from `src/` and `data/` during the build, so the image always matches the source, not the committed `index.html`.

To deploy:

1. Once per Google Cloud project:

   ```bash
   gcloud auth login
   ```

   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
   ```

2. Build in Cloud Build and deploy. Run this from the repo root:

   ```bash
   gcloud run deploy raskolnikov-wandering --source . --region europe-north1 --allow-unauthenticated
   ```

   Notes:
   - `europe-north1` (Finland) is the closest region to Petersburg; any region works.
   - `--allow-unauthenticated` makes the page public. Some organisation policies forbid this. Drop the flag to keep the service private.
   - Add `--max-instances 2` if you want a hard cap on cost.

What the container does:

- **Port:** listens on `$PORT`, which Cloud Run sets. The default is 8080.
- **Endpoints:** serves `/` (and `/index.html`) plus `/healthz`. Everything else returns 404, so the data files and build tools are never exposed.
- **Compression:** sends the page pre-gzipped, about 290 KB instead of 1.4 MB, with `Cache-Control: no-cache` and an ETag, so repeat visits get a `304`.
- **Security headers:** a Content-Security-Policy that pins the page's one inline script by its SHA-256 hash and allows only jsDelivr (three.js) and Google Fonts. It also sets `nosniff`, a referrer policy, a permissions policy and HSTS.
- **Base images:** pulled through `mirror.gcr.io`, Google's cache of Docker Hub, to avoid Docker Hub's anonymous pull limits.

To test the container locally:

```bash
docker build -t raskolnikov-wandering .
```

```bash
docker run --rm -p 8080:8080 raskolnikov-wandering
```

Then open http://localhost:8080.

## Sources and licences

- F. M. Dostoevsky, *Crime and Punishment*, trans. Constance Garnett (1914). Public domain, [Project Gutenberg #2554](https://www.gutenberg.org/ebooks/2554). Russian text consulted at [ilibrary.ru](https://ilibrary.ru/text/69/p.1/index.html).
- Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). `data/map.json` and the geometry embedded in `index.html` are derived from OSM and are available under the [Open Database License](https://opendatacommons.org/licenses/odbl/).
- Address traditions come from popular guides ([peterburg2.ru](https://peterburg2.ru/articles/marshrut-po-peterburgu-adresa-geroev-romana-prestuplenie-i-nakazanie-231759.html), [Vokrug Sveta](https://www.vokrugsveta.ru/articles/mesto-prestupleniya-i-nakazaniya-izmenit-nelzya-gde-snimali-novyi-serial-po-romanu-fedora-dostoevskogo-id5955567/), KudaGo), not from a critical edition. Treat them accordingly.
- Rendering: [three.js](https://threejs.org/) r147.
